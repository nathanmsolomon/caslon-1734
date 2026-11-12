"""Register and average every instance of each glyph across all copies.

Usage: python -I average.py <out_dir> <instances_dir> [<instances_dir> ...]

Each instance is converted to ink density (0 = paper, 1 = solid ink) using
its own copy's paper/ink levels, upsampled, placed with its baseline on a fixed
row, then aligned to the class mean by sub-pixel phase correlation. Writes per
glyph: mean density (avg_<id>.png, 16-bit), the stack spread (std_<id>.png)
and glyphs.json with baseline row, scale and instance count.
"""
import sys, os, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyphnames import NAMES  # noqa: E402
import typelib_profile as _prof  # noqa: E402   per-project settings (N:\Claude Work\_typelib)

UP = 4         # upsampling factor (600 ppi scan -> 2400 ppi working grid)
MAX_PER_GLYPH = int(os.environ.get("CASLON_MAXPER", "400"))   # impressions per glyph (lower for quick tests)
DYMAX = float(os.environ.get("CASLON_DYMAX", "6"))   # px at scan resolution
# clip below the baseline, x line pitch (env CASLON_BELOW; Arrighi Nov 11: masked cuts can go deeper)
BELOW = float(_prof.get("below"))
# outlier reference from the crops that agree with the medoid (Colines book pages); off = plain median
MEDOID = bool(_prof.get("medoid_ref"))
# over-attested letters are sampled with a per-letter seed (so workers agree with a serial run),
# or, as Caslon and Garamont always did, from one generator shared down the alphabet
LETTER_RNG = bool(_prof.get("per_letter_rng"))
TAILED = {"Q"}   # letters whose tail varies between impressions
DOTTED = {"j"}   # letters whose detached dot sits a little differently on each impression
RAISED = {"'"}   # marks that float well above the baseline (book OCR also labels letters as these)
ONLY = os.environ.get("CASLON_ONLY_CHARS")   # re-average just these characters (scripts/redo_chars.py)
if ONLY and ONLY.startswith("["):
    ONLY = set(json.loads(ONLY))    # a JSON list names whole glyphs ("fl", "ſt"), not single characters
# letters are averaged independently: with COLINES_AVG_JOBS > 1 the letters are split
# across that many worker processes (each this same script with CASLON_ONLY_CHARS set)
# and their outputs merged; same canvas, same results per letter (Nov 10 2026)
JOBS = int(_prof.get("avg_jobs")) if LETTER_RNG else 1   # env COLINES_AVG_JOBS; workers need the per-letter seed


