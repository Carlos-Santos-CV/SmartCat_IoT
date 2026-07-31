import json
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from pywebpush import WebPushException, webpush
from app.database import Alerta, Gato, PushSubscription, Refeicao, SessionLocal, UsoCaixa

load_dotenv()

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT = int(os.getenv("MQTT_PORT", 1883))

# --- Configuração de Web Push (VAPID) ---
# Gere seu par de chaves com o script scripts/generate_vapid_keys.py
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "mailto:contato@smartcat.local")

# Janela de deduplicação: não repete o mesmo tipo de alerta para o mesmo
# gato se já existe um alerta em aberto (não resolvido) gerado dentro desse intervalo.
JANELA_DEDUPLICACAO_HORAS = 2


def _enviar_push_para_todos(db, titulo: str, corpo: str, dados: dict):
    """Envia uma notificação Web Push para todos os tutores inscritos.
    Assinaturas inválidas/expiradas (HTTP 404/410) são removidas automaticamente."""
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        print("[PUSH] Chaves VAPID não configuradas — pulando envio de notificação.")
        return

    inscricoes = db.query(PushSubscription).all()
    payload = json.dumps({"title": titulo, "body": corpo, "data": dados})

    for sub in inscricoes:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
            )
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                print(f"[PUSH] Assinatura expirada, removendo: {sub.endpoint[:40]}...")
                db.delete(sub)
                db.commit()
            else:
                print(f"[PUSH ERRO] Falha ao notificar {sub.endpoint[:40]}...: {e}")


def registrar_alerta(db, gato: Gato, tipo: str, mensagem: str, severidade: str = "ALTA"):
    """Cria um Alerta persistente (se não houver um em aberto do mesmo tipo
    dentro da janela de deduplicação) e dispara a notificação push aos tutores."""
    limite = datetime.utcnow() - timedelta(hours=JANELA_DEDUPLICACAO_HORAS)
    alerta_existente = (
        db.query(Alerta)
        .filter(
            Alerta.gato_id == gato.id,
            Alerta.tipo == tipo,
            Alerta.resolvido == False,  # noqa: E712
            Alerta.created_at >= limite,
        )
        .first()
    )
    if alerta_existente:
        # Já existe um alerta em aberto recente do mesmo tipo: evita spam de notificações.
        return alerta_existente

    novo_alerta = Alerta(
        gato_id=gato.id,
        tipo=tipo,
        severidade=severidade,
        mensagem=mensagem,
    )
    db.add(novo_alerta)
    db.commit()
    db.refresh(novo_alerta)

    print(f"[ALERTA {tipo}] 🚨 {mensagem}")
    _enviar_push_para_todos(
        db,
        titulo=f"🐱 SmartCat — {gato.nome}",
        corpo=mensagem,
        dados={"tipo": tipo, "gato_id": gato.id, "alerta_id": novo_alerta.id},
    )
    return novo_alerta


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
                gato_tag=tag_recebida,
                duracao_visita_s=duracao,
                alerta_retencao=gerar_alerta
            )
            db.add(evento)
            db.flush()  # garante que o evento tenha ID antes de possivelmente gerar o alerta

            if gerar_alerta and gato:
                registrar_alerta(
                    db,
                    gato,
                    tipo="RETENCAO_CAIXA",
                    mensagem=(
                        f"{gato.nome} permaneceu {duracao}s na caixa de areia "
                        f"(limite configurado: {limite_caixa}s). Pode indicar estresse, "
                        f"constipação ou infecção urinária."
                    ),
                    severidade="ALTA",
                )
            elif gerar_alerta:
                print(f"[ALERTA RETENÇÃO] 🚨 Tag desconhecida permaneceu {duracao}s na caixa (Limite: {limite_caixa}s)!")
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
            horas_sem_comer = (
                round((datetime.utcnow() - ultima_refeicao.created_at).total_seconds() / 3600, 1)
                if ultima_refeicao
                else None
            )
            descricao_tempo = (
                f"há mais de {horas_sem_comer}h" if horas_sem_comer is not None
                else "desde que foi cadastrado (nenhuma refeição registrada)"
            )
            registrar_alerta(
                db,
                gato,
                tipo="JEJUM",
                mensagem=(
                    f"{gato.nome} não come {descricao_tempo} "
                    f"(limite configurado: {gato.limite_jejum_horas}h). "
                    f"Jejum prolongado pode ser sinal de estresse, dor ou doença."
                ),
                severidade="ALTA",
            )
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