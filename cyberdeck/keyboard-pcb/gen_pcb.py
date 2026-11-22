"""Generate clam_kbd.kicad_pcb from circuit.py with KiCad's own pcbnew API (run with /usr/bin/python3).

    /usr/bin/python3 gen_pcb.py            # place + nets + zones -> clam_kbd.kicad_pcb, clam_kbd.dsn
    /usr/bin/python3 gen_pcb.py --ses X    # import a Freerouting session, refill zones, save
"""
import json
import math
import sys

import pcbnew

from circuit import PARTS, BOARD, HOLES, AUTO, NO_BOTTOM_ZONE

FP_DIR = "/usr/share/kicad/footprints"
OX, OY = 20.0, 120.0           # case (x, y-up)  ->  KiCad (x, y-down)


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY - y))


def mm(v):
    return pcbnew.FromMM(v)


def build():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.0))
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetTrackWidth(mm(0.2)); nc.SetClearance(mm(0.2)); nc.SetViaDiameter(mm(0.6)); nc.SetViaDrill(mm(0.3))
    ds.m_TrackMinWidth = mm(0.15); ds.m_MinClearance = mm(0.15); ds.m_ViasMinSize = mm(0.5); ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.3)

    # nets
    netinfo = {}
    for p in PARTS:
        for net in p["pins"].values():
            if net not in netinfo:
                ni = pcbnew.NETINFO_ITEM(board, net)
                board.Add(ni)
                netinfo[net] = ni

    # outline (Edge.Cuts): rounded rectangle with the trackball notch on the right edge
    x0, y0, x1, y1, r = BOARD["x0"], BOARD["y0"], BOARD["x1"], BOARD["y1"], BOARD["r"]
    nx0, ny0, _, ny1 = BOARD["notch"]

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    def arc(c, a0):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC)
        pts = [(c[0] + r * math.cos(math.radians(a0 + d)), c[1] + r * math.sin(math.radians(a0 + d))) for d in (0, 45, 90)]
        s.SetArcGeometry(P(*pts[0]), P(*pts[1]), P(*pts[2])); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    seg((x0 + r, y0), (x1 - r, y0)); arc((x1 - r, y0 + r), 270)
    seg((x1, y0 + r), (x1, ny0)); seg((x1, ny0), (nx0, ny0)); seg((nx0, ny0), (nx0, ny1)); seg((nx0, ny1), (x1, ny1))
    seg((x1, ny1), (x1, y1 - r)); arc((x1 - r, y1 - r), 0)
    seg((x1 - r, y1), (x0 + r, y1)); arc((x0 + r, y1 - r), 90)
    seg((x0, y1 - r), (x0, y0 + r)); arc((x0 + r, y0 + r), 180)

    # footprints
    uuids = json.load(open("sch_uuids.json"))
    fps = {}
    for p in PARTS:
        lib, name = p["footprint"].split(":")
        fp = pcbnew.FootprintLoad(f"{FP_DIR}/{lib}.pretty", name)
        if fp is None:
            raise SystemExit(f"footprint not found: {p['footprint']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(p["ref"]); fp.SetValue(p["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + uuids[p["ref"]]))
        for k in ("MPN", "LCSC"):
            if p[k.lower()]:
                fp.SetProperty(k, p[k.lower()])
        board.Add(fp)                                   # must be on the board before Flip()
        fps[p["ref"]] = fp
        fp.SetPosition(P(*p["pos"]))
        fp.SetOrientationDegrees(p["rot"])
        if p["side"] == "bottom":
            fp.Flip(fp.GetPosition(), False)
        for pad in fp.Pads():
            net = p["pins"].get(pad.GetNumber())
            if net:
                pad.SetNet(netinfo[net])
        # silkscreen: key switches and key diodes carry no reference (the matrix is regular);
        # small passives get 0.8 mm text
        ref_txt = fp.Reference()
        if (p["ref"].startswith("SW") and p["ref"] not in ("SW100", "SW101")) or \
                (p["ref"].startswith("D") and p["ref"][1:].isdigit() and int(p["ref"][1:]) > 100):
            ref_txt.SetVisible(False)
        elif p["ref"][0] in "CR" and p["ref"][1:].isdigit():
            ref_txt.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); ref_txt.SetTextThickness(mm(0.12))
        fp.Value().SetVisible(False)

    auto_place(board, fps)

    # M2 mounting holes (screws go up into bosses under the deck)
    for i, (hx, hy) in enumerate(HOLES):
        fp = pcbnew.FootprintLoad(f"{FP_DIR}/MountingHole.pretty", "MountingHole_2.2mm_M2")
        fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_2.2mm_M2"))
        fp.SetReference(f"H{i + 1}"); fp.SetPosition(P(hx, hy)); fp.Reference().SetVisible(False)
        board.Add(fp)

    # ground pour on both layers
    gnd = netinfo["GND"]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(gnd); z.SetIsFilled(False)
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            ol.Append(P(x, y))
        board.Add(z)

    # labels
    t = pcbnew.PCB_TEXT(board)
    t.SetText("CLAMSHELL KB  rev A\nRP2040 · 42 keys + L/R")
    t.SetPosition(P(30.0, 25.0)); t.SetLayer(pcbnew.B_SilkS); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2))); t.SetTextThickness(mm(0.18))
    board.Add(t)
    return board


