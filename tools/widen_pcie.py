"""Widens the straight PCIe and REFCLK pair sections to 0.30 mm (KiCad 9 Python).

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\widen_pcie.py

These pairs run at the M.2 contact pitch (0.5 mm between centres). At 0.20 mm wide they
leave a 0.30 mm gap: about 114 ohm differential on JLC04161H-7628 (tools/impedance.py).
At 0.30 mm wide on the same centres the gap is 0.20 mm: about 89 ohm (PCIe: 85 ohm ±15 %).
Only the segments that run parallel to their partner at that pitch are changed.
"""
import math
import os
import pcbnew

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware")
PCB = os.path.join(HW, "cartouche-drive.kicad_pcb")
PAIRS = ("/PCIE_RX", "/PCIE_TX", "/REFCLK_")
board = pcbnew.LoadBoard(PCB)
segs = {}
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname().startswith(PAIRS):
        segs.setdefault(t.GetNetname(), []).append(t)


def partner(n):
    for i in range(len(n) - 1, 0, -1):
        for a, b in (("P", "N"), ("N", "P")):
            if n[i] == a and n[:i] + b + n[i + 1:] in segs:
                return n[:i] + b + n[i + 1:]


def dist(p, t):
    a, c = t.GetStart(), t.GetEnd()
    ax, ay, bx, by = a.x / 1e6, a.y / 1e6, c.x / 1e6, c.y / 1e6
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - ax - u * dx, p[1] - ay - u * dy)


n_w = 0
for n, ts in segs.items():
    m = partner(n)
    if not m:
        continue
    for t in ts:
        mates = [u for u in segs[m] if u.GetLayer() == t.GetLayer()]
        s, e = t.GetStart(), t.GetEnd()
        pts = [((s.x * (1 - k) + e.x * k) / 1e6, (s.y * (1 - k) + e.y * k) / 1e6) for k in (0.1, 0.5, 0.9)]
        # the whole segment must sit at 0.5 mm centre to centre from its partner
        if mates and all(abs(min(dist(p, u) for u in mates) - 0.5) < 0.02 for p in pts):
            t.SetWidth(pcbnew.FromMM(0.30))
            n_w += 1
print("segments widened:", n_w)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
