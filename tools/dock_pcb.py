#!/usr/bin/env python3
"""PCBs of the two Dock boards (draft). Run `python3 tools/dock_sch.py` first.

  python3 tools/dock_pcb.py     -> hardware/dock-contact/maratus-dock-contact.kicad_pcb,
                                   hardware/dock-base/maratus-dock-base.kicad_pcb, reports/drc-dock-*.rpt

Same flow as tools/pcb.py: connectors at fixed positions, the few passives next to the pin they connect to,
Freerouting, GND pours on both sides, DRC. Two layers, 1.6 mm. The Ethernet pairs are autorouted, not routed as
pairs: redo them by hand before ordering.
"""
import shutil
import subprocess

import pcbnew

import dock_sch
import mech
import pcb
import sch
from pcb import IU, MM, P

JACK_FRONT = 19.74      # RJ45 footprint: distance from its origin to the front of the jack (F.Fab extent)
JACK_OVERHANG = 2.3     # the jack's front stands this far beyond the board edge (assumption, see docs/design-spec.md)
FIELD = (4.4, 13.5)     # centre of the pin field on the contact board


def contact_pins():
    """Spring pin positions on the contact board, seen from the Core's side, with the field centre at FIELD: row a
    at x + 1.75, pad 1 lowest. That was the Core's pad field until 2026-11-14. The Core's field now lies horizontal
    (row a on top, pad 1 on the right, seen from the Core's front), so this board meets it only when it is mounted
    a quarter turn anticlockwise (its right edge up). The board is not redrawn yet: see tools/dock.py build()."""
    from sheets.dock_contact import PADS
    out = {}
    for pad in PADS:
        row, n = pad[0], int(pad[1])
        out[f"P{row.upper()}{n}"] = (FIELD[0] + (1.75 if row == "a" else -1.75), FIELD[1] + (5 - n) * 2.54, 0)
    return out


BOARDS = {
    # Both Docks (tools/dock.py: BAR and FLOAT) take the same two boards.
    # Contact board: its back lies on the floor of a recess in the Dock's front, a printed saddle holds it from the
    # front, so it has no holes. The pins are through-hole; the harness header stands upright beside them on the
    # back and goes through a window in the recess floor. The ID resistor is in the strip above the header.
    "dock-contact": dict(size=(16.2, 27.0), holes=[], back={"J1", "R101"},
                         fixed=lambda w, h: {**contact_pins(), "J1": (11.0, 13.5, 90), "R101": (11.5, 1.3, 0)}),
    # Base board, on the shelf of the port drawer; its rear edge lies on the inside of the port panel. Seen from the
    # Dock's rear: USB-C left, RJ45 right, the harness header between them next to the jack (short Ethernet pairs).
    # The front edge is notched: 2.5 mm where the Dock's front plate is thick, 14 mm behind the contact board's
    # harness plug. x = 23.1 minus the Dock's x (tools/dock.py).
    "dock-base": dict(size=(46.2, 25.0), holes=[(3.0, 12.0), (17.0, 21.0)], back=set(),
                      notch=[(5.4, 2.5, 28.6), (10.9, 14.0, 21.3)],       # (x0, depth, x1) from the front edge
                      fixed=lambda w, h: {
                          "J2": (37.05 + 4.445, h + JACK_OVERHANG - JACK_FRONT, 270),   # RJ45, port over the rear edge
                          "J1": (6.6, h - 3.675, 0),                                    # USB-C, flush with the rear edge
                          "J3": (24.4, 21.0, 90)}),                                     # harness, VIN pins at the rear
}


def outline(w, h, notch):
    """Board outline as corner points: a rectangle whose front edge (y = 0) has stepped notches."""
    xs = sorted({0.0, w, *[x for x0, _, x1 in notch for x in (x0, x1)]})
    depth = lambda x: max([d for x0, d, x1 in notch if x0 <= x < x1], default=0.0)
    pts = []
    for a, b in zip(xs, xs[1:]):
        pts += [(a, depth(a)), (b, depth(a))]
    return [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]] + [(w, h), (0.0, h)]


def rules(board):
    bds = board.GetDesignSettings()
    bds.SetBoardThickness(IU(1.6))
    bds.m_MinClearance, bds.m_TrackMinWidth = IU(0.2), IU(0.2)
    bds.m_ViasMinSize, bds.m_ViasMinAnnularWidth, bds.m_MinThroughDrill = IU(0.6), IU(0.13), IU(0.3)
    bds.m_HoleClearance, bds.m_HoleToHoleMin, bds.m_CopperEdgeClearance = IU(0.15), IU(0.25), IU(0.25)
    ns = bds.m_NetSettings
    ns.ClearNetclasses()
    ns.ClearNetclassPatternAssignments()
    default = ns.GetDefaultNetclass()
    # 0.4 mm is the widest track that enters the USB-C VBUS pads with 0.2 mm clearance. GND gets its copper from
    # the pours on both sides, so it is routed at the default width.
    for nc, track in ((default, 0.25), (pcbnew.NETCLASS("Power"), 0.4)):
        nc.SetClearance(IU(0.2))
        nc.SetTrackWidth(IU(track))
        nc.SetViaDiameter(IU(0.6))
        nc.SetViaDrill(IU(0.3))
        if nc is not default:
            ns.SetNetclass(nc.GetName(), nc)
    ns.SetNetclassPatternAssignment("VIN", "Power")
    pcb.PCB.with_suffix(".kicad_dru").write_text(
        '(version 1)\n(rule "USB-C shell pads sit at the board edge by design"\n'
        '  (condition "A.Reference == \'J1\'")\n  (constraint edge_clearance (min 0.1mm)))\n'
        '(rule "RJ45 jack overhangs the board edge by design"\n'
        '  (condition "A.Reference == \'J2\'")\n  (constraint edge_clearance (min 0.1mm)))\n')


