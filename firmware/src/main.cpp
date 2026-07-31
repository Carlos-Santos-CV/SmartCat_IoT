#include <Arduino.h>
#include <ArduinoJson.h>
#include <MFRC522.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <WiFi.h>

/** Configuration Constants **/

namespace NetworkConfig {
constexpr const char *SSID_WIFI = "Wokwi-GUEST";
constexpr const char *SENHA_WIFI = "";
constexpr const char *BROKER_MQTT = "broker.hivemq.com";
constexpr int PORTA_MQTT = 1883;
constexpr const char *TOPICO_COMIDA = "smartcat/estacao_comida/telemetria";
constexpr const char *TOPICO_CAIXA = "smartcat/caixa_areia/telemetria";
} // namespace NetworkConfig

namespace HardwareConfig {
constexpr int SS_PIN = 5;
constexpr int RST_PIN = 4;
constexpr int PINO_JOY_PESO = 1;
constexpr int PINO_JOY_SW = 2;
constexpr int MAX_ANALOG_VALUE = 4095;
} // namespace HardwareConfig

// Global Objects
MFRC522 rfid(HardwareConfig::SS_PIN, HardwareConfig::RST_PIN);
WiFiClient espClient;
PubSubClient client(espClient);

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
    Serial.println("[Wi-Fi] Conectado!");
  }
}

unsigned long lastMqttCheck = 0;

void handleMQTT() {
  if (!client.connected() && millis() - lastMqttCheck > 5000) {
    Serial.println("[MQTT] Tentando conectar ao Broker...");
    String clientId = "SmartCat_S3_" + String(random(0xffff), HEX);
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
  Serial.println("\n=== SmartCat ESP32-S3 Inicializado ===");
}

void loop() {
  handleWiFi();
  handleMQTT();

  if (client.connected()) {
    client.loop();
  }

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

    int valorAnalogico = analogRead(HardwareConfig::PINO_JOY_PESO);
    float pesoConsumidoG =
        map(valorAnalogico, 0, HardwareConfig::MAX_ANALOG_VALUE, 5, 80);

    String nomeGato = (tagID == "A1B2C3D4") ? "Luna" : "Thor";

    StaticJsonDocument<256> doc;
    doc["estacao_id"] = "pote_sala_s3";
    doc["gato_tag"] = tagID;
    doc["gato_nome"] = nomeGato;
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

  bool estadoBotaoAtual = digitalRead(HardwareConfig::PINO_JOY_SW);

  // Detecção de clique (borda de descida: HIGH -> LOW)
  if (ultimoEstadoBotao == HIGH && estadoBotaoAtual == LOW) {
    delay(100); // Debounce
    if (!emUsoCaixa) {
      // Clique 1: Gato Entrou na Caixa
      emUsoCaixa = true;
      tempoEntradaCaixa = millis();
      Serial.println("\n[Caixa de Areia] Gato ENTROU na caixa...");
    } else {
      // Clique 2: Gato Saiu da Caixa
      emUsoCaixa = false;
      unsigned long duracaoVisitaSegundos = (millis() - tempoEntradaCaixa) / 1000;

      StaticJsonDocument<256> docCaixa;
      docCaixa["estacao_id"] = "caixa_banheiro_s3";
      docCaixa["gato_nome"] = "Thor";
      docCaixa["duracao_visita_s"] = duracaoVisitaSegundos;
      docCaixa["alerta_retencao"] = (duracaoVisitaSegundos > 300);

      char bufferCaixa[256];
      serializeJson(docCaixa, bufferCaixa);

      client.publish(NetworkConfig::TOPICO_CAIXA, bufferCaixa);
      Serial.printf("[MQTT Caixa Enviado]: %s\n", bufferCaixa);
    }
  }
  ultimoEstadoBotao = estadoBotaoAtual;
}