import os
from datetime import date
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import Gato, Refeicao, SessionLocal, UsoCaixa

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