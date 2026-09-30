"""Builds hardware/cartouche-drive.kicad_pcb from the schematic netlist (KiCad 9 Python).

Run with KiCad's own Python (it has pcbnew):
  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\build_pcb.py
Steps: read the netlist, load every footprint, place it, assign the nets,
draw the outline, set the 4-layer stack and design rules, add the ground
planes, then export a Specctra DSN for Freerouting.

Board frame (mm, KiCad y goes down): 36 x 46 mm. The M.2 2230 SSD lies over the
right part of the board (on its 4.75 mm connector and an M2 standoff). The JMS583
sits under the SSD with its PCIe side facing the socket's PCIe pins (same order,
no crossing); the USB-C receptacle is on the left edge, facing the USB side.
"""
import os
import re
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(os.path.dirname(HERE), "hardware")
KFP = r"C:\Program Files\KiCad\9.0\share\kicad\footprints"
NET = os.path.join(HW, "cartouche-drive.net")
OUT = os.path.join(HW, "cartouche-drive.kicad_pcb")
W, H = 36.0, 46.0

mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


# ---------------------------------------------------------------- netlist
txt = open(NET, encoding="utf8").read()
comps = {}
for m in re.finditer(r'\(comp \(ref "([^"]+)"\)(.*?)\(sheetpath', txt, re.S):
    body = m.group(2)
    fp = re.search(r'\(footprint "([^"]*)"\)', body)
    val = re.search(r'\(value "([^"]*)"\)', body)
    comps[m.group(1)] = dict(fp=fp.group(1) if fp else "", value=val.group(1) if val else "")
nets = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)(?=\(net \(code|\)\s*\)\s*$)', txt, re.S):
    for r, p in re.findall(r'\(ref "([^"]+)"\) \(pin "([^"]+)"', m.group(2)):
        nets[(r, p)] = m.group(1)

# ---------------------------------------------------------------- placement (x, y, rotation)
# Big parts are placed by hand; every small part is then placed automatically
# as close as possible to the pad it serves (same net on a big part), without
# overlapping anything (courtyards + 0.25 mm), on a 0.25 mm grid.
JX = 23.24                       # socket centre: puts the socket's PCIe pins right under the chip's
PLACE = {
    "J2": (JX, 36.0, 0),         # M.2 socket; card edge at y 35.75, SSD up to y 5.75
    "H1": (JX, 5.75, 0),         # M2 standoff at the far end of a 2230 card
    "U1": (24.0, 23.8, 270),     # JMS583, PCIe side down (towards J2), USB side left (towards J1)
    "J1": (5.0, 24.8, 270),      # USB-C, mouth on the left edge
    "U2": (11.7, 10.0, 90),      # SSD 3.3 V buck: VIN on the VBUS side (left), VOUT on the +3V3 side
    "C41": (JX, 43.5, 0),        # 330 uF tantalum (3.1 mm tall): below the socket, outside the SSD
}
BIG = ["J2", "U1", "J1", "U2", "C41", "H1"]
NEAR = {"Y1": ("U1", "50"), "U3": ("U1", "5"), "L1": ("U1", "64"), "LED1": ("U1", "8"),
        # one 100 nF per power pin of the JMS583, as close as possible to that pin
        **{f"C{9+i}": ("U1", p) for i, p in enumerate(["2", "20", "25", "30", "31", "33", "36", "40", "43", "46", "49", "53"])},
        **{f"C{23+i}": ("U1", p) for i, p in enumerate(["6", "11", "32", "56", "52"])},
        "C21": ("U1", "19"), "C22": ("U1", "19"), "C28": ("U1", "1"), "C29": ("U1", "16"), "C7": ("U1", "64"), "C8": ("U1", "64"),
        "R5": ("U1", "39"), "R6": ("U1", "15"), "C30": ("U1", "15"), "R3": ("U1", "10"), "R4": ("U1", "10"),
        "C31": ("U1", "50"), "C32": ("U1", "51"), "R7": ("U1", "58"), "R8": ("U1", "59"),
        "C1": ("U1", "21"), "C2": ("U1", "22"), "C3": ("U1", "24"), "C4": ("U1", "23"),
        "C34": ("U1", "45"), "C35": ("U1", "44"), "C36": ("U1", "38"), "C37": ("U1", "37"), "R13": ("U1", "55"),
        "R1": ("J1", "A5"), "R2": ("J1", "B5"), "C5": ("J1", "A4"), "C6": ("J1", "B9"),
        # SSD buck: around U2
        "R14": ("U2", "1"), "C38": ("U2", "2"), "C39": ("U2", "8"), "R15": ("U2", "6"), "R16": ("U2", "6"),
        "C40": ("U2", "4"), "C42": ("U2", "5"),
        # M.2 3.3 V pins
        "C43": ("J2", "2"), "C44": ("J2", "12"), "C45": ("J2", "70"), "C46": ("J2", "74"),
        "R10": ("U3", "1"), "R11": ("U3", "3"), "R12": ("U3", "7"), "C33": ("U3", "8"), "R9": ("LED1", "2")}
