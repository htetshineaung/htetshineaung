"""
Clamshell keyboard PCB - circuit definition (single source of truth).

Everything here feeds both generated files: the KiCad schematic (gen_sch.py) and the KiCad
PCB (gen_pcb.py), so they cannot disagree.

Board: 4-layer (GND and 3V3 inner planes), 1.0 mm FR4, sits under the clamshell deck (see ../clamshell/clamshell.py).
  Top:    46 tactile switches (XKB TS-1187A 5.1x5.1x1.5 mm), OLED pin pads, BOOT/RESET, LED,
          and the built-in trackball: a 4-roller hall-effect mechanism (BlackBerry-style, as in
          the Pimoroni trackball) sits on the board, 4 DRV5033 omnipolar hall switches read its roller magnets,
          a KMR2 switch under the ball is the click.
  Bottom: RP2040 + flash + crystal + 3.3 V LDO, key diodes, connectors.

Coordinates are CASE coordinates in mm (x right, y from the front edge toward the hinge),
the same frame as clamshell.py, so key switches land exactly under the key-mat caps.

Link to the Pi 5: UART (Pi 5 3-pin UART connector, /dev/ttyAMA10) + 5 V from the battery
step-down. A USB connector is kept for flashing firmware only.
"""

# ------------------------------------------------------------------ geometry (from clamshell.py)
KEY_PX, KEY_PY = 8.4, 7.6
KEY_W, KEY_H = 7.4, 6.6
KB_X0, KB_Y0 = 12.0, 12.0
TB_CX, TB_CY = 124.0, 40.0
LR_W, LR_H, LR_Y0 = 9.0, 7.0, 13.0
OLED_CX, OLED_CY = 24.0, 56.5

BOARD = dict(x0=3.5, y0=4.0, x1=136.5, y1=76.0, r=4.0, notch=None)   # one solid board
# Trackball mechanism (measure yours before ordering): body outline and where each roller's
# magnet passes over the board, relative to the ball centre (TB_CX, TB_CY).
TB_BODY = (12.0, 12.0)                                   # footprint of the mechanism, mm
TB_HALL = {"TB_UP": (0.0, 5.0), "TB_DOWN": (0.0, -5.0), "TB_LEFT": (-5.0, 0.0), "TB_RIGHT": (5.0, 0.0)}
HOLES = [(7.0, 8.0), (108.5, 8.0), (22.0, 73.5), (108.5, 71.0), (64.0, 73.5)]   # M2, to deck bosses
NO_BOTTOM_ZONE = (0.0, 27.0, 20.5, 80.0)               # above the Pi's USB jacks: no bottom parts

# ------------------------------------------------------------------ key layout
ROWS = [  # matrix row 0 = top row of keys (q..), as printed on the key mat
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "BKSP"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", "SCLN", "ENTER"],
    ["SHIFT", "z", "x", "c", "v", "b", "n", "m", "COMMA", "DOT", "SLASH"],
    ["CTRL", "ALT", "FN", "TAB", "SPACE", None, None, "QUOT", "MINUS", "EQL", "ESC"],
]


def key_center(row, col):
    """Case coordinates of a key centre. Row 0 is the back row (furthest from the user)."""
    y0 = KB_Y0 + (3 - row) * KEY_PY
    return KB_X0 + col * KEY_PX + KEY_W / 2, y0 + KEY_H / 2


# ------------------------------------------------------------------ parts
# Each part: ref, symbol, footprint, value, MPN, LCSC (blank = let JLCPCB match by MPN),
#            side ("top"/"bottom"), position (case x, y), rotation, pins {pin number: net}
PARTS = []


def part(ref, symbol, footprint, value, pins, pos, side="bottom", rot=0, mpn="", lcsc="", dnp=False):
    PARTS.append(dict(ref=ref, symbol=symbol, footprint=footprint, value=value, pins=pins,
                      pos=pos, side=side, rot=rot, mpn=mpn, lcsc=lcsc, dnp=dnp))


R0402, C0402, C0603 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric"

