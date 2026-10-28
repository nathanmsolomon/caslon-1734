"""Write specimen/catalogue.typ: every Caslon 1734 font, every version, full character set.

Usage: python -I gen_catalogue.py
       typst compile --font-path fonts --font-path fonts/experimental specimen/catalogue.typ specimen/Caslon1734_catalogue.pdf

For each face (largest first): Roman and Italic, each in the clean and the
Impression version, showing the character set in order (capitals, lowercase,
figures, punctuation, ligatures, small caps where present) at a readable size,
the characters the font lacks, and a sample line at the measured body. Then the
titling capitals and an appendix of the experimental (unfinished) faces.
Font fallback is off, so nothing shown comes from any other typeface.
"""
import os, json, glob
from fontTools.ttLib import TTFont

UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZÆŒ"
LOW = "abcdefghijklmnopqrstuvwxyzæœſ"
FIG = "0123456789"
PUN = ".,;:?!'-()&"
LIGS = [("ff", "f_f"), ("fi", "f_i"), ("fl", "f_l"), ("ffi", "f_f_i"), ("ffl", "f_f_l"),
        ("ſt", "longs_t"), ("ſi", "longs_i"), ("ſſ", "longs_longs"), ("ſſi", "longs_longs_i"),
        ("ſh", "longs_h"), ("ſk", "longs_k"), ("ſl", "longs_l"), ("ct", "c_t")]
SAMPLE = "Quouſque tandem abutere, Catilina, patientia noſtra?"

FACES = [  # label, file stem, result json for the body (None = Pica), note
    ("French Cannon", "FrenchCannon", "fc_roman", "sheet only"),
    ("Two Lines Great Primer", "TwoLinesGreatPrimer", "tlgp_roman", "sheet only"),
    ("Two Lines English", "TwoLinesEnglish", "tle_roman", "sheet only"),
    ("Double Pica", "DoublePica", "dp_roman", "sheet + Glynn, The Day of Judgment (1757) for the roman"),
    ("Great Primer", "GreatPrimer", "gp_roman", "sheet + 1785 specimen + Caribbeana (1741), Doctor King's Apology (1755)"),
    ("English", "English", "en_roman", "sheet + 1785 specimen + Eboracum (1736), Polybius (1761)"),
    ("Pica", "Pica", None, "sheet + The Religious Philosopher (1730), Corruptae Latinitatis, Epictetus (1741) for “!”; small caps"),
    ("Small Pica No. 1", "SmallPicaNo.1", "sp1_roman", "sheet + Parliamentary History vol. 4"),
    ("Small Pica No. 2", "SmallPicaNo.2", "sp2_roman", "sheet + 1785 specimen + Faction Detected (1743), Parliamentary History vol. 23"),
    ("Long Primer No. 1", "LongPrimerNo.1", "lp1_roman", "sheet + 1785 specimen + ten books (Vertot 1757, M. Tullii and others)"),
    ("Long Primer No. 2", "LongPrimerNo.2", "lp2_roman", "sheet + 1785 specimen + four Wellcome books (Bailey 1736 and others)"),
    ("Brevier", "Brevier", "br_roman", "sheet + 1785 specimen + Juvenal, England's Gazetteer"),
]
EXPERIMENTAL = [("Nonpareil", "Nonpareil", "np_roman"), ("Pearl", "Pearl", "pr_roman")]


def s(t):
    """Typst string literal."""
    return '"' + t.replace("\\", "\\\\").replace('"', '\\"') + '"'


def body_pt(res):
    px = json.load(open(f"work/{res}_result.json", encoding="utf-8"))["pitch_px"] if res else 97.1
    return round(px / 600 * 72, 2)


def family(path):
    n = TTFont(path)["name"]
    return (n.getDebugName(16) or n.getDebugName(1))


def block(path, size_pt):
    f = TTFont(path)
    cmap, names = f.getBestCmap(), set(f.getGlyphOrder())
    fam = family(path)
    italic = "Italic" in os.path.basename(path)
    style = 'style: "italic", ' if italic else ""
    font = f'font: {s(fam)}, {style}fallback: false'
    have = lambda chars: "".join(c for c in chars if ord(c) in cmap)
    miss = lambda chars: "".join(c for c in chars if ord(c) not in cmap)
    out = []
    for title, chars in (("Capitals", UP), ("Lowercase", LOW), ("Figures", FIG), ("Punctuation", PUN)):
        h = have(chars)
        if h:
            out.append(f'#row[{title}][#text({font}, size: 22pt, tracking: 3pt, {s(" ".join(h))})]')
    ligs = [seq for seq, gname in LIGS if gname in names]
    if ligs:
        out.append(f'#row[Ligatures][#text({font}, size: 22pt, features: ("liga", "hlig", "dlig"), {s("  ".join(ligs))})]')
    sc = [n for n in names if n.endswith(".sc")]
    if sc:
        letters = "".join(sorted(n[0] for n in sc))
        out.append(f'#row[Small caps][#text({font}, size: 22pt, features: ("smcp",), tracking: 3pt, {s(" ".join(letters))})]')
    m = miss(UP + LOW + FIG + PUN)
    out.append(f'#row[Lacks][#text(font: "Franklin Gothic Book", size: 9pt, fill: luma(110), {s(" ".join(m) if m else "nothing in the basic set")})]')
    out.append(f'#row[At body][#text({font}, size: {size_pt}pt, {s(SAMPLE)})]')
    return "\n".join(out)


