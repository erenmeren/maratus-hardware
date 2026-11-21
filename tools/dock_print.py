#!/usr/bin/env python3
"""Maratus Dock, print prototypes for the Core as it is since 2026-11-15 (pad field horizontal at the bottom, two
magnets level with it, one M4 lock point above it). Two looks the owner asked for on 2026-11-18, each drawn for
both Core bodies (lens and slim): A BAR (the Core leans on a round bar, concept of 2026-11-10) and D TILE (the Core
lies on a wedge of its own outline, like a card terminal, concept of 2026-11-13).

  out/tools/cadenv/bin/python tools/dock_print.py [slim] [bar|tile|mono]  -> mechanical/dock-{lens,slim}-{bar,tile,mono}/

Since 2026-11-21 also B MONO (`mono`), drawn for each body: SOFT for the lens body, SHARP for the slim body.

Made to print and to try the look and the fit with a printed Core. Inside each Dock:
- Since 2026-11-19 the spring-pin half of the connector, Promax NF6268-20PA's mate NC6268-20PA
  (docs/reference/promax_NC6268-20PA.pdf p.1): its housing in a pocket, its raised part in a window of the face
  (0.2 mm play), its board's front 6.10 mm (the working height) behind the face, so the Core's flat contacts press
  the pins 1.40 mm; its two guide pins (8.50 mm high) reach 2.40 mm into the Core's part and put the Core in place.
- A 0.2 mm oversize recess for that contact board, 56 x 12 x 1.6 mm, with 2.4 mm behind it for the pins' tails. The
  board is not drawn yet (tools/dock_pcb.py still draws the vertical one) and nothing fixes it in the recess.
- Two pockets, each for a stack of two 10 x 2 mm discs, opposite the Core's two magnets. Since 2026-11-21 (owner:
  the magnets stay inside, as in the Core) they are closed at the front by 0.5 mm of plastic and open to the inside.
- A 5 mm thick boss with a 4.5 mm hole opposite the Core's M4 nut, for an M4 x 8 bolt (3 mm into the Core).
- The port drawer of tools/dock.py (port panel, shelf, base board with RJ45 and USB-C), unchanged.
Not a tooling design; not printed, not tried. The magnets' pull is calculated, not measured.
"""
import json
import math
import pathlib
import sys

from build123d import (Box, Circle, Compound, Cone, Cylinder, Line, Plane, Pos, RectangleRounded, Rot, ThreePointArc,
                       export_step, export_stl, extrude, fillet, import_step, make_face)

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
MAG_SKIN = core.MAGNET_SKIN                         # plastic in front of the Dock's magnets, as in the Core
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
    add = magnets(f, MAG_UV, MAG_SKIN)[0] & hull
    add += f.place(box(-SLAB - 0.5, V_LOCK - SLAB - 0.5, -SLAB, SLAB + 0.5, V_LOCK + SLAB + 0.5, 0)) & hull
    bw, bh, bt = BOARD
    cut = f.place(box(-bw / 2 - 0.2, CV - bh / 2 - 0.2, BOARD_W - bt - 2.4, bw / 2 + 0.2, CV + bh / 2 + 0.2, BOARD_W))
    (bl, bwd, _), (rl, rw, _) = m.CONTACT_BASE, m.CONTACT_BOSS      # NC6268's housing has NF6268's outline
    cut += f.place(Pos(0, CV, BOARD_W - 0.01) * extrude(RectangleRounded(bl + 0.4, bwd + 0.4, bwd / 2 + 0.19),
                                                       amount=NC_BASE + 0.11))
    cut += f.place(box(-rl / 2 - 0.2, CV - rw / 2 - 0.2, BOARD_W, rl / 2 + 0.2, CV + rw / 2 + 0.2, 0.5))
    cut += magnets(f, MAG_UV, MAG_SKIN)[1]
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
    """A: a round bar as long as the Core is wide lies on the table; the Core leans 20 degrees back onto a flat on
    its front. Since the pads, the magnets and the lock lie in the Core's lowest 25 mm, the bar touches the Core
    around 14 mm up its rear face, which lifts the Core's bottom edge off the table. A foot under the middle of
    the bar carries the front; orange caps close the bar's ends; the port panel is a flat on its back.
    shortcut: the lock bolt cannot be reached with the bar closed; add an access path if the lock is wanted."""
    # r and s are larger than in dock.py (19, 13): the magnets now sit low, and their pockets need room in front of
    # the base board. 22 and 17 since 2026-11-19 (were 20, 15): the NC6268-20PA's board lies 6.1 mm deep
    r, wall, cut, s, cap, skin, floor, foot, va = 22.0, 2.0, 1.5, 17.0, 2.2, 1.6, 2.0, 18.0, 14.0
    zc = r - cut
    lean = 20.0                                         # 15 until 2026-11-21: too upright on the print (owner)
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


