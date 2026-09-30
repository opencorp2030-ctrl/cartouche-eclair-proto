"""Generates hardware/cartouche-drive.kicad_sch from the connection list below.

CARTOUCHE Drive: USB 3.2 Gen 2 (10 Gb/s) to NVMe bridge on a JMicron JMS583,
for an M.2 2230 SSD. Every JMS583 pin comes from the JMS583 datasheet
(PDS-17001 rev 1.0, tables 2 to 9). Each part is drawn with a short label on
each pin (label-style schematic): pins with the same label are connected.

Run from the repo root:  python3 tools/gen_schematic.py
Then: kicad-cli sch erc hardware/cartouche-drive.kicad_sch
"""
import os
import re
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "hardware")
KICAD_SYM = os.environ.get("KICAD_SYMBOLS", "/mnt/c/Program Files/KiCad/9.0/share/kicad/symbols")
PROJECT = "cartouche-drive"
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "cartouche-drive-root"))

# ------------------------------------------------------------------ parts
# ref, library symbol, value, footprint, LCSC, (x, y) in mm, DNP
PARTS = []
NETS = {}          # (ref, pin number) -> net name


def part(ref, sym, value, fp, lcsc, xy, pins, dnp=False):
    PARTS.append(dict(ref=ref, sym=sym, value=value, fp=fp, lcsc=lcsc, xy=xy, dnp=dnp))
    for pin, net in pins.items():
        NETS[(ref, str(pin))] = net


R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0201 = "Capacitor_SMD:C_0201_0603Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"


def R(ref, val, lcsc, xy, a, b, dnp=False):
    part(ref, "Device:R", val, R0402, lcsc, xy, {1: a, 2: b}, dnp)


def C(ref, val, lcsc, xy, a, b, fp=C0402):
    part(ref, "Device:C", val, fp, lcsc, xy, {1: a, 2: b})


# --- U1 JMS583 (datasheet pin numbers) ----------------------------------------
jms = {1: "VBUS", 2: "+1V0", 3: "SPI_SO", 4: "SPI_SCK", 5: "SPI_SI", 6: "+3V3_JMS", 7: "SPI_CS",
       8: "LED_K", 9: None, 10: "VBUS_DET", 11: "+3V3_JMS", 12: None, 13: None, 14: None,
       15: "RST", 16: "VBUS", 17: "USB_DM", 18: "USB_DP", 19: "+3V3_JMS", 20: "+1V0",
       21: "U_TXP1", 22: "U_TXN1", 23: "U_TXN2", 24: "U_TXP2", 25: "+1V0", 26: "USB_RX1P", 27: "USB_RX1N",
       28: "USB_RX2N", 29: "USB_RX2P", 30: "+1V0", 31: "+1V0", 32: "+3V3_JMS", 33: "+1V0",
       34: "PCIE_RXN1", 35: "PCIE_RXP1", 36: "+1V0", 37: "P_TXN1", 38: "P_TXP1", 39: "REXT", 40: "+1V0",
       41: "PCIE_RXN0", 42: "PCIE_RXP0", 43: "+1V0", 44: "P_TXN0", 45: "P_TXP0", 46: "+1V0",
       47: "REFCLK_N", 48: "REFCLK_P", 49: "+1V0", 50: "XIN", 51: "XOUT", 52: "+3V3_JMS", 53: "+1V0",
       54: "PERST", 55: "CLKREQ", 56: "+3V3_JMS", 57: None, 58: "MODE0", 59: "MODE1", 60: "GND",
       61: "CC2", 62: "CC1", 63: "GND", 64: "LXO", 65: "GND"}
part("U1", "cartouche:JMS583", "JMS583", "cartouche:QFN-64_L8.0-W8.0-P0.40-TL-EP4.5", "C9900110183", (190, 150), jms)

# --- J1 USB-C (Molex 105450-0101, USB 3.2 receptacle) ------------------------
usbc = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
        "A2": "USB_TX1P", "A3": "USB_TX1N", "B11": "USB_RX1P", "B10": "USB_RX1N",
        "B2": "USB_TX2P", "B3": "USB_TX2N", "A11": "USB_RX2P", "A10": "USB_RX2N",
        "A8": None, "B8": None, "S1": "GND"}
part("J1", "Connector:USB_C_Receptacle", "USB-C 105450-0101", "Connector_USB:USB_C_Receptacle_Molex_105450-0101",
     "C134092", (60, 110), usbc)

