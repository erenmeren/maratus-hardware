#!/usr/bin/env python3
"""Maratus Dock, mechanical design (3D-print geometry) in the two shapes the owner chose on 2026-11-10 from three
look concepts: BAR (the Core leans on one round bar) and FLOAT (the Core hovers over a thin plate, a pod behind
carries it). The Core leans back 15 degrees in both, and both take the same inner parts.

  out/tools/cadenv/bin/python tools/dock.py [bar|float]    -> mechanical/dock-bar, mechanical/dock-float, mechanical/dock

Dock frame: x right (seen from the customer's side), y towards the back, z up, table at z = 0.
Core-local frame: u right, v up along the device from its bottom edge, w from its rear face (0) towards the glass.

Inner parts, the same in both Docks (boards from tools/dock_pcb.py):
- Contact board: its back lies on the floor of a recess in the Dock's front face. A printed saddle holds it from the
  front (two countersunk M2 x 8 screws) and carries the block that reaches into the Core's pad window. The harness
  header on the board's back goes through a window in the recess floor.
- Port drawer: the port panel with a shelf; the base board (RJ45, USB-C) is screwed onto the shelf. The drawer goes
  in from the Dock's rear and is held by screws from below.
- Magnets (owner, 2026-11-12): two stacks of two 10 x 2 mm discs in the Dock's front, opposite one disc each in the
  Core's floor (tools/mech.py: BAR uses the Core's outer pair, FLOAT the inner). They hold the Core on the Dock;
  the saddle's block in the Core's pad window puts it in place.
- Lock, optional: two M2 x 8 screws from inside the Dock into two bosses in the Core's floor, reached with a long
  screwdriver (service-only release): in BAR through two holes in its rear, in FLOAT over the port panel once the
  pod's cap is lifted off. BAR uses the Core's outer boss pair, FLOAT the inner.
Spring pin: Harwin P70-2300045R, docs/reference/harwin_P70-2300045R.pdf: body 1.5 mm, 4.9 mm normal working height,
0.83 N each. The 12 fitted pins push the Core off with about 10 N; the magnets' pull is calculated at about 27 N
and not measured (docs/design-spec.md section 13).
RJ45: Wurth 7499010121A, docs/reference/wurth_7499010121A.pdf p.1. Harness plugs: docs/reference/jst_ePH.pdf.
Not a tooling design: no draft angles, lock and screw strength not analysed, nothing printed or tested. Neither
Dock stands a firm press on the screen without being fixed to the counter (docs/design-spec.md section 13).
"""
import json
import math
import pathlib
import sys

from build123d import (Box, Circle, Compound, Cone, Cylinder, Line, Plane, Pos, Rectangle, RectangleRounded, Rot,
                       ThreePointArc, export_step, export_stl, extrude, fillet, import_step, make_face)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import enclosure as core  # noqa: E402
import mech as m  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent / "mechanical"
COMMON = ROOT / "dock"                       # board models and the printed parts both Docks share
LEAN = 15.0                                  # degrees from vertical
SIN, COS = math.sin(math.radians(LEAN)), math.cos(math.radians(LEAN))
CORE_W, CORE_H, CORE_D = core.OX1 - core.OX0, core.OY1 - core.OY0, core.Z_GLASS - core.Z_REAR
BIG = 400.0
PIN_WORK, PIN_BODY = 4.9, 1.5                # spring pin: working height above its board, body diameter
PAD_DEPTH = core.Z_PCB_BACK - core.Z_REAR    # the Core's pads lie this far inside its rear face (3.6)
BOARD_W = -(PIN_WORK - PAD_DEPTH)            # contact board front face, behind the Core's rear face (-1.3)
PLUG_SMT, PLUG_THT = 8.6, 8.0                # mated height of a PH plug on its header (jst_ePH.pdf p.2, p.1)
CV = core.OY1 - m.REAR_PADS[1]               # v of the pad field's centre; its u is 0
# Contact board (KiCad x, y seen from the Core's side; kept in step with tools/dock_pcb.py): 16.2 x 27 mm, pin field
# centre at `field`, j1 = the harness header's body on its back, r101 = the ID resistor on its back, screws = the
# saddle's two screws beside the board.
CONTACT = dict(size=(16.2, 27.0), field=(4.4, 13.5), t=1.6, j1=(7.25, 2.8, 15.75, 24.2), r101=(9.7, 0.2, 13.3, 2.4),
               screws=[(18.65, 5.5), (18.65, 21.5)])
