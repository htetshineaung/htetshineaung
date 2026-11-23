#include "motion.h"

#include <math.h>
#include <string.h>

#include "config.h"

void tb_init(tb_state_t *s) { memset(s, 0, sizeof *s); }

static int8_t clamp8(float v) {
    if (v > 127.0f) return 127;
    if (v < -127.0f) return -127;
    return (int8_t)v;
}

tb_motion_t tb_step(tb_state_t *s, int up, int down, int left, int right, bool scroll) {
    tb_motion_t m = {0, 0, 0, 0};
    int x = right - left, y = down - up;            // screen y grows downwards
    if (scroll) {
        s->rx = s->ry = 0;
        s->wx += x;
        s->wy += y;
        int notches_y = s->wy / TB_SCROLL_DIV, notches_x = s->wx / TB_SCROLL_DIV;
        s->wy -= notches_y * TB_SCROLL_DIV;
        s->wx -= notches_x * TB_SCROLL_DIV;
        m.wheel = clamp8((float)-notches_y);         // roll up = scroll up (positive wheel)
        m.pan = clamp8((float)notches_x);
        return m;
    }
    s->wx = s->wy = 0;
    if (x == 0 && y == 0) { s->rx = s->ry = 0; return m; }
    float speed = sqrtf((float)(x * x + y * y));
    float f = TB_GAIN * (1.0f + TB_ACCEL * speed);
    if (f > TB_MAX_FACTOR) f = TB_MAX_FACTOR;
    float fx = x * f + s->rx, fy = y * f + s->ry;
    m.dx = clamp8(fx);
    m.dy = clamp8(fy);
    s->rx = fx - m.dx;                              // keep the fraction for the next period
    s->ry = fy - m.dy;
    return m;
}

uint16_t batt_mv_from_adc(uint16_t raw) {
    uint32_t vadc = (uint32_t)raw * ADC_VREF_MV / 4095u;
    return (uint16_t)(vadc * VBAT_DIV_NUM / VBAT_DIV_DEN);
}

// per-cell resting voltage (mV) -> percent
static const uint16_t cell_mv[] = {3300, 3500, 3600, 3700, 3750, 3800, 3850, 3900, 3950, 4000, 4100, 4200};
static const uint8_t cell_pc[] = {0, 5, 10, 22, 35, 47, 57, 66, 75, 83, 93, 100};

uint8_t batt_percent(uint16_t mv) {
    uint16_t cell = mv / 2;
    const int n = sizeof cell_mv / sizeof cell_mv[0];
    if (cell <= cell_mv[0]) return 0;
    if (cell >= cell_mv[n - 1]) return 100;
    for (int i = 1; i < n; i++) {
        if (cell <= cell_mv[i]) {
            uint32_t span = cell_mv[i] - cell_mv[i - 1];
            uint32_t pos = cell - cell_mv[i - 1];
            return (uint8_t)(cell_pc[i - 1] + (cell_pc[i] - cell_pc[i - 1]) * pos / span);
        }
    }
    return 100;
}
