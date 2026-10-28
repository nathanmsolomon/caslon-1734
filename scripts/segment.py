"""Segment a specimen block into glyph instances and label them from a transcription.

Usage: python -I segment.py <page.png> <x0> <y0> <x1> <y1> <transcription.txt> <out_dir>

Transcription: one printed line per text line. Ligature sorts are written in
{braces}, e.g. {ſt}. Spaces separate words. Each glyph instance is saved as a
grayscale crop with its geometry (ink bbox, baseline) in instances.json.
"""
import sys, os, json, re
import cv2
import numpy as np


def tokens(line):
    """Words -> list of glyph names (ligatures kept as one glyph)."""
    words = []
    for w in line.split():
        words.append(re.findall(r"\{[^}]+\}|.", w))
    return words


def _merge(a, b):
    g = dict(parts=a["parts"] + b["parts"], x0=min(a["x0"], b["x0"]), x1=max(a["x1"], b["x1"]))
    g["y0"] = min(a["y0"], b["y0"]); g["y1"] = max(a["y1"], b["y1"])
    return g


_RATIOS = None


def _ratios():
    global _RATIOS
    if _RATIOS is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work", "width_ratios.json")
        _RATIOS = json.load(open(p, encoding="utf-8"))["ratio"] if os.path.exists(p) else {}
    return _RATIOS


def repair(w, target, bw, lab, labels=None):
    """Fix a word's glyph list to the transcribed count: drop specks, merge
    broken letters, split touching letters. With labels, the glyph to split is
    the one most too wide for the letter it would carry, and it is cut where the
    two letters' expected widths meet (refined to the thinnest nearby column)."""
    w = list(w)
    R = _ratios()
    caps_h = [g["y1"] - g["y0"] for g, c in zip(w, labels or []) if c in "EFHILT"]
    lows_h = [g["y1"] - g["y0"] for g, c in zip(w, labels or []) if c in "xzvwnmuo"]
    area = lambda g: sum(p["a"] for p in g["parts"])
    while len(w) > target:
        specks = [k for k, g in enumerate(w[:-1]) if area(g) < 60]
        if specks:
            w.pop(specks[0]); continue
        gaps = [w[k + 1]["x0"] - w[k]["x1"] for k in range(len(w) - 1)]
        k = int(np.argmin(gaps))
        if labels and len(labels) == target and R and (caps_h or lows_h) and len(w) == target + 1:
            # choose the merge whose resulting widths best fit the labels
            ch_ = float(np.median(caps_h)) if caps_h else None
            xh_ = float(np.median(lows_h)) if lows_h else None
            def expw(c):
                r = R.get(c)
                return None if r is None else r * (ch_ if c.isupper() and ch_ else xh_ if xh_ else ch_)
            best = None
            for k_ in range(len(w) - 1):
                cand = w[:k_] + [_merge(w[k_], w[k_ + 1])] + w[k_ + 2:]
                cost = sum(abs(np.log(max(1, g["x1"] - g["x0"]) / e)) for g, c in zip(cand, labels) if (e := expw(c)))
                if best is None or cost < best[0]:
                    best = (cost, k_)
            k = best[1]
        w[k:k + 2] = [_merge(w[k], w[k + 1])]
    while len(w) < target:
        meds = np.median([g["x1"] - g["x0"] for g in w])
        frac = None
        if labels and len(labels) == target and R and (caps_h or lows_h):
            ch_ = float(np.median(caps_h)) if caps_h else None
            xh_ = float(np.median(lows_h)) if lows_h else None
            def expw(c):
                r = R.get(c)
                if r is None:
                    return meds
                return r * (ch_ if c.isupper() and ch_ else xh_ if xh_ else ch_)
            # prefix labelling up to each candidate glyph
            scores = [(g["x1"] - g["x0"]) / max(1.0, expw(labels[k_])) if k_ < len(labels) else 0 for k_, g in enumerate(w)]
            k = int(np.argmax(scores))
            if k + 1 < len(labels):
                a_, b_ = expw(labels[k]), expw(labels[k + 1])
                frac = a_ / (a_ + b_)
        else:
            k = int(np.argmax([(g["x1"] - g["x0"]) / meds for g in w]))
        g = w[k]
        if len(g["parts"]) != 1:
            break
        p = g["parts"][0]
        m = lab[p["y"]:p["y"] + p["h"], p["x"]:p["x"] + p["w"]] == p["i"]
        col = m.sum(0).astype(float)
        if frac is not None:
            c0 = frac * len(col); lo, hi = int(c0 - 0.12 * len(col)), int(c0 + 0.12 * len(col))
            lo, hi = max(1, lo), min(len(col) - 1, hi)
        else:
            lo, hi = int(0.2 * len(col)), int(0.8 * len(col))
        if hi <= lo:
            break
        cut = lo + int(np.argmin(col[lo:hi]))
        if not m[:, :cut].any() or not m[:, cut:].any():
            break
        out = []
        for sx0, sx1 in ((0, cut), (cut, len(col))):
            sub = m[:, sx0:sx1]
            ys = np.where(sub.any(1))[0]
            q = dict(x=p["x"] + sx0, y=p["y"] + int(ys[0]), w=sx1 - sx0, h=int(ys[-1] - ys[0] + 1),
                     a=int(sub.sum()), i=p["i"], clip=(p["x"] + sx0, p["x"] + sx1))
            out.append(dict(parts=[q], x0=q["x"], x1=q["x"] + q["w"], y0=q["y"], y1=q["y"] + q["h"]))
        w[k:k + 1] = out
    return w


