# MARATUS — Custom Hardware, PCB & Industrial Design Master Prompt

## Your Role

You are a multidisciplinary hardware product development team consisting of:

- Senior electronics and PCB design engineer
- Embedded systems engineer specialising in Espressif ESP32
- RF and wireless hardware engineer
- Industrial and mechanical product designer
- Design-for-manufacturing (DFM) engineer
- Product reliability and compliance engineer

Your objective is to engineer a **real, manufacturable commercial device**, not just create a concept render.

You have the ability to create electronic schematics, PCB layouts, mechanical CAD models, enclosures, and manufacturing files. Use these capabilities to produce actual design deliverables.

The project is called **MARATUS**.

Website: https://maratus.co/

Software repository: https://github.com/erenmeren/maratus-admin

Device protocol: https://github.com/erenmeren/maratus-admin/blob/main/docs/device-protocol.md

Carefully examine the existing website, device concept, product functionality, and available technical documentation before beginning.

---

# 1. Understand the Product

Maratus is a cloud-connected customer-facing retail interaction device.

It sits at checkout counters in supermarkets, cafés, retail stores, restaurants, petrol stations, and other commercial locations.

Its primary function is to display dynamically generated QR codes that customers scan using their smartphones.

Example:

1. A customer completes a purchase.
2. The retailer's POS or business application sends a URL to the Maratus cloud API.
3. The cloud sends a command to the correct Maratus device.
4. The device displays a QR code representing that URL.
5. The customer scans the code with their phone.
6. The device returns to a branded idle screen or a configured pinned experience.

The destination content is owned and hosted by the retailer. Maratus does not need to store receipts, transaction contents, or customer payment information.

The current backend uses HTTPS for bootstrap and MQTT for device commands, configuration, acknowledgements, heartbeats, and OTA notifications.

The device must remain compatible with this architecture.

Important software capabilities:

- Secure provisioning and device identity
- Remote QR triggering
- Configurable branding and display layouts
- Persistent idle/pinned screens
- MQTT communication over TLS
- Heartbeats and device status
- Secure firmware OTA updates
- Remote configuration
- Device identification and diagnostics

This is NOT a payment terminal.

It does not need a credit card reader, payment processor, receipt printer, or barcode reader in the initial version.

The user already has a functional ESP32-P4 development-board proof of concept with a 4-inch display and an LVGL-based interface.

We are now replacing development hardware with our own custom product.

# 2. Overall Product Architecture

We want to establish a family of hardware products based on **one reusable central device**.

The product family should eventually consist of:

**Maratus Core**

The main 4-inch display device, containing its own PCB, processor, wireless connectivity, touchscreen, and buzzer.

**Maratus Dock**

A secure desktop docking station providing Ethernet connectivity, power, and mechanical locking.

**Maratus LAN Module**

An optional compact Ethernet accessory for customers who do not want the dock.

**Maratus Battery Module**

An optional battery-powered accessory for locations where permanent power is not available.

**Future Expansion Modules**

Potential camera, barcode scanner, QR scanner, or other accessories.

The main device must be identical across these use cases whenever technically possible.

Avoid creating separate main PCB designs for every deployment scenario.

However, do not sacrifice electrical safety, sealing, RF performance, or reliability merely to force universal modularity.

# 3. Main Processing and Wireless Hardware

## Mandatory processors

Use:

- **ESP32-P4** as the primary application processor.
- **ESP32-C5** as the wireless connectivity coprocessor.

The ESP32-C5 must support:

- 2.4 GHz Wi-Fi
- 5 GHz Wi-Fi
- Wi-Fi 6 functionality supported by the selected module and firmware
- Reliable enterprise/retail wireless networking

Note: Dual-band capability does not mean simultaneous operation on both bands.

Research and select the exact production-compatible ESP32-P4 part and ESP32-C5 module.

Consider ESP32-C5-WROOM-1 or WROOM-1U, depending on RF and enclosure requirements.

Investigate connecting P4 and C5 through SDIO with ESP-Hosted.

Use the most appropriate validated approach rather than blindly copying a development board.

Evaluate:

- GPIO allocation
- Boot circuitry
- SPI flash and PSRAM
- SDIO and clock routing
- Power supply and decoupling
- Reset control
- Watchdogs
- Programming and debugging
- RF antenna placement
- Secure Boot
- Flash/NVS encryption
- Firmware partitioning and rollback
- Production provisioning