def dot_parts(s, base):
    """(stem top row, dot bottom row) of one registered impression, or None when it
    shows no detached dot above its main stroke (an OCR-misread long s or f)."""
    m = (s > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 3:
        return None
    big = 1 + int(np.argmax(st[1:, 4]))
    top = st[big, 1]
    dots = [i for i in range(1, n) if i != big and st[i, 1] + st[i, 3] <= top and st[i, 4] > 0.02 * st[big, 4]
            and st[i, 1] + st[i, 3] < base]
    if not dots:
        return None
    d = max(dots, key=lambda i: st[i, 4])
    return top, st[d, 1] + st[d, 3]
CONGEAL = os.environ.get("CASLON_CONGEAL", "1") != "0"   # on by default (Oct 21 test: 83 of 83 letters sharper)


def congeal(stack, iters=3):
    """Joint elastic alignment of impressions already registered by shifting.

    Paper stretch, a sort leaning in the forme and uneven impression bend each
    copy slightly differently, so a shift-only mean blurs at the edges. Each copy
    is warped towards the current mean by dense optical flow, smoothed with a
    Gaussian far wider than a stroke (so a warp can bend a letter but never thin
    or thicken a stroke) and capped at 1.5 scan pixels. The flow common to all
    copies is removed first, so the shared shape cannot drift; then the mean is
    recomputed and the process repeats.
    """
    n, h, w = stack.shape
    m0 = stack.mean(0)
    rows = np.where((m0 > 0.3).any(1))[0]
    ink_h = (rows[-1] - rows[0] + 1) if len(rows) else h / 2
    sig = max(2.0 * UP, 0.12 * ink_h)
    cap = 1.5 * UP
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    for _ in range(iters):
        tgt = (np.clip(stack.mean(0), 0, 1) * 255).astype(np.uint8)
        # the smoothed flows are kept at quarter resolution (they vary slowly)
        hs, ws = max(1, h // 4), max(1, w // 4)
        flows = np.empty((n, hs, ws, 2), np.float32)
        for k in range(n):
            f = dis.calc(tgt, (np.clip(stack[k], 0, 1) * 255).astype(np.uint8), None)
            f = cv2.GaussianBlur(f, (0, 0), sig)
            flows[k] = cv2.resize(f, (ws, hs), interpolation=cv2.INTER_AREA)
        flows -= flows.mean(0, keepdims=True)
        mag = np.sqrt((flows ** 2).sum(-1, keepdims=True))
        flows *= np.minimum(1.0, cap / (mag + 1e-6))
        for k in range(n):
            f = cv2.resize(flows[k], (w, h), interpolation=cv2.INTER_LINEAR)
            stack[k] = cv2.remap(stack[k], gx + f[..., 0], gy + f[..., 1], cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return stack
PAD = 40        # px (at scan resolution) of margin around the canvas


def density(crop, paper, ink):
    d = (paper - crop.astype(np.float32)) / (paper - ink)
    return np.clip(d, 0, 1)


def group(d):
    """Which book a supplementary dir belongs to: work/eboX/n12 and work/eboi/n12
    are both Eboracum, work/k85_gp_roman/b1 is the 1785 specimen, and so on."""
    import re
    return re.sub(r"(X|Y)?i?$", "", os.path.basename(os.path.dirname(os.path.normpath(d))))


def glyph_id(ch):
    return "_".join(f"{ord(c):04X}" for c in ch)


def parallel(out, args, dirs):
    """Average the letters in JOBS worker processes and merge their outputs into out."""
    import subprocess, shutil, tempfile
    count = {}
    for d in dirs:
        for i in json.load(open(os.path.join(d, "instances.json"), encoding="utf-8"))["instances"]:
            count[i["ch"]] = count.get(i["ch"], 0) + 1
    # balance by work: the congeal cost grows with the number of impressions
    groups, load = [[] for _ in range(JOBS)], [0] * JOBS
    for ch in sorted(count, key=lambda c: -count[c]):
        k = load.index(min(load)); groups[k].append(ch); load[k] += count[ch]
    key = os.environ.get("CASLON_SINGLES_KEY") or os.path.basename(os.path.normpath(out))
    tmp = tempfile.mkdtemp(prefix="avg_", dir=os.path.dirname(os.path.abspath(out)) or ".")
    procs = []
    for k, chs in enumerate(groups):
        if not chs:
            continue
        env = dict(os.environ, CASLON_ONLY_CHARS=json.dumps(chs, ensure_ascii=False), CASLON_SINGLES_KEY=key,
                   COLINES_AVG_JOBS="1")
        sub = os.path.join(tmp, f"w{k}")
        log = open(sub + ".log", "w", encoding="utf-8")
        procs.append((sub, log, subprocess.Popen([sys.executable, "-I", "-X", "utf8", os.path.abspath(__file__), sub] + args,
                                                 env=env, stdout=log, stderr=subprocess.STDOUT)))
    failed = [sub for sub, log, p in procs if p.wait() != 0]
    for _, log, _ in procs:
        log.close()
    for sub, _, _ in procs:
        sys.stdout.write(open(sub + ".log", encoding="utf-8").read())
    if failed:
        raise SystemExit("average.py worker failed: " + ", ".join(f + ".log" for f in failed))
    merged = None
    for sub, _, _ in procs:
        g = json.load(open(os.path.join(sub, "glyphs.json"), encoding="utf-8"))
        if merged is None:
            merged = g
        else:
            assert (g["width"], g["height"], g["base_row"]) == (merged["width"], merged["height"], merged["base_row"])
            merged["glyphs"].update(g["glyphs"])
        for f in os.listdir(sub):
            if f.endswith(".png"):
                shutil.move(os.path.join(sub, f), os.path.join(out, f))
    merged["glyphs"] = dict(sorted(merged["glyphs"].items()))
    json.dump(merged, open(os.path.join(out, "glyphs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    out, args = sys.argv[1], sys.argv[2:]
    # dirs prefixed with '+' (or listed in a file given as @list.txt with '+' lines)
    # are supplementary: used only for characters the primary sources lack
    expanded = []
    for a in args:
        if a.startswith("@"):
            expanded += [l.strip() for l in open(a[1:]) if l.strip()]
        else:
            expanded.append(a)
    dirs = [a.lstrip("+") for a in expanded]
    supp = {a.lstrip("+") for a in expanded if a.startswith("+")}
    os.makedirs(out, exist_ok=True)
    if JOBS > 1 and not ONLY and not supp and not os.environ.get("CASLON_ONLY_THIN"):
        # (book-only agreement and thin-glyph logs need every letter at once, so
        # supplementary sources keep the single-process path)
        return parallel(out, args, dirs)
    # book-only glyphs seen fewer than 5 times, checked by eye: {avg dir name: {ch: "dir/file"}}
    sp_ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "impression_singles.json")
    SINGLES = json.load(open(sp_, encoding="utf-8")).get(os.environ.get("CASLON_SINGLES_KEY") or os.path.basename(os.path.normpath(out)), {}) if os.path.exists(sp_) else {}
    # glyphs judged unreliable by eye despite passing the rules: {avg dir name: {ch: reason}}
    rp_ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reject_glyphs.json")
    REJECT = json.load(open(rp_, encoding="utf-8")).get(os.environ.get("CASLON_SINGLES_KEY") or os.path.basename(os.path.normpath(out)), {}) if os.path.exists(rp_) else {}
    # Colines book pages: an impression checked by eye to seed a letter's reference when
    # its crops split into a good and a mis-cut cluster: {avg dir name: {ch: "dir/file"}}
    sd_ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_glyphs.json")
    SEEDS = json.load(open(sd_, encoding="utf-8")).get(os.environ.get("CASLON_SINGLES_KEY") or os.path.basename(os.path.normpath(out)), {}) if os.path.exists(sd_) else {}
    thin_log = {}
    primary_chars = set()
    primary_n = {}
    # letters the sheet shows only this often or less are strengthened with book
    # impressions from confirmed same-cut sources (user's decision, Oct 21 2026)
    RARE = 3
    # fewest agreeing impressions for a letter that only the books supply (profile min_book,
    # env GARAMONT_MIN_BOOK: Garamont 3 since Nov 11 2026, Caslon and Colines 5)
    MIN_BOOK = int(_prof.get("min_book"))
    # sheet labels known to be mis-cuts (e.g. S. Augustin roman "g" = "af"): the sheet's
    # impressions of them are ignored, so the books supply the letter (run_size.py sheet_drop)
    DROP = {c for c in os.environ.get("GARAMONT_SHEET_DROP", "").split(",") if c}
    rng = np.random.default_rng(0)
    for d in dirs:
        if d not in supp:
            for i_ in json.load(open(os.path.join(d, "instances.json"), encoding="utf-8"))["instances"]:
                if i_["ch"] in DROP:
                    continue
                primary_chars.add(i_["ch"]); primary_n[i_["ch"]] = primary_n.get(i_["ch"], 0) + 1
    per_char = {}
    calib = {}
    CALIB = set("noeahdmu")
    LC_CAL, UC_CAL = set("xnuvzmo"), set("EFHILNT")
    SIZE_CAL = LC_CAL | UC_CAL
    for d in dirs:
        meta = json.load(open(os.path.join(d, "instances.json"), encoding="utf-8"))
        crops = [cv2.imread(os.path.join(d, i["file"]), cv2.IMREAD_GRAYSCALE) for i in meta["instances"]]
        if not crops:
            continue
        allpx = np.concatenate([c.ravel() for c in crops])
        paper = float(np.percentile(allpx, 75))
        ink = float(np.percentile(allpx, 2))
        t_otsu = (paper - meta["otsu"]) / (paper - ink)
        # no letter rises more than ~0.85 of the line pitch above the baseline or
        # falls more than ~0.36 below it; anything beyond is the neighbouring line
        # (solid-set small sizes put the line above inside the crop)
        bl = {}
        for i in meta["instances"]:
            if "line" in i:
                bl.setdefault(i["line"], []).append(i["baseline"])
        lines = sorted(bl)
        steps = [(np.median(bl[b]) - np.median(bl[a])) / (b - a) for a, b in zip(lines, lines[1:])]
        pitch_d = float(np.median(steps)) if len(steps) >= 3 else None
        for inst, crop in zip(meta["instances"], crops):
            if inst["ch"] in SIZE_CAL and inst["ch"] in primary_chars:
                # ink height of letters both sources have: the book's scan scale is
                # known only to a few per cent, and capitals and lowercase are
                # matched to the sheet separately
                rows_ink = np.where((density(crop, paper, ink) > 0.5).sum(1) >= 2)[0]
                if len(rows_ink):
                    calib.setdefault(("hb", group(d), inst["ch"]) if d in supp else ("hp", inst["ch"]), []).append(float(rows_ink[-1] - rows_ink[0] + 1))
            if d in supp and inst["ch"] in CALIB and inst["ch"] in primary_chars:
                # letters both sources have: measure how much heavier the book prints
                dd = density(crop, paper, ink)
                calib.setdefault(("b", group(d), inst["ch"]), []).append(float((dd > t_otsu).sum()))
            elif d not in supp and inst["ch"] in CALIB:
                dd = density(crop, paper, ink)
                calib.setdefault(("p", inst["ch"]), []).append(float((dd > t_otsu).sum()))
            if d in supp and ((inst["ch"] in primary_chars and primary_n.get(inst["ch"], 0) > RARE) or inst["ch"].startswith("LIG:")):
                continue
            if d in supp and not (inst["ch"] in NAMES or inst["ch"].endswith(".sc")
                                  or (len(inst["ch"]) == 1 and inst["ch"].isascii() and inst["ch"].isalnum())):
                continue   # OCR oddities (ł, Þ, ꝶ ...) are not letters of this fount
            if d not in supp and inst["ch"] in DROP:
                continue
            dens = density(crop, paper, ink)
            if pitch_d and pitch_d > 0:
                rows = inst["crop"][1] + np.arange(dens.shape[0]) - inst["baseline"]
                dens[(rows < -0.85 * pitch_d) | (rows > BELOW * pitch_d)] = 0
            per_char.setdefault(inst["ch"], []).append((inst, dens, d, t_otsu))

    # size calibration of the book against the sheet, then rescale book-only glyphs
    # each book (a different scan and printing) is calibrated on its own
    def size_ratio(chars, G):
        r = [np.median(calib[("hp", c)]) / np.median(calib[("hb", G, c)]) for c in chars
             if len(calib.get(("hp", c), [])) >= 2 and len(calib.get(("hb", G, c), [])) >= 5]
        return float(np.median(r)) if len(r) >= 2 else None
    groups = sorted({group(d) for d in supp})
    f_lc = {G: size_ratio(LC_CAL, G) or 1.0 for G in groups}
    f_uc = {G: size_ratio(UC_CAL, G) or f_lc[G] for G in groups}
    if supp:
        for G in groups:
            print(f"book size calibration [{G}]: lowercase x {f_lc[G]:.3f}  capitals x {f_uc[G]:.3f}")
        for ch, items in per_char.items():
            for k, (inst, dens, d, t) in enumerate(items):
                if d not in supp:
                    continue
                f = f_uc[group(d)] if ch[:1].isupper() else f_lc[group(d)]
                if abs(f - 1) < 0.005:
                    continue
                dens2 = cv2.resize(dens, None, fx=f, fy=f, interpolation=cv2.INTER_LINEAR)
                cx, cy = inst["crop"]
                inst2 = dict(inst, crop=[inst["x0"] - f * (inst["x0"] - cx), inst["baseline"] - f * (inst["baseline"] - cy)])
                items[k] = (inst2, dens2, d, t)

    # common canvas: tall enough for ascenders/descenders at this size
    maxw = max(c.shape[1] for v in per_char.values() for _, c, _, _ in v)
    maxh_above = max(i["baseline"] - i["crop"][1] for v in per_char.values() for i, _, _, _ in v)
    maxh_below = max(i["crop"][1] + c.shape[0] - i["baseline"] for v in per_char.values() for i, c, _, _ in v)
    H = int(np.ceil(maxh_above + maxh_below)) + 2 * PAD
    # letters are placed with their ink's left edge a third of the way in (room
    # for kerns to the left), so leave room for the widest one plus that third
    W = int(1.5 * maxw) + 2 * PAD
    base_row = int(np.ceil(maxh_above)) + PAD  # baseline row at scan resolution

    # weight calibration: ink area of the sheet's impressions over the book's, for
    # letters both have; book-only glyphs are traced to that much less ink
    # (book areas were measured before rescaling, hence f_lc squared)
    weight_ratio = {}
    for G in groups:
        rats = [np.median(calib[("p", c)]) / (np.median(calib[("b", G, c)]) * f_lc[G] ** 2) for c in CALIB
                if len(calib.get(("p", c), [])) >= 3 and len(calib.get(("b", G, c), [])) >= 10]
        weight_ratio[G] = float(np.median(rats)) if len(rats) >= 3 else 1.0
        print(f"book weight calibration [{G}]: sheet/book ink area {weight_ratio[G]:.3f} from {len(rats)} letters")
    info = {}
    book_agree = {}
    for ch, items in sorted(per_char.items()):
        if os.environ.get("CASLON_ONLY_THIN") and not (all(it[2] in supp for it in items) and len(items) < 5):
            continue    # quick pass that only collects thinly attested glyphs for review
        if ONLY and ch not in ONLY:
            continue
        if ch in REJECT:
            print(ch, "rejected by eye (reject_glyphs.json):", REJECT[ch])
            continue
        if ch in RAISED:
            # an apostrophe sits far above the baseline; book "apostrophes" standing on
            # it are misread letters (t, n, d, T) or page furniture
            up_ = [it for it in items if "y1" not in it[0] or
                   it[0]["baseline"] - it[0]["y1"] > 0.8 * (it[0]["y1"] - it[0]["y0"])]
            if len(up_) < len(items):
                print(ch, "impressions standing on the baseline dropped:", len(items) - len(up_), "of", len(items))
            items = up_
            if not items:
                continue
        # beyond a couple of hundred the mean no longer changes; also keep the
        # stack (float32 canvases) within about 2.5 GB of memory
        cap = int(min(MAX_PER_GLYPH, max(40, 2.5e9 / (H * UP * W * UP * 4 * 2))))
        if len(items) > cap:
            # seeded per letter, so the sample does not depend on which other letters
            # this process averages (parallel workers)
            rng_ = np.random.default_rng([ord(c) for c in ch]) if LETTER_RNG else rng
            items = [items[k] for k in sorted(rng_.choice(len(items), cap, replace=False))]
        stack = []
        for inst, dens, _, _ in items:
            canvas = np.zeros((H * UP, W * UP), np.float32)
            big = np.clip(cv2.resize(dens, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC), 0, 1)
            # vertical: baseline to base_row (sub-pixel via the float baseline)
            top = (base_row - (inst["baseline"] - inst["crop"][1])) * UP
            # horizontal: ink centre to canvas centre (refined below)
            # start from the ink's LEFT edge (stable), not its centre: tails and kerns
            # of variable length (Q, f, j) would otherwise offset the bodies
            cx = inst["x0"] - inst["crop"][0]
            left = (W / 3 - cx) * UP
            # undo the sheet's rotation about the glyph's baseline point
            ang = np.degrees(np.arctan(inst.get("slope", 0.0)))
            R = cv2.getRotationMatrix2D((cx * UP, (inst["baseline"] - inst["crop"][1]) * UP), ang, 1.0)
            R[0, 2] += left; R[1, 2] += top
            canvas = cv2.warpAffine(big, R.astype(np.float32), (W * UP, H * UP), flags=cv2.INTER_LINEAR)
            stack.append(canvas)
        stack = np.array(stack)
        # how far registration may move a copy: fixed for text sizes, 5% of the
        # letter's height for display letters over 120 px (a 250 px titling capital
        # from another edition can sit 10 px off after baseline placement)
        m0_ = stack.mean(0); r0_ = np.where((m0_ > 0.3).any(1))[0]
        ink_h = (r0_[-1] - r0_[0] + 1) / UP if len(r0_) else 0
        dym, dxm = (0.05 * ink_h, 0.05 * ink_h) if ink_h > 120 else (DYMAX, 4.0)
        dym = max(dym, DYMAX)
        tots = np.array([it[3] for it in items])
        isb = np.array([it[2] in supp for it in items])     # which impressions are book ones
        ids = np.array([os.path.basename(os.path.normpath(it[2])) + "/" + it[0]["file"] for it in items])
        # iterative alignment to the mean (the baseline estimate carries line-level
        # noise, so vertical is refined too, but only a little)
        win = cv2.createHanningWindow((W * UP, H * UP), cv2.CV_32F)
        # register on the part above the baseline: tails and descenders (Q, the
        # kerned f) vary between impressions and would otherwise drag the bowls apart
        win[base_row * UP + 2 * UP:, :] *= 0.05
        if ch in TAILED:
            # register on the bowl only: the long tail leaves it at varying points
            mean0 = stack.mean(0); cols = np.where((mean0 > 0.3).any(0))[0]
            if len(cols):
                cut = int(cols[0] + 0.6 * (cols[-1] - cols[0]))
                win[:, cut:] *= 0.05
        for _ in range(3):
            mean = stack.mean(0)
            for k in range(len(stack)):
                (dx, dy), _ = cv2.phaseCorrelate(mean * win, stack[k] * win)
                dy = float(np.clip(dy, -dym * UP, dym * UP)); dx = float(np.clip(dx, -dxm * UP, dxm * UP))
                M = np.float32([[1, 0, -dx], [0, 1, -dy]])
                stack[k] = cv2.warpAffine(stack[k], M, (W * UP, H * UP), flags=cv2.INTER_LINEAR)
        dot_cut = None
        if ch in DOTTED and len(stack) >= 2:
            # a j without a detached dot is not a j (book OCR reads the italic long s
            # and f as j, and in the italic often more ſ than j): keep only the
            # impressions that show one, whenever at least two do
            parts = [dot_parts(s_, base_row * UP) for s_ in stack]
            has = np.array([p_ is not None for p_ in parts])
            if has.sum() >= 2:
                if (~has).any():
                    print(ch, "impressions without a detached dot dropped:", int((~has).sum()), "of", len(stack))
                stack = stack[has]; tots = tots[has]; isb = isb[has]; ids = ids[has]
                items = [it for it, h_ in zip(items, has) if h_]
                dot_cut = int(np.median([(t_ + b_) / 2 for t_, b_ in [p_ for p_ in parts if p_ is not None]]))
            elif all(it[2] in supp for it in items):
                # book-only and none (or one) show a dot: the "j"s are misread long s or
                # f, and a wrong glyph is worse than a missing one
                print(ch, "book-only glyph dropped:", int(has.sum()), "of", len(stack), "impressions show a dot")
                continue
        # a thinly attested book-only glyph: every registered impression, kept for
        # review (scripts/review_singles.py) before rejection can discard any
        thin = all(it[2] in supp for it in items) and len(items) < 5
        if thin:
            stack0, tots0, isb0, ids0 = stack.copy(), tots.copy(), isb.copy(), ids.copy()
        # reject instances that don't look like the rest (mislabels, touching
        # neighbours, damaged sorts); keep everything when there are only 2
        rejected = []
        if 2 <= len(stack) < 6 and SEEDS.get(ch) in list(ids):
            # too few to vote: the impression checked by eye stands alone
            j = int(list(ids).index(SEEDS[ch]))
            rejected = [dict(file=str(ids[k]), score=0.0) for k in range(len(stack)) if k != j]
            stack, tots, isb, ids = stack[j:j + 1], tots[j:j + 1], isb[j:j + 1], ids[j:j + 1]
            print(ch, "single impression seeded by eye:", SEEDS[ch])
        if len(stack) == 2:
            # two impressions that disagree: one is defective; under-inking (a lost
            # arm or serif) is the usual fault, so keep the one with more ink
            a, b = stack[0] - stack[0].mean(), stack[1] - stack[1].mean()
            if float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9)) < 0.75:
                k = int(stack[1].sum() > stack[0].sum())
                rejected = [dict(file=os.path.join(os.path.basename(items[1 - k][2]), items[1 - k][0]["file"]), score=0.0)]
                stack = stack[k:k + 1]; tots = tots[k:k + 1]; isb = isb[k:k + 1]; ids = ids[k:k + 1]
        if len(stack) >= 3:
            med = np.median(stack, 0)
            def ncc(a, b):
                a = a - a.mean(); b = b - b.mean()
                return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))
            if len(stack) >= 6 and MEDOID:
                # book pages, not a specimen: in joined italic words the letter cuts can
                # slip, and when half a letter's crops are its neighbours the median is a
                # blend that rejects nothing. Take the reference from the impressions that
                # agree with the most typical one (the medoid) instead.
                sm = np.array([cv2.resize(s_, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA).ravel() for s_ in stack])
                sm = sm - sm.mean(1, keepdims=True); sm /= np.linalg.norm(sm, axis=1, keepdims=True) + 1e-9
                P = sm @ sm.T
                ref = int(np.argmax(np.median(P, 1)))
                if SEEDS.get(ch) in list(ids):
                    ref = int(list(ids).index(SEEDS[ch]))
                    print(ch, "reference seeded by eye:", SEEDS[ch])
                core = P[ref] >= 0.6
                if os.environ.get("COLINES_DEBUG"):
                    print(ch, "reference row", np.round(np.sort(P[ref]), 2).tolist())
                if core.sum() >= 3:
                    med = np.median(stack[core], 0)
                else:
                    core = None
            else:
                core = None
            scores = np.array([ncc(s, med) for s in stack])
            mad = np.median(np.abs(scores - np.median(scores))) + 1e-3
            keep = scores >= min(np.median(scores) - 4 * mad, 0.9)
            keep |= scores >= 0.85
            if core is not None and (scores >= 0.5).sum() >= 3:
                keep &= scores >= 0.5     # the mis-cut crops form a second cluster far below
            if os.environ.get("COLINES_DEBUG"):
                print(ch, "scores", np.round(np.sort(scores), 2).tolist())
            if keep.sum() >= 2:
                rejected = [dict(file=os.path.join(os.path.basename(items[k][2]), items[k][0]["file"]),
                                 score=round(float(scores[k]), 3)) for k in np.where(~keep)[0]]
                stack = stack[keep]; tots = tots[keep]; isb = isb[keep]; ids = ids[keep]
                for _ in range(2):
                    mean = stack.mean(0)
                    for k in range(len(stack)):
                        (dx, dy), _ = cv2.phaseCorrelate(mean * win, stack[k] * win)
                        dy = float(np.clip(dy, -dym * UP, dym * UP)); dx = float(np.clip(dx, -dxm * UP, dxm * UP)); dx = float(np.clip(dx, -dxm * UP, dxm * UP))
                        M = np.float32([[1, 0, -dx], [0, 1, -dy]])
                        stack[k] = cv2.warpAffine(stack[k], M, (W * UP, H * UP), flags=cv2.INTER_LINEAR)
        if all(it[2] in supp for it in items) and len(stack) >= 20:
            # microfilm: many impressions that register poorly average to a smear;
            # keep the best-matching quarter and re-register them on their own mean
            med0 = np.median(stack, 0); m0 = med0 - med0.mean()
            sc = np.array([((s - s.mean()) * m0).sum() / (np.sqrt(((s - s.mean()) ** 2).sum() * (m0 ** 2).sum()) + 1e-9) for s in stack])
            if np.median(sc) < 0.7:
                top = np.argsort(-sc)[:max(8, len(stack) // 4)]
                stack = stack[top]; tots = tots[top]; isb = isb[top]; ids = ids[top]
                for _ in range(3):
                    mean_ = stack.mean(0)
                    for k in range(len(stack)):
                        (dx, dy), _ = cv2.phaseCorrelate(mean_ * win, stack[k] * win)
                        dy = float(np.clip(dy, -dym * UP, dym * UP)); dx = float(np.clip(dx, -dxm * UP, dxm * UP))
                        stack[k] = cv2.warpAffine(stack[k], np.float32([[1, 0, -dx], [0, 1, -dy]]), (W * UP, H * UP), flags=cv2.INTER_LINEAR)
                print(ch, "book-only glyph sharpened: best", len(stack), "impressions kept")
        if all(it[2] in supp for it in items):
            # a book-only glyph must be well attested: enough impressions that
            # agree with each other (OCR misreads figures and rare capitals, and a
            # wrong glyph is worse than a missing one)
            # agreement of the impressions kept after outlier rejection (measured
            # before rejection, a few misreads would sink a well-attested glyph)
            agree = 0.0
            if len(stack) >= 3:
                med2 = np.median(stack, 0) - np.median(stack, 0).mean()
                agree = float(np.median([((s - s.mean()) * med2).sum() / (np.sqrt(((s - s.mean()) ** 2).sum() * (med2 ** 2).sum()) + 1e-9) for s in stack]))
            pick = SINGLES.get(ch) if thin else None
            if pick is not None and pick in list(ids0):
                # too few to average, but this impression was checked by eye
                # (scripts/impression_singles.json): Impression font only
                j = int(np.where(ids0 == pick)[0][0])
                stack, tots, isb, ids = stack0[j:j + 1], tots0[j:j + 1], isb0[j:j + 1], ids0[j:j + 1]
                rejected = []
                print(ch, "single impression verified by eye:", pick)
            elif len(stack) < MIN_BOOK:
                print(ch, "book-only glyph dropped: n", len(stack), "agreement", round(agree, 3))
                if thin:
                    os.makedirs(os.path.join(out, "thin"), exist_ok=True)
                    for k_, s_ in enumerate(stack0):
                        cv2.imwrite(os.path.join(out, "thin", f"{glyph_id(ch)}_{k_}.png"), (np.clip(s_, 0, 1) * 65535).astype(np.uint16))
                    thin_log[glyph_id(ch)] = dict(ch=ch, ids=list(map(str, ids0)), kept_by_rejection=list(map(str, ids)))
                continue
            else:
                book_agree[glyph_id(ch)] = (ch, len(stack), agree)   # judged after the loop
        # the Impression fonts show one real printing: keep the impressions as they
        # were before congealing warps them (half precision, to spare memory)
        if dot_cut is not None and len(stack) >= 2:
            # the dot sits a little differently relative to the stem on each
            # impression, so with the stems registered the dots average to a faint
            # blur that the trace loses. Register the dot on its own (everything above
            # the stem's top) and join it back, as the Q's tail is.
            dots = stack.copy()
            wd = np.zeros_like(win); wd[:dot_cut, :] = 1
            wd = cv2.GaussianBlur(wd, (0, 0), 2 * UP)
            for _ in range(3):
                dm = dots.mean(0)
                for k in range(len(dots)):
                    (dx, dy), _ = cv2.phaseCorrelate(dm * wd, dots[k] * wd)
                    dy = float(np.clip(dy, -dym * UP, dym * UP)); dx = float(np.clip(dx, -6 * UP, 6 * UP))
                    dots[k] = cv2.warpAffine(dots[k], np.float32([[1, 0, -dx], [0, 1, -dy]]), (W * UP, H * UP), flags=cv2.INTER_LINEAR)
            blend = np.clip((dot_cut - np.arange(H * UP)[:, None]) / (2.0 * UP) + 0.5, 0, 1).astype(np.float32)
            for k in range(len(stack)):
                stack[k] = stack[k] * (1 - blend) + dots[k] * blend
            print(ch, "dot registered on its own above row", dot_cut)
        unwarped = None
        if CONGEAL and len(stack) >= 4:
            unwarped = stack.astype(np.float16)
            stack = congeal(stack)
        mean, std = np.clip(stack.mean(0), 0, 1), stack.std(0)
        if ch in TAILED and len(stack) >= 2:
            # the tail sits in a slightly different place relative to the bowl in
            # every impression: with the bowls registered the tails average to a
            # blur that traces lumpy. Register the tail on its own (everything below
            # the lower part of the bowl) and join the two sharp halves.
            rows = np.where((mean > 0.3).any(1))[0]
            if len(rows):
                cut = int(base_row * UP - 0.12 * (base_row * UP - rows[0]))
                tail = stack.copy()
                wt = np.zeros_like(win); wt[cut:, :] = 1
                wt = cv2.GaussianBlur(wt, (0, 0), 2 * UP) * win
                for _ in range(3):
                    tm = tail.mean(0)
                    for k in range(len(tail)):
                        (dx, dy), _ = cv2.phaseCorrelate(tm * wt, tail[k] * wt)
                        dy = float(np.clip(dy, -dym * UP, dym * UP)); dx = float(np.clip(dx, -6 * UP, 6 * UP))
                        tail[k] = cv2.warpAffine(tail[k], np.float32([[1, 0, -dx], [0, 1, -dy]]), (W * UP, H * UP), flags=cv2.INTER_LINEAR)
                blend = np.clip((np.arange(H * UP)[:, None] - cut) / (2.0 * UP) + 0.5, 0, 1).astype(np.float32)
                for k in range(len(stack)):
                    stack[k] = stack[k] * (1 - blend) + tail[k] * blend
                mean, std = np.clip(stack.mean(0), 0, 1), stack.std(0)
        if 2 <= len(stack) <= 3:
            # with so few impressions a mean keeps any one copy's accident (a stain
            # or smudge on the paper): the median of three outvotes it, and with
            # two only ink both copies share is kept (the trace's ink-area match
            # restores the weight the intersection loses)
            # but a thin hairline never lands on exactly the same pixels twice, so a
            # strict per-pixel vote erases it: where every copy has ink within a
            # couple of pixels, keep the mean; elsewhere (a stain on one copy) vote
            robust = np.clip(np.median(stack, 0) if len(stack) == 3 else stack.min(0), 0, 1)
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4 * UP + 1, 4 * UP + 1))
            near = np.array([cv2.dilate(s_.astype(np.float32), k) > 0.3 for s_ in stack])
            agree_all = near.sum(0) >= (len(stack) if len(stack) == 2 else 2)
            mean = np.where(agree_all, mean, robust)
        if len(stack) < 20:
            # averaging many impressions smooths away the grain of ink and paper; a
            # letter seen only a few times keeps it and traces lumpy beside its
            # neighbours. Give it the smoothing its average lacks (none at ~20+).
            sig = 2.0 * UP * np.sqrt(1 - len(stack) / 20.0)
            mean = cv2.GaussianBlur(mean.astype(np.float32), (0, 0), sig)
        gid = glyph_id(ch)
        cv2.imwrite(os.path.join(out, f"avg_{gid}.png"), (mean * 65535).astype(np.uint16))
        cv2.imwrite(os.path.join(out, f"std_{gid}.png"), (np.clip(std * 2, 0, 1) * 255).astype(np.uint8))
        # the single most typical real impression, for the "printed" version: the
        # one that departs least from the consensus (a stained copy departs most)
        if len(stack) <= 3:
            best = int(np.argmin([np.abs(s - mean).sum() for s in stack]))
        else:
            mc = mean - mean.mean()
            best = int(np.argmax([((s - s.mean()) * mc).sum() / (np.linalg.norm(s - s.mean()) + 1e-9) for s in stack]))
        # keep that impression's own edges and texture, but nothing outside the
        # consensus letter (plus a small margin): stains, specks, neighbours
        keep = cv2.dilate((mean > 0.25).astype(np.uint8), np.ones((3 * UP, 3 * UP), np.uint8)).astype(np.float32)
        real = unwarped[best].astype(np.float32) if unwarped is not None and len(unwarped) == len(stack) else stack[best]
        cv2.imwrite(os.path.join(out, f"inst_{gid}.png"), (np.clip(real * keep, 0, 1) * 65535).astype(np.uint16))
        # ink area each real impression shows at its own copy's Otsu level
        # a letter mixing sheet and book impressions takes its weight from the sheet
        # ones (microfilm prints heavier; the sheet is the ground truth for weight)
        wsel = [k_ for k_ in range(len(stack)) if not isb[k_]] if (isb.any() and not isb.all()) else list(range(len(stack)))
        target_area = float(np.mean([(stack[k_] > tots[k_]).sum() for k_ in wsel]))
        if all(it[2] in supp for it in items):
            target_area *= float(np.mean([weight_ratio[group(it[2])] for it in items]))
        info[gid] = dict(ch=ch, n=int(len(stack)), target_area=target_area, rejected=rejected, copies=sorted({os.path.basename(d) for _, _, d, _ in items}))
        if len(stack) >= 4 and _prof.get("split_half"):
            # the impressions averaged in two halves: a set of mis-cuts or misreads disagrees with
            # itself (read by check_glyphs.py; adds a field, changes no image)
            ha, hb = stack[0::2].mean(0), stack[1::2].mean(0)
            ha = ha - ha.mean(); hb = hb - hb.mean()
            info[gid]["split_half"] = round(float((ha * hb).sum() / (np.sqrt((ha * ha).sum() * (hb * hb).sum()) + 1e-9)), 3)
        if thin and pick is not None and pick in list(ids0):
            info[gid]["single"] = pick       # build.py leaves it out of the clean font
        print(ch, len(stack), "of", len(items), [r["score"] for r in rejected])
    # book-only glyphs: microfilm impressions agree less than the sheet's, so the
    # bar is relative to how well this book's well-attested glyphs agree
    ref = [a for _, n, a in book_agree.values() if n >= 20]
    bar = min(0.6 * float(np.median(ref)), 0.5) if len(ref) >= 3 else 0.5   # garbage is then caught by check_plausible.py
    for gid, (ch, n, a) in book_agree.items():
        if a < bar:
            print(ch, f"book-only glyph dropped: n {n} agreement {a:.3f} < {bar:.3f}")
            info.pop(gid, None)
            for pre in ("avg_", "std_", "inst_"):
                try:
                    os.remove(os.path.join(out, f"{pre}{gid}.png"))
                except OSError:
                    pass
    if book_agree:
        print("book-only agreement bar", round(bar, 3), "from", len(ref), "well-attested glyphs")
    if thin_log:
        json.dump(thin_log, open(os.path.join(out, "thin", "thin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dict(glyphs=info, up=UP, base_row=base_row * UP, width=W * UP, height=H * UP,
                   scan_ppi=600), open(os.path.join(out, "glyphs.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
