"""
Gera um par de chaves VAPID (curva P-256) para autenticar as notificações
Web Push do SmartCat.

Uso:
    python scripts/generate_vapid_keys.py

Copie a saída para o seu arquivo backend/.env:
    VAPID_PUBLIC_KEY=...
    VAPID_PRIVATE_KEY=...
    VAPID_CLAIM_EMAIL=mailto:seuemail@dominio.com

A chave pública também precisa ser configurada no worker/servidor (mesmo .env),
pois é ela que o navegador usa para criar a inscrição no PushManager.
"""
import base64

from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def gerar_chaves_vapid():
    chave_privada = ec.generate_private_key(ec.SECP256R1())
    numeros_privados = chave_privada.private_numbers()
    numeros_publicos = numeros_privados.public_numbers

    # Chave privada: inteiro 'd' em 32 bytes, codificado em base64url (sem padding)
    d_bytes = numeros_privados.private_value.to_bytes(32, "big")
    private_key_b64 = _b64url(d_bytes)

    # Chave pública: ponto não comprimido (0x04 || X || Y), 65 bytes, base64url
    x_bytes = numeros_publicos.x.to_bytes(32, "big")
    y_bytes = numeros_publicos.y.to_bytes(32, "big")
    public_point = b"\x04" + x_bytes + y_bytes
    public_key_b64 = _b64url(public_point)

    return public_key_b64, private_key_b64


if __name__ == "__main__":
    public_key, private_key = gerar_chaves_vapid()
    print("Par de chaves VAPID gerado com sucesso!\n")
    print("Adicione ao seu arquivo backend/.env:\n")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print("VAPID_CLAIM_EMAIL=mailto:seuemail@dominio.com")
