# Maratus hardware

Custom hardware for Maratus (maratus.co): the **Core** (4-inch QR display device), the **Dock** and
the **LAN Module**. This repo holds KiCad sources, mechanical CAD and design documents.

Related repos: `erenmeren/maratus-firmware` (ESP-IDF firmware), `erenmeren/maratus-admin` (cloud, device protocol).

## Status

- Phase 0 (feasibility and architecture): done. Decisions are in `docs/design-spec.md`.
- Phase 1 (Core schematic and PCB): schematic draft exists for all seven sheets, every part has a
  footprint. `display` is drawn for the Newhaven NHD-4.0-480480AF-MSXP-CTP panel. A draft PCB
  exists: scripted placement, autorouted, no hand-routed critical nets (design-spec section 10;
  on 2026-11-10 its DRC report had 0 unconnected pads and 2 silkscreen warnings).
  A prototype enclosure exists as generated CAD (design-spec section 12). None of it is reviewed
  by a hardware or mechanical engineer.
- Nothing here is manufacturing-ready. No hardware has been built or tested.

## Rules

1. Never invent pin numbers, ratings, footprints, prices or availability. Pin data comes from the
   manufacturer's datasheet or an official library. If the source cannot be opened, stop and say so.
2. "Passes ERC" or "passes DRC" may only be said when the report file in `reports/` was produced in
   the current session. Quote the violation counts from the report.
3. A clean ERC is necessary, not sufficient. List everything that still needs measurement,
   prototype validation or human review.
4. Never describe a design as manufacturing-ready.
5. `hardware/inputs/*.csv` are the source of truth for the P4 and C5 pin assignment. Change them
   only deliberately, then run `python3 tools/check_pinmap.py`; it must pass.
6. Work in small steps: one schematic sheet at a time, ERC after each sheet, then stop for review.
7. V1 scope is fixed: no camera, scanner, NFC, battery charger or PoE on the Core.
8. Record the datasheet (file name and page) for every symbol or footprint drawn by hand.

## Toolchain

- KiCad 9 or newer. Start every session with `kicad-cli version`. Check flags with `-h` before
  first use; they differ between versions.
- ERC (exit code 5 means violations):
  `kicad-cli sch erc --severity-all --exit-code-violations -o reports/erc.rpt hardware/core/maratus-core.kicad_sch`
  Two `pin_to_pin` warnings on U1 pins 101 and 102 are known (design-spec section 11 item 7).
- DRC:
  `kicad-cli pcb drc --severity-all --schematic-parity --exit-code-violations -o reports/drc.rpt hardware/core/maratus-core.kicad_pcb`
- Schematic PDF for review: `kicad-cli sch export pdf -o out/maratus-core-sch.pdf hardware/core/maratus-core.kicad_sch`
- Pin map check: `python3 tools/check_pinmap.py`
- Schematic generator: `python3 tools/sch.py gen` rewrites `hardware/core/*.kicad_sch` and
  `hardware/lib/maratus/maratus.kicad_sym` from `tools/sheets/*.py` and `tools/maratus_lib.py`.
  Edit those files, not the `.kicad_sch`: changes made in the KiCad GUI are lost on the next run.
  `python3 tools/sch.py pins LIB:NAME` prints a library symbol's pin table.
- PCB generator: `python3 tools/pcb.py place` rewrites `hardware/core/maratus-core.kicad_pcb` from
  the netlist (outline, placement, planes, rules; fixed positions are `FIXED` in the script),
  `route` runs Freerouting and fills the zones, `fab` writes Gerbers, drill, position file, STEP
  and renders to `out/fab`. Manual edits of the board are lost on the next `place`.
  Freerouting 2.5.0 and its Java 25 runtime live in `out/tools` (not in git; download again from
  github.com/freerouting/freerouting and adoptium.net).
- Enclosure: `out/tools/cadenv/bin/python tools/enclosure.py` (build123d in a Python 3.12 venv made
  with `uv`) writes `mechanical/core/*.step|stl`; `blender -b -P tools/render_enclosure.py` renders
  them. Shared dimensions are in `tools/mech.py`.
