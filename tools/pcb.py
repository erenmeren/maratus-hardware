#!/usr/bin/env python3
"""Maratus Core PCB generator (draft layout). Run `python3 tools/sch.py gen` first.

  python3 tools/pcb.py place   netlist -> hardware/core/maratus-core.kicad_pcb: outline, footprints, nets,
                               scripted placement, inner planes, rules. Also writes out/pcb/maratus-core.dsn
  python3 tools/pcb.py route   Freerouting on the DSN, imports the session, adds outer GND pours, fills zones
  python3 tools/pcb.py finish  second Freerouting session on the routed board, for the last few connections;
                               `finish 12 free` also lets it put vias under the P4 (see tune_dsn)
  python3 tools/pcb.py fab     Gerbers, drill files, position file, STEP model and renders

Placement is automatic: a few parts have fixed positions (FIXED), every other part goes to the nearest free
spot next to the IC pin it connects to. Routing is the autorouter's. Nothing is length-matched or
impedance-controlled, so this board is a draft for a layout engineer, not a design to order.
KiCad's top side (F.Cu) faces the display: the parts sit there. The rear contact pads and the service switch are
on the back, which faces the housing floor.
"""
import collections
import importlib
import json
import math
import pathlib
import shutil
import subprocess
import sys

import numpy as np
import pcbnew

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mech  # noqa: E402
import sch  # noqa: E402

PCB = sch.CORE / f"{sch.PROJECT}.kicad_pcb"
OUT = sch.ROOT / "out" / "pcb"
# Freerouting 2.5.0 needs Java 25: a local runtime in out/tools/jre25 (Temurin), the system Java is 21.
JAVA = sch.ROOT / "out" / "tools" / "jre25" / "bin" / "java"
JAR = sch.ROOT / "out" / "tools" / "freerouting-2.5.0.jar"
MM, IU = pcbnew.ToMM, pcbnew.FromMM
W, H = mech.PCB_W, mech.PCB_H

# ref -> (x, y, rotation). Everything else is placed automatically.
FIXED = {
    # C5 module, turned so its SDIO pins (9-14) face the P4. The 1U variant has no antenna on the module, so its
    # orientation is free; the antenna cable runs from its connector along the board's left edge.
    "U2": (16.6, 13.0, 180),
    "U1": (45.0, 21.5, 0),        # P4: DSI pins on its bottom side, 15 mm above J2 so the two lanes can swap over
    "J2": (mech.LCD_TAIL_X, mech.FFC_MOUTH_Y - 4.55, 0),   # FH12 body front is 4.55 mm from the footprint origin
    "J4": (mech.TP_TAIL_X, mech.FFC_MOUTH_Y - 4.6, 0),     # TE 84953 body front is 4.6 mm from the origin
    "J1": (mech.USB_X, None, 0),  # y from the footprint's "PCB Edge" line
    # Back side, long axis horizontal (owner, 2026-11-14), near the bottom edge: at mid-height it walled the
    # bottom of B.Cu off from the P4 and two USB-C nets stayed open. Seen from the front: row a on top, pad 1 on
    # the right. Only its middle 13.5 mm is under the LCD tail; KEEPOUT keeps parts off the rest.
    "P1": (*mech.REAR_PADS, 0),
    "SW701": (*mech.SERVICE_SW, 180), # part side at the bottom edge, plunger towards the edge (slot in the bottom wall)
    "BZ701": (*mech.BUZZER, 0),
    "U7": (59.5, 21.5, 0),        # PHY: RMII pins face U1, its passives get the top right corner
    "J3": (65.8, 46.0, 90),       # camera connector (DNP) on the right edge, opening outwards, below the PHY
    "U3": (26.5, 33.0, 0),        # flash next to the FLASH_* pins (bottom-left corner of U1)
    "U6": (48.2, 61.5, 0),        # power mux just above the rear pads' VIN end (b1, b2)
    "U5": (57.0, 57.5, 0), "U9": (56.0, 47.0, 0),
    "U8": (24.0, 44.5, 0),        # backlight boost next to the LED pins of J2 (pads 1, 2)
    "D102": (48.0, 55.2, 0),      # VIN TVS next to the rear pads
}
NEAR = {"R512": "U7"}             # placed next to this part, not next to the biggest one on its nets
LAST = {"TP104": (65.0, 7.5)}     # only on a plane, no net to follow: after everything else, the free spot nearest to this point
BACK = {"P1"}                     # footprints on B.Cu, the side that faces the housing floor
# The open-source-hardware mark (owner, 2026-11-15: anyone who wants may build the Core), on the back's silkscreen in
# a place free of pads and vias on the routed board of 2026-11-15. KiCad's own footprint: footprint, x, y.
LOGO = ("Symbol:OSHW-Logo2_9.8x8mm_SilkScreen", 10.0, 58.0)
# Body sizes of parts that have no 3D model on this machine (w, h, height in mm), for the 3D views only.
# Buzzer: cmt-8504-100-smt.pdf p.1. Inductor: tps61169.pdf p.12 Table 7-2. P4 and mux heights are nominal.
NO_MODEL = {"U1": (10.0, 10.0, 0.9), "BZ701": (8.5, 8.5, 4.0), "L401": (4.0, 4.0, 1.8), "U6": (2.0, 2.5, 0.9)}
RAILS = sch.RAILS | {"GND", "PHY_3V3", "3V3_USBPHY"}
# 3V3 and GND are planes: their pads only need a short default-width stub to a via.
POWER_NETS = {"5V_SYS", "VIN", "VBUS", "V_ACC", "VDD_HP", "VDD_FLASH", "VDD_PSRAM", "VDD_MIPI", "PHY_3V3",
              "3V3_USBPHY", "BUCK3V3_SW", "DCDC_SW", "BL_SW", "LED_A", "LED_K", "BUZZER_P", "BUZZER_N", "CAM_3V3"}
