"""Like-for-like fidelity: IoU of font glyph vs each real impression, measured
exactly like impression-vs-impression (crop level, sub-pixel aligned).
Usage: python -I fidelity.py <font.otf> <pitch_px> <instances_dir> [...]"""
import sys, json, os, itertools, random
import cv2, numpy as np
from fontTools.ttLib import TTFont
sys.path.insert(0, os.path.dirname(__file__))
from proof import PolyPen, NAMES, LIGATURES

def iou_aligned(A, B):
    H = max(A.shape[0], B.shape[0]) + 12; W = max(A.shape[1], B.shape[1]) + 12
    pa = np.zeros((H, W), np.float32); pb = pa.copy()
    pa[:A.shape[0], :A.shape[1]] = A; pb[:B.shape[0], :B.shape[1]] = B
    (dx, dy), _ = cv2.phaseCorrelate(pa, pb)
    pb = cv2.warpAffine(pb, np.float32([[1, 0, -dx], [0, 1, -dy]]), (W, H)) > 0.5
    pa = pa > 0.5
    return (pa & pb).sum() / ((pa | pb).sum() + 1e-9)

def render(gs, name, s, SS=8):
    pp = PolyPen(gs); gs[name].draw(pp)
    pts = np.concatenate([np.array(p) for p in pp.polys])
    xmin, ymin = pts.min(0); xmax, ymax = pts.max(0)
    W = int((xmax - xmin) * s) + 4; H = int((ymax - ymin) * s) + 4
    m = np.zeros((H * SS, W * SS), np.uint8)
    for p in pp.polys:
        q = np.array([[((x - xmin) * s + 2) * SS, ((ymax - y) * s + 2) * SS] for x, y in p], np.int32)
        t = np.zeros_like(m); cv2.fillPoly(t, [q], 255); m ^= t
    return (cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA) > 127).astype(np.float32)

fontp, pitch, dirs = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
gs = TTFont(fontp).getGlyphSet(); s = pitch / 1000
random.seed(0)
font_iou, ref_iou, per = [], [], {}
for d in dirs:
    meta = json.load(open(d + "/instances.json", encoding="utf-8"))
    by = {}
    for i in meta["instances"]:
        by.setdefault(i["ch"], []).append(i)
    for ch, L in by.items():
        nm = NAMES.get(ch, ch)
        if nm not in gs or ch in ",.-:":
            continue
        g = render(gs, nm, s)
        ims = [(cv2.GaussianBlur(cv2.imread(f"{d}/{i['file']}", 0), (3, 3), 0) < meta["otsu"]).astype(np.float32) for i in L[:12]]
        f = [iou_aligned(g, im) for im in ims]
        font_iou += f; per.setdefault(ch, []).extend(f)
        pairs = list(itertools.combinations(range(len(ims)), 2))
        for a, b in random.sample(pairs, min(10, len(pairs))):
            ref_iou.append(iou_aligned(ims[a], ims[b]))
print(f"font vs impression       IoU median {np.median(font_iou):.3f}")
print(f"impression vs impression IoU median {np.median(ref_iou):.3f}")
worst = sorted(per.items(), key=lambda kv: np.median(kv[1]))[:10]
print("lowest:", ", ".join(f"{c} {np.median(v):.2f}" for c, v in worst))
