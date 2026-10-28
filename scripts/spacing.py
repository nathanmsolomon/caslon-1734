"""Recover each sort's metal set-width from how neighbours sit in printed words.

Usage: python -I spacing.py <avg_dir> <text_lines> <instances_dir> [...]

Within a word, metal bodies abut, so for neighbours A then B:
    inkleft(B) - inkleft(A) = r_A + lsb_B
where r_A is the distance from A's ink left edge to its body's right edge and
lsb_B is B's left sidebearing. Solved by least squares across every pair on
every copy. The one free constant (shifting all r up and all lsb down) is fixed
by asking symmetric letters to have equal sidebearings on average.
<text_lines> = how many lines are running text (later lines, e.g. a spaced
capitals line, get their own unknown extra space per line).
Writes metrics.json (scan px, 600 ppi) into avg_dir.
"""
import sys, os, json
import numpy as np
import cv2

SYMMETRIC = set("nouimlvxw")
# capital side shapes (left, right): s = straight stem, r = round, d = diagonal,
# o = open/overhanging. Only a weak prior; measured pairs override it.
CAP_SIDES = {
    "A": "dd", "B": "sr", "C": "ro", "D": "sr", "E": "so", "F": "so", "G": "rs",
    "H": "ss", "I": "ss", "J": "so", "K": "sd", "L": "so", "M": "ss", "N": "ss",
    "O": "rr", "P": "sr", "Q": "rr", "R": "sd", "S": "rr", "T": "oo", "U": "ss",
    "V": "dd", "W": "dd", "X": "dd", "Y": "dd", "Z": "rr", "&": "rr",
    ",": "rr", ".": "rr", ":": "rr", ";": "rr", "-": "rr", "?": "rr", "!": "rr",
}
# pairs that don't abut body-to-body: Q's tail is a kern overhanging the next
# sort, and compositors put a thin space before : ; ? !
SKIP_PAIR = lambda a, b: a == "Q" or b in ":;?!"
SIDE_PX = {"s": 6.0, "r": 3.5, "d": 0.5, "o": 1.5}   # scan px at Pica, 600 ppi
PRIOR_W = 0.3


