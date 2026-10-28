"""Match the display alphabets of a later Caslon specimen page to the 1734 faces.

Usage: python -I titling_match.py <page.jpg> <ppi> "<row text>|<row text>|..." [out_dir]

The large sizes (Five/Four Lines Pica, Two Lines ...) are shown as capital and
lowercase rows. Rows are found from the big ink components (each letter one
component, merged where they overlap in x); each row text given (in reading
order, rows of other glyphs such as Greek are skipped) is assigned to the next
row with that many letters. Every 1734 display and titling face with templates
for the row's letters is compared: the scale is fixed by the scan resolution
(ppi/600), and each letter is matched by shift-tolerant NCC after the template
is scaled to the letter's measured height. Printed per row: the best faces
with median NCC and the height ratio (1.00 = same body). With out_dir, each
row's letters are saved in instances.json format (one folder per row) for
averaging into the face it matches.
"""
import sys, os, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from align_core import load_templates  # noqa: E402

FACES = [(f"titling{i}", f"work/titling{i}_avgF") for i in range(1, 8)] + \
        [("tle", "work/tle_roman_avgF"), ("tlgp", "work/tlgp_roman_avgF"), ("fc", "work/fc_roman_avgF"),
         ("dp", "work/dp_roman_avgF"), ("gp", "work/gp_roman_avgF")]


def inkh(img):
    ys = np.where((img > 0.3).any(1))[0]
    return ys[-1] - ys[0] + 1 if len(ys) else 0


def ncc(g, t):
    p = 10
    w = np.pad(g, ((p + max(0, t.shape[0] - g.shape[0]),) * 2, (p + max(0, t.shape[1] - g.shape[1]),) * 2))
    return float(cv2.matchTemplate(w, t, cv2.TM_CCOEFF_NORMED).max())


def main():
    page, ppi, texts = sys.argv[1], float(sys.argv[2]), sys.argv[3].split("|")
    out = sys.argv[4] if len(sys.argv) > 4 else None
    k = 600.0 / ppi
    im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)
    im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    paper, ink = float(np.percentile(im, 90)), float(np.percentile(im, 1))
    dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
    bw = (dens > 0.45).astype(np.uint8)
    otsu = float(cv2.threshold(cv2.GaussianBlur(im, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[0])
    n, lab, st, _ = cv2.connectedComponentsWithStats(bw, 8)
    H = im.shape[0]
    comps = [list(s) + [j + 1] for j, s in enumerate(st[1:]) if s[3] > 0.012 * H and s[4] > 200 and s[2] < 0.5 * im.shape[1]]
    # rows: components whose vertical centres are close
    comps.sort(key=lambda s: s[1] + s[3] / 2)
    rows = []
    for s in comps:
        cy = s[1] + s[3] / 2
        if rows and abs(cy - rows[-1]["cy"]) < 0.35 * rows[-1]["h"]:
            r = rows[-1]; r["c"].append(s); r["cy"] = np.mean([c[1] + c[3] / 2 for c in r["c"]]); r["h"] = max(r["h"], s[3])
        else:
            rows.append(dict(c=[s], cy=cy, h=s[3]))
    for r in rows:
        r["c"].sort(key=lambda s: s[0])
        gl = []
        for s in r["c"]:
            if gl and min(gl[-1][2], s[0] + s[2]) - max(gl[-1][0], s[0]) > 0.3 * min(s[2], gl[-1][2] - gl[-1][0]):
                g = gl[-1]; gl[-1] = [min(g[0], s[0]), min(g[1], s[1]), max(g[2], s[0] + s[2]), max(g[3], s[1] + s[3]), g[4] + [s[5]]]
            else:
                gl.append([s[0], s[1], s[0] + s[2], s[1] + s[3], [s[5]]])
        r["g"] = gl
    T = {nm: load_templates(d) for nm, d in FACES if os.path.exists(f"{d}/glyphs.json")}
    ri = 0
    ratio = 1.0     # size of this block relative to its 1734 face (carried to the block's later rows)
    for ti, text in enumerate(texts):
        while ri < len(rows) and len(rows[ri]["g"]) != len(text):
            ri += 1
        if ri >= len(rows):
            print(f"{text}: no row with {len(text)} letters"); continue
        r = rows[ri]; ri += 1
        res = []
        for nm, tp in T.items():
            sc, rat = [], []
            for (x0, y0, x1, y1, _), ch in zip(r["g"], text):
                if ch not in tp:
                    continue
                g = dens[y0:y1, x0:x1]
                th = inkh(tp[ch]["img"])
                f = (y1 - y0) / th
                t = cv2.resize(tp[ch]["img"], None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                sc.append(ncc(g, t)); rat.append(f)
            if len(sc) >= 2:
                res.append((float(np.median(sc)), nm, len(sc), float(np.median(rat))))
        res.sort(reverse=True)
        if res and res[0][0] >= 0.93 and res[0][1].startswith("titling") and abs(res[0][3] - 1) < 0.08:
            ratio = res[0][3]
        print(f"{text:14s} " + " | ".join(f"{nm} {v:.3f} x{rt:.2f} ({c})" for v, nm, c, rt in res[:4]), flush=True)
        if out:
            # editions differ in size by a few percent (paper shrinkage, scan
            # resolution): resample the row to the 1734 size before saving
            f_ = 1.0 / ratio
            imr = cv2.resize(im, None, fx=f_, fy=f_, interpolation=cv2.INTER_CUBIC)
            labr = cv2.resize(lab.astype(np.float32), None, fx=f_, fy=f_, interpolation=cv2.INTER_NEAREST).astype(np.int32)
            d = os.path.join(out, f"row{ti}")
            os.makedirs(d, exist_ok=True)
            inst = []
            base = f_ * float(np.median([g[3] for g, ch in zip(r["g"], text) if ch not in "QJgjpqy"] or [r["g"][0][3]]))
            for pos, ((x0, y0, x1, y1, ids), ch) in enumerate(zip(r["g"], text)):
                x0, y0, x1, y1 = [int(round(v * f_)) for v in (x0, y0, x1, y1)]
                pad = 8
                cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
                crop = imr[cy0:y1 + pad, cx0:x1 + pad]
                # only this letter's own components (a kerned f reaches over the next letter)
                own = np.isin(labr[cy0:y1 + pad, cx0:x1 + pad], ids).astype(np.uint8)
                m = cv2.dilate(own, np.ones((5, 5), np.uint8)).astype(bool)
                fn = f"{pos:04d}.png"
                cv2.imwrite(os.path.join(d, fn), np.where(m, crop, np.uint8(paper)).astype(np.uint8))
                inst.append(dict(file=fn, ch=ch, line=0, word=0, pos=pos, nword=len(text), x0=int(x0), x1=int(x1),
                                 y0=int(y0), y1=int(y1), crop=[int(cx0), int(cy0)], baseline=base, slope=0.0))
            json.dump(dict(instances=inst, otsu=otsu, source=os.path.basename(page)), open(os.path.join(d, "instances.json"), "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
