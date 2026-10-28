"""Space Q like O: in metal Q was cast on O's set width and its tail kerned.

Usage: python -I fix_q.py <font.otf> [tolerance_units] [reference.otf  (used when there is no O)]

Q's long tail runs under the next letter (a kerned sort), so its advance cannot
be read from its ink box, and with few impressions the spacing solver gets it
badly wrong. Here Q gets O's advance, shifted by the difference of their left
sidebearings (the bowls coincide), when that differs from the current advance
by more than <tolerance> (default 60).
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen


def main():
    fp = sys.argv[1]
    tol = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    f = TTFont(fp)
    cmap, gs = f.getBestCmap(), f.getGlyphSet()
    if ord("Q") not in cmap:
        return
    q = cmap[ord("Q")]
    pq = BoundsPen(gs); gs[q].draw(pq)
    adv_old, lsb = f["hmtx"][q]
    if ord("O") in cmap:
        o = cmap[ord("O")]
        po = BoundsPen(gs); gs[o].draw(po)
        adv = int(round(f["hmtx"][o][0] + pq.bounds[0] - po.bounds[0]))
    elif len(sys.argv) > 3:
        # no O in this fount (the sheet's large sizes show only running text):
        # the bowl is an O, as wide as the reference O's proportion makes it for
        # Q's height, followed by the reference O's right sidebearing
        r = TTFont(sys.argv[3]); rgs = r.getGlyphSet(); ro = r.getBestCmap()[ord("O")]
        pr = BoundsPen(rgs); rgs[ro].draw(pr)
        o_w, o_h = pr.bounds[2] - pr.bounds[0], pr.bounds[3] - pr.bounds[1]
        o_rsb = r["hmtx"][ro][0] - pr.bounds[2]
        bowl_w = o_w / o_h * (pq.bounds[3] - max(pq.bounds[1], -0.02 * o_h))
        adv = int(round(pq.bounds[0] + bowl_w + o_rsb))
    else:
        return
    if abs(adv - adv_old) > tol:
        f["hmtx"][q] = (adv, lsb)
        f.save(fp)
        print(fp.split("/")[-1], f"Q advance {adv_old} -> {adv} (O's set width)")


if __name__ == "__main__":
    main()
