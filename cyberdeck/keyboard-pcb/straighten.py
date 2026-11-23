"""Replace any-angle track segments with a 0/90-degree + 45-degree pair wherever that keeps clearance.

    python straighten.py <in.kicad_pcb> <out.kicad_pcb>

Both corner choices are tried (straight part first, 45-degree part first).  Segment ends stay where
they are, so connectivity does not change; segments that another track joins in the middle are left
alone.  Clearance is checked against other nets' tracks, vias and pads (pad bounding boxes, so it is
conservative) and the board edge.  Refill zones afterwards.  KiCad 7 to 10.
"""
import math
import sys

import pcbnew

from trim_dangling import seg_dist, xy, is_via, via_r, uid

T, M = pcbnew.ToMM, pcbnew.FromMM


def odd(a, b):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 45
    return L > 0.02 and 0.2 < ang < 44.8


def octo(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = min(abs(dx), abs(dy))
    ex, ey = math.copysign(d, dx), math.copysign(d, dy)
    return [(b[0] - ex, b[1] - ey), (a[0] + ex, a[1] + ey)]


class Obstacles:
    """Copper per layer in 1 mm buckets: ('s', a, b, half width), ('c', centre, r), ('r', x0, y0, x1, y1)."""

    def __init__(self):
        self.items, self.cells, self.dead = {}, {}, set()

    def add(self, key, layer, net, shape):
        self.items[key] = (layer, net, shape)
        x0, y0, x1, y1 = self.bbox(shape)
        for i in range(int(math.floor(x0)) - 1, int(math.floor(x1)) + 2):
            for j in range(int(math.floor(y0)) - 1, int(math.floor(y1)) + 2):
                self.cells.setdefault((layer, i, j), []).append(key)

    @staticmethod
    def bbox(s):
        if s[0] == "s":
            (ax, ay), (bx, by), hw = s[1], s[2], s[3]
            return min(ax, bx) - hw, min(ay, by) - hw, max(ax, bx) + hw, max(ay, by) + hw
        if s[0] == "c":
            (cx, cy), r = s[1], s[2]
            return cx - r, cy - r, cx + r, cy + r
        return s[1], s[2], s[3], s[4]

    def near(self, layer, p):
        for k in self.cells.get((layer, int(math.floor(p[0])), int(math.floor(p[1]))), ()):
            if k not in self.dead:
                yield self.items[k]


def dist(s, p):
    if s[0] == "s":
        return seg_dist(p, s[1], s[2]) - s[3]
    if s[0] == "c":
        return math.dist(p, s[1]) - s[2]
    dx = max(s[1] - p[0], 0.0, p[0] - s[3])
    dy = max(s[2] - p[1], 0.0, p[1] - s[4])
    return math.hypot(dx, dy)


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    ds = board.GetDesignSettings()
    clr = 0.15
    for get in (lambda: ds.GetDefault().GetClearance(), lambda: ds.m_NetSettings.GetDefaultNetclass().GetClearance()):
        try:
            clr = T(get()); break
        except Exception:
            pass
    clr += 0.01
    try:
        edge_clr = T(ds.m_CopperEdgeClearance) + 0.01
    except AttributeError:
        edge_clr = 0.31
    layers = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    obs = Obstacles()
    for fp in board.GetFootprints():
        for i, p in enumerate(fp.Pads()):
            bb = p.GetBoundingBox()
            r = ("r", T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
            for ly in layers:
                if p.IsOnLayer(ly):
                    obs.add(("pad", fp.GetReference(), i, ly), ly, p.GetNetCode(), r)
            if p.GetDrillSize().x > 0:                  # a hole needs clearance on every layer
                for ly in layers:
                    obs.add(("hole", fp.GetReference(), i, ly), ly, p.GetNetCode(),
                            ("c", xy(p.GetPosition()), T(p.GetDrillSize().x) / 2 + 0.1))
    edges = []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            pts = [d.GetStart(), d.GetArcMid(), d.GetEnd()] if d.GetShape() == pcbnew.SHAPE_T_ARC else [d.GetStart(), d.GetEnd()]
            edges += [(xy(a), xy(b)) for a, b in zip(pts, pts[1:])]
    tracks = list(board.GetTracks())
    for t in tracks:
        if is_via(t):
            for ly in layers:
                obs.add((uid(t), ly), ly, t.GetNetCode(), ("c", xy(t.GetPosition()), via_r(t)))
        elif t.GetLayer() in layers:
            obs.add((uid(t), t.GetLayer()), t.GetLayer(), t.GetNetCode(),
                    ("s", xy(t.GetStart()), xy(t.GetEnd()), T(t.GetWidth()) / 2))

    ends = {}                                           # (net, layer) -> track ends; (net, None) -> vias
    for t in tracks:
        if is_via(t):
            ends.setdefault((t.GetNetCode(), None), []).append(xy(t.GetPosition()))
        else:
            ends.setdefault((t.GetNetCode(), t.GetLayer()), []).extend((xy(t.GetStart()), xy(t.GetEnd())))

    def clear(a, b, ly, net, hw):
        n = max(2, int(math.dist(a, b) / 0.02))
        for k in range(n + 1):
            p = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            for lyr, onet, s in obs.near(ly, p):
                if onet != net and dist(s, p) < hw + clr:
                    return False
            if any(seg_dist(p, e0, e1) < hw + edge_clr for e0, e1 in edges):
                return False
        return True

    fixed = left = 0
    for t in tracks:
        if is_via(t) or t.GetClass() != "PCB_TRACK" or t.GetLayer() not in layers:
            continue
        a, b = xy(t.GetStart()), xy(t.GetEnd())
        if not odd(a, b):
            continue
        ly, net, hw = t.GetLayer(), t.GetNetCode(), T(t.GetWidth()) / 2
        # leave it if another same-net track or via lands in its middle (a T-junction)
        tee = any(seg_dist(p, a, b) < hw + 0.01 and math.dist(p, a) > hw and math.dist(p, b) > hw
                  for p in ends.get((net, ly), []) + ends.get((net, None), []))
        if tee:
            left += 1
            continue
        obs.dead.add((uid(t), ly))                      # it must not block its own replacement
        for m in octo(a, b):
            if clear(a, m, ly, net, hw) and clear(m, b, ly, net, hw):
                for p, q in ((a, m), (m, b)):
                    s = pcbnew.PCB_TRACK(board)
                    s.SetStart(pcbnew.VECTOR2I(M(p[0]), M(p[1]))); s.SetEnd(pcbnew.VECTOR2I(M(q[0]), M(q[1])))
                    s.SetWidth(t.GetWidth()); s.SetLayer(ly); s.SetNet(t.GetNet()); s.SetLocked(t.IsLocked())
                    board.Add(s)
                    obs.add((uid(s), ly), ly, net, ("s", p, q, hw))
                board.Delete(t)
                fixed += 1
                break
        else:
            obs.dead.discard((uid(t), ly))
            left += 1
    print(f"straightened {fixed} segments; {left} left at their angle (no room, or a junction)")
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
