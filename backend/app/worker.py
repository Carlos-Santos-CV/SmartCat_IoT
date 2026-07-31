import json
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
from app.database import Refeicao, SessionLocal, UsoCaixa

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT = int(os.getenv("MQTT_PORT", 1883))


# --- Callback de Recepção do MQTT ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        db = SessionLocal()

        if "estacao_comida" in msg.topic:
            evento = Refeicao(
                estacao_id=payload.get("estacao_id"),
                gato_tag=payload.get("gato_tag"),
                gato_nome=payload.get("gato_nome"),
                consumo_g=payload.get("consumo_g"),
            )
            db.add(evento)
            print(
                f"[WORKER MQTT] Refeição gravada no DB: {payload.get('gato_nome')} ({payload.get('consumo_g')}g)"
            )

        elif "caixa_areia" in msg.topic:
            evento = UsoCaixa(
                estacao_id=payload.get("estacao_id"),
                gato_nome=payload.get("gato_nome"),
                duracao_visita_s=payload.get("duracao_visita_s"),
                alerta_retencao=payload.get("alerta_retencao"),
            )
            db.add(evento)
            print(
                f"[WORKER MQTT] Visita à caixa gravada no DB: {payload.get('gato_nome')} ({payload.get('duracao_visita_s')}s)"
            )

        db.commit()
        db.close()
    except Exception as e:
        print(f"[WORKER ERRO] Falha ao processar payload MQTT: {e}")


# --- Regra de Negócio/Saúde: Checagem de Jejum Prolongado (> 24h) ---
def verificar_jejum_gatos():
    db = SessionLocal()
    limite_24h = datetime.utcnow() - timedelta(hours=24)

    # Consulta a última refeição do gato Thor
    ultima_refeicao = (
        db.query(Refeicao)
        .filter(Refeicao.gato_nome == "Thor")
        .order_by(Refeicao.created_at.desc())
        .first()
    )

    if not ultima_refeicao or ultima_refeicao.created_at < limite_24h:
        print(
            "\n[ALERTA SAÚDE] 🚨 ATENÇÃO: O gato Thor não realiza refeições há mais de 24 horas!"
        )
        # Espaço reservado para o disparo da chamada WebPush ao PWA
    else:
        print(
            f"[CHECK SAÚDE] ✅ Alimentação do Thor OK. Última refeição: {ultima_refeicao.created_at}"
        )

    db.close()


def start_worker():
    # Inicializa o cliente MQTT
    client = mqtt.Client()
    client.on_message = on_message

    print(f"[WORKER] Conectando ao Broker MQTT: {BROKER}:{PORT}...")
    try:
        client.connect(BROKER, PORT, 60)
        client.subscribe("smartcat/+/telemetria")
        client.loop_start()
    except Exception as e:
        print(f"[WORKER ERRO] Erro ao conectar ao broker MQTT: {e}")

    # Inicializa o Agendador de Alertas (APScheduler)
    scheduler = BackgroundScheduler()
    # Executa a checagem a cada 15 minutos (ou ajuste para testes rápidos, ex: seconds=30)
    scheduler.add_job(verificar_jejum_gatos, "interval", minutes=15)
    scheduler.start()

    print(
        "[WORKER] Escutador MQTT e Agendador de Alertas iniciados com sucesso!"
    )


if __name__ == "__main__":
    start_worker()
    while True:
        time.sleep(1)