def main():
    page, x0, y0, x1, y1, trans, out = sys.argv[1:8]
    x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
    im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)[y0:y1, x0:x1]
    os.makedirs(out, exist_ok=True)
    lines_t = [l.rstrip("\n") for l in open(trans, encoding="utf-8") if l.strip()]

    blur = cv2.GaussianBlur(im, (3, 3), 0)
    thr, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(bw, 8)
    comps = [dict(x=s[0], y=s[1], w=s[2], h=s[3], a=s[4], i=k) for k, s in enumerate(stats) if k and s[4] >= 12]

    # text lines: cluster the bottoms of mid-sized components (mostly baseline-sitting letters)
    hs = sorted(c["h"] for c in comps if c["h"] > 10)
    hmed = hs[len(hs) // 2]
    bots = sorted(c["y"] + c["h"] for c in comps if 0.7 * hmed < c["h"] < 1.8 * hmed)
    groups = [[bots[0]]]
    for b in bots[1:]:
        if b - groups[-1][-1] > 0.5 * hmed:
            groups.append([b])
        else:
            groups[-1].append(b)
    groups = [g for g in groups if len(g) >= 4]
    centers = [float(np.median(g)) - 0.5 * hmed for g in groups]  # x-height midline
    print("lines", len(centers), "transcribed lines", len(lines_t))
    if len(centers) != len(lines_t):
        print("LINE COUNT MISMATCH", centers)
        sys.exit(1)
    cent_arr = np.array(centers)
    for c in comps:
        c["line"] = int(np.argmin(np.abs(cent_arr - (c["y"] + c["h"] / 2))))

    report, instances = [], []
    for li, tline in enumerate(lines_t):
        cs = [c for c in comps if c["line"] == li]
        cs.sort(key=lambda c: c["x"])
        # group components overlapping horizontally (i-dots, colons, accents)
        glyphs = []
        for c in cs:
            if glyphs:
                g = glyphs[-1]
                ov = min(g["x1"], c["x"] + c["w"]) - max(g["x0"], c["x"])
                if ov > 0.5 * min(c["w"], g["x1"] - g["x0"]):
                    g["parts"].append(c)
                    g["x0"] = min(g["x0"], c["x"]); g["x1"] = max(g["x1"], c["x"] + c["w"])
                    continue
            glyphs.append(dict(parts=[c], x0=c["x"], x1=c["x"] + c["w"]))
        for g in glyphs:
            g["y0"] = min(p["y"] for p in g["parts"]); g["y1"] = max(p["y"] + p["h"] for p in g["parts"])
        # words by gap size
        gaps = [glyphs[k + 1]["x0"] - glyphs[k]["x1"] for k in range(len(glyphs) - 1)]
        twords = tokens(tline)
        nwords = len(twords)
        # the nwords-1 largest gaps are word spaces
        order = sorted(range(len(gaps)), key=lambda k: -gaps[k])[: nwords - 1]
        cuts = sorted(order)
        gw, start = [], 0
        for k in cuts:
            gw.append(glyphs[start:k + 1]); start = k + 1
        gw.append(glyphs[start:])
        # baseline: robust line fit through the bottoms of flat-serifed letters,
        # so a slightly rotated sheet doesn't smear the averages vertically
        # repair mis-segmented words first, so the baseline fit can use them too
        rep = []
        for wi, (w, t) in enumerate(zip(gw, twords)):
            rep.append(len(w) != len(t))
            if rep[-1]:
                gw[wi] = repair(w, len(t), bw, lab, [c.strip("{}") for c in t])
        flat = [((g["x0"] + g["x1"]) / 2, g["y1"]) for w, t in zip(gw, twords) if len(w) == len(t)
                for g, ch in zip(w, t) if ch.strip("{}") in "imnrhkluxzABDEFHIKLMNPRTXYZÆ"]
        if len(flat) < 3:
            flat = [((g["x0"] + g["x1"]) / 2, g["y1"]) for g in glyphs]
        fx, fy = np.array(flat, float).T
        coef = np.polyfit(fx, fy, 1) if len(fx) > 1 else np.array([0.0, fy[0]])
        for _ in range(3):
            res = fy - np.polyval(coef, fx)
            keep = np.abs(res) < max(2.0, 2.5 * np.median(np.abs(res)))
            if keep.sum() >= 3:
                coef = np.polyfit(fx[keep], fy[keep], 1)
        # the printed line is not always straight (a bent line of type, a curled
        # sheet): correct the straight fit by the median residual of the nearest
        # flat-bottomed letters
        res = fy - np.polyval(coef, fx)
        def base_at(x, coef=coef, fx=fx, res=res):
            near = np.argsort(np.abs(fx - x))[:5]
            return float(np.polyval(coef, x) + (np.median(res[near]) if len(fx) >= 5 else 0.0))
        xh = [g["y1"] - g["y0"] for w, t in zip(gw, twords) if len(w) == len(t)
              for g, ch in zip(w, t) if ch in "xzvwnmuo"]
        for wi, (w, t) in enumerate(zip(gw, twords)):
            repaired = rep[wi]
            if len(w) != len(t):
                report.append(f"line {li+1} word {wi+1} '{''.join(t)}': {len(w)} glyphs vs {len(t)} chars")
                if not w:
                    continue
                wx0, wx1 = max(0, w[0]["x0"] - 8), w[-1]["x1"] + 8
                wy0, wy1 = max(0, min(g["y0"] for g in w) - 8), max(g["y1"] for g in w) + 8
                dbg = cv2.cvtColor(im[wy0:wy1, wx0:wx1], cv2.COLOR_GRAY2BGR)
                for k, g in enumerate(w):
                    col = [(0, 0, 255), (0, 160, 0), (255, 0, 0)][k % 3]
                    cv2.rectangle(dbg, (g["x0"] - wx0, g["y0"] - wy0), (g["x1"] - wx0, g["y1"] - wy0), col, 1)
                os.makedirs(os.path.join(out, "mismatch"), exist_ok=True)
                cv2.imwrite(os.path.join(out, "mismatch", f"L{li+1}W{wi+1}.png"), dbg)
                continue
            for pos, (g, ch) in enumerate(zip(w, t)):
                name = ch.strip("{}")
                pad = 6
                gx0, gy0 = max(0, g["x0"] - pad), max(0, g["y0"] - pad)
                gx1, gy1 = g["x1"] + pad, g["y1"] + pad
                crop = im[gy0:gy1, gx0:gx1]
                # mask out ink from neighbouring glyphs
                m = np.zeros_like(crop, dtype=bool)
                for p in g["parts"]:
                    mm = lab[gy0:gy1, gx0:gx1] == p["i"]
                    if "clip" in p:
                        xs = np.arange(gx0, gx0 + mm.shape[1])
                        mm &= ((xs >= p["clip"][0]) & (xs < p["clip"][1]))[None, :]
                    m |= mm
                m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                clean = np.where(m, crop, np.uint8(np.median(im))).astype(np.uint8)
                idx = len(instances)
                fn = f"{idx:04d}.png"
                cv2.imwrite(os.path.join(out, fn), clean)
                instances.append(dict(file=fn, ch=name, line=li, word=wi, pos=pos, nword=len(t), repaired=repaired,
                                      x0=int(g["x0"]) + x0, x1=int(g["x1"]) + x0,
                                      y0=int(g["y0"]) + y0, y1=int(g["y1"]) + y0,
                                      crop=[int(gx0) + x0, int(gy0) + y0],
                                      baseline=base_at((g["x0"] + g["x1"]) / 2) + y0, slope=float(coef[0]), xheight=float(np.median(xh)) if xh else None))
    json.dump(dict(instances=instances, otsu=float(thr)), open(os.path.join(out, "instances.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(instances), "instances")
    print("\n".join(report) if report else "all words matched")


if __name__ == "__main__":
    main()
