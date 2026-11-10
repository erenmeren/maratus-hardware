# Maratus Core — design specification for schematic capture

Phase 0 decisions in schematic-ready form, dated 2026-11-09. "Verified" means read from the named
source on that date. "Confirm" means it must be checked against the datasheet before it is drawn.

## 1. Product

An always-powered 4-inch touchscreen that shows a cloud-triggered QR code. HTTPS for bootstrap and
OTA download, MQTT over TLS for everything else (`maratus-admin/docs/device-protocol.md`). The
current firmware runs on a Waveshare ESP32-P4-WIFI6-Touch-LCD-4B (ST7703 720x720 panel, GT911
touch, ESP32-C6 over SDIO, P4 silicon v1.0, ESP-IDF 5.5).

## 2. Main parts

| Ref | Part | Status | Open this source |
| --- | --- | --- | --- |
| U1 | ESP32-P4NRW32X (chip revision v3.x, QFN104) | Verified | Espressif P4 datasheet; chip revision v3.x user guide |
| U2 | ESP32-C5-WROOM-1-N4 | Verified | Espressif C5 module datasheet |
| U3 | 16 MB quad SPI NOR, 3.3 V (W25Q128JVSIQ) | Pins and QE bit verified; boot test on the prototype | Winbond datasheet p.75-76; Espressif design guidelines p.15 |
| U4 | TLV62569 buck for VDD_HP | Verified as an Espressif-listed DCDC | TI datasheet; P4X reference schematic |
| U5 | TLV62569 buck, 5 V to 3.3 V, 2 A | Verified: 2.5-5.5 V in, 6 V absolute; see section 11 item 4 | TI datasheet p.3-4 |
| U6 | TPS2121RUXR power mux | Verified | TI datasheet |
| U7 | IP101GRI Ethernet PHY, QFN-32 | Verified | IC Plus IP101G datasheet |
| U8 | TPS61169 backlight boost LED driver, fed from 3V3 | Candidate | TI TPS61169 datasheet; section 8 |
| U9 | TPS2553DBV 5 V switch for V_ACC, limit 524 / 577 / 638 mA | Verified | TI TPS2553 datasheet p.16-17 |
| U10 | TPS3839K33 reset supervisor, 2.93 V, 200 ms | Verified | TI TPS3839 datasheet p.1, p.4 |
| J1 | USB-C receptacle, USB 2.0, 16-pin, GCT USB4105-GF-A | Verified | GCT drawing p.1 |
| J2 | LCD FFC connector, 24-pin 0.5 mm, top contact (Amphenol F32Q-1A7H1-11024) | Footprint from KiCad; part datasheet not read | Newhaven panel datasheet p.4; DigiKey listing |
| J4 | Touch FFC connector, 6-pin 1.0 mm, bottom contact (TE 84952-6) | Footprint from KiCad; confirm fold on a sample | Newhaven panel datasheet p.5; te.com product page |
| P1 | Rear contact field, 18 pads | Defined below | – |

Reference schematics to place in `docs/reference/` and follow:
- Espressif ESP32-P4X-Function-EV-Board schematic (v3.x reference for U1, U4, flash, crystal).
- Waveshare ESP32-P4-WIFI6-Touch-LCD-4B schematic (the working board: panel FPC, backlight, touch).
  It uses v1.x silicon, so its P4 power section must not be copied unchanged.
- Espressif ESP32-P4 Hardware Design Guidelines, schematic checklist and PCB layout pages.
- ESP-Hosted MCU docs: `docs/getting-started-mcu.md` section 1 (SDIO hardware).

## 3. Power tree