# --- J2 M.2 key M socket (LOTES APCI0113-P001A, standard M.2 pin-out) --------
m2 = {n: None for n in list(range(1, 59)) + list(range(67, 78))}
for n in (1, 3, 9, 15, 21, 27, 33, 39, 45, 51, 57, 71, 73, 75, 76, 77):
    m2[n] = "GND"
for n in (2, 4, 12, 14, 16, 18, 70, 72, 74):
    m2[n] = "+3V3"
# M.2 names are from the host side: PET = host transmits (our TX, through the 220 nF caps),
# PER = host receives (the SSD's TX, already AC-coupled on the SSD).
m2.update({29: "PCIE_RXN1", 31: "PCIE_RXP1", 35: "PCIE_TXN1_M2", 37: "PCIE_TXP1_M2",
           41: "PCIE_RXN0", 43: "PCIE_RXP0", 47: "PCIE_TXN0_M2", 49: "PCIE_TXP0_M2",
           50: "PERST", 52: "CLKREQ", 53: "REFCLK_N", 55: "REFCLK_P"})
part("J2", "cartouche:APCI0113-P001A", "M.2 key M (2230)", "cartouche:CONN-SMD_APCI0113-P001A", "C841669", (330, 150), m2)

# --- USB side passives ---------------------------------------------------------
R("R1", "5.1k", "C25905", (95, 70), "CC1", "GND")            # Rd: the drive is a USB-C sink
R("R2", "5.1k", "C25905", (95, 80), "CC2", "GND")
C("C1", "100nF", "C1525", (110, 95), "U_TXP1", "USB_TX1P")  # datasheet: 100 nF on each SS TX line
C("C2", "100nF", "C1525", (110, 105), "U_TXN1", "USB_TX1N")
C("C3", "100nF", "C1525", (110, 115), "U_TXP2", "USB_TX2P")
C("C4", "100nF", "C1525", (110, 125), "U_TXN2", "USB_TX2N")
R("R3", "10k", "C25744", (95, 160), "VBUS", "VBUS_DET")      # VBUS detector on GPIO[6] (datasheet 7.6)
R("R4", "20k", "C25765", (95, 170), "VBUS_DET", "GND")       # 5 V x 20/30 = 3.33 V
C("C5", "10uF 25V", "C15850", (80, 185), "VBUS", "GND", C0805)
C("C6", "100nF", "C1525", (95, 185), "VBUS", "GND")

# --- JMS583 support -------------------------------------------------------------
part("L1", "Device:L", "4.7uH", "Inductor_SMD:L_1008_2520Metric", "", (150, 60), {1: "LXO", 2: "+1V0"})  # datasheet 5.3.5
C("C7", "22uF", "C45783", (165, 45), "+1V0", "GND", C0805)
C("C8", "10uF", "C15525", (175, 45), "+1V0", "GND")
for i, x in enumerate(range(185, 185 + 12 * 10, 10)):                 # one 100 nF per 1.0 V pin (3 VCCK + 9 AVDDL)
    C(f"C{9+i}", "100nF", "C1525", (x, 45), "+1V0", "GND")
C("C21", "1uF", "C52923", (150, 250), "+3V3_JMS", "GND")              # datasheet: 1 uF on AVDD33
C("C22", "10uF", "C15525", (160, 250), "+3V3_JMS", "GND")
for i, x in enumerate(range(170, 170 + 5 * 10, 10)):                  # 4 VCCO + XAVDDH
    C(f"C{23+i}", "100nF", "C1525", (x, 250), "+3V3_JMS", "GND")
C("C28", "10uF 25V", "C15850", (220, 250), "VBUS", "GND", C0805)      # VDDREG / VBUS pins
C("C29", "100nF", "C1525", (230, 250), "VBUS", "GND")
R("R5", "12k 1%", "C25752", (240, 250), "REXT", "GND")               # datasheet: 12 k 1 % on REXT
R("R6", "10k", "C25744", (250, 250), "+3V3_JMS", "RST")              # reset RC (datasheet 5.3.7)
C("C30", "1uF", "C52923", (260, 250), "RST", "GND")
R("R7", "10k", "C25744", (270, 250), "MODE0", "GND", dnp=True)      # MODE straps: not fitted (internal pull-ups)
R("R8", "10k", "C25744", (280, 250), "MODE1", "GND", dnp=True)
part("Y1", "cartouche:SX0B25.000F1210F30", "25MHz 12pF", "cartouche:CRYSTAL-SMD_4P-L1.6-W1.2-BL", "C7301914",
     (130, 200), {1: "XIN", 3: "XOUT", 2: "GND", 4: "GND"})
