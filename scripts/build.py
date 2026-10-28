"""Trace averaged (or single-impression) glyph images and compile an OTF.

Usage: python -I build.py <avg_dir> <variant: clean|impression> <pitch_px> <out.otf>

clean      : 50% contour of the multi-impression mean, smoothed curves
impression : 50% contour of the single most typical real impression, traced
             tightly so paper and ink texture survive
pitch_px   : measured line pitch at 600 ppi = the metal body = 1000 units
"""
import sys, os, json
import cv2
import numpy as np
import potrace
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

UPM = 1000
# harvested but malformed (too few clean impressions, tangled with neighbours)
DROP = set()  # "!" was here while it had 2-3 impressions; average.py now drops any book-only glyph with < 5 agreeing
sys.path.insert(0, os.path.dirname(__file__))
from glyphnames import glyph_name  # noqa: E402


FEATURES = """
languagesystem DFLT dflt;
languagesystem latn dflt;
feature liga {
{liga}
} liga;
feature hlig {
{hlig}
} hlig;
feature smcp {
{smcp}
} smcp;
feature c2sc {
{c2sc}
} c2sc;
@LETTER = [{letters}];
# Historical long s: medial and initial s become long s, except before
# b, f, k (and never at the end of a word). Off by default.
feature hist {
  ignore sub s' [{nolong}];
  sub s' @LETTER by longs;
} hist;
"""




def trace(mask, variant):
    bm = potrace.Bitmap(~mask)  # potracer treats False as ink
    if variant == "clean":
        path = bm.trace(turdsize=60, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                        alphamax=1.0, opticurve=True, opttolerance=0.3)
    else:
        path = bm.trace(turdsize=8, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                        alphamax=0.6, opticurve=False)
    return path


