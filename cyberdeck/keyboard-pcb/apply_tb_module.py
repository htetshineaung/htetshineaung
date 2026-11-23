"""Turn the routed built-in-hall revision of the keyboard board into the trackball-breakout revision
without re-routing the whole board.

    python apply_tb_module.py <routed_old.kicad_pcb> <out.kicad_pcb>

1. deletes the hall sensors U4-U7, their caps C20-C23, pull-ups R20-R23, the click switch SW102,
   their old silkscreen outline, and every track of the five trackball nets (re-routed to J6 later);
2. trims the +3V3 / GND stubs that led to the removed parts (trim_dangling.py);
3. adds the ball window (Edge.Cuts), the breakout header J6, LED resistors R20-R22, screw holes H6/H7
   and the module outline on the fab layers, exactly where gen_pcb.py puts them;
4. deletes other-net copper that the new pads, holes and window clash with (prints those nets);
5. hides MPN/LCSC fields that KiCad 8+ printed on the silkscreen, puts RP2040 pins 31/40/41 (GPIO20/28/29) on the LED nets, then checks every pad's net against
   the generated clam_kbd.kicad_pcb (hash).
Next: route the open pads with fix_route.py --inner, trim_dangling.py, then export_jlc.sh (refill + DRC).
Coordinates are KiCad board millimetres of the generated clam_kbd.kicad_pcb.  KiCad 7 to 10.
"""
import hashlib
import math
import os
import sys

import pcbnew

from trim_dangling import trim, seg_dist, via_r, xy, is_via

T, M = pcbnew.ToMM, pcbnew.FromMM
KICAD7 = pcbnew.GetMajorMinorVersion().startswith("7.")
FP_DIR = next((d for d in (os.environ.get("KICAD_FP_DIR", ""), "/usr/share/kicad/footprints",
                            "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints") if d and os.path.isdir(d)),
              "/usr/share/kicad/footprints")

REMOVE = "U4 U5 U6 U7 C20 C21 C22 C23 R20 R21 R22 R23 SW102".split()
TB_NETS = ("TB_UP", "TB_DOWN", "TB_LEFT", "TB_RIGHT", "TB_CLICK")
WINDOW = (137.0, 69.0, 151.0, 83.0, 2.0)          # x0, y0, x1, y1, corner radius
MODULE = (129.6, 62.3, 151.8, 91.3)               # breakout board outline (under the PCB)
OLD_SILK = (137.5, 72.0, 150.5, 86.5)             # old 12 x 12 mechanism square + "TRACKBALL" label
R_FIELDS = {"MPN": "0402WGF1000TCE", "LCSC": "C25076"}
ADD = [  # ref, library, footprint, x, y, rotation, bottom side, value, pad nets, fields, schematic uuid
    ("J6", "Connector_PinHeader_2.54mm", "PinHeader_1x11_P2.54mm_Vertical", 130.6, 64.3, 0, False, "TRACKBALL",
     {"1": "+3V3", "2": "GND", "3": "TB_CLICK", "4": "TB_RIGHT", "5": "TB_LEFT", "6": "TB_DOWN", "7": "TB_UP",
      "9": "TB_LED_G", "10": "TB_LED_R", "11": "TB_LED_B"},
     {"MPN": "trackball breakout header (solder the module's pins through)"}, "76760a05-ed06-4948-b003-c472cc825898"),
    ("R20", "Resistor_SMD", "R_0402_1005Metric", 126.3, 84.8, 0, True, "100R", {"1": "TB_R", "2": "TB_LED_R"},
     R_FIELDS, "5399cd42-72f3-4bd9-894c-11d7845af9b8"),
    ("R21", "Resistor_SMD", "R_0402_1005Metric", 126.3, 86.8, 0, True, "100R", {"1": "TB_G", "2": "TB_LED_G"},
     R_FIELDS, "2b38a748-47d4-49a9-8510-8e0beae4855f"),
    ("R22", "Resistor_SMD", "R_0402_1005Metric", 126.3, 88.8, 0, True, "100R", {"1": "TB_B", "2": "TB_LED_B"},
     R_FIELDS, "60831840-9dbc-4d4d-bf11-dece1fd75c2a"),
    ("H6", "MountingHole", "MountingHole_2.2mm_M2", 150.4, 63.7, 0, False, None, {}, {}, None),
    ("H7", "MountingHole", "MountingHole_2.2mm_M2", 150.4, 87.0, 0, False, None, {}, {}, None),
]
U1_NETS = {"31": "TB_R", "40": "TB_G", "41": "TB_B"}
EXPECTED_HASH = "7fbcbfe8a38f688b06b1e93676eebc53"  # pad_net_hash() of the generated clam_kbd.kicad_pcb
CLR, EDGE, HOLE_R, HOLE_CLR, SCREW_R = 0.15 + 0.03, 0.3 + 0.03, 1.1, 0.25 + 0.03, 2.0
COPPER = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)


