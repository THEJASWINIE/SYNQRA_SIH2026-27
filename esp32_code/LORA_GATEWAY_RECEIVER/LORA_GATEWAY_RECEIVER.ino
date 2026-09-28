#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>

// =====================================================
// FOG-ORCHESTRATOR 2.0 — LORA GATEWAY AGGREGATOR
// =====================================================
// Based on the physically proven Vehicle A (TRUCK_01) LoRa architecture.
//
// Architecture:
//   TRUCK_01 --LoRa (433MHz)--> Gateway ESP32 --WiFi (HTTP POST)--> Backend
//   TRUCK_02 --LoRa (433MHz)--> Gateway ESP32 --WiFi (HTTP POST)--> Backend
//
// Direct V2V (TRUCK_01 <---> TRUCK_02) remains independent peer-to-peer.
// The Gateway is transport infrastructure only:
//   - NO physics calculations
//   - NO dispatch optimization
//   - NO Digital Twin logic
//   - NO HMI logic
//   - NO vehicle positioning algorithms
// =====================================================

// LoRa SPI pins (FROZEN - matches Vehicle A)
#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23

// LoRa control pins (FROZEN - matches Vehicle A)
#define LORA_SS    5
#define LORA_RST   4
#define LORA_DIO0  34

// LoRa Frequency (FROZEN - matches Vehicle A)
#define LORA_FREQUENCY 433E6

// Wi-Fi Credentials & Backend Endpoint
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

const char* WIFI_SSID     = SECRET_WIFI_SSID;
const char* WIFI_PASSWORD = SECRET_WIFI_PASSWORD;
const char* HMI_SERVER    = SECRET_HMI_TELEMETRY_URL;

// Wi-Fi Reconnect timer
unsigned long lastWiFiCheck = 0;
const unsigned long WIFI_CHECK_INTERVAL = 5000;

// Packet & Forwarding Statistics
unsigned long packetsReceived = 0;
unsigned long packetsForwarded = 0;
unsigned long packetsForwardFailed = 0;
unsigned long malformedPackets = 0;
unsigned long lastStatusPrint = 0;

// Probe backend reachability (Problem 2 - State H)
bool checkBackendReachability() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[GATEWAY] Backend: UNREACHABLE (WiFi offline)");
    return false;
  }
  HTTPClient http;
  http.setTimeout(1500);

  String healthUrl = String(HMI_SERVER);
  int apiIdx = healthUrl.indexOf("/api/");
  if (apiIdx != -1) {
    healthUrl = healthUrl.substring(0, apiIdx) + "/api/health";
  } else {
    healthUrl = "http://192.168.137.1:8000/api/health";
  }

  http.begin(healthUrl);
  int httpCode = http.GET();
  bool reachable = (httpCode == 200);
  if (reachable) {
    Serial.println("[GATEWAY] Backend: REACHABLE");
  } else {
    Serial.print("[GATEWAY] Backend: UNREACHABLE (status=");
    Serial.print(httpCode);
    Serial.println(")");
  }
  http.end();
  return reachable;
}

// Wi-Fi connection logic matching Vehicle A (sketch_aug26a)
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  Serial.print("[GATEWAY] Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(500);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[GATEWAY] WiFi: CONNECTED");
    Serial.print("[GATEWAY] IP: ");
    Serial.println(WiFi.localIP());
    checkBackendReachability();
  } else {
    Serial.println("[GATEWAY] WiFi: DISCONNECTED (will retry)");
  }
}