```
USB-C VBUS (5 V) --TVS--> TPS2121 IN2 \
Rear pads VIN (5 V) --TVS--> TPS2121 IN1 (priority) --> 5V_SYS
5V_SYS --> U5 buck --> 3V3 --> C5 module, P4 IO rails, VDD_LDO, VDD_DCDCC, PHY, panel logic, touch
3V3    --> U4 buck (EN_DCDC, FB_DCDC from P4) --> VDD_HP (0.99-1.3 V) --> VDD_HP_0..3
P4 LDO1 (VDDO_FLASH, 3.3 V) --> flash VCC, VDD_FLASH_IO
P4 LDO2 (VDDO_PSRAM)        --> VDD_PSRAM_0/1
P4 LDO3 (VDDO_3, 2.5 V set in firmware) --> VDD_MIPI_DPHY
3V3    --> backlight boost --> LED array (6.1 V, 140 mA)
5V_SYS --> U9 switch (ACC_PWR_EN, ACC_PWR_FLT_N) --> V_ACC pad
3V3    --> U10 supervisor --> P4_EN (CHIP_PU)
```

- TPS2121: over-voltage lockout just above 5.5 V, current limit about 2.2 A, status pin to
  `PWR_SRC_ST`. Resistor values from the TI datasheet equations.
- 3V3 peak about 1.44 A against U5's 2 A (recalculated 2026-11-10): C5 transmit 403 mA, P4 minimum
  supply 430 mA and the rest of the earlier 0.97 A, plus the backlight boost at full brightness
  (0.31 A typical, 0.39 A worst case at 7.0 V, 147 mA and an assumed 80 % efficiency), panel logic
  65 mA and touch 16 mA.
- Budget on 5V_SYS (recalculated 2026-11-10, U5 efficiency assumed 90 %): about 0.43 A typical at
  full brightness (estimate), 1.2 A peak (3V3 peak 1.06 A at the 5 V side plus the buzzer's
  150 mA), 1.7 A with a 0.5 A accessory, 1.85 A at the accessory switch's highest limit. The mux
  limit is 2.2 A typical.
- A 1.5 A USB-C source covers the Core alone. An accessory needs a 3 A source or rear-pad power,
  so firmware reads the CC sense pins before it enables V_ACC.
- USB-C: 5.1 k on CC1 and CC2. Each CC also goes through a divider to an ADC pin
  (`USBC_CC1_SENSE`, `USBC_CC2_SENSE`).

## 4. ESP32-P4 rules (Espressif schematic checklist, read 2026-11-09)

- Chip revision v3.x: pin 54 is `VDD_HP_1`. The DCDC feedback resistors (two 499 k) and capacitor
  (22 pF) are populated; take their exact position from the P4X reference schematic.
- VDD_HP: 10 uF bulk plus 0.1 uF at each of the four pins. DCDC placed tight to the chip.
- VDD_LDO and VDD_DCDCC: 10 uF on the trace plus 0.1 uF at each pin, 3.0-3.6 V.
- VDDO_FLASH, VDDO_PSRAM, VDDO_3, VDDO_4: 1 uF each, close to the pin.
- VDD_MIPI_DPHY: 2.25-2.75 V, 10 nF + 0.1 uF + 1 uF.
- VDD_USBPHY: 3.3 V, 10 nF + 0.1 uF + 4.7 uF, through a 0R link.
- VDD_BAT: must not float; 0.1 uF + 10 uF to 3V3. VDD_ANA, VDD_LP, VDD_IO_0/4/5/6: 0.1 uF each.
- VDD_IO_5 (SDIO pin domain) is tied to 3V3; no SD-card voltage switching.
- CHIP_PU: 10 k pull-up and 1 uF, must not float, rails stable at least 50 us before it rises.
- Strapping pins GPIO34-38. GPIO35 = 1 selects SPI boot. GPIO35 = 0 with GPIO36 = 1 selects
  download. Pull-up on GPIO35, no large capacitor on it.
- Crystal: 40 MHz, within 10 ppm. Load capacitors tuned on the prototype.
- Flash: quad SPI on the dedicated FLASH_* pins, 0R series footprints, pull-up on CS, 0.1 uF.
- DSI_REXT: 4.02 k to ground. CSI_REXT footprint only (DNP).
- USB: USB-Serial-JTAG on GPIO24 (D-) and GPIO25 (D+), series 22R. High-speed PHY on its dedicated
  pins, ESD capacitance at most 1 pF, optional 1 M on DP.