def V(x, y):
    return pcbnew.VECTOR2I(M(x), M(y))


def pad_net_hash(board):
    lines = sorted(f"{fp.GetReference()}|{p.GetNumber()}|{p.GetNetname()}"
                   for fp in board.GetFootprints() for p in fp.Pads() if p.GetNumber())
    return hashlib.md5("\n".join(lines).encode()).hexdigest()


def pt_rect(p, r):
    dx = max(r[0] - p[0], 0.0, p[0] - r[2])
    dy = max(r[1] - p[1], 0.0, p[1] - r[3])
    return math.hypot(dx, dy)


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _intersect(p1, p2, q1, q2):
    d1, d2 = _cross(q1, q2, p1), _cross(q1, q2, p2)
    d3, d4 = _cross(p1, p2, q1), _cross(p1, p2, q2)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def seg_rect(a, b, r):
    """Distance between segment ab and an axis-aligned rectangle (0 if they overlap)."""
    if pt_rect(a, r) == 0 or pt_rect(b, r) == 0:
        return 0.0
    cs = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    if any(_intersect(a, b, cs[i], cs[(i + 1) % 4]) for i in range(4)):
        return 0.0
    return min([seg_dist(c, a, b) for c in cs] + [pt_rect(a, r), pt_rect(b, r)])


def net(board, name):
    ni = board.FindNet(name)
    if ni is None:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
    return ni


def shape(board, layer, kind, pts, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    if kind == "seg":
        s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*pts[0])); s.SetEnd(V(*pts[1]))
    else:
        s.SetShape(pcbnew.SHAPE_T_ARC); s.SetArcGeometry(V(*pts[0]), V(*pts[1]), V(*pts[2]))
    s.SetLayer(layer); s.SetWidth(M(width)); board.Add(s)


def add_window(board):
    x0, y0, x1, y1, r = WINDOW

    def arc(cx, cy, a0):
        shape(board, pcbnew.Edge_Cuts, "arc", [(cx + r * math.cos(math.radians(a0 + d)),
                                               cy + r * math.sin(math.radians(a0 + d))) for d in (0, 45, 90)])
    shape(board, pcbnew.Edge_Cuts, "seg", [(x0 + r, y0), (x1 - r, y0)]); arc(x1 - r, y0 + r, 270)
    shape(board, pcbnew.Edge_Cuts, "seg", [(x1, y0 + r), (x1, y1 - r)]); arc(x1 - r, y1 - r, 0)
    shape(board, pcbnew.Edge_Cuts, "seg", [(x1 - r, y1), (x0 + r, y1)]); arc(x0 + r, y1 - r, 90)
    shape(board, pcbnew.Edge_Cuts, "seg", [(x0, y1 - r), (x0, y0 + r)]); arc(x0 + r, y0 + r, 180)
    mx0, my0, mx1, my1 = MODULE
    cs = [(mx0, my0), (mx1, my0), (mx1, my1), (mx0, my1)]
    for layer in (pcbnew.F_Fab, pcbnew.B_Fab):
        for a, b in zip(cs, cs[1:] + cs[:1]):
            shape(board, layer, "seg", [a, b], 0.12)
    t = pcbnew.PCB_TEXT(board)
    t.SetText("TRACKBALL BREAKOUT UNDER THIS BOARD"); t.SetPosition(V((mx0 + mx1) / 2, my0 + 1.2))
    t.SetLayer(pcbnew.F_Fab); t.SetTextSize(pcbnew.VECTOR2I(M(0.8), M(0.8))); t.SetTextThickness(M(0.12))
    board.Add(t)


