"""Compare KiCad's exported netlist (clam_kbd.net) with circuit.py, pin by pin."""
import sys
from kicad_lib import parse_sexp
from circuit import nets

n = parse_sexp(open(sys.argv[1] if len(sys.argv) > 1 else "clam_kbd.net").read())
netsec = next(x for x in n if isinstance(x, list) and x[0] == "nets")
got = {}
for net in netsec[1:]:
    name = next(x for x in net if isinstance(x, list) and x[0] == "name")[1].lstrip("/")
    got[name] = sorted((next(y for y in x if isinstance(y, list) and y[0] == "ref")[1],
                        next(y for y in x if isinstance(y, list) and y[0] == "pin")[1])
                       for x in net if isinstance(x, list) and x[0] == "node")
want = {k: sorted(v) for k, v in nets().items()}
bad = [k for k, v in want.items() if [x for x in got.get(k, []) if not x[0].startswith("#")] != v]
extra = [k for k in got if k not in want and not k.startswith("unconnected")]
for k in bad:
    print("MISMATCH", k, want[k][:5], got.get(k, [])[:5])
print(f"circuit nets {len(want)} | KiCad nets {len(got)} | mismatches {len(bad)} | unexpected {extra} | "
      f"no-connect pins {sum(1 for k in got if k.startswith('unconnected'))}")
sys.exit(1 if bad or extra else 0)
