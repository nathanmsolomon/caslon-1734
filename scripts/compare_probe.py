"""Which 1734 size does a probed book match? Proportions corrected for microfilm.

Usage: python -I compare_probe.py <book_avg> [<book_avg> ...]

Microfilm (and OCR harvesting) distorts letters unevenly: thin serifs drop out,
so n m h u measure narrower, round letters wider. The distortion is measured on
Eboracum (Caslon English, confirmed) against the sheet's English and divided out
of each book's ratios; the corrected ratios are then compared with every sheet
size (rms relative difference). The book's x-height is also shown in Pica terms.
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from proportions import measure  # noqa: E402

SHEET = {"English": "work/en_roman_avgF", "Pica": "work/pica_roman_avg3", "Small Pica 1": "work/sp1_roman_avgF",
         "Small Pica 2": "work/sp2_roman_avgF", "Long Primer 1": "work/lp1_roman_avgF",
         "Long Primer 2": "work/lp2_roman_avgF", "Brevier": "work/br_roman_avgF", "Great Primer": "work/gp_roman_avgF"}
KEYS = ["asc", "desc", "w_n", "w_m", "w_o", "w_e", "w_a", "w_c", "w_h", "w_s", "w_u"]

_, ref_book = measure("work/probe/ebo_avg")
_, ref_sheet = measure(SHEET["English"])
corr = {k: ref_sheet[k] / ref_book[k] for k in KEYS}
sheet = {nm: measure(d) for nm, d in SHEET.items()}

for b in sys.argv[1:]:
    xh, r = measure(b)
    rc = {k: r[k] * corr[k] for k in KEYS if k in r}
    res = []
    for nm, (sxh, s) in sheet.items():
        ks = [k for k in rc if k in s and np.isfinite(s[k])]
        res.append((float(np.sqrt(np.mean([(rc[k] / s[k] - 1) ** 2 for k in ks]))), nm, sxh))
    res.sort()
    print(f"{b.split('/')[-2][:45]:45s} xh {xh:5.1f} | " + " | ".join(f"{nm} {d:.3f} (xh {sxh:.1f})" for d, nm, sxh in res[:3]))
