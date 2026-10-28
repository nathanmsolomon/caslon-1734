"""Screen a page scan: is it the same type, at the same size, as the 1734 averages?

Usage: python -I screen.py <avg_dir> <ppi> <page.jpg> [<page.jpg> ...]
       (ppi = the scan's resolution; 'self' runs the 1734 sheet as the yardstick)

For a sweep of scales, every averaged lowercase template is matched against the
page (normalised cross-correlation on ink density). Reports the best scale
(1.00 = exactly the 1734 Pica size) and the median of each template's 25 best
match scores at that scale.
"""
import sys, os, json
import cv2
import numpy as np

TEST = "aenomdhcrstupb"


def page_density(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE).astype(np.float32)
    paper, ink = np.percentile(im, 80), np.percentile(im, 1)
    return np.clip((paper - im) / (paper - ink), 0, 1)


def templates(avg):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    out = {}
    for gid, v in g["glyphs"].items():
        if v["ch"] in TEST:
            a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
            ys, xs = np.where(a > 0.15)
            pad = 3 * g["up"]
            out[v["ch"]] = a[max(0, ys.min() - pad):ys.max() + pad, max(0, xs.min() - pad):xs.max() + pad]
    return out, g["up"]


def top_scores(res, k, w, h):
    res = res.copy(); vals = []
    for _ in range(k):
        _, mv, _, (x, y) = cv2.minMaxLoc(res)
        vals.append(mv)
        res[max(0, y - h // 2):y + h // 2, max(0, x - w // 2):x + w // 2] = -1
    return vals


def score(dens, tpls, up, factor):
    s = []
    for ch, t in tpls.items():
        tt = cv2.resize(t, None, fx=factor / up, fy=factor / up, interpolation=cv2.INTER_AREA)
        if tt.shape[0] >= dens.shape[0] or tt.shape[1] >= dens.shape[1] or min(tt.shape) < 6:
            continue
        res = cv2.matchTemplate(dens, tt, cv2.TM_CCOEFF_NORMED)
        # windows of blank paper (density clipped to exactly 0 on clean scans) have
        # no variance, and OpenCV can return a spurious 1.0 there: ignore any window
        # holding less than a third of the template's ink
        ink = cv2.boxFilter(dens, -1, (tt.shape[1], tt.shape[0]), normalize=False, anchor=(0, 0))
        ink = ink[:res.shape[0], :res.shape[1]]
        res[ink < tt.sum() / 3] = -1
        s.append(np.median(top_scores(res, 25, tt.shape[1], tt.shape[0])))
    return float(np.median(s)) if s else 0.0


def main():
    avg, ppi, pages = sys.argv[1], sys.argv[2], sys.argv[3:]
    tpls, up = templates(avg)
    for p in pages:
        dens = page_density(p)
        if ppi == "self":
            base = 1.0
        else:
            base = float(ppi) / 600.0
        # coarse sweep over plausible sizes (Long Primer .. Great Primer), then fine
        coarse = np.arange(0.70, 1.45, 0.04)
        sc = [(score(dens, tpls, up, base * s), s) for s in coarse]
        best = max(sc)[1]
        fine = np.arange(best - 0.04, best + 0.041, 0.01)
        sf = [(score(dens, tpls, up, base * s), s) for s in fine]
        v, s = max(sf)
        print(f"{os.path.basename(p):40s} best scale {s:.2f}  match {v:.3f}")


if __name__ == "__main__":
    main()
