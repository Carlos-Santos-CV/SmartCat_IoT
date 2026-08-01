import json
import os

from dotenv import load_dotenv
from pywebpush import WebPushException, webpush

from app.database import PushSubscription

load_dotenv()

# --- Configuração de Web Push (VAPID) ---
# Gere seu par de chaves com o script scripts/generate_vapid_keys.py
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "mailto:contato@smartcat.local")


def enviar_push_para_todos(db, titulo: str, corpo: str, dados: dict | None = None):
    """Envia uma notificação Web Push para todos os tutores inscritos.
    Assinaturas inválidas/expiradas (HTTP 404/410) são removidas automaticamente.

    Retorna um resumo {"enviadas": int, "removidas": int, "configurado": bool}
    para quem quiser reportar o resultado (ex.: endpoint de teste)."""
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        print("[PUSH] Chaves VAPID não configuradas — pulando envio de notificação.")
        return {"enviadas": 0, "removidas": 0, "configurado": False}

    inscricoes = db.query(PushSubscription).all()
    payload = json.dumps({"title": titulo, "body": corpo, "data": dados or {}})

    enviadas = 0
    removidas = 0

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
            enviadas += 1
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                print(f"[PUSH] Assinatura expirada, removendo: {sub.endpoint[:40]}...")
                db.delete(sub)
                db.commit()
                removidas += 1
            else:
                print(f"[PUSH ERRO] Falha ao notificar {sub.endpoint[:40]}...: {e}")

    return {"enviadas": enviadas, "removidas": removidas, "configurado": True}
