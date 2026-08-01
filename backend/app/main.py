import os
from datetime import date, datetime
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import Alerta, Estacao, Gato, PushSubscription, Refeicao, SessionLocal, UsoCaixa
from app.push_service import enviar_push_para_todos

load_dotenv()

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")

app = FastAPI(title="SmartCat API & PWA", version="1.0.0")

# --- Descobre o caminho absoluto do diretório 'app' ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# --- Montagem dos Arquivos Estáticos ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Rota Principal: Serve o Frontend PWA ---
@app.get("/", response_class=HTMLResponse)
def read_index():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>SmartCat API Online! (Arquivo index.html não encontrado)</h1>"


# --- Service Worker servido na RAIZ ---
# Precisa estar em "/" (não em "/static/sw.js") para poder controlar
# a página inteira do app. Um Service Worker só controla páginas dentro
# do seu próprio caminho ou abaixo dele — em /static/ ele nunca
# controlaria a página principal, e navigator.serviceWorker.ready
# ficaria esperando para sempre (era por isso que o toggle travava).
@app.get("/sw.js")
def service_worker():
    sw_path = os.path.join(STATIC_DIR, "sw.js")
    return FileResponse(sw_path, media_type="application/javascript")


# --- Schemas de Validação (Pydantic) ---
class GatoCreate(BaseModel):
    tag_rfid: str
    nome: str
    data_nascimento: date
    peso_meta_g: Optional[float] = None
    limite_jejum_horas: Optional[int] = 24
    limite_caixa_segundos: Optional[int] = 300


# --- Endpoints REST API para o PWA ---
@app.post("/api/gatos")
def criar_gato(gato: GatoCreate, db: Session = Depends(get_db)):
    db_gato = db.query(Gato).filter(Gato.tag_rfid == gato.tag_rfid).first()
    if db_gato:
        raise HTTPException(status_code=400, detail="Tag RFID já cadastrada.")

    novo_gato = Gato(
        tag_rfid=gato.tag_rfid,
        nome=gato.nome,
        data_nascimento=gato.data_nascimento,
        peso_meta_g=gato.peso_meta_g,
        limite_jejum_horas=gato.limite_jejum_horas,
        limite_caixa_segundos=gato.limite_caixa_segundos,
    )
    db.add(novo_gato)
    db.commit()
    db.refresh(novo_gato)
    return novo_gato


@app.get("/api/gatos")
def listar_gatos(db: Session = Depends(get_db)):
    return db.query(Gato).all()


@app.get("/api/refeicoes")
def listar_refeicoes(db: Session = Depends(get_db)):
    return db.query(Refeicao).order_by(Refeicao.created_at.desc()).limit(50).all()


@app.get("/api/caixa-areia")
def listar_uso_caixa(db: Session = Depends(get_db)):
    return db.query(UsoCaixa).order_by(UsoCaixa.created_at.desc()).limit(50).all()


@app.get("/api/eventos")
def listar_eventos(db: Session = Depends(get_db)):
    """Feed unificado de atividade: refeições + uso da caixa de areia,
    já com nome do gato e nome da estação resolvidos."""
    eventos = []

    refeicoes = db.query(Refeicao).order_by(Refeicao.created_at.desc()).limit(50).all()
    for r in refeicoes:
        eventos.append({
            "tipo": "REFEICAO",
            "created_at": r.created_at,
            "gato_nome": r.gato.nome if r.gato else f"Tag desconhecida ({r.gato_tag})",
            "estacao_nome": r.estacao.nome if r.estacao else (r.estacao_mac or "Estação desconhecida"),
            "consumo_g": r.consumo_g,
        })

    usos_caixa = db.query(UsoCaixa).order_by(UsoCaixa.created_at.desc()).limit(50).all()
    for u in usos_caixa:
        eventos.append({
            "tipo": "CAIXA",
            "created_at": u.created_at,
            "gato_nome": u.gato.nome if u.gato else f"Tag desconhecida ({u.gato_tag})",
            "estacao_nome": u.estacao.nome if u.estacao else (u.estacao_mac or "Estação desconhecida"),
            "duracao_visita_s": u.duracao_visita_s,
            "alerta_retencao": u.alerta_retencao,
        })

    eventos.sort(key=lambda e: e["created_at"], reverse=True)
    return eventos[:50]