PLATE = 5.5                                  # the Dock's front is this thick where the contact board sits
ZONE = (-5.2, 17.4)                          # u range of that thick part
LEG, LEG_U1 = 4.0, 16.4                      # the saddle's leg: depth of its pocket, outer edge
SLAB = 5.0                                   # front thickness at a lock screw: 5 mm of an M2 x 8 in the Dock, 3 in the Core
LOCK_OUTER, LOCK_INNER = [[(x - m.PCB_W / 2, core.OY1 - y) for x, y in pair] for pair in (m.DOCK_LOCK[:2], m.DOCK_LOCK[2:])]
MAGNETS = [(x - m.PCB_W / 2, core.OY1 - y) for x, y in m.DOCK_MAGNETS]     # (u, v), opposite the Core's
MAGNETS = {"bar": MAGNETS, "float": MAGNETS}       # one pair since 2026-11-15, the same for both bodies
MAG_POCKET = 2 * m.MAGNET_T + 0.1            # a stack of two discs, 0.1 mm under the Dock's front face
# Base board (KiCad x, y; Dock x = 23.1 - x, y from the front edge to the rear edge on the port panel's inside):
# 46.2 x 25 mm, parts up. The jack has no 3D model on this machine: a box from its footprint's F.Fab outline and its
# height (wurth_7499010121A.pdf p.1: 16.1 x 25.4 x 13.55 mm); it stands 2.3 mm over the rear edge. j3 = harness header.
BASE = dict(size=(46.2, 25.0), t=1.6, holes=[(3.0, 12.0), (17.0, 21.0)], rj45_x=37.05, usb_x=6.6,
            jack=(29.0, 1.9, 45.1, 27.3, 13.55), j3=(22.2, 4.55, 27.7, 23.45))
PANEL = (49.2, 20.0, 2.0)                    # port panel: width, height, thickness; the jack is 0.3 mm proud of it
SHELF_H = 3.5                                # under the board: the jack's pins are 3.05 mm long (wurth p.1)
RJ45_CUT = (16.6, 14.05)                     # panel cut-out of the jack, from the base board's top face
# Shelf under the base board (KiCad x0, y0, x1; to the rear edge): not under the jack's pins and pegs, not under the
# front edge's notch. Pockets (x0, y0, x1, y1, depth) for the USB-C shell's legs and the harness header's pins.
SHELF = [(0.3, 9.0, 5.5), (5.5, 14.2, 28.6), (28.6, 18.5, 45.9)]
SHELF_POCKETS = [(1.2, 16.6, 12.0, 23.6, 1.5), (23.2, 14.2, 25.6, 22.4, 2.6)]
DRAWER_SCREWS = [(14.5, 16.0), (37.0, 21.75)]    # from below into the shelf (KiCad x, y); BAR uses the first only


class Frame:
    """Where the Core stands: its bottom rear edge at Dock (y0, z0), leaning back LEAN degrees."""

    def __init__(self, y0, z0):
        self.y0, self.z0 = y0, z0

    def place(self, part):
        """Core-local solid -> Dock frame."""
        return Pos(0, self.y0, self.z0) * Rot(90 - LEAN, 0, 0) * part

    def pt(self, v, w):
        """Core-local (v, w) -> Dock (y, z)."""
        return self.y0 + v * SIN - w * COS, self.z0 + v * COS + w * SIN

    def v_at(self, z, w):
        """v of the point at Dock height z on the plane at Core-local depth w."""
        return (z - self.z0 - w * SIN) / COS

    def behind(self, w=0.0):
        """Everything at Core-local depth w or deeper."""
        return self.place(Pos(0, 0, w - BIG / 2) * Box(BIG, BIG, BIG))

    def core(self):
        to_local = lambda p: Pos(-m.PCB_W / 2, core.OY1, -core.Z_REAR) * p
        panel, _ = core.dummies()
        return [self.place(to_local(part)) for part in (core.body(), panel, core.magnets())]

    def screen(self):
        """Corners of the lit area on the glass (for the pictures): bottom left, bottom right, top right, top left."""
        ax, ay, aw, ah = m.PANEL_AA
        assert abs(m.PANEL_W - 2 * ax - aw) < 0.01, "PANEL_AA: the datasheet has 3.00 mm on both sides"
        u0, v1 = m.PANEL_X0 + ax - m.PCB_W / 2, core.OY1 - m.PANEL_Y0 - ay
        u1, v0 = u0 + aw, v1 - ah
        return [(u, *self.pt(v, CORE_D + 0.03)) for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]


def box(u0, v0, w0, u1, v1, w1):
    return Pos((u0 + u1) / 2, (v0 + v1) / 2, (w0 + w1) / 2) * Box(u1 - u0, v1 - v0, w1 - w0)