# ---------------------------------------------------------------- board
board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = mm(0.09)
ds.m_MinClearance = mm(0.09)
ds.m_ViasMinSize = mm(0.35)
ds.m_MinThroughDrill = mm(0.2)
ds.m_CopperEdgeClearance = mm(0.3)
ds.m_HoleClearance = mm(0.2)
ds.m_HoleToHoleMin = mm(0.2)
ds.m_ViasMinAnnularWidth = mm(0.075)
ds.SetBoardThickness(mm(1.6))
nc = ds.m_NetSettings.GetDefaultNetclass()
nc.SetTrackWidth(mm(0.15))
nc.SetClearance(mm(0.1))
nc.SetViaDiameter(mm(0.4))
nc.SetViaDrill(mm(0.2))

netinfo = {}


def net(name):
    if name not in netinfo:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        netinfo[name] = n
    return netinfo[name]


for ref, c in sorted(comps.items()):
    if not c["fp"]:
        continue
    lib, name = c["fp"].split(":")
    path = os.path.join(HW, "lib", "cartouche.pretty") if lib == "cartouche" else os.path.join(KFP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        sys.exit(f"footprint not found: {c['fp']}")
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    fp.SetFPIDAsString(c["fp"])
    if ref in ("R7", "R8"):
        fp.SetDNP(True)
    if ref.startswith("H"):
        fp.SetExcludedFromBOM(True)
    x, y, rot = PLACE.get(ref, (W / 2, H + 20, 0))
    board.Add(fp)
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    for pad in fp.Pads():
        n = nets.get((ref, pad.GetNumber()))
        if n:
            pad.SetNet(net(n))

# ---------------------------------------------------------------- automatic placement of the small parts
fps = {f.GetReference(): f for f in board.GetFootprints()}
SSD = (JX - 11.3, 5.0, JX + 11.3, 36.0)          # SSD shadow: only parts lower than 2.5 mm
TALL = {"C41", "J1"}
occupied = []
placed_done = set()


def box(f, margin=0.25):
    bb = f.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetLeft()) - margin, pcbnew.ToMM(bb.GetTop()) - margin,
            pcbnew.ToMM(bb.GetRight()) + margin, pcbnew.ToMM(bb.GetBottom()) + margin)


def free(b):
    if b[0] < 0.4 or b[1] < 0.4 or b[2] > W - 0.4 or b[3] > H - 0.4:
        return False
    if b[1] < 8.5 and b[3] > 3.0 and b[0] < JX + 3 and b[2] > JX - 3:   # keep the standoff clear
        return False
    if b[3] > 27.3 and b[1] < 32.4 and b[0] < 28.8 and b[2] > 19.8:      # PCIe channel: kept for the pairs
        return False
    if b[2] > 8.8 and b[0] < 20.0 and b[3] > 20.2 and b[1] < 28.2:       # USB channel: kept for the pairs
        return False
    return all(b[2] <= o[0] or b[0] >= o[2] or b[3] <= o[1] or b[1] >= o[3] for o in occupied)


for r in BIG:
    occupied.append(box(fps[r], 0.3))


def pad_xy(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == num:
            return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)


def anchor(ref):
    if ref in NEAR:
        return pad_xy(*NEAR[ref]), NEAR[ref][0]
    best = None
    for p in fps[ref].Pads():
        n = p.GetNetname()
        if not n or n in ("/GND",):
            continue
        for big in BIG:
            for q in fps[big].Pads():
                if q.GetNetname() == n:
                    d = (pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y))
                    if best is None or big == "U1":
                        best = (d, big)
                    break
    return best if best else ((W / 2, 45.0), "U1")