# --- Adicione este Schema abaixo do GatoCreate ---
class GatoUpdate(BaseModel):
    tag_rfid: Optional[str] = None
    nome: Optional[str] = None
    data_nascimento: Optional[date] = None
    peso_meta_g: Optional[float] = None
    limite_jejum_horas: Optional[int] = None
    limite_caixa_segundos: Optional[int] = None


# --- Novos Endpoints do CRUD de Pets ---

@app.put("/api/gatos/{gato_id}")
def atualizar_gato(gato_id: int, gato_data: GatoUpdate, db: Session = Depends(get_db)):
    db_gato = db.query(Gato).filter(Gato.id == gato_id).first()
    if not db_gato:
        raise HTTPException(status_code=404, detail="Gato não encontrado.")

    # Se alterou a Tag RFID, verifica se já não pertence a outro gato
    if gato_data.tag_rfid and gato_data.tag_rfid != db_gato.tag_rfid:
        tag_existente = db.query(Gato).filter(Gato.tag_rfid == gato_data.tag_rfid).first()
        if tag_existente:
            raise HTTPException(status_code=400, detail="Esta Tag RFID já está em uso por outro pet.")

    # Atualiza apenas os campos enviados
    update_dict = gato_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_gato, key, value)

    db.commit()
    db.refresh(db_gato)
    return db_gato


@app.delete("/api/gatos/{gato_id}")
def deletar_gato(gato_id: int, db: Session = Depends(get_db)):
    db_gato = db.query(Gato).filter(Gato.id == gato_id).first()
    if not db_gato:
        raise HTTPException(status_code=404, detail="Gato não encontrado.")

    db.delete(db_gato)
    db.commit()
    return {"message": f"Pet {db_gato.nome} removido com sucesso."}


# --- Schemas Pydantic para Estações ---
class EstacaoCreate(BaseModel):
    mac_address: str
    nome: str
    tipo: str  # "COMIDA" ou "CAIXA"

class EstacaoUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None

# --- Endpoints da API de Estações ---
@app.get("/api/estacoes")
def listar_estacoes(db: Session = Depends(get_db)):
    return db.query(Estacao).all()

@app.post("/api/estacoes")
def criar_estacao(estacao: EstacaoCreate, db: Session = Depends(get_db)):
    db_existente = db.query(Estacao).filter(Estacao.mac_address == estacao.mac_address).first()
    if db_existente:
        raise HTTPException(status_code=400, detail="Dispositivo com este MAC já cadastrado.")
    
    nova_estacao = Estacao(**estacao.dict())
    db.add(nova_estacao)
    db.commit()
    db.refresh(nova_estacao)
    return nova_estacao

@app.put("/api/estacoes/{estacao_id}")
def atualizar_estacao(estacao_id: int, estacao_data: EstacaoUpdate, db: Session = Depends(get_db)):
    db_estacao = db.query(Estacao).filter(Estacao.id == estacao_id).first()
    if not db_estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada.")
    
    update_data = estacao_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_estacao, key, value)
    
    db.commit()
    db.refresh(db_estacao)
    return db_estacao

@app.delete("/api/estacoes/{estacao_id}")
def deletar_estacao(estacao_id: int, db: Session = Depends(get_db)):
    db_estacao = db.query(Estacao).filter(Estacao.id == estacao_id).first()
    if not db_estacao:
        raise HTTPException(status_code=404, detail="Estação não encontrada.")
    
    db.delete(db_estacao)
    db.commit()
    return {"message": "Estação removida."}


# ======================================================
# 🚨 ALERTAS DE SAÚDE
# ======================================================

