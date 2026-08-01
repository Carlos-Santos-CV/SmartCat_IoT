Claro! Vou explicar o `firmware/src/main.cpp` por partes — é o código que roda no ESP32-S3 e é responsável por ler o RFID, medir o "peso" e publicar tudo via MQTT.

## 1. Configurações (namespaces)

```cpp
namespace NetworkConfig { ... }
namespace HardwareConfig { ... }
```

- **`NetworkConfig`**: credenciais Wi-Fi (`Wokwi-GUEST`, rede aberta usada só na simulação), endereço do broker MQTT (`broker.hivemq.com:1883`) e os dois tópicos de publicação (`estacao_comida` e `caixa_areia`).
- **`HardwareConfig`**: pinos do leitor RFID (SS=5, RST=4), pinos do joystick (peso=GPIO1, botão=GPIO2), resolução do ADC (`4095`) e a `JANELA_IDENTIFICACAO_MS` (10 segundos) — usada para "lembrar" qual gato comeu por último.

## 2. Identidade do dispositivo

```cpp
String getDeviceID() {
  String mac = WiFi.macAddress();
  mac.replace(":", "");
  return "ESP32_" + mac;
}
```

Gera um ID único por dispositivo a partir do MAC address (ex: `ESP32_240AC4000110`). Esse ID é o que identifica a estação no backend — não precisa ser configurado manualmente, é dinâmico.

## 3. Conexão não-bloqueante (Wi-Fi e MQTT)

```cpp
void handleWiFi() { ... }
void handleMQTT() { ... }
```

Em vez de travar o programa esperando conectar (`delay()`), essas funções tentam reconectar a cada 5 segundos, verificando `millis()`. Isso permite que o `loop()` continue rodando (lendo sensores) mesmo enquanto a rede está caindo/reconectando.

## 4. `setup()`

Inicializa a serial, o barramento SPI (usado pelo leitor RFID), o próprio RFID (`rfid.PCD_Init()`) e configura o servidor MQTT.

## 5. `loop()` — o coração do firmware

Tem duas "estações" simuladas rodando em paralelo:

### 🍽️ Estação de comida (RFID + peso)

```cpp
if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
```

Quando uma tag RFID é aproximada:
1. Lê o UID da tag e monta uma string hexadecimal (`tagID`), ex: `A1B2C3D4`.
2. Guarda essa tag e o instante da leitura em `ultimaTagLida` / `timestampUltimaTag` — isso é usado depois pela estação da caixa de areia.
3. Lê o valor analógico do joystick (`analogRead`) e faz um `map()` de 0–4095 para 5–80 gramas, **simulando** o peso de ração consumido (no hardware real isso seria uma célula de carga).
4. Monta um JSON `{ estacao_id, gato_tag, consumo_g }` e publica no tópico `smartcat/estacao_comida/telemetria`.
5. Aplica um cooldown de 2 segundos (não-bloqueante, via `while` + `yield()`) para não disparar leituras repetidas da mesma aproximação.

### 🧹 Estação da caixa de areia (botão do joystick)

```cpp
static bool emUsoCaixa = false;
```

Como não há um segundo leitor RFID no protótipo, essa parte simula **entrada/saída** da caixa com cliques no botão do joystick, detectando a borda de descida (HIGH→LOW) com debounce de 100ms:

- **1º clique** → marca `emUsoCaixa = true` e guarda o horário de entrada. Também tenta descobrir *qual gato* está usando a caixa: se a última tag lida no pote de comida foi há **menos de 10 segundos**, assume que é o mesmo gato (`tagRecente`); senão, deixa a tag vazia (gato desconhecido).
- **2º clique** → marca `emUsoCaixa = false`, calcula a duração da visita (`(millis() - tempoEntradaCaixa) / 1000`) e publica `{ estacao_id, gato_tag, duracao_visita_s }` no tópico `smartcat/caixa_areia/telemetria`.

## Resumo da lógica de "identificação por proximidade temporal"

Esse é o ponto mais interessante (e a maior limitação) do firmware: como só existe **um leitor RFID físico** compartilhado entre as duas estações simuladas, o sistema não sabe com certeza quem está na caixa de areia — ele **infere** que é o último gato que comeu, e só aceita essa inferência se isso aconteceu há no máximo 10 segundos. Fora dessa janela, o evento é registrado com `gato_tag` vazio (o backend trata isso como "tag desconhecida").

Isso é uma simplificação intencional para a simulação no Wokwi; em um protótipo físico real, o ideal seria ter um leitor RFID dedicado em cada estação, eliminando essa heurística.