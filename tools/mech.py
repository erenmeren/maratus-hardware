"""Mechanical constants shared by tools/pcb.py and tools/enclosure.py. All values in mm.

Slim layout (2026-11-10): the touch glass reaches the edge of the housing on all four sides, the PCB sits
entirely behind the panel with its parts facing the display, the display is the lid of a one-piece body.
PCB frame: origin at the board's top-left corner seen from the device FRONT (= KiCad top view, the part side),
x to the right, y down. Panel data: docs/reference/NHD-4.0-480480AF-MSXP-CTP.pdf p.4.
"""
PANEL_W, PANEL_H, PANEL_T = 77.86, 81.84, 4.15   # LCM outline, total thickness with touch glass
PANEL_GLASS_T = 1.4                              # touch glass; the FFC tails leave from the 2.75 mm behind it
PANEL_AA = (3.00, 2.95, 71.86, 70.18)            # lit area in the front view: left, top, width, height; 8.71 below it
TAIL_LEN = 30.0                                  # both FFC tails, measured from the panel's bottom edge
LCD_TAIL_FRONT_X, LCD_TAIL_W = 32.68, 12.5       # left edge of the LCD tail in the front view, tail width
TP_TAIL_FRONT_X, TP_TAIL_W = 10.75, 7.0          # left edge of the touch tail in the front view, tail width

PCB_W, PCB_H, PCB_T = 74.0, 72.0, 1.2
PCB_R = 2.0                                      # outline corner radius
PANEL_X0 = (PCB_W - PANEL_W) / 2                 # panel left edge in the PCB frame (-1.93)
PANEL_Y0 = -9.5                                  # panel top edge: the strip above the PCB is for the antenna
PANEL_Y1 = PANEL_Y0 + PANEL_H                    # panel bottom edge (72.34)

LCD_TAIL_X = PANEL_X0 + LCD_TAIL_FRONT_X + LCD_TAIL_W / 2    # tail centres in the PCB frame: 37.0
TP_TAIL_X = PANEL_X0 + TP_TAIL_FRONT_X + TP_TAIL_W / 2       # 12.32
# Connector openings. A tail turns around the panel's bottom edge (about 4.5 mm) and goes 3.5 mm into the
# connector, which leaves 22 mm; 1.7 mm of that is slack.
FFC_MOUTH_Y = PANEL_Y1 - 22.0 + 1.7              # 52.04

HOLES = [(3.5, 3.5), (PCB_W - 3.5, 3.5), (3.5, PCB_H - 3.5), (PCB_W - 3.5, PCB_H - 3.5)]   # M2 screws, 2.2 mm
HOLE_D = 2.2

# Positions the enclosure needs (PCB frame). Kept in step with FIXED in tools/pcb.py.
USB_X = 57.0                                     # USB-C receptacle centre on the bottom edge
USB_TAB = (12.0, 1.2)                            # the board's tab under the receptacle: width, length beyond the bottom
                                                 # edge. It brings the receptacle's mouth to 1.39 mm behind the body's
                                                 # outer face (GCT_USB4105_drawing.pdf p.1: a plug mates up to 1.85 mm)
REAR_PADS = (LCD_TAIL_X, 66.0)                   # contact part P1 on the BACK of the board, long axis horizontal
# P1 since 2026-11-19 (owner): Promax NF9642-20PA, docs/reference/promax_NF9642-20PA.pdf p.1 (housing height from
# promax_NF6268-20PA.pdf p.1, the same part with wire tails). Its housing stands
# 3.50 mm on the board's back and goes through the floor: contact faces 0.10 mm behind the rear face (2.0 + 1.6).
REAR_PADS_SIZE = (29.1, 4.5)                     # its pins' copper on the board: 2 x 10 at 3.00 mm, rows 2.40 mm, 2.1 mm pads
CONTACT_BASE = (50.4, 7.4, 2.5)                  # housing on the board: length, width (round ends), height
CONTACT_BOSS = (38.0, 5.5, 1.0)                  # its raised part with the contacts, through the floor
BUZZER_X = 23.5                                  # centre of the row of three sound slots in the bottom wall
SERVICE_SW = (BUZZER_X - 4.8, 69.5)              # part side, side-actuated, plunger 0.5 mm inside the bottom edge:
                                                 # its slot is the fourth in the row of the buzzer's three (2.4 mm pitch)
BUZZER = (BUZZER_X + 2.3, 58.5)                  # part side. Until 2026-11-19 at (23.5, 62): P1's left pins come
                                                 # through the board there; 2.3 mm right of the slots to clear J4
ANTENNA = (PCB_W / 2, PANEL_Y0 + 4.6, 42.0, 7.0)  # centre x, centre y, length, width of the flex antenna on the floor
# The lock point: one M4 thin nut in the floor, on the centre line above the pad window (owner, 2026-11-14: one
# metal point, not screw holes; the Dock hides what goes into it, and other makers' stands can use the same
# thread). Nothing is on the back of the board there. Before: four, then two bosses for M2 screws.
DOCK_LOCK = [(REAR_PADS[0], 55.0)]
LOCK_NUT = (7.0, 2.2)                            # M4 thin nut, ISO 4035: across flats, height
# Magnets that hold the Core on a Dock (2026-11-12): one disc under a thin skin of the floor at each place, a stack
# of two in the Dock's front opposite it. Owner, 2026-11-15: one pair, level with the contact field and the same
# distance either side of it, as near to it as it goes. The left one cannot go nearer: the buzzer is a magnetic one
# and stands above the board there (the magnet's edge is 0.75 mm outside the buzzer's outline, its centre 10.8 mm
# from the buzzer's): test the buzzer with the magnets fitted. The right one lies under the USB-C receptacle.
# Before: four, an outer pair for BAR and an inner pair for FLOAT, 9.5 and 18.6 mm above the field.
# Since 2026-11-19 (owner: the magnets may move) 10.5 mm higher: P1's housing, 50.4 mm long, reaches under both old
# places, and beside it the screw bosses are in the way. The left one is again 0.75 mm outside the buzzer's outline.
MAGNET_D, MAGNET_T = 10.0, 2.0                   # N42 disc, magnetised through its thickness
DOCK_MAGNETS = [(REAR_PADS[0] - 23.5, REAR_PADS[1] - 10.5), (REAR_PADS[0] + 23.5, REAR_PADS[1] - 10.5)]  # (13.5, 55.5), (60.5, 55.5)

# Stack. Z = 0 on the PCB's part side, +Z towards the display.
STANDOFF = 2.0                                   # PCB back to the floor: screw bosses (until 2026-11-14 also the B3U-1000P, 1.6 mm)
PART_H = 4.0                                     # tallest part (buzzer, cmt-8504-100-smt.pdf p.1)
GAP_PARTS_PANEL = 0.5
