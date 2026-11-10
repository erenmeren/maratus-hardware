"""Mechanical constants shared by tools/pcb.py and tools/enclosure.py. All values in mm.

PCB frame: origin at the board's top-left corner seen from the device REAR (= KiCad top view, all parts are on
that face), x to the right, y down. Panel data: docs/reference/NHD-4.0-480480AF-MSXP-CTP.pdf p.4.
"""
PANEL_W, PANEL_H, PANEL_T = 77.86, 81.84, 4.15   # LCM outline, total thickness with touch glass
PANEL_VA_W, PANEL_VA_H = 72.86, 71.18            # touch glass viewing area
PANEL_VA_LEFT, PANEL_VA_TOP = 2.50, 2.45         # viewing area offset from the outline, FRONT view
TAIL_LEN = 30.0                                  # both FFC tails, measured from the panel's bottom edge
LCD_TAIL_FRONT_X, LCD_TAIL_W = 32.68, 12.5       # left edge of the LCD tail in the FRONT view, tail width
TP_TAIL_FRONT_X, TP_TAIL_W = 10.75, 7.0          # left edge of the touch tail in the FRONT view, tail width

PCB_W, PCB_H, PCB_T = 76.0, 96.5, 1.2
PCB_R = 2.0                                      # outline corner radius
PANEL_X0 = (PCB_W - PANEL_W) / 2                 # panel left edge in the PCB frame (-0.93)
PANEL_Y0 = 8.0                                   # panel top edge: the first 8 mm of the PCB carry the antenna
PANEL_Y1 = PANEL_Y0 + PANEL_H                    # panel bottom edge (89.84)

# Tail centres in the PCB frame (rear view mirrors the front-view x).
LCD_TAIL_X = PANEL_X0 + PANEL_W - (LCD_TAIL_FRONT_X + LCD_TAIL_W / 2)   # 38.0
TP_TAIL_X = PANEL_X0 + PANEL_W - (TP_TAIL_FRONT_X + TP_TAIL_W / 2)      # 62.68
NOTCH_DEPTH = 2.5                                # the tails wrap around the bottom edge inside these notches
LCD_NOTCH = (LCD_TAIL_X - 7.0, LCD_TAIL_X + 7.0)
TP_NOTCH = (TP_TAIL_X - 4.3, TP_TAIL_X + 4.3)
FFC_MOUTH_Y = 76.0                               # connector openings; leaves about 1.5 mm of slack in a 30 mm tail

HOLES = [(3.6, 3.6), (PCB_W - 3.6, 3.6), (3.6, PCB_H - 3.6), (PCB_W - 3.6, PCB_H - 3.6)]   # M2 screws, 2.2 mm
HOLE_D = 2.2

# Cut-out in the top edge under the C5 module antenna (6.5 mm long): x0, x1, depth. Espressif ESP32-C5 hardware
# design guidelines, "Positioning a Module on a Base Board": antenna outside the base board, board cut away on
# both sides of it. The same page asks for 15 mm of clearance to metal; the LCD back is 1 mm away. RF is unproven.
ANTENNA_NOTCH = (25.0, 51.0, 7.0)

# Positions the enclosure needs (PCB frame). Kept in step with FIXED in tools/pcb.py.
USB_X = 17.0                                     # USB-C receptacle centre on the bottom edge
REAR_PADS = (59.0, 34.0)                         # centre of the 2 x 9 contact field P1
REAR_PADS_SIZE = (22.32, 5.5)                    # pad field extent (9 pads at 2.54 mm, rows 3.5 mm apart, 2 mm pads)
BUZZER = (51.5, 88.0)
SERVICE_SW = (71.0, 58.0)

# Stack (z from the front glass surface towards the rear).
GAP_PANEL_PCB = 0.6                              # foam between the panel's metal back and the PCB
PART_H = 4.0                                     # tallest part on the rear face (buzzer, cmt-8504-100-smt.pdf p.1)
