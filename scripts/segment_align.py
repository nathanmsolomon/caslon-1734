"""Forced alignment of a transcribed block: place each word's letter templates
by dynamic programming, so touching letters (italic joins, ink spread) are
separated by shape instead of by gaps.

Usage: python -I segment_align.py <block.png> <x0> <y0> <x1> <y1> <transcription.txt> <avg_dir> <out_dir>

Lines and word spans are found as in segment.py (word spaces = the largest
gaps). Within a word, template k (from avg_dir) is scored at every x by NCC
on ink density with its baseline on the fitted line baseline (±2 px). The DP
picks x_1 < ... < x_n maximising total score minus a penalty on deviations of
each step from the template's ink width plus a nominal sidebearing gap. Each
pixel of the word then goes to the placed template that claims it most.
"""
import sys, os, json, re
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from segment import tokens  # noqa: E402

BORROW = {}     # name -> (avg_dir, scale): template borrowed from another size
SYNTH = {}      # name -> component glyphs, set from the command line (--synth ſſi=ſ+ſ+i)
GAP = 3.0       # nominal ink gap between neighbours (px at 600 ppi)
SIGMA = 10.0    # tolerance on that gap (px)
W_PEN = 0.1     # weight of the spacing prior relative to NCC (a tie-breaker, not a constraint)


