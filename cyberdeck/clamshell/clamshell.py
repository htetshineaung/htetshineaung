"""
Pi 5 Clamshell  -  concept v1 (phase 1: shape + internal layout)

A mini laptop: 5" DSI touchscreen in a hinged lid, Raspberry Pi 5 + 2x 18650 cells + power
board in the base, our own thumb keyboard (RP2040) with a trackball, L/R buttons and a small
OLED status screen on top.

Base, top view (user at the bottom):

      hinge     HDMI x2     DSI cable slot      hinge
   +--[==]--------[  ]----------[====]----------[==]--+
   |   speaker / vent strip                           |
   | [OLED]  ...................................      |  right wall: USB-C charge,
   |  Pi 5 lies under the keys (USB/Eth = left wall)  |  power switch, power button
   |  q w e r t y u i o p <-                  (ball)  |
   |  a s d f g h j k l ; enter                       |
   |  ^ z x c v b n m , . /                   [L][R]  |
   |  ctrl alt fn [  space  ] ' -                     |
   |  ===== 18650 ===== | ===== 18650 =====           |  (cells under the front of the keys)
   +--------------------------------------------------+

Printed parts:
  clam_base.stl        tray (floor down, no supports)
  clam_top_plate.stl   keyboard deck (top face down)
  clam_keymat.stl      one-piece key mat, print in TPU 95A (caps down)
  clam_lid_back.stl    lid shell (outside face down)
  clam_lid_bezel.stl   screen bezel (front face down)
Axles: 2x M3x30 screws + nyloc nuts + nylon washers (set the hinge friction).

!! Concept dimensions. Check before printing: the screen module (`scr_*`), Pi cooler height
   (`pi_stack_top`), the exact tactile switch and the battery contacts you use.
"""
import os
import cadquery as cq

# ============================================================
# PARAMETERS (mm)
# ============================================================
W, D = 140.0, 86.0           # footprint (base and lid)
corner_r = 8.0
top_round = 2.0              # soft top / bottom edges
wall, floor_t = 2.0, 1.8

# Base stack (z): floor | Pi 5 (USB jacks 16 mm tall) | keyboard PCB | switches | key mat | top plate
pi_standoff = 2.5
pi_pcb_t = 1.6
pi_jack_h = 16.0             # USB / Ethernet stack above the Pi PCB (sets the base height)
kb_pcb_t = 1.0
sw_h = 1.5                   # 5.2 x 5.2 x 1.5 mm SMD tactile switch
mat_web = 0.6
plate_t = 1.4
cap_proud = 0.5              # key caps stand this far above the plate

# Pi 5, rotated 180 deg: HDMI edge at the back (ports between the hinges), USB/Eth on the left
pi_w, pi_d = 85.0, 56.0
pi_holes = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
port_overhang = 2.5

# 2x 18650 in series (2S) along the front, under the keys
cell_d, cell_l = 18.5, 65.3
cell_gap = 1.5               # spot-welded 2S stick pack (cells end to end, nickel strip)
cell_y0 = wall + 1.0

# Keyboard: 4 x 11 grid of thumb keys (space bar = 3 cells)
key_px, key_py = 8.4, 7.6    # pitch
key_w, key_h = 7.4, 6.6      # cap / hole size
kb_x0, kb_y0 = 12.0, 12.0    # grid front-left corner
kb_cols, kb_rows = 11, 4
space_cols = (4, 6)          # bottom row: columns 4..6 merged into the space bar

# Trackball (Pimoroni breakout 25 x 22 x 9.5) and L/R buttons, right of the keys
tb_cx, tb_cy = 124.0, 40.0
tb_board_w, tb_board_d, tb_h = 22.0, 25.0, 9.5
tb_hole_d = 13.0
lr_w, lr_h, lr_y0 = 9.0, 7.0, 13.0

# OLED 0.96" 128x64 (module 27 x 27, glass window 23 x 12) top-left above the keys
oled_cx, oled_cy, oled_win = 24.0, 56.5, (23.0, 12.0)

# Lid: 5" DSI touchscreen (CHECK: outline, active area, thickness)
lid_t = 8.6
scr_w, scr_d, scr_t = 120.7, 75.8, 6.0
scr_win = (110.0, 66.0)
scr_off_y = -1.0             # screen centre offset toward the front (away from the hinge)
bezel_t, back_t = 1.2, 1.4
lid_lip = 1.0                # rim that keeps the glass off the keys when closed

