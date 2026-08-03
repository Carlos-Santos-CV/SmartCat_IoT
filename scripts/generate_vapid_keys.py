#!/usr/bin/env python3
"""
Gera par de chaves VAPID para Web Push Notifications.

Este script deve ser executado uma vez para gerar as chaves que serão
usadas tanto em desenvolvimento quanto em produção.

Uso:
    python scripts/generate_vapid_keys.py

Saída:
    Imprime as chaves no formato pronto para copiar para o .env
"""

import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def urlsafe_base64_encode(data: bytes) -> str:
    """Codifica bytes para base64 URL-safe (padrão VAPID)."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def main():
    print("=" * 70)
    print(" SmartCat IoT - Gerador de Chaves VAPID para Web Push")
    print("=" * 70)
    print()
    
    # Gera par de chaves elliptic curve (P-256)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    # Serializa chaves no formato VAPID (raw bytes, base64 URL-safe)
    private_bytes = private_key.private_numbers().private_value.to_bytes(32, byteorder='big')

    # Formato raw P-256: 0x04 + X (32 bytes) + Y (32 bytes) = 65 bytes total
    public_point = b'\x04' + \
                   public_key.public_numbers().x.to_bytes(32, byteorder='big') + \
                   public_key.public_numbers().y.to_bytes(32, byteorder='big')

    vapid_private_key = urlsafe_base64_encode(private_bytes)
    vapid_public_key = urlsafe_base64_encode(public_point)
    
    print("Chaves geradas com sucesso!")
    print()
    print("=" * 70)
    print("COPIE ESTES VALORES PARA SEU ARQUIVO .env:")
    print("=" * 70)
    print()
    print(f"VAPID_PUBLIC_KEY={vapid_public_key}")
    print(f"VAPID_PRIVATE_KEY={vapid_private_key}")
    print(f"VAPID_CLAIM_EMAIL=mailto:dev@smartcat.local")
    print()
    print("=" * 70)
    print("NOTAS IMPORTANTES:")
    print("=" * 70)
    print("1. Estas chaves devem ser as MESMAS em dev e prod")
    print("2. Guarde a PRIVATE_KEY com segurança (não compartilhe)")
    print("3. A PUBLIC_KEY vai para o frontend (service worker)")
    print("4. O email em VAPID_CLAIM_EMAIL é apenas identificador")
    print("=" * 70)


if __name__ == "__main__":
    main()
