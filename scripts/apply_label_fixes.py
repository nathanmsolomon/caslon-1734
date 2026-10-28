"""Apply by-eye label corrections to harvested impressions (scripts/label_fixes.json).

Usage: python -I apply_label_fixes.py

label_fixes.json maps "work/<tag>/n<page>/<file>.png" to a new label ("?fig" or
any label starting with "?" sets the impression aside). The OCR's label is kept
as "ocr_ch". Idempotent; run after any re-harvest (relabel_all.sh does).
"""
import json, os
from collections import defaultdict

S = os.path.dirname(os.path.abspath(__file__))


def main():
    fixes = json.load(open(os.path.join(S, "label_fixes.json"), encoding="utf-8"))["labels"]
    by_dir = defaultdict(dict)
    for path, lab in fixes.items():
        d, f = os.path.split(path)
        by_dir[d][f] = lab
    n = 0
    for d, fs in by_dir.items():
        p = os.path.join(d, "instances.json")
        if not os.path.exists(p):
            continue
        meta = json.load(open(p, encoding="utf-8"))
        for i in meta["instances"]:
            if i["file"] in fs and i["ch"] != fs[i["file"]]:
                i.setdefault("ocr_ch", i["ch"])
                i["ch"] = fs[i["file"]]
                n += 1
        json.dump(meta, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print(n, "labels corrected by eye")


if __name__ == "__main__":
    main()