# Hinge: two pairs of knuckles, M3 axles
hinge_y = D - 5.5
knuckle_r = 4.6
axle_d = 3.3
base_knuckles = [(7.0, 19.0), (121.0, 133.0)]
lid_knuckles = [(19.6, 34.0), (106.0, 120.4)]
ffc_slot = (72.0, 96.0)      # DSI flat cable passes here, between the hinges
open_deg = 112.0             # lid angle in the assembled preview

eps = 0.01

# ============================================================
# DERIVED
# ============================================================
pcb_z = floor_t + pi_standoff
pcb_top = pcb_z + pi_pcb_t
pi_stack_top = pcb_top + pi_jack_h
kb_pcb_z = pi_stack_top + 0.7
sw_top = kb_pcb_z + kb_pcb_t + sw_h
plate_z = sw_top + mat_web + 0.1
BH = plate_z + plate_t                     # base height = deck surface
cap_top = BH + cap_proud
x_pcb = wall + port_overhang               # Pi PCB left edge (jacks flush with the left wall)
pi_oy = D - wall - 1.0 - pi_d              # Pi front edge
assert wall + 1.5 + 2 * cell_l + cell_gap <= W - wall, "cells do not fit across the base"
hinge_z = BH


def pi_to_dev(x, y):
    return (x_pcb + pi_w - x, pi_oy + pi_d - y)


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def rbox(x0, y0, z0, x1, y1, z1, r):
    return box(x0, y0, z0, x1, y1, z1).edges("|Z").fillet(r)


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def xcyl(x0, x1, y, z, r):
    """Cylinder along X (hinge knuckles / axles)."""
    return cq.Workplane("YZ").circle(r).extrude(x1 - x0).translate((x0, y, z))


def outline(z0, z1, inset=0.0):
    return rbox(inset, inset, z0, W - inset, D - inset, z1, corner_r - inset)


def key_cells():
    """(x0, y0, x1, y1) for every key hole / cap."""
    out = []
    for r in range(kb_rows):
        y0 = kb_y0 + (kb_rows - 1 - r) * key_py
        c = 0
        while c < kb_cols:
            span = 1
            if r == kb_rows - 1 and c == space_cols[0]:
                span = space_cols[1] - space_cols[0] + 1
            x0 = kb_x0 + c * key_px
            out.append((x0, y0, x0 + (span - 1) * key_px + key_w, y0 + key_h))
            c += span
    lr_x = tb_cx - lr_w - 0.6
    out += [(lr_x, lr_y0, lr_x + lr_w, lr_y0 + lr_h), (tb_cx + 0.6, lr_y0, tb_cx + 0.6 + lr_w, lr_y0 + lr_h)]
    return out


# ============================================================
# BASE TRAY
# ============================================================
base = (outline(0, BH).faces(">Z").edges().fillet(top_round)
        .faces("<Z").edges().chamfer(1.0))
base = base.cut(outline(floor_t, BH + eps, wall))
# ledge that carries the top plate
base = base.union(outline(plate_z - 1.2, plate_z, wall - eps).cut(outline(plate_z - 1.3, plate_z + eps, wall + 1.2)))

# Pi standoffs
for hx, hy in pi_holes:
    x, y = pi_to_dev(hx, hy)
    base = base.union(cyl(x, y, floor_t - eps, pcb_z, 5.0)).cut(cyl(x, y, 0.6, pcb_z + eps, 2.2))

# battery saddles
for i in range(2):
    x0 = wall + 1.5 + i * (cell_l + cell_gap)
    for sx in (x0 + 8, x0 + cell_l - 8):
        sad = box(sx - 2, cell_y0, floor_t - eps, sx + 2, cell_y0 + cell_d, floor_t + 6)
        base = base.union(sad.cut(xcyl(sx - 3, sx + 3, cell_y0 + cell_d / 2, floor_t + cell_d / 2, cell_d / 2 + 0.2)))

# trackball posts (board sits under the deck, ball through the plate)
tb_seat = cap_top + 0.4 - tb_h
for dx in (-tb_board_w / 2 + 1.5, tb_board_w / 2 - 1.5):
    for dy in (-tb_board_d / 2 + 1.5, tb_board_d / 2 - 1.5):
        base = base.union(box(tb_cx + dx - 1.5, tb_cy + dy - 1.5, floor_t - eps, tb_cx + dx + 1.5, tb_cy + dy + 1.5, tb_seat))

# --- ports
def left_open(pi_y, half_w, z0, z1):
    _, yc = pi_to_dev(0, pi_y)
    return box(-eps, yc - half_w, z0, wall + eps, yc + half_w, z1)

