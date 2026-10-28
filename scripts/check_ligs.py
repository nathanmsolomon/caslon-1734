"""Check book-sourced ligatures; rebuild any that do not look like themselves.

Usage: python -I check_ligs.py <font.otf> <glyphs.json> <reference.otf> [threshold]

Ligatures with any book impressions (book-only, or rare sheet ligatures mixed with book ones) are
rendered and compared with the reference font's ligature of the same name (the
Pica, where it has a good one) or, failing that, with this font's own component
letters set side by side. A ligature scoring below the threshold (default 0.6)
is rebuilt from its own letters, as the compositor would set it without the
ligature sort: the text still sets correctly, only the joined form is lost.
"""
import sys, os, json, re
import cv2
import numpy as np
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setline import render  # noqa: E402
from check_plausible import ncc  # noqa: E402
from glyphnames import NAMES, LIGATURES  # noqa: E402
from overrides import lig_from_parts  # noqa: E402


def ink(im):
    ys, xs = np.where(im < 128)
    if len(ys) == 0:
        return None
    c = (255 - im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]).astype(np.float32)
    return cv2.resize(c, (max(4, int(round(c.shape[1] * 96 / c.shape[0]))), 96), interpolation=cv2.INTER_AREA)


def main():
    fp, gj, rp = sys.argv[1], sys.argv[2], sys.argv[3]
    thr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
    g = json.load(open(gj, encoding="utf-8"))["glyphs"]
    # any ligature with book impressions in it (book-only, or mixed with a few sheet ones)
    book = {v["ch"] for v in g.values()}   # every ligature, sheet ones too (a single mislabelled sheet impression is possible)
    # single impressions were each verified by eye (impression_singles.json); a true ffl's joined
    # hoods never look like its separate letters, so the score would only overrule that check
    byeye = {v["ch"] for v in g.values() if v.get("single")}
    f, r = TTFont(fp), TTFont(rp)
    fo, ro = set(f.getGlyphOrder()), set(r.getGlyphOrder())
    out = []
    for seq in LIGATURES + ["ct"]:
        name = NAMES[seq][0]
        if seq not in book or name not in fo:
            continue
        a = ink(render(fp, 260, [seq], margin=0.1))
        if name in ro:
            b = ink(render(rp, 260, [seq], margin=0.1))
        else:
            # its own letters on their own advances, as the compositor sets them without the sort
            b = ink(render(fp, 260, [seq], margin=0.1, ligs=False))
        s = ncc(a, b) if a is not None and b is not None else 0.0
        out.append(f"{seq}{s:.2f}")
        if seq in byeye:
            out[-1] += "(by eye)"
        elif s < thr:
            lig_from_parts(fp, name)
            out[-1] += "(rebuilt)"
    print(os.path.basename(fp), "ligatures:", " ".join(out) or "none from books")


if __name__ == "__main__":
    main()
