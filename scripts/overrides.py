"""Hand-checked corrections the automatic rules miss (each one an estimate).

Usage: python -I overrides.py

Each entry was found by eye in a proof and is listed in the README. Two kinds:
  rsb  : set a glyph's right sidebearing to the reference's (Pica of the same
         style), shifted for the difference in italic slant at cap height
  ratio:<size> : right sidebearing as the same fraction of the ink width as in
         that sibling size (when Pica's letter is shaped too differently)
  lig  : rebuild a ligature from its own component letters (as set without the
         ligature sort) when its averaged outline is damaged
  unlig: take a mislabelled ligature out of the ligature substitutions (the
         text then sets its separate letters)
Applied to both the clean and Impression versions. Idempotent.
"""
import math
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

OVERRIDES = [
    ("GreatPrimer", "Italic", "rsb", "R"),        # measured right side too loose ("R ome")
    ("LongPrimerNo.2", "Italic", "ratio:LongPrimerNo.1", "ſ"),  # gap after long s ("Quouſ que"); No. 1's proportion
    ("TwoLinesEnglish", "Roman", "lig", "longs_t"),  # doubled hook on the ſt sort
    ("Pica", "Roman", "unlig", "longs_b"),   # all 7 book "ſb" impressions are ſt (OCR label); found Oct 28
]


def bounds(f, g):
    p = BoundsPen(f.getGlyphSet()); f.getGlyphSet()[g].draw(p)
    return p.bounds


def set_rsb(fp, ch, refp):
    f, r = TTFont(fp), TTFont(refp)
    g, rg = f.getBestCmap()[ord(ch)], r.getBestCmap()[ord(ch)]
    b, rb = bounds(f, g), bounds(r, rg)
    rcap = bounds(r, r.getBestCmap()[ord("H")])[3]
    over = rcap * (math.tan(math.radians(-f["post"].italicAngle)) - math.tan(math.radians(-r["post"].italicAngle)))
    rsb = (r["hmtx"][rg][0] - rb[2]) - over
    adv = int(round(b[2] + rsb))
    f["hmtx"][g] = (adv, f["hmtx"][g][1])
    f.save(fp)
    return f"{ch} rsb -> {int(rsb)}"


def set_rsb_ratio(fp, ch, sibp):
    f, r = TTFont(fp), TTFont(sibp)
    g, rg = f.getBestCmap()[ord(ch)], r.getBestCmap()[ord(ch)]
    b, rb = bounds(f, g), bounds(r, rg)
    frac = (r["hmtx"][rg][0] - rb[2]) / (rb[2] - rb[0])
    rsb = frac * (b[2] - b[0])
    f["hmtx"][g] = (int(round(b[2] + rsb)), f["hmtx"][g][1])
    f.save(fp)
    return f"{ch} rsb -> {int(rsb)} ({frac:.2f} of ink, as in {sibp.split('1734')[1][:-4]})"


def lig_from_parts(fp, lig):
    f = TTFont(fp); gs = f.getGlyphSet()
    parts = lig.split("_")
    cs = f["CFF "].cff.topDictIndex[0].CharStrings
    pen = T2CharStringPen(sum(f["hmtx"][p][0] for p in parts), None)
    x = 0
    for p in parts:
        rec = DecomposingRecordingPen(gs); gs[p].draw(rec)
        for op, args in rec.value:
            getattr(pen, op)(*[(a[0] + x, a[1]) if isinstance(a, tuple) else a for a in args])
        x += f["hmtx"][p][0]
    cs[lig] = pen.getCharString(private=cs[lig].private, globalSubrs=cs[lig].globalSubrs)
    f["hmtx"][lig] = (x, f["hmtx"][parts[0]][1])
    f.save(fp)
    return f"{lig} rebuilt from {'+'.join(parts)}"


def unlig(fp, lig):
    f = TTFont(fp); n = 0
    for lk in f["GSUB"].table.LookupList.Lookup:
        for st in lk.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if hasattr(st, "ligatures"):
                for first in list(st.ligatures):
                    keep = [l for l in st.ligatures[first] if l.LigGlyph != lig]
                    n += len(st.ligatures[first]) - len(keep)
                    if keep:
                        st.ligatures[first] = keep
                    else:
                        del st.ligatures[first]
    if n:
        f.save(fp)
    return f"{lig} taken out of the ligature substitutions ({n})"


def main():
    for size, style, kind, what in OVERRIDES:
        for var in ("", "Impression"):
            fp = f"fonts/Caslon1734{size}{var}-{style}.otf"
            ref = f"fonts/Caslon1734Pica-{style}.otf"
            if kind == "rsb":
                msg = set_rsb(fp, what, ref)
            elif kind.startswith("ratio:"):
                msg = set_rsb_ratio(fp, what, f"fonts/Caslon1734{kind[6:]}{var}-{style}.otf")
            elif kind == "unlig":
                msg = unlig(fp, what)
            else:
                msg = lig_from_parts(fp, what)
            print(fp.split("/")[-1], "override:", msg)


if __name__ == "__main__":
    main()
