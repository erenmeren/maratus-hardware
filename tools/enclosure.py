#!/usr/bin/env python3
"""Maratus Core enclosure (prototype, 3D-print geometry): front shell and rear cover.

  out/tools/cadenv/bin/python tools/enclosure.py     -> mechanical/core/*.step and *.stl

Needs build123d (Python 3.12 environment in out/tools/cadenv). Dimensions come from tools/mech.py.
CAD frame: X = PCB x (device seen from the rear), Y = -PCB y, Z = 0 on the PCB's rear face, +Z towards the rear.
Assembly: panel into the front shell, PCB onto the four bosses, both FFC tails folded onto the rear face,
rear cover on, four M2 x 10 thread-forming screws from the rear through cover posts and PCB into the bosses.
Not a tooling design: no draft angles, no snap fits, no sealing, wall strength not analysed.
"""
import pathlib
import sys

from build123d import (Axis, Circle, Compound, Pos, Rectangle, RectangleRounded, export_step, export_stl, extrude, fillet,
                       import_step)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mech as m  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "mechanical" / "core"

WALL, LIP_T, COVER_T = 1.8, 1.0, 1.6
Z_PCB_FRONT = -m.PCB_T                                  # -1.2
Z_PANEL_BACK = Z_PCB_FRONT - m.GAP_PANEL_PCB            # -1.8
Z_GLASS = Z_PANEL_BACK - m.PANEL_T                      # -5.95: front glass surface, inside face of the bezel
Z_FRONT = Z_GLASS - LIP_T                               # -6.95: outside face of the bezel
Z_TOP = m.PART_H + 0.5                                  # 4.5: top of the tray wall, inside face of the cover
Z_REAR = Z_TOP + COVER_T                                # 6.1
# Cavity: panel plus 0.35 mm at the sides, PCB plus 0.4 / 0.5 mm at top and bottom.
CX0, CX1 = m.PANEL_X0 - 0.35, m.PANEL_X0 + m.PANEL_W + 0.35
CY0, CY1 = -0.4, m.PCB_H + 0.5
OX0, OX1, OY0, OY1 = CX0 - WALL, CX1 + WALL, CY0 - WALL, CY1 + WALL
USB_Z, USB_W, USB_H = 1.63, 9.6, 3.8                    # receptacle centre above the PCB (3.26 mm shell), opening


def block(x0, y0, x1, y1, z0, z1, r=0.0):
    """Box given in the PCB frame (y down)."""
    face = RectangleRounded(x1 - x0, y1 - y0, r) if r else Rectangle(x1 - x0, y1 - y0)
    return Pos((x0 + x1) / 2, -(y0 + y1) / 2, z0) * extrude(face, amount=z1 - z0)


def cyl(x, y, d, z0, z1):
    return Pos(x, -y, z0) * extrude(Circle(d / 2), amount=z1 - z0)


def front_shell():
    part = block(OX0, OY0, OX1, OY1, Z_FRONT, Z_TOP, r=4.0)
    part = fillet(part.edges().group_by(Axis.Z)[0], 0.8)                 # soften the front rim
    part -= block(CX0, CY0, CX1, CY1, Z_GLASS, Z_TOP, r=2.2)
    # Window: the touch glass viewing area plus 0.3 mm. The bezel covers the glass border.
    vx0 = m.PANEL_X0 + m.PANEL_W - m.PANEL_VA_LEFT - m.PANEL_VA_W
    vy0 = m.PANEL_Y0 + m.PANEL_VA_TOP
    part -= block(vx0 - 0.3, vy0 - 0.3, vx0 + m.PANEL_VA_W + 0.3, vy0 + m.PANEL_VA_H + 0.3, Z_FRONT, Z_GLASS, r=1.0)
    for x, y in m.HOLES:                                                 # PCB bosses with pilot holes for M2 screws
        part += cyl(x, y, 5.0, Z_GLASS, Z_PCB_FRONT)
        part -= cyl(x, y, 1.7, Z_GLASS + 0.6, Z_PCB_FRONT)
    # Panel stops: top edge, and bottom edge between the tails and the bosses. 3 mm high, 0.35 mm play.
    top, bottom = m.PANEL_Y0 - 0.35, m.PANEL_Y1 + 0.35
    for x0, x1 in ((8.0, 30.0), (46.0, 68.0)):
        part += block(x0, top - 1.2, x1, top, Z_GLASS, Z_GLASS + 3.0)
    for x0, x1 in ((8.0, 29.5), (46.5, 57.5)):
        part += block(x0, bottom, x1, bottom + 1.2, Z_GLASS, Z_GLASS + 3.0)
    # USB-C opening in the bottom wall.
    part -= block(m.USB_X - USB_W / 2, CY1 - 0.2, m.USB_X + USB_W / 2, OY1 + 0.2, USB_Z - USB_H / 2, USB_Z + USB_H / 2)
    # The receptacle's front is flush with the PCB edge (GCT_USB4105_drawing.pdf), 0.5 mm inside the wall. A pocket
    # for the plug's overmould leaves 0.5 mm of wall, so the plug stops 1.0 mm short of the receptacle.
    part -= block(m.USB_X - 6.5, OY1 - 1.3, m.USB_X + 6.5, OY1 + 0.2, USB_Z - 3.6, USB_Z + 2.8, r=0)
    return part