- RMII: series resistor on the 50 MHz clock at its source.
- ADC inputs: 0.1 uF at the pin.
- Minimum supply current without peripherals: 430 mA.

Pin assignment: `hardware/inputs/maratus-core-gpio-map.csv` (105 pads, all assigned).

## 5. Wi-Fi coprocessor

- ESP-Hosted over 4-bit SDIO on P4 SDMMC slot 0, IO MUX pins: CLK GPIO43, CMD GPIO44, D0-D3
  GPIO39-42. C5 side is fixed: CLK GPIO9, CMD GPIO10, D0 GPIO8, D1 GPIO7, D2 GPIO14, D3 GPIO13.
- 51 k pull-ups to 3V3 on CMD and D0-D3. Series resistor footprints on all six lines, DNP
  capacitor footprint on CLK.
- `C5_EN` from P4 GPIO45 (10 k pull-up, 1 uF at the module). `C5_BOOT` from GPIO46 to C5 GPIO28.
  UART0 of the C5 to P4 GPIO47/48, so the P4 can flash a blank C5. Confirm the C5 boot-strap
  levels in the module datasheet, table "Boot Mode Control".
- C5 straps GPIO25 and MTDI set the SDIO sampling edge and float by default: fit DNP pull-up and
  pull-down footprints on both.
- Module supply: 10 uF + 0.1 uF at the pin; the 3V3 rail must deliver 0.6 A to the module.
- Module pin map: `hardware/inputs/maratus-core-c5-pin-map.csv`.
- Firmware notes carried over: coprocessor image version must match the host; SDIO buffers stay
  in internal RAM.

## 6. Ethernet

- IP101GRI on the Core, RMII, 25 MHz crystal, PHY supplies the 50 MHz reference to P4 GPIO50.
- Pins: TX_EN GPIO49, TXD0 GPIO34, TXD1 GPIO35, CRS_DV GPIO28, RXD0 GPIO29, RXD1 GPIO30,
  MDC GPIO31, MDIO GPIO52 (1.5 k pull-up), reset GPIO51. Same as the Waveshare P4 dev kit, which
  uses PHY address 1.
- GPIO23 to the PHY clock input through a DNP 0R (option to drop the crystal later).
- The four MDI lines (TX+, TX-, RX+, RX-) go to the rear pads through a low-capacitance ESD
  array. Magnetics and RJ45 are in the accessory. Confirm in the IP101G datasheet that the
  transformer centre taps need no supply from the Core.
- PHY is held in reset unless the accessory ID says an Ethernet accessory is attached.

## 7. Rear contact field (P1)

