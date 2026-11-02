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
# Levels are built on the Arduboy from the level number: each level is 16
# chunks of 8 columns. Chunk 0 is the start, chunks 14-15 are the staircase and
# flag, and chunks 1-13 are picked from the pieces below. Harder pieces unlock
# as the level number goes up (see PipQuest.ino, chunkFor()).
#
# Legend:  .  sky          #  ground       B  brick (big Pip breaks it)
#          ?  coin block   M  power block (berry, or flower if already big)
#          W  wing block   (berry, or feather if already big)
#          P  pipe (always 2 wide)         o  coin      s  spikes
#          e  enemy (blob, or a snail/spiky on later levels)
#          t  snail (stomp it for a kickable shell)    k  spiky (can't be stomped)
#
# Each piece is rows 1-7 (row 0 sits under the score bar and stays empty).
# Every piece must have ground at its first and last column, so any two
# pieces can be joined. Themes: H hills, C cave (gets a brick ceiling on
# row 1, so pieces must leave rows 1-2 free), S sky.
PIECES = [
 # (themes, difficulty 0-3, rows 1..7)
 ("HC", 0, ["........",
            "........",
            "........",
            "........",
            "....e...",
            "########",
            "########"]),
 ("HC", 0, ["........",
            "........",
            ".?BMB?..",
            "........",
            "........",
            "########",
            "########"]),
 ("HC", 0, ["........",
            "........",
            "..oooo..",
            "........",
            "........",
            "###..###",
            "###..###"]),
 ("HC", 0, ["........",
            "........",
            "........",
            "...PP...",
            "...PP.e.",
            "########",
            "########"]),
 ("HC", 0, ["........",
            "........",
            "........",
            "...##...",
            "..####..",
            "########",
            "########"]),
 ("HS", 1, ["........",
            "........",
            "..?W?...",
            "........",
            "........",
            "########",
            "########"]),
 ("H", 1,  ["........",
            "........",
            "...PP...",
            "...PP...",
            "...PP...",
            "########",
            "########"]),
 ("HC", 1, ["........",
            "........",
            "..ooo...",
            "........",
            "........",
            "##...###",
            "##...###"]),
 ("H", 1,  ["........",
            "........",
            "...##...",
            "..####..",
            ".######.",
            "########",
            "########"]),
 ("HC", 1, ["........",
            "..oooo..",
            ".BBBBBB.",
            "........",
            "...t....",
            "########",
            "########"]),
 ("HC", 1, ["........",
            "........",
            "........",
            "........",
            "..t...e.",
            "########",
            "########"]),
 ("HC", 2, ["........",
            "........",
            "...oo...",
            "........",
            "...ss...",
            "########",
            "########"]),
 ("HC", 2, ["........",
            "........",
            "........",
            "..BBBB..",
            "........",
            "##....##",
            "##....##"]),
 ("HC", 2, ["........",
            "........",
            "...?....",
            "........",
            "..k..e..",
            "########",
            "########"]),
 ("H", 3,  ["........",
            "........",
            "........",
            "PP....PP",
            "PP.ss.PP",
            "########",
            "########"]),
 ("HC", 3, ["........",
            "........",
            "..BBBB..",
            "........",
            ".e.e.t..",
            "########",
            "########"]),
 ("HC", 3, ["........",
            "........",
            "...oo...",
            "...##...",
            "........",
            "#......#",
            "#......#"]),
 ("S", 0,  ["........",
            "........",
            "........",
            "...oo...",
            "...##...",
            "##....##",
            "##....##"]),
 ("S", 0,  ["........",
            ".....oo.",
            ".....##.",
            "..##....",
            "........",
            "#......#",
            "#......#"]),
 ("S", 2,  ["........",
            "........",
            "...e....",
            "..####..",
            "........",
            "#......#",
            "#......#"]),
 ("S", 3,  ["........",
            "........",
            "........",
            ".....k..",
            ".##..##.",
            "#......#",
            "#......#"]),
]

for themes, d, rows in PIECES:
    assert len(rows) == 7 and all(len(r) == 8 for r in rows), rows
    assert rows[5][0] == "#" and rows[5][7] == "#" or rows[3][0] == "P", rows
    if "C" in themes:
        assert rows[0] == "........", rows

THEME_BITS = {"H": 1, "C": 2, "S": 4}
with open(os.path.join(OUT, "levels.h"), "w") as f:
    f.write("// Generated by tools/gen_assets.py - edit the pieces there and re-run it.\n")
    f.write("#pragma once\n\n")
    f.write("#define LEVEL_W 128\n#define LEVEL_H 8\n#define NUM_LEVELS 128\n")
    f.write("#define NUM_PIECES %d\n" % len(PIECES))
    def find(theme, marker):
        return next(i for i, (th, d, rows) in enumerate(PIECES)
                    if theme in th and any(marker in r for r in rows))
    f.write("#define PIECE_POWER %d   // ? block row with an M block\n" % find("H", "?BMB?"))
    f.write("#define PIECE_WING %d    // ? block row with a W block\n" % find("S", "?W?"))
    f.write("#define PIECE_SKY_EASY %d\n\n" % next(i for i, (th, d, r) in enumerate(PIECES) if th == "S" and d == 0))
    f.write("// low 3 bits: themes (1 hills, 2 cave, 4 sky); high nibble: difficulty\n")
    f.write("const uint8_t pieceInfo[NUM_PIECES] PROGMEM = {\n  ")
    f.write(", ".join("0x%02X" % (sum(THEME_BITS[t] for t in th) | (d << 4)) for th, d, _ in PIECES))
    f.write("\n};\n\n")
    f.write("const char pieces[NUM_PIECES][7][8] PROGMEM = {\n")
    for th, d, rows in PIECES:
        f.write("  { %s },\n" % ", ".join("{%s}" % ",".join("'%s'" % c for c in r) for r in rows))
    f.write("};\n")
