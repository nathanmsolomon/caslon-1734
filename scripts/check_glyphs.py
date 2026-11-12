r"""Is each averaged glyph the letter its label says? Three checks that need no eye, for every build.

Usage: python -I -X utf8 check_glyphs.py <avg dir> [--ref=<avg dir>,<avg dir>...] [--out=<dir>] [--italic]
  -> <out>/report.json, report.md, flagged.png   (default out: <avg dir>/checks)
  exit 1 when anything is flagged, 0 when clean.

Why: the fidelity score compares a font with the crops it was built from, so a consistently
mis-cut letter scores well (Garamont's S. Augustin "g" was "af" for two weeks; Colines' italic
T was an e). A flag here means LOOK AT IT, not that the glyph is wrong.

1. CLASS. Every letter has a build that does not depend on the design: x-height letters stop at
   the x-height, capitals and ascenders rise above it, g p q y descend, a full stop is small and
   on the line, an accented letter has ink above the x-height, a ligature is about as wide as its
   parts. Measured in the face's own x-heights (from its own a c e m n o r s u v x z).
2. CROSS-SOURCE. The glyph, scaled to a common x-height, is compared with EVERY letter of one or
   more reference faces of the same style (another size, another revival). It is flagged when it
   matches a different letter clearly better than its own, or is far wider or narrower than its
   own letter in the reference.
3. AGREEMENT. The average against its most typical single impression (inst_*.png), and, when
   average.py recorded it, the two halves of the impressions averaged separately (split_half).
   Junk sets disagree with themselves.
Reads only; writes only under --out.
"""
import os, sys, json, unicodedata
import numpy as np, cv2

XH = set("acemnorsuvxz")
ASC = set("bdhklſ")
DESC = set("gpqy")
MARKS_ABOVE = {"̀", "́", "̂", "̃", "̄", "̈", "̆", "̊"}
N = 40   # common x-height in px for comparison


def load(avg):
    G = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    out = {}
    for gid, v in G["glyphs"].items():
        p = os.path.join(avg, f"avg_{gid}.png")
        a = cv2.imread(p, -1)
        if a is None:
            continue
        a = a.astype(np.float32) / (65535 if a.dtype == np.uint16 else 255)
        m = a > 0.5
        ys, xs = np.where(m)
        if len(ys) < 20:
            continue
        out[v["ch"]] = dict(gid=gid, n=v.get("n"), a=a, top=G["base_row"] - ys.min(), bot=ys.max() - G["base_row"],
                            x0=xs.min(), x1=xs.max(), w=xs.max() - xs.min() + 1, split=v.get("split_half"), meta=v)
    xh = [g["top"] for c, g in out.items() if c in XH]
    return out, (float(np.median(xh)) if len(xh) >= 3 else None), G


def norm(g, xh, base_row):
    """The glyph's ink box on a fixed canvas, x-height = N px, baseline at a fixed row, centred."""
    s = N / xh
    a = g["a"]; H, W = a.shape
    y0 = max(0, int(base_row - 2.6 * xh)); y1 = min(H, int(base_row + 1.4 * xh))
    c = a[y0:y1, max(0, g["x0"] - 2):g["x1"] + 3]
    c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    can = np.zeros((int(4.0 * N) + 2, int(5.0 * N)), np.float32)
    top = int(round(2.6 * N - (base_row - y0) * s))
    h = min(c.shape[0], can.shape[0] - max(top, 0)); w = min(c.shape[1], can.shape[1])
    x = (can.shape[1] - w) // 2
    can[max(top, 0):max(top, 0) + h, x:x + w] = c[:h, :w]
    return can


def ncc(a, b):
    best = -1.0
    for dx in (-3, -2, -1, 0, 1, 2, 3):
        for dy in (-2, 0, 2):
            bb = np.roll(np.roll(b, dx, 1), dy, 0)
            x = a - a.mean(); y = bb - bb.mean()
            best = max(best, float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-9)))
    return best


