"""Segment a book page into labelled glyph instances using the scan's OCR text layer.

Usage: python -I segment_ocr.py <page.jpg> <djvu.xml> <page_index> <ppi> <avg_dir> <out_dir> [expected_xheight]

The page is resampled to 600 ppi so it shares the 1734 pipeline's geometry.
OCR words give text + box; components inside a box are grouped into glyphs and
accepted only when the count matches a tokenisation of the word (ligature
readings tried when needed). OCR writes long s as 'f', so every f-shape is
re-decided by comparing it with the 1734 'f' and 'ſ'. Words whose known letters
don't match the 1734 roman (italic, other founts, OCR garbage) are dropped.
Ligature sorts the 1734 sheet doesn't show are labelled LIG:<ocr> for review.
Words whose blob count doesn't match (touching or broken letters) fall back to
forced alignment with the 1734 templates (align_core.py); those instances are
marked "aligned". Lines are size-checked against the page's own x-height.
"""
import sys, os, re, json, html, itertools
import cv2
import numpy as np

# corrected spellings for words the OCR misread (e.g. æ read as "ae"): a JSON map
# {page_index: {ocr_text: corrected_text}}; with CASLON_ONLYFIX set, only those words
WF = json.load(open(os.environ["CASLON_WORDFIX"], encoding="utf-8")) if os.environ.get("CASLON_WORDFIX") else None
ONLYFIX = bool(os.environ.get("CASLON_ONLYFIX"))
YR = [float(v) for v in os.environ['CASLON_YRANGE'].split(',')] if os.environ.get('CASLON_YRANGE') else None

sys.path.insert(0, os.path.dirname(__file__))
from segment import repair  # noqa: E402
from align_core import load_templates as load_align, align_word  # noqa: E402

ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.;:-'?!&()æœÆŒ")
# OCR-space ligature patterns (OCR spells long s as f)
LIGS = ["ffi", "ffl", "ff", "fi", "fl", "ft", "ct", "fb", "fh", "fk"]
TARGET = set("kwxyzYZ0123456789")
XH_EXPECT = None  # x-height (px at 600 ppi) of the size being harvested


def tokenisations(word):
    """All ways to read the word with optional ligature merges."""
    out = []
    def rec(k, acc):
        if k == len(word):
            out.append(acc); return
        rec(k + 1, acc + [word[k]])
        for L in LIGS:
            if word.startswith(L, k):
                rec(k + len(L), acc + [L])
    rec(0, [])
    return out


def load_templates(avg):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    up, out = g["up"], {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
        a = cv2.resize(a, None, fx=1 / up, fy=1 / up, interpolation=cv2.INTER_AREA)
        ys, xs = np.where(a > 0.15)
        out[v["ch"]] = a[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3]
    return out


def match(dens, g, tpl):
    """Best NCC of template within a window around glyph g."""
    th, tw = tpl.shape
    cx, cy = (g["x0"] + g["x1"]) // 2, (g["y0"] + g["y1"]) // 2
    y0, x0 = max(0, cy - th // 2 - 8), max(0, cx - tw // 2 - 8)
    win = dens[y0:y0 + th + 16, x0:x0 + tw + 16]
    if win.shape[0] < th or win.shape[1] < tw:
        return -1.0
    return float(cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED).max())


# how each OCR ligature pattern may be read when force-aligning (long s as f)
ROMAN_READ = {"ffi": ("ffi", "ſſi"), "ffl": ("ffl",), "ff": ("ff", "ſſ"), "fi": ("fi", "ſi"), "fl": ("fl", "ſl"),
              "ft": ("ſt",), "fb": ("ſb",), "fh": ("ſh",), "fk": ("ſk",), "ct": ("ct",)}


def align_readings(core, TA, cap=16):
    """Readings of an OCR word for forced alignment: ligature patterns as one sort
    (the 1734 template if there is one, else a wildcard LIG:<ocr>), a lone f as f
    or long s."""
    toks, k = [], 0
    while k < len(core):
        L = next((L for L in LIGS if core.startswith(L, k)), None)
        if L:
            toks.append(L); k += len(L)
        else:
            toks.append(core[k]); k += 1
    opts = []
    for tk in toks:
        if tk in ROMAN_READ:
            opts.append([(r,) for r in ROMAN_READ[tk] if r in TA] or [("LIG:" + tk,)])
        elif tk == "f" and "ſ" in TA:
            opts.append([("f",), ("ſ",)])
        else:
            opts.append([(tk,)])
    out = [()]
    for o in opts:
        out = [a + b for a in out for b in o][:cap]
    return out


def align_fallback(text, cs, dens, bw, im, paper, TA):
    """A word whose ink blobs don't match its spelling (touching or broken
    letters): place the 1734 templates by forced alignment and give each ink
    pixel to a letter, as the italic harvester does. Kept only when the letters
    the sheet shows match well (mean 0.7, none below 0.45)."""
    core = text.strip(",.;:?!'()-")
    if len(core) < 2 or not core.isalpha() or not cs or not XH_EXPECT:
        return None
    mid = [c for c in cs if 0.75 * XH_EXPECT <= c["h"] <= 1.3 * XH_EXPECT]
    if not mid:
        return None
    base = float(np.median([c["y"] + c["h"] for c in mid]))
    wx0 = int(min(c["x"] for c in cs)); wx1 = int(max(c["x"] + c["w"] for c in cs))
    best = None
    for v in align_readings(core, TA):
        res, score = align_word(dens, bw, im, paper, base, wx0, wx1, list(v), TA, XH_EXPECT, {})
        if score is not None and (best is None or score > best[1]):
            best = (res, score, v)
    if best is None:
        return None
    res, score, v = best
    known = [o["score"] for o in res if o and o["name"] in TA]
    if score < 0.7 or any(o is None for o in res) or (known and min(known) < 0.45):
        return None
    out = []
    for o in res:
        x0, y0, x1, y1 = o["box"]
        out.append((dict(x0=x0, x1=x1, y0=y0, y1=y1, img=o["img"], crop_xy=o["crop_xy"]), o["name"]))
    return out


def main():
    global XH_EXPECT
    page, xml, pidx, ppi, avg, out = sys.argv[1:7]
    XH_EXPECT = float(sys.argv[7]) if len(sys.argv) > 7 else None
    pidx, ppi = int(pidx), float(ppi)
    k = 600.0 / ppi
    im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)
    im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    os.makedirs(out, exist_ok=True)
    blur = cv2.GaussianBlur(im, (3, 3), 0)
    otsu, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    comps = [dict(x=s[0], y=s[1], w=s[2], h=s[3], a=s[4], i=j) for j, s in enumerate(stats) if j and s[4] >= 12]
    paper, ink = np.percentile(im, 80), np.percentile(im, 1)
    dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
    tpls = load_templates(avg)
    TA = load_align(avg)

    x = open(xml, encoding="utf-8").read()
    pg = re.split(r"<OBJECT ", x)[1:][pidx]
    lines = re.findall(r"<LINE>(.*?)</LINE>", pg, re.S)
    xheights = []
    instances, stats_ = [], dict(words=0, accepted=0, italic=0, count=0, ambiguous=0)
    pending = []
    for li, L in enumerate(lines):
        words = [(list(map(int, c.split(","))), html.unescape(t).strip())
                 for c, t in re.findall(r'<WORD coords="([\d,]+)"[^>]*>([^<]*)</WORD>', L)]
        line_glyphs = []
        for wi, ((l, b, r, t), text) in enumerate(words):
            if WF is not None:
                fixmap = WF.get(str(pidx), {})
                if text in fixmap:
                    text = fixmap[text]
                elif ONLYFIX:
                    continue
            # a later specimen book sets several cuts of one size on a page: harvest
            # only the block asked for (CASLON_YRANGE = top,bottom in OCR coords)
            if YR and not (YR[0] <= (t + b) / 2 <= YR[1]):
                continue
            stats_["words"] += 1
            text = text.strip()
            if not text or any(ch not in ALLOWED for ch in text):
                continue
            core = text.strip(",.;:?!'()-")
            # letters only from all-letter words, figures only from all-figure tokens;
            # a lone mark (compositors set ? ! ; : after a thin space) is its own token
            lone = len(text) == 1 and text in "?!;:"
            # the ampersand stands alone or as "&c." (et cetera)
            amp = core in ("&", "&c")
            if not lone and not amp and (not core or not (core.isalpha() or all(ch.isdigit() or ch in ",." for ch in core))):
                continue
            l, b, r, t = [int(v * k) for v in (l, b, r, t)]
            hgt = b - t
            cs = [c for c in comps if l - 4 <= c["x"] + c["w"] / 2 <= r + 4
                  and t - 0.3 * hgt <= c["y"] + c["h"] / 2 <= b + 0.3 * hgt]
            cs.sort(key=lambda c: c["x"])
            glyphs = []
            for c in cs:
                if glyphs:
                    gg = glyphs[-1]
                    ov = min(gg["x1"], c["x"] + c["w"]) - max(gg["x0"], c["x"])
                    if ov > 0.5 * min(c["w"], gg["x1"] - gg["x0"]):
                        gg["parts"].append(c)
                        gg["x0"] = min(gg["x0"], c["x"]); gg["x1"] = max(gg["x1"], c["x"] + c["w"])
                        continue
                glyphs.append(dict(parts=[c], x0=c["x"], x1=c["x"] + c["w"]))
            for gg in glyphs:
                gg["y0"] = min(p["y"] for p in gg["parts"]); gg["y1"] = max(p["y"] + p["h"] for p in gg["parts"])
            if lone and len(glyphs) != 1:
                # OCR boxes for lone marks are loose: keep the one glyph built
                # from two vertically stacked parts (stroke over dot)
                def stacked(gg):
                    if len(gg["parts"]) < 2:
                        return False
                    ps = sorted(gg["parts"], key=lambda q: q["y"])
                    return ps[0]["y"] + ps[0]["h"] <= ps[-1]["y"] + 2
                st = [gg for gg in glyphs if stacked(gg)]
                glyphs = st if len(st) == 1 else glyphs
            cands = [tk for tk in tokenisations(text) if len(tk) == len(glyphs)]
            if not cands:
                fixed = repair(glyphs, len(text), bw, lab) if glyphs else []
                if len(fixed) == len(text):
                    glyphs, cands = fixed, [list(text)]
            if not cands:
                al = align_fallback(text, cs, dens, bw, im, paper, TA)
                if al:
                    stats_["aligned"] = stats_.get("aligned", 0) + 1
                    for pos, (gg, tk) in enumerate(al):
                        line_glyphs.append((wi, pos, len(al), gg, tk))
                    continue
                stats_["count"] += 1; continue
            if len(cands) > 1:
                # prefer the reading with ligatures only where glyphs are wide
                stats_["ambiguous"] += 1; continue
            toks = cands[0]
            # italic / wrong-fount check on letters the 1734 sheet shows
            known = [match(dens, gg, tpls[tk]) for gg, tk in zip(glyphs, toks) if tk in tpls and tk not in "fs"]
            if len(known) >= 2 and np.median(known) < 0.6:
                stats_["italic"] += 1; continue
            labels = []
            for gg, tk in zip(glyphs, toks):
                if tk == "f":
                    tk = "ſ" if match(dens, gg, tpls["ſ"]) > match(dens, gg, tpls["f"]) else "f"
                elif tk == "s":
                    tk = "s"
                elif len(tk) > 1:
                    alt = {"fi": "ſi", "ft": "ſt", "ffi": "ſſi"}.get(tk)
                    if alt and alt in tpls and match(dens, gg, tpls[alt]) > 0.8:
                        tk = alt
                    elif tk == "ft":
                        tk = "LIG:ft"
                    else:
                        tk = "LIG:" + tk
                labels.append(tk)
            stats_["accepted"] += 1
            for pos, (gg, tk) in enumerate(zip(glyphs, labels)):
                line_glyphs.append((wi, pos, len(labels), gg, tk))
        if not line_glyphs:
            continue
        # size check: x-height letters must agree with the line's x-height; a
        # word whose x-height letters disagree is another size (small caps, notes)
        XH = set("acemnorsuvwxz")
        hs = [gg["y1"] - gg["y0"] for _, _, _, gg, tk in line_glyphs if tk in XH]
        # correction-only runs see just a word or two per line; title pages have
        # short lines too (CASLON_MINXH sets the minimum)
        if len(hs) < int(os.environ.get("CASLON_MINXH", 2 if ONLYFIX else 5)):
            continue
        pending.append((li, line_glyphs, float(np.median(hs))))
    # size check per line, against this page's own x-height: ink spread makes a
    # whole book (or page) measure a few percent taller or shorter than the
    # sheet, so a fixed window around the sheet's x-height threw away good lines.
    # The page reference is the median over lines near the expected size (another
    # size on the page, such as notes, is at least ~10% off); lines must then be
    # within 5% of it.
    near = [xh for _, _, xh in pending if not XH_EXPECT or abs(xh / XH_EXPECT - 1) <= 0.12]
    ref = float(np.median(near)) if near else None
    for li, line_glyphs, xh in pending:
        if ref is None or abs(xh / ref - 1) > 0.05:
            stats_["wrong_size_lines"] = stats_.get("wrong_size_lines", 0) + 1
            continue
        bad_words = set()
        for wi in {w for w, _, _, _, _ in line_glyphs}:
            wh = [gg["y1"] - gg["y0"] for w, _, _, gg, tk in line_glyphs if w == wi and tk in XH]
            if wh and abs(np.median(wh) / xh - 1) > 0.15:
                bad_words.add(wi)
        line_glyphs = [lg for lg in line_glyphs if lg[0] not in bad_words
                       and not (lg[4] in XH and abs((lg[3]["y1"] - lg[3]["y0"]) / xh - 1) > 0.2)]
        xheights.append(xh)
        flat = [((gg["x0"] + gg["x1"]) / 2, gg["y1"]) for _, _, _, gg, tk in line_glyphs if tk in "imnrhkluxBDEFHIKLMNPRTX"]
        if len(flat) < 3:
            continue
        fx, fy = np.array(flat, float).T
        coef = np.polyfit(fx, fy, 1)
        for _ in range(3):
            res = fy - np.polyval(coef, fx)
            keep = np.abs(res) < max(2.0, 2.5 * np.median(np.abs(res)))
            if keep.sum() >= 3:
                coef = np.polyfit(fx[keep], fy[keep], 1)
        for wi, pos, nw, gg, tk in line_glyphs:
            if "img" in gg:
                clean = gg["img"]; gx0, gy0 = gg["crop_xy"]
                fn = f"{len(instances):04d}.png"
                cv2.imwrite(os.path.join(out, fn), clean)
                instances.append(dict(file=fn, ch=tk, line=li, word=wi, pos=pos, nword=nw,
                                      x0=int(gg["x0"]), x1=int(gg["x1"]), y0=int(gg["y0"]), y1=int(gg["y1"]),
                                      crop=[int(gx0), int(gy0)], baseline=float(np.polyval(coef, (gg["x0"] + gg["x1"]) / 2)),
                                      slope=float(coef[0]), aligned=True))
                continue
            pad = 6
            gx0, gy0 = max(0, gg["x0"] - pad), max(0, gg["y0"] - pad)
            gx1, gy1 = gg["x1"] + pad, gg["y1"] + pad
            crop = im[gy0:gy1, gx0:gx1]
            m = np.zeros_like(crop, dtype=bool)
            for p in gg["parts"]:
                mm = lab[gy0:gy1, gx0:gx1] == p["i"]
                if "clip" in p:
                    xs = np.arange(gx0, gx0 + mm.shape[1])
                    mm &= ((xs >= p["clip"][0]) & (xs < p["clip"][1]))[None, :]
                m |= mm
            m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            clean = np.where(m, crop, np.uint8(paper)).astype(np.uint8)
            fn = f"{len(instances):04d}.png"
            cv2.imwrite(os.path.join(out, fn), clean)
            instances.append(dict(file=fn, ch=tk, line=li, word=wi, pos=pos, nword=nw,
                                  x0=int(gg["x0"]), x1=int(gg["x1"]), y0=int(gg["y0"]), y1=int(gg["y1"]),
                                  crop=[int(gx0), int(gy0)], baseline=float(np.polyval(coef, (gg["x0"] + gg["x1"]) / 2)),
                                  slope=float(coef[0])))
    json.dump(dict(instances=instances, otsu=float(otsu), source=os.path.basename(page),
                   xheight=float(np.median(xheights)) if xheights else None),
              open(os.path.join(out, "instances.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tgt = sum(1 for i in instances if i["ch"] in TARGET or i["ch"].startswith("LIG"))
    print(os.path.basename(page), stats_, "instances", len(instances), "target/ligature", tgt,
          "x-height px@600", round(float(np.median(xheights)), 1) if xheights else None)


if __name__ == "__main__":
    main()