// Forward parsed vehicle state to FastAPI backend via HTTP POST
bool forwardTelemetryToBackend(
  const String& vehicleId,
  unsigned long sequence,
  float rpm,
  float speed,
  long ax, long ay, long az,
  long gx, long gy, long gz,
  int rssi,
  float snr
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi TX] FAILED: Wi-Fi not connected");
    packetsForwardFailed++;
    return false;
  }

  HTTPClient http;
  http.setTimeout(1000); // Strict bounded timeout (<= 1s) to avoid stalling LoRa receiver
  http.begin(HMI_SERVER);
  http.addHeader("Content-Type", "application/json");

  // Construct canonical HardwareTelemetryPayload JSON
  String json = "{";
  json += "\"vehicle_id\":\"" + vehicleId + "\",";
  json += "\"sequence\":" + String(sequence) + ",";
  json += "\"rpm\":" + String(rpm, 2) + ",";
  json += "\"speed\":" + String(speed, 3) + ",";
  json += "\"ax\":" + String(ax) + ",";
  json += "\"ay\":" + String(ay) + ",";
  json += "\"az\":" + String(az) + ",";
  json += "\"gx\":" + String(gx) + ",";
  json += "\"gy\":" + String(gy) + ",";
  json += "\"gz\":" + String(gz) + ",";
  json += "\"rssi\":" + String(rssi) + ",";
  json += "\"snr\":" + String(snr, 2) + ",";
  json += "\"source\":\"LORA_GATEWAY\"";
  json += "}";

  int httpCode = http.POST(json);

  // Step 14 logging format
  Serial.print("[WiFi TX] vehicle=");
  Serial.print(vehicleId);
  Serial.print(" sequence=");
  Serial.print(sequence);
  Serial.print(" status=");
  Serial.println(httpCode);

  bool success = (httpCode >= 200 && httpCode < 300) || (httpCode == 409); // 409 Conflict is valid duplicate/ordering rejection
  if (success) {
    packetsForwarded++;
    if (httpCode == 409) {
      Serial.print("[WiFi TX] 409 Response: ");
      Serial.println(http.getString());
    }
  } else {
    packetsForwardFailed++;
    if (httpCode > 0) {
      Serial.print("[WiFi TX] Error response: ");
      Serial.println(http.getString());
    }
  }

  http.end();
  return success;
}

// Forward parsed Safe Beacon to FastAPI backend via HTTP POST (Gap 2)
bool forwardBeaconToBackend(
  const String& vehicleId,
  unsigned long beaconSeq,
  const String& state,
  const String& zoneId,
  int rssi,
  float snr
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi BEACON TX] FAILED: Wi-Fi not connected");
    return false;
  }

  HTTPClient http;
  http.setTimeout(1000);

  String beaconUrl = String(HMI_SERVER);
  int apiIdx = beaconUrl.indexOf("/api/");
  if (apiIdx != -1) {
    beaconUrl = beaconUrl.substring(0, apiIdx) + "/api/hardware/beacon";
  } else {
    beaconUrl = "http://192.168.137.1:8000/api/hardware/beacon";
  }

  http.begin(beaconUrl);
  http.addHeader("Content-Type", "application/json");

  String json = "{";
  json += "\"vehicle_id\":\"" + vehicleId + "\",";
  json += "\"beacon_sequence\":" + String(beaconSeq) + ",";
  json += "\"state\":\"" + state + "\",";
  json += "\"zone_id\":\"" + zoneId + "\",";
  json += "\"rssi\":" + String(rssi) + ",";
  json += "\"snr\":" + String(snr, 2) + ",";
  json += "\"source\":\"LORA_GATEWAY\"";
  json += "}";

  int httpCode = http.POST(json);
  Serial.print("[WiFi BEACON TX] vehicle=");
  Serial.print(vehicleId);
  Serial.print(" seq=");
  Serial.print(beaconSeq);
  Serial.print(" state=");
  Serial.print(state);
  Serial.print(" status=");
  Serial.println(httpCode);

  bool success = (httpCode == 200 || httpCode == 409);
  if (success) {
    packetsForwarded++;
  } else {
    packetsForwardFailed++;
  }
  http.end();
  return success;
}

