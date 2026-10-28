"""Which large Caslon sizes does a title page (or heading page) use?

Usage: python -I title_probe.py <ppi> <djvu.xml> <page.jpg>:<page_index> [...]

Title pages are set mostly in capitals of the display sizes, which the
lowercase page screen (screen_all.py) cannot see. Each OCR word is split into
glyphs (connected components, merged where they overlap in x); a glyph whose
OCR letter has a template in a size, and whose ink height is within 6% of that
template's, is compared with it (shift-tolerant NCC, scale 0.97-1.03). Per page
and size it prints the number of glyphs tested and their median NCC; a size
counts as present when 6 or more glyphs score a median of 0.85 or higher.
Roman sizes only (the italic needs its own shear).

With CASLON_HARVEST=<size name>:<out_dir>, every page where that size counts as
present also has its glyphs for that size scoring 0.85 or more written to
<out_dir>/n<page_index> in the harvesters' instances.json format.
"""
import sys, os, re, html, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from align_core import load_templates  # noqa: E402

SIZES = [("Great Primer", "work/gp_roman_avgF"), ("English", "work/en_roman_avgF"),
         ("Double Pica", "work/dp_roman_avgF"), ("2L Great Primer", "work/tlgp_roman_avgF"),
         ("2L English", "work/tle_roman_avgF"), ("French Cannon", "work/fc_roman_avgF")] + \
        [(f"Titling {i}", f"work/titling{i}_avgF") for i in range(1, 8)]


def inkh(img):
    ys = np.where((img > 0.3).any(1))[0]
    return ys[-1] - ys[0] + 1 if len(ys) else 0


def ncc(glyph, tpl):
    best = -1.0
    for s in (0.97, 1.0, 1.03):
        t = cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        pad = 8
        w = np.pad(glyph, ((pad + max(0, t.shape[0] - glyph.shape[0]),) * 2, (pad + max(0, t.shape[1] - glyph.shape[1]),) * 2))
        best = max(best, float(cv2.matchTemplate(w, t, cv2.TM_CCOEFF_NORMED).max()))
    return best


DESC = set("QJgjpqy")


def save(out, page_im, paper, kept, base_of):
    otsu = float(cv2.threshold(cv2.GaussianBlur(page_im, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[0])
    os.makedirs(out, exist_ok=True)
    inst = []
    for (x0, y0, x1, y1, ch, li, wi, pos, nw, m) in kept:
        pad = 6
        cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
        crop = page_im[cy0:y1 + pad, cx0:x1 + pad]
        mm = cv2.dilate(m[cy0:y1 + pad, cx0:x1 + pad].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        fn = f"{len(inst):05d}.png"
        cv2.imwrite(os.path.join(out, fn), np.where(mm, crop, np.uint8(paper)).astype(np.uint8))
        inst.append(dict(file=fn, ch=ch, line=li, word=wi, pos=pos, nword=nw, x0=int(x0), x1=int(x1), y0=int(y0), y1=int(y1),
                         crop=[int(cx0), int(cy0)], baseline=base_of[(li, wi)], slope=0.0))
    json.dump(dict(instances=inst, otsu=otsu, source="title_probe"), open(os.path.join(out, "instances.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(inst)


def main():
    ppi, xml = float(sys.argv[1]), sys.argv[2]
    hv = os.environ.get("CASLON_HARVEST", "").split(":", 1) if os.environ.get("CASLON_HARVEST") else None
    k = 600.0 / ppi
    T = {nm: load_templates(d) for nm, d in SIZES if os.path.exists(f"{d}/glyphs.json")}
    H = {nm: {c: inkh(v["img"]) for c, v in t.items() if len(c) == 1 and c.isalpha()} for nm, t in T.items()}
    objs = re.split(r"<OBJECT ", open(xml, encoding="utf-8").read())[1:]
    for spec in sys.argv[3:]:
        page, pidx = spec.rsplit(":", 1)
        im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)
        if im is None:
            print(os.path.basename(page), pidx, "unreadable", flush=True); continue
        im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
        paper, ink = float(np.percentile(im, 80)), float(np.percentile(im, 1))
        dens = np.clip((paper - im.astype(np.float32)) / (paper - ink), 0, 1).astype(np.float32)
        bw = (dens > 0.4).astype(np.uint8)
        res = {nm: [] for nm in T}
        kept, base_of = [], {}
        for wi, (c, w) in enumerate(re.findall(r'<WORD coords="([\d,]+)"[^>]*>([^<]*)</WORD>', objs[int(pidx)])):
            text = html.unescape(w).strip().strip(".,;:'()-")
            if len(text) < 2 or not text.isalpha():
                continue
            l, b, r, t = [int(int(v) * k) for v in c.split(",")]
            hh = b - t
            y0, y1 = max(0, t - hh // 3), min(im.shape[0], b + hh // 3)
            x0, x1 = max(0, l - 6), min(im.shape[1], r + 6)
            if y1 - y0 < 4 or x1 - x0 < 4:
                continue
            n, lab, st, _ = cv2.connectedComponentsWithStats(np.ascontiguousarray(bw[y0:y1, x0:x1]), 8)
            comps = sorted([s for s in st[1:] if s[4] >= 30 and s[3] > 0.3 * hh], key=lambda s: s[0])
            gl = []
            for s in comps:
                if gl and min(gl[-1][2], s[0] + s[2]) - max(gl[-1][0], s[0]) > 0.4 * min(s[2], gl[-1][2] - gl[-1][0]):
                    g = gl[-1]; gl[-1] = [min(g[0], s[0]), min(g[1], s[1]), max(g[2], s[0] + s[2]), max(g[3], s[1] + s[3])]
                else:
                    gl.append([s[0], s[1], s[0] + s[2], s[1] + s[3]])
            if len(gl) != len(text):
                continue
            bots = [y0 + b1 for (a0, b0, a1, b1), ch in zip(gl, text) if ch not in DESC]
            base_of[(0, wi)] = float(np.median(bots)) if bots else float(y0 + max(g_[3] for g_ in gl))
            for pos, ((a0, b0, a1, b1), ch) in enumerate(zip(gl, text)):
                g = dens[y0 + b0:y0 + b1, x0 + a0:x0 + a1]
                h = b1 - b0
                for nm in T:
                    th = H[nm].get(ch)
                    if not th or abs(h / th - 1) > 0.06:
                        continue
                    v = ncc(g, T[nm][ch]["img"])
                    res[nm].append(v)
                    if hv and nm == hv[0] and v >= 0.85:
                        m = np.zeros(bw.shape, bool)
                        m[y0 + b0:y0 + b1, x0 + a0:x0 + a1] = bw[y0 + b0:y0 + b1, x0 + a0:x0 + a1] > 0
                        kept.append((x0 + a0, y0 + b0, x0 + a1, y0 + b1, ch, 0, wi, pos, len(text), m))
        out = []
        for nm, v in res.items():
            if v:
                med = float(np.median(v))
                out.append((med, nm, len(v)))
        out.sort(reverse=True)
        hit = [f"{nm}" for med, nm, n_ in out if n_ >= 6 and med >= 0.85]
        saved = save(f"{hv[1]}/n{pidx}", im, paper, kept, base_of) if hv and hv[0] in hit and kept else 0
        print(os.path.basename(page), pidx, " | ".join(f"{nm} {n_}g {med:.3f}" for med, nm, n_ in out[:5]),
              "=> " + (", ".join(hit) if hit else "none") + (f" [saved {saved}]" if saved else ""), flush=True)


if __name__ == "__main__":
    main()