# No parts here (x0, y0, x1, y1): the two FFC tails lying over the board, screw heads, the rear pads (a part
# above them finds no room for its vias; the fixed parts U6 and BZ701 reach 1 and 2 mm over the field's ends),
# and last the routing channel for the DSI pairs between U1's bottom side and J2.
KEEPOUT = [(mech.LCD_TAIL_X - 6.75, mech.FFC_MOUTH_Y + 0.5, mech.LCD_TAIL_X + 6.75, H),
           (mech.TP_TAIL_X - 3.9, mech.FFC_MOUTH_Y + 2.5, mech.TP_TAIL_X + 3.9, H),
           *[(x - 3.0, y - 3.0, x + 3.0, y + 3.0) for x, y in mech.HOLES],
           (mech.REAR_PADS[0] - mech.REAR_PADS_SIZE[0] / 2 - 0.3, mech.REAR_PADS[1] - mech.REAR_PADS_SIZE[1] / 2 - 0.3,
            mech.REAR_PADS[0] + mech.REAR_PADS_SIZE[0] / 2 + 0.3, mech.REAR_PADS[1] + mech.REAR_PADS_SIZE[1] / 2 + 0.3),
           (33.0, 30.5, 46.0, 44.0)]
EDGE = 0.8      # parts stay this far inside the outline
STRICT_FIXED = True     # tools/dock_pcb.py turns this off: its spring pins sit closer than the placer's margins
LIBS = {**sch.FP_LIBS}


def P(x, y):
    return pcbnew.VECTOR2I(IU(x), IU(y))


def short(net):
    return net.rsplit("/", 1)[-1]


# ---------- netlist ----------

def read_netlist():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "core.net"
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(path),
                    str(sch.CORE / f"{sch.PROJECT}.kicad_sch")], check=True, stdout=subprocess.DEVNULL)
    tree = sch.parse(path.read_text())
    one = lambda node, key: sch.uq(sch.kids(node, key)[0][1])
    comps = {}
    for c in sch.kids(sch.kids(tree, "components")[0], "comp"):
        sp = sch.kids(c, "sheetpath")[0]
        props = {one(p, "name"): (one(p, "value") if sch.kids(p, "value") and len(sch.kids(p, "value")[0]) > 1 else "")
                 for p in sch.kids(c, "property")}
        fields = {one(f, "name"): (sch.uq(f[2]) if len(f) > 2 else "") for f in sch.kids(sch.kids(c, "fields")[0], "field")}
        comps[one(c, "ref")] = dict(value=one(c, "value"), fp=one(c, "footprint"), path=one(sp, "tstamps") + one(c, "tstamps"),
                                    sheet=props.get("Sheetname", ""), sheetfile=props.get("Sheetfile", ""),
                                    fields=fields, dnp="dnp" in props)
    nets = {}
    for n in sch.kids(sch.kids(tree, "nets")[0], "net"):
        nets[one(n, "name")] = [(one(node, "ref"), one(node, "pin")) for node in sch.kids(n, "node")]
    return comps, nets


def sheet_groups():
    """ref -> (sheet, group number, dnp), from the same sheet descriptions tools/sch.py renders."""
    info = {}
    for name in sch.SHEETS:
        sheet, group = sch.Sheet(name), 0
        importlib.import_module(f"sheets.{name.replace('-', '_')}").build(sheet)
        for kind, item in sheet.items:
            if kind == "group":
                group += 1
            elif kind == "part":
                info[item["ref"]] = (name, group, item["dnp"])
    return info


# ---------- board ----------

def load_footprint(fpid):
    lib, name = fpid.split(":", 1)
    fp = pcbnew.FootprintLoad(str(LIBS.get(lib, sch.KICAD_FP / f"{lib}.pretty")), name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def geometry(fp):
    """{rotation: (courtyard box, {pad number: [(x, y), ...]})} with the footprint at the origin."""
    out = {}
    for rot in (0, 90, 180, 270):
        fp.SetPosition(P(0, 0))
        fp.SetOrientationDegrees(rot)
        boxes = [g.GetBoundingBox() for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_CrtYd] \
            or [p.GetBoundingBox() for p in fp.Pads()]
        box = (MM(min(b.GetLeft() for b in boxes)), MM(min(b.GetTop() for b in boxes)),
               MM(max(b.GetRight() for b in boxes)), MM(max(b.GetBottom() for b in boxes)))
        pads = collections.defaultdict(list)
        for p in fp.Pads():
            pads[p.GetNumber()].append((MM(p.GetPosition().x), MM(p.GetPosition().y)))
        out[rot] = (box, dict(pads))
    return out


def outline(board):
    r = mech.PCB_R
    tw, tl = mech.USB_TAB       # the tab under the USB-C receptacle, in the bottom edge
    pts = [(r, 0), (W - r, 0), "arc", (W, r), (W, H - r), "arc", (W - r, H),
           (mech.USB_X + tw / 2, H), (mech.USB_X + tw / 2, H + tl), (mech.USB_X - tw / 2, H + tl), (mech.USB_X - tw / 2, H),
           (r, H), "arc", (0, H - r), (0, r), "arc", (r, 0)]
    corners = iter([(W - r, r), (W - r, H - r), (r, H - r), (r, r)])
    prev = pts[0]
    for i, p in enumerate(pts[1:], 1):
        if p == "arc":
            continue
        s = pcbnew.PCB_SHAPE(board)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(IU(0.1))
        if pts[i - 1] == "arc":
            cx, cy = next(corners)
            ang = math.atan2((prev[1] + p[1]) / 2 - cy, (prev[0] + p[0]) / 2 - cx)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(P(*prev), P(cx + r * math.cos(ang), cy + r * math.sin(ang)), P(*p))
        else:
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*prev))
            s.SetEnd(P(*p))
        board.Add(s)
        prev = p