Use official Espressif hardware reference designs and PCB guidelines.

References:

https://documentation.espressif.com/esp32-p4_datasheet_en.html

https://documentation.espressif.com/esp32-c5-wroom-1_wroom-1u_datasheet_en.html

https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32p4/

# 4. Display Requirements

The main device must have a **4-inch capacitive touchscreen**.

Preferred:

- AMOLED display
- Premium appearance
- Sharp text and QR codes
- Good colour reproduction
- Wide viewing angles
- MIPI DSI if supported by the selected panel and board architecture

However, AMOLED is a preference, not an unconditional requirement.

Compare at least:

1. A manufacturable 4-inch AMOLED touchscreen.
2. A suitable 4-inch IPS LCD touchscreen.

Evaluate:

- Exact manufacturer and part number
- Controller and interface compatibility
- MIPI lane count and signal bandwidth
- Touch controller and available driver
- LVGL integration
- Operating temperature
- Outdoor readability
- Brightness
- Panel lifespan
- Static-image burn-in
- Availability and replacement options
- Prototype and 500-unit production cost

The device may display static logos, QR codes, and branded screens for extended periods.

If AMOLED is unsuitable because of burn-in, thermal limitations, sourcing, firmware support, or cost, explain why and recommend the better engineering choice.

Do not select a panel solely because its diagonal size is correct.

Confirm the display's complete interface, controller initialization requirements, electrical specifications, FPC connector, and mechanical drawing.

A protected glass front with minimal bezels is preferred.

# 5. Audio Requirements

The device must produce a short audible beep when a relevant interaction occurs.

A simple piezo buzzer or compact acoustic transducer is sufficient.

No microphone, voice assistant, or high-fidelity speaker is required.

Choose a solution that is:

- Inexpensive
- Compact
- Reliable
- Firmware-controllable
- Audible in retail environments
- Compatible with the planned enclosure and weather protection

Consider acoustic sealing or a suitable membrane where needed.

# 6. Power Architecture

The main device must operate without a battery.

Provide USB-C input for independent operation, installation, and servicing.

It must also accept power through the dock/module interface.

Design safe power-path management that accounts for:

- USB-C input power
- Dock power
- Future battery module input
- Reverse-current protection
- Overcurrent protection
- ESD and transient protection
- Short-circuit protection
- Input priority and power switching
- Brownout behaviour
- Hot-plug events
- Power consumption and thermal performance

Determine whether uninterrupted operation during power-source transitions is necessary and feasible.

The base device must work even if no optional module is installed.

Avoid unnecessary power-management complexity in V1.

The first hardware revision does not need a complete internal battery charging system unless there is a compelling engineering reason. Battery protection, charging, and fuel-gauge circuitry may live in the future battery module.

# 7. Universal Docking and Expansion Interface

This is one of the most important design challenges.

We need a carefully designed modular interface that can eventually support:

- Secure desktop docking
- Ethernet accessories
- Battery accessories
- Other peripheral modules

I am considering a combination of:

**Pogo pins + magnetic alignment + mechanical locking.**

Please evaluate this architecture critically.

Magnets should help align and position the device.

They must NOT be the only mechanism preventing removal or theft.

Design a robust physical retention and locking system that can be released only by authorised staff using a service tool, key, or other controlled mechanism.

The modular connection must be:

- Mechanically keyed
- Resistant to incorrect alignment
- Protected against shorts
- Suitable for repeated attachment cycles
- Resistant to accidental detachment
- Reasonably resistant to tampering
- Compact and visually unobtrusive

Analyse whether pogo contacts are appropriate for each intended signal.

Consider connector voltage/current ratings, contact sequence, ESD, corrosion, high-speed signal integrity, and hot-plug safety.

Do not route high-speed interfaces such as MIPI CSI, USB high-speed, or Ethernet RMII through ordinary pogo pins without validating the physical-layer requirements.

If pogo pins are unsuitable for particular signals, propose a hybrid connector or an alternative architecture.

Define a reusable expansion interface containing only the functions genuinely needed.

Potential functions include:

- Power
- Ground
- Accessory identification
- I2C
- UART
- USB where appropriate
- Selected control signals

Reserve enough flexibility for future accessories without making the initial board unnecessarily large or expensive.

