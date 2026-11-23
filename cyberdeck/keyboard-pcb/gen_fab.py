"""JLCPCB assembly files from the board: bom.csv (Comment, Designator, Footprint, LCSC) and cpl.csv.
Run with /usr/bin/python3 after routing. Check rotations in JLCPCB's placement preview before ordering.

    /usr/bin/python3 gen_fab.py [positions.csv]

Placements come from the routed board when its position export is given (kicad-cli pcb export pos
--format csv --units mm --side both, as export_jlc.sh writes it) or fab/routed_positions.csv exists:
parts nudged while routing must be placed where the routed copper expects them."""
import csv
import os
import sys
from collections import OrderedDict
import pcbnew
from circuit import PARTS

meta = {p["ref"]: p for p in PARTS}
POS = sys.argv[1] if len(sys.argv) > 1 else "fab/routed_positions.csv"
routed = {}
if os.path.exists(POS):
    for r in csv.DictReader(open(POS)):
        routed[r["Ref"]] = (float(r["PosX"]), float(r["PosY"]), float(r["Rot"]), r["Side"])
board = pcbnew.LoadBoard("clam_kbd.kicad_pcb")
groups = OrderedDict()
rows = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    p = meta.get(ref)
    if not p or p["dnp"] or p["footprint"].startswith("TestPoint"):
        continue
    hand = p["footprint"].startswith("Connector_PinHeader")          # OLED pads: hand-solder the module
    if hand:
        continue
    pos = fp.GetPosition()
    x, y, rot, side = (pcbnew.ToMM(pos.x), -pcbnew.ToMM(pos.y), fp.GetOrientationDegrees(),
                       "bottom" if fp.IsFlipped() else "top")
    if routed:
        if ref not in routed:
            raise SystemExit(f"{ref} is not on the routed board ({POS}): re-export it")
        rx, ry, rr, rs = routed[ref]
        if (abs(rx - x) > 0.001 or abs(ry - y) > 0.001 or (rr - rot) % 360 > 0.01 or rs != side):
            print(f"{ref}: placed as on the routed board ({rx:.3f}, {ry:.3f}) not the generated one ({x:.3f}, {y:.3f})")
        x, y, rot, side = rx, ry, rr, rs
    rows.append([ref, f"{x:.3f}mm", f"{y:.3f}mm", "Bottom" if side == "bottom" else "Top", f"{rot % 360:.0f}"])
    if hand:
        continue
    comment = "Key switch 5.1x5.1x1.5" if ref.startswith("SW") and ref not in ("SW100", "SW101", "SW102") else p["value"]
    key = (comment, p["footprint"].split(":")[1], p["lcsc"], p["mpn"])
    groups.setdefault(key, []).append(ref)
with open("fab/bom.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC", "MPN", "Qty"])
    for (val, fpn, lcsc, mpn), refs in groups.items():
        w.writerow([val, ",".join(sorted(refs, key=lambda r: (r.rstrip("0123456789"), int("0" + "".join(c for c in r if c.isdigit()))))),
                    fpn, lcsc, mpn, len(refs)])
with open("fab/cpl.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    w.writerows(rows)
print(len(groups), "BOM lines,", sum(len(v) for v in groups.values()), "placed parts")
