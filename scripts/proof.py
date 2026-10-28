"""Overlay proof: re-set each scanned word with the font, at the scan's own
scale and word positions, and colour the disagreement.

Usage: python -I proof.py <font.otf> <page.png> <instances_dir> <pitch_px> <out.png>

Black = both, red = scan only (font too thin / missing), blue = font only.
Word positions come from the scan (the lines are justified); letters inside a
word are placed purely by the font's advance widths, so this also tests the
recovered spacing.
"""
import sys, os, json
import cv2
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

ALIGN = False

sys.path.insert(0, os.path.dirname(__file__))
from glyphnames import NAMES as _N, LIGATURES
NAMES = {k: v[0] for k, v in _N.items()}


class PolyPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs); self.polys = []; self.cur = []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 12)[1:]:
            u = 1 - t
            self.cur.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                             u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    def _closePath(self):
        if self.cur: self.polys.append(self.cur)
        self.cur = []


def main():
    global ALIGN
    fontp, page, idir, pitch, outp = sys.argv[1:6]
    ALIGN = len(sys.argv) > 6 and sys.argv[6] == "align"
    pitch = float(pitch)
    f = TTFont(fontp); gs = f.getGlyphSet(); hmtx = f["hmtx"]
    s = pitch / 1000.0
    I = json.load(open(os.path.join(idir, "instances.json"), encoding="utf-8"))["instances"]
    im = cv2.imread(page, cv2.IMREAD_GRAYSCALE)
    x0 = min(i["crop"][0] for i in I) - 30; y0 = min(i["crop"][1] for i in I) - 30
    x1 = max(i["x1"] for i in I) + 30; y1 = max(i["y1"] for i in I) + 30
    scan = im[y0:y1, x0:x1]
    _, scan_bw = cv2.threshold(cv2.GaussianBlur(scan, (3, 3), 0), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    SS = 4  # supersample the font raster
    fr = np.zeros(((y1 - y0) * SS, (x1 - x0) * SS), np.uint8)
    shifts = []
    words = {}
    for i in I:
        words.setdefault((i["line"], i["word"]), []).append(i)
    for key, ws in words.items():
        ws.sort(key=lambda i: i["pos"])
        first = ws[0]
        n0 = NAMES.get(first["ch"], first["ch"])
        if n0 not in gs:
            continue
        # place the word so the first glyph's ink-left matches the scan's
        pp = PolyPen(gs); gs[n0].draw(pp)
        left_ink = min(p[0] for poly in pp.polys for p in poly) if pp.polys else 0
        pen_x = first["x0"] - left_ink * s
        for i in ws:
            nm = NAMES.get(i["ch"], i["ch"])
            if nm not in gs:
                pen_x += 0; continue
            pp = PolyPen(gs); gs[nm].draw(pp)
            base = i["baseline"]
            polys = [np.array([[((pen_x + x * s) - x0) * SS, ((base - y * s) - y0) * SS] for x, y in poly], np.int32)
                     for poly in pp.polys]
            # even-odd fill handles counters
            mask = np.zeros_like(fr)
            for p in polys:
                tmp = np.zeros_like(fr); cv2.fillPoly(tmp, [p], 255); mask ^= tmp
            if ALIGN:
                # shape-only check: slide this glyph (within 4 px) onto its own impression
                gx0, gy0 = max(0, (i["x0"] - x0 - 10)), max(0, (i["y0"] - y0 - 10))
                gx1, gy1 = i["x1"] - x0 + 10, i["y1"] - y0 + 10
                fm = cv2.resize(mask, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)[gy0:gy1, gx0:gx1].astype(np.float32)
                sm = scan_bw[gy0:gy1, gx0:gx1].astype(np.float32)
                if fm.sum() > 0 and sm.sum() > 0:
                    (ddx, ddy), _ = cv2.phaseCorrelate(fm, sm)
                    if abs(ddx) < 4 and abs(ddy) < 4:
                        M = np.float32([[1, 0, ddx * SS], [0, 1, ddy * SS]])
                        mask = cv2.warpAffine(mask, M, (mask.shape[1], mask.shape[0]))
                        shifts.append((ddx, ddy))
            fr |= mask
            pen_x += hmtx[nm][0] * s
    font_bw = cv2.resize(fr, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA) > 127
    sc = scan_bw > 0
    (sx, sy), _ = cv2.phaseCorrelate(sc.astype(np.float32), font_bw.astype(np.float32))
    print(f"global offset font vs scan: dx {sx:+.2f} dy {sy:+.2f} px")
    out = np.full(sc.shape + (3,), 255, np.uint8)
    out[sc & font_bw] = (40, 40, 40)
    out[sc & ~font_bw] = (40, 40, 230)
    out[~sc & font_bw] = (230, 120, 30)
    cv2.imwrite(outp, out)
    both, so, fo = (sc & font_bw).sum(), (sc & ~font_bw).sum(), (~sc & font_bw).sum()
    if shifts:
        sh = np.array(shifts)
        print(f"per-glyph placement error: rms dx {np.sqrt((sh[:,0]**2).mean()):.2f} dy {np.sqrt((sh[:,1]**2).mean()):.2f} px (n={len(sh)})")
    print(f"agreement (IoU) {both / (both + so + fo):.3f}  scan-only {so / sc.sum():.3f}  font-only {fo / sc.sum():.3f}")


if __name__ == "__main__":
    main()