def above(z):
    """Everything at Dock height z or higher."""
    return Pos(0, 0, z + BIG / 2) * Box(BIG, BIG, BIG)


def arc(centre, r, p, q):
    """Outline item for profile(): the arc around centre from p to q (the short way), as (mid point, q)."""
    d = (p[0] + q[0] - 2 * centre[0], p[1] + q[1] - 2 * centre[1])
    n = math.hypot(*d)
    return (centre[0] + r * d[0] / n, centre[1] + r * d[1] / n), q


def profile(outline, x0, x1):
    """Extrudes a closed (y, z) outline from x0 to x1. Items are corner points or arc() items."""
    edges, prev = [], outline[0]
    for item in [*outline[1:], outline[0]]:
        if isinstance(item[0], tuple):
            edges.append(ThreePointArc(prev, *item))
            prev = item[1]
        else:
            edges.append(Line(prev, item))
            prev = item
    return Pos(x0, 0, 0) * extrude(Plane.YZ * make_face(edges), amount=x1 - x0, dir=(1, 0, 0))


def circle3(a, b, c):
    """Centre and radius of the circle through three (y, z) points."""
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    sq = [p[0] ** 2 + p[1] ** 2 for p in (a, b, c)]
    y = (sq[0] * (b[1] - c[1]) + sq[1] * (c[1] - a[1]) + sq[2] * (a[1] - b[1])) / d
    z = (sq[0] * (c[0] - b[0]) + sq[1] * (a[0] - c[0]) + sq[2] * (b[0] - a[0])) / d
    return (y, z), math.hypot(a[0] - y, a[1] - z)


def pad_centres():
    """(u, v) of the 18 rear pads: two columns 3.5 mm apart, 9 rows at 2.54 mm."""
    return [(du, CV + (i - 4) * 2.54) for du in (-1.75, 1.75) for i in range(9)]


def contact_uv(x, y):
    """Contact board (KiCad x, y; seen from the Core's side) -> Core-local (u, v)."""
    return x - CONTACT["field"][0], CV + CONTACT["field"][1] - y


def seat(f):
    """The Dock's front under the contact board: (solid to add inside the Dock's outer shape, cutter).
    Recess for the board (its back on the floor, 2.9 mm deep) and the saddle; under the pins' solder tails the
    floor is 1.2 mm lower; the harness header, its plug and the start of the wires go through a window."""
    (u0, v1), (u1, v0) = contact_uv(0, 0), contact_uv(*CONTACT["size"])
    back = BOARD_W - CONTACT["t"]
    add = box(ZONE[0], v0 - 1.4, -PLATE, ZONE[1], v1 + 1.4, 0)
    cut = box(u0 - 0.2, v0 - 0.2, back, u1 + 0.2, v1 + 0.2, 1)
    cut += box(u1, v0 - 0.2, -LEG, LEG_U1, v1 + 0.2, 1)
    cut += box(-2.5, CV - 11.4, back - 1.2, 2.6, CV + 11.4, back)
    for (x0, y0, x1, y1), depth in ((CONTACT["j1"], PLUG_SMT + 0.6), (CONTACT["r101"], 0.9)):
        (a0, b1), (a1, b0) = contact_uv(x0, y0), contact_uv(x1, y1)
        cut += box(a0 - 0.4, b0 - 0.4, back - depth, a1 + 0.4, b1 + 0.4, back)
    for xy in CONTACT["screws"]:        # bosses and pilot holes for the saddle's two screws
        us, vs = contact_uv(*xy)
        add += box(us - 2.6, vs - 2.6, -LEG - 5.6, us + 2.6, vs + 2.6, -PLATE + 0.1)
        cut += Pos(us, vs, -LEG - 4.6) * extrude(Circle(0.85), amount=4.7)
    return f.place(add), f.place(cut)


def saddle():
    """Holds the contact board in its recess (Core-local frame). A 1.05 mm plate over the board, the block that
    reaches 3.0 mm into the Core's 3.6 mm deep pad window with a 1.9 mm hole per pad, and a leg beside the board
    with the two screws. Its front is 0.1 mm under the Dock's front face. The block has 0.3 mm play all round in
    the window (corners rounded like the window's): it puts the pads on the pins and carries the Core's weight,
    with or without the lock screws, and it is in the window 1.7 mm before the first pin touches a pad."""
    (u0, v1), (u1, v0) = contact_uv(0, 0), contact_uv(*CONTACT["size"])
    part = box(u0 - 0.1, v0 - 0.1, BOARD_W + 0.15, u1 + 0.3, v1 + 0.1, -0.1)
    part += box(u1 + 0.3, v0 - 0.1, -LEG + 0.1, LEG_U1 - 0.1, v1 + 0.1, -0.1)
    hw, hl = m.REAR_PADS_SIZE[0] / 2 + 1.2, m.REAR_PADS_SIZE[1] / 2 + 1.2
    part += Pos(0, CV, -0.1) * extrude(RectangleRounded(2 * hw, 2 * hl, 1.2), amount=3.1)
    for u, v in pad_centres():
        part -= Pos(u, v, -2) * extrude(Circle(PIN_BODY / 2 + 0.2), amount=6)
    for xy in CONTACT["screws"]:        # countersunk, so no head stands against the Core's rear face
        us, vs = contact_uv(*xy)
        part -= Pos(us, vs, -LEG) * extrude(Circle(1.15), amount=LEG)
        part -= Pos(us, vs, -0.7) * Cone(0.75, 1.95, 1.2)
    return part


