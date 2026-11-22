"""
Pi 5 + 3.5" GPIO LCD + M5Stack Cardputer "mini-deck" case  -  v5 (thin walls)

v5 = slimmest version so far:
  * 25.1 mm thick: 1.6 mm floor, 2.5 mm Pi standoffs, 1.6 mm faceplate, Cardputer on the floor.
  * 1.8 mm outer walls all round. Faceplate screws go into small round posts tucked into
    the spare corners (M2 self-tapping), not into thick walls.
  * Cable fully hidden: Pi lower-front USB-A (slim right-angle plug) -> 7.5 mm left channel,
    under the Ethernet jack -> trench inside the divider -> plug bay right of the Cardputer,
    where its USB-C is (right end, near the back, near the top).
Fitted to measured Cardputer v1.1 photos (USB-C right end, Grove left end, ~22 mm tall).

Top view (user sits at the bottom):

   +---------------------------------------------+
   |o          back: USB-C power, 2x HDMI, UART o|
   |  +---------------------------------------+  |
   |ch|  3.5" LCD window (Pi 5 underneath)     |  |  right: microSD / power button + vents
   |an+---------------------------------------+  |
   |==========  divider cable trench  ==========|
   | +-----------------------------------+ plug |
   | | Cardputer (inset ~1.5 mm)          |=bay  |  <- USB-C on its right end, speaker grille
   |o+-----------------------------------+     o|
   +---------------( scoop )---------------------+

Printed parts:
  deck_tray.stl       body. Print upright (floor on bed), no supports.
  deck_faceplate.stl  top plate. Print top face DOWN, no supports.

Hardware: 4x M2.5x5 (Pi -> standoffs), 4x M2x6 self-tapping (faceplate -> posts),
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
pi_cl_back = 2.3             # extra room at the back so the back-left screw post clears the USB plugs
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
cp_left_gap = 5.0            # room left of the Cardputer (corner post + Grove plug for option B)
plug_bay_min = 9.5           # room right of the Cardputer for the right-angle USB-C head
plug_relief = 1.0            # pocket in the faceplate underside over the USB-C head
usb_c_half_h = 3.3
spk_z = 13.0                 # speaker grille height (under the USB-C)

# --- Shell ---
skin = 1.8                   # all outer walls
floor_t = 1.6
chan_w = 7.5                 # left channel: slim right-angle USB-A head
trench_w = 5.0
trench_wall = 1.2
corner_r = 4.0
bottom_chamfer = 1.2
lid_t = 1.6
lid_chamfer = 0.6
post_od, post_pilot = 4.2, 1.7     # faceplate posts, M2 self-tapping
lid_screw_d, lid_head_d = 2.3, 4.0
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
W = max(cx1 + plug_bay_min + skin,                  # Cardputer row
        x_pcb + pi_w + pi_cl + post_od + skin)      # Pi row incl. right posts
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


def pi_to_dev(x, y):
    """Pi rotated 180 deg: HDMI edge at the back, USB/Eth edge on the left."""
    return (pi_ox + pi_w - x, pi_oy + pi_d - y)


def box(x0, y0, z0, x1, y1, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


pr = post_od / 2 - 0.3        # posts sink 0.3 mm into the walls (no tangent faces)
posts = [
    (skin + pr, skin + pr),                    # front-left, in the gap left of the Cardputer
    (W - skin - pr, skin + pr),                # front-right, right of the Cardputer
    (skin + pr, D - skin - pr),                # back-left, behind the back USB pair
    (W - skin - pr, D - skin - pr),            # back-right, right of the Pi
]
_, usb_back_far = pi_to_dev(0, usb_back_y - 8.0)
assert D - skin - post_od >= usb_back_far - 0.01, "back-left post hits the USB plugs"

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
# Grove room left of the Cardputer (option B), open into the trench
tray = tray.cut(box(skin, cp_grove_y - 6.0, cp_floor_z + 1.0, cx0 + eps, ty0 + eps, H + eps))
# Speaker grille through the right wall, in line with the Cardputer speaker
for i in range(4):
    y = cp_usb_y - 4.5 + i * 3.0
    tray = tray.cut(box(W - skin - eps, y, cp_floor_z + spk_z - 4.0, W + eps, y + 1.6, cp_floor_z + spk_z + 4.0))

# Faceplate posts (added back after the cavities were cut)
for x, y in posts:
    tray = tray.union(cyl(x, y, floor_t - eps, H, post_od))
    tray = tray.cut(cyl(x, y, H - 10.0, H + eps, post_pilot))

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
tray = tray.cut(left_open(usb_front_y, 8.0, pcb_top + 8.0, pcb_top + 16.8))   # upper USB, front pair
tray = tray.cut(left_open(usb_back_y, 8.0, pcb_top - 0.5, pcb_top + 16.8))    # both USB, back pair

# --- Back: USB-C power, RTC JST, micro-HDMI x2, UART JST (plug over-moulds go through)
bx0, _ = pi_to_dev(47.0, 0)
bx1, _ = pi_to_dev(3.0, 0)
tray = tray.cut(box(bx0 - 1.5, D - skin - eps, pcb_z - 1.5, bx1 + 1.5, D + eps, pcb_top + 9.0))
for i in range(int((bx1 - bx0) // wall_vent_pitch)):
    x = bx0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(x, D - skin - eps, pcb_top + 11.0, x + wall_vent_w, D + eps, H - 2.0))

# --- Right: microSD + power button, cooler exhaust
_, sy0 = pi_to_dev(0, 50.0)
_, sy1 = pi_to_dev(0, 6.0)
tray = tray.cut(box(W - skin - eps, sy0, floor_t + 0.6, W + eps, sy1, pcb_top + 4.0))
for i in range(int((sy1 - sy0) // wall_vent_pitch)):
    y = sy0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(W - skin - eps, y, pcb_top + 6.5, W + eps, y + wall_vent_w, H - 2.0))

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
face = box(0, 0, H, W, D, TOP).edges("|Z").fillet(corner_r)
face = face.cut(cq.Workplane("XY").rect(lcd_win_w, lcd_win_d).extrude(lid_t + 2 * eps)
                .edges("|Z").fillet(2.0).translate((win_cx, win_cy, H - eps)))
face = face.cut(cq.Workplane("XY").rect(cp_bay_w, cp_bay_d).extrude(lid_t + 2 * eps)
                .edges("|Z").fillet(2.0)
                .translate((cp_mid, y_cp0 + cp_bay_d / 2, H - eps)))
face = face.faces(">Z").edges().chamfer(lid_chamfer)
face = face.cut(box(cx1 - 0.5, cp_usb_y - 7.0, H - eps, W - skin, ty1, H + plug_relief))
face = face.cut(scoop())
for x, y in posts:
    face = face.cut(cyl(x, y, H - eps, TOP + eps, lid_screw_d))
    face = face.cut(cyl(x, y, TOP - 0.6, TOP + eps, lid_head_d))

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
print(f"Case v5: {W:.1f} x {D:.1f} x {TOP:.1f} mm | x_pcb={x_pcb:.1f} pi_oy={pi_oy:.1f} "
      f"cp x {cx0:.1f}..{cx1:.1f} y {y_cp0:.1f}..{y_cp0 + cp_bay_d:.1f} trench {ty0:.1f}..{ty1:.1f} "
      f"usb_c y={cp_usb_y:.1f} grove y={cp_grove_y:.1f} posts={[(round(a, 1), round(b, 1)) for a, b in posts]}")
