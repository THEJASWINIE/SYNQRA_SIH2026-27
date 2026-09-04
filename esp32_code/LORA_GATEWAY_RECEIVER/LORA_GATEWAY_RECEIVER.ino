#include <SPI.h>
#include <LoRa.h>

// =====================================================
// LORA GATEWAY RECEIVER FIRMWARE — FOG-ORCHESTRATOR 2.0
// Listens continuously on 433 MHz, appends RSSI/SNR,
// and streams raw telemetry lines over USB Serial at 115200 baud.
// =====================================================

#define LORA_SCK  18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS   5
#define LORA_RST  4
#define LORA_DIO0 34

#define LORA_FREQUENCY 433E6

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000);

  Serial.println("[GATEWAY] Starting LoRa Receiver Gateway...");

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("[GATEWAY] ERROR: LoRa initialization failed!");
    while (1);
  }

  Serial.println("[GATEWAY] LoRa Receiver Listening on 433 MHz...");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incomingPayload = "";
    while (LoRa.available()) {
      incomingPayload += (char)LoRa.read();
    }

    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    // Sanity check: Ensure payload contains valid vehicle identifier token
    if (incomingPayload.startsWith("V=") || incomingPayload.indexOf("V=") != -1) {
      // Append RSSI & SNR metadata for gateway telemetry reporting
      String gatewayOutput = incomingPayload + ",RSSI=" + String(rssi) + ",SNR=" + String(snr, 1);
      
      // Output raw canonical string to host via USB Serial
      Serial.println(gatewayOutput);
    }
  }
}
