"""Remove stray pieces lying wholly above the fount's tallest ascender.

Usage: python -I fix_strays.py <font.otf>

Solid-set lines put the bottoms of the line above inside a letter's crop; when
a glyph has only a few impressions such a piece can survive averaging. No letter
of the fount rises above its long s / l / b / d / h / k, so any contour whose
lowest point lies above (that height x 1.02) is removed. Accented letters are
skipped. Changed glyphs are listed.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen

TALL = ["longs", "l", "b", "d", "h", "k"]
SKIP = {"ecircumflex", "edieresis", "icircumflex"}


def contours(rec):
    cur, out = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def main():
    fp = sys.argv[1]
    f = TTFont(fp)
    gs = f.getGlyphSet()
    order = set(f.getGlyphOrder())
    tops = []
    for g in TALL:
        if g in order:
            p = BoundsPen(gs); gs[g].draw(p)
            if p.bounds:
                tops.append(p.bounds[3])
    if not tops:
        return
    limit = 1.02 * sorted(tops)[len(tops) // 2]   # median: one bad ascender can't set it
    top = f["CFF "].cff.topDictIndex[0]
    cs = top.CharStrings
    changed = []
    for g in f.getGlyphOrder():
        if g in SKIP or g == ".notdef":
            continue
        rec = DecomposingRecordingPen(gs); gs[g].draw(rec)
        cons = contours(rec)
        parts = g.split("_")
        if len(parts) > 1 and all(p_ in order for p_ in parts):
            pb = BoundsPen(gs); gs[g].draw(pb)
            if pb.bounds and pb.bounds[3] > 1.05 * limit:
                # a stray fused onto a ligature: set it from its own letters instead
                # (as the compositor would without the ligature sort)
                pen = T2CharStringPen(sum(f["hmtx"][p_][0] for p_ in parts), None)
                x = 0
                for p_ in parts:
                    r2 = DecomposingRecordingPen(gs); gs[p_].draw(r2)
                    for op, args in r2.value:
                        getattr(pen, op)(*[(a[0] + x, a[1]) if isinstance(a, tuple) else a for a in args])
                    x += f["hmtx"][p_][0]
                cs[g] = pen.getCharString(private=cs[g].private, globalSubrs=cs[g].globalSubrs)
                f["hmtx"][g] = (x, f["hmtx"][parts[0]][1])
                changed.append(g + "(rebuilt from " + "+".join(parts) + ")")
                continue
        keep = []
        for c in cons:
            ys = [pt[1] for _, args in c for pt in args if isinstance(pt, tuple)]
            if ys and min(ys) > limit:
                continue
            keep.append(c)
        if len(keep) == len(cons) or not keep:
            continue
        pen = T2CharStringPen(f["hmtx"][g][0], None)
        for c in keep:
            for op, args in c:
                getattr(pen, op)(*args)
        cs[g] = pen.getCharString(private=cs[g].private, globalSubrs=cs[g].globalSubrs)
        changed.append(g)
    if changed:
        f.save(fp)
    print(fp.split("/")[-1], "stray pieces removed from:", " ".join(changed) or "none")


if __name__ == "__main__":
    main()
