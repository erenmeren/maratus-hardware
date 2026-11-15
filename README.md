# maratus-hardware

Open hardware for **Maratus** (maratus.co): the **Core** (an always-powered 4-inch touchscreen that
shows a cloud-triggered QR code), the **Dock** and the **LAN Module**. KiCad sources, mechanical
CAD and design documents.

**Status: draft.** Nothing here is manufacturing-ready, and no hardware has been built or tested.
The boards are generated and autorouted; the critical nets still need a layout engineer
(`docs/design-spec.md`, sections 10 and 11).

## Where to start

| Path | Content |
| --- | --- |
| `docs/design-spec.md` | The design decisions, block by block, and the open items |
| `hardware/core/` | KiCad project of the Core |
| `hardware/dock-contact/`, `hardware/dock-base/` | KiCad projects of the Dock's two boards |
| `mechanical/core/` | Enclosure (STEP, STL), cover lens (DXF and drawing) |
| `tools/` | Generators and checks; the commands are listed in `CLAUDE.md` |

Related repositories: `erenmeren/maratus-firmware` (ESP-IDF firmware) and `erenmeren/maratus-admin`
(cloud, device protocol).

## Licence

Apache License 2.0, see `LICENSE`. Copyright 2026 the Maratus authors.

Not covered by it: the datasheets and reference schematics in `docs/reference/`, which belong to
their manufacturers and are kept here for reference, and Espressif's KiCad library in
`hardware/lib/espressif`, a git submodule with its own licence.
