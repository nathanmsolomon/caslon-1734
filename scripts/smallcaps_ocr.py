"""Harvest roman SMALL CAPITALS from a book page via its OCR layer.

Usage: python -I smallcaps_ocr.py <page.jpg> <djvu.xml> <page_index> <ppi> <roman_avg> <xheight_px600> <out_dir>

OCR spells small capitals as capitals. A glyph in an all-capital word is taken
as a small capital when its height is near the x-height (0.8-1.25x) and it
matches its own roman capital scaled down to that height; a glyph at full
capital height in the same word is labelled as the capital. Labels: 'A.sc'.
A word needs at least one small capital from DISTINCT (its lowercase differs).
"""
import sys, os, re, json, html
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from segment import repair  # noqa: E402
from align_core import load_templates  # noqa: E402

DESC = set("QJ")   # may reach below the line
# small capitals whose lowercase has a different shape; C O S V W X Z look the
# same in both, so a capitalised lowercase word ("How", "Law") would pass as
# small caps on those letters alone
DISTINCT = set("ABDEFGHIJKLMNPQRTUY")


def main():
    page, xml, pidx, ppi, ravg, xh, out = sys.argv[1:8]
    pidx, ppi, xh = int(pidx), float(ppi), float(xh)
    k = 600.0 / ppi
    im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)
    im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    os.makedirs(out, exist_ok=True)
    paper, ink = float(np.percentile(im, 80)), float(np.percentile(im, 1))
    dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
    otsu, bw = cv2.threshold(cv2.GaussianBlur(im, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    comps = [dict(x=s[0], y=s[1], w=s[2], h=s[3], a=s[4], i=j) for j, s in enumerate(stats) if j and s[4] >= 12]
    T = load_templates(ravg)
    capH = {c: T[c]["img"].shape[0] for c in T if len(c) == 1 and c.isupper()}

    x = open(xml, encoding="utf-8").read()
    pg = re.split(r"<OBJECT ", x)[1:][pidx]
    lines = re.findall(r"<LINE>(.*?)</LINE>", pg, re.S)
    inst, st = [], dict(words=0, kept=0, count=0, shape=0, size=0)
    for li, L in enumerate(lines):
        for wi, (c, w) in enumerate(re.findall(r'<WORD coords="([\d,]+)"[^>]*>([^<]*)</WORD>', L)):
            full = html.unescape(w).strip()
            raw = full.rstrip(".,;:")
            if len(raw) < 2 or not raw.isalpha():
                continue
            # OCR spells small caps as lowercase (x-height) or capitals; trailing
            # punctuation is its own glyph, so keep it as a token
            text = raw.upper() + full[len(raw):]
            st["words"] += 1
            l, b, r, t = [int(int(v) * k) for v in c.split(",")]
            hgt = b - t
            cs = sorted([q for q in comps if l - 4 <= q["x"] + q["w"] / 2 <= r + 4 and t - 0.3 * hgt <= q["y"] + q["h"] / 2 <= b + 0.3 * hgt],
                        key=lambda q: q["x"])
            glyphs = []
            for q in cs:
                if glyphs:
                    g = glyphs[-1]
                    if min(g["x1"], q["x"] + q["w"]) - max(g["x0"], q["x"]) > 0.5 * min(q["w"], g["x1"] - g["x0"]):
                        g["parts"].append(q); g["x0"] = min(g["x0"], q["x"]); g["x1"] = max(g["x1"], q["x"] + q["w"]); continue
                glyphs.append(dict(parts=[q], x0=q["x"], x1=q["x"] + q["w"]))
            for g in glyphs:
                g["y0"] = min(p["y"] for p in g["parts"]); g["y1"] = max(p["y"] + p["h"] for p in g["parts"])
            if len(glyphs) != len(text):
                glyphs = repair(glyphs, len(text), bw, lab) if glyphs else []
                if len(glyphs) != len(text):
                    st["count"] += 1; continue
            hs = [g["y1"] - g["y0"] for g, ch in zip(glyphs, text) if ch not in DESC and ch.isalpha()]
            if not hs:
                continue
            base = float(np.median([g["y1"] for g, ch in zip(glyphs, text) if ch not in DESC and ch.isalpha()]))
            labels, ok = [], True
            capscore, lowscore = [], []
            for g, ch in zip(glyphs, text):
                if not ch.isalpha():
                    labels.append(ch); continue
                h = g["y1"] - g["y0"]
                if ch in DESC:
                    h = base - g["y0"]
                if 0.8 * xh <= h <= 1.25 * xh:
                    lbl = ch + ".sc"
                elif h >= 1.35 * xh:
                    lbl = ch
                else:
                    ok = False; break
                if lbl.endswith(".sc") and ch in T:
                    # small cap vs lowercase: which template explains this glyph better?
                    y0, x0 = max(0, g["y0"] - 10), max(0, g["x0"] - 10)
                    win = dens[y0:g["y1"] + 10, x0:g["x1"] + 10]
                    def ncc(tpl, scale):
                        tt = cv2.resize(tpl, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                        if win.shape[0] < tt.shape[0] or win.shape[1] < tt.shape[1]:
                            return -1.0
                        return float(cv2.matchTemplate(win, tt, cv2.TM_CCOEFF_NORMED).max())
                    lw = ch.lower()
                    if lw in T:
                        # compare only where both forms have a template (a missing
                        # lowercase scored -1 and passed lowercase words as small caps)
                        tpl = T[ch]["img"]
                        capscore.append(ncc(tpl, (g["y1"] - g["y0"] + 4) / tpl.shape[0]))
                        lowscore.append(ncc(T[lw]["img"], 1.0))
                labels.append(lbl)
            # a small-capital word: an optional full capital, then only small capitals
            # (the full capital is required: it rules out old-style figures, which
            # look like small-capital I and O, and lowercase words that happen to score)
            letters = [lb for lb in labels if lb[0].isalpha()]
            if ok and (letters[0].endswith(".sc") or sum(lb.endswith(".sc") for lb in letters) < 2
                       or not all(lb.endswith(".sc") for lb in letters[1:])):
                ok = False
            if not ok or not capscore:
                st["shape"] += 1; continue
            # at least one small capital that a lowercase letter could not imitate
            if not any(lb.endswith(".sc") and lb[0] in DISTINCT for lb in letters):
                st["shape"] += 1; continue
            # a word is small capitals when the scaled capitals explain it clearly
            # better than the lowercase does
            if np.mean(capscore) < 0.65 or np.mean(capscore) - np.mean(lowscore) < 0.08:
                st["shape"] += 1; continue
            if not any(lb.endswith(".sc") for lb in labels):
                continue
            st["kept"] += 1
            for pos, (g, lbl) in enumerate(zip(glyphs, labels)):
                pad = 6
                gx0, gy0 = max(0, g["x0"] - pad), max(0, g["y0"] - pad)
                crop = im[gy0:g["y1"] + pad, gx0:g["x1"] + pad]
                m = np.zeros_like(crop, bool)
                for p in g["parts"]:
                    mm = lab[gy0:g["y1"] + pad, gx0:g["x1"] + pad] == p["i"]
                    if "clip" in p:
                        xs = np.arange(gx0, gx0 + mm.shape[1]); mm &= ((xs >= p["clip"][0]) & (xs < p["clip"][1]))[None, :]
                    m |= mm
                m = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                fn = f"{len(inst):05d}.png"
                cv2.imwrite(os.path.join(out, fn), np.where(m, crop, np.uint8(paper)).astype(np.uint8))
                inst.append(dict(file=fn, ch=lbl, line=li, word=wi, pos=pos, nword=len(labels),
                                 x0=int(g["x0"]), x1=int(g["x1"]), y0=int(g["y0"]), y1=int(g["y1"]),
                                 crop=[int(gx0), int(gy0)], baseline=base, slope=0.0))
    json.dump(dict(instances=inst, otsu=float(otsu), source=os.path.basename(page)),
              open(os.path.join(out, "instances.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(os.path.basename(page), st, "small caps", sum(i["ch"].endswith(".sc") for i in inst))


if __name__ == "__main__":
    main()
