#!/bin/sh
# Export a JLCPCB order package (Gerbers + drill zip) from a routed board, after a clean DRC.
#   sh export_jlc.sh clam_kbd_v2_routed.kicad_pcb
# Needs KiCad 8+ (kicad-cli). On macOS the app's copy is used if kicad-cli is not on PATH.
set -e
BOARD="${1:-clam_kbd_v2_routed.kicad_pcb}"
CLI="$(command -v kicad-cli || echo /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli)"
OUT="jlc_out"
rm -rf "$OUT" && mkdir -p "$OUT/gerbers"

"$CLI" pcb drc --refill-zones --save-board --exit-code-violations -o "$OUT/drc.rpt" \
    --severity-error "$BOARD" > /dev/null 2>&1 || {
    echo "DRC has errors - see $OUT/drc.rpt (unconnected items must be routed first)"; grep '^\*\*' "$OUT/drc.rpt"; exit 1; }

"$CLI" pcb export gerbers -o "$OUT/gerbers" \
    -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --subtract-soldermask "$BOARD"
"$CLI" pcb export drill -o "$OUT/gerbers/" --excellon-separate-th --generate-map --map-format gerberx2 "$BOARD"
"$CLI" pcb export pos -o "$OUT/positions.csv" --format csv --units mm --side both "$BOARD"
(cd "$OUT/gerbers" && zip -q ../clam_kbd_gerbers.zip ./*)
echo "Done: $OUT/clam_kbd_gerbers.zip  (upload to JLCPCB: 4 layers, 1.0 mm, stackup JLC04101H-7628 or similar)"
echo "BOM / CPL for assembly: fab/bom.csv and fab/cpl.csv (from gen_fab.py), or $OUT/positions.csv"
