"""Renders the enclosure STLs: blender -b -P tools/render_enclosure.py  ->  out/enclosure-*.png

Reads mechanical/core/*.stl (written by tools/enclosure.py). Two pictures: closed from the front, and opened
from the rear with the cover lifted 30 mm.
"""
import math
import pathlib

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "mechanical" / "core", ROOT / "out"
PARTS = {"maratus-core-front-shell": (0.08, 0.08, 0.09), "maratus-core-rear-cover": (0.10, 0.10, 0.11),
         "panel-dummy": (0.01, 0.01, 0.012), "pcb-dummy": (0.02, 0.25, 0.08)}
CENTRE = Vector((38.0, -48.0, 0.0))

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = {}
for name, colour in PARTS.items():
    bpy.ops.wm.stl_import(filepath=str(SRC / f"{name}.stl"))
    obj = objs[name] = bpy.context.selected_objects[0]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
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
    light.rotation_euler = (Vector(loc)).to_track_quat("Z", "Y").to_euler()
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


shot("front", (110, -90, -260))             # the front of the device faces -Z
objs["maratus-core-rear-cover"].location.z = 30
shot("rear-open", (-150, -130, 270))