Investigate whether multiple accessories can be connected simultaneously and whether accessory stacking is practical.

Do not assume stacking is necessary if it creates reliability or mechanical problems.

# 8. Ethernet Design

Ethernet is a core commercial requirement.

It must be available in two configurations.

## Configuration A — Desktop Dock

The main device attaches to a locking desktop dock.

The dock provides:

- RJ45 Ethernet connectivity
- Device power
- Mechanical support
- Cable management
- Physical anti-theft locking

Ideally, the device connects electrically through the docking interface.

## Configuration B — Standalone Ethernet Module

Customers who do not want a desk dock can attach a small Ethernet module directly to the main device.

The module should provide the same essential LAN functionality without requiring a large desktop stand.

## Engineering requirement

The ESP32-P4 includes an Ethernet MAC, but the final physical architecture must be engineered carefully.

Compare feasible approaches, including:

- Native ESP32-P4 Ethernet MAC with an external PHY
- Appropriate PHY placement in the main device or accessory
- An adequately engineered modular Ethernet connection
- A validated USB-to-Ethernet bridge solution, if driver support exists
- Other reliable alternatives

Consider 10/100 Mbps Ethernet sufficient for the current product unless there is a compelling reason for more.

Evaluate power, PCB space, signal integrity, magnetics, isolation, hot-plug safety, drivers, and assembly cost.

Do not assume raw RMII can simply pass through pogo contacts.

Select the best solution and explain the trade-offs.

Investigate optional PoE for the dock, but do not add it to V1 without a clear reliability and cost justification.

Wi-Fi and Ethernet must have predictable connection priority and failover behaviour.

# 9. Outdoor / Petrol Station Deployment

The hardware must eventually be suitable for outdoor installations such as petrol stations.

In these locations:

- The main device may not use a conventional desktop dock.
- It may require a wall, pole, or secure fixture mount.
- It may be exposed to sunlight, dust, rain, temperature changes, and vandalism.
- It must be difficult for unauthorised users to remove.
- A battery accessory may be useful.

The mechanical design must investigate:

- Water ingress
- Dust ingress
- UV exposure
- Display readability
- Condensation
- Thermal expansion
- Surface temperature
- Anti-tamper mounting
- Weather-resistant power connections
- Sealed accessory interfaces

Use IP65 as an initial design target for an outdoor variant, not as a certification claim.

Critically important:

Petrol station forecourts may contain hazardous areas where explosive fuel vapours are possible.

UK DSEAR / explosive-atmosphere equipment requirements must be considered.

Do NOT assume a standard ESP32 board, lithium battery, 3D-printed enclosure, or ordinary electrical connector is safe for use in a classified hazardous zone.

The initial prototype is intended only for locations permitted by the site's risk assessment.

If installation inside a hazardous zone is required, identify the necessary specialist engineering, certification, and product changes.

Do not claim ATEX, UKEX, IECEx, or equivalent compliance without the required engineering and conformity assessment.

# 10. Industrial Design Direction

The physical product should look like premium commercial hardware.

It must not resemble an exposed electronics project or a generic hobbyist ESP32 development kit.

Design inspiration:

- Maratus.co visual identity and existing device concept
- Apple-level material refinement and simplicity
- Teenage Engineering's deliberate industrial-design detailing
- Premium retail hardware

Do not copy an existing company's product design.

The device should have its own recognisable Maratus identity.

Preferred visual characteristics:

- Clean, geometric form
- Minimal bezels
- High-quality front glass
- Premium graphite/dark-grey appearance
- Carefully controlled seams
- Subtle Maratus branding
- Hidden or discreet mounting hardware
- Simple and elegant rear module interface
- Visually integrated docking mechanism

Explore graphite, black, white, and restrained green accents.

Consider high-quality PC+ABS or other RF-compatible polymers for the main body, with carefully selected metal accents where practical.

Do not allow an aluminium enclosure to compromise 2.4/5 GHz antenna performance.

The device should look equally intentional:

- In a dock
- Without a dock
- On a secure outdoor mount

The dock should look like an extension of the product, not a separate generic phone stand.

The customer-facing screen must be easy to scan from typical checkout-counter positions.

Account for ergonomics, viewing angle, reflections, cable exit direction, and countertop stability.

# 11. 3D Printing and Enclosure Prototyping

I own a 3D printer.

