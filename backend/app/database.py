import os
from datetime import datetime, date
from sqlalchemy import Column, DateTime, Date, Float, Integer, String, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartcat.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Gato(Base):
    __tablename__ = "gatos"

    id = Column(Integer, primary_key=True, index=True)
    tag_rfid = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    data_nascimento = Column(Date, nullable=False)
    peso_meta_g = Column(Float, nullable=True)
    limite_jejum_horas = Column(Integer, default=24)        # Padrão: 24 horas
    limite_caixa_segundos = Column(Integer, default=300)   # Padrão: 5 minutos (300s)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    refeicoes = relationship("Refeicao", back_populates="gato")
    visitas_caixa = relationship("UsoCaixa", back_populates="gato")


class Refeicao(Base):
    __tablename__ = "refeicoes"

    id = Column(Integer, primary_key=True, index=True)
    gato_id = Column(Integer, ForeignKey("gatos.id"), nullable=True)
    estacao_id = Column(String)
    gato_tag = Column(String)
    consumo_g = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    gato = relationship("Gato", back_populates="refeicoes")


class UsoCaixa(Base):
    __tablename__ = "uso_caixa"

    id = Column(Integer, primary_key=True, index=True)
    gato_id = Column(Integer, ForeignKey("gatos.id"), nullable=True)
    estacao_id = Column(String)
    gato_tag = Column(String)
    duracao_visita_s = Column(Integer)
    alerta_retencao = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    gato = relationship("Gato", back_populates="visitas_caixa")

# Adicione esta classe ao final do seu database.py
class Estacao(Base):
    __tablename__ = "estacoes"

    id = Column(Integer, primary_key=True, index=True)
    mac_address = Column(String, unique=True, index=True, nullable=False) # Ex: ESP32_240AC4000110
    nome = Column(String, nullable=False)                                # Ex: Pote da Sala
    tipo = Column(String, nullable=False)                                # "COMIDA" ou "CAIXA"
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)