- Netlist check: `python3 tools/check_netlist.py` (P4, C5 and rear-pad nets against the pin maps
  and design-spec section 7, plus every cross-sheet net). Run it after every `gen`.

## Layout of this repo

| Path | Content |
| --- | --- |
| `docs/brief.md` | The original project brief. Read it once; it sets the standard of work. |
| `docs/design-spec.md` | Phase 0 decisions in schematic-ready form. |
| `docs/bringup-checklist.md` | Prototype bring-up checklist (all lines untested). |
| `docs/reference/` | Datasheets and reference schematics. Fetch them; do not work from memory. |
| `hardware/inputs/` | Pin maps and preliminary BOM (CSV). |
| `hardware/core/` | KiCad project for the Core (to be created). |
| `hardware/lib/espressif/` | Espressif KiCad library (git submodule). |
| `hardware/lib/maratus/` | Project symbols and footprints drawn from datasheets. |
| `mechanical/core/` | Generated enclosure CAD (STEP, STL) and the board's STEP model. |
| `reports/` | ERC and DRC reports. |
| `tools/` | Checks and generators. |

## Libraries

- Espressif's official library: `https://github.com/espressif/kicad-libraries`, as a submodule at
  `hardware/lib/espressif`. Symbols `ESP32-P4X` and `ESP32-C5-WROOM-1`; footprints `ESP32-P4` and
  `ESP32-C5-WROOM-1`. The symbols' Footprint field uses the nickname `PCM_Espressif`, so register the
  library under that nickname in project-local `sym-lib-table` and `fp-lib-table` with
  `${KIPRJMOD}` paths.
- KiCad's standard libraries for every part that exists there.
- Anything else goes in `hardware/lib/maratus`, drawn from the datasheet. The symbol library and
  `maratus.pretty` are generated from `tools/maratus_lib.py`, which records the datasheet file
  and page per symbol.

## Schematic structure

Hierarchical, one sheet per block, connected by hierarchical labels using the net names in
`hardware/inputs/maratus-core-gpio-map.csv`:

1. `power` – USB-C input, rear-pad input, power mux, 3.3 V buck, V_ACC switch, supervisor
2. `p4-core` – ESP32-P4NRW32X, core DCDC, crystal, flash, decoupling, straps, test pads
3. `wifi` – ESP32-C5-WROOM-1-N4, SDIO pull-ups, C5 control and recovery lines
4. `display` – LCD FFC, touch FFC, backlight boost driver
5. `ethernet` – IP101GRI PHY, crystal, ESD arrays
6. `expansion` – 18-pad rear contact field, protection parts
7. `misc` – buzzer, service switch, USB-C data, camera footprint (DNP)

Drawing style of the generated sheets: every pin has a stub and a net label; parts are connected by
net name, not by drawn wires. Hierarchical labels carry signals only. Rails (`3V3`, `5V_SYS`, `VIN`,
`VBUS`, `V_ACC`, `VDD_HP`, `VDD_FLASH`, `VDD_PSRAM`, `VDD_MIPI`) are global labels and `GND` is a
power symbol. The cross-sheet net list is `LINKS` in `tools/sch.py`.

## PCB layout

The board in the repo is a generated draft: `tools/pcb.py` places the parts and Freerouting routes
them. It shows that the design fits and connects; it is not a layout to order. Critical nets
(DSI, SDIO, RMII, USB, crystal, core DCDC loop) still have to be placed and routed by a person in
the KiCad GUI against Espressif's layout guide, with a fabricator's stack-up for the impedances.
Once a person edits the board, stop running `tools/pcb.py place`.

## Blocked on people

- Panel samples: the Newhaven NHD-4.0-480480AF-MSXP-CTP has to be ordered. The FFC fold direction
  (J2 top contact, J4 bottom contact) and the ST7701SN init sequence are confirmed on a sample.
  See `docs/design-spec.md` section 8.
- A layout engineer for the critical nets and a review of the whole draft.
- RF: the taller body with the module's PCB antenna was chosen on 2026-11-10; range has to be
  measured on a prototype (the antenna is 1 mm from the LCD's metal back).
