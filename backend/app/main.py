from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal, Refeicao, UsoCaixa

# A variável OBRIGATORIAMENTE precisa se chamar 'app'
app = FastAPI(title="SmartCat API", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "online", "sistema": "SmartCat Cloud Backend"}

@app.get("/api/refeicoes")
def listar_refeicoes(db: Session = Depends(get_db)):
    return db.query(Refeicao).order_by(Refeicao.created_at.desc()).limit(50).all()

@app.get("/api/caixa-areia")
def listar_uso_caixa(db: Session = Depends(get_db)):
    return db.query(UsoCaixa).order_by(UsoCaixa.created_at.desc()).limit(50).all()