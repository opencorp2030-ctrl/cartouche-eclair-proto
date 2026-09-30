# CARTOUCHE Drive

A small USB-C drive for an M.2 2230 NVMe SSD, built around the JMicron JMS583
bridge (USB 3.2 Gen 2, 10 Gb/s → PCIe Gen 3 ×2). It is the prototype drive for
[CARTOUCHE](https://cartouche.candygate.eu), a local AI that runs from a USB drive.

**Status:** schematic v0.1 (ERC clean). PCB: draft v0.1 — placement, 4-layer stack, ground and power planes done; autorouted draft **not for fabrication** (the 10 Gb/s pairs still have to be routed as coupled, length-matched pairs).

## Blocks

| Block | Parts |
|---|---|
| USB-C (sink, 5 V) | Molex 105450-0101, CC pull-downs 5.1 kΩ, 100 nF on each SuperSpeed TX line |
| Bridge | JMS583 (QFN-64 8×8, 0.4 mm), 25 MHz crystal, REXT 12 kΩ 1 %, reset RC, SPI flash |
| Chip power | JMS583 internal regulators: 5 V → 1.0 V (buck, 4.7 µH) and 5 V → 3.3 V (LDO, chip only) |
| SSD power | TPS82130 3 A buck, 5 V → 3.3 V, 330 µF bulk |
| SSD | LOTES APCI0113 M.2 key M socket, 2 PCIe lanes, 220 nF on each PCIe TX line |

## Files

- `hardware/` — KiCad 9 project (`cartouche-drive.kicad_sch`), local libraries in `hardware/lib/`
- `hardware/cartouche-drive-schematic.pdf` — schematic export
- `tools/gen_schematic.py` — the connection list that generates the schematic
- `tools/build_pcb.py` — board, placement, planes and fan-out vias (KiCad Python)
- `tools/route_pcb.py` — net classes and Freerouting run

## References

- JMS583 datasheet PDS-17001 rev 1.0 (JMicron) — pin-out and required parts
- Part footprints: LCSC / EasyEDA libraries (LOTES C841669, Molex C134092, TPS82130 C473914)

## License

Hardware: CERN-OHL-S-2.0 · Tools: MIT