def lock(f, positions, reach=70.0):
    """Cutter for the lock screws: 2.4 mm clearance holes through the Dock's front, heads inside, and a 4.5 mm
    screwdriver hole on the same axis out through the Dock's rear."""
    cut = None
    for u, v in positions:
        hole = Pos(u, v, -SLAB - 1) * extrude(Circle(1.2), amount=SLAB + 2)
        hole += Pos(u, v, -SLAB - reach) * extrude(Circle(2.25), amount=reach)
        cut = hole if cut is None else cut + hole
    return f.place(cut)


def magnets(f, places):
    """The Dock's magnets: (solid to add inside the Dock's outer shape, cutter, the two stacks). Each pocket is open
    to the front, where the magnets are glued in, and has 1.2 mm of plastic around and behind it."""
    def discs(radius, w0, w1):
        each = [Pos(u, v, w0) * extrude(Circle(radius), amount=w1 - w0) for u, v in places]
        return f.place(sum(each[1:], each[0]))
    r = m.MAGNET_D / 2
    return discs(r + 1.3, -MAG_POCKET - 1.2, 0), discs(r + 0.1, -MAG_POCKET, 1), discs(r, -MAG_POCKET, -0.1)


def block(x0, y0, z0, x1, y1, z1):
    """Box in the Dock frame."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


class Drawer:
    """Port panel with the shelf that carries the base board. yp = y of the panel's outer face, zb = its bottom."""

    def __init__(self, yp, zb):
        self.yp, self.zb = yp, zb
        self.top = zb + SHELF_H + BASE["t"]         # the base board's top face

    def xy(self, x, y):
        """Base board (KiCad x, y) -> Dock (x, y)."""
        return BASE["size"][0] / 2 - x, self.yp - PANEL[2] - BASE["size"][1] + y

    def part(self):
        (pw, ph, pt), yp, zb, top = PANEL, self.yp, self.zb, self.top
        part = block(-pw / 2, yp - pt, zb, pw / 2, yp, zb + ph)
        jx, ux = self.xy(BASE["rj45_x"], 0)[0], self.xy(BASE["usb_x"], 0)[0]
        part -= block(jx - RJ45_CUT[0] / 2, yp - pt - 1, top, jx + RJ45_CUT[0] / 2, yp + 1, top + RJ45_CUT[1])
        # USB-C opening with a pocket for the plug's overmould (0.55 mm of panel left)
        part -= block(ux - 4.8, yp - pt - 1, top + 1.63 - 1.9, ux + 4.8, yp + 1, top + 1.63 + 1.9)
        part -= block(ux - 6.5, yp - 1.45, top + 1.63 - 3.2, ux + 6.5, yp + 1, top + 1.63 + 3.2)
        for x0, y0, x1 in SHELF:
            (ax, ay), (bx, by) = self.xy(x0, y0), self.xy(x1, BASE["size"][1])
            part += block(bx, ay, zb, ax, by + 0.01, zb + SHELF_H)
        for x0, y0, x1, y1, depth in SHELF_POCKETS:
            (ax, ay), (bx, by) = self.xy(x0, y0), self.xy(x1, y1)
            part -= block(bx, ay, zb + SHELF_H - depth, ax, by, zb + SHELF_H + 1)
        for xy in BASE["holes"]:            # M2 pilot holes for the board's screws
            part -= Pos(*self.xy(*xy), zb + 0.2) * extrude(Circle(0.85), amount=SHELF_H)
        for xy in DRAWER_SCREWS:            # and for the screws from below
            part -= Pos(*self.xy(*xy), zb) * extrude(Circle(0.85), amount=3.2)
        return part

    def opening(self, depth, up=0.2):
        """Cutter for the Dock's rear: the way in for the drawer (the board has 0.5 mm play each side), and a 1 mm
        ledge at each end of the panel (0.2 mm play around it). `up`: how far the cut goes above the panel."""
        (pw, ph, pt), yp, zb = PANEL, self.yp, self.zb
        return (block(-pw / 2 + 1.0, yp - depth, zb - 0.2, pw / 2 - 1.0, yp + 5, zb + ph + up)
                + block(-pw / 2 - 0.2, yp - pt - 0.05, zb - 0.2, pw / 2 + 0.2, yp + 5, zb + ph + up))

    def screw(self, i, length):
        """Cutter for a countersunk M2 screw from below (head at z = 0) into the shelf's pilot hole i."""
        x, y = self.xy(*DRAWER_SCREWS[i])
        return Pos(x, y, 0) * extrude(Circle(1.15), amount=length) + Pos(x, y, 0.6) * Cone(1.95, 0.75, 1.2)


