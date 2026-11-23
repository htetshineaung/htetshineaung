// SSD1306 / SH1106 128x64 OLED over I2C.
#pragma once
#include <stdbool.h>
#include <stdint.h>

bool oled_init(void);                 // false if no display answers at OLED_ADDR
void oled_show(const uint8_t *fb);    // fb: 1024 bytes, page format
void oled_power(bool on);
