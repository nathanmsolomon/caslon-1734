"""Render text with a built font (own layout: ligatures + advance widths).
Usage: python -I setline.py <font.otf> <px_per_em> <out.png> <text lines...>"""
import sys, os
import cv2, numpy as np
from fontTools.ttLib import TTFont
sys.path.insert(0, os.path.dirname(__file__))
from proof import PolyPen, NAMES, LIGATURES

LIGS = [(seq, NAMES[seq]) for seq in LIGATURES]

def names(text, gs, cmap=None, ligs=True):
    # characters go through the font's cmap (as in any application), so remapped
    # or unmapped glyphs show as they really will
    out, k = [], 0
    while k < len(text):
        for seq, nm in (LIGS if ligs else []):
            if text.startswith(seq, k) and nm in gs:
                out.append(nm); k += len(seq); break
        else:
            ch = text[k]
            if ch == " ":
                nm = "space"
            elif cmap is not None:
                nm = cmap.get(ord(ch), ".notdef")
            else:
                nm = NAMES.get(ch, ch)
            out.append(nm if nm in gs else ".notdef"); k += 1
    return out

def render(fontp, em, lines, SS=4, margin=0.5, ligs=True):
    f = TTFont(fontp); gs = f.getGlyphSet(); hm = f["hmtx"]; s = em / 1000 * SS
    cm = f.getBestCmap()
    asc = f["hhea"].ascent
    # room for kerned overhangs past the last advance (Q tail, f hood)
    W = int(max(sum(hm[n][0] for n in names(l, gs, cm, ligs)) for l in lines) * s + 2 * margin * em * SS + 0.6 * em * SS)
    H = int((len(lines) + 2 * margin) * em * SS)
    m = np.zeros((H, W), np.uint8)
    for li, l in enumerate(lines):
        x = margin * em * SS; base = (margin * em + li * em) * SS + asc * s
        for n in names(l, gs, cm, ligs):
            pp = PolyPen(gs); gs[n].draw(pp)
            g = np.zeros_like(m)
            for p in pp.polys:
                q = np.array([[x + px * s, base - py * s] for px, py in p], np.int32)
                t = np.zeros_like(m); cv2.fillPoly(t, [q], 255); g ^= t
            m |= g; x += hm[n][0] * s
    return 255 - cv2.resize(m, (W // SS, H // SS), interpolation=cv2.INTER_AREA)

if __name__ == "__main__":
    img = render(sys.argv[1], float(sys.argv[2]), sys.argv[4:])
    cv2.imwrite(sys.argv[3], img)
