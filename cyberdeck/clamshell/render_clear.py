"""Transparent-case renders: the clamshell shells in clear material with the real internals inside.

    EGL_PLATFORM=surfaceless python render_clear.py [out_dir]

Builds simple stand-in models of everything inside (Pi 5 + ports + cooler, 2S 18650 pack, the
keyboard PCB with its switches, RP2040, trackball and OLED, the 5" DSI screen in the lid), puts
the case parts around them as clear (PETG / clear resin) and renders a few views with pyrender.
Also exports stl/internals_open.stl so you can check fit in a slicer or viewer.
"""
import math
import os
import sys

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
import numpy as np
import pyrender
import trimesh
from PIL import Image

import clamshell as C
import cadquery as cq

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")


def ball(x, y, z, d):
    return cq.Workplane("XY").sphere(d / 2).translate((x, y, z))


# ------------------------------------------------------------------ internals (case coordinates)
parts = {}                                  # name -> (cq shape, rgba, in_lid)


def add(name, shape, rgba, lid=False):
    if name in parts:
        parts[name] = (parts[name][0].union(shape), rgba, lid)
    else:
        parts[name] = (shape, rgba, lid)


# Raspberry Pi 5 (rotated 180 deg: USB / Ethernet at the left wall, HDMI at the back)
add("pi_pcb", C.box(C.x_pcb, C.pi_oy, C.pcb_z, C.x_pcb + C.pi_w, C.pi_oy + C.pi_d, C.pcb_top), (0.10, 0.45, 0.20, 1))
for pi_y, hw, h in ((45.75, 8.0, 13.5), (29.1, 7.0, 15.8), (10.2, 7.0, 15.8)):
    y = C.pi_oy + C.pi_d - pi_y
    add("pi_ports", C.box(C.x_pcb - C.port_overhang, y - hw, C.pcb_top, C.x_pcb + 17.5, y + hw, C.pcb_top + h),
        (0.78, 0.80, 0.83, 1))
cx, cy = C.pi_to_dev(32.0, 30.0)            # SoC + active cooler
add("pi_cooler", C.box(cx - 14, cy - 14, C.pcb_top, cx + 14, cy + 14, C.pcb_top + 8.0), (0.15, 0.15, 0.17, 1))
add("pi_fan", C.cyl(cx, cy, C.pcb_top + 8.0, C.pcb_top + 8.6, 24), (0.30, 0.30, 0.33, 1))
for hx in (C.D - C.wall - 4,):
    for px in (12.0, 25.5):                 # 2x micro-HDMI at the back edge
        x, _ = C.pi_to_dev(px, 0)
        add("pi_ports", C.box(x - 3.5, C.D - C.wall - 7, C.pcb_top, x + 3.5, C.D - C.wall - 0.5, C.pcb_top + 3.2),
            (0.78, 0.80, 0.83, 1))

# 2S 18650 stick pack along the front, under the keys
for i in range(2):
    x0 = C.wall + 1.5 + i * (C.cell_l + C.cell_gap)
    add("cells", C.xcyl(x0, x0 + C.cell_l, C.cell_y0 + C.cell_d / 2, C.floor_t + C.cell_d / 2, C.cell_d / 2),
        (0.10, 0.35, 0.85, 1))
    add("cell_caps", C.xcyl(x0 + C.cell_l - 0.8, x0 + C.cell_l + 0.4, C.cell_y0 + C.cell_d / 2,
                            C.floor_t + C.cell_d / 2, 5.0), (0.75, 0.75, 0.75, 1))

# keyboard PCB (4-layer, matte black) with its parts
kz, kt = C.kb_pcb_z, C.kb_pcb_z + C.kb_pcb_t
add("kb_pcb", C.rbox(3.5, 4.0, kz, 136.5, 76.0, kt, 4.0), (0.08, 0.10, 0.12, 1))
for (x0, y0, x1, y1) in C.key_cells():
    xs = [(x0 + x1) / 2] if x1 - x0 < 10 else [x0 + C.key_w / 2, x1 - C.key_w / 2]
    for x in xs:
        y = (y0 + y1) / 2
        add("switches", C.box(x - 2.55, y - 2.55, kt, x + 2.55, y + 2.55, kt + C.sw_h), (0.85, 0.85, 0.88, 1))
add("rp2040", C.box(64 - 3.5, 60 - 3.5, kz - 0.9, 64 + 3.5, 60 + 3.5, kz), (0.05, 0.05, 0.05, 1))
add("rp2040", C.box(74 - 2.6, 60.5 - 2.6, kz - 1.8, 74 + 2.6, 60.5 + 2.6, kz), (0.05, 0.05, 0.05, 1))   # flash
tb_top = kt + 5.0
add("trackball_body", C.box(C.tb_cx - 6, C.tb_cy - 6, kt, C.tb_cx + 6, C.tb_cy + 6, kt + 4.2), (0.12, 0.12, 0.12, 1))
add("trackball_ball", ball(C.tb_cx, C.tb_cy, tb_top, 7.0), (0.92, 0.18, 0.20, 1))
oz = C.plate_z - 3.2
add("oled_pcb", C.box(C.oled_cx - 13.5, C.oled_cy - 13.5, oz, C.oled_cx + 13.5, C.oled_cy + 13.5, oz + 1.2), (0.10, 0.25, 0.55, 1))
add("oled_glass", C.box(C.oled_cx - 13, C.oled_cy - 8, oz + 1.2, C.oled_cx + 13, C.oled_cy + 8, oz + 2.6), (0.02, 0.02, 0.03, 1))

