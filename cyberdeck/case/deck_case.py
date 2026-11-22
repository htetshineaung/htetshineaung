"""
Pi 5 + 3.5" GPIO LCD + M5Stack Cardputer "mini-deck" case.

Layout (top view, user sits at the bottom of this sketch):

        back  (USB-C power, 2x micro-HDMI, UART JST exit here)
   +-------------------------------------------+
   |  [screw]                         [screw]  |
   |  +-------------------------------------+  |
   |  |   Raspberry Pi 5 + 3.5" LCD          |  |  <- right wall: microSD / power-button slot
   |  |   (rotated 180 deg, GPIO faces you)  |  |
   |  +-------------------------------------+  |
   |  [screw]       divider (Grove tunnel)  [screw]
   |  +-------------------------------------+  |
   |  |        M5Stack Cardputer            |  |
   |  |        (drops in from the top)      |  |
   |  +--------------( finger )-------------+  |
   +-------------------------------------------+
        front
   ^ left wall: Pi USB-A x4 + Ethernet open slot

Two printed parts:
  deck_tray.stl  - body. Print upright (floor on bed), no supports.
  deck_lid.stl   - screen bezel over the Pi section. Print top face DOWN, no supports.

Hardware: 4x M2.5x6 screws (Pi -> printed standoffs, or M2.5 brass standoffs that
came with the LCD), 4x M2.5x8 self-tapping (lid -> tray corner pillars).

!! Measure YOUR stack before printing: `stack_above_pcb` (Pi PCB top surface ->
   top of LCD glass) and the LCD window offset. Everything else follows.
"""
import os
import cadquery as cq

# ============================================================
# PARAMETERS (mm)
# ============================================================
# --- Raspberry Pi 5 (official mechanical drawing) ---
pi_w = 85.0              # board length (USB/Ethernet edge is the far end)
pi_d = 56.0              # board width (HDMI/USB-C edge -> GPIO edge)
pi_pcb_t = 1.6
pi_holes = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]  # from corner opposite USB, HDMI edge = y0
pi_cl = 1.0              # clearance around the board

# --- Pi + LCD stack ---
standoff_h = 4.0         # floor -> underside of Pi PCB (airflow under the SoC)
standoff_od = 6.0
pilot_d = 2.2            # M2.5 self-tap pilot
stack_above_pcb = 17.5   # Pi PCB top -> LCD glass top. MEASURE (photo suggests ~17-19 w/ low cooler)
lid_gap = 0.3            # air gap between glass and lid underside

# --- 3.5" 480x320 LCD visible window ---
lcd_win_w = 75.0         # active area is ~73.4 x 49.0, +margin
lcd_win_d = 51.0
lcd_win_dx = 0.0         # shift window along device X (+ = right) to match your glass
lcd_win_dy = 0.0         # shift window along device Y (+ = back)

# --- M5Stack Cardputer (docs.m5stack.com: 84.0 x 54.0 x 19.7) ---
cp_w = 84.0
cp_d = 54.0
cp_h = 19.7
cp_cl = 0.4              # per side, drop-in fit (PLA)
cp_protrude = 1.5        # Cardputer top sits this much above the tray rim (easy to grab)
cp_side_slot_len = 34.0  # side cut-outs (USB-C / power switch / IR). VERIFY on your unit
cp_side_slot_y = 0.62    # slot centre as a fraction of Cardputer depth from the front
finger_w = 30.0          # front finger notch
grove_w = 20.0           # tunnel through divider for the Grove cable (UART option)
grove_dx = 0.0           # tunnel centre offset from case centre

# --- Shell ---
floor_t = 2.0
side_wall = 6.0          # thick so the lid screw pillars live outside the Pi footprint
back_wall = 6.0
divider = 6.0
front_wall = 3.0
corner_r = 3.0
bottom_chamfer = 0.8
lid_t = 2.4
lid_screw_d = 2.8        # M2.5 clearance in the lid
lid_pilot_d = 2.2
lid_pilot_depth = 12.0

# --- Ventilation ---
floor_slot_w = 3.0
floor_slot_len = 50.0
floor_slot_pitch = 6.0
floor_slot_n = 7
wall_vent_w = 2.5
wall_vent_pitch = 5.0

