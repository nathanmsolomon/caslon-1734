"""Harvest the 1785 Caslon specimen blocks that are the same cuts as our 1734 faces.

Usage: python -I harvest_1785.py

Blocks were identified by survey_later.py (README, "Survey, Oct 20 2026"). Each
block is harvested on its own (CASLON_YRANGE), with the OCR layer, into
work/k85_<size>_<style>/n<page><k>/ (named like book pages, so build.py treats
the letters as book letters). Small Pica No. 1 and Double Pica are left out:
the survey could not confirm them as the 1734 cuts.
"""
import os, re, sys, json, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from survey_later import page_blocks  # noqa: E402

BD = "source/specimens_later/1785_uc"
PPI = 500
# (our size key, style, page, heading regex)
BLOCKS = [
    ("gp", "roman", 26, r"GREAT\s+PRIMER\s+ROMAN"), ("gp", "italic", 26, r"Great\s+Primer\s+Itali"),
    ("en", "roman", 30, r"PICA\s+BODY,\s+ENGLISH"), ("en", "roman", 32, r"ENGLISH\s+ROMAN,\s+No"),
    ("en", "italic", 32, r"Engli.h\s+Itali"),
    ("pica", "roman", 34, r"ENGLISH\s+BODY,\s+PICA"), ("pica", "roman", 34, r"^PICA\s+ROMAN"),
    ("pica", "roman", 36, r"SMALL\s+PICA\s+BODY,\s+PICA"), ("pica", "italic", 34, r"Pica\s+Itali"),
    ("sp2", "roman", 38, r"PICA\s+BODY,\s+SMALL\s+PICA"), ("sp2", "roman", 40, r"^SMALL\s+PICA\s+ROMAN"),
    ("sp2", "roman", 40, r"LONG\s+PRIMER\s+BODY,\s+SMALL"), ("sp2", "italic", 40, r"Small\s+Pica\s+Itali"),
    ("lp1", "roman", 42, r"SMALL\s+PICA\s+BODY,\s+LONG"), ("lp1", "roman", 42, r"^LONG\s+PRIMER\s+ROMAN"),
    ("lp1", "italic", 42, r"Long\s+Primer\s+Itali"),
    ("lp1", "roman", 44, r"BURGEOIS\s+BODY,\s+LONG\s+PRIMER\s+ROMAN\.\s+No\s+[iI1]"),
    ("lp2", "roman", 44, r"^LONG\s+PRIMER\s+ROMAN\.\s+No\s+2"), ("lp2", "italic", 44, r"Long\s+Primer\s+Itali"),
    ("br", "roman", 50, r"BURGEOIS\s+BODY,\s+BREVIER\s+ROMAN\.\s+No\s+2"), ("br", "roman", 50, r"^BREVIER\s+ROMAN\.\s+No\s+2"),
    ("br", "italic", 50, r"Brevier\s+Itali"), ("br", "roman", 52, r"MINION\s+BODY,\s+BREVIER\s+ROMAN\.\s+No\s+2"),
]
# x-height in px at 600 ppi (segment box convention), per size, for the italic
# harvester's letter detection (Caslon's italic x-height is close to the roman's)
XH = {"gp": 57, "en": 47, "pica": 44, "sp2": 37, "lp1": 35, "lp2": 35, "br": 28.5}
TPL = {"gp": "gp", "en": "en", "pica": None, "sp2": "sp2", "lp1": "lp1", "lp2": "lp2", "br": "br"}


def avg_dir(size, style):
    if size == "pica":
        return "work/pica_roman_avg4" if style == "roman" else "work/pica_italic_avg11"
    return f"work/{size}_{style}_avgF"


def main():
    pages = open(f"{BD}/djvu.xml", encoding="utf-8", errors="replace").read().split("<OBJECT")[1:]
    py = [sys.executable, "-I", "-X", "utf8"]
    only = sys.argv[1] if len(sys.argv) > 1 else None     # "roman" or "italic"
    for k, (size, style, n, pat) in enumerate(BLOCKS):
        if only and style != only:
            continue
        blocks = [b for b in page_blocks(pages[n]) if re.search(pat, b[0])]
        if not blocks:
            print("no block:", size, style, n, pat); continue
        head, y0, y1 = blocks[0]
        out = f"work/k85_{size}_{style}/n{n}{k:02d}"
        env = dict(os.environ, CASLON_YRANGE=f"{y0},{y1}")
        page = f"{BD}/n{n}.jpg"
        if style == "roman":
            cmd = py + ["scripts/segment_ocr.py", page, f"{BD}/djvu.xml", str(n), str(PPI), avg_dir(size, "roman"), out]
        else:
            slant = 16.5 if size == "pica" else json.load(open(f"configs/{size}_italic.json", encoding="utf-8")).get("slant", 18)
            cmd = py + ["scripts/segment_ocr_italic.py", page, f"{BD}/djvu.xml", str(n), str(PPI), str(slant),
                        avg_dir(size, "italic"), avg_dir(size, "roman"), str(XH[size]), out]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8")
        last = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
        print(f"{size:4s} {style:6s} n{n} {head[:38]:38s} -> {out} | {last[:110]}")


if __name__ == "__main__":
    main()
