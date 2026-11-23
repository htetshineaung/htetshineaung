// OLED status screen layout, drawn into a 128 x 64 framebuffer (SSD1306 page format:
// byte = 8 vertical pixels, fb[page * 128 + x]). Pure logic, previewed on the host.
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define UI_W 128
#define UI_H 64
#define UI_LINES 5        // 0 clock (header), 1-3 status lines, 4 notification
#define UI_LINE_MAX 40

typedef struct {
    uint8_t batt_pc;
    uint16_t batt_mv;
    bool link;            // Pi heartbeat seen recently
    bool fn, caps;
    char line[UI_LINES][UI_LINE_MAX + 1];
    uint32_t ms;          // time, drives the notification scroll
} ui_state_t;

void ui_render(uint8_t *fb, const ui_state_t *s);   // fb: UI_W * UI_H / 8 bytes
// low-level helpers (also used by the boot splash)
void ui_clear(uint8_t *fb);
void ui_text(uint8_t *fb, int x, int y, const char *s);
