#!/usr/bin/env python3
"""Maratus Dock, print prototypes for the Core as it is since 2026-11-15 (pad field horizontal at the bottom, two
magnets level with it, one M4 lock point above it). Two looks the owner asked for on 2026-11-18, each drawn for
both Core bodies (lens and slim): A BAR (the Core leans on a round bar, concept of 2026-11-10) and D TILE (the Core
lies on a wedge of its own outline, like a card terminal, concept of 2026-11-13).

  out/tools/cadenv/bin/python tools/dock_print.py [slim] [bar|tile]  -> mechanical/dock-{lens,slim}-{bar,tile}/

Made to print and to try the look and the fit with a printed Core. Inside each Dock:
- Since 2026-11-19 the spring-pin half of the connector, Promax NF6268-20PA's mate NC6268-20PA
  (docs/reference/promax_NC6268-20PA.pdf p.1): its housing in a pocket, its raised part in a window of the face
  (0.2 mm play), its board's front 6.10 mm (the working height) behind the face, so the Core's flat contacts press
  the pins 1.40 mm; its two guide pins (8.50 mm high) reach 2.40 mm into the Core's part and put the Core in place.
- A 0.2 mm oversize recess for that contact board, 56 x 12 x 1.6 mm, with 2.4 mm behind it for the pins' tails. The
  board is not drawn yet (tools/dock_pcb.py still draws the vertical one) and nothing fixes it in the recess.
- Two pockets, each for a stack of two 10 x 2 mm discs, opposite the Core's two magnets.
- A 5 mm thick boss with a 4.5 mm hole opposite the Core's M4 nut, for an M4 x 8 bolt (3 mm into the Core).
- The port drawer of tools/dock.py (port panel, shelf, base board with RJ45 and USB-C), unchanged.
Not a tooling design; not printed, not tried. The magnets' pull is calculated, not measured.
"""
import json
import math
import pathlib
import sys

from build123d import (Box, Circle, Compound, Cone, Cylinder, Pos, RectangleRounded, Rot, export_step, export_stl,
                       extrude, import_step)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dock  # noqa: E402  (imports enclosure, which reads `slim` from sys.argv)
import enclosure as core  # noqa: E402
import mech as m  # noqa: E402
from dock import BIG, Drawer, above, block, box, magnets  # noqa: E402

BODY = "lens" if core.LENS else "slim"
ROOT = pathlib.Path(__file__).resolve().parent.parent / "mechanical"
CORE_W, CORE_H = core.OX1 - core.OX0, core.OY1 - core.OY0
CORE_D = core.Z_TOP - core.Z_REAR                    # rear face to the front face (lens or glass)
CV = core.OY1 - m.REAR_PADS[1]                       # v of the pad field's centre (its u is 0)
V_LOCK = core.OY1 - m.DOCK_LOCK[0][1]                # v of the Core's M4 nut
MAG_UV = [(x - m.PCB_W / 2, core.OY1 - y) for x, y in m.DOCK_MAGNETS]
BOARD = (56.0, 12.0, 1.6)                            # contact board, not drawn: width, height, thickness
BOARD_W = -6.1                                       # its front face behind the Core's rear face: NC6268's working height
NC_BASE, NC_TOP = 2.5, 4.5                           # NC6268-20PA: housing base and raised part, height over its board
SLAB, BOLT = 5.0, 4.5                                # the lock boss's thickness, the bolt's clearance hole


class Frame:
    """Core-local (u right, v up from the bottom edge, w from the rear face to the front) -> Dock (x right, y back,
    z up, table at z = 0); the Core leans back `lean` degrees from upright, its bottom rear edge at (y0, z0)."""

    def __init__(self, lean, y0, z0):
        self.lean, self.y0, self.z0 = lean, y0, z0
        self.sin, self.cos = math.sin(math.radians(lean)), math.cos(math.radians(lean))

    def place(self, part):
        return Pos(0, self.y0, self.z0) * Rot(90 - self.lean, 0, 0) * part

    def pt(self, v, w):
        return self.y0 + v * self.sin - w * self.cos, self.z0 + v * self.cos + w * self.sin

    def behind(self, w=0.0):
        return self.place(Pos(0, 0, w - BIG / 2) * Box(BIG, BIG, BIG))

    def core(self):
        to_local = Pos(-m.PCB_W / 2, core.OY1, -core.Z_REAR)
        parts = core.dummies()
        out = {"core-body": core.body(), "core-panel": parts["panel-dummy"], "core-magnets": core.magnets()}
        if "lens-dummy" in parts:
            out["core-lens"] = parts["lens-dummy"]
        return {k: self.place(to_local * p) for k, p in out.items()}

    def screen(self):
        ax, ay, aw, ah = m.PANEL_AA
        u0, v1 = m.PANEL_X0 + ax - m.PCB_W / 2, core.OY1 - (core.PY0 + ay)
        return [(u, *self.pt(v, CORE_D + 0.03)) for u, v in ((u0, v1 - ah), (u0 + aw, v1 - ah), (u0 + aw, v1), (u0, v1))]


