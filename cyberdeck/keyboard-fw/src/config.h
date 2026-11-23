// Clamshell keyboard firmware - pins and tunables.
// Pin numbers are RP2040 GPIOs and match cyberdeck/keyboard-pcb/circuit.py.
#pragma once

// --- link to the Pi 5 (J1 PI_LINK -> Pi 5 3-pin debug UART, /dev/ttyAMA10)
#define PIN_LINK_TX      0          // KB_TX -> Pi RX
#define PIN_LINK_RX      1          // KB_RX <- Pi TX
#define LINK_BAUD        115200

// --- key matrix: rows are driven low one at a time, columns read with pull-ups
//     (diodes: anode at the switch, cathode at the row)
#define PIN_ROW0         2          // ROW0..ROW3 = GPIO2..5
#define PIN_COL0         6          // COL0..COL11 = GPIO6..17
#define MATRIX_ROWS      4
#define MATRIX_COLS      12
#define DEBOUNCE_MS      5

// --- OLED (I2C1)
#define PIN_I2C_SDA      18
#define PIN_I2C_SCL      19
#define OLED_ADDR        0x3C
#define OLED_SH1106      0          // 1 if your 0.96" module uses the SH1106 controller (132 columns)
#define OLED_FLIP        0          // 1 to rotate the picture 180 degrees

// --- built-in trackball: DRV5033 hall switches (open drain, low near a magnet), click switch
#define PIN_TB_UP        21
#define PIN_TB_DOWN      22
#define PIN_TB_LEFT      23
#define PIN_TB_RIGHT     24
#define PIN_TB_CLICK     27
#define TB_PERIOD_MS     8          // motion report period
#define TB_GAIN          3.0f       // pointer counts per hall edge at slow speed
#define TB_ACCEL         0.35f      // extra gain per edge/period of speed
#define TB_MAX_FACTOR    14.0f
#define TB_SCROLL_DIV    4          // hall edges per wheel notch while fn is held

// --- misc
#define PIN_LED          25         // status LED (caps lock)
#define PIN_VBAT_ADC     26         // ADC0: VBAT through 100k / 33k
#define VBAT_DIV_NUM     133        // Vbat = Vadc * 133 / 33
#define VBAT_DIV_DEN     33
#define ADC_VREF_MV      3300

#define LINK_TIMEOUT_MS  6000       // no PING from the Pi for this long -> "Pi offline"
#define FW_VERSION_MAJOR 1
#define FW_VERSION_MINOR 0
