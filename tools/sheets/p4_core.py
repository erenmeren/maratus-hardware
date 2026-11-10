"""p4-core: ESP32-P4NRW32X, core DCDC, crystal, flash, decoupling, straps, test pads.

U1 pad nets come from hardware/inputs/maratus-core-gpio-map.csv (one exception: pad 51, see below).
Reference circuit: docs/reference/SCH_ESP32-P4X_FUNCTION_EV_BOARD_V1.7_20260203.pdf ("EV", pages 2-3),
esp-hardware-design-guidelines-en-master-esp32p4.pdf ("HDG"), esp32-p4_datasheet_en.pdf ("DS").
Page numbers are PDF page indexes. Deliberate differences from the EV board are marked "differs".
"""
import csv

from sch import ROOT, C0603, C0805

SPARE = ("TP_GPIO0", "TP_GPIO1", "TP_GPIO20", "TP_GPIO21", "TP_GPIO22", "TP_GPIO26", "TP_GPIO27", "TP_GPIO32",
         "TP_GPIO33", "TP_GPIO53", "TP_GPIO54")
FLASH = {"FLASH_CS": "1", "FLASH_Q": "2", "FLASH_WP": "3", "FLASH_D": "5", "FLASH_CK": "6", "FLASH_HOLD": "7"}


