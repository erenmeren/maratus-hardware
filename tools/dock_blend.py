"""Pictures and a .blend of each Dock with the Core on it, from the files tools/dock.py wrote.

  out/tools/cadenv/bin/python tools/dock.py                   # writes mechanical/dock-{bar,float}/*.stl, scene.json
  blender -b -P tools/dock_blend.py [-- draft] [bar|float]    # -> out/dock-{bar,float}-{hero,open,side,rear,inside}.png,
  blender out/maratus-dock-bar.blend                          #    out/maratus-dock-{bar,float}.blend

All STL files are in the Dock's frame (x right, y back, z up, table at z = 0). 1 Blender unit = 50 mm.
Transparent pictures with a soft shadow; `inside` hides the Dock's outer part, so the boards, the saddle and the
port drawer can be seen; `open` hides the Core, so the Dock's front with its pins and magnets can be seen.
The display shows out/dock-screen.png (written by tools/dock.py) when that file exists.
"""
import json
import pathlib
import sys

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
S = 0.02
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DRAFT = "draft" in ARGS
ORANGE = dict(color=(1.0, 0.13, 0.008), rough=0.4)
PALETTE = {       # the Core and the Dock's body are printed in the same material
    "bar": {"body": dict(color=(0.66, 0.66, 0.62), rough=0.48), "accent": ORANGE},
    "float": {"body": dict(color=(0.028, 0.028, 0.031), rough=0.46), "accent": ORANGE},
}
for _core in ("lens", "slim"):      # tools/dock_print.py (2026-11-18): BAR in BAR's colours, TILE in FLOAT's
    PALETTE[f"{_core}-bar"], PALETTE[f"{_core}-tile"] = PALETTE["bar"], PALETTE["float"]
# B MONO (2026-11-21), in the colours of its concept sheet (out/maratus-dock-mono.pdf): SOFT blue, SHARP orange.
PALETTE["lens-mono"] = {"body": dict(color=(0.0, 0.156, 0.479), rough=0.42), "accent": dict(color=(0.93, 0.86, 0.0), rough=0.4)}
PALETTE["slim-mono"] = {"body": dict(color=(0.896, 0.175, 0.014), rough=0.45), "accent": dict(color=(0.011, 0.011, 0.012), rough=0.5)}
COMMON = {"glass": dict(color=(0.004, 0.004, 0.005), rough=0.07), "dark": dict(color=(0.02, 0.05, 0.03), rough=0.6),
          "steel": dict(color=(0.55, 0.55, 0.57), rough=0.3)}
# What a picture leaves out: `inside` the Dock's outer part, `open` the Core (the Dock as it stands when the Core is off).
HIDE = {"inside": {"body", "pod", "cap", "shell"}, "open": {"core-body", "core-panel", "core-lens", "core-magnets", "screen"}}
# Camera offset from the target in mm, lens in mm (None: orthographic side view), key light offset.
SHOTS = {"hero": ((175, -330, 135), 85, (-260, -330, 420)),
         "open": ((175, -330, 135), 85, (-260, -330, 420)),
         "side": ((600, 0, 0), None, (420, -300, 380)),
         "rear": ((-185, 330, 150), 85, (-330, 240, 400)),
         "inside": ((-150, 300, 190), 85, (-330, 240, 400))}


def material(name, color, rough, image=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    mat.diffuse_color = (*color, 1.0)
    if image:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(image))
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.6
    return mat


def build(key):
    src = ROOT / "mechanical" / f"dock-{key}"
    spec = json.loads((src / "scene.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mats = {name: material(name, **kw) for name, kw in {**COMMON, **PALETTE[key]}.items()}
    objs = {}
    for part, mat in spec["parts"].items():
        bpy.ops.wm.stl_import(filepath=str(src / f"{part}.stl"), global_scale=S)
        obj = objs[part] = bpy.context.selected_objects[0]
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_auto_smooth(angle=0.5)     # curved faces without the STL's facets
        obj.data.materials.append(mats[mat])
    mesh = bpy.data.meshes.new("screen")                # what the display shows
    mesh.from_pydata([tuple(c * S for c in p) for p in spec["screen"]], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for loop, co in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop.uv = co
    picture = OUT / "dock-screen.png"
    mesh.materials.append(material("screen", (0, 0, 0), 0.07, image=picture if picture.exists() else None))
    objs["screen"] = bpy.data.objects.new("screen", mesh)
    scene.collection.objects.link(objs["screen"])
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.0005))
    bpy.context.active_object.is_shadow_catcher = True

    world = bpy.data.worlds.new("w")                    # even ambient light, so the only shadows are the two lamps'
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.85, 0.85, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.42
    scene.world = world
    lamps = []
    for name, size, energy in (("key", 7.0, 420.0), ("fill", 9.0, 110.0)):
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        lamp.data.size, lamp.data.energy = size, energy
        scene.collection.objects.link(lamp)
        lamps.append(lamp)
    key_light, fill_light = lamps
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12 if DRAFT else 96
    scene.cycles.use_adaptive_sampling, scene.cycles.adaptive_threshold = True, 0.02
    scene.cycles.use_denoising = True
    scale = 0.4 if DRAFT else 1.0
    scene.render.resolution_x, scene.render.resolution_y = int(1600 * scale), int(1300 * scale)
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"

    target = Vector((0, spec["size"][1] / 2 - 2, spec["size"][2] / 2 - 2)) * S
    aim = lambda obj: setattr(obj, "rotation_euler", (obj.location - target).to_track_quat("Z", "Y").to_euler())
    for shot, (offset, lens, light) in SHOTS.items():
        cam.location = target + Vector(offset) * S
        aim(cam)
        if lens:
            cam.data.type, cam.data.lens = "PERSP", lens
        else:
            cam.data.type, cam.data.ortho_scale = "ORTHO", 150 * S
        key_light.location = target + Vector(light) * S
        fill_light.location = target + Vector((-light[0], light[1] * 0.6, light[2] * 0.5)) * S
        aim(key_light)
        aim(fill_light)
        for part, obj in objs.items():
            obj.hide_render = part in HIDE.get(shot, ())
        scene.render.filepath = str(OUT / f"dock-{key}-{shot}.png")
        bpy.ops.render.render(write_still=True)
    cam.location = target + Vector(SHOTS["hero"][0]) * S    # the saved scene opens on the front view
    aim(cam)
    cam.data.type, cam.data.lens = "PERSP", SHOTS["hero"][1]
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f"maratus-dock-{key}.blend"))


for variant in [a for a in ARGS if a in PALETTE] or ("bar", "float"):
    build(variant)