def class_check(ch, g, xh, glyphs, italic):
    """Return a list of reasons the glyph's build does not fit its label."""
    t, b, w = g["top"] / xh, g["bot"] / xh, g["w"] / xh
    why = []
    base = unicodedata.normalize("NFD", ch)
    if ch.endswith((".sc", ".alt", ".sw")) or ch.startswith("LIG:"):
        return why
    if len(ch) == 1 and len(base) >= 2 and any(m in MARKS_ABOVE for m in base[1:]):
        low = base[0]
        need = 1.25 if low in XH or low in DESC or low in "i" else None   # p-tilde with its tilde lost is a plain p
        if need and t < need:
            why.append(f"accented letter with no ink above the x-height (top {t:.2f} xh)")
        return why
    if len(ch) > 1 and not any(unicodedata.combining(c) for c in ch):
        parts = [glyphs[c]["w"] for c in ch if c in glyphs]
        if len(parts) == len(ch):
            r = g["w"] / sum(parts)
            if r < 0.62 or r > 1.3:
                why.append(f"ligature {r:.2f} x the width of its letters")
        return why
    if len(ch) != 1:
        return why
    if ch in XH:
        if t > 1.3: why.append(f"x-height letter rising to {t:.2f} xh")
        if t < 0.75: why.append(f"x-height letter only {t:.2f} xh tall")
        if b > 0.3 and not (italic and ch in "z"): why.append(f"x-height letter descending {b:.2f} xh")
    elif ch in ASC or ch == "f":
        if t < 1.25: why.append(f"ascender letter only {t:.2f} xh tall")
        if b > 0.3 and not (ch in "fſ" and italic): why.append(f"ascender letter descending {b:.2f} xh")
    elif ch == "t":
        if t < 1.02 or t > 1.75: why.append(f"t {t:.2f} xh tall")
    elif ch in DESC:
        if b < 0.25: why.append(f"descender letter with no descender ({b:.2f} xh)")
        if t > 1.35: why.append(f"descender letter rising to {t:.2f} xh")
    elif ch in "ij":
        if t < 1.15: why.append(f"{ch} with no dot above the x-height ({t:.2f} xh)")
        if ch == "j" and b < 0.2: why.append("j with no descender")
    elif ch.isupper() and ch.isalpha() and ord(ch) < 0x250:
        if t < 1.2: why.append(f"capital only {t:.2f} xh tall")
        if b > 0.3 and ch not in "JQ" and not italic: why.append(f"capital descending {b:.2f} xh")
    elif ch == ".":
        if t > 0.6 or b > 0.25 or w > 0.6: why.append(f"full stop {w:.2f} wide, top {t:.2f}, below {b:.2f} xh")
    elif ch == ",":
        if t > 0.7 or w > 0.7: why.append(f"comma {w:.2f} wide, top {t:.2f} xh")
    elif ch.isdigit():
        if t + b < 0.8: why.append(f"figure only {t + b:.2f} xh tall")
    return why


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1") for a in sys.argv[1:] if a.startswith("--"))
    avg = os.path.normpath(args[0]); out = opt.get("out") or os.path.join(avg, "checks")
    glyphs, xh, G = load(avg)
    if xh is None:
        sys.exit("no x-height letters: cannot check")
    italic = "italic" in opt or "ital" in os.path.basename(avg).lower()
    refs = []
    for r in [x for x in opt.get("ref", "").split(",") if x]:
        if os.path.normpath(r) == avg or not os.path.exists(os.path.join(r, "glyphs.json")):
            continue
        rg, rxh, RG = load(r)
        if rxh:
            refs.append((os.path.basename(os.path.normpath(r)), {c: (norm(g, rxh, RG["base_row"]), g["w"] / rxh) for c, g in rg.items()
                                                                 if not c.endswith("?")}))
    rows = []
    for ch, g in sorted(glyphs.items()):
        if ch.endswith("?"):
            continue
        why = class_check(ch, g, xh, glyphs, italic)
        me = norm(g, xh, G["base_row"]); own, other, wr = [], [], []
        for rname, R in refs:
            sc = {c: ncc(me, im) for c, (im, _) in R.items()}
            if ch in sc:
                own.append(sc[ch]); wr.append((g["w"] / xh) / R[ch][1])
            bo = max(((v, c) for c, v in sc.items() if c != ch), default=(0, ""))
            other.append((bo[0], bo[1], rname, sc.get(ch)))
        ro = dict(ch=ch, gid=g["gid"], n=g["n"], top=round(g["top"] / xh, 2), bot=round(g["bot"] / xh, 2), w=round(g["w"] / xh, 2))
        if ch.endswith((".sw", ".alt", ".sc")):
            own = []      # a second or swash sort differs from the reference's by design
        if own:
            o = float(np.median(own)); ro["own"] = round(o, 3)
            better = [(v, c, rn) for v, c, rn, s in other if s is not None and v - s > 0.10]
            # most references must agree that another letter fits clearly better
            if len(better) > len(own) / 2 and o < 0.80:
                names = sorted({c for _, c, _ in better})
                why.append(f"looks more like {' / '.join(names)} (own {o:.2f}, other {max(v for v, _, _ in better):.2f})")
            elif o < 0.45:
                why.append(f"unlike its own letter in the references ({o:.2f})")
            wmed = float(np.median(wr)); ro["width_vs_ref"] = round(wmed, 2)
            if wmed > 1.6 or wmed < 0.6:
                why.append(f"{wmed:.2f} x the width of its letter in the references")
        elif refs:
            v, c, rn, _ = max(other)
            ro["nearest"] = f"{c} {v:.2f}"
        inst = cv2.imread(os.path.join(avg, f"inst_{g['gid']}.png"), -1)
        if inst is not None and (g["n"] or 0) >= 3:
            i = inst.astype(np.float32) / (65535 if inst.dtype == np.uint16 else 255)
            x, y = g["a"] - g["a"].mean(), i - i.mean()
            ag = float((x * y).sum() / (np.sqrt((x * x).sum() * (y * y).sum()) + 1e-9)); ro["avg_vs_inst"] = round(ag, 3)
            if ag < 0.55:
                why.append(f"the average is unlike its most typical impression ({ag:.2f})")
        if g["split"] is not None:
            ro["split_half"] = g["split"]
            if g["split"] < 0.6:
                why.append(f"the two halves of its impressions disagree ({g['split']:.2f})")
        ro["flags"] = why
        rows.append(ro)
    os.makedirs(out, exist_ok=True)
    flagged = [r for r in rows if r["flags"]]
    json.dump(dict(avg=avg, xheight_px=round(xh / G.get("up", 1), 2), italic=italic, references=[r for r, _ in refs], glyphs=rows),
              open(os.path.join(out, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    L = [f"# Glyph checks: {os.path.basename(avg)}", "", f"{len(rows)} glyphs, {len(flagged)} flagged. References: {', '.join(r for r, _ in refs) or 'none'}.", ""]
    L += [f"- **{r['ch']}** (U+{' U+'.join('%04X' % ord(c) for c in r['ch'])}, n={r['n']}): " + "; ".join(r["flags"]) for r in flagged]
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    if flagged:
        tiles = []
        for r in flagged:
            t = (255 - np.clip(norm(glyphs[r["ch"]], xh, G["base_row"]), 0, 1) * 255).astype(np.uint8)
            t = np.pad(t, ((0, 26), (0, 0)), constant_values=255)
            cv2.putText(t, "U+" + "+".join("%04X" % ord(c) for c in r["ch"]) + f" n{r['n']}", (2, t.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1)
            cv2.line(t, (0, int(2.6 * N)), (t.shape[1], int(2.6 * N)), 170, 1); cv2.line(t, (0, int(1.6 * N)), (t.shape[1], int(1.6 * N)), 210, 1)
            tiles.append(np.pad(t, 1, constant_values=120))
        while len(tiles) % 6:
            tiles.append(np.full_like(tiles[0], 255))
        cv2.imwrite(os.path.join(out, "flagged.png"), np.vstack([np.hstack(tiles[k:k + 6]) for k in range(0, len(tiles), 6)]))
    print(f"{os.path.basename(avg)}: {len(rows)} glyphs, {len(flagged)} flagged" + ("" if not flagged else ": " + "  ".join(r["ch"] for r in flagged)))
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
