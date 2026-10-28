"""Is a book's type the same cut as a 1734 face? Compare averaged letters directly.

Usage: python -I design_match.py <book_avg_dir> <sheet_avg_dir> [<sheet_avg_dir> ...]

For common lowercase letters both averages have, each letter is cropped to its
ink, scaled so the x-height letters' heights agree (median over the set), and
compared by IoU of the half-density shapes after best alignment. Averaging many
impressions removes most of the noise that defeats a page screen, so the median
IoU separates same-cut from merely-similar type. Prints one line per sheet face,
best first.
"""
import sys, os, json
import cv2
import numpy as np

LET = "aeonmrstucdhilpb"


def load(d):
    g = json.load(open(os.path.join(d, "glyphs.json"), encoding="utf-8"))
    out = {}
    for gid, v in g["glyphs"].items():
        if v["ch"] in LET and v.get("n", 0) >= 3:
            a = cv2.imread(os.path.join(d, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
            ys, xs = np.where(a > 0.5)
            if len(ys) > 20:
                out[v["ch"]] = (a > 0.5)[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8)
    return out


def iou(a, b):
    h, w = max(a.shape[0], b.shape[0]) + 8, max(a.shape[1], b.shape[1]) + 8
    A = np.zeros((h, w), np.uint8); A[4:4 + a.shape[0], 4:4 + a.shape[1]] = a
    best = 0.0
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            B = np.zeros((h, w), np.uint8)
            y0, x0 = 4 + dy, 4 + dx
            B[y0:y0 + b.shape[0], x0:x0 + b.shape[1]] = b[:h - y0, :w - x0]
            inter, uni = (A & B).sum(), (A | B).sum()
            best = max(best, inter / uni if uni else 0)
    return best


def main():
    book = load(sys.argv[1])
    res = []
    for sd in sys.argv[2:]:
        sheet = load(sd)
        common = [c for c in LET if c in book and c in sheet]
        if len(common) < 5:
            continue
        xh = [c for c in "aeonmrsuc" if c in common]
        k = np.median([sheet[c].shape[0] / book[c].shape[0] for c in xh])
        vals = []
        for c in common:
            b = book[c]
            b = cv2.resize(b, (max(1, int(round(b.shape[1] * k))), max(1, int(round(b.shape[0] * k)))), interpolation=cv2.INTER_NEAREST)
            vals.append(iou(sheet[c], b))
        res.append((float(np.median(vals)), os.path.basename(sd.rstrip("/")), len(common), round(float(k), 3)))
    for v, nm, n, k in sorted(res, reverse=True):
        print(f"{v:.3f}  {nm:22s} ({n} letters, scale {k})")


if __name__ == "__main__":
    main()
