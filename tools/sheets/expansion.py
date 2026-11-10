"""expansion: 18-pad rear contact field P1 and its protection parts.

Sources: docs/design-spec.md section 7 (pad table, ACC_ID network, series and pull-up values).
Datasheets (docs/reference/, PDF page indexes): tpd4e05u06.pdf, bat54s_onsemi.pdf.
P1 footprint: tools/maratus_lib.py rear_pads().
"""
from sch import NC

ESD = "Power_Protection:TPD4E05U06DQA"
ESD_FP = "Package_SON:USON-10_2.5x1.0mm_P0.5mm"


def build(s):
    s.group("P1 rear contact field - 2 x 9 pads, row a / row b as in design-spec section 7")
    s.part("P1", "Connector_Generic:Conn_02x09_Row_Letter_First", "Rear pads 2x9", {
        "a1": "GND", "a2": "ETH_TX_P", "a3": "ETH_TX_N", "a4": "GND", "a5": "ETH_RX_P", "a6": "ETH_RX_N",
        "a7": "GND", "a8": "ACC_USB_DP", "a9": "ACC_USB_DN",
        "b1": "VIN", "b2": "VIN", "b3": "GND", "b4": "ACC_ID", "b5": "ACC_IO1_PAD", "b6": "ACC_IO2_PAD",
        "b7": "ACC_INT_N_PAD", "b8": "GND", "b9": "V_ACC",
    }, "maratus:RearPads_2x9_P2.54mm_D2.0mm",
        src="design-spec 7 pad table. Pad diameter 2.0 mm is an assumption: confirm against the Dock's spring pins")

    s.group("Accessory ID - 10k pull-up, 10k series, clamp to the rails; the 0.1 uF sits at the ADC pin on p4-core")
    s.R("10k 1%", "3V3", "ACC_ID", src="design-spec 7")
    s.R("10k 1%", "ACC_ID", "ACC_ID_ADC", src="design-spec 7")
    s.part("D601", "Diode:BAT54S", "BAT54S", {"A": "GND", "K": "3V3", "COM": "ACC_ID_ADC"},
           "Package_TO_SOT_SMD:SOT-23", src="bat54s_onsemi.pdf p.1: pin 1 anode, 2 cathode, 3 common; 30 V, 200 mA")

    s.group("Accessory IO - 100R series, 10k pull-ups, ESD array on the pad side")
    for net in ("ACC_IO1", "ACC_IO2", "ACC_INT_N"):
        s.R("100R", net, net + "_PAD", src="design-spec 7")
        s.R("10k", "3V3", net, src="design-spec 7")
    s.part("D602", ESD, "TPD4E05U06DQA", {
        "D1+": "ACC_IO1_PAD", "D1-": "ACC_IO2_PAD", "D2+": "ACC_INT_N_PAD", "D2-": "ACC_ID", "GND": "GND", "NC": NC,
    }, ESD_FP, src="tpd4e05u06.pdf p.4 Table 4-2: 1 D1+, 2 D1-, 3 GND, 4 D2+, 5 D2-, 8 GND, others NC. p.7: stand-off "
                    "5.5 V")

    s.group("Accessory USB (P4 high-speed PHY, host) - ESD array, optional 1M on DP")
    s.part("D603", ESD, "TPD4E05U06DQA", {
        "D1+": "ACC_USB_DP", "D1-": "ACC_USB_DN", "D2+": NC, "D2-": NC, "GND": "GND", "NC": NC,
    }, ESD_FP, src="tpd4e05u06.pdf p.1: 0.42-0.5 pF typical per line; design-spec 7 asks for at most 1 pF")
    s.R("1M", "ACC_USB_DP", "GND", dnp=True, src="design-spec 4: optional 1M on DP")
