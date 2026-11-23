"""Delete dead-end track stubs and dangling vias, e.g. after parts were removed from a routed board.

    python trim_dangling.py <in.kicad_pcb> <out.kicad_pcb> [NET ...]

Without NET names every net is trimmed.  First splits any segment that another same-net segment
or via joins in its middle (a T-junction), so a stub can be cut back exactly to the junction; then
repeatedly deletes segments with an end that touches nothing of their own net (pad, via, other
segment; for GND also its filled pour; touching means the copper overlaps, as KiCad counts it) and non-GND vias that join fewer than two segments and no pad (a via that only joins tracks on
one layer is replaced by joining them at its centre).
GND vias are kept: they stitch the planes.  Works with KiCad 7 to 10.
"""
import math
import sys

import pcbnew

T, M = pcbnew.ToMM, pcbnew.FromMM
EPS = 0.005                          # mm: two ends closer than this are joined
PLANE_NETS = ("GND",)
COPPER = (pcbnew.F_Cu, pcbnew.B_Cu)


def V(p):
    return pcbnew.VECTOR2I(M(p[0]), M(p[1]))


def xy(v):
    return (T(v.x), T(v.y))


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def is_via(t):
    return t.GetClass() == "PCB_VIA"


def via_r(v):
    try:
        return T(v.GetWidth(pcbnew.F_Cu)) / 2          # KiCad 9+: per-layer width
    except (TypeError, NotImplementedError):
        return T(v.GetWidth()) / 2


def uid(o):
    return o.m_Uuid.AsString()


def pad_hit(pad, p, layer, tol=0.0):
    """Is point p on the pad's copper, or within tol mm of it (a track end's half width)?"""
    if not pad.IsOnLayer(layer):
        return False
    pt, acc = V(p), M(tol)
    for call in (lambda: pad.HitTest(pt, acc, layer), lambda: pad.HitTest(pt, acc), lambda: pad.HitTest(pt)):
        try:
            return bool(call())
        except (TypeError, NotImplementedError):
            pass
    bb = pad.GetBoundingBox()
    return T(bb.GetLeft()) - tol <= p[0] <= T(bb.GetRight()) + tol and T(bb.GetTop()) - tol <= p[1] <= T(bb.GetBottom()) + tol


def zone_hit(zones, p, layer, tol=0.0):
    pt = V(p)
    for z in zones:
        if not z.IsOnLayer(layer):
            continue
        try:
            if z.HitTestFilledArea(layer, pt, M(tol)):
                return True
        except (TypeError, NotImplementedError, AttributeError):
            pass
    return False


def new_seg(board, like, a, b):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(V(a)); t.SetEnd(V(b)); t.SetWidth(like.GetWidth()); t.SetLayer(like.GetLayer())
    t.SetNet(like.GetNet()); t.SetLocked(like.IsLocked())
    board.Add(t)
    return t


def split_junctions(board, items):
    """Split straight segments where another same-net segment end or via lands on them (anywhere
    within the copper, not only on the centre line), so a stub beyond the junction can be cut off."""
    segs = [t for t in items if t.GetClass() == "PCB_TRACK"]
    ends = {}                                           # layer -> (point, half width) of segment ends
    for t in items:
        if not is_via(t):
            hw = T(t.GetWidth()) / 2
            ends.setdefault(t.GetLayer(), []).extend(((xy(t.GetStart()), hw), (xy(t.GetEnd()), hw)))
    vpts = [(xy(v.GetPosition()), via_r(v)) for v in items if is_via(v)]
    added, gone = [], set()
    for s in segs:
        a, b = xy(s.GetStart()), xy(s.GetEnd())
        hw = T(s.GetWidth()) / 2
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L <= 2 * hw:
            continue
        cuts = set()
        for p, r in ends.get(s.GetLayer(), []) + vpts:
            if seg_dist(p, a, b) > max(EPS, hw + r):
                continue
            t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (L * L)
            if hw < t * L < L - hw:                     # not at (within a half width of) either end
                cuts.add(round(t, 6))
        if not cuts:
            continue
        chain = [a] + [(a[0] + dx * t, a[1] + dy * t) for t in sorted(cuts)] + [b]
        added += [new_seg(board, s, p, q) for p, q in zip(chain, chain[1:])]
        gone.add(uid(s))
    keep = [t for t in items if uid(t) not in gone]
    for t in items:
        if uid(t) in gone:
            board.Delete(t)
    return keep + added, len(gone)


