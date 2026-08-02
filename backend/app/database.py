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
    estacao_id = Column(Integer, ForeignKey("estacoes.id"), nullable=True)
    estacao_mac = Column(String)  # MAC bruto recebido via MQTT — preservado mesmo se a estação ainda não estiver cadastrada
    gato_tag = Column(String)
    consumo_g = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    gato = relationship("Gato", back_populates="refeicoes")
    estacao = relationship("Estacao", back_populates="refeicoes")


class UsoCaixa(Base):
    __tablename__ = "uso_caixa"

    id = Column(Integer, primary_key=True, index=True)
    gato_id = Column(Integer, ForeignKey("gatos.id"), nullable=True)
    estacao_id = Column(Integer, ForeignKey("estacoes.id"), nullable=True)
    estacao_mac = Column(String)  # MAC bruto recebido via MQTT — preservado mesmo se a estação ainda não estiver cadastrada
    gato_tag = Column(String)
    duracao_visita_s = Column(Integer)
    alerta_retencao = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    gato = relationship("Gato", back_populates="visitas_caixa")
    estacao = relationship("Estacao", back_populates="visitas_caixa")

# Adicione esta classe ao final do seu database.py
class Estacao(Base):
    __tablename__ = "estacoes"

    id = Column(Integer, primary_key=True, index=True)
    mac_address = Column(String, unique=True, index=True, nullable=False) # Ex: ESP32_240AC4000110
    nome = Column(String, nullable=False)                                # Ex: Pote da Sala
    tipo = Column(String, nullable=False)                                # "COMIDA" ou "CAIXA"
    created_at = Column(DateTime, default=datetime.utcnow)

    refeicoes = relationship("Refeicao", back_populates="estacao")
    visitas_caixa = relationship("UsoCaixa", back_populates="estacao")


class Alerta(Base):
    """Registro persistente de alertas de saúde/comportamento gerados pelo sistema."""
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    gato_id = Column(Integer, ForeignKey("gatos.id"), nullable=False)
    tipo = Column(String, nullable=False)          # "JEJUM" | "RETENCAO_CAIXA" | "PESO"
    severidade = Column(String, default="ALTA")    # "ALTA" | "MEDIA" | "BAIXA"
    mensagem = Column(String, nullable=False)
    resolvido = Column(Boolean, default=False)
    resolvido_em = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    gato = relationship("Gato")


class PushSubscription(Base):
    """Inscrição do navegador do tutor para receber notificações Web Push."""
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, unique=True, index=True, nullable=False)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# ======================================================
# Migração leve de colunas ausentes
# ======================================================
# O projeto não usa Alembic — Base.metadata.create_all() só CRIA tabelas
# que ainda não existem, nunca ALTERA tabelas já existentes. Isso significa
# que um banco criado antes de um novo Column ser adicionado a um modelo
# (ex.: estacao_mac) fica com a tabela desatualizada, e qualquer SELECT
# que toque nessa coluna quebra com "no such column" / "UndefinedColumn".
#
# Esta função roda automaticamente na inicialização, detecta colunas que os
# modelos esperam mas que ainda não existem no banco, e adiciona via
# ALTER TABLE — sem apagar nada. Idempotente: rodar de novo não faz nada
# se as colunas já existirem.
def _migrar_colunas_faltantes():
    from sqlalchemy import inspect, text

    colunas_esperadas = [
        ("refeicoes", "estacao_id", "INTEGER"),
        ("refeicoes", "estacao_mac", "VARCHAR"),
        ("uso_caixa", "estacao_id", "INTEGER"),
        ("uso_caixa", "estacao_mac", "VARCHAR"),
    ]

    inspector = inspect(engine)
    tabelas_existentes = set(inspector.get_table_names())

    with engine.begin() as conn:
        for tabela, coluna, tipo_sql in colunas_esperadas:
            if tabela not in tabelas_existentes:
                continue  # tabela nova — create_all() já cuidou dela com o schema certo
            colunas_atuais = {c["name"] for c in inspector.get_columns(tabela)}
            if coluna not in colunas_atuais:
                print(f"[MIGRATE] Adicionando coluna ausente: {tabela}.{coluna}")
                conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo_sql}"))


_migrar_colunas_faltantes()