18 circular gold pads, 2 rows of 9, 2.54 mm pitch along the row, 3.5 mm between rows, on the rear
face of the PCB. No vias in pads. Pad diameter 2.0 mm (assumption of 2026-11-10, leaves a 0.54 mm
gap; confirm against the Dock's spring pins). Footprint `maratus:RearPads_2x9_P2.54mm_D2.0mm`,
generated by `tools/maratus_lib.py`.

| Pad | Row A | Row B |
| --- | --- | --- |
| 1 | GND | VIN (5 V in) |
| 2 | ETH_TX_P | VIN (5 V in) |
| 3 | ETH_TX_N | GND |
| 4 | GND | ACC_ID |
| 5 | ETH_RX_P | ACC_IO1 |
| 6 | ETH_RX_N | ACC_IO2 |
| 7 | GND | ACC_INT_N |
| 8 | ACC_USB_DP | GND |
| 9 | ACC_USB_DN | V_ACC (5 V out) |

- ACC_ID: 10 k pull-up to 3V3 on the Core, series 10 k and clamp before the ADC pin, 0.1 uF.
- ACC_IO1, ACC_IO2, ACC_INT_N: 100R series, ESD array, 10 k pull-ups to 3V3.
- USB pair: ESD array with at most 1 pF, routed as a 90 ohm pair.
- VIN: TVS, then mux IN1. V_ACC: from U9, off by default.

| Accessory | ID resistor to GND | ACC_ID voltage |
| --- | --- | --- |
| None | open | 3.30 V |
| Dock | 1.0 k | 0.30 V |
| LAN module | 2.2 k | 0.60 V |
| Battery module | 4.7 k | 1.06 V |
| Outdoor mount | 10 k | 1.65 V |
| Smart accessory (details over I2C) | 22 k | 2.27 V |
| Factory test jig | 47 k | 2.72 V |

## 8. Display and touch

- Panel: Newhaven NHD-4.0-480480AF-MSXP-CTP, chosen 2026-11-10. 4.0-inch 480 x 480 IPS, ST7701SN,
  2-lane MIPI DSI, FT5426G touch over I2C, 850 cd/m2, outline 77.86 x 81.84 x 4.15 mm. Reason: the
  full datasheet is public and the maker's shop listed 1190 pieces in stock that day. Datasheet:
  `docs/reference/NHD-4.0-480480AF-MSXP-CTP.pdf` (PDF pages: 4 drawing, 5 pin tables, 6 ratings,
  7 DSI timing, 15 and 17 reset and power-on timing, 18 touch address).
- It replaces the 720 x 720 ST7703 + GT911 class (Startek KD040HDFID032-C026C), which has no public
  datasheet. Firmware has to move to 480 x 480, `espressif/esp_lcd_st7701` (lists MIPI-DSI and
  esp32p4) and an FT5x06-family touch driver. FT5426G with `espressif/esp_lcd_touch_ft5x06` is not
  confirmed. The ST7701SN init sequence for this glass is not in the datasheet.
- J2, LCD FFC, 24 pins at 0.5 mm: 1 LED_K, 2 LED_A, 3 NC, 4 VDD, 5 GND, 6 DN0, 7 DP0, 8 GND, 9 CN,
  10 CP, 11 GND, 12 DN1, 13 DP1, 14 GND, 15 RESETX, 16 CSX, 17 SCL, 18 SDA, 19 SDO, 20 TE_L,
  21 IM0, 22 IM1, 23 IM3, 24 LANSEL (datasheet p.5).
- Mode straps for MIPI DSI with 2 data lanes: IM0 high, IM1 low, IM3 low (datasheet p.5), LANSEL
  high (`docs/reference/ST7701S_SPEC_V1.4.pdf` p.39). Unused SPI pins: CSX high, SCL and SDA low,
  SDO open (same file, p.37-38). TE_L goes to a test point.
- J4, touch FFC, 6 pins at 1.0 mm: 1 VDD, 2 GND, 3 SCL, 4 SDA, 5 INT, 6 RST. I2C address 0x38
  (0x70 write, p.18). 4.7 k pull-ups on SCL and SDA (p.5).
- Connectors: as read from the p.4 drawing, the LCD tail has its contacts on the display-front
  side and the touch tail on the back side. Both tails are 30 mm long, wrap around the PCB's bottom
  edge and lie on the rear face, so J2 is top-contact and J4 bottom-contact, both with the opening
  towards the bottom edge. In that position panel pin 1 is on the right and the footprints' pad 1
  on the left, so the pin order is reversed: J2 pad n = panel pin 25 - n, J4 pad n = touch pin
  7 - n. Confirm all of this on a sample before ordering boards.
- J2 is an Amphenol F32Q-1A7H1-11024 (top contact per the DigiKey listing) because KiCad has its
  footprint; its datasheet is not in `docs/reference` and its FFC thickness is not confirmed. The
  panel datasheet names a Molex 52435-2471, which has no KiCad footprint. J4 is a TE 84952-6
  (bottom contact, 0.3 mm FFC, active per te.com) in place of the Molex 52271-0679.
- Supplies (p.6): panel VDD 3.3 V, 43 mA typical, 65 mA max. Touch 3.3 V, 15.85 mA. Backlight
  6.1 V typical (5.4-6.8 V) at 140 mA, 168 mA max.
- U8: TPS61169 fed from 3V3, 4.7 uH, RSET 1.5 ohm (125 / 136 / 147 mA over the feedback voltage
  range). It is not fed from 5V_SYS: `docs/reference/tps61169.pdf` p.9 requires the LED array's
  minimum forward voltage above the maximum input voltage, or the LEDs glow in shutdown. A 100 k
  resistor discharges the output after an open-LED shutdown (output reaches 36-39 V).
- DSI timing values (p.7): H total 790, front porch 150, back porch 150, sync 10; V total 530,
  front porch 20, back porch 20, sync 10; pixel clock 25 MHz.
- Core-side nets: DSI clock and two data pairs, `LCD_RST_N` GPIO3, `LCD_BL_PWM` GPIO2,
  `TP_RST_N` GPIO4, `TP_INT` GPIO5, `I2C0_SDA` GPIO7, `I2C0_SCL` GPIO8.

## 9. Other blocks

- Buzzer: Same Sky (CUI) CMT-8504-100-SMT, rated 5 V, 4 kHz, 100 dB at 10 cm, 150 mA max, fed from
  5V_SYS. AO3400A low-side driver, MBR0540 flyback diode, gate from `BUZZER_PWM` (GPIO6) with
  100 k pull-down. A pin held high puts 5 V on a 12-18 ohm coil: firmware must only ever drive PWM.
- Service switch: `SERVICE_BTN_N` on GPIO9, 10 k pull-up, reachable only with a pin tool.
- Test pads: P4_EN, BOOT (GPIO35), UART0 TX/RX, C5 EN/BOOT/UART0, all rails, every spare GPIO.
- Camera: 15-pin 1.0 mm FFC footprint (TE 1-84952-5) on the CSI pins, not populated. Pin order of
  the Espressif EV board J9; the Waveshare board uses the same order.

## 10. PCB (draft layout, generated 2026-11-10)

Generated by `tools/pcb.py` from the netlist; constants in `tools/mech.py`. Regenerating overwrites
any manual edit of `hardware/core/maratus-core.kicad_pcb`.

- Outline 76.0 x 96.5 mm, 1.2 mm, 4 layers, corner radius 2 mm, four 2.2 mm holes for M2 screws.
  This replaces the earlier 78 x 82 mm limit: the board now carries the antenna above the panel
  (8 mm) and the screw bosses below it (6.7 mm).
- KiCad's top side is the device's rear face. Every part is on that side; the other side lies
  against the LCD's metal back behind 0.6 mm of foam and carries tracks only.
- Layers: F.Cu signals and parts, In1.Cu GND plane, In2.Cu 3V3 plane, B.Cu signals. GND pours on
  both outer layers. The script adds a short stub and a via next to every GND and 3V3 pad (243
  vias), because the autorouter does not connect pads to planes.
- Cut-outs: 26 x 7 mm in the top edge under the C5 module's antenna (Espressif ESP32-C5 hardware
  design guidelines, "Positioning a Module on a Base Board"), and two 2.5 mm notches in the bottom
  edge where the FFC tails wrap around the board (14 mm for the LCD tail, 8.6 mm for touch).