def load_templates(avg):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    up, base = g["up"], g["base_row"]
    T = {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        a = cv2.resize(a, None, fx=1 / up, fy=1 / up, interpolation=cv2.INTER_AREA)
        ys, xs = np.where(a > 0.3)
        if len(ys) == 0:
            continue      # an average with no solid ink is unusable as a template
        y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
        t = a[y0:y1, x0:x1]
        T[v["ch"]] = dict(img=t, base=base / up - y0, inkw=float(xs.max() - xs.min() + 1), mask=t > 0.3)
    for name, (d_, sc_) in BORROW.items():
        force = name.endswith("!")
        name = name.rstrip("!")
        if name in T and not force:
            continue
        o = load_templates.__wrapped__(d_) if hasattr(load_templates, "__wrapped__") else None
        g2 = json.load(open(os.path.join(d_, "glyphs.json"), encoding="utf-8"))
        for gid2, v2 in g2["glyphs"].items():
            if v2["ch"] == name:
                a2 = cv2.imread(os.path.join(d_, f"avg_{gid2}.png"), -1).astype(np.float32) / 65535
                f2 = sc_ / g2["up"]
                a2 = cv2.resize(a2, None, fx=f2, fy=f2, interpolation=cv2.INTER_AREA)
                ys2, xs2 = np.where(a2 > 0.3)
                y0b, x0b = ys2.min() - 2, xs2.min() - 2
                t2 = a2[y0b:ys2.max() + 3, x0b:xs2.max() + 3]
                T[name] = dict(img=t2, base=g2["base_row"] * f2 - y0b, inkw=float(xs2.max() - xs2.min() + 1), mask=t2 > 0.3)
    # stand-in templates for glyphs whose first-pass average is unusable:
    # compose them from good parts (used only to find the glyph; the final
    # shape still comes from the real impressions)
    for name, parts in SYNTH.items():
        if not all(p in T for p in parts):
            continue
        hb = max(T[p]["base"] for p in parts)
        hd = max(T[p]["img"].shape[0] - T[p]["base"] for p in parts)
        H = int(np.ceil(hb + hd)); x = 0; pieces = []
        for p in parts:
            pieces.append((p, x)); x += int(T[p]["inkw"] + GAP)
        W = x + 8
        img = np.zeros((H, W), np.float32)
        for p, px in pieces:
            t = T[p]["img"]; ty = int(round(hb - T[p]["base"]))
            hh, ww = min(t.shape[0], H - ty), min(t.shape[1], W - px)
            img[ty:ty + hh, px:px + ww] = np.maximum(img[ty:ty + hh, px:px + ww], t[:hh, :ww])
        T[name] = dict(img=img, base=hb, inkw=float(x - GAP), mask=img > 0.3)
    return T


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for a in sys.argv[1:]:
        if a.startswith("--borrow"):
            # --borrow=Q:other_avg_dir:scale  (a template from another size, used only to locate)
            for spec in a.split("=", 1)[1].split(","):
                ch_, d_, sc_ = spec.split(":", 2)[0], spec.split(":")[1] + (":" + spec.split(":")[2] if spec.count(":") > 2 else ""), None
                parts_ = spec.split(":"); ch_, sc_ = parts_[0], float(parts_[-1]); d_ = ":".join(parts_[1:-1])
                BORROW[ch_] = (d_, sc_)
    for a in sys.argv[1:]:
        if a.startswith("--synth"):
            for spec in a.split("=", 1)[1].split(","):
                k, v = spec.split(":"); SYNTH[k] = v.split("+")
    page, x0, y0, x1, y1, trans, avg, out = args[:8]
    x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
    im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)[y0:y1, x0:x1]
    # pad so templates near the block edge can still be placed
    PADB = 60
    im = cv2.copyMakeBorder(im, PADB, PADB, PADB, PADB, cv2.BORDER_CONSTANT, value=int(np.percentile(im, 80)))
    x0 -= PADB; y0 -= PADB
    os.makedirs(out, exist_ok=True)
    T = load_templates(avg)
    lines_t = [l.rstrip("\n") for l in open(trans, encoding="utf-8") if l.strip()]
    blur = cv2.GaussianBlur(im, (3, 3), 0)
    thr, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    paper, ink = float(np.percentile(im, 80)), float(np.percentile(im, 1))
    dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    comps = [dict(x=s[0], y=s[1], w=s[2], h=s[3], a=s[4], i=k) for k, s in enumerate(stats) if k and s[4] >= 12]
    hs = sorted(c["h"] for c in comps if c["h"] > 10); hmed = hs[len(hs) // 2]
    bots = sorted(c["y"] + c["h"] for c in comps if 0.7 * hmed < c["h"] < 1.8 * hmed)
    groups = [[bots[0]]]
    for b in bots[1:]:
        (groups.append([b]) if b - groups[-1][-1] > 0.5 * hmed else groups[-1].append(b))
    groups = [g for g in groups if len(g) >= 4]
    centers = np.array([float(np.median(g)) - 0.5 * hmed for g in groups])
    if len(centers) != len(lines_t):
        # fallback: the line count is known, so take that many peaks of the
        # smoothed ink profile (tight small sizes blur the gaps between lines)
        nl = len(lines_t)
        sig = min(max(2.0, hmed / 4), (bw.shape[0] - 120) / (nl + 1) / 5)
        prof = cv2.GaussianBlur((bw > 0).sum(1).astype(np.float32).reshape(-1, 1), (1, 0), sig).ravel()
        mind = 0.6 * (prof.size - 120) / (nl + 1)
        cand = [y for y in range(1, prof.size - 1) if prof[y] >= prof[y - 1] and prof[y] >= prof[y + 1] and prof[y] > 0]
        cand.sort(key=lambda y: -prof[y]); pk = []
        for y in cand:
            if all(abs(y - q) > mind for q in pk):
                pk.append(y)
            if len(pk) == nl:
                break
        if len(pk) != nl and len(pk) >= max(2, nl // 2):
            # extend the measured pitch to the expected number of lines (a short
            # alphabet line can merge into the shoulder of the line above)
            pk = sorted(pk); pitch = float(np.median(np.diff(pk)))
            grid = [pk[0] + pitch * k for k in range(nl)]
            pk = [min(pk, key=lambda q: abs(q - g)) if min(abs(q - g) for q in pk) < pitch / 3 else g for g in grid]
        if len(pk) != nl:
            print("LINE COUNT MISMATCH", len(centers), nl); sys.exit(1)
        centers = np.array(sorted(pk), float)
    for c in comps:
        c["line"] = int(np.argmin(np.abs(centers - (c["y"] + c["h"] / 2))))

    instances, report = [], []
    for li, tline in enumerate(lines_t):
        cs = sorted([c for c in comps if c["line"] == li], key=lambda c: c["x"])
        # coarse glyph groups only to find word spaces
        gl = []
        for c in cs:
            if gl and min(gl[-1][1], c["x"] + c["w"]) - max(gl[-1][0], c["x"]) > 0:
                gl[-1] = (min(gl[-1][0], c["x"]), max(gl[-1][1], c["x"] + c["w"]), gl[-1][2] + [c])
            else:
                gl.append((c["x"], c["x"] + c["w"], [c]))
        twords = tokens(tline)
        gaps = [gl[k + 1][0] - gl[k][1] for k in range(len(gl) - 1)]
        cuts = sorted(sorted(range(len(gaps)), key=lambda k: -gaps[k])[:len(twords) - 1])
        spans, s0 = [], 0
        for k in cuts:
            spans.append(gl[s0:k + 1]); s0 = k + 1
        spans.append(gl[s0:])
        # baseline: robust fit through bottoms of all line components that sit on it
        pts = [((c["x"] + c["x"] + c["w"]) / 2, c["y"] + c["h"]) for c in cs if 0.7 * hmed < c["h"] < 1.3 * hmed]
        if len(pts) < 3:   # capitals line: everything is cap height
            pts = [((c["x"] + c["x"] + c["w"]) / 2, c["y"] + c["h"]) for c in cs if 0.7 * hmed < c["h"] < 1.8 * hmed]
        fx, fy = np.array(pts, float).T
        coef = np.polyfit(fx, fy, 1)
        for _ in range(3):
            res = fy - np.polyval(coef, fx); keep = np.abs(res) < max(2.0, 2 * np.median(np.abs(res)))
            coef = np.polyfit(fx[keep], fy[keep], 1)
        for wi, (span, toks) in enumerate(zip(spans, twords)):
            names = [t.strip("{}") for t in toks]
            if any(nm not in T for nm in names) or not span:
                report.append(f"line {li+1} word {wi+1}: no template for {[nm for nm in names if nm not in T]}"); continue
            wx0, wx1 = span[0][0], span[-1][1]
            xs = np.arange(wx0 - 8, wx1 + 8)
            base = float(np.polyval(coef, (wx0 + wx1) / 2))
            # score maps: S[k][j] = best NCC with template k's ink-left at xs[j]
            S, BDY = [], []
            for nm in names:
                t = T[nm]; th, tw = t["img"].shape
                ty = int(round(base - t["base"]))
                best = np.full(len(xs), -1.0, np.float32); bdy = np.zeros(len(xs), int)
                # the baseline is evaluated per position (long words, e.g. the
                # alphabet line, span a visible tilt of the sheet)
                for dy in range(-10, 11):
                    yy = ty + dy
                    if yy < 0 or yy + th > dens.shape[0]:
                        continue
                    strip = dens[yy:yy + th, max(0, xs[0] - 2):min(dens.shape[1], xs[-1] + tw + 2)]
                    if strip.shape[1] < tw:
                        continue
                    r = cv2.matchTemplate(strip, t["img"], cv2.TM_CCOEFF_NORMED)[0]
                    off = max(0, xs[0] - 2)
                    for j, x in enumerate(xs):
                        q = x - 2 - off  # template box starts 2 px left of ink-left
                        if 0 <= q < len(r) and r[q] > best[j]:
                            best[j] = r[q]; bdy[j] = dy
                S.append(best); BDY.append(bdy)
            # DP over positions
            nk, nx = len(names), len(xs)
            D = np.full((nk, nx), -1e9); P = np.zeros((nk, nx), int)
            D[0] = S[0] - W_PEN * ((xs - wx0) / SIGMA) ** 2
            for k in range(1, nk):
                exp = T[names[k - 1]]["inkw"] + GAP
                for j in range(nx):
                    d = xs[j] - xs
                    cand = D[k - 1] - W_PEN * np.minimum(((d - exp) / SIGMA) ** 2, 4.0)
                    # the next letter may not start inside the previous one (an I fits
                    # H's right stem); overhanging sorts are allowed to overlap more
                    prev = names[k - 1]
                    frac = 0.38 if prev in ("Q",) else 0.4 if prev in ("f", "ſ", "j", "ff", "ſſ") else 0.8
                    cand[d <= max(2, frac * T[prev]["inkw"])] = -1e9
                    P[k, j] = int(np.argmax(cand)); D[k, j] = cand[P[k, j]] + S[k][j]
            endpen = W_PEN * (((xs + T[names[-1]]["inkw"]) - wx1) / SIGMA) ** 2
            j = int(np.argmax(D[-1] - endpen))
            pos = [0] * nk
            for k in range(nk - 1, -1, -1):
                pos[k] = j; j = P[k, j]
            score = float(np.mean([S[k][pos[k]] for k in range(nk)]))
            if score < 0.3:
                report.append(f"line {li+1} word {wi+1} '{''.join(names)}': weak alignment {score:.2f}"); continue
            # assign word pixels to the template claiming them most
            # fixed, generous vertical window (ascenders/descenders, kerns), never
            # limited by the templates, so a short template cannot clip impressions
            wy0 = int(min(base - max(T[nm]["base"] for nm in names), base - 2.3 * hmed)) - 4
            wy1 = int(max(base + max(T[nm]["img"].shape[0] - T[nm]["base"] for nm in names), base + 1.3 * hmed)) + 4
            wy0, wy1 = max(0, wy0), min(im.shape[0], wy1)
            region = bw[wy0:wy1, max(0, wx0 - 12):wx1 + 12] > 0
            ox = max(0, wx0 - 12)
            claim = np.zeros((nk,) + region.shape, np.float32)
            CP = 14   # claim zone extends beyond the template box, so a clipped template can regrow
            for k, nm in enumerate(names):
                t = T[nm]; th, tw = t["img"].shape
                soft = cv2.GaussianBlur(np.pad(t["img"], CP), (0, 0), 3.0)
                tx = xs[pos[k]] - 2 - ox - CP; ty = int(round(base - t["base"])) + int(BDY[k][pos[k]]) - wy0 - CP
                sh_, sw_ = soft.shape
                ya, xa = max(0, ty), max(0, tx)
                yb, xb = min(region.shape[0], ty + sh_), min(region.shape[1], tx + sw_)
                if yb > ya and xb > xa:
                    claim[k, ya:yb, xa:xb] = soft[ya - ty:yb - ty, xa - tx:xb - tx]
            # a pixel belongs to the template whose (blurred) ink is strongest there
            owner = np.argmax(claim, 0); owned = claim.max(0) > 0.01
            # geodesic ownership: grow every letter from the solid core of its placed
            # template outward THROUGH THE INK, so a pixel belongs to the letter it is
            # connected to (an f's hook follows its stem, not the u it overhangs)
            core = np.zeros(region.shape, np.int32); bestv = np.zeros(region.shape, np.float32)
            for k, nm in enumerate(names):
                t = T[nm]; th, tw = t["img"].shape
                tx = xs[pos[k]] - 2 - ox; ty = int(round(base - t["base"])) + int(BDY[k][pos[k]]) - wy0
                ya, xa = max(0, ty), max(0, tx)
                yb, xb = min(region.shape[0], ty + th), min(region.shape[1], tx + tw)
                if yb > ya and xb > xa:
                    sub = t["img"][ya - ty:yb - ty, xa - tx:xb - tx]
                    sel = (sub > 0.6) & region[ya:yb, xa:xb] & (sub > bestv[ya:yb, xa:xb])
                    core[ya:yb, xa:xb][sel] = k + 1; bestv[ya:yb, xa:xb][sel] = sub[sel]
            from collections import deque
            grown = core.copy(); qd = deque(zip(*np.nonzero(grown))); Hr, Wr = region.shape
            while qd:
                y_, x_ = qd.popleft(); L_ = grown[y_, x_]
                for dy_ in (-1, 0, 1):
                    for dx_ in (-1, 0, 1):
                        yy_, xx_ = y_ + dy_, x_ + dx_
                        if 0 <= yy_ < Hr and 0 <= xx_ < Wr and grown[yy_, xx_] == 0 and region[yy_, xx_]                                 and claim[L_ - 1, yy_, xx_] > 0.02:   # stay within this letter's own zone
                            grown[yy_, xx_] = L_; qd.append((yy_, xx_))
            reached = grown > 0
            owner = np.where(reached, grown - 1, owner); owned = owned | reached
            # unclaimed ink joins the letter that owns most of its connected stroke
            # (so a hook missing from a template still follows its stem)
            ncc_, cl = cv2.connectedComponents(region.astype(np.uint8), connectivity=8)
            for cid in range(1, ncc_):
                cm = cl == cid
                un = cm & ~owned
                if not un.any():
                    continue
                own = owner[cm & owned]
                if own.size:
                    owner[un] = np.bincount(own, minlength=nk).argmax(); owned |= un
            for k, nm in enumerate(names):
                m = region & owned & (owner == k)
                # never take ink above or below the letter's own template box (in
                # tightly set sizes descenders of one line touch the next line)
                t_ = T[nm]; ty_ = int(round(base - t_["base"])) + int(BDY[k][pos[k]]) - wy0
                vm = np.zeros(m.shape[0], bool)
                vm[max(0, ty_ - 5):max(0, ty_ + t_["img"].shape[0] + 5)] = True
                m &= vm[:, None]
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
                        if sm_[j_, 4] < 0.04 * sm_[big_, 4] and not (bx0 <= cx_ <= bx1):
                            m &= lm_ != j_
                if m.sum() < 15:
                    continue
                yy, xx = np.where(m)
                gx0, gx1, gy0, gy1 = xx.min() + ox, xx.max() + ox + 1, yy.min() + wy0, yy.max() + wy0 + 1
                pad = 6
                cx0, cy0 = max(0, gx0 - pad), max(0, gy0 - pad)
                crop = im[cy0:gy1 + pad, cx0:gx1 + pad]
                mm = np.zeros_like(crop, bool)
                sub = m[max(0, cy0 - wy0):max(0, cy0 - wy0) + crop.shape[0], max(0, cx0 - ox):max(0, cx0 - ox) + crop.shape[1]]
                mm[:sub.shape[0], :sub.shape[1]] = sub
                mm = cv2.dilate(mm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
                clean = np.where(mm, crop, np.uint8(paper)).astype(np.uint8)
                fn = f"{len(instances):04d}.png"
                cv2.imwrite(os.path.join(out, fn), clean)
                instances.append(dict(file=fn, ch=nm, line=li, word=wi, pos=k, nword=nk,
                                      x0=int(gx0) + x0, x1=int(gx1) + x0, y0=int(gy0) + y0, y1=int(gy1) + y0,
                                      crop=[int(cx0) + x0, int(cy0) + y0],
                                      baseline=float(np.polyval(coef, (gx0 + gx1) / 2)) + y0 + float(BDY[k][pos[k]]),
                                      slope=float(coef[0]), align=float(S[k][pos[k]])))
    json.dump(dict(instances=instances, otsu=float(thr)), open(os.path.join(out, "instances.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(len(instances), "instances")
    print("\n".join(report) if report else "all words aligned")


if __name__ == "__main__":
    main()