def place_small(ref):
    f = fps[ref]
    (ax, ay), big = anchor(ref)
    if big not in BIG and big not in placed_done:
        sys.exit(f'{ref} anchors on {big} before it is placed')
    c = f.GetPosition() if False else None
    bc = fps[big].GetPosition()
    cx, cy = pcbnew.ToMM(bc.x), pcbnew.ToMM(bc.y)
    dx, dy = ax - cx, ay - cy
    L = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    tx, ty = ax + dx / L * 2.2, ay + dy / L * 2.2
    for rad in [i * 0.25 for i in range(0, 120)]:
        steps = max(1, int(rad * 8))
        for k in range(steps):
            import math
            t = 2 * math.pi * k / steps
            for rot in (0, 90):
                x, y = round((tx + rad * math.cos(t)) * 4) / 4, round((ty + rad * math.sin(t)) * 4) / 4
                f.SetOrientationDegrees(rot)
                f.SetPosition(P(x, y))
                b = box(f)
                if ref in TALL and not (b[2] <= SSD[0] or b[0] >= SSD[2] or b[3] <= SSD[1] or b[1] >= SSD[3]):
                    continue
                if free(b):
                    occupied.append(b)
                    placed_done.add(ref)
                    return
    sys.exit(f"no room for {ref}")


FIRST = ["Y1", "U3", "L1", "LED1"]
order = FIRST + [r for r in NEAR if r not in FIRST] + sorted(r for r in fps if r not in BIG and r not in NEAR)
for r in order:
    place_small(r)

# ---------------------------------------------------------------- PCIe pairs, routed by hand (script)
# The chip's PCIe side and the socket's PCIe pins are in the same order (RX1, TX1,
# RX0, TX0, REFCLK; N then P), so each line goes straight down with one small jog.
# The 1.0 V pins and REXT between the pairs escape inwards, to vias in the ring
# between the pins and the exposed pad. TX lines get their 220 nF caps in line,
# N and P caps staggered so the other line of the pair passes beside them.
def pad_of(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == num:
            return p


def track(a, b, netname, w=0.2, layer=pcbnew.F_Cu):
    if abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3:
        return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(P(*a)); t.SetEnd(P(*b)); t.SetWidth(mm(w)); t.SetLayer(layer)
    t.SetNet(net(netname)); t.SetLocked(True)
    board.Add(t)


def via(x, y, netname, d=0.4, drill=0.2, locked=True):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y)); v.SetWidth(mm(d)); v.SetDrill(mm(drill)); v.SetNet(net(netname)); v.SetLocked(locked)
    board.Add(v)


def xy(p):
    return pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)


ucx, ucy = xy(fps["U1"])
PAIRS = [("34", "29"), ("35", "31"), ("37", "35"), ("38", "37"), ("41", "41"), ("42", "43"),
         ("44", "47"), ("45", "49"), ("47", "53"), ("48", "55")]   # (U1 pin, J2 pin)
CAPS = {"37": ("C37", 0), "38": ("C36", 1), "44": ("C35", 0), "45": ("C34", 1)}   # TX lines: cap, stagger row
yj = xy(pad_of("J2", "29"))[1]
y0 = xy(pad_of("U1", "34"))[1] + 0.45            # just past the chip pads
yjog = y0 + 0.55
ycap = [yjog + 0.6, yjog + 2.05]
for up, jp in PAIRS:
    a, b = pad_of("U1", up), pad_of("J2", jp)
    (xa, ya), (xb, yb) = xy(a), xy(b)
    n = a.GetNetname()
    track((xa, ya), (xa, y0), n)
    track((xa, y0), (xb, yjog), n)
    if up in CAPS:
        ref, row = CAPS[up]
        c = fps[ref]
        c.SetOrientationDegrees(90)
        c.SetPosition(P(xb, ycap[row]))
        p1, p2 = sorted([q for q in c.Pads() if q.GetNumber() in ('1', '2')], key=lambda p: pcbnew.ToMM(p.GetPosition().y))
        if p1.GetNetname() != n:                  # pad 1 must face the chip
            c.SetOrientationDegrees(270)
            p1, p2 = sorted([q for q in c.Pads() if q.GetNumber() in ('1', '2')], key=lambda p: pcbnew.ToMM(p.GetPosition().y))
        track((xb, yjog), xy(p1), n)
        track(xy(p2), (xb, yb), p2.GetNetname())
    else:
        track((xb, yjog), (xb, yb), n)

