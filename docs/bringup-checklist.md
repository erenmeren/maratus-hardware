# Maratus Core — prototype bring-up checklist

Status of every line today: **untested**. No hardware exists yet. Work top to bottom; do not move on while a line fails.

## 0. Before power
- [ ] Visual inspection: P4 QFN and C5 module orientation, no bridges on the P4 exposed-pad vias, FPC connectors latched.
- [ ] Resistance to ground on 5V_SYS, 3V3, VDD_HP, VDD_FLASH, VDD_PSRAM, VDD_MIPI: no shorts.
- [ ] Display, touch FPC and buzzer disconnected for first power.
- [ ] On a panel sample: both FFC tails reach J2 and J4 when folded back behind the panel, and pin 1 of each
      tail lands on pad 1 of its connector.

## 1. Power-up (bench supply, 5.0 V, 300 mA limit)
- [ ] USB-C only: 5V_SYS present, 3V3 = 3.3 V +/-3 %, VDD_HP inside 0.99–1.3 V once the P4 leaves reset.
- [ ] Rear-pad VIN only: same rails, PWR_SRC_ST reports the pad input.
- [ ] In the body: the board slides into its place with the USB-C receptacle in the wall's pocket; USB-C plugs
      of two makes go through the oval opening, seat fully and latch.
- [ ] CHIP_PU rises after 3V3 is stable (scope: more than 50 µs margin).
- [ ] Idle current recorded; raise the limit to 2 A only after rails look right.

## 2. Boot and programming
- [ ] USB-C enumerates as USB-Serial-JTAG; `esptool` reads chip revision v3.x and the eFuse MAC.
- [ ] Flash a hello-world built for chip revision v3.x; 32 MB PSRAM and 16 MB flash detected.
- [ ] BOOT test pad low + reset enters download mode; UART0 test pads show the ROM log.
- [ ] C5: P4 holds C5_BOOT low, pulses C5_EN, and flashes the ESP-Hosted slave image over UART.

## 3. Wi-Fi (ESP-Hosted over SDIO)
- [ ] SDIO link up at 5 MHz, then 20 MHz, then 40 MHz without CRC errors.
- [ ] Join a 2.4 GHz AP and a 5 GHz AP; record RSSI next to the current dev board at the same spot.
- [ ] iperf TCP for 30 minutes on each band; no SDIO resets in the log.
- [ ] 3V3 droop during 5 GHz transmit bursts under 100 mV (scope at the module pin).
- [ ] Sleep on Wi-Fi (screen off, P4 awake, C5 joined): record the board's current; a cloud
      `trigger` and a touch each bring the screen back, time recorded.

## 4. Display, touch, buzzer
- [ ] Panel FFCs plugged and unplugged only with power off. With no panel the backlight output
      reaches 36–39 V; LED_A is back below 7 V before the panel is connected.
- [ ] Backlight is fully dark with LCD_BL_PWM low.
- [ ] Backlight PWM dims 5–100 % with no visible flicker; LED current matches the panel datasheet.
- [ ] MIPI DSI: colour bars, then the LVGL UI at the target frame rate; no tearing or sparkle.
- [ ] Touch reports all four corners and the centre; interrupt line toggles.
- [ ] A dense QR code (version 10 or higher) scans from 30 cm and 60 cm at 30 % and 100 % brightness.
- [ ] Buzzer audible at 1 m over shop noise; sound level measured at 10 cm.
- [ ] The same measurement with the two Dock magnets glued into the body, and with the Core on a Dock (a magnet's
      centre is 10.8 mm from the buzzer's, its edge 0.75 mm outside the buzzer's outline).
- [ ] Service switch: a paper clip through the fourth slot in the bottom wall clicks it and it releases;
      the clip cannot be pushed past the switch. GPIO9 reads low while it is pressed.

## 5. Ethernet (needs a dock or LAN-module test coupon)
- [ ] PHY answers on MDIO; 50 MHz reference clock clean at GPIO50.
- [ ] Link at 100 Mbit/s full duplex through the pogo contacts; DHCP lease obtained.
- [ ] iperf for 24 hours: zero link drops, packet loss recorded.
- [ ] Pull the cable, then the accessory, while running: firmware fails over to Wi-Fi and back, no reset.
- [ ] Sleep on Ethernet (screen off, P4 awake): record the board's current with the C5 running and
      with C5_EN held low. Release C5_EN: the C5 comes back with no P4 reset. Pull the cable with
      the C5 shut down: record the time until the device is online over Wi-Fi.

