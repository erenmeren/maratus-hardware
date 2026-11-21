# Maratus Core — design specification for schematic capture

Phase 0 decisions in schematic-ready form, dated 2026-11-09. "Verified" means read from the named
source on that date. "Confirm" means it must be checked against the datasheet before it is drawn.

## 1. Product

An always-powered 4-inch touchscreen that shows a cloud-triggered QR code. HTTPS for bootstrap and
OTA download, MQTT over TLS for everything else (`maratus-admin/docs/device-protocol.md`). The
current firmware runs on a Waveshare ESP32-P4-WIFI6-Touch-LCD-4B (ST7703 720x720 panel, GT911
touch, ESP32-C6 over SDIO, P4 silicon v1.0, ESP-IDF 5.5).

Sleep mode (owner, 2026-11-13): the product will have one and it matters to him. Decided the same
day: the P4 does not sleep. Sleep means the screen off with the P4 awake and connected, on Wi-Fi
and on Ethernet; on Ethernet the C5 can be shut down as well, on request. Reasons and open points
are in section 11 item 12. The wake-up line from the C5 (section 5) stays on the board, unused.

## 2. Main parts

| Ref | Part | Status | Open this source |
| --- | --- | --- | --- |
| U1 | ESP32-P4NRW32X (chip revision v3.x, QFN104) | Verified | Espressif P4 datasheet; chip revision v3.x user guide |
| U2 | ESP32-C5-WROOM-1U-N4 (external antenna) | Verified | Espressif C5 module datasheet |
| ANT1 | Taoglas FXP830.07.0100C flex antenna, 42 x 7 mm, 100 mm cable, I-PEX MHF I | Candidate; 5 GHz gain above the module's certified limit | `docs/reference/FXP830.07.0100C.pdf` |
| U3 | 16 MB quad SPI NOR, 3.3 V (W25Q128JVSIQ) | Pins and QE bit verified; boot test on the prototype | Winbond datasheet p.75-76; Espressif design guidelines p.15 |
| U4 | TLV62569 buck for VDD_HP | Verified as an Espressif-listed DCDC | TI datasheet; P4X reference schematic |
| U5 | TLV62569 buck, 5 V to 3.3 V, 2 A | Verified: 2.5-5.5 V in, 6 V absolute; see section 11 item 4 | TI datasheet p.3-4 |
| U6 | TPS2121RUXR power mux | Verified | TI datasheet |
| U7 | IP101GRI Ethernet PHY, QFN-32 | Verified | IC Plus IP101G datasheet |
| U8 | TPS61169 backlight boost LED driver, fed from 3V3 | Candidate | TI TPS61169 datasheet; section 8 |
| U9 | TPS2553DBV 5 V switch for V_ACC, limit 524 / 577 / 638 mA | Verified | TI TPS2553 datasheet p.16-17 |
| U10 | TPS3839K33 reset supervisor, 2.93 V, 200 ms | Verified | TI TPS3839 datasheet p.1, p.4 |
| J1 | USB-C receptacle, USB 2.0, 16-pin, GCT USB4105-GF-A | Verified | GCT drawing p.1 |
| J2 | LCD FFC connector, 24-pin 0.5 mm, bottom contact (Hirose FH12-24S-0.5SH(55)) | Footprint from KiCad; Hirose datasheet not read | Newhaven panel datasheet p.4; DigiKey listing |
| J4 | Touch FFC connector, 6-pin 1.0 mm, top contact (TE 84953-6) | Footprint from KiCad; availability unclear | Newhaven panel datasheet p.5; te.com product page |
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
- Host wake-up, added 2026-11-13 for the sleep mode: `C5_WAKE` from C5 GPIO2 through R317 (0 ohm)
  to P4 GPIO0. GPIO0-15 are the P4's LP pins (datasheet section 2.3.2), the ones that work in deep
  sleep. ESP-Hosted's host power save (its `docs/features/power-save.md`, read 2026-11-13): the C5
  keeps the network up and drives this line, level high by default, when the host is needed; the
  host pin has to be RTC-capable; C5 GPIO2 is its default for the P4X-C5 board on SDIO. Only deep
  sleep of the host is implemented there, so the P4 reboots on every wake; its
  `docs/features/network-split.md` decides which packets wake it. Espressif's P4X-C5 EV board
  (`C5_IO2`, `P4_WAKEUP_C5`) and Waveshare's ESP32-P4-NANO-WIFI6-DB (R18, to P4 GPIO6) have the
  same link. No pull resistor, as on both: MTMS is listed as a strapping pin of the C5 (module
  datasheet p.16). GPIO0 is one of the two 32 kHz crystal pins, so that crystal can no longer be
  added; GPIO1 is the last free LP pin. Unused since the owner decided on 2026-11-13 that the P4
  does not sleep (section 11 item 12); R317 stays fitted as an option for a later version.
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

Since 2026-11-19 (owner) P1 is a part: Promax NF6268-20PA, the flat-contact half of a standard
pair whose spring-pin half NC6268-20PA goes on the Dock (`docs/reference/promax_NF6268-20PA.pdf`
and `promax_NC6268-20PA.pdf`, p.1 each). 20 gold-plated contacts, 2 rows of 10, 3.00 mm pitch,
rows 2.40 mm apart; 2.0 A max at 12 V DC and 50 mOhm a contact; the spring side has 1.40 mm
working stroke, 45 gf a pin and 50,000 cycles. Housing 50.40 x 7.40 x 2.50 mm with round ends
and a 38.00 x 5.50 mm raised part 1.00 mm higher (3.50 mm in all), through-hole pins of 1.10 mm
that come out 1.90 mm on the part side. It stands on the board's back: the raised part goes
through the floor and the contact faces end 0.10 mm behind the rear face (3.6 mm between the
board and the rear face). Footprint `maratus:Promax_NF6268-20PA`, generated by
`tools/maratus_lib.py`; its 1.3 mm holes and 1.9 mm pads are assumptions, the drawing gives no
PCB layout (asked of Promax on 2026-11-19). The STEP model Promax sent under this name is
another part (NF1158-20PA, 4.5 mm high); asked for the right one. Until that day P1 was a field
of 18 round 2.0 mm pads on the board (2 x 9, 2.54 mm, rows 3.5 mm apart), behind a 3.6 mm deep
window in the floor.

Position: centre at x = 37.0, y = 66.0 mm on the board, long axis horizontal (owner,
2026-11-14). Seen from the Core's front, row A is the upper row (y = 64.8 mm), row B the lower
(y = 67.2 mm), contact 1 is on the right (x = 50.5 mm) and contact 10 on the left (x = 23.5 mm);
seen from the back, contact 1 is on the left. The pins of contacts 9 and 10 come through where
the buzzer stood until 2026-11-19; it moved up to (25.8, 58.5). The two spare contacts A10 and
B10 are GND.

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
| 10 | GND | GND |

- ACC_ID: 10 k pull-up to 3V3 on the Core, series 10 k and clamp before the ADC pin, 0.1 uF.
- ACC_IO1, ACC_IO2, ACC_INT_N: 100R series, ESD array, 10 k pull-ups to 3V3.
- USB pair: ESD array with at most 1 pF, routed as a 90 ohm pair.
- VIN: TVS, then mux IN1. V_ACC: from U9, off by default.

| Accessory | ID resistor to GND | ACC_ID voltage |
| --- | --- | --- |
| None | open | 3.30 V |
| Dock | 1.0 k | 0.30 V |
| LAN module | 2.2 k | 0.60 V |
| USB and UART module (added 2026-11-13) | 3.3 k | 0.82 V |
| Battery module | 4.7 k | 1.06 V |
| UART module (added 2026-11-13) | 6.8 k | 1.34 V |
| Outdoor mount | 10 k | 1.65 V |
| USB module (added 2026-11-13) | 15 k | 1.98 V |
| Smart accessory (details over I2C) | 22 k | 2.27 V |
| Factory test jig | 47 k | 2.72 V |

### Modules on the rear pads (owner, 2026-11-13: later modules such as a scanner or a camera have to work)

The Core itself stays without camera, scanner and NFC (V1 scope). The 20 contacts already carry what
such modules need, so the pad table above is kept as it is. None of it is tested.

| Module needs | Pads | Limits |
| --- | --- | --- |
| Power from the Core | V_ACC, GND | 5 V, off until ACC_ID is read; U9 limits at 524 to 638 mA, so a module may take 0.5 A |
| Power into the Core | VIN x 2, GND | 5 V; a module that needs more than 0.5 A powers itself and may feed the Core here |
| UART | ACC_IO1 (Core transmits, GPIO10), ACC_IO2 (Core receives, GPIO11) | 3.3 V logic; UART1 on the P4's IO MUX (datasheet Table 2-3) |
| I2C | ACC_IO1 (SDA), ACC_IO2 (SCL) | instead of the UART, not beside it; 10 k pull-ups on the Core, a module adds its own for 400 kHz |
| Interrupt or trigger | ACC_INT_N (GPIO12) | either direction, 3.3 V logic |
| USB | ACC_USB_DP, ACC_USB_DN, V_ACC as the 5 V supply | Core is the host on the P4's high-speed controller |
| Ethernet | the four MDI pads | transformer in the module (section 6) |

- USB host, from Espressif's USB host documentation for the P4 (docs.espressif.com/projects/esp-usb,
  read 2026-11-13): high-, full- and low-speed devices work directly on the port. One hub is
  supported, more with an option, but the hub driver has no transaction translator: behind a hub
  only high-speed devices work, unless the port runs as a full-speed-only host. Class drivers
  Espressif publishes (its esp-usb repository, `host/class`): CDC, HID, MSC, UAC, UVC.
- Scanner: UART (transmit, receive, trigger on ACC_INT_N) or USB. Example read on 2026-11-13,
  Waveshare's Barcode Scanner Module (user manual V2.1 and pin sheet): 5 V, 210 mA operating, UART
  and USB, trigger input active low, 3.3 V scan engine.
- Camera: USB only (UVC class). MIPI CSI cannot go through spring pins; the unfitted connector
  J3 on the board is the place for a CSI camera.
