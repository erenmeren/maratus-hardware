#!/usr/bin/env python3
"""Generate the Maratus Core KiCad schematic from the descriptions in tools/sheets/.

    python3 tools/sch.py gen            # rewrite hardware/core/*.kicad_sch and the maratus symbol lib
    python3 tools/sch.py pins LIB:NAME  # pin table of a library symbol

The .kicad_sch files are generated output. Edit tools/sheets/<sheet>.py and regenerate;
edits made in the KiCad GUI are lost on the next run.

Style: every pin gets a short stub and a label (or a GND symbol / no-connect flag). Parts are
connected by net name, not by drawn wires. Rails are global labels, nets that leave a sheet are
hierarchical labels, everything else is a local label.

Checks done here (the generator fails instead of writing a wrong file):
- every pin of every part is assigned a net or NC, by pin number or pin name
- pin keys that do not exist on the symbol are rejected
- a footprint must exist in a footprint library and have a pad for every symbol pin number
  (or be "" = not chosen yet)
- a local net used on one pin only is rejected (typo guard)
- every hierarchical label of a sheet is used, and every cross-sheet P4 net exists in the pin map
"""
import collections
import copy
import csv
import functools
import importlib
import math
import os
import pathlib
import re
import subprocess
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "hardware" / "core"
PROJECT = "maratus-core"
NS = uuid.UUID("6d617261-7475-732d-636f-726500000001")
KICAD_SYM = pathlib.Path(os.environ.get("KICAD10_SYMBOL_DIR", "/usr/share/kicad/symbols"))
KICAD_FP = pathlib.Path(os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints"))
SYM_LIBS = {"PCM_Espressif": ROOT / "hardware/lib/espressif/symbols/Espressif.kicad_sym",
            "maratus": ROOT / "hardware/lib/maratus/maratus.kicad_sym"}
FP_LIBS = {"PCM_Espressif": ROOT / "hardware/lib/espressif/footprints/Espressif.pretty",
           "maratus": ROOT / "hardware/lib/maratus/maratus.pretty"}

SHEETS = ["power", "p4-core", "wifi", "display", "ethernet", "expansion", "misc"]  # CLAUDE.md order
RAILS = {"3V3", "5V_SYS", "VIN", "VBUS", "V_ACC", "VDD_HP", "VDD_FLASH", "VDD_PSRAM", "VDD_MIPI"}
NC = "NC"
I, O, B = "input", "output", "bidirectional"

# Nets that cross sheets: (net, sheet A, label shape on A, sheet B, label shape on B)
LINKS = [(n, "p4-core", a, s, b) for s, rows in {
    "power": [("ACC_PWR_EN", O, I), ("ACC_PWR_FLT_N", I, O), ("PWR_SRC_ST", I, O), ("VSYS_SENSE", I, O),
              ("USBC_CC1_SENSE", I, O), ("USBC_CC2_SENSE", I, O), ("P4_EN", I, O)],
    "wifi": [("SDIO_CLK", O, I), ("SDIO_CMD", B, B), ("SDIO_D0", B, B), ("SDIO_D1", B, B), ("SDIO_D2", B, B),
             ("SDIO_D3", B, B), ("C5_EN", O, I), ("C5_BOOT", O, I), ("C5_U0RXD", O, I), ("C5_U0TXD", I, O)],
    "ethernet": [("RMII_REF_CLK", I, O), ("RMII_TX_EN", O, I), ("RMII_TXD0", O, I), ("RMII_TXD1", O, I),
                 ("RMII_CRS_DV", I, O), ("RMII_RXD0", I, O), ("RMII_RXD1", I, O), ("ETH_MDC", O, I),
                 ("ETH_MDIO", B, B), ("ETH_PHY_RST_N", O, I), ("ETH_REFCLK_ALT", O, I)],
    "display": [("DSI_CLK_P", O, I), ("DSI_CLK_N", O, I), ("DSI_D0_P", B, B), ("DSI_D0_N", B, B),
                ("DSI_D1_P", O, I), ("DSI_D1_N", O, I), ("LCD_RST_N", O, I), ("LCD_BL_PWM", O, I),
                ("TP_RST_N", O, I), ("TP_INT", I, O), ("I2C0_SDA", B, B), ("I2C0_SCL", B, B)],
    "misc": [("USBC_DP", B, B), ("USBC_DN", B, B), ("BUZZER_PWM", O, I), ("SERVICE_BTN_N", I, O),
             ("CSI_CLK_P", I, O), ("CSI_CLK_N", I, O), ("CSI_D0_P", I, O), ("CSI_D0_N", I, O),
             ("CSI_D1_P", I, O), ("CSI_D1_N", I, O)],
    "expansion": [("ACC_ID_ADC", I, O), ("ACC_IO1", B, B), ("ACC_IO2", B, B), ("ACC_INT_N", B, B),
                  ("ACC_USB_DP", B, B), ("ACC_USB_DN", B, B)],
}.items() for n, a, b in rows] + [
    # Not P4 pin nets, so not in the gpio map. J1 sits on `power`; its data pair goes to `misc`.
    ("USBC_CONN_DP", "power", B, "misc", B), ("USBC_CONN_DN", "power", B, "misc", B),
    # MDI pairs, names from design-spec section 7.
    ("ETH_TX_P", "ethernet", B, "expansion", B), ("ETH_TX_N", "ethernet", B, "expansion", B),
    ("ETH_RX_P", "ethernet", B, "expansion", B), ("ETH_RX_N", "ethernet", B, "expansion", B),
]

# Common footprints (KiCad standard libraries)
R0402, C0402 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric"
C0603, C0805 = "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric"
TP_PAD = "TestPoint:TestPoint_Pad_D1.0mm"


# ---------- S-expressions ----------

TOKEN = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')


def parse(text):
    stack = [[]]
    for t in TOKEN.findall(text):
        if t == "(":
            stack[-1].append([])
            stack.append(stack[-1][-1])
        elif t == ")":
            stack.pop()
        else:
            stack[-1].append(t)
    return stack[0][0]


def dump(x):
    return x if isinstance(x, str) else "(" + " ".join(dump(i) for i in x) + ")"


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def uq(a):
    return re.sub(r"\\(.)", r"\1", a[1:-1]) if a.startswith('"') else a


def kids(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def uid(*key):
    return str(uuid.uuid5(NS, "/".join(key)))


def num(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


# ---------- symbol libraries ----------

@functools.lru_cache(None)
def load_lib(nick):
    path = SYM_LIBS.get(nick, KICAD_SYM / f"{nick}.kicad_sym")
    return {uq(c[1]): c for c in kids(parse(path.read_text()), "symbol")}


@functools.lru_cache(None)
def lib_symbol(lib_id):
    """Library symbol with `extends` resolved, named LIB:NAME as KiCad stores it in a schematic."""
    nick, name = lib_id.split(":", 1)
    lib = load_lib(nick)
    if name not in lib:
        raise SystemExit(f"symbol {lib_id} not found")

    def flat(n):
        sym = copy.deepcopy(lib[n])
        ext = kids(sym, "extends")
        if not ext:
            return sym
        base = flat(uq(ext[0][1]))
        bname = uq(base[1])
        props = {c[1]: c for c in kids(sym, "property")}
        out = [base[0], q(n)]
        for c in base[2:]:
            if isinstance(c, list) and c[0] == "property":
                c = props.pop(c[1], c)
            elif isinstance(c, list) and c[0] == "symbol":
                if props:  # child-only properties go before the first unit
                    out += props.values()
                    props = {}
                c[1] = q(n + uq(c[1])[len(bname):])
            out.append(c)
        return out

    sym = flat(name)
    sym[1] = q(lib_id)
    return sym


Pin = collections.namedtuple("Pin", "num name etype x y ang unit hidden")


@functools.lru_cache(None)
def pins_of(lib_id):
    name, out = lib_id.split(":", 1)[1], []
    for unit_sym in kids(lib_symbol(lib_id), "symbol"):
        unit, style = map(int, uq(unit_sym[1])[len(name) + 1:].split("_"))
        if style > 1:
            continue
        for p in kids(unit_sym, "pin"):
            at = kids(p, "at")[0]
            hidden = "hide" in p or bool(kids(p, "hide"))
            out.append(Pin(uq(kids(p, "number")[0][1]), uq(kids(p, "name")[0][1]), p[1], float(at[1]),
                           float(at[2]), int(float(at[3])) if len(at) > 3 else 0, unit, hidden))
    return out


def props_of(lib_id):
    return {uq(p[1]): p for p in kids(lib_symbol(lib_id), "property")}


@functools.lru_cache(None)
def footprint_pads(fp):
    """Pad names of a footprint, or None if the footprint does not exist."""
    lib, name = fp.split(":", 1)
    path = FP_LIBS.get(lib, KICAD_FP / f"{lib}.pretty") / f"{name}.kicad_mod"
    return set(re.findall(r'\(pad "([^"]*)"', path.read_text())) if path.exists() else None


# ---------- sheet description ----------

def interface(sheet):
    """{net: (label shape, peer sheet)} of one sheet."""
    out = {}
    for net, a, sa, b, sb in LINKS:
        if a == sheet:
            out[net] = (sa, b)
        elif b == sheet:
            out[net] = (sb, a)
    return out


FONT = "(effects (font (size 1.27 1.27)) %s)"
PAPERS = [("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594), ("A0", 1189, 841)]
STUB = 2.54
SIDE = {0: ("L", -1, 0, 180), 180: ("R", 1, 0, 0), 90: ("B", 0, 1, 270), 270: ("T", 0, -1, 90)}  # pin angle -> side, dx, dy, label angle
JUST = {0: "left", 90: "left", 180: "right", 270: "right"}


def est(text):
    return 1.1 * len(text) + 4


def snap(v):
    return math.ceil(v / 2.54 - 1e-9) * 2.54


class Sheet:
    def __init__(self, name):
        self.name, self.items, self.count, self.single_ok = name, [], collections.Counter(), set()
        self.base = 100 * (SHEETS.index(name) + 1)
        self.path = f"/{uid('sheet', PROJECT)}/{uid('root', 'sheet', name)}"

    # -- description API --
    def group(self, title):
        self.items.append(("group", title))

    def auto(self, prefix):
        self.count[prefix] += 1
        return f"{prefix}{self.base + self.count[prefix]}"

    def part(self, ref, lib_id, value, pins, fp, src="", dnp=False):
        """pins: {pin number or pin name: net}. Use NC for a deliberately open pin."""
        if fp:
            pads = footprint_pads(fp)
            if pads is None:
                raise SystemExit(f"{self.name}/{ref}: footprint {fp} not found")
            missing = {p.num for p in pins_of(lib_id)} - pads
            if missing:
                raise SystemExit(f"{self.name}/{ref}: {fp} has no pad for pin(s) {sorted(missing)} of {lib_id}")
        nets, used = {}, set()
        for p in pins_of(lib_id):
            key = p.num if p.num in pins else p.name
            if key not in pins:
                raise SystemExit(f"{self.name}/{ref}: pin {p.num} ({p.name}) of {lib_id} not assigned")
            nets[p.num] = pins[key]
            used.add(key)
        if set(pins) - used:
            raise SystemExit(f"{self.name}/{ref}: {lib_id} has no pin {sorted(set(pins) - used)}")
        self.items.append(("part", dict(ref=ref, lib_id=lib_id, value=value, nets=nets, fp=fp, src=src, dnp=dnp)))
        return ref

    def R(self, value, a, b, fp=R0402, **kw):
        return self.part(self.auto("R"), "Device:R", value, {"1": a, "2": b}, fp, **kw)

    def C(self, value, a, b="GND", fp=C0402, **kw):
        return self.part(self.auto("C"), "Device:C", value, {"1": a, "2": b}, fp, **kw)

    def tp(self, net):
        return self.part(self.auto("TP"), "Connector:TestPoint", net, {"1": net}, TP_PAD)

    def flag(self, net):
        """PWR_FLAG: tells ERC this net is powered (source is a connector or passes through a passive)."""
        return self.part(self.auto("#FLG"), "power:PWR_FLAG", "PWR_FLAG", {"1": net}, "")

    def park(self, *nets):
        """Hierarchical nets of this sheet that have no part to land on yet (connector not drawn).
        They are listed as bare labels, so ERC keeps reporting them as unconnected."""
        self.items.append(("park", nets))

    def single(self, *nets):
        """Local nets that are allowed to appear on one pin only."""
        self.single_ok |= set(nets)

    # -- rendering --
    def _instance(self, lib_id, ref, value, x, y, unit=1, rot=0, fp="", src="", dnp=False, key=""):
        props = props_of(lib_id)
        s = (f'\t(symbol (lib_id {q(lib_id)}) (at {num(x)} {num(y)} {rot}) (unit {unit}) (exclude_from_sim no) '
             f'(in_bom {"no" if ref.startswith("#") else "yes"}) (on_board yes) (dnp {"yes" if dnp else "no"}) '
             f'(uuid "{uid(self.name, ref, key, str(unit))}")\n')
        fields = {"Reference": ref, "Value": value, "Footprint": fp,
                  "Datasheet": uq(props["Datasheet"][2]) if "Datasheet" in props else "",
                  "Description": uq(props["Description"][2]) if "Description" in props else ""}
        if src:
            fields["Source"] = src
        for k, v in fields.items():
            at = kids(props[k], "at")[0] if k in props else ["at", "0", "0", "0"]
            lib_hidden = k in props and ("hide" in dump(props[k]))
            hide = k not in ("Reference", "Value") or lib_hidden or ref.startswith("#") and k == "Reference"
            px, py = float(at[1]), float(at[2])
            if rot:  # only one-pin symbols at the origin are rotated; keep their text near the pin
                px, py = 0, -5.08 if rot == 180 else 0
            s += (f'\t\t(property {q(k)} {q(v)} (at {num(x + px)} {num(y - py)} {at[3] if len(at) > 3 and not rot else 0}) '
                  f'{FONT % ("(hide yes)" if hide else "")})\n')
        s += f'\t\t(instances (project {q(PROJECT)} (path {q(self.path)} (reference {q(ref)}) (unit {unit}))))\n\t)\n'
        return s

    def _net(self, net, x, y, ang, key, uses):
        """Stub and label for one pin end at (x, y); ang is the library pin angle."""
        if net == NC:
            return f'\t(no_connect (at {num(x)} {num(y)}) (uuid "{uid(self.name, key, "nc")}"))\n'
        _, dx, dy, lang = SIDE[ang]
        ex, ey = x + dx * STUB, y + dy * STUB
        s = (f'\t(wire (pts (xy {num(x)} {num(y)}) (xy {num(ex)} {num(ey)})) (stroke (width 0) (type default)) '
             f'(uuid "{uid(self.name, key, "w")}"))\n')
        uses[net] += 1
        if net == "GND":
            self.count["#PWR"] += 1
            rot = {270: 0, 90: 180, 180: 270, 0: 90}[lang]
            return s + self._instance("power:GND", f"#PWR{self.base * 10 + self.count['#PWR']:05d}", "GND", ex, ey,
                                      rot=rot, key=key)
        tail = f'(at {num(ex)} {num(ey)} {lang}) {FONT % f"(justify {JUST[lang]})"} (uuid "{uid(self.name, key, "l")}"))\n'
        if net in RAILS:
            return s + f'\t(global_label {q(net)} (shape passive) {tail}'
        if net in interface(self.name):
            return s + f'\t(hierarchical_label {q(net)} (shape {interface(self.name)[net][0]}) {tail}'
        return s + f'\t(label {q(net)} {tail}'

    def _layout(self, pw, ph):
        """Each group is laid out as a box (parts flow left to right, wrapping); boxes are shelf-packed."""
        left, top, width, fits = 20.32, 20.32, pw - 20, True
        boxes = []  # (title, note, [(item, unit, pin positions, x, y)], box width, box height)
        for kind, item in self.items:
            if kind == "group":
                title, _, note = item.partition(" - ")
                boxes.append([title, note, [], max(2.2 * len(title), 1.2 * len(note)), 10.16])
                self._cursor = [0, 10.16, 0]  # x, y, row height inside the box
                continue
            cur, box = self._cursor, boxes[-1]
            if kind == "park":
                box[2].append((item, None, None, cur[0], cur[1]))
                cur[0], cur[2] = cur[0] + 45.72, max(cur[2], 2.54 * len(item) + 2.54)
                box[3], box[4] = max(box[3], cur[0]), max(box[4], cur[1] + cur[2])
                continue
            pins = pins_of(item["lib_id"])
            for unit in sorted({p.unit for p in pins if p.unit}) or [1]:
                pos = {}
                for p in pins:
                    if p.unit in (0, unit):
                        net = item["nets"][p.num]
                        if pos.setdefault((p.x, p.y, p.ang), net) != net:
                            raise SystemExit(f"{self.name}/{item['ref']}: stacked pins at {p.num} need one net")
                big = len(pos) > 3
                m = dict(L=2.54, R=7.62, T=7.62 if big else 2.54, B=2.54)
                for (x, y, a), net in pos.items():
                    if net != NC:
                        m[SIDE[a][0]] = max(m[SIDE[a][0]], STUB + est(net))
                xs, ys = [k[0] for k in pos], [k[1] for k in pos]
                w, h = max(xs) - min(xs) + m["L"] + m["R"] + 2.54, max(ys) - min(ys) + m["T"] + m["B"] + 2.54
                if cur[0] + w > 0.62 * (width - left) and cur[0] > 0:  # squarish boxes pack better
                    cur[:] = [0, cur[1] + cur[2] + 5.08, 0]
                box[2].append((item, unit, pos, cur[0] + m["L"] - min(xs), cur[1] + m["T"] + max(ys)))
                cur[0], cur[2] = cur[0] + w + 2.54, max(cur[2], h)
                box[3], box[4] = max(box[3], cur[0]), max(box[4], cur[1] + cur[2])
        body, libs, uses = "", {"power:GND"}, collections.Counter()
        self.count["#PWR"] = 0
        x, y, shelf_h = left, top, 0
        for title, note, cells, bw, bh in boxes:
            if x + bw > width and x > left:
                x, y, shelf_h = left, y + shelf_h + 10.16, 0
            body += (f'\t(text {q(title)} (exclude_from_sim no) (at {num(x)} {num(y + 3.81)} 0) '
                     f'(effects (font (size 2.54 2.54) (bold yes)) (justify left bottom)) (uuid "{uid(self.name, "group", title)}"))\n')
            if note:
                body += (f'\t(text {q(note)} (exclude_from_sim no) (at {num(x)} {num(y + 6.35)} 0) '
                         f'(effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid(self.name, "note", title)}"))\n')
            for item, unit, pos, rx, ry in cells:
                ox, oy = snap(x + rx), snap(y + ry)
                if unit is None:  # parked nets
                    for i, net in enumerate(item):
                        uses[net] += 1
                        body += (f'\t(hierarchical_label {q(net)} (shape {interface(self.name)[net][0]}) '
                                 f'(at {num(ox + 35.56)} {num(oy + 2.54 * i)} 180) {FONT % "(justify right)"} '
                                 f'(uuid "{uid(self.name, "park", net)}"))\n')
                    continue
                libs.add(item["lib_id"])
                body += self._instance(item["lib_id"], item["ref"], item["value"], ox, oy, unit, 0, item["fp"],
                                       item["src"], item["dnp"])
                for (px, py, a), net in sorted(pos.items()):
                    body += self._net(net, ox + px, oy - py, a, f"{item['ref']}/{unit}/{px}/{py}", uses)
            # stay inside the frame and clear of the title block (bottom right, about 190 x 45 mm)
            fits &= y + bh < ph - 15 and not (x + bw > pw - 200 and y + bh > ph - 55)
            x, shelf_h = x + bw + 12.7, max(shelf_h, bh)
        return (body, libs, uses) if fits else None

    def render(self):
        for paper, pw, ph in PAPERS:
            out = self._layout(pw, ph)
            if out:
                break
        body, libs, uses = out
        iface = interface(self.name)
        unused = [n for n in iface if not uses[n]]
        single = [n for n, c in uses.items() if c == 1 and n not in iface and n not in RAILS and n != "GND"
                  and n not in self.single_ok]
        if self.items and (unused or single):
            raise SystemExit(f"{self.name}: unused hierarchical nets {unused}; local nets on one pin only {single}")
        if not self.items:  # not drawn yet: list the hierarchical labels only
            for i, (net, (shape, _)) in enumerate(iface.items()):
                body += (f'\t(hierarchical_label {q(net)} (shape {shape}) (at 50.8 {num(38.1 + 2.54 * i)} 180) '
                         f'{FONT % "(justify right)"} (uuid "{uid(self.name, "hl", net)}"))\n')
            libs = set()
        lib_text = "".join("\t\t" + dump(lib_symbol(l)) + "\n" for l in sorted(libs))
        return header(self.name, self.name, paper).replace("\t(lib_symbols)\n", f"\t(lib_symbols\n{lib_text}\t)\n") \
            + body + "\t(embedded_fonts no)\n)\n"


def header(name, title, paper="A3"):
    return f"""(kicad_sch
	(version 20250114)
	(generator "eeschema")
	(generator_version "9.0")
	(uuid "{uid('sheet', name)}")
	(paper "{paper}")
	(title_block
		(title "Maratus Core - {title}")
		(date "2026-11-09")
		(rev "0.1")
		(company "Maratus")
		(comment 1 "Phase 1 draft. Not reviewed, not built, not for manufacture.")
		(comment 2 "Generated by tools/sch.py from tools/sheets/. Do not edit by hand.")
	)
	(lib_symbols)
"""


def root():
    """Top sheet: seven sheet symbols, every sheet pin on a stub with a local label."""
    def rows(name):  # pins of one sheet symbol, grouped by peer sheet, None = gap
        by_peer = collections.defaultdict(list)
        for net, (shape, peer) in interface(name).items():
            by_peer[peer].append((net, shape))
        cols = (["power", "wifi", "ethernet"], ["display", "misc", "expansion"]) if name == "p4-core" \
            else (["p4-core"] + [p for p in by_peer if p != "p4-core"], [])
        return [sum(([None] + by_peer[p] for p in col if p in by_peer), [])[1:] for col in cols]

    place = {"p4-core": (165.1, 38.1, 50.8)}
    for col_x, names in ((50.8, ["power", "wifi", "ethernet"]), (320.04, ["display", "misc", "expansion"])):
        y = 38.1
        for n in names:
            place[n] = (col_x, y, 45.72)
            y += 2.54 * (len(rows(n)[0]) + 1) + 15.24
    body, sheets = "", ""
    for page, name in enumerate(SHEETS, start=2):
        x, y0, w = place[name]
        left, right = rows(name)
        if name in ("power", "wifi", "ethernet"):  # left column: pins face p4-core
            left, right = [], left
        h = 2.54 * (max(len(left), len(right)) + 1)
        pins = ""
        for col, px, ang, just, dx in ((left, x, 180, "left", -5.08), (right, x + w, 0, "right", 5.08)):
            for i, row in enumerate(col):
                if not row:
                    continue
                net, shape = row
                py = y0 + 2.54 * (i + 1)
                pins += (f'\t\t(pin {q(net)} {shape} (at {num(px)} {num(py)} {ang}) (uuid "{uid("root", name, "pin", net)}") '
                         f'{FONT % f"(justify {just})"})\n')
                body += (f'\t(wire (pts (xy {num(px)} {num(py)}) (xy {num(px + dx)} {num(py)})) '
                         f'(stroke (width 0) (type default)) (uuid "{uid("root", name, "wire", net)}"))\n')
                body += (f'\t(label {q(net)} (at {num(px + dx)} {num(py)} {180 if dx < 0 else 0}) '
                         f'{FONT % ("(justify right bottom)" if dx < 0 else "(justify left bottom)")} '
                         f'(uuid "{uid("root", name, "label", net)}"))\n')
        sheets += f"""	(sheet (at {num(x)} {num(y0)}) (size {num(w)} {num(h)})
		(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)
		(stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))
		(uuid "{uid('root', 'sheet', name)}")
		(property "Sheetname" {q(name)} (at {num(x)} {num(y0 - 0.7116)} 0) {FONT % "(justify left bottom)"})
		(property "Sheetfile" {q(name + ".kicad_sch")} (at {num(x)} {num(y0 + h + 0.5846)} 0) {FONT % "(justify left top)"})
{pins}		(instances (project {q(PROJECT)} (path "/{uid('sheet', PROJECT)}" (page "{page}"))))
	)
"""
    return (header(PROJECT, "top level") + body + sheets
            + '\t(sheet_instances (path "/" (page "1")))\n\t(embedded_fonts no)\n)\n')


def check_links():
    def col(name, i):
        with open(ROOT / "hardware" / "inputs" / name, newline="") as f:
            return [r[i] for r in list(csv.reader(f))[1:]]
    p4, c5 = col("maratus-core-gpio-map.csv", 2), col("maratus-core-c5-pin-map.csv", 2)
    names = [l[0] for l in LINKS]
    assert len(names) == len(set(names)), "duplicate net in LINKS"
    for net, a, _, b, _ in LINKS:
        assert a in SHEETS and b in SHEETS and a != b, net
        assert a != "p4-core" or net in p4, f"{net} is not a net in the P4 gpio map"
        assert b != "wifi" or net in c5, f"{net} is not a net in the C5 pin map"


def gen():
    sys.path.insert(0, str(ROOT / "tools"))
    check_links()
    importlib.import_module("maratus_lib").write()
    files = {f"{PROJECT}.kicad_sch": root()}
    for name in SHEETS:
        sheet, mod = Sheet(name), ROOT / "tools" / "sheets" / f"{name.replace('-', '_')}.py"
        if mod.exists():
            importlib.import_module(f"sheets.{mod.stem}").build(sheet)
        files[f"{name}.kicad_sch"] = sheet.render()
        print(f"  {name}: {sum(k == 'part' for k, _ in sheet.items)} parts")
    for fname, text in files.items():
        (CORE / fname).write_text(text)
        subprocess.run(["kicad-cli", "sch", "upgrade", "--force", str(CORE / fname)], check=True,
                       stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    if sys.argv[1:2] == ["gen"]:
        gen()
    elif sys.argv[1:2] == ["pins"]:
        for lib_id in sys.argv[2:]:
            pr = props_of(lib_id)
            print(f"{lib_id}  footprint={uq(pr['Footprint'][2])!r}  filters={uq(pr['ki_fp_filters'][2]) if 'ki_fp_filters' in pr else ''!r}")
            print(f"  datasheet={uq(pr['Datasheet'][2])}")
            for p in sorted(pins_of(lib_id), key=lambda p: (p.unit, [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', p.num)])):
                print(f"  {p.num:>4} {p.name:<22} {p.etype:<14} unit {p.unit} at ({p.x:g}, {p.y:g}) {p.ang}{' hidden' if p.hidden else ''}")
    else:
        sys.exit(__doc__)