## 6. Cloud path (existing protocol, unchanged)
- [ ] Claim, identity and MQTT over TLS connect on Wi-Fi and on Ethernet.
- [ ] `trigger` → QR on screen → ack, measured end to end.
- [ ] `config-changed` with branding images renders; heartbeat arrives every period.
- [ ] `firmware-update`: OTA to a second v3.x build, reboot, rollback on a deliberately bad image.

## 7. Accessory interface and power switching
- [ ] ACC_ID reads the expected voltage for each ID resistor; an open contact reads "none".
- [ ] V_ACC stays off with no accessory, switches on after ID, and current-limits into a short.
- [ ] Hot-plug dock power with USB-C attached and the reverse: 3V3 never dips below 3.1 V, no reboot.
- [ ] 1,000 attach/detach cycles on one unit: contact resistance and Ethernet link checked every 100.
- [ ] Wrong-way attach attempt is blocked mechanically; shorting adjacent pads with a probe causes no damage.
- [ ] Module pads through spring pins (18-pin test coupon): a full-speed and a high-speed USB device
      enumerate on ACC_USB with V_ACC as their supply; a high-speed transfer runs 30 minutes with no
      error. V_ACC measured at the pad with a 0.5 A load.
- [ ] UART loopback on ACC_IO1/ACC_IO2 at 115200 and 921600 baud with no error; an I2C device answers
      at 100 kHz on the same pads; ACC_INT_N works as an input and as an output.

## 7a. Dock (BAR or FLOAT body printed, both Dock boards assembled)
- [ ] Before the Core goes in: continuity from each spring pin to its harness pin and to the jack or USB-C pin;
      no short between VIN and GND; 1.0 k between the ACC_ID pin and GND.
- [ ] The contact board lies flat in its recess, the saddle's front is not proud of the Dock's front face.
- [ ] Spring pin tips stand 1.9 mm proud of the saddle's block and all 12 move freely in their holes.
- [ ] Magnets, Dock unpowered: the Core snaps on from about 2 mm away and seats with no gap; the force to pull
      it off is measured with a spring scale (calculated: about 17 N on top of the Core's weight).
- [ ] Core on its magnets, no screws: every pin lands inside its pad (marking paste on the pads), measured
      offset recorded. Repeat with the lock screws in.
- [ ] Attach and detach ten times with the Dock powered: no reboot, no burn marks on pads or pins.
- [ ] The Core goes straight onto the Dock's front face with the pins compressed; no pin snags on a pad edge.
- [ ] BAR: the caps are flush with the Core's side walls; the foot and the bar's standing face both touch the table.
- [ ] The Core's service slot (bottom wall) can be reached on the Dock, or the Core lifts off for it.
- [ ] FLOAT: the gap between the Core and the plate is even; the plate lies flat on the table.
- [ ] Pin height: gap between Core and the Dock's front face is closed, pins are not bottomed out.
- [ ] The port drawer slides in, its panel is flush; an RJ45 plug latches and a USB-C plug seats fully.
- [ ] USB-C power into the Dock: 5 V on the Core's VIN pads, Core boots, ACC_ID reads 0.30 V.
- [ ] Lock screws reach their bosses through the rear holes; the Core does not rock when the screen is pressed.
- [ ] Dock taped to a desk: pressing the top edge of the screen does not tip or push it. Loose, record the push
      at which it tips (estimate in design-spec section 13).

## 8. Security (on sacrificial units only — eFuses are permanent)
- [ ] Secure Boot v2 and flash encryption enabled in release mode; unsigned image refused.
- [ ] NVS encryption on; device key unreadable from a flash dump.
- [ ] USB download path restricted as intended after provisioning.

## 9. Pre-compliance sanity
- [ ] ESD gun (if available): ±4 kV contact on rear pads, USB-C shell and screen edge, unit powered.
- [ ] Thermal: 2 hours at full brightness in the closed enclosure; hottest surface and LCD temperature recorded.
- [ ] Near-field probe scan around the RMII clock, SDIO and DSI lines for obvious emitters.
- [ ] Cold start at 0 °C and warm soak at 45 °C (kitchen-grade test is fine at this stage).
