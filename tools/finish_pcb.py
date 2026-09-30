"""Final touches on the routed board: component references moved to the fab layer (no silk
text over pads), a small board label on the silkscreen, zones refilled.

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools\\finish_pcb.py
"""
import os
import pcbnew

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware")
PCB = os.path.join(HW, "cartouche-drive.kicad_pcb")
board = pcbnew.LoadBoard(PCB)
for f in board.GetFootprints():
    f.Reference().SetLayer(pcbnew.F_Fab)
t = pcbnew.PCB_TEXT(board)
t.SetText("CARTOUCHE Drive v0.3")
t.SetLayer(pcbnew.F_SilkS)
t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(4.8), pcbnew.FromMM(43.5)))
t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
t.SetTextThickness(pcbnew.FromMM(0.15))
board.Add(t)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("finished")