# 1.0 V pins and REXT on the PCIe side: short stub inwards to a via in the ring
for num, off in (("33", 3.1), ("36", 2.75), ("39", 3.1), ("40", 2.75), ("43", 2.75), ("46", 2.75)):
    p = pad_of("U1", num)
    x, y = xy(p)
    vy = ucy + off
    track((x, y), (x, vy), p.GetNetname(), 0.15)
    via(x, vy, p.GetNetname())


# ---------------------------------------------------------------- USB 3.2 pairs, routed by the script
# USB-C rows: A (inner, towards the chip) and B (outer). A B-row pad is reached through a
# via placed exactly between the two rows (0.6 mm gap: 0.4 mm via + 0.1 mm each side).
# TX1 and RX2 go straight to the A row on F.Cu; TX2 and RX1 cross each other, so they
# drop to B.Cu (over the In2 ground plane) and come up at their B-row vias.
jx = xy(fps["J1"])[0]
def jpad(n):
    return xy(pad_of("J1", n))
BETWEEN = 0.65                                     # from a B pad towards the A row
for n in ["B1", "B12", "B4", "B9", "B5", "B6", "B7", "B10", "B11", "B2", "B3"]:
    x, y = jpad(n)
    netn = pad_of("J1", n).GetNetname()
    track((x, y), (x + BETWEEN, y), netn, 0.2)
    via(x + BETWEEN, y, netn)
for a_, b_ in (("A1", "B12"), ("A12", "B1"), ("A4", "B9"), ("A9", "B4")):   # A-row ground / VBUS:
    xa_, ya_ = jpad(a_)                              # joined to the via of the facing B-row pad
    xb_, yb_ = jpad(b_)
    track((xa_, ya_), (xb_ + BETWEEN, yb_), pad_of("J1", a_).GetNetname(), 0.2)

for n_, vx_ in (("A5", 9.35), ("A6", 9.95), ("A7", 9.35)):   # CC1, D+, D-: vias towards the chip, staggered
    x_, y_ = jpad(n_)
    netn = pad_of("J1", n_).GetNetname()
    track((x_, y_), (vx_, y_), netn, 0.2)
    via(vx_, y_, netn, locked=False)


def u(n):
    return xy(pad_of("U1", n))


def place_cap(ref, x, y, net_in):
    c = fps[ref]
    c.SetOrientationDegrees(0)
    c.SetPosition(P(x, y))
    q = sorted([p for p in c.Pads() if p.GetNumber() in ("1", "2")], key=lambda p: -pcbnew.ToMM(p.GetPosition().x))
    if q[0].GetNetname() != net_in:
        c.SetOrientationDegrees(180)
        q = sorted([p for p in c.Pads() if p.GetNumber() in ("1", "2")], key=lambda p: -pcbnew.ToMM(p.GetPosition().x))
    return xy(q[0]), xy(q[1]), q[1].GetNetname()     # pad towards the chip, pad towards the connector


# Impedance: on the JLC04161H-7628 stack (0.21 mm to the ground plane, er ~4.4), IPC-2141 gives
# ~94 ohm differential for 0.20 mm tracks 0.10 mm apart (target 90 ohm +-10 %). So the long runs
# are tightened to 0.30 mm centre to centre; they open up only at the caps and the pads.
def poly_track(pts, netname, layer=pcbnew.F_Cu, w=0.2):
    for p0, p1 in zip(pts, pts[1:]):
        track(p0, p1, netname, w, layer)


# TX1: chip 21 (P) / 22 (N) -> C1 / C2 -> A2 / A3 on F.Cu
(xp, yp), (xn, yn) = u("21"), u("22")
nP, nN = pad_of("U1", "21").GetNetname(), pad_of("U1", "22").GetNetname()
pinP_in, pinP_out, nP2 = place_cap("C1", 17.2, yp, nP)
pinN_in, pinN_out, nN2 = place_cap("C2", 15.8, yn, nN)
track((xp, yp), pinP_in, nP)
track((xn, yn), pinN_in, nN)
(xa2, ya2), (xa3, ya3) = jpad("A2"), jpad("A3")
yc = (yp + yn) / 2
poly_track([pinP_out, (15.0, yp), (14.95, yc - 0.15), (10.6, yc - 0.15), (10.6 - abs(yc - 0.15 - ya2), ya2), (xa2, ya2)], nP2)
poly_track([pinN_out, (15.0, yn), (14.95, yc + 0.15), (10.6, yc + 0.15), (10.6 - abs(yc + 0.15 - ya3), ya3), (xa3, ya3)], nN2)

