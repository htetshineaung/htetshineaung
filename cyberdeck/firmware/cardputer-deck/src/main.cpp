// Cardputer Deck - turns an M5Stack Cardputer into
//   1) a USB HID keyboard for a Raspberry Pi 5, and
//   2) a status / notification screen fed by the Pi over the same USB cable (CDC serial).
//
// Link protocol (one line per message, '|' separated, '\n' terminated):
//   Pi  -> Cardputer  S|host|ip|cpu%|tempC|ram%|disk%|uptime|HH:MM|load
//   Pi  -> Cardputer  N|app|summary|body          (notification)
//   Pi  -> Cardputer  B|0..255                    (backlight)
//   Cardputer -> Pi   K|<mod hex>|<k1 hex>,<k2 hex>..   (UART mode only, HID usage codes)
//
// Keys:  Fn+; . , /  = Up Down Left Right     Fn+`  = Esc        Fn+Del = Delete
//        Fn+1..0     = F1..F10   Fn+- = F11    Fn+= = F12
//        Fn+[ / ]    = Home / End              Fn+' = PageUp     Fn+Enter = PageDown
//        opt = Super/GUI key.   G0 button (top) = next screen page.
//
// Trackball (USB mode): Pimoroni Trackball Breakout (I2C 0x0A) + PCF8574 (0x20) with the L / R
// buttons on P0 / P1, all on the Grove port (G2 = SDA, G1 = SCL) powered by a 3.3 V regulator.
//   roll = move pointer, press ball or L = left click, R = right click, fn + roll = scroll.
//   The trackball LED glows blue for a few seconds when a notification arrives.

#include <Arduino.h>
#include <M5Cardputer.h>
#include "USB.h"
#include "USBHIDKeyboard.h"
#if !DECK_LINK_UART
#include "USBHIDMouse.h"
#include <Wire.h>
#endif

#ifndef DECK_LINK_UART
#define DECK_LINK_UART 0
#endif

static constexpr int UART_RX_PIN = 1;  // Grove G1  <- Pi TX
static constexpr int UART_TX_PIN = 2;  // Grove G2  -> Pi RX
static constexpr uint32_t LINK_BAUD = 115200;
static constexpr uint32_t OFFLINE_MS = 8000;
static constexpr uint32_t TOAST_MS = 6000;
static constexpr uint32_t DIM_AFTER_MS = 120000;

USBHIDKeyboard Keyboard;
bool fnHeld = false;
static void wake();
Stream *piLink = nullptr;
M5Canvas canvas(&M5Cardputer.Display);

// ---------------------------------------------------------------- state
struct Status {
  String host = "-", ip = "-", uptime = "-", clock = "--:--", load = "-";
  int cpu = 0, ram = 0, disk = 0;
  float temp = 0;
} st;

struct Note { String app, summary, body; uint32_t at; };
static constexpr int NOTE_MAX = 6;
Note notes[NOTE_MAX];
int noteCount = 0;          // total received (ring index = count % NOTE_MAX)
uint32_t lastStatusMs = 0, toastUntil = 0, lastActivity = 0;
uint8_t brightness = 160;
bool dimmed = false;
int page = 0;               // 0 status, 1 notifications, 2 key help
static constexpr int PAGES = 3;
bool dirty = true;

// ---------------------------------------------------------------- keyboard
// HID usage IDs
enum : uint8_t {
  H_1 = 0x1E, H_0 = 0x27, H_ENTER = 0x28, H_ESC = 0x29, H_BKSP = 0x2A, H_MINUS = 0x2D,
  H_EQUAL = 0x2E, H_LBRACE = 0x2F, H_RBRACE = 0x30, H_SEMI = 0x33, H_QUOTE = 0x34,
  H_GRAVE = 0x35, H_COMMA = 0x36, H_DOT = 0x37, H_SLASH = 0x38, H_F1 = 0x3A, H_F11 = 0x44,
  H_F12 = 0x45, H_HOME = 0x4A, H_PGUP = 0x4B, H_DEL = 0x4C, H_END = 0x4D, H_PGDN = 0x4E,
  H_RIGHT = 0x4F, H_LEFT = 0x50, H_DOWN = 0x51, H_UP = 0x52,
};

