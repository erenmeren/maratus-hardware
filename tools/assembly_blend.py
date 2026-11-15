"""Builds out/maratus-core-assembly.blend: body, the board with its parts, the panel lifted 30 mm.

  python3 tools/pcb.py fab                      # writes out/pcb/board.glb and out/pcb/placeholders.json
  blender -b -P tools/assembly_blend.py
  blender out/maratus-core-assembly.blend

1 Blender unit = 50 mm, so the model fills the default view. The front of the device faces +Z.
Parts without a 3D model on this machine are plain grey boxes of their body size (NO_MODEL in tools/pcb.py).
"""
import json
import math
import pathlib

import bpy

ROOT = pathlib.Path(__file__).resolve().parent.parent
S = 0.02                    # Blender units per mm
OX, OY = -37.0, 31.5        # moves the middle of the body to the origin (mm, CAD frame of tools/enclosure.py)
PCB_T = 1.2


def material(name, colour, rough=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    mat.diffuse_color = (*colour, 1.0)
    return mat


bpy.ops.wm.read_factory_settings(use_empty=True)
for name, colour, lift in (("maratus-core-body", (0.10, 0.10, 0.11), 0.0), ("panel-dummy", (0.01, 0.01, 0.012), 30.0)):
    bpy.ops.wm.stl_import(filepath=str(ROOT / "mechanical" / "core" / f"{name}.stl"), global_scale=S)
    obj = bpy.context.selected_objects[0]
    obj.location = (OX * S, OY * S, lift * S)
    obj.data.materials.append(material(name, colour, 0.3 if "panel" in name else 0.55))

# The board from KiCad: metres, y flipped, z = 0 on the board's back face.
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "out" / "pcb" / "board.glb"))
board = bpy.data.objects.new("board", None)
bpy.context.scene.collection.objects.link(board)
for obj in set(bpy.data.objects) - before:
    if obj.parent is None and obj is not board:
        obj.parent = board
board.scale = (1000 * S,) * 3
board.location = (OX * S, OY * S, -PCB_T * S)

grey = material("no-3d-model", (0.25, 0.25, 0.27))
for ref, (x, y, rot, w, h, z) in json.loads((ROOT / "out" / "pcb" / "placeholders.json").read_text()).items():
    bpy.ops.mesh.primitive_cube_add(size=1)
    box = bpy.context.active_object
    box.name = f"{ref} (box)"
    box.scale = (w * S, h * S, z * S)
    box.location = ((x + OX) * S, (-y + OY) * S, z / 2 * S)
    box.rotation_euler.z = math.radians(rot)
    box.data.materials.append(grey)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "out" / "maratus-core-assembly.blend"))