# TX2: chip 23 (N) / 24 (P) -> C4 / C3 -> F.Cu, 45 degree step, vias -> B.Cu -> B3 / B2 vias
tx2 = {}
for pin, cap, cx, dy, vx, jx0 in (("23", "C4", 17.2, 0.7, 11.0, 14.8), ("24", "C3", 15.8, 0.7, 11.6, 14.97)):
    (xa, ya) = u(pin)
    n = pad_of("U1", pin).GetNetname()
    pin_in, pin_out, n2 = place_cap(cap, cx, ya, n)
    track((xa, ya), pin_in, n)
    poly_track([pin_out, (jx0, ya), (jx0 - dy, ya + dy), (vx, ya + dy)], n2)
    via(vx, ya + dy, n2)
    tx2[pin] = (vx, ya + dy, n2)
(vxn, vyn, nn), (vxp, vyp, np_) = tx2["23"], tx2["24"]
(xb3, yb3), (xb2, yb2) = jpad("B3"), jpad("B2")
ym = (yb3 + yb2) / 2
poly_track([(vxn, vyn), (11.15, vyn + 0.15), (11.15, ym - 0.15), (8.2, ym - 0.15), (8.2 - 0.1, yb3), (xb3 + BETWEEN, yb3)], nn, pcbnew.B_Cu)
poly_track([(vxp, vyp), (11.45, vyp + 0.15), (11.45, ym + 0.15), (8.2, ym + 0.15), (8.2 - 0.1, yb2), (xb2 + BETWEEN, yb2)], np_, pcbnew.B_Cu)

# RX1: chip 26 (P) / 27 (N) -> vias -> B.Cu up and left -> B11 / B10 vias
(xp, yp), (xn, yn) = u("26"), u("27")
nP, nN = pad_of("U1", "26").GetNetname(), pad_of("U1", "27").GetNetname()
track((xp, yp), (16.6, yp), nP); via(16.6, yp, nP)
track((xn, yn), (16.0, yn), nN); via(16.0, yn, nN)
(xb11, yb11), (xb10, yb10) = jpad("B11"), jpad("B10")
ym = (yb11 + yb10) / 2
poly_track([(16.6, yp), (16.45, yp - 0.15), (16.45, ym - 0.15), (8.2, ym - 0.15), (8.1, yb11), (xb11 + BETWEEN, yb11)], nP, pcbnew.B_Cu)
poly_track([(16.0, yn), (16.15, yn - 0.15), (16.15, ym + 0.15), (8.2, ym + 0.15), (8.1, yb10), (xb10 + BETWEEN, yb10)], nN, pcbnew.B_Cu)

# RX2: chip 28 (N) / 29 (P) -> A10 / A11 on F.Cu, square corners
(xn, yn), (xp, yp) = u("28"), u("29")
nN, nP = pad_of("U1", "28").GetNetname(), pad_of("U1", "29").GetNetname()
(xa10, ya10), (xa11, ya11) = jpad("A10"), jpad("A11")
ym = (ya10 + ya11) / 2
poly_track([(xn, yn), (17.7, yn), (17.7, ym - 0.15), (8.9, ym - 0.15), (8.9 - abs(ym - 0.15 - ya10), ya10), (xa10, ya10)], nN)
poly_track([(xp, yp), (18.0, yp), (18.0, ym + 0.15), (8.9, ym + 0.15), (8.9 - abs(ym + 0.15 - ya11), ya11), (xa11, ya11)], nP)

# power pins on the USB side: stubs inwards to ring vias (staggered)
for num, off in (("19", 3.1), ("20", 2.75), ("25", 2.75), ("30", 3.1), ("31", 2.75)):   # (33 is below, at 3.1)
    p = pad_of("U1", num)
    x, y = xy(p)
    vx = ucx - off
    track((x, y), (vx, y), p.GetNetname(), 0.15)
    via(vx, y, p.GetNetname())
