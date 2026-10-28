"""Proof sheet for one config: the 1734 block above, the same text set in the
new font below (clean version), at the scan's own scale.

Usage: python -I proof_size.py <config.json> [<config.json> ...]
Writes proofs/<name>_proof.png for each.
"""
import sys, os, json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from setline import render  # noqa: E402


def label(img, text):
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    bar = np.full((max(40, img.shape[1] // 40), img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (10, bar.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, bar.shape[0] / 60, (30, 30, 160), 2)
    return np.vstack([bar, img])


def main():
    for cp in sys.argv[1:]:
        C = json.load(open(cp, encoding="utf-8"))
        R = json.load(open(f"work/{C['name']}_result.json", encoding="utf-8"))
        nm = C["name"]
        if C.get("images"):                       # italic: show the original, unsheared block
            geo = json.load(open(C["images"]["1"].replace("_p1.png", "_geometry.json")))
            x0, y0, x1, y1 = geo["boxes"]["1"]
        else:
            x0, y0, x1, y1 = C["boxes"]["1"]
        scan = cv2.imread("work/page1.png", 0)[y0:y1, x0:x1]
        text = [l.rstrip("\n").replace("{", "").replace("}", "") for l in open(C["trans"], encoding="utf-8") if l.strip()]
        font = R["fonts"][0]
        img = render(font, R["pitch_px"], text)
        W = max(scan.shape[1], img.shape[1])
        pad = lambda a: np.pad(a, ((0, 0), (0, W - a.shape[1]), (0, 0)), constant_values=255)
        fid = R["fidelity"][0].split("median")[-1].strip() + " vs " + R["fidelity"][1].split("median")[-1].strip()
        sheet = np.vstack([pad(label(scan, f"1734 specimen: {C['family']} {C['style']} (McGill copy 2)")),
                           pad(label(img, f"font, same text set solid; fidelity {fid}"))])
        s = min(1.0, 1400 / sheet.shape[1])
        out = f"proofs/{nm}_proof.png"
        cv2.imwrite(out, cv2.resize(sheet, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        print(out)


if __name__ == "__main__":
    main()
