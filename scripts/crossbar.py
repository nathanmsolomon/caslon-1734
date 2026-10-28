"""Crossbar scores used to separate f-ligatures from long-s ligatures.
ff_score: ink continuity between the two stems at crossbar height (ff vs ſſ).
fi_score: ink to the right of the first stem at crossbar height (fi vs ſi, ffi vs ſſi)."""
import cv2, numpy as np

def _ink(path):
    im = cv2.imread(path, 0).astype(np.float32); dd = 255 - im
    ys, xs = np.where(dd > 70)
    return dd[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

def ff_score(path):
    dd = cv2.resize(_ink(path), (48, 64), interpolation=cv2.INTER_AREA)
    b = dd[22:32, :].mean(0); b = b / (b.max() + 1e-6)
    pk = sorted(np.argsort(b)[-2:]); a, c = pk if pk[1] - pk[0] >= 6 else (10, 34)
    return float(b[a:c].min())

def fi_score(path):
    dd = _ink(path); H, W = dd.shape
    prof = dd[int(0.38 * H):int(0.48 * H), :].mean(0) / (dd.max() + 1e-6)
    stem = int(np.argmax(dd[int(0.5 * H):, :].mean(0)[:W // 2]))
    right = prof[stem + 4:stem + 4 + int(0.18 * W)]
    return float(right.mean()) if len(right) else 0.0, W / H
