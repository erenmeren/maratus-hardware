"""dock-base: the Dock's base board. USB-C power input, RJ45 jack with magnetics, harness to the contact board.

Sources (docs/reference/): GCT_USB4105_drawing.pdf, smaj5.0a_vishay.pdf, wurth_7499010121A.pdf p.1 (pins: 1 TD+,
2 CTD, 3 TD-, 4 RD+, 5 CRD, 6 RD-, 8 chassis side of the 1 nF / 2 kV capacitor, 9-12 LEDs; 1:1 turns ratio),
jst_ePH.pdf, IP101G_preliminary_datasheet_lcsc.pdf p.7 and p.55 (centre taps go to capacitors, not to a supply).
The PHY sits in the Core; this board only carries the magnetics. No LED signals come over the rear pads, so the
jack's LEDs stay dark.
"""
from sch import NC, C0805

SMA = "Diode_SMD:D_SMA"


def build(s):
    s.group("USB-C power input - 5 V only, no data")
    s.part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB4105-GF-A", {
        "VBUS": "VIN", "GND": "GND", "SHIELD": "GND", "CC1": "USBC_CC1", "CC2": "USBC_CC2",
        "D+": NC, "D-": NC, "SBU1": NC, "SBU2": NC,
    }, "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
        src="GCT_USB4105_drawing.pdf p.1. The Core's own mux and TVS follow on its VIN pads")
    s.R("5.1k", "USBC_CC1", "GND", src="Rd on each CC so a USB-C source turns VBUS on")
    s.R("5.1k", "USBC_CC2", "GND")
    s.part("D1", "Diode:SMAJ5.0CA", "SMAJ5.0CA", {"1": "VIN", "2": "GND"}, SMA,
           src="smaj5.0a_vishay.pdf p.2: stand-off 5.0 V, clamp 9.2 V at 43.5 A")
    s.C("10uF 10V", "VIN", fp=C0805, src="assumption: bulk capacitor at the input")
    s.C("100nF", "VIN")
    s.flag("VIN")
    s.flag("GND")

    s.group("RJ45 with 10/100 magnetics - pairs from the Core's PHY, centre taps to capacitors")
    s.part("J2", "Connector:RJ45_Wuerth_7499010121A", "7499010121A", {
        "1": "ETH_TX_P", "2": "ETH_TCT", "3": "ETH_TX_N", "4": "ETH_RX_P", "5": "ETH_RCT", "6": "ETH_RX_N", "7": NC,
        "8": "CHASSIS", "9": NC, "10": NC, "11": NC, "12": NC, "SH": "CHASSIS",
    }, "Connector_RJ:RJ45_Wuerth_7499010121A_Horizontal",
        src="wurth_7499010121A.pdf p.1 schematic. Transmit pair of the Core's PHY on TD, receive pair on RD")
    s.C("100nF", "ETH_TCT", src="IP101G datasheet p.7, p.55: centre tap to a capacitor, no supply")
    s.C("100nF", "ETH_RCT")
    s.R("1M", "CHASSIS", "GND", src="assumption: shield and jack chassis bleed to GND; review for EMC")
    s.C("1nF 2kV", "CHASSIS", fp="Capacitor_SMD:C_1206_3216Metric", src="assumption, same reason")
    s.flag("CHASSIS")

    s.group("Harness to the contact board - JST PH, 8 wires")
    s.part("J3", "Connector_Generic:Conn_01x08", "B8B-PH-K-S", {
        "1": "VIN", "2": "VIN", "3": "GND", "4": "ETH_TX_P", "5": "ETH_TX_N", "6": "GND", "7": "ETH_RX_P", "8": "ETH_RX_N",
    }, "Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical", src="jst_ePH.pdf p.1; same pin order as the contact board")
