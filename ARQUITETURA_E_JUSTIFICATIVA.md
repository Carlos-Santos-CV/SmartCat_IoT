# 📘 Justificativa Técnica da Arquitetura IoT - Projeto SmartCat

## 1. Visão Geral da Arquitetura

O sistema **SmartCat** foi projetado seguindo os princípios de **Edge Computing** com processamento na nuvem (Cloud-Edge Hybrid). A arquitetura divide-se em três camadas distintas:

1.  **Camada de Percepção (Edge):** Microcontrolador ESP32-S3 + Sensores (RFID + Célula de Carga).
2.  **Camada de Transporte:** Protocolo MQTT sobre TCP/IP via Wi-Fi.
3.  **Camada de Aplicação/Processamento (Cloud):** Backend Python (FastAPI), Banco de Dados e Motor de Regras.

Esta seção detalha a escolha de cada componente hardware e protocolo, fundamentada em critérios de **custo-benefício**, **precisão**, **consumo energético** e **escalabilidade**.

---

## 2. Escolha do Microcontrolador: ESP32-S3

Para a unidade de borda (o dispositivo físico instalado na casa do tutor), optou-se pelo **ESP32-S3** da Espressif Systems, em detrimento de alternativas como Arduino Uno (ATmega328P), ESP8266 ou Raspberry Pi Pico W.

### 2.1. Por que o ESP32-S3?

| Critério | ESP32-S3 | ESP8266 (NodeMCU) | Arduino Uno | Raspberry Pi Zero 2 W |
| :--- | :--- | :--- | :--- | :--- |
| **Conectividade** | Wi-Fi 4 (802.11 b/g/n) + **Bluetooth 5 (LE)** | Wi-Fi apenas | Nenhuma (requer shield) | Wi-Fi + Bluetooth |
| **Processamento** | Dual-core Xtensa LX7 @ 240 MHz | Single-core @ 160 MHz | 16 MHz | Quad-core ARM @ 1GHz |
| **Memória (SRAM)** | 512 KB | ~50 KB (útil) | 2 KB | 512 MB |
| **Segurança** | **Acelerador AES, SHA, RSA** | Básico | Nenhum | Via SO Linux |
| **Consumo (Deep Sleep)** | ~10-20 µA | ~20 µA | N/A (alto) | ~100 mA (mínimo) |
| **Custo Unitário** | ~R$ 35,00 - R$ 45,00 | ~R$ 25,00 | ~R$ 40,00 | ~R$ 150,00+ |
| **Ecossistema** | PlatformIO / Arduino / ESP-IDF | Arduino | Arduino | Linux / Python |

### 2.2. Argumentos Técnicos para a Escolha

1.  **Capacidade de Processamento e Memória:**
    *   O protocolo MQTT com segurança (TLS) e o parsing de JSON exigem mais RAM do que o ESP8266 pode oferecer estavelmente. O ESP32-S3 possui **512 KB de SRAM**, permitindo buffers maiores para leitura de sensores e pilhas de rede robustas sem *crashes*.
    *   Os dois núcleos permitem separar tarefas: um núcleo gerencia a conectividade Wi-Fi/MQTT (que é "pesada" e intermitente), enquanto o outro lê sensores e gerencia a interface local, garantindo responsividade.

2.  **Segurança Nativa (Hardware Security):**
    *   Diferente de microcontroladores básicos, o S3 possui aceleradores criptográficos de hardware para cálculos de chaves públicas/privadas. Isso é crucial para garantir a integridade dos dados de saúde do animal e futuramente permitir atualizações de firmware seguras (OTA Signed).

3.  **Bluetooth Low Energy (BLE):**
    *   Embora o projeto atual use Wi-Fi, o BLE abre portas para futuras funcionalidades, como configuração inicial do dispositivo via aplicativo móvel (sem digitar senha no código) ou detecção de proximidade passiva.

4.  **Custo-Benefício Acadêmico e Comercial:**
    *   Com um custo inferior a R$ 50,00, o ESP32-S3 oferece performance comparável a dispositivos de entrada de 5 anos atrás por uma fração do preço de um computador de placa única (SBC) como o Raspberry Pi, que consumiria 10x mais energia e custaria 4x mais.

---

## 3. Sensores e Atuadores Selecionados

### 3.1. Identificação: Leitor RFID MFRC522 (13.56 MHz)

A escolha do padrão RFID de 13.56 MHz (ISO/IEC 14443A) em vez de etiquetas ativas (Bluetooth/UWB) ou códigos QR baseia-se em:

*   **Autonomia e Passividade:** As tags (chaveiros/colares) são **passivas**, ou seja, não possuem bateria. Elas duram indefinidamente e não requerem manutenção pelo usuário, um fator crítico para a adoção em massa.
*   **Custo da Tag:** As tags RFID custam menos de R$ 2,00 cada, permitindo identificar múltiplos pets ou até mesmo objetos (brinquedos) com custo irrelevante.
*   **Confiabilidade:** Ao contrário de câmeras (visão computacional) que falham com pouca luz ou oclusão, o RFID funciona no escuro total e dentro de caixas de areia fechadas, desde que a antena esteja próxima.
*   **Precisão de Identificação:** Taxa de erro próxima de zero para leitura única. O sistema sabe *exatamente* qual gato entrou, eliminando ambiguidades de sistemas baseados em peso ou imagem.

