# Clamshell keyboard PCB (phase 2)

Our own thumb keyboard for the Pi 5 Clamshell: RP2040, 42 keys + mouse L/R (45 switches: the space bar has two) on 1.5 mm tactile
switches, trackball and OLED connectors, battery voltage sense. 2-layer, 1.0 mm, 133 × 72 mm,
shaped to drop into the clamshell base under the deck.

| File | What it is |
|---|---|
| `circuit.py` | **Source of truth**: every part, value, MPN/LCSC, position and pin→net |
| `gen_sch.py` → `clam_kbd.kicad_sch` | KiCad 7 schematic (label-connected), opens in KiCad |
| `gen_pcb.py` → `clam_kbd.kicad_pcb`, `clam_kbd.dsn` | Placed PCB with nets, outline, GND pours; Specctra file for the autorouter |
| `verify_netlist.py` | Checks KiCad's exported netlist against `circuit.py`, pin by pin |
| `run_drc.py` | KiCad DRC through the pcbnew API |
| `gen_fab.py` → `fab/bom.csv`, `fab/cpl.csv` | JLCPCB assembly files |
| `render/` | Top / bottom renders, schematic PDF |

```bash
python3 gen_sch.py && kicad-cli sch export netlist clam_kbd.kicad_sch -o clam_kbd.net && python3 verify_netlist.py
KICAD7_FOOTPRINT_DIR=/usr/share/kicad/footprints /usr/bin/python3 gen_pcb.py
/usr/bin/python3 run_drc.py drc.rpt
```

## Status
- Schematic: generated; KiCad netlist matches `circuit.py` on all 91 nets (0 mismatches).
- Placement: done, matched to the clamshell key mat; DRC clean apart from unrouted nets and
  cosmetic silkscreen overlaps.
- **Routing: not done yet.** Autorouting with Freerouting was blocked in the build sandbox.
  Route it in KiCad (Freerouting plugin or by hand), or let the generator route once allowed:
  `java -jar freerouting.jar -de clam_kbd.dsn -do clam_kbd.ses`, then
  `/usr/bin/python3 gen_pcb.py --ses clam_kbd.ses`, `run_drc.py`, then export Gerbers.

## Circuit
- **MCU:** RP2040 + W25Q16JVSSIQ 2 MB QSPI flash, 12 MHz ABM8-272-T3 crystal (15 pF, 1 kΩ on
  XOUT), BOOT button (QSPI_SS via 1 kΩ) and RESET, 100 nF per supply pin, 1 µF on VREG in/out.
- **Power:** +5 V from the battery step-down (J1) or the programming USB through a B5819W
  (so the Pi's 5 V never back-feeds a USB host) → AP2112K-3.3 LDO → +3V3 → RP2040 core LDO → +1V1.
- **Link to the Pi:** UART at 3.3 V on J1. In the clamshell the Pi's USB ports face out
  through the case wall, so the keyboard talks over the Pi 5's internal UART connector
  (`/dev/ttyAMA10`) and Linux turns key/mouse frames into a virtual keyboard and mouse.
- **Matrix:** 4 rows × 12 columns, 1N4148WS per key (cathode to row: rows driven low, columns
  pulled up). The space bar has two switches in parallel on one diode. L/R are on column 11.
- **I²C1** (GPIO18/19, 4.7 kΩ pull-ups): OLED (J2 pads) and trackball (J3, with INT on GPIO20).
- **Battery sense:** 100 kΩ / 33 kΩ divider + 100 nF on GPIO26 (8.4 V → 2.08 V).

| Connector | Pins | Goes to |
|---|---|---|
| J1 PI_LINK (JST-SH 4) | 1 +5V · 2 GND · 3 KB_RX · 4 KB_TX | step-down 5 V/GND; Pi 5 UART connector (Pi TX → KB_RX, Pi RX ← KB_TX, GND) |
| J5 USB_PROG (JST-SH 4) | 1 VBUS · 2 D− · 3 D+ · 4 GND | USB cable for flashing firmware (hold BOOT, tap RESET) |
| J3 TRACKBALL (JST-SH 5) | 1 3V3 · 2 SDA · 3 SCL · 4 INT · 5 GND | Pimoroni Trackball Breakout |
| J4 VBAT (JST-SH 2) | 1 VBAT · 2 GND | 2S pack + (after the BMS) |
| J2 OLED (4 pads, 2.54 mm) | 1 GND · 2 VCC · 3 SCL · 4 SDA | 0.96" SSD1306 module, soldered flat. **Check your module's pin order** |

| RP2040 | Function | RP2040 | Function |
|---|---|---|---|
| GPIO0 / 1 | UART0 TX / RX → Pi | GPIO18 / 19 | I²C1 SDA / SCL |
| GPIO2–5 | ROW0–3 | GPIO20 | trackball INT |
| GPIO6–17 | COL0–11 | GPIO25 | status LED |
| GPIO26 | battery sense (ADC0) | GPIO21–24, 27–29 | spare |

## Before ordering
- Route, then re-run DRC and the netlist check.
- Confirm the LCSC numbers left blank (flash, crystal, JST-SH, KMR2) in JLCPCB's part search;
  JLCPCB can also match by MPN.
- Check part rotations in JLCPCB's placement preview (KiCad and JLCPCB zero-rotation
  conventions differ for some packages).
- Datasheet sites were not reachable from the build sandbox: pinouts were checked against the
  KiCad library symbols and the standard pin tables, not the PDFs.
