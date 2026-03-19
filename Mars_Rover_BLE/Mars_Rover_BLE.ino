/*
 * BLE Motor Control — ESP32-C6 + TB6612FNG
 * 
 * Commands (via BLE UART or Serial):
 *   f<speed>   — Forward (0-255)
 *   b<speed>   — Backward (0-255)
 *   s          — Stop
 *   e          — Enable driver
 *   d          — Disable driver
 *
 * Connect via nRF Connect / LightBlue
 * Device name: MarsRover
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ── Motor pins ──
#define STBY  11
#define IN1   10
#define IN2   1
#define PWMA  6

// ── BLE UUIDs (Nordic UART Service) ──
#define SERVICE_UUID        "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHAR_RX_UUID        "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHAR_TX_UUID        "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

BLEServer* pServer = nullptr;
BLECharacteristic* pTxChar = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// ── Motor control ──
void setMotor(int direction, int speed) {
  if (direction == 1) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
  } else if (direction == -1) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
  } else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
  }
  analogWrite(PWMA, speed);
}

// Send a string back over BLE + Serial
void respond(const String& msg) {
  Serial.println(msg);
  if (deviceConnected && pTxChar) {
    pTxChar->setValue(msg.c_str());
    pTxChar->notify();
  }
}

// ── Command parser ──
void handleCommand(String input) {
  input.trim();
  input.toLowerCase();
  if (input.length() == 0) return;

  char cmd = input.charAt(0);
  int speed = 0;

  if (input.length() > 1) {
    speed = input.substring(1).toInt();
    speed = constrain(speed, 0, 255);
  }

  switch (cmd) {
    case 'f':
      setMotor(1, speed);
      respond(">> Forward at speed: " + String(speed));
      break;
    case 'b':
      setMotor(-1, speed);
      respond(">> Backward at speed: " + String(speed));
      break;
    case 's':
      setMotor(0, 0);
      respond(">> Stopped");
      break;
    case 'e':
      digitalWrite(STBY, HIGH);
      respond(">> Driver enabled");
      break;
    case 'd':
      digitalWrite(STBY, LOW);
      setMotor(0, 0);
      respond(">> Driver disabled");
      break;
    default:
      respond(">> Unknown: " + input);
      break;
  }
}

// ── BLE callbacks ──
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* s) override {
    deviceConnected = true;
    Serial.println("[BLE] Client connected");
  }
  void onDisconnect(BLEServer* s) override {
    deviceConnected = false;
    Serial.println("[BLE] Client disconnected");
    setMotor(0, 0);
    Serial.println("[BLE] Motor stopped (safety)");
  }
};

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* pChar) override {
    String val = pChar->getValue().c_str();
    Serial.print("[BLE RX] ");
    Serial.println(val);
    handleCommand(val);
  }
};

void setup() {
  Serial.begin(115200);
  delay(2000);

  // Motor pins
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(STBY, OUTPUT);
  pinMode(PWMA, OUTPUT);
  digitalWrite(STBY, HIGH);

  // BLE init
  BLEDevice::init("MarsRover");
  BLEDevice::setMTU(517);
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  BLEService* pService = pServer->createService(SERVICE_UUID);

  pTxChar = pService->createCharacteristic(
    CHAR_TX_UUID,
    BLECharacteristic::PROPERTY_NOTIFY
  );
  pTxChar->addDescriptor(new BLE2902());

  BLECharacteristic* pRxChar = pService->createCharacteristic(
    CHAR_RX_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  pRxChar->setCallbacks(new RxCallbacks());

  pService->start();

  BLEAdvertising* pAdv = BLEDevice::getAdvertising();
  pAdv->addServiceUUID(SERVICE_UUID);
  pAdv->setScanResponse(true);
  pAdv->setMinPreferred(0x06);
  pAdv->setMinPreferred(0x12);
  pAdv->start();

  Serial.println("================================");
  Serial.println("  MarsRover BLE Ready");
  Serial.println("  Device: MarsRover");
  Serial.println("  Send: f255 / b150 / s / e / d");
  Serial.println("================================");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    handleCommand(input);
  }

  if (!deviceConnected && oldDeviceConnected) {
    delay(500);
    pServer->startAdvertising();
    Serial.println("[BLE] Advertising restarted");
    oldDeviceConnected = false;
  }
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = true;
  }
}