def zone(board, net, layer, box=None, priority=0, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net:
        z.SetNet(board.FindNet(net))
    x0, y0, x1, y1 = box or (0, 0, W, H)
    z.Outline().NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        z.Outline().Append(IU(x), IU(y))
    z.SetAssignedPriority(priority)
    z.SetZoneName(name)
    z.SetLocalClearance(IU(0.2))
    z.SetMinThickness(IU(0.2))
    z.SetThermalReliefGap(IU(0.2))
    z.SetThermalReliefSpokeWidth(IU(0.3))
    board.Add(z)
    return z


def rules(board):
    bds = board.GetDesignSettings()
    bds.SetBoardThickness(IU(mech.PCB_T))
    bds.m_MinClearance, bds.m_TrackMinWidth = IU(0.09), IU(0.1)
    bds.m_ViasMinSize, bds.m_ViasMinAnnularWidth, bds.m_MinThroughDrill = IU(0.4), IU(0.1), IU(0.2)
    # 0.15 mm hole clearance: the USB4105 land pattern has 0.19 mm between its signal pads and locating holes
    # 0.25 mm copper to edge: the router keeps about 0.26 mm
    bds.m_HoleClearance, bds.m_HoleToHoleMin, bds.m_CopperEdgeClearance = IU(0.15), IU(0.25), IU(0.25)
    PCB.with_suffix(".kicad_dru").write_text(
        '(version 1)\n'
        '(rule "USB-C shell pads sit at the board edge by design"\n'
        '  (condition "A.Reference == \'J1\'")\n'
        '  (constraint edge_clearance (min 0.1mm)))\n')
    ns = bds.m_NetSettings
    ns.ClearNetclasses()                 # the project file keeps the previous run's classes
    ns.ClearNetclassPatternAssignments()
    default = ns.GetDefaultNetclass()
    # Power: 0.2 mm is the widest track that enters the P4's 0.2 mm pads at 0.35 mm pitch with 0.1 mm clearance.
    # The router's automatic neck-down is off (it produced 0.095 mm tracks), so the class width must fit the pads.
    # 0.09 mm clearance, 0.1 mm tracks and 0.4 mm vias: with less, a track cannot pass a via next to a 0.35 mm
    # pitch pad, and the P4's fan-out does not complete. To be checked against the fabricator's limits.
    for nc, clearance, track, via, drill in ((default, 0.09, 0.1, 0.4, 0.2), (pcbnew.NETCLASS("Power"), 0.09, 0.2, 0.45, 0.2)):
        nc.SetClearance(IU(clearance))
        nc.SetTrackWidth(IU(track))
        nc.SetViaDiameter(IU(via))
        nc.SetViaDrill(IU(drill))
        if nc is not default:
            ns.SetNetclass(nc.GetName(), nc)
    for net in sorted(POWER_NETS):
        ns.SetNetclassPatternAssignment(f"*{net}", "Power")


# ---------- placement ----------

class Placer:
    def __init__(self, comps, nets, info, geo):
        self.comps, self.nets, self.info, self.geo = comps, nets, info, geo
        self.pos, self.boxes, self.used = {}, np.zeros((0, 4)), collections.Counter()
        self.netof = {(ref, pin): net for net, nodes in nets.items() for ref, pin in nodes}
        self.npads = {ref: sum(len(v) for v in geo[ref][0][1].values()) for ref in comps}
        self.keep = np.array(KEEPOUT)

    def box(self, ref, x, y, rot):
        (x0, y0, x1, y1), m = self.geo[ref][rot][0], self.margin(ref)
        return x + x0 - m, y + y0 - m, x + x1 + m, y + y1 + m

    def margin(self, ref):
        if ref == "U1":
            return 3.0      # room for the QFN fan-out tracks and their vias
        if ref == "P1":
            return 1.5      # window in the rear housing
        return 0.5 if self.npads[ref] > 8 else 0.3    # 0.3: a via and a track fit between two 0402 parts

    def free(self, ref, x, y, rot):
        if ref in BACK:
            return True
        b = self.box(ref, x, y, rot)
        if ref not in FIXED and (b[0] < EDGE or b[1] < EDGE or b[2] > W - EDGE or b[3] > H - EDGE):
            return False
        for rects in (self.boxes, self.keep if ref not in FIXED else self.keep[:0]):
            if len(rects) and np.any((rects[:, 0] < b[2]) & (rects[:, 2] > b[0]) & (rects[:, 1] < b[3]) & (rects[:, 3] > b[1])):
                return False
        return True

    def put(self, ref, x, y, rot):
        self.pos[ref] = (x, y, rot)
        if ref not in BACK:     # parts on the back take no room on the part side
            self.boxes = np.vstack([self.boxes, self.box(ref, x, y, rot)])

    def pad_xy(self, ref, pin, k=0):
        x, y, rot = self.pos[ref]
        pts = self.geo[ref][rot][1][pin]
        px, py = pts[min(k, len(pts) - 1)]
        return x + px, y + py

    def anchor(self, ref):
        """(pin of ref, (ref, pin) to sit next to) or None while nothing it connects to is placed."""
        sheet, group, _ = self.info[ref]
        best = None
        for pin in self.geo[ref][0][1]:
            net = self.netof.get((ref, pin))
            if not net or short(net) == "GND" or net.startswith("unconnected"):
                continue
            placed = [(r, p) for r, p in self.nets[net] if r in self.pos and r != ref and NEAR.get(ref, r) == r]
            if not placed:
                continue
            rail = short(net) in RAILS or len(self.nets[net]) > 8
            if rail:    # decoupling: the biggest part of the same group, else of the same sheet, least-loaded pad
                rank = lambda rp: (self.info[rp[0]][:2] != (sheet, group), self.info[rp[0]][0] != sheet,
                                   -self.npads[rp[0]], self.used[rp], rp)
                cand = [rp for rp in placed if self.npads[rp[0]] >= 5]
                if not cand:
                    continue
            else:       # signal: the biggest part on the net
                rank = lambda rp: (-self.npads[rp[0]], rp)
                cand = placed
            target = min(cand, key=rank)
            score = (rail, len(self.nets[net]), -self.npads[target[0]])
            if best is None or score < best[0]:
                best = (score, pin, target)
        if best is None:
            return None
        return best[1], best[2]

    def place(self, ref, pin, target):
        """Next to the pad target = (ref, pin), or at the free spot nearest to the point target = (x, y)."""
        point = not isinstance(target[0], str)
        ax, ay = target if point else self.pad_xy(*target)
        if not point:
            self.used[target] += 1
        r = 0.0 if point else 3.0 if ref.startswith("TP") else 0.6    # test pads stay out of the fan-out area
        while r < 70:
            best = None
            for k in range(max(8, int(2 * math.pi * r / 0.35))):
                a = 2 * math.pi * k / max(8, int(2 * math.pi * r / 0.35))
                x, y = round((ax + r * math.cos(a)) * 20) / 20, round((ay + r * math.sin(a)) * 20) / 20
                for rot in (0, 90, 180, 270):
                    if not self.free(ref, x, y, rot):
                        continue
                    px, py = self.geo[ref][rot][1][pin][0]
                    d = math.hypot(x + px - ax, y + py - ay)
                    if best is None or d < best[0]:
                        best = (d, x, y, rot)
            if best:
                return self.put(ref, *best[1:])
            r += 0.35
        raise SystemExit(f"no room for {ref}")

    def run(self):
        clash = []
        for ref, (x, y, rot) in FIXED.items():
            if not self.free(ref, x, y, rot):
                clash.append((ref, tuple(round(float(v), 2) for v in self.box(ref, x, y, rot))))
            self.put(ref, x, y, rot)
        if clash and STRICT_FIXED:
            raise SystemExit(f"fixed parts overlap an earlier one: {clash}")
        todo = [r for r in self.comps if r not in self.pos]
        # Test pads of P4 pins go straight after the ICs, right outside the fan-out area: a short straight route
        # instead of a long one through the ring of passives. Other test pads come last.
        own = lambda r: r.startswith("TP") and any(n == "U1" for n, _ in self.nets[self.netof[(r, "1")]])
        order = lambda r: (r.startswith("TP") and not own(r), self.npads[r] < 3 and not own(r), -self.npads[r], r)
        while todo:
            ready = [(r, self.anchor(r)) for r in sorted(todo, key=order)]
            ready = [(r, a) for r, a in ready if a]
            if not ready:
                if any(r not in LAST for r in todo):
                    raise SystemExit(f"no placed neighbour for {todo}")
                for ref in todo:
                    self.place(ref, "1", LAST[ref])
                break
            first = order(ready[0][0])[:2]      # one class of parts per pass: ICs, then passives, then test pads
            for ref in [r for r, _ in ready if order(r)[:2] == first]:
                self.place(ref, *self.anchor(ref))  # picked again: the pads' load changes within the pass
                todo.remove(ref)
        return self.pos


def plan_fanout(board, nets=("GND", "3V3")):
    """[(net, pad x, pad y, via x, via y, side)]: a via next to every pad of the plane nets, so the router only has
    to route signals. Fine-pitch pads (under 0.35 mm) are left to the router; pads of 1.25 mm and more on parts
    with more than 8 pads (exposed pads, module ground pads) get the via in their centre."""
    pads = [(fp, p) for fp in board.GetFootprints() for p in fp.Pads()]
    rect = lambda p: (MM(p.GetBoundingBox().GetLeft()), MM(p.GetBoundingBox().GetTop()),
                      MM(p.GetBoundingBox().GetRight()), MM(p.GetBoundingBox().GetBottom()))
    rects = np.array([rect(p) for _, p in pads])
    u1 = next(fp for fp in board.GetFootprints() if fp.GetReference() == "U1").GetPosition()
    halo = (MM(u1.x) - 8.6, MM(u1.y) - 8.6, MM(u1.x) + 8.6, MM(u1.y) + 8.6)     # the P4's fan-out area stays free
    blocked = [halo, KEEPOUT[-1]]
    plan, fine = [], []

    def gap(x, y, skip):        # distance from a point to the nearest pad rectangle other than `skip`
        dx = np.maximum(np.maximum(rects[:, 0] - x, x - rects[:, 2]), 0)
        dy = np.maximum(np.maximum(rects[:, 1] - y, y - rects[:, 3]), 0)
        d = np.hypot(dx, dy)
        if skip < len(d):
            d[skip] = 9
        return d.min()

    def ok(x, y, i):
        if not (0.7 < x < W - 0.7 and 0.7 < y < H - 0.7) or any(math.hypot(x - hx, y - hy) < 2.7 for hx, hy in mech.HOLES):
            return False
        if any(b[0] < x < b[2] and b[1] < y < b[3] for b in blocked):
            return False
        return gap(x, y, i) >= 0.36 and all(math.hypot(x - q[3], y - q[4]) >= 0.6 for q in plan)

    for i, (fp, pad) in enumerate(pads):
        if fp.GetReference() == "U1" and pad.GetNetname() == "VDD_HP":
            # Core supply: its four pins sit on four sides of the P4. Each gets a via just inside the pad row,
            # into a small VDD_HP area on In2.Cu under the chip (see cmd_place), which ties them together.
            x0, y0, x1, y1 = (float(v) for v in rects[i])
            cx, cy, fx, fy = (x0 + x1) / 2, (y0 + y1) / 2, MM(fp.GetPosition().x), MM(fp.GetPosition().y)
            dx, dy = cx - fx, cy - fy
            if min(abs(dx), abs(dy)) > 3.9:     # pad next to a corner: via in the free corner between the pad rows
                inward, width = (fx + math.copysign(4.15, dx), fy + math.copysign(4.15, dy)), 0.1
            else:                               # 4.1 mm from the centre: between the pad row (4.55) and the EP (3.75)
                inward, width = ((fx + math.copysign(4.1, dx), cy) if abs(dx) > abs(dy) else (cx, fy + math.copysign(4.1, dy))), 0.2
            plan.append(("VDD_HP", round(cx, 3), round(cy, 3), round(inward[0], 3), round(inward[1], 3), "F", width))
            continue
        if pad.GetNetname() not in nets or pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            continue
        side = "F" if pad.IsOnLayer(pcbnew.F_Cu) else "B"     # the stub is on the pad's own side
        x0, y0, x1, y1 = rects[i]
        cx, cy, w, h = round(float(x0 + x1) / 2, 3), round(float(y0 + y1) / 2, 3), float(x1 - x0), float(y1 - y0)
        if min(w, h) < 0.35:
            fine.append((fp, pad.GetNetname(), cx, cy, w, h))
            continue
        if min(w, h) >= 1.25 and fp.GetPadCount() > 8 and side == "F":
            plan.append((pad.GetNetname(), cx, cy, cx, cy, side))
            continue
        ox, oy = cx - MM(fp.GetPosition().x), cy - MM(fp.GetPosition().y)
        base = math.atan2(oy, ox) if abs(ox) + abs(oy) > 0.05 else 0.0
        for extra, turn in ((e, s) for e in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5) for s in (0, 90, -90, 180, 45, -45, 135, -135)):
            a = base + math.radians(turn)
            reach = min(w / 2 / abs(math.cos(a)) if abs(math.cos(a)) > 1e-6 else 99,
                        h / 2 / abs(math.sin(a)) if abs(math.sin(a)) > 1e-6 else 99)
            d = reach + 0.43 + extra
            x, y = round(cx + d * math.cos(a), 3), round(cy + d * math.sin(a), 3)
            if ok(x, y, i) and all(gap(cx + s * math.cos(a), cy + s * math.sin(a), i) >= 0.24 for s in np.arange(reach, d, 0.1)):
                plan.append((pad.GetNetname(), cx, cy, x, y, side))
                break
    # Fine-pitch pads (P4 supply pins, FFC and USB-C pins): the router does not connect these to a plane on its
    # own. One via per run of neighbouring pads of the same net, straight out from the pad row; two vias that
    # would trap the pin between them are pushed 0.1 mm apart.
    runs = []
    for fp, net, cx, cy, w, h in fine:
        fx, fy = MM(fp.GetPosition().x), MM(fp.GetPosition().y)
        n = (0.0, math.copysign(1, cy - fy)) if w < h else (math.copysign(1, cx - fx), 0.0)
        last = runs[-1] if runs else None
        if last and last["fp"] is fp and last["net"] == net and last["n"] == n and math.hypot(cx - last["pads"][-1][0], cy - last["pads"][-1][1]) < 0.55:
            last["pads"].append((cx, cy))
        else:
            runs.append(dict(fp=fp, net=net, n=n, pads=[(cx, cy)], reach=max(w, h) / 2 + 0.6))
    spots = []
    for r in runs:
        mx, my = sum(q[0] for q in r["pads"]) / len(r["pads"]), sum(q[1] for q in r["pads"]) / len(r["pads"])
        spots.append([mx + r["n"][0] * r["reach"], my + r["n"][1] * r["reach"]])
    for i, a in enumerate(spots):
        for j in range(i + 1, len(spots)):
            b, n = spots[j], runs[i]["n"]
            if runs[i]["fp"] is runs[j]["fp"] and runs[j]["n"] == n and 0.6 <= math.hypot(a[0] - b[0], a[1] - b[1]) < 0.95:
                s = 0.1 if (b[0] - a[0]) * n[1] + (b[1] - a[1]) * n[0] > 0 else -0.1     # along the pad row
                a[0], a[1], b[0], b[1] = a[0] - s * abs(n[1]), a[1] - s * abs(n[0]), b[0] + s * abs(n[1]), b[1] + s * abs(n[0])
    for r, (sx, sy) in zip(runs, spots):
        n = r["n"]
        for out, side in ((o, s) for o in (0.0, 0.35, 0.7, 1.05) for s in (0.0, 0.15, -0.15, 0.3, -0.3)):
            x, y = round(sx + n[0] * out + abs(n[1]) * side, 3), round(sy + n[1] * out + abs(n[0]) * side, 3)
            if 0.7 < x < W - 0.7 and 0.7 < y < H - 0.7 and gap(x, y, len(rects)) >= 0.33 \
                    and all(math.hypot(x - q[3], y - q[4]) >= 0.6 for q in plan):
                plan.extend((r["net"], px, py, x, y, "F") for px, py in r["pads"])
                break
    return plan


