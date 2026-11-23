// Trackball counts -> pointer / scroll motion, and battery voltage -> percent.
// Pure logic (no hardware), unit-tested on the host.
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct { float rx, ry; int wx, wy; } tb_state_t;
typedef struct { int8_t dx, dy, wheel, pan; } tb_motion_t;

void tb_init(tb_state_t *s);
// Hall edges counted during one report period. scroll = fn held (ball scrolls instead).
tb_motion_t tb_step(tb_state_t *s, int up, int down, int left, int right, bool scroll);

// raw 12-bit ADC reading at the divider -> battery millivolts
uint16_t batt_mv_from_adc(uint16_t raw);
// 2S Li-ion pack voltage -> 0..100 % (resting-voltage curve)
uint8_t batt_percent(uint16_t mv);
