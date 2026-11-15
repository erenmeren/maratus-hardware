"""display: LCD FFC, touch FFC, backlight boost driver.

Panel: Newhaven NHD-4.0-480480AF-MSXP-CTP, 4.0 inch 480 x 480 IPS, ST7701SN, 2-lane MIPI DSI, FT5426G touch.
Sources (page numbers are PDF page indexes):
- docs/reference/NHD-4.0-480480AF-MSXP-CTP.pdf: p.4 drawing and connector part numbers, p.5 pin tables,
  p.6 supply and backlight ratings, p.7 DSI timing values, p.18 touch I2C address (0x70 write = 0x38).
- docs/reference/ST7701S_SPEC_V1.4.pdf: p.37 IM pins, p.37-38 unused SPI pins, p.39 LANSEL.
- docs/reference/tps61169.pdf.
- docs/reference/mbr0540.pdf.
Contact side: the LCD tail has its contacts on the display-front side, the touch tail on the back (p.4). The
board's part side faces the display and both tails fold back behind the panel, so J2 is bottom-contact and
J4 top-contact, both with the opening towards the bottom edge, pins in panel order. Confirm on a sample.
"""
from sch import NC, C0603, C0805

R0603 = "Resistor_SMD:R_0603_1608Metric"


def build(s):
    s.group("LCD FFC J2 - 24-pin 0.5 mm, MIPI DSI mode, 2 data lanes")
    s.part("J2", "Connector_Generic_MountingPin:Conn_01x24_MountingPin", "FH12-24S-0.5SH(55)", {
        "1": "LED_K", "2": "LED_A", "3": NC, "4": "3V3", "5": "GND",
        "6": "DSI_D0_N", "7": "DSI_D0_P", "8": "GND", "9": "DSI_CLK_N", "10": "DSI_CLK_P", "11": "GND",
        "12": "DSI_D1_N", "13": "DSI_D1_P", "14": "GND", "15": "LCD_RST_N",
        "16": "LCD_CSX", "17": "GND", "18": "GND", "19": NC, "20": "LCD_TE",
        "21": "LCD_IM0", "22": "GND", "23": "GND", "24": "LCD_LANSEL", "MP": "GND",
    }, "Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal",
        src="NHD-4.0-480480AF-MSXP-CTP.pdf p.5: 1 LED_K, 2 LED_A, 3 NC, 4 VDD, 5 GND, 6 DN0, 7 DP0, 8 GND, 9 CN, "
            "10 CP, 11 GND, 12 DN1, 13 DP1, 14 GND, 15 RESETX, 16 CSX, 17 SCL, 18 SDA, 19 SDO, 20 TE_L, 21 IM0, "
            "22 IM1, 23 IM3, 24 LANSEL. Pad n = panel pin n: the parts face the display, the tail folds back "
            "behind the panel, and seen from the front both pin 1 and the footprint's pad 1 are on the left. "
            "Hirose FH12-24S-0.5SH(55): bottom contact, 0.30 mm FFC, active (DigiKey listing read 2026-11-10; "
            "Hirose's datasheet is not in docs/reference)")
    s.R("10k", "3V3", "LCD_IM0", src="NHD p.5 interface table: MIPI DSI is IM0 = 1, IM1 = 0, IM3 = 0 or 1")
    s.R("10k", "3V3", "LCD_LANSEL", src="ST7701S_SPEC_V1.4.pdf p.39: LANSEL high = 2 data lanes, low = 1")
    s.R("10k", "3V3", "LCD_CSX", src="ST7701S_SPEC_V1.4.pdf p.37-38: unused CSX and SCL to VDDI or DGND, SDA to "
                                      "DGND, SDO open")
    s.R("10k", "3V3", "LCD_RST_N", src="gpio map: panel out of reset while the P4 pin floats")
    s.C("4.7uF 10V", "3V3", fp=C0603, src="assumption: panel supply decoupling at J2. NHD p.6: VDD 3.3 V, 65 mA max")
    s.C("100nF", "3V3")
    s.tp("LCD_TE")

    s.group("Touch FFC J4 - 6-pin 1.0 mm, FT5426G, I2C address 0x38")
    s.part("J4", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "TE 84953-6", {
        "1": "3V3", "2": "GND", "3": "I2C0_SCL", "4": "I2C0_SDA", "5": "TP_INT", "6": "TP_RST_N", "MP": "GND",
    }, "Connector_FFC-FPC:TE_84953-6_1x06-1MP_P1.0mm_Horizontal",
        src="NHD-4.0-480480AF-MSXP-CTP.pdf p.5: 1 VDD, 2 GND, 3 SCL, 4 SDA, 5 INT, 6 RST; pad n = touch pin n, as "
            "for J2. TE 84953-6: 6 positions, 1 mm, top contact, 0.3 mm FFC (te.com product page read 2026-11-10; "
            "that page also says it is not currently available, so stock is unconfirmed)")
    s.R("4.7k", "3V3", "I2C0_SCL", src="NHD p.5: SCL and SDA require 4.7k pull-ups")
    s.R("4.7k", "3V3", "I2C0_SDA")
    s.R("10k", "3V3", "TP_RST_N", src="assumption: touch out of reset while the P4 pin floats")
    s.R("10k", "3V3", "TP_INT", src="assumption: the datasheet does not say whether INT is open-drain")
    s.C("100nF", "3V3", src="assumption: touch supply decoupling at J4. NHD p.6: 2.7-3.6 V, 15.85 mA")

    s.group("Backlight boost U8 - 3V3 to the LED array (6.1 V, 140 mA typical)")
    s.part("U8", "maratus:TPS61169DCK", "TPS61169DCKR", {
        "VIN": "3V3", "CTRL": "LCD_BL_PWM", "SW": "BL_SW", "FB": "LED_K", "GND": "GND",
    }, "Package_TO_SOT_SMD:SOT-353_SC-70-5",
        src="tps61169.pdf p.3 pins, p.5 limits, PWM 5-100 kHz on CTRL. Fed from 3V3, not 5V_SYS: p.9 section 6.3.3 "
            "needs the LED array's minimum forward voltage above the maximum input voltage, or the LEDs glow "
            "through L and D in shutdown. NHD p.6: array 5.4 V minimum at 140 mA, lower when dimmed")
    s.part("L401", "Device:L", "4.7uH LPS4018-472ML", {"1": "3V3", "2": "BL_SW"},
           "Inductor_SMD:L_Coilcraft_LPS4018", src="tps61169.pdf p.12 Table 7-2: 1.9 A saturation. Peak about "
                                                   "0.6 A from eq. 3-5 at 3.3 V in, 7.0 V out, 147 mA, 0.75 MHz")
    s.part("D401", "Diode:MBR0540", "MBR0540", {"A": "BL_SW", "K": "LED_A"}, "Diode_SMD:D_SOD-123",
           src="mbr0540.pdf p.2: 40 V, 0.5 A average, 1.0 A repetitive peak. tps61169.pdf p.12: breakdown above the "
               "open-LED protection voltage (36-39 V, p.5): 1 V of margin at the 39 V limit")
    s.C("1uF 50V", "LED_A", fp=C0805, src="tps61169.pdf p.11 Figure 7-1, p.13: 1 uF to 4.7 uF. 50 V for open-LED")
    s.C("4.7uF 10V", "3V3", fp=C0603, src="tps61169.pdf p.11 Figure 7-1")
    # ILED = VFB / RSET. 1.5 ohm: 125 / 136 / 147 mA for VFB 188 / 204 / 220 mV. 32 mW at 147 mA.
    s.R("1.5R 1%", "LED_K", "GND", fp=R0603, src="tps61169.pdf p.9 eq. 1, p.5 VREF. NHD p.6: backlight 140 mA "
                                                  "typical, 168 mA maximum")
    s.R("100k", "LED_A", "GND", src="assumption: discharges the output capacitor after an open-LED shutdown, so "
                                    "plugging the panel back in does not dump up to 39 V into a 6 V array")
    s.R("100k", "LCD_BL_PWM", "GND", src="gpio map: backlight off while the P4 is in reset")
    s.tp("LED_A")
    s.tp("LED_K")