def apply_fanout(board, plan):
    """Adds the vias and stubs of `plan` that are not on the board yet (the session import can drop them)."""
    have = {(v.GetPosition().x, v.GetPosition().y) for v in board.GetTracks() if v.GetClass() == "PCB_VIA"}
    stubs = {(t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) for t in board.GetTracks() if t.GetClass() != "PCB_VIA"}
    for net, cx, cy, vx, vy, side, *rest in plan:
        a, b = P(cx, cy), P(vx, vy)
        if (b.x, b.y) not in have:
            have.add((b.x, b.y))
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(b)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetWidth(IU(0.4))
            via.SetDrill(IU(0.2))
            via.SetNet(board.FindNet(net))
            via.SetLocked(True)
            board.Add(via)
        if (cx, cy) != (vx, vy) and (a.x, a.y, b.x, b.y) not in stubs and (b.x, b.y, a.x, a.y) not in stubs:
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(a)
            track.SetEnd(b)
            track.SetWidth(IU(rest[0] if rest else 0.2))
            track.SetLayer(pcbnew.F_Cu if side == "F" else pcbnew.B_Cu)
            track.SetNet(board.FindNet(net))
            track.SetLocked(True)
            board.Add(track)


def bridge_usb(board):
    """Joins J1's two D+ pads (A6, B6) below the pad row and its two D- pads (B7, A7) above it, as locked tracks.
    The four pads alternate in one row, so one pair has to go round each side. Left to the router, a VBUS track
    under the row shut A6 in on three runs of 2026-11-14."""
    j1 = board.FindFootprintByReference("J1")
    pad = {p.GetNumber(): p for p in j1.Pads()}
    have = {(t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) for t in board.GetTracks() if t.GetClass() != "PCB_VIA"}
    for a, b, side in (("A6", "B6", 1), ("B7", "A7", -1)):      # side: +1 on the connector's side of the row, -1 inside
        (ax, y), bx = (MM(pad[a].GetPosition().x), MM(pad[a].GetPosition().y)), MM(pad[b].GetPosition().x)
        half = MM(max(pad[a].GetSize().x, pad[a].GetSize().y)) / 2
        y1, y2 = y + side * (half + 0.08), y + side * (half + 0.26)        # 0.21 mm from the pad between them
        pts = [(ax, y), (ax, y1), (ax + 0.18, y2), (bx - 0.18, y2), (bx, y1), (bx, y)]
        for s, e in zip(pts, pts[1:]):
            s, e = P(*s), P(*e)
            if (s.x, s.y, e.x, e.y) in have:
                continue
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(s), track.SetEnd(e), track.SetWidth(IU(0.1)), track.SetLayer(pcbnew.F_Cu)
            track.SetNet(pad[a].GetNet()), track.SetLocked(True)
            board.Add(track)