# VCCO (pin 32, corner of the USB side): via just outside the pad, clear of the RX2 pair
p = pad_of("U1", "32")
x, y = xy(p)
track((x, y), (x - 1.14, y + 0.2), p.GetNetname(), 0.15)
via(x - 1.14, y + 0.2, p.GetNetname())

# outline with rounded corners
R = 1.5


def seg(a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    board.Add(s)


def arc(c, start, ang):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetCenter(P(*c))
    s.SetStart(P(*start))
    s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    board.Add(s)


seg((R, 0), (W - R, 0)); seg((W, R), (W, H - R)); seg((W - R, H), (R, H)); seg((0, H - R), (0, R))
arc((W - R, R), (W - R, 0), 90); arc((W - R, H - R), (W, H - R), 90); arc((R, H - R), (R, H), 90); arc((R, R), (0, R), 90)

# planes: In1 = solid GND (reference for the 10 Gb/s pairs on F.Cu),
# In2 = power plane split in two: +3V3 for the SSD (top) and VBUS (bottom)
board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)


def plane(layer, netname, y0, y1, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(netname))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((0.3, y0), (W - 0.3, y0), (W - 0.3, y1), (0.3, y1)):
        ol.Append(mm(x), mm(y))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetLocalClearance(mm(0.15))
    z.SetAssignedPriority(prio)
    board.Add(z)


plane(pcbnew.In1_Cu, "/GND", 0.3, H - 0.3)

# In2: VBUS in the bottom part and in a strip up the right edge to the regulator
# input; +3V3 (SSD) everywhere else. The strip edge falls between U2's VIN and VOUT pads.
u2 = {p.GetNumber(): pcbnew.ToMM(p.GetPosition().x) for p in fps["U2"].Pads()}
XB = round((u2["2"] + min(u2["4"], u2["5"])) / 2, 2)
if not u2["2"] < min(u2["4"], u2["5"]) - 0.3:
    sys.exit(f"U2 rotation: VIN {u2['2']} must be left of VOUT {u2['4']},{u2['5']}")


def poly(layer, netname, pts, prio):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(netname))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(x), mm(y))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetLocalClearance(mm(0.15))
    z.SetAssignedPriority(prio)
    board.Add(z)


plane(pcbnew.In2_Cu, "/GND", 0.3, H - 0.3)

# +1.0 V island on In2 right under the JMS583 (inside the In2 ground plane): every 1.0 V
# via lands on it, and no track can cut it (In2 is a plane layer, not routed)
z = pcbnew.ZONE(board)
z.SetLayer(pcbnew.In2_Cu)
z.SetNet(net("/+1V0"))
ol = z.Outline()
ol.NewOutline()
R1V = (ucx - 6.4, ucy - 6.4, ucx + 6.4, ucy + 6.4)
for x, y in ((R1V[0], R1V[1]), (R1V[2], R1V[1]), (R1V[2], R1V[3]), (R1V[0], R1V[3])):
    ol.Append(mm(x), mm(y))
z.SetMinThickness(mm(0.2))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
z.SetLocalClearance(mm(0.15))
z.SetAssignedPriority(2)
board.Add(z)


def region_ok(netname, x, y):
    if netname == "/GND":
        return True
    if netname == "/+1V0":
        return R1V[0] + 0.4 < x < R1V[2] - 0.4 and R1V[1] + 0.4 < y < R1V[3] - 0.4
    in_vbus = x < XB - 0.5
    in_3v3 = x > XB + 0.5
    return in_vbus if netname == "/VBUS" else in_3v3


# fanout: a via next to every pad of a plane net (GND, VBUS, +3V3), thermal vias in exposed pads
allpads = [p for f in board.GetFootprints() for p in f.Pads()]
vias = []


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def clear_of_tracks(x, y, netname, r):
    for t in board.GetTracks():
        if t.GetNetname() == netname:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            vx, vy = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
            if ((x - vx) ** 2 + (y - vy) ** 2) ** 0.5 < r + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.1:
                return False
            continue
        a, b = t.GetStart(), t.GetEnd()
        if seg_dist(x, y, pcbnew.ToMM(a.x), pcbnew.ToMM(a.y), pcbnew.ToMM(b.x), pcbnew.ToMM(b.y)) < r + pcbnew.ToMM(t.GetWidth()) / 2 + 0.1:
            return False
    return True


