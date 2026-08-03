#include <Arduino.h>
#include <ArduinoJson.h>
#include <MFRC522.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <WiFi.h>

/** Configuration Constants **/

namespace NetworkConfig {
// SSID e senha do WiFi - definidos via build_flags do PlatformIO
// Dev: -D WIFI_SSID="Wokwi-GUEST" -D WIFI_PASSWORD=""
// Prod: -D WIFI_SSID="SUA_REDE" -D WIFI_PASSWORD="SUA_SENHA"
#ifndef WIFI_SSID
#define WIFI_SSID "Wokwi-GUEST"  // Fallback se não definido
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif

#ifndef MQTT_BROKER
#define MQTT_BROKER "broker.hivemq.com"
#endif

#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif

constexpr const char *SSID_WIFI = WIFI_SSID;
constexpr const char *SENHA_WIFI = WIFI_PASSWORD;
constexpr const char *BROKER_MQTT = MQTT_BROKER;
constexpr int PORTA_MQTT = MQTT_PORT;

constexpr const char *TOPICO_COMIDA = "smartcat/estacao_comida/telemetria";
constexpr const char *TOPICO_CAIXA = "smartcat/caixa_areia/telemetria";
} // namespace NetworkConfig

namespace HardwareConfig {
constexpr int SS_PIN = 5;
constexpr int RST_PIN = 4;
constexpr int PINO_JOY_PESO = 1;
constexpr int PINO_JOY_SW = 2;
constexpr int MAX_ANALOG_VALUE = 4095;
// Janela de tempo em que uma leitura RFID feita no pote de comida ainda
// é considerada válida para identificar o gato na caixa de areia.
// Necessário porque, nesse hardware simulado, há um único leitor
// compartilhado entre as duas estações (não há leitor dedicado na caixa).
constexpr unsigned long JANELA_IDENTIFICACAO_MS = 10000; // 10 segundos
} // namespace HardwareConfig

// Global Objects
MFRC522 rfid(HardwareConfig::SS_PIN, HardwareConfig::RST_PIN);
WiFiClient espClient;
PubSubClient client(espClient);

// String global para armazenar o ID único do dispositivo derivado do MAC
String dispositivoID = "";

// Última tag lida no pote de comida e o instante dessa leitura.
// Usada para tentar identificar o gato na caixa de areia, mas só
// dentro da JANELA_IDENTIFICACAO_MS (ver acima).
String ultimaTagLida = "";
unsigned long timestampUltimaTag = 0;

/** Função para obter o ID Dinâmico baseado no MAC Address **/
String getDeviceID() {
  String mac = WiFi.macAddress();
  mac.replace(":", ""); // Remove os dois pontos do MAC
  return "ESP32_" + mac;
}

/** Non-blocking Connection Handling **/

bool isWifiConnected = false;
unsigned long lastWifiCheck = 0;

void handleWiFi() {
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiCheck > 5000) {
    Serial.print("[Wi-Fi] Tentando conectar...");
    WiFi.begin(NetworkConfig::SSID_WIFI, NetworkConfig::SENHA_WIFI);
    lastWifiCheck = millis();
  } else if (WiFi.status() == WL_CONNECTED && !isWifiConnected) {
    isWifiConnected = true;
    dispositivoID = getDeviceID(); // Gera o ID assim que o Wi-Fi inicializa a interface
    Serial.print("[Wi-Fi] Conectado! Dispositivo ID: ");
    Serial.println(dispositivoID);
  }
}

unsigned long lastMqttCheck = 0;

void handleMQTT() {
  if (!client.connected() && millis() - lastMqttCheck > 5000) {
    Serial.println("[MQTT] Tentando conectar ao Broker...");
    // Usa o ID único do dispositivo na conexão MQTT para evitar desconexões
    String clientId = dispositivoID.length() > 0 ? dispositivoID : "SmartCat_S3_" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("[MQTT] Conectado!");
    } else {
      Serial.print("[MQTT] Erro de conexao: ");
      Serial.println(client.state());
    }
    lastMqttCheck = millis();
  }
}

/** Setup and Loop **/

