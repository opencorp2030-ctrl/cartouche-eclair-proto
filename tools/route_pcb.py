"""Routes hardware/cartouche-drive.kicad_pcb with Freerouting, then pours ground (KiCad 9 Python).

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\route_pcb.py <path to freerouting.jar>

Net classes: HS = 10 Gb/s USB and 8 Gb/s PCIe pairs (0.20 mm tracks), PWR = supplies
(0.40 mm), Default = the rest (0.15 mm). Pair widths are a first estimate for the JLC
4-layer stack: to be checked with JLCPCB's impedance calculator (90 ohm USB, 85 ohm PCIe).
"""
import os
import subprocess
import sys
import pcbnew

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware")
PCB = os.path.join(HW, "cartouche-drive.kicad_pcb")
JAR = sys.argv[1]
mm = pcbnew.FromMM

board = pcbnew.LoadBoard(PCB)
ns = board.GetDesignSettings().m_NetSettings


def netclass(name, width, clear, via=0.45, drill=0.2):
    nc = pcbnew.NETCLASS(name)
    nc.SetTrackWidth(mm(width))
    nc.SetClearance(mm(clear))
    nc.SetViaDiameter(mm(via))
    nc.SetViaDrill(mm(drill))
    ns.SetNetclass(name, nc)
    return nc


netclass("HS", 0.20, 0.10, 0.4, 0.2)
netclass("PWR", 0.25, 0.10, 0.5, 0.25)
HS = ("/USB_TX", "/USB_RX", "/U_TX", "/P_TX", "/PCIE_", "/REFCLK_", "/USB_DP", "/USB_DM")
PWR = ("/VBUS", "/+3V3", "/+1V0", "/LXO", "/+3V3_JMS")
for pat in HS:
    ns.SetNetclassPatternAssignment(pat + "*", "HS")
for pat in PWR:
    ns.SetNetclassPatternAssignment(pat, "PWR")
board.SynchronizeNetsAndNetClasses(True)

dsn = os.path.join(HW, "cartouche-drive.dsn")
ses = os.path.join(HW, "cartouche-drive.ses")
if not pcbnew.ExportSpecctraDSN(board, dsn):
    sys.exit("DSN export failed")
print("DSN exported, routing…", flush=True)
r = subprocess.run(["java", "-jar", JAR, "-de", dsn, "-do", ses, "-mp", "100", "-host-mode", "cli"],
                   capture_output=True, text=True, timeout=1500)
print(r.stdout[-1500:], r.stderr[-1500:])
if not os.path.exists(ses):
    sys.exit("no SES produced")
if not pcbnew.ImportSpecctraSES(board, ses):
    sys.exit("SES import failed")

# pours: F.Cu ground; B.Cu split in two, VBUS on the left (USB-C, regulator input) and
# +3V3 on the right (regulator output, M.2 supply pins); the boundary runs between U2's VIN and VOUT.
W, H = 36.0, 46.0
u2 = {p.GetNumber(): pcbnew.ToMM(p.GetPosition().x) for f in board.GetFootprints() if f.GetReference() == "U2" for p in f.Pads()}
XB = round((u2["2"] + min(u2["4"], u2["5"])) / 2, 2)


def pour(layer, netname, pts, prio):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(netname))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
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


pour(pcbnew.F_Cu, "/GND", [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)], 0)
pour(pcbnew.B_Cu, "/VBUS", [(0.3, 0.3), (XB - 0.2, 0.3), (XB - 0.2, H - 0.3), (0.3, H - 0.3)], 1)
pour(pcbnew.B_Cu, "/+3V3", [(XB + 0.2, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (XB + 0.2, H - 0.3)], 1)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("routed and saved", PCB)