# --- MCU cluster (bottom side, above the Pi cooler: ~6.7 mm of air below the board)
MX, MY = 64.0, 60.0
rp = {"1": "+3V3", "10": "+3V3", "22": "+3V3", "33": "+3V3", "42": "+3V3", "49": "+3V3",
      "23": "+1V1", "50": "+1V1", "43": "+3V3", "44": "+3V3", "45": "+1V1", "48": "+3V3",
      "57": "GND", "19": "GND",
      "20": "XIN", "21": "XOUT",
      "24": "SWCLK", "25": "SWDIO", "26": "RUN",
      "46": "USB_DM_MCU", "47": "USB_DP_MCU",
      "51": "QSPI_SD3", "52": "QSPI_SCLK", "53": "QSPI_SD0", "54": "QSPI_SD2", "55": "QSPI_SD1", "56": "QSPI_SS",
      "2": "KB_TX", "3": "KB_RX",                       # GPIO0/1 = UART0 TX/RX -> Pi
      "4": "ROW0", "5": "ROW1", "6": "ROW2", "7": "ROW3",                # GPIO2..5
      "8": "COL0", "9": "COL1", "11": "COL2", "12": "COL3", "13": "COL4", "14": "COL5",  # GPIO6..11
      "15": "COL6", "16": "COL7", "17": "COL8", "18": "COL9", "27": "COL10", "28": "COL11",  # GPIO12..17
      "29": "I2C_SDA", "30": "I2C_SCL",                 # GPIO18/19 = I2C1
      "32": "TB_UP", "34": "TB_DOWN", "35": "TB_LEFT", "36": "TB_RIGHT",   # GPIO21..24: hall switches
      "39": "TB_CLICK",                                 # GPIO27: ball click
      "37": "LED",                                      # GPIO25
      "38": "VBAT_SENSE",                               # GPIO26 / ADC0
      }
part("U1", "MCU_RaspberryPi:RP2040", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm", "RP2040", rp,
     (MX, MY), mpn="RP2040", lcsc="C2040")
part("U3", "Memory_Flash:W25Q32JVSS", "Package_SO:SOIC-8_5.23x5.23mm_P1.27mm", "W25Q16JVSSIQ",
     {"1": "QSPI_SS", "2": "QSPI_SD1", "3": "QSPI_SD2", "4": "GND", "5": "QSPI_SD0", "6": "QSPI_SCLK", "7": "QSPI_SD3", "8": "+3V3"},
     (MX + 10.0, MY + 0.5), rot=90, mpn="W25Q16JVSSIQ")
part("Y1", "Device:Crystal_GND24", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "12MHz",
     {"1": "XIN", "2": "GND", "3": "XOUT_R", "4": "GND"}, (MX - 6.5, MY - 7.0), mpn="ABM8-272-T3")
part("R1", "Device:R_Small", R0402, "1k", {"1": "XOUT", "2": "XOUT_R"}, (MX - 2.5, MY - 6.5), rot=90, mpn="0402WGF1001TCE", lcsc="C11702")
part("C16", "Device:C_Small", C0402, "15pF", {"1": "XIN", "2": "GND"}, (MX - 9.5, MY - 8.5), mpn="0402CG150J500NT", lcsc="C1548")
part("C17", "Device:C_Small", C0402, "15pF", {"1": "XOUT_R", "2": "GND"}, (MX - 4.0, MY - 9.5), mpn="0402CG150J500NT", lcsc="C1548")
# decoupling: one 100 nF per IOVDD pin, 2 on DVDD, ADC_AVDD, USB_VDD; 1 uF on VREG_IN / VREG_VOUT
dec = [("C4", "+3V3", (MX - 5.0, MY + 3.5)), ("C5", "+3V3", (MX - 5.0, MY - 2.0)), ("C6", "+3V3", (MX - 1.0, MY - 5.0)),
       ("C7", "+3V3", (MX + 4.5, MY - 5.0)), ("C8", "+3V3", (MX + 5.0, MY + 3.0)), ("C9", "+3V3", (MX + 1.5, MY + 5.0)),
       ("C10", "+1V1", (MX - 2.0, MY + 5.0)), ("C11", "+1V1", (MX + 3.5, MY + 5.2)),
       ("C14", "+3V3", (MX + 5.0, MY - 1.5)), ("C15", "+3V3", (MX + 2.0, MY - 5.0))]