// Parse packet using Vehicle A's exact parsing logic adapted for both vehicles
bool parsePacket(String packet) {
  packet.trim();

  Serial.println();
  Serial.println("<<< RAW LORA RX >>>");
  Serial.println(packet);

  if (packet.length() == 0) {
    malformedPackets++;
    Serial.println("REJECT: EMPTY PACKET");
    return false;
  }

  // 1. Diagnostic / Discovery Packet: HELLO,<VEHICLE_ID>
  if (packet.startsWith("HELLO,")) {
    int commaIdx = packet.indexOf(',');
    String vehicleId = packet.substring(commaIdx + 1);
    vehicleId.trim();
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    Serial.print("[LoRa RX] HELLO,");
    Serial.println(vehicleId);
    Serial.print("[LoRa RX] vehicle=");
    Serial.print(vehicleId);
    Serial.print(" RSSI=");
    Serial.print(rssi);
    Serial.print(" dBm SNR=");
    Serial.print(snr, 2);
    Serial.println(" dB");
    return true;
  }

  // 2. Production Safe Beacon Packet: BEACON,<VEHICLE_ID>,<seq>,<state>,<timestamp>,<zone_id> (Gap 2)
  if (packet.startsWith("BEACON,")) {
    String bFields[6];
    int bIndex = 0;
    int bStart = 0;
    for (int i = 0; i <= packet.length(); i++) {
      if (i == packet.length() || packet.charAt(i) == ',') {
        if (bIndex < 6) {
          bFields[bIndex] = packet.substring(bStart, i);
          bFields[bIndex].trim();
          bIndex++;
        }
        bStart = i + 1;
      }
    }
    if (bIndex >= 4) {
      String bVeh = bFields[1];
      bVeh.toUpperCase();
      unsigned long bSeq = strtoul(bFields[2].c_str(), NULL, 10);
      String bState = bFields[3];
      bState.toUpperCase();
      String bZone = (bIndex >= 6) ? bFields[5] : "PIT_ZONE_A";

      int rssi = LoRa.packetRssi();
      float snr = LoRa.packetSnr();

      Serial.println();
      Serial.println("**************************************************");
      Serial.println(">>> [LoRa RX] PRODUCTION SAFE BEACON RECEIVED! <<<");
      Serial.print("[LoRa RX] vehicle=");
      Serial.print(bVeh);
      Serial.print(" beacon_seq=");
      Serial.print(bSeq);
      Serial.print(" state=");
      Serial.print(bState);
      Serial.print(" RSSI=");
      Serial.print(rssi);
      Serial.print(" dBm SNR=");
      Serial.print(snr, 2);
      Serial.println(" dB");
      Serial.println("**************************************************");

      forwardBeaconToBackend(bVeh, bSeq, bState, bZone, rssi, snr);
      packetsReceived++;
      return true;
    }
  }

  // Diagnostic / Hardware Isolation Test Packets: TRUCK02_LORA_TEST,<seq> or LORA_TEST,<seq>
  if (packet.startsWith("TRUCK02_LORA_TEST,") || packet.startsWith("LORA_TEST,")) {
    int commaIdx = packet.indexOf(',');
    unsigned long seq = packet.substring(commaIdx + 1).toInt();
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    Serial.println();
    Serial.println("**************************************************");
    Serial.println(">>> [LoRa RX] HARDWARE TEST PACKET RECEIVED! <<<");
    Serial.print("[LoRa RX] vehicle=TRUCK_02 sequence=");
    Serial.print(seq);
    Serial.print(" RSSI=");
    Serial.print(rssi);
    Serial.print(" dBm SNR=");
    Serial.print(snr, 2);
    Serial.println(" dB");
    Serial.println("**************************************************");
    packetsReceived++;
    return true;
  }

  // 3. Canonical Telemetry Packet: STATE,<VEHICLE_ID>,sequence,rpm,speed,ax,ay,az,gx,gy,gz
  // Split using Vehicle A's exact robust token loop
  String fields[11];
  int fieldIndex = 0;
  int startIndex = 0;

  for (int i = 0; i <= packet.length(); i++) {
    if (i == packet.length() || packet.charAt(i) == ',') {
      if (fieldIndex < 11) {
        fields[fieldIndex] = packet.substring(startIndex, i);
        fields[fieldIndex].trim();
        fieldIndex++;
      }
      startIndex = i + 1;
    }
  }

  if (fieldIndex != 11) {
    malformedPackets++;
    Serial.print("[LoRa RX] UNKNOWN/IGNORED: Wrong field count (");
    Serial.print(fieldIndex);
    Serial.println("): " + packet);
    return false;
  }

  if (fields[0] != "STATE") {
    malformedPackets++;
    Serial.println("[LoRa RX] UNKNOWN/IGNORED: " + packet);
    return false;
  }

  String vehicleId = fields[1];
  vehicleId.trim();
  vehicleId.toUpperCase();

  // Dynamically accept BOTH TRUCK_01 and TRUCK_02
  if (vehicleId != "TRUCK_01" && vehicleId != "TRUCK_02") {
    malformedPackets++;
    Serial.println("[LoRa RX] UNKNOWN/IGNORED: Unknown vehicle " + vehicleId);
    return false;
  }

  unsigned long sequence = strtoul(fields[2].c_str(), NULL, 10);
  float rpm   = fields[3].toFloat();
  float speed = fields[4].toFloat();
  long ax     = fields[5].toInt();
  long ay     = fields[6].toInt();
  long az     = fields[7].toInt();
  long gx     = fields[8].toInt();
  long gy     = fields[9].toInt();
  long gz     = fields[10].toInt();

  int rssi = LoRa.packetRssi();
  float snr = LoRa.packetSnr();

  packetsReceived++;

  // Step 14 logging format
  Serial.print("[LoRa RX] vehicle=");
  Serial.print(vehicleId);
  Serial.print(" sequence=");
  Serial.print(sequence);
  Serial.print(" RSSI=");
  Serial.print(rssi);
  Serial.print(" dBm SNR=");
  Serial.print(snr, 2);
  Serial.println(" dB");

  // Forward to backend wirelessly via Wi-Fi HTTP POST
  forwardTelemetryToBackend(
    vehicleId, sequence, rpm, speed,
    ax, ay, az, gx, gy, gz,
    rssi, snr
  );

  return true;
}

