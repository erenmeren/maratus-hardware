#!/usr/bin/env python3
"""Maratus Core enclosure (prototype, 3D-print geometry): one body, the display is its lid.

  out/tools/cadenv/bin/python tools/enclosure.py [slim]     -> mechanical/core/*.step, *.stl and the lens's .dxf

Two fronts, the same board and the same rear and bottom in both:
- lens (default; owner, 2026-11-14, after Apple HomeView's screen side): the body's outline is a square with 12 mm
  corners, 4.36 mm larger than the panel on every side, and a 1 mm cover lens with a black border lies over the
  panel and the walls inside a 1.2 mm rim. The panel's own glass has square corners: its corner stays inside the
  body's corner with 1.2 mm of wall. The panel sits 2.11 mm higher over the board than in the slim body, so the
  body's bottom face is where it was and everything on the bottom edge (USB-C, slots) is unchanged.
- slim (the body before that day): the touch glass is flush with the rim and reaches it on all four sides; the
  walls are 1.5 mm (2.0 mm at the bottom), the corners 3 mm.

Needs build123d (Python 3.12 environment in out/tools/cadenv). Dimensions come from tools/mech.py.
CAD frame: X = PCB x (device seen from the front), Y = -PCB y, Z = 0 on the PCB's part side, +Z towards the display.
Assembly: lock nut into its pocket (glue), antenna onto the floor above the board, PCB laid onto the four bosses a
little towards the top and slid down until the USB-C receptacle is in its pocket (M2 x 4 thread-forming screws from
the part side), both FFC tails into J2 and J4, panel folded down onto the taped shelf, lens taped over it.
Not a tooling design: no draft angles, no sealing, wall strength not analysed, panel and lens are held by tape only.
Not tried: the panel's touch through the lens.
"""
import math
import pathlib
import sys

from build123d import (Align, Axis, Circle, Compound, ExportDXF, FontStyle, Pos, Rectangle, RectangleRounded,
                       RegularPolygon, Rot, Text, Unit, export_step, export_stl, extrude, fillet, import_step)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mech as m  # noqa: E402

LENS = "slim" not in sys.argv[1:]
BASE = pathlib.Path(__file__).resolve().parent.parent / "mechanical" / "core"
OUT = BASE if LENS else BASE / "slim"                   # the slim body's files go into their own folder
WALL, WALL_BOTTOM, FLOOR_T, PLAY = 1.5, 2.0, 1.6, 0.25
Z_PCB_BACK = -m.PCB_T                                   # -1.2
Z_FLOOR = Z_PCB_BACK - m.STANDOFF                       # -3.2: inside face of the floor
Z_REAR = Z_FLOOR - FLOOR_T                              # -4.8: rear face of the device
Z_PANEL_BACK = m.PART_H + m.GAP_PARTS_PANEL             # 4.5: shelf the panel lies on
Z_GLASS = Z_PANEL_BACK + m.PANEL_T                      # 8.65: the panel's glass surface
SHELF = 1.5                                             # shelf width and height (45 degree wedge, prints unsupported)
if LENS:
    R_OUT, RIM, LENS_T = 12.0, 1.2, 1.0                 # outline corners, rim around the lens, lens
    EDGE = (R_OUT * (math.sqrt(2) - 1) + RIM) / math.sqrt(2)       # panel edge to body edge: 4.36
    UP = EDGE - (WALL_BOTTOM + PLAY)                    # the panel sits this much higher over the board: 2.11
    SIDE = EDGE - PLAY                                  # wall beside the panel: 4.11
else:
    R_OUT, RIM, LENS_T, UP, SIDE = 3.0, 0.0, 0.0, 0.0, WALL