- NFC reader: I2C with ACC_INT_N, or UART.
- Sensors (owner, 2026-11-14: humidity, CO2 and sound are possible later): parts that speak I2C
  share ACC_IO1/ACC_IO2 with each other, each on its own address. A microphone does not use
  I2C: it needs the two IO lines for itself (then no I2C beside it), a USB audio device (UAC
  class), or the module's own microcontroller. No part is chosen. Examples read on 2026-11-14
  from the makers' datasheets, to see whether such parts fit the pads:

  | Part | Bus | Supply | Current | Source |
  | --- | --- | --- | --- | --- |
  | Sensirion SHT4x, humidity and temperature | I2C, address 0x44, 0x45 or 0x46 by order code | 1.08 to 3.6 V | 0.4 uA average | datasheet V7.3 p.1, p.9 |
  | Sensirion SCD4x, CO2 | I2C, address 0x62 | 2.4 to 5.5 V; inputs need 0.65 x VDD for a high | 15 mA average, 175 mA peak (205 max) at 3.3 V | datasheet V1.5 p.4, p.7 |
  | NXP PN532, NFC reader | I2C, SPI or UART, interrupt pin; address not read | 2.7 to 5.5 V, interface pads 1.6 to 3.6 V | 25 mA digital, 6 mA analog, 60 mA transmitter (150 max) | data sheet rev. 3.2 p.4 |
  | Infineon IM69D130, microphone | PDM: clock and data, 0.4 to 3.3 MHz | 1.62 to 3.6 V | 0.98 mA (1.3 max) | datasheet p.7, p.8 |

  What follows for a module: the addresses do not collide, so humidity, CO2 and NFC share the
  two I2C pads. All four are 3.3 V parts on their bus side and the pads carry 5 V only, so a
  module has its own 3.3 V regulator; the SCD4x has to run from 3.3 V, because at 5 V it wants
  3.25 V for a high and the Core pulls the lines to 3.3 V. The Core's 10 k pull-ups are live
  before V_ACC is switched on. The microphone fits the P4: three I2S ports with a PDM receive
  mode, and the PDM-to-PCM converter on I2S0 (ESP-IDF I2S page for the P4, read 2026-11-14).
  CO2 sensor, NFC reader and the scanner of the example above at their maxima together are
  about 0.6 A, more than V_ACC gives; a Dock feeds them from its own input.
- Dock with an NFC reader and a barcode scanner (owner, 2026-11-14: the Core has to be ready
  for it): fits the 18 pads, nothing is added to the Core. Power and Ethernet as today. NFC
  reader on I2C with ACC_INT_N. Scanner on USB, a full-speed device directly on the port (HID
  or CDC class), triggered by a command or by its own sensing because the interrupt line is
  taken. An I2C memory for the smart-accessory class can share the bus with the NFC reader.
  Such a Dock can feed its parts from its own 5 V input, so V_ACC's 0.5 A does not limit them.
  A camera on top of these two needs the microcontroller of the next point.
- A module with several functions: camera on USB, everything else behind the module's own
  microcontroller on the UART. I2C and UART at the same time, or a second USB port, would need
  two more pads (the P4's full-speed controller on GPIO26/27 is free, on test pads). Not done:
  it changes the pad field, the housing's window and the Dock's boards. Since 2026-11-14 the
  field lies horizontal with 25.8 mm of board beyond each end.
- The Dock contacts 12 of the 18 pads; USB, the IO lines and V_ACC get no pin there (section 13).
  Owner, 2026-11-14: for now a module takes the Dock's place with its own contact board; later
  a Dock and a module should work together. The Core needs nothing more for that: the Dock's
  signals (VIN, GND, Ethernet) and the module's (USB, IO, interrupt, V_ACC) are on different
  pads. Only ACC_ID is shared, so a Dock with a module needs an ID value of its own or the
  smart-accessory class. That later Dock needs the six missing pins, six more holes in the
  saddle, a connector for the module and more than the harness's 8 wires. Nothing is designed
  for it.
- Open: high-speed USB through spring pins is unproven; V_ACC's voltage at 0.5 A (it comes from
  5V_SYS through the mux and U9); firmware has no accessory code yet.

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
  side and the touch tail on the back side. Both tails are 30 mm long. The board's part side faces
  the display and the tails fold back around the panel's bottom edge onto it, so J2 is
  bottom-contact and J4 top-contact, both with the opening towards the bottom edge, 20 mm above
  it. Seen from the front, panel pin 1 and the footprints' pad 1 are both on the left, so the
  pins are in panel order. Confirm all of this on a sample before ordering boards.
  Samples arrived 2026-11-14. The owner's first check that day, by eye: with the screen facing
  him the wide (LCD) tail faces him and the 6-pin (touch) tail faces away, which is the contact
  side assumed above, so J2 stays bottom-contact and J4 top-contact. Also from him that day:
  the short (touch) tail is on the left and the wide one in the middle; folded back, the tails
  reach 20 mm up the back; their length is 3 cm (he first wrote "3 mm" and
  confirmed 3 cm the same day). He says his sample
  looks like DigiKey's product photo of this part, and that photo (viewed 2026-11-14) shows the
  wide tail's contacts from the front with "1" printed at its left end and "24" at its right:
  pin 1 on the left, as assumed. The sample also went into his printed body and seated fully
  (owner, 2026-11-14), so the outline of the p.4 drawing holds for the fit. Pin 1 of the touch
  tail is on the left too, seen from the front (owner, same day). On the board, read from the
  file that day: pad 1 of J2 is at x = 31.3 mm and pad 24 at 42.8 mm, pad 1 of J4 at 9.87 mm
  and pad 6 at 14.87 mm, so pad 1 is on the left for both, as on the tails. The
  tails' offsets from the panel's left edge (drawing: 32.68 mm for the LCD tail and 10.75 mm
  for the touch tail, `tools/mech.py`): the owner measured them on a sample that day and says
  they match; he gave no numbers. Not checked: a tail in a real connector.
- J2 is a Hirose FH12-24S-0.5SH(55) (bottom contact, 0.30 mm FFC, active per the DigiKey
  listing; Hirose's own datasheet is not in `docs/reference`). J4 is a TE 84953-6 (top contact,
  0.3 mm FFC per te.com, which also says it is not currently available). The panel datasheet
  names Molex 52435-2471 and 52271-0679; neither has a KiCad footprint.
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
  Since 2026-11-14 (owner: no hole for it in the rear, make it look like one of the holes beside
  the buzzer's) SW701 is the side-actuated Omron B3U-3000P (`b3u_omron.pdf` p.1 and p.3: body
  3 x 2.5 x 1.2 mm, plunger 0.7 mm beyond the body, 1.59 N) on the part side at the bottom edge,
  at (18.7, 69.5) with its plunger 0.5 mm inside the board edge. It is pressed through a slot in
  the bottom wall, the fourth in the row of the buzzer's three (section 12). Before that day it
  was the top-actuated B3U-1000P on the back, pressed through a hole in the floor.
- Test pads: P4_EN, BOOT (GPIO35), UART0 TX/RX, C5 EN/BOOT/UART0, all rails, every spare GPIO.
- Camera: 15-pin 1.0 mm FFC footprint (TE 1-84952-5) on the CSI pins, not populated. Pin order of
  the Espressif EV board J9; the Waveshare board uses the same order.

## 10. PCB (draft layout, slim version generated 2026-11-10)

Generated by `tools/pcb.py` from the netlist; constants in `tools/mech.py`. Regenerating overwrites
any manual edit of `hardware/core/maratus-core.kicad_pcb`.

- Outline 74.0 x 72.0 mm, 1.2 mm, 4 layers, corner radius 2 mm, four 2.2 mm holes for M2 screws.
  Since 2026-11-14 the bottom edge has a tab, 12.0 mm wide and 1.2 mm long, centred on x = 57.0:
  the USB-C receptacle J1 stands on it, its mouth on the tab's edge at y = 73.2 (section 12).
  The tab's inner corners are drawn square.
  The board is smaller than the panel and sits entirely behind it.
- KiCad's top side faces the display and carries the parts. The back faces the housing floor and
  carries only the rear contact pads P1 (long axis horizontal near the bottom edge since
  2026-11-14; the placer keeps parts off the part side above it, only the buzzer's two right
  pads lie over its left end). Since 2026-11-14 no part is on the back: the service switch
  SW701 moved to the part side.
- Layers: F.Cu signals and parts, In1.Cu GND plane, In2.Cu 3V3 plane, B.Cu signals. GND pours on
  both outer layers. The script adds a short stub and a via next to every GND and 3V3 pad, because
  the autorouter does not connect pads to planes.
- Rules: 0.09 mm clearance, 0.1 mm tracks, 0.4 / 0.2 mm vias; power nets 0.2 mm tracks and
  0.45 / 0.2 mm vias. The fan-out of the P4 (0.35 mm pitch) did not complete with 0.1 mm
  clearance and 0.45 mm vias. 0.2 mm is the widest track that enters the P4's pads, so the supply
  tracks (VDD_HP above all) are thinner than they should be and need copper areas drawn by hand.
  All of these are assumptions to check against the chosen fabricator's limits and prices. No
  stack-up with dielectric thicknesses is defined, so no impedance is controlled.
  Held against JLCPCB's pages on 2026-11-16 (`docs/layout-brief.md`): track and space are at
  its 0.09 mm limit, vias under 0.45 mm cost more (674 of 734), and the 0.15 mm hole clearance
  and the 0.1 mm edge clearance at J1 are below its 0.2 mm. The same brief holds the draft's
  routed lengths against Espressif's layout rules: none of the fast groups meets them (DSI
  pairs up to 72 mil apart inside a pair, SDIO data up to 1148 mil longer than the clock, vias
  on the crystal's traces). The owner decided that day that a person lays out the critical nets
  before a board is ordered.
- Fixed positions: C5 module top left and turned so that its SDIO pins face the P4 (the 1U module
  has no antenna of its own, so its orientation is free), P4 upper middle with its DSI pins facing J2, J2 and J4
  with their openings 52 mm from the top edge, USB-C on the bottom edge at x = 57 mm, PHY right of
  the P4, camera connector (DNP) on the right edge, buzzer at (23.5, 62) (at (25.8, 58.5) since 2026-11-19). Everything else is
  placed by the script next to the IC pin it connects to. No parts lie under the two FFC tails.
- Routing is the Freerouting autorouter's, unedited. It does not route differential pairs as
  pairs, match lengths or follow Espressif's layout guide for DSI, USB, RMII, SDIO, the crystal or
  the core DCDC loop. A layout engineer has to redo those nets before any board is ordered.
- Result of 2026-11-10 (`reports/drc.rpt`): 0 DRC violations, 0 unconnected pads, 0 footprint
  errors, 0 schematic parity issues; 2856 track segments and 734 vias. It took `route 40` and then
  `finish 12 free`: with the module the other way round 9 connections stayed open, and the last
  one (SDIO_D3 at P4 pad 83) only closed when the router was allowed a via under the P4. Two
  signal layers are full around the P4; the result changes from run to run. A layout engineer may
  well want six layers or fewer test pads.
- Ground test pad, 2026-11-13: TP104 (GND) was added in the power sheet and put on the routed
  board at (65.0, 7.5) on the front ground pour by a one-off script, without placing or routing
  again. `reports/drc.rpt` of that day: 0 violations, 0 unconnected pads, 0 footprint errors,
  0 schematic parity issues; ERC as before (the 2 known warnings). The board before that is
  `out/pcb/routed-2026-11-10.kicad_pcb`. A new `place` puts TP104 somewhere else.
