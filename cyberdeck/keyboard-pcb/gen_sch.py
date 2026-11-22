"""Generate clam_kbd.kicad_sch from circuit.py (label-connected schematic, KiCad 7 format)."""
import math
import uuid

from circuit import PARTS
from kicad_lib import find_symbol, symbol_pins, dump_sexp, Q

PROJECT = "clam_kbd"
G = 2.54
ROOT_UUID = str(uuid.uuid4())


def U():
    return str(uuid.uuid4())


def snap(v):
    return round(v / G) * G


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


# --- placement on an A1 sheet
place = {}
special = {"U1": (180.0, 160.0), "U3": (290.0, 110.0), "U2": (90.0, 70.0), "Y1": (110.0, 160.0)}
groups = {
    "misc": [p for p in PARTS if not p["ref"].startswith(("SW", "D1")) or p["ref"] in ("SW_BOOT", "SW_RST", "D1")],
}
misc_x, misc_y = 40.0, 260.0
col_misc = 0
for p in PARTS:
    r = p["ref"]
    if r in special:
        place[r] = special[r]
for p in PARTS:
    r = p["ref"]
    if r in place:
        continue
    if (r.startswith("SW") and r not in ("SW100", "SW101", "SW102")) or (r.startswith("D") and r[1:].isdigit() and int(r[1:]) > 100):
        continue
    place[r] = (40.0 + (col_misc % 9) * 30.48, 230.0 + (col_misc // 9) * 30.48)
    col_misc += 1

# key matrix grid: one cell per key (switch(es) + diode), 12 columns x 4 rows
matrix_cells = {}
for p in PARTS:
    r = p["ref"]
    if r.startswith("D") and r[1:].isdigit() and int(r[1:]) > 100:
        row = int(p["pins"]["1"][3:])
        anode = p["pins"]["2"]
        matrix_cells.setdefault(anode, {"diode": r, "row": row, "switches": []})
for p in PARTS:
    r = p["ref"]
    if r.startswith("SW") and r not in ("SW100", "SW101", "SW102"):
        matrix_cells[p["pins"]["2"]]["switches"].append((r, int(p["pins"]["1"][3:])))
for anode, cell in matrix_cells.items():
    col = cell["switches"][0][1]
    bx, by = 400.0 + col * 45.72, 60.0 + cell["row"] * 45.72
    for i, (sref, _) in enumerate(cell["switches"]):
        place[sref] = (bx + i * 20.32, by)
    place[cell["diode"]] = (bx, by + 17.78)

# --- build
lib_syms = {}
items = []
for p in PARTS:
    sym = find_symbol(p["symbol"])
    lib_syms[p["symbol"]] = sym
    pins = symbol_pins(sym)
    X, Y = (snap(v) for v in place[p["ref"]])
    sym_uuid = U()
    p["sch_uuid"] = sym_uuid
    pin_uuids = [["pin", Q(pn[0]), ["uuid", U()]] for pn in pins]
    props = [
        ["property", "Reference", p["ref"], ["at", fmt(X), fmt(Y - 7.62), "0"], ["effects", ["font", ["size", "1.27", "1.27"]]]],
        ["property", "Value", p["value"], ["at", fmt(X), fmt(Y + 7.62), "0"], ["effects", ["font", ["size", "1.27", "1.27"]]]],
        ["property", "Footprint", p["footprint"], ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
        ["property", "Datasheet", "", ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
        ["property", "MPN", p["mpn"], ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
        ["property", "LCSC", p["lcsc"], ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
        ["property", "Side", p["side"], ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
    ]
    items.append(["symbol", ["lib_id", p["symbol"]], ["at", fmt(X), fmt(Y), "0"], ["unit", "1"],
                  ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["uuid", sym_uuid]] + props + pin_uuids +
                 [["instances", ["project", PROJECT, ["path", "/" + ROOT_UUID, ["reference", p["ref"]], ["unit", "1"]]]]])
    for (num, name, etype, px, py, ang, length, unit) in pins:
        ex, ey = X + px, Y - py                       # pin connection point (schematic y is down)
        a = math.radians(ang)
        ox, oy = -math.cos(a), math.sin(a)            # outward, in schematic coordinates
        net = p["pins"].get(num)
        if net is None:
            if etype != "no_connect":
                items.append(["no_connect", ["at", fmt(ex), fmt(ey)], ["uuid", U()]])
            continue
        wx, wy = ex + ox * G, ey + oy * G
        items.append(["wire", ["pts", ["xy", fmt(ex), fmt(ey)], ["xy", fmt(wx), fmt(wy)]],
                      ["stroke", ["width", "0"], ["type", "default"]], ["uuid", U()]])
        if abs(ox) > 0.5:
            lang, just = ("0", "left") if ox > 0 else ("180", "right")
        else:
            lang, just = ("90", "left") if oy < 0 else ("270", "right")
        items.append(["label", net, ["at", fmt(wx), fmt(wy), lang], ["fields_autoplaced"],
                      ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", just, "bottom"]], ["uuid", U()]])

# power flags on externally supplied rails
flag = find_symbol("power:PWR_FLAG")
lib_syms["power:PWR_FLAG"] = flag
for i, net in enumerate(["+5V", "GND", "VBUS_USB", "VBAT"]):
    X, Y = snap(40.0 + i * 25.4), snap(30.0)
    items.append(["symbol", ["lib_id", "power:PWR_FLAG"], ["at", fmt(X), fmt(Y), "0"], ["unit", "1"],
                  ["in_bom", "no"], ["on_board", "no"], ["dnp", "no"], ["uuid", U()],
                  ["property", "Reference", f"#FLG0{i + 1}", ["at", fmt(X), fmt(Y - 3.81), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
                  ["property", "Value", "PWR_FLAG", ["at", fmt(X), fmt(Y - 5.08), "0"], ["effects", ["font", ["size", "1.27", "1.27"]]]],
                  ["property", "Footprint", "", ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
                  ["property", "Datasheet", "", ["at", fmt(X), fmt(Y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
                  ["pin", Q("1"), ["uuid", U()]],
                  ["instances", ["project", PROJECT, ["path", "/" + ROOT_UUID, ["reference", f"#FLG0{i + 1}"], ["unit", "1"]]]]])
    items.append(["wire", ["pts", ["xy", fmt(X), fmt(Y)], ["xy", fmt(X), fmt(Y + G)]], ["stroke", ["width", "0"], ["type", "default"]], ["uuid", U()]])
    items.append(["label", net, ["at", fmt(X), fmt(Y + G), "270"], ["fields_autoplaced"],
                  ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "right", "bottom"]], ["uuid", U()]])

title = ["title_block", ["title", "Clamshell thumb keyboard"], ["rev", "A"], ["company", "Pi 5 Clamshell"],
         ["comment", "1", "RP2040, 42 keys + mouse L/R, OLED, trackball, battery sense. Generated by gen_sch.py from circuit.py"]]
sch = ["kicad_sch", ["version", "20230121"], ["generator", "eeschema"], ["uuid", ROOT_UUID], ["paper", "A1"], title,
       ["lib_symbols"] + list(lib_syms.values())] + items + [["sheet_instances", ["path", "/", ["page", Q("1")]]]]

if __name__ == "__main__":
    with open(f"{PROJECT}.kicad_sch", "w") as f:
        f.write(dump_sexp(sch) + "\n")
    import json
    json.dump({p["ref"]: p["sch_uuid"] for p in PARTS}, open("sch_uuids.json", "w"))
    print(f"wrote {PROJECT}.kicad_sch with {len(PARTS)} symbols")