def _box(fp, grow=0.15):
    b = fp.GetBoundingBox(False, False)
    g = mm(grow)
    return (b.GetLeft() - g, b.GetTop() - g, b.GetRight() + g, b.GetBottom() + g)


def _hit(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _inside_board(bx):
    """Inside the outline (with margin), outside the trackball notch and the no-bottom zone."""
    x0, y0 = P(BOARD["x0"] + 0.6, BOARD["y1"] - 0.6), P(BOARD["x1"] - 0.6, BOARD["y0"] + 0.6)
    if bx[0] < x0.x or bx[2] > y0.x or bx[1] < x0.y or bx[3] > y0.y:
        return False
    n = BOARD["notch"]
    a, c = P(n[0] - 0.5, n[3] + 0.5), P(n[2], n[1] - 0.5)
    if _hit(bx, (a.x, a.y, c.x, c.y)):
        return False
    z = NO_BOTTOM_ZONE
    a, c = P(z[0], z[3]), P(z[2], z[1])
    return not _hit(bx, (a.x, a.y, c.x, c.y))


def auto_place(board, fps):
    """Put each AUTO part on its anchor's side, `dist` mm outward from the anchor pin(s),
    oriented radially, then nudge to the nearest spot that collides with nothing."""
    side_of = {p["ref"]: p["side"] for p in PARTS}
    placed = [r for r in fps if r not in AUTO]
    for ref, (anchor, pins, dist) in AUTO.items():
        fp, afp = fps[ref], fps[anchor]
        pads = [pd for pd in afp.Pads() if pd.GetNumber() in pins]
        px = sum(pd.GetPosition().x for pd in pads) / len(pads)
        py = sum(pd.GetPosition().y for pd in pads) / len(pads)
        cx, cy = afp.GetPosition().x, afp.GetPosition().y
        dx, dy = px - cx, py - cy
        if abs(dx) >= abs(dy):
            ux, uy, rot = (1 if dx > 0 else -1), 0, 0
        else:
            ux, uy, rot = 0, (1 if dy > 0 else -1), 90
        tx, ty = px + ux * mm(dist) - (dx if anchor in ("U1", "U3") and False else 0), py + uy * mm(dist)
        if ref == "U3":
            rot = 90 if rot == 0 else 0
        others = [_box(fps[o]) for o in placed if side_of.get(o) == side_of[ref] or fps[o].GetLayer() == fp.GetLayer()]
        for hx, hy in HOLES:                            # M2 holes + screw head keep-out
            c = P(hx, hy)
            others.append((c.x - mm(2.6), c.y - mm(2.6), c.x + mm(2.6), c.y + mm(2.6)))
        best = None
        for ring in range(0, 60):
            r = mm(0.25 * ring)
            n = max(1, ring * 4)
            for k in range(n):
                ang = 2 * math.pi * k / n
                fp.SetPosition(pcbnew.VECTOR2I(int(tx + r * math.cos(ang)), int(ty + r * math.sin(ang))))
                fp.SetOrientationDegrees(rot if side_of[ref] == "top" else (180 - rot) % 360 if False else rot)
                bx = _box(fp)
                if _inside_board(bx) and not any(_hit(bx, o) for o in others):
                    best = True
                    break
            if best:
                break
        if not best:
            print("WARN: no free spot for", ref)
        placed.append(ref)


def fill(board):
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


if __name__ == "__main__":
    if "--ses" in sys.argv:
        board = pcbnew.LoadBoard("clam_kbd.kicad_pcb")
        ok = pcbnew.ImportSpecctraSES(board, sys.argv[sys.argv.index("--ses") + 1])
        print("imported SES:", ok)
        fill(board)
        board.Save("clam_kbd.kicad_pcb")
    else:
        build().Save("clam_kbd.kicad_pcb")
        board = pcbnew.LoadBoard("clam_kbd.kicad_pcb")      # reload: fully initialised board
        fill(board)
        board.Save("clam_kbd.kicad_pcb")
        print("DSN export:", pcbnew.ExportSpecctraDSN(board, "clam_kbd.dsn"))
    print("footprints", len(board.GetFootprints()), "nets", board.GetNetCount(), "tracks", len(board.GetTracks()))