- Rear pads turned, 2026-11-14 (section 7): placed and routed again from the scripts. Changes in
  `tools/pcb.py`: P1 at rotation 0 on its new centre; a keep-out over the pad field for placed
  parts (a part above the pads finds no room for its plane vias: at mid-height C106 and then U6
  lost their ground via); TP104 has no net to follow, so it is placed last at the free spot
  nearest to (65.0, 7.5) and is now at (71.3, 7.85). It took `route 40` and `finish 12 free`,
  which left one connection open: the USB-C receptacle's two D+ pads (J1 A6 and B6), because the
  router had run VBUS right under the pad row. A one-off script moved that VBUS run 0.4 mm down
  and drew the D+ bridge between the pads and it. Result (`reports/drc.rpt`, created
  2026-11-14T17:27): 0 DRC violations, 0 unconnected pads, 0 footprint errors, 0 schematic parity
  issues; 2739 track segments and 736 vias. `tools/check_netlist.py`: 66 checks, 0 failed. The
  board before the change is `out/pcb/routed-2026-11-10.kicad_pcb` plus the two script edits of
  2026-11-13; it is not kept in the repo. The Ethernet pairs and the accessory USB pair to the
  pads are new autorouted tracks like the rest: not routed as pairs.
- Service switch moved, 2026-11-14 evening (section 9). A full `place` and `route` with the
  switch at its new place left 4 to 21 connections open in five router runs (via cost 15, 25,
  35, 50; `finish` changed nothing), although SW701 was the only part that had moved. So the
  board of the afternoon was kept and patched by a one-off script: SW701 swapped for the
  B3U-3000P at (18.7, 69.5), the old branch of `SERVICE_BTN_N` and the old ground stub removed
  (25 tracks and vias), the plane fan-out of its ground pad added, and only the new connection
  routed with every other track protected (7 tracks and 2 vias, from R706 down the back at
  x = 18.0). Every part is where a new `place` puts it. `tools/pcb.py` now also draws the USB-C
  receptacle's D+ and D- bridges itself, locked, before the router runs (`bridge_usb`). Result
  (`reports/drc.rpt`, created 2026-11-14T19:56): 0 DRC violations, 0 unconnected pads,
  0 footprint errors, 0 schematic parity issues; 2727 track segments and 734 vias. ERC that
  evening: 0 errors, 2 warnings (the known pair); `tools/check_netlist.py`: 66 checks, 0 failed.
  Copy of the board: `out/pcb/routed-2026-11-14.kicad_pcb` (not in git). A new `route` from
  scratch is not known to close: keep that copy. Nothing is on the back now, so the 2.0 mm
  between the PCB and the floor is no longer set by the switch; whether the body can be
  thinner was not looked at.
- USB-C receptacle on a tab, 2026-11-14 late evening (section 12). The outline got the tab and J1
  moved 1.2 mm towards the edge. `tools/pcb.py place` still hands the placer J1's old position
  and shifts it afterwards: moved in the placer, it re-placed 35 other parts. On the routed
  board a one-off script moved J1, removed the tracks of its nets around it (VBUS, CC1, CC2,
  D+, D-) and of `USBC_CC2_SENSE`, which ran under the receptacle where a shell pin and a peg
  now are, and routed those again with every other track protected. The router left
  `USBC_CC2_SENSE` open; the script draws it on the back between the receptacle's front and
  rear shell pins (y = 68.6). Dead ends of the old routes were removed. Result
  (`reports/drc.rpt`, created 2026-11-14T20:51): 0 DRC violations, 0 unconnected pads,
  0 footprint errors, 0 schematic parity issues; 2739 track segments and 734 vias. Copies:
  `out/pcb/routed-2026-11-14.kicad_pcb`, and the board before this change next to it
  (`...-before-usb-tab`). The D+ and D- tracks near J1 are new autorouted tracks, not a pair.
- Wake-up link, 2026-11-13: R317 (`C5_WAKE`, section 5) was put on the routed board at
  (27.41, 22.86) by a one-off script, and Freerouting drew its two connections with every
  existing track protected. 26 track segments and 2 vias were added and nothing else moved (3590
  to 3618 tracks and vias, 253 footprints). The P4 side of it runs about 42 mm on the back and
  passes 1.26 mm from the top edge: no matter for a level that changes once per wake, but not
  a route a person would draw. `reports/drc.rpt` of that day: 0 violations, 0 unconnected pads,
  0 footprint errors, 0 schematic parity issues; ERC the 2 known warnings. The design before
  that is in `out/backup-2026-11-13-before-wake/`. A new `place` puts R317 somewhere else.
- Contact part, 2026-11-19 (owner): P1 became Promax NF6268-20PA (section 7), 2 x 10
  through-hole pins on the back. Its pins come through on the part side where the buzzer stood, so
  the buzzer moved to (25.8, 58.5) (2.3 mm right of its sound slots, which stay at x = 23.5, to
  clear J4) and the board was placed and routed again from scratch with `tools/pcb.py place`,
  `route` and `finish 15`; a first `route` left one VDD_MIPI connection open through three more
  router sessions, a second `route` and `finish 15` closed everything. P1's GND pins are joined
  to the pours in full, as J1's. Result: 2857 track segments, 754 vias, 254 footprints;
  `reports/drc.rpt` of 2026-11-19: 6 violations, 0 unconnected pads, 0 footprint errors, 0
  schematic parity issues. All 6 are J1's four shell tabs and two pegs inside P1's courtyard on
  the back (`pth_inside_courtyard`, `npth_inside_courtyard`): USB4105-GF-A's stakes are 0.95 mm
  (`GCT_USB4105_drawing.pdf` p.1, stake length blank = 0.95 mm), so they end inside the 1.2 mm
  board, but solder that comes through the shell tabs' holes would lie under P1's housing:
  solder J1 from the front and keep those four holes flush on the back. ERC the 2 known
  warnings. Kept: `out/pcb/routed-2026-11-19.kicad_pcb`, and the board before the change in
  `out/pcb/routed-2026-11-18-before-nf6268.kicad_pcb`. Order files since that day: 198 parts of
  56 kinds fitted by JLCPCB; not fitted: the C5 module, the buzzer and P1.
- Order files, 2026-11-13: `python3 tools/jlc.py` writes `out/fab/jlcpcb/`: a Gerber and drill
  archive per board (the Dock's two as well), and for the Core a BOM and a placement file in
  JLCPCB's column names. Part numbers are in `hardware/inputs/jlcpcb-parts.csv`, each read from
  JLCPCB's parts library on the date in the file. The Core's BOM has 55 lines for 197 parts, all
  on the front. Not fitted by JLCPCB: the C5 module and the buzzer (no stock there). The service
  switch is on the front since 2026-11-14 (B3U-3000P, C963349, 17,933 in stock that day), so no
  part is on the back and the order is one-sided. Stock on 2026-11-13
  was 6 for the P4 and 26 for the ESD array, so it has to be looked at again on the day. This
  does not make the draft a board to order: everything in this section still holds. Not checked:
  JLCPCB's part orientation against KiCad's rotation (look at pin 1 in their preview), their
  footprints against ours, and the board against their rules and surcharges (0.09 mm clearance,
  0.2 mm drills).
- With the parts facing the display, the P4's DSI lanes are in the mirrored order of the panel's
  (D1, CLK, D0 against D0, CLK, D1 at J2), so two pairs have to swap sides on a second layer.
- Look (owner, 2026-11-12): production boards in matte black solder mask with a gold (ENIG) finish
  and a tidy appearance ("Apple quality"); prototypes may have any colour and finish that works.
  Gold shows only where the mask is open (pads, test pads, P1); tracks under a black mask are not
  visible. The autorouted draft does not look like that: placement on a grid, few visible vias and
  sparse silkscreen belong in the layout engineer's brief.
- Open hardware (owner, 2026-11-15: anyone who wants may build the Core): the open-source-hardware
  mark is on the back's silkscreen at (10.0, 58.0), KiCad's footprint
  `Symbol:OSHW-Logo2_9.8x8mm_SilkScreen`, board-only (`LOGO` in `tools/pcb.py`; added to the routed
  board by a one-off call of `pcb.logo`). DRC of 2026-11-15T13:59: 0 violations, 0 unconnected
  pads, 0 schematic parity issues. Licence: Apache License 2.0 (owner, 2026-11-15; `LICENSE`).
  The datasheets in `docs/reference/` and Espressif's library are not the project's to license.

## 11. Open items

1. Panel samples, ST7701SN init sequence, FFC fold direction and pin order on a sample, and the
   J2 connector's datasheet (section 8).
2. Body shape: slim body, glass to the edge, external antenna (decided by the owner 2026-11-10,
   and again on 2026-11-12 against the PCB-antenna module, which needs a body about 8 mm taller).
   RF range and antenna certification are unproven (section 12).
3. Flash: boot test on the prototype (pins and QE bit are verified on paper).
4. 5V_SYS over-voltage window: the mux lockout trips at 5.48 / 5.75 / 5.97 V, while U5 is
   recommended to 5.5 V (6 V absolute) and the buzzer to 6.0 V. A reviewer has to decide whether
   to lower the lockout. Backlight: confirm TPS61169 on the prototype.
5. Ethernet through pogo contacts is unproven until a prototype passes a 24-hour soak.
6. Rear pad diameter against the Dock's spring pins: 2.0 mm allows 0.55 mm of misalignment, the
   estimated worst case is 0.65 mm (section 13). Check on a printed Core and Dock; 2.2 mm pads or
   tighter fits are the options.
7. ERC has 2 known `pin_to_pin` warnings: Espressif's symbol types VDD_ANA and VDD_BAT (U1 pins
   101, 102) as bidirectional, and they sit on 3V3, which carries a PWR_FLAG. Not a wiring fault.
8. Factory programming without the USB-C port (looked at 2026-11-12): no jig is designed. The
   pads a jig needs are on the part side, 1.0 mm each: UART0 (TP209, TP210), P4_EN (TP206),
   BOOT, which is GPIO35 on TP207, and since 2026-11-13 GND (TP104). The rear pads cannot do it: they
   carry the high-speed USB pair, which the ROM can download over (P4 datasheet p.37), but no
   BOOT line to select download mode.
9. SDIO to the C5 uses SDMMC slot 0 (GPIO39-44); Espressif's P4X-C5 EV board uses GPIO14-19
   (`SD2_*` in its schematic), and so do Waveshare's ESP32-P4-NANO-WIFI6-DB and its
   ESP32-P4-WIFI6-Touch-LCD-4B, the board the firmware runs on today. No reference board uses
   slot 0 for this link. The firmware's ESP-Hosted configuration has to select slot 0; the
   choice exists (`CONFIG_ESP_HOSTED_SDIO_SLOT_0` in the `sdkconfig` of `maratus-firmware`,
   read 2026-11-13) and is set to slot 1 there.