@app.get("/api/alertas")
def listar_alertas(apenas_abertos: bool = False, db: Session = Depends(get_db)):
    """Lista os alertas de saúde gerados pelo sistema (mais recentes primeiro).
    Use ?apenas_abertos=true para retornar somente os ainda não resolvidos."""
    query = db.query(Alerta)
    if apenas_abertos:
        query = query.filter(Alerta.resolvido == False)  # noqa: E712

    alertas = query.order_by(Alerta.created_at.desc()).limit(100).all()
    return [
        {
            "id": a.id,
            "gato_id": a.gato_id,
            "gato_nome": a.gato.nome if a.gato else "Pet removido",
            "tipo": a.tipo,
            "severidade": a.severidade,
            "mensagem": a.mensagem,
            "resolvido": a.resolvido,
            "created_at": a.created_at,
        }
        for a in alertas
    ]


@app.put("/api/alertas/{alerta_id}/resolver")
def resolver_alerta(alerta_id: int, db: Session = Depends(get_db)):
    """Marca um alerta como resolvido/reconhecido pelo tutor."""
    db_alerta = db.query(Alerta).filter(Alerta.id == alerta_id).first()
    if not db_alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")

    db_alerta.resolvido = True
    db_alerta.resolvido_em = datetime.utcnow()
    db.commit()
    db.refresh(db_alerta)
    return db_alerta


# ======================================================
# 🔔 NOTIFICAÇÕES WEB PUSH
# ======================================================

class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: dict  # {"p256dh": "...", "auth": "..."}


@app.get("/api/push/vapid-public-key")
def obter_chave_publica_vapid():
    """Fornece a chave pública VAPID para o frontend registrar a inscrição push."""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=503,
            detail="Notificações push não configuradas no servidor (VAPID_PUBLIC_KEY ausente).",
        )
    return {"publicKey": VAPID_PUBLIC_KEY}


@app.post("/api/push/subscribe")
def inscrever_push(sub: PushSubscriptionCreate, db: Session = Depends(get_db)):
    """Registra (ou atualiza) a inscrição de push do navegador do tutor."""
    p256dh = sub.keys.get("p256dh")
    auth = sub.keys.get("auth")
    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Chaves de inscrição inválidas.")

    existente = db.query(PushSubscription).filter(PushSubscription.endpoint == sub.endpoint).first()
    if existente:
        existente.p256dh = p256dh
        existente.auth = auth
        db.commit()
        return {"message": "Inscrição atualizada."}

    nova = PushSubscription(endpoint=sub.endpoint, p256dh=p256dh, auth=auth)
    db.add(nova)
    db.commit()
    return {"message": "Inscrição registrada com sucesso."}


@app.post("/api/push/unsubscribe")
def desinscrever_push(sub: PushSubscriptionCreate, db: Session = Depends(get_db)):
    """Remove a inscrição de push (ex.: usuário desativou notificações)."""
    db.query(PushSubscription).filter(PushSubscription.endpoint == sub.endpoint).delete()
    db.commit()
    return {"message": "Inscrição removida."}


@app.post("/api/push/test")
def enviar_notificacao_teste(db: Session = Depends(get_db)):
    """Dispara uma notificação push de teste para todos os tutores inscritos.
    Serve pra validar rapidamente se a configuração VAPID e a inscrição do
    navegador estão funcionando, sem precisar esperar um alerta real."""
    total_inscricoes = db.query(PushSubscription).count()
    if total_inscricoes == 0:
        raise HTTPException(
            status_code=400,
            detail="Nenhum navegador está inscrito para notificações ainda. "
                   "Clique em 'Ativar notificações' antes de testar.",
        )

    resultado = enviar_push_para_todos(
        db,
        titulo="🐱 SmartCat — Notificação de Teste",
        corpo="Se você recebeu isso, as notificações push estão funcionando! 🎉",
        dados={"tipo": "TESTE"},
    )

    if not resultado["configurado"]:
        raise HTTPException(
            status_code=503,
            detail="Notificações push não configuradas no servidor "
                   "(gere as chaves com scripts/generate_vapid_keys.py e configure o .env).",
        )

    return {
        "message": f"Notificação de teste enviada para {resultado['enviadas']} dispositivo(s).",
        **resultado,
    }