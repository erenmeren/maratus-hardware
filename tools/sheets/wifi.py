"""wifi: ESP32-C5-WROOM-1-N4 as ESP-Hosted SDIO slave, SDIO pull-ups, C5 control and recovery lines.

Sources (docs/reference/): esp32-c5-wroom-1_wroom-1u_datasheet_en.pdf p.16-19 (straps, boot mode),
ESP32_P4X_C5_Function_EV_board-2.0-schematics.pdf p.5 (Espressif P4X + C5 reference: 10 uF + 0.1 uF,
EN 10k + 1 uF, 51k on CMD and D0-D3, GPIO25 left open), design-spec.md section 5.
Module pad nets come from hardware/inputs/maratus-core-c5-pin-map.csv.
"""
import csv

from sch import ROOT, C0805

SDIO = ("SDIO_CLK", "SDIO_CMD", "SDIO_D0", "SDIO_D1", "SDIO_D2", "SDIO_D3")


def build(s):
    with open(ROOT / "hardware" / "inputs" / "maratus-core-c5-pin-map.csv", newline="") as f:
        # the six SDIO pads sit behind a series resistor, so their pad-side net is NAME_C5
        pads = {r[0]: r[2] + "_C5" if r[2] in SDIO else r[2] for r in list(csv.reader(f))[1:]}

    s.group("U2 ESP32-C5-WROOM-1-N4 - pad nets from maratus-core-c5-pin-map.csv")
    s.part("U2", "PCM_Espressif:ESP32-C5-WROOM-1", "ESP32-C5-WROOM-1-N4", pads, "PCM_Espressif:ESP32-C5-WROOM-1",
           src="Espressif KiCad library symbol; pin map checked by tools/check_pinmap.py")
    s.C("10uF 10V", "3V3", fp=C0805, src="P4X-C5 EV board p.5 C1; design-spec 5")
    s.C("100nF", "3V3", src="P4X-C5 EV board p.5 C2")
    s.R("10k", "3V3", "C5_EN", src="P4X-C5 EV board p.5 R4")
    s.C("1uF", "C5_EN", src="P4X-C5 EV board p.5 C8")

    s.group("SDIO - series footprints (0R, tune on the prototype), 51k pull-ups at the module, DNP cap on CLK")
    for net in SDIO:
        s.R("0R", net, net + "_C5", src="design-spec 5: series resistor footprint on all six lines")
    for net in SDIO[1:]:
        s.R("51k 1%", "3V3", net + "_C5", src="P4X-C5 EV board p.5 R1/R3/R5/R6/R11; no pull-up on CLK")
    s.C("TBD", "SDIO_CLK_C5", dnp=True, src="design-spec 5: DNP capacitor footprint on CLK, value from measurement")

    s.group("Strap footprints (all DNP: GPIO25 and MTDI float, as on the Espressif board) and test pads")
    for net in ("C5_STRAP_GPIO25", "C5_STRAP_MTDI"):
        s.R("10k", "3V3", net, dnp=True, src="C5 datasheet p.18 Table 4-4: SDIO sampling/driving edge")
        s.R("10k", net, "GND", dnp=True)
    for net in ("C5_EN", "C5_BOOT", "C5_U0RXD", "C5_U0TXD", "C5_STRAP_GPIO27", "C5_STRAP_GPIO26", "C5_TP_GPIO2"):
        s.tp(net)