I want to manufacture the first prototypes myself after receiving the PCB and display.

Design the enclosure so it is genuinely suitable for 3D printing.

Provide:

- Parametric CAD files
- STEP mechanical models
- STL files
- Editable original CAD project
- Printable separated parts
- Assembly instructions
- Screw and insert specifications
- Mechanical tolerances
- PCB mounting features
- Display mounting features
- Clearances for connectors and antennas

Consider common FDM printing limitations.

Avoid unnecessarily complicated supports, inaccessible screws, weak snap-fits, or unprintable internal features.

Use suitable threaded inserts or screws for prototype assembly.

Design the enclosure for maintenance by authorised technicians, not by customers.

The device should not have an exposed user-accessible reset button.

A recessed service reset or internal service access is acceptable.

For outdoor prototypes, consider materials such as ASA and appropriate seals, while being explicit that 3D printing alone does not establish weatherproof or explosive-atmosphere certification.

The enclosure must be based on the actual PCB, display, connectors, antenna keep-out regions, and thermal constraints.

Do not design an attractive enclosure that cannot physically contain the electronics.

# 12. Future Modules — Design for Expansion, Not Full Implementation

Future accessory possibilities include:

- Camera
- Barcode reader
- QR scanner
- Battery module
- Other retail interaction peripherals

These are NOT required in the first prototype.

However, we should avoid an architecture that makes them impossible later.

For cameras, examine the ESP32-P4 MIPI CSI capability and whether an internal FPC camera interface is more appropriate than sending camera signals through external pogo contacts.

For barcode readers, investigate UART or USB-based accessory interfaces.

Reserve appropriate electrical resources and mechanical expansion strategies where economical.

Do not include camera sensors, barcode scanners, NFC hardware, or unnecessary peripherals on the initial PCB.

Maintain a clear distinction between:

- Implemented V1 features
- Reserved interfaces
- Future accessory concepts

# 13. Commercial Production Requirements

This device is intended for commercial deployment in the United Kingdom, Europe, and Turkey.

Design decisions should consider eventual CE/UK market conformity assessment, radio compliance, EMC, electrical safety, RoHS, environmental reliability, and the relevant requirements of target countries.

Investigate applicable standards and clearly distinguish legal requirements from optional engineering targets.

Prioritise:

- Readily available production components
- Stable supply chains
- Reasonable PCB assembly costs
- Testability during manufacturing
- Low component count
- Reliable mechanical assembly
- Future repair and replacement
- Secure factory provisioning

The first step is small-scale prototyping, approximately 5–10 devices.

The longer-term goal is a potential first production batch of approximately 500 units.

Cost matters significantly.

An aggressive historical target is approximately USD $30 for the core device at volume, but this is a stretch goal, not an assumption.

Do not claim the target is achievable without a defensible BOM and manufacturing estimate.

Compare realistic costs for 10, 100, and 500 units.

Keep core hardware, display, enclosure, dock, and optional accessories separately costed.

Optimise for the best practical balance of premium appearance, reliability, security, and manufacturing cost.

# 14. Development Process — Follow This Order

This project must be executed in stages.

## Phase 0 — Requirements and Feasibility

Study Maratus and produce:

1. Product requirements summary.
2. Proposed system block diagram.
3. Main component selection.
4. ESP32-P4 + ESP32-C5 architecture.
5. Display comparison.
6. Ethernet integration decision.
7. Universal expansion connector architecture.
8. Preliminary power budget.
9. Preliminary mechanical envelope and PCB size constraints.
10. Main technical risks.

Compare competing designs where necessary, then recommend one architecture.

Do not remain indefinitely in brainstorming mode.

Make justified engineering decisions and begin implementation.

## Phase 1 — Design the Main PCB FIRST

Create the actual Maratus Core PCB.

Preferred tool: KiCad, using native editable project files.

Deliver:

- Complete electrical schematic
- PCB layout
- Native KiCad project
- Detailed BOM with manufacturer part numbers
- GPIO and interface allocation table
- Power-tree diagram
- RF and antenna implementation details
- Display and touch connections
- C5 SDIO connections
- USB-C circuitry
- Buzzer circuitry
- Expansion connector definition
- Programming and factory-test pads
- Reset and boot circuit
- 3D PCB model
- Gerber files
- Drill files
- Assembly position files
- Manufacturing/assembly notes
- ERC and DRC reports

