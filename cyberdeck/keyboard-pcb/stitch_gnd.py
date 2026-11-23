"""Give every small-part GND (and, on the 4-layer board, +3V3) pad its own via into the planes, so no pad depends on the
pour squeezing between the RP2040's decoupling caps.

    python stitch_gnd.py <in.kicad_pcb> <out.kicad_pcb> <out.dsn>           # before autorouting
    python stitch_gnd.py <in.kicad_pcb> <out.kicad_pcb> <out.dsn> --grid    # after autorouting

* Each SMD GND pad (caps, crystal, LDO, connectors, LED, buttons, test pad) gets a 0.6/0.3 via
  0.8-1.4 mm away, in the first free direction, joined by a short 0.3 mm track on the pad's layer.
* The RP2040 exposed pad gets a 3x3 grid of vias (thermal + ground return).
* --grid (run on the routed board): a 3 mm grid of stitching vias wherever there is room, so the
  top and bottom pours become one ground plane with no cut-off islands.
Placement is checked against all other-net copper on both layers (pads, tracks, vias) and the
board edge.  Everything added is locked, so Freerouting routes around it.
Works with KiCad 7 and KiCad 10 pcbnew.
"""
import math
import sys

import pcbnew

src, dst, dsn = sys.argv[1], sys.argv[2], sys.argv[3]
GRID = "--grid" in sys.argv
board = pcbnew.LoadBoard(src)
mm, to_mm = pcbnew.FromMM, pcbnew.ToMM
CLR = 0.22            # mm, copper to copper (rule is 0.2)
VIA_D, VIA_DRILL, TW = 0.6, 0.3, 0.3

gnd = board.GetNetInfo().GetNetItem("GND")
gnd_code = gnd.GetNetCode()

# --- obstacles: (kind, data, half-width) in mm
rects, segs, circles = [], [], []
for fp in board.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        # same-net SMD pads are not obstacles for that net (through-hole pads always are: drills)
        net = p.GetNetCode() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD else -1
        rects.append((to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom()), net))
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA":            # every via, GND too: keeps drill-to-drill spacing
        c = t.GetPosition()
        circles.append((to_mm(c.x), to_mm(c.y), 0.3))      # all vias on this board are 0.6 mm
    else:
        a, b = t.GetStart(), t.GetEnd()
        segs.append((to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y), to_mm(t.GetWidth()) / 2, t.GetNetCode()))
edge = board.GetBoardEdgesBoundingBox()
ex0, ey0, ex1, ey1 = to_mm(edge.GetLeft()), to_mm(edge.GetTop()), to_mm(edge.GetRight()), to_mm(edge.GetBottom())
holes = [(to_mm(fp.GetPosition().x), to_mm(fp.GetPosition().y)) for fp in board.GetFootprints()
         if fp.GetReference().startswith("H")]
edge_segs = []
for d in board.GetDrawings():
    if d.GetLayer() != pcbnew.Edge_Cuts:
        continue
    if d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        pts = [d.GetStart(), d.GetEnd()]
    elif d.GetShape() == pcbnew.SHAPE_T_ARC:
        pts = [d.GetStart(), d.GetArcMid(), d.GetEnd()]
    else:
        continue
    for a, b in zip(pts, pts[1:]):
        edge_segs.append((to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y), 0.0))


def inside_outline(px, py):
    """Ray casting against the Edge.Cuts outline (arcs as two chords)."""
    n = 0
    for (x0, y0, x1, y1, _) in edge_segs:
        if (y0 > py) != (y1 > py) and px < x0 + (py - y0) * (x1 - x0) / (y1 - y0):
            n += 1
    return n % 2 == 1


def seg_dist(px, py, s):
    x0, y0, x1, y1 = s[:4]
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def free(px, py, r, edge_clr=0.4):
    """Is a copper disc of radius r at (px, py) clear of all copper of other nets than CUR?"""
    for (a, b, c, d, n) in rects:
        if n == CUR:
            continue
        qx, qy = min(max(px, a), c), min(max(py, b), d)
        if math.hypot(px - qx, py - qy) < r + CLR:
            return False
    for s in segs:
        if s[5] != CUR and seg_dist(px, py, s) < r + s[4] + CLR:
            return False
    for (cx, cy, cr) in circles:
        if math.hypot(px - cx, py - cy) < r + cr + CLR:
            return False
    for s in edge_segs:
        if seg_dist(px, py, s) < r + edge_clr:
            return False
    for (hx, hy) in holes:
        if math.hypot(px - hx, py - hy) < r + 2.0:
            return False
    if not inside_outline(px, py):
        return False
    return ex0 + r + edge_clr < px < ex1 - r - edge_clr and ey0 + r + edge_clr < py < ey1 - r - edge_clr


