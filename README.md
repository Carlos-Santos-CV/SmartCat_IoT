# 🐱 SmartCat IoT

Sistema integrado de **Internet das Coisas (IoT)** para monitoramento remoto de gatos domésticos: identifica cada pet por **RFID**, mede o **consumo de ração** e o **tempo de uso da caixa de areia**, e envia **alertas de saúde** em tempo real ao tutor por meio de uma **Progressive Web App (PWA)**.

> Alterações sutis de rotina — comer menos, ficar mais tempo na caixa de areia, jejuar por muitas horas — costumam ser os primeiros sinais de problemas como estresse, diabetes ou infecções urinárias. O SmartCat automatiza essa observação, que normalmente depende só do olho do tutor.

---

## 📋 Sumário

- [Problema e Objetivos](#-problema-e-objetivos)
- [Arquitetura](#-arquitetura)
- [Funcionalidades](#-funcionalidades)
- [Stack Tecnológica](#-stack-tecnológica)
- [Estrutura do Repositório](#-estrutura-do-repositório)
- [Modelo de Dados](#-modelo-de-dados)
- [Fluxo de Eventos (MQTT)](#-fluxo-de-eventos-mqtt)
- [Regras de Alerta de Saúde](#-regras-de-alerta-de-saúde)
- [API REST](#-api-rest)
- [Notificações Web Push](#-notificações-web-push)
- [Instalação em Dispositivos Móveis](#-instalação-em-dispositivos-móveis)
- [Como Executar](#-como-executar)
  - [Ambiente de Desenvolvimento (Local)](#-ambiente-de-desenvolvimento-local)
  - [Ambiente de Deploy (Produção / VM)](#-ambiente-de-deploy-produção--vm)
  - [Execução Manual (Alternativa)](#-execução-manual-alternativa-sem-docker)
  - [Firmware (ESP32 / Wokwi)](#firmware-esp32--wokwi)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Portabilidade e Requisitos de Infraestrutura](#-portabilidade-e-requisitos-de-infraestrutura)
- [Roadmap](#-roadmap)
- [Licença](#-licença)

---

## 🎯 Problema e Objetivos

Tutores de gatos têm dificuldade em acompanhar com precisão a rotina de seus pets — frequência de alimentação, gramas exatas de ração consumidas e uso da caixa de areia — especialmente em lares com múltiplos animais, onde não dá para saber *quem* comeu ou usou a caixa. O SmartCat resolve isso com sensoriamento automatizado e individualizado.

**Objetivo geral:** registrar de forma automatizada e individual o comportamento alimentar e de higiene de cada gato, disponibilizando esses dados ao tutor em tempo real.

**Objetivos específicos:**

| Objetivo | Como o sistema atende |
|---|---|
| Identificação individual | Leitura de tag RFID a cada aproximação de uma estação |
| Coleta e telemetria | Estações publicam eventos via **MQTT** (protocolo leve, ideal para IoT) |
| Acompanhamento remoto | PWA para cadastrar pets/estações e visualizar histórico e métricas |
| Alertas preventivos | Parâmetros configuráveis por gato (peso meta, limite de jejum, limite de permanência na caixa) geram alertas automáticos + push |

---

## 🏗️ Arquitetura

O sistema é dividido em três camadas fracamente acopladas, comunicando-se por MQTT (hardware → servidor) e HTTP/REST (servidor ↔ PWA).

```mermaid
flowchart TD
    subgraph HW["📡 Camada de Hardware (Estações IoT)"]
        RFID["Leitor RFID<br/>(MFRC522)"]
        SENS["Sensor de Peso<br/>(joystick / potenciômetro simula célula de carga)"]
        ESP["ESP32-S3"]
        RFID --> ESP
        SENS --> ESP
    end

    subgraph MSG["📨 Infraestrutura de Mensageria"]
        BROKER["Broker MQTT<br/>(Mosquitto / HiveMQ)"]
    end

    subgraph SRV["🖥️ Servidor Central"]
        WORKER["Worker MQTT<br/>(paho-mqtt + APScheduler)"]
        API["API REST<br/>(FastAPI)"]
        DB[("Banco de Dados<br/>PostgreSQL / SQLite")]
        PUSH["Serviço Web Push<br/>(VAPID)"]
        WORKER --> DB
        API --> DB
        WORKER --> PUSH
    end

    subgraph PWA["📱 Interface do Tutor (PWA)"]
        UI["Dashboard Web<br/>(HTML/CSS/JS + Service Worker)"]
    end

    %% Conexões verticais
    ESP -- "publish smartcat/estacao_comida/telemetria<br/>publish smartcat/caixa_areia/telemetria" --> BROKER
    BROKER -- "subscribe smartcat/+/telemetria" --> WORKER
    UI -- "HTTP/REST (fetch)" --> API
    PUSH -. "Web Push (alertas)" .-> UI
```

**As três camadas do projeto:**

1. **Hardware e Sensoriamento (Estações IoT)** — dispositivos ESP32 posicionados no pote de comida e na caixa de areia, responsáveis por ler a tag RFID do pet e medir as variáveis físicas (peso consumido / tempo de permanência).
2. **Infraestrutura e Mensageria (Servidor Central)** — recebe os eventos via broker MQTT, persiste em banco relacional e aplica as regras de negócio (deduplicação de alertas, verificação de jejum, notificações).
3. **Aplicação e Interface (PWA)** — dashboard responsivo para o tutor cadastrar pets e estações, acompanhar o feed de eventos em tempo real e reagir a alertas de saúde, com suporte a notificações push mesmo com o app fechado.

---

## ✨ Funcionalidades

- 🐾 **CRUD de pets** — cadastro de gatos com tag RFID, nome, data de nascimento, peso meta, limite de jejum (h) e limite de permanência na caixa (s)
- 📶 **CRUD de estações** — vincula estações físicas (identificadas por MAC address) como `COMIDA` ou `CAIXA`
- 🍽️ **Registro automático de refeições** — consumo em gramas, por gato e por estação
- 🧹 **Registro automático de uso da caixa de areia** — duração da visita, com sinalização de retenção excessiva
- 📰 **Feed unificado de eventos** — refeições e visitas à caixa, mais recentes primeiro, com nomes resolvidos
- 🚨 **Alertas de saúde automáticos**, com deduplicação (evita spam):
  - Jejum prolongado (verificação periódica a cada 15 min)
  - Retenção excessiva na caixa de areia
- 🔔 **Notificações Web Push** (protocolo VAPID) — o tutor recebe o alerta mesmo com o navegador fechado
- 📲 **PWA instalável e com suporte offline** — manifest + Service Worker (com cache de assets estáticos), ícones dedicados para Android e iOS, e botão de instalação nativo em navegadores compatíveis (ver [Instalação em Dispositivos Móveis](#-instalação-em-dispositivos-móveis))
- 🔁 **Identificação sem leitor dedicado na caixa** — o firmware reaproveita a última tag lida no pote de comida dentro de uma janela de 10s, simulando a identificação do gato na caixa de areia com um único leitor RFID

---

## 🧰 Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| **Firmware** | C++ (Arduino framework), PlatformIO, ESP32-S3, simulação via **Wokwi** |
| **Bibliotecas do firmware** | `ArduinoJson`, `PubSubClient` (MQTT), `MFRC522` (RFID) |
| **Backend** | Python 3.10, **FastAPI**, Uvicorn, SQLAlchemy ORM |
| **Mensageria** | MQTT — `paho-mqtt` (worker) / **Eclipse Mosquitto** ou `broker.hivemq.com` (broker público) |
| **Agendamento** | APScheduler (varredura periódica de jejum) |
| **Banco de dados** | PostgreSQL 15 (produção/Docker) ou SQLite (fallback local) |
| **Notificações** | Web Push API + VAPID (`pywebpush`, `cryptography`) |
| **Frontend (PWA)** | HTML5, CSS3, JavaScript (Vanilla), Service Worker, Web App Manifest |
| **Infraestrutura** | Docker & Docker Compose |
| **Deploy alternativo** | `passenger_wsgi.py` (suporte a hospedagem compatível com Passenger/cPanel) |

---

## 📁 Estrutura do Repositório

```
SmartCat_IoT/
├── backend/
│   ├── app/
│   │   ├── main.py            # API REST (FastAPI) — rotas de gatos, estações, alertas, push
│   │   ├── worker.py          # Worker MQTT — ingestão de telemetria + regras de alerta
│   │   ├── push_service.py    # Lógica compartilhada de envio de Web Push (VAPID)
│   │   ├── database.py        # Modelos SQLAlchemy (ORM) e conexão com o banco
│   │   ├── static/
│   │   │   ├── css/             # style.css
│   │   │   ├── js/              # app.js, push.js
│   │   │   ├── icons/           # icon-192.png, icon-512.png, apple-touch-icon.png
│   │   │   └── manifest.json    # Web App Manifest (PWA)
│   │   └── templates/
│   │       └── index.html      # Dashboard servido na rota "/"
│   ├── passenger_wsgi.py       # Entry point para hospedagem via Passenger/cPanel
│   ├── requirements.txt
│   └── Dockerfile
├── deploy/
│   ├── Caddyfile              # Configuração do Caddy (reverse proxy)
│   └── mosquitto.conf         # Configuração do broker MQTT (Mosquitto)
├── firmware/
│   ├── src/main.cpp           # Firmware ESP32-S3 (leitura RFID + peso + envio MQTT)
│   ├── platformio.ini         # Dependências e board de destino
│   ├── platformio.local.example  # Exemplo de configurações locais do PlatformIO
│   ├── diagram.json           # Esquema de ligação para simulação Wokwi
│   ├── wiring-diagram.png     # Diagrama de conexões físicas
│   └── wokwi.toml             # Configuração da simulação Wokwi
├── scripts/
│   └── generate_vapid_keys.py # Gera par de chaves VAPID para o Web Push
├── docker-compose.yml         # Orquestra db (Postgres) + broker (Mosquitto) + web (API)
├── docker-compose.override.yml  # Overrides para desenvolvimento local
├── docker-compose.prod.yml    # Configuração para produção
├── setup-dev.sh               # Script de setup do ambiente de desenvolvimento
└── LICENSE                    # Apache License 2.0
```

---

## 🗄️ Modelo de Dados

```mermaid
erDiagram
    GATO ||--o{ REFEICAO : registra
    GATO ||--o{ USO_CAIXA : registra
    GATO ||--o{ ALERTA : gera
    ESTACAO ||--o{ REFEICAO : origina
    ESTACAO ||--o{ USO_CAIXA : origina

    GATO {
        int id PK
        string tag_rfid UK
        string nome
        date data_nascimento
        float peso_meta_g
        int limite_jejum_horas "padrão 24h"
        int limite_caixa_segundos "padrão 300s"
        datetime created_at
    }

    REFEICAO {
        int id PK
        int gato_id FK
        int estacao_id FK "nullable — estação ainda não cadastrada"
        string estacao_mac "MAC bruto do MQTT, sempre preservado"
        string gato_tag
        float consumo_g
        datetime created_at
    }

    USO_CAIXA {
        int id PK
        int gato_id FK
        int estacao_id FK "nullable — estação ainda não cadastrada"
        string estacao_mac "MAC bruto do MQTT, sempre preservado"
        string gato_tag
        int duracao_visita_s
        bool alerta_retencao
        datetime created_at
    }

    ESTACAO {
        int id PK
        string mac_address UK
        string nome
        string tipo "COMIDA ou CAIXA"
        datetime created_at
    }

    ALERTA {
        int id PK
        int gato_id FK
        string tipo "JEJUM, RETENCAO_CAIXA, PESO"
        string severidade "ALTA, MEDIA, BAIXA"
        string mensagem
        bool resolvido
        datetime resolvido_em
        datetime created_at
    }

    PUSH_SUBSCRIPTION {
        int id PK
        string endpoint UK
        string p256dh
        string auth
        datetime created_at
    }
```

> `estacao_id` é uma chave estrangeira de verdade para `ESTACAO.id`, mas fica `nullable`: como os eventos chegam via MQTT identificando a estação só pelo MAC address, é possível que a estação ainda não tenha sido cadastrada no sistema no momento do evento. Por isso existe também o campo `estacao_mac`, que sempre guarda o MAC bruto recebido — nada se perde mesmo quando `estacao_id` fica nulo, e o dado fica disponível para uma eventual reconciliação posterior (ex.: uma refeição registrada antes do tutor cadastrar a estação).

---

## 📡 Fluxo de Eventos (MQTT)

Cada estação publica em um tópico próprio; o worker do backend assina o wildcard `smartcat/+/telemetria`.

| Tópico | Publicado por | Payload (JSON) |
|---|---|---|
| `smartcat/estacao_comida/telemetria` | Estação de comida | `{ "estacao_id": "ESP32_...", "gato_tag": "A1B2C3D4", "consumo_g": 42.5 }` |
| `smartcat/caixa_areia/telemetria` | Estação da caixa de areia | `{ "estacao_id": "ESP32_...", "gato_tag": "A1B2C3D4", "duracao_visita_s": 87 }` |

### Sequência: refeição registrada

```mermaid
sequenceDiagram
    participant Gato as 🐱 Gato
    participant HW as Estação (ESP32)
    participant MQTT as Broker MQTT
    participant Worker as Worker (backend)
    participant DB as Banco de Dados
    participant PWA as PWA (Tutor)

    Gato->>HW: Aproxima-se do pote (tag RFID)
    HW->>HW: Lê tag RFID + peso consumido
    HW->>MQTT: publish smartcat/estacao_comida/telemetria
    MQTT->>Worker: on_message()
    Worker->>DB: identifica gato pela tag + INSERT Refeicao
    PWA->>Worker: GET /api/eventos (polling)
    Worker->>DB: consulta últimos eventos
    DB-->>PWA: feed atualizado (refeição aparece)
```

### Sequência: uso da caixa de areia com alerta

```mermaid
sequenceDiagram
    participant HW as Estação (ESP32)
    participant MQTT as Broker MQTT
    participant Worker as Worker (backend)
    participant DB as Banco de Dados
    participant Push as Web Push
    participant PWA as PWA (Tutor)

    HW->>MQTT: publish duracao_visita_s (saída da caixa)
    MQTT->>Worker: on_message()
    Worker->>DB: INSERT UsoCaixa
    alt duracao_visita_s > limite_caixa_segundos do gato
        Worker->>DB: verifica alerta em aberto (janela de 2h)
        Worker->>DB: INSERT Alerta (tipo=RETENCAO_CAIXA)
        Worker->>Push: envia notificação a todos os tutores inscritos
        Push-->>PWA: notificação push (mesmo com app fechado)
    end
```

---

## 🚨 Regras de Alerta de Saúde

Implementadas em `backend/app/worker.py`:

| Tipo | Gatilho | Frequência de checagem |
|---|---|---|
| **JEJUM** | Nenhuma refeição registrada dentro de `limite_jejum_horas` (padrão 24h) | Varredura agendada a cada **15 minutos** (APScheduler) sobre todos os gatos cadastrados |
| **RETENCAO_CAIXA** | Duração da visita à caixa de areia excede `limite_caixa_segundos` (padrão 300s / 5 min) | Em tempo real, a cada evento MQTT recebido |

Ambos os tipos passam por **deduplicação**: se já existe um alerta do mesmo tipo em aberto (não resolvido) para aquele gato criado nas últimas **2 horas**, um novo alerta/nova notificação não é disparado — evitando spam ao tutor. Alertas podem ser marcados como resolvidos pelo tutor via `PUT /api/alertas/{id}/resolver`.

---

## 🔌 API REST

Base URL local: `http://localhost:8000`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Serve o dashboard PWA (`index.html`) |
| `GET` | `/api/gatos` | Lista todos os pets cadastrados |
| `POST` | `/api/gatos` | Cadastra um novo pet (tag RFID única) |
| `PUT` | `/api/gatos/{id}` | Atualiza dados de um pet |
| `DELETE` | `/api/gatos/{id}` | Remove um pet |
| `GET` | `/api/estacoes` | Lista estações cadastradas |
| `POST` | `/api/estacoes` | Cadastra uma estação (MAC address único) |
| `PUT` | `/api/estacoes/{id}` | Atualiza uma estação |
| `DELETE` | `/api/estacoes/{id}` | Remove uma estação |
| `GET` | `/api/refeicoes` | Últimas 50 refeições registradas |
| `GET` | `/api/caixa-areia` | Últimos 50 usos da caixa de areia |
| `GET` | `/api/eventos` | Feed unificado (refeições + caixa), últimos 50, mais recentes primeiro |
| `GET` | `/api/alertas?apenas_abertos=` | Lista alertas (opcionalmente só os não resolvidos) |
| `PUT` | `/api/alertas/{id}/resolver` | Marca um alerta como resolvido |
| `GET` | `/api/push/vapid-public-key` | Retorna a chave pública VAPID para o navegador se inscrever |
| `POST` | `/api/push/subscribe` | Registra a inscrição push do navegador do tutor |
| `POST` | `/api/push/unsubscribe` | Remove a inscrição push |
| `POST` | `/api/push/test` | Dispara uma notificação de teste para todos os inscritos (debug rápido) |

A documentação interativa (Swagger) fica disponível automaticamente em `/docs` graças ao FastAPI.

---

## 🔔 Notificações Web Push

O sistema usa o padrão **Web Push + VAPID**, permitindo alertas mesmo com o navegador fechado (via Service Worker):

1. Gere um par de chaves VAPID:
   ```bash
   python scripts/generate_vapid_keys.py
   ```
2. Copie a saída para `backend/.env` (e/ou `docker/.env`, se estiver usando Docker):
   ```
   VAPID_PUBLIC_KEY=...
   VAPID_PRIVATE_KEY=...
   VAPID_CLAIM_EMAIL=mailto:seuemail@dominio.com
   ```
3. No dashboard, o tutor clica em **"🔕 Ativar notificações"** — o navegador se inscreve via `PushManager` e a inscrição é enviada para `POST /api/push/subscribe`.
4. Quando o worker gera um alerta (`registrar_alerta`), ele envia a notificação para **todas** as inscrições salvas; assinaturas expiradas (HTTP 404/410) são removidas automaticamente.
5. Depois de ativar, aparece o botão **"🧪 Enviar teste"** — dispara `POST /api/push/test`, útil para validar a configuração VAPID e a inscrição do navegador sem precisar esperar um alerta real de saúde acontecer.

A lógica de envio (`enviar_push_para_todos`) fica centralizada em `backend/app/push_service.py`, reaproveitada tanto pelo `worker.py` (alertas automáticos) quanto pelo `main.py` (endpoint de teste).

---

## 📲 Instalação em Dispositivos Móveis

O SmartCat é um PWA instalável — funciona em tela cheia, como um app nativo, sem passar pela loja de aplicativos. O comportamento muda conforme a plataforma:

| Plataforma | Como instalar |
|---|---|
| **Android** (Chrome, Edge, Samsung Internet) | O navegador detecta automaticamente que o app é instalável e mostra um banner ou o botão **"⬇️ Instalar app"** no cabeçalho do próprio SmartCat |
| **Desktop** (Chrome/Edge no Windows, macOS, Linux) | Ícone de instalação (⊕) na barra de endereço, ou o mesmo botão **"⬇️ Instalar app"** |
| **iOS** (Safari) | Instalação manual: toque em **Compartilhar** (ícone de seta para cima) → **"Adicionar à Tela de Início"**. O Safari não dispara instalação automática nem exibe o botão do app — essa limitação é do próprio iOS |

**Pré-requisitos técnicos** (já implementados no projeto):

- `manifest.json` com ícones `192x192` e `512x512` (`purpose: "any maskable"`)
- Ícone dedicado `apple-touch-icon.png` (180x180, opaco, sem cantos arredondados — o iOS aplica o arredondamento sozinho)
- Service Worker (`sw.js`) registrado, com handler de `fetch` — os arquivos estáticos ficam em cache, então o app abre mesmo sem conexão (os dados dinâmicos da API continuam exigindo rede)
- **Servir a aplicação via HTTPS** — obrigatório para instalabilidade em produção (exceto em `localhost`, que é tratado como seguro para testes)

---

## 🚀 Como Executar

O SmartCat foi projetado para rodar em **dois ambientes principais**: Desenvolvimento (local) e Deploy (produção/VM). O sistema é **agnóstico à infraestrutura** — qualquer ambiente com Docker e/ou PlatformIO funciona.

---

### 🧑‍💻 Ambiente de Desenvolvimento (Local)

Ideal para testar, desenvolver e validar a lógica antes de ir para produção. Use o **simulador Wokwi** (sem hardware físico) ou o ESP32 conectado ao seu computador.

#### Pré-requisitos

- Docker & Docker Compose instalados
- Python 3.10+ (para scripts auxiliares)
- PlatformIO Core (opcional, se for compilar firmware fora do Wokwi)
- Extensão Wokwi no VS Code/VSCodium (opcional, para simulação)

#### Passo 1: Gerar Chaves VAPID (Notificações Push)

```bash
cd /workspace
python scripts/generate_vapid_keys.py
# Copie as chaves geradas
```

#### Passo 2: Configurar Variáveis de Ambiente

Crie o arquivo `backend/.env`:

```bash
cp backend/.env.example backend/.env
```

Edite `backend/.env` com as chaves VAPID geradas:

```ini
DATABASE_URL=sqlite:///./smartcat.db
MQTT_BROKER=broker.hivemq.com
MQTT_PORT=1883
VAPID_PUBLIC_KEY=<cole_aqui>
VAPID_PRIVATE_KEY=<cole_aqui>
VAPID_CLAIM_EMAIL=mailto:dev@smartcat.local
```

#### Passo 3: Subir Serviços com Docker Compose

Na raiz do projeto:

```bash
docker compose up --build
```

Serviços disponíveis:
- **Dashboard**: [http://localhost:8000](http://localhost:8000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Worker MQTT**: logs via `docker compose logs -f worker`

> 💡 O ambiente de desenvolvimento usa **SQLite** por padrão (sem necessidade de subir PostgreSQL) e conecta ao broker público `broker.hivemq.com` (não precisa subir Mosquitto local).

#### Passo 4: Rodar o Firmware (Simulado ou Físico)

**Opção A — Simulador Wokwi (Recomendado para Dev):**

1. Abra a pasta `firmware/` no VS Code com a extensão Wokwi instalada
2. Selecione o environment `dev` na barra inferior do PlatformIO
3. Pressione `F1` → "Wokwi: Start Simulator"
4. O simulador conecta automaticamente a `broker.hivemq.com`

**Opção B — Hardware Físico (ESP32 conectado via USB):**

```bash
cd firmware
pio run -e dev --target upload
pio device monitor -e dev -b 115200
```

---

### ☁️ Ambiente de Deploy (Produção / VM)

Projeto para rodar em servidores cloud (ex: Google Cloud VM, AWS EC2, Azure VM) ou qualquer máquina com Docker. O exemplo abaixo usa **Google Cloud Platform (GCP)**, mas o processo é idêntico em outros provedores.

#### Pré-requisitos

- VM Linux (Ubuntu 22.04+, Debian 11+) com Docker e Docker Compose instalados
- Acesso SSH à VM
- Firewall liberado nas portas:
  - **80** (HTTP) e **443** (HTTPS) para acesso web
  - **1883** (MQTT) para comunicação com ESP32
- ESP32-S3 físico com firmware compilado para produção

#### Passo 1: Clonar o Repositório na VM

```bash
git clone https://github.com/seu-usuario/SmartCat_IoT.git ~/smartcat
cd ~/smartcat
```

#### Passo 2: Configurar Variáveis de Ambiente de Produção

Crie o arquivo `.env` na **raiz do projeto** (necessário para o Docker Compose ler):

```bash
cat > .env << 'EOF'
# Banco de Dados PostgreSQL
POSTGRES_USER=smartcat
POSTGRES_PASSWORD=senha_forte_aleatoria
POSTGRES_DB=smartcat_db

# URL de conexão usada pela aplicação
DATABASE_URL=postgresql://smartcat:senha_forte_aleatoria@db:5432/smartcat_db

# Broker MQTT (serviço local na rede Docker)
MQTT_BROKER=broker
MQTT_PORT=1883

# Web Push (USE AS MESMAS CHAVES DO DESENVOLVIMENTO)
VAPID_PUBLIC_KEY=<mesma_chave_do_dev>
VAPID_PRIVATE_KEY=<mesma_chave_do_dev>
VAPID_CLAIM_EMAIL=mailto:admin@smartcat.cloud
EOF
```

> ⚠️ **Importante:** Use as **mesmas chaves VAPID** do ambiente de desenvolvimento para não invalidar as notificações push já registradas nos navegadores dos usuários.

#### Passo 3: Configurar Firewall da VM

**Google Cloud Platform (GCP):**

```bash
# Liberar HTTP/HTTPS
gcloud compute firewall-rules create allow-http \
  --allow tcp:80,tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --description "Acesso Web ao SmartCat"

# Liberar MQTT para ESP32
gcloud compute firewall-rules create allow-mqtt \
  --allow tcp:1883 \
  --source-ranges 0.0.0.0/0 \
  --description "Acesso MQTT para ESP32"
```

**Outros provedores:** Libere as portas 80, 443 e 1883 no painel de segurança/firewall.

#### Passo 4: Subir Serviços em Produção

Use os arquivos de compose de produção (inclui Caddy para HTTPS automático):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Verifique o status:

```bash
docker compose ps
# Deve mostrar: web, worker, db, broker, caddy (todos saudáveis)
```

Acesse pelo IP da VM ou domínio configurado:
- HTTP: `http://<IP_DA_VM>`
- HTTPS: `https://seu-dominio.com` (após apontar DNS e configurar Caddyfile)

#### Passo 5: Compilar e Gravar Firmware no ESP32 Físico

O firmware de produção deve apontar para o **IP público da VM** (ou domínio).

1. **Descubra o IP externo da VM:**
   ```bash
   curl ifconfig.me
   # Anote o IP, ex: 34.95.195.6
   ```

2. **Crie o arquivo de configuração local (não versionado):**
   
   Em `firmware/platformio.local.ini`:
   ```ini
   [env:prod]
   extends = env:esp32-s3-devkitc-1
   build_flags = 
       ${env:esp32-s3-devkitc-1.build_flags}
       -D WIFI_SSID=\"NOME_DA_REDE_WIFI\"
       -D WIFI_PASSWORD=\"SENHA_DA_REDE\"
       -D MQTT_BROKER=\"34.95.195.6\"
       -D MQTT_PORT=1883
   ```

3. **Compile e faça upload no ESP32:**
   ```bash
   cd firmware
   pio run -e prod --target upload
   pio device monitor -e prod -b 115200
   ```

4. **Verifique a conexão no Serial Monitor:**
   ```
   [Wi-Fi] Conectado! Dispositivo ID: ESP32_...
   [MQTT] Tentando conectar ao Broker...
   [MQTT] Conectado! (ao IP da VM)
   ```

#### Passo 6: Teste Final

1. Acesse o dashboard no navegador
2. Cadastre um pet, uma estação e uma tag RFID
3. Aproxime a tag do leitor RFID no ESP32 físico
4. Verifique o evento aparecendo no dashboard em tempo real

---

### 🔧 Execução Manual (Alternativa sem Docker)

Caso prefira rodar os serviços manualmente (útil para debug avançado):

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # ajuste DATABASE_URL para sqlite:///./smartcat.db se não usar Postgres

# Terminal 1 — API
uvicorn app.main:app --reload

# Terminal 2 — Worker MQTT (ingestão de telemetria + alertas agendados)
python -m app.worker
```

Sem `DATABASE_URL` definido, o backend cai automaticamente para SQLite local (`smartcat.db`).

### Firmware (ESP32 / Wokwi)

O firmware foi desenvolvido para **ESP32-S3**, com leitor RFID **MFRC522** e um joystick analógico simulando a célula de carga (peso) e o botão de presença na caixa de areia.

![Esquema de ligação: ESP32-S3, leitor RFID MFRC522 e joystick analógico](./firmware/wiring-diagram.png)

> 📄 Walkthrough completo do código linha a linha em [`firmware/README.md`](./firmware/README.md).

**Simulação (sem hardware físico) via [Wokwi](https://wokwi.com/):**
1. Abra a pasta `firmware/` no VS Code com a extensão Wokwi instalada, ou importe `diagram.json` diretamente no simulador web.
2. Compile com PlatformIO (`pio run`) e inicie a simulação — ela usa o `diagram.json` para as ligações e `wokwi.toml` para apontar o binário.

**Hardware físico:**
1. Instale o [PlatformIO](https://platformio.org/) (extensão do VS Code ou CLI).
2. Ajuste `NetworkConfig::SSID_WIFI` / `SENHA_WIFI` em `firmware/src/main.cpp` para sua rede.
3. Conecte o ESP32-S3 e rode:
   ```bash
   cd firmware
   pio run --target upload
   pio device monitor
   ```

**Ligações principais** (tabela completa com fios/cores em [`firmware/README.md`](./firmware/README.md)):

| Componente | Pino ESP32-S3 |
|---|---|
| MFRC522 — SDA/SS | GPIO 5 |
| MFRC522 — RST | GPIO 4 |
| MFRC522 — SCK / MOSI / MISO | GPIO 12 / 11 / 13 |
| Joystick — eixo vertical (peso) | GPIO 1 |
| Joystick — botão (entrada/saída da caixa) | GPIO 2 |

> No hardware simulado só existe **um leitor RFID**, compartilhado entre as duas estações. Por isso o firmware guarda a última tag lida no pote de comida por até 10 segundos (`JANELA_IDENTIFICACAO_MS`) e a reutiliza para identificar o gato que entra na caixa de areia logo em seguida.

---

## ⚙️ Variáveis de Ambiente

### Desenvolvimento (`backend/.env`)

| Variável | Descrição | Valor Típico (Dev) |
|---|---|---|
| `DATABASE_URL` | String de conexão do banco | `sqlite:///./smartcat.db` |
| `MQTT_BROKER` | Endereço do broker MQTT | `broker.hivemq.com` |
| `MQTT_PORT` | Porta do broker MQTT | `1883` |
| `VAPID_PUBLIC_KEY` | Chave pública Web Push | *(gerar com script)* |
| `VAPID_PRIVATE_KEY` | Chave privada Web Push | *(gerar com script)* |
| `VAPID_CLAIM_EMAIL` | E-mail de contato VAPID | `mailto:dev@smartcat.local` |

### Deploy / Produção (`.env` na raiz)

Além das variáveis acima (com valores ajustados), o ambiente de produção requer:

| Variável | Descrição | Valor Típico (Prod) |
|---|---|---|
| `POSTGRES_USER` | Usuário do PostgreSQL | `smartcat` |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL | *(senha forte)* |
| `POSTGRES_DB` | Nome do banco PostgreSQL | `smartcat_db` |
| `DATABASE_URL` | Connection string (aponta p/ serviço Docker) | `postgresql://smartcat:senha@db:5432/smartcat_db` |
| `MQTT_BROKER` | Broker na rede Docker interna | `broker` |

> 💡 **Dica:** As chaves VAPID devem ser **as mesmas** em desenvolvimento e produção para que as notificações push continuem funcionando após o deploy.

---

## 🌍 Portabilidade e Requisitos de Infraestrutura

O SmartCat foi projetado para ser **agnóstico à infraestrutura**:

| Requisito | Mínimo | Recomendado |
|---|---|---|
| **CPU** | 1 vCPU | 2 vCPU |
| **RAM** | 1 GB | 2 GB |
| **Armazenamento** | 5 GB | 10 GB SSD |
| **Sistema Operacional** | Linux com Docker | Ubuntu 22.04 LTS / Debian 11+ |
| **Conectividade** | Internet (para broker público) | IP estático + domínio (para HTTPS) |

**Onde pode rodar:**
- ✅ Google Cloud Platform (GCP) — VM Compute Engine
- ✅ Amazon Web Services (AWS) — EC2
- ✅ Microsoft Azure — Virtual Machines
- ✅ Oracle Cloud — Free Tier
- ✅ Servidor físico local (home lab)
- ✅ Qualquer VPS com Docker (Hetzner, DigitalOcean, Linode, etc.)

**O firmware ESP32 pode se conectar de:**
- Qualquer rede Wi-Fi com acesso à internet
- A partir de qualquer localização geográfica, desde que consiga reachar o IP/domínio do servidor

---

## 🗺️ Roadmap

Ideias de evolução natural do projeto (não implementadas no código atual):

- Alerta de desvio de peso (`tipo="PESO"` já modelado em `Alerta`, mas ainda sem regra de disparo)
- Leitor RFID dedicado na caixa de areia (eliminando a heurística de janela de identificação)
- Autenticação/multiusuário na PWA (hoje qualquer inscrição push recebe todos os alertas)
- Gráficos históricos de consumo e frequência por gato

---

## 📄 Licença

Distribuído sob a **Apache License 2.0** — veja o arquivo [LICENSE](./LICENSE) para o texto completo.