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
# The 128 levels are built on the Arduboy from the level number by
# buildLevel() and rawTile() in PipQuest.ino. This only writes the sizes.
with open(os.path.join(OUT, "levels.h"), "w") as f:
    f.write("// Generated by tools/gen_assets.py\n#pragma once\n\n")
    f.write("#define LEVEL_W 200     // widest level, in tiles (25 sections of 8)\n")
    f.write("#define LEVEL_H 8\n#define NUM_LEVELS 128\n")
