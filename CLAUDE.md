# Maratus hardware

Custom hardware for Maratus (maratus.co): the **Core** (4-inch QR display device), the **Dock** and
the **LAN Module**. This repo holds KiCad sources, mechanical CAD and design documents.

Related repos: `erenmeren/maratus-firmware` (ESP-IDF firmware), `erenmeren/maratus-admin` (cloud, device protocol).

## Status

- Phase 0 (feasibility and architecture): done. Decisions are in `docs/design-spec.md`.
- Phase 1 (Core schematic and PCB): schematic draft exists for all seven sheets, every part has a
  footprint. `display` is drawn for the Newhaven NHD-4.0-480480AF-MSXP-CTP panel. A draft PCB
  exists: scripted placement, autorouted, no hand-routed critical nets (design-spec section 10;
  on 2026-11-10 the slim board's DRC report had 0 violations and 0 unconnected pads, and again
  on 2026-11-13 after a GND test pad and the C5 wake-up link (R317) were added by script).
  On 2026-11-14 the owner had the rear pad field turned to lie horizontal; it moved to the bottom
  edge and the board was placed and routed again (0 violations, 0 unconnected pads, after a
  one-off script joined the USB-C receptacle's two D+ pads; design-spec sections 7 and 10).
  The same day the service switch moved from the back to the part side at the bottom edge
  (side-actuated B3U-3000P, pressed through a fourth slot beside the buzzer's three) and the
  Dock lock holes went from four to two and then to one M4 nut above the pad window: the back
  carries the pads only, and the rear of the body shows the pad window and one hole. The switch was moved on the routed
  board by a one-off script (DRC of 2026-11-14T19:56: 0 violations, 0 unconnected pads); a new
  `route` from scratch left connections open, so keep `out/pcb/routed-2026-11-14.kicad_pcb`.
  Late that day the USB-C receptacle moved onto a 1.2 mm tab of the board so that the body has
  a phone-style oval opening (design-spec sections 10 and 12); again a one-off script on the
  routed board, DRC of 2026-11-14T20:51: 0 violations, 0 unconnected pads.
  The owner wants a sleep mode and decided on 2026-11-13 that the P4 does not sleep: the screen
  goes off, and on Ethernet the C5 can be shut down on request (design-spec section 11 item 12).
  The wake-up line from the C5 stays on the board, unused (section 5).
  A prototype enclosure exists as generated CAD (design-spec section 12): since 2026-11-14 the
  lens body, a square with 12 mm corners and a 1 mm cover lens over the panel (the owner liked
  that front on Apple's HomeView); the slim body before it is kept as a fallback because the
  panel's touch through the lens is not tried. None of it is reviewed by a hardware or
  mechanical engineer. The owner wants the rear contacts level with the rear face (2026-11-14
  night); the pictures in `out/maratus-case-compare.pdf` show that, the CAD and the board still
  have the pad window 3.6 mm deep, and the contact part is not chosen (design-spec section 12).
  The owner wants the hardware open so that anyone can build it (2026-11-15): the
  open-source-hardware mark is on the back of the Core board (design-spec section 10). There is
  no licence file yet; the owner has to choose the licence.
- Dock (brief Phase 3, started at the owner's request on 2026-11-10): draft schematics and
  autorouted boards for its two boards (`dock-contact`, `dock-base`) and two generated bodies
  around the same inner parts (design-spec section 13): BAR (the Core leans on a 38 mm round bar
  with orange end caps) and FLOAT (the Core hovers over an orange plate, a narrow wedge-shaped pod behind).
  The owner chose these two on 2026-11-10 from three look concepts, after rejecting a cradle as
  too bulky and a wedge foot as looking like a separate part; he has not picked one of the two
  yet. Magnets hold the Core on either Dock (owner, 2026-11-12; their pull is calculated, not
  measured) and two screws are an optional lock. Neither stands a press on the screen unless it
  is taped to the counter. Not reviewed. The LAN Module is not started.
  Out of date since 2026-11-14: both bodies, the saddle and the contact board are drawn for the
  upright pad field and no longer fit the Core. `tools/dock.py` stops with a message. Since
  2026-11-15 the Core has two magnets, level with the pad field and 23.5 mm either side of its
  centre (owner; design-spec section 12), not the four the Docks were drawn to. They are
  to be drawn again once the owner has chosen the Dock's look (he asked for more concepts that
  day: `out/maratus-design-concepts-4.pdf`).
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
  `route` runs Freerouting and fills the zones, `finish 12 free` is a second router session for
  the last connections, `fab` writes Gerbers, drill, position file, STEP and renders to `out/fab`.
  Manual edits of the board are lost on the next `place`. Routing differs from run to run: keep a
  copy of a board with 0 unconnected pads before routing again.
  Freerouting 2.5.0 and its Java 25 runtime live in `out/tools` (not in git; download again from
  github.com/freerouting/freerouting and adoptium.net).
- Enclosure: `out/tools/cadenv/bin/python tools/enclosure.py` (build123d in a Python 3.12 venv made
  with `uv`) writes `mechanical/core/*.step|stl` and the lens's `.dxf`; with `slim` it writes the
  earlier body into `mechanical/core/slim/`. `blender -b -P tools/render_enclosure.py` renders
  `mechanical/core`. Shared dimensions are in `tools/mech.py`.
  `out/tools/cadenv/bin/python tools/lens_drawing.py` writes the lens's dimensioned drawing (PDF)
  from that `.dxf`, to send to a glass maker.
- Dock: `python3 tools/dock_sch.py` (both schematics and their ERC), then `python3 tools/dock_pcb.py`
  (both boards, Freerouting, DRC into `reports/drc-dock-*.rpt`, STEP), then
  `out/tools/cadenv/bin/python tools/dock.py [bar|float]` (both bodies, saddle, port drawer,
  interference check with both boards and the Core) and `blender -b -P tools/dock_blend.py`
  (pictures and one `.blend` per body in `out/`).
  `dock-base` has 2 known `silk_edge_clearance` warnings: the RJ45 jack overhangs the board edge.
  The contact board's size and pin field are written in both `tools/dock_pcb.py` and
  `tools/dock.py`: change them together.
- Order files for JLCPCB: `python3 tools/jlc.py` writes `out/fab/jlcpcb/` from the boards as they
  are (Gerber archives of all three boards, BOM and placement file of the Core). Part numbers
  are in `hardware/inputs/jlcpcb-parts.csv`; stock there changes daily. The boards are drafts.
- Netlist check: `python3 tools/check_netlist.py` (P4, C5 and rear-pad nets against the pin maps
  and design-spec section 7, plus every cross-sheet net). Run it after every `gen`.

## Layout of this repo

| Path | Content |
| --- | --- |
| `docs/brief.md` | The original project brief. Read it once; it sets the standard of work. |
| `docs/design-spec.md` | Phase 0 decisions in schematic-ready form. |
| `docs/bringup-checklist.md` | Prototype bring-up checklist (all lines untested). |
| `docs/reference/` | Datasheets and reference schematics. Fetch them; do not work from memory. |
| `hardware/inputs/` | Pin maps, preliminary BOMs of the Core and the Dock, JLCPCB part numbers (CSV). |
| `hardware/core/` | KiCad project for the Core (generated). |
| `hardware/dock-contact/`, `hardware/dock-base/` | KiCad projects of the Dock's two boards (generated). |
| `hardware/lib/espressif/` | Espressif KiCad library (git submodule). |
| `hardware/lib/maratus/` | Project symbols and footprints drawn from datasheets. |
| `mechanical/core/` | Generated enclosure CAD (STEP, STL) and the board's STEP model. |
| `mechanical/dock/` | STEP models of the Dock's boards; saddle and port drawer (STEP, STL), used by both bodies. |
| `mechanical/dock-bar/`, `mechanical/dock-float/` | Generated CAD of the two Dock bodies, each with the Core and the inner parts in place. |
| `reports/` | ERC and DRC reports. |
| `tools/` | Checks and generators. |

## Libraries

- Espressif's official library: `https://github.com/espressif/kicad-libraries`, as a submodule at
  `hardware/lib/espressif`. Symbols `ESP32-P4X` and `ESP32-C5-WROOM-1U`; footprints `ESP32-P4` and
  `ESP32-C5-WROOM-1U`. The symbols' Footprint field uses the nickname `PCM_Espressif`, so register the
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
3. `wifi` – ESP32-C5-WROOM-1U-N4 (external antenna), SDIO pull-ups, C5 control and recovery lines,
   host wake-up line
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

- Panel samples: the Newhaven NHD-4.0-480480AF-MSXP-CTP samples arrived on 2026-11-14 (owner).
  The contact sides are as assumed (owner's check by eye: LCD tail contacts to the front, touch
  tail to the back; J2 bottom contact, J4 top contact, `docs/design-spec.md` section 8), pin 1
  of both tails is on the left seen from the front, the tails reach the connectors and the
  panel fits the printed body. Still to confirm: the ST7701SN init sequence (needs a board that
  can drive the panel).
- A layout engineer for the critical nets and a review of the whole draft.
- Dock body: the owner picks BAR or FLOAT, on pictures or on prints (design-spec section 13). The
  boards are the same for both.
- RF: the owner chose the slim body (glass to the edge) with an external flex antenna on
  2026-11-10 and kept it on 2026-11-12 over the PCB-antenna module. Range has to be measured on a prototype, and the antenna's gain is above what the
  module was certified with (design-spec section 12).