Pay attention to controlled-impedance routing, ground planes, MIPI constraints, RF layout, decoupling, return paths, and EMI.

Explicitly identify anything still requiring measurement, prototype validation, or manual engineering review.

A visually plausible PCB image is not a substitute for a valid schematic and routed PCB.

Deliver real design source files if you have CAD generation capabilities.

If a feature cannot be implemented reliably, identify the blocker rather than inventing completion.

## Phase 2 — Design the Main Enclosure

After the PCB and selected display dimensions are established:

1. Create the mechanical product design.
2. Design the front and rear housing.
3. Incorporate the real PCB and display STEP models.
4. Add screw bosses and mounts.
5. Position the USB-C and service access.
6. Integrate the buzzer acoustic path.
7. Integrate the expansion connection.
8. Define magnetic alignment and locking features.
9. Respect antenna placement and keep-out zones.
10. Provide STL, STEP, and editable CAD files.

Show multiple orthographic views, exploded assembly views, and realistic product renders.

Provide print orientation and assembly notes.

## Phase 3 — Design the Desktop Dock

Next, design the dedicated Maratus Dock.

It must support:

- Stable angled desktop placement
- RJ45 Ethernet
- Power input or another validated power arrangement
- Device alignment
- Protected electrical contacts
- Secure mechanical locking
- Cable routing
- Service-only device release
- Repeatable attachment and detachment

Deliver:

- Complete mechanical CAD
- Dock PCB, if required
- Schematic and manufacturing files for any dock electronics
- STL/STEP files
- Locking mechanism detail
- Assembly instructions
- Full assembly model with the Maratus Core installed

The dock must be compatible with the final main device, not an unrelated concept model.

## Phase 4 — Define Future Accessories

Only after the core device and dock are designed:

Document the technical interfaces and possible mechanical layouts for:

- Standalone LAN Module
- Battery Module
- Camera Module
- Barcode Scanner Module
- Secure outdoor mounting accessory

Do not spend the initial engineering effort fully developing these modules.

Their purpose in V1 is to validate and future-proof the core architecture.

# 15. Design Validation

Before describing any hardware as manufacturing-ready, perform all available checks.

At minimum review:

- Schematic ERC
- PCB DRC
- Electrical power budgets
- Thermal feasibility
- Display interface compatibility
- RF placement
- Connector pinout and mechanical orientation
- Docking contact sequencing
- Mechanical interference and tolerances
- PCB/enclosure fit
- Fastener accessibility
- Cable routing
- Assembly feasibility
- Test access
- Major compliance risks

Create a checklist for prototype bring-up, covering:

- Power-up
- Boot and programming
- Wi-Fi at 2.4/5 GHz
- Ethernet
- Touchscreen
- Display rendering
- Buzzer
- Cloud MQTT communication
- QR triggering
- Secure OTA
- Dock connection
- Repeated attachment cycles
- Power source switching
- Basic ESD and environmental pre-compliance checks

Clearly label untested areas.

# 16. Expected Outputs and Working Style

I do not want a generic design essay or a collection of concept pictures.

I want actual engineering progress.

For every phase:

1. Explain your important design decisions briefly.
2. Create the required technical files.
3. Show the resulting design.
4. Validate it as far as your tools permit.
5. Identify unresolved issues.
6. Provide the files in editable manufacturing-friendly formats.
7. Explain what I can physically order, assemble, and test.

Do not fabricate component specifications, part availability, pricing, or engineering validation results.

Use real manufacturer datasheets and verified footprints.

Make sensible decisions autonomously where requirements are flexible. Ask questions only when a missing decision would materially affect safety, compatibility, or expensive manufacturing commitments.

Prefer the simplest robust architecture over unnecessary complexity.

## Final Instruction

**Begin with Phase 0 and immediately progress toward Phase 1: the real custom Maratus PCB.**

The first engineering objective is to produce a correct, compact, manufacturable ESP32-P4 + ESP32-C5 board with a 4-inch touchscreen, buzzer, USB-C power, and a reliable dock/accessory interface.

Once the main board is validated, design the 3D-printable enclosure around it, followed by the secure Ethernet dock.

**The ultimate outcome should be a coherent family of physical hardware products that can be prototyped, tested, and eventually manufactured — not just attractive renders.**