Z_TOP = Z_GLASS + LENS_T                                # front face: the lens (9.65), or the glass
PY0, PY1 = m.PANEL_Y0 - UP, m.PANEL_Y1 - UP             # the panel in the PCB frame
CX0, CX1 = m.PANEL_X0 - PLAY, m.PANEL_X0 + m.PANEL_W + PLAY
CY0, PCY1 = PY0 - PLAY, PY1 + PLAY                      # the panel's cavity
CY1 = m.PANEL_Y1 + PLAY                                 # the board's cavity ends here (72.59) in both bodies
OX0, OX1, OY0, OY1 = CX0 - SIDE, CX1 + SIDE, CY0 - SIDE, CY1 + WALL_BOTTOM
# USB-C receptacle (GCT_USB4105_drawing.pdf p.1): centre 1.73 mm above the PCB, shell 3.31 mm high, mouth 8.34 x
# 2.56 mm inside. The opening is that mouth plus 0.28 mm all round, with full round ends, as on a phone.
USB_Z, USB_W, USB_H, USB_TOP = 1.73, 8.9, 3.1, 3.31
MAGNET_SKIN = 0.5                                       # floor left behind a Dock magnet: it cannot be seen from outside
AA_R = 5.0                                              # corners of the lens's window; the picture is rounded to match
# The name (owner, 2026-11-14: it has to be on the product somewhere). Lens body: printed on the lens, in the middle
# of the wide border under the picture. Slim body: no room on the front, so sunk 0.4 mm into the rear.
MARK, MARK_SIZE, MARK_REAR_Y, MARK_DEPTH = "maratus", 4.6, 14.0, 0.4


def block(x0, y0, x1, y1, z0, z1, r=0.0):
    """Box given in the PCB frame (y down)."""
    face = RectangleRounded(x1 - x0, y1 - y0, r) if r else Rectangle(x1 - x0, y1 - y0)
    return Pos((x0 + x1) / 2, -(y0 + y1) / 2, z0) * extrude(face, amount=z1 - z0)


def cyl(x, y, d, z0, z1):
    return Pos(x, -y, z0) * extrude(Circle(d / 2), amount=z1 - z0)


def slot(x, y, w, h, z0, z1):
    """Prism with full round ends (w x h), its axis along Z."""
    return Pos(x, -y, z0) * extrude(RectangleRounded(w, h, h / 2 - 0.01), amount=z1 - z0)