def boards(f, d):
    """The two Dock boards from KiCad, placed in the Dock, with boxes for the jack and the mated harness plugs.
    KiCad's STEP: y flipped, z = 0 on the board's back."""
    out = {}
    src = COMMON / "maratus-dock-contact-pcb.step"
    if src.exists():
        back = BOARD_W - CONTACT["t"]
        x0, y0, x1, y1 = CONTACT["j1"]
        (a0, b1), (a1, b0) = contact_uv(x0, y0), contact_uv(x1, y1)
        out["contact board"] = f.place(Compound(children=[Pos(*contact_uv(0, 0), back) * import_step(str(src)),
                                                          box(a0, b0, back - PLUG_SMT, a1, b1, back)]))
    src = COMMON / "maratus-dock-base-pcb.step"
    if src.exists():
        solids = [Pos(*d.xy(0, 0), d.top - BASE["t"]) * Rot(0, 0, 180) * import_step(str(src))]
        for (x0, y0, x1, y1), h in ((BASE["jack"][:4], BASE["jack"][4]), (BASE["j3"], PLUG_THT)):
            (ax, ay), (bx, by) = d.xy(x0, y0), d.xy(x1, y1)
            solids.append(block(bx, ay, d.top, ax, by, d.top + h))
        out["base board"] = Compound(children=solids)
    return out


def bar():
    """BAR: a round bar as long as the Core is wide lies on the table; the Core leans on a flat on its front, its
    bottom edge 1.2 mm above the table. A foot under the middle of the bar's front reaches the table behind the
    Core's bottom edge: the Core's weight is in front of the bar. Orange caps close the bar's ends; the port panel
    is the flat on its back."""
    r, wall, cut, s, cap, front, floor, foot = 19.0, 2.0, 1.5, 13.0, 2.2, 1.6, 2.0, 18.0
    z0 = 1.2
    f = Frame(CORE_D * COS + (z0 + CORE_D * SIN) * SIN / COS, z0)     # the plane of the glass meets the table at y = 0
    zc = r - cut                                                     # 1.5 mm of the bar is cut off as its standing face
    va = (zc - z0 + s * SIN) / COS                                   # the axis is s behind the Core's rear face
    yc = f.pt(va, -s)[0]
    end = CORE_W / 2 - cap
    tube = lambda rad, x0, x1: Pos((x0 + x1) / 2, yc, zc) * Rot(0, 90, 0) * Cylinder(rad, x1 - x0)
    solid = f.behind() & above(0)
    d = Drawer(yc + math.sqrt(r ** 2 - (PANEL[1] / 2) ** 2), zc - PANEL[1] / 2)     # the panel is a chord of the bar
    hull = (tube(r, -end, end) + block(-foot, yc - 60, 0, foot, yc, zc)) & solid
    body = hull - (tube(r - wall, -end, end) & above(floor) & f.behind(-front))
    add, cutter = seat(f)
    body += add & hull
    flat = math.sqrt(r * r - s * s)                                  # the bar touches the Core from va - flat to va + flat
    assert all(abs(v - va) + m.MAGNET_D / 2 + 1.3 < flat for _, v in MAGNETS["bar"]), "a magnet is off the bar's flat"
    madd, mcut, _ = magnets(f, MAGNETS["bar"])
    body += madd & hull
    su, sv = m.SERVICE_SW[0] - m.PCB_W / 2, core.OY1 - m.SERVICE_SW[1]
    body += f.place(Pos(su, sv, -45) * extrude(Circle(3.0), amount=45)) & hull     # guide for the service pin
    for sgn in (-1, 1):
        u, v = LOCK_OUTER[0]
        x0, x1 = sorted((sgn * (abs(u) - 3.5), sgn * (abs(u) + 2.3)))
        body += f.place(box(x0, v - 4, -SLAB, x1, v + 4, 0)) & hull                # front thickness at the lock screws
        x0, x1 = sorted((sgn * (PANEL[0] / 2 - 1.0), sgn * (PANEL[0] / 2 + 2.0)))  # walls at the ends of the panel
        body += tube(r - wall + 0.1, x0, x1) & block(-BIG, yc + 12, -BIG, BIG, yc + BIG, BIG)
    sx, sy = d.xy(*DRAWER_SCREWS[0])
    body += Pos(sx, sy, 0) * extrude(Circle(3.5), amount=d.zb - 0.1)               # the drawer's shelf lands on this
    body -= cutter
    body -= lock(f, LOCK_OUTER)
    body -= mcut
    body -= f.place(Pos(su, sv, -46) * extrude(Circle(1.0), amount=47))
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
        ring = lambda g: tube(r - wall - g, s0, s1) & above(floor + g) & f.behind(-front - g)
        part += ring(0.15) - ring(1.75)
        part -= Pos(sgn * (end + cap), yc + 1.0, zc) * Rot(25, 0, 0) * Box(2.4, 14.0, 1.8)      # coin slot (look only)
        return part

    printed = {"body": (body, "body"), "cap-left": (end_cap(-1), "accent"), "cap-right": (end_cap(1), "accent")}
    note = (f"bar {2 * r:.0f} mm across, its axis {s:.1f} mm behind the Core's rear face and {zc:.1f} mm above the table; "
            f"it touches the Core from {va - math.sqrt(r * r - s * s):.1f} to {va + math.sqrt(r * r - s * s):.1f} mm up its "
            f"rear face; standing face {2 * math.sqrt(r * r - zc * zc):.1f} mm deep, {yc - math.sqrt(r * r - zc * zc):.1f} "
            f"to {yc + math.sqrt(r * r - zc * zc):.1f} mm behind the front; foot at {f.pt(f.v_at(0, 0), 0)[0]:.1f} mm")
    return f, d, printed, note


