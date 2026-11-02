#!/usr/bin/env python3
"""Generates sprites.h and levels.h for Pip Quest.
Edit the pixel art or level layout below, then run:  python3 tools/gen_assets.py
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

# ================================================================ sprites
# '#' = lit pixel. All art faces RIGHT; left-facing frames are mirrored.

HERO_SMALL = {
 "stand": """
..####..
.#######
.####.#.
.######.
..####..
.######.
..####..
..#..#..""",
 "walk": """
..####..
.#######
.####.#.
.######.
..####..
.######.
..####..
.#....#.""",
 "jump": """
..####..
.#######
.####.#.
.######.
#.####.#
.######.
..####..
.#...#..""",
}

# Big Pip is 8x16, built from a head, a torso (per power) and legs (per pose)
BIG_HEAD = {
 "big": """
..####..
.#######
.#######
.####.#.
.######.
..####..
...##...""",
 "spark": """
..####..
.##.####
.#######
.####.#.
.######.
..####..
...##...""",
 "wing": """
#.####.#
########
.#######
.####.#.
.######.
..####..
...##...""",
}
BIG_TORSO = {
 "big": """
.######.
########
#.####.#
#.####.#
..####..""",
 "spark": """
.#.##.#.
##....##
#.#..#.#
#..##..#
..####..""",
 "wing": """
.######.
########
#.####.#
#.####.#
..####..""",
}
BIG_TORSO_JUMP = {
 "big": """
#.####.#
.######.
..####..
..####..
..####..""",
 "spark": """
#.#..#.#
.#.##.#.
..#..#..
..####..
..####..""",
 "wing": """
#.####.#
.######.
..####..
..####..
..####..""",
}
BIG_LEGS = {
 "stand": """
..#..#..
..#..#..
..#..#..
.##..##.""",
 "walk": """
..#..#..
.#....#.
.#....#.
##....##""",
 "jump": """
..#..#..
.#...#..
.#....#.
.......#""",
}

BLOB = [
"""
........
..####..
.######.
##.##.##
########
.######.
.#....#.
#......#""",
"""
........
..####..
.######.
##.##.##
########
.######.
..#..#..
.##..##.""",
"""
........
........
........
........
........
.######.
#.####.#
########""",
]
SNAIL = [  # faces right (shell at the back/left, head on the right)
"""
........
.......#
..###.#.
.#...##.
##.##.##
#.#..#.#
########
.######.""",
"""
........
.......#
..###.#.
.#...##.
##.##.##
#.#..#.#
########
#.####.#""",
]
SHELL = """
........
..####..
.#....#.
#.####.#
#.#..#.#
#.####.#
.######.
........"""
SPIKY = [
"""
#..#..#.
.#.#.#..
.######.
########
##.##.##
########
.######.
.#....#.""",
"""
#..#..#.
.#.#.#..
.######.
########
##.##.##
########
.######.
#......#""",
]
ITEMS = {
 "berry": """
....##..
...#....
.######.
##.#####
#.######
########
.######.
..####..""",
 "flower": """
..#..#..
.#.##.#.
..#..#..
...##...
.#.##.#.
..####..
...##...
...##...""",
 "feather": """
......##
....####
...###.#
..###.#.
.###.#..
.##.#...
.#.#....
#.......""",
 "spark": """
.##.....
####....
####....
.##.....
........
........
........
........""",
 "poof": """
#..#..#.
.#.#.#..
..###...
###.####
..###...
.#.#.#..
#..#..#.
........""",
}
TILES = {
 "ground": """
########
########
#.#.#.#.
.#.#.#.#
#.#.#.#.
.#.#.#.#
#.#.#.#.
.#.#.#.#""",
 "brick": """
########
#...#...
#...#...
########
..#...#.
..#...#.
########
#...#...""",
 "question": """
########
#..##..#
#.#..#.#
#....#.#
#...#..#
#......#
#...#..#
########""",
 "used": """
########
#......#
#.#..#.#
#......#
#......#
#.#..#.#
#......#
########""",
 "pipe_top_l": """
########
#.......
#.#.#...
#.......
########
.#......
.#.#....
.#......""",
 "pipe_top_r": """
########
.......#
.......#
.......#
########
......#.
......#.
......#.""",
 "pipe_l": """
.#......
.#.#....
.#......
.#.#....
.#......
.#.#....
.#......
.#.#....""",
 "pipe_r": """
......#.
......#.
......#.
......#.
......#.
......#.
......#.
......#.""",
 "coin1": """
...##...
..#..#..
.#.##.#.
.#.##.#.
.#.##.#.
..#..#..
...##...
........""",
 "coin2": """
...##...
...##...
...##...
...##...
...##...
...##...
...##...
........""",
 "pole": """
...#....
...#....
...#....
...#....
...#....
...#....
...#....
...#....""",
 "flag": """
...#####
...####.
...###..
...##...
...#....
...#....
...#....
...#....""",
 "spike": """
........
........
.#...#..
.#...#..
###.###.
###.###.
########
########""",
 "check_off": """
...#....
...#....
...#....
...#....
...###..
...##...
...#....
..###...""",
 "check_on": """
...####.
...###..
...##...
...#....
...#....
...#....
...#....
..###...""",
}