def front(f, hull):
    """What every Dock has where it meets the Core: (solid to add inside `hull`, cutter)."""
    add = magnets(f, MAG_UV)[0] & hull
    add += f.place(box(-SLAB - 0.5, V_LOCK - SLAB - 0.5, -SLAB, SLAB + 0.5, V_LOCK + SLAB + 0.5, 0)) & hull
    bw, bh, bt = BOARD
    cut = f.place(box(-bw / 2 - 0.2, CV - bh / 2 - 0.2, BOARD_W - bt - 2.4, bw / 2 + 0.2, CV + bh / 2 + 0.2, BOARD_W))
    (bl, bwd, _), (rl, rw, _) = m.CONTACT_BASE, m.CONTACT_BOSS      # NC6268's housing has NF6268's outline
    cut += f.place(Pos(0, CV, BOARD_W - 0.01) * extrude(RectangleRounded(bl + 0.4, bwd + 0.4, bwd / 2 + 0.19),
                                                       amount=NC_BASE + 0.11))
    cut += f.place(box(-rl / 2 - 0.2, CV - rw / 2 - 0.2, BOARD_W, rl / 2 + 0.2, CV + rw / 2 + 0.2, 0.5))
    cut += magnets(f, MAG_UV)[1]
    cut += f.place(Pos(0, V_LOCK, -SLAB - 1) * extrude(Circle(BOLT / 2), amount=SLAB + 2))
    return add, cut


def nc_part(f):
    """NC6268-20PA's housing and its board, without pins, for the overlap check."""
    (bl, bwd, _), (rl, rw, _) = m.CONTACT_BASE, m.CONTACT_BOSS
    bw, bh, bt = BOARD
    part = f.place(Pos(0, CV, BOARD_W) * extrude(RectangleRounded(bl, bwd, bwd / 2 - 0.01), amount=NC_BASE))
    part += f.place(box(-rl / 2, CV - rw / 2, BOARD_W + NC_BASE, rl / 2, CV + rw / 2, BOARD_W + NC_TOP))
    return part + f.place(box(-bw / 2, CV - bh / 2, BOARD_W - bt, bw / 2, CV + bh / 2, BOARD_W))


def base_board(d):
    """The base board from KiCad (unchanged since 2026-11-10) with boxes for the RJ45 jack and the harness plug."""
    src = ROOT / "dock" / "maratus-dock-base-pcb.step"
    solids = [Pos(*d.xy(0, 0), d.top - dock.BASE["t"]) * Rot(0, 0, 180) * import_step(str(src))]
    for (x0, y0, x1, y1), h in ((dock.BASE["jack"][:4], dock.BASE["jack"][4]), (dock.BASE["j3"], dock.PLUG_THT)):
        (ax, ay), (bx, by) = d.xy(x0, y0), d.xy(x1, y1)
        solids.append(block(bx, ay, d.top, ax, by, d.top + h))
    return Compound(children=solids)


