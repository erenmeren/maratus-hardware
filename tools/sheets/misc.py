"""misc: buzzer, service switch, USB-C data, camera footprint (DNP).

Sources: docs/design-spec.md sections 4 and 9; SCH_ESP32-P4X_FUNCTION_EV_BOARD_V1.7_20260203.pdf p.3
(CSI connector J9 pin order). Datasheets in docs/reference/ (PDF page indexes): usblc6-2.pdf,
cmt-8504-100-smt.pdf, ao3400a.pdf, mbr0540.pdf, b3u_omron.pdf.
"""
from sch import NC, C0805


def build(s):
    s.group("USB-C data - ESD at the connector side, 22R series to the P4 USB-Serial-JTAG pins")
    s.part("D701", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", {
        "I/O1": "USBC_CONN_DP", "I/O2": "USBC_CONN_DN", "VBUS": "VBUS", "GND": "GND",
    }, "Package_TO_SOT_SMD:SOT-23-6", src="usblc6-2.pdf p.1: 1 and 6 I/O1, 2 GND, 3 and 4 I/O2, 5 VBUS. p.2: 3.5 pF max")
    s.R("22R", "USBC_CONN_DP", "USBC_DP", src="design-spec 4: series 22R on GPIO25 (D+)")
    s.R("22R", "USBC_CONN_DN", "USBC_DN", src="design-spec 4: series 22R on GPIO24 (D-)")

    s.group("Buzzer - 5 V magnetic transducer on 5V_SYS, low-side N-MOSFET, flyback diode, gate pull-down")
    s.part("BZ701", "Device:Buzzer", "CMT-8504-100-SMT", {"+": "BUZZER_P", "-": "BUZZER_N"},
           "Buzzer_Beeper:MagneticBuzzer_CUI_CMT-8504-100-SMT",
           src="cmt-8504-100-smt.pdf p.1: rated 5 V, 1-6 V, 150 mA max, 4 kHz, 100 dB at 10 cm, coil 12-18 ohm. "
               "p.2: + pad top left, - pad bottom left, two dummy pads (footprint pads 1, 2, 3 and 4)")
    s.R("0R", "5V_SYS", "BUZZER_P", src="buzzer is rated 5 V; keeps its 4 kHz current pulses off 3V3")
    s.C("10uF 10V", "BUZZER_P", fp=C0805, src="assumption: local reservoir for the coil current pulses")
    s.part("D702", "Diode:MBR0540", "MBR0540", {"K": "BUZZER_P", "A": "BUZZER_N"}, "Diode_SMD:D_SOD-123",
           src="flyback across the coil, design-spec 9. Same part as D401. mbr0540.pdf p.2: 40 V, 0.5 A average, "
               "1.0 A repetitive peak; coil peak is 5.5 V / 12 ohm = 0.46 A")
    s.part("Q701", "Transistor_FET:AO3400A", "AO3400A", {"G": "BUZZER_GATE", "S": "GND", "D": "BUZZER_N"},
           "Package_TO_SOT_SMD:SOT-23", src="ao3400a.pdf p.1-2: 30 V, 5.7 A, under 48 mOhm at 2.5 V gate drive, "
                                            "threshold 0.65-1.45 V. Replaces 2N7002 (too weak for 0.46 A)")
    s.R("100R", "BUZZER_PWM", "BUZZER_GATE", src="assumption: gate series resistor")
    s.R("100k", "BUZZER_GATE", "GND", src="design-spec 9: 100k pull-down")

    s.group("Service switch - recessed, active low")
    s.part("SW701", "Switch:SW_Push", "B3U-3000P", {"1": "SERVICE_BTN_N", "2": "GND"},
           "Button_Switch_SMD:SW_SPST_B3U-3000P",
           src="b3u_omron.pdf p.1, p.3: side-actuated (owner, 2026-11-14: pressed through a slot in the bottom wall), "
               "SPST-NO, no ground terminal, 1.59 N, 10 uA at 1 V minimum load. Until then B3U-1000P on the back")
    s.R("10k", "3V3", "SERVICE_BTN_N", src="design-spec 9")
    s.C("100nF", "SERVICE_BTN_N", src="assumption: debounce")

    s.group("Camera connector (DNP) - 15 pins at 1.0 mm, pin order of Espressif EV board J9")
    s.part("J3", "Connector_Generic_MountingPin:Conn_01x15_MountingPin", "TE 1-84952-5 (DNP)", {
        "1": "GND", "2": "CSI_D0_N", "3": "CSI_D0_P", "4": "GND", "5": "CSI_D1_N", "6": "CSI_D1_P", "7": "GND",
        "8": "CSI_CLK_N", "9": "CSI_CLK_P", "10": "GND", "11": NC, "12": NC, "13": NC, "14": NC, "15": "CAM_3V3",
        "MP": "GND",
    }, "Connector_FFC-FPC:TE_1-84952-5_1x15-1MP_P1.0mm_Horizontal", dnp=True,
        src="P4X EV board schematic p.3 J9: 1 GND, 2 DN0, 3 DP0, 4 GND, 5 DN1, 6 DP1, 7 GND, 8 CLK_N, 9 CLK_P, "
            "10 GND, 11 CAM_IO0, 12 CAM_IO1, 13 SCL, 14 SDA, 15 3V3. EV BOM J9: 15 position, 1 mm. Waveshare "
            "schematic p.1 J1 has the same order. Candidate connector, bottom contact, its datasheet is not in "
            "docs/reference")
    s.R("0R", "3V3", "CAM_3V3", dnp=True, src="keeps the unused connector unpowered")
    s.C("10uF 10V", "CAM_3V3", fp=C0805, dnp=True, src="P4X EV board schematic p.3 C46")