def clear_of_pads(x, y, netname, r=0.45):
    for p in allpads:
        if p.GetNetname() == netname:
            continue
        bb = p.GetBoundingBox()
        if (pcbnew.ToMM(bb.GetLeft()) - r < x < pcbnew.ToMM(bb.GetRight()) + r and
                pcbnew.ToMM(bb.GetTop()) - r < y < pcbnew.ToMM(bb.GetBottom()) + r):
            return False
    return all((x - vx) ** 2 + (y - vy) ** 2 > 0.6 ** 2 for vx, vy, _ in vias) and 0.8 < x < W - 0.8 and 0.8 < y < H - 0.8


def add_via(x, y, netname, pad=None, tw=0.25):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetWidth(mm(0.4))
    v.SetDrill(mm(0.2))
    v.SetNet(net(netname))
    board.Add(v)
    vias.append((x, y, netname))
    if pad is not None:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pad.GetPosition())
        t.SetEnd(P(x, y))
        t.SetWidth(mm(tw))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(net(netname))
        board.Add(t)


import math
for f in board.GetFootprints():
    fc = f.GetPosition()
    if f.GetReference() == "J1":
        continue
    for p in f.Pads():
        n = p.GetNetname()
        if n not in ("/GND", "/VBUS", "/+3V3", "/+1V0") or p.GetAttribute() not in (pcbnew.PAD_ATTRIB_SMD,):
            continue
        if f.GetReference() == "U1" and p.GetNumber() in ("20", "25", "30", "31", "33", "36", "40", "43", "46"):   # ring vias
            continue
        px, py = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
        sx, sy = pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)
        if sx > 2.0 and sy > 2.0:                       # exposed pad: thermal vias inside it
            for dx in (-0.8, 0.8):
                for dy in (-0.8, 0.8):
                    if sx > 3.5:
                        add_via(px + dx, py + dy, n)
                    elif dx < 0 and dy < 0:
                        add_via(px, py, n)
            continue
        if any(abs(vx - px) < 1.2 and abs(vy - py) < 1.2 and vn == n for vx, vy, vn in vias):
            continue
        dx, dy = px - pcbnew.ToMM(fc.x), py - pcbnew.ToMM(fc.y)
        fine = min(sx, sy) < 0.5
        if fine:                                     # fine pitch: straight out, perpendicular to the row
            if f.GetReference() == "J1":
                angles = [0.0]                       # USB-C: into the board, away from the mouth
            else:                                    # along the pad's long axis, away from the part
                ang = p.GetOrientation().AsDegrees()
                lx, ly = (sx, sy)
                vertical = (ly > lx) != (round(ang) % 180 == 90)
                if vertical:
                    angles = [math.pi / 2 if dy > 0 else -math.pi / 2]
                else:
                    angles = [0 if dx > 0 else math.pi]
            dists = (0.9, 1.1, 1.4, 1.8, 2.2)
        else:
            base = math.atan2(dy, dx) if (dx or dy) else 0
            angles = [base + (k // 2) * (math.pi / 6) * (1 if k % 2 else -1) for k in range(12)]
            dists = (0.75, 0.95, 1.2, 1.5, 1.9, 2.4)
        done = False
        for d in dists:
            for a in angles:
                x, y = round(px + d * math.cos(a), 2), round(py + d * math.sin(a), 2)
                tw = 0.18 if fine else 0.25
                stub_ok = all(clear_of_tracks(px + (x - px) * k, py + (y - py) * k, n, tw / 2) and
                              (k < 0.25 or clear_of_pads(px + (x - px) * k, py + (y - py) * k, n, tw / 2 + 0.12)) for k in (0.3, 0.45, 0.6, 0.8, 1.0))
                if region_ok(n, x, y) and clear_of_pads(x, y, n) and clear_of_tracks(x, y, n, 0.2) and stub_ok:
                    add_via(x, y, n, p, tw)
                    done = True
                    break
            if done:
                break

# small silkscreen text; references of passives only on the fab layer
for f in board.GetFootprints():
    t = f.Reference()
    t.SetTextSize(P(0.8, 0.8)); t.SetTextThickness(mm(0.12))
    f.Value().SetVisible(False)
    if f.GetReference()[0] in "RC" and not f.GetReference().startswith("CE"):
        t.SetLayer(pcbnew.F_Fab)

board.Save(OUT)
print(f"{len(comps)} parts placed, {len(netinfo)} nets, board {W} x {H} mm, 4 layers -> {OUT}")