eps = 0.01

# ============================================================
# DERIVED
# ============================================================
bay_pi_w = pi_w + 2 * pi_cl                     # 87
bay_pi_d = pi_d + 2 * pi_cl                     # 58
W = bay_pi_w + 2 * side_wall                    # 99
cp_bay_w = cp_w + 2 * cp_cl
cp_bay_d = cp_d + 2 * cp_cl
y_cp0 = front_wall
y_pi0 = front_wall + cp_bay_d + divider         # front edge of Pi bay
D = y_pi0 + bay_pi_d + back_wall
pcb_z = floor_t + standoff_h                    # underside of Pi PCB
pcb_top = pcb_z + pi_pcb_t
H = pcb_top + stack_above_pcb + lid_gap         # tray rim height
cp_floor_z = H + cp_protrude - cp_h
assert cp_floor_z > floor_t + 1.0, "Cardputer pocket floor too thin"

pi_ox, pi_oy = side_wall + pi_cl, y_pi0 + pi_cl  # Pi board origin (device coords)


def pi_to_dev(x, y):
    """Pi is rotated 180 deg: HDMI edge faces the back, USB/Eth edge faces left."""
    return (pi_ox + pi_w - x, pi_oy + pi_d - y)


def box(x0, y0, z0, x1, y1, z1):
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


screw_pts = [(3.5, y_pi0 - 3.0), (W - 3.5, y_pi0 - 3.0),
             (3.5, D - 3.5), (W - 3.5, D - 3.5)]

# ============================================================
# TRAY
# ============================================================
tray = (cq.Workplane("XY").box(W, D, H, centered=False)
        .edges("|Z").fillet(corner_r)
        .faces("<Z").edges().chamfer(bottom_chamfer))

# Pi bay
tray = tray.cut(box(side_wall, y_pi0, floor_t, side_wall + bay_pi_w, y_pi0 + bay_pi_d, H + eps))
# Cardputer pocket
cx0 = (W - cp_bay_w) / 2
tray = tray.cut(box(cx0, y_cp0, cp_floor_z, cx0 + cp_bay_w, y_cp0 + cp_bay_d, H + eps))

# Pi standoffs
for hx, hy in pi_holes:
    x, y = pi_to_dev(hx, hy)
    post = (cq.Workplane("XY").circle(standoff_od / 2).extrude(standoff_h)
            .translate((x, y, floor_t - eps)))
    tray = tray.union(post)
    tray = tray.cut(cq.Workplane("XY").circle(pilot_d / 2).extrude(standoff_h + 1)
                    .translate((x, y, floor_t + 0.6)))

# --- Pi port openings ---
# Back: USB-C power, RTC JST, micro-HDMI x2, UART JST  (Pi x ~3..47 on HDMI edge)
bx0, _ = pi_to_dev(47.0, 0)
bx1, _ = pi_to_dev(3.0, 0)
tray = tray.cut(box(bx0, D - back_wall - eps, pcb_z - 1.0, bx1, D + eps, pcb_top + 8.0))
# outer relief so plug over-moulds seat fully through the 6 mm wall
tray = tray.cut(box(bx0 - 2, D - 3.0, pcb_z - 2.5, bx1 + 2, D + eps, pcb_top + 9.5))

# Left: USB-A x4 + Ethernet - open to the rim (lid closes it)
tray = tray.cut(box(-eps, y_pi0 + pi_cl + 0.5, pcb_top - 0.5,
                    side_wall + eps, y_pi0 + pi_cl + pi_d - 0.5, H + eps))

# Right: microSD (under PCB) + power button + airflow
_, sy0 = pi_to_dev(0, 50.0)
_, sy1 = pi_to_dev(0, 6.0)
tray = tray.cut(box(W - side_wall - eps, sy0, floor_t + 1.0, W + eps, sy1, pcb_top + 4.0))

# Right wall upper vents (active-cooler exhaust)
vz0, vz1 = pcb_top + 6.5, H - 2.0
n = int((sy1 - sy0) // wall_vent_pitch)
for i in range(n):
    y = sy0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(W - side_wall - eps, y, vz0, W + eps, y + wall_vent_w, vz1))
