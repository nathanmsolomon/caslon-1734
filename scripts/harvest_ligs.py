"""Harvest ligature sorts found by the ligature-reading OCR model (ligocr, see
N:\\Claude Work\\Ligature OCR) from a book already confirmed as a Caslon cut.

Usage: python -I harvest_ligs.py <split.json> <alto_dir> <page_dir> <ppi> <out_root> <sort> <style>
                                 <locator_avg_dir> <locator_scale> [--slant 16.5] [--min-ncc 0.5]

split.json (N:\\SimTools\\_tmp\\caslon_trial\\split_style.py): each word holding the
sort, its page and its style (roman/italic, from the word's measured slant). For each
word of the wanted style:
  1. the page is resampled to 600 ppi (k = 600/ppi) and, for italic, sheared upright by
     the slant: the same frame as segment_ocr*.py, so these instances average with the
     book's existing ones (and share its size/weight calibration in average.py)
  2. the sort's rough position is Kraken's box for that character (ALTO <Glyph>)
  3. a locator template (the same sort from another Caslon size, scaled: the face
     being filled has no template, that is the gap) is matched (NCC on ink density)
     within 1.5 x-heights; matches below --min-ncc are dropped
  4. the crop keeps only ink under the (blurred) locator, so neighbours do not enter
Writes <out_root>/n<page>/{NNNNN.png, instances.json} in the book-instance format.
The locator is used only to find the sort; the averaged glyph is this book's ink.
"""
import sys, os, re, json, html, glob
import numpy as np, cv2

LIGCP = {"ct": "\ue000", "ffi": "\ufb03", "ffl": "\ufb04", "fi": "\ufb01", "ſt": "\ufb05", "ſi": "\ue001",
         "ſſ": "\ue002", "ſſi": "\ue003", "ſh": "\ue004", "ſl": "\ue005", "ſk": "\ue006", "ſb": "\ue007"}


def locator(avg, ch, scale):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    for gid, v in g["glyphs"].items():
        if v["ch"] == ch:
            a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1).astype(np.float32) / 65535
            a = cv2.resize(a, None, fx=scale / g["up"], fy=scale / g["up"], interpolation=cv2.INTER_AREA)
            ys, xs = np.where(a > 0.3)
            y0, y1, x0, x1 = ys.min() - 3, ys.max() + 4, xs.min() - 3, xs.max() + 4
            base = g["base_row"] * scale / g["up"] - y0
            return a[y0:y1, x0:x1], base
    raise SystemExit(f"no {ch} in {avg}")


def main():
    split, alto_dir, page_dir, ppi, out_root, sort, style, loc_avg, loc_scale = sys.argv[1:10]
    slant = float(sys.argv[sys.argv.index("--slant") + 1]) if "--slant" in sys.argv else 16.5
    min_ncc = float(sys.argv[sys.argv.index("--min-ncc") + 1]) if "--min-ncc" in sys.argv else 0.5
    k = 600.0 / float(ppi); t = np.tan(np.radians(slant)) if style == "italic" else 0.0
    T, tbase = locator(loc_avg, sort, float(loc_scale))
    th, tw = T.shape; xh = 44.0
    soft = cv2.GaussianBlur(T, (0, 0), 2.0)
    words = [w for w in json.load(open(split, encoding="utf-8")) if sort in w["sorts"] and w["style"] == style]
    bypage = {}
    for w in words:
        bypage.setdefault(w["page"], []).append(w)
    kept = tried = 0
    for page, ws in sorted(bypage.items()):
        n = page.split("_n")[-1]
        img0 = cv2.imread(os.path.join(page_dir, f"n{n}.jpg"), cv2.IMREAD_GRAYSCALE)
        x = open(os.path.join(alto_dir, page + "_v4.xml"), encoding="utf-8").read()
        glyphs = [(float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
                  for m in re.finditer(r'<Glyph[^>]*CONTENT="' + re.escape(html.escape(LIGCP[sort])) +
                                       r'"[^>]*HPOS="([\d.]+)" VPOS="([\d.]+)" WIDTH="([\d.]+)" HEIGHT="([\d.]+)"', x)]
        if not glyphs:
            glyphs = [(float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
                      for m in re.finditer(r'<Glyph[^>]*CONTENT="' + LIGCP[sort] +
                                           r'"[^>]*HPOS="([\d.]+)" VPOS="([\d.]+)" WIDTH="([\d.]+)" HEIGHT="([\d.]+)"', x)]
        im = cv2.resize(img0, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
        H, W = im.shape
        paper = float(np.percentile(im, 80)); ink = float(np.percentile(im, 1))
        if t:
            im = cv2.warpAffine(im, np.float32([[1, t, 0], [0, 1, 0]]), (W + int(t * H) + 2, H),
                                flags=cv2.INTER_CUBIC, borderValue=paper)
        dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
        otsu, _ = cv2.threshold(cv2.GaussianBlur(im, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        out = os.path.join(out_root, f"n{n}")
        os.makedirs(out, exist_ok=True)
        inst = []
        for w in ws:
            X, Y, Ww, Hh = w["box"]
            # the glyph of this sort that lies inside this word's box
            g = [gg for gg in glyphs if X - 5 <= gg[0] <= X + Ww + 5 and Y - 5 <= gg[1] <= Y + Hh + 5]
            if not g:
                continue
            gx, gy, gw, gh = g[0]
            cx, cy = (gx + gw / 2) * k, (gy + gh / 2) * k
            cx += t * cy
            x0, x1 = int(max(0, cx - 1.5 * xh - tw)), int(min(dens.shape[1], cx + 1.5 * xh + tw))
            y0, y1 = int(max(0, cy - 1.2 * xh - th)), int(min(dens.shape[0], cy + 1.2 * xh + th))
            reg = dens[y0:y1, x0:x1]
            tried += 1
            if reg.shape[0] <= th or reg.shape[1] <= tw:
                continue
            r = cv2.matchTemplate(reg, T, cv2.TM_CCOEFF_NORMED)
            _, mv, _, (bx, by) = cv2.minMaxLoc(r)
            if mv < min_ncc:
                continue
            ax, ay = x0 + bx, y0 + by
            crop = im[ay:ay + th, ax:ax + tw].copy()
            keep = soft > 0.05
            crop[~keep[:crop.shape[0], :crop.shape[1]]] = np.uint8(paper)
            ys, xs = np.where((dens[ay:ay + th, ax:ax + tw] > 0.5) & keep[:crop.shape[0], :crop.shape[1]])
            if len(ys) < 20:
                continue
            fn = f"{len(inst):05d}.png"
            cv2.imwrite(os.path.join(out, fn), crop)
            inst.append(dict(file=fn, ch=sort, line=int(round(cy / 100)), word=0, pos=0, nword=1,
                             x0=int(ax + xs.min()), x1=int(ax + xs.max() + 1), y0=int(ay + ys.min()), y1=int(ay + ys.max() + 1),
                             crop=[int(ax), int(ay)], baseline=float(ay + tbase), slope=0.0, align=float(mv),
                             wild=False, source="ligocr_v4"))
            kept += 1
        json.dump(dict(instances=inst, otsu=float(otsu), source=f"n{n}.jpg", harvest="harvest_ligs.py"),
                  open(os.path.join(out, "instances.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{sort} {style}: {kept} of {tried} kept (NCC >= {min_ncc})")


if __name__ == "__main__":
    main()