def body():
    part = block(OX0, OY0, OX1, OY1, Z_REAR, Z_TOP, r=R_OUT)
    part = fillet(part.edges().group_by(Axis.Z)[0], 2.5 if LENS else 1.0)   # rear edge
    part = fillet(part.edges().group_by(Axis.Z)[-1], 0.4 if LENS else 0.5)  # front rim
    if LENS:        # seat of the lens: the walls' tops are level with the panel's glass
        part -= block(OX0 + RIM, OY0 + RIM, OX1 - RIM, OY1 - RIM, Z_GLASS, Z_TOP + 1, r=R_OUT - RIM)
    part -= block(CX0, CY0, CX1, PCY1, Z_FLOOR, Z_TOP + 1, r=0.5)
    if PCY1 < CY1:  # the board reaches further down than the panel: its cavity goes on under a ledge of the wall,
        # only as wide as the board and with the board's corners, or it would break through the body's round corners
        part -= block(-0.4, PCY1 - 3, m.PCB_W + 0.4, CY1, Z_FLOOR, Z_PANEL_BACK, r=m.PCB_R + 0.2)
    # Shelf under the panel's edge on the top, left and right walls. A wedge: the tapered void leaves 1.5 mm at the
    # top and nothing at the bottom. Slim: also two tabs in the bottom corners, on the bottom wall.
    ring = block(CX0, CY0, CX1, PCY1, Z_PANEL_BACK - SHELF, Z_PANEL_BACK)
    void = Pos((CX0 + CX1) / 2, -(CY0 + PCY1) / 2, Z_PANEL_BACK - SHELF) * extrude(
        Rectangle(CX1 - CX0, PCY1 - CY0), amount=SHELF, taper=45)
    shelf = ring - void
    tab = SHELF if LENS else 5.0
    shelf -= block(CX0 + tab, PCY1 - SHELF - 0.2, CX1 - tab, PCY1 + 0.2, Z_PANEL_BACK - SHELF, Z_PANEL_BACK)
    part += shelf
    for x, y in m.HOLES:                                                  # PCB bosses, pilot holes for M2 screws
        part += cyl(x, y, 5.5, Z_FLOOR, Z_PCB_BACK)
        part -= cyl(x, y, 1.7, Z_REAR + 0.5, Z_PCB_BACK)
    # Lock point: an M4 thin nut pressed into a hexagonal pocket from the inside before the board goes in (glue it:
    # it must not be able to drop onto the board, 0.6 mm above it). 0.8 mm of floor holds it against the pull.
    # A bolt may reach 3.0 mm into the Core and no further.
    flats, high = m.LOCK_NUT
    for x, y in m.DOCK_LOCK:
        part += cyl(x, y, 10.0, Z_FLOOR, Z_REAR + 0.8 + high + 0.2)
        part -= cyl(x, y, 4.5, Z_REAR, Z_PCB_BACK)
        part -= Pos(x, -y, Z_REAR + 0.8) * extrude(RegularPolygon(flats / math.sqrt(3), 6), amount=Z_PCB_BACK - Z_REAR)
    for x, y in m.DOCK_MAGNETS:                                           # glued in from the inside, a collar around each
        part += cyl(x, y, m.MAGNET_D + 2.2, Z_FLOOR, Z_REAR + MAGNET_SKIN + m.MAGNET_T)
        part -= cyl(x, y, m.MAGNET_D + 0.2, Z_REAR + MAGNET_SKIN, Z_PCB_BACK)
    ax, ay, al, aw = m.ANTENNA                                           # 0.4 mm recess that locates the antenna
    part -= block(ax - al / 2 - 0.5, ay - aw / 2 - 0.5, ax + al / 2 + 0.5, ay + aw / 2 + 0.5, Z_FLOOR - 0.4, Z_FLOOR)
    px, py = m.REAR_PADS                                                  # window in the floor over the contact field
    w, h = m.REAR_PADS_SIZE[0] + 3.0, m.REAR_PADS_SIZE[1] + 3.0
    part -= block(px - w / 2, py - h / 2, px + w / 2, py + h / 2, Z_REAR, Z_FLOOR, r=1.5)
    # Bottom wall: USB-C opening (owner, 2026-11-14: like a phone's). The receptacle stands on the board's tab, its
    # mouth mech.USB_TAB[1] beyond the bottom edge, in a pocket on the inside of the wall (also cut into the shelf
    # above it); the plug goes through an oval hole in the wall's outer part. The plug's overmould stops on the
    # outer face, which is within the drawing's 1.85 mm of the mouth, so there is no pocket for it any more.
    # The board is laid in a little towards the top and slid down into the pocket.
    tw, tl = m.USB_TAB
    mouth = m.PCB_H + tl
    assert 0.3 < OY1 - mouth < 1.85 - 0.3, f"USB-C mouth {OY1 - mouth:.2f} mm behind the outer face"
    part -= block(m.USB_X - tw / 2 - 0.3, CY1 - 0.7, m.USB_X + tw / 2 + 0.3, mouth + 0.25, Z_PCB_BACK - 0.3, USB_TOP + 0.3)
    part -= Pos(m.USB_X, -(mouth + OY1) / 2, USB_Z) * Rot(90, 0, 0) * extrude(
        RectangleRounded(USB_W, USB_H, USB_H / 2 - 0.01), amount=(OY1 - mouth) / 2 + 0.5, both=True)
    # Recesses for the two FFC tails where they turn around the panel's bottom edge (behind the glass); in the lens
    # body they are cut into the ledge. Then the sound slots for the buzzer.
    for cx, half in ((m.LCD_TAIL_X, m.LCD_TAIL_W / 2 + 0.5), (m.TP_TAIL_X, m.TP_TAIL_W / 2 + 0.4)):
        part -= block(cx - half, PCY1 - 0.1, cx + half, PCY1 + 1.2, Z_PANEL_BACK - SHELF, Z_GLASS - m.PANEL_GLASS_T)
    z0, z1 = 0.1, 3.3
    for dx in (-2.4, 0.0, 2.4):
        part -= block(m.BUZZER[0] + dx - 0.6, CY1 - 0.2, m.BUZZER[0] + dx + 0.6, OY1 + 0.2, z0, z1)
    # Service switch (owner, 2026-11-14): a fourth slot in the same row. From outside it is a slot like the other
    # three, 1 mm deep; only its lowest 1.2 mm goes through the wall, at the height of the switch's plunger
    # (b3u_omron.pdf p.3: body 1.2 mm high), so a pin cannot pass over the switch into the board.
    sx = m.SERVICE_SW[0]
    part -= block(sx - 0.6, OY1 - 1.0, sx + 0.6, OY1 + 0.2, z0, z1)
    part -= block(sx - 0.6, CY1 - 0.2, sx + 0.6, OY1 + 0.2, z0, z0 + 1.2)
    if not LENS:    # the name, read from behind: turned about Y, so the cut goes into the floor (1.2 mm left)
        part -= Pos(m.PCB_W / 2, -MARK_REAR_Y, Z_REAR) * Rot(0, 180, 0) * extrude(mark(), amount=-MARK_DEPTH)
    return part


