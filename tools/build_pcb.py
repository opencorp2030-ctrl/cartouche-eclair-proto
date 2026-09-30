"""Builds hardware/cartouche-drive.kicad_pcb from the schematic netlist (KiCad 9 Python).

Run with KiCad's own Python (it has pcbnew):
  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\build_pcb.py
Steps: read the netlist, load every footprint, place it, assign the nets,
draw the outline, set the 4-layer stack and design rules, add the ground
planes, then export a Specctra DSN for Freerouting.

Board frame (mm, KiCad y goes down): 30 x 66 mm. The M.2 2230 SSD lies over
the top part of the board (on its 4.75 mm connector and an M2 standoff), the
JMS583 sits under the connector, the USB-C receptacle is on the bottom edge.
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
W, H = 30.0, 66.0

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
PLACE = {
    "J2": (15.0, 34.25, 0),      # M.2 socket; card edge at y 34.0, SSD up to y 4.0
    "U1": (15.0, 50.0, 90),      # JMS583: PCIe side faces the socket
    "J1": (15.0, 61.2, 0),       # USB-C on the bottom edge
    "U2": (25.2, 22.0, 270),      # SSD 3.3 V buck (VIN pads towards the right edge / VBUS strip)
    "C41": (25.0, 58.5, 90),     # 330 uF tantalum (3.1 mm tall: outside the SSD shadow)
    "H1": (15.0, 4.0, 0),        # M2 standoff at the far end of a 2230 card
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
nc.SetClearance(mm(0.13))
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
SSD = (3.5, 3.0, 26.5, 34.0)                     # SSD shadow: only parts lower than 2.5 mm
TALL = {"C41"}
occupied = []
placed_done = set()


def box(f, margin=0.25):
    bb = f.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetLeft()) - margin, pcbnew.ToMM(bb.GetTop()) - margin,
            pcbnew.ToMM(bb.GetRight()) + margin, pcbnew.ToMM(bb.GetBottom()) + margin)


def free(b):
    if b[0] < 0.4 or b[1] < 0.4 or b[2] > W - 0.4 or b[3] > H - 0.4:
        return False
    if b[1] < 5.5 and b[3] > 2.0 and b[0] < 18 and b[2] > 12:   # keep the standoff clear
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
    z.SetLocalClearance(mm(0.25))
    z.SetAssignedPriority(prio)
    board.Add(z)


plane(pcbnew.In1_Cu, "/GND", 0.3, H - 0.3)

# In2: VBUS in the bottom part and in a strip up the right edge to the regulator
# input; +3V3 (SSD) everywhere else. The strip edge falls between U2's VIN and VOUT pads.
u2 = {p.GetNumber(): pcbnew.ToMM(p.GetPosition().x) for p in fps["U2"].Pads()}
XB = round((u2["2"] + max(u2["4"], u2["5"])) / 2, 2)
if not u2["2"] > max(u2["4"], u2["5"]) + 0.3:
    sys.exit(f"U2 rotation: VIN {u2['2']} must be right of VOUT {u2['4']},{u2['5']}")


def poly(layer, netname, pts, prio):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(netname))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(x), mm(y))
    z.SetMinThickness(mm(0.2))
    z.SetLocalClearance(mm(0.25))
    z.SetAssignedPriority(prio)
    board.Add(z)


YV = 44.0
poly(pcbnew.In2_Cu, "/VBUS", [(0.3, YV), (XB + 0.2, YV), (XB + 0.2, 12.0), (W - 0.3, 12.0), (W - 0.3, H - 0.3), (0.3, H - 0.3)], 1)
poly(pcbnew.In2_Cu, "/+3V3", [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, 11.6), (XB - 0.2, 11.6), (XB - 0.2, YV - 0.4), (0.3, YV - 0.4)], 1)


def region_ok(netname, x, y):
    if netname == "/GND":
        return True
    in_vbus = y > YV + 0.3 or (x > XB + 0.5 and 12.3 < y < YV - 0.3)
    in_3v3 = (y < YV - 0.7 and x < XB - 0.5) or y < 11.3
    return in_vbus if netname == "/VBUS" else in_3v3


# fanout: a via next to every pad of a plane net (GND, VBUS, +3V3), thermal vias in exposed pads
allpads = [p for f in board.GetFootprints() for p in f.Pads()]
vias = []


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
    for p in f.Pads():
        n = p.GetNetname()
        if n not in ("/GND", "/VBUS", "/+3V3") or p.GetAttribute() not in (pcbnew.PAD_ATTRIB_SMD,):
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
                angles = [-math.pi / 2]              # USB-C: into the board, away from the mouth
            elif abs(dx) > abs(dy):
                angles = [0 if dx > 0 else math.pi]
            else:
                angles = [math.pi / 2 if dy > 0 else -math.pi / 2]
            dists = (0.9, 1.1, 1.4, 1.8, 2.2)
        else:
            base = math.atan2(dy, dx) if (dx or dy) else 0
            angles = [base + (k // 2) * (math.pi / 6) * (1 if k % 2 else -1) for k in range(12)]
            dists = (0.75, 0.95, 1.2, 1.5)
        done = False
        for d in dists:
            for a in angles:
                x, y = round(px + d * math.cos(a), 2), round(py + d * math.sin(a), 2)
                if region_ok(n, x, y) and clear_of_pads(x, y, n):
                    add_via(x, y, n, p, 0.18 if fine else 0.25)
                    done = True
                    break
            if done:
                break

# small silkscreen text; references of passives only on the fab layer
for f in board.GetFootprints():
    t = f.Reference()
    t.SetTextSize(P(0.6, 0.6)); t.SetTextThickness(mm(0.1))
    f.Value().SetVisible(False)
    if f.GetReference()[0] in "RC" and not f.GetReference().startswith("CE"):
        t.SetLayer(pcbnew.F_Fab)

board.Save(OUT)
print(f"{len(comps)} parts placed, {len(netinfo)} nets, board {W} x {H} mm, 4 layers -> {OUT}")
