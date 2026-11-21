#!/usr/bin/env python3
"""Check the KiCad netlist of the Core against the pin maps and the rear-pad table.

Exports the netlist with kicad-cli, then checks:
- U1 (ESP32-P4): every pad is on the net named in hardware/inputs/maratus-core-gpio-map.csv
- U2 (ESP32-C5 module): every pad is on the net named in maratus-core-c5-pin-map.csv, NC pads are open
- P1 (rear pads): every pad is on the net of docs/design-spec.md section 7
- every net that crosses sheets (tools/sch.py LINKS) has at least two pins on it

A pad may reach its net through one two-pin series part; the pad-side net is then NAME_<suffix>
(SDIO_CLK_C5, ACC_IO1_PAD, 3V3_USBPHY) and the check confirms that a part bridges NAME and that net.

Run from the repo root:  python3 tools/check_netlist.py
Exit code 0 = all checks pass, 1 = at least one failed. Parts that are not placed yet are reported
as "not drawn" and do not fail the run.
"""
import collections
import csv
import importlib
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sch  # noqa: E402

ROOT = sch.ROOT
NET = ROOT / "out" / "maratus-core.net"
# design-spec.md section 7
P1 = {"a1": "GND", "a2": "ETH_TX_P", "a3": "ETH_TX_N", "a4": "GND", "a5": "ETH_RX_P", "a6": "ETH_RX_N",
      "a7": "GND", "a8": "ACC_USB_DP", "a9": "ACC_USB_DN", "a10": "GND", "b1": "VIN", "b2": "VIN", "b3": "GND",
      "b4": "ACC_ID", "b5": "ACC_IO1", "b6": "ACC_IO2", "b7": "ACC_INT_N", "b8": "GND", "b9": "V_ACC", "b10": "GND"}


def rows(name):
    with open(ROOT / "hardware" / "inputs" / name, newline="") as f:
        return list(csv.reader(f))[1:]


subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(NET), str(sch.CORE / "maratus-core.kicad_sch")],
               check=True, stdout=subprocess.DEVNULL)
tree = sch.parse(NET.read_text())
pin_net, part_pins, net_nodes = {}, collections.defaultdict(dict), collections.defaultdict(list)
for net in sch.kids(sch.kids(tree, "nets")[0], "net"):
    name = sch.uq(sch.kids(net, "name")[0][1])
    short = name if name.startswith("unconnected-") else name.rsplit("/", 1)[-1]
    for node in sch.kids(net, "node"):
        ref, pin = sch.uq(sch.kids(node, "ref")[0][1]), sch.uq(sch.kids(node, "pin")[0][1])
        pin_net[ref, pin] = short
        part_pins[ref][pin] = short
        net_nodes[short].append((ref, pin))

checks, errors, notes = [], [], []


def check(cond, msg):
    checks.append(msg)
    if not cond:
        errors.append(msg)


def bridged(a, b):
    return any(len(p) == 2 and set(p.values()) == {a, b} for p in part_pins.values())


def pads(ref, table):
    """table: {pad: net}. Returns the pads that are wrong."""
    bad = []
    for pad, want in table.items():
        got = pin_net.get((ref, pad))
        if want == "NC":
            ok = got is None or got.startswith("unconnected-")
        else:
            ok = got == want or (str(got).startswith(want + "_") and bridged(want, got))
        if not ok:
            bad.append(f"{ref}.{pad}: want {want}, got {got}")
    return bad


for ref, label, table in (
        ("U1", "P4: all 105 pads on the gpio-map net", {r[0]: r[2] for r in rows("maratus-core-gpio-map.csv")}),
        ("U2", "C5: all 32 pads on the pin-map net", {r[0]: r[2] for r in rows("maratus-core-c5-pin-map.csv")}),
        ("P1", "Rear contact part: all 20 contacts on the design-spec net", P1)):
    if ref not in part_pins:
        notes.append(f"{ref} not drawn yet")
        continue
    bad = pads(ref, table)
    check(not bad, label + ("" if not bad else ": " + "; ".join(bad)))

drawn = {name for name in sch.SHEETS if (ROOT / "tools" / "sheets" / f"{name.replace('-', '_')}.py").exists()}
parked = set()  # nets a sheet lists with park(): their connector is not drawn yet
for name in drawn:
    sheet = sch.Sheet(name)
    importlib.import_module("sheets." + name.replace("-", "_")).build(sheet)
    parked |= {net for kind, item in sheet.items if kind == "park" for net in item}
for net, a, _, b, _ in sch.LINKS:
    if net in parked:
        notes.append(f"{net}: parked, connector not drawn")
    elif a in drawn and b in drawn:
        n = len(net_nodes.get(net, []))
        check(n >= 2, f"Link {a} <-> {b}: {net} has {n} pins")
    else:
        notes.append(f"{net}: {a if a not in drawn else b} not drawn yet")

single = sorted(n for n, nodes in net_nodes.items() if len(nodes) == 1 and not n.startswith("unconnected-"))
print(f"{len(checks)} checks, {len(errors)} failed; {len(part_pins)} parts, {len(net_nodes)} nets")
for c in checks:
    print(("  FAIL " if c in errors else "  ok   ") + c)
print(f"  note: {len(notes)} items skipped because a sheet or part is not drawn"
      + (": " + ", ".join(notes[:6]) + (" ..." if len(notes) > 6 else "") if notes else ""))
print(f"  note: nets with a single pin: {', '.join(single) if single else 'none'}")
sys.exit(1 if errors else 0)