for ref, net, pos in dec:
    part(ref, "Device:C_Small", C0402, "100nF", {"1": net, "2": "GND"}, pos, rot=90, mpn="CL05B104KO5NNNC", lcsc="C1525")
part("C12", "Device:C_Small", C0402, "1uF", {"1": "+3V3", "2": "GND"}, (MX - 5.2, MY + 6.0), rot=90, mpn="CL05A105KA5NQNC", lcsc="C52923")
part("C13", "Device:C_Small", C0402, "1uF", {"1": "+1V1", "2": "GND"}, (MX - 0.2, MY + 7.0), rot=90, mpn="CL05A105KA5NQNC", lcsc="C52923")
part("C18", "Device:C_Small", C0402, "100nF", {"1": "+3V3", "2": "GND"}, (MX + 10.0, MY + 5.5), mpn="CL05B104KO5NNNC", lcsc="C1525")

# --- BOOTSEL / RESET (top side, reachable with the deck lifted off)
part("R5", "Device:R_Small", R0402, "1k", {"1": "QSPI_SS", "2": "BOOT_N"}, (MX + 8.0, MY - 7.5), mpn="0402WGF1001TCE", lcsc="C11702")
part("SW100", "Switch:SW_Push", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", "BOOT",
     {"1": "BOOT_N", "2": "GND"}, (98.0, 66.0), side="top", mpn="KMR221GLFS")
part("R6", "Device:R_Small", R0402, "10k", {"1": "+3V3", "2": "RUN"}, (MX - 8.5, MY - 1.0), rot=90, mpn="0402WGF1002TCE", lcsc="C25744")
part("SW101", "Switch:SW_Push", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", "RESET",
     {"1": "RUN", "2": "GND"}, (98.0, 72.0), side="top", mpn="KMR221GLFS")

# --- power: 5 V in (Pi link or programming USB) -> 3.3 V LDO
part("U2", "Regulator_Linear:AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", "AP2112K-3.3",
     {"1": "+5V", "2": "GND", "3": "+5V", "5": "+3V3"}, (46.0, 66.0), mpn="AP2112K-3.3TRG1", lcsc="C51118")
part("C1", "Device:C_Small", C0402, "1uF", {"1": "+5V", "2": "GND"}, (42.5, 66.0), rot=90, mpn="CL05A105KA5NQNC", lcsc="C52923")
part("C2", "Device:C_Small", C0402, "1uF", {"1": "+3V3", "2": "GND"}, (49.5, 66.0), rot=90, mpn="CL05A105KA5NQNC", lcsc="C52923")
part("C3", "Device:C_Small", C0603, "10uF", {"1": "+3V3", "2": "GND"}, (52.0, 63.0), rot=90, mpn="CL10A106KP8NNNC", lcsc="C19702")
part("D1", "Device:D_Schottky_Small", "Diode_SMD:D_SOD-123", "B5819W", {"1": "+5V", "2": "VBUS_USB"}, (38.0, 66.0), rot=90, mpn="B5819W", lcsc="C8598")

# --- built-in trackball: 4 hall switches under the roller magnets, click switch under the ball.
# DRV5033 outputs are open drain: 10k pull-ups to 3V3 (the RP2040's own pull-ups work too).
for i, (net, (dx, dy)) in enumerate(TB_HALL.items()):
    hx, hy = TB_CX + dx, TB_CY + dy
    part(f"U{4 + i}", "Sensor_Magnetic:DRV5033FAxDBZ", "Package_TO_SOT_SMD:SOT-23", "DRV5033FA",
         {"1": "+3V3", "2": net, "3": "GND"}, (hx, hy), side="top", rot=(90 if dx == 0 else 0),
         mpn="DRV5033FAQDBZR")
    ox, oy = (6.5 if dx >= 0 else -6.5, 0.0) if dy == 0 else (0.0, 6.0 if dy > 0 else -6.0)
    part(f"C{20 + i}", "Device:C_Small", C0402, "100nF", {"1": "+3V3", "2": "GND"},
         (hx + ox + (1.2 if dy != 0 else 0), hy + oy + (0 if dy != 0 else 1.2)), side="top", rot=90,
         mpn="CL05B104KO5NNNC", lcsc="C1525")
    part(f"R{20 + i}", "Device:R_Small", R0402, "10k", {"1": "+3V3", "2": net},
         (hx + ox - (1.2 if dy != 0 else 0), hy + oy - (0 if dy != 0 else 1.2)), side="top", rot=90,
         mpn="0402WGF1002TCE", lcsc="C25744")