def mark():
    return Text(MARK, MARK_SIZE, font="Noto Sans", font_style=FontStyle.BOLD, align=(Align.CENTER, Align.CENTER))


def magnets():
    z = Z_REAR + MAGNET_SKIN
    return Compound(children=[cyl(x, y, m.MAGNET_D, z, z + m.MAGNET_T) for x, y in m.DOCK_MAGNETS])


def lens_outline():
    """(x0, y0, x1, y1, r) of the lens with 0.1 mm play in its seat, and of its clear window over the lit area."""
    ax, ay, aw, ah = m.PANEL_AA
    return ((OX0 + RIM + 0.1, OY0 + RIM + 0.1, OX1 - RIM - 0.1, OY1 - RIM - 0.1, R_OUT - RIM - 0.1),
            (m.PANEL_X0 + ax, PY0 + ay, m.PANEL_X0 + ax + aw, PY0 + ay + ah, AA_R))


def mark_front():
    """(x, y) of the name's centre on the lens: the middle of the border under the picture."""
    ax, ay, aw, ah = m.PANEL_AA
    return (OX0 + OX1) / 2, (PY0 + ay + ah + OY1 - RIM) / 2


def dummies():
    out = {"panel-dummy": block(m.PANEL_X0, PY0, m.PANEL_X0 + m.PANEL_W, PY1, Z_PANEL_BACK, Z_GLASS)}
    pcb = block(0, 0, m.PCB_W, m.PCB_H, Z_PCB_BACK, 0, r=m.PCB_R)
    pcb += block(m.USB_X - m.USB_TAB[0] / 2, m.PCB_H - 1, m.USB_X + m.USB_TAB[0] / 2, m.PCB_H + m.USB_TAB[1], Z_PCB_BACK, 0)
    for x, y in m.HOLES:     # so a printed stand-in can be screwed onto the bosses
        pcb -= cyl(x, y, m.HOLE_D, Z_PCB_BACK, 0)
    out["pcb-dummy"] = pcb
    if LENS:
        (x0, y0, x1, y1, r), _ = lens_outline()
        out["lens-dummy"] = block(x0, y0, x1, y1, Z_GLASS, Z_TOP, r=r)
    return out