static uint8_t fnLayer(uint8_t k) {
  if (k >= H_1 && k <= H_0) return H_F1 + (k - H_1);  // 1..0 -> F1..F10
  switch (k) {
    case H_SEMI:   return H_UP;
    case H_DOT:    return H_DOWN;
    case H_COMMA:  return H_LEFT;
    case H_SLASH:  return H_RIGHT;
    case H_GRAVE:  return H_ESC;
    case H_BKSP:   return H_DEL;
    case H_MINUS:  return H_F11;
    case H_EQUAL:  return H_F12;
    case H_LBRACE: return H_HOME;
    case H_RBRACE: return H_END;
    case H_QUOTE:  return H_PGUP;
    case H_ENTER:  return H_PGDN;
    default:       return k;
  }
}

static void sendKeys(uint8_t mods, const uint8_t keys[6]) {
#if DECK_LINK_UART
  char buf[48];
  int n = snprintf(buf, sizeof(buf), "K|%02X|", mods);
  bool first = true;
  for (int i = 0; i < 6; i++) {
    if (!keys[i]) continue;
    n += snprintf(buf + n, sizeof(buf) - n, first ? "%02X" : ",%02X", keys[i]);
    first = false;
  }
  piLink->print(buf);
  piLink->print('\n');
#else
  KeyReport r = {};
  r.modifiers = mods;
  memcpy(r.keys, keys, 6);
  Keyboard.sendReport(&r);
#endif
}

static void pollKeyboard() {
  if (!M5Cardputer.Keyboard.isChange()) return;
  uint8_t keys[6] = {0};
  uint8_t mods = 0;
  if (M5Cardputer.Keyboard.isPressed()) {
    auto &ks = M5Cardputer.Keyboard.keysState();
    if (ks.ctrl)  mods |= 0x01;  // L-Ctrl
    if (ks.shift) mods |= 0x02;  // L-Shift
    if (ks.alt)   mods |= 0x04;  // L-Alt
    if (ks.opt)   mods |= 0x08;  // L-GUI (Super)
    int n = 0;
    for (uint8_t k : ks.hid_keys) {
      if (n >= 6) break;
      keys[n++] = ks.fn ? fnLayer(k) : k;
    }
  }
  sendKeys(mods, keys);
  fnHeld = M5Cardputer.Keyboard.isPressed() && M5Cardputer.Keyboard.keysState().fn;
  wake();
}

// ---------------------------------------------------------------- trackball + L/R buttons
#if !DECK_LINK_UART
USBHIDMouse Mouse;
static constexpr int I2C_SDA = 2, I2C_SCL = 1;           // Grove G2 / G1
static constexpr uint8_t TB_ADDR = 0x0A, PCF_ADDR = 0x20;
static constexpr uint8_t TB_REG_LED = 0x00, TB_REG_LEFT = 0x04;   // LEFT,RIGHT,UP,DOWN,SWITCH
static constexpr uint8_t TB_SWITCH_STATE = 0x80;
static constexpr bool TB_SWAP_XY = false, TB_INVERT_X = false, TB_INVERT_Y = false;  // mounting fixes
bool tbPresent = false, pcfPresent = false;
uint8_t mouseButtons = 0;
uint32_t ledUntil = 0;
float scrollAcc = 0;

static bool i2cPresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

static void tbLed(uint8_t r, uint8_t g, uint8_t b, uint8_t w) {
  if (!tbPresent) return;
  Wire.beginTransmission(TB_ADDR);
  Wire.write(TB_REG_LED);
  Wire.write(r); Wire.write(g); Wire.write(b); Wire.write(w);
  Wire.endTransmission();
}

