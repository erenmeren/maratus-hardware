#!/usr/bin/env python3
"""Check the Maratus Core pin maps in hardware/inputs/ against reference data.

Reference data:
- tools/espressif_pins.json: pin numbers, names and alternates extracted from Espressif's
  official KiCad symbols (espressif/kicad-libraries, commit dd76561).
- Pin-mux options below: ESP-IDF master (commit 0e6b480f), emac_periph.c and sdmmc_pins.h,
  and the ESP32-P4 hardware design guidelines.

Run from the repo root:  python3 tools/check_pinmap.py
Exit code 0 = all checks pass, 1 = at least one failed.
"""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = json.loads((ROOT / "tools" / "espressif_pins.json").read_text())


def rows(name):
    with open(ROOT / "hardware" / "inputs" / name, newline="") as f:
        r = list(csv.reader(f))
    return r[1:]


P4 = [(int(r[0]), r[1], r[2], r[3]) for r in rows("maratus-core-gpio-map.csv")]
C5 = [(int(r[0]), r[1], r[2]) for r in rows("maratus-core-c5-pin-map.csv")]

checks, errors = [], []


def check(cond, msg):
    checks.append(msg)
    if not cond:
        errors.append(msg)


# 1. Pin numbers and names match Espressif's symbols
lib_p4 = {int(n): nm for n, nm, _, _ in LIB["ESP32-P4X"]}
check(len(P4) == len(lib_p4) == 105, "P4: all 105 pads (104 + EP) assigned")
check(all(lib_p4.get(p) == name for p, name, *_ in P4), "P4: every pin number/name matches symbol ESP32-P4X")
lib_c5 = {int(n): nm for n, nm, _, _ in LIB["ESP32-C5-WROOM-1"]}
check(len(C5) == len(lib_c5) == 29, "C5: all 29 module pads assigned")
check(all(lib_c5.get(p) == name for p, name, _ in C5), "C5: every pin number/name matches symbol ESP32-C5-WROOM-1")

net_of = {name.split("/")[0]: net for _, name, net, _ in P4}


def gp(n):
    return net_of["GPIO%d" % n]


# 2. Every GPIO on its own net
gpio_nets = [net for _, name, net, _ in P4 if name.startswith("GPIO")]
check(len(gpio_nets) == len(set(gpio_nets)) == 55, "P4: 55 GPIOs, each on its own net")

# 3. RMII signals on legal IO MUX pins
RMII = {
    "RMII_REF_CLK": [32, 44, 50], "RMII_TX_EN": [33, 40, 49], "RMII_TXD0": [34, 41],
    "RMII_TXD1": [35, 42], "RMII_CRS_DV": [28, 45, 51], "RMII_RXD0": [29, 46, 52],
    "RMII_RXD1": [30, 47, 53],
}
for sig, opts in RMII.items():
    used = [g for g in opts if gp(g) == sig]
    check(len(used) == 1, f"RMII: {sig} on a valid IO MUX pin {opts}")
check(gp(23) == "ETH_REFCLK_ALT", "RMII: GPIO23 kept as REF_50M_CLK output option")

# 4. SDIO on SDMMC slot 0 IO MUX pins, and on the C5's fixed slave pins
SLOT0 = {"SDIO_CLK": 43, "SDIO_CMD": 44, "SDIO_D0": 39, "SDIO_D1": 40, "SDIO_D2": 41, "SDIO_D3": 42}
check(all(gp(g) == s for s, g in SLOT0.items()), "SDIO: P4 side on SDMMC slot 0 pins GPIO39-44")
C5_SDIO = {"SDIO_CLK": "GPIO9", "SDIO_CMD": "GPIO10", "SDIO_D0": "GPIO8",
           "SDIO_D1": "GPIO7", "SDIO_D2": "GPIO14", "SDIO_D3": "GPIO13"}
c5net = {}
for _, name, net in C5:
    for part in name.split("/"):
        c5net[part] = net
check(all(c5net.get(g) == s for s, g in C5_SDIO.items()), "SDIO: C5 side on its fixed SDIO slave pins")
alts = {nm: a for _, nm, _, a in LIB["ESP32-C5-WROOM-1"]}
check("SDIO_CLK" in alts["GPIO9"] and "SDIO_CMD" in alts["GPIO10"] and "SDIO_DATA0" in alts["GPIO8"]
      and "SDIO_DATA1" in alts["GPIO7"] and "SDIO_DATA2" in alts["GPIO14/USB_D+"]
      and "SDIO_DATA3" in alts["GPIO13/USB_D-"], "SDIO: C5 pin functions confirmed by symbol alternates")
c5_nets = [net for _, _, net in C5]
for n in list(SLOT0) + ["C5_EN", "C5_BOOT", "C5_U0RXD", "C5_U0TXD"]:
    check(n in gpio_nets and n in c5_nets, f"Link: {n} present on both P4 and C5")

# 5. USB
check(gp(24) == "USBC_DN" and gp(25) == "USBC_DP", "USB-C: D-/D+ on GPIO24/25 (USB-Serial-JTAG)")
check(net_of["USB-DM"] == "ACC_USB_DN" and net_of["USB-DP"] == "ACC_USB_DP", "Accessory USB on the HS PHY pins")

# 6. Strapping pins
check(gp(35) == "RMII_TXD1", "Strap: GPIO35 (BOOT) only drives a PHY input")
check(gp(37) == "UART0_TXD" and gp(38) == "UART0_RXD", "Strap/UART0: GPIO37/38 on test pads only")
check(gp(36).startswith("TP_"), "Strap: GPIO36 has no load")

# 7. Analog nets on ADC1 pins (GPIO16-23)
for n in ["ACC_ID_ADC", "VSYS_SENSE", "USBC_CC1_SENSE", "USBC_CC2_SENSE"]:
    g = [int(k[4:]) for k, v in net_of.items() if v == n and k.startswith("GPIO")]
    check(len(g) == 1 and 16 <= g[0] <= 23, f"ADC: {n} on an ADC1 pin")

# 8. Supply pins on the intended rails
RAIL = {
    "VDD_HP_0": "VDD_HP", "VDD_HP_1": "VDD_HP", "VDD_HP_2": "VDD_HP", "VDD_HP_3": "VDD_HP",
    "VDD_LP": "3V3", "VDD_IO_0": "3V3", "VDD_IO_4": "3V3", "VDD_IO_5": "3V3", "VDD_IO_6": "3V3",
    "VDD_LDO": "3V3", "VDD_DCDCC": "3V3", "VDD_ANA": "3V3", "VDD_BAT": "3V3", "VDD_USBPHY": "3V3",
    "VDD_FLASH_IO": "VDD_FLASH", "VDDO_FLASH": "VDD_FLASH", "VDD_PSRAM_0": "VDD_PSRAM",
    "VDD_PSRAM_1": "VDD_PSRAM", "VDDO_PSRAM": "VDD_PSRAM", "VDD_MIPI_DPHY": "VDD_MIPI", "VDDO_3": "VDD_MIPI",
}
check(all(net_of.get(p) == r for p, r in RAIL.items()), "Power: all 21 supply pins on the intended rail")

print(f"{len(checks)} checks, {len(errors)} failed")
for c in checks:
    print(("  FAIL " if c in errors else "  ok   ") + c)
sys.exit(1 if errors else 0)
