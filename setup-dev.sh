# ==========================================
# SmartCat IoT - Setup Rápido (Desenvolvimento)
# ==========================================
# Script para configurar o ambiente de desenvolvimento automaticamente

set -e

echo "=========================================="
echo " SmartCat IoT - Setup de Desenvolvimento"
echo "=========================================="
echo ""

# 1. Verificar Python
echo "[1/5] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python 3 não encontrado. Instale Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✓ $PYTHON_VERSION"

# 2. Gerar chaves VAPID se não existirem
echo ""
echo "[2/5] Configurando chaves VAPID..."
if [ -f "backend/.env" ] && grep -q "VAPID_PRIVATE_KEY=" backend/.env && ! grep -q "<COLE_A_CHAVE" backend/.env; then
    echo "✓ Chaves VAPID já existem em backend/.env"
else
    echo "Gerando novas chaves VAPID..."
    python3 scripts/generate_vapid_keys.py > /tmp/vapid_keys.txt
    cat /tmp/vapid_keys.txt
    
    # Extrair chaves do output
    VAPID_PUBLIC=$(grep "VAPID_PUBLIC_KEY=" /tmp/vapid_keys.txt | cut -d'=' -f2)
    VAPID_PRIVATE=$(grep "VAPID_PRIVATE_KEY=" /tmp/vapid_keys.txt | cut -d'=' -f2)
    
    # Criar .env com as chaves
    cat > backend/.env << EOF
# ==========================================
# SmartCat IoT - Ambiente de Desenvolvimento
# ==========================================

# --- Banco de Dados ---
DATABASE_URL=sqlite:///./smartcat.db

# --- Broker MQTT ---
MQTT_BROKER=broker.hivemq.com
MQTT_PORT=1883

# --- Notificações Web Push (VAPID) ---
VAPID_PUBLIC_KEY=$VAPID_PUBLIC
VAPID_PRIVATE_KEY=$VAPID_PRIVATE
VAPID_CLAIM_EMAIL=mailto:dev@smartcat.local
EOF
    
    echo "✓ backend/.env criado com chaves VAPID"
    rm /tmp/vapid_keys.txt
fi

# 3. Verificar Docker
echo ""
echo "[3/5] Verificando Docker..."
if command -v docker &> /dev/null && docker ps &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✓ $DOCKER_VERSION"
else
    echo "⚠ Docker não disponível ou não está rodando"
    echo "  Opcional: você pode rodar o backend sem Docker"
fi

# 4. Verificar Docker Compose
echo ""
echo "[4/5] Verificando Docker Compose..."
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
    else
        COMPOSE_VERSION=$(docker compose version)
    fi
    echo "✓ $COMPOSE_VERSION"
else
    echo "⚠ Docker Compose não encontrado"
fi

# 5. Resumo
echo ""
echo "[5/5] Resumo da configuração"
echo "=========================================="
echo ""
echo "Arquivos criados:"
echo "  ✓ backend/.env (com chaves VAPID)"
echo "  ✓ backend/.env.dev (template)"
echo "  ✓ deploy/.env.prod (template para produção)"
echo "  ✓ .env.overview (visão geral)"
echo ""
echo "Próximos passos:"
echo ""
echo "OPÇÃO A - Com Docker (RECOMENDADO):"
echo "  cd /workspace"
echo "  docker compose up --build"
echo "  # Acessar: http://localhost:8000"
echo ""
echo "OPÇÃO B - Sem Docker (apenas backend):"
echo "  cd /workspace/backend"
echo "  pip install -r requirements.txt"
echo "  uvicorn app.main:app --reload"
echo "  # Terminal separado:"
echo "  python -m app.worker"
echo ""
echo "FIRMWARE (Wokwi Simulator):"
echo "  - Abra VSCode/VSCodium com extensão Wokwi"
echo "  - Pressione F1 → 'Wokwi: Start Simulator'"
echo ""
echo "=========================================="
echo "✓ Setup concluído!"
echo "=========================================="