def populate(board, fps, comps, nets, pos, info, back=()):
    """Puts the footprints on the board with the symbol's fields, path and nets, so schematic parity holds."""
    netof = {(ref, pin): net for net, nodes in nets.items() for ref, pin in nodes}
    for ref, c in comps.items():
        fp, (x, y, rot) = fps[ref], pos[ref]
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetSheetname(f"/{c['sheet']}/")
        fp.SetSheetfile(c["sheetfile"])
        fp.SetDNP(c["dnp"])
        fp.SetExcludedFromBOM(False)            # as in the schematic, whatever the library footprint says
        for name, text in c["fields"].items():  # the parity check compares every symbol field
            if name != "Footprint":
                fp.SetField(name, text)
                fp.GetField(name).SetVisible(False)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        fp.Reference().SetLayer(pcbnew.F_Fab)   # designators go on the assembly drawing, not on silkscreen
        fp.Reference().SetPosition(P(x, y))
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(IU(0.4), IU(0.4)))
        fp.Reference().SetTextThickness(IU(0.06))
        fp.Value().SetVisible(False)
        board.Add(fp)
        if ref in back:         # after Add: flipping a footprint that is not on a board crashes pcbnew
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in fp.Pads():
            net = netof.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(board.FindNet(net))


def holes(board, positions):
    for i, (x, y) in enumerate(positions, 1):
        fp = load_footprint("MountingHole:MountingHole_2.2mm_M2")
        fp.SetReference(f"H{i}")
        fp.SetBoardOnly(True)
        fp.SetPosition(P(x, y))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)