def add_parts(board):
    new = []
    for ref, lib, name, x, y, rot, bottom, value, nets, fields, uuid in ADD:
        fp = pcbnew.FootprintLoad(f"{FP_DIR}/{lib}.pretty", name)
        if fp is None:
            raise SystemExit(f"footprint not found: {lib}:{name} in {FP_DIR}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        if value:
            fp.SetValue(value)
        if uuid:
            fp.SetPath(pcbnew.KIID_PATH("/" + uuid))
        for k, v in fields.items():
            try:
                fp.SetProperty(k, v)
            except AttributeError:                  # KiCad 8+
                fp.SetField(k, v)
        hide_fields(fp)
        board.Add(fp)
        fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
        if bottom:
            if KICAD7:
                fp.Flip(fp.GetPosition(), False)
            else:
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for pad in fp.Pads():
            if pad.GetNumber() in nets:
                pad.SetNet(net(board, nets[pad.GetNumber()]))
        if ref.startswith("H"):
            fp.Reference().SetVisible(False)
        elif ref.startswith("R"):
            fp.Reference().SetTextSize(pcbnew.VECTOR2I(M(0.8), M(0.8))); fp.Reference().SetTextThickness(M(0.12))
        fp.Value().SetVisible(False)
        new.append(fp)
    return new


def clear_clashes(board, new):
    """Delete other-net tracks and vias that the new pads, the screw holes or the window clash with."""
    zones = []                                      # (net code or -1 for all, layers, kind, geometry, gap)
    for fp in new:
        if fp.GetReference().startswith("H"):
            c = xy(fp.GetPosition())
            zones.append((-1, (pcbnew.F_Cu, pcbnew.B_Cu), "circle", (c, SCREW_R), 0.0))
            zones.append((-1, (pcbnew.In1_Cu, pcbnew.In2_Cu), "circle", (c, HOLE_R), HOLE_CLR))
            continue
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            r = (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
            zones.append((p.GetNetCode(), tuple(ly for ly in COPPER if p.IsOnLayer(ly)), "rect", r, CLR))
    zones.append((-1, COPPER, "rect", WINDOW[:4], EDGE))
    ripped, gone = {}, []
    for t in board.GetTracks():
        for nc, layers, kind, g, gap in zones:
            if nc == t.GetNetCode() and nc > 0:
                continue
            if is_via(t):
                c, w = xy(t.GetPosition()), via_r(t)
                d = pt_rect(c, g) if kind == "rect" else math.dist(c, g[0]) - g[1]
            else:
                if t.GetLayer() not in layers:
                    continue
                a, b, w = xy(t.GetStart()), xy(t.GetEnd()), T(t.GetWidth()) / 2
                d = seg_rect(a, b, g) if kind == "rect" else seg_dist(g[0], a, b) - g[1]
            if d < gap + w:
                ripped[t.GetNetname()] = ripped.get(t.GetNetname(), 0) + 1
                gone.append(t)
                break
    for t in gone:
        board.Delete(t)
    return ripped


def hide_fields(fp):
    """Hide a footprint's MPN/LCSC fields (KiCad 8+ shows new fields on the silkscreen); count them."""
    try:
        fields = fp.GetFields()
    except AttributeError:                              # KiCad 7: properties, never printed
        return 0
    n = 0
    for f in fields:
        if f.GetName() in ("MPN", "LCSC") and f.IsVisible():
            f.SetVisible(False); n += 1
    return n


def hide_part_fields(board):
    """Boards made by gen_pcb.py with KiCad 8+ printed every MPN/LCSC on the silkscreen: hide them."""
    return sum(hide_fields(fp) for fp in board.GetFootprints())


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    print("hid", hide_part_fields(board), "MPN/LCSC texts on the silkscreen")
    for ref in REMOVE:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            raise SystemExit(f"{ref} not on {src}: is this the routed hall-sensor revision?")
        board.Delete(fp)
    old = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.F_SilkS and
           ((d.GetClass() == "PCB_TEXT" and d.GetText() == "TRACKBALL") or
            (d.GetClass() == "PCB_SHAPE" and all(pt_rect(xy(p), OLD_SILK) == 0 for p in (d.GetStart(), d.GetEnd()))))]
    for d in old:
        board.Delete(d)
    tb = [t for t in board.GetTracks() if t.GetNetname() in TB_NETS]
    for t in tb:
        board.Delete(t)
    print(f"removed {len(REMOVE)} parts, {len(old)} old silkscreen items, {len(tb)} trackball-net tracks/vias")
    s, v = trim(board, {"+3V3", "GND"})
    print(f"trimmed {s} +3V3/GND stub segments and {v} vias that led to the removed parts")

    add_window(board)
    new = add_parts(board)
    ripped = clear_clashes(board, new)
    print("deleted clashing copper:", ", ".join(f"{k} ({n})" for k, n in sorted(ripped.items())) or "none")
    if ripped:
        s, v = trim(board, set(ripped))
        print(f"trimmed {s} segments and {v} vias left without a pad by that")
    u1 = board.FindFootprintByReference("U1")
    for pad in u1.Pads():
        if pad.GetNumber() in U1_NETS:
            if pad.GetNetname():
                print(f"warning: U1.{pad.GetNumber()} was on {pad.GetNetname()}")
            pad.SetNet(net(board, U1_NETS[pad.GetNumber()]))

    h = pad_net_hash(board)
    print("pad nets match the generated board" if h == EXPECTED_HASH else
          f"WARNING: pad nets differ from the generated board ({h})")
    board.Save(dst)
    print("saved", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