class Grid:
    """1 mm buckets of segment bounding boxes, for quick 'what is near this point' lookups."""

    def __init__(self, segs):
        self.cells = {}
        for i, (_, _, a, b, hw) in enumerate(segs):
            for cx in range(int(math.floor(min(a[0], b[0]) - hw)), int(math.floor(max(a[0], b[0]) + hw)) + 1):
                for cy in range(int(math.floor(min(a[1], b[1]) - hw)), int(math.floor(max(a[1], b[1]) + hw)) + 1):
                    self.cells.setdefault((cx, cy), []).append(i)

    def near(self, p):
        return self.cells.get((int(math.floor(p[0])), int(math.floor(p[1]))), [])


def trim(board, names=None):
    """Trim dead ends on the named nets (all nets if None).  Returns (segments, vias) deleted."""
    by_net = {}
    for t in board.GetTracks():
        if t.GetNetCode() == 0 or (names and t.GetNetname() not in names):
            continue
        by_net.setdefault(t.GetNetCode(), []).append(t)
    pads, zones = {}, {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.setdefault(p.GetNetCode(), []).append(
                (p, T(bb.GetLeft()) - EPS, T(bb.GetTop()) - EPS, T(bb.GetRight()) + EPS, T(bb.GetBottom()) + EPS))
    for z in board.Zones():
        if not z.GetIsRuleArea():
            zones.setdefault(z.GetNetCode(), []).append(z)
    nseg = nvia = 0
    for nc, items in by_net.items():
        plane = items[0].GetNetname() in PLANE_NETS
        items, _ = split_junctions(board, items)
        npads = pads.get(nc, [])

        def on_pad(p, layer, tol):
            return any(x0 - tol <= p[0] <= x1 + tol and y0 - tol <= p[1] <= y1 + tol and pad_hit(pd, p, layer, tol)
                       for pd, x0, y0, x1, y1 in npads)

        while True:
            segs = [(uid(t), t.GetLayer(), xy(t.GetStart()), xy(t.GetEnd()), T(t.GetWidth()) / 2)
                    for t in items if not is_via(t)]
            vias = [(uid(t), xy(t.GetPosition()), via_r(t)) for t in items if is_via(t)]
            grid = Grid(segs)

            def touches(p, layer, me, mine):
                """Does the end p of segment `me` (half width `mine`) overlap other copper of its net?"""
                for i in grid.near(p):
                    u, ly, a, b, hw = segs[i]
                    if u != me and ly == layer and seg_dist(p, a, b) <= max(EPS, hw + mine):
                        return True
                if any(math.dist(p, c) <= r + mine for _, c, r in vias):
                    return True
                if on_pad(p, layer, mine):
                    return True
                return plane and zone_hit(zones.get(nc, []), p, layer, mine)

            dead = {u for u, ly, a, b, hw in segs if not touches(a, ly, u, hw) or not touches(b, ly, u, hw)}
            added = []
            if not plane:
                objs = {uid(t): t for t in items}
                for u, c, r in vias:
                    if any(on_pad(c, ly, r) for ly in COPPER):
                        continue
                    hits = [(su, ly, a if math.dist(c, a) <= r + hw else b) for su, ly, a, b, hw in segs
                            if su not in dead and (math.dist(c, a) <= r + hw or math.dist(c, b) <= r + hw)]
                    if len(hits) < 2:
                        dead.add(u)
                    elif len({ly for _, ly, _ in hits}) < 2:
                        # it only joins tracks on one layer: join them at its centre instead, drop the via
                        for su, ly, p in hits:
                            if math.dist(p, c) > EPS:
                                added.append(new_seg(board, objs[su], p, c))
                        dead.add(u)
            if not dead:
                break
            keep = [t for t in items if uid(t) not in dead] + added
            for t in [t for t in items if uid(t) in dead]:  # ids are read before anything is deleted
                if is_via(t):
                    nvia += 1
                else:
                    nseg += 1
                board.Delete(t)
            items = keep
    return nseg, nvia


if __name__ == "__main__":
    src, dst, nets = sys.argv[1], sys.argv[2], sys.argv[3:]
    b = pcbnew.LoadBoard(src)
    s, v = trim(b, set(nets) or None)
    print(f"trimmed {s} dead-end segments and {v} dangling vias")
    b.Save(dst)