static void pointerInit() {
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
  tbPresent = i2cPresent(TB_ADDR);
  pcfPresent = i2cPresent(PCF_ADDR);
  if (pcfPresent) {                       // PCF8574: write 1s = inputs with weak pull-ups
    Wire.beginTransmission(PCF_ADDR);
    Wire.write(0xFF);
    Wire.endTransmission();
  }
  tbLed(0, 0, 0, 8);                      // faint white "on" glow
}

static int8_t accel(int v) {
  int out = v * (abs(v) > 3 ? 4 : 2);
  return (int8_t)constrain(out, -127, 127);
}

static void pollPointer() {
  static uint32_t last = 0;
  if (millis() - last < 8) return;        // ~125 Hz
  last = millis();

  int dx = 0, dy = 0;
  uint8_t buttons = 0;
  if (tbPresent) {
    Wire.beginTransmission(TB_ADDR);
    Wire.write(TB_REG_LEFT);
    if (Wire.endTransmission(false) == 0 && Wire.requestFrom((int)TB_ADDR, 5) == 5) {
      uint8_t d[5];
      for (int i = 0; i < 5; i++) d[i] = Wire.read();
      dx = (int)d[1] - (int)d[0];         // right - left
      dy = (int)d[3] - (int)d[2];         // down - up
      if (d[4] & TB_SWITCH_STATE) buttons |= MOUSE_LEFT;
    }
    if (TB_SWAP_XY) { int t = dx; dx = dy; dy = t; }
    if (TB_INVERT_X) dx = -dx;
    if (TB_INVERT_Y) dy = -dy;
  }
  if (pcfPresent && Wire.requestFrom((int)PCF_ADDR, 1) == 1) {
    uint8_t p = Wire.read();              // buttons pull P0/P1 to GND
    if (!(p & 0x01)) buttons |= MOUSE_LEFT;
    if (!(p & 0x02)) buttons |= MOUSE_RIGHT;
  }

  if (dx || dy) {
    if (fnHeld) {                         // fn + roll = scroll
      scrollAcc += -dy * 0.5f;
      int8_t w = (int8_t)scrollAcc;
      scrollAcc -= w;
      if (w) Mouse.move(0, 0, w);
    } else {
      Mouse.move(accel(dx), accel(dy));
    }
  }
  for (uint8_t b : {(uint8_t)MOUSE_LEFT, (uint8_t)MOUSE_RIGHT}) {
    if ((buttons & b) != (mouseButtons & b)) (buttons & b) ? Mouse.press(b) : Mouse.release(b);
  }
  mouseButtons = buttons;
  if (dx || dy || buttons) wake();

  if (ledUntil && millis() > ledUntil) { ledUntil = 0; tbLed(0, 0, 0, 8); }
}
#endif

static void wake() {
  lastActivity = millis();
  if (dimmed) { dimmed = false; M5Cardputer.Display.setBrightness(brightness); }
}

// ---------------------------------------------------------------- piLink parser
static int splitFields(const String &line, String out[], int max) {
  int n = 0, start = 0;
  while (n < max) {
    int bar = line.indexOf('|', start);
    if (bar < 0) { out[n++] = line.substring(start); break; }
    out[n++] = line.substring(start, bar);
    start = bar + 1;
  }
  return n;
}

