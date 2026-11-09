# Maratus hardware

Custom hardware for Maratus (maratus.co): the **Core** (4-inch QR display device), the **Dock** and
the **LAN Module**. This repo holds KiCad sources, mechanical CAD and design documents.

Related repos: `erenmeren/maratus-firmware` (ESP-IDF firmware), `erenmeren/maratus-admin` (cloud, device protocol).

## Status

- Phase 0 (feasibility and architecture): done. Decisions are in `docs/design-spec.md`.
- Phase 1 (Core schematic and PCB): starting. No schematic exists yet.
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
- DRC:
  `kicad-cli pcb drc --severity-all --schematic-parity --exit-code-violations -o reports/drc.rpt hardware/core/maratus-core.kicad_pcb`
- Schematic PDF for review: `kicad-cli sch export pdf -o out/maratus-core-sch.pdf hardware/core/maratus-core.kicad_sch`
- Pin map check: `python3 tools/check_pinmap.py`

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
| `reports/` | ERC and DRC reports. |
| `tools/` | Checks and generators. |

## Libraries

- Espressif's official library: `https://github.com/espressif/kicad-libraries`, as a submodule at
  `hardware/lib/espressif`. Symbols `ESP32-P4X` and `ESP32-C5-WROOM-1`; footprints `ESP32-P4` and
  `ESP32-C5-WROOM-1`. The symbols' Footprint field uses the nickname `PCM_Espressif`, so register the
  library under that nickname in project-local `sym-lib-table` and `fp-lib-table` with
  `${KIPRJMOD}` paths.
- KiCad's standard libraries for every part that exists there.
- Anything else goes in `hardware/lib/maratus`, drawn from the datasheet.

## Schematic structure

Hierarchical, one sheet per block, connected by hierarchical labels using the net names in
`hardware/inputs/maratus-core-gpio-map.csv`:

1. `power` – USB-C input, rear-pad input, power mux, 3.3 V buck, V_ACC switch, supervisor
2. `p4-core` – ESP32-P4NRW32X, core DCDC, crystal, flash, decoupling, straps, test pads
3. `wifi` – ESP32-C5-WROOM-1-N4, SDIO pull-ups, C5 control and recovery lines
4. `display` – LCD/touch FPC, backlight boost driver
5. `ethernet` – IP101GRI PHY, crystal, ESD arrays
6. `expansion` – 18-pad rear contact field, protection parts
7. `misc` – buzzer, service switch, USB-C data, camera footprint (DNP)

## PCB layout

Routing is not automated. Critical nets (DSI, SDIO, RMII, USB, crystal, core DCDC loop, antenna
keep-out) are placed and routed by a person in the KiCad GUI. Claude prepares the stackup, net
classes and custom rules, runs DRC, reviews against Espressif's layout guide and produces the
fabrication outputs.

## Blocked on people

- LCD panel datasheet, drawing and init sequence (FPC pinout, logic levels, backlight string).
  Until it arrives the `display` sheet cannot be finished.
- Body shape decision: taller body with module PCB antenna (current assumption) or square body
  with the external-antenna module variant.
