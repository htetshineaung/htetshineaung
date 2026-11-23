"""Finish the last few connections the autorouter leaves open: grid A* router on F.Cu/B.Cu.

    python fix_route.py <board.kicad_pcb> <out.kicad_pcb> REF.PAD [REF.PAD ...] [--lock] [--dsn] [--rip MM] [--inner] [--net NAME ...]

--rip MM first deletes unlocked tracks of other nets within MM of the pad, then routes the pad,
then reconnects every net it ripped up.

Tracks come out at 0, 45 or 90 degrees.  Each REF.PAD is routed to the nearest copper (pad, track or via) of the same net that is not
already connected to it.  Grid 0.05 mm, track 0.15 mm, the board's own clearance, vias 0.5/0.3 mm; inner layers are planes
(vias pass through them), so only the outer layers are searched (plus In2.Cu with --inner).  Refill zones afterwards.
"""
import heapq
import math
import sys

import pcbnew

NETS = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--net"]   # --net NAME: reconnect a whole net
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--net"]
LOCK = "--lock" in sys.argv          # lock what we add (run before the autorouter)
src, dst, targets = args[0], args[1], args[2:]
board = pcbnew.LoadBoard(src)
T, M = pcbnew.ToMM, pcbnew.FromMM
G = 0.05                          # grid, mm
TW, VIA_D, VIA_DR = 0.15, 0.5, 0.3


def _clearance():
    """Default net-class clearance of this board (+0.01 mm margin), whatever the KiCad version."""
    ds = board.GetDesignSettings()
    for get in (lambda: ds.GetDefault().GetClearance(),
                lambda: ds.m_NetSettings.GetDefaultNetclass().GetClearance(),
                lambda: ds.m_NetSettings.m_DefaultNetClass.GetClearance()):
        try:
            return T(get()) + 0.01
        except Exception:
            pass
    return 0.21


CLR = _clearance()
# --inner: also route on In2.Cu (the inner routing layer; its ground pour flows around tracks)
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu) + ((pcbnew.In2_Cu,) if "--inner" in sys.argv else ())


def seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def collect(net):
    """Obstacles per layer as (kind, data): other-net copper only; plus same-net targets."""
    obs = {ly: [] for ly in LAYERS}
    tgt = {ly: [] for ly in LAYERS}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            r = (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
            for ly in LAYERS:
                if p.IsOnLayer(ly):
                    (tgt if p.GetNetCode() == net else obs)[ly].append(("r", r, p))
            if p.GetDrillSize().x > 0:                       # drilled: blocks vias on any net
                obs["hole"] = obs.get("hole", []) + [("c", (T(p.GetPosition().x), T(p.GetPosition().y),
                                                             T(p.GetDrillSize().x) / 2), None)]
    for t in board.GetTracks():
        same = t.GetNetCode() == net
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            for ly in LAYERS:
                (tgt if same else obs)[ly].append(("c", (T(c.x), T(c.y), 0.3), t))
            obs["hole"] = obs.get("hole", []) + [("c", (T(c.x), T(c.y), 0.15), None)]
        else:
            a, b = t.GetStart(), t.GetEnd()
            d = ("s", (T(a.x), T(a.y), T(b.x), T(b.y), T(t.GetWidth()) / 2), t)
            if t.GetLayer() in obs:
                (tgt if same else obs)[t.GetLayer()].append(d)
            elif not same and t.GetLayer() == pcbnew.In2_Cu:  # not routed on, but a via passes through it
                obs.setdefault("via_only", []).append(d)
    edges = []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            pts = [d.GetStart(), d.GetArcMid(), d.GetEnd()] if d.GetShape() == pcbnew.SHAPE_T_ARC else [d.GetStart(), d.GetEnd()]
            for a, b in zip(pts, pts[1:]):
                edges.append((T(a.x), T(a.y), T(b.x), T(b.y)))
    for fp in board.GetFootprints():                         # mounting holes
        if fp.GetReference().startswith("H"):
            obs["hole"] = obs.get("hole", []) + [("c", (T(fp.GetPosition().x), T(fp.GetPosition().y), 1.1), None)]
    return obs, tgt, edges


def bbox(item):
    k, d, _ = item
    if k == "r":
        return d[0], d[1], d[2], d[3]
    if k == "c":
        return d[0] - d[2], d[1] - d[2], d[0] + d[2], d[1] + d[2]
    return min(d[0], d[2]) - d[4], min(d[1], d[3]) - d[4], max(d[0], d[2]) + d[4], max(d[1], d[3]) + d[4]


class Index:
    """1 mm buckets; an item is listed in every bucket within 1 mm of its bounding box."""
    def __init__(self, items, margin=1.0):
        self.b = {}
        for it in items:
            x0, y0, x1, y1 = bbox(it)
            for i in range(int(math.floor(x0 - margin)), int(math.floor(x1 + margin)) + 1):
                for j in range(int(math.floor(y0 - margin)), int(math.floor(y1 + margin)) + 1):
                    self.b.setdefault((i, j), []).append(it)

    def near(self, x, y):
        return self.b.get((int(math.floor(x)), int(math.floor(y))), ())


def dist_to(item, x, y):
    k, d, _ = item
    if k == "r":
        qx, qy = min(max(x, d[0]), d[2]), min(max(y, d[1]), d[3])
        return math.hypot(x - qx, y - qy)
    if k == "c":
        return math.hypot(x - d[0], y - d[1]) - d[2]
    return seg_dist(x, y, *d[:4]) - d[4]


def key(obj):
    return obj.m_Uuid.AsString()             # stable identity (Python wrappers are not)


def points(item):
    k, d, obj = item
    if k == "s":
        return [(d[0], d[1]), (d[2], d[3])]
    if k == "c":
        return [(d[0], d[1])]
    return [((d[0] + d[2]) / 2, (d[1] + d[3]) / 2)]


def island(pad, tgt):
    """ids of the same-net objects connected to `pad` (touching chains, vias join layers)."""
    items = {}
    for ly in LAYERS:
        for it in tgt[ly]:
            items.setdefault(key(it[2]), []).append((ly, it))
    seen, todo = {key(pad)}, [key(pad)]
    while todo:
        cur = items.get(todo.pop(), [])
        for ly, it in cur:
            for oid, lst in items.items():
                if oid in seen:
                    continue
                for ly2, it2 in lst:
                    if ly2 != ly:
                        continue
                    if any(dist_to(it2, x, y) <= 0.01 for x, y in points(it)) or \
                            any(dist_to(it, x, y) <= 0.01 for x, y in points(it2)):
                        seen.add(oid); todo.append(oid); break
    return seen


def route(ref, num):
    fp = board.FindFootprintByReference(ref)
    pad = next(p for p in fp.Pads() if p.GetNumber() == num)
    net = pad.GetNetCode()
    obs, tgt, edges = collect(net)
    idx = [Index(obs[ly]) for ly in LAYERS]
    hidx = Index(obs.get("hole", []))
    vidx = Index(obs.get("via_only", []))
    eidx = Index([("s", (*e, 0.0), None) for e in edges])
    sx, sy = T(pad.GetPosition().x), T(pad.GetPosition().y)
    slayer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    # targets: same-net copper that is not already connected to the start pad
    own = island(pad, tgt)
    goals = {ly: [it for it in tgt[ly] if key(it[2]) not in own] for ly in LAYERS}
    near = [it for ly in LAYERS for it in goals[ly]]
    if not near:
        print(ref, num, "no target"); return False
    gx, gy = min(((dist_to(it, sx, sy), it) for it in near), key=lambda z: z[0])[1][1][:2]
    box = (min(sx, gx) - 8, min(sy, gy) - 8, max(sx, gx) + 8, max(sy, gy) + 8)
    nx, ny = int((box[2] - box[0]) / G) + 1, int((box[3] - box[1]) / G) + 1
    half = TW / 2 + CLR

    cache = {}

    def ok(ix, iy, li):
        key = (ix, iy, li)
        if key in cache:
            return cache[key]
        x, y = box[0] + ix * G, box[1] + iy * G
        good = all(dist_to(e, x, y) > TW / 2 + 0.3 for e in eidx.near(x, y))
        if good:
            for it in idx[li].near(x, y):
                if dist_to(it, x, y) < half:
                    good = False; break
        cache[key] = good
        return good

    vcache = {}

    def via_ok(ix, iy):
        if (ix, iy) in vcache:
            return vcache[(ix, iy)]
        x, y = box[0] + ix * G, box[1] + iy * G
        good = all(dist_to(it, x, y) >= VIA_D / 2 + CLR for li in range(len(LAYERS)) for it in idx[li].near(x, y))
        good = good and all(dist_to(it, x, y) >= VIA_DR / 2 + 0.25 for it in hidx.near(x, y))
        good = good and all(dist_to(it, x, y) >= VIA_D / 2 + CLR for it in vidx.near(x, y))
        vcache[(ix, iy)] = good
        return good

    def at_goal(ix, iy, li):
        x, y = box[0] + ix * G, box[1] + iy * G
        return any(dist_to(it, x, y) <= 0.0 for it in goals[LAYERS[li]])

    six, siy, sli = round((sx - box[0]) / G), round((sy - box[1]) / G), LAYERS.index(slayer)
    # start from every point of the copper already joined to the pad (pad, its stubs, its vias)
    starts, exact = {(six, siy, sli)}, {}
    for li_, ly in enumerate(LAYERS):
        for it in tgt[ly]:
            if key(it[2]) in own:
                for (x, y) in points(it):
                    jx, jy = round((x - box[0]) / G), round((y - box[1]) / G)
                    if 0 <= jx < nx and 0 <= jy < ny:
                        starts.add((jx, jy, li_)); exact.setdefault((jx, jy, li_), (x, y))
    openq = [(0, 0, st, None) for st in starts]
    came, gbest = {}, {st: 0 for st in starts}
    moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    end = None
    steps = 0
    while openq and steps < 3_000_000:
        f, g, cur, parent = heapq.heappop(openq)
        if cur in came:
            continue
        came[cur] = parent
        steps += 1
        ix, iy, li = cur
        # leaving the start pad: allow cells inside it even though the pad is "same net"
        if at_goal(ix, iy, li):
            end = cur; break
        cand = [((ix + dx, iy + dy, li), c) for dx, dy, c in moves]
        cand += [((ix, iy, lj), 25) for lj in range(len(LAYERS)) if lj != li]   # via
        for nxt, c in cand:
            jx, jy, lj = nxt
            if not (0 <= jx < nx and 0 <= jy < ny) or nxt in came:
                continue
            if lj != li:
                if not via_ok(jx, jy):
                    continue
            elif not ok(jx, jy, lj):
                continue
            ng = g + c
            if ng < gbest.get(nxt, 1e18):
                gbest[nxt] = ng
                h = math.hypot(jx - round((gx - box[0]) / G), jy - round((gy - box[1]) / G))
                heapq.heappush(openq, (ng + h, ng, nxt, cur))
    if end is None:
        print(ref, num, "no path found after", steps, "steps; open", len(openq)); return False
    path = []
    n = end
    while n is not None:
        path.append(n); n = came[n]
    path.reverse()
    # emit: split at layer changes (vias), then pull each run tight with line-of-sight checks
    netinfo = pad.GetNet()
    pts = [(box[0] + p[0] * G, box[1] + p[1] * G, p[2]) for p in path]
    if path[0][:2] == (six, siy):
        pts[0] = (sx, sy, pts[0][2])
    elif path[0] in exact:                  # began on a track end or via: start exactly there, not on the grid
        pts[0] = (*exact[path[0]], pts[0][2])
    # the goal test uses a pad's bounding box, whose corners are off the copper of a round pad:
    # finish at the pad centre
    ex, ey, el = pts[-1]
    hit = [it for it in goals[LAYERS[el]] if dist_to(it, ex, ey) <= 0.0]
    if hit and hit[0][0] == "r":
        c = hit[0][2].GetPosition()
        pts.append((T(c.x), T(c.y), el))

    def free_xy(x, y, li):
        if not all(dist_to(e, x, y) > TW / 2 + 0.3 for e in eidx.near(x, y)):
            return False
        return all(dist_to(it, x, y) >= half for it in idx[li].near(x, y))

    def clear(a, b, li):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.02))
        for k in range(1, n):
            x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            if not free_xy(x, y, li) and not (k / n < 0.5 and math.hypot(x - sx, y - sy) < 0.5):
                return False
        return True

    def octo(a, b):
        """Corner points that join a and b with one 0/90 and one 45-degree segment: [] if a-b already
        is one of those angles, else the two choices (straight part first, 45-degree part first)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        ax, ay = abs(dx), abs(dy)
        if min(ax, ay) < 1e-6 or abs(ax - ay) < 1e-6:
            return []
        d = min(ax, ay)
        ex, ey = math.copysign(d, dx), math.copysign(d, dy)
        return [(b[0] - ex, b[1] - ey), (a[0] + ex, a[1] + ey)]

    def join(a, b, li):
        """Corner points of a clear 0/45/90-degree join from a to b ([] = straight), or None."""
        mids = octo(a, b)
        if not mids:
            return [] if clear(a, b, li) else None
        for m in mids:
            if clear(a, m, li) and clear(m, b, li):
                return [m]
        return None

    runs, cur = [], [pts[0]]
    for p in pts[1:]:
        if p[2] != cur[-1][2]:
            runs.append(cur); cur = [p]
        else:
            cur.append(p)
    runs.append(cur)
    nseg = nvia = 0
    for ri, run in enumerate(runs):
        li = run[0][2]
        i = 0
        while i < len(run) - 1:
            # pull the path tight, but only with 0/45/90-degree segments
            j = len(run) - 1
            mids = join(run[i], run[j], li)
            while mids is None and j > i + 1:
                j -= 1
                mids = join(run[i], run[j], li)
            chain = [run[i][:2]] + (mids or []) + [run[j][:2]]
            for a_, b_ in zip(chain, chain[1:]):
                add_track(a_, b_, LAYERS[li], netinfo); nseg += 1
            i = j
        if ri < len(runs) - 1:                                # via joins this run to the next one
            x, y = run[-1][0], run[-1][1]
            if (runs[ri + 1][0][0], runs[ri + 1][0][1]) != (x, y):
                runs[ri + 1].insert(0, (x, y, runs[ri + 1][0][2]))
            v = pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(M(x), M(y))); v.SetDrill(M(VIA_DR))
            try:
                v.SetWidth(M(VIA_D))
            except TypeError:
                v.SetWidth(pcbnew.F_Cu, M(VIA_D))
            v.SetNet(netinfo); v.SetLocked(LOCK); board.Add(v); nvia += 1
    print(f"{ref}.{num} ({pad.GetNetname()}): routed, {nseg} segments, {nvia} vias, {len(path)} grid steps")
    return True


def add_track(a, b, layer, net):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(M(a[0]), M(a[1]))); t.SetEnd(pcbnew.VECTOR2I(M(b[0]), M(b[1])))
    t.SetWidth(M(TW)); t.SetLayer(layer); t.SetNet(net); t.SetLocked(LOCK)
    board.Add(t)


def rip(ref, num, radius):
    """Delete unlocked other-net tracks/vias within `radius` mm of a pad; return their net codes."""
    pad = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    px, py = T(pad.GetPosition().x), T(pad.GetPosition().y)
    nets = set()
    for t in list(board.GetTracks()):
        if t.IsLocked() or t.GetNetCode() == pad.GetNetCode():
            continue
        if t.GetClass() == "PCB_VIA":
            d = math.hypot(T(t.GetPosition().x) - px, T(t.GetPosition().y) - py)
        else:
            a, b = t.GetStart(), t.GetEnd()
            d = seg_dist(px, py, T(a.x), T(a.y), T(b.x), T(b.y))
        if d < radius:
            nets.add(t.GetNetCode()); board.Delete(t)
    return nets


def reconnect(netcode):
    """Route every pad of a net that is cut off from the rest of it."""
    for _ in range(12):
        pads = [(fp.GetReference(), p.GetNumber(), p) for fp in board.GetFootprints() for p in fp.Pads()
                if p.GetNetCode() == netcode]
        _, tgt, _ = collect(netcode)
        all_keys = {key(p) for _, _, p in pads}
        todo = None
        for r, n, p in pads:
            if not all_keys <= island(p, tgt):
                todo = (r, n); break
        if todo is None:
            return True
        if not route(*todo):
            return False
    return False


RIP = float(sys.argv[sys.argv.index("--rip") + 1]) if "--rip" in sys.argv else 0.0
if RIP:
    targets = [t for t in targets if t != str(RIP) and "." in t and not t.replace(".", "").isdigit()]
for spec in targets:
    r, n = spec.split(".")
    ripped = rip(r, n, RIP) if RIP else set()
    if ripped:
        print(f"{spec}: ripped up {len(ripped)} nets nearby")
    route(r, n)
    for nc in ripped:
        name = board.GetNetInfo().GetNetItem(nc).GetNetname()
        print("  reconnect", name, "->", "ok" if reconnect(nc) else "FAILED")
for name in NETS:
    ni = board.FindNet(name)
    print("reconnect", name, "->", "ok" if ni and reconnect(ni.GetNetCode()) else "FAILED")
board.Save(dst)
if "--dsn" in sys.argv:                 # also write a Specctra file for the autorouter
    b2 = pcbnew.LoadBoard(dst)
    print("DSN export:", pcbnew.ExportSpecctraDSN(b2, dst.rsplit(".", 1)[0] + ".dsn"))
