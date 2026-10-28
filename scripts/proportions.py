"""Letter proportions of an averaged fount, independent of scan resolution.

Usage: python -I proportions.py <avg_dir> [<avg_dir> ...]

From each average (thresholded at half density): x-height, ascender and
descender heights and the widths of common letters, all divided by the
x-height. Caslon's sizes are separate cuts, so these ratios tell them apart
where absolute size (unknown scan ppi) cannot.
"""
import sys, os, json
import cv2
import numpy as np

HEIGHT = {"asc": "bdhkl", "desc": "pq"}
WIDTH = "nmoeachsu"


def measure(avg):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    base = g["base_row"]
    box = {}
    for gid, v in g["glyphs"].items():
        ch = v["ch"]
        if len(ch) != 1 or ch not in "xnuvz" + "".join(HEIGHT.values()) + WIDTH:
            continue
        a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        ys, xs = np.where(a > 0.5)
        if len(ys) < 20:
            continue
        box[ch] = (base - ys.min(), ys.max() - base, xs.max() - xs.min() + 1, v["n"])
    xh = np.median([box[c][0] for c in "xnuvz" if c in box])
    out = {"asc": np.median([box[c][0] for c in HEIGHT["asc"] if c in box]) / xh,
           "desc": np.median([box[c][1] for c in HEIGHT["desc"] if c in box]) / xh}
    for c in WIDTH:
        if c in box:
            out["w_" + c] = box[c][2] / xh
    return xh / g["up"], out


if __name__ == "__main__":
    keys = ["asc", "desc"] + ["w_" + c for c in WIDTH]
    print(f"{'source':28s} {'xh px':>6s} " + " ".join(f"{k:>6s}" for k in keys))
    for d in sys.argv[1:]:
        xh, r = measure(d)
        print(f"{os.path.basename(d.rstrip('/'))[:28]:28s} {xh:6.1f} " + " ".join(f"{r.get(k, float('nan')):6.3f}" for k in keys))