def main():
    o = ['#set page(paper: "a4", margin: (x: 16mm, y: 15mm), numbering: "1")',
         '#set par(justify: false)',
         '#let lab(t) = text(font: "Franklin Gothic", stretch: 75%, size: 8.5pt, fill: rgb("#8a2b1d"), t)',
         '#let row(a, b) = grid(columns: (24mm, 1fr), column-gutter: 3mm, align: (right + horizon, left + horizon), lab(a), b) + v(2.2mm)',
         '#let vhead(t) = block(above: 5mm, below: 2mm, text(font: "Franklin Gothic Book", size: 10pt, weight: "regular", t))',
         '#align(center)[#v(30mm)#text(font: "Caslon 1734 Great Primer", size: 30pt, "A CATALOGUE")#v(3mm)',
         '#text(font: "Caslon 1734 English", size: 14pt, "of the Founts reconſtructed from the Specimen of")#v(2mm)',
         '#text(font: "Caslon 1734 Great Primer", size: 18pt, "WILLIAM CASLON")#v(2mm)',
         '#text(font: "Caslon 1734 English", style: "italic", size: 14pt, "Letter-Founder, in Chiſwell-Street, London, 1734")#v(12mm)',
         '#text(font: "Franklin Gothic Book", size: 9.5pt)[Every face in every version: Roman and Italic, each as a clean (averaged) font and as an',
         'Impression font (one typical real impression). Characters are shown in order at a readable size, with what each font lacks',
         'and a line at the body measured on the 1734 sheet. Nothing is drawn from any other typeface.]]',
         '#pagebreak()']
    for label, stem, res, note in FACES:
        bp = body_pt(res)
        o.append(f'#block(breakable: false)[#text(font: "Caslon 1734 Great Primer", size: 20pt, {s(label)}) #h(3mm) '
                 f'#lab[body {bp} pt · {note}]]')
        for style in ("Roman", "Italic"):
            for var, vlabel in (("", "clean"), ("Impression", "Impression")):
                p = f"fonts/Caslon1734{stem}{var}-{style}.otf"
                if os.path.exists(p):
                    o.append(f'#block(breakable: false)[#vhead[{style} · {vlabel}]\n{block(p, bp)}]')
        o.append('#pagebreak()')
    o.append('#text(font: "Caslon 1734 Great Primer", size: 20pt, "Titling Capitals") #h(3mm) #lab[sizes estimated from the sheet; each shows only the letters on its alphabet line]')
    for k in range(1, 8):
        for var, vlabel in (("", "clean"), ("Impression", "Impression")):
            p = f"fonts/Caslon1734Titling{k}{var}-Roman.otf"
            if os.path.exists(p):
                f = TTFont(p); have = "".join(c for c in UP if ord(c) in f.getBestCmap())
                o.append(f'#block(breakable: false)[#vhead[Titling {k} · {vlabel}]'
                         f'#text(font: {s(family(p))}, fallback: false, size: 34pt, tracking: 4pt, {s(have)})]')
    o.append('#pagebreak()')
    o.append('#text(font: "Caslon 1734 Great Primer", size: 20pt, "Appendix: experimental faces") #v(2mm)'
             '#text(font: "Franklin Gothic Book", size: 9.5pt)[Nonpareil and Pearl were set aside: their impressions on the sheet are too '
             'small and faint for an accurate build, and no book source could be identified. Shown as built, unfinished.]')
    for label, stem, res in EXPERIMENTAL:
        bp = body_pt(res)
        o.append(f'#block(breakable: false)[#text(font: "Caslon 1734 Great Primer", size: 16pt, {s(label)}) #h(3mm) #lab[body {bp} pt · experimental]]')
        for style in ("Roman", "Italic"):
            for var, vlabel in (("", "clean"), ("Impression", "Impression")):
                p = f"fonts/experimental/Caslon1734{stem}{var}-{style}.otf"
                if os.path.exists(p):
                    o.append(f'#block(breakable: false)[#vhead[{style} · {vlabel}]\n{block(p, bp)}]')
    os.makedirs("specimen", exist_ok=True)
    open("specimen/catalogue.typ", "w", encoding="utf-8").write("\n".join(o) + "\n")
    print("specimen/catalogue.typ")


if __name__ == "__main__":
    main()