### 3.2. Pesagem: Célula de Carga + HX711

Para medir o consumo de ração e o tempo na caixa de areia, utilizamos células de carga de barra (strain gauges) com o conversor ADC HX711.

*   **Precisão:** O HX711 é um ADC de 24 bits dedicado a células de carga. Ele permite detectar variações de gramas (ex: 5g de ração) mesmo em uma plataforma que suporta quilos.
*   **Imunidade a Ruído:** Diferente de ler um sensor analógico direto no GPIO do ESP32 (que tem ruído elétrico), o HX711 faz a amplificação e digitalização próximo ao sensor, enviando dados digitais limpos via protocolo síncrono para o microcontrolador.
*   **Custo:** Uma solução profissional de pesagem industrial custaria centenas de reais. Este conjunto custa menos de R$ 20,00 e oferece precisão suficiente para monitoramento veterinário preventivo.

---

## 4. Protocolo de Comunicação: MQTT (Message Queuing Telemetry Transport)

Optou-se pelo **MQTT** em vez de HTTP/REST ou WebSockets para a comunicação entre o dispositivo e a nuvem.

### 4.1. Justificativa Técnica

1.  **Modelo Publish/Subscribe (Desacoplamento):**
    *   O dispositivo (ESP32) não precisa saber o endereço IP do servidor backend, apenas do *Broker*. Isso facilita a troca de servidores ou adição de novos serviços (ex: um serviço de Analytics) sem reprogramar o firmware. Basta o novo serviço se inscrever no tópico.

2.  **Eficiência de Banda e Bateria:**
    *   O cabeçalho de uma mensagem MQTT tem apenas **2 bytes** (mínimo), contra dezenas de bytes de um cabeçalho HTTP. Em redes Wi-Fi instáveis ou para economizar dados, essa eficiência é vital.
    *   Suporte nativo a **QoS (Quality of Service)**:
        *   *QoS 0:* "Fire and forget" (para telemetria frequente onde perder um dado não é grave).
        *   *QoS 1:* "At least once" (garantia de entrega para alertas críticos).

3.  **Gerenciamento de Conexão Intermitente:**
    *   O protocolo foi desenhado para redes instáveis. O recurso **Last Will and Testament (LWT)** permite que o broker notifique o sistema imediatamente se o dispositivo cair inesperadamente (ex: falta de energia), gerando um alerta de "Dispositivo Offline".

4.  **Escalabilidade:**
    *   Brokers modernos (como HiveMQ ou Mosquitto) suportam milhões de conexões simultâneas. A arquitetura permite escalar horizontalmente o backend sem alterar o firmware dos dispositivos.

---

## 5. Infraestrutura de Nuvem e Containerização

O backend foi construído utilizando **Docker** e orquestrado via **Docker Compose**, rodando em uma VM genérica (ex: Google Cloud Compute Engine).

### 5.1. Por que Docker e não Serverless (Lambda/Cloud Functions)?

*   **Estado Persistente e Worker Longo:** O componente `worker.py` mantém uma conexão TCP persistente com o Broker MQTT para ouvir mensagens em tempo real. Funções serverless são efêmeras (iniciam e morrem a cada requisição), o que tornaria a subscrição MQTT complexa e cara (cold starts constantes).
*   **Portabilidade:** A exigência do projeto de rodar tanto no MacBook do desenvolvedor quanto na VM da Google Cloud sem alterações de código é atendida pelos containers. O ambiente é imutável e consistente.
*   **Custo Previsível:** Para um fluxo de dados contínuo de IoT, manter uma VM pequena (ex: e2-micro ou e2-small na GCP) é frequentemente mais barato do que executar milhares de invocações de funções serverless processando cada mensagem MQTT individualmente.

### 5.2. Banco de Dados: PostgreSQL vs. SQLite

*   **Desenvolvimento:** Usa-se **SQLite** para simplicidade (arquivo único, zero configuração), facilitando a entrada de novos desenvolvedores no projeto.
*   **Produção:** Migra-se para **PostgreSQL** via Docker. O SQLAlchemy (ORM) abstrai essa diferença. O PostgreSQL oferece robustez, concorrência e integridade de dados necessárias para um histórico de saúde de longo prazo.

---

## 6. Conclusão da Arquitetura

A arquitetura proposta equilibra **baixo custo de hardware** (total do dispositivo < R$ 80,00) com **alta confiabilidade de software**.

*   **No Edge:** O ESP32-S3 fornece poder de sobra para processamento local e segurança, garantindo que o dispositivo não seja um gargalo.
*   **No Transporte:** O MQTT garante leveza e resiliência contra falhas de rede.
*   **Na Nuvem:** A containerização Docker assegura que o sistema seja replicável, escalável e fácil de manter, atendendo aos requisitos acadêmicos de reprodutibilidade e aos requisitos práticos de um produto viável.

Esta combinação torna o SmartCat não apenas um protótipo funcional, mas uma base sólida para um produto comercializável de IoT veterinária.
