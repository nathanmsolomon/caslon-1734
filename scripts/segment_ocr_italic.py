"""Harvest ITALIC glyph instances from a book page, using its OCR layer.

Usage: python -I segment_ocr_italic.py <page.jpg> <djvu.xml> <page_index> <ppi> <slant_deg>
                                       <italic_avg> <roman_avg> <xheight_px600> <out_dir> [wildwidths.json]

The page is resampled to 600 ppi and sheared upright by the italic slant; OCR
boxes are mapped through the same shear. Each acceptable word is force-aligned
with the italic templates (unknown letters as wildcards). A word is kept only if
its known letters match the italic clearly better than the roman, and its
x-height agrees with the size being harvested.
"""
import sys, os, re, json, html
import cv2
import numpy as np

# corrected spellings for words the OCR misread (e.g. æ read as "ae"): a JSON map
# {page_index: {ocr_text: corrected_text}}; with CASLON_ONLYFIX set, only those words
WF = json.load(open(os.environ["CASLON_WORDFIX"], encoding="utf-8")) if os.environ.get("CASLON_WORDFIX") else None
ONLYFIX = bool(os.environ.get("CASLON_ONLYFIX"))
YR = [float(v) for v in os.environ['CASLON_YRANGE'].split(',')] if os.environ.get('CASLON_YRANGE') else None

sys.path.insert(0, os.path.dirname(__file__))
from align_core import load_templates, align_word, score_maps  # noqa: E402

XH = set("acemnorsuvwxz")
# OCR-space ligature patterns (OCR spells long s as f), longest first
# (the italic has no ſb/ſh/ſk sorts: those are two letters)
LIGS = ["ffi", "ffl", "ff", "fi", "fl", "ft"]
# the italic sorts each OCR pattern may be
LIG_READ = {"ffi": ("ffi", "ſſi"), "ffl": ("ffl",), "ff": ("ff", "ſſ"), "fi": ("fi", "ſi"), "fl": ("fl", "ſl"),
            "ft": ("ſt",)}


def variants_of(core, TI, cap=24):
    """Readings of an OCR word for alignment. Ligature patterns are read as one
    sort, as Caslon's compositors set them: the italic's own ligature template
    where the sheet shows it, else a wildcard labelled LIG:<ocr> for
    relabel_ligs.py. (Never split into letters: a split ligature would put
    joined f's into the plain f and i averages.) A lone f may be f or long s."""
    toks = []
    k = 0
    while k < len(core):
        L = next((L for L in LIGS if core.startswith(L, k)), None)
        if L:
            toks.append(L); k += len(L)
        else:
            toks.append(core[k]); k += 1
    opts = []
    for tk in toks:
        if tk in LIG_READ:
            known = [r for r in LIG_READ[tk] if r in TI]
            opts.append([(r,) for r in known] or [("LIG:" + tk,)])
        elif tk == "f" and "ſ" in TI:
            opts.append([("f",), ("ſ",)])
        else:
            opts.append([(tk,)])
    out = [()]
    for o in opts:
        out = [a + b for a in out for b in o][:cap]
    return out


def default_wild(xh_exp):
    """Widths for letters this size's italic has no template for (wildcards),
    from the Pica italic (which has them, from Bowyer's book) scaled by
    x-height. A fixed guess of half an x-height cut wide letters short (an
    italic w is about 1.4 x-heights), handing most of the letter to its
    neighbours."""
    ref = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work", "pica_italic_avg11")
    try:
        g = json.load(open(os.path.join(ref, "glyphs.json"), encoding="utf-8"))
    except OSError:
        return {}
    up, out = g["up"], {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(ref, f"avg_{gid}.png"), -1)
        if a is None:
            continue
        xs = np.where((a > 0.5 * 65535).any(0))[0]
        if len(xs):
            out[v["ch"]] = (xs[-1] - xs[0] + 1) / up * xh_exp / 44.0     # Pica x-height 44 px at 600 ppi
    return out