C("C31", "18pF", "C1549", (115, 215), "XIN", "GND")                  # 2 x (12 pF - ~3 pF stray)
C("C32", "18pF", "C1549", (145, 215), "XOUT", "GND")
part("LED1", "Device:LED", "red", "LED_SMD:LED_0603_1608Metric", "C2286", (260, 200), {1: "LED_K", 2: "LED_A"})
R("R9", "1k", "C11702", (275, 200), "LED_A", "+3V3")                 # GPIO[4] = LED (datasheet 5.4), sinks current

# --- SPI flash (firmware / VID-PID) -------------------------------------------------
part("U3", "cartouche:ZD25WQ16CEIGR", "ZD25WQ16", "cartouche:USON-8_L3.0-W2.0-P0.50-BL-EP", "C7304007", (130, 290),
     {1: "SPI_CS", 2: "SPI_SO", 3: "FLASH_WP", 4: "GND", 5: "SPI_SI", 6: "SPI_SCK", 7: "FLASH_HOLD", 8: "+3V3", 9: "GND"})
R("R10", "10k", "C25744", (100, 280), "SPI_CS", "+3V3")
R("R11", "10k", "C25744", (100, 290), "FLASH_WP", "+3V3")
R("R12", "10k", "C25744", (100, 300), "FLASH_HOLD", "+3V3")
C("C33", "100nF", "C1525", (160, 290), "+3V3", "GND")

# --- PCIe to the SSD ----------------------------------------------------------------------
C("C34", "220nF", "C76932", (270, 110), "P_TXP0", "PCIE_TXP0_M2", C0201)   # datasheet: 220 nF on each PCIe TX
C("C35", "220nF", "C76932", (270, 120), "P_TXN0", "PCIE_TXN0_M2", C0201)
C("C36", "220nF", "C76932", (270, 130), "P_TXP1", "PCIE_TXP1_M2", C0201)
C("C37", "220nF", "C76932", (270, 140), "P_TXN1", "PCIE_TXN1_M2", C0201)
R("R13", "10k", "C25744", (280, 190), "CLKREQ", "+3V3")              # CLKREQ# is open-drain

# --- 3.3 V for the SSD (the JMS583 LDO is for the chip only, 150 mA max) ----------------
part("U2", "cartouche:TPS82130SILR", "TPS82130", "cartouche:USIP-8_L3.0-W2.8-P0.65-TL-EP", "C473914", (330, 280),
     {1: "SSD_EN", 2: "VBUS", 3: "GND", 4: "+3V3", 5: "+3V3", 6: "FB", 7: None, 8: "SS", 9: "GND"})
R("R14", "10k", "C25744", (300, 265), "VBUS", "SSD_EN")
C("C38", "10uF 25V", "C15850", (300, 290), "VBUS", "GND", C0805)
C("C39", "3.3nF", "C1536", (300, 300), "SS", "GND")
R("R15", "475k 1%", "C5713272", (365, 270), "+3V3", "FB")            # Vout = 0.8 V x (1 + 475/150) = 3.33 V
R("R16", "150k 1%", "C2909320", (365, 285), "FB", "GND")
C("C40", "22uF", "C45783", (380, 270), "+3V3", "GND", C0805)
part("C41", "Device:C_Polarized", "330uF 10V", "Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D", "C105408",
     (395, 270), {1: "+3V3", 2: "GND"})
C("C42", "100nF", "C1525", (380, 290), "+3V3", "GND")
for i, x in enumerate(range(360, 400, 10)):                          # M.2 3.3 V pins
    C(f"C{43+i}", "10uF", "C15525", (x, 110), "+3V3", "GND")

part("H1", "Mechanical:MountingHole_Pad", "M2 standoff (SSD)", "MountingHole:MountingHole_2.2mm_M2_Pad_Via", "", (60, 330), {1: "GND"})

