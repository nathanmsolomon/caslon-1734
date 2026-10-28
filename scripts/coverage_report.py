"""Print a Markdown table of what each font lacks (DOCUMENTATION.md section 8).

Usage: python -I coverage_report.py > work/coverage.md

For every face: the characters of the standard set (gen_catalogue.py: capitals,
lowercase, figures, punctuation, ligatures) missing from the clean font, and those
the Impression font adds (verified single impressions). Read from the fonts
themselves (cmap + ligature substitutions).
"""
import os, sys
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_catalogue import UP, LOW, FIG, PUN, LIGS, FACES  # noqa: E402

TITLING = [(f"Titling {n}", f"Titling{n}") for n in range(1, 8)]


def have(fp):
    f = TTFont(fp)
    s = {chr(c) for c in f.getBestCmap()}
    ligs = set()
    if "GSUB" in f:
        for lk in f["GSUB"].table.LookupList.Lookup:
            for st in lk.SubTable:
                st = getattr(st, "ExtSubTable", st)
                for ls in getattr(st, "ligatures", {}).values():
                    ligs |= {l.LigGlyph for l in ls}
    return s | {seq for seq, name in LIGS if name in ligs}


def row(label, stem, style, chars):
    c, i = f"fonts/Caslon1734{stem}-{style}.otf", f"fonts/Caslon1734{stem}Impression-{style}.otf"
    if not os.path.exists(c):
        return None
    hc, hi = have(c), have(i) if os.path.exists(i) else set()
    miss = [x for x in chars if x not in hc]
    extra = [x for x in chars if x in hi and x not in hc]
    gone = [x for x in miss if x not in extra]
    if len(gone) > len(chars) / 2:
        # display sizes: the sheet shows a line or two, so list what is there
        present = [x for x in chars if x in hc]
        return f"| {label} {style.lower()} | all but these {len(present)}: {' '.join(present)} | {' '.join(extra) or '—'} |"
    return f"| {label} {style.lower()} | {' '.join(gone) or '—'} | {' '.join(extra) or '—'} |"


def main():
    full = list(UP + LOW + FIG + PUN) + [seq for seq, _ in LIGS]
    print("| Font | Missing (both versions) | In the Impression version only |")
    print("|---|---|---|")
    for label, stem, *_ in FACES:
        for style in ("Roman", "Italic"):
            r = row(label, stem, style, full)
            if r:
                print(r)
    caps = list(UP)
    for label, stem in TITLING:
        r = row(label, stem, "Roman", caps)
        if r:
            print(r.replace(" roman |", " |", 1))


if __name__ == "__main__":
    main()
