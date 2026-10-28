"""Line pitch of a book page, in px: the classic way to tell a type's body.

Usage: python -I line_pitch.py <page.jpg> [<page.jpg> ...]

Autocorrelation of the row ink profile of the central text block; prints the
strongest period between 70 and 280 px with its strength. A solid-set page has
pitch = body; a leaded page has pitch > body.
"""
import sys, os
import cv2
import numpy as np


def pitch(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE).astype(np.float32)
    h, w = im.shape
    c = im[int(0.2 * h):int(0.8 * h), int(0.25 * w):int(0.75 * w)]
    paper, ink = np.percentile(c, 80), np.percentile(c, 1)
    prof = np.clip((paper - c) / (paper - ink + 1e-6), 0, 1).mean(1)
    prof = prof - prof.mean()
    ac = np.correlate(prof, prof, "full")[len(prof) - 1:]
    ac /= ac[0] + 1e-9
    lo, hi = 70, min(280, len(ac) - 1)
    k = lo + int(np.argmax(ac[lo:hi]))
    # refine: a peak at 2x the true pitch can win; prefer the half if strong
    if k // 2 >= lo and ac[k // 2 - 3:k // 2 + 4].max() > 0.6 * ac[k]:
        k = k // 2 - 3 + int(np.argmax(ac[k // 2 - 3:k // 2 + 4]))
    # sub-pixel parabola
    if 1 <= k < len(ac) - 1:
        a, b, c2 = ac[k - 1], ac[k], ac[k + 1]
        k = k + 0.5 * (a - c2) / (a - 2 * b + c2 + 1e-9)
    return float(k), float(ac[int(round(k))])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        k, s = pitch(p)
        print(f"{os.path.basename(p)[:60]:60s} pitch {k:6.1f} px  strength {s:.2f}")
