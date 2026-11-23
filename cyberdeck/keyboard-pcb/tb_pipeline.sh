#!/bin/sh
# Trackball-breakout revision of the routed keyboard board (run in this folder on the Mac).
set -e
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$PY apply_tb_module.py clam_kbd_routed.kicad_pcb r1.kicad_pcb
$PY fix_route.py r1.kicad_pcb r2.kicad_pcb J6.9 J6.10 J6.11 R20.1 R21.1 R22.1 J6.3 J6.4 J6.5 J6.6 J6.7 J6.1 --inner
# the RP2040's right-side pins 34-41 all need an escape now: redo that fan-out together
$PY cluster_route.py r2.kicad_pcb r3.kicad_pcb 87.44 60.8 3.5 U1.34 U1.35 U1.36 U1.38 U1.39 U1.40 U1.41 \
    --rip-also +3V3:89.75,59.4,91.8,59.7 --rip-also +3V3:91.2,59.55,91.8,62.65 \
    --rip-nets COL10,COL11,+1V1 --reconnect +3V3 --tries 24
$PY trim_dangling.py r3.kicad_pcb clam_kbd_tb_routed.kicad_pcb
cp clam_kbd_routed.kicad_pro clam_kbd_tb_routed.kicad_pro
$CLI pcb drc --refill-zones --save-board -o clam_kbd_tb_drc.rpt clam_kbd_tb_routed.kicad_pcb > /dev/null 2>&1 || true
grep '^\*\*' clam_kbd_tb_drc.rpt | head -5