part("SW102", "Switch:SW_Push", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", "TB_CLICK",
     {"1": "TB_CLICK", "2": "GND"}, (TB_CX, TB_CY), side="top", mpn="KMR221GLFS")

# --- connectors (all on the bottom, cables run to the Pi / power board)
part("J1", "Connector_Generic:Conn_01x04", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "PI_LINK",
     {"1": "+5V", "2": "GND", "3": "KB_RX", "4": "KB_TX"}, (57.0, 72.5), rot=180, mpn="SM04B-SRSS-TB")
part("J5", "Connector_Generic:Conn_01x04", "Connector_JST:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal", "USB_PROG",
     {"1": "VBUS_USB", "2": "USB_DN", "3": "USB_DP", "4": "GND"}, (46.0, 72.5), rot=180, mpn="SM04B-SRSS-TB")
part("R2", "Device:R_Small", R0402, "27R", {"1": "USB_DM_MCU", "2": "USB_DN"}, (MX - 6.5, MY + 8.5), rot=90, mpn="0402WGF270KTCE", lcsc="C25100")
part("R3", "Device:R_Small", R0402, "27R", {"1": "USB_DP_MCU", "2": "USB_DP"}, (MX - 5.0, MY + 8.5), rot=90, mpn="0402WGF270KTCE", lcsc="C25100")
part("J4", "Connector_Generic:Conn_01x02", "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal", "VBAT",
     {"1": "VBAT", "2": "GND"}, (108.5, 24.0), mpn="SM02B-SRSS-TB")
part("J2", "Connector_Generic:Conn_01x04", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "OLED",
     {"1": "GND", "2": "+3V3", "3": "I2C_SCL", "4": "I2C_SDA"}, (OLED_CX - 3.81, 68.3), side="top", rot=90,
     mpn="SSD1306 0.96in 128x64 I2C module (GND VCC SCL SDA)")

# --- I2C pull-ups, battery sense, status LED, SWD pads
part("R10", "Device:R_Small", R0402, "4.7k", {"1": "+3V3", "2": "I2C_SDA"}, (MX + 13.5, MY - 4.0), rot=90, mpn="0402WGF4701TCE", lcsc="C25900")
part("R11", "Device:R_Small", R0402, "4.7k", {"1": "+3V3", "2": "I2C_SCL"}, (MX + 15.0, MY - 4.0), rot=90, mpn="0402WGF4701TCE", lcsc="C25900")
part("R8", "Device:R_Small", R0402, "100k", {"1": "VBAT", "2": "VBAT_SENSE"}, (88.0, 30.0), rot=90, mpn="0402WGF1003TCE", lcsc="C25741")
part("R9", "Device:R_Small", R0402, "33k", {"1": "VBAT_SENSE", "2": "GND"}, (90.0, 32.5), mpn="0402WGF3302TCE", lcsc="C25779")
part("C19", "Device:C_Small", C0402, "100nF", {"1": "VBAT_SENSE", "2": "GND"}, (86.0, 32.5), mpn="CL05B104KO5NNNC", lcsc="C1525")
part("R7", "Device:R_Small", R0402, "1k", {"1": "LED", "2": "LED_A"}, (58.0, 61.0), side="top", rot=90, mpn="0402WGF1001TCE", lcsc="C11702")
part("D2", "Device:LED_Small", "LED_SMD:LED_0603_1608Metric", "GREEN", {"1": "GND", "2": "LED_A"}, (58.0, 64.0), side="top",
     rot=90, mpn="KT-0603G", lcsc="C72043")
for i, (ref, net) in enumerate([("TP1", "SWCLK"), ("TP2", "SWDIO"), ("TP3", "GND")]):
    part(ref, "Connector:TestPoint", "TestPoint:TestPoint_Pad_D1.0mm", net, {"1": net}, (80.0 + 2.5 * i, 72.5))

