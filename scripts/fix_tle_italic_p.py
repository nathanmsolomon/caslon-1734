"""Two Lines English italic: the p carried the comma before it, and the comma was a speck (Nov 12 2026).

Usage: python -I -X utf8 scripts/fix_tle_italic_p.py   (from the project root; idempotent)

Found by check_glyphs.py (N:\\Claude Work\\_typelib) and confirmed on the published font: on the
sheet's line 2, "Catilina, patientia", the aligner put the comma of "Catilina," into the p's box
(typing p set ",p") and labelled a 11 x 17 px speck as that comma. The averager then kept the three
specks and rejected the two real commas of line 1 ("abutere,") as the minority.
In work/tle_italic_pfs_p0..2 (instances.json backed up once as .before_p_fix):
  - each p crop is reduced to the p (its largest ink piece and anything over its own width);
  - the comma that was in it becomes a new impression labelled "," (real ink, moved to its label);
  - the three specks are set aside (label "?speck", OCR-style, as label_fixes does).
Nothing else is touched. Re-averaging and the insertion into the fonts are done by
work/tle_fix_nov12.sh.
"""
import os, json, shutil
import numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    for p in "012":
        d = os.path.join(ROOT, "work", f"tle_italic_pfs_p{p}"); jp = os.path.join(d, "instances.json")
        if not os.path.exists(jp + ".before_p_fix"):
            shutil.copy(jp, jp + ".before_p_fix")
        J = json.load(open(jp + ".before_p_fix", encoding="utf-8")); I = J["instances"]; add = []
        for it in I:
            if it["ch"] == "," and (it["x1"] - it["x0"]) * (it["y1"] - it["y0"]) < 600:
                it["ocr_ch"] = ","; it["ch"] = "?speck"; print(f"p{p} {it['file']}: speck set aside")
            if it["ch"] != "p":
                continue
            src = os.path.join(d, it["file"]); keep = src + ".before_p_fix"
            if not os.path.exists(keep):
                shutil.copy(src, keep)
            g = cv2.imread(keep, 0); paper = int(np.percentile(g, 90))
            n, lab, st, _ = cv2.connectedComponentsWithStats((g < J["otsu"]).astype(np.uint8), 8)
            big = 1 + int(np.argmax(st[1:, 4])); bx0, bx1 = st[big, 0], st[big, 0] + st[big, 2]
            mine = [k for k in range(1, n) if k == big or (st[k, 0] + st[k, 2] / 2 >= bx0)]
            other = [k for k in range(1, n) if k not in mine and st[k, 4] >= 60]
            m = cv2.dilate(np.isin(lab, mine).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            cv2.imwrite(src, np.where(m, g, np.uint8(paper)).astype(np.uint8))
            ox, oy = it["crop"]
            it.update(x0=int(ox + min(st[k, 0] for k in mine)), x1=int(ox + max(st[k, 0] + st[k, 2] for k in mine)),
                      y0=int(oy + min(st[k, 1] for k in mine)), y1=int(oy + max(st[k, 1] + st[k, 3] for k in mine)), fixed="comma removed Nov 12")
            if other:
                k = max(other, key=lambda k: st[k, 4])
                mc = cv2.dilate((lab == k).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                fn = "c_" + it["file"]
                cv2.imwrite(os.path.join(d, fn), np.where(mc, g, np.uint8(paper)).astype(np.uint8))
                add.append(dict(it, file=fn, ch=",", pos=-1, x0=int(ox + st[k, 0]), x1=int(ox + st[k, 0] + st[k, 2]), y0=int(oy + st[k, 1]),
                                y1=int(oy + st[k, 1] + st[k, 3]), fixed="the comma cut out of the p's crop Nov 12", align=1.0))
                print(f"p{p} {it['file']}: p kept, its comma ({st[k, 2]} x {st[k, 3]} px) is now {fn}")
        J["instances"] = I + add
        json.dump(J, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