def _thin(img):
    """Zhang-Suen thinning (boolean array)."""
    im = np.pad(img.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = [np.roll(np.roll(im, dy, 0), dx, 1) for dy, dx in
                 ((1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1))]
            # P2..P9 order: N, NE, E, SE, S, SW, W, NW (roll by +1 brings the north neighbour down)
            P2, P3, P4, P5, P6, P7, P8, P9 = P[0], P[7], P[6], P[5], P[4], P[3], P[2], P[1]
            B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
            seq = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c = (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
            else:
                c = (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)
            rm = (im == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if rm.any():
                im[rm] = 0; changed = True
        if not changed:
            return im[1:-1, 1:-1].astype(bool)


def recover_hairlines(a, mask, thr):
    """Faint hairlines (C's top, Z's diagonals at small sizes) fall below the
    area-matched threshold. Add back the centreline of faint ink that touches the
    letter, drawn at the letter's own thinnest stroke width."""
    low = a > 0.45 * thr
    if not low.any() or not mask.any():
        return mask
    # downsample for speed, thin, then scale back
    f = 0.5
    sk = _thin(cv2.resize(low.astype(np.uint8), None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST) > 0)
    sk = cv2.resize(sk.astype(np.uint8), (a.shape[1], a.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    add = sk & ~mask
    # never inside an enclosed counter: faint specks there (paper texture, a
    # neighbour's ghost) would be joined to the letter by a spurious line
    inv = (~mask).astype(np.uint8)
    nh, lh, sh, _ = cv2.connectedComponentsWithStats(inv, 4)
    for i in range(1, nh):
        x, y, w, h, _a = sh[i]
        if x > 0 and y > 0 and x + w < mask.shape[1] and y + h < mask.shape[0]:
            add &= lh != i
    if not add.any():
        return mask
    dist = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
    ridge = dist[(dist > 0) & (dist >= cv2.dilate(dist, np.ones((3, 3), np.uint8)) - 1e-3)]
    r = max(2, int(round(np.percentile(ridge, 10)))) if ridge.size else 2
    # keep only skeleton pieces connected to the existing letter
    n, lab = cv2.connectedComponents((add | cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)).astype(np.uint8), 8)
    main = set(np.unique(lab[mask])) - {0}
    add &= np.isin(lab, list(main))
    grown = cv2.dilate(add.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
    return mask | (grown & low)


def _thr_for_area(a, tgt):
    lo, hi = 0.02, 0.98
    for _ in range(30):
        t = (lo + hi) / 2
        if (a > t).sum() > tgt:
            lo = t
        else:
            hi = t
    return (lo + hi) / 2


def _j_dot(mask, a, instp, tgt, name):
    """The j's dot sits a little differently on each impression, so averaging spreads
    it thin and the area-matched threshold (set by the stem) loses it. Measure the dot
    on the typical real impression (the Impression font's) and threshold the averaged
    dot alone to that ink area; the averaged position is kept."""
    if not os.path.exists(instp):
        return mask
    im = cv2.imread(instp, -1).astype(np.float32) / 65535
    im = im > (_thr_for_area(im, tgt) if tgt else 0.5)
    n, lab, st, _ = cv2.connectedComponentsWithStats(im.astype(np.uint8), 8)
    if n < 3:
        return mask
    big = 1 + int(np.argmax(st[1:, 4]))
    top = st[big, 1]
    dots = [i for i in range(1, n) if i != big and st[i, 1] + st[i, 3] <= top and st[i, 4] > 0.01 * st[big, 4]]
    if not dots:
        return mask
    d = max(dots, key=lambda i: st[i, 4])
    want = st[d, 4]
    # the dot region ends where the averaged stem begins (its top can sit a little
    # higher than the impression's)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n2 < 2:
        return mask
    split = min((st[d, 1] + st[d, 3] + top) // 2, st2[1 + int(np.argmax(st2[1:, 4])), 1] - 1)
    have = int(mask[:split].sum())
    if have >= 0.6 * want:
        return mask
    r = a[:split]
    mask = mask.copy()
    mask[:split] = r > _thr_for_area(r, want)
    print(f"{name}: dot thresholded on its own to the impression's dot area ({have} -> {want} px)")
    return mask


def _stroke(mask):
    """Thickness of a letter's main strokes: twice the 90th percentile of the
    distance-transform ridge."""
    d = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    r = d[(d > 0) & (d >= cv2.dilate(d, np.ones((3, 3), np.uint8)) - 1e-3)]
    return 2 * float(np.percentile(r, 90)) if r.size else 0.0


def _is_book(v):
    import re
    return bool(v.get("copies")) and all(re.fullmatch(r"n\d+", c) for c in v["copies"])


def _p(pt):
    return (pt.x, pt.y)


def draw(path, pen):
    for curve in path:
        pen.moveTo(_p(curve.start_point))
        for seg in curve.segments:
            if seg.is_corner:
                pen.lineTo(_p(seg.c)); pen.lineTo(_p(seg.end_point))
            else:
                pen.curveTo(_p(seg.c1), _p(seg.c2), _p(seg.end_point))
        pen.closePath()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    avg, variant, pitch, outp = args[0], args[1], float(args[2]), args[3]
    slant = float(opts.get("slant", 0))       # italic: glyphs were traced upright; lean them back
    family = opts.get("family")
    style = opts.get("style", "Regular")
    tslant = np.tan(np.radians(slant))
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    met = json.load(open(os.path.join(avg, "metrics.json"), encoding="utf-8"))["glyphs"]
    up, base_row = g["up"], g["base_row"]
    k = UPM / pitch            # font units per scan px
    ku = k / up                # font units per working-grid px
    # Q: body as wide as O, tail kerns over the next sort (metal practice)
    if "Q" in met and "O" in met:
        met["Q"] = dict(met["Q"], adv=met["O"]["adv"], lsb=met["O"]["lsb"])

    order, cmap, charstrings, advances, bounds = [".notdef", "space"], {0x20: "space"}, {}, {}, {}
    # .notdef: empty box
    pen = T2CharStringPen(500, None)
    for (x0, y0, x1, y1) in ((50, 0, 450, 700), (100, 50, 400, 650)):
        pen.moveTo((x0, y0)); pen.lineTo((x1, y0)); pen.lineTo((x1, y1)); pen.lineTo((x0, y1)); pen.closePath()
    charstrings[".notdef"] = pen.getCharString(); advances[".notdef"] = 500
    pen = T2CharStringPen(333, None); charstrings["space"] = pen.getCharString()
    advances["space"] = 333    # thick space (3-to-em), the period's standard word space

    lows, highs = [], []
    # book-only letters (microfilm) can trace heavier than the sheet's: their main
    # strokes are held to the proportion of this size's n that Pica shows
    ratios = {}
    rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stroke_ratios.json")
    if os.path.exists(rp):
        ratios = json.load(open(rp, encoding="utf-8")).get("Italic" if slant else "Roman", {})
    n_stroke = None
    for gid0, v0 in g["glyphs"].items():
        if v0["ch"] == "n" and v0.get("target_area"):
            src0 = "avg" if variant == "clean" else "inst"
            a0 = cv2.imread(os.path.join(avg, f"{src0}_{gid0}.png"), -1).astype(np.float32) / 65535
            if variant == "clean":
                a0 = cv2.GaussianBlur(a0, (0, 0), 1.5)
            n_stroke = _stroke(a0 > _thr_for_area(a0, v0["target_area"]))
    # main source, plus optional extra sources (e.g. small caps: --extra=dir),
    # each with its own canvas geometry and metrics; extras only add new glyphs
    jobs = [(gid, v, avg, met, up, base_row, True) for gid, v in sorted(g["glyphs"].items(), key=lambda t: t[1]["ch"])]
    for ex in [e for e in opts.get("extra", "").split(",") if e]:
        ge = json.load(open(os.path.join(ex, "glyphs.json"), encoding="utf-8"))
        me = json.load(open(os.path.join(ex, "metrics.json"), encoding="utf-8"))["glyphs"]
        jobs += [(gid, v, ex, me, ge["up"], ge["base_row"], False) for gid, v in sorted(ge["glyphs"].items(), key=lambda t: t[1]["ch"])
                 if v["ch"] in me and v["ch"] not in met]
    for gid, v, avg, met_, up, base_row, is_main in jobs:
        ku = k / up
        ch = v["ch"]
        if ch in DROP or ch.startswith("LIG:"):   # unsorted ligature (e.g. from a specimen source)
            continue
        if variant == "clean" and v.get("single"):   # one impression, verified by eye: too few to average
            continue
        name, uni = glyph_name(ch)
        src = "avg" if variant == "clean" else "inst"
        a = cv2.imread(os.path.join(avg, f"{src}_{gid}.png"), -1).astype(np.float32) / 65535
        if variant == "clean":
            a = cv2.GaussianBlur(a, (0, 0), 1.5)
        # threshold that gives the same ink area as the real impressions average
        tgt = v.get("target_area")
        if tgt:
            lo, hi = 0.02, 0.98
            for _ in range(30):
                t = (lo + hi) / 2
                if (a > t).sum() > tgt:
                    lo = t
                else:
                    hi = t
            thr = (lo + hi) / 2
        else:
            thr = 0.5
        if n_stroke and is_main and _is_book(v) and ch in ratios:
            want = ratios[ch] * n_stroke
            if _stroke(a > thr) > 1.04 * want:     # only ever thinner, never thicker
                lo, hi = thr, 0.95
                for _ in range(20):
                    t = (lo + hi) / 2
                    if _stroke(a > t) > want:
                        lo = t
                    else:
                        hi = t
                print(f"{ch}: book letter thinned to Pica's stroke proportion (threshold {thr:.2f} -> {hi:.2f})")
                thr = hi
        mask = a > thr
        if variant == "clean" and ch == "j":
            mask = _j_dot(mask, a, os.path.join(avg, f"inst_{gid}.png"), tgt, name)
        if variant == "clean" and not os.environ.get("CASLON_NO_HAIRLINES"):
            mask = recover_hairlines(a, mask, thr)
        if variant == "clean" and mask.any():
            few = v.get("n", 99) <= 3
            # paper showing through a lightly inked impression leaves white specks
            # inside strokes, and a damaged sort a small nibble at an edge; neither is
            # the letter's design. Close small notches, then fill enclosed holes far
            # smaller than any real counter (relative to the letter's stroke width).
            dist = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
            ridge = dist[(dist > 0) & (dist >= cv2.dilate(dist, np.ones((3, 3), np.uint8)) - 1e-3)]
            half = float(np.percentile(ridge, 50)) if ridge.size else 4.0   # half the typical stroke
            r = max(2, int(round(0.5 * half)))
            closed = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE,
                                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
            # closing may only fill notches, never bridge two separate strokes: keep
            # its additions only where they are small blobs touching the letter
            add = (closed & ~mask) if few else np.zeros_like(mask)   # notches: only where too few impressions to outvote a dented sort
            na, la, sa, _ = cv2.connectedComponentsWithStats(add.astype(np.uint8), 8)
            for i in range(1, na):
                if sa[i, 4] <= (1.2 * half) ** 2 * np.pi:
                    mask |= la == i
            inv = (~mask).astype(np.uint8)
            nh, lh, sh, _ = cv2.connectedComponentsWithStats(inv, 4)
            for i in range(1, nh):
                x, y, w, h, area = sh[i]
                enclosed = x > 0 and y > 0 and x + w < mask.shape[1] and y + h < mask.shape[0]
                if enclosed and area <= (0.8 * half) ** 2 * np.pi:   # specks only, never a small counter
                    mask |= lh == i
        # keep only components that belong to the glyph (drop stray halo specks)
        n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        big = max(st[1:, 4]) if n > 1 else 0
        keepl = [i for i in range(1, n) if st[i, 4] > max(150, 0.02 * big)]
        if variant == "clean" and v.get("n", 1) >= 3:
            # real ink is present in most impressions; a fragment that turned up in
            # only one of them (a neighbour's descender, a speck) cannot reach high
            # density in the mean
            # except the dot of i or j: it is in every impression, but sits a little
            # differently on each, so its mean stays low (the Brevier j's peaks at ~0.5)
            dot = None
            if ch in ("i", "j") and keepl:
                mb = max(keepl, key=lambda i: st[i, 4])
                above = [i for i in keepl if st[i, 1] + st[i, 3] <= st[mb, 1]]
                dot = max(above, key=lambda i: st[i, 4]) if above else None
            keepl = [i for i in keepl if i == dot or a[lab == i].max() >= 0.55]
        if (len(ch) == 1 and ch.isupper()) or ch.endswith(".sc"):
            # capitals have no detached parts; small separate pieces are neighbours
            # repeated in every copy of the same forme (a descender from the line
            # above, the italic Q's tail running under R)
            # keep pieces whose centre lies within the main body's extent (thin
            # strokes of an averaged C or Z can break apart); drop outside pieces
            if keepl:
                mb = max(keepl, key=lambda i: st[i, 4])
                bx0, by0, bw_, bh_ = st[mb, 0], st[mb, 1], st[mb, 2], st[mb, 3]
                def inside(i):
                    cx_, cy_ = st[i, 0] + st[i, 2] / 2, st[i, 1] + st[i, 3] / 2
                    return bx0 - 0.1 * bw_ <= cx_ <= bx0 + 1.1 * bw_ and by0 - 0.1 * bh_ <= cy_ <= by0 + 1.1 * bh_
                keepl = [i for i in keepl if i == mb or (inside(i) and st[i, 4] >= 0.02 * big)]
        mask = np.isin(lab, keepl)
        xs = np.where(mask.any(0))[0]; ys = np.where(mask.any(1))[0]
        if len(ys) == 0:
            print(f"WARNING {ch}: nothing left after cleaning; skipped"); continue
        # horizontal reference must match spacing.py: left edge of the mean at 50%
        ref = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        cols_ = np.where((ref > 0.5).any(0))[0]
        if len(cols_) == 0 or ch not in met_:
            print(f"WARNING {ch}: no solid ink in the mean or no metrics; skipped"); continue
        inkleft = cols_[0]
        m = met_[ch]
        adv = round(m["adv"] * k)
        if adv < 0.3 * m["inkw"] * k:      # safety: a solver failure must not produce an unusable font
            print(f"WARNING {ch}: advance {adv} below 30% of ink width; clamped")
            adv = round(0.3 * m["inkw"] * k)
        dx = m["lsb"] * k - inkleft * ku
        path = trace(mask, variant)
        pen = T2CharStringPen(adv, None)
        # upright trace -> font units, then shear about the baseline (x += tan(a) * y)
        tp = TransformPen(pen, (ku, 0, -ku * tslant, -ku, dx + base_row * ku * tslant, base_row * ku))
        draw(path, tp)
        charstrings[name] = pen.getCharString(); advances[name] = adv
        order.append(name)
        if uni:
            cmap[uni] = name
        if is_main:
            lows.append(((base_row - ys[-1]) * ku, ch)); highs.append(((base_row - ys[0]) * ku, ch))

    # vertical metrics: the metal body is exactly 1000 units; its bottom sits
    # just below the lowest descender (p, q), the rest is above the baseline
    desc_letters = [y for y, c in lows if c in "pq"]
    descent = int(round(min(desc_letters) - 0.02 * UPM)) if desc_letters else -230
    if "descent" in opts:      # family members share one body position
        descent = int(opts["descent"])
    ascent = UPM + descent
    fam = (family or "Caslon 1734 Pica") + (" Impression" if variant == "impression" else "")
    fb = FontBuilder(UPM, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupCFF(fam.replace(" ", ""), {"FullName": fam}, charstrings, {})
    lsbs = {}
    for nme in order:
        cs = charstrings[nme]
        from fontTools.pens.boundsPen import BoundsPen
        bp = BoundsPen(None); cs.draw(bp)
        lsbs[nme] = int(bp.bounds[0]) if bp.bounds else 0
    fb.setupHorizontalMetrics({nme: (advances[nme], lsbs[nme]) for nme in order})
    fb.setupHorizontalHeader(ascent=ascent, descent=descent, lineGap=0)
    fb.setupNameTable(dict(familyName=fam, styleName=style,
                           uniqueFontIdentifier=fam + " 0.1",
                           fullName=f"{fam} {style}", psName=fam.replace(" ", "") + "-" + style.replace(" ", ""),
                           version="Version 0.100",
                           description=("Reconstructed from William Caslon's 1734 specimen sheet "
                                        "(McGill University Library copies, 600 ppi). Each glyph is "
                                        "the registered average of every impression on three copies; "
                                        "spacing solved from printed neighbours. 1000 units = measured "
                                        "Pica body.")))
    fb.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0,
                usWinAscent=max(ascent, int(max(h for h, _ in highs)) + 10),
                usWinDescent=max(-descent, int(-min(l for l, _ in lows)) + 10),
                fsSelection=(0x01 if slant else 0x40) | 0x80)
    fb.setupPost(italicAngle=-slant)
    have = set(order)
    letters = " ".join(x for x in "a b c d e f g h i j k l m n o p q r s t u v w x y z edieresis icircumflex longs".split() if x in have)
    nolong = " ".join(x for x in "b f k".split() if x in have)
    if not ("s" in have and "longs" in have and letters):
        FEAT = FEATURES.split("@LETTER")[0]          # no long-s feature without both forms
    else:
        FEAT = FEATURES
    rules = [("longs longs i", "longs_longs_i"), ("f f i", "f_f_i"), ("f f l", "f_f_l"),
             ("longs longs", "longs_longs"), ("longs i", "longs_i"), ("longs t", "longs_t"),
             ("longs h", "longs_h"), ("longs k", "longs_k"), ("longs l", "longs_l"), ("longs b", "longs_b"), ("f f", "f_f"), ("f i", "f_i"), ("f l", "f_l")]
    def ok(seq, lig):
        return lig in have and all(x in have for x in seq.split())
    liga = "\n".join(f"  sub {seq} by {lig};" for seq, lig in rules if ok(seq, lig)) or "  sub space by space;"
    hlig = "  sub c t by c_t;" if ok("c t", "c_t") else "  sub space by space;"
    scs = sorted(n_ for n_ in have if n_.endswith(".sc"))
    smcp = "\n".join(f"  sub {n_[0].lower()} by {n_};" for n_ in scs if n_[0].lower() in have) or "  sub space by space;"
    c2sc = "\n".join(f"  sub {n_[0].upper()} by {n_};" for n_ in scs if n_[0].upper() in have) or "  sub space by space;"
    fea = FEAT.replace("{smcp}", smcp).replace("{c2sc}", c2sc).replace("{letters}", letters).replace("{nolong}", nolong).replace("{liga}", liga).replace("{hlig}", hlig)
    addOpenTypeFeaturesFromString(fb.font, fea)
    fb.save(outp)
    print("saved", outp, len(order), "glyphs; ascent", ascent, "descent", descent)


if __name__ == "__main__":
    main()
