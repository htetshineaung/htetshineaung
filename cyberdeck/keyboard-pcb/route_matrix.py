"""Pre-route the regular key matrix so the autorouter only has to finish the MCU area.

    python route_matrix.py <in.kicad_pcb> <out.kicad_pcb> <out.dsn>

Pattern (all tracks locked, so Freerouting keeps them):
  * Columns, top layer: each switch's left COL pad -> short stub left -> one vertical trace per
    column in the 1.4 mm gap between switch columns.
  * Rows, bottom layer: each diode cathode -> short stub toward the back -> one horizontal trace
    per row, 1.7 mm behind the diodes.
  * Each diode anode -> bottom trace -> via beside the switch -> top trace into the switch's
    second pad.
  * The space bar's second switch is tied to the first one on the top layer.
Diodes that had to be moved off-centre (above the Pi's USB jacks) and the mouse L/R keys are
left for the autorouter.
Works with KiCad 7 and KiCad 10 pcbnew.
"""
import sys
from collections import defaultdict

import pcbnew

from circuit import PARTS

src, dst, dsn = sys.argv[1], sys.argv[2], sys.argv[3]
board = pcbnew.LoadBoard(src)
for old in list(board.GetTracks()):       # start from a clean board: drop any earlier routing
    board.Delete(old)
mm = pcbnew.FromMM
W = mm(0.25)
COL_GAP_X = mm(1.2)        # column trace sits this far left of the switch's left pads
ROW_OFFSET = mm(1.7)       # row trace sits this far behind (smaller KiCad y) the diode
VIA_INSET = mm(1.325)      # via sits this far from the pin-2 pad toward the switch centre

fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
meta = {p["ref"]: p for p in PARTS}
netinfo = board.GetNetInfo()


def net(name):
    return netinfo.GetNetItem(name)


def V(x, y):
    return pcbnew.VECTOR2I(int(x), int(y))


def track(a, b, layer, n):
    if a.x == b.x and a.y == b.y:
        return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(a); t.SetEnd(b); t.SetWidth(W); t.SetLayer(layer); t.SetNet(n); t.SetLocked(True)
    board.Add(t)


def via(p, n):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(p); v.SetDrill(mm(0.3))
    try:
        v.SetWidth(mm(0.6))
    except TypeError:                       # KiCad 9/10 padstack API
        v.SetWidth(pcbnew.F_Cu, mm(0.6))
    v.SetNet(n); v.SetLocked(True)
    board.Add(v)


def pads(ref, number):
    return [p for p in fps[ref].Pads() if p.GetNumber() == number]


key_sw = [r for r, p in meta.items() if p["symbol"] == "Switch:SW_Push" and r not in ("SW100", "SW101")]
diodes = [r for r, p in meta.items() if r.startswith("D") and r[1:].isdigit() and int(r[1:]) > 100]
anode_to_sw = defaultdict(list)
for r in key_sw:
    anode_to_sw[meta[r]["pins"]["2"]].append(r)

# --- columns (top)
col_stubs = defaultdict(list)            # x_line -> [(y, net)]
space_second = None
for r in key_sw:
    p = meta[r]
    if p["value"] in ("MOUSE_L", "MOUSE_R"):
        continue
    sws = anode_to_sw[p["pins"]["2"]]
    if p["value"] == "SPACE" and len(sws) > 1 and fps[r].GetPosition().x > min(fps[s].GetPosition().x for s in sws):
        space_second = r                     # the right-hand space switch: tied below
        continue
    left = min(pads(r, "1"), key=lambda q: q.GetPosition().x)
    lp = left.GetPosition()
    x_line = lp.x - COL_GAP_X
    track(lp, V(x_line, lp.y), pcbnew.F_Cu, left.GetNet())
    col_stubs[(x_line, left.GetNetname())].append(lp.y)
for (x_line, name), ys in col_stubs.items():
    if len(ys) > 1:
        track(V(x_line, min(ys)), V(x_line, max(ys)), pcbnew.F_Cu, net(name))

if space_second:                             # tie the two space-bar switches together (top layer)
    first = next(s for s in anode_to_sw[meta[space_second]["pins"]["2"]] if s != space_second)
    a1 = max(pads(first, "1"), key=lambda q: q.GetPosition().x).GetPosition()
    b1 = min(pads(space_second, "1"), key=lambda q: q.GetPosition().x).GetPosition()
    track(a1, b1, pcbnew.F_Cu, net(meta[first]["pins"]["1"]))
    a2 = max(pads(first, "2"), key=lambda q: q.GetPosition().x).GetPosition()
    b2 = min(pads(space_second, "2"), key=lambda q: q.GetPosition().x).GetPosition()
    track(a2, b2, pcbnew.F_Cu, net(meta[first]["pins"]["2"]))

# --- rows (bottom) and anodes
row_stubs = defaultdict(list)            # (row net, y_line) -> [x]
for d in diodes:
    p = meta[d]
    sws = anode_to_sw[p["pins"]["2"]]
    sw = min(sws, key=lambda s: fps[s].GetPosition().x)
    if meta[sw]["value"] in ("MOUSE_L", "MOUSE_R"):
        continue
    dpos, spos = fps[d].GetPosition(), fps[sw].GetPosition()
    if abs(dpos.x - spos.x) > mm(0.5):       # moved off-centre: leave for the autorouter
        continue
    cath = pads(d, "1")[0]; an = pads(d, "2")[0]
    cp, ap = cath.GetPosition(), an.GetPosition()
    y_line = cp.y - ROW_OFFSET
    track(cp, V(cp.x, y_line), pcbnew.B_Cu, cath.GetNet())
    row_stubs[(cath.GetNetname(), y_line)].append(cp.x)
    # anode: via beside the switch pin-2 pad on the anode's side
    pin2 = [q for q in pads(sw, "2")]
    target = min(pin2, key=lambda q: abs(q.GetPosition().x - ap.x)).GetPosition()
    vpos = V(target.x, target.y - VIA_INSET)
    track(ap, V(vpos.x, ap.y), pcbnew.B_Cu, an.GetNet())
    track(V(vpos.x, ap.y), vpos, pcbnew.B_Cu, an.GetNet())
    via(vpos, an.GetNet())
    track(vpos, target, pcbnew.F_Cu, an.GetNet())
for (name, y_line), xs in row_stubs.items():
    if len(xs) > 1:
        track(V(min(xs), y_line), V(max(xs), y_line), pcbnew.B_Cu, net(name))

board.Save(dst)
board = pcbnew.LoadBoard(dst)
print("tracks:", len(board.GetTracks()), "| DSN export:", pcbnew.ExportSpecctraDSN(board, dsn))
