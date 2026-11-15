#!/usr/bin/env python3
"""Schematics of the two Dock boards, with the same generator as the Core: python3 tools/dock_sch.py

Writes hardware/dock-contact/ and hardware/dock-base/ (one root sheet and one sheet each) from tools/sheets/dock_*.py,
runs ERC on both into reports/erc-dock-*.rpt. Run `python3 tools/sch.py gen` afterwards if the Core is also needed:
both write hardware/lib/maratus.
"""
import json
import shutil
import subprocess

import sch

BOARDS = {"dock-contact": "Maratus Dock contact board", "dock-base": "Maratus Dock base board"}


def use(name):
    """Points the generator's globals at one Dock board."""
    sch.PROJECT, sch.TITLE = f"maratus-{name}", BOARDS[name]
    sch.CORE, sch.SHEETS, sch.LINKS = sch.ROOT / "hardware" / name, [name], []
    sch.CORE.mkdir(exist_ok=True)
    for table in ("sym-lib-table", "fp-lib-table"):     # same relative library paths as the Core project
        shutil.copy(sch.ROOT / "hardware" / "core" / table, sch.CORE / table)
    pro = sch.CORE / f"{sch.PROJECT}.kicad_pro"      # without a project file kicad-cli ignores the library tables
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": pro.name, "version": 3}}, indent=2) + "\n")
    return sch.CORE / f"{sch.PROJECT}.kicad_sch"


if __name__ == "__main__":
    for name in BOARDS:
        top = use(name)
        sch.gen()
        report = sch.ROOT / "reports" / f"erc-{name}.rpt"
        subprocess.run(["kicad-cli", "sch", "erc", "--severity-all", "-o", str(report), str(top)],
                       check=True, stdout=subprocess.DEVNULL)
        print(f"  {name}: {[l.strip() for l in report.read_text().splitlines() if 'ERC messages' in l]}")
