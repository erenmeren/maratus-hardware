# Maratus Core: brief for a layout engineer

2026-11-16. The Core board is a generated draft: scripted placement, autorouted, not reviewed and
not manufacturing-ready. This brief asks a layout engineer to lay out the critical nets by hand
and to review the rest. Nothing in it is tested on hardware.

## What is asked

1. Choose the stack-up with the fabricator and set the track geometry for the impedances below.
2. Place and route by hand, in the KiCad GUI: MIPI DSI, both USB pairs, SDIO, RMII with its
   50 MHz clock, the 40 MHz crystal, the P4's core DCDC loop, the Ethernet pairs to the rear
   pads. Move parts where the routing needs it.
3. Draw the supply copper the autorouter could not: `VDD_HP` above all (section 10 of the spec).
4. Review the rest of the draft and say what else has to change: layer count, via sizes, test
   pads, anything that will not survive production.
5. Hand back the board, the stack-up and impedance table from the fabricator, a length report of
   the nets below, and a list of every rule of this brief that is not met, with the reason.

Once the board is edited by hand, `tools/pcb.py place` and `route` must not be run again: they
rewrite the board.

## What exists

| Item | Where |
| --- | --- |
| KiCad project, version 10.0.8 used on 2026-11-16 | `hardware/core/maratus-core.kicad_pro`, `.kicad_sch`, `.kicad_pcb` |
| Design decisions; PCB in section 10, housing in section 12 | `docs/design-spec.md` |
| Pin assignment of the P4 and the C5 (source of truth) | `hardware/inputs/*.csv` |
| Datasheets and Espressif's reference designs | `docs/reference/` |
| Mechanical numbers the board has to meet | `tools/mech.py`, STEP files in `mechanical/core/` |
| 3D pictures of the draft | `out/maratus-core-pcb-3d.pdf` (not in git; `out/pcb-3d/build.py`) |

The schematic is generated from `tools/sheets/*.py`. A change to the schematic goes into those
files, not into the `.kicad_sch`.

Board: 74.0 x 72.0 mm plus a 12.0 x 1.2 mm tab for the USB-C receptacle, 1.2 mm thick, 4 copper
layers: F.Cu parts and signals, In1.Cu ground, In2.Cu 3V3, B.Cu signals. Parts on the front
only; the back carries the rear contact part P1 (since 2026-11-19 Promax NF6268-20PA, through-hole). Rules of the draft: 0.09 mm clearance, 0.1 mm tracks,
0.4 / 0.2 mm vias, power nets 0.2 mm tracks and 0.45 / 0.2 mm vias.

Checks run on 2026-11-16 (reports in `reports/`):

| Check | Result |
| --- | --- |
| ERC, `reports/erc.rpt` | 0 errors, 2 warnings (`pin_to_pin` on U1 pins 101 and 102, known: spec section 11 item 7) |
| DRC with schematic parity, `reports/drc.rpt` | 0 violations, 0 unconnected pads, 0 footprint errors, 0 parity issues |
| `tools/check_pinmap.py` | 36 checks, 0 failed |
| `tools/check_netlist.py` | 66 checks, 0 failed; 249 parts, 203 nets |

These checks say the board is connected as the schematic says and meets its own clearances. They
say nothing about signal integrity, power integrity or EMC.

## Rules to meet, and where the draft stands

Source of the rules: Espressif, ESP Hardware Design Guidelines for the ESP32-P4, section "PCB
Layout Design" (`docs/reference/esp-hardware-design-guidelines-en-master-esp32p4.pdf`, PDF pages
23 to 28; the same text is at
docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32p4/pcb-layout-design-esp32p4.html).

The draft's lengths are the total track length of each net as routed, all branches included,
measured on the board file on 2026-11-16; a stub to a pull-up or a test pad counts. They show
the size of the gap, not exact pin-to-pin lengths. 1 mil = 0.0254 mm.

