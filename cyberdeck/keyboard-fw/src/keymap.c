#include "keymap.h"

#include <string.h>

#include "hid.h"

#define K(u)   {u, 0}
#define S(u)   {u, A_SHIFT}
#define FN     {0, A_FN}
#define MB(b)  {b, A_MOUSE}
#define __     {0, 0}

// Matrix positions follow circuit.py: row 0 is the top row of keys (q ... backspace),
// column 11 holds the L / R mouse keys next to the trackball.
const action_t keymap_base[MATRIX_ROWS][MATRIX_COLS] = {
    {K(K_Q), K(K_W), K(K_E), K(K_R), K(K_T), K(K_Y), K(K_U), K(K_I), K(K_O), K(K_P), K(K_BSPC), MB(1)},
    {K(K_A), K(K_S), K(K_D), K(K_F), K(K_G), K(K_H), K(K_J), K(K_K), K(K_L), K(K_SCLN), K(K_ENTER), MB(2)},
    {K(K_LSFT), K(K_Z), K(K_X), K(K_C), K(K_V), K(K_B), K(K_N), K(K_M), K(K_COMM), K(K_DOT), K(K_SLSH), __},
    {K(K_LCTL), K(K_LALT), FN, K(K_TAB), K(K_SPACE), __, __, K(K_QUOT), K(K_MINUS), K(K_EQUAL), K(K_ESC), __},
};

// fn layer (as printed on the key mat): numbers, symbols, arrows, page keys
const action_t keymap_fn[MATRIX_ROWS][MATRIX_COLS] = {
    {K(K_1), K(K_2), K(K_3), K(K_4), K(K_5), K(K_6), K(K_7), K(K_8), K(K_9), K(K_0), K(K_DEL), MB(4)},
    {S(K_1), S(K_2), S(K_3), S(K_4), S(K_5), S(K_6), K(K_LEFT), K(K_DOWN), K(K_RIGHT), K(K_UP), K(K_PGDN), MB(2)},
    {K(K_CAPS), S(K_7), S(K_8), S(K_9), S(K_0), K(K_LBRC), K(K_RBRC), S(K_LBRC), S(K_RBRC), S(K_BSLS), K(K_BSLS), __},
    {K(K_LCTL), K(K_LALT), FN, S(K_GRV), K(K_PGUP), __, __, K(K_GRV), S(K_MINUS), S(K_EQUAL), K(K_LGUI), __},
};

static action_t held[MATRIX_ROWS][MATRIX_COLS];   // action latched at press time
static bool is_down[MATRIX_ROWS][MATRIX_COLS];
static uint8_t usage_count[256];                  // how many sources hold each usage
static int fn_count, shift_phys, shift_synth;
static uint8_t btn_count[3];

void kb_init(void) {
    memset(held, 0, sizeof held);
    memset(is_down, 0, sizeof is_down);
    memset(usage_count, 0, sizeof usage_count);
    fn_count = shift_phys = shift_synth = 0;
    memset(btn_count, 0, sizeof btn_count);
}

static void usage_change(uint8_t u, bool down, const kb_out_t *out) {
    if (!u) return;
    if (down) {
        if (usage_count[u]++ == 0 && out && out->key) out->key(out->ctx, u, true);
    } else if (usage_count[u]) {
        if (--usage_count[u] == 0 && out && out->key) out->key(out->ctx, u, false);
    }
}

// Left shift is shared by the physical shift key and the shifted fn symbols.
static void shift_change(bool phys, bool down, const kb_out_t *out) {
    int before = shift_phys + shift_synth;
    if (phys) shift_phys += down ? 1 : -1;
    else shift_synth += down ? 1 : -1;
    int after = shift_phys + shift_synth;
    if (before == 0 && after > 0) usage_change(K_LSFT, true, out);
    if (before > 0 && after == 0) usage_change(K_LSFT, false, out);
}

static uint8_t btn_mask(void) {
    return (uint8_t)((btn_count[0] ? 1 : 0) | (btn_count[1] ? 2 : 0) | (btn_count[2] ? 4 : 0));
}

static void apply(action_t a, bool down, const kb_out_t *out) {
    if (a.flags & A_FN) { fn_count += down ? 1 : -1; return; }
    if (a.flags & A_MOUSE) {
        for (int b = 0; b < 3; b++)
            if (a.usage & (1 << b)) btn_count[b] += down ? 1 : -1;
        if (out && out->buttons) out->buttons(out->ctx, btn_mask());
        return;
    }
    if (a.usage == K_LSFT) { shift_change(true, down, out); return; }
    if (down) {
        if (a.flags & A_SHIFT) shift_change(false, true, out);
        usage_change(a.usage, true, out);
    } else {
        usage_change(a.usage, false, out);
        if (a.flags & A_SHIFT) shift_change(false, false, out);
    }
}

void kb_event(int row, int col, bool down, const kb_out_t *out) {
    if (row < 0 || row >= MATRIX_ROWS || col < 0 || col >= MATRIX_COLS) return;
    if (down == is_down[row][col]) return;
    is_down[row][col] = down;
    if (down) {
        action_t a = (fn_count > 0) ? keymap_fn[row][col] : keymap_base[row][col];
        if (fn_count > 0 && a.usage == 0 && a.flags == 0) a = keymap_base[row][col];
        held[row][col] = a;
        apply(a, true, out);
    } else {
        apply(held[row][col], false, out);       // release exactly what was pressed
        held[row][col] = (action_t){0, 0};
    }
}

void kb_release_all(const kb_out_t *out) {
    for (int r = 0; r < MATRIX_ROWS; r++)
        for (int c = 0; c < MATRIX_COLS; c++)
            if (is_down[r][c]) kb_event(r, c, false, out);
}

bool kb_fn_held(void) { return fn_count > 0; }
uint8_t kb_buttons(void) { return btn_mask(); }

int kb_held_usages(uint8_t *o, int max) {
    int n = 0;
    for (int u = 1; u < 256 && n < max; u++)
        if (usage_count[u]) o[n++] = (uint8_t)u;
    return n;
}