10. PHY crystal Y2: the part in the order BOM is the EV board's (TKD SX32Y025000BA1T, as the
    -001 listing), whose load is 10 pF by JLCPCB's listing, with the EV board's 20 pF load
    capacitors. That is copied, not calculated: measure the 25 MHz on the prototype.
11. Buzzer CMT-8504-100-SMT-TR: JLCPCB lists it as no longer manufactured and has none
    (2026-11-13); DigiKey UK showed a 13-week lead time on 2026-11-12. Its supply has to be
    checked before the next board, or another buzzer chosen.
12. Sleep mode (owner, 2026-11-13: wanted, important). Decided by the owner on 2026-11-13: the
    P4 does not sleep. Sleep means the screen off with the P4 awake and connected, the same on
    Wi-Fi and on Ethernet, so a cloud message or a touch brings the screen back without a
    reboot. On Ethernet the C5 can be shut down as well, on request (a setting; where it lives
    and its default are open): the P4 holds `C5_EN` low (2 uA typical with CHIP_PU low, module
    datasheet p.35, plus 0.33 mA in the 10 k pull-up). With the C5 shut down, a pulled cable
    leaves the device offline until the C5 has booted and joined Wi-Fi again. The board needs
    no change for any of this. The wake-up line (R317, section 5) stays fitted and unused.
    Nothing here is measured.
    If the P4 slept (not planned; read from the schematic): the wake sources on LP pins would be
    touch `TP_INT` (GPIO5), the service switch (GPIO9), `ACC_INT_N` (GPIO12) and `C5_WAKE`
    (GPIO0). With the P4 asleep and no pin held, the pull-downs switch the backlight, the buzzer
    and V_ACC off and hold the PHY in reset, and the C5's EN pull-up keeps the C5 running
    (GPIO45 is not an LP pin). Ethernet cannot wake the P4, because the MAC is inside it.
    Looked up on 2026-11-13, the grounds for the decision:
    - Ethernet as a wake source: ESP-IDF's sleep modes page for the P4 lists none, and
      Espressif's IP101 driver (esp-eth-drivers, `ip101/src/esp_eth_phy_ip101.c`) has no code for
      the PHY's WOL+. That feature (IP101G datasheet p.48-49) wakes on a magic packet, a link
      change or any packet and signals it on the INTR pin, which the Core does not connect; a
      magic packet can only come from the same local network.
    - Screen off: `LCD_BL_PWM` low switches the backlight off completely (about 0.31 A of the
      3V3 load at full brightness). The panel's logic supply is wired straight to 3V3. After the
      Sleep In command the driver IC takes 75 uA typical, 160 uA maximum (ST7701S spec p.46, MIPI
      table), against 43 mA typical for the panel in operation (panel datasheet p.6), so no
      supply switch is planned. Touch controller: 15.85 mA in operation (panel datasheet p.6);
      the datasheet gives no low-power figure.
    - P4 (datasheet p.91, typical at 3.3 V): awake and idle 15 to 56 mA depending on clock and
      peripheral clocks, Light-sleep 0.8 mA, Deep-sleep 0.012 mA. PHY: about 150 mW (IP101G
      datasheet p.7).
    - ESP-Hosted's wake rule (its `coprocessor/features/eh_cp_feat_nw_split/src/eh_cp_feat_nw_split.c`,
      main branch): while the host sleeps, the C5 drops every packet for the host unless its port
      is in the configured forward list, or it is plain MQTT from port 1883 whose payload starts
      with `wakeup-host`. The product's MQTT runs over TLS, which the C5 cannot read, so the wake
      channel has to be designed in firmware (forward list, or a connection the C5 holds itself).
    - What P4 sleep is worth (assessment of 2026-11-13; the owner agreed the same day): it saves
      the P4's idle current, 15 to 56 mA at 3.3 V (0.05 to 0.19 W), where switching the screen
      off saves about 1.2 W. It costs a reboot on every wake and an MQTT client with credentials
      of its own in the C5's firmware, because the C5 cannot keep the P4's TLS session alive.
      Flash for that looks sufficient: ESP-Hosted's 4 MB layout gives 1.75 MB per OTA slot,
      Waveshare's prebuilt C5 firmware is 1.35 MB, and MQTT with TLS takes about 0.3 MB in the
      P4 build of `maratus-firmware` (from its map file, crypto library included). Not built for
      the C5; its RAM was not looked at. Recommendation, accepted: P4 awake with the screen off
      on both connections; R317 stays on the board as an option.
    - Shutting the C5 down and bringing it back: ESP-Hosted's host API has `esp_hosted_deinit()`,
      `esp_hosted_init()` and `esp_hosted_connect_to_slave()` (its `host/compat/include/esp_hosted.h`,
      main branch). Whether that cycle works without a P4 reboot is not tried.
    Open: the current of each state measured on a prototype, the C5's current while it holds the
    Wi-Fi link, the time for the C5 to be back on Wi-Fi after `C5_EN` is released, and the
    touch controller's current with the screen off.
13. Service switch and static discharge. Compared with the schematic of Waveshare's
    ESP32-P4-WIFI6-Touch-LCD-4B on 2026-11-13 (`docs/reference/ESP32-P4-WIFI6-Touch-LCD-4B.pdf`,
    netlist from its bookmarks): its shared circuits (P4, core DCDC, flash, SDIO module, PHY)
    agree with the Core's, and one practice is missing here. It has a protection diode on each
    button line (ED1, ED2). The Core's service switch is pressed with a metal pin tool and its
    line has only 10 k and 100 nF; SW701 is the B3U-1000P, the version without a ground
    terminal. Omron lists the B3U-1100P with a ground terminal "for protection against static
    electricity" (`b3u_omron.pdf` p.1); KiCad has its footprint. Not changed: decide at the next
    schematic round, and check stock first.
    2026-11-14: the switch became the side-actuated B3U-3000P, again without a ground terminal:
    the side-actuated version with one (B3U-3100P; JLCPCB lists B3U-3100PM, C4364500) had no
    stock at JLCPCB that day. The line still has only 10 k and 100 nF, and the pin now enters
    from the bottom wall, where hands are. Open: a protection diode on `SERVICE_BTN_N`, or the
    B3U-3100P when it can be bought (KiCad has its footprint; it has a third pad).

## 12. Enclosure (prototype geometry; lens body since 2026-11-14, slim body of 2026-11-10 kept)

Generated by `tools/enclosure.py` (build123d) into `mechanical/core/`: STEP and STL of one body,
plus an assembly STEP. It is geometry for a 3D-printed fit check, not a tooling design: no draft
angles, no sealing, no strength analysis.

The lens body (owner, 2026-11-14: "now you can settle the case's design", after he had liked the
screen side of Apple's HomeView and asked how the corners could be round). The generator's
default; `tools/enclosure.py slim` still writes the body described in the rest of this section
into `mechanical/core/slim/`. The rear, the bottom edge and the board are the same in both.

- Outline: a square with 12 mm corners, 86.59 x 90.57 mm, 14.45 mm thick (slim: 81.36 x 85.84 x
  13.45, corners 3 mm). The panel's glass has square corners, so the body is 4.36 mm larger than
  the panel on every side: that is what leaves 1.2 mm of wall at the panel's corner.
- Cover lens: 83.99 x 87.97 x 1.0 mm, corners 10.7 mm, in a seat inside a 1.2 mm rim, taped
  over the panel's glass and the tops of the walls. Black border, clear window over the lit
  area with 5 mm corners (the firmware has to round the picture to match). The border is
  6.16 mm at the sides, 6.11 mm at the top and 11.87 mm at the bottom, where the "maratus"
  mark goes. `mechanical/core/maratus-core-lens.dxf` has the outline and the window for a laser
  cutter or a print shop. A new part, made to order: no supplier, price or minimum asked.
  Looked up on 2026-11-15, nothing ordered or quoted: for a trial piece in 1 mm clear acrylic,
  Cut Laser Cut (London) takes one-off jobs and customer-supplied acrylic (its own clear stock
  starts at 2 mm), and Hobarts (UK) lists 1.0 mm clear cast Perspex sheet; for printed glass,
  Saida Glass (Dongguan) lists custom black-printed cover glass with a minimum of 100 pieces
  on that product's page. In the UK (same day, from the firms' own pages, no quote asked): Mars
  Outpost (Bristol) cuts acrylic 1 to 10 mm that it sources itself, minimum charge 20 GBP a
  job; Cut It Out (South Yorkshire) has a 20 GBP minimum but stocks 3 and 5 mm only; UQG
  Optics (Cambridge) makes toughened windows to a drawing with screen printing as an option,
  its sheet list starts at 3 mm; Glasstops (Norwich) cuts glass by waterjet with no minimum
  quantity, thinnest glass not stated. No UK firm found that offers 1 mm strengthened glass
  with a black print in small numbers, and none publishes a price for such a part.
  In China (2026-11-16, from the firms' own pages, all in Dongguan, no price or sample fee
  published): Saida Glass's FAQ says no minimum quantity, a sampling cost that is refunded with
  mass production and samples in 12 to 15 days, against the 100 pieces of its product page; WM
  Cover Glass says no minimum for prototypes, 0.3 to 3.0 mm, chemical strengthening; Fuxin
  Glass says 200 pieces, free samples with the shipping paid by the customer, within 7 days.
  For a request for a quotation, `tools/lens_drawing.py` writes
  `mechanical/core/maratus-core-lens-drawing.pdf` from the DXF (A4, 1 : 1): the border measured
  on the lens itself is 6.06 mm at the sides, 6.01 mm at the top and 11.77 mm at the bottom (the
  figures above are measured from the rim), the mark is 18.82 x 3.09 mm. Chosen for that sheet on
  2026-11-15, not tried: the print on the rear face (towards the display), opaque black, the mark
  in a second colour (grey, as in the pictures; yellow since 2026-11-16, see the colour
  study below); outline tolerance +/-0.10 mm from the 0.1 mm of
  play in the seat. Left to the maker and asked on the sheet: glass type, edge finish, inks,
  position tolerance of the print.
- The panel sits 2.11 mm higher over the board than in the slim body, so that the body's bottom
  face is where it was: USB-C opening, the four slots, pad window and lock point are unchanged.
  The board's bottom 1.8 mm and its tab lie under a ledge of the bottom wall; both FFC tails
  turn around the panel's edge through recesses in that ledge and have about 2 mm more slack
  than before (about 9 mm of each 30 mm tail is spare). No connector moved on the board.
- Walls 4.11 mm beside the panel (solid), 2.0 mm at the bottom at board level. Thinnest places:
  0.85 mm at the panel cavity's four corners (inside the rim) and 1.08 mm at the board
  cavity's two bottom corners. Rear edge rounded 2.5 mm.
