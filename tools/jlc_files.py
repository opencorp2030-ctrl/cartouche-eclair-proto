"""Turns KiCad's BOM and position exports into JLCPCB's formats and zips the Gerbers.

  python3 tools/jlc_files.py      (after the kicad-cli exports into hardware/fab/)
"""
import csv
import os
import re
import zipfile

FAB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hardware", "fab")


def expand(refs):
    out = []
    for part in refs.split(","):
        m = re.match(r"([A-Z]+)(\d+)-[A-Z]*(\d+)$", part.strip())
        if m:
            out += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif part.strip():
            out.append(part.strip())
    return out


rows = list(csv.DictReader(open(os.path.join(FAB, "bom-kicad.csv"), encoding="utf8")))
with open(os.path.join(FAB, "jlcpcb-bom.csv"), "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for r in rows:
        refs = [x for x in expand(r["Reference"]) if not x.startswith(("H", "#"))]
        if refs:
            w.writerow([r["Value"], ",".join(refs), r["Footprint"].split(":")[-1], r["LCSC"]])
pos = list(csv.DictReader(open(os.path.join(FAB, "positions.csv"), encoding="utf8")))
with open(os.path.join(FAB, "jlcpcb-cpl.csv"), "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for p in pos:
        if p["Ref"].startswith("H"):
            continue
        w.writerow([p["Ref"], p["PosX"] + "mm", p["PosY"] + "mm", "Top", p["Rot"]])
gdir = os.path.join(FAB, "gerbers")
with zipfile.ZipFile(os.path.join(FAB, "cartouche-drive-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for n in sorted(os.listdir(gdir)):
        z.write(os.path.join(gdir, n), n)
print(len(rows), "BOM lines,", len(pos), "placed parts, gerbers zipped")
