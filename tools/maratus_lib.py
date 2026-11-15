"""Project symbols drawn from datasheets -> hardware/lib/maratus/maratus.kicad_sym.

One entry per part that has no symbol in KiCad's or Espressif's library. Every entry names the
datasheet file in docs/reference/ and the page the pin numbers were read from (CLAUDE.md rule 8).
Pin tuples: (number, name, electrical type). Written by `python3 tools/sch.py gen`.
The same run writes hardware/lib/maratus/maratus.pretty (footprints that are PCB features, not parts).
"""
import os
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parent.parent / "hardware" / "lib" / "maratus" / "maratus.kicad_sym"

SYMBOLS = {
    "TPS2121RUX": dict(
        description="2.8-22 V priority power mux, seamless switchover, VQFN-HR-12 (RUX)",
        footprint="Package_DFN_QFN:Texas_VQFN-HR-12_2x2.5mm_P0.5mm",
        datasheet="https://www.ti.com/lit/ds/symlink/tps2121.pdf",
        source="docs/reference/tps2121.pdf p.4-5 (Pin Functions, TPS2121 VQFN-HR column)",
        left=[("7", "IN1", "power_in"), ("6", "PR1", "input"), ("5", "OV1", "input"),
              ("2", "IN2", "power_in"), ("3", "CP2", "input"), ("4", "OV2", "input")],
        # two OUT pads: only one is power_out, or ERC reports two outputs on one net
        right=[("1", "OUT", "power_out"), ("8", "OUT", "passive"), ("9", "ST", "open_collector"),
               ("10", "ILM", "passive"), ("11", "SS", "passive")],
        bottom=[("12", "GND", "power_in")],
    ),
    "TPS2553DBV": dict(
        description="Adjustable current-limited power switch, active-high enable, auto retry, SOT-23-6",
        footprint="Package_TO_SOT_SMD:SOT-23-6",
        datasheet="https://www.ti.com/lit/ds/symlink/tps2553.pdf",
        source="docs/reference/tps2553.pdf p.4 (Figure 5-1 DBV, Table 5-1 TPS2553 SOT-23 column)",
        left=[("1", "IN", "power_in"), ("3", "EN", "input")],
        right=[("6", "OUT", "power_out"), ("4", "~{FAULT}", "open_collector"), ("5", "ILIM", "passive")],
        bottom=[("2", "GND", "power_in")],
    ),
    "IP101GRI": dict(
        description="10/100 Ethernet PHY, MII/RMII, QFN-32 4x4 mm, -40 to 85 C. Ground is the exposed pad only.",
        footprint="Package_DFN_QFN:QFN-32-1EP_4x4mm_P0.4mm_EP2.65x2.65mm",
        datasheet="IP101G-DS-R01 (IC Plus)",
        source="docs/reference/IP101G_preliminary_datasheet_lcsc.pdf p.10 (Figure 3 pin diagram), p.16-18 (pin "
               "description), p.64 (package: 4x4 mm, 0.4 mm pitch, exposed pad 2.60-2.75 mm)",
        left=[("32", "RESET_N", "input"), ("22", "MDC", "input"), ("23", "MDIO", "bidirectional"),
              ("5", "TXEN", "input"), ("9", "TXD0", "input"), ("8", "TXD1", "input"), ("7", "TXD2", "input"),
              ("6", "TXD3", "input"), ("1", "TXER/FXSD", "input"), ("10", "TXCLK/50M_CLKI", "bidirectional"),
              ("14", "RXCLK/50M_CLKO", "output"), ("19", "RXDV/CRS_DV/FX_HEN", "bidirectional"),
              ("18", "RXD0", "output"), ("17", "RXD1", "output"), ("16", "RXD2", "output"), ("15", "RXD3", "output"),
              ("21", "RXER/INTR_32", "bidirectional"), ("20", "CRS/LEDMOD", "bidirectional"),
              ("4", "COL/RMII", "bidirectional")],
        right=[("30", "MDI_TP", "bidirectional"), ("29", "MDI_TN", "bidirectional"), ("27", "MDI_RP", "bidirectional"),
               ("26", "MDI_RN", "bidirectional"), ("2", "X1", "input"), ("3", "X2", "output"),
               ("25", "ISET", "passive"), ("28", "REGOUT", "power_out"), ("11", "LED0/PHY_AD0", "bidirectional"),
               ("12", "LED3/PHY_AD3", "bidirectional"), ("24", "TEST_ON", "input")],
        top=[("31", "AVDD33", "power_in"), ("13", "VDDIO", "power_in")],
        bottom=[("33", "GND", "power_in")],
    ),
    "TPS61169DCK": dict(
        description="38 V boost WLED driver, 204 mV feedback, PWM dimming on CTRL, SC-70-5 (DCK)",
        footprint="Package_TO_SOT_SMD:SOT-353_SC-70-5",
        datasheet="https://www.ti.com/lit/ds/symlink/tps61169.pdf",
        source="docs/reference/tps61169.pdf p.3 (pin configuration and functions, DCK package)",
        left=[("5", "VIN", "power_in"), ("4", "CTRL", "input")],
        right=[("1", "SW", "passive"), ("3", "FB", "input")],
        bottom=[("2", "GND", "power_in")],
    ),
}

FONT = "(effects (font (size 1.27 1.27))%s)"