- The name (owner, 2026-11-14: "maratus" has to be on the product somewhere, front or back):
  on the lens body it is printed on the lens, in the middle of the border under the picture
  (layer `mark` of the lens's DXF); on the slim body, which has no room on the front, it is
  sunk 0.4 mm into the rear, 25 mm below the top edge (1.2 mm of floor left). Noto Sans Bold,
  4.6 mm: a stand-in, the brand's own lettering is not in the repo.
- Both bodies from five directions (front, rear, bottom, two angled), the straight views at
  1 : 1, for the owner to compare: `out/maratus-case-compare.pdf` (sources in
  `out/case-compare/`, not in git). Since 2026-11-14 night, as the owner asked: a white screen
  with a black QR code and Inter lettering, a silver body on light grey tiles, no labels in the
  pictures. The colours are examples.
- Colour study of the lens body (owner, 2026-11-15: between orange and red, the silver of the
  pictures, dark grey and a few more, the wordmark in a colour that suits the body; perhaps
  after the colour book of a Japanese artist): `out/maratus-core-colours.pdf`, ten options with
  four views each (sources in `out/case-colours/`, not in git). Six pairs follow Sanzo Wada,
  A Dictionary of Color Combinations (names, CMYK values and combination numbers from the open
  data set github.com/mattdesl/dictionary-of-colour-combinations; its hex values are converted
  from the CMYK): Spectrum Red and Orange, each with the wordmark in the body's colour,
  Sea Green with Peach Red, Blue with Yellow, Dark Tyrian Blue with Light Glaucous Blue, Slate
  Color with Golden Yellow. The owner found silver, ivory and dusky green dull the same day,
  named Teenage Engineering, Nothing and Apple, then asked for blue, purple and red and one
  more of the assistant's choice, all vivid, and had Peach Red, the first answer to "between
  orange and red", made more orange (now the book's Orange). Picked by eye, because those makers publish no
  colour values for these finishes: yellow (after Teenage Engineering's pocket operator modular
  400), a black body with a red wordmark (after Nothing), pink (after the iPhone 16) and a
  purple. No body colour is chosen. For a trial of the glass the owner chose Yellow on
  2026-11-16: five pieces, all with the yellow wordmark (he first named five colours, then
  dropped them for one). The lens drawing asks for yellow in place of grey and for the maker's
  minimum order quantity and value. The owner sent the request for a quotation to UQG Optics,
  Glasstops, Saida Glass, WM Cover Glass and Fuxin Glass on 2026-11-16, with a light copy of
  the colour PDF. Delivery is to the United Kingdom: the requests to China ask for the cost to the door,
  import duty and VAT, and the days from payment to arrival. Saida Glass answered the same
  day without a price: no strict minimum quantity, and two questions (glass or PMMA for the
  five pieces, the quantity of a later production), then a third: indoors or outdoors. The
  owner's answers: glass; quantity not fixed, prices asked at 100, 500 and 1,000 pieces;
  indoors first, outdoors as well but not the priority. No price from Saida Glass yet.
  WM Cover Glass (Dongguan Weiman Technology) quoted by mail on 2026-11-16, for chemically
  strengthened AGC glass (grade not named) with a PVD anti-fingerprint coating, black border
  and yellow mark: 230 USD for the five pieces, refunded once orders reach 3,000 pieces; 50 USD
  express shipping, duty not included; 5 to 7 days to make and about 5 to 7 days in transit;
  3.80 USD a piece at 100 pieces plus 85 USD shipping. It asked how often the glass is touched
  (spray coating is cheaper, PVD lasts longer), whether the mark has to let light through, and
  whether the black may be Pantone Black C. Not answered in its mail: how the 230 USD is made
  up, the price of an extra piece, the courier, UK VAT, how to pay. Its second mail the same
  day, after the owner's questions: the glass is AGC soda-lime, surface stress at least
  550 MPa, depth of layer over 10 um; five pieces 210 USD with a sprayed coating, 230 USD with
  PVD; each extra piece 3.80 USD, so ten pieces with PVD 249 USD; the 230 USD is not split
  (glass, inks, screens, grinding, coating, labour); DHL, UK duty and VAT paid by the owner to
  the courier; bank transfer or PayPal; 2.00 USD a piece at 500 and 1.80 USD at 1,000 with
  PVD, 1.85 and 1.65 USD sprayed. Its proposal for the mark, which is not backlit: black
  first with the letters left clear, then yellow over them; a photo after printing. Not
  answered: a refund of the sample charge below 3,000 pieces, a Pantone number for the
  yellow. Nothing ordered.
  Saida Glass quoted on 2026-11-17 (quotation SD-2026111705, not in the repo), for
  chemically strengthened soda-lime glass with the black border, the yellow mark and an
  anti-fingerprint coating whose kind is not stated: 140 USD for the five pieces plus 53 USD
  shipping by air with UK duties and taxes included; 3.00 USD a piece at 100 (shipping
  85 USD), 1.50 USD at 500 (195 USD), 1.30 USD at 1,000 (325 USD); with UV-resistant ink
  160 USD for five, 4.00, 1.60 and 1.40 USD a piece; 15 days to make the samples and 15 to 18
  days in transit; the sample charge refunded at 2,000 pieces; payment in advance by bank
  transfer. Against WM Cover Glass: cheaper, and about three weeks slower.
  The owner decided on 2026-11-17 to take five samples from each of the two, to compare them
  before choosing one for production; speed no longer decides, because the board is not
  ordered yet. He told both the same day. WM Cover Glass then offered 210 USD plus 50 USD
  shipping for its five pieces (the owner had named Saida's price, not the firm); whether
  that is still with PVD is asked. Saida Glass answered the same day: its coating is
  sprayed, the glass is AGC with a surface stress of at least 500 MPa and a depth of layer of
  at least 8 um, payment by PayPal is possible, and it asked for a Pantone or RAL number for
  the yellow. Named for it: Pantone 7408 C, the nearest of two candidates to #f7c200 by the
  screen values in third-party tables (7408 C #F6BE00, 7406 C #F1C400; Pantone's own values
  were not read, and a screen value is not the printed colour). So the two sample sets differ
  in the coating: PVD from WM Cover Glass, sprayed from Saida Glass. WM Cover Glass sent its
  proforma invoice PI-K016-261117 the same day: five pieces at 42 USD, with PVD, plus 50 USD
  freight, 260 USD in all, 5 to 7 days after payment, customs code 7007190000. The owner
  paid it by PayPal on 2026-11-17 (205.58 GBP) and confirmed Saida's order of five the same
  day (193 USD). Saida sent its proforma invoice SD-2026111806 on 2026-11-18 (193 USD: five
  pieces 140 USD, air DDP shipping 53 USD; made 15 days after payment; its transport terms
  field says EXW Dongguan while the shipping line says DDP) and the owner paid it by PayPal the
  same day (152.72 GBP, to vicky_xu@saideglass.com, shown as Han XiaoWei). PayPal held an old
  delivery address; the right one is on the invoice, and Saida is asked to ship there and to
  confirm DDP. No glass has arrived.
  Fuxin Glass quoted on 2026-11-18 with a drawing of its own (not in the repo), for chemically
  strengthened aluminosilicate glass: five samples 469 USD ex works (312.5 USD the pieces,
  156.5 USD the screen-printing setup, credited once orders reach 500 pieces), shipping, duty
  and VAT not included; minimum order 100 pieces at 7.50 USD, 6.25 USD at 500; 15 to 20 days
  after full payment. The only maker of the three to offer aluminosilicate, but two to four
  times the price of the others; the owner did not order (2026-11-18) and keeps it in reserve
  if the soda-lime samples prove too weak.
  Glasstops declined on 2026-11-17: no custom glass at
  present, its waterjet is out of use. No answer from UQG Optics yet.
- Contacts level with the rear face (owner, 2026-11-14 night, on those pictures: they must not
  lie inside the device). Drawn on 2026-11-19 with a bought part, Promax NF6268-20PA (end of
  this item and section 7). Before that day `tools/enclosure.py`, the board and the STEP files
  had the window with the board's pads 3.6 mm behind the
  rear face (2.0 mm standoff plus 1.6 mm floor). It needs: a contact part of that height
  between the board and the rear face (not chosen, no part number), 18 holes in the floor in
  place of the window, a footprint for that part in place of the pad field P1, and another way
  to locate the Dock, whose contact block reached 3.0 mm into the window and kept the Core
  from turning (section 13).
  Looked up on 2026-11-16 in Mill-Max's data sheets, nothing chosen: its surface-mount target
  discs 1625 and 1656 are 3.18 and 3.96 mm wide and 0.89 mm high, too wide for the 2.54 mm
  pitch and too low. The nearest stock part is the through-hole target header of series 419
  (`docs/reference/millmax_419-10-254-00-001000.pdf`, the 54-pin double-row strip: 2.54 mm
  pitch, flat face, head 1.778 mm, 4.191 mm above the board, tails 0.508 mm for 0.711 mm
  holes, 3.175 mm long). It does not fit the design as it is: it stands 0.59 mm above the
  3.6 mm; the field's rows are 3.5 mm apart (the sheet's text gives the pitch, not the row
  spacing); its head leaves the Dock's 0.9 mm plunger 0.44 mm of misalignment where the 2.0 mm
  pad leaves 0.55 mm (open item 6); its tails come out 1.6 mm on the part side, where U6 and
  BZ701 reach over the field's ends. An 18-pin version, price and stock are not checked.
  Magnetic pairs (owner, 2026-11-16: Square's devices have spring contacts, and such connector
  pairs are sold): EDAC's series 685/686 (`docs/reference/edac_685-686-689_ordering-guide.pdf`:
  2 to 31 contacts, one or two rows, magnets hold and polarise) has an 18-contact pair with
  drawings, male 685A1821220113Q and female 686A1821F20111E (read on 2026-11-16 at
  files.edac.net/edac/content/685/685A1821220113Q.pdf and .../686/686A1821F20111E.pdf; not
  copied into the repository, their title blocks forbid reproduction): two rows of nine
  2.40 mm apart, two N52 magnets 27.40 mm apart,
  2 A and 12 V a contact, 0.8 mm stroke, 10,000 cycles, 0.8 mm through-hole pins, hand or
  selective soldering only. The female's contact nose is 18.30 x 5.30 mm and stands 3.0 mm
  before a 2.0 mm flange, made to pass through a wall and end level with it. Its face,
  however, is 11.80 mm in front of its board and its body is 38.5 x 9.1 mm, against the 3.6 mm
  between this board and the rear face: it does not fit the body as it is. The male is 49.60 x
  8.80 mm with two screw ears. No distributor, price or stock was found for this pair. EDAC's
  MPM/MPF pairs end at 9 contacts in one row; Mill-Max's Maxnetic 878 has 2 pins at 4 mm and
  stands 9.6 mm high. Makers in Dongguan that offer custom magnetic pairs on their own pages,
  nothing asked: CFE (2 to 30 pins), Promax, Yiwei (double row, 2.54 mm). The AliExpress
  listing the owner named could not be opened, and no source was found for how Square builds
  its contacts. The same day the owner sent a request for a proposal to CFE, Promax and EDAC's
  office in England: a pair with 18 flat contacts on the Core, level with the rear face 3.6 mm
  from the board (3.5 to 4.5 mm offered), in an opening of about 26 x 9 mm, and spring pins on
  the Dock; one-page sheet `out/maratus-core-contact-request.pdf` (script in
  `out/contact-request/`, not in git). Magnets inside the pair are not asked for (owner, same
  day, after weighing it: a magnet that fits 3.6 mm may not hold the Core, and reflow harms
  magnets): the Core keeps its two 10 x 2 mm discs, and the request says magnets in the
  connector are welcome, not required. That wording was softer than the owner's decision; on
  2026-11-18 he confirmed: no magnets in the contact pair, the two in the body stay. CFE answered on 2026-11-17 with no proposal and no
  price: it says it can develop a custom pair and first asks for the yearly volume, the
  timeline, whether the device is the owner's own product, and the company's name, website
  and place. The owner's answers (2026-11-17): 500 to 1,000 a year in the first year of
  production, prototypes as soon as possible, the first production batch in the first quarter
  of 2027, his own product, no registered company yet (he orders as an individual), London.
  CFE declined the same day: no standard pair of its own fits, a custom pair needs a new
  mould, and its minimum for magnetic connectors is 5,000 sets, against 500 to 1,000 a year.
  It offers to look again if the design is changed to take one of its standard connectors.
  So CFE makes no custom pair at this volume. No answer from EDAC yet.
  Promax answered on 2026-11-19 with two standard pairs; the owner took NC6268-20PA (Dock) and
  NF6268-20PA (Core), ten pairs for prototypes, and moving the magnets (section 7, and the
  magnets below). Drawn the same day: NF6268-20PA stands on the board's back, its raised part
  fills a window in the floor and its 50.4 x 7.4 mm housing sits in a 0.6 mm pocket on the
  inside of the floor (1.0 mm of floor left there); the contact faces end 0.10 mm behind the
  rear face. Asked of Promax that day, not answered: the price of 5 and 10 pairs and at 500
  and 1,000, shipping and UK duty, lead time, the right STEP model, the contact face's
  diameter and height, the PCB layout, and whether 2.0 A holds for all 20 contacts at once.
  The guide pins of the NC6268-20PA (8.50 mm high against a 6.10 mm working height) reach
  2.40 mm into the NF6268-20PA; that its guide holes are that deep is assumed.
