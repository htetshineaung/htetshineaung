# Clamshell keyboard PCB (phase 2)

Our own thumb keyboard for the Pi 5 Clamshell: RP2040, 42 keys + mouse L/R (45 switches: the space bar has two) on 1.5 mm tactile
switches, a BlackBerry-style trackball breakout under a window in the board, OLED pads, battery voltage
sense. 4-layer (In1 solid GND plane,
In2 extra routing layer), 1.0 mm, 133 × 72 mm,
shaped to drop into the clamshell base under the deck.

| File | What it is |
|---|---|
| `circuit.py` | **Source of truth**: every part, value, MPN/LCSC, position and pin→net |
| `gen_sch.py` → `clam_kbd.kicad_sch` | KiCad 7 schematic (label-connected), opens in KiCad |
| `gen_pcb.py` → `clam_kbd.kicad_pcb`, `clam_kbd.dsn` | Placed PCB with nets, outline, GND pours; Specctra file for the autorouter |
| `verify_netlist.py` | Checks KiCad's exported netlist against `circuit.py`, pin by pin |
| `run_drc.py` | KiCad DRC through the pcbnew API |
| `gen_fab.py` → `fab/bom.csv`, `fab/cpl.csv` | JLCPCB assembly files (placements from `fab/routed_positions.csv`, the routed board's export) |
| `apply_tb_module.py`, `cluster_route.py`, `trim_dangling.py`, `tb_pipeline.sh` | Turn the routed rev A board into rev B (trackball breakout) without re-routing everything |
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
- **Routing:** scripted pipeline, run with KiCad 10's Python on the Mac (KiCad 7 works too):
  1. `route_matrix.py clam_kbd.kicad_pcb clam_kbd_rN.kicad_pcb x.dsn`: clears old routing and
     pre-routes the regular key matrix (columns on top, rows on the bottom, locked).
  2. `stitch_gnd.py clam_kbd_rN.kicad_pcb clam_kbd_rN.kicad_pcb x.dsn`: one via per small-part
     GND pad, a 3x3 via grid in the RP2040 exposed pad, and the TESTEN stub.
  3. (the DSN written by step 2 is the autorouter input; `export_dsn.py` can hide the pours)
  4. `java -Djava.awt.headless=true -jar freerouting-2.5.0.jar --gui.enabled=false
     -de clam_kbd_rN.dsn -do clam_kbd_rN.ses -mp 60 -mt 6`
  5. Import the `.ses` (`pcbnew.ImportSpecctraSES`), then `stitch_gnd.py ... --grid` for a 3 mm
     stitching-via grid, then `kicad-cli pcb drc --refill-zones --save-board`.
  6. `fix_route.py board board U1.6 U1.7 --inner [--rip 0.6]`: grid router for any pins the
     autorouter leaves open (can rip up nearby tracks and reconnect them).
  7. `gnd_islands.py board.kicad_pcb` lists any ground islands; `export_jlc.sh board` gates on DRC and
     writes the Gerber zip.
  Result (rev A): 0 unconnected, 0 DRC errors, 1171 segments on F/In2/B, 215 vias.
  Rules (`clam_kbd_rN.kicad_pro`): 0.15 mm track and clearance, 0.5/0.3 mm vias, 0.3 mm to the
  edge; all within JLCPCB's standard 4-layer process (the router's few 0.09 mm neck-downs at the
  RP2040 pins are inside JLCPCB's 0.09 mm multilayer limit).
- **Trackball (rev B):** the ready-made BlackBerry-style trackball breakout (pins VCC GND BTN RHT
  LFT DWN UP WHT GRN RED BLU) sits *under* the board: its own 11-pin header is soldered through J6
  (plated holes, both boards), two M2 screws with 2.5 mm spacers (H6, H7) hold its other edge, and
  the ball comes up through a 14 × 14 mm window centred at (124, 44). The module's hall outputs and
  click go straight to the RP2040 (GPIO21–24 up/down/left/right, GPIO27 click); its RGB LED goes
  through 100 Ω R20–R22 to GPIO20/28/29 (works whichever way the module's LED is wired: the
  firmware picks the polarity). WHT is not connected. The module runs from +3V3.
- **Rev B routing** (`tb_pipeline.sh`, on the Mac with KiCad 10): `apply_tb_module.py` removes the
  rev A hall sensors and their tracks, adds J6 / R20–R22 / H6–H7 / the window and clears copper they
  clash with (pad nets are checked against the generated board by hash); `fix_route.py` routes the
  new connections; `cluster_route.py` redoes the RP2040's right-side fan-out (pins 34–41 all need
  an escape now), trying routing orders until every pin gets out; `trim_dangling.py` cuts the
  stubs left over. Result: 0 unconnected, 0 DRC errors.

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
- **I²C1** (GPIO18/19, 4.7 kΩ pull-ups): OLED (J2 pads).
- **Battery sense:** 100 kΩ / 33 kΩ divider + 100 nF on GPIO26 (8.4 V → 2.08 V).

| Connector | Pins | Goes to |
|---|---|---|
| J1 PI_LINK (JST-SH 4) | 1 +5V · 2 GND · 3 KB_RX · 4 KB_TX | step-down 5 V/GND; Pi 5 UART connector (Pi TX → KB_RX, Pi RX ← KB_TX, GND) |
| J5 USB_PROG (JST-SH 4) | 1 VBUS · 2 D− · 3 D+ · 4 GND | USB cable for flashing firmware (hold BOOT, tap RESET) |
| J4 VBAT (JST-SH 2) | 1 VBAT · 2 GND | 2S pack + (after the BMS) |
| J2 OLED (4 pads, 2.54 mm) | 1 GND · 2 VCC · 3 SCL · 4 SDA | 0.96" SSD1306 module, soldered flat. **Check your module's pin order** |

| RP2040 | Function | RP2040 | Function |
|---|---|---|---|
| GPIO0 / 1 | UART0 TX / RX → Pi | GPIO18 / 19 | I²C1 SDA / SCL |
| GPIO2–5 | ROW0–3 | GPIO21–24, 27 | trackball up/down/left/right, click |
| GPIO6–17 | COL0–11 | GPIO25 | status LED |
| GPIO26 | battery sense (ADC0) | GPIO20 / 28 / 29 | trackball LED red / green / blue |

| J6 pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Breakout | VCC | GND | BTN | RHT | LFT | DWN | UP | WHT | GRN | RED | BLU |
| Net | +3V3 | GND | TB_CLICK | TB_RIGHT | TB_LEFT | TB_DOWN | TB_UP | — | TB_LED_G | TB_LED_R | TB_LED_B |

## Before ordering
- Route, then re-run DRC and the netlist check.
- Confirm the LCSC numbers left blank (flash, crystal, JST-SH, KMR2) in JLCPCB's part search;
  JLCPCB can also match by MPN.
- Check part rotations in JLCPCB's placement preview (KiCad and JLCPCB zero-rotation
  conventions differ for some packages).
- Datasheet sites were not reachable from the build sandbox: pinouts were checked against the
  KiCad library symbols and the standard pin tables, not the PDFs.
