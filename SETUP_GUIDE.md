# 🚀 SmartCat IoT - Guia de Configuração Rápida

## ✅ O Que Foi Feito

### 1. Script Gerador de Chaves VAPID
- **Arquivo**: `scripts/generate_vapid_keys.py`
- **Uso**: `python scripts/generate_vapid_keys.py`
- Gera chaves criptográficas para Web Push Notifications
- As MESMAS chaves devem ser usadas em dev e prod

### 2. Arquivos de Configuração (.env)
| Arquivo | Finalidade |
|---------|-----------|
| `backend/.env` | **PRONTO PARA USO** - já vem com chaves VAPID geradas. Usado em dev e prod (via `env_file:` no docker-compose.yml) |
| `backend/.env.dev` | Template para desenvolvimento |
| `.env` (raiz do projeto) | Só o que o Compose precisa pra subir o Postgres (`POSTGRES_USER/PASSWORD/DB`). Lido automaticamente, sem `--env-file` |
| `.env.example` (raiz do projeto) | Template do arquivo acima |
| `.env.overview` | Visão geral das diferenças entre ambientes |

### 3. Firmware sem Hardcoded
- **`platformio.ini`**: Agora tem `[env:dev]` e `[env:prod]`
- **`main.cpp`**: Usa macros `WIFI_SSID`, `MQTT_BROKER` definidas via build_flags
- **`platformio.local.example`**: Template para credenciais reais (não versionar)
- **`.gitignore`**: Atualizado para ignorar `platformio.local.ini`

### 4. Script de Setup Automático
- **Arquivo**: `setup-dev.sh`
- **Uso**: `./setup-dev.sh`
- Verifica dependências, gera chaves, cria .env automaticamente

---

## 🔧 Desenvolvimento (MacBook)

### Opção A: Setup Automático (RECOMENDADO)

```bash
cd /workspace
./setup-dev.sh
```

### Opção B: Manual Passo a Passo

#### 1. Gerar chaves VAPID (se não usou o script)
```bash
python3 scripts/generate_vapid_keys.py
# Copie as chaves para backend/.env
```

#### 2. Backend com Docker
```bash
cd /workspace
docker compose up --build
# Acessar: http://localhost:8000
```

#### 3. Backend sem Docker
```bash
cd /workspace/backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# Terminal separado:
python -m app.worker
```

#### 4. Firmware (Wokwi Simulator)
1. Abra VSCode/VSCodium
2. Instale extensão "Wokwi Simulator for ESP32"
3. Abra a pasta `/workspace/firmware`
4. Pressione `F1` → "Wokwi: Start Simulator"
5. **Importante**: Selecione environment `dev` na barra inferior do VSCode

---

## ☁️ Deploy (GCP VM)

### 1. Clonar repositório
```bash
git clone <seu-repo> smartcat
cd smartcat
```

### 2. Configurar ambiente
```bash
# Credenciais do Postgres (o Compose lê ".env" na raiz sozinho, sem flag)
cp .env.example .env
nano .env
chmod 600 .env

# Config da aplicação (VAPID, MQTT, etc.) — as MESMAS chaves VAPID do desenvolvimento
cp backend/.env.example backend/.env
nano backend/.env
```

### 3. Subir serviços
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
(sem `--env-file`: o Compose já carrega `./.env` da raiz automaticamente)

### 4. Firmware no ESP32 Físico

#### Opção A: Usando platformio.local.ini (RECOMENDADO)
```bash
cd /workspace/firmware
cp platformio.local.example platformio.local.ini
nano platformio.local.ini  # Edite com suas credenciais WiFi reais
pio run -e prod --target upload
```

#### Opção B: Editando platformio.ini diretamente
```bash
cd /workspace/firmware
nano platformio.ini  # Edite [env:prod] com suas credenciais
pio run -e prod --target upload
```

---

## 📊 Comparação: Dev vs Deploy

| Componente | Desenvolvimento | Deploy (GCP) |
|------------|----------------|--------------|
| **Database** | SQLite (`smartcat.db`) | PostgreSQL Docker |
| **MQTT Broker** | `broker.hivemq.com` (público) | Mosquitto Docker (interno) |
| **VAPID Keys** | Geradas uma vez | **MESMAS chaves** (copiar) |
| **HTTPS** | Não (localhost) | Sim (Caddy automático) |
| **Firmware** | Wokwi Simulator | ESP32 físico |
| **Environment** | `[env:dev]` | `[env:prod]` |

---

## 🎯 Pontos de Atenção

### ✅ Eliminação de Hardcoded
- [x] WiFi SSID/Password → via `build_flags` do PlatformIO
- [x] MQTT Broker → via `build_flags` do PlatformIO
- [x] VAPID Keys → via `.env` (backend)
- [x] Database URL → via `.env` (backend)

### ⚠️ Ainda Requer Atenção
1. **Caddyfile**: Domínio `seu-dominio.com` precisa ser substituído
2. **Limites de saúde**: Podem virar variáveis de ambiente se quiser ajustar sem rebuild

---

## 🐛 Troubleshooting

### Backend não inicia
```bash
# Verificar se .env existe
ls -la backend/.env

# Verificar formato das chaves VAPID
grep VAPID backend/.env
```

### Firmware não conecta no WiFi
```bash
# Verificar se está usando environment correto
pio run -e dev  # ou -e prod

# Limpar build anterior
pio run --target clean
```

### Web Push não funciona
1. Verifique se as chaves VAPID são as MESMAS em dev e prod
2. O navegador deve estar acessando via HTTPS (ou localhost)
3. Service worker precisa ser registrado novamente após mudar chaves

---

## 📚 Próximos Passos Sugeridos

1. **Testar em desenvolvimento**:
   ```bash
   ./setup-dev.sh
   docker compose up
   ```

2. **Validar firmware no Wokwi**:
   - Abra firmware no VSCode
   - Inicie simulador Wokwi
   - Veja eventos chegando em `http://localhost:8000`

3. **Preparar deploy**:
   - Copie as MESMAS chaves VAPID de `backend/.env` para o `backend/.env` da VM
   - Configure `.env` na raiz da VM com uma senha forte de Postgres (veja `.env.example`)
   - Configure `platformio.local.ini` com WiFi da rede de demonstração

---

**Status**: ✅ Projeto pronto para rodar em desenvolvimento e deploy!
