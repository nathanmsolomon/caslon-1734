"""Write specimen/specimen.typ: every Caslon 1734 face at its measured body size.

Usage: python -I gen_specimen.py   (then: typst compile --font-path fonts specimen/specimen.typ)

Body sizes are the sheet's measured line pitch (px at 600 ppi -> pt); text follows
the 1734 sheet (Cicero, In Catilinam I), with a second line of letters the sheet
does not show, where book sources supplied them.
"""
import json, os

W = "work"
CICERO = ("Quouſque tandem abutere, Catilina, patientia noſtra? quamdiu nos etiam furor iſte tuus "
          "eludet? quem ad finem ſeſe effrenata jactabit audacia?")
EXTRA = "Wykeham, by the way, works quickly: xyz"
FACES = [  # (label, family, result json for the pitch, roman text length, has book letters)
    ("French Cannon", "Caslon 1734 French Cannon", "fc_roman", 14, False),
    ("Two Lines Great Primer", "Caslon 1734 Two Lines Great Primer", "tlgp_roman", 22, False),
    ("Two Lines English", "Caslon 1734 Two Lines English", "tle_roman", 30, False),
    ("Double Pica", "Caslon 1734 Double Pica", "dp_roman", 46, False),
    ("Great Primer", "Caslon 1734 Great Primer", "gp_roman", 60, True),
    ("English", "Caslon 1734 English", "en_roman", 80, True),
    ("Pica", "Caslon 1734 Pica", None, 999, True),
    ("Small Pica No. 1", "Caslon 1734 Small Pica No. 1", "sp1_roman", 999, False),
    ("Small Pica No. 2", "Caslon 1734 Small Pica No. 2", "sp2_roman", 999, False),
    ("Long Primer No. 1", "Caslon 1734 Long Primer No. 1", "lp1_roman", 999, False),
    ("Long Primer No. 2", "Caslon 1734 Long Primer No. 2", "lp2_roman", 999, False),
    ("Brevier", "Caslon 1734 Brevier", "br_roman", 999, False),
]
TITLING = [(f"Titling {k}", f"Caslon 1734 Titling {k}", f"titling{k}", t) for k, t in
           [(1, "ABC"), (2, "ABCD"), (3, "ABCDEF"), (4, "ABCDEFGH"), (5, "ABCDEFGHIJ"), (6, "ABCDEFGHIJKL"), (7, "ABCDEFGHIJKLMN")]]


def pt(res, default=97.1):
    px = json.load(open(f"{W}/{res}_result.json", encoding="utf-8"))["pitch_px"] if res else default
    return round(px / 600 * 72, 2)


def cut(s, n):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0]


def esc(s):
    return s.replace("\\", "\\\\").replace("#", "\\#").replace("*", "\\*").replace("_", "\\_")


fams = sorted({l.split("fonts")[0] for l in []})
out = ['#set page(paper: "a4", margin: (x: 18mm, y: 16mm))',
       '#set par(justify: false, leading: 0pt, spacing: 0pt)',
       '#let label(t) = text(font: "Franklin Gothic", stretch: 75%, size: 8pt, fill: rgb("#8a2b1d"), t)',
       '#align(center)[#text(font: "Caslon 1734 Great Primer", size: 26pt)[A SPECIMEN] #v(2mm)',
       '#set par(leading: 5pt); #text(font: "Caslon 1734 Pica", size: 11.65pt)[of the Founts reconſtructed from the Specimen of',
       ' WILLIAM CASLON, Letter-Founder, in Chiſwell-Street, London, 1734]] #v(8mm)']
for label, fam, res, n, book in FACES:
    size = pt(res)
    note = f"{label} · body {size} pt as printed on the 1734 sheet"
    note += " · w y k x z & others from period books" if book else " · sheet letters only"
    out.append(f'#block(breakable: false)[#label[{note}] #v(1.2mm)')
    out.append(f'#text(font: "{fam}", size: {size}pt, top-edge: "ascender", bottom-edge: "descender")[{esc(cut(CICERO, n))}]')
    out.append(f'#linebreak()#text(font: "{fam}", size: {size}pt, style: "italic", top-edge: "ascender", bottom-edge: "descender")[{esc(cut(CICERO, n))}]')
    if book:
        out.append(f'#linebreak()#text(font: "{fam}", size: {size}pt, top-edge: "ascender", bottom-edge: "descender")[{esc(cut(EXTRA, n))}]')
    out.append('] #v(5mm)')
out.append('#pagebreak() #label[Titling capitals · sizes estimated from the sheet (no running text to measure the body)] #v(3mm)')
for label, fam, res, t in TITLING:
    out.append(f'#block(breakable: false)[#label[{label}] #linebreak() #text(font: "{fam}", size: {pt(res)}pt)[{t}]] #v(3mm)')
out.append('#v(6mm) #label[Clean (averaged) and Impression (one typical real impression) versions, English]  #v(2mm)')
for fam in ["Caslon 1734 English", "Caslon 1734 English Impression"]:
    out.append(f'#text(font: "{fam}", size: 12.88pt, top-edge: "ascender", bottom-edge: "descender")[{esc(cut(CICERO, 80))}] #linebreak()')
os.makedirs("specimen", exist_ok=True)
open("specimen/specimen.typ", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("specimen/specimen.typ")