base = base.cut(left_open(45.75, 8.4, pcb_top - 0.4, pcb_top + 13.9))     # Ethernet
base = base.cut(left_open(29.1, 7.4, pcb_top - 0.4, pcb_top + 16.2))      # USB pair
base = base.cut(left_open(10.2, 7.4, pcb_top - 0.4, pcb_top + 16.2))      # USB pair
hx0, _ = pi_to_dev(43.5, 0)
hx1, _ = pi_to_dev(21.5, 0)
base = base.cut(box(hx0, D - wall - eps, pcb_z - 1.0, hx1, D + eps, pcb_top + 5.0))   # 2x micro-HDMI
# right wall: USB-C charge, slide switch, power button
base = base.cut(rbox(W - wall - eps, 58.0, 6.0, W + eps, 67.0, 9.4, 1.0))
base = base.cut(box(W - wall - eps, 44.0, 6.5, W + eps, 52.0, 9.5))
base = base.cut(cq.Workplane("YZ").circle(2.2).extrude(wall + 2 * eps).translate((W - wall - eps, 34.0, 8.0)))
# floor vents under the Pi, feet pockets
cx, cy = pi_to_dev(pi_w / 2, pi_d / 2)
for i in range(6):
    base = base.cut(cq.Workplane("XY").slot2D(46.0, 2.6).extrude(floor_t + 2 * eps)
                    .translate((cx, cy + (i - 2.5) * 6.0, -eps)))
for fx, fy in [(14, 12), (W - 14, 12), (14, D - 12), (W - 14, D - 12)]:
    base = base.cut(cyl(fx, fy, -eps, 0.8, 9.0))

# hinge: base knuckles + clearance for the lid knuckles, DSI cable slot
for x0, x1 in base_knuckles:
    base = base.union(xcyl(x0, x1, hinge_y, hinge_z, knuckle_r).intersect(outline(0, BH + 10)))
for x0, x1 in lid_knuckles:
    base = base.cut(xcyl(x0 - 0.4, x1 + 0.4, hinge_y, hinge_z, knuckle_r + 0.5))
for x0, x1 in base_knuckles + lid_knuckles:
    base = base.cut(xcyl(x0 - 1, x1 + 1, hinge_y, hinge_z, axle_d / 2))
base = base.cut(box(ffc_slot[0], D - wall - 2.5, BH - 4.0, ffc_slot[1], D - wall + eps, BH + 1))

# ============================================================
# TOP PLATE (keyboard deck) and KEY MAT
# ============================================================
plate = outline(plate_z, BH, wall + 0.25).faces(">Z").edges().chamfer(0.4)
mat = None
for x0, y0, x1, y1 in key_cells():
    plate = plate.cut(rbox(x0 - 0.2, y0 - 0.2, plate_z - eps, x1 + 0.2, y1 + 0.2, BH + eps, 1.4))
    cap = rbox(x0 + 0.15, y0 + 0.15, sw_top, x1 - 0.15, y1 - 0.15, cap_top, 1.2)
    mat = cap if mat is None else mat.union(cap)
web = rbox(kb_x0 - 2, kb_y0 - 2, sw_top, kb_x0 + kb_cols * key_px + 1, kb_y0 + kb_rows * key_py + 1, sw_top + mat_web, 2)
lr_web = rbox(tb_cx - lr_w - 2.6, lr_y0 - 2, sw_top, tb_cx + lr_w + 2.6, lr_y0 + lr_h + 2, sw_top + mat_web, 2)
mat = mat.union(web).union(lr_web)
plate = plate.cut(cyl(tb_cx, tb_cy, plate_z - eps, BH + eps, tb_hole_d))
plate = plate.cut(rbox(oled_cx - oled_win[0] / 2, oled_cy - oled_win[1] / 2, plate_z - eps,
                       oled_cx + oled_win[0] / 2, oled_cy + oled_win[1] / 2, BH + eps, 1.0))
for i in range(9):                                   # speaker / vent strip over the Pi
    x = 46.0 + i * 6.0
    plate = plate.cut(cq.Workplane("XY").slot2D(10.0, 2.2, angle=90).extrude(plate_t + 2 * eps)
                      .translate((x, 64.0, plate_z - eps)))
plate = plate.cut(box(ffc_slot[0], D - wall - 4.0, plate_z - eps, ffc_slot[1], D, BH + eps))
for x0, x1 in lid_knuckles + base_knuckles:
    plate = plate.cut(xcyl(x0 - 0.5, x1 + 0.5, hinge_y, hinge_z, knuckle_r + 0.6))