# 5" DSI screen in the lid (modelled closed, rotated with the lid)
sx0, sx1 = C.W / 2 - C.scr_w / 2, C.W / 2 + C.scr_w / 2
sy0, sy1 = C.scr_cy - C.scr_d / 2, C.scr_cy + C.scr_d / 2
gz = C.lz0 + C.bezel_t
add("screen_glass", C.box(sx0, sy0, gz, sx1, sy1, gz + 1.8), (0.02, 0.03, 0.05, 1), lid=True)
add("screen_pcb", C.box(sx0 + 2, sy0 + 2, gz + 1.8, sx1 - 2, sy1 - 2, gz + 3.4), (0.10, 0.40, 0.18, 1), lid=True)

# case parts: clear shells, frosted clear TPU key mat
CLEAR = (0.80, 0.90, 1.00, 0.20)
case = {"base": (C.base, CLEAR, False), "plate": (C.plate, CLEAR, False),
        "keymat": (C.mat, (0.95, 0.97, 1.00, 0.45), False),
        "lid_back": (C.lid_back, CLEAR, True), "bezel": (C.bezel, (0.75, 0.85, 1.0, 0.25), True)}


def to_mesh(shape, tol=0.08):
    vs, tris = shape.val().tessellate(tol, 0.2)
    v = np.array([(p.x, p.y, p.z) for p in vs], dtype=np.float64)
    return trimesh.Trimesh(v, np.array(tris), process=False)


def build_scene(open_lid, opaque_case=False):
    scene = pyrender.Scene(bg_color=[0.96, 0.97, 0.98, 1.0], ambient_light=[0.35, 0.35, 0.38])
    meshes = []
    for name, (shape, rgba, lid) in list(parts.items()) + list(case.items()):
        s = C.lid_open(shape) if (lid and open_lid) else shape
        tm = to_mesh(s)
        if opaque_case and rgba[3] < 1:
            rgba = (0.93, 0.93, 0.95, 1.0)
        blend = rgba[3] < 1
        mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=rgba, metallicFactor=0.0,
                                                 roughnessFactor=0.15 if blend else 0.6,
                                                 alphaMode="BLEND" if blend else "OPAQUE", doubleSided=True)
        scene.add(pyrender.Mesh.from_trimesh(tm, material=mat, smooth=False))
        meshes.append((name, tm))
    return scene, meshes


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(np.asarray, (eye, target, up))
    f = target - eye; f = f / np.linalg.norm(f)
    s = np.cross(f, up); s = s / np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = s, u, -f, eye
    return m


def render(scene, eye, target, path, size=(1600, 1100), fov=30):
    cam = pyrender.PerspectiveCamera(yfov=math.radians(fov), aspectRatio=size[0] / size[1])
    cn = scene.add(cam, pose=look_at(eye, target))
    lights = []
    for d in ((1, -1, 2), (-1, -0.5, 1.5), (0, 1, 1)):
        pose = look_at(np.array(target) + np.array(d) * 300, target)
        lights.append(scene.add(pyrender.DirectionalLight(color=[1, 1, 1], intensity=2.6), pose=pose))
    r = pyrender.OffscreenRenderer(*size)
    color, _ = r.render(scene, flags=pyrender.RenderFlags.RGBA)
    r.delete()
    scene.remove_node(cn)
    for l in lights:
        scene.remove_node(l)
    Image.fromarray(color).convert("RGB").save(path)
    print("wrote", path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ctr = (C.W / 2, C.D / 2, C.BH / 2)
    scene, meshes = build_scene(open_lid=True)
    trimesh.util.concatenate([m for n, m in meshes if n not in case]).export(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl", "internals_open.stl"))
    render(scene, (C.W / 2 - 150, -230, 210), (C.W / 2, C.D / 2 + 10, 30), os.path.join(OUT, "clear_open.png"))
    render(scene, (C.W / 2 + 0.01, C.D / 2 - 40, 330), (C.W / 2, C.D / 2, 0), os.path.join(OUT, "clear_top.png"), fov=34)
    render(scene, (C.W + 230, -170, 120), (C.W / 2, C.D / 2 + 25, 25), os.path.join(OUT, "clear_side.png"))
    render(scene, (C.W / 2 - 90, -150, -250), (C.W / 2, C.D / 2, 8), os.path.join(OUT, "clear_bottom.png"))
    scene, _ = build_scene(open_lid=False)
    render(scene, (C.W / 2 + 170, -200, 170), (C.W / 2, C.D / 2, 15), os.path.join(OUT, "clear_closed.png"))