- Two soft plugs (owner, same day), `plug-lock.stl` and `plug-usb.stl`: for the lock point when
  the Core is used without a Dock, for the USB-C opening when it is on one. First guesses.
- Not tried, and the reason the slim body is kept: the panel's touch through 1 mm more glass
  or acrylic. Also open: how the lens is bonded (tape at the edge leaves an air gap over the
  panel), the tails' extra slack on a sample, printing the thin corners.

The slim body, as generated on 2026-11-10 and changed since (rear, bottom edge):

- The owner rejected the first version for its thick frame (2026-11-10). In this one the touch
  glass reaches the rim on all four sides and the display is the lid of a one-piece body.
- Outside 81.36 x 85.84 x 13.45 mm. Plastic seen from the front: 1.75 mm at the sides and top,
  2.25 mm at the bottom, including 0.25 mm of play around the glass. The panel's own black border
  (2.5 mm sides, 8.2 mm bottom) stays.
- Lit area (datasheet p.4): 71.86 x 70.18 mm, 3.00 mm from the glass's edge at the sides, 2.95 mm
  at the top and 8.71 mm at the bottom, so its centre is 2.88 mm above the centre of the glass.
  The Dock pictures before 2026-11-11 drew it 5 mm from every edge, which was wrong. The pictures
  now show the real area with a black screen whose content is centred on the glass
  (`screen_image` in `tools/dock.py`). The border only looks even if the firmware does the same:
  black background, nothing bright at the lit area's edge, content 20 lines below the panel's
  centre (0.146 mm per line). This is a proposal for the firmware, not a decision.
- Stack from the rear: 1.6 mm floor, 2.0 mm bosses, PCB 1.2 mm, 4.5 mm for parts (buzzer 4.0 mm),
  panel 4.15 mm.
- The panel lies on a 1.5 mm wedge-shaped shelf on the top, left and right walls and two tabs in
  the bottom corners, held by double-sided tape. Nothing else retains it.
- The PCB is screwed to four bosses with M2 x 4 thread-forming screws (corrected 2026-11-12: the
  pilot holes are 3.1 mm deep, and an M2 x 5 through the 1.2 mm board needs 3.8 mm) from the part side, before
  the panel goes on.
- Bottom wall: USB-C opening like a phone's (owner, 2026-11-14): an oval hole of 8.9 x 3.1 mm
  with full round ends, the receptacle's mouth (8.34 x 2.56 mm inside) 1.39 mm behind the outer
  face. `GCT_USB4105_drawing.pdf` p.1 shows the plug's overmould at least 1.85 mm in front of the
  mouth when mated, so the overmould stops on the outer face with 0.46 mm to spare and needs no
  pocket. Until that day the mouth was 2.59 mm behind the face and a 13 x 6.4 mm pocket let the
  overmould in. The 1.2 mm come from the board's tab (section 10); on the inside of the wall a
  pocket takes the tab and the receptacle's front, so the board is laid in a little towards
  the top and slid down. The wall in front of the pocket is 1.14 mm thick. Not checked: a real
  plug in a printed body; whether the tab's 0.61 mm inside the wall survives handling.
  Asked whether another receptacle would have spared the tab, the owner kept it (2026-11-14):
  the mouth has to be 1.2 mm further out with any 7.35 mm receptacle, and GCT's drawing puts
  the board's edge under the mouth. The alternative is to let the receptacle overhang a plain
  edge by 1.2 mm (KiCad's footprint of the HCTL HC-TYPE-C-16P-01A does so by 1.23 mm).
  Also in the bottom wall: recesses for the two FFC tails behind the glass, three sound slots
  for the buzzer and, since 2026-11-14, a fourth slot in the same row for the service switch.
  All four are 1.2 x 3.2 mm at 2.4 mm pitch (the sound slots were 2.5 mm high before). The
  service slot is 1 mm deep; only its lowest 1.2 mm goes through the wall, at the height of the
  switch's plunger, so a pin cannot pass over the switch into the board. Floor: since 2026-11-19 a 38.3 x 5.8 mm window that the contact
  part's raised part fills, and a 0.6 mm pocket on its inside for the part's housing (section 7);
  before that day a 25.3 x 8.5 mm window over the rear pads, 3.6 mm deep (upright before
  2026-11-14). 0.4 mm recess that locates the antenna. The 1.6 mm pin hole under the service switch is gone since 2026-11-14.
- Antenna: Taoglas FXP830 stuck on the floor in the 9 mm strip above the PCB, cable to the
  module's connector. The LCD's metal back is about 7.7 mm in front of it and the PCB edge 1 mm
  below it; the datasheet's figures are for free space on 2 mm ABS. Its 5 GHz peak gain (6.86 dBi)
  is above the 3.65 dBi the module was certified with, so certification needs its own test or a
  lower-gain antenna. RF range must be measured.
- Dock interface: since 2026-11-19 the two guide pins of the Dock's NC6268-20PA locate the Core
  in the contact part's guide holes (before: the Dock's contact block in the pad window), and one M4 nut
  in the floor is the lock point (end of this item). Until 2026-11-14 night: two bosses
  in the floor took a Dock's two M2 lock screws from the rear (1.7 mm pilot holes, 3.6 mm deep).
  Owner, 2026-11-14: only two holes, beside the pads, and the Docks are designed to them. They
  are on the pads' centre line at PCB (8.0, 66.0) and (66.0, 66.0), 29 mm either side of the
  middle; nearer on the right the USB-C receptacle's shell pins are in the way. Until that day
  there were four: an outer pair at (3, 54.6) and (71, 54.6) for BAR and an inner pair at
  (15.5, 49.6) and (58.5, 49.6) for FLOAT. The service switch's pin hole in the rear went the
  same day (the switch moved to the bottom edge): the rear has the pad window and these two
  holes only. Nothing is on the back of the board at those places (only P1 and SW701
  are on the back). The four Dock magnets in the floor are unchanged (two pairs, not visible
  from outside; one pair beside the pad field since 2026-11-15, see the magnets item below).
  Open since the same evening (owner): he would rather have one lock point with a metal part
  than two screw holes, no screws at all for the lock, and silicone plugs: one for the lock
  point when the Core is used without a Dock, one for the USB-C opening when it is on a Dock.
  Seven lock ideas are drawn in `out/maratus-lock-options.pdf` (sources in `out/lock-options/`,
  not in git): six use one steel plate with a 3 x 7 mm slot above the pad window, one latches
  in the pad window itself. Only 3.6 mm lie between the rear face and the board there. Nothing
  is chosen or worked out; the two screw holes stay in the body until he picks one.
  Looked up for him on 2026-11-14: Stripe's dock for its Reader S700/S710 (installation guide,
  docs.stripecdn.com/s700-s710-dock.pdf) holds the reader by a hook in a lower slot, pogo pins
  and one M4 bolt with a D-ring, turned by hand from under the dock into an M4 nut in the
  reader ("little to no movement" when tight); the dock itself has a 1/4 inch nut for stands.
  Payment-terminal stands (Havis FlexiPole) use a backplate with a quick-release latch that a
  key latch can replace; tablet kiosks use key-locked steel enclosures, a Kensington slot and
  VESA 100 x 100. The tripod thread he asked about is a standard: ISO 1222:2010, 1/4-20 UNC
  (6.35 mm) or 3/8-16 UNC. Its screw length and socket depth were not in the pages that could
  be read; a 1/4 inch nut is unlikely to fit in the 3.6 mm over the board, an M4 nut does.
  Decided the same night after he asked for my view (he wants the mechanism hidden in the
  Dock and the Core usable on other makers' stands): the Core gets one M4 thin nut (ISO 4035,
  7 mm across flats, 2.2 mm high; dimensions from distributors' tables) at PCB (37.0, 55.0),
  on the centre line above the pad window, in place of the two screw bosses. It is pressed
  into a hexagonal pocket from the inside, 0.8 mm of floor holds it, the board is 0.6 mm above
  it: glue it, and no bolt may reach more than 3.0 mm into the Core. What goes into it is the
  Dock's business (a hand-turned captive bolt hidden under the Dock, as Stripe does) or another
  maker's stand; the pad window keeps the Core from turning. The Dock is to carry a 1/4-20 nut
  underneath for stands. Not worked out: the nut's pull-out strength in a printed floor, ESD
  on a floating metal nut next to the board, the Dock's bolt. `out/maratus-lock-options.pdf`
  still shows the slot-plate ideas. The owner agreed that night ("tamam pine göre
  değiştirelim tasarımı", read as: go on with the M4 bolt). `out/maratus-lock-final.pdf` shows
  it: a spring-loaded captive M4 bolt in the Dock, pushed and turned by a ringed head that is
  recessed in the Dock's rear face (the Core stands close to upright, so the bolt lies about
  level and its head cannot be under the Dock, as was first said), a round silicone plug for
  the hole when there is no Dock, and another maker's stand held by one M4 screw and a 3 mm
  tongue in the pad window. All of that is a sketch.
- Antenna cable: the module's connector faces the middle of the board (the module is turned so
  its SDIO pins face the P4), and the cable is 100 mm long. Where it lies in the 4.5 mm between
  board and panel is not drawn.
