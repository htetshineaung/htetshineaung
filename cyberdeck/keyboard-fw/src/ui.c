#include "ui.h"

#include <stdio.h>
#include <string.h>

#include "font5x7.h"

static void px(uint8_t *fb, int x, int y, bool on) {
    if (x < 0 || x >= UI_W || y < 0 || y >= UI_H) return;
    uint8_t m = (uint8_t)(1u << (y & 7));
    if (on) fb[(y >> 3) * UI_W + x] |= m;
    else fb[(y >> 3) * UI_W + x] &= (uint8_t)~m;
}

static void hline(uint8_t *fb, int x0, int x1, int y) { for (int x = x0; x <= x1; x++) px(fb, x, y, true); }
static void vline(uint8_t *fb, int x, int y0, int y1) { for (int y = y0; y <= y1; y++) px(fb, x, y, true); }

void ui_clear(uint8_t *fb) { memset(fb, 0, UI_W * UI_H / 8); }

static int glyph(uint8_t *fb, int x, int y, char c) {
    if (c < 0x20 || c > 0x7E) c = '?';
    const uint8_t *g = font5x7[c - 0x20];
    for (int col = 0; col < 5; col++)
        for (int row = 0; row < 7; row++)
            if (g[col] & (1 << row)) px(fb, x + col, y + row, true);
    return x + 6;
}

void ui_text(uint8_t *fb, int x, int y, const char *s) {
    while (*s) x = glyph(fb, x, y, *s++);
}

static int text_w(const char *s) { return (int)strlen(s) * 6; }

static void battery_icon(uint8_t *fb, int x, int y, uint8_t pc) {
    hline(fb, x, x + 16, y); hline(fb, x, x + 16, y + 7);
    vline(fb, x, y, y + 7); vline(fb, x + 16, y, y + 7);
    vline(fb, x + 17, y + 2, y + 5); vline(fb, x + 18, y + 2, y + 5);
    int fill = pc * 14 / 100;
    for (int i = 0; i < fill; i++) vline(fb, x + 2 + i, y + 2, y + 5);
}

void ui_render(uint8_t *fb, const ui_state_t *s) {
    char buf[48];
    ui_clear(fb);

    // header: battery, percent, fn / caps flags, clock from the Pi
    battery_icon(fb, 0, 0, s->batt_pc);
    snprintf(buf, sizeof buf, "%u%%", s->batt_pc);
    ui_text(fb, 22, 0, buf);
    int x = 22 + text_w(buf) + 6;
    if (s->fn) { ui_text(fb, x, 0, "FN"); x += 15; }
    if (s->caps) ui_text(fb, x, 0, "CAPS");
    if (s->link && s->line[0][0]) ui_text(fb, UI_W - text_w(s->line[0]), 0, s->line[0]);
    hline(fb, 0, UI_W - 1, 10);

    if (!s->link) {
        ui_text(fb, 0, 15, "Pi offline");
        snprintf(buf, sizeof buf, "Battery %u.%02u V", s->batt_mv / 1000, (s->batt_mv % 1000) / 10);
        ui_text(fb, 0, 26, buf);
        ui_text(fb, 0, 37, "Waiting for the Pi");
        return;
    }
    for (int i = 1; i <= 3; i++) ui_text(fb, 0, 15 + (i - 1) * 11, s->line[i]);

    // notification: scrolls when longer than the screen
    const char *n = s->line[4];
    if (*n) {
        hline(fb, 0, UI_W - 1, 50);
        int w = text_w(n);
        if (w <= UI_W) ui_text(fb, 0, 55, n);
        else {
            int period = w + 40;                          // text + gap, in pixels
            int off = (int)((s->ms / 40) % (uint32_t)period);
            ui_text(fb, -off, 55, n);
            ui_text(fb, -off + period, 55, n);
        }
    }
}