def float_():
    """FLOAT: a thin plate on the table; the Core hovers 9 mm above it, carried by a wedge behind its lower half that
    is narrower than the Core. The wedge's top is one flat slope from the Core down to a rolled rear edge, which ends
    on the top of the port panel. Slope and roll are a cap that lifts off: with it off, the screwdriver reaches the
    lock screws over the port panel, so the pod has no screwdriver holes. The plate closes the pod from below."""
    plate_t, hover, plate_d, lip = 3.0, 9.0, 66.0, 6.0
    half, yr, vpod, roll, edge, wall, rear, inset = 29.5, 62.0, 34.5, 6.0, 5.0, 2.2, 5.0, 1.0
    f = Frame(lip + CORE_D * COS, plate_t + hover)       # the glass's bottom edge is `lip` behind the plate's front edge
    d = Drawer(yr - inset, plate_t)                      # the port panel lies `inset` inside the rear face
    plate = Pos(0, plate_d / 2, 0) * extrude(RectangleRounded(CORE_W, plate_d, 10.0), amount=plate_t)
    plate = fillet([e for e in plate.edges() if e.center().Z > plate_t - 0.01], 0.8)
    seam = plate_t + PANEL[1] + 0.2                      # the cap ends on the top of the panel's opening
    crown, centre = f.pt(vpod, 0), (yr - roll, seam)
    dist = math.hypot(centre[0] - crown[0], centre[1] - crown[1])
    ang = math.atan2(centre[1] - crown[1], centre[0] - crown[0]) + math.asin(roll / dist)    # the slope is tangent to the roll
    dy, dz, run = math.cos(ang), math.sin(ang), math.sqrt(dist ** 2 - roll ** 2)
    tangent = (crown[0] + run * dy, crown[1] + run * dz)
    hull = profile([f.pt(f.v_at(plate_t, 0), 0), (yr, plate_t), (yr, seam), arc(centre, roll, (yr, seam), tangent), crown],
                   -half, half)
    # One radius along each side: the slope's edge, the roll's and the rear corner are one tangent line.
    hull = fillet([e for e in hull.edges() if e.bounding_box().size.X < 0.01 and e.center().Y > 30
                   and e.center().Z > plate_t + 0.01], edge)
    # The cap is everything above the plane through the seam that is parallel to the slope (lo, hi: mm above it).
    band = lambda lo, hi: profile([(yr + 200 * dy, seam + 200 * dz + lo), (yr - 200 * dy, seam - 200 * dz + lo),
                                   (yr - 200 * dy, seam - 200 * dz + hi), (yr + 200 * dy, seam + 200 * dz + hi)], -BIG, BIG)
    cap, tub = hull & band(0, BIG), hull - band(0, BIG)
    slope = -dz / dy
    v_seam = (seam + slope * (yr - f.y0 - PLATE * COS) - f.z0 + PLATE * SIN) / (COS + slope * SIN)
    assert v_seam > contact_uv(0, 0)[1] + 1.4, "the cap cuts into the contact board's seat: raise vpod"
    hole = f.pt(LOCK_INNER[0][1], 0)
    over = hole[1] - (d.yp - hole[0]) * SIN / COS - 2.25 - (plate_t + PANEL[1])    # screwdriver hole's lower edge over the panel
    assert over > 1.0, "the screwdriver does not pass over the port panel"
    # Inside: walls `wall` thick (the rear wall `rear`, for the panel's ledge), open to the cap.
    yi = yr - rear
    cav = profile([f.pt(f.v_at(plate_t - 1, -wall), -wall), (yi, plate_t - 1), (yi, 100.0), f.pt(f.v_at(100.0, -wall), -wall)],
                  -half + wall, half - wall)
    pod = tub - cav
    add, cutter = seat(f)
    pod += add & tub
    for u, v in LOCK_INNER:
        pod += f.place(Pos(u, v, -SLAB) * extrude(Circle(4.0), amount=SLAB)) & tub
    assert all(v + m.MAGNET_D / 2 + 1.3 < v_seam for _, v in MAGNETS["float"]), "a magnet reaches the cap's seam"
    madd, mcut, _ = magnets(f, MAGNETS["float"])
    pod += madd & tub
    # Four M2 screws from below hold the plate: two blocks in front of the drawer, two ribs on the side walls
    # beside it, all four grown out of the side walls.
    pillars = ([(sgn * (half - wall - 2.2), 27.0, 4.6, 5.0) for sgn in (-1, 1)]
               + [(sgn * (half - 2.0), 53.0, 4.0, 6.0) for sgn in (-1, 1)])
    for x, y, px, py in pillars:
        pod += block(x - px / 2, y - py / 2, plate_t, x + px / 2, y + py / 2, plate_t + 8) & tub
        pod -= Pos(x, y, plate_t) * extrude(Circle(0.85), amount=7)
    pod -= cutter
    pod -= lock(f, LOCK_INNER)
    pod -= mcut
    pod -= d.opening(rear + 1, BIG)    # nothing of the pod over the panel: the cap's rear edge closes the opening
    # Two rails under the cap sit inside the side walls (0.15 mm play); their rear ends stand against the rear wall.
    # shortcut: nothing holds the cap down but that fit, tune the play or add a catch after the first print
    for sgn in (-1, 1):
        x0, x1 = sorted((sgn * (half - wall - 1.35), sgn * (half - wall - 0.15)))
        cap += block(x0, 38.0, 0, x1, yi - 0.15, BIG) & band(-2.5, 0.5)
    for x, y, _, _ in pillars:          # countersunk, so no screw head stands on the table
        plate -= Pos(x, y, 0) * extrude(Circle(1.15), amount=plate_t) + Pos(x, y, 0.6) * Cone(1.95, 0.75, 1.2)
    for i in range(len(DRAWER_SCREWS)):
        plate -= d.screw(i, plate_t)
    note = (f"plate {CORE_W:.1f} x {plate_d:.0f} x {plate_t:.0f} mm, Core {hover:.0f} mm above it; pod {2 * half:.0f} mm wide, "
            f"from {f.pt(f.v_at(plate_t, 0), 0)[0]:.1f} to {yr:.0f} mm behind the plate's front edge, up to {vpod:.1f} mm up the "
            f"Core's rear face ({crown[1]:.1f} mm above the table); its top falls {math.degrees(-ang):.1f} degrees to a "
            f"{roll:.0f} mm roll that ends {seam:.1f} mm above the table; the cap is the top {roll * (1 - math.cos(math.pi / 2 + ang)):.2f} mm "
            f"(seam {v_seam:.1f} mm up the seat's back); with the cap off the screwdriver passes {over:.2f} mm over the panel")
    return f, d, {"pod": (pod, "body"), "cap": (cap, "body"), "plate": (plate, "accent")}, note