- Magnets for a Dock (owner, 2026-11-12): 10 x 2 mm N42 discs (supermagnete S-10-02-N or
  first4magnets F670; both pages say about 1.3 kg) glued into pockets in the floor from the
  inside, behind 0.5 mm of floor, so nothing shows on the rear. A 0.9 mm collar stands around each;
  the magnets end 1.1 mm under the PCB. Since 2026-11-19 there are two at (13.5, 55.5) and
  (60.5, 55.5) in the PCB frame: 23.5 mm either side of the contact part's centre and 10.5 mm
  above it (owner, that day: the magnets may move). The contact part's housing, 50.4 mm long,
  reaches under their earlier places, and beside it the screw bosses are in the way. From
  2026-11-15 to 2026-11-19 they were at (13.5, 66.0) and (60.5, 66.0), level with the pad
  field (owner: symmetric, level with the contact field, near it). Both have the same pole
  towards the rear. They sit beside the
  spring pins, so their pull meets the pins' push with no lever between them. The Docks have
  to be drawn to these places (section 13 is out of date anyway). Before that day: four, an
  outer pair at (7.1, 47.4) and (66.9, 47.4) for BAR and an inner pair at (13.6, 56.5) and
  (60.4, 56.5) for FLOAT; a body printed before 2026-11-15 has those pockets.
  The buzzer is a magnetic one; since 2026-11-19 it stands on the board at (25.8, 58.5),
  8.5 mm square, 12.4 mm from the left magnet's centre and 3.05 mm outside its edge. Not
  checked: the buzzer's level with the magnets fitted. The right magnet no longer lies under
  the USB-C receptacle. Distances to the service switch and other parts: not measured again. Holding force with two magnets: not calculated again, not measured.
- Open: no gasket; opening the device means peeling the display off its tape.

## 13. Dock (draft, two bodies, generated 2026-11-10, FLOAT's rear redrawn 2026-11-12)

Generated by `tools/dock_sch.py` (schematics), `tools/dock_pcb.py` (boards) and `tools/dock.py`
(bodies) into `hardware/dock-contact`, `hardware/dock-base`, `mechanical/dock` (board models and
the printed parts both bodies share), `mechanical/dock-bar` and `mechanical/dock-float`. Same
standing as the Core: generated, autorouted, reviewed by nobody, nothing built.

Out of date since 2026-11-14: the Core's pad field now lies horizontal and 6 mm lower (section 7)
and everything below describes the Dock for the upright field. The contact board's 12 pins still meet the pads
when the board is mounted a quarter turn anticlockwise (seen from the Core's side, its header
side up), but its harness plug then spans x = -10.7 to +10.7 mm of the Dock, where the RJ45 jack
takes x = -22.0 to -5.9 mm (heights not compared, nothing built to check). So the contact board,
its seat, the saddle and both bodies have to be drawn again. Not done: the owner is still choosing
the Dock's look (BAR, FLOAT or one of the later concepts). Until then `tools/dock.py` stops with
a message, and the files in `mechanical/dock-bar`, `mechanical/dock-float`, `hardware/dock-contact`
and the Dock's order files are the upright-field versions.

Print prototypes for the Core as it is (owner, 2026-11-18): `tools/dock_print.py` draws A BAR and
D TILE (concept 2) for both Core bodies into `mechanical/dock-{lens,slim}-{bar,tile}`, to print
and try the look and the fit. Since 2026-11-19 each holds the spring-pin half of the Core's
contact pair, Promax NC6268-20PA: its housing in a pocket, its raised part in a window of the
face, its board 6.10 mm (the working height) behind the face, in a recess for a contact board of
56 x 12 x 1.6 mm with 2.4 mm behind it for the pins' tails (board not drawn, not fixed); its two
guide pins put the Core in place. Before that day: a block that reached 3.0 mm into the Core's
pad window, with 18 pin holes and a 31 x 12 mm board. Also
two pockets for stacks of two 10 x 2 mm discs opposite the Core's two magnets, a 5 mm boss with a
4.5 mm hole for an M4 x 8 lock bolt into the Core's nut, and the unchanged port drawer and base
board; the script checks that no two parts overlap, the NC6268-20PA and its board included. BAR:
the bar is 44 mm across and its axis 17 mm behind the Core's rear face (40 and 15 until
2026-11-19, 38 and 13 in `tools/dock.py`), so that the contact board clears the base board; the
bar touches the Core from 0.0 to 28.0 mm up its rear face and the Core's bottom edge stands
11.4 mm above the table. Its lock bolt cannot be
reached with the bar closed. TILE: a 2.2 mm shell of the Core's outline on a 3 mm base plate (four
M2 screws), glass 25 degrees from the table, the wedge 13 mm high at the front (6 mm until
2026-11-19: the contact part with its board reaches 10.1 mm behind the face), upright rear wall with the port panel; the lock bolt
goes in from inside with the plate off. Not printed, not tried; the contact board is not drawn.

- Function: power and Ethernet for the Core through its rear pads, a stand, magnets that hold the
  Core (since 2026-11-12), and an optional screw lock.
  There is no active part in the Dock. The PHY is in the Core; the Dock holds the magnetics (inside
  the RJ45 jack), a USB-C power inlet and the 1.0 k ID resistor.
- Shape, how it got here. On 2026-11-10 the owner rejected a 92 x 90 x 50 mm cradle as too bulky
  and a 78 mm wide wedge foot because Core and Dock looked like two separate parts, and called a
  third Dock (as wide as the Core, a chin under the glass, a concave sweep behind) better. He then
  asked for three look concepts between Teenage Engineering and Apple (`out/concepts`, not in git)
  and chose two of them to go on with: BAR and FLOAT. Both are built here around the same inner
  parts, so one set of boards fits either body. Which of the two becomes the Dock is the owner's
  decision. The third Dock's generator is no longer in `tools/` (a copy is in `out/dock-v3`).
- BAR. A round bar, 38 mm across and as long as the Core is wide, lies on the table on a 14.8 mm
  deep standing face (1.5 mm cut off). The Core leans on a flat on the bar's front, from 6.5 to
  34.2 mm up its rear face; the bar's axis is 13.0 mm behind that face. The Core's bottom edge is
  1.2 mm above the table. 49.7 mm deep, 87.5 mm high, the bar 36.5 mm. The concept picture had a
  36 mm bar; 38 mm is what the RJ45 jack needs (0.5 mm between the jack's end and the 1.6 mm front
  wall). Printed parts: the body (2 mm wall), two orange end caps (2.2 mm, with a ring that fits
  the bore), the saddle and the port drawer. The port panel is the flat on the bar's back.
  - Under the middle 36 mm of the bar's front a foot fills the wedge between the Core's rear face
    and the bar, down to the table 13.9 mm behind the front. It is needed: the Core's weight is in
    front of the standing face (24.7 to 39.5 mm behind the front).
  - The bar covers the Core's service pin hole, so a 2.0 mm guide hole goes through the bar on the
    same axis (about 25 mm of plastic) and comes out on its upper rear.
  - The Core's own USB-C port and buzzer slots stay open, 1.2 to 4.7 mm above the table. A plug
    does not fit there while docked.
  - A 0.3 mm recess (70 x 8.5 mm) in the standing face takes mounting tape.
  - The coin slots in the caps are decoration. The caps have 0.15 mm play in the bore: glue them,
    a press or snap fit is not designed.
- FLOAT. A plate of 81.4 x 66 x 3 mm (10 mm corners) lies on the table. The Core hovers 9 mm above
  it, the glass's bottom edge 6 mm behind the plate's front edge. A pod, 59 mm wide, stands behind
  the Core's lower part as a wedge: it reaches 34.5 mm up the Core's rear face (45.3 mm above the
  table), its top is one flat slope of 28.6 degrees down to a 6 mm roll, and the roll ends on the
  top of the port panel, 23.2 mm above the table and 62 mm behind the plate's front edge. The
  side edges and the rear corners have one 5 mm radius. 66 mm deep, 98.3 mm high. Printed parts:
  the pod (walls 2.2 mm, rear wall 5 mm, open at the bottom and at the top), the cap, the orange
  plate, the saddle and the port drawer. The port panel lies 1 mm inside the pod's rear face.
  - Rear redrawn on 2026-11-12: the owner found the first pod crude (a 55 mm box with a curved
    roof, a 32 mm rear wall, two screwdriver holes above the port panel and the panel's seam all
    round). The rear wall was that high only because the holes had to come out above the panel.
  - The cap is the top 3.1 mm of the wedge, slope and roll in one part; the seam is a plane
    parallel to the slope, without a groove. It has two rails that sit inside the side walls
    (0.15 mm play) and stand against the rear wall. Nothing else holds it: the fit has to be
    tuned on a print, or a catch added. Its rear edge closes the port opening from above and
    stands 1 mm over the panel, which is where a fingernail lifts it.
  - The plate closes the pod: four M2 x 8 countersunk screws from below into two blocks and two
    ribs inside the pod, two M2 x 6 into the drawer's shelf.
  - The Core's service pin hole, its USB-C port and its buzzer slots stay free.
  - The plate is a printed part here (about 20 g). The same outline in 3 mm steel would weigh
    about 123 g (15.7 cm3 at 7.85 g/cm3) and stand better; that part is not designed.
