"""Lower the bottom edge of sheet block boxes so descenders of the last line fit.

Usage: python -I extend_boxes.py <config_name> [...]

A box ending just under the alphabet line's baseline cuts J's tail and Q's
(found by crop_audit.py). For each copy, the bottom edge moves down to just
above the next ink below the block (the next block's heading), at most 45 px.
Only configs that crop from the page images (roman blocks) are changed.
"""
import sys, json
import cv2
import numpy as np


def main():
    for nm in sys.argv[1:]:
        p = f"configs/{nm}.json"
        C = json.load(open(p, encoding="utf-8"))
        if C.get("images"):
            print(nm, "uses its own block images; skipped"); continue
        changed = {}
        for k, (x0, y0, x1, y1) in C["boxes"].items():
            im = cv2.imread(f"work/page{k}.png", cv2.IMREAD_GRAYSCALE)
            band = im[y1:y1 + 120, x0:x1].astype(np.float32)
            paper = np.percentile(band, 90)
            ink_rows = ((paper - band) > 60).sum(1)
            # rows past the current edge that still belong to this block's last line
            # (descenders) are ink-sparse; the next block starts after a clear gap
            gap_end = None
            seen_gap = False
            for r in range(len(ink_rows)):
                if ink_rows[r] <= 2:
                    seen_gap = True
                elif seen_gap and ink_rows[r] > 8:
                    gap_end = r; break
            limit = 45 if gap_end is None else max(0, min(45, gap_end - 6))
            changed[k] = [x0, y0, x1, y1 + limit]
        C["boxes"] = changed
        json.dump(C, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(nm, {k: v[3] for k, v in changed.items()})


if __name__ == "__main__":
    main()
