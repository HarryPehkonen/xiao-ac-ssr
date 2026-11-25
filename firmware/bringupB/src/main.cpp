// bringupB — hold, flip or blink the board's GATE_DRV pin so BRINGUP section B can be measured.
//
// GATE_DRV is the XIAO's D1 = GPIO3 on J1 pad 2, and it feeds R3 (150 ohm) into the MOC3063's
// LED.  With no firmware loaded, GPIO3 is an unconfigured input: it drives nothing, so a meter
// across R3 reads ~0 V and B1 cannot pass.  This sketch gives you a state you can command and
// hold, so the measurement is a static number rather than a race with a blinking pin.
//
// Deliberately absent: WiFi, Bluetooth, ESP-NOW.  The radio draws ~250 mA bursts in the same
// ground system as a 12 mA measurement; turn it on later, not while verifying the drive path.
//
// Controls
//   BOOT button (D9/GPIO9)  short press cycles BLINK -> HOLD_ON -> HOLD_OFF
//   serial console          1 = hold on, 0 = hold off, b = blink, s = status
//
// Fail-safe: GPIO3 is driven LOW in setup(), before the console and before any delay, so a
// reset can never leave the load energised (BRINGUP section E, row 1).

#include <Arduino.h>

static const uint8_t PIN_GATE = D1;  // GPIO3 — the board's GATE_DRV net
static const uint8_t PIN_BOOT = D9;  // GPIO9 — BOOT button, 10k pull-up on the module

static const uint32_t BLINK_MS = 1000;  // 1 s on / 1 s off: slow enough for a DMM to settle
static const uint32_t DEBOUNCE_MS = 50;

enum Mode : uint8_t { MODE_BLINK, MODE_ON, MODE_OFF };

static Mode mode = MODE_BLINK;
static bool gateHigh = false;
static uint32_t lastToggle = 0;
static uint32_t lastButtonChange = 0;
static bool lastButtonLevel = HIGH;

static const char *modeName(Mode m) {
  switch (m) {
    case MODE_ON:  return "HOLD_ON";
    case MODE_OFF: return "HOLD_OFF";
    default:       return "BLINK";
  }
}

static void driveGate(bool high) {
  gateHigh = high;
  digitalWrite(PIN_GATE, high ? HIGH : LOW);
}

// Print the state and the number the meter should show for it.
static void report(const char *why) {
  Serial.printf("\n[%lu ms] %s\n", (unsigned long)millis(), why);
  Serial.printf("  mode      : %s\n", modeName(mode));
  Serial.printf("  GATE_DRV  : %s (D1 / GPIO3, J1 pad 2)\n", gateHigh ? "HIGH" : "low");
  if (gateHigh) {
    Serial.println("  expect    : ~1.8-2.1 V across R3  ->  ~12-14 mA into the opto LED");
    Serial.println("              (red probe on R3 pad 1, the GATE_DRV end - the lower of the two pads)");
  } else {
    Serial.println("  expect    : ~0 V across R3  ->  no LED current");
  }
}

static void setMode(Mode m) {
  mode = m;
  if (m == MODE_ON) {
    driveGate(true);
  } else if (m == MODE_OFF) {
    driveGate(false);
  } else {
    lastToggle = millis();
    driveGate(true);  // start BLINK in the visible half
  }
  report("mode changed");
}

static void nextMode() { setMode((Mode)((mode + 1) % 3)); }

static void pollButton() {
  const bool level = digitalRead(PIN_BOOT);
  if (level != lastButtonLevel && (millis() - lastButtonChange) > DEBOUNCE_MS) {
    lastButtonChange = millis();
    lastButtonLevel = level;
    if (level == LOW) nextMode();  // press = pulled to ground
  }
}

static void pollSerial() {
  while (Serial.available()) {
    const char c = (char)Serial.read();
    switch (c) {
      case '1': setMode(MODE_ON);  break;
      case '0': setMode(MODE_OFF); break;
      case 'b': setMode(MODE_BLINK); break;
      case 's': report("status"); break;
      default: break;
    }
  }
}

void setup() {
  // Fail-safe first, before anything else can run.
  pinMode(PIN_GATE, OUTPUT);
  digitalWrite(PIN_GATE, LOW);

  pinMode(PIN_BOOT, INPUT_PULLUP);

  Serial.begin(115200);
  delay(200);  // let the USB CDC enumerate before the first print

  Serial.println();
  Serial.println("bringupB — xiao-ac-ssr, BRINGUP section B (logic side, mains disconnected)");
  Serial.println("  GATE_DRV = D1 = GPIO3, J1 pad 2, through R3 (150 ohm) into the MOC3063 LED");
  Serial.println("  commands: 1 = hold on, 0 = hold off, b = blink, s = status   (BOOT button cycles)");
  report("booted: GPIO3 driven low before anything else");

  setMode(MODE_BLINK);
  lastButtonLevel = digitalRead(PIN_BOOT);
}

void loop() {
  pollButton();
  pollSerial();

  if (mode == MODE_BLINK && (millis() - lastToggle) >= BLINK_MS) {
    lastToggle = millis();
    driveGate(!gateHigh);
    if (gateHigh) {
      Serial.println("  BLINK: GATE_DRV high -> expect ~1.8-2.1 V across R3");
    } else {
      Serial.println("  BLINK: GATE_DRV low  -> expect ~0 V across R3");
    }
  }
}
