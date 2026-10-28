"""Which faces in a later Caslon specimen book are the same cuts as our 1734 faces?

Usage: python -I survey_later.py <book_dir> <ppi> <first_page> <last_page>

<book_dir> holds nNN.jpg page images and djvu.xml (Internet Archive OCR). Each
page is split into blocks at its headings (lines naming a size); each roman
block is screened against every 1734 roman average (normalised cross-
correlation of the lowercase templates, small scale sweep around the scan's
ppi). A block that is the same cut as a 1734 face matches it at scale ~1.00
with a clear margin over the other sizes. Prints one line per block.
"""
import sys, os, re, html
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screen import templates, score  # noqa: E402

FACES = [("Double Pica", "work/dp_roman_avgF"), ("Great Primer", "work/gp_roman_avgF"),
         ("English", "work/en_roman_avgF"), ("Pica", "work/pica_roman_avg4"),
         ("Small Pica 1", "work/sp1_roman_avgF"), ("Small Pica 2", "work/sp2_roman_avgF"),
         ("Long Primer 1", "work/lp1_roman_avgF"), ("Long Primer 2", "work/lp2_roman_avgF"),
         ("Brevier", "work/br_roman_avgF")]
HEAD = re.compile(r"(ROMAN|Roman|Italic|Italick|Canon|Cannon|Primer|Pica|Brevier|Nonpareil|Pearl|Minion|Burgeois|Bourgeois|English|Englifh|Paragon)")


def page_blocks(xml_page):
    lines = []
    for L in re.findall(r"<LINE>(.*?)</LINE>", xml_page, re.S):
        ws = re.findall(r'<WORD coords="([\d,]+)"[^>]*>([^<]*)</WORD>', L)
        if not ws:
            continue
        txt = " ".join(html.unescape(t) for _, t in ws)
        cs = [list(map(int, c.split(","))) for c, _ in ws]
        lines.append((min(c[3] for c in cs), max(c[1] for c in cs), txt))   # top, bottom, text
    heads = [(t, b, x) for t, b, x in lines if HEAD.search(x) and len(x) < 60]
    blocks = []
    for k, (t, b, x) in enumerate(heads):
        nxt = heads[k + 1][0] if k + 1 < len(heads) else max(l[1] for l in lines) + 20
        blocks.append((x, b + 8, nxt - 8))
    return blocks


def density(img):
    im = img.astype(np.float32)
    paper, ink = np.percentile(im, 80), np.percentile(im, 1)
    return np.clip((paper - im) / (paper - ink + 1e-6), 0, 1)


def main():
    bd, ppi, a, b = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    T = [(nm,) + templates(d) for nm, d in FACES if os.path.exists(f"{d}/glyphs.json")]
    pages = open(f"{bd}/djvu.xml", encoding="utf-8", errors="replace").read().split("<OBJECT")[1:]
    for n in range(a, b + 1):
        im = cv2.imread(f"{bd}/n{n}.jpg", cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        for head, y0, y1 in page_blocks(pages[n]):
            if re.search(r"Itali", head) or y1 - y0 < 60:
                continue
            dens = density(im[max(0, y0):y1, :])
            res = []
            for nm, tpls, up in T:
                best = max((score(dens, tpls, up, ppi / 600 * s), s) for s in np.arange(0.94, 1.07, 0.03))
                res.append((best[0], nm, round(best[1], 2)))
            res.sort(reverse=True)
            print(f"n{n:3d} {head[:44]:44s} | " + " | ".join(f"{nm} x{s} {v:.3f}" for v, nm, s in res[:3]), flush=True)


if __name__ == "__main__":
    main()
