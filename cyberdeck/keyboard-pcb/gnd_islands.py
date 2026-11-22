"""Find ground-pour islands that are not tied to the main ground plane (board must be zone-filled).

    python gnd_islands.py <board.kicad_pcb> [--prune <out.kicad_pcb>]

Each filled outline of the GND zones (every copper layer) is a node; vias, through-hole pads and
GND tracks join nodes.  Everything not in the largest group is reported with the GND pads it
holds.  --prune deletes stitching vias (vias with no track on them) that only join stray
islands, so the next zone fill drops those islands.
"""
import sys
from collections import defaultdict

import pcbnew

path = sys.argv[1]
prune = sys.argv[sys.argv.index("--prune") + 1] if "--prune" in sys.argv else None
board = pcbnew.LoadBoard(path)
T = pcbnew.ToMM
gnd = board.GetNetInfo().GetNetItem("GND").GetNetCode()
COPPER = [ly for ly in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu) if board.IsLayerEnabled(ly)]

# nodes: (layer, outline index) of each filled GND polygon
islands = []                                         # (layer, SHAPE_POLY_SET, idx, area)
for z in board.Zones():
    if z.GetNetCode() != gnd:
        continue
    for layer in COPPER:
        if not z.IsOnLayer(layer):
            continue
        ps = z.GetFilledPolysList(layer)
        for i in range(ps.OutlineCount()):
            islands.append((layer, ps, i, abs(ps.Outline(i).Area())))

parent = list(range(len(islands)))


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    a, b = find(a), find(b)
    if a != b:
        parent[a] = b


def hits(pt, layer):
    return [k for k, (ly, ps, i, _) in enumerate(islands) if ly == layer and ps.Outline(i).PointInside(pt)]


# connectors: vias, through-hole pads, GND tracks (both ends)
vias, track_ends = [], set()
for t in board.GetTracks():
    if t.GetNetCode() != gnd:
        continue
    if t.GetClass() == "PCB_VIA":
        vias.append(t)
    else:
        for p in (t.GetStart(), t.GetEnd()):
            track_ends.add((p.x, p.y))
groups = []                                          # (kind, item, island ids)
for v in vias:
    p = v.GetPosition()
    groups.append(("via", v, sum((hits(p, ly) for ly in COPPER), [])))
pad_islands = {}
for fp in board.GetFootprints():
    for pd in fp.Pads():
        if pd.GetNetCode() != gnd:
            continue
        p = pd.GetPosition()
        ids = []
        for layer in COPPER:
            if pd.IsOnLayer(layer):
                ids += hits(p, layer)
        pad_islands[f"{fp.GetReference()}.{pd.GetNumber()}"] = (pd, ids)
        groups.append(("pad", pd, ids))
for t in board.GetTracks():                          # a GND track joins whatever its ends touch
    if t.GetNetCode() == gnd and t.GetClass() != "PCB_VIA":
        ids = hits(t.GetStart(), t.GetLayer()) + hits(t.GetEnd(), t.GetLayer())
        groups.append(("track", t, ids))
# pads and vias joined by a track: union through shared track ends
for kind, item, ids in groups:
    for a in ids[1:]:
        union(ids[0], a)
end_ids = defaultdict(list)
for kind, item, ids in groups:
    if kind == "track":
        for p in (item.GetStart(), item.GetEnd()):
            end_ids[(p.x, p.y)] += ids
    elif ids:
        p = item.GetPosition()
        end_ids[(p.x, p.y)] += ids
for ids in end_ids.values():
    for a in ids[1:]:
        union(ids[0], a)

area = defaultdict(float)
for k, isl in enumerate(islands):
    area[find(k)] += isl[3]
main = max(area, key=area.get)
stray = defaultdict(list)
for k, isl in enumerate(islands):
    if find(k) != main:
        stray[find(k)].append(k)
print(f"{len(islands)} GND fill islands, {len(stray)} groups not joined to the main plane")
pruned = 0
for g, ks in stray.items():
    pads = [n for n, (pd, ids) in pad_islands.items() if ids and find(ids[0]) == g]
    bb = islands[ks[0]][1].Outline(islands[ks[0]][2]).BBox()
    print(f"  group at ({T(bb.Centre().x):.2f}, {T(bb.Centre().y):.2f}) mm, "
          f"{sum(islands[k][3] for k in ks) / 1e12:.2f} mm^2, pads: {pads or '-'}")
    if prune and not pads:
        for kind, item, ids in groups:
            if kind == "via" and ids and find(ids[0]) == g:
                p = item.GetPosition()
                if (p.x, p.y) not in track_ends:
                    board.Delete(item); pruned += 1
if prune:
    board.Save(prune)
    print("pruned stitching vias:", pruned)