def build(name):
    spec = BOARDS[name]
    w, h = spec["size"]
    top = dock_sch.use(name)
    assert top.exists(), "run tools/dock_sch.py first"
    pcb.PCB = sch.CORE / f"{sch.PROJECT}.kicad_pcb"
    pcb.OUT = sch.ROOT / "out" / f"pcb-{name}"
    pcb.W, pcb.H, pcb.BACK, pcb.STRICT_FIXED, pcb.NEAR = w, h, spec["back"], False, {}
    pcb.FIXED = spec["fixed"](w, h)
    notch = spec.get("notch", [])
    pcb.KEEPOUT = [*[(x - 2.6, y - 2.6, x + 2.6, y + 2.6) for x, y in spec["holes"]],
                   *[(x0 - 0.3, 0, x1 + 0.3, d + 0.3) for x0, d, x1 in notch], (0, 0, 0, 0)]     # never empty: the placer wants rows
    comps, nets = pcb.read_netlist()
    info = pcb.sheet_groups()
    pcb.PCB.unlink(missing_ok=True)
    board = pcbnew.NewBoard(str(pcb.PCB))
    board.SetCopperLayerCount(2)
    rules(board)
    corners = outline(w, h, notch)
    for a, b in zip(corners, corners[1:] + corners[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(IU(0.1))
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        board.Add(s)
    for net in nets:
        board.Add(pcbnew.NETINFO_ITEM(board, net))
    fps = {ref: pcb.load_footprint(c["fp"]) for ref, c in comps.items()}
    geo = {ref: pcb.geometry(fp) for ref, fp in fps.items()}
    pos = pcb.Placer(comps, nets, info, geo).run()
    pcb.populate(board, fps, comps, nets, pos, info, spec["back"])
    pcb.holes(board, spec["holes"])
    for x0, d, x1 in notch:         # the router keeps no distance to an inner edge: no copper within 0.45 mm of a notch
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            area = pcb.zone(board, "", layer, box=(x0 - 0.45, -1.0, x1 + 0.45, d + 0.45), name="notch")
            area.SetIsRuleArea(True)
            area.SetDoNotAllowTracks(True)
            area.SetDoNotAllowVias(True)
            area.SetDoNotAllowZoneFills(True)
    pcbnew.SaveBoard(str(pcb.PCB), board)
    pcbnew.GetSettingsManager().SaveProject()
    dsn, ses = pcb.OUT / f"{sch.PROJECT}.dsn", pcb.OUT / f"{sch.PROJECT}.ses"
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    ses.unlink(missing_ok=True)
    pcb.freerouting(dsn, ses, "40")
    board = pcbnew.LoadBoard(str(pcb.PCB))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise SystemExit("session import failed")
    for ref in ("J1", "J2", "J3"):  # connector ground and shell pins: solid connection to the pours
        fp = board.FindFootprintByReference(ref)
        for pad in fp.Pads() if fp else ():
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    pcb.zone(board, "GND", pcbnew.F_Cu, name="GND pour")
    pcb.zone(board, "GND", pcbnew.B_Cu, name="GND pour")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb.PCB), board)
    report = sch.ROOT / "reports" / f"drc-{name}.rpt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "--schematic-parity", "-o", str(report), str(pcb.PCB)],
                   check=True, stdout=subprocess.DEVNULL)
    found = [line.strip("* \n") for line in report.read_text().splitlines() if line.startswith("** Found")]
    tracks = board.GetTracks()
    print(f"{name}: {w:g} x {h:g} mm, {len(comps)} parts, {sum(t.GetClass() != 'PCB_VIA' for t in tracks)} track segments, "
          f"{sum(t.GetClass() == 'PCB_VIA' for t in tracks)} vias; DRC: {'; '.join(found)}")
    step = sch.ROOT / "mechanical" / "dock" / f"maratus-{name}-pcb.step"
    step.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["kicad-cli", "pcb", "export", "step", "-f", "-o", str(step), "--subst-models", str(pcb.PCB)],
                   check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    for board_name in BOARDS:
        build(board_name)
    shutil.rmtree(sch.ROOT / "out" / "pcb-dock-contact" / "__pycache__", ignore_errors=True)
