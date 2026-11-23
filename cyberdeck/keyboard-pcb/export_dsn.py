"""Export a Specctra DSN for Freerouting with the GND pours hidden, so GND gets routed with real
tracks like any other net (the pours alone cannot reach into the RP2040's decoupling ring).
The session is later imported into the board that still has its pours.

    python export_dsn.py <board.kicad_pcb> <out.dsn>
"""
import os
import shutil
import sys

import pcbnew

src, dsn = sys.argv[1], sys.argv[2]
tmp = os.path.splitext(dsn)[0] + "_nozone.kicad_pcb"
pro = os.path.splitext(src)[0] + ".kicad_pro"
if os.path.exists(pro):                       # keep the same design rules for the temporary copy
    shutil.copy(pro, os.path.splitext(tmp)[0] + ".kicad_pro")
board = pcbnew.LoadBoard(src)
for z in list(board.Zones()):
    board.Delete(z)
board.Save(tmp)
board = pcbnew.LoadBoard(tmp)
print("zones left:", len(list(board.Zones())), "| DSN export:", pcbnew.ExportSpecctraDSN(board, dsn))