- Contact board, 16.2 x 27 mm, 2 layers, 1.6 mm. 12 spring pins Harwin P70-2300045R
  (`docs/reference/harwin_P70-2300045R.pdf`: free height 6.2 mm, working height 4.9 mm with a
  window of 4.6 to 5.2 mm, 0.83 N, 2 A, 30 mOhm, 10,000 cycles, 0.9 mm plunger) on the pads the
  Dock uses: 5 x GND, 2 x VIN, the four Ethernet lines and ACC_ID. USB, the IO lines and V_ACC get
  no pin. The pins are through-hole. The harness header (JST B8B-PH-SM4-TB, surface mount,
  `jst_ePH.pdf` p.4) stands upright beside them on the back, the ID resistor above it. The board
  has no holes. The pin positions are those of P1 on the Core board (compared for the first
  version; the pin field did not change).
- Base board, 46.2 x 25 mm, 2 layers, 1.6 mm, two M2 holes. Seen from the rear: USB-C left, RJ45
  right, the harness header between them next to the jack (short Ethernet pairs), its power pins
  at the rear. The front edge is notched: 2.5 mm where the Dock's front is thick, 14 mm behind the
  contact board's harness plug. USB-C receptacle for 5 V only (5.1 k on each CC, no data),
  SMAJ5.0CA, 10 uF and 100 nF, RJ45 jack Wurth 7499010121A with built-in 10/100 magnetics
  (`wurth_7499010121A.pdf` p.1), 100 nF on each centre tap and no supply to them (IP101G datasheet
  p.7 and p.55), jack shield to GND through 1 M and 1 nF / 2 kV (assumption, for EMC review). The
  jack's LEDs are not connected: no LED signal comes over the rear pads.
- Harness: 8 wires, pin 1 to pin 1, JST PH housings PHR-8 with SPH-002T-P0.5S contacts
  (`jst_ePH.pdf` p.2-3), AWG 24. Two wires each for VIN and GND, the two Ethernet pairs twisted.
  Length is not fixed yet; to be measured on the print.
- Power path: USB-C, harness, two spring pins, the Core's VIN pads, then the Core's TVS and mux.
  Each link is rated 2 A (pin, PH contact); the Core draws up to 1.2 A. The Dock has no fuse and
  no current limit of its own, and it does not read the CC lines, so it takes whatever the USB-C
  source gives at 5 V. The supply has to be able to deliver 1.5 A.
- Seating: the Core's rear face lies on the Dock's front face (the flat of the bar, the front of
  the pod). The Dock's front is 5.5 mm thick where the contact board sits. The board lies with its
  back on the floor of a 2.9 mm deep recess, so the pins' force goes into solid plastic; the floor
  is 1.2 mm lower under the pins' solder tails and has a window for the harness header and its
  plug (8.6 mm high when mated, `jst_ePH.pdf` p.2). A printed saddle holds the board from the
  front: a 1.05 mm plate over the board, a leg beside it with two countersunk M2 x 8 screws, and
  the block that reaches 3.0 mm into the Core's 3.6 mm deep pad window, with a 1.9 mm hole per pad.
  Since 2026-11-12 the block has 0.3 mm play all round, with corners rounded like the window's
  (before: 1.25 mm up and down, and the lock screws set the height). It puts the pads on the pins
  and carries the Core's weight, with or without the screws, and it is in the window 1.7 mm before
  the first pin touches a pad, so a pin cannot land between two pads. The
  saddle's front is 0.1 mm under the Dock's front face. The pins are compressed by 1.3 mm. 12 pins
  push the Core off with about 10 N; the magnets hold against that.
- Magnets (owner, 2026-11-12): opposite each of the Core's two magnets for that body (section 12)
  the Dock's front has a stack of two of the same 10 x 2 mm discs. The pocket is open to the
  front, 4.1 mm deep, with 1.2 mm of plastic around and behind it; the magnets are glued in, lie
  0.1 mm under the face and can be seen when the Core is off (`out/dock-*-open.png`). BAR: 29.9 mm
  either side of the centre and 27.2 mm up the Core's rear face, beside the base board. FLOAT:
  23.4 mm either side and 18.1 mm up, under the inner lock bosses. Docked, the faces are 0.6 mm
  apart (0.5 mm of the Core's floor and 0.1 mm).
  - Pull, calculated and not measured (pole faces as point poles, remanence 1.3 T; the same
    calculation gives 1.36 kg for one disc on steel, where both suppliers say about 1.3 kg):
    13.5 N per pair at 0.6 mm, 11.0 N at 1.0 mm, and 7.4 N at 1.9 mm, which is where the pins
    first touch. Two pairs give about 27 N against the pins' 10 N, so about 17 N holds the Core.
    It comes off by hand, and a Dock that is not fixed to the counter comes with it.
  - Sideways a pair pulls back to centre with about 1.1 N at 0.3 mm. That does not locate the
    Core; the saddle's block does.
  - Smallest gaps in the model: Dock magnets to the base board 2.9 mm in BAR and 9.7 mm in FLOAT;
    their bosses to the base board 1.6 mm in BAR.
- Port drawer: the port panel (49.2 x 20 x 2 mm) with a 3.5 mm high shelf; the base board is
  screwed onto the shelf (two M2 x 4; an M2 x 5 is 0.1 mm longer than board and hole) with its rear edge on the panel's inside. The jack stands
  0.3 mm proud of the panel; the USB-C opening has a pocket for the plug's overmould (0.55 mm of
  panel left). The drawer goes in from the Dock's rear (board 0.5 mm play each side) until the
  panel lies on a 1 mm ledge at each end, and is screwed from below: one M2 x 10 countersunk
  through a boss in the bar, two M2 x 6 through the plate of FLOAT.
- Lock (optional since the magnets): two M2 x 8 screws from inside the Dock into two of the Core's floor bosses, 5 mm of each
  screw in the Dock's front and 3 mm in the Core. They are reached with a long screwdriver through
  two 4.5 mm holes in the Dock's rear in BAR, and with the cap lifted off in FLOAT. BAR uses the
  outer bosses (20 mm above the Core's bottom edge); its holes come out of the bar's back about
  12 mm above the table, either side of the panel. FLOAT uses the inner bosses (25 mm up), because
  the outer ones are outside the pod; the screwdriver lies in the open pod and passes 1.37 mm over
  the port panel, so the pod has no holes. Without the screws only the magnets
  hold the Core. That is the whole lock: it stops a quick grab, not a thief with a screwdriver.
  Thread-forming screws in printed bosses wear out after a few cycles; a production part needs
  threaded inserts or a latch. The owner asked on 2026-11-12 for a lock without screws. A latch in
  the Dock that springs into a slot in the Core's rear and is released with a pin tool through a
  hole is the candidate; it is not designed, and waits until both bodies have been printed.
- Checked by the scripts on 2026-11-10 (FLOAT's body again on 2026-11-12): ERC of both boards (0 messages), DRC (contact board
  0 violations and 0 unconnected pads; base board 0 unconnected pads and 2 `silk_edge_clearance`
  warnings where the jack overhangs the edge; `reports/drc-dock-*.rpt`), each printed part is one
  solid, and for each body no interference between any two of: body or pod, caps or cap and
  plate, saddle, drawer, both board models, the jack and both mated harness plugs (boxes), the Core's
  body and its panel. The spring pins have no 3D model, so they are not in that check. Smallest
  gaps measured in the model: jack to body 0.5 mm in BAR (the jack's end to the front wall) and
  1.6 mm in FLOAT (1.7 mm to the cap); base board to body 0.3 mm in BAR and 0.5 mm in FLOAT.
  Run again on 2026-11-12 with the magnets and the tighter block, with the Core's four magnets and
  the Dock's two stacks as parts of the check: no interference in either body, and none between
  the Core's body, its magnets and the Core board's model.
- Standing. Neither body stands a firm press on the screen by its own weight; both have to be
  fixed to the counter (mounting tape; a lock against theft needs that anyway). Estimate, with
  masses that are assumed and not weighed (Core 110 g, both Dock boards with the jack 15 g, printed
  parts solid PLA): the assembly tips backwards when a horizontal push exceeds about 0.25 N at
  the screen's top edge and 0.5 N at its middle for BAR, 0.6 N and 1.1 N for FLOAT with the printed
  plate, 0.9 N and 1.7 N with a steel plate. With a Core of 80 or 150 g the figures move by about
  a quarter. Sliding is not estimated. FLOAT's figures were worked out for the first pod and not
  again for the wedge of 2026-11-12; the plate is the same.
- Tolerances, estimated and not measured. Sideways: block in window 0.3 mm, pin body in its hole
  0.2 mm, Core board on its screws 0.15 mm, together 0.65 mm against the 0.55 mm a 0.9 mm plunger
  may be off centre on a 2.0 mm pad. Along the Core's height the chain is the same since
  2026-11-12, and the Core's weight takes up the block's play downwards. In height: the pin's window is +/-0.3 mm, set by the Core's
  rear face and boss, the Dock's front face and recess floor (four printed surfaces) and the
  contact board's thickness.
- Assumptions and gaps:
  - The jack stands 2.3 mm over the board's edge. Wurth's drawing has to confirm where the edge may be.
  - KiCad has no 3D model of the jack on this machine; the interference check uses a box of its
    outline (16.1 x 25.4 x 13.55 mm). Its pins (3.05 mm, `wurth_7499010121A.pdf` p.1) are not in
    the model; the shelf leaves that area free.
  - The Ethernet pairs on both boards are autorouted, not routed as pairs. Clearance between the
    jack's shield net and GND is not checked against an isolation voltage.
  - The router keeps no distance to the notch's inner edges; `tools/dock_pcb.py` adds keep-out
    areas 0.45 mm around the notch for that.
  - Ethernet through spring pins, a harness and two connectors is unproven (open item 5).
  - All pins have the same length, so GND does not make contact first. Attach and detach with the
    Dock unpowered until that is solved or tested. With magnets, attaching to a powered Dock is
    what a user will do, so this has to be tested before anything else (bring-up 7 and 7a).
  - Magnets: only glue holds them (cyanoacrylate assumed), their poles are set by hand at
    assembly, and N42 is good to 80 C (supplier pages). What the Dock's bare magnets do to a
    card with a magnetic stripe laid against them is not looked at.
  - Not designed: cable strain relief, a slot for a security cable, feet, ballast.
  - How the harness lies is not drawn. In BAR its wires have about 6 mm behind the contact board's
    plug before the base board's notch edge.
  - Printing is not worked out. The bar's body standing on one end needs supports inside (the
    walls at the panel's ends, bosses, the pin guide); the pod can lie on its front face; the
    saddle's plate is 1.05 mm thick and bridges the board.
  - The saddle is screwed on one side only. Its other side is held down by the Core when docked.
  - Thin places: BAR has 1.6 mm of front wall behind the jack; FLOAT has a 1.2 mm web between the
    panel's pocket and each screwdriver hole.
  - The look needs two filaments: the body in the Core's colour, caps or plate in orange. In BAR
    the caps and the Core's side walls are flush only as far as the prints match.
  - The LAN Module is not started.
