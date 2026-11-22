"""Tiny helpers to read KiCad 7 symbol libraries (pins, positions) for the generator."""
import re

SYM_DIR = "/usr/share/kicad/symbols"
FP_DIR = "/usr/share/kicad/footprints"


class Q(str):
    """A string that was quoted in the source file."""


BARE = {"yes", "no", "hide", "default", "left", "right", "top", "bottom", "mirror", "power_in", "power_out",
        "input", "output", "bidirectional", "passive", "tri_state", "unspecified", "no_connect",
        "open_collector", "open_emitter", "free", "line", "inverted", "clock", "none", "outline",
        "background", "dash", "solid", "dot", "dash_dot", "eeschema", "italic", "bold", "x", "y",
        "inverted_clock", "input_low", "clock_low", "output_low", "edge_clock_high", "non_logic", "fields_autoplaced"}


def parse_sexp(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(Q(t[1:-1].replace('\\"', '"')) if t.startswith('"') else t)
    return cur[0]


NUM = re.compile(r'^-?\d+(\.\d+)?$')
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def _atom(s, head):
    if isinstance(s, Q):
        return '"' + str(s).replace('"', '\\"') + '"'
    if head or NUM.match(s) or s in BARE or UUID.match(s):
        return s
    return '"' + s.replace('"', '\\"') + '"'


def dump_sexp(node, indent=0):
    """Serialise back to KiCad S-expression text."""
    if not isinstance(node, list):
        return _atom(node, False)
    parts = []
    for i, n in enumerate(node):
        if isinstance(n, list):
            parts.append("\n" + "  " * (indent + 1) + dump_sexp(n, indent + 1))
        else:
            parts.append(_atom(n, i == 0))
    return "(" + " ".join(parts) + ")"


_cache = {}


def load_lib(name):
    if name not in _cache:
        _cache[name] = parse_sexp(open(f"{SYM_DIR}/{name}.kicad_sym").read())
    return _cache[name]


def find_symbol(lib_id):
    """Return the full symbol definition (resolving `extends`) renamed to lib_id."""
    lib_name, sym_name = lib_id.split(":")
    lib = load_lib(lib_name)
    syms = {n[1]: n for n in lib if isinstance(n, list) and n and n[0] == "symbol"}
    s = syms[sym_name]
    ext = next((n for n in s if isinstance(n, list) and n[0] == "extends"), None)
    if ext:
        base = syms[ext[1]]
        props = {p[1]: p for p in s if isinstance(p, list) and p[0] == "property"}
        merged = ["symbol", lib_id]
        for n in base[2:]:
            if isinstance(n, list) and n[0] == "property" and n[1] in props:
                merged.append(props[n[1]])
            elif isinstance(n, list) and n[0] == "symbol":
                merged.append(["symbol", n[1].replace(ext[1], sym_name, 1)] + n[2:])
            else:
                merged.append(n)
        return merged
    out = ["symbol", lib_id] + s[2:]
    return out


def symbol_pins(sym):
    """[(number, name, electrical_type, x, y, angle, length, unit)] for unit 1/0 bodies."""
    pins = []
    for sub in sym:
        if isinstance(sub, list) and sub[0] == "symbol":
            unit = int(sub[1].rsplit("_", 2)[-2])
            for p in sub:
                if isinstance(p, list) and p[0] == "pin":
                    at = next(n for n in p if isinstance(n, list) and n[0] == "at")
                    ln = next(n for n in p if isinstance(n, list) and n[0] == "length")
                    nm = next(n for n in p if isinstance(n, list) and n[0] == "name")
                    no = next(n for n in p if isinstance(n, list) and n[0] == "number")
                    pins.append((no[1], nm[1], p[1], float(at[1]), float(at[2]),
                                 float(at[3]) if len(at) > 3 else 0.0, float(ln[1]), unit))
    return pins