# --- key matrix: switch on top, diode (cathode to row) on the bottom right below it
SW_FP = "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A"
SW_MPN, SW_LCSC = "TS-1187A-B-A-B", "C318884"
D_FP = "Diode_SMD:D_SOD-323"
keys = []  # (name, matrix row, matrix col, [switch positions])
for r, row in enumerate(ROWS):
    for c, name in enumerate(row):
        if name is None:
            continue
        if name == "SPACE":                       # 3-wide cap: two switches in parallel, one diode
            keys.append((name, r, c, [key_center(r, 4), key_center(r, 6)]))
        else:
            keys.append((name, r, c, [key_center(r, c)]))
lr_x = TB_CX - LR_W - 0.6
keys.append(("MOUSE_L", 0, 11, [(lr_x + LR_W / 2, LR_Y0 + LR_H / 2)]))
keys.append(("MOUSE_R", 1, 11, [(TB_CX + 0.6 + LR_W / 2, LR_Y0 + LR_H / 2)]))

sw_n = 1
for n, (name, r, c, positions) in enumerate(keys, start=1):
    anode = f"KD{n}"
    for (x, y) in positions:
        part(f"SW{sw_n}", "Switch:SW_Push", SW_FP, name, {"1": f"COL{c}", "2": anode}, (x, y), side="top",
             mpn=SW_MPN, lcsc=SW_LCSC)
        sw_n += 1
    dx, dy = positions[0]
    if NO_BOTTOM_ZONE[0] <= dx <= NO_BOTTOM_ZONE[2] and NO_BOTTOM_ZONE[1] <= dy <= NO_BOTTOM_ZONE[3]:
        dx = NO_BOTTOM_ZONE[2] + 0.2             # keep clear of the Pi's USB jacks
    part(f"D{100 + n}", "Device:D_Small", D_FP, "1N4148WS", {"1": f"ROW{r}", "2": anode}, (dx, dy),
         mpn="1N4148WS", lcsc="C2128")

KEYMAP = {(r, c): name for name, r, c, _ in keys}

# Parts placed automatically by gen_pcb.py next to the pin they serve:
#   ref: (anchor ref, anchor pin(s), distance outward from the anchor's centre-to-pin direction, mm)
AUTO = {
    "C4": ("U1", ["1"], 4.8), "C5": ("U1", ["10"], 4.8), "C6": ("U1", ["22"], 4.8), "C7": ("U1", ["33"], 4.8),
    "C8": ("U1", ["42"], 4.8), "C9": ("U1", ["49"], 4.8), "C10": ("U1", ["23"], 4.8), "C11": ("U1", ["50"], 4.8),
    "C14": ("U1", ["43"], 4.8), "C15": ("U1", ["48"], 4.8), "C12": ("U1", ["44"], 4.8), "C13": ("U1", ["45"], 4.8),
    "R2": ("U1", ["46"], 5.5), "R3": ("U1", ["47"], 5.5), "R5": ("U1", ["56"], 6.0), "R6": ("U1", ["26"], 5.0),
    "R10": ("U1", ["29"], 6.5), "R11": ("U1", ["30"], 6.5),
    "Y1": ("U1", ["20", "21"], 7.5), "R1": ("U1", ["21"], 5.0),
    "C16": ("Y1", ["1"], 2.6), "C17": ("Y1", ["3"], 2.6),
    "U3": ("U1", ["51", "52", "53", "54", "55", "56"], 11.0), "C18": ("U3", ["8"], 3.0),
    "C1": ("U2", ["1"], 2.8), "C2": ("U2", ["5"], 2.8), "C3": ("U2", ["5"], 4.8),
    "R8": ("J4", ["1"], 4.0), "R9": ("J4", ["1"], 5.5), "C19": ("J4", ["1"], 7.0),
}

# ------------------------------------------------------------------ derived
def nets():
    out = {}
    for p in PARTS:
        for pin, net in p["pins"].items():
            out.setdefault(net, []).append((p["ref"], pin))
    return out


if __name__ == "__main__":
    n = nets()
    print(f"{len(PARTS)} parts, {len(n)} nets, {sum(1 for p in PARTS if p['ref'].startswith('SW') and p['symbol'].startswith('Switch'))} switches")
    singles = [k for k, v in n.items() if len(v) < 2]
    print("single-pin nets:", singles)