def bar():
    """A: a round bar as long as the Core is wide lies on the table; the Core leans 15 degrees back onto a flat on
    its front. Since the pads, the magnets and the lock lie in the Core's lowest 25 mm, the bar touches the Core
    around 14 mm up its rear face, which lifts the Core's bottom edge off the table. A foot under the middle of
    the bar carries the front; orange caps close the bar's ends; the port panel is a flat on its back.
    shortcut: the lock bolt cannot be reached with the bar closed; add an access path if the lock is wanted."""
    # r and s are larger than in dock.py (19, 13): the magnets now sit low, and their pockets need room in front of
    # the base board. 22 and 17 since 2026-11-19 (were 20, 15): the NC6268-20PA's board lies 6.1 mm deep
    r, wall, cut, s, cap, skin, floor, foot, va = 22.0, 2.0, 1.5, 17.0, 2.2, 1.6, 2.0, 18.0, 14.0
    zc = r - cut
    lean = 15.0
    sn, cs = math.sin(math.radians(lean)), math.cos(math.radians(lean))
    z0 = zc - va * cs + s * sn                          # the axis is s behind the rear face, level with v = va
    f = Frame(lean, CORE_D * cs + (z0 + CORE_D * sn) * sn / cs, z0)   # the glass's plane meets the table at y = 0
    yc = f.pt(va, -s)[0]
    flat = math.sqrt(r * r - s * s)
    for (_, v), what in ((MAG_UV[0], "a magnet"), ((0, V_LOCK), "the lock boss"), ((0, CV - m.CONTACT_BASE[1] / 2 - 0.2), "the window")):
        assert abs(v - va) + 6.3 < flat or what == "the window" and va - v + 1.0 < flat, f"{what} is off the bar's flat"
    end = CORE_W / 2 - cap
    tube = lambda rad, x0, x1: Pos((x0 + x1) / 2, yc, zc) * Rot(0, 90, 0) * Cylinder(rad, x1 - x0)
    solid = f.behind() & above(0)
    d = Drawer(yc + math.sqrt(r ** 2 - (dock.PANEL[1] / 2) ** 2), zc - dock.PANEL[1] / 2)
    hull = (tube(r, -end, end) + block(-foot, yc - 60, 0, foot, yc, zc)) & solid
    body = hull - (tube(r - wall, -end, end) & above(floor) & f.behind(-skin))
    add, cutter = front(f, hull)
    body += add
    for sgn in (-1, 1):                 # walls at the ends of the panel
        x0, x1 = sorted((sgn * (dock.PANEL[0] / 2 - 1.0), sgn * (dock.PANEL[0] / 2 + 2.0)))
        body += tube(r - wall + 0.1, x0, x1) & block(-BIG, yc + 12, -BIG, BIG, yc + BIG, BIG)
    sx, sy = d.xy(*dock.DRAWER_SCREWS[0])
    body += Pos(sx, sy, 0) * extrude(Circle(3.5), amount=d.zb - 0.1)               # the drawer's shelf lands on this
    body -= cutter
    body -= d.opening(12.0)
    body -= d.screw(0, d.zb)
    body -= block(-35, yc - 6, -1, 35, yc + 2.5, 0.3)                              # 0.3 mm recess for mounting tape
    for sgn in (-1, 1):                 # shadow groove where a cap meets the bar
        x0, x1 = sorted((sgn * (end - 0.4), sgn * end))
        body -= tube(r + 1, x0, x1) - tube(r - 0.9, x0, x1)

    def end_cap(sgn):
        x0, x1 = sorted((sgn * end, sgn * (end + cap)))
        part = tube(r, x0, x1) & solid
        s0, s1 = sorted((sgn * (end - 2.0), sgn * end))                 # spigot: a ring that fits the bar's bore
        ring = lambda g: tube(r - wall - g, s0, s1) & above(floor + g) & f.behind(-skin - g)
        part += ring(0.15) - ring(1.75)
        return part

    printed = {"body": (body, "body"), "cap-left": (end_cap(-1), "accent"), "cap-right": (end_cap(1), "accent")}
    note = (f"bar {2 * r:.0f} mm across, axis {zc:.1f} mm above the table; it touches the Core from {va - flat:.1f} to "
            f"{va + flat:.1f} mm up its rear face; the Core's bottom edge is {z0:.1f} mm above the table")
    return f, d, printed, note