def add_via(x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetDrill(mm(VIA_DRILL))
    try:
        v.SetWidth(mm(VIA_D))
    except TypeError:                       # KiCad 9/10 padstack API
        v.SetWidth(pcbnew.F_Cu, mm(VIA_D))
    v.SetNet(CUR_NET); v.SetLocked(True)
    board.Add(v)
    circles.append((x, y, VIA_D / 2))


def add_track(a, b, layer, width=None):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
    t.SetWidth(mm(width or TW)); t.SetLayer(layer); t.SetNet(CUR_NET); t.SetLocked(True)
    board.Add(t)


CUR_NET, CUR = gnd, gnd_code
n_via = n_skip = 0
skipped = []
if GRID:
    CLR = 0.45                                   # leave room for the pour to flow round the via
    x = ex0 + 2.0
    while x < ex1 - 2.0:
        y = ey0 + 2.0
        while y < ey1 - 2.0:
            if free(x, y, VIA_D / 2, 1.0):
                add_via(x, y); n_via += 1
            y += 3.0
        x += 3.0
# plane nets: GND always; +3V3 too when there is a +3V3 zone (the 4-layer board's In2 plane)
plane_nets = [gnd] + [z.GetNet() for z in board.Zones() if z.GetNetname() == "+3V3"][:1]
for CUR_NET in ([] if GRID else plane_nets):
    CUR = CUR_NET.GetNetCode()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for p in fp.Pads():
            if p.GetNetCode() != CUR or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            c = p.GetPosition(); px, py = to_mm(c.x), to_mm(c.y)
            layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
            try:
                sz = p.GetSize()
            except TypeError:                                # KiCad 9/10 padstack API
                sz = p.GetSize(layer)
            w, h = to_mm(sz.x), to_mm(sz.y)
            if ref == "U1" and min(w, h) > 2.5 and CUR == gnd_code:              # exposed pad: 3x3 via grid inside it
                for i in (-1, 0, 1):
                    for j in (-1, 0, 1):
                        add_via(px + 1.0 * i, py + 1.0 * j); n_via += 1
                continue
            if ref == "U1" and CUR == gnd_code:
                continue                                     # pin 19 (TESTEN) is tied to the EP below
            # prefer directions pointing away from the footprint centre
            fc = fp.GetPosition(); ax, ay = px - to_mm(fc.x), py - to_mm(fc.y)
            base = math.atan2(ay, ax) if (ax or ay) else 0.0
            qfn = ref == "U1"                      # 0.4 mm pitch: thin stub straight out of the package
            if qfn:
                base = 0.0 if abs(ax) >= abs(ay) else math.pi / 2
                base += math.pi if (ax if abs(ax) >= abs(ay) else ay) < 0 else 0.0
            tw = 0.2 if qfn else TW
            done = False
            for dist in ((1.2, 1.4, 1.7) if qfn else (0.85, 1.0, 1.2, 1.4, 1.7)):
                for k in range(1 if qfn else 16):
                    ang = base + (k // 2 + 1) * (1 if k % 2 else -1) * math.pi / 8 if k else base
                    vx, vy = px + dist * math.cos(ang), py + dist * math.sin(ang)
                    if not free(vx, vy, VIA_D / 2):
                        continue
                    # the joining track must be clear too (skip the part that sits inside the pad)
                    ok = True
                    start = (max(w, h) / 2 + 0.15) / dist if qfn else 0.4   # QFN: only beyond the pad
                    for f in [start + (0.85 - start) * i / 4 for i in range(5)]:
                        tx, ty = px + (vx - px) * f, py + (vy - py) * f
                        if not free(tx, ty, tw / 2, 0.3):
                            ok = False; break
                    if not ok:
                        continue
                    add_track((px, py), (vx, vy), layer, tw); add_via(vx, vy)
                    n_via += 1; done = True
                    break
                if done:
                    break
            if not done:
                n_skip += 1; skipped.append(f"{ref}.{p.GetNumber()}")

# RP2040 pin 19 (TESTEN, GND): short stub straight into the exposed pad
u1 = next(fp for fp in board.GetFootprints() if fp.GetReference() == "U1")
p19 = next(p for p in u1.Pads() if p.GetNumber() == "19")
ep = next(p for p in u1.Pads() if p.GetNumber() == "57")
lay = pcbnew.F_Cu if p19.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
a, b = p19.GetPosition(), ep.GetPosition()
# go perpendicular to the package edge until in line with the EP edge
ax, ay, bx, by = to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y)
if abs(ax - bx) > abs(ay - by):
    end = (bx + math.copysign(1.4, ax - bx), ay)
else:
    end = (ax, by + math.copysign(1.4, ay - by))
if not GRID:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a); t.SetEnd(pcbnew.VECTOR2I(mm(end[0]), mm(end[1])))
    t.SetWidth(mm(0.2)); t.SetLayer(lay); t.SetNet(gnd); t.SetLocked(True)
    board.Add(t)

board.Save(dst)
board = pcbnew.LoadBoard(dst)
print(f"GND vias added: {n_via}, pads without room: {n_skip} {skipped}")
print("tracks:", len(board.GetTracks()), "| DSN export:", pcbnew.ExportSpecctraDSN(board, dsn))