void setup() {
  Serial.begin(115200);
  pinMode(HardwareConfig::PINO_JOY_SW, INPUT_PULLUP);

  // SCK, MISO, MOSI, SS
  SPI.begin(12, 13, 11, HardwareConfig::SS_PIN);
  rfid.PCD_Init();

  client.setServer(NetworkConfig::BROKER_MQTT, NetworkConfig::PORTA_MQTT);
  Serial.println("\n=== SmartCat ESP32-S3 Inicializado (ID Dinâmico via MAC) ===");
}

void loop() {
  handleWiFi();
  handleMQTT();

  if (client.connected()) {
    client.loop();
  }

  // Fallback caso tente rodar sem conectar o Wi-Fi
  String estacaoIdAtual = dispositivoID.length() > 0 ? dispositivoID : "ESP32_DESCONHECIDO";

  // ======================================================
  // 1. ESTAÇÃO POTE DE COMIDA (RFID + Leitura de Peso)
  // ======================================================
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    String tagID = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      if (rfid.uid.uidByte[i] < 0x10)
        tagID += "0";
      tagID += String(rfid.uid.uidByte[i], HEX);
    }
    tagID.toUpperCase();
    ultimaTagLida = tagID;
    timestampUltimaTag = millis();

    int valorAnalogico = analogRead(HardwareConfig::PINO_JOY_PESO);
    float pesoConsumidoG =
        map(valorAnalogico, 0, HardwareConfig::MAX_ANALOG_VALUE, 5, 80);

    // JSON sem hardcode: ID da estação vem dinamicamente do hardware
    StaticJsonDocument<256> doc;
    doc["estacao_id"] = estacaoIdAtual;
    doc["gato_tag"] = tagID;
    doc["consumo_g"] = pesoConsumidoG;

    char bufferJSON[256];
    serializeJson(doc, bufferJSON);

    client.publish(NetworkConfig::TOPICO_COMIDA, bufferJSON);
    Serial.printf("[MQTT Comida Enviado]: %s\n", bufferJSON);

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    // Cooldown não-bloqueante
    unsigned long startDelay = millis();
    while (millis() - startDelay < 2000) {
      yield();
    }
  }

  // ======================================================
  // 2. ESTAÇÃO CAIXA DE AREIA (Simulado pelo Clique do Joystick)
  // ======================================================
  static bool emUsoCaixa = false;
  static unsigned long tempoEntradaCaixa = 0;
  static bool ultimoEstadoBotao = HIGH;
  static String tagCaixaAtual = "";

  bool estadoBotaoAtual = digitalRead(HardwareConfig::PINO_JOY_SW);

  // Detecção de clique (borda de descida: HIGH -> LOW)
  if (ultimoEstadoBotao == HIGH && estadoBotaoAtual == LOW) {
    delay(100); // Debounce
    if (!emUsoCaixa) {
      // Clique 1: Entrada na Caixa
      emUsoCaixa = true;
      tempoEntradaCaixa = millis();

      // Usa a última tag lida no pote de comida, mas só se foi lida
      // recentemente (dentro da janela de identificação). Isso evita
      // atribuir a visita a um gato que comeu horas atrás.
      bool tagRecente = (millis() - timestampUltimaTag) <= HardwareConfig::JANELA_IDENTIFICACAO_MS;
      tagCaixaAtual = tagRecente ? ultimaTagLida : "";

      Serial.println("\n[Caixa de Areia] Presenca detectada na caixa...");
    } else {
      // Clique 2: Saída da Caixa
      emUsoCaixa = false;
      unsigned long duracaoVisitaSegundos = (millis() - tempoEntradaCaixa) / 1000;

      // JSON da Caixa sem hardcode de ID
      StaticJsonDocument<256> docCaixa;
      docCaixa["estacao_id"] = estacaoIdAtual;
      docCaixa["gato_tag"] = tagCaixaAtual;
      docCaixa["duracao_visita_s"] = duracaoVisitaSegundos;

      char bufferCaixa[256];
      serializeJson(docCaixa, bufferCaixa);

      client.publish(NetworkConfig::TOPICO_CAIXA, bufferCaixa);
      Serial.printf("[MQTT Caixa Enviado]: %s\n", bufferCaixa);
    }
  }
  ultimoEstadoBotao = estadoBotaoAtual;
}