# power flags: tell ERC which nets are supplied
for i, (net, x) in enumerate([("VBUS", 40), ("+3V3", 60), ("+3V3_JMS", 80), ("+1V0", 100), ("GND", 120)]):
    part(f"#FLG{i+1}", "power:PWR_FLAG", "PWR_FLAG", "", "", (x, 350), {1: net})

# ------------------------------------------------------------------ symbol library access
_cache = {}


def lib_text(lib):
    if lib not in _cache:
        path = os.path.join(HW, "lib", "cartouche.kicad_sym") if lib == "cartouche" else os.path.join(KICAD_SYM, lib + ".kicad_sym")
        _cache[lib] = open(path, encoding="utf8").read()
    return _cache[lib]


def sexpr_block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced")


def symbol_def(lib_id):
    lib, name = lib_id.split(":")
    t = lib_text(lib)
    m = re.search(r'\(symbol "' + re.escape(name) + r'"', t)
    blk = sexpr_block(t, m.start())
    ext = re.search(r'\(extends "([^"]+)"\)', blk)
    if ext:
        raise ValueError(f"{lib_id} extends {ext.group(1)}: pick the base symbol")
    return blk.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)


def pins_of(lib_id):
    blk = symbol_def(lib_id)
    out = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)', blk):
        tail = blk[m.end():m.end() + 600]
        num = re.search(r'\(number "([^"]*)"', tail).group(1)
        out.setdefault(num, []).append((float(m.group(1)), float(m.group(2)), int(m.group(3))))
    return out


def U():
    return str(uuid.uuid4())


def snap(v):
    return round(round(v / 1.27) * 1.27, 2)


# ------------------------------------------------------------------ write the sheet
used = sorted({p["sym"] for p in PARTS})
out = [f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{ROOT_UUID}") (paper "A2")',
       '  (title_block (title "CARTOUCHE Drive") (rev "0.1") (comment 1 "USB 3.2 Gen 2 to NVMe, JMS583, M.2 2230"))',
       "  (lib_symbols"]
for s in used:
    out.append("    " + symbol_def(s))
out.append("  )")
labels, nc = [], []
for p in PARTS:
    x, y = snap(p["xy"][0]), snap(p["xy"][1])
    power = p["sym"].startswith("power:")
    props = [("Reference", p["ref"]), ("Value", p["value"]), ("Footprint", p["fp"]), ("Datasheet", ""), ("LCSC", p["lcsc"])]
    ps = "".join(f'\n    (property "{k}" "{v}" (at {x} {y + 2.54 * i} 0) (effects (font (size 1.27 1.27)){" (hide yes)" if (k not in ("Reference", "Value") or power) else ""}))'
                 for i, (k, v) in enumerate(props))
    pins = pins_of(p["sym"])
    pin_uuids = "".join(f'\n    (pin "{n}" (uuid "{U()}"))' for n in pins)
    out.append(f'  (symbol (lib_id "{p["sym"]}") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom {"no" if (power or p["ref"].startswith("H")) else "yes"}) '
               f'(on_board {"no" if power else "yes"}) (dnp {"yes" if p["dnp"] else "no"}) (uuid "{U()}"){ps}{pin_uuids}\n'
               f'    (instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{p["ref"]}") (unit 1)))))')
    for num, spots in pins.items():
        net = NETS.get((p["ref"], num), "__missing__")
        for (px, py, ang) in spots:
            ex, ey = round(x + px, 2), round(y - py, 2)
            if net is None:
                nc.append(f'  (no_connect (at {ex} {ey}) (uuid "{U()}"))')
            elif net == "__missing__":
                raise SystemExit(f"{p['ref']} pin {num} has no net in the connection list")
            else:
                la = {0: 180, 180: 0, 90: 270, 270: 90}[ang]
                labels.append(f'  (label "{net}" (at {ex} {ey} {la}) (effects (font (size 1.0 1.0)) (justify {"right" if la == 180 else "left"} bottom)) (uuid "{U()}"))')
out += labels + nc
out.append(f'  (sheet_instances (path "/" (page "1")))\n)')
os.makedirs(HW, exist_ok=True)
open(os.path.join(HW, PROJECT + ".kicad_sch"), "w", encoding="utf8").write("\n".join(out) + "\n")
nets = sorted({n for n in NETS.values() if n})
print(f"{len(PARTS)} parts, {len(nets)} nets, {len(labels)} labels, {len(nc)} no-connects")
