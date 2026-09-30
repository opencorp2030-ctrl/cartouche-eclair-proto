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
for d in list(board.GetDrawings()):                  # replace an earlier label
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetText().startswith("CARTOUCHE Drive"):
        board.Remove(d)
t = pcbnew.PCB_TEXT(board)
t.SetText("CARTOUCHE Drive v0.4")
t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
t.SetLayer(pcbnew.F_SilkS)
t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(43.5)))
t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9)))
t.SetTextThickness(pcbnew.FromMM(0.15))
board.Add(t)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("finished")
