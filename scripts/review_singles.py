"""Contact sheet of thinly attested book-only glyphs (1-4 impressions), for the
by-eye check that lets one into the Impression font (scripts/impression_singles.json).

Usage: python -I review_singles.py <avg dir> <out.png> [reference avg dirs...] [--thin=<dir>]
(--thin: an average.py run with CASLON_ONLY_THIN=1 on the same sources; default <avg dir>)

Each row: the glyph's impressions as average.py registered them (avg dir/thin/,
numbered as in thin.json), then the same character from each reference size,
scaled by the ratio of the two sizes' x ink heights, then two letters of this
face for weight and size. Accept an impression only if it is plainly that
character, the right size and weight, and not broken or a wrong-fount sort.
"""
import sys, os, json, glob
import numpy as np, cv2

CONTEXT = {"d": "0123456789", "u": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "l": "abcdefghijklmnopqrstuvwxyz"}


def load(avg):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    return g, {v["ch"]: gid for gid, v in g["glyphs"].items()}


def img(path):
    a = cv2.imread(path, -1)
    return None if a is None else a.astype(np.float32) / 65535


def xh(avg, g, by):
    a = img(os.path.join(avg, f"avg_{by['x']}.png")) if "x" in by else None
    if a is None:
        return None
    r = np.where((a > 0.5).any(1))[0]
    return (r[-1] - r[0] + 1) if len(r) else None


def crop(a, base_row, h):
    # same vertical window for every tile (baseline at the same height)
    top = max(0, base_row - int(0.95 * h)); a = a[top:top + int(1.45 * h)]
    cols = np.where((a > 0.3).any(0))[0]
    if len(cols):
        a = a[:, max(0, cols[0] - 10):cols[-1] + 10]
    return a


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--thin=")]
    td = next((a[7:] for a in sys.argv[1:] if a.startswith("--thin=")), args[0])
    avg, outp, refs = args[0], args[1], args[2:]
    g, by = load(avg)
    gt = json.load(open(os.path.join(td, "glyphs.json"), encoding="utf-8"))
    thin = json.load(open(os.path.join(td, "thin", "thin.json"), encoding="utf-8"))
    X = xh(avg, g, by) or 100
    H = int(2.4 * X)
    rows = []
    for gid, t in sorted(thin.items(), key=lambda kv: kv[1]["ch"]):
        ch = t["ch"]
        tiles = []
        for k in range(len(t["ids"])):
            a = img(os.path.join(td, "thin", f"{gid}_{k}.png"))
            tiles.append((crop(a, gt["base_row"], 1.0 * H), f"{k}" + ("" if t["ids"][k] in t["kept_by_rejection"] else " rej")))
        for r in refs:
            gr, br = load(r)
            if ch in br:
                xr = xh(r, gr, br)
                a = img(os.path.join(r, f"avg_{br[ch]}.png"))
                if a is not None and xr:
                    f = X / xr
                    a = cv2.resize(a, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
                    tiles.append((crop(a, int(gr["base_row"] * f), 1.0 * H), os.path.basename(os.path.normpath(r)).split("_")[0]))
        kind = "d" if ch.isdigit() else "u" if ch.isupper() else "l"
        for c in [c for c in CONTEXT[kind] if c != ch and c in by][:2]:
            a = img(os.path.join(avg, f"avg_{by[c]}.png"))
            tiles.append((crop(a, g["base_row"], 1.0 * H), f"this {c}"))
        rows.append((ch, tiles))
    pad, lab = 20, 60
    th = max(t.shape[0] for _, ts in rows for t, _ in ts) + lab
    sheet_rows = []
    for ch, ts in rows:
        row = [np.full((th, 160), 255, np.uint8)]
        cv2.putText(row[0], repr(ch), (10, th // 2), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 0, 3)
        for t, name in ts:
            tile = np.full((th, t.shape[1] + 2 * pad), 255, np.uint8)
            tile[:t.shape[0], pad:pad + t.shape[1]] = (255 * (1 - np.clip(t, 0, 1))).astype(np.uint8)
            cv2.putText(tile, name, (pad, th - 15), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 90, 2)
            row.append(tile)
        sheet_rows.append(np.hstack(row))
    W = max(r.shape[1] for r in sheet_rows)
    sheet = np.vstack([np.hstack([r, np.full((r.shape[0], W - r.shape[1]), 255, np.uint8)]) for r in sheet_rows])
    s = min(1.0, 3000 / W)
    cv2.imwrite(outp, cv2.resize(sheet, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
    print(outp, len(rows), "glyphs")


if __name__ == "__main__":
    main()
