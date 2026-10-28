"""One line from every font: proofs/family_overview.png"""
import sys, os, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from setline import render  # noqa: E402

ORDER = [("titling1", "ABCD"), ("titling2", "ABCDE"), ("titling3", "ABCDEFG"), ("titling4", "ABCDEFGHI"),
         ("titling5", "ABCDEFGHIJK"), ("titling6", "ABCDEFGHIJKL"), ("titling7", "ABCDEFGHIKLMN"),
         ("fc_roman", "Quouſque tandem"), ("fc_italic", "Quouſque tandem"),
         ("tlgp_roman", "Quouſque tandem abutere"), ("tlgp_italic", "Catilina, patientia"),
         ("tle_roman", "Quouſque tandem abutere, Catilina"), ("tle_italic", "Catilina patientia noſtra?"),
         ("dp_roman", "Quouſque tandem abutere, Catilina, patientia"), ("dp_italic", "Quouſque tandem abutere, Catilina"),
         ("gp_roman", "Quouſque tandem abutere, Catilina, patientia noſtra?"), ("gp_italic", "Quouſque tandem abutere, Catilina, patientia"),
         ("english_r", "Quouſque tandem abutere, Catilina, patientia noſtra? quamdiu"),
         ("english_i", "Quouſque tandem abutere, Catilina, patientia noſtra?"),
         ("pica_r", "Melium, novis rebus ſtudentem, manu ſua occîdit. Fuit, fuit iſta quondam"),
         ("pica_i", "Melium, novis rebus ſtudentem, manu ſua occîdit. Fuit, fuit"),
         ("sp1_roman", "At nos vigeſimum jam diem patimur hebeſcere aciem horum autoritatis."),
         ("sp1_italic", "At nos vigeſimum jam diem patimur hebeſcere aciem horum"),
         ("sp2_roman", "At nos vigeſimum jam diem patimur hebeſcere aciem horum autoritatis."),
         ("sp2_italic", "At nos vigeſimum jam diem patimur hebeſcere aciem horum au-"),
         ("lp1_roman", "Verum ego hoc, quod jampridem factum eſſe oportuit, certa de cauſſa"),
         ("lp2_roman", "Verum ego hoc, quod jampridem factum eſſe oportuit, certa de cauſſa"),
         ("br_roman", "Novemb. C. Manlium audaciæ ſatellitem atque adminiſtrum tuæ? num me fefellit,"),
         ("np_roman", "O dii immortales ubi nam gentium ſumus? quam rempub. habemus? in qua urbe vivimus?"),
         ("pr_roman", "O dii immortales ubi nam gentium ſumus? quam rempub. habemus?")]
SPECIAL = {"english_r": ("fonts/Caslon1734English-Roman.otf", 107.3, "English Roman"),
           "english_i": ("fonts/Caslon1734English-Italic.otf", 107.3, "English Italic"),
           "pica_r": ("fonts/Caslon1734Pica-Roman.otf", 97.1, "Pica Roman"),
           "pica_i": ("fonts/Caslon1734Pica-Italic.otf", 97.1, "Pica Italic")}
rows = []
for nm, txt in ORDER:
    if nm in SPECIAL:
        f, pitch, label = SPECIAL[nm]
    else:
        R = json.load(open(f"work/{nm}_result.json", encoding="utf-8"))
        C = json.load(open(f"configs/{nm}.json", encoding="utf-8"))
        f, pitch, label = R["fonts"][0], R["pitch_px"], C["family"].replace("Caslon 1734 ", "") + " " + C["style"]
    img = render(f, pitch, [txt], margin=0.1)
    lab = np.full((img.shape[0], 420), 255, np.uint8)
    cv2.putText(lab, label, (10, img.shape[0] // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 90, 2)
    rows.append(np.hstack([lab, img]))
W = max(r.shape[1] for r in rows)
sheet = np.vstack([np.pad(r, ((0, 0), (0, W - r.shape[1])), constant_values=255) for r in rows])
s = 1600 / W
cv2.imwrite("proofs/family_overview.png", cv2.resize(sheet, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
print("proofs/family_overview.png")