# bosses that hold the keyboard PCB (M2x4 self-tapping screws from below; positions = circuit.HOLES)
kb_holes = [(7.0, 8.0), (108.5, 8.0), (22.0, 73.5), (108.5, 71.0), (64.0, 73.5)]
for hx, hy in kb_holes:
    plate = plate.union(cyl(hx, hy, kb_pcb_z + kb_pcb_t, plate_z + eps, 4.5))
    plate = plate.cut(cyl(hx, hy, kb_pcb_z + kb_pcb_t - eps, plate_z + 0.8, 1.7))

# ============================================================
# LID (modelled closed: screen face at z = BH + lid_lip, back at BH + lid_lip + lid_t)
# ============================================================
lz0 = BH + lid_lip
lid_outer = (outline(lz0, lz0 + lid_t).faces(">Z").edges().fillet(top_round))
scr_cy = D / 2 + scr_off_y
lid_back = lid_outer.cut(box(-1, -1, lz0 - 1, W + 1, D + 1, lz0 + bezel_t))          # bezel is a separate part
lid_back = lid_back.cut(outline(lz0 + bezel_t - eps, lz0 + lid_t - back_t, wall))
bezel = outline(lz0, lz0 + bezel_t, wall + 0.2)
bezel = bezel.cut(rbox(W / 2 - scr_win[0] / 2, scr_cy - scr_win[1] / 2, lz0 - eps,
                       W / 2 + scr_win[0] / 2, scr_cy + scr_win[1] / 2, lz0 + bezel_t + eps, 1.5))
bezel = bezel.union(outline(lz0 - lid_lip, lz0 + eps, 0).cut(outline(lz0 - lid_lip - eps, lz0 + 2 * eps, 1.6)))
# lid knuckles + clearance for the base knuckles, cable slot
for x0, x1 in lid_knuckles:
    lid_back = lid_back.union(xcyl(x0, x1, hinge_y, hinge_z, knuckle_r).intersect(outline(BH - 10, lz0 + lid_t)))
for x0, x1 in base_knuckles:
    lid_back = lid_back.cut(xcyl(x0 - 0.4, x1 + 0.4, hinge_y, hinge_z, knuckle_r + 0.5))
    bezel = bezel.cut(xcyl(x0 - 0.4, x1 + 0.4, hinge_y, hinge_z, knuckle_r + 0.5))
for x0, x1 in lid_knuckles:
    bezel = bezel.cut(xcyl(x0 - 0.4, x1 + 0.4, hinge_y, hinge_z, knuckle_r + 0.5))
for x0, x1 in base_knuckles + lid_knuckles:
    lid_back = lid_back.cut(xcyl(x0 - 1, x1 + 1, hinge_y, hinge_z, axle_d / 2))
lid_back = lid_back.cut(box(ffc_slot[0], D - wall - 2.5, BH - 1, ffc_slot[1], D - wall + eps, lz0 + 3))
# finger notch at the front of the lid
lid_back = lid_back.cut(cq.Workplane("XZ").ellipse(14, 3.2).extrude(-6).translate((W / 2, -1, lz0)))


# ============================================================
# EXPORT
# ============================================================
def lid_open(shape):
    return shape.rotate((0, hinge_y, hinge_z), (1, hinge_y, hinge_z), -open_deg)


def flat(shape, flip=False):
    s = shape.rotate((0, 0, 0), (1, 0, 0), 180) if flip else shape
    bb = s.val().BoundingBox()
    return s.translate((-bb.xmin, -bb.ymin, -bb.zmin))


out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
if __name__ == "__main__":
    os.makedirs(out, exist_ok=True)
    kw = dict(tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(flat(base), os.path.join(out, "clam_base.stl"), **kw)
    cq.exporters.export(flat(plate, True), os.path.join(out, "clam_top_plate.stl"), **kw)
    cq.exporters.export(flat(mat, True), os.path.join(out, "clam_keymat.stl"), **kw)
    cq.exporters.export(flat(lid_back, True), os.path.join(out, "clam_lid_back.stl"), **kw)
    cq.exporters.export(flat(bezel), os.path.join(out, "clam_lid_bezel.stl"), **kw)
    cq.exporters.export(base.union(plate).union(mat).union(lid_open(lid_back)).union(lid_open(bezel)),
                        os.path.join(out, "clam_assembled_open.stl"), **kw)
    cq.exporters.export(base.union(plate).union(mat).union(lid_back).union(bezel),
                        os.path.join(out, "clam_assembled_closed.stl"), **kw)
print(f"Clamshell: {W} x {D} mm, base {BH:.1f} mm, closed {lz0 + lid_t:.1f} mm | kb pcb z={kb_pcb_z:.1f} "
      f"plate z={plate_z:.1f} cap top={cap_top:.1f} tb seat={tb_seat:.1f} pi_oy={pi_oy:.1f}")