static void handleLine(const String &line) {
  String f[10];
  int n = splitFields(line, f, 10);
  if (n < 1 || f[0].length() != 1) return;
  switch (f[0][0]) {
    case 'S':
      if (n < 9) return;
      st.host = f[1]; st.ip = f[2]; st.cpu = f[3].toInt(); st.temp = f[4].toFloat();
      st.ram = f[5].toInt(); st.disk = f[6].toInt(); st.uptime = f[7]; st.clock = f[8];
      st.load = n > 9 ? f[9] : "-";
      lastStatusMs = millis();
      break;
    case 'N': {
      if (n < 3) return;
      Note &nt = notes[noteCount % NOTE_MAX];
      nt.app = f[1]; nt.summary = f[2]; nt.body = n > 3 ? f[3] : ""; nt.at = millis();
      noteCount++;
      toastUntil = millis() + TOAST_MS;
      lastActivity = millis();
      if (dimmed) { dimmed = false; M5Cardputer.Display.setBrightness(brightness); }
      M5Cardputer.Speaker.tone(2200, 60);
#if !DECK_LINK_UART
      tbLed(0, 60, 255, 0);
      ledUntil = millis() + 4000;
#endif
      break;
    }
    case 'B':
      if (n < 2) return;
      brightness = constrain(f[1].toInt(), 0, 255);
      M5Cardputer.Display.setBrightness(brightness);
      break;
  }
  dirty = true;
}

static void pollLink() {
  static String buf;
  while (piLink->available()) {
    char c = (char)piLink->read();
    if (c == '\n') { buf.trim(); if (buf.length()) handleLine(buf); buf = ""; }
    else if (c != '\r' && buf.length() < 300) buf += c;
  }
}

// ---------------------------------------------------------------- drawing
static const uint16_t C_BG = 0x0841, C_FG = TFT_WHITE, C_DIM = 0x8410, C_ACC = 0x07FF,
                      C_OK = 0x07E0, C_WARN = 0xFD20, C_BAD = 0xF800;

static uint16_t levelColor(int pct) { return pct < 60 ? C_OK : pct < 85 ? C_WARN : C_BAD; }

static void bar(int x, int y, int w, int h, int pct, uint16_t col) {
  pct = constrain(pct, 0, 100);
  canvas.drawRect(x, y, w, h, C_DIM);
  canvas.fillRect(x + 1, y + 1, (w - 2) * pct / 100, h - 2, col);
}

static void row(int y, const char *label, int pct, const String &txt) {
  canvas.setTextColor(C_DIM);
  canvas.drawString(label, 4, y);
  bar(42, y + 1, 130, 10, pct, levelColor(pct));
  canvas.setTextColor(C_FG);
  canvas.drawString(txt, 178, y);
}

static void drawTopBar(bool online) {
  canvas.fillRect(0, 0, 240, 18, 0x18E3);
  canvas.setTextColor(C_ACC);
  canvas.drawString(st.host, 4, 2);
  canvas.setTextColor(C_FG);
  canvas.drawRightString(st.clock, 200, 2);
  int batt = M5.Power.getBatteryLevel();
  canvas.setTextColor(batt < 20 ? C_BAD : C_DIM);
  canvas.drawRightString(String(batt) + "%", 236, 2);
  canvas.fillCircle(116, 9, 4, online ? C_OK : C_BAD);
}

static void drawStatus(bool online) {
  if (!online) {
    canvas.setTextColor(C_WARN);
    canvas.drawCentreString("Waiting for Pi...", 120, 50);
    canvas.setTextColor(C_DIM);
    canvas.drawCentreString("keyboard is active", 120, 72);
    return;
  }
  row(24, "CPU", st.cpu, String(st.cpu) + "%");
  int tPct = (int)((st.temp - 30) * 100 / 55);  // 30C..85C
  row(42, "TEMP", tPct, String(st.temp, 0) + "C");
  row(60, "RAM", st.ram, String(st.ram) + "%");
  row(78, "DISK", st.disk, String(st.disk) + "%");
  canvas.setTextColor(C_DIM);
  canvas.drawString("IP", 4, 98);   canvas.drawString("UP", 4, 116);
  canvas.setTextColor(C_FG);
  canvas.drawString(st.ip, 42, 98);
  canvas.drawString(st.uptime + "  ld " + st.load, 42, 116);
}

