"""Last-mile fixes after routing: moves a fan-out via a little away from a track that is
too close to its hole (its stub follows), and removes a dangling via with its stub.

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\nudge_pcb.py hardware\\drc.rpt
"""
import math
import os
import re
import sys
import pcbnew

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware")
PCB = os.path.join(HW, "cartouche-drive.kicad_pcb")
rpt = open(sys.argv[1], encoding="utf8").read()
board = pcbnew.LoadBoard(PCB)
tracks = list(board.GetTracks())


def at(x, y, kind):
    for t in tracks:
        p = t.GetPosition() if kind == "via" else t.GetStart()
        if (t.Type() == pcbnew.PCB_VIA_T) == (kind == "via") and abs(p.x / 1e6 - x) < 0.02 and abs(p.y / 1e6 - y) < 0.02:
            return t


moved = removed = 0
for block in re.split(r"\n(?=\[)", rpt):
    if block.startswith("[hole_clearance]"):
        need = 0.2 - float(re.search(r"réel ([\d.]+) mm|actual ([\d.]+) mm", block).group(1) or 0) + 0.03
        tr = re.search(r"@\(([\d.]+) mm, ([\d.]+) mm\): (?:Piste|Track)", block)
        vi = re.search(r"@\(([\d.]+) mm, ([\d.]+) mm\): Via", block)
        t, v = at(float(tr.group(1)), float(tr.group(2)), "track"), at(float(vi.group(1)), float(vi.group(2)), "via")
        if not (t and v):
            continue
        vx, vy = v.GetPosition().x / 1e6, v.GetPosition().y / 1e6
        ax, ay, bx, by = t.GetStart().x / 1e6, t.GetStart().y / 1e6, t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
        dx, dy = bx - ax, by - ay
        k = max(0, min(1, ((vx - ax) * dx + (vy - ay) * dy) / (dx * dx + dy * dy)))
        nx, ny = vx - (ax + k * dx), vy - (ay + k * dy)
        L = math.hypot(nx, ny) or 1
        new = pcbnew.VECTOR2I(int((vx + nx / L * need) * 1e6), int((vy + ny / L * need) * 1e6))
        old = v.GetPosition()
        for s in tracks:                              # the stub that ends on the via follows it
            if s.Type() != pcbnew.PCB_VIA_T and s.GetNetCode() == v.GetNetCode():
                if s.GetEnd() == old:
                    s.SetEnd(new)
                if s.GetStart() == old:
                    s.SetStart(new)
        v.SetPosition(new)
        moved += 1
    if block.startswith("[via_dangling]"):
        vi = re.search(r"@\(([\d.]+) mm, ([\d.]+) mm\): Via", block)
        v = at(float(vi.group(1)), float(vi.group(2)), "via")
        if v:
            old = v.GetPosition()
            for s in tracks:
                if s.Type() != pcbnew.PCB_VIA_T and s.GetNetCode() == v.GetNetCode() and (s.GetEnd() == old or s.GetStart() == old):
                    board.Remove(s)
            board.Remove(v)
            removed += 1
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("moved", moved, "vias, removed", removed)
