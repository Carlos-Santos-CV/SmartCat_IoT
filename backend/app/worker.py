import json
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
from app.database import Gato, Refeicao, SessionLocal, UsoCaixa

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT = int(os.getenv("MQTT_PORT", 1883))


# --- Callback de Recepção de Dados via MQTT ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        db = SessionLocal()

        # 1. Identifica a tag RFID recebida do ESP32
        tag_recebida = payload.get("gato_tag")
        gato = db.query(Gato).filter(Gato.tag_rfid == tag_recebida).first()
        gato_id = gato.id if gato else None
        nome_gato = gato.nome if gato else f"Tag Desconhecida ({tag_recebida})"

        # 2. Evento da Estação de Comida
        if "estacao_comida" in msg.topic:
            evento = Refeicao(
                gato_id=gato_id,
                estacao_id=payload.get("estacao_id"),
                gato_tag=tag_recebida,
                consumo_g=payload.get("consumo_g"),
            )
            db.add(evento)
            print(f"[WORKER MQTT] Refeição gravada: {nome_gato} ({payload.get('consumo_g')}g)")

        # 3. Evento da Caixa de Areia
        elif "caixa_areia" in msg.topic:
            duracao = payload.get("duracao_visita_s", 0)
            
            # Checa o limite customizado do gato (ou usa 300s como fallback)
            limite_caixa = gato.limite_caixa_segundos if gato else 300
            gerar_alerta = duracao > limite_caixa

            evento = UsoCaixa(
                gato_id=gato_id,
                estacao_id=payload.get("estacao_id"),
                duracao_visita_s=duracao,
                alerta_retencao=gerar_alerta
            )
            db.add(evento)
            
            if gerar_alerta:
                print(f"[ALERTA RETENÇÃO] 🚨 {nome_gato} permaneceu {duracao}s na caixa (Limite: {limite_caixa}s)!")
            else:
                print(f"[WORKER MQTT] Caixa de Areia gravada: {nome_gato} ({duracao}s)")

        db.commit()
        db.close()
    except Exception as e:
        print(f"[WORKER ERRO] Falha ao processar payload: {e}")


# --- Regra de Saúde Agendada: Varredura Dinâmica de Jejum ---
def verificar_jejum_todos_gatos():
    db = SessionLocal()
    gatos = db.query(Gato).all()

    if not gatos:
        print("[CHECK SAÚDE] Nenhum gato cadastrado no sistema até o momento.")
        db.close()
        return

    for gato in gatos:
        limite_tempo = datetime.utcnow() - timedelta(hours=gato.limite_jejum_horas)

        ultima_refeicao = (
            db.query(Refeicao)
            .filter(Refeicao.gato_id == gato.id)
            .order_by(Refeicao.created_at.desc())
            .first()
        )

        if not ultima_refeicao or ultima_refeicao.created_at < limite_tempo:
            print(
                f"[ALERTA JEJUM] 🚨 {gato.nome} não realiza refeições há mais de {gato.limite_jejum_horas}h!"
            )
            # Ponto de integração para o WebPush
        else:
            print(f"[CHECK SAÚDE] ✅ {gato.nome}: Alimentação dentro do prazo normal.")

    db.close()


def start_worker():
    client = mqtt.Client()
    client.on_message = on_message

    print(f"[WORKER] Conectando ao Broker MQTT: {BROKER}:{PORT}...")
    try:
        client.connect(BROKER, PORT, 60)
        client.subscribe("smartcat/+/telemetria")
        client.loop_start()
    except Exception as e:
        print(f"[WORKER ERRO] Erro ao conectar ao broker: {e}")

    # Agendador APScheduler (executa a checagem a cada 15 minutos)
    scheduler = BackgroundScheduler()
    scheduler.add_job(verificar_jejum_todos_gatos, "interval", minutes=15)
    scheduler.start()

    print("[WORKER] Escutador Dinâmico e Agendador de Alertas ativos!")


if __name__ == "__main__":
    start_worker()
    while True:
        time.sleep(1)