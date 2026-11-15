"""Renders the enclosure STLs: blender -b -P tools/render_enclosure.py  ->  out/enclosure-*.png

Reads mechanical/core/*.stl (written by tools/enclosure.py). Three pictures: closed from the front, open with the
panel lifted 30 mm, and the rear. The front of the device faces +Z.
"""
import pathlib

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "mechanical" / "core", ROOT / "out"
PARTS = {"maratus-core-body": (0.08, 0.08, 0.09), "panel-dummy": (0.01, 0.01, 0.012), "pcb-dummy": (0.02, 0.25, 0.08),
         "lens-dummy": (0.012, 0.012, 0.014)}       # the lens body's cover lens; the slim body has none
PARTS = {name: colour for name, colour in PARTS.items() if (SRC / f"{name}.stl").exists()}
CENTRE = Vector((37.0, -31.5, 2.0))

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = {}
for name, colour in PARTS.items():
    bpy.ops.wm.stl_import(filepath=str(SRC / f"{name}.stl"))
    obj = objs[name] = bpy.context.selected_objects[0]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.3 if name == "panel-dummy" else 0.12 if name == "lens-dummy" else 0.55
    obj.data.materials.append(mat)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1400, 1050
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
scene.world = world
for loc, energy in (((250, 150, 300), 2.5), ((-200, -250, -300), 2.5)):
    light = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    light.data.energy = energy
    light.location = loc
    light.rotation_euler = Vector(loc).to_track_quat("Z", "Y").to_euler()
    scene.collection.objects.link(light)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens, cam.data.clip_end = 60, 5000
scene.collection.objects.link(cam)
scene.camera = cam


def shot(name, offset):
    cam.location = CENTRE + Vector(offset)
    cam.rotation_euler = (cam.location - CENTRE).to_track_quat("Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"enclosure-{name}.png")
    bpy.ops.render.render(write_still=True)


shot("front", (90, -110, 250))
shot("rear", (-110, -120, -250))
objs["panel-dummy"].location.z = 30
if "lens-dummy" in objs:
    objs["lens-dummy"].location.z = 55
shot("open", (110, -170, 230))
