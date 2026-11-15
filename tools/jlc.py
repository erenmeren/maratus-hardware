#!/usr/bin/env python3
"""Order files for JLCPCB, from the boards as they are (nothing is placed or routed again).

  python3 tools/jlc.py     -> out/fab/jlcpcb/<board>-gerber.zip for all three boards, and for the Core
                              maratus-core-bom.csv, maratus-core-cpl.csv and maratus-core-not-fitted.txt

Part numbers: hardware/inputs/jlcpcb-parts.csv, one line per value and footprint, each checked against JLCPCB's
parts library on the date in the file. A line with an empty part number is a part JLCPCB does not fit; its note says
why. A part with no line at all stops the script.
The Dock's two boards are ordered bare: their parts are few and large, and are soldered by hand
(hardware/inputs/maratus-dock-bom-preliminary.csv).
BOM and CPL have the column names JLCPCB asks for. Rotations are KiCad's: JLCPCB turns some packages differently,
so look at pin 1 of every IC in their placement preview before paying.
Draft boards: read docs/design-spec.md section 10 before ordering anything.
"""
import csv
import pathlib
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "fab" / "jlcpcb"
PARTS = ROOT / "hardware" / "inputs" / "jlcpcb-parts.csv"
BOARDS = {"maratus-core": ("core", 4, True), "maratus-dock-contact": ("dock-contact", 2, False),
          "maratus-dock-base": ("dock-base", 2, False)}       # folder, copper layers, assembled by JLCPCB
NOT_PARTS = ("TestPoint:", "MountingHole:")                   # pads and holes of the board itself


def cli(*args):
    subprocess.run(["kicad-cli", *map(str, args)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gerbers(name, folder, layers):
    board = ROOT / "hardware" / folder / f"{name}.kicad_pcb"
    copper = "F.Cu,In1.Cu,In2.Cu,B.Cu" if layers == 4 else "F.Cu,B.Cu"
    with tempfile.TemporaryDirectory() as tmp:
        cli("pcb", "export", "gerbers", "-o", tmp, "--subtract-soldermask", "-l",
            copper + ",F.Paste,B.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts", board)
        cli("pcb", "export", "drill", "-o", tmp + "/", "--excellon-separate-th", board)
        files = sorted(pathlib.Path(tmp).iterdir())
        with zipfile.ZipFile(OUT / f"{name}-gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.name)
    return len(files)


def bom(name, folder, parts):
    """Writes the BOM of the parts JLCPCB fits. Returns their references and the lines it does not fit."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "bom.csv"
        cli("sch", "export", "bom", "--fields", "Reference,Value,Footprint,${DNP}", "--group-by", "Value,Footprint,${DNP}",
            "--ref-range-delimiter", "", "-o", raw, ROOT / "hardware" / folder / f"{name}.kicad_sch")
        rows = list(csv.DictReader(raw.open()))
    fitted, left, unknown, lines = set(), [], [], {}      # lines: one per part number
    for r in rows:
        refs, key = r["Reference"], (r["Value"], r["Footprint"])
        if r["DNP"] or r["Footprint"].startswith(NOT_PARTS):
            continue
        if key not in parts:
            unknown.append(f"{refs}: {key[0]} | {key[1]}")
        elif not parts[key]["JLCPCB part"]:
            left.append(f"{refs}: {key[0]} - {parts[key]['Note']}")
        else:
            line = lines.setdefault(parts[key]["JLCPCB part"], [parts[key]["MPN"], [], key[1].split(":")[-1]])
            line[1] += refs.split(",")
            fitted.update(refs.split(","))
    if unknown:
        sys.exit(f"{name}: no line in {PARTS.name} for:\n  " + "\n  ".join(unknown))
    with (OUT / f"{name}-bom.csv").open("w", newline="") as f:
        csv.writer(f).writerows([("Comment", "Designator", "Footprint", "LCSC Part #"),
                                 *[(mpn, ",".join(refs), fp, part) for part, (mpn, refs, fp) in lines.items()]])
    (OUT / f"{name}-not-fitted.txt").write_text("\n".join(left) + "\n")
    return fitted, left, len(lines)


def cpl(name, folder, fitted):
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "pos.csv"
        cli("pcb", "export", "pos", "-o", raw, "--format", "csv", "--units", "mm", "--side", "both", "--exclude-dnp",
            ROOT / "hardware" / folder / f"{name}.kicad_pcb")
        rows = [r for r in csv.DictReader(raw.open()) if r["Ref"] in fitted]
    missing = fitted - {r["Ref"] for r in rows}
    assert not missing, f"{name}: in the BOM but not on the board: {sorted(missing)}"
    with (OUT / f"{name}-cpl.csv").open("w", newline="") as f:
        csv.writer(f).writerows([("Designator", "Mid X", "Mid Y", "Layer", "Rotation"),
                                 *[(r["Ref"], r["PosX"], r["PosY"], r["Side"], r["Rot"]) for r in rows]])
    return {r["Side"] for r in rows}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    parts = {(r["Value"], r["Footprint"]): r for r in csv.DictReader(PARTS.open())}
    for name, (folder, layers, assembled) in BOARDS.items():
        print(f"{name}: {gerbers(name, folder, layers)} Gerber and drill files", end="")
        if assembled:
            fitted, left, kinds = bom(name, folder, parts)
            sides = cpl(name, folder, fitted)
            print(f"; BOM {len(fitted)} parts of {kinds} kinds on the {' and '.join(sorted(sides))} side; "
                  f"{len(left)} lines not fitted", end="")
        print()