static void drawNotes() {
  if (!noteCount) { canvas.setTextColor(C_DIM); canvas.drawCentreString("No notifications", 120, 60); return; }
  int shown = min(noteCount, 4);
  for (int i = 0; i < shown; i++) {
    const Note &nt = notes[(noteCount - 1 - i) % NOTE_MAX];
    int y = 22 + i * 28;
    canvas.setTextColor(C_ACC);
    canvas.drawString(nt.app.substring(0, 12), 4, y);
    uint32_t age = (millis() - nt.at) / 60000;
    canvas.setTextColor(C_DIM);
    canvas.drawRightString(String(age) + "m", 236, y);
    canvas.setTextColor(C_FG);
    canvas.drawString(nt.summary.substring(0, 28), 4, y + 13);
  }
}

static void drawHelp() {
  canvas.setTextColor(C_ACC);
  canvas.drawString("Fn layer", 4, 22);
  canvas.setTextColor(C_FG);
  const char *lines[] = {"; . , /   arrows      `  Esc", "1..0 F1-F10  - F11  = F12",
                         "[ ] Home/End   ' PgUp  Ent PgDn", "Del Delete     opt = Super",
                         "ball/L click  R right  fn+ball scroll", "G0 button: next page"};
  for (int i = 0; i < 6; i++) canvas.drawString(lines[i], 4, 38 + i * 16);
}

static void drawToast() {
  const Note &nt = notes[(noteCount - 1) % NOTE_MAX];
  canvas.fillRoundRect(6, 26, 228, 102, 6, 0x2124);
  canvas.drawRoundRect(6, 26, 228, 102, 6, C_ACC);
  canvas.setTextColor(C_ACC);
  canvas.drawString(nt.app.substring(0, 26), 14, 32);
  canvas.setTextColor(C_FG);
  canvas.drawString(nt.summary.substring(0, 26), 14, 52);
  canvas.setTextColor(C_DIM);
  // naive wrap of the body over 3 lines
  for (int i = 0; i < 3; i++) canvas.drawString(nt.body.substring(i * 30, i * 30 + 30), 14, 74 + i * 16);
}

static void render() {
  bool online = millis() - lastStatusMs < OFFLINE_MS && lastStatusMs != 0;
  canvas.fillSprite(C_BG);
  canvas.setFont(&fonts::Font2);
  canvas.setTextSize(1);
  drawTopBar(online);
  if (millis() < toastUntil && noteCount) drawToast();
  else if (page == 0) drawStatus(online);
  else if (page == 1) drawNotes();
  else drawHelp();
  canvas.pushSprite(0, 0);
}

// ---------------------------------------------------------------- main
void setup() {
  auto cfg = M5.config();
  M5Cardputer.begin(cfg, true);  // true = enable keyboard scanning
  M5Cardputer.Display.setRotation(1);
  M5Cardputer.Display.setBrightness(brightness);
  canvas.createSprite(240, 135);

#if DECK_LINK_UART
  Serial1.begin(LINK_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
  piLink = &Serial1;
  USB.productName("Cardputer Deck");
  USB.begin();
  Serial.begin(115200);  // debug only
#else
  USB.manufacturerName("M5Stack");
  USB.productName("Cardputer Deck");
  Keyboard.begin();
  Mouse.begin();
  USB.begin();
  pointerInit();
  Serial.begin(LINK_BAUD);
  piLink = &Serial;
#endif
  lastActivity = millis();
}

void loop() {
  M5Cardputer.update();
  pollKeyboard();
#if !DECK_LINK_UART
  pollPointer();
#endif
  pollLink();

  if (M5Cardputer.BtnA.wasPressed()) {
    page = (page + 1) % PAGES;
    toastUntil = 0;
    wake();
    dirty = true;
  }
  if (!dimmed && millis() - lastActivity > DIM_AFTER_MS) {
    dimmed = true;
    M5Cardputer.Display.setBrightness(20);
  }

  static uint32_t lastDraw = 0;
  if (dirty || millis() - lastDraw > 500) {
    render();
    lastDraw = millis();
    dirty = false;
  }
  delay(5);
}