def logo(board):
    fp = load_footprint(LOGO[0])
    fp.SetReference("LOGO1")
    fp.SetBoardOnly(True)
    fp.SetPosition(P(*LOGO[1:]))
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    board.Add(fp)
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)     # after Add, as in populate()


def cmd_place():
    comps, nets = read_netlist()
    info = sheet_groups()
    PCB.unlink(missing_ok=True)
    board = pcbnew.NewBoard(str(PCB))
    board.SetCopperLayerCount(4)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)      # as a signal layer the router shreds the 3V3 plane
    rules(board)
    outline(board)
    for name in nets:
        board.Add(pcbnew.NETINFO_ITEM(board, name))
    fps, geo = {}, {}
    for ref, c in comps.items():
        fp = fps[ref] = load_footprint(c["fp"])
        geo[ref] = geometry(fp)
    if FIXED["J1"][1] is None:      # USB-C: put the footprint's "PCB Edge" line on the bottom edge
        fps["J1"].SetOrientationDegrees(0)      # geometry() leaves the footprint rotated
        edge = [g.GetBoundingBox().Centre().y for g in fps["J1"].GraphicalItems()
                if g.GetLayer() == pcbnew.Dwgs_User and g.GetClass() == "PCB_SHAPE"]
        assert len(edge) == 1, "USB-C footprint: expected one PCB Edge line"
        FIXED["J1"] = (FIXED["J1"][0], round(H - MM(edge[0]), 3), 0)
    pos = Placer(comps, nets, info, geo).run()
    # The receptacle stands on the board's tab, mech.USB_TAB[1] further out. The placer sees it at the old bottom
    # edge, so the parts around it stay where they were routed (moving it re-placed 35 parts on 2026-11-14) and
    # the strip between the two positions stays free for the tracks to its pads.
    pos["J1"] = (pos["J1"][0], round(pos["J1"][1] + mech.USB_TAB[1], 3), pos["J1"][2])
    populate(board, fps, comps, nets, pos, info, BACK)
    holes(board, mech.HOLES)
    logo(board)
    zone(board, "GND", pcbnew.In1_Cu, name="GND plane")
    zone(board, "3V3", pcbnew.In2_Cu, name="3V3 plane")
    ux, uy, _ = pos["U1"]       # inside the P4's pad rows there are only ground vias, so this area cuts no 3V3 via off
    zone(board, "VDD_HP", pcbnew.In2_Cu, box=(ux - 4.45, uy - 4.45, ux + 4.45, uy + 4.45), priority=1, name="VDD_HP under U1")
    plan = plan_fanout(board)
    apply_fanout(board, plan)
    bridge_usb(board)
    (OUT / "fanout.json").write_text(json.dumps(plan))
    print(f"plane fan-out: {len(plan)} vias")
    pcbnew.SaveBoard(str(PCB), board)
    pcbnew.GetSettingsManager().SaveProject()
    shutil.copy(PCB, OUT / "placed.kicad_pcb")
    dsn = OUT / f"{sch.PROJECT}.dsn"
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    # The router gets 0.093 mm clearance: a little margin over KiCad's 0.09 mm for rounding at arcs and vias.
    tune_dsn(dsn, pos["U1"])
    auto = len(comps) - len(FIXED)
    print(f"placed {len(comps)} parts ({len(FIXED)} fixed, {auto} automatic), {len(nets)} nets -> {PCB.relative_to(sch.ROOT)}")


