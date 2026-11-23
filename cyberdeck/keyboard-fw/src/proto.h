// Link protocol between the keyboard (RP2040) and the Pi 5.
//
// Frame:  0xA5 | type | len | payload[len] | crc8(type, len, payload)   (CRC-8, poly 0x07, init 0)
// Same definition in cyberdeck/clamshell-pi/clamkbd.py.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PROTO_SYNC       0xA5
#define PROTO_MAX_LEN    64
#define PROTO_VERSION    1

// keyboard -> Pi
#define F_KEY    0x01   // usage(u8 HID), down(u8)
#define F_MOUSE  0x02   // dx(i8) dy(i8) wheel(i8) pan(i8) buttons(u8: 1 L, 2 R, 4 M)
#define F_BATT   0x03   // mv(u16 LE) percent(u8)
#define F_HELLO  0x04   // proto(u8) fw_major(u8) fw_minor(u8)
#define F_STATE  0x05   // buttons(u8) then the HID usages held right now (0..16 bytes)
// Pi -> keyboard
#define F_LINE   0x10   // index(u8 0..4) text(ascii, up to 40)
#define F_LEDS   0x11   // bit0 caps lock
#define F_PING   0x12   // (empty) heartbeat; keyboard answers with F_HELLO
#define F_OLED   0x13   // on(u8)
#define F_BOOT   0x14   // (empty) reboot into the USB bootloader

uint8_t proto_crc8(const uint8_t *data, size_t n);
// Writes a frame into out (needs len + 4 bytes). Returns the frame length.
size_t proto_encode(uint8_t *out, uint8_t type, const uint8_t *payload, uint8_t len);

typedef struct {
    uint8_t state, type, len, idx;
    uint8_t buf[PROTO_MAX_LEN];
    uint32_t bad;                 // frames dropped (bad CRC / length)
} proto_rx_t;

void proto_rx_init(proto_rx_t *rx);
// Feed one received byte. Returns true when rx->type / rx->len / rx->buf hold a complete valid frame.
bool proto_feed(proto_rx_t *rx, uint8_t byte);
