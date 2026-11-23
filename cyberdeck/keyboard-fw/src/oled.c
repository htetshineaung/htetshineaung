#include "oled.h"

#include "config.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"
#include "pico/stdlib.h"

#define OLED_I2C i2c1

static bool present;

static bool cmd(uint8_t c) {
    uint8_t b[2] = {0x00, c};
    return i2c_write_timeout_us(OLED_I2C, OLED_ADDR, b, 2, false, 2000) == 2;
}

bool oled_init(void) {
    i2c_init(OLED_I2C, 400 * 1000);
    gpio_set_function(PIN_I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C_SDA);                    // board has 4.7k pull-ups; harmless
    gpio_pull_up(PIN_I2C_SCL);
    sleep_ms(50);
    static const uint8_t seq[] = {
        0xAE,                    // display off
        0xD5, 0x80,              // clock
        0xA8, 0x3F,              // multiplex 64
        0xD3, 0x00,              // offset
        0x40,                    // start line 0
        0x8D, 0x14,              // charge pump on (SSD1306; ignored by SH1106)
        0x20, 0x02,              // page addressing (works on both controllers)
#if OLED_FLIP
        0xA0, 0xC0,
#else
        0xA1, 0xC8,              // segment remap + COM scan direction
#endif
        0xDA, 0x12,              // COM pins
        0x81, 0xCF,              // contrast
        0xD9, 0xF1,              // pre-charge
        0xDB, 0x40,              // VCOMH
        0xA4, 0xA6,              // resume RAM, normal (not inverted)
        0xAF,                    // display on
    };
    present = true;
    for (unsigned i = 0; i < sizeof seq; i++)
        if (!cmd(seq[i])) { present = false; break; }
    return present;
}

void oled_show(const uint8_t *fb) {
    if (!present) return;
    uint8_t buf[129];
    buf[0] = 0x40;                                // data
    for (int page = 0; page < 8; page++) {
        int col = OLED_SH1106 ? 2 : 0;            // SH1106 RAM is 132 wide, centred
        cmd((uint8_t)(0xB0 | page));
        cmd((uint8_t)(col & 0x0F));
        cmd((uint8_t)(0x10 | (col >> 4)));
        for (int i = 0; i < 128; i++) buf[1 + i] = fb[page * 128 + i];
        i2c_write_timeout_us(OLED_I2C, OLED_ADDR, buf, sizeof buf, false, 20000);
    }
}

void oled_power(bool on) {
    if (present) cmd(on ? 0xAF : 0xAE);
}