| Group | Nets | Espressif's rule | Draft |
| --- | --- | --- | --- |
| MIPI DSI, P4 to J2 | `DSI_CLK_P/N`, `DSI_D0_P/N`, `DSI_D1_P/N` | 100 ohm differential, +/-10 %. Within a pair 10 mil, between pairs 30 mil. Ground reference without a break. Ground copper round the pairs or 2W between them, 3W to other fast signals. A pair of ground return vias at every layer change. | Not routed as pairs. Within a pair: clock 72, D0 21, D1 43 mil. Between pairs: 957 to 1239 mil, 282 mil apart. 2 to 4 vias a line, partly on B.Cu, which lies over the 3V3 plane. |
| MIPI CSI, P4 to J3 (not fitted) | `CSI_CLK_P/N`, `CSI_D0_P/N`, `CSI_D1_P/N` | As DSI. | Within a pair: clock 3, D0 106, D1 88 mil. Between pairs: 1346 to 1674 mil. 2 to 4 vias a line. |
| USB to the USB-C receptacle | `USBC_DP/DN`, `USBC_CONN_DP/DN` | 90 ohm differential, +/-10 %, in parallel, equal lengths. As few vias as possible, ground return vias at each. Ground reference without a break, ground copper round the pair. | Not routed as pairs. P4 side 736 and 765 mil, 2 vias each. Connector side 2113 and 1299 mil, 5 and 4 vias. |
| USB to the rear pads | `ACC_USB_DP/DN` | As above. | 2954 and 2512 mil, 7 and 5 vias. |
| SDIO, P4 to the C5 module | `SDIO_CLK`, `SDIO_CMD`, `SDIO_D0` to `D3`, and the same names with `_C5` on the module's side of the series parts | 50 ohm, +/-10 %. Command and data within +/-50 mil of the clock. Whole run ideally within 2000 mil. No layer change; ground reference without a break; ground copper round the clock. | Clock 1955 mil in all. Against the clock: CMD -134, D0 +1148, D1 +784, D2 -277, D3 -484 mil. D0 and D1 are longer than 2000 mil. 2 to 12 vias a line. |
| 40 MHz crystal | `XTAL_P`, `XTAL_N`, `XTAL_P_X`, `XTAL_N_X` | Crystal at least 4.5 mm from the clock pin. No vias on the clock traces. Complete ground plane, ground vias round the trace, no signal under the crystal, no large inductor near it. | 2 vias each on `XTAL_P`, `XTAL_N` and `XTAL_P_X`. Distance and what runs underneath: not measured. |
| P4 supplies | `VDD_HP`, `VDD_LDO`, `VDD_DCDCC`, 3V3 and the others | 3V3 main supply 25 mil. `VDD_HP_0` to `_3`, `VDD_LDO`, `VDD_DCDCC` 20 mil; the others 10 mil. Star routing. 10 uF at each entry, 0.1 uF a pin. | 0.2 mm (8 mil) tracks: the widest that enters the P4's pads. Copper areas have to be drawn. |
| Core DCDC | `VDD_HP_SW`, `FB_DCDC`, `EN_DCDC` and the converter's parts | Converter close to the chip; input, output and feedback loops as short as possible. | Placed by script next to the pins, routed by the autorouter. Loop areas not looked at. `FB_DCDC` is 1097 mil long. |

Not in Espressif's page; rules from the PHY's data sheet
(`docs/reference/IP101G_preliminary_datasheet_lcsc.pdf`, p.55, section 6):

| Group | Nets | Rule | Draft |
| --- | --- | --- | --- |
| RMII and its clock | `RMII_REF_CLK`, `RMII_TXD0/1`, `RMII_TX_EN`, `RMII_RXD0/1`, `RMII_CRS_DV`, `ETH_REFCLK_ALT`, `PHY_CLKI`, `PHY_CLKO` | Clock trace to the PHY as long as the clock trace to the MAC. Guard traces at the clock. No signal parallel to the clock. Ground plane without a gap. | `RMII_REF_CLK` 2530 mil, 4 vias. Data lines 353 to 1006 mil, up to 4 vias. |
| Ethernet pairs, PHY to the rear pads | `ETH_TX_P/N`, `ETH_RX_P/N` | As short as possible. Termination resistors at the PHY's pins. Three times the spacing to other traces. Vias only close to the device. | Not routed as pairs. TX 2504 and 2548 mil, RX 2769 and 2903 mil, 3 to 5 vias a line. No impedance is stated in that data sheet: the engineer sets it (the transformer is in the Dock). |

## Stack-up and impedance

