# Pi 5 + Cardputer Mini-Deck

A pocket Linux machine: **Raspberry Pi 5** with a **3.5" GPIO touchscreen** on top, and an
**M5Stack Cardputer** in front of it as the **keyboard** and a **second screen for status
and notifications**.

![assembled case preview](case/preview/deck_assembled_preview.png)

```
             back:  USB-C power · micro-HDMI x2 · UART
   ┌─────────────────────────────────────────────┐
   │  ┌───────────────────────────────────────┐  │
   │  │     3.5" LCD  (Linux desktop/TTY)     │  │  right: microSD / power button
   │  │     Raspberry Pi 5 underneath         │  │
   │  └───────────────────────────────────────┘  │
   ├──────────────────[ cable tunnel ]───────────┤
   │  ┌───────────────────────────────────────┐  │
   │  │ [status screen]   M5Stack Cardputer   │  │
   │  │  q w e r t y u i o p  (keyboard)      │  │
   │  └───────────────( finger )──────────────┘  │
   └─────────────────────────────────────────────┘
   left: hidden cable channel; Ethernet + 3 USB-A   front
```

## 1. Parts

| Qty | Part | Notes |
|---|---|---|
| 1 | Raspberry Pi 5 (any RAM) | 27 W **5 V / 5 A** USB-C PSU recommended |
| 1 | 3.5" 480×320 SPI GPIO LCD (the one in your photo) | plugs onto the 40-pin header |
| 1 | Low-profile cooler (Active Cooler or heatsink) | must fit under the LCD |
| 1 | M5Stack Cardputer (v1 / v1.1) | keyboard + status screen |
| 1 | **USB-A → USB-C data cable, right-angle at both ends** (~15 cm; USB-A end angled up/down) | the only wire; lives in the hidden left channel |
| 4 | M2.5 × 6 screws (or the brass standoffs that came with the LCD) | Pi → tray |
| 4 | M2.5 × 8 self-tapping screws | faceplate → tray |
| — | PLA/PETG ~160 g | two printed parts |

## 2. Wiring

### Option A — USB (recommended, no soldering)

```
 Raspberry Pi 5                              M5Stack Cardputer
 ┌───────────────┐                           ┌───────────────┐
 │ USB-A (any)   │═══ USB-A ⇄ USB-C cable ═══│ USB-C         │
 └───────────────┘                           └───────────────┘
   one cable carries:  5 V (charges Cardputer) + HID keyboard + CDC serial (status/notifications)
```

* The Cardputer shows up as a normal **USB keyboard** → works in the BIOS-less boot console,
  TTY login, desktop, everything. No driver.
* The same cable is a **serial port** (`/dev/cardputer`) the Pi uses to push stats/notifications.
* The 3.5" LCD uses all 40 GPIO pins, so USB is also the cleanest choice.

### Option B — wired UART (frees all USB ports)

The Pi 5 has a separate **3-pin UART connector** (JST-SH 1.0 mm, labelled `UART`, between
the two micro-HDMI ports — visible in your photo). It is *not* covered by the LCD.

```
 Pi 5 "UART" JST-SH (3-pin)              Cardputer Grove port (HY2.0-4P)
 ┌──────────┐                            ┌───────────────┐
 │ TX  ─────┼──────────────────────────► │ G1  (RX)      │  yellow
 │ RX  ◄────┼─────────────────────────── │ G2  (TX)      │  white
 │ GND ─────┼──────────────────────────  │ GND           │  black
 └──────────┘                            │ 5V   ✗ leave unconnected
                                         └───────────────┘
```

* Both sides are **3.3 V logic** — no level shifter. **Do not connect Grove 5 V.**
* Pin order follows the Raspberry Pi Debug Connector spec; confirm with a multimeter
  before plugging: the Pi's **TX idles at ~3.3 V** once the UART is enabled.
* The Cardputer then runs on its own battery (charge it via USB-C when needed).
* Keys are sent as text frames and injected by the Pi daemon as a virtual keyboard
  (`uinput`), so it only works once Linux has booted.
* Build the firmware with `pio run -e cardputer-uart` and install the Pi side with
  `sudo ./install.sh --uart`.

## 3. Firmware for the Cardputer

`firmware/cardputer-deck/` (PlatformIO, Arduino framework, M5Cardputer library)

```bash
cd firmware/cardputer-deck
pio run -t upload            # USB mode   (hold G0 while plugging in if no port appears)
pio run -e cardputer-uart -t upload   # UART mode
```

Arduino IDE: install the **M5Cardputer** library, then set
`Tools → USB Mode = USB-OTG (TinyUSB)` and `USB CDC On Boot = Enabled`.

**Keyboard map**