VARIANTS = {"bar": bar, "float": float_}


def overlap(a, b):
    return sum(h.volume for h in (s & t for s in a.solids() for t in b.solids()) if h)


def build(name):
    if m.REAR_PADS_SIZE[0] > m.REAR_PADS_SIZE[1]:
        # The Core's pad field lies horizontal since 2026-11-14 (owner). Turning the contact board with it puts
        # its harness plug across the RJ45 jack, so the board, the seat, the saddle and both bodies have to be
        # drawn again. Left until the owner has chosen the Dock's look (docs/design-spec.md section 13).
        raise SystemExit("tools/dock.py draws the Dock for a vertical pad field; the Core's field is horizontal now")
    out = ROOT / f"dock-{name}"
    out.mkdir(parents=True, exist_ok=True)
    COMMON.mkdir(parents=True, exist_ok=True)
    f, d, printed, note = VARIANTS[name]()
    core_body, core_panel, core_magnets = f.core()
    shared = {"saddle": saddle(), "drawer": Drawer(0, 0).part()}       # in their own frames, for printing
    for key, part in shared.items():
        export_step(part, str(COMMON / f"maratus-dock-{key}.step"))
        export_stl(part, str(COMMON / f"maratus-dock-{key}.stl"), tolerance=0.03, angular_tolerance=0.2)
    parts = {**{key: part for key, (part, _) in printed.items()}, "saddle": f.place(shared["saddle"]), "drawer": d.part(),
             "core body": core_body, "core panel": core_panel, "core magnets": core_magnets,
             "dock magnets": magnets(f, MAGNETS[name])[2], **boards(f, d)}
    for key, part in parts.items():
        if key in printed or key in shared:
            assert part.is_valid and len(part.solids()) == 1, f"{key}: {len(part.solids())} solids"
            bb = shared.get(key, part).bounding_box()       # shared parts: size in their own frame
            print(f"{name} {key}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3")
        if key in printed:
            export_step(part, str(out / f"maratus-dock-{name}-{key}.step"))
        export_stl(part, str(out / f"{key.replace(' ', '-')}.stl"), tolerance=0.03, angular_tolerance=0.2)
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if {a, b} == {"core body", "core panel"}:
                continue
            v = overlap(parts[a], parts[b])
            assert v < 0.05, f"{name}: {a} collides with {b} ({v:.2f} mm3)"
    print(f"  no overlap between any two of: {', '.join(names)}")
    everything = Compound(children=list(parts.values())).bounding_box()
    print(f"  with the Core docked: {everything.size.X:.1f} wide, {everything.size.Y:.1f} deep, {everything.max.Z:.1f} mm high, "
          f"lean {LEAN:.0f} degrees; {note}")
    export_step(Compound(children=list(parts.values())), str(out / f"maratus-dock-{name}-assembly.step"))
    scene = {"parts": {**{key: mat for key, (_, mat) in printed.items()}, "saddle": "body", "drawer": "body",
                       "core-body": "body", "core-panel": "glass", "core-magnets": "steel", "dock-magnets": "steel",
                       "contact-board": "dark", "base-board": "dark"},
             "screen": f.screen(), "size": [round(everything.size.X, 1), round(everything.max.Y, 1), round(everything.max.Z, 1)]}
    (out / "scene.json").write_text(json.dumps(scene, indent=1))


