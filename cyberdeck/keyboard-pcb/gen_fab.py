"""JLCPCB assembly files from the board: bom.csv (Comment, Designator, Footprint, LCSC) and cpl.csv.
Run with /usr/bin/python3 after routing. Check rotations in JLCPCB's placement preview before ordering."""
import csv
from collections import OrderedDict
import pcbnew
from circuit import PARTS

meta = {p["ref"]: p for p in PARTS}
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
    rows.append([ref, f"{pcbnew.ToMM(pos.x):.3f}mm", f"{-pcbnew.ToMM(pos.y):.3f}mm",
                 "Bottom" if fp.IsFlipped() else "Top", f"{fp.GetOrientationDegrees() % 360:.0f}"])
    if hand:
        continue
    comment = "Key switch 5.1x5.1x1.5" if ref.startswith("SW") and ref not in ("SW100", "SW101") else p["value"]
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
