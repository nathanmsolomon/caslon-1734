"""Which averaging better predicts printings it has not seen? (held-out test)

Usage: python -I holdout_test.py <sources.txt> <out_dir> [maxper]

Fidelity to the 1734 sheet rewards a shape that looks like a typical blurred
impression; the clean fonts aim at the type itself. So each method is judged on
impressions it did not use: one source at a time is held out (each sheet copy,
the 1785 specimen block), the letters are averaged from all the other sources
with congealing off and on, and the averages are compared with every held-out
impression of the same letter.

Comparison per impression: both are cropped to their ink; the average is
thresholded so that its ink area equals the impression's (weight is set from
real impressions anyway, so only shape is judged) and aligned by the best shift
within 3 px; the score is IoU. Prints per fold and overall the median IoU of
each method and how often congealing wins.
"""
import sys, os, json, subprocess
import cv2
import numpy as np

PY = [sys.executable, "-I", "-X", "utf8"]


def density(crop, paper, ink):
    return np.clip((paper - crop.astype(np.float32)) / (paper - ink + 1e-6), 0, 1)


def ink_crop(a, thr):
    ys, xs = np.where(a > thr)
    if len(ys) < 10:
        return None
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def iou_best(A, B):
    h, w = max(A.shape[0], B.shape[0]) + 8, max(A.shape[1], B.shape[1]) + 8
    P = np.zeros((h, w), bool); P[4:4 + A.shape[0], 4:4 + A.shape[1]] = A
    best = 0.0
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            Q = np.zeros((h, w), bool)
            y0, x0 = 4 + dy, 4 + dx
            Q[y0:y0 + B.shape[0], x0:x0 + B.shape[1]] = B[:h - y0, :w - x0]
            u = (P | Q).sum()
            best = max(best, (P & Q).sum() / u if u else 0)
    return best


def load_avg(d):
    g = json.load(open(os.path.join(d, "glyphs.json"), encoding="utf-8"))
    up = g["up"]
    out = {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(d, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        out[v["ch"]] = cv2.resize(a, None, fx=1 / up, fy=1 / up, interpolation=cv2.INTER_AREA)
    return out


def score(avg, held):
    meta = json.load(open(os.path.join(held, "instances.json"), encoding="utf-8"))
    otsu = meta.get("otsu", 128)
    res = []
    for i in meta["instances"]:
        ch = i["ch"]
        if ch not in avg or len(ch) != 1 or not ch.isalnum():
            continue
        im = cv2.imread(os.path.join(held, i["file"]), cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        paper, ink = float(np.percentile(im, 90)), float(np.percentile(im, 1))
        d = density(im, paper, ink)
        imp = ink_crop(d, 0.5)
        if imp is None:
            continue
        A = imp > 0.5
        a = ink_crop(avg[ch], 0.15)
        if a is None:
            continue
        # threshold the average to the impression's ink area
        vals = np.sort(a.ravel())[::-1]
        k = min(len(vals) - 1, int(A.sum()))
        B = a > vals[k]
        res.append(iou_best(A, B))
    return res


def main():
    src, out = sys.argv[1], sys.argv[2]
    maxper = sys.argv[3] if len(sys.argv) > 3 else "120"
    lines = [l.strip() for l in open(src, encoding="utf-8") if l.strip()]
    sheet = [l for l in lines if not l.startswith("+")]
    k85 = [l for l in lines if l.startswith("+") and "k85_" in l.replace("\\", "/")]
    folds = [(os.path.basename(s), [s]) for s in sheet]
    if k85:
        folds.append(("1785 specimen", k85))
    os.makedirs(out, exist_ok=True)
    tot = {"0": [], "1": []}
    for name, held in folds:
        keep = [l for l in lines if l not in held]
        lst = os.path.join(out, f"src_{len(tot['0'])}.txt")
        open(lst, "w", encoding="utf-8").write("\n".join(keep))
        sc = {}
        for cg in ("0", "1"):
            d = os.path.join(out, f"avg_{name.replace(' ', '_')}_cg{cg}")
            if not os.path.exists(os.path.join(d, "glyphs.json")):
                subprocess.run(PY + ["scripts/average.py", d, "@" + lst], env=dict(os.environ, CASLON_CONGEAL=cg, CASLON_MAXPER=maxper),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            avg = load_avg(d)
            sc[cg] = []
            for h in held:
                sc[cg] += score(avg, h.lstrip("+"))
            tot[cg] += sc[cg]
        n = min(len(sc["0"]), len(sc["1"]))
        wins = sum(1 for a, b in zip(sc["0"], sc["1"]) if b > a)
        print(f"{name:22s} {n:5d} impressions  plain {np.median(sc['0']):.4f}  congealed {np.median(sc['1']):.4f}  congealed better on {wins}/{n}", flush=True)
    n = min(len(tot["0"]), len(tot["1"]))
    wins = sum(1 for a, b in zip(tot["0"], tot["1"]) if b > a)
    print(f"{'ALL':22s} {n:5d} impressions  plain {np.median(tot['0']):.4f}  congealed {np.median(tot['1']):.4f}  congealed better on {wins}/{n}")


if __name__ == "__main__":
    main()
