"""
Pi 5 + 3.5" GPIO LCD + M5Stack Cardputer "mini-deck" case  -  v7 (trackball + L/R buttons)

v7 adds a trackball (Pimoroni Trackball Breakout, 25 x 22 x 9.5 mm) to the RIGHT of the
keyboard, with L / R mouse buttons as flexure tabs cut into the faceplate pressing 6x6x5 mm
tactile switches. Trackball + buttons talk to the Cardputer over its Grove port (I2C).
Otherwise as v6:
  * 25.1 mm thick: 1.6 mm floor, 2.5 mm Pi standoffs, 1.6 mm faceplate, Cardputer on the floor.
  * 1.8 mm outer walls, no screws and no corner posts: the faceplate has a 0.8 mm lip that
    snaps over a matching step on top of the walls (flush outside, small catches inside).
  * Footprint is the boards plus walls and the cable route, nothing else.
  * Cable fully hidden: Pi lower-front USB-A (slim right-angle plug) -> 7.5 mm left channel,
    under the Ethernet jack -> trench inside the divider -> plug bay right of the Cardputer,
    where its USB-C is (right end, near the back, near the top).
Fitted to measured Cardputer v1.1 photos (USB-C right end, Grove left end, ~22 mm tall).

Top view (user sits at the bottom):

   +---------------------------------------------+
   |           back: USB-C power, 2x HDMI, UART  |
   |  +---------------------------------------+  |
   |ch|  3.5" LCD window (Pi 5 underneath)     |  |  right: microSD / power button + vents
   |an+---------------------------------------+  |
   |==========  divider cable trench  ==========|
   | +-----------------------------------+ plug   (ball)   |
   | | Cardputer (inset ~1.5 mm)          |=bay   [ L ][ R ]|
   | +-----------------------------------+                 |
   +---------------( scoop )--------------------------------+

Printed parts:
  deck_tray.stl       body. Print upright (floor on bed), no supports.
  deck_faceplate.stl  top plate. Print top face DOWN, no supports.

Hardware: 4x M2.5x5 (Pi -> standoffs). Faceplate snaps on (pry up at the front scoop).
          Trackball breakout (stick on its 4 posts with foam tape), 2x 6x6x5 mm tactile
          switches (glue on the pedestals), PCF8574 I2C expander + 3.3 V regulator (bay right
          of the Pi), Grove cable from the Cardputer's left end through the trench.
          1x USB-A (slim right-angle, head <= 7 mm, "up/down") to USB-C (right-angle,
          "left/right") data cable, ~20 cm.

!! Measure YOUR parts first: `stack_above_pcb`, `lcd_win_dx/dy`.
"""
import os
import cadquery as cq

# ============================================================
# PARAMETERS (mm)
# ============================================================
# --- Raspberry Pi 5 ---
pi_w, pi_d, pi_pcb_t = 85.0, 56.0, 1.6
pi_holes = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]  # HDMI edge = y0
pi_cl = 0.8                  # side / front clearance around the board
pi_cl_back = 0.8
port_overhang = 2.5          # USB/Ethernet jacks stick out past the PCB edge
eth_y, usb_front_y, usb_back_y = 45.75, 29.1, 10.2   # jack centres along the Pi edge (Pi coords)

# --- Pi + LCD stack ---
standoff_h = 2.5             # Pi 5 underside is flat apart from the microSD socket (~1.4 mm)
standoff_od = 5.0
pilot_d = 2.2                # M2.5 self-tap
stack_above_pcb = 17.5       # Pi PCB top -> LCD glass top. MEASURE
lid_gap = 0.3

# --- LCD window ---
lcd_win_w, lcd_win_d = 75.0, 51.0
lcd_win_dx, lcd_win_dy = 0.0, 0.0

# --- Cardputer v1.1 (84 x 54; ~22 tall at the StampS3A block) ---
cp_w, cp_d, cp_h = 84.0, 54.0, 22.0
cp_cl = 0.4
cp_usb_from_back = 10.0      # USB-C centre, RIGHT end, from the Cardputer's back edge
cp_usb_z = 19.0              # USB-C centre height above the Cardputer's bottom
cp_grove_from_back = 9.0     # Grove port centre, LEFT end, from the back edge
cp_left_gap = 6.0            # room for the Grove plug on the Cardputer's left end (trackball I2C)
plug_bay_min = 9.5           # room right of the Cardputer for the right-angle USB-C head
plug_relief = 1.0            # pocket in the faceplate underside over the USB-C head
usb_c_half_h = 3.3
spk_z = 13.0                 # speaker height (under the USB-C); grille is in the faceplate

