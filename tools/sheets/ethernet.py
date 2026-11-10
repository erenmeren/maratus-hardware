"""ethernet: IP101GRI PHY in RMII mode, 25 MHz crystal, PHY drives the 50 MHz reference, MDI ESD array.

Reference circuit: SCH_ESP32-P4X_FUNCTION_EV_BOARD_V1.7_20260203.pdf p.5 ("EV"). Datasheet:
IP101G_preliminary_datasheet_lcsc.pdf ("DS", a 2012 preliminary copy). Waveshare schematic p.1 ("WS").
Differences from EV: no RJ45, transformer or LEDs on the Core. The four MDI lines leave through the
rear pads; the accessory holds the transformer and its centre-tap capacitors (DS p.7 and p.55: centre
taps to decoupling capacitors, not to any supply). PHY address 1.
"""
from sch import NC, C0603

UP = ("PHY_COL", "PHY_CRS", "PHY_RXER", "PHY_AD0")


def build(s):
    s.group("U7 IP101GRI - RMII, PHY address 1, held in reset by default")
    s.part("U7", "maratus:IP101GRI", "IP101GRI", {
        "RESET_N": "ETH_PHY_RST_N", "MDC": "ETH_MDC", "MDIO": "ETH_MDIO",
        "TXEN": "RMII_TX_EN", "TXD0": "RMII_TXD0", "TXD1": "RMII_TXD1", "TXD2": NC, "TXD3": NC,
        "TXER/FXSD": "PHY_TXER", "TXCLK/50M_CLKI": "PHY_CLKI", "RXCLK/50M_CLKO": "PHY_CLKO",
        "RXDV/CRS_DV/FX_HEN": "PHY_CRS_DV", "RXD0": "PHY_RXD0", "RXD1": "PHY_RXD1", "RXD2": NC, "RXD3": NC,
        "RXER/INTR_32": "PHY_RXER", "CRS/LEDMOD": "PHY_CRS", "COL/RMII": "PHY_COL",
        "MDI_TP": "ETH_TX_P", "MDI_TN": "ETH_TX_N", "MDI_RP": "ETH_RX_P", "MDI_RN": "ETH_RX_N",
        "X1": "PHY_X1", "X2": "PHY_X2", "ISET": "PHY_ISET", "REGOUT": "PHY_REGOUT",
        "LED0/PHY_AD0": "PHY_AD0", "LED3/PHY_AD3": "PHY_AD3", "TEST_ON": NC,
        "AVDD33": "PHY_3V3", "VDDIO": "PHY_3V3", "GND": "GND",
    }, "Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm",
        src="DS p.10 pin diagram, p.16-18 pin table; EV p.5 U8. Pins 6, 7, 15, 16, 24 open as on EV")

    s.group("Supply - 0R link, decoupling, internal regulator output, bias resistor")
    s.R("0R", "3V3", "PHY_3V3", src="EV p.5 R213")
    for value in ("100nF", "10uF 6.3V", "100nF", "10uF 6.3V"):
        s.C(value, "PHY_3V3", fp=C0603 if value.startswith("10uF") else "Capacitor_SMD:C_0402_1005Metric",
            src="EV p.5 C112, C114, C109, C108")
    s.flag("PHY_3V3")
    s.C("10uF 6.3V", "PHY_REGOUT", fp=C0603, src="EV p.5 C113; DS p.7: REGOUT is for internal use only")
    s.C("100nF", "PHY_REGOUT", src="EV p.5 C111")
    s.R("6.19k 1%", "PHY_ISET", "GND", src="EV p.5 R165; DS p.18")

    s.group("25 MHz crystal - load capacitance of the crystal not chosen, capacitors as on EV")
    s.part("Y2", "Device:Crystal_GND24", "25MHz 10ppm 3225 (CL TBD)", {"1": "PHY_XI", "3": "PHY_XO", "G": "GND"},
           "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", src="EV p.5 Y3; DS p.57 Table 13: 25 MHz, 50 ppm, 20 pF")
    s.R("0R", "PHY_X1", "PHY_XI", src="EV p.5 R161")
    s.R("0R", "PHY_X2", "PHY_XO", src="EV p.5 R158")
    s.C("20pF", "PHY_XI", src="EV p.5 C68")
    s.C("20pF", "PHY_XO", src="EV p.5 C64")
    s.R("10M", "PHY_XI", "PHY_XO", dnp=True, src="EV p.5 R159, not fitted there either")

    s.group("50 MHz reference - PHY output to the P4 and back into the PHY; DNP link for a P4-driven clock")
    s.R("0R", "PHY_CLKO", "RMII_REF_CLK", src="EV p.5 R139: series resistor at the source (HDG p.23)")
    s.R("0R", "RMII_REF_CLK", "PHY_CLKI", src="EV p.5 R142; DS p.16: pin 10 needs 50 MHz in RMII mode")
    s.R("0R", "ETH_REFCLK_ALT", "RMII_REF_CLK", dnp=True,
        src="design-spec 6: GPIO23 option if the crystal is dropped (then remove the PHY_CLKO link)")

    s.group("RMII and SMI - 0R at the PHY outputs, MDIO pull-up, reset pull-down")
    for net in ("RXD0", "RXD1", "CRS_DV"):
        s.R("0R", "PHY_" + net, "RMII_" + net, src="EV p.5 R144, R143, R150")
    s.R("1.5k", "PHY_3V3", "ETH_MDIO", src="EV p.5 R163; design-spec 6")
    s.R("10k", "ETH_PHY_RST_N", "GND", src="assumption: keeps the PHY in reset until firmware releases it "
                                           "(design-spec 6). EV drives RESET_N directly, no pull: differs")

    s.group("Strap resistors - sampled at reset release (DS p.47, p.57: 5.1k)")
    for net, src in zip(UP, ("EV p.5 R149: COL/RMII = 1 selects RMII", "EV p.5 R155: CRS/LEDMOD = 1",
                             "EV p.5 R157: RXER/INTR_32 pull-up", "EV p.5 R141: PHY_AD0 = 1")):
        s.R("5.1k", "PHY_3V3", net, src=src)
    s.R("5.1k", "PHY_TXER", "GND", src="EV p.5 R169; DS p.16: TXER floats or goes to GND in RMII mode")
    s.R("5.1k", "PHY_AD3", "GND", src="EV p.5 R140: PHY_AD3 = 0, so the PHY address is 1")

    s.group("MDI ESD array - before the rear pads; no termination parts (49.9 ohm is inside the PHY, DS p.1)")
    s.part("D501", "Power_Protection:TPD4E05U06DQA", "TPD4E05U06DQA", {
        "D1+": "ETH_TX_P", "D1-": "ETH_TX_N", "D2+": "ETH_RX_P", "D2-": "ETH_RX_N", "GND": "GND", "NC": NC,
    }, "Package_SON:USON-10_2.5x1.0mm_P0.5mm",
        src="tpd4e05u06.pdf p.4 Table 4-2 pins, p.7 stand-off 5.5 V, p.1 0.42-0.5 pF. WS p.1 uses RClamp0524PATCT in "
            "this position")
