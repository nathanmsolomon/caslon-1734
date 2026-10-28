"""Forced alignment of one word: place letter templates by DP, then hand each
ink pixel to a letter. Shared by segment_ocr_italic.py (and usable elsewhere).

Tokens with no template are wildcards: their position is free, scored
neutrally, and they receive the ink between their neighbours that no known
template claims. A wildcard's expected width comes from `wild_w`.
"""
import cv2
import numpy as np

GAP, SIGMA, W_PEN, WILD_SCORE = 3.0, 10.0, 0.1, 0.55


def load_templates(avg, synth=None):
    import os, json
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    up, base = g["up"], g["base_row"]
    T = {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        a = cv2.resize(a, None, fx=1 / up, fy=1 / up, interpolation=cv2.INTER_AREA)
        ys, xs = np.where(a > 0.3)
        if len(ys) == 0:
            continue
        y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
        t = a[y0:y1, x0:x1]
        T[v["ch"]] = dict(img=t, base=base / up - y0, inkw=float(xs.max() - xs.min() + 1))
    return T


def score_maps(dens, names, T, base, xs):
    S = []
    for nm in names:
        if nm not in T:
            S.append(np.full(len(xs), WILD_SCORE, np.float32)); continue
        t = T[nm]; th, tw = t["img"].shape
        ty = int(round(base - t["base"]))
        best = np.full(len(xs), -1.0, np.float32)
        for dy in range(-6, 7):
            yy = ty + dy
            if yy < 0 or yy + th > dens.shape[0]:
                continue
            off = max(0, xs[0] - 2)
            strip = dens[yy:yy + th, off:min(dens.shape[1], xs[-1] + tw + 2)]
            if strip.shape[1] < tw:
                continue
            r = cv2.matchTemplate(strip, t["img"], cv2.TM_CCOEFF_NORMED)[0]
            q = xs - 2 - off
            ok = (q >= 0) & (q < len(r))
            best[ok] = np.maximum(best[ok], r[q[ok]])
        S.append(best)
    return S


def align_word(dens, bw, im, paper, base, wx0, wx1, names, T, hmed, wild_w):
    """Returns list of (name, mask_bbox, crop_image, score) or None."""
    xs = np.arange(wx0 - 8, wx1 + 8)
    def width(nm):
        if nm in T:
            return T[nm]["inkw"]
        if nm.startswith("LIG:") and nm not in wild_w:
            # an unknown ligature: its letters side by side, the f's overlapping
            return sum(T[c]["inkw"] if c in T else 0.5 * hmed for c in nm[4:]) * 0.85
        return wild_w.get(nm, 0.5 * hmed)
    S = score_maps(dens, names, T, base, xs)
    nk, nx = len(names), len(xs)
    D = np.full((nk, nx), -1e9); P = np.zeros((nk, nx), int)
    D[0] = S[0] - W_PEN * ((xs - wx0) / SIGMA) ** 2
    for k in range(1, nk):
        exp = width(names[k - 1]) + GAP
        d = xs[:, None] - xs[None, :]               # d[j, i] = x_j - x_i
        cand = D[k - 1][None, :] - W_PEN * np.minimum(((d - exp) / SIGMA) ** 2, 4.0)
        prev = names[k - 1]
        frac = 0.38 if prev in ("Q",) else 0.4 if prev in ("f", "ſ", "j", "ff", "ſſ", "LIG:ff") else 0.8
        cand[d <= max(2, frac * width(prev))] = -1e9
        P[k] = np.argmax(cand, 1); D[k] = cand[np.arange(nx), P[k]] + S[k]
    endpen = W_PEN * (((xs + width(names[-1])) - wx1) / SIGMA) ** 2
    j = int(np.argmax(D[-1] - endpen))
    pos = [0] * nk
    for k in range(nk - 1, -1, -1):
        pos[k] = j; j = P[k, j]
    known = [S[k][pos[k]] for k in range(nk) if names[k] in T]
    # pixel ownership
    tb = max([T[nm]["base"] for nm in names if nm in T] + [2.3 * hmed])
    td = max([T[nm]["img"].shape[0] - T[nm]["base"] for nm in names if nm in T] + [1.3 * hmed])
    wy0, wy1 = max(0, int(base - max(tb, 2.3 * hmed)) - 4), min(im.shape[0], int(base + max(td, 1.3 * hmed)) + 4)
    ox = max(0, wx0 - 12)
    region = bw[wy0:wy1, ox:wx1 + 12] > 0
    claim = np.zeros((nk,) + region.shape, np.float32)
    CP = 14
    for k, nm in enumerate(names):
        x = xs[pos[k]] - ox
        if nm in T:
            t = T[nm]; soft = cv2.GaussianBlur(np.pad(t["img"], CP), (0, 0), 3.0)
            tx = x - 2 - CP; ty = int(round(base - t["base"])) - wy0 - CP
            sh, sw = soft.shape
            ya, xa, yb, xb = max(0, ty), max(0, tx), min(region.shape[0], ty + sh), min(region.shape[1], tx + sw)
            if yb > ya and xb > xa:
                claim[k, ya:yb, xa:xb] = soft[ya - ty:yb - ty, xa - tx:xb - tx]
        else:
            # wildcard: a weak flat claim over its expected span
            xe = int(x + width(nm))
            r0 = max(0, int(base - 1.9 * hmed) - wy0); r1 = min(region.shape[0], int(base + 1.1 * hmed) - wy0)
            claim[k, r0:r1, max(0, x - 1):max(0, min(region.shape[1], xe + 1))] = 0.3
    owner = np.argmax(claim, 0); owned = claim.max(0) > 0.01
    n_, cl = cv2.connectedComponents(region.astype(np.uint8), connectivity=8)
    for cid in range(1, n_):
        cm = cl == cid; un = cm & ~owned
        if un.any():
            own = owner[cm & owned]
            if own.size:
                owner[un] = np.bincount(own, minlength=nk).argmax(); owned |= un
    # a wildcard keeps only strokes that touch its own x-height band (drops
    # fragments of the lines above and below)
    band = np.zeros(region.shape, bool)
    b0, b1 = max(0, int(base - hmed) - wy0), min(region.shape[0], int(base) - wy0)
    band[b0:b1] = True
    touching = np.zeros(n_ + 1, bool)
    touching[np.unique(cl[band & region])] = True
    out = []
    for k, nm in enumerate(names):
        m = region & owned & (owner == k)
        # drop small detached specks outside the letter's main body (they would
        # shift its ink edges); dots and accents within its width are kept
        nm_, lm_, sm_, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        if nm_ > 2:
            big_ = 1 + int(np.argmax(sm_[1:, 4]))
            bx0, bx1 = sm_[big_, 0], sm_[big_, 0] + sm_[big_, 2]
            for j_ in range(1, nm_):
                if j_ == big_:
                    continue
                cx_ = sm_[j_, 0] + sm_[j_, 2] / 2
                # a wildcard's span is generous, so it can take the full stop or
                # comma after it: keep only its main shape and pieces within its
                # width (letters without a template here, k w x y z, are single
                # connected shapes; a broken hairline lies within the width)
                lim = 1.0 if nm not in T else 0.04
                if sm_[j_, 4] < lim * sm_[big_, 4] and not (bx0 <= cx_ <= bx1):
                    m &= lm_ != j_
        if nm not in T:
            m &= touching[cl]
        if m.sum() < 15:
            out.append(None); continue
        yy, xx = np.where(m)
        gx0, gx1, gy0, gy1 = xx.min() + ox, xx.max() + ox + 1, yy.min() + wy0, yy.max() + wy0 + 1
        pad = 6
        cx0, cy0 = max(0, gx0 - pad), max(0, gy0 - pad)
        crop = im[cy0:gy1 + pad, cx0:gx1 + pad]
        mm = np.zeros_like(crop, bool)
        # copy the owned mask into the crop frame, clamping at the window edges
        sy, sx = cy0 - wy0, cx0 - ox
        ya, xa = max(0, sy), max(0, sx)
        yb, xb = min(m.shape[0], sy + crop.shape[0]), min(m.shape[1], sx + crop.shape[1])
        mm[ya - sy:yb - sy, xa - sx:xb - sx] = m[ya:yb, xa:xb]
        mm = cv2.dilate(mm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        out.append(dict(name=nm, box=(int(gx0), int(gy0), int(gx1), int(gy1)), crop_xy=(int(cx0), int(cy0)),
                        img=np.where(mm, crop, np.uint8(paper)).astype(np.uint8), score=float(S[k][pos[k]])))
    return out, (float(np.mean(known)) if known else None)