def symbol(name, description, footprint, datasheet, source, left=(), right=(), bottom=(), top=()):
    rows = max(len(left), len(right))
    longest = lambda col: max([len(p[1]) for p in col] + [2])
    hw = max(7.62, 2.54 * (max(len(top), len(bottom)) // 2 + 1), 0.55 * (longest(left) + longest(right)) + 2.54)
    hw = 2.54 * round(hw / 2.54 + 0.49)
    hh = 2.54 * (rows // 2 + 1)
    pins = ""

    def pin(p, x, y, ang):
        return (f'(pin {p[2]} line (at {x:g} {y:g} {ang}) (length 2.54) '
                f'(name "{p[1]}" {FONT % ""}) (number "{p[0]}" {FONT % ""}))\n')
    for col, x, ang in ((left, -hw - 2.54, 0), (right, hw + 2.54, 180)):
        for i, p in enumerate(col):
            pins += pin(p, x, hh - 2.54 * (i + 1), ang)
    for col, y, ang in ((bottom, -hh - 2.54, 90), (top, hh + 2.54, 270)):
        for i, p in enumerate(col):
            pins += pin(p, 2.54 * (i - (len(col) - 1) // 2), y, ang)
    hide = " (hide yes)"
    return f"""(symbol "{name}" (exclude_from_sim no) (in_bom yes) (on_board yes)
(property "Reference" "U" (at {-hw:g} {hh + 3.81:g} 0) {FONT % " (justify left)"})
(property "Value" "{name}" (at {-hw:g} {hh + 1.27:g} 0) {FONT % " (justify left)"})
(property "Footprint" "{footprint}" (at 0 0 0) {FONT % hide})
(property "Datasheet" "{datasheet}" (at 0 0 0) {FONT % hide})
(property "Description" "{description}" (at 0 0 0) {FONT % hide})
(property "Source" "{source}" (at 0 0 0) {FONT % hide})
(symbol "{name}_0_1" (rectangle (start {-hw:g} {hh:g}) (end {hw:g} {-hh:g}) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "{name}_1_1"
{pins}))
"""


def write():
    text = ('(kicad_symbol_lib (version 20241209) (generator "maratus_tools") (generator_version "9.0")\n'
            + "".join(symbol(n, **d) for n, d in SYMBOLS.items()) + ")\n")
    tmp = OUT.with_suffix(".tmp.kicad_sym")
    tmp.write_text(text)
    subprocess.run(["kicad-cli", "sym", "upgrade", "--force", str(tmp)], check=True, stdout=subprocess.DEVNULL)
    os.replace(tmp, OUT)  # atomic: a parallel reader never sees a half-written library
    PRETTY.mkdir(exist_ok=True)
    (PRETTY / f"{REAR_PADS}.kicad_mod").write_text(rear_pads())
    (PRETTY / f"{SPRING_PIN}.kicad_mod").write_text(spring_pin())
    subprocess.run(["kicad-cli", "fp", "upgrade", "--force", str(PRETTY)], check=True, stdout=subprocess.DEVNULL)


PRETTY = OUT.with_name("maratus.pretty")
REAR_PADS = "RearPads_2x9_P2.54mm_D2.0mm"


def rear_pads():
    """P1 contact field, docs/design-spec.md section 7: 2 rows of 9 round pads, 2.54 mm pitch, rows 3.5 mm apart.
    The 2.0 mm pad diameter is an assumption (0.54 mm gap); confirm it against the Dock's spring pins."""
    text = lambda prop, value, y, layer: (
        f'\t(property "{prop}" "{value}" (at 0 {y:g} 0) (layer "{layer}") '
        f'(effects (font (size 1 1) (thickness 0.15))))\n')
    pads = "".join(
        f'\t(pad "{row}{i + 1}" smd circle (at {2.54 * (i - 4):g} {y:g}) (size 2 2) (layers "F.Cu" "F.Mask"))\n'
        for row, y in (("a", -1.75), ("b", 1.75)) for i in range(9))
    assert pads.count("(pad ") == 18
    return (f'(footprint "{REAR_PADS}" (version 20241229) (generator "maratus_tools") (layer "F.Cu")\n'
            '\t(descr "Maratus Core rear contact field P1: 2 x 9 round pads, 2.54 mm pitch, rows 3.5 mm apart, '
            'pad 2.0 mm (assumed). design-spec section 7")\n'
            + text("Reference", "REF**", -4.2, "F.SilkS") + text("Value", REAR_PADS, 4.2, "F.Fab")
            + '\t(attr smd exclude_from_pos_files exclude_from_bom)\n'
            '\t(fp_rect (start -11.41 -3) (end 11.41 3) (stroke (width 0.05) (type solid)) (fill no) '
            '(layer "F.CrtYd"))\n' + pads + ")\n")


SPRING_PIN = "SpringPin_Harwin_P70-2300045R"


def spring_pin():
    """Harwin P70-2300045R, docs/reference/harwin_P70-2300045R.pdf (recommended PCB pad layout): 0.85 mm through
    hole for the 0.7 mm peg, 1.8 mm solder pad. Body 1.5 mm, 6.2 mm free height."""
    text = lambda prop, value, y, layer: (
        f'\t(property "{prop}" "{value}" (at 0 {y:g} 0) (layer "{layer}") '
        f'(effects (font (size 0.6 0.6) (thickness 0.1))))\n')
    return (f'(footprint "{SPRING_PIN}" (version 20241229) (generator "maratus_tools") (layer "F.Cu")\n'
            '\t(descr "Harwin P70-2300045R spring-loaded contact with peg, 6.2 mm free height, 4.9 mm working height. '
            'Pad layout from the customer information sheet")\n'
            + text("Reference", "REF**", -1.8, "F.Fab") + text("Value", SPRING_PIN, 1.8, "F.Fab")
            + '\t(attr through_hole)\n'
            '\t(fp_circle (center 0 0) (end 1.15 0) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))\n'
            '\t(fp_circle (center 0 0) (end 0.75 0) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))\n'
            '\t(pad "1" thru_hole circle (at 0 0) (size 1.8 1.8) (drill 0.85) (layers "*.Cu" "*.Mask"))\n)\n')
