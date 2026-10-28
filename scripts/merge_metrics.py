"""Merge spacing: 1734 measurements win; supplementary-source glyphs are mapped
onto the 1734 standard by a linear fit over shared lowercase letters; figures
sit on an en (half the body), as founders cast them.
Usage: python -I merge_metrics.py <avg_dir> <pitch_px> [primary_glob]
primary_glob: the specimen's instance dirs (default work/pica_roman_p*)"""
import sys, os, json
import numpy as np
avg, pitch = sys.argv[1], float(sys.argv[2])
PRIMARY = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(avg), "pica_roman_p*")
NTEXT = int(sys.argv[4]) if len(sys.argv) > 4 else 7   # running-text lines in the specimen block
A = json.load(open(os.path.join(avg, "metrics_1734.json"), encoding="utf-8"))
B = json.load(open(os.path.join(avg, "metrics_book.json"), encoding="utf-8"))
import glob
on_sheet = set()
for f in [f for pat in PRIMARY.split(",") for f in glob.glob(os.path.join(pat, "instances.json"))]:
    on_sheet |= {i["ch"] for i in json.load(open(f, encoding="utf-8"))["instances"]}
a_ = {c: m for c, m in A["glyphs"].items() if c in on_sheet}
b_ = B["glyphs"]
common = [c for c in a_ if c in b_ and a_[c]["pairs"] >= 10 and b_[c]["pairs"] >= 30 and c.islower()]
k, o = np.polyfit([b_[c]["adv"] for c in common], [a_[c]["adv"] for c in common], 1)
res = np.array([a_[c]["adv"] - (k * b_[c]["adv"] + o) for c in common])
out = dict(a_)
for c, m in b_.items():
    if c in out:
        continue
    adv = pitch / 2 if c.isdigit() else k * m["adv"] + o
    f = adv / m["adv"]
    lsb = m["lsb"] * f
    out[c] = dict(adv=float(adv), lsb=float(lsb), rsb=float(adv - lsb - m["inkw"]), inkw=m["inkw"],
                  pairs=m["pairs"], source="book (mapped)" if not c.isdigit() else "book lsb, en set-width")
for c in a_:
    out[c] = dict(out[c], source="1734 specimen")
# Capitals. In running text a capital starts its word, so only its RIGHT side
# ever abuts a letter; the left side is never observed (in either source).
#  right side: 1734 text where the capital is followed by a letter there,
#              otherwise the book's running text, scaled to 1734 sidebearings
#  left side : symmetric letters mirror their measured right side; straight-
#              stemmed lefts take H's, round lefts take O's
#  check     : resulting widths vs the widths measured in the 1734 alphabet line
right_in_1734 = set()
for f in [f for pat in PRIMARY.split(",") for f in glob.glob(os.path.join(pat, "instances.json"))]:
    I = json.load(open(f, encoding="utf-8"))["instances"]
    key = {(i["line"], i["word"], i["pos"]) for i in I}
    right_in_1734 |= {i["ch"] for i in I if i["line"] < NTEXT and (i["line"], i["word"], i["pos"] + 1) in key}
sbA = np.mean([a_[c]["lsb"] + a_[c]["rsb"] for c in common]); sbB = np.mean([b_[c]["lsb"] + b_[c]["rsb"] for c in common])
sb_scale = sbA / sbB
caps = [c for c in out if len(c) == 1 and c.isupper()]
rsb = {}
for c in caps:
    if c in right_in_1734:
        rsb[c] = (a_[c]["rsb"], "1734 text")
    elif c in b_ and b_[c]["pairs"] >= 15:
        rsb[c] = (b_[c]["rsb"] * sb_scale, "book text, scaled")
SYM = set("AHIMNOTUVWXYSZ")  # not J: its tail hooks left below the line
STRAIGHT_L, ROUND_L = set("BDEFKLPR"), set("CGOQ")
check = []
for c in caps:
    if c not in rsb or c == "Q":
        continue
    r, rsrc = rsb[c]
    if c in SYM:
        l, lsrc = r, "mirrors right"
    elif c in STRAIGHT_L and "H" in rsb:
        l, lsrc = rsb["H"][0], "= H"
    elif c in ROUND_L and "O" in rsb:
        l, lsrc = rsb["O"][0], "= O"
    else:
        continue
    l, r = max(l, 0.0), r
    adv = l + out[c]["inkw"] + r
    src = f"right: {rsrc}; left: {lsrc}"
    if c in a_:
        check.append((c, adv, a_[c]["adv"]))
        # two independent width estimates (alphabet line vs rebuilt): average
        # them, sharing the difference equally between the sidebearings
        half = (a_[c]["adv"] - adv) / 4
        l, r, adv = l + half, r + half, (adv + a_[c]["adv"]) / 2
        src += "; width = mean with 1734 alphabet line"
    out[c] = dict(out[c], adv=float(adv), lsb=float(l), rsb=float(r), source=src)
if check:
    d = np.array([x[1] - x[2] for x in check])
    print(f"capital widths vs 1734 alphabet line: mean diff {d.mean():+.2f} px, rms {np.sqrt((d**2).mean()):.2f} px (n={len(d)})")
    for c, a, b in check:
        print(f"  {c}: rebuilt {a:6.1f}  alphabet-line {b:6.1f}")

# thinly measured ligatures: keep the ligature's own traced ink, give it the
# first component's left and the last component's right sidebearing
for c in list(out):
    if len(c) > 1 and c not in a_ and out[c]["pairs"] < 20 and all(x in out for x in c):
        lsb, rsb = out[c[0]]["lsb"], max(out[c[-1]]["rsb"], 0.0)
        adv = lsb + out[c]["inkw"] + rsb
        out[c] = dict(out[c], adv=float(adv), lsb=float(lsb), rsb=float(rsb),
                      source="component sidebearings around own ink (few measurements)")
json.dump(dict(A, glyphs=out, mapping=dict(k=float(k), o=float(o), rms_px=float(np.sqrt((res ** 2).mean())), n=len(common))),
          open(os.path.join(avg, "metrics.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"merged: {len(a_)} from 1734, {len(out) - len(a_)} mapped from book; map rms {np.sqrt((res**2).mean()):.2f} px")