| Keys | Sends |
|---|---|
| `Fn` + `;` `.` `,` `/` | ↑ ↓ ← → |
| `Fn` + `` ` `` | Esc |
| `Fn` + `Del` | Delete (plain `Del` = Backspace) |
| `Fn` + `1`…`0`, `-`, `=` | F1…F10, F11, F12 |
| `Fn` + `[` / `]` | Home / End |
| `Fn` + `'` / `Enter` | Page Up / Page Down |
| `ctrl` `alt` `Aa`(shift) | Ctrl, Alt, Shift |
| `opt` | Super (Windows/GUI key) |
| `G0` button (top) | next status page |

**Cardputer screen pages:** ① live stats (CPU, temp, RAM, disk, IP, uptime, clock, Pi link LED, Cardputer battery) → ② last notifications → ③ key help. New notifications pop up as a 6-second toast with a beep; the screen dims after 2 minutes idle.

## 4. Pi software

```bash
cd pi
sudo ./install.sh          # or: sudo ./install.sh --uart
cardputer-notify "Hello" "Deck is alive"
```

Installs:

* `cardputer-statusd` (system service) — sends stats every 2 s, warns on under-voltage/throttling,
  forwards notifications.
* `cardputer-dbus-bridge` (user service) — mirrors **desktop notifications**
  (`notify-send`, browser, chat apps…) to the Cardputer.
* `cardputer-notify` — send your own from scripts/cron:
  `make && cardputer-notify -a build "Build OK" || cardputer-notify -a build "Build FAILED"`
* udev rule → stable `/dev/cardputer`.

## 5. 3.5" LCD on the Pi 5

The old `LCD-show` scripts do not support the Pi 5. On current Raspberry Pi OS:

1. Find the controller on the board label/listing (most 3.5" GPIO screens: **ILI9486** with
   **XPT2046/ADS7846** touch; some newer ones: ST7796S).
2. Use the vendor's Pi 5 / Bookworm instructions if it is a Waveshare/LCDwiki screen, otherwise
   try the in-kernel overlays in `/boot/firmware/config.txt`:

   ```ini
   dtparam=spi=on
   dtoverlay=piscreen,speed=16000000,rotate=270     # ILI9486 panel
   # touch is built into piscreen; if not, add an ads7846 overlay for your board
   ```
3. **The case mounts the Pi rotated 180°** (power/HDMI at the back, USB at the left), so if
   the image is upside-down change `rotate=270` → `rotate=90` (touch follows the same param).

## 6. Case (3D print)

Files in `case/stl/`:

| File | Print orientation | Supports |
|---|---|---|
| `deck_tray.stl` | floor on the bed | none |
| `deck_faceplate.stl` | already flipped: top face on the bed | none |
| `*.step` | for editing in Fusion/FreeCAD | — |

**Print settings:** PLA or PETG, 0.2 mm layer, 3 walls, 15–20 % gyroid infill, no supports.
PETG preferred — the Pi 5 runs warm under the screen.

Overall size **108 × 131 × 28 mm**. v2: one faceplate over the whole top, the Cardputer
sits flush with it, and the link cable is hidden in a channel along the left side
(the lower-front USB-A port is used internally; Ethernet and the other three USB ports
stay reachable through recessed openings).

![tray](case/preview/deck_tray.png)

### Before you print — measure these 3 things

Edit the parameters at the top of `case/deck_case.py` and re-run `python deck_case.py`
(needs `pip install cadquery`):

| Parameter | Default | What to measure |
|---|---|---|
| `stack_above_pcb` | 17.5 mm | Pi PCB top surface → top of the LCD glass (with your cooler) |
| `lcd_win_dx`, `lcd_win_dy` | 0, 0 | glass centre offset from the board centre (most 3.5" glass sits off-centre toward the FPC end) |
| `cp_usb_y_frac` | 0.62 | where the USB-C sits along the Cardputer's **left** side (fraction from its front); the cable enters there from the hidden channel |

Other useful knobs: `cp_cl` (Cardputer fit, 0.4 mm/side), `cp_recess`, `chan_w` (cable channel width), `pi_cl`, `standoff_h`.

### Assembly

1. Flash the Cardputer and install the Pi software first (easier outside the case).
2. Fit the cooler, screw the Pi into the tray standoffs (USB/Ethernet toward the **left** side).
3. Plug the LCD onto the GPIO header, add its standoffs.
4. Plug the right-angle cable into the **lower-front** USB-A port, lay it in the left channel
   (it passes under the Ethernet jack) and bring the USB-C end out at the Cardputer pocket.
5. Plug in the Cardputer, drop it into its pocket (top flush with the faceplate).
6. Screw the faceplate on (4 × M2.5 self-tappers into the corner pillars).
   For Option B, route the Grove cable through the tunnel in the divider instead.