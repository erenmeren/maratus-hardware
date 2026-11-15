"""dock-contact: the Dock's contact board. Spring pins onto the Core's rear pads, ID resistor, harness to the base board.

Sources: docs/design-spec.md section 7 (pad table, ID resistor 1.0 k for the Dock),
docs/reference/harwin_P70-2300045R.pdf (spring pin: 2 A, 30 mOhm, 0.83 N at 4.9 mm, 10,000 cycles),
docs/reference/jst_ePH.pdf p.1 (PH series: 2 A per contact with AWG 24, 100 V).
Only the 12 pads the Dock uses get a pin: USB, the accessory IO lines and V_ACC stay open. Fewer pins also means
less force pushing the Core off (12 x 0.83 N).
"""
PADS = {"a1": "GND", "a2": "ETH_TX_P", "a3": "ETH_TX_N", "a4": "GND", "a5": "ETH_RX_P", "a6": "ETH_RX_N", "a7": "GND",
        "b1": "VIN", "b2": "VIN", "b3": "GND", "b4": "ACC_ID", "b8": "GND"}
PIN_FP = "maratus:SpringPin_Harwin_P70-2300045R"


def build(s):
    s.group("Spring pins - one per used rear pad of the Core; the value is the pad name (design-spec section 7)")
    for pad, net in PADS.items():
        ref = f"P{pad[0].upper()}{pad[1]}"      # PA1 ... PB8: tools/dock_pcb.py places each on its pad position
        s.part(ref, "Connector:TestPoint", pad, {"1": net}, PIN_FP,
               src="design-spec 7 pad table; harwin_P70-2300045R.pdf pad layout" if pad == "a1" else "")
    s.flag("GND")
    s.flag("VIN")

    s.group("Accessory ID - 1.0 k to GND tells the Core that a Dock is attached (0.30 V on ACC_ID)")
    s.R("1.0k 1%", "ACC_ID", "GND", src="design-spec 7 accessory table")

    s.group("Harness to the base board - JST PH, 8 wires; twist each Ethernet pair")
    s.part("J1", "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "B8B-PH-SM4-TB", {
        "1": "VIN", "2": "VIN", "3": "GND", "4": "ETH_TX_P", "5": "ETH_TX_N", "6": "GND", "7": "ETH_RX_P", "8": "ETH_RX_N",
        "MP": "GND",
    }, "Connector_JST:JST_PH_B8B-PH-SM4-TB_1x08-1MP_P2.00mm_Vertical",
        src="jst_ePH.pdf p.4 (SMT header: the board's front lies on the Dock's plastic, so no pins may come through); "
            "p.1: 2 A per contact. Two contacts for VIN: the Core can draw 1.2 A")