def screen_image(path, px=1024):
    """What the display shows in the pictures: the text of the concept picture on maratus.co and a QR code, on black.
    The lit area is not centred on the glass (2.95 mm above it, 8.71 mm below), so the layout is placed from the
    glass's centre. Firmware has to do the same, or the content sits 2.9 mm too high."""
    import subprocess
    from PIL import Image, ImageDraw, ImageFont
    _, ay, aw, ah = m.PANEL_AA
    k = px / aw                                                     # pixels per mm
    row = lambda mm: round((m.PANEL_H / 2 + mm - ay) * k)           # mm below the glass's centre -> image row
    qr = path.with_name("dock-qr.png")                              # 25 modules of 20 px: 35 mm
    subprocess.run(["qrencode", "-o", str(qr), "-s", "20", "-m", "0", "-l", "M", "https://maratus.co"], check=True)
    code = Image.open(qr).convert("L").point(lambda p: 255 - p)
    img = Image.new("RGB", (px, round(ah * k)), (0, 0, 0))
    img.paste(Image.merge("RGB", (code, code, code)), ((px - code.width) // 2, row(-16.0)))
    font = lambda style, size: ImageFont.truetype(subprocess.run(
        ["fc-match", "-f", "%{file}", f"Noto Sans:{style}"], capture_output=True, text=True, check=True).stdout, size)
    draw = ImageDraw.Draw(img)
    for text, fnt, mm in (("A little surprise.", font("bold:italic", 80), -25.9), ("Just for you.", font("regular", 44), 24.1)):
        draw.text(((px - draw.textlength(text, font=fnt)) / 2, row(mm)), text, font=fnt, fill=(226, 245, 106))
    img.save(path)


if __name__ == "__main__":
    for variant in sys.argv[1:] or VARIANTS:
        build(variant)
    screen_image(ROOT.parent / "out" / "dock-screen.png")
