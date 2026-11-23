"""Re-do a tight fan-out: rip the given nets near a spot, then route their pads in different orders
until every one gets out (fix_route.py does each route).

    python cluster_route.py <in.kicad_pcb> <out.kicad_pcb> X Y RADIUS REF.PAD [REF.PAD ...] [--rip-also NET:x0,y0,x1,y1 ...] [--tries N]
"""
import math
import random
import subprocess
import sys

import pcbnew

T = pcbnew.ToMM
argv = sys.argv[1:]
tries = int(argv[argv.index("--tries") + 1]) if "--tries" in argv else 40
also = [argv[i + 1] for i, a in enumerate(argv) if a == "--rip-also"]
extra = argv[argv.index("--rip-nets") + 1].split(",") if "--rip-nets" in argv else []   # ripped too, reconnected last
recon = argv[argv.index("--reconnect") + 1].split(",") if "--reconnect" in argv else []  # reconnected only
pos = [a for i, a in enumerate(argv) if not a.startswith("--") and
       (i == 0 or argv[i - 1] not in ("--tries", "--rip-also", "--rip-nets", "--reconnect"))]
src, dst, cx, cy, rad, pads = pos[0], pos[1], float(pos[2]), float(pos[3]), float(pos[4]), pos[5:]


def ripped_board(path):
    b = pcbnew.LoadBoard(src)
    nets = set()
    for spec in pads:
        ref, num = spec.split(".")
        nets |= {p.GetNetname() for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num}
    nets |= set(extra)
    boxes = []
    for a in also:
        n, r = a.split(":")
        boxes.append((n, tuple(float(v) for v in r.split(","))))
    gone = []
    clipped = 0
    for t in b.GetTracks():
        pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        pts = [(T(p.x), T(p.y)) for p in pts]
        inside = [math.hypot(x - cx, y - cy) < rad for x, y in pts]
        if t.GetNetname() in nets and all(inside):
            gone.append(t)
        elif t.GetNetname() in nets and t.GetClass() == "PCB_TRACK" and any(inside):
            # long segment leaving the cleared circle: cut it back to the circle
            (ix, iy), (ox, oy) = (pts[0], pts[1]) if inside[0] else (pts[1], pts[0])
            lo, hi = 0.0, 1.0                        # bisect for the crossing point
            for _ in range(40):
                m = (lo + hi) / 2
                if math.hypot(ix + (ox - ix) * m - cx, iy + (oy - iy) * m - cy) < rad:
                    lo = m
                else:
                    hi = m
            px, py = ix + (ox - ix) * hi, iy + (oy - iy) * hi
            p = pcbnew.VECTOR2I(pcbnew.FromMM(px), pcbnew.FromMM(py))
            if inside[0]:
                t.SetStart(p)
            else:
                t.SetEnd(p)
            clipped += 1
        elif any(t.GetNetname() == n and all(r[0] <= x <= r[2] and r[1] <= y <= r[3] for x, y in pts) for n, r in boxes):
            gone.append(t)
    for t in gone:
        b.Delete(t)
    b.Save(path)
    print("clipped", clipped, "long segments at the circle")
    return len(gone)


tmp = dst.rsplit(".", 1)[0] + "_ripped.kicad_pcb"
print("ripped", ripped_board(tmp), "items")
orders = [list(pads), list(reversed(pads))]
mid = len(pads) // 2
orders.append(sorted(pads, key=lambda p: abs(pads.index(p) - mid)))
orders.append(sorted(pads, key=lambda p: -abs(pads.index(p) - mid)))
rng = random.Random(1)
while len(orders) < tries:
    o = list(pads); rng.shuffle(o)
    if o not in orders:
        orders.append(o)
best = None
for i, order in enumerate(orders):
    out = subprocess.run([sys.executable, "fix_route.py", tmp, dst] + order + ["--inner"] +
                         [x for n in extra + recon for x in ("--net", n)],
                         capture_output=True, text=True).stdout
    failed = [l.split()[0] + "." + l.split()[1] for l in out.splitlines() if "no path" in l or "no target" in l]
    failed += [l.split()[1] for l in out.splitlines() if l.startswith("reconnect") and "FAILED" in l]
    print(f"try {i + 1}: {' '.join(order)} -> {'OK' if not failed else 'failed ' + ' '.join(failed)}", flush=True)
    if not failed:
        print(out)
        sys.exit(0)
    if best is None or len(failed) < best[0]:
        best = (len(failed), order)
print("no order routed everything; best:", best)
sys.exit(1)