def section(outline):
    """A closed (y, z) outline as a face on the YZ plane (points, or (mid, end) pairs for arcs), as dock.profile."""
    edges, prev = [], outline[0]
    for item in [*outline[1:], outline[0]]:
        if isinstance(item[0], tuple):
            edges.append(ThreePointArc(prev, *item))
            prev = item[1]
        else:
            edges.append(Line(prev, item))
            prev = item
    return Plane.YZ * make_face(edges)


def across(face, x0, x1):
    return Pos(x0, 0, 0) * extrude(face, amount=x1 - x0, dir=(1, 0, 0))


def try_fillet(edges, radii, part):
    """The largest of `radii` that works on `edges`, or `part` unchanged."""
    for radius in radii:
        try:
            return fillet(edges, radius), radius
        except ValueError:
            continue
    return part, 0.0


def circle3(a, b, c):
    """Centre and radius of the circle through three (y, z) points."""
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def mono():
    """B, drawn once for each body (owner, 2026-11-21: one with rounded edges, one without). Core and foot are one
    block of one colour: the Core sits in a pocket of the foot on a thin chin, leaning 20 degrees back, its rear face
    on the foot's front wall, which carries the contact part, the magnets and the lock boss as on the other Docks.
    Lens body, SOFT: seen from the front Core and chin make one rounded square; one convex curve behind; the curve's
    side edges rounded 8 mm. Slim body, SHARP: one flat 45 degree slope to an upright rear wall; edges 0.6 mm.
    A 2.2 mm shell (1.6 mm behind the Core) over an inset 3 mm base plate with four countersunk M2 screws; the port
    drawer flush in the rear wall, two M2 screws from below; the lock bolt goes in from inside with the plate off.
    The corner cups beside the lens Core's lowest corners stop 7 mm up, where they are still 1.2 mm thick."""
    lean, z0, depth, gap, wall, skin, plate_t = 20.0, 3.0, 58.0, 0.3, 2.2, 1.6, 3.0
    sn, cs = math.sin(math.radians(lean)), math.cos(math.radians(lean))
    f = Frame(lean, CORE_D * cs + (z0 + CORE_D * sn) * sn / cs, z0)   # the front's plane meets the table at y = 0
    half = CORE_W / 2
    v_front = (0 - z0 - CORE_D * sn) / cs
    on_face = lambda z: f.pt((z - z0 + skin * sn) / cs, -skin)          # the shell's inner face behind the Core
    if core.LENS:
        r_cup, h_rear = 7.0, 30.0
        p_top, e_top = f.pt(46.0, 0), (depth, h_rear)
        dy, dz = e_top[0] - p_top[0], p_top[1] - e_top[1]
        mid = ((p_top[0] + e_top[0]) / 2 + 0.17 * dz, (p_top[1] + e_top[1]) / 2 + 0.17 * dy)
        back = [p_top, (mid, e_top)]
        (yc, zc), rho = circle3(p_top, mid, e_top)
        ri = rho - wall                                                  # the shell's inner curve
        k0, k1 = f.pt(0, -skin), (sn, cs)                                # inner face: point and direction
        b = 2 * ((k0[0] - yc) * k1[0] + (k0[1] - zc) * k1[1])
        c = (k0[0] - yc) ** 2 + (k0[1] - zc) ** 2 - ri * ri
        t = (-b + math.sqrt(b * b - 4 * c)) / 2
        c2 = (k0[0] + t * k1[0], k0[1] + t * k1[1])
        c3 = (depth - wall, zc + math.sqrt(ri * ri - (depth - wall - yc) ** 2))
        a2, a3 = math.atan2(c2[1] - zc, c2[0] - yc), math.atan2(c3[1] - zc, c3[0] - yc)
        am = (a2 + a3) / 2
        inner = [on_face(-1.0), c2, ((yc + ri * math.cos(am), zc + ri * math.sin(am)), c3), (depth - wall, -1.0)]
    else:
        r_cup, h_rear, tip = 0.0, 24.0, 1.2
        t = ((depth - f.y0) * cs - (h_rear - z0) * sn - tip) / (cs + sn)
        top = (depth - t, h_rear + t)                                   # the 45 degree slope meets the Core
        back = [f.pt((top[0] - f.y0) * sn + (top[1] - z0) * cs, 0), top, (depth, h_rear)]
        k = depth + h_rear - wall * math.sqrt(2)                       # the slope's inner face: y + z = k
        y_face0, z_face0 = f.pt(0, -skin)
        v2 = (k - y_face0 - z_face0) / (sn + cs)
        inner = [on_face(-1.0), f.pt(v2, -skin), (depth - wall, k - depth + wall), (depth - wall, -1.0)]
    outer = [f.pt(v_front, CORE_D), f.pt(r_cup, CORE_D), f.pt(r_cup, 0), *back, (depth, 0.0)]
    hull = across(section(outer), -half, half)
    hull &= f.place(Pos(0, v_front + 60, -80) * extrude(RectangleRounded(CORE_W, 120, core.R_OUT), amount=80 + CORE_D + 1))
    pocket = f.place(Pos(0, CORE_H / 2, 0) * extrude(RectangleRounded(CORE_W + 2 * gap, CORE_H + 2 * gap,
                                                                     core.R_OUT + gap), amount=CORE_D + 10))
    cav = across(section(inner), -half + wall, half - wall)
    r_side = 0.0
    if core.LENS:
        rear = [g for g in hull.edges() if abs(g.center().Y - depth) < 0.05 and abs(g.center().Z - h_rear) < 0.5]
        hull = try_fillet(rear, (4.0, 3.0), hull)[0]                   # first: the side edges then run smoothly
        side = [g for g in hull.edges() if abs(abs(g.center().X) - half) < 0.05 and g.center().Y > back[0][0] - 1.0
                and g.center().Z > 0.5]
        hull, r_side = try_fillet(side, (8.0, 6.0, 4.0), hull)
        crest = [g for g in cav.edges() if abs(g.center().Y - (depth - wall)) < 0.05 and abs(g.center().Z - c3[1]) < 0.5]
        cav = try_fillet(crest, (2.0, 1.5, 1.0), cav)[0]              # the inside follows the outside: same order
        inside = [g for g in cav.edges() if abs(abs(g.center().X) - (half - wall)) < 0.05 and g.center().Y > c2[0] - 1.0
                  and g.center().Z > 0.5]
        cav, r_in = try_fillet(inside, (max(r_side - wall, 1.0), 5.0, 4.5), cav)  # concentric: the wall stays 2.2 mm
        assert r_side <= wall or r_in, "the shell's inner corners would break through the rounded outer edges"
    else:
        outside = [g for g in hull.edges() if g.center().Z > 0.05]
        hull = try_fillet(outside, (0.6, 0.4), hull)[0]
    hull -= pocket                                                     # after the fillets: they work on the plain shape
    body = hull - cav
    pillars = [(sgn * (half - wall - 2.0), y) for sgn in (-1, 1) for y in (on_face(plate_t + 8)[0] + 4.0, depth - wall - 4.0)]
    for x, y in pillars:
        body += block(x - 2.0, y - 3.0, plate_t, x + 2.0, y + 3.0, plate_t + 8) & hull
        body -= Pos(x, y, plate_t) * extrude(Circle(0.85), amount=7)
    add, cutter = front(f, hull)
    body += add
    body -= cutter
    d = Drawer(depth, plate_t)                                          # the panel flush with the rear face
    body -= d.opening(wall + 1.5, 0.2)
    y0p = on_face(plate_t)[0] + 0.2
    pw_, pl_ = CORE_W - 2 * wall - 0.4, depth - wall - 0.2 - y0p
    r_plate = max(r_side - wall - 0.2, 0.5) if core.LENS else 0.5      # the cavity's rear corners are round on SOFT
    plate = Pos(0, y0p + pl_ / 2, 0) * extrude(RectangleRounded(pw_, pl_, r_plate), amount=plate_t) - cutter
    for x, y in pillars:
        plate -= Pos(x, y, 0) * extrude(Circle(1.15), amount=plate_t) + Pos(x, y, 0.6) * Cone(1.95, 0.75, 1.2)
    for i in range(len(dock.DRAWER_SCREWS)):
        plate -= d.screw(i, plate_t)
    printed = {"foot": (body, "body"), "plate": (plate, "body")}
    note = (f"{'SOFT' if core.LENS else 'SHARP'}: foot {CORE_W:.1f} wide, {depth:.0f} deep, rear wall {h_rear:.0f} mm "
            f"high{f', side edges rounded {r_side:.0f} mm' if r_side else ''}; the Core leans {lean:.0f} degrees, its "
            f"rear edge {z0:.0f} mm over the table")
    return f, d, printed, note


VARIANTS = {"bar": bar, "tile": tile, "mono": mono}


def overlap(a, b):
    return sum(h.volume for h in (s & t for s in a.solids() for t in b.solids()) if h)


def build(name):
    out = ROOT / f"dock-{BODY}-{name}"
    out.mkdir(parents=True, exist_ok=True)
    f, d, printed, note = VARIANTS[name]()
    parts = {**{k: p for k, (p, _) in printed.items()}, "drawer": d.part(), **f.core(),
             "dock-magnets": magnets(f, MAG_UV, MAG_SKIN)[2], "base-board": base_board(d),
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