def rows(art, h=8):
    r = art.strip("\n").split("\n")
    assert len(r) == h and all(len(x) == 8 for x in r), art
    return r


def to_bytes(r, mirror=False):
    """r: list of 8-char strings (height multiple of 8) -> Arduboy sprite bytes"""
    if mirror:
        r = [x[::-1] for x in r]
    out = []
    for page in range(len(r) // 8):
        for c in range(8):
            b = 0
            for y in range(8):
                if r[page * 8 + y][c] == "#":
                    b |= 1 << y
            out.append(b)
    return out


def sprite(name, frames, h=8):
    data = [8, h]
    for f in frames:
        data += f
    body = ", ".join("0x%02X" % b for b in data)
    return "const uint8_t PROGMEM %s[] = {\n  %s\n};\n" % (name, body)


def big_frame(form, pose):
    torso = BIG_TORSO_JUMP[form] if pose == "jump" else BIG_TORSO[form]
    r = rows(BIG_HEAD[form], 7) + rows(torso, 5) + rows(BIG_LEGS[pose], 4)
    assert len(r) == 16
    return r


POSES = ("stand", "walk", "jump")
small = [to_bytes(rows(HERO_SMALL[p])) for p in POSES]
small += [to_bytes(rows(HERO_SMALL[p]), True) for p in POSES]
big = []
for form in ("big", "spark", "wing"):
    big += [to_bytes(big_frame(form, p)) for p in POSES]
    big += [to_bytes(big_frame(form, p), True) for p in POSES]

tile_order = list(TILES)
item_order = list(ITEMS)

with open(os.path.join(OUT, "sprites.h"), "w") as f:
    f.write("// Generated by tools/gen_assets.py - do not edit by hand\n#pragma once\n\n")
    f.write("// Small Pip: 0 stand R, 1 walk R, 2 jump R, 3-5 the same facing left\n")
    f.write(sprite("heroSprite", small))
    f.write("\n// Big Pip 8x16: frame = form * 6 + (left ? 3 : 0) + pose\n")
    f.write("// form 0 big, 1 spark, 2 wing; pose 0 stand, 1 walk, 2 jump\n")
    f.write(sprite("heroBigSprite", big, 16))
    f.write("\n// Blob: 0 walk A, 1 walk B, 2 squashed\n")
    f.write(sprite("blobSprite", [to_bytes(rows(a)) for a in BLOB]))
    f.write("\n// Snail: 0-1 walking right, 2-3 walking left\n")
    f.write(sprite("snailSprite", [to_bytes(rows(a)) for a in SNAIL] +
                   [to_bytes(rows(a), True) for a in SNAIL]))
    f.write(sprite("shellSprite", [to_bytes(rows(SHELL))]))
    f.write(sprite("spikySprite", [to_bytes(rows(a)) for a in SPIKY]))
    f.write("\n")
    for i, t in enumerate(item_order):
        f.write("#define ITEM_%s %d\n" % (t.upper(), i))
    f.write(sprite("itemSprite", [to_bytes(rows(ITEMS[t])) for t in item_order]))
    f.write("\n")
    for i, t in enumerate(tile_order):
        f.write("#define TILE_%s %d\n" % (t.upper(), i))
    f.write(sprite("tileSprite", [to_bytes(rows(TILES[t])) for t in tile_order]))

# ================================================================ levels
# Legend:  .  sky          #  ground       B  brick (big Pip breaks it)
#          ?  coin block   M  power block (berry, or flower if already big)
#          W  wing block   (berry, or feather if already big)
#          P  pipe (always 2 wide)         o  coin      s  spikes
#          e  blob         t  snail (stomp it for a kickable shell)
#          k  spiky (can't be stomped)     K  checkpoint flag
#          S  player start F  goal flag pole
# Row 0 sits under the score bar, so keep it empty.
W, H = 128, 8


def new_level():
    return [["."] * W for _ in range(H)]


def put(g, x, y, c):
    g[y][x] = c


def ground(g, x0, x1):
    for x in range(x0, x1 + 1):
        g[6][x] = "#"
        g[7][x] = "#"


def column(g, x, height, c="#"):  # stacks on top of the ground (row 5 upward)
    for i in range(height):
        g[5 - i][x] = c


def pipe(g, x, height):
    column(g, x, height, "P")
    column(g, x + 1, height, "P")


def hrow(g, x0, x1, y, c):
    for x in range(x0, x1 + 1):
        g[y][x] = c


def stairs_and_flag(g, x):
    for i in range(5):
        column(g, x + i, i + 1)
    column(g, x + 5, 5)
    for y in range(1, 6):
        g[y][x + 11] = "F"


# ---- Level 1: Green Hills (learn the berry and shells)
L1 = new_level()
ground(L1, 0, 43); ground(L1, 46, 71); ground(L1, 75, 81); ground(L1, 84, 127)
put(L1, 2, 5, "S")
put(L1, 7, 3, "?")
hrow(L1, 11, 15, 3, "B"); put(L1, 12, 3, "M"); put(L1, 14, 3, "?")
put(L1, 18, 5, "e")
pipe(L1, 22, 2)
put(L1, 27, 5, "e")
pipe(L1, 31, 3)
put(L1, 36, 5, "t")
put(L1, 40, 5, "e")
hrow(L1, 43, 46, 3, "o")
hrow(L1, 50, 57, 3, "B"); put(L1, 53, 3, "?"); put(L1, 56, 3, "M")
hrow(L1, 51, 55, 2, "o")
put(L1, 52, 2, "e")
put(L1, 61, 5, "K")
put(L1, 65, 5, "t"); put(L1, 68, 5, "e"); put(L1, 70, 5, "e")
hrow(L1, 72, 74, 2, "o")
for i, h in enumerate([1, 2, 3, 3]):
    column(L1, 78 + i, h)
for i, h in enumerate([3, 2, 1]):
    column(L1, 84 + i, h)
hrow(L1, 89, 95, 4, "o")
put(L1, 91, 2, "?"); put(L1, 93, 2, "?")
put(L1, 97, 5, "e"); put(L1, 99, 5, "t")
pipe(L1, 104, 2)
stairs_and_flag(L1, 110)

# ---- Level 2: Spike Hills (spark flower, spikies)
L2 = new_level()
ground(L2, 0, 15); ground(L2, 19, 30); ground(L2, 34, 36); ground(L2, 40, 58)
ground(L2, 62, 75); ground(L2, 80, 127)
put(L2, 2, 5, "S")
put(L2, 7, 3, "?"); put(L2, 8, 3, "M"); put(L2, 9, 3, "?")
put(L2, 13, 5, "e")
hrow(L2, 15, 19, 2, "o")
put(L2, 22, 5, "s"); put(L2, 23, 5, "s")
put(L2, 26, 5, "k"); put(L2, 29, 5, "e")
hrow(L2, 31, 33, 3, "B")
hrow(L2, 37, 39, 3, "B"); put(L2, 38, 3, "M"); put(L2, 38, 2, "o")
pipe(L2, 43, 2)
put(L2, 47, 5, "s"); put(L2, 48, 5, "s"); put(L2, 49, 5, "s")
pipe(L2, 51, 2)
put(L2, 55, 5, "t"); put(L2, 57, 5, "k")
hrow(L2, 59, 61, 3, "o")
put(L2, 64, 5, "K")
hrow(L2, 66, 72, 3, "B"); put(L2, 67, 3, "?"); put(L2, 69, 3, "M")
hrow(L2, 66, 71, 2, "o"); put(L2, 70, 2, "e")
put(L2, 73, 5, "k")
hrow(L2, 76, 79, 4, "B")
hrow(L2, 76, 79, 3, "o")
put(L2, 84, 5, "s"); put(L2, 85, 5, "s")
put(L2, 88, 5, "k"); put(L2, 90, 5, "t"); put(L2, 92, 5, "e")
pipe(L2, 95, 3)
hrow(L2, 99, 104, 5, "s")
hrow(L2, 99, 104, 3, "B"); hrow(L2, 99, 104, 2, "o")
stairs_and_flag(L2, 108)
put(L2, 117, 5, "k")

# ---- Level 3: Brick Cave (a ceiling, shells to kick, brick pockets)
L3 = new_level()
hrow(L3, 0, 100, 1, "B")
ground(L3, 0, 33); ground(L3, 37, 61); ground(L3, 65, 95); ground(L3, 99, 127)
put(L3, 2, 5, "S")
put(L3, 9, 5, "e"); put(L3, 12, 5, "e")
hrow(L3, 15, 18, 3, "B"); put(L3, 16, 3, "M"); put(L3, 17, 3, "?")
pipe(L3, 22, 1)
put(L3, 26, 5, "t"); put(L3, 29, 5, "e"); put(L3, 31, 5, "e")
hrow(L3, 34, 36, 3, "o")
hrow(L3, 40, 46, 3, "B"); hrow(L3, 41, 45, 4, "o"); hrow(L3, 41, 45, 5, "o")
put(L3, 50, 5, "k")
pipe(L3, 53, 2)
put(L3, 58, 5, "K")
hrow(L3, 62, 64, 5, "B")                       # brick bridge over a pit
put(L3, 68, 5, "t"); put(L3, 71, 5, "e"); put(L3, 73, 5, "e"); put(L3, 75, 5, "e")
hrow(L3, 78, 81, 3, "?"); put(L3, 79, 3, "M")
put(L3, 85, 5, "k"); put(L3, 88, 5, "t")
pipe(L3, 91, 1)
hrow(L3, 96, 98, 3, "o")
stairs_and_flag(L3, 104)

# ---- Level 4: Sky Road (the feather lets you fly over everything)
L4 = new_level()
ground(L4, 0, 12); ground(L4, 46, 55); ground(L4, 86, 96); ground(L4, 109, 127)
put(L4, 2, 5, "S")
put(L4, 6, 3, "W"); put(L4, 9, 3, "W")
hrow(L4, 16, 21, 5, "#"); put(L4, 19, 4, "e")
hrow(L4, 25, 28, 4, "#"); put(L4, 27, 3, "e")
hrow(L4, 32, 35, 3, "#"); hrow(L4, 32, 35, 2, "o")
hrow(L4, 39, 42, 5, "#"); put(L4, 41, 4, "k")
put(L4, 48, 5, "K"); put(L4, 52, 5, "t")
hrow(L4, 59, 61, 4, "#")
hrow(L4, 65, 67, 3, "#"); hrow(L4, 65, 67, 2, "o")
hrow(L4, 71, 73, 4, "#"); put(L4, 72, 3, "e")
hrow(L4, 77, 79, 5, "#")
hrow(L4, 75, 85, 1, "o")                       # coin trail for flyers
hrow(L4, 82, 83, 4, "#")
put(L4, 89, 3, "?"); put(L4, 90, 3, "W"); put(L4, 91, 3, "?")
put(L4, 92, 5, "e"); put(L4, 94, 5, "k")
hrow(L4, 99, 101, 4, "#")
hrow(L4, 104, 106, 3, "#"); put(L4, 105, 2, "e")
stairs_and_flag(L4, 111)

LEVELS = [L1, L2, L3, L4]
NAMES = ["GREEN HILLS", "SPIKE HILLS", "BRICK CAVE", "SKY ROAD"]

with open(os.path.join(OUT, "levels.h"), "w") as f:
    f.write("// Generated by tools/gen_assets.py - you can also edit these strings directly.\n")
    f.write("// Each row must be exactly LEVEL_W characters. See tools/gen_assets.py for the legend.\n")
    f.write("#pragma once\n\n")
    f.write("#define LEVEL_W %d\n#define LEVEL_H %d\n#define NUM_LEVELS %d\n\n" % (W, H, len(LEVELS)))
    f.write("const char levels[NUM_LEVELS][LEVEL_H][LEVEL_W + 1] PROGMEM = {\n")
    for n, g in enumerate(LEVELS):
        f.write("  { // Level %d: %s\n" % (n + 1, NAMES[n]))
        for r in g:
            f.write('    "%s",\n' % "".join(r))
        f.write("  },\n")
    f.write("};\n")

if __name__ == "__main__":
    for n, g in enumerate(LEVELS):
        print("Level", n + 1, NAMES[n])
        for r in g:
            print("".join(r))
