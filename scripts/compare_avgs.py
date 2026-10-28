"""Compare two averaging runs of the same sources: edge sharpness and weight.

Usage: python -I compare_avgs.py <avg_dir_A> <avg_dir_B>

Per letter present in both (with at least 4 impressions): the edge blur width,
i.e. the area where the mean density is between 0.15 and 0.85 divided by the
length of the 0.5 outline (in scan pixels; smaller is sharper), and the ink area
at 0.5 (B / A, to show that the weight is unchanged). Prints the medians and the
letters that changed most.
"""
import sys, os, json
import cv2
import numpy as np


def stats(d, gid, up):
    a = cv2.imread(os.path.join(d, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
    band = ((a > 0.15) & (a < 0.85)).sum()
    m = (a > 0.5).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    per = sum(cv2.arcLength(c, True) for c in cs)
    return band / max(per, 1) / up, m.sum()


def main():
    A, B = sys.argv[1], sys.argv[2]
    ga, gb = (json.load(open(os.path.join(d, "glyphs.json"), encoding="utf-8")) for d in (A, B))
    up = ga["up"]
    rows = []
    for gid, v in ga["glyphs"].items():
        if gid in gb["glyphs"] and v["n"] >= 4:
            wa, aa = stats(A, gid, up)
            wb, ab = stats(B, gid, up)
            rows.append((v["ch"], v["n"], wa, wb, ab / max(aa, 1)))
    if not rows:
        print("no common letters"); return
    wa = np.array([r[2] for r in rows]); wb = np.array([r[3] for r in rows]); ar = np.array([r[4] for r in rows])
    print(f"{len(rows)} letters: edge blur width {np.median(wa):.3f} -> {np.median(wb):.3f} px "
          f"({100 * (np.median(wb / wa) - 1):+.1f}% median per letter); sharper in {(wb < wa).sum()} of {len(rows)}; "
          f"ink area ratio median {np.median(ar):.3f} (range {ar.min():.3f}-{ar.max():.3f})")
    for r in sorted(rows, key=lambda r: r[3] / r[2])[:6]:
        print(f"  {r[0]} n={r[1]}: {r[2]:.3f} -> {r[3]:.3f}, area x{r[4]:.3f}")


if __name__ == "__main__":
    main()
