"""Which Caslon 1734 size (if any) is this page set in?

Usage: python -I screen_all.py <ppi> <page.jpg> [<page.jpg> ...]

For each size the lowercase templates are slid over a central crop of the page
at a narrow scale sweep around the expected size (using each size's measured
body in px at 600 ppi), so a page is tested against every size at once. Reports
the best few (size, scale, NCC). A real match sits near scale 1.00 with NCC
above ~0.93; scans of unknown resolution show a consistent scale across sizes.
"""
import sys, os, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from screen import templates, score, page_density  # noqa: E402

SIZES = [("Pica R", "work/pica_roman_avg3"), ("English R", "work/en_roman_avgF"), ("English R", "work/english_avg7"),
         ("Great Primer R", "work/gp_roman_avgF"), ("Double Pica R", "work/dp_roman_avgF"),
         ("Small Pica 1 R", "work/sp1_roman_avgF"), ("Small Pica 2 R", "work/sp2_roman_avgF"),
         ("Long Primer 1 R", "work/lp1_roman_avgF"), ("Long Primer 2 R", "work/lp2_roman_avgF"),
         ("Brevier R", "work/br_roman_avgF")]


def main():
    ppi, pages = float(sys.argv[1]), sys.argv[2:]
    T = []
    seen = set()
    only = [x for x in os.environ.get("CASLON_SIZES", "").split(",") if x]
    down = float(os.environ.get("CASLON_DOWN", "1"))   # work at a lower resolution for speed
    for nm, d in SIZES:
        if only and not any(o in nm for o in only):
            continue
        if nm in seen or not os.path.exists(f"{d}/glyphs.json"):
            continue
        seen.add(nm); T.append((nm,) + templates(d))
    for p in pages:
        dens = page_density(p)
        h, w = dens.shape
        dens = dens[int(0.25 * h):int(0.6 * h), int(0.12 * w):int(0.88 * w)]   # body text area
        if down != 1:
            dens = cv2.resize(dens, None, fx=down, fy=down, interpolation=cv2.INTER_AREA)
        res = []
        for nm, tpls, up in T:
            best = max((score(dens, tpls, up, down * ppi / 600 * s), s) for s in np.arange(*map(float, os.environ.get("CASLON_SWEEP", "0.88,1.13,0.03").split(","))))
            res.append((best[0], nm, round(best[1], 2)))
        res.sort(reverse=True)
        print(p if os.environ.get("CASLON_FULLPATH") else os.path.basename(p), " | ".join(f"{n} x{s} {v:.3f}" for v, n, s in res[:4]), flush=True)


if __name__ == "__main__":
    main()