def main():
    avg, ntext, args = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    expanded = []
    for a in args:
        expanded += [l.strip() for l in open(a[1:]) if l.strip()] if a.startswith("@") else [a]
    dirs = [a.lstrip("+") for a in expanded]
    alltext = {a.lstrip("+") for a in expanded if a.startswith("+")}  # book pages: every line is text
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    up = g["up"]
    # ink width of each averaged glyph at the 50% density contour (scan px)
    inkw = {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        xs = np.where((a > 0.5).any(0))[0]
        if len(xs) == 0:
            continue                      # no solid ink in the mean: unusable glyph
        inkw[v["ch"]] = (xs[-1] - xs[0] + 1) / up
    chars = sorted(inkw)
    ci = {c: k for k, c in enumerate(chars)}
    n = len(chars)
    rows, rhs, extra = [], [], {}
    seen_l, seen_r = {}, {}     # how often each side is observed abutting in running text
    for di, d in enumerate(dirs):
        I = json.load(open(os.path.join(d, "instances.json"), encoding="utf-8"))["instances"]
        rej = {r["file"] for v in g["glyphs"].values() for r in v["rejected"]}
        I = [i for i in I if os.path.join(os.path.basename(d), i["file"]) not in rej]
        key = {(i["line"], i["word"], i["pos"]): i for i in I}
        # a line of lowercase only (a specimen's "abcdefgh" under its letterspaced
        # capitals) was set solid: measure it like running text, or its letters'
        # sidebearings trade off against the line's unknown spacing
        lines_ = {}
        for i in I:
            lines_.setdefault(i["line"], []).append(i["ch"])
        solid = {ln for ln, chs in lines_.items() if all(len(c) == 1 and c.islower() for c in chs)}
        for i in I:
            j = key.get((i["line"], i["word"], i["pos"] + 1))
            if not j or SKIP_PAIR(i["ch"], j["ch"]) or i["ch"] not in ci or j["ch"] not in ci:
                continue
            dx = (j["x0"] - i["x0"]) * np.sqrt(1 + i.get("slope", 0) ** 2)
            row = np.zeros(2 * n)
            row[ci[i["ch"]]] += 1          # r_A
            row[n + ci[j["ch"]]] += 1      # lsb_B
            text_ = d in alltext or i["line"] < ntext or i["line"] in solid
            if text_:
                seen_r[i["ch"]] = seen_r.get(i["ch"], 0) + 1; seen_l[j["ch"]] = seen_l.get(j["ch"], 0) + 1
            if not text_:         # spaced line: one extra unknown per (copy, line)
                extra.setdefault((di, i["line"]), len(extra))
                row = np.append(row, 0)    # placeholder, widened below
                row = (row, extra[(di, i["line"])])
            rows.append(row); rhs.append(dx)
    m = 2 * n + len(extra)
    A = []
    for row in rows:
        full = np.zeros(m)
        if isinstance(row, tuple):
            full[:2 * n] = row[0][:2 * n]; full[2 * n + row[1]] = 1
        else:
            full[:2 * n] = row
        A.append(full)
    A, b = np.array(A), np.array(rhs)
    # gauge: for symmetric letters lsb = rsb = r - inkw - ... i.e. 2*lsb - r = -inkw
    w = 5.0
    for c in chars:
        if c in SYMMETRIC:
            row = np.zeros(m); row[n + ci[c]] = 2 * w; row[ci[c]] = -w
            A = np.vstack([A, row]); b = np.append(b, -w * inkw[c])
    # very weak prior lsb ~ rsb for every letter: only matters when a side is never
    # observed (e.g. round s, which only ends words where medial s is long)
    for c in chars:
        if c not in CAP_SIDES:
            row = np.zeros(m); row[n + ci[c]] = 2 * 0.05; row[ci[c]] = -0.05
            A = np.vstack([A, row]); b = np.append(b, -0.05 * inkw[c])
    # weak priors so under-determined sorts (capitals seen only in the spaced
    # alphabet line, isolated '&') still get a sensible split of their width.
    # lsb prior row: lsb = p ; rsb prior row: r - inkw = p
    caps_w = [inkw[c] for c in chars if c in CAP_SIDES and c.isupper()]
    side_scale = (np.median(caps_w) / 62.0) if caps_w else 1.0      # SIDE_PX are Pica values
    for c in chars:
        if c not in CAP_SIDES:
            continue
        pl, pr = CAP_SIDES[c]
        for side, cls in (("l", pl), ("r", pr)):
            p = SIDE_PX[cls] * side_scale
            # a side never seen abutting in running text is pinned by the prior
            # (in the spaced alphabet line only sums of neighbouring sides are known)
            wgt = PRIOR_W if (seen_l if side == "l" else seen_r).get(c, 0) else 3.0
            row = np.zeros(m)
            if side == "l":
                row[n + ci[c]] = wgt; target = wgt * p
            else:
                row[ci[c]] = wgt; target = wgt * (p + inkw[c])
            A = np.vstack([A, row]); b = np.append(b, target)
    # robust: iteratively drop large residuals (mislabels that slipped through)
    ndata = len(rows)
    keep = np.ones(len(b), bool)
    for _ in range(4):
        x, *_ = np.linalg.lstsq(A[keep], b[keep], rcond=None)
        res = A @ x - b
        s = 1.4826 * np.median(np.abs(res[:ndata][keep[:ndata]])) + 1e-6
        keep[:ndata] = np.abs(res[:ndata]) < max(3 * s, 1.5)
    x, *_ = np.linalg.lstsq(A[keep], b[keep], rcond=None)
    res = (A @ x - b)[:ndata][keep[:ndata]]
    obs = {c: int(((A[keep][:, ci[c]] != 0) | (A[keep][:, n + ci[c]] != 0)).sum()) for c in chars}
    out = {}
    for c in chars:
        r, lsb = x[ci[c]], x[n + ci[c]]
        adv = lsb + r
        out[c] = dict(adv=float(adv), lsb=float(lsb), rsb=float(r - inkw[c]), inkw=float(inkw[c]), pairs=obs[c])
    extras = {f"copy{k[0]}_line{k[1]}": float(x[2 * n + v]) for k, v in extra.items()}
    json.dump(dict(glyphs=out, extra_space=extras, rms=float(np.sqrt((res ** 2).mean())),
                   pairs_used=int(keep[:ndata].sum()), pairs_total=ndata),
              open(os.path.join(avg, "metrics.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("pairs", int(keep[:ndata].sum()), "of", ndata, "rms px", round(float(np.sqrt((res ** 2).mean())), 2))
    print("extra space on spaced lines:", {k: round(v, 1) for k, v in extras.items()})
    for c in chars:
        o = out[c]
        print(f"{c}\tadv {o['adv']:6.1f}  lsb {o['lsb']:5.1f}  rsb {o['rsb']:5.1f}  pairs {o['pairs']}")


if __name__ == "__main__":
    main()