def tile():
    """D: the Core lies on a wedge of its own outline, its glass 25 degrees from the table, its bottom edge in front.
    The wedge is a 2.2 mm shell on an orange 3 mm base plate (four countersunk M2 screws from below); its rear wall
    is upright and carries the port panel. The lock bolt goes in from inside, with the base plate off."""
    # thick 13 since 2026-11-19 (was 6): the NC6268-20PA, its board and the pins' tails reach 10.1 mm behind the face
    tilt, thick, plate_t, wall, rear = 25.0, 13.0, 3.0, 2.2, 5.0
    f = Frame(90 - tilt, CORE_D * math.sin(math.radians(tilt)), thick * math.cos(math.radians(tilt)))
    y_rear = f.pt(CORE_H, 0)[0]
    outline = lambda grow, w0, w1: f.place(Pos(0, CORE_H / 2, w0) * extrude(
        RectangleRounded(CORE_W + 2 * grow, CORE_H + 2 * grow, core.R_OUT + grow), amount=w1 - w0))
    upto = lambda y: block(-BIG, y - BIG, -BIG, BIG, y, BIG)
    solid = outline(0, -120, 0) & upto(y_rear) & above(0)
    plate, hull = solid & block(-BIG, -BIG, 0, BIG, BIG, plate_t), solid & above(plate_t)
    cav = outline(-wall, -120, -wall) & upto(y_rear - rear) & above(plate_t - 1)
    shell = hull - cav
    add, cutter = front(f, hull)
    shell += add
    d = Drawer(y_rear - 1.0, plate_t)                    # the panel 1 mm inside the rear face
    pillars = [(sgn * (CORE_W / 2 - wall - 2.0), y, 4.0, 6.0) for sgn in (-1, 1) for y in (12.0, y_rear - rear - 8.0)]
    for x, y, px, py in pillars:
        shell += block(x - px / 2, y - py / 2, plate_t, x + px / 2, y + py / 2, plate_t + 8) & hull
        shell -= Pos(x, y, plate_t) * extrude(Circle(0.85), amount=7)
        plate -= Pos(x, y, 0) * extrude(Circle(1.15), amount=plate_t) + Pos(x, y, 0.6) * Cone(1.95, 0.75, 1.2)
    shell -= cutter
    shell -= d.opening(rear + 1, 0.2)
    for i in range(len(dock.DRAWER_SCREWS)):
        plate -= d.screw(i, plate_t)
    printed = {"shell": (shell, "body"), "plate": (plate, "accent")}
    note = (f"wedge {CORE_W:.1f} wide, {y_rear:.1f} deep, rear wall {f.pt(CORE_H, 0)[1]:.1f} mm high; glass "
            f"{tilt:.0f} degrees from the table; base plate {plate_t:.0f} mm")
    return f, d, printed, note


VARIANTS = {"bar": bar, "tile": tile}


def overlap(a, b):
    return sum(h.volume for h in (s & t for s in a.solids() for t in b.solids()) if h)


def build(name):
    out = ROOT / f"dock-{BODY}-{name}"
    out.mkdir(parents=True, exist_ok=True)
    f, d, printed, note = VARIANTS[name]()
    parts = {**{k: p for k, (p, _) in printed.items()}, "drawer": d.part(), **f.core(),
             "dock-magnets": magnets(f, MAG_UV)[2], "base-board": base_board(d),
             "dock-contact": nc_part(f)}
    for key in [*printed, "drawer"]:
        part = parts[key]
        assert part.is_valid and len(part.solids()) == 1, f"{key}: {len(part.solids())} solids"
        bb = part.bounding_box()
        print(f"{BODY} {name} {key}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, {part.volume / 1000:.1f} cm3")
        export_step(part, str(out / f"maratus-dock-{BODY}-{name}-{key}.step"))
    for key, part in parts.items():
        export_stl(part, str(out / f"{key}.stl"), tolerance=0.03, angular_tolerance=0.2)
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if {a, b} <= {"core-body", "core-panel", "core-lens", "core-magnets"}:
                continue
            v = overlap(parts[a], parts[b])
            assert v < 0.05, f"{BODY} {name}: {a} collides with {b} ({v:.2f} mm3)"
    print(f"  no overlap between any two of: {', '.join(names)}")
    allbb = Compound(children=list(parts.values())).bounding_box()
    print(f"  docked: {allbb.size.X:.1f} wide, {allbb.size.Y:.1f} deep, {allbb.max.Z:.1f} mm high; {note}")
    export_step(Compound(children=list(parts.values())), str(out / f"maratus-dock-{BODY}-{name}-assembly.step"))
    mats = {**{k: mat for k, (_, mat) in printed.items()}, "drawer": "body", "core-body": "body", "core-panel": "glass",
            "core-magnets": "steel", "dock-magnets": "steel", "base-board": "dark", "dock-contact": "dark"}
    if "core-lens" in parts:
        mats["core-lens"] = "glass"
    scene = {"parts": mats, "screen": f.screen(),
             "size": [round(allbb.size.X, 1), round(allbb.max.Y, 1), round(allbb.max.Z, 1)]}
    (out / "scene.json").write_text(json.dumps(scene, indent=1))


if __name__ == "__main__":
    for variant in [a for a in sys.argv[1:] if a in VARIANTS] or VARIANTS:
        build(variant)
