"""power: USB-C input, rear-pad input, power mux, 3.3 V buck, V_ACC switch, reset supervisor.

Sources (docs/reference/): tps2121.pdf, tlv62569.pdf, tps2553.pdf, tps3839.pdf, GCT_USB4105_drawing.pdf,
smaj5.0a_vishay.pdf,
design-spec.md section 3. Page numbers are PDF page indexes.
"""
from sch import NC, C0603, C0805

SMA = "Diode_SMD:D_SMA"


def build(s):
    s.group("USB-C input (J1) - VBUS to mux IN2, CC pull-downs and CC sense dividers")
    s.part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB4105-GF-A", {
        "VBUS": "VBUS", "GND": "GND", "SHIELD": "GND", "CC1": "USBC_CC1", "CC2": "USBC_CC2",
        "D+": "USBC_CONN_DP", "D-": "USBC_CONN_DN", "SBU1": NC, "SBU2": NC,
    }, "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
        src="GCT_USB4105_drawing.pdf p.1: pin table, ratings, ordering grid (GF = gold flash, A = tape and reel, 0.95 mm shell stakes)")
    s.R("5.1k", "USBC_CC1", "GND", src="design-spec 3: 5.1k Rd on each CC")
    s.R("5.1k", "USBC_CC2", "GND")
    # 100k + 100k: halves the CC voltage for the ADC and adds 200k in parallel with the 5.1k Rd (-2.5 %)
    s.R("100k", "USBC_CC1", "USBC_CC1_SENSE", src="assumption: divider ratio 1/2")
    s.R("100k", "USBC_CC1_SENSE", "GND")
    s.R("100k", "USBC_CC2", "USBC_CC2_SENSE")
    s.R("100k", "USBC_CC2_SENSE", "GND")
    s.part("D101", "Diode:SMAJ5.0CA", "SMAJ5.0CA", {"1": "VBUS", "2": "GND"}, SMA,
           src="smaj5.0a_vishay.pdf p.2: stand-off 5.0 V, breakdown 6.40-7.25 V, clamp 9.2 V at 43.5 A. Bidirectional so "
               "it cannot be fitted reversed. tps2121.pdf p.31-32: hot-plug needs a TVS at the input. Stand-off is "
               "below the 5.5 V USB-C maximum: leakage rises above 5.0 V")
    s.C("1uF 25V", "VBUS", fp=C0603)
    s.flag("VBUS")
    s.flag("GND")

    s.group("Rear-pad input - VIN to mux IN1 (priority)")
    s.part("D102", "Diode:SMAJ5.0CA", "SMAJ5.0CA", {"1": "VIN", "2": "GND"}, SMA, src="same as D101")
    s.C("1uF 25V", "VIN", fp=C0603)
    s.flag("VIN")

    s.group("Power mux U6 - XCOMP mode: IN1 has priority while IN1 > 0.86 x IN2, fast switchover")
    s.part("U6", "maratus:TPS2121RUX", "TPS2121RUXR", {
        "IN1": "VIN", "IN2": "VBUS", "OUT": "5V_SYS", "GND": "GND", "PR1": "MUX_PR1", "CP2": "MUX_CP2",
        "OV1": "MUX_OV1", "OV2": "MUX_OV2", "ILM": "MUX_ILM", "SS": "MUX_SS", "ST": "PWR_SRC_ST",
    }, "Package_DFN_QFN:Texas_VQFN-HR-12_2x2.5mm_P0.5mm",
        src="tps2121.pdf p.4-5 pins, p.18 Table 9-3 modes, p.25-26 XCOMP example (Figure 10-9)")
    # PR1 = VIN x 4.99/(4.99+8.06) = 0.382 VIN; CP2 = VBUS x 4.99/(4.99+10.2) = 0.329 VBUS.
    # CP2 >= VREF enables fast switchover; IN1 is used while PR1 > CP2, i.e. VIN > 0.86 x VBUS (4.30 V at 5.0 V).
    s.R("8.06k 1%", "VIN", "MUX_PR1", src="tps2121.pdf p.26 eq. 12-13, values recalculated for 5 V / 5 V")
    s.R("4.99k 1%", "MUX_PR1", "GND")
    s.R("10.2k 1%", "VBUS", "MUX_CP2", src="tps2121.pdf p.26 eq. 12 (same divider as the TI example)")
    s.R("4.99k 1%", "MUX_CP2", "GND")
    # OVLO = VREF x (22.1+4.99)/4.99 = 5.43 x VREF: 5.48 / 5.75 / 5.97 V for VREF 1.01 / 1.06 / 1.10 V
    s.R("22.1k 1%", "VIN", "MUX_OV1", src="tps2121.pdf p.23 eq. 6, p.8 VREF 1.01/1.06/1.10 V")
    s.R("4.99k 1%", "MUX_OV1", "GND")
    s.R("22.1k 1%", "VBUS", "MUX_OV2")
    s.R("4.99k 1%", "MUX_OV2", "GND")
    # ILM = 65.2 / R^0.861 (R in kOhm) = 2.20 A typ at 51.1k
    s.R("51.1k 1%", "MUX_ILM", "GND", src="tps2121.pdf p.13 eq. 2")
    s.C("1uF", "MUX_SS", src="tps2121.pdf p.13 Table 9-1: 88 V/s at 5 V; p.25 Figure 10-9 uses 1 uF")
    s.R("10k", "3V3", "PWR_SRC_ST", src="tps2121.pdf p.6: ST pull-up 6-20k. High = IN1 (rear pads) or off, low = USB-C")
    s.C("22uF 10V", "5V_SYS", fp=C0805)
    s.C("22uF 10V", "5V_SYS", fp=C0805)
    s.C("100nF", "5V_SYS")
    s.R("200k 1%", "5V_SYS", "VSYS_SENSE", src="assumption: ratio 1/3, 1.83 V at 5.5 V")
    s.R("100k 1%", "VSYS_SENSE", "GND")
    s.tp("5V_SYS")

    s.group("3.3 V buck U5 - 5V_SYS to 3V3, 2 A class")
    s.part("U5", "Regulator_Switching:TLV62569DBV", "TLV62569DBVR", {
        "VIN": "5V_SYS", "EN": "5V_SYS", "GND": "GND", "SW": "BUCK3V3_SW", "FB": "BUCK3V3_FB",
    }, "Package_TO_SOT_SMD:SOT-23-5", src="tlv62569.pdf p.3 pins, p.8 Figure 5 and Table 3")
    s.part("L101", "Device:L", "2.2uH XAL4020-222ME", {"1": "BUCK3V3_SW", "2": "3V3"},
           "Inductor_SMD:L_Coilcraft_XAL4020-XXX", src="tlv62569.pdf p.8 Table 3, p.9 Table 4")
    # VOUT = 0.6 V x (1 + 453k/100k) = 3.318 V
    s.R("453k 1%", "3V3", "BUCK3V3_FB", src="tlv62569.pdf p.9 eq. 2, R2 <= 200k")
    s.R("100k 1%", "BUCK3V3_FB", "GND")
    s.C("6.8pF", "3V3", "BUCK3V3_FB", dnp=True, src="tlv62569.pdf p.9: optional feed-forward for R2 = 100k")
    s.C("10uF 10V", "5V_SYS", fp=C0805, src="tlv62569.pdf p.10: 4.7 uF or more at the input")
    s.C("100nF", "5V_SYS")
    s.C("22uF 10V", "3V3", fp=C0805, src="tlv62569.pdf p.9 Table 4: 2.2 uH with 10-44 uF proven for VOUT >= 1.8 V")
    s.C("100nF", "3V3")
    s.flag("3V3")
    s.tp("3V3")

    s.group("V_ACC switch U9 - 5V_SYS to the accessory pad, off by default")
    s.part("U9", "maratus:TPS2553DBV", "TPS2553DBVR", {
        "IN": "5V_SYS", "GND": "GND", "EN": "ACC_PWR_EN", "~{FAULT}": "ACC_PWR_FLT_N", "ILIM": "ACC_ILIM",
        "OUT": "V_ACC",
    }, "Package_TO_SOT_SMD:SOT-23-6", src="tps2553.pdf p.4 pins, p.3 Table 4-1 (active high, auto retry)")
    # IOS min/nom/max = 25230/R^1.016, 23950/R^0.977, 22980/R^0.94 mA = 524 / 577 / 638 mA at 45.3k
    s.R("45.3k 1%", "ACC_ILIM", "GND", src="tps2553.pdf p.16-17 eq. 1-3")
    s.R("100k", "ACC_PWR_EN", "GND", src="gpio map: off by default. tps2553.pdf p.6: EN has no internal pull")
    s.R("10k", "3V3", "ACC_PWR_FLT_N", src="gpio map: open-drain fault, 10k pull-up")
    s.C("100nF", "5V_SYS", src="tps2553.pdf p.4: 0.1 uF or more from IN to GND, close to the IC")
    s.C("10uF 10V", "V_ACC", fp=C0805, src="assumption; tps2553.pdf p.1 ESD rating needs external capacitance")
    s.C("100nF", "V_ACC")
    s.tp("V_ACC")

    s.group("Reset supervisor U10 - holds P4_EN low until 3V3 is above 2.93 V, then 200 ms")
    s.part("U10", "Power_Supervisor:TPS3839DBZ", "TPS3839K33DBZ", {
        "VDD": "3V3", "GND": "GND", "~{RESET}": "SUP_RESET_N",
    }, "Package_TO_SOT_SMD:SOT-23", src="tps3839.pdf p.1 (push-pull, 200 ms), p.4 (K33 = 2.93 V)")
    # push-pull output: the 1k lets a test jig or the RC on P4_EN pull the line without fighting the supervisor
    s.R("1k", "SUP_RESET_N", "P4_EN", src="assumption")
    s.C("100nF", "3V3")
