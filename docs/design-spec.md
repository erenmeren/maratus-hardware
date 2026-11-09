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
| U3 | 16 MB quad SPI NOR, 3.3 V (W25Q128JVSIQ candidate) | Confirm | Winbond datasheet; Espressif flash guidance |
| U4 | TLV62569 buck for VDD_HP | Verified as an Espressif-listed DCDC | TI datasheet; P4X reference schematic |
| U5 | TLV62569 buck, 5 V to 3.3 V, 2 A class | Confirm ratings | TI datasheet |
| U6 | TPS2121RUXR power mux | Verified | TI datasheet |
| U7 | IP101GRI Ethernet PHY, QFN-32 | Verified | IC Plus IP101G datasheet |
| U8 | Backlight boost LED driver | Blocked on panel datasheet | – |
| U9 | Current-limited 5 V switch for V_ACC, about 0.5 A | Confirm | TI TPS2553 datasheet (candidate) |
| U10 | Reset supervisor, about 3.0 V threshold | Confirm | candidate TPS3839 |
| J1 | USB-C receptacle, USB 2.0, 16-pin (GCT USB4105 candidate) | Confirm | GCT drawing |
| J2 | LCD + touch FPC connector, 30-pin 0.5 mm | Blocked on panel datasheet | – |
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
5V_SYS --> backlight boost --> LED string
5V_SYS --> U9 switch (ACC_PWR_EN, ACC_PWR_FLT_N) --> V_ACC pad
3V3    --> U10 supervisor --> P4_EN (CHIP_PU)
```

- TPS2121: over-voltage lockout just above 5.5 V, current limit about 2.2 A, status pin to
  `PWR_SRC_ST`. Resistor values from the TI datasheet equations.
- Budget on 5V_SYS: about 360 mA typical, 1.0 A peak, 1.5 A with a 0.5 A accessory.
  3V3 peak about 0.97 A (C5 transmit 403 mA, P4 minimum supply 430 mA).
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
face of the PCB. No vias in pads.

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

- Panel class: 4.0-inch 720 x 720 IPS, ST7703, 2-lane MIPI DSI, GT911 touch over I2C, bonded cover
  glass. Candidate: Startek KD040HDFID032-C026C (84.00 x 85.99 x 3.76 mm, 30-pin 0.5 mm FPC).
- Blocked: FPC pinout, logic supply levels, connector contact side, backlight LED string voltage
  and current. Do not draw J2 or U8 from assumptions.
- Known Core-side nets: DSI clock and two data pairs, `LCD_RST_N` GPIO3, `LCD_BL_PWM` GPIO2,
  `TP_RST_N` GPIO4, `TP_INT` GPIO5, `I2C0_SDA` GPIO7, `I2C0_SCL` GPIO8 (2.2 k pull-ups).

## 9. Other blocks

- Buzzer: SMD electromagnetic transducer, N-MOSFET low-side driver with flyback diode, gate from
  `BUZZER_PWM` (GPIO6) with 100 k pull-down.
- Service switch: `SERVICE_BTN_N` on GPIO9, 10 k pull-up, reachable only with a pin tool.
- Test pads: P4_EN, BOOT (GPIO35), UART0 TX/RX, C5 EN/BOOT/UART0, all rails, every spare GPIO.
- Camera: 22-pin 0.5 mm FPC footprint on the CSI pins, not populated.

## 10. PCB constraints

- Outline at most 78 x 82 mm, 4 layers, 1.2 mm, controlled impedance, parts on the rear face.
- C5 module at the top edge, antenna section clear of copper, the LCD metal back, magnets and
  screws. Take the keep-out from the module datasheet, section "Module Placement for PCB Design".
- P4, core DCDC, crystal and flash in one tight group.
- DSI pairs 100 ohm differential over unbroken ground. SDIO and RMII length-matched per group.
- USB-C and buzzer port on the bottom edge. Rear pad field towards the lower half.

## 11. Open items

1. Panel datasheet, drawing, init sequence and samples.
2. Body shape: taller body with PCB antenna (assumed) or square body with ESP32-C5-WROOM-1U.
3. Flash part number against Espressif's guidance.
4. Backlight driver and buzzer part numbers.
5. Ethernet through pogo contacts is unproven until a prototype passes a 24-hour soak.