# --- Trackball zone (right of the keyboard) ---
tb_enable = True
tb_board_w, tb_board_d, tb_h = 22.0, 25.0, 9.5   # Pimoroni Trackball Breakout (x, y, height incl. ball)
tb_gap_to_plug = 9.0         # space between the Cardputer and the trackball for the USB-C head
tb_cy = 35.0                 # trackball centre, mm from the front of the case
tb_ball_protrude = 0.6       # ball top above the faceplate top
tb_hole_d = 13.0             # faceplate hole around the ball. CHECK against your ball
tb_post = 3.0                # corner posts the board sits on (foam tape)
btn_w, btn_d, btn_gap = 10.5, 11.0, 1.0           # flexure button tabs (each)
btn_y0 = 4.0                 # tab front edge from the case front
btn_slot = 0.8               # slot around the tabs
btn_hinge_t = 0.8            # faceplate thinned to this along the hinge
btn_nub_d, btn_nub_h = 3.0, 0.6
sw_h = 5.0                   # 6x6x5 mm tactile switch, body + stem
sw_preload = 0.1

# --- Shell ---
skin = 1.8                   # all outer walls
floor_t = 1.6
chan_w = 7.5                 # left channel: slim right-angle USB-A head
trench_w = 5.0
trench_wall = 1.2
corner_r = 3.0
bottom_chamfer = 1.2
lid_t = 1.6
lid_chamfer = 0.6
lip_t, lip_h = 0.8, 3.0      # faceplate lip over the wall step
lip_cl = 0.1                 # fit clearance lip <-> step
catch_h, catch_d, catch_len = 0.8, 0.3, 8.0   # snap bumps on the lip / grooves in the step
scoop_r, scoop_depth, scoop_w = 14.0, 7.0, 28.0

# --- Ventilation ---
floor_slot_w, floor_slot_len, floor_slot_pitch, floor_slot_n = 3.0, 50.0, 6.0, 7
wall_vent_w, wall_vent_pitch = 2.5, 5.0

eps = 0.01

# ============================================================
# DERIVED
# ============================================================
x_pcb = skin + chan_w + port_overhang               # Pi PCB left edge
cx0 = skin + cp_left_gap                            # Cardputer pocket
cp_bay_w, cp_bay_d = cp_w + 2 * cp_cl, cp_d + 2 * cp_cl
cx1 = cx0 + cp_bay_w
tb_x0 = cx1 + tb_gap_to_plug                       # trackball board left edge
W = max(cx1 + plug_bay_min + skin,                  # Cardputer row
        x_pcb + pi_w + pi_cl + skin,                # Pi row
        (tb_x0 + tb_board_w + 0.6 + skin) if tb_enable else 0)
y_cp0 = skin
y_cp_back = y_cp0 + cp_cl + cp_d
ty0 = y_cp0 + cp_bay_d + trench_wall                # cable trench
ty1 = ty0 + trench_w
y_pi0 = ty1 + trench_wall                           # Pi bay front
pi_ox, pi_oy = x_pcb, y_pi0 + pi_cl
D = pi_oy + pi_d + pi_cl_back + skin
pcb_z = floor_t + standoff_h
pcb_top = pcb_z + pi_pcb_t
H = pcb_top + stack_above_pcb + lid_gap             # tray rim; faceplate sits on it
TOP = H + lid_t
cp_floor_z = floor_t
cp_recess = TOP - cp_floor_z - cp_h
assert cp_recess >= 0, "case thinner than the Cardputer"
assert cp_floor_z + cp_usb_z + usb_c_half_h <= H + plug_relief, "USB-C plug hits the faceplate"
cp_mid = (cx0 + cx1) / 2
cp_usb_y = y_cp_back - cp_usb_from_back
cp_grove_y = y_cp_back - cp_grove_from_back
win_cx = x_pcb + pi_w / 2 + lcd_win_dx
win_cy = pi_oy + pi_d / 2 + lcd_win_dy
tb_cx = tb_x0 + tb_board_w / 2
tb_seat_z = TOP + tb_ball_protrude - tb_h           # underside of the trackball board
btn_x0 = tb_cx - btn_gap / 2 - btn_w                # L tab; R tab = btn_x0 + btn_w + btn_gap
sw_top_z = H - btn_nub_h - sw_h + sw_preload        # pedestal top for the switches
assert tb_cy - tb_board_d / 2 > btn_y0 + btn_d + 1.0, "buttons overlap the trackball"