def rear_cover():
    part = block(OX0, OY0, OX1, OY1, Z_TOP, Z_REAR, r=4.0)
    part = fillet(part.edges().group_by(Axis.Z)[-1], 0.8)
    lip = block(CX0 + 0.15, CY0 + 0.15, CX1 - 0.15, CY1 - 0.15, Z_TOP - 0.8, Z_TOP, r=2.05)
    part += lip - block(CX0 + 1.35, CY0 + 1.35, CX1 - 1.35, CY1 - 1.35, Z_TOP - 0.8, Z_TOP, r=0.9)
    for x, y in m.HOLES:                                                 # posts clamp the PCB onto the bosses
        part += cyl(x, y, 5.4, 0.1, Z_TOP)
    for x, y in m.HOLES:
        part -= cyl(x, y, 2.4, 0.1, Z_REAR)
        part -= cyl(x, y, 4.4, Z_REAR - 1.3, Z_REAR)                      # screw head recess
    px, py = m.REAR_PADS                                                 # window over the contact field P1
    w, h = m.REAR_PADS_SIZE[0] + 3.0, m.REAR_PADS_SIZE[1] + 3.0
    part -= block(px - w / 2, py - h / 2, px + w / 2, py + h / 2, Z_TOP, Z_REAR, r=1.5)
    bx, by = m.BUZZER                                                    # sound holes over the buzzer port
    for dx, dy in ((0, 0), (2.2, 0), (-2.2, 0), (1.1, 1.9), (-1.1, 1.9), (1.1, -1.9), (-1.1, -1.9)):
        part -= cyl(bx + dx, by + dy, 1.3, Z_TOP, Z_REAR)
    part -= cyl(*m.SERVICE_SW, 1.6, Z_TOP, Z_REAR)                        # pin hole over the service switch
    return part


def dummies():
    panel = block(m.PANEL_X0, m.PANEL_Y0, m.PANEL_X0 + m.PANEL_W, m.PANEL_Y1, Z_GLASS, Z_PANEL_BACK)
    pcb = block(0, 0, m.PCB_W, m.PCB_H, Z_PCB_FRONT, 0, r=m.PCB_R)
    for (x0, x1) in (m.LCD_NOTCH, m.TP_NOTCH):
        pcb -= block(x0, m.PCB_H - m.NOTCH_DEPTH, x1, m.PCB_H + 1, Z_PCB_FRONT, 0)
    pcb -= block(m.ANTENNA_NOTCH[0], -1, m.ANTENNA_NOTCH[1], m.ANTENNA_NOTCH[2], Z_PCB_FRONT, 0)
    for x, y in m.HOLES:     # so a printed stand-in can be screwed into the shells
        pcb -= cyl(x, y, m.HOLE_D, Z_PCB_FRONT, 0)
    return panel, pcb


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    front, rear = front_shell(), rear_cover()
    panel, pcb = dummies()
    for name, part in (("front-shell", front), ("rear-cover", rear)):
        assert part.is_valid, name
        export_step(part, str(OUT / f"maratus-core-{name}.step"))
        export_stl(part, str(OUT / f"maratus-core-{name}.stl"), tolerance=0.02, angular_tolerance=0.2)
        bb = part.bounding_box()
        print(f"{name}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, volume {part.volume / 1000:.1f} cm3")
    # Interference checks against the panel and the bare PCB (parts on the PCB are not modelled here).
    for a_name, a in (("front-shell", front), ("rear-cover", rear)):
        for b_name, b in (("panel", panel), ("pcb", pcb)):
            v = (a & b).volume if (a & b) else 0.0
            print(f"  overlap {a_name} / {b_name}: {v:.2f} mm3")
            assert v < 0.01, f"{a_name} collides with {b_name}"
    assert (front & rear).volume < 0.01, "front shell collides with rear cover"
    export_step(Compound(children=[front, rear, panel, pcb]), str(OUT / "maratus-core-assembly.step"))
    board = OUT / "maratus-core-pcb.step"       # written by `tools/pcb.py fab`: the routed board with its 3D models
    if board.exists():      # KiCad's STEP frame: y flipped, z = 0 on the face towards the display
        pcb3d = Pos(0, 0, -m.PCB_T) * import_step(str(board))
        top = pcb3d.bounding_box().max.Z
        print(f"board model: tallest modelled part {top:.2f} mm above the PCB, {Z_TOP - top:.2f} mm below the cover")
        for a_name, a in (("front-shell", front), ("rear-cover", rear), ("panel", panel)):
            hits = [(s, a & s) for s in pcb3d.solids()]
            v = sum(h.volume for _, h in hits if h)
            print(f"  overlap {a_name} / board model: {v:.2f} mm3")
            assert v < 0.05, f"{a_name} collides with the board model"
    for name, part in (("panel-dummy", panel), ("pcb-dummy", pcb)):
        export_stl(part, str(OUT / f"{name}.stl"), tolerance=0.05)
    print(f"outside: {OX1 - OX0:.1f} x {OY1 - OY0:.1f} x {Z_REAR - Z_FRONT:.2f} mm")


if __name__ == "__main__":
    main()
