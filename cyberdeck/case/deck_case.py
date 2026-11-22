"""
Pi 5 + 3.5" GPIO LCD + M5Stack Cardputer "mini-deck" case  -  v4 (slim)

v4 = v3 made as thin as the parts allow (25.1 mm): 1.6 mm floor, 2.5 mm Pi standoffs,
1.6 mm faceplate, and the Cardputer resting straight on the floor.
Fitted to measured Cardputer v1.1 photos: one faceplate over the whole top, the
Cardputer inset ~1.5 mm below it, and the USB link cable fully hidden:
  Pi lower-front USB-A -> left channel (under the Ethernet jack) -> trench inside the
  divider -> plug bay on the RIGHT of the Cardputer, where its USB-C is (back end, near top).
Speaker grille in the right wall lines up with the Cardputer speaker under its USB-C.

Top view (user sits at the bottom):

   +----------------------------------------------+
   | [o]        back: USB-C power, 2x HDMI, UART [o]|
   | |c|  +------------------------------------+   |
   | |h|  |  3.5" LCD window (Pi 5 underneath) |   |  right: microSD / power button + vents
   | |a|  +------------------------------------+   |
   | |n|==========  divider cable trench  ========|
   |  +------------------------------------+ |pl|  |
   |  | Cardputer (inset, drops in)        |=|ug|  |  <- USB-C on its right end
   |  +------------------------------------+       |
   | [o]              ( scoop )               [o]  |
   +----------------------------------------------+
   left wall: openings for Ethernet, upper USB of the front pair, both USB of the back pair.
   The lower-front USB-A port is used internally for the Cardputer cable.

Printed parts:
  deck_tray.stl       body. Print upright (floor on bed), no supports.
  deck_faceplate.stl  top plate. Print top face DOWN, no supports.

Hardware: 4x M2.5x5 (Pi -> standoffs), 4x M2.5x8 self-tapping (faceplate -> tray),
          1x USB-A (right-angle, "up/down" angled) to USB-C (right-angle, "left/right"), ~20 cm.

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
pi_cl = 1.0
port_overhang = 2.5          # USB/Ethernet jacks stick out past the PCB edge
eth_y, usb_front_y, usb_back_y = 45.75, 29.1, 10.2   # jack centres along the Pi edge (Pi coords)

# --- Pi + LCD stack ---
standoff_h = 2.5            # Pi 5 underside is flat apart from the microSD socket (~1.4 mm)
standoff_od = 6.0
pilot_d = 2.2
stack_above_pcb = 17.5       # Pi PCB top -> LCD glass top. MEASURE
lid_gap = 0.3

# --- LCD window ---
lcd_win_w, lcd_win_d = 75.0, 51.0
lcd_win_dx, lcd_win_dy = 0.0, 0.0

# --- Cardputer v1.1 (84 x 54; measured ~22 tall at the StampS3A block, doc says 19.7) ---
cp_w, cp_d, cp_h = 84.0, 54.0, 22.0
cp_cl = 0.4
cp_usb_from_back = 10.0      # USB-C centre, RIGHT end, measured from the Cardputer's back edge
cp_usb_z = 19.0              # USB-C centre height above the Cardputer's bottom
cp_grove_from_back = 9.0     # Grove port centre, LEFT end, from the back edge
cp_left_gap = 6.7            # room left of the Cardputer (Grove plug, option B)
plug_bay_w = 11.5            # room right of the Cardputer for the right-angle USB-C head
plug_relief = 1.0            # pocket in the faceplate underside over the USB-C head
usb_c_half_h = 3.3           # right-angle USB-C overmould, half height
spk_from_back, spk_z = 10.0, 13.0   # speaker grille under the USB-C

# --- Shell ---
floor_t = 1.6
outer_left = 2.5             # outer skin of the cable channel
chan_w = 11.0                # free width between port faces / Cardputer and the skin
right_wall = 6.0
front_wall = 6.0
back_wall = 6.0
divider = 8.0                # holds a cable trench
trench_w = 5.0
corner_r = 5.0
bottom_chamfer = 1.5
lid_t = 1.6
lid_chamfer = 0.6
screw_d, lid_pilot_d, lid_pilot_depth = 2.8, 2.2, 12.0
scoop_r, scoop_depth, scoop_w = 14.0, 8.0, 28.0

# --- Ventilation ---
floor_slot_w, floor_slot_len, floor_slot_pitch, floor_slot_n = 3.0, 50.0, 6.0, 7
wall_vent_w, wall_vent_pitch = 2.5, 5.0

eps = 0.01

# ============================================================
# DERIVED
# ============================================================
x_pcb = outer_left + chan_w + port_overhang          # Pi PCB left edge
bay_x0, bay_x1 = x_pcb - pi_cl, x_pcb + pi_w + pi_cl
W = bay_x1 + right_wall
y_cp0 = front_wall
cp_bay_w, cp_bay_d = cp_w + 2 * cp_cl, cp_d + 2 * cp_cl
y_pi0 = y_cp0 + cp_bay_d + divider
D = y_pi0 + pi_d + 2 * pi_cl + back_wall
pcb_z = floor_t + standoff_h
pcb_top = pcb_z + pi_pcb_t
H = pcb_top + stack_above_pcb + lid_gap            # tray rim; faceplate sits on it
TOP = H + lid_t
cp_floor_z = floor_t                               # Cardputer sits on the floor
cp_recess = TOP - cp_floor_z - cp_h
assert cp_recess >= 0, "case thinner than the Cardputer"
assert cp_floor_z + cp_usb_z + usb_c_half_h <= H + plug_relief, "USB-C plug hits the faceplate"
cx_mid = (bay_x0 + bay_x1) / 2                      # Pi / LCD centre line
cx0 = outer_left + cp_left_gap                       # Cardputer pocket left edge
cx1 = cx0 + cp_bay_w
assert W - outer_left - cx1 >= plug_bay_w - 0.01, "no room for the USB-C plug"
cp_mid = (cx0 + cx1) / 2
y_cp_back = y_cp0 + cp_cl + cp_d                    # Cardputer back edge
cp_usb_y = y_cp_back - cp_usb_from_back
cp_grove_y = y_cp_back - cp_grove_from_back
ty0 = y_cp0 + cp_bay_d + (divider - trench_w) / 2   # cable trench in the divider
ty1 = ty0 + trench_w
pi_ox, pi_oy = x_pcb, y_pi0 + pi_cl


def pi_to_dev(x, y):
    """Pi rotated 180 deg: HDMI edge at the back, USB/Eth edge on the left."""
    return (pi_ox + pi_w - x, pi_oy + pi_d - y)


def box(x0, y0, z0, x1, y1, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


screw_pts = [(6.5, 6.5), (W - 3.5, 3.5), (5.0, D - 3.5), (W - 3.5, D - 3.5)]

# ============================================================
# TRAY
# ============================================================
tray = (cq.Workplane("XY").box(W, D, H, centered=False)
        .edges("|Z").fillet(corner_r)
        .faces("<Z").edges().chamfer(bottom_chamfer))

# Pi bay (extends left into the channel where the jacks are)
tray = tray.cut(box(outer_left, y_pi0, floor_t, bay_x1, y_pi0 + pi_d + 2 * pi_cl, H + eps))
# Left channel: from the Pi bay forward to the divider trench
tray = tray.cut(box(outer_left, ty0, floor_t, outer_left + chan_w, y_pi0 + eps, H + eps))
# Cable trench along the divider, wall to wall
tray = tray.cut(box(outer_left, ty0, floor_t, W - outer_left, ty1, H + eps))
# Cardputer pocket
tray = tray.cut(box(cx0, y_cp0, cp_floor_z, cx1, y_cp0 + cp_bay_d, H + eps))
# Plug bay right of the Cardputer (USB-C head), open into the trench
tray = tray.cut(box(cx1 - eps, cp_usb_y - 7.0, cp_floor_z + 3.0, W - outer_left, ty0 + eps, H + eps))
# Grove room left of the Cardputer (option B), open into the trench
tray = tray.cut(box(outer_left, cp_grove_y - 6.0, cp_floor_z + 1.0, cx0 + eps, ty0 + eps, H + eps))
# Speaker grille through the right wall, in line with the Cardputer speaker
for i in range(4):
    y = cp_usb_y - 4.5 + i * 3.0
    tray = tray.cut(box(W - outer_left - eps, y, cp_floor_z + spk_z - 4.0, W + eps, y + 1.6, cp_floor_z + spk_z + 4.0))

# Pi standoffs
for hx, hy in pi_holes:
    x, y = pi_to_dev(hx, hy)
    tray = tray.union(cq.Workplane("XY").circle(standoff_od / 2).extrude(standoff_h)
                      .translate((x, y, floor_t - eps)))
    tray = tray.cut(cq.Workplane("XY").circle(pilot_d / 2).extrude(floor_t + standoff_h)
                    .translate((x, y, 0.6)))

# --- Left skin openings (user-facing ports). Lower-front USB stays hidden (internal cable).
def left_open(pi_y, half_w, z0, z1):
    _, yc = pi_to_dev(0, pi_y)
    return box(-eps, yc - half_w, z0, outer_left + eps, yc + half_w, z1)

tray = tray.cut(left_open(eth_y, 8.5, pcb_top - 0.5, pcb_top + 15.0))         # Ethernet
tray = tray.cut(left_open(usb_front_y, 8.0, pcb_top + 8.0, pcb_top + 16.8))   # upper USB, front pair
tray = tray.cut(left_open(usb_back_y, 8.0, pcb_top - 0.5, pcb_top + 16.8))    # both USB, back pair

# --- Back: USB-C power, RTC JST, micro-HDMI x2, UART JST
bx0, _ = pi_to_dev(47.0, 0)
bx1, _ = pi_to_dev(3.0, 0)
tray = tray.cut(box(bx0, D - back_wall - eps, pcb_z - 1.0, bx1, D + eps, pcb_top + 8.0))
tray = tray.cut(box(bx0 - 2, D - 3.0, pcb_z - 2.5, bx1 + 1, D + eps, pcb_top + 9.5))
for i in range(int((bx1 - bx0) // wall_vent_pitch)):
    x = bx0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(x, D - back_wall - eps, pcb_top + 11.0, x + wall_vent_w, D + eps, H - 2.0))

# --- Right: microSD + power button, cooler exhaust
_, sy0 = pi_to_dev(0, 50.0)
_, sy1 = pi_to_dev(0, 6.0)
tray = tray.cut(box(W - right_wall - eps, sy0, floor_t + 1.0, W + eps, sy1, pcb_top + 4.0))
for i in range(int((sy1 - sy0) // wall_vent_pitch)):
    y = sy0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(W - right_wall - eps, y, pcb_top + 6.5, W + eps, y + wall_vent_w, H - 2.0))

# --- Floor vents under the Pi
fy_c = y_pi0 + pi_cl + pi_d / 2
for i in range(floor_slot_n):
    y = fy_c + (i - (floor_slot_n - 1) / 2) * floor_slot_pitch
    tray = tray.cut(cq.Workplane("XY").slot2D(floor_slot_len, floor_slot_w)
                    .extrude(floor_t + 2 * eps).translate((cx_mid, y, -eps)))

# --- Finger scoop at the front (shared with the faceplate)
def scoop():
    return (cq.Workplane("XZ").circle(scoop_r).extrude(-(y_cp0 + 1.0))
            .translate((cp_mid, -0.5, TOP + scoop_r - scoop_depth))
            .intersect(box(cp_mid - scoop_w / 2, -1, 0, cp_mid + scoop_w / 2, y_cp0 + 1, TOP + 1)))

tray = tray.cut(scoop())

# --- Faceplate screw pilots
for x, y in screw_pts:
    tray = tray.cut(cq.Workplane("XY").circle(lid_pilot_d / 2).extrude(lid_pilot_depth + eps)
                    .translate((x, y, H - lid_pilot_depth)))

# ============================================================
# FACEPLATE (modelled in place)
# ============================================================
face = box(0, 0, H, W, D, TOP).edges("|Z").fillet(corner_r)
wcx = cx_mid + lcd_win_dx
wcy = y_pi0 + pi_cl + pi_d / 2 + lcd_win_dy
face = face.cut(cq.Workplane("XY").rect(lcd_win_w, lcd_win_d).extrude(lid_t + 2 * eps)
                .edges("|Z").fillet(2.0).translate((wcx, wcy, H - eps)))
face = face.cut(cq.Workplane("XY").rect(cp_bay_w, cp_bay_d).extrude(lid_t + 2 * eps)
                .edges("|Z").fillet(2.0)
                .translate((cp_mid, y_cp0 + cp_bay_d / 2, H - eps)))
face = face.faces(">Z").edges().chamfer(lid_chamfer)
face = face.cut(box(cx1 - 0.5, cp_usb_y - 7.0, H - eps, W - outer_left, ty1, H + plug_relief))
face = face.cut(scoop())
for x, y in screw_pts:
    face = face.cut(cq.Workplane("XY").circle(screw_d / 2).extrude(lid_t + 2 * eps)
                    .translate((x, y, H - eps)))
    face = face.cut(cq.Workplane("XY").circle(2.6).extrude(0.6 + eps)
                    .translate((x, y, TOP - 0.6)))          # shallow head recess
# grille over the cable channel / port side, mirrored by one on the right margin
for gx in (outer_left + chan_w / 2 + 1.5, bay_x1 + right_wall / 2 - 1.0):
    for i in range(6):
        y = wcy + (i - 2.5) * 7.0
        face = face.cut(cq.Workplane("XY").slot2D(5.0, 2.0, angle=90)
                        .extrude(lid_t + 2 * eps).translate((gx, y, H - eps)))

# ============================================================
# EXPORT
# ============================================================
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
os.makedirs(out, exist_ok=True)
face_print = face.translate((0, 0, -H)).rotate((0, 0, 0), (1, 0, 0), 180)
face_print = face_print.translate((0, 0, -face_print.val().BoundingBox().zmin))
if __name__ == "__main__":
    for old in ("deck_lid.stl", "deck_lid.step"):
        p = os.path.join(out, old)
        if os.path.exists(p):
            os.remove(p)
    cq.exporters.export(tray, os.path.join(out, "deck_tray.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(face_print, os.path.join(out, "deck_faceplate.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(tray.union(face), os.path.join(out, "deck_assembled_preview.stl"),
                        tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(tray, os.path.join(out, "deck_tray.step"))
    cq.exporters.export(face_print, os.path.join(out, "deck_faceplate.step"))
print(f"Case v4: {W:.1f} x {D:.1f} x {TOP:.1f} mm  | Pi PCB x={x_pcb:.1f}, Pi bay y0={y_pi0:.1f}, "
      f"pocket x {cx0:.1f}..{cx1:.1f}, floor z={cp_floor_z:.1f}, recess={cp_recess:.1f}, pcb_z={pcb_z:.1f}, USB-C y={cp_usb_y:.1f} "
      f"z={cp_floor_z + cp_usb_z:.1f}, Grove y={cp_grove_y:.1f}, trench y {ty0:.1f}..{ty1:.1f}")
