#!/bin/sh
# Trackball-breakout revision of the routed keyboard board (run in this folder on the Mac).
set -e
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$PY apply_tb_module.py clam_kbd_routed.kicad_pcb r1.kicad_pcb
# battery sense (RP2040 pin 38) sits between the trackball wires: move its via into the gap between
# the switch group (pins 31-36) and the LED group (pins 39-41), off the path of pin 39's wire
$PY - <<'PYEOF'
import math, pcbnew
b = pcbnew.LoadBoard("r1.kicad_pcb"); T, M = pcbnew.ToMM, pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(M(x), M(y))
net = b.FindNet("VBAT_SENSE")
for t in list(b.GetTracks()):
    if t.GetNetname() != "VBAT_SENSE":
        continue
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if all(math.hypot(T(p.x) - 88.4, T(p.y) - 61.2) < 0.5 for p in pts):   # old via and its two stubs
        b.Delete(t)
def seg(a, c, layer):
    s = pcbnew.PCB_TRACK(b); s.SetStart(V(*a)); s.SetEnd(V(*c)); s.SetWidth(M(0.15)); s.SetLayer(layer); s.SetNet(net); b.Add(s)
seg((88.18, 61.0), (88.35, 60.83), pcbnew.B_Cu)
seg((88.35, 60.83), (88.35, 61.15), pcbnew.In2_Cu); seg((88.35, 61.15), (88.55, 61.35), pcbnew.In2_Cu)
v = pcbnew.PCB_VIA(b); v.SetPosition(V(88.35, 60.83)); v.SetDrill(M(0.3)); v.SetNet(net)
try:
    v.SetWidth(M(0.5))
except TypeError:
    v.SetWidth(pcbnew.F_Cu, M(0.5))
b.Add(v); b.Save("r1.kicad_pcb"); print("battery-sense via moved to (88.35, 60.83)")
PYEOF
# LED resistors to header pins 9-11: short straight links
$PY fix_route.py r1.kicad_pcb r2.kicad_pcb J6.9 J6.10 J6.11
# the trackball bus: RP2040 pins 31-41 are in the header's order, so the wires run side by side on the
# outer layers (routed bottom line first). Clear a 5 mm circle of the crowded fan-out and the inner-layer
# tracks under the bus path first; reconnect what that disturbs afterwards (In2 allowed there)
$PY cluster_route.py r2.kicad_pcb r3.kicad_pcb 87.44 60.8 5.0 U1.41 U1.40 U1.39 U1.36 U1.35 U1.34 U1.32 U1.31 \
    --rip-also +3V3:89.75,59.4,91.8,59.7 --rip-also +3V3:91.2,59.55,91.8,62.65 --rip-also +3V3:88.5,58.3,89.8,59.6 \
    --rip-also VBAT_SENSE:88.5,61.3,124.5,97.3 \
    --rip-nets COL10,COL11,+1V1 --reconnect +3V3,VBAT_SENSE --outer --tries 12
$PY trim_dangling.py r3.kicad_pcb r4.kicad_pcb
# anything still at an odd angle (some came from rev A's fix-ups) -> 0/90 + 45 degrees
$PY straighten.py r4.kicad_pcb clam_kbd_tb_routed.kicad_pcb
cp clam_kbd_routed.kicad_pro clam_kbd_tb_routed.kicad_pro
$CLI pcb drc --refill-zones --save-board -o clam_kbd_tb_drc.rpt clam_kbd_tb_routed.kicad_pcb > /dev/null 2>&1 || true
grep '^\*\*' clam_kbd_tb_drc.rpt | head -5