def plugs():
    """Silicone plugs (owner, 2026-11-14), as shapes to print in a soft material: one for the lock point when the
    Core is used without a Dock, one for the USB-C opening when it is on one. Flange outside, neck in the hole,
    tip in the nut's thread or in the receptacle's mouth (0.8 mm: the receptacle's tongue starts behind that).
    Sizes are a first guess: nothing is printed or tried."""
    lock = cyl(0, 0, 8.0, 0, 0.8) + cyl(0, 0, 4.4, 0.8, 1.6) + cyl(0, 0, 3.5, 1.6, 3.6)
    wall = OY1 - (m.PCB_H + m.USB_TAB[1])               # outer face to the receptacle's mouth: 1.39
    usb = slot(0, 0, 11.0, 5.0, 0, 0.8) + slot(0, 0, USB_W, USB_H, 0.8, 0.8 + wall) + slot(0, 0, 8.2, 2.4, 0.8 + wall, 1.6 + wall)
    return {"plug-lock": lock, "plug-usb": usb}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    part = body()
    parts = dummies()
    panel, pcb = parts["panel-dummy"], parts["pcb-dummy"]
    assert part.is_valid, "body"
    export_step(part, str(OUT / "maratus-core-body.step"))
    export_stl(part, str(OUT / "maratus-core-body.stl"), tolerance=0.02, angular_tolerance=0.2)
    bb = part.bounding_box()
    print(f"body ({'lens' if LENS else 'slim'}): {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm, volume {part.volume / 1000:.1f} cm3")
    if LENS:
        ax, ay, aw, ah = m.PANEL_AA
        print(f"black border around the picture: {m.PANEL_X0 + ax - OX0 - RIM:.2f} mm sides, {PY0 + ay - OY0 - RIM:.2f} mm top, "
              f"{OY1 - RIM - (PY0 + ay + ah):.2f} mm bottom; rim {RIM} mm; the panel {UP:.2f} mm higher over the board")
    else:
        print(f"plastic seen from the front: {CX0 - OX0 + PLAY:.2f} mm sides and top, {OY1 - CY1 + PLAY:.2f} mm bottom")
    mag = magnets()
    for name, other in (*parts.items(), ("magnets", mag)):
        v = sum(h.volume for h in (part & s for s in other.solids()) if h)
        print(f"  overlap body / {name}: {v:.2f} mm3")
        assert v < 0.01, f"body collides with {name}"
    print(f"magnets: {len(m.DOCK_MAGNETS)} x {m.MAGNET_D:.0f} x {m.MAGNET_T:.0f} mm behind {MAGNET_SKIN} mm of floor, "
          f"{Z_PCB_BACK - mag.bounding_box().max.Z:.2f} mm under the PCB")
    export_step(Compound(children=[part, *parts.values()]), str(OUT / "maratus-core-assembly.step"))
    for name, other in (*parts.items(), *plugs().items()):
        export_stl(other, str(OUT / f"{name}.stl"), tolerance=0.03)
    if LENS:        # for a laser cutter or a print shop: the lens's outline and its clear window, in millimetres
        dxf = ExportDXF(unit=Unit.MM)
        for layer, (x0, y0, x1, y1, r) in zip(("outline", "window"), lens_outline()):
            dxf.add_layer(layer)
            dxf.add_shape(Pos((x0 + x1) / 2, -(y0 + y1) / 2) * RectangleRounded(x1 - x0, y1 - y0, r), layer=layer)
        dxf.add_layer("mark")
        mx, my = mark_front()
        dxf.add_shape(Pos(mx, -my) * mark(), layer="mark")
        dxf.write(str(OUT / "maratus-core-lens.dxf"))
        (x0, y0, x1, y1, r), _ = lens_outline()
        print(f"lens: {x1 - x0:.2f} x {y1 - y0:.2f} x {LENS_T} mm, corners {r:.1f} mm -> maratus-core-lens.dxf")
    board = BASE / "maratus-core-pcb.step"      # written by `tools/pcb.py fab`: the routed board with its 3D models
    if board.exists():      # KiCad's STEP frame: y flipped, z = 0 on the board's back face
        pcb3d = Pos(0, 0, -m.PCB_T) * import_step(str(board))
        bb = pcb3d.bounding_box()
        if abs(bb.size.X - m.PCB_W) > 0.5 or abs(bb.size.Y - m.PCB_H) > 1.5:
            print(f"  board model is {bb.size.X:.1f} x {bb.size.Y:.1f} mm, not this layout's board: run tools/pcb.py fab")
            return
        print(f"board model: parts reach {bb.max.Z:.2f} mm in front of the PCB ({Z_PANEL_BACK - bb.max.Z:.2f} mm below "
              f"the panel) and {Z_PCB_BACK - bb.min.Z:.2f} mm behind it ({bb.min.Z - Z_FLOOR:.2f} mm above the floor)")
        for name, a in (("body", part), ("panel", panel), ("magnets", mag)):
            v = sum(h.volume for h in (t & s for t in a.solids() for s in pcb3d.solids()) if h)
            print(f"  overlap {name} / board model: {v:.2f} mm3")
            assert v < 0.05, f"{name} collides with the board model"


if __name__ == "__main__":
    main()
