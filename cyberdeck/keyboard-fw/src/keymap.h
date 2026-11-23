// Key matrix -> HID key events and mouse buttons, with the fn layer.
// Pure logic (no hardware), unit-tested on the host in tests/test_host.c.
#pragma once
#include <stdbool.h>
#include <stdint.h>

#include "config.h"

// action flags
#define A_SHIFT  0x01   // send with shift held (symbols on the fn layer)
#define A_FN     0x02   // the fn key itself
#define A_MOUSE  0x04   // usage = mouse button mask (1 L, 2 R, 4 M)

typedef struct { uint8_t usage, flags; } action_t;

typedef struct {
    void (*key)(void *ctx, uint8_t usage, bool down);   // HID usage pressed / released
    void (*buttons)(void *ctx, uint8_t mask);            // mouse buttons held via keys
    void *ctx;
} kb_out_t;

extern const action_t keymap_base[MATRIX_ROWS][MATRIX_COLS];
extern const action_t keymap_fn[MATRIX_ROWS][MATRIX_COLS];

void kb_init(void);
// A debounced key change at (row, col).
void kb_event(int row, int col, bool down, const kb_out_t *out);
// Release everything (used when the link or USB resets).
void kb_release_all(const kb_out_t *out);
bool kb_fn_held(void);
uint8_t kb_buttons(void);
// HID usages held right now (modifiers included). Returns the count (<= max).
int kb_held_usages(uint8_t *out, int max);