def pi_to_dev(x, y):
    """Pi rotated 180 deg: HDMI edge at the back, USB/Eth edge on the left."""
    return (pi_ox + pi_w - x, pi_oy + pi_d - y)


def box(x0, y0, z0, x1, y1, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


step_z = H - lip_h                                  # top of the wall is stepped for the lip
# snap catches: (x, y, side) along the straight parts of the walls, clear of openings
catches = [(skin / 2, 22.0, "x"), (skin / 2, y_pi0 - 2.0, "x"),
           (W - skin / 2, 14.0, "x"), (W - skin / 2, D - 8.0, "x"),
           (W * 0.22, skin / 2, "y"), (W * 0.78, skin / 2, "y"),
           (W * 0.25, D - skin / 2, "y")]


def outline(inset, z0, z1):
    r = max(0.2, corner_r - inset)
    return (cq.Workplane("XY").rect(W - 2 * inset, D - 2 * inset).extrude(z1 - z0)
            .edges("|Z").fillet(r).translate((W / 2, D / 2, z0)))


def catch(x, y, side, grow, z_mid):
    """Bump (grow=0) or groove (grow>0) straddling the lip/step interface."""
    L, d, h = catch_len + grow, catch_d + grow, catch_h + grow
    edge = lip_t                                   # interface sits lip_t in from the outside
    if side == "x":
        xi = edge if x < W / 2 else W - edge
        sgn = 1 if x < W / 2 else -1
        x0, x1 = sorted((xi, xi + sgn * d))
        return box(x0, y - L / 2, z_mid - h / 2, x1, y + L / 2, z_mid + h / 2)
    yi = edge if y < D / 2 else D - edge
    sgn = 1 if y < D / 2 else -1
    y0, y1 = sorted((yi, yi + sgn * d))
    return box(x - L / 2, y0, z_mid - h / 2, x + L / 2, y1, z_mid + h / 2)


catch_z = step_z + lip_h * 0.45

# ============================================================
# TRAY
# ============================================================
tray = (cq.Workplane("XY").box(W, D, H, centered=False)
        .edges("|Z").fillet(corner_r)
        .faces("<Z").edges().chamfer(bottom_chamfer))

# Pi bay: wall to wall (left part is the cable channel / jack space)
tray = tray.cut(box(skin, y_pi0, floor_t, W - skin, D - skin, H + eps))
# Left channel down to the trench, and the trench itself
tray = tray.cut(box(skin, ty0, floor_t, skin + chan_w, y_pi0 + eps, H + eps))
tray = tray.cut(box(skin, ty0, floor_t, W - skin, ty1, H + eps))
# Cardputer pocket
tray = tray.cut(box(cx0, y_cp0, cp_floor_z, cx1, y_cp0 + cp_bay_d, H + eps))
# Plug bay right of the Cardputer, open into the trench
tray = tray.cut(box(cx1 - eps, cp_usb_y - 7.0, cp_floor_z + 3.0, W - skin, ty0 + eps, H + eps))
if tb_enable:
    # Trackball / button zone: hollow from the floor, a thin rib keeps the Cardputer located
    tray = tray.cut(box(cx1 + 1.2, skin, floor_t, W - skin, ty0 + eps, H + eps))
    for cx, cy in [(tb_x0 + 1.5, tb_cy - tb_board_d / 2 + 1.5), (tb_x0 + tb_board_w - 1.5, tb_cy - tb_board_d / 2 + 1.5),
                   (tb_x0 + 1.5, tb_cy + tb_board_d / 2 - 1.5), (tb_x0 + tb_board_w - 1.5, tb_cy + tb_board_d / 2 - 1.5)]:
        tray = tray.union(box(cx - tb_post / 2, cy - tb_post / 2, floor_t - eps, cx + tb_post / 2, cy + tb_post / 2, tb_seat_z))
    for bx in (btn_x0, btn_x0 + btn_w + btn_gap):
        sx, sy = bx + btn_w / 2, btn_y0 + btn_d / 2
        tray = tray.union(box(sx - 4.5, sy - 4.5, floor_t - eps, sx + 4.5, sy + 4.5, sw_top_z))
# Grove room left of the Cardputer (option B only, when cp_left_gap is set)
if cp_left_gap > 0.5:
    tray = tray.cut(box(skin, cp_grove_y - 6.0, cp_floor_z + 1.0, cx0 + eps, ty0 + eps, H + eps))
# Speaker: grille in the right wall only when nothing sits beside the Cardputer
if not tb_enable:
    for i in range(4):
        y = cp_usb_y - 4.5 + i * 3.0
        tray = tray.cut(box(W - skin - eps, y, cp_floor_z + spk_z - 4.0, W + eps, y + 1.6, cp_floor_z + spk_z + 4.0))

# Step around the top of the outer wall for the faceplate lip, plus catch grooves
tray = tray.cut(outline(0, step_z, H + eps).cut(outline(lip_t + lip_cl, step_z - eps, H + 2 * eps)))
for x, y, side in catches:
    tray = tray.cut(catch(x, y, side, 0.15, catch_z))

# Pi standoffs
for hx, hy in pi_holes:
    x, y = pi_to_dev(hx, hy)
    tray = tray.union(cyl(x, y, floor_t - eps, pcb_z, standoff_od))
    tray = tray.cut(cyl(x, y, 0.6, pcb_z + eps, pilot_d))


# --- Left skin openings (user-facing ports). Lower-front USB stays hidden (internal cable).
def left_open(pi_y, half_w, z0, z1):
    _, yc = pi_to_dev(0, pi_y)
    return box(-eps, yc - half_w, z0, skin + eps, yc + half_w, z1)

tray = tray.cut(left_open(eth_y, 8.5, pcb_top - 0.5, pcb_top + 15.0))         # Ethernet
tray = tray.cut(left_open(usb_front_y, 8.0, pcb_top + 8.0, H + eps))         # upper USB, front pair (open to the lip)
tray = tray.cut(left_open(usb_back_y, 8.0, pcb_top - 0.5, H + eps))          # both USB, back pair (open to the lip)

# --- Back: USB-C power, RTC JST, micro-HDMI x2, UART JST (plug over-moulds go through)
bx0, _ = pi_to_dev(47.0, 0)
bx1, _ = pi_to_dev(3.0, 0)
tray = tray.cut(box(bx0 - 1.5, D - skin - eps, pcb_z - 1.5, bx1 + 1.5, D + eps, pcb_top + 9.0))
for i in range(int((bx1 - bx0) // wall_vent_pitch)):
    x = bx0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(x, D - skin - eps, pcb_top + 11.0, x + wall_vent_w, D + eps, step_z - 0.8))

# --- Right: microSD + power button, cooler exhaust
_, sy0 = pi_to_dev(0, 50.0)
_, sy1 = pi_to_dev(0, 6.0)
tray = tray.cut(box(W - skin - eps, sy0, floor_t + 0.6, W + eps, sy1, pcb_top + 4.0))
for i in range(int((sy1 - sy0) // wall_vent_pitch)):
    y = sy0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(W - skin - eps, y, pcb_top + 6.5, W + eps, y + wall_vent_w, step_z - 0.8))

# --- Floor vents under the Pi
for i in range(floor_slot_n):
    y = win_cy + (i - (floor_slot_n - 1) / 2) * floor_slot_pitch
    tray = tray.cut(cq.Workplane("XY").slot2D(floor_slot_len, floor_slot_w)
                    .extrude(floor_t + 2 * eps).translate((win_cx, y, -eps)))


# --- Finger scoop at the front (shared with the faceplate)
def scoop():
    return (cq.Workplane("XZ").circle(scoop_r).extrude(-(y_cp0 + 1.0))
            .translate((cp_mid, -0.5, TOP + scoop_r - scoop_depth))
            .intersect(box(cp_mid - scoop_w / 2, -1, 0, cp_mid + scoop_w / 2, y_cp0 + 1, TOP + 1)))

tray = tray.cut(scoop())

# ============================================================
# FACEPLATE (modelled in place)
# ============================================================
face = outline(0, H, TOP).union(outline(0, step_z, H + eps).cut(outline(lip_t, step_z - eps, H + 2 * eps)))
for x, y, side in catches:
    face = face.union(catch(x, y, side, 0.0, catch_z))
face = face.cut(cq.Workplane("XY").rect(lcd_win_w, lcd_win_d).extrude(lid_t + 2 * eps)
                .edges("|Z").fillet(2.0).translate((win_cx, win_cy, H - eps)))
face = face.cut(cq.Workplane("XY").rect(cp_bay_w, cp_bay_d).extrude(lid_t + 2 * eps)
                .edges("|Z").fillet(2.0)
                .translate((cp_mid, y_cp0 + cp_bay_d / 2, H - eps)))
face = face.faces(">Z").edges().chamfer(lid_chamfer)
face = face.cut(box(cx1 - 0.5, cp_usb_y - 7.0, H - eps, W - skin, ty1, H + plug_relief))
face = face.cut(scoop())
if tb_enable:
    face = face.cut(cyl(tb_cx, tb_cy, H - eps, TOP + eps, tb_hole_d))                    # ball
    face = face.cut(box(tb_x0 - 0.5, tb_cy - tb_board_d / 2 - 0.5, H - eps,
                        tb_x0 + tb_board_w + 0.5, tb_cy + tb_board_d / 2 + 0.5, H + 0.8))  # module relief
    for bx in (btn_x0, btn_x0 + btn_w + btn_gap):
        x0, x1, y0, y1 = bx, bx + btn_w, btn_y0, btn_y0 + btn_d
        u = (box(x0 - btn_slot, y0 - btn_slot, H - eps, x1 + btn_slot, y1, TOP + eps)
             .cut(box(x0, y0, H - 1, x1, y1 + 1, TOP + 1)))                      # U slot, hinge at the back
        face = face.cut(u)
        face = face.cut(box(x0, y1 - 1.5, H - eps, x1, y1 + 0.5, TOP - btn_hinge_t))   # thin hinge
        face = face.union(cyl(bx + btn_w / 2, y0 + btn_d / 2, H - btn_nub_h, H + eps, btn_nub_d))  # nub
        face = face.cut(cyl(bx + btn_w / 2, y0 + btn_d / 2, TOP - 0.4, TOP + eps, 6.0))    # finger dimple
    # speaker grille over the Cardputer's right end, grille over the bay right of the Pi
    for i in range(4):
        face = face.cut(cq.Workplane("XY").slot2D(6.0, 1.6).extrude(lid_t + 2 * eps)
                        .translate((cx1 + 4.5, cp_usb_y - 9.0 - i * 3.2, H - eps)))
    gx = (x_pcb + pi_w + pi_cl + W - skin) / 2
    for i in range(7):
        face = face.cut(cq.Workplane("XY").slot2D(12.0, 2.0)
                        .extrude(lid_t + 2 * eps).translate((gx, win_cy + (i - 3) * 6.0, H - eps)))
face = face.cut(left_open(usb_front_y, 8.0, pcb_top + 8.0, H + eps))
face = face.cut(left_open(usb_back_y, 8.0, pcb_top - 0.5, H + eps))

# ============================================================
# EXPORT
# ============================================================
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
os.makedirs(out, exist_ok=True)
face_print = face.translate((0, 0, -H)).rotate((0, 0, 0), (1, 0, 0), 180)
face_print = face_print.translate((0, 0, -face_print.val().BoundingBox().zmin))
if __name__ == "__main__":
    cq.exporters.export(tray, os.path.join(out, "deck_tray.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(face_print, os.path.join(out, "deck_faceplate.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(tray.union(face), os.path.join(out, "deck_assembled_preview.stl"),
                        tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(tray, os.path.join(out, "deck_tray.step"))
    cq.exporters.export(face_print, os.path.join(out, "deck_faceplate.step"))
print(f"Case v7: {W:.1f} x {D:.1f} x {TOP:.1f} mm | x_pcb={x_pcb:.1f} pi_oy={pi_oy:.1f} "
      f"cp x {cx0:.1f}..{cx1:.1f} y {y_cp0:.1f}..{y_cp0 + cp_bay_d:.1f} trench {ty0:.1f}..{ty1:.1f} "
      f"usb_c y={cp_usb_y:.1f} trackball x {tb_x0:.1f} c=({tb_cx:.1f},{tb_cy:.1f}) seat z={tb_seat_z:.1f} "
      f"buttons x {btn_x0:.1f} sw_top={sw_top_z:.1f}")
