// Host unit tests for the hardware-free firmware logic.
//   make -C tests        (builds and runs; writes oled_*.pgm previews)
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../src/hid.h"
#include "../src/keymap.h"
#include "../src/motion.h"
#include "../src/proto.h"
#include "../src/ui.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

// ------------------------------------------------------------------ proto
static void test_proto(void) {
    uint8_t buf[80], pl[3] = {0x14, 1, 0};
    size_t n = proto_encode(buf, F_KEY, pl, 2);
    CHECK(n == 6 && buf[0] == 0xA5 && buf[1] == F_KEY && buf[2] == 2);
    CHECK(proto_crc8((const uint8_t *)"123456789", 9) == 0xF4);    // CRC-8/SMBUS check value

    proto_rx_t rx;
    proto_rx_init(&rx);
    // garbage, then a frame, then a corrupted frame, then an empty-payload frame
    uint8_t stream[64];
    size_t k = 0;
    stream[k++] = 0x00; stream[k++] = 0xA5; stream[k++] = 0xFF;      // junk incl. a fake sync with bad length
    k += proto_encode(stream + k, F_KEY, pl, 2);
    size_t bad_at = k;
    k += proto_encode(stream + k, F_BATT, pl, 3);
    stream[bad_at + 4] ^= 0x55;                                     // corrupt payload
    k += proto_encode(stream + k, F_PING, NULL, 0);
    int got = 0, types[4];
    for (size_t i = 0; i < k; i++)
        if (proto_feed(&rx, stream[i])) types[got++] = rx.type;
    CHECK(got == 2 && types[0] == F_KEY && types[1] == F_PING);
    CHECK(rx.bad >= 1);
}

// ------------------------------------------------------------------ keymap
typedef struct { int n; uint8_t u[64]; bool d[64]; uint8_t buttons; } log_t;
static void on_key(void *c, uint8_t u, bool d) { log_t *l = c; l->u[l->n] = u; l->d[l->n++] = d; }
static void on_btn(void *c, uint8_t m) { ((log_t *)c)->buttons = m; }

static void test_keymap(void) {
    log_t L = {0};
    kb_out_t out = {on_key, on_btn, &L};
    kb_init();

    // plain q
    kb_event(0, 0, true, &out); kb_event(0, 0, false, &out);
    CHECK(L.n == 2 && L.u[0] == K_Q && L.d[0] && !L.d[1]);

    // fn + q = 1 ; fn released before q -> still releases "1"
    L.n = 0;
    kb_event(3, 2, true, &out); kb_event(0, 0, true, &out); kb_event(3, 2, false, &out); kb_event(0, 0, false, &out);
    CHECK(L.n == 2 && L.u[0] == K_1 && L.u[1] == K_1 && !L.d[1]);

    // fn + a = "!" -> shift down, 1 down, 1 up, shift up
    L.n = 0;
    kb_event(3, 2, true, &out); kb_event(1, 0, true, &out); kb_event(1, 0, false, &out); kb_event(3, 2, false, &out);
    CHECK(L.n == 4 && L.u[0] == K_LSFT && L.d[0] && L.u[1] == K_1 && L.u[3] == K_LSFT && !L.d[3]);

    // physical shift held across a shifted fn symbol: shift must stay down
    L.n = 0;
    kb_event(2, 0, true, &out);                     // shift
    kb_event(3, 2, true, &out); kb_event(1, 0, true, &out); kb_event(1, 0, false, &out); kb_event(3, 2, false, &out);
    CHECK(L.n == 3 && L.u[0] == K_LSFT && L.d[0] && L.u[1] == K_1 && L.u[2] == K_1);
    kb_event(2, 0, false, &out);
    CHECK(L.n == 4 && L.u[3] == K_LSFT && !L.d[3]);

    // fn + shift = caps lock
    L.n = 0;
    kb_event(3, 2, true, &out); kb_event(2, 0, true, &out); kb_event(2, 0, false, &out); kb_event(3, 2, false, &out);
    CHECK(L.n == 2 && L.u[0] == K_CAPS);

    // mouse keys: L, R, fn+L = middle
    kb_event(0, 11, true, &out); CHECK(L.buttons == 1);
    kb_event(1, 11, true, &out); CHECK(L.buttons == 3);
    kb_event(0, 11, false, &out); kb_event(1, 11, false, &out); CHECK(L.buttons == 0);
    kb_event(3, 2, true, &out); kb_event(0, 11, true, &out); CHECK(L.buttons == 4);
    kb_event(0, 11, false, &out); kb_event(3, 2, false, &out); CHECK(L.buttons == 0);

    // held usages + release_all
    L.n = 0;
    kb_event(3, 0, true, &out); kb_event(0, 1, true, &out);
    uint8_t held[16];
    int h = kb_held_usages(held, 16);
    CHECK(h == 2 && held[0] == K_W && held[1] == K_LCTL);
    kb_release_all(&out);
    CHECK(kb_held_usages(held, 16) == 0);

    // every fn-layer position that is empty falls back to the base key (e.g. none here),
    // and every printed key has an action
    int mapped = 0;
    for (int r = 0; r < MATRIX_ROWS; r++)
        for (int c = 0; c < MATRIX_COLS; c++)
            if (keymap_base[r][c].usage || keymap_base[r][c].flags) mapped++;
    CHECK(mapped == 44);                            // 42 keys + L + R  (fn counted, space once)
}

