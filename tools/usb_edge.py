"""Moves the board's left edge so the USB-C receptacle face sits at the board edge
(KiCad 9 Python).

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\usb_edge.py

The Molex 105450-0101 footprint marks the PCB edge 4.325 mm in front of its origin
(Dwgs.User "PCB Edge"); with J1 at x = 5.0 mm and rotated -90°, that is x = 0.675 mm.
The left edge was at x = 0, so the board stuck out 0.675 mm in front of the receptacle
and a plug's overmould would hit it. The whole outline (and the pours) moves right by
that amount, so the board stays 36 x 46 mm; zones are refilled. Run it once.
"""
import os
import pcbnew

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware")
PCB = os.path.join(HW, "cartouche-drive.kicad_pcb")
X0 = 0.675                      # new left edge, mm
mm, um = pcbnew.ToMM, pcbnew.FromMM
b = pcbnew.LoadBoard(PCB)
for d in b.GetDrawings():                       # the whole outline moves right by X0
    if d.GetLayer() == pcbnew.Edge_Cuts:
        d.Move(pcbnew.VECTOR2I(um(X0), 0))
for z in b.Zones():                            # only the pour edges that follow the outline
    ol = z.Outline()
    for i in range(ol.TotalVertices()):
        v = ol.CVertex(i)
        if mm(v.x) < 1.0 or mm(v.x) > 35.0:
            ol.SetVertex(i, pcbnew.VECTOR2I(v.x + um(X0), v.y))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB)
print("left edge moved to x =", X0)