def tune_dsn(dsn, u1, keepout=True):
    """Router-only changes to the exported DSN: clearance margin, and no new vias under the P4.

    The router gets 0.093 mm clearance, a little over KiCad's 0.09 mm, for rounding at arcs and vias. Without the
    via keep-out it drops signal vias between the P4's pad rows and its exposed pad, which cuts the VDD_HP area
    on In2.Cu into pieces. The keep-out is not in the KiCad board: the fan-out vias there are intended.
    keepout=False drops it for a last pass: a pad whose way out is blocked may then leave inwards. Check the
    DRC report for VDD_HP afterwards.
    """
    text = dsn.read_text()
    assert "(clearance 90)" in text or "(clearance 90.1)" in text
    text = text.replace("(clearance 90)", "(clearance 93)").replace("(clearance 90.1)", "(clearance 93)")
    if not keepout:
        return dsn.write_text(text)
    x0, y0, x1, y1 = ((u1[0] - 4.45) * 1000, -(u1[1] + 4.45) * 1000, (u1[0] + 4.45) * 1000, -(u1[1] - 4.45) * 1000)
    keep = "".join(f'    (via_keepout "" (rect {layer} {x0:g} {y0:g} {x1:g} {y1:g}))\n' for layer in ("F.Cu", "B.Cu"))
    marker = "    (via "       # the first one is the via list of the structure section
    assert marker in text and text.index(marker) < text.index("(placement")
    dsn.write_text(text.replace(marker, keep + marker, 1))


def freerouting(dsn, ses, passes):
    log = OUT / "freerouting.log"
    with log.open("a") as f:
        subprocess.run([str(JAVA), "-jar", str(JAR), "-de", str(dsn), "-do", str(ses), "-mp", passes,
                        "--gui.enabled=false", "--api_server.enabled=false", "--router.automatic_neckdown=false",
                        "--router.scoring.via_costs=25",
                        "--usage_and_diagnostic_data.disable_analytics=true"], stdout=f, stderr=subprocess.STDOUT, check=False)
    if not ses.exists():
        raise SystemExit(f"Freerouting wrote no session file, see {log}")


def cmd_finish(passes="15", free=""):
    """Second router session on the routed board: the first one stops with a few connections it keeps ripping up."""
    dsn, ses = OUT / f"{sch.PROJECT}.dsn", OUT / f"{sch.PROJECT}.ses"
    shutil.copy(OUT / "placed.kicad_pcb", PCB)
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise SystemExit("session import failed")
    apply_fanout(board, json.loads((OUT / "fanout.json").read_text()))
    bridge_usb(board)
    pcbnew.ExportSpecctraDSN(board, str(dsn))
    u1 = board.FindFootprintByReference("U1").GetPosition()
    tune_dsn(dsn, (MM(u1.x), MM(u1.y)), keepout=not free)
    ses.unlink()
    freerouting(dsn, ses, passes)
    cmd_import()


