"""Give a clean font and its Impression twin the same character coverage.

Usage: python -I sync_coverage.py <clean.otf> <impression.otf> [chars]

Book-sourced characters are checked separately in each version and can pass in
one and fail in the other; a character missing from either is unmapped from both,
so the two versions always set the same text. Exception: a glyph seen only one
to four times and checked by eye (impression_singles.json) is in the Impression
version only, by design.
"""
import sys, os, json, re
from fontTools.ttLib import TTFont

KEYS = {"Brevier": "br", "DoublePica": "dp", "English": "en", "GreatPrimer": "gp", "LongPrimerNo.1": "lp1",
        "LongPrimerNo.2": "lp2", "SmallPicaNo.1": "sp1", "SmallPicaNo.2": "sp2"}


def singles(path):
    m = re.match(r"Caslon1734(.+?)(?:Impression)?-(Roman|Italic)\.otf$", os.path.basename(path))
    sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "impression_singles.json")
    if not m or not os.path.exists(sp):
        return set()
    key = {"Pica": "pica_" + m.group(2).lower() + ("_avg4" if m.group(2) == "Roman" else "_avg11")}.get(m.group(1))
    key = key or f"{KEYS.get(m.group(1), '?')}_{m.group(2).lower()}_avgS"
    return set(json.load(open(sp, encoding="utf-8")).get(key, {}))

DEFAULT = "kwxyzKUVWXYZhj0123456789&!'?:;()"


def main():
    a, b = sys.argv[1], sys.argv[2]
    chars = sys.argv[3] if len(sys.argv) > 3 else DEFAULT
    fa, fb = TTFont(a), TTFont(b)
    ca, cb = fa.getBestCmap(), fb.getBestCmap()
    keep = singles(a)
    drop = [ch for ch in chars if (ord(ch) in ca) != (ord(ch) in cb) and not (ch in keep and ord(ch) in cb)]
    for f, p in ((fa, a), (fb, b)):
        changed = False
        for t in f["cmap"].tables:
            if t.isUnicode():
                for ch in drop:
                    if t.cmap.pop(ord(ch), None) is not None:
                        changed = True
        if changed:
            f.save(p)
    print(a.split("/")[-1], "+ Impression: unmapped from both:", "".join(drop) or "none")


if __name__ == "__main__":
    main()
