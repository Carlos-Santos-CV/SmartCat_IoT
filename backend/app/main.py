import os
from datetime import date
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import Estacao, Gato, Refeicao, SessionLocal, UsoCaixa

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