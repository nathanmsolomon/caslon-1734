"""Contact sheet of averaged glyphs: python -I sheet.py <avg_dir> <out.png> [scale]"""
import sys, json
import cv2
import numpy as np

d, outp = sys.argv[1], sys.argv[2]
sc = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35
g = json.load(open(d + "/glyphs.json", encoding="utf-8"))
B = g["base_row"]
# window from the glyphs themselves (taller sizes need more room than Pica)
tops, bots = [], []
for gid in g["glyphs"]:
    a_ = cv2.imread(f"{d}/avg_{gid}.png", -1)
    ys_ = np.where((a_ > 0.25 * 65535).any(1))[0]
    if len(ys_):
        tops.append(ys_[0]); bots.append(ys_[-1])
top, bot = max(0, int(np.percentile(tops, 2)) - 10), int(np.percentile(bots, 98)) + 10
cells = []
for gid, v in g["glyphs"].items():
    a = cv2.imread(f"{d}/avg_{gid}.png", -1).astype(np.float32) / 65535
    ys, xs = np.where(a > 0.25)
    x0, x1 = max(0, xs.min() - 20), xs.max() + 20
    c = 255 - (np.clip(a[top:bot, x0:x1] * 1.0, 0, 1) * 255).astype(np.uint8)
    c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
    cv2.line(c, (0, int((B - top) * sc)), (c.shape[1], int((B - top) * sc)), (230, 180, 120), 1)
    cv2.putText(c, str(v["n"]), (2, c.shape[0] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)
    cells.append(c)
Wmax = 1500
rows, row, w = [], [], 0
for c in cells:
    if w + c.shape[1] + 6 > Wmax:
        rows.append(row); row, w = [], 0
    row.append(c); w += c.shape[1] + 6
rows.append(row)
H = cells[0].shape[0]
out = []
for r in rows:
    strip = np.hstack([np.pad(c, ((4, 4), (3, 3), (0, 0)), constant_values=255) for c in r])
    out.append(np.pad(strip, ((0, 0), (0, Wmax - strip.shape[1]), (0, 0)), constant_values=255))
cv2.imwrite(outp, np.vstack(out))