// ------------------------------------------------------------------ motion + battery
static void test_motion(void) {
    tb_state_t s;
    tb_init(&s);
    tb_motion_t m = tb_step(&s, 0, 0, 0, 1, false);
    CHECK(m.dx > 0 && m.dy == 0);
    m = tb_step(&s, 2, 0, 0, 0, false);
    CHECK(m.dy < 0 && m.dx == 0);
    tb_motion_t slow = tb_step(&s, 0, 0, 0, 1, false), fast = tb_step(&s, 0, 0, 0, 8, false);
    CHECK(fast.dx > 8 * slow.dx);                   // acceleration
    int wheel = 0;
    for (int i = 0; i < 8; i++) wheel += tb_step(&s, 1, 0, 0, 0, true).wheel;
    CHECK(wheel == 8 / TB_SCROLL_DIV);              // roll up = scroll up

    CHECK(batt_percent(8400) == 100 && batt_percent(6600) == 0);
    CHECK(batt_percent(7400) > 15 && batt_percent(7400) < 30);
    CHECK(batt_percent(7900) > batt_percent(7600));
    // 8.4 V on the 100k/33k divider is 2.084 V -> raw ~2587
    uint16_t mv = batt_mv_from_adc(2587);
    CHECK(mv > 8350 && mv < 8450);
}

// ------------------------------------------------------------------ UI preview
static void write_pgm(const char *path, const uint8_t *fb) {
    FILE *f = fopen(path, "wb");
    fprintf(f, "P5 %d %d 255\n", UI_W, UI_H);
    for (int y = 0; y < UI_H; y++)
        for (int x = 0; x < UI_W; x++) fputc((fb[(y >> 3) * UI_W + x] >> (y & 7)) & 1 ? 255 : 0, f);
    fclose(f);
}

static void test_ui(void) {
    static uint8_t fb[UI_W * UI_H / 8];
    ui_state_t s = {.batt_pc = 78, .batt_mv = 7720, .link = true, .fn = false, .caps = false, .ms = 0};
    strcpy(s.line[0], "12:30");
    strcpy(s.line[1], "CPU 41C  12%  RAM 23%");
    strcpy(s.line[2], "home  10.0.0.42");
    strcpy(s.line[3], "~3h05m left");
    strcpy(s.line[4], "Mya: dinner at 7? Bring the charger pls");
    ui_render(fb, &s);
    write_pgm("oled_status.pgm", fb);
    int lit = 0;
    for (int i = 0; i < (int)sizeof fb; i++) lit += fb[i] != 0;
    CHECK(lit > 50);
    s.link = false; s.fn = true; s.caps = true;
    ui_render(fb, &s);
    write_pgm("oled_offline.pgm", fb);
}

int main(void) {
    test_proto();
    test_keymap();
    test_motion();
    test_ui();
    printf(fails ? "%d FAILED\n" : "all host tests passed\n", fails);
    return fails ? 1 : 0;
}
