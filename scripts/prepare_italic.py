"""Measure an italic block's slant, find it on all three copies, blank the
neighbouring column and shear it upright.

Usage: python -I prepare_italic.py <name> <x0> <y0> <x1> <y1> [column_cut]
  box on work/page1.png; column_cut = crop-relative x beyond which to blank
Writes work/<name>_p{0,1,2}.png and work/<name>_geometry.json; prints the slant.
"""
import sys, json
import cv2
import numpy as np


def main():
    name = sys.argv[1]
    x0, y0, x1, y1 = map(int, sys.argv[2:6])
    cut = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != "-" else None
    force_angle = float(sys.argv[7]) if len(sys.argv) > 7 else None   # small sizes: projection is unreliable
    im1 = cv2.imread("work/page1.png", 0)
    blk = im1[y0:y1, x0:x1].copy()
    if cut:
        blk[:, cut:] = int(np.median(blk))
    _, bw = cv2.threshold(cv2.GaussianBlur(blk, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = bw.astype(np.float32) / 255; H, W = bw.shape
    r = np.convolve(bw.sum(1), np.ones(30), "same"); peaks = []
    for y in range(H):
        if r[y] == r[max(0, y - 45):y + 45].max() and r[y] > 0.3 * r.max() and (not peaks or y - peaks[-1] > 60):
            peaks.append(y)
    tot = {}
    for c in peaks:
        band = bw[max(0, c - 35):c + 25]; h, w = band.shape
        for a in np.arange(8, 26, 0.5):
            t = np.tan(np.radians(a))
            p = cv2.warpAffine(band, np.float32([[1, t, 0], [0, 1, 0]]), (w + int(t * h) + 2, h)).sum(0)
            tot[a] = tot.get(a, 0) + float((p ** 2).sum())
    A = float(max(tot, key=tot.get)) if force_angle is None else force_angle
    t = np.tan(np.radians(A))
    s = 0.25
    T = cv2.resize(im1[y0:y1, x0:x1], None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    boxes = {"1": [x0, y0, x1, y1]}
    for p in ("0", "2"):
        im = cv2.imread(f"work/page{p}.png", 0)
        I = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        rr = cv2.matchTemplate(I, T, cv2.TM_CCOEFF_NORMED); _, mv, _, (x, y) = cv2.minMaxLoc(rr)
        X, Y = int(x / s), int(y / s); boxes[p] = [X, Y, X + (x1 - x0), Y + (y1 - y0)]
        print("copy", p, "match", round(mv, 3), boxes[p])
    for p, (a, b, c, d) in boxes.items():
        im = cv2.imread(f"work/page{p}.png", 0)[b:d, a:c].copy()
        if cut:
            im[:, cut:] = int(np.median(im))
        h, w = im.shape
        cv2.imwrite(f"work/{name}_p{p}.png", cv2.warpAffine(im, np.float32([[1, t, 0], [0, 1, 0]]), (w + int(t * h) + 2, h),
                                                            flags=cv2.INTER_CUBIC, borderValue=int(np.median(im))))
    json.dump(dict(angle=A, boxes=boxes, column_cut=cut, size=[int(x1 - x0 + t * (y1 - y0) + 2), int(y1 - y0)]),
              open(f"work/{name}_geometry.json", "w"))
    print("slant", A)


if __name__ == "__main__":
    main()