def build(s):
    with open(ROOT / "hardware" / "inputs" / "maratus-core-gpio-map.csv", newline="") as f:
        pads = {r[0]: r[2] for r in list(csv.reader(f))[1:]}
    pads["51"] = "3V3_USBPHY"  # VDD_USBPHY sits behind a 0R link from 3V3 (gpio map note, EV R233)

    s.group("U1 ESP32-P4NRW32X (chip revision v3.x) - pad nets from maratus-core-gpio-map.csv")
    s.part("U1", "PCM_Espressif:ESP32-P4X", "ESP32-P4NRW32X", pads, "PCM_Espressif:ESP32-P4",
           src="Espressif KiCad library symbol; pin map checked by tools/check_pinmap.py")

    s.group("Core DCDC U4 - 3V3 to VDD_HP, feedback trimmed by the chip through FB_DCDC")
    s.part("U4", "Regulator_Switching:TLV62569DBV", "TLV62569DBVR", {
        "VIN": "3V3", "EN": "EN_DCDC", "GND": "GND", "SW": "VDD_HP_SW", "FB": "FB_DCDC",
    }, "Package_TO_SOT_SMD:SOT-23-5", src="EV p.2 U7: 4 VIN, 1 EN = EN_DCDC, 3 SW, 5 FB = FB_DCDC")
    s.part("L201", "Device:L", "2.2uH WPN252010U2R2MT", {"1": "VDD_HP_SW", "2": "VDD_HP"},
           "Inductor_SMD:L_1008_2520Metric", src="EV p.2 L1 and EV BOM (Sunlord, 2520)")
    s.R("499k 1%", "VDD_HP", "FB_DCDC", src="EV p.2 R128: DCDC output to FB node")
    s.C("22pF", "VDD_HP", "FB_DCDC", src="EV p.2 C53: in parallel with R128")
    s.R("499k 1%", "FB_DCDC", "GND", src="EV p.2 R138: FB node to GND")
    s.C("4.7uF 6.3V", "3V3", fp=C0603, src="EV p.2 C54 at U7 VIN (EV 0R link R127 not fitted here: differs)")
    s.C("22uF 6.3V", "VDD_HP", fp=C0805, src="EV p.2 C61 at the DCDC output")
    s.flag("VDD_HP")
    s.tp("VDD_HP")

    s.group("Decoupling - one row per supply pad, values from EV p.2 unless noted")
    for net, caps, src in (
            ("3V3", ("10uF", "100nF"), "VDD_LP pad 9: EV C87, C83"),
            ("3V3", ("100nF",), "VDD_IO_0 pad 21: EV C88"),
            ("VDD_HP", ("10uF", "100nF"), "VDD_HP_0 pad 26: EV C107, C86"),
            ("VDD_FLASH", ("1uF", "100nF"), "VDD_FLASH_IO pad 30: EV C20, C25"),
            ("VDD_MIPI", ("10nF", "100nF", "1uF"), "VDD_MIPI_DPHY pad 41: EV C93, C92, C91"),
            ("3V3_USBPHY", ("10nF", "100nF", "4.7uF"), "VDD_USBPHY pad 51: EV C100, C99, C98, chip side of the link"),
            ("VDD_HP", ("100nF",), "VDD_HP_1 pad 54 (v3.x core supply): EV C118; EV 0R link R232 not fitted: differs"),
            ("VDD_PSRAM", ("1uF", "100nF"), "VDD_PSRAM_0 pad 59: EV C104, C105"),
            ("3V3", ("100nF",), "VDD_IO_4 pad 62: EV C97"),
            ("VDD_PSRAM", ("100nF",), "VDD_PSRAM_1 pad 67: gpio map; EV shares the pad 59 pair: differs"),
            ("VDD_FLASH", ("1uF",), "VDDO_FLASH pad 71: EV C56"),
            ("VDD_PSRAM", ("1uF",), "VDDO_PSRAM pad 72: EV C50"),
            ("VDD_MIPI", ("1uF",), "VDDO_3 pad 73: EV C55"),
            ("VDDO_4", ("1uF",), "VDDO_4 pad 74: EV C51. Unused LDO output"),
            ("3V3", ("100nF",), "VDD_LDO pad 75: EV C103"),
            ("VDD_HP", ("100nF",), "VDD_HP_2 pad 76: EV C89"),
            ("3V3", ("10uF", "100nF"), "VDD_DCDCC pad 77: EV C95, C96; HDG p.12: 10 uF for VDD_LDO and VDD_DCDCC"),
            ("3V3", ("100nF",), "VDD_IO_5 pad 85 (SDIO domain on 3V3; EV feeds it from VDDO_4: differs)"),
            ("VDD_HP", ("100nF",), "VDD_HP_3 pad 91: EV C94"),
            ("3V3", ("100nF",), "VDD_IO_6 pad 96: EV C90"),
            ("3V3", ("100nF",), "VDD_ANA pad 101: EV C85"),
            ("3V3", ("10uF", "100nF"), "VDD_BAT pad 102: EV C82, C84; must not float (design-spec 4)")):
        for i, value in enumerate(caps):
            big = value in ("10uF", "4.7uF")
            s.C(value + (" 6.3V" if big else ""), net, fp=C0603 if big else "Capacitor_SMD:C_0402_1005Metric",
                src=src if i == 0 else "")
    s.R("0R", "3V3", "3V3_USBPHY", src="EV p.2 R233; gpio map: 0R series link")
    s.flag("3V3_USBPHY")
    for net in ("VDD_FLASH", "VDD_PSRAM", "VDD_MIPI", "VDDO_4"):
        s.tp(net)

    s.group("40 MHz crystal - load capacitors to be tuned on the prototype")
    s.part("Y1", "Device:Crystal_GND24", "40MHz 10ppm CL15pF 3225", {"1": "XTAL_P_X", "3": "XTAL_N_X", "G": "GND"},
           "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", src="EV p.2 Y2 and EV BOM (40 MHz, 15 pF, 10 ppm); HDG p.15")
    s.R("0R", "XTAL_P", "XTAL_P_X", src="EV p.2 R67")
    s.R("0R", "XTAL_N", "XTAL_N_X", src="EV p.2 R70")
    s.C("22pF", "XTAL_P_X", src="EV p.2 C28")
    s.C("22pF", "XTAL_N_X", src="EV p.2 C45")

    s.group("SPI flash U3 - quad SPI on the dedicated FLASH_* pads, 0R series footprints")
    s.part("U3", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", {
        **{pin: net + "_F" for net, pin in FLASH.items()}, "8": "VDD_FLASH", "4": "GND",
    }, "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm",
        src="W25Q128JV_RevF p.75-76 (SOIC-8 208 mil, QE=1); HDG p.15 Table 3: CK-CLK, CS-CS#, D-DI, Q-DO, WP-WP#, "
            "HOLD-HOLD#. EV fits GD25Q128ESIG: differs")
    for net in FLASH:
        s.R("0R", net, net + "_F", src="HDG p.15: 0R series footprints; EV p.3")
    s.R("10k", "VDD_FLASH", "FLASH_CS_F", src="EV p.3 R18; HDG p.15: pull-up on FLASH_CS")
    s.C("100nF", "VDD_FLASH", src="EV p.3 C16; HDG p.15")

    s.group("Reset, strapping pins and factory test pads")
    s.R("10k", "3V3", "P4_EN", src="HDG p.14: R = 10k, C = 1 uF on CHIP_PU. EV fits 0.1 uF: differs")
    s.C("1uF", "P4_EN")
    s.tp("P4_EN")
    s.R("10k", "3V3", "RMII_TXD1", src="GPIO35 BOOT: HDG p.18 pull-up, no capacitor; EV p.3")
    s.tp("RMII_TXD1")
    s.R("10k", "3V3", "TP_GPIO36", src="GPIO36 floats by default and must be 1 for download boot: DS p.36-37 "
                                       "Tables 3-1, 3-3; EV p.3. The gpio map lists a test pad only: differs")
    s.tp("TP_GPIO36")
    for net in ("UART0_TXD", "UART0_RXD") + SPARE:
        s.tp(net)

    s.group("MIPI reference resistors and ADC input filters")
    s.R("4.02k 1%", "DSI_REXT", "GND", src="EV p.2; design-spec 4")
    s.R("4.02k 1%", "CSI_REXT", "GND", dnp=True, src="CSI unused in V1 (HDG p.23: may float). EV fits it: differs")
    for net in ("ACC_ID_ADC", "VSYS_SENSE", "USBC_CC1_SENSE", "USBC_CC2_SENSE"):
        s.C("100nF", net, src="design-spec 4: 0.1 uF at each ADC pin")
