# First prompt for Claude Code

Paste the block below into Claude Code, started in the root of this repo.

```
Read CLAUDE.md, docs/design-spec.md and docs/brief.md before doing anything.

We are starting Phase 1: the Maratus Core schematic in KiCad. Work in this order and stop at each
STOP so I can review.

Step 1 - toolchain
- Run `kicad-cli version` and `python3 tools/check_pinmap.py`. Report both results.
- Read `kicad-cli sch erc -h` and `kicad-cli pcb drc -h` and tell me if any flag in CLAUDE.md
  does not exist in this version.
- Add https://github.com/espressif/kicad-libraries as a git submodule at hardware/lib/espressif.

Step 2 - references
- Download into docs/reference/: the ESP32-P4 datasheet, the ESP32-P4 chip revision v3.x user
  guide, the ESP32-P4 hardware design guidelines (PDF), the ESP32-P4X-Function-EV-Board
  schematic, the Waveshare ESP32-P4-WIFI6-Touch-LCD-4B schematic, the ESP32-C5-WROOM-1 datasheet,
  and the datasheets for IP101GRI, TPS2121, TLV62569 and W25Q128JV.
- For each file, tell me what you got and from which URL. If one cannot be downloaded, say so
  and do not substitute a different document.
- Check every "Confirm" item in docs/design-spec.md against these documents and list what you
  found, with page numbers.
STOP.

Step 3 - project skeleton
- Create the KiCad project hardware/core/maratus-core with project-local library tables
  (Espressif library under the nickname PCM_Espressif) and the hierarchical sheets listed in
  CLAUDE.md. Empty sheets with their hierarchical labels only.
- Run ERC, save reports/erc.rpt, export the schematic PDF to out/.
STOP.

Step 4 - one sheet at a time
- Order: power, p4-core, wifi, ethernet, expansion, misc. Leave display until the panel
  datasheet is in docs/reference/.
- For each sheet: draw it from the datasheets in docs/reference/, run ERC, save the report,
  export the PDF, and give me a short list of (a) what you verified and where, (b) what you
  assumed, (c) what a human must check.
STOP after each sheet.

Never tell me a sheet is correct because ERC is clean. Tell me what ERC cannot see.
```
