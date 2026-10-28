"""Give a titling font's few lowercase letters estimated sidebearings.

Usage: python -I fix_titling_lowercase.py <font.otf> <reference.otf>

The titling lines show only a handful of lowercase letters (Titling 1: a b c d e g,
Titling 2: a-h), seen in 4-7 pairs each: enough to fix the gap between two
neighbours, not how it divides between them, so the spacing solver fell back on a
fixed split and gave d, g and h large negative sidebearings. They are replaced by
the reference's (Double Pica roman, the largest Caslon roman with the full lowercase,
spaced from the sheet and a book) scaled by the ratio of x-heights. These are
estimates, not measures. Changed glyphs are listed.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen


def bounds(font, name):
    gs = font.getGlyphSet()
    p = BoundsPen(gs); gs[name].draw(p)
    return p.bounds


def main():
    fp, rp = sys.argv[1], sys.argv[2]
    f, r = TTFont(fp), TTFont(rp)
    fc, rc = f.getBestCmap(), r.getBestCmap()
    low = [c for c in "abcdefghijklmnopqrstuvwxyz" if ord(c) in fc and ord(c) in rc]
    if not low:
        print(fp.split("/")[-1], "lowercase sidebearings estimated: no lowercase"); return
    # x-height from the lowercase both fonts have without ascenders or descenders
    xs = [c for c in "xaceo" if c in low] or low[:1]
    xf = max(bounds(f, fc[ord(c)])[3] for c in xs)
    xr = max(bounds(r, rc[ord(c)])[3] for c in xs)
    s = xf / xr
    cs = f["CFF "].cff.topDictIndex[0].CharStrings
    gs = f.getGlyphSet()
    changed = []
    for c in low:
        g, rg = fc[ord(c)], rc[ord(c)]
        b, rb = bounds(f, g), bounds(r, rg)
        lsb, rsb = b[0], f["hmtx"][g][0] - b[2]
        new_l, new_r = rb[0] * s, (r["hmtx"][rg][0] - rb[2]) * s
        adv = int(round(new_l + (b[2] - b[0]) + new_r))
        pen = T2CharStringPen(adv, None)
        gs[g].draw(TransformPen(pen, (1, 0, 0, 1, new_l - lsb, 0)))
        cs[g] = pen.getCharString(private=cs[g].private, globalSubrs=cs[g].globalSubrs)
        f["hmtx"][g] = (adv, int(round(new_l)))
        changed.append(f"{c}({int(lsb)},{int(rsb)}->{int(new_l)},{int(new_r)})")
    f.save(fp)
    print(fp.split("/")[-1], f"lowercase sidebearings estimated (x-height ratio {s:.3f}):", " ".join(changed))


if __name__ == "__main__":
    main()
