import os
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Lê a URL do PostgreSQL das variáveis de ambiente (ou usa SQLite por padrão se for rodar standalone)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartcat.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Refeicao(Base):
    __tablename__ = "refeicoes"

    id = Column(Integer, primary_key=True, index=True)
    estacao_id = Column(String)
    gato_tag = Column(String)
    gato_nome = Column(String)
    consumo_g = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsoCaixa(Base):
    __tablename__ = "uso_caixa"

    id = Column(Integer, primary_key=True, index=True)
    estacao_id = Column(String)
    gato_nome = Column(String)
    duracao_visita_s = Column(Integer)
    alerta_retencao = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)


# Cria as tabelas automaticamente no banco se elas não existirem
Base.metadata.create_all(bind=engine)