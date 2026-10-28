"""Sort the harvesters' unresolved ligatures (LIG:xx) into real ligature names.

Usage: python -I relabel_ligs.py <font.otf> <harvest_dir> [<harvest_dir> ...]

OCR writes long s as f, so a ligature sort comes back as LIG:fh, LIG:fl, ... .
  certain by spelling: fh -> ſh, fk -> ſk, fb -> ſb, ft -> ſt (Caslon cut no ft),
                       ct -> ct, ffl -> ffl
  ambiguous:           ff (ff / ſſ), fi (fi / ſi), fl (fl / ſl), ffi (ffi / ſſi)
Ambiguous ones are decided by spelling (English word list, or the Latin
Hunspell dictionary for Latin books and the specimens' Cicero); an fl/ſl that
looks more like ſt is dropped. (Older note:) Ambiguous ones are compared with the two letter pairs drawn in this size's own
font (same scale, shift-tolerant correlation); the closer wins, and impressions
too close to call (difference < 0.03) are left unlabelled. The OCR reading is
kept as "ocr_lig". Instances are relabelled in place.
"""
import sys, os, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setline import render  # noqa: E402

CERTAIN = {"fh": "ſh", "fk": "ſk", "fb": "ſb", "ft": "ſt", "ct": "ct", "ffl": "ffl"}
AMBIG = {"ff": ("ff", "ſſ"), "fi": ("fi", "ſi"), "fl": ("fl", "ſl"), "ffi": ("ffi", "ſſi")}


def ink(img_dark_on_light):
    im = img_dark_on_light
    paper, inkv = np.percentile(im, 85), np.percentile(im, 2)
    d = np.clip((paper - im.astype(np.float32)) / (paper - inkv + 1e-6), 0, 1).astype(np.float32)
    ys, xs = np.where(d > 0.4)
    if len(ys) < 10:
        return None
    c = d[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return cv2.resize(c, (max(4, int(round(c.shape[1] * 96 / c.shape[0]))), 96), interpolation=cv2.INTER_AREA)


def pair_image(font, seq):
    # letters drawn one after another (never the font's own ligature glyph)
    parts = [render(font, 300, [ch], margin=0.02) for ch in seq]
    h = max(p.shape[0] for p in parts)
    row = np.hstack([np.pad(p, ((0, h - p.shape[0]), (0, 0)), constant_values=255) for p in parts])
    return ink(row)


def ncc(a, b):
    w = max(a.shape[1], b.shape[1]); m = int(0.15 * w) + 4
    big = np.pad(b, ((10, 10), (m + (w - b.shape[1]) // 2, m + w - b.shape[1] - (w - b.shape[1]) // 2)))
    if a.shape[0] > big.shape[0] or a.shape[1] > big.shape[1]:
        return 0.0
    return float(cv2.matchTemplate(big, a, cv2.TM_CCOEFF_NORMED).max())


def main():
    font, dirs = sys.argv[1], sys.argv[2:]
    words_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "source", "wordlists", "words_alpha.txt")
    WORDS = set(w.strip() for w in open(words_path, encoding="utf-8"))
    # Latin books and the specimens' Cicero: a Hunspell Latin dictionary (handles
    # inflections, -que, æ, i/j), source/wordlists/la (dictionary-la, from
    # extensions.openoffice.org); read with spylls (pip install spylls; an extra
    # library folder can be given in CASLON_PYLIBS)
    try:
        if os.environ.get("CASLON_PYLIBS"):
            sys.path.insert(0, os.environ["CASLON_PYLIBS"])
        from spylls.hunspell import Dictionary
        LA = Dictionary.from_files(os.path.join(os.path.dirname(words_path), "la", "index"))
    except Exception as e:
        print("no Latin dictionary:", e); LA = None
    def is_word(w):
        return w in WORDS or (LA is not None and len(w) > 1 and LA.lookup(w))
    # OCR also reads the ſt sort as "fl": an fl/ſl that looks more like ſt is dropped
    tpl = {q: pair_image(font, q) for q in ("fl", "ſl", "ſt")}
    counts = {}
    for d in dirs:
        p = os.path.join(d, "instances.json")
        if not os.path.exists(p):
            continue
        meta = json.load(open(p, encoding="utf-8"))
        # the word each instance came from, in OCR spelling (long s written f)
        wordtxt = {}
        for i in meta["instances"]:
            ocr0 = i.get("ocr_lig") or (i["ch"][4:] if i["ch"].startswith("LIG:") else None)
            wordtxt.setdefault((i.get("line"), i.get("word")), []).append((i.get("pos", 0), "{" + ocr0 + "}" if ocr0 else i["ch"].replace("ſ", "s")))
        changed = False
        for i in meta["instances"]:
            ocr = i.get("ocr_lig") or (i["ch"][4:] if i["ch"].startswith("LIG:") else None)
            if not ocr:
                continue
            new = CERTAIN.get(ocr)
            if ocr in AMBIG:
                # decide by spelling: which reading of the ligature makes a word?
                parts = [t for _, t in sorted(wordtxt[(i.get("line"), i.get("word"))])]
                tag = "{" + ocr + "}"
                f_seq, s_seq = AMBIG[ocr]
                def spell(seq):
                    w = "".join(seq.replace("ſ", "s") if t == tag else t.strip("{}") for t in parts)
                    return "".join(c for c in w.lower() if c.isalpha())
                fw, sw = spell(f_seq), spell(s_seq)
                # English decides when it can; Latin only when neither reading is
                # an English word (its dictionary accepts some odd forms)
                f_ok, s_ok = fw in WORDS, sw in WORDS
                if not f_ok and not s_ok and LA is not None:
                    f_ok, s_ok = is_word(fw), is_word(sw)
                new = f_seq if f_ok and not s_ok else s_seq if s_ok and not f_ok else None
                if new in ("fl", "ſl"):
                    im = cv2.imread(os.path.join(d, i["file"]), cv2.IMREAD_GRAYSCALE)
                    a = ink(im) if im is not None else None
                    if a is None or ncc(a, tpl["ſt"]) > ncc(a, tpl[new]):
                        new = None
            i["ocr_lig"] = ocr
            i["ch"] = new if new else "LIG:" + ocr
            counts[i["ch"]] = counts.get(i["ch"], 0) + 1
            changed = True
        if changed:
            json.dump(meta, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print(os.path.basename(font), {k: v for k, v in sorted(counts.items(), key=lambda t: -t[1])})


if __name__ == "__main__":
    main()
