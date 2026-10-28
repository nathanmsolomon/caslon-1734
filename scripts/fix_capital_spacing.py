"""Replace implausible capital sidebearings with the Pica's, as an estimate.

Usage: python -I fix_capital_spacing.py <font.otf> <reference.otf> [tolerance_units] [metrics.json]

With the size's metrics.json, a right sidebearing is left alone when the capital
was seen followed by a letter in running text (then it was measured, not
inferred); only left sides, and right sides never observed, are replaced.

A capital's left side is never observed in running text (it follows a space),
so the spacing solver infers it; with few impressions the inference can go far
wrong. Every font here has 1000 units per body, so sidebearings are comparable
across sizes: any capital sidebearing more than <tolerance> (default 150) units
away from the reference's is replaced by the reference value (outline shifted,
advance adjusted). Changed glyphs are listed; these are estimates, not measures.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen

CAPS = "ABCDEFGHIJKLMNOPRSTUVWXYZ" + "Æ"   # not Q: its kerned tail differs by size


def sides(font, name):
    gs = font.getGlyphSet()
    p = BoundsPen(gs); gs[name].draw(p)
    if p.bounds is None:
        return None
    adv = font["hmtx"][name][0]
    return p.bounds[0], adv - p.bounds[2], p.bounds[2] - p.bounds[0]


def main():
    fp, rp = sys.argv[1], sys.argv[2]
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 150
    import json, os
    seen = {}
    if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
        seen = {c: v.get("pairs", 0) for c, v in json.load(open(sys.argv[4], encoding="utf-8"))["glyphs"].items()}
    f, r = TTFont(fp), TTFont(rp)
    fc, rc = f.getBestCmap(), r.getBestCmap()
    top = f["CFF "].cff.topDictIndex[0]
    cs = top.CharStrings
    gs = f.getGlyphSet()
    changed = []
    pH = BoundsPen(r.getGlyphSet()); r.getGlyphSet()[rc[ord("H")]].draw(pH)
    r_cap = pH.bounds[3] if pH.bounds else 700
    for ch in CAPS:
        u = ord(ch)
        if u not in fc or u not in rc:
            continue
        g = fc[u]
        s, rs = sides(f, g), sides(r, rc[u])
        if not s or not rs:
            continue
        lsb, rsb, ink = s
        # italics: a steeper slant puts more of a capital's top past its advance,
        # so the reference right side is shifted by the extra overhang at cap height
        import math
        d_over = r_cap * (math.tan(math.radians(-f["post"].italicAngle)) - math.tan(math.radians(-r["post"].italicAngle)))
        rs = (rs[0], rs[1] - d_over, rs[2])
        new_l = rs[0] if abs(lsb - rs[0]) > tol else lsb
        measured_right = seen.get(ch, 0) >= 3
        # a measured right side is trusted unless it is wildly off (a mis-measure)
        new_r = rs[1] if abs(rsb - rs[1]) > (150 if measured_right else tol) else rsb
        if (new_l, new_r) == (lsb, rsb):
            continue
        dx = new_l - lsb
        adv = int(round(new_l + ink + new_r))
        pen = T2CharStringPen(adv, None)
        gs[g].draw(TransformPen(pen, (1, 0, 0, 1, dx, 0)))
        cs[g] = pen.getCharString(private=cs[g].private, globalSubrs=cs[g].globalSubrs)
        f["hmtx"][g] = (adv, int(round(new_l)))
        changed.append(f"{ch}({int(lsb)},{int(rsb)}->{int(new_l)},{int(new_r)})")
    if changed:
        f.save(fp)
    print(fp.split("/")[-1], "capital sidebearings estimated from reference:", " ".join(changed) or "none")


if __name__ == "__main__":
    main()
