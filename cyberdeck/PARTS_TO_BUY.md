# Pi 5 Clamshell - parts to buy

Everything except the keyboard PCB (ordered assembled from JLCPCB with the files in
`keyboard-pcb/`) and the printed case.

## Main parts

| Qty | Part | Notes |
|---|---|---|
| 1 | Raspberry Pi 5 | you have it |
| 1 | Raspberry Pi Active Cooler (official) | low profile, fits under the keyboard |
| 1 | Waveshare 5inch DSI LCD (800 x 480, capacitive touch) | 121 x 76 mm outline; 4 corner standoffs |
| 1 | Raspberry Pi 5 display cable, 22-pin to 15-pin, 200 mm | Pi 5 uses the small 22-pin connector; the screen has 15-pin |
| 1 | BlackBerry-style trackball breakout (the blue board: VCC GND BTN RHT LFT DWN UP WHT GRN RED BLU) | soldered under the keyboard PCB with its own pin header, almost flush (see the washers below) |
| 1 | 0.96" OLED 128 x 64, SSD1306, I2C, 4 pins in the order **GND VCC SCL SDA** | check the pin order on the listing photo |

## Power

| Qty | Part | Notes |
|---|---|---|
| 2 | 18650 Li-ion cells, flat top, 3000 mAh or more (e.g. Samsung 30Q, Molicel P28A) | or buy a ready 2S stick pack with BMS, cells end to end, max 136 mm long |
| 1 | 2S BMS board (7.4 V, 5 A or more) + nickel strip | not needed if the pack already has a BMS |
| 1 | 2S USB-C charger module, IP2326 type (5 V in, 8.4 V charge, ~15 W) | its USB-C port is the charging port on the right side |
| 1 | Pololu D36V50F5 step-down regulator (5 V, 5.5 A) | powers the Pi 5 and the keyboard |
| 1 | USB-C male plug, solder type (or a short USB-C power lead to cut) | step-down output into the Pi's USB-C |
| 1 | Mini slide switch, SS12D00 type (fits an 8 x 3 mm slot) | master on/off, switches the step-down's enable pin |
| 1 | 6 x 6 mm tactile switch with a tall round stem (or a 4 mm panel push button) | power button, wired to the Pi 5's power-button pads |

## Cables and wire

| Qty | Part | Notes |
|---|---|---|
| 1 pack | JST-SH 1.0 mm pre-crimped cables, single-ended: 4-pin (x2), 3-pin (x1), 2-pin (x1) | keyboard PI_LINK (4) to the Pi 5 UART (3) + 5 V; USB_PROG (4); VBAT (2) |
| 1 | Old USB-A cable to cut | soldered to a 4-pin JST-SH for flashing keyboard firmware |
| 1 roll each | Silicone wire 22 AWG (power) and 28-30 AWG (signals) | |
| 1 | Heat-shrink tube assortment | |

## Screws and small hardware

| Qty | Part | Where |
|---|---|---|
| 5 | M2 x 4 mm self-tapping (pan head) | keyboard PCB into the deck bosses |
| 2 | M2 x 6 mm screws, low pan head + 2 M2 nuts | trackball module to the keyboard PCB |
| 1 bag | M2 nylon washers, 0.5 mm | between the trackball module and the keyboard PCB: the module sits almost flush so the ball stands 1-1.5 mm above the deck (solder its header without the black plastic spacer) |
| 4 | M2.5 x 6 mm self-tapping screws | Pi 5 onto the base standoffs |
| 4 | M2.5 x 4 mm screws | screen standoffs through the lid back |
| 2 | M3 x 30 mm screws + 2 M3 nyloc nuts + 4 M3 nylon washers | hinge axles (tighten for friction) |

## Printing

| Qty | Material | For |
|---|---|---|
| ~250 g | Clear PETG or clear polycarbonate (or clear SLA resin from a print service) | base, deck, lid, bezel |
| ~50 g | Clear TPU 95A | one-piece key mat |

## Keyboard PCB (JLCPCB)

Order after the trackball-module revision of the files is published: 4 layers, 1.0 mm,
ENIG, assembly on both sides, with `fab/bom.csv` and `fab/cpl.csv`. You solder on yourself:
the OLED module and the trackball breakout.