// Receive function matching Vehicle A (sketch_aug26a receiveV2V)
void receiveLoRaPackets() {
  int packetSize = LoRa.parsePacket();
  if (packetSize <= 0) {
    return;
  }

  Serial.println();
  Serial.print("LoRa packet size: ");
  Serial.println(packetSize);

  String packet = "";
  packet.reserve(packetSize + 1);

  while (LoRa.available()) {
    packet += (char)LoRa.read();
  }

  // Parse and process
  parsePacket(packet);

  // Return to receive mode immediately (matching Vehicle A)
  LoRa.receive();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("==================================================");
  Serial.println("   FOG-ORCHESTRATOR 2.0 — LoRa GATEWAY NODE");
  Serial.println("==================================================");

  // Configure SPI matching Vehicle A
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);

  // Configure LoRa pins matching Vehicle A
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  Serial.println("Initializing LoRa...");

  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("[GATEWAY] LoRa: FAILED");
    while (true) {
      delay(1000);
    }
  }

  // Radio parameters consistent with Vehicle A
  LoRa.enableCrc();
  LoRa.setTxPower(17);

  // Start continuous receive mode
  LoRa.receive();

  Serial.println("[GATEWAY] LoRa: READY");
  Serial.println("Frequency: 433 MHz");
  Serial.println("CRC: ENABLED");
  Serial.println("RX MODE: ENABLED");

  // Connect to Wi-Fi matching Vehicle A
  connectWiFi();

  Serial.print("[GATEWAY] Target telemetry endpoint: ");
  Serial.println(HMI_SERVER);
  Serial.println("==================================================");
}

void loop() {
  unsigned long now = millis();

  // Continuous LoRa packet check matching Vehicle A (sketch_aug26a)
  receiveLoRaPackets();

  // Periodic Wi-Fi connection monitor (non-blocking)
  if (now - lastWiFiCheck >= WIFI_CHECK_INTERVAL) {
    lastWiFiCheck = now;
    if (WiFi.status() != WL_CONNECTED) {
      connectWiFi();
    }
  }

  // Periodic status summary
  if (now - lastStatusPrint >= 10000) {
    lastStatusPrint = now;
    Serial.println("--- [GATEWAY STATUS] ---");
    Serial.print("RX packets: ");
    Serial.print(packetsReceived);
    Serial.print(" | Forwarded: ");
    Serial.print(packetsForwarded);
    Serial.print(" | Failed: ");
    Serial.print(packetsForwardFailed);
    Serial.print(" | Malformed: ");
    Serial.print(malformedPackets);
    Serial.print(" | Wi-Fi: ");
    Serial.println(WiFi.status() == WL_CONNECTED ? "ONLINE" : "OFFLINE");
  }

  // Cooperative delay matching Vehicle A
  delay(2);
}