def main():
    page, xml, pidx, ppi, slant, iavg, ravg, xh_exp, out = sys.argv[1:10]
    wild_w = json.load(open(sys.argv[10], encoding="utf-8")) if len(sys.argv) > 10 else default_wild(float(sys.argv[8]))
    pidx, ppi, xh_exp = int(pidx), float(ppi), float(xh_exp)
    t = np.tan(np.radians(float(slant)))
    k = 600.0 / ppi
    im0 = cv2.imread(page, cv2.IMREAD_GRAYSCALE)
    im0 = cv2.resize(im0, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    H, W = im0.shape
    paper = float(np.percentile(im0, 80)); ink = float(np.percentile(im0, 1))
    im = cv2.warpAffine(im0, np.float32([[1, t, 0], [0, 1, 0]]), (W + int(t * H) + 2, H),
                        flags=cv2.INTER_CUBIC, borderValue=paper)
    os.makedirs(out, exist_ok=True)
    blur = cv2.GaussianBlur(im, (3, 3), 0)
    otsu, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    comps = np.array([s for s in stats[1:] if s[4] >= 12]) if n > 1 else np.zeros((0, 5))
    TI, TR = load_templates(iavg), load_templates(ravg)

    x = open(xml, encoding="utf-8").read()
    pg = re.split(r"<OBJECT ", x)[1:][pidx]
    lines = re.findall(r"<LINE>(.*?)</LINE>", pg, re.S)
    inst, st = [], dict(words=0, kept=0, roman=0, size=0, junk=0)
    for li, L in enumerate(lines):
        words = [(list(map(int, c.split(","))), html.unescape(w).strip())
                 for c, w in re.findall(r'<WORD coords="([\d,]+)"[^>]*>([^<]*)</WORD>', L)]
        last_italic = -9
        for wi, ((l, b, r, tp), text) in enumerate(words):
            if WF is not None:
                fixmap = WF.get(str(pidx), {})
                if text in fixmap:
                    text = fixmap[text]
                elif ONLYFIX:
                    continue
            # a later specimen book sets several cuts of one size on a page: harvest
            # only the block asked for (CASLON_YRANGE = top,bottom in OCR coords)
            if YR and not (YR[0] <= (tp + b) / 2 <= YR[1]):
                continue
            st["words"] += 1
            if text in ("?", "!") and last_italic == wi - 1:
                # a lone mark straight after an italic word: take the glyph made of
                # two stacked parts (stroke over dot) inside its (sheared) box
                L_, B_, R_, T_ = [v * k for v in (l, b, r, tp)]
                xl_, xr_ = L_ + t * T_, R_ + t * B_
                sel = comps[(comps[:, 0] + comps[:, 2] / 2 >= xl_ - 4) & (comps[:, 0] + comps[:, 2] / 2 <= xr_ + 4) &
                            (comps[:, 1] + comps[:, 3] / 2 >= T_ - 0.4 * (B_ - T_)) & (comps[:, 1] + comps[:, 3] / 2 <= B_ + 0.3 * (B_ - T_))]
                pairs = [(a_, b_) for a_ in sel for b_ in sel if a_[1] + a_[3] <= b_[1] + 2 and b_[3] < 0.45 * xh_exp
                         and abs((a_[0] + a_[2] / 2) - (b_[0] + b_[2] / 2)) < 0.4 * xh_exp and a_[3] > 0.6 * xh_exp]
                if len(pairs) == 1:
                    a_, b_ = pairs[0]
                    x0, y0 = int(min(a_[0], b_[0])), int(a_[1]); x1, y1 = int(max(a_[0] + a_[2], b_[0] + b_[2])), int(b_[1] + b_[3])
                    m = np.zeros(im.shape, bool)
                    for c_ in (a_, b_):
                        m[c_[1]:c_[1] + c_[3], c_[0]:c_[0] + c_[2]] |= bw[c_[1]:c_[1] + c_[3], c_[0]:c_[0] + c_[2]] > 0
                    cx0, cy0 = max(0, x0 - 6), max(0, y0 - 6)
                    crop = im[cy0:y1 + 6, cx0:x1 + 6]
                    mm = cv2.dilate(m[cy0:y1 + 6, cx0:x1 + 6].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
                    fn = f"{len(inst):05d}.png"
                    cv2.imwrite(os.path.join(out, fn), np.where(mm, crop, np.uint8(paper)).astype(np.uint8))
                    inst.append(dict(file=fn, ch=text, line=li, word=wi, pos=0, nword=1, x0=x0, x1=x1, y0=y0, y1=y1,
                                     crop=[cx0, cy0], baseline=float(y1), slope=0.0, align=1.0, wild=True))
                continue
            core = text.strip(",.;:?!'()-")
            if not core.isalpha() or len(core) < 2:
                st["junk"] += 1; continue
            l, b, r, tp = [v * k for v in (l, b, r, tp)]
            xl, xr = l + t * tp, r + t * b                    # sheared box extent
            cs = comps[(comps[:, 0] + comps[:, 2] / 2 >= xl - 4) & (comps[:, 0] + comps[:, 2] / 2 <= xr + 4) &
                       (comps[:, 1] + comps[:, 3] / 2 >= tp - 0.3 * (b - tp)) & (comps[:, 1] + comps[:, 3] / 2 <= b + 0.3 * (b - tp))]
            if len(cs) == 0:
                continue
            wx0, wx1 = int(cs[:, 0].min()), int((cs[:, 0] + cs[:, 2]).max())
            mid = cs[(cs[:, 3] > 0.7 * xh_exp) & (cs[:, 3] < 1.3 * xh_exp)]
            if len(mid) < 1:
                st["size"] += 1; continue
            base = float(np.median(mid[:, 1] + mid[:, 3]))
            best = None
            for v in variants_of(core, TI):
                res, score = align_word(dens, bw, im, paper, base, wx0, wx1, list(v), TI, xh_exp, wild_w)
                if score is not None and (best is None or score > best[1]):
                    best = (res, score, list(v))
            if best is None:
                continue
            res, score, v = best
            if score < 0.6:
                st["roman"] += 1; continue
            # italic must beat roman on the same known letters
            known = [c for c in v if c in TI and c in TR]
            if known:
                xs = np.arange(wx0 - 8, wx1 + 8)
                rS = score_maps(dens, v, TR, base, xs)
                rbest = np.mean([rS[i].max() for i, c in enumerate(v) if c in TR])
                if rbest >= score:
                    st["roman"] += 1; continue
            # size gate on x-height letters
            hs = [o["box"][3] - o["box"][1] for o in res if o and o["name"] in XH and o["name"] in TI]
            if hs and abs(np.median(hs) / xh_exp - 1) > 0.08:
                st["size"] += 1; continue
            st["kept"] += 1
            last_italic = wi
            for pos, o in enumerate(res):
                if o is None:
                    continue
                fn = f"{len(inst):05d}.png"
                cv2.imwrite(os.path.join(out, fn), o["img"])
                x0, y0, x1, y1 = o["box"]
                inst.append(dict(file=fn, ch=o["name"], line=li, word=wi, pos=pos, nword=len(v),
                                 x0=x0, x1=x1, y0=y0, y1=y1, crop=list(o["crop_xy"]), baseline=base, slope=0.0,
                                 align=o["score"], wild=o["name"] not in TI))
    json.dump(dict(instances=inst, otsu=float(otsu), source=os.path.basename(page)),
              open(os.path.join(out, "instances.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(os.path.basename(page), st, "instances", len(inst), "wild", sum(i["wild"] for i in inst))


if __name__ == "__main__":
    main()
