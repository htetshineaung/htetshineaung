"""Run KiCad DRC (pcbnew API) and summarise. Usage: /usr/bin/python3 run_drc.py report.rpt"""
import re, sys
from collections import Counter
import pcbnew

out = sys.argv[1] if len(sys.argv) > 1 else "drc.rpt"
board = pcbnew.LoadBoard("clam_kbd.kicad_pcb")
pcbnew.WriteDRCReport(board, out, pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(out).read()
kinds = Counter(re.findall(r"^\[(\w+)\]", txt, re.M))
for line in re.findall(r"^\*\* .*$", txt, re.M):
    print(line)
for k, v in kinds.most_common():
    print(f"{v:5d}  {k}")
