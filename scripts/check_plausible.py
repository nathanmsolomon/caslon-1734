"""Remove book-sourced glyphs that do not look like the letter they claim to be.

Usage: python -I check_plausible.py <font.otf> <reference.otf> [chars] [threshold]

Each character (default: the letters and marks only books supply) is rendered
in the font and in a well-established reference (the Pica of the same style),
cropped to its ink, scaled to a common height and compared by normalised
cross-correlation. A genuine letter of a neighbouring Caslon size matches its
Pica counterpart closely; a garbled average (OCR misreads, neighbours) does
not. Failing characters are unmapped (removed from the cmap) and listed.
Characters checked by eye and found genuine are listed in plausible_keep.json.
"""
import sys, os
import cv2
import numpy as np
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(__file__))
from setline import render  # noqa: E402

DEFAULT = "kwxyzKUVWXYZ0123456789&!'"


def ink(fontp, ch):
    im = render(fontp, 200, [ch], margin=0.3)
    ys, xs = np.where(im < 128)
    if len(ys) == 0:
        return None
    c = (255 - im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]).astype(np.float32)
    h = 96
    return cv2.resize(c, (max(4, int(round(c.shape[1] * h / c.shape[0]))), h), interpolation=cv2.INTER_AREA)


def ncc(a, b):
    # best match over small shifts: a sweeping tail (italic y, Q) moves the ink
    # box without the letter being any different
    w = max(a.shape[1], b.shape[1])
    if min(a.shape[1], b.shape[1]) < 0.55 * w:
        return 0.0   # very different widths: not the same letter (a stem fits inside any letter)
    m = int(0.2 * w) + 4
    big = np.pad(b, ((12, 12), (m + (w - b.shape[1]) // 2, m + w - b.shape[1] - (w - b.shape[1]) // 2)))
    if a.shape[0] > big.shape[0] or a.shape[1] > big.shape[1]:
        return 0.0
    return float(cv2.matchTemplate(big, a, cv2.TM_CCOEFF_NORMED).max())


def main():
    fp, rp = sys.argv[1], sys.argv[2]
    chars = sys.argv[3] if len(sys.argv) > 3 else DEFAULT
    thr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
    f, r = TTFont(fp), TTFont(rp)
    fc, rc = f.getBestCmap(), r.getBestCmap()
    bad, scores = [], []
    # characters confirmed genuine by eye despite a low score (plausible_keep.json:
    # {font name without "Impression": {chars: reason}}); applies to both versions
    kp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plausible_keep.json")
    import json as _json
    keepmap = _json.load(open(kp, encoding="utf-8")) if os.path.exists(kp) else {}
    fname = os.path.basename(fp).replace("Impression", "").replace(".otf", "").replace("Caslon1734", "")
    keep = "".join(k for k in keepmap.get(fname, {}))
    # every reference letter, to ask which one each glyph resembles most (catches
    # mislabels between look-alikes such as V/W or Y/Z that pass on score alone)
    pool = [c for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&!?;:()'ſ" if ord(c) in rc]
    refs = {c: ink(rp, c) for c in pool}
    for ch in chars:
        if ord(ch) not in fc or ord(ch) not in rc:
            continue
        a = ink(fp, ch)
        if ch not in refs:
            refs[ch] = ink(rp, ch)
        if a is None or refs[ch] is None:
            continue
        s = ncc(a, refs[ch])
        best, bs = max(((c, ncc(a, refs[c])) for c in pool if c.lower() != ch.lower() and refs[c] is not None), key=lambda t: t[1])
        scores.append(f"{ch}{s:.2f}" + (f"(~{best}{bs:.2f})" if bs > s else ""))
        if (s < thr or bs > s + 0.05) and ch not in keep:
            bad.append(ch)
    if bad:
        for t in f["cmap"].tables:
            if t.isUnicode():
                for ch in bad:
                    t.cmap.pop(ord(ch), None)
        f.save(fp)
    print(fp.split("/")[-1], " ".join(scores), "| removed:", "".join(bad) or "none")


if __name__ == "__main__":
    main()