- Rules: 0.09 mm clearance, 0.1 mm tracks, 0.4 / 0.2 mm vias; power nets 0.2 mm tracks and
  0.45 / 0.2 mm vias. The fan-out of the P4 (0.35 mm pitch) did not complete with 0.1 mm
  clearance and 0.45 mm vias. 0.2 mm is the widest track that enters the P4's pads, so the supply
  tracks (VDD_HP above all) are thinner than they should be and need copper areas drawn by hand.
  All of these are assumptions to check against the chosen fabricator's limits and prices. No
  stack-up with dielectric thicknesses is defined, so no impedance is controlled.
- Fixed positions: C5 module top centre, P4 in the middle with its DSI pins facing J2, J2 and J4
  76 mm from the top with their openings down, USB-C on the bottom edge at x = 17 mm, rear pads P1
  centred at (59, 34), PHY between the P4 and P1, buzzer at (51.5, 88). Everything else is placed
  by the script next to the IC pin it connects to.
- Routing is the Freerouting autorouter's, unedited. It does not route differential pairs as
  pairs, match lengths or follow Espressif's layout guide for DSI, USB, RMII, SDIO, the crystal or
  the core DCDC loop. A layout engineer has to redo those nets before any board is ordered.
- The P4's DSI clock pins are in the opposite order to the panel's (CLK_N, CLK_P against CLK_P,
  CLK_N at J2), so that pair has to cross on a second layer.