def cmd_route(passes="40"):
    dsn, ses = OUT / f"{sch.PROJECT}.dsn", OUT / f"{sch.PROJECT}.ses"
    ses.unlink(missing_ok=True)
    (OUT / "freerouting.log").unlink(missing_ok=True)
    freerouting(dsn, ses, passes)
    cmd_import()


def cmd_import():
    """Session file -> board: tracks and vias, plane fan-out, outer GND pours, zone fill."""
    shutil.copy(OUT / "placed.kicad_pcb", PCB)     # start again from the unrouted board the DSN was made from
    board = pcbnew.LoadBoard(str(PCB))
    if not pcbnew.ImportSpecctraSES(board, str(OUT / f"{sch.PROJECT}.ses")):
        raise SystemExit("session import failed")
    apply_fanout(board, json.loads((OUT / "fanout.json").read_text()))
    bridge_usb(board)
    for ref in ("J1", "P1"):    # USB-C GND pins, contact part's GND pins: two thermal spokes do not fit
        for pad in board.FindFootprintByReference(ref).Pads():
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    tracks = board.GetTracks()
    vias = sum(t.GetClass() == "PCB_VIA" for t in tracks)
    narrow = [t for t in tracks if t.GetClass() != "PCB_VIA" and t.GetWidth() < IU(0.1)]
    for t in narrow:    # the router necks down below the 0.1 mm minimum at some pads
        t.SetWidth(IU(0.1))
    # The router leaves a few segments of a micron or two, which KiCad reports as dangling. Removed after the last
    # GetTracks(): pcbnew's Python track list is unusable once an item has been removed.
    stubs = [t for t in tracks if t.GetClass() != "PCB_VIA" and t.GetLength() < IU(0.005)]
    for t in stubs:
        board.Remove(t)
    zone(board, "GND", pcbnew.F_Cu, name="GND pour")
    zone(board, "GND", pcbnew.B_Cu, name="GND pour")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)
    print(f"imported {len(tracks) - vias - len(stubs)} track segments, {vias} vias, widened {len(narrow)} segments "
          f"to 0.1 mm, removed {len(stubs)} stubs under 5 um")


def cmd_fab():
    """Fabrication and review outputs in out/fab. Draft data: do not order boards from it."""
    fab = sch.ROOT / "out" / "fab"
    (fab / "gerber").mkdir(parents=True, exist_ok=True)
    cli = lambda *a: subprocess.run(["kicad-cli", "pcb", *a, str(PCB)], check=True, stdout=subprocess.DEVNULL)
    cli("export", "gerbers", "-o", str(fab / "gerber"), "--subtract-soldermask", "-l",
        "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Fab,Edge.Cuts")
    cli("export", "drill", "-o", str(fab / "gerber") + "/", "--excellon-separate-th", "--generate-map", "--map-format", "pdf")
    cli("export", "pos", "-o", str(fab / "maratus-core-pos.csv"), "--format", "csv", "--units", "mm", "--side", "front",
        "--exclude-dnp")
    # Espressif's footprints point at ${KICAD9_3RD_PARTY}/3dmodels/com_github_espressif_kicad-libraries/...; give
    # kicad-cli that path through a link to the submodule.
    third = sch.ROOT / "out" / "3rdparty"
    (third / "3dmodels").mkdir(parents=True, exist_ok=True)
    link = third / "3dmodels" / "com_github_espressif_kicad-libraries"
    if not link.exists():
        link.symlink_to(sch.ROOT / "hardware" / "lib" / "espressif" / "3dmodels")
    models = ("-D", f"KICAD9_3RD_PARTY={third}", "--subst-models", "--no-dnp")
    cli("export", "step", "-f", "-o", str(sch.ROOT / "mechanical" / "core" / "maratus-core-pcb.step"), *models)
    cli("export", "glb", "-f", "-o", str(OUT / "board.glb"), *models, "--include-tracks", "--include-pads",
        "--include-silkscreen")
    # Parts whose 3D model is missing, as boxes for tools/assembly_blend.py: ref -> x, y, rotation, w, h, height.
    board = pcbnew.LoadBoard(str(PCB))
    boxes = {}
    for ref, (w, h, z) in NO_MODEL.items():
        fp = board.FindFootprintByReference(ref)
        boxes[ref] = (MM(fp.GetPosition().x), MM(fp.GetPosition().y), fp.GetOrientationDegrees(), w, h, z)
    (OUT / "placeholders.json").write_text(json.dumps(boxes))
    for side in ("top", "bottom"):
        cli("render", "-o", str(fab / f"maratus-core-{side}.png"), "--side", side, "-w", "1500", "-h", "1900",
            "--background", "opaque", "--quality", "basic", *models[:2])
    print(f"outputs in {fab.relative_to(sch.ROOT)} and mechanical/core/maratus-core-pcb.step")


if __name__ == "__main__":
    cmd = {"place": cmd_place, "route": cmd_route, "finish": cmd_finish, "import": cmd_import, "fab": cmd_fab}.get(sys.argv[1] if len(sys.argv) > 1 else "")
    if not cmd:
        sys.exit(__doc__)
    cmd(*sys.argv[2:])
