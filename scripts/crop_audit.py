"""Audit for letters cut off by cropping.

Usage: python -I crop_audit.py <config_name> [...]

For every instance that went into a size's final average, checks whether ink
reaches the edge of its crop (top, bottom, left, right), and whether the averaged
glyph has ink at the vertical clip lines average.py applies (-0.85 / +0.36 of
the line pitch from the baseline). A letter whose ink touches an edge in many
impressions is probably being truncated. Prints the worst letters per size.
"""
import sys, os, json, glob
import cv2
import numpy as np


def touches(img, thr):
    d = img < thr
    return d[0, :].sum() >= 2, d[-1, :].sum() >= 2, d[:, 0].sum() >= 2, d[:, -1].sum() >= 2


def main():
    for nm in sys.argv[1:]:
        R = json.load(open(f"work/{nm}_result.json", encoding="utf-8"))
        srcs = [l.strip().lstrip("+") for l in open(f"work/{nm}_sources.txt")] if os.path.exists(f"work/{nm}_sources.txt") else []
        if not srcs:
            srcs = sorted(glob.glob(f"work/{nm}_pfs_p*")) or sorted(glob.glob(f"work/{nm}_fin_p*")) or sorted(glob.glob(f"work/{nm}_al_p*"))
        stats = {}
        for d in srcs:
            if not os.path.exists(f"{d}/instances.json"):
                continue
            meta = json.load(open(f"{d}/instances.json", encoding="utf-8"))
            book = os.path.basename(d).startswith("n")
            for i in meta["instances"]:
                im = cv2.imread(os.path.join(d, i["file"]), cv2.IMREAD_GRAYSCALE)
                if im is None or im.size == 0:
                    continue
                thr = (float(np.percentile(im, 80)) + float(np.percentile(im, 2))) / 2
                t, b, l, r = touches(im, thr)
                s = stats.setdefault((i["ch"], book), [0, 0, 0, 0, 0])
                s[0] += 1; s[1] += t; s[2] += b; s[3] += l; s[4] += r
        bad = []
        for (ch, book), (n, t, b, l, r) in stats.items():
            if n >= 3:
                worst = max(t, b, l, r) / n
                if worst >= 0.25:
                    side = "top bottom left right".split()[int(np.argmax([t, b, l, r]))]
                    bad.append((worst, ch, "book" if book else "sheet", n, side))
        bad.sort(reverse=True)
        print(f"== {nm}: {len(bad)} letters touch a crop edge in >=25% of impressions")
        for w, ch, src, n, side in bad[:12]:
            print(f"   {ch!r:7s} {src:5s} {side:6s} {w:.0%} of {n}")


if __name__ == "__main__":
    main()