# Back wall upper vents
for i in range(int((bx1 - bx0) // wall_vent_pitch)):
    x = bx0 + 2.5 + i * wall_vent_pitch
    tray = tray.cut(box(x, D - back_wall - eps, pcb_top + 11.0, x + wall_vent_w, D + eps, H - 2.0))

# Floor vents under the Pi
fy_c = y_pi0 + bay_pi_d / 2
for i in range(floor_slot_n):
    y = fy_c + (i - (floor_slot_n - 1) / 2) * floor_slot_pitch
    tray = tray.cut(cq.Workplane("XY").slot2D(floor_slot_len, floor_slot_w)
                    .extrude(floor_t + 2 * eps).translate((W / 2, y, -eps)))

# --- Cardputer openings ---
fx0 = W / 2 - finger_w / 2
tray = tray.cut(box(fx0, -eps, cp_floor_z + 4.0, fx0 + finger_w, y_cp0 + eps, H + eps))
sc = y_cp0 + cp_cl + cp_d * cp_side_slot_y
for xa, xb in [(-eps, cx0 + eps), (cx0 + cp_bay_w - eps, W + eps)]:
    tray = tray.cut(box(xa, sc - cp_side_slot_len / 2, cp_floor_z + 3.0,
                        xb, sc + cp_side_slot_len / 2, H + eps))
gx = W / 2 + grove_dx
tray = tray.cut(box(gx - grove_w / 2, y_pi0 - divider - eps, cp_floor_z + 3.0,
                    gx + grove_w / 2, y_pi0 + eps, H + eps))

# Lid screw pilots in the four corner pillars
for x, y in screw_pts:
    tray = tray.cut(cq.Workplane("XY").circle(lid_pilot_d / 2).extrude(lid_pilot_depth + eps)
                    .translate((x, y, H - lid_pilot_depth)))

# ============================================================
# LID (bezel over the Pi section) - modelled in place, top face at H + lid_t
# ============================================================
ly0 = y_pi0 - divider
lid = (box(0, ly0, H, W, D, H + lid_t)
       .edges("|Z").fillet(corner_r)
       .faces(">Z").edges().chamfer(0.6))
wcx = side_wall + bay_pi_w / 2 + lcd_win_dx
wcy = y_pi0 + bay_pi_d / 2 + lcd_win_dy
window = (cq.Workplane("XY").rect(lcd_win_w, lcd_win_d).extrude(lid_t + 2 * eps)
          .edges("|Z").fillet(1.5).translate((wcx, wcy, H - eps)))
lid = lid.cut(window)
for x, y in screw_pts:
    lid = lid.cut(cq.Workplane("XY").circle(lid_screw_d / 2).extrude(lid_t + 2 * eps)
                  .translate((x, y, H - eps)))
# small vent slots in the lid side margins
for side in (-1, 1):
    x = wcx + side * (lcd_win_w / 2 + 5.5)
    for i in range(5):
        y = wcy + (i - 2) * 8.0
        lid = lid.cut(cq.Workplane("XY").slot2D(6.0, 2.2, angle=90)
                      .extrude(lid_t + 2 * eps).translate((x, y, H - eps)))

# ============================================================
# EXPORT
# ============================================================
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
os.makedirs(out, exist_ok=True)
lid_print = lid.translate((0, 0, -H)).rotate((0, 0, 0), (1, 0, 0), 180)  # top face down
lid_print = lid_print.translate((0, 0, -lid_print.val().BoundingBox().zmin))
cq.exporters.export(tray, os.path.join(out, "deck_tray.stl"), tolerance=0.01, angularTolerance=0.1)
cq.exporters.export(lid_print, os.path.join(out, "deck_lid.stl"), tolerance=0.01, angularTolerance=0.1)
cq.exporters.export(tray.union(lid), os.path.join(out, "deck_assembled_preview.stl"),
                    tolerance=0.01, angularTolerance=0.1)
cq.exporters.export(tray, os.path.join(out, "deck_tray.step"))
cq.exporters.export(lid_print, os.path.join(out, "deck_lid.step"))
print(f"Case: {W:.1f} x {D:.1f} x {H + lid_t:.1f} mm  (tray rim {H:.1f}, "
      f"Cardputer floor z={cp_floor_z:.1f})")