No stack-up with dielectric thicknesses is defined, so no impedance is controlled in the draft.
The fabricator assumed so far is JLCPCB (`tools/jlc.py`, `hardware/inputs/jlcpcb-parts.csv`). Read
from its own pages on 2026-11-16:

- Controlled impedance is offered on 4 layers at 0.8, 1.0, 1.2, 1.6 and 2.0 mm, tolerance
  +/-10 %, +/-5 % on request (jlcpcb.com/impedance, jlcpcb.com/capabilities/pcb-capabilities).
- Dielectric constants: prepreg 7628 4.4, 3313 4.1, 2116 4.16, 1080 3.91, core 4.6. Copper:
  outer 0.035 mm, inner 0.0152 mm. The page prints 19 named 4-layer stack-ups (JLC04161H-...)
  and does not say which of them gives 1.2 mm.
- Track widths come from JLCPCB's impedance calculator. It is interactive; no width for 50, 90
  or 100 ohm is printed on a page, so none is given here. The engineer reads them for the chosen
  stack-up.
- Limits for multilayer boards with 1 oz copper: track and space 0.09 / 0.09 mm; via 0.15 mm hole
  in 0.25 mm at least, and a 0.2 or 0.25 mm hole with a via under 0.45 mm costs more; via hole to
  track 0.2 mm; copper to a routed edge 0.2 mm; via hole to via hole 0.2 mm.
- Filled and capped vias in pads are "the default for 6-layer and above"; for 4 layers the page
  does not say.

Where the draft's rules sit against those limits:

| Draft rule | JLCPCB's page | Note |
| --- | --- | --- |
| 0.09 mm clearance, 0.1 mm tracks | 0.09 / 0.09 mm | At the limit everywhere, not only at the P4. |
| 0.4 / 0.2 mm vias | costs more under 0.45 mm | 674 of the draft's 734 vias. |
| 0.15 mm hole clearance | 0.2 mm via hole to track, 0.2 mm NPTH to track | Below the page's value. Set for the USB4105 land pattern (0.19 mm from signal pads to the locating holes). |
| 0.1 mm copper to edge at J1 | 0.2 mm | Below the page's value: the receptacle's shell pads at the tab's edge. |

Targets: 100 ohm differential for MIPI, 90 ohm differential for USB, 50 ohm single-ended for
SDIO (Espressif, above). Whether four layers are enough is the engineer's call: the two signal
layers are full round the P4, and Espressif's own advice is to take MIPI and SDIO to an inner
layer right after the chip.

## Fixed by the housing

Section 12 of the spec and `tools/mech.py` give the numbers. Fixed: the board outline and its
four screw holes; the USB-C receptacle J1 on the tab; the two FFC connectors J2 and J4 and the
strips under the two tails where no part may stand; the buzzer BZ701; the service switch SW701
at the bottom edge; part heights under the panel. The C5 module may move, but its U.FL connector
has to reach the flex antenna on the housing floor.

Rear contacts (changed 2026-11-19, after the measurements above): P1 is now Promax
NF6268-20PA on the back, 2 x 10 through-hole pins at 3.00 mm, rows 2.40 mm apart, centre
(37.0, 66.0), housing 50.4 x 7.4 mm (spec section 7). Its pins come through to the part side,
1.9 mm long; the buzzer moved to (25.8, 58.5) to make room, and the board was placed and routed
again, so the lengths in the table above are from the board before that day. The hole and pad
sizes are assumed until Promax sends its PCB layout.

## Acceptance

- `kicad-cli pcb drc --severity-all --schematic-parity --exit-code-violations -o reports/drc.rpt hardware/core/maratus-core.kicad_pcb`:
  0 violations, 0 unconnected pads.
- `python3 tools/check_netlist.py` and `python3 tools/check_pinmap.py`: 0 failed.
- The length report shows every rule of the tables above met, or names the exception.
- The stack-up is one the fabricator sells, with its impedance table.

## Still open after the layout

Only a built board can show these (`docs/bringup-checklist.md`, all lines untested): the panel's
init sequence, touch through the cover lens, Wi-Fi range with the flex antenna, Ethernet and
high-speed USB through spring contacts, the buzzer next to the magnets, `V_ACC` at 0.5 A. EMC
has not been looked at.
