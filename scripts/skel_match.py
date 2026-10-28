"""Is a book's type the same cut as a 1734 face? Compare letter skeletons.

Usage: python -I skel_match.py <book_avg_dir> <sheet_avg_dir> [<sheet_avg_dir> ...]

design_match.py compares filled shapes (IoU), so a book printed with more or
less ink than the sheet loses score even when the cut is the same. Here each
averaged letter is reduced to its centreline (Zhang-Suen thinning of the
half-density shape), the book letters are scaled so the x-height letters'
heights agree with the sheet's, and each pair of skeletons is compared by
symmetric chamfer distance (mean distance from every skeleton pixel of one to
the nearest of the other, after the best small shift), in percent of the
x-height. Stroke weight drops out; only the drawing is left. Prints one line per
sheet face, best (smallest distance) first, with the IoU-style scale.
"""
import sys, os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design_match import load, LET  # noqa: E402


def thin(b):
    """Zhang-Suen thinning of a 0/1 image."""
    im = np.pad(b.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = [np.roll(np.roll(im, -dy, 0), -dx, 1) for dy, dx in
                 ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))]
            p2, p3, p4, p5, p6, p7, p8, p9 = P
            B = sum(P)
            seq = P + [p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            m = (im == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if m.any():
                im[m] = 0; changed = True
        if not changed:
            return im[1:-1, 1:-1]


def chamfer(a, b, xh):
    """Symmetric mean skeleton distance (percent of x-height), best shift within 3 px."""
    h, w = max(a.shape[0], b.shape[0]) + 10, max(a.shape[1], b.shape[1]) + 10
    A = np.zeros((h, w), np.uint8); A[5:5 + a.shape[0], 5:5 + a.shape[1]] = a
    dA = cv2.distanceTransform((1 - A).astype(np.uint8), cv2.DIST_L2, 3)
    ya, xa = np.where(A > 0)
    best = 1e9
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            B = np.zeros((h, w), np.uint8)
            B[5 + dy:5 + dy + b.shape[0], 5 + dx:5 + dx + b.shape[1]] = b
            yb, xb = np.where(B > 0)
            if len(yb) == 0:
                continue
            dB = cv2.distanceTransform((1 - B).astype(np.uint8), cv2.DIST_L2, 3)
            d = 0.5 * (dA[yb, xb].mean() + dB[ya, xa].mean())
            best = min(best, d)
    return 100.0 * best / xh


def main():
    book = load(sys.argv[1])
    res = []
    for sd in sys.argv[2:]:
        sheet = load(sd)
        common = [c for c in LET if c in book and c in sheet]
        if len(common) < 5:
            continue
        xhc = [c for c in "aeonmrsuc" if c in common]
        k = np.median([sheet[c].shape[0] / book[c].shape[0] for c in xhc])
        xh = float(np.median([sheet[c].shape[0] for c in xhc]))
        vals = []
        for c in common:
            b = book[c]
            b = cv2.resize(b, (max(1, int(round(b.shape[1] * k))), max(1, int(round(b.shape[0] * k)))), interpolation=cv2.INTER_NEAREST)
            vals.append(chamfer(thin(sheet[c]), thin(b), xh))
        res.append((float(np.median(vals)), os.path.basename(sd.rstrip("/\\")), len(common), round(float(k), 3)))
    for v, nm, n, k in sorted(res):
        print(f"{v:5.2f}%  {nm:22s} ({n} letters, scale {k})")


if __name__ == "__main__":
    main()