- Result of 2026-11-10 (`reports/drc.rpt`): 0 unconnected pads, 0 schematic parity errors, 2
  warnings (the module's silkscreen is clipped at the antenna cut-out). 2468 track segments on
  F.Cu and B.Cu, 675 vias. As routed, the accessory USB pair is 76.2 mm and 56.0 mm long with 6
  and 5 vias, ETH_RX is 25.1 mm and 16.3 mm, and each DSI pair is about 20 mm with up to two
  vias per line. Those numbers are why the fast nets must be rerouted by hand.
- Outputs of `python3 tools/pcb.py fab` (not in git): Gerbers and drill files in
  `out/fab/gerber`, `out/fab/maratus-core-pos.csv`, renders, and the board's STEP model in
  `mechanical/core/maratus-core-pcb.step`. They exist to check the flow, not to order boards.

## 11. Open items

1. Panel samples, ST7701SN init sequence, FFC fold direction and pin order on a sample, and the
   J2 connector's datasheet (section 8).
2. Body shape: taller body with PCB antenna, decided 2026-11-10. RF range is unproven (section 12).
3. Flash: boot test on the prototype (pins and QE bit are verified on paper).
4. 5V_SYS over-voltage window: the mux lockout trips at 5.48 / 5.75 / 5.97 V, while U5 is
   recommended to 5.5 V (6 V absolute) and the buzzer to 6.0 V. A reviewer has to decide whether
   to lower the lockout. Backlight: confirm TPS61169 on the prototype.
5. Ethernet through pogo contacts is unproven until a prototype passes a 24-hour soak.
6. Rear pad diameter (2.0 mm assumed) against the Dock's spring pins.
7. ERC has 2 known `pin_to_pin` warnings: Espressif's symbol types VDD_ANA and VDD_BAT (U1 pins
   101, 102) as bidirectional, and they sit on 3V3, which carries a PWR_FLAG. Not a wiring fault.

## 12. Enclosure (prototype geometry, generated 2026-11-10)

Generated by `tools/enclosure.py` (build123d) into `mechanical/core/`: STEP and STL for the front
shell and the rear cover, plus an assembly STEP. It is geometry for a 3D-printed fit check, not a
tooling design: no draft angles, no snap fits, no sealing, no strength analysis.

- Outside 82.2 x 101.0 x 13.05 mm. Taller body with the module's PCB antenna above the panel.
- Stack from the front: 1.0 mm bezel lip, panel 4.15 mm, 0.6 mm foam, PCB 1.2 mm, 4.5 mm for
  parts (buzzer 4.0 mm), 1.6 mm rear cover.
- Front shell: bezel window over the touch viewing area (72.86 x 71.18 mm plus 0.3 mm), panel
  stops at its top and bottom edges, four bosses that carry the PCB, USB-C opening in the bottom
  wall with a pocket for the plug's overmould. The receptacle's front is flush with the PCB edge,
  so the plug stops about 1.0 mm short of it: check plug retention on the printed part.
- Rear cover: four posts that clamp the PCB onto the bosses, window over the rear pads P1, seven
  1.3 mm sound holes over the buzzer, a 1.6 mm pin hole over the service switch.
- Four M2 x 10 thread-forming screws from the rear, through cover posts and PCB into the bosses.
- Checked in CAD: no overlap between shells, panel and the board's STEP model; the tallest
  modelled part is 3.3 mm, 1.2 mm below the cover. The C5 module, the buzzer and J2 have no 3D
  model and are not in that check.
- Open: the rear pads sit 6.1 mm below the rear surface, so the Dock needs a contact block that
  reaches into the window. No magnets, no Dock interface, no gasket. The antenna has 1 mm to the
  LCD's metal back where Espressif recommends 15 mm of clearance: RF range must be measured, and
  the alternative is the ESP32-C5-WROOM-1U with an external antenna.
