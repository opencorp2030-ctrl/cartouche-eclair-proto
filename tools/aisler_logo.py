"""Adds the AISLER logo placeholder on the bottom silkscreen (KiCad 9 Python).

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\aisler_logo.py

AISLER replaces a rectangle made of four separate lines, 0.08382 mm (3.3 mil)
wide, 4:1 aspect ratio, long side 30-60 mm, with its logo when the board is
ordered from them (sponsorship). Other fabs print the empty outline.
Placed vertically along the right edge (bottom side): no holes or pads there. Idempotent.
"""
import os
import pcbnew

PCB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware", "cartouche-drive.kicad_pcb")
X0, Y0, W, H = 28.7, 1.6, 7.5, 30.0          # mm, 4:1, vertical
WIDTH = 0.08382
um = pcbnew.FromMM
b = pcbnew.LoadBoard(PCB)
for d in list(b.GetDrawings()):              # remove a previous placeholder
    if d.GetLayer() == pcbnew.B_SilkS and d.GetClass() == "PCB_SHAPE" and abs(pcbnew.ToMM(d.GetWidth()) - WIDTH) < 1e-4:
        b.Remove(d)
pts = [(X0, Y0), (X0 + W, Y0), (X0 + W, Y0 + H), (X0, Y0 + H)]
for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.B_SilkS)
    s.SetStart(pcbnew.VECTOR2I(um(x1), um(y1)))
    s.SetEnd(pcbnew.VECTOR2I(um(x2), um(y2)))
    s.SetWidth(um(WIDTH))
    b.Add(s)
b.Save(PCB)
print(f"AISLER placeholder: {W} x {H} mm at ({X0}, {Y0}) on B.Silkscreen")
