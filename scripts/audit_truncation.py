"""Are harvested letters being cut off? Width/height audit of every harvest.

Usage: python -I audit_truncation.py <size> <roman|italic> <dir_or_glob> [...]

A letter clipped by a crop box or by the ink-splitting of forced alignment
comes out narrower (or shorter) than the letter really is. For each harvested
impression the ink extent is compared with the expected extent of that letter
in that size: the size's own sheet average where it has the letter, otherwise
the Pica of the same style scaled by x-height. Per source group and letter it
prints the median ratio and the share of impressions under 0.8 of the expected
width (or height); a healthy harvest sits near 1.0 with few under 0.8.
"""
import sys, os, json, glob, collections
import cv2
import numpy as np

REF = {"pica_roman": "work/pica_roman_avg4", "pica_italic": "work/pica_italic_avg11"}
XH_PICA = 44.0


def extents(avg):
    g = json.load(open(os.path.join(avg, "glyphs.json"), encoding="utf-8"))
    up, out = g["up"], {}
    for gid, v in g["glyphs"].items():
        a = cv2.imread(os.path.join(avg, f"avg_{gid}.png"), -1)
        if a is None:
            continue
        m = a > 0.5 * 65535
        xs, ys = np.where(m.any(0))[0], np.where(m.any(1))[0]
        if len(xs):
            out[v["ch"]] = ((xs[-1] - xs[0] + 1) / up, (ys[-1] - ys[0] + 1) / up)
    return out


def ink_extent(path):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    paper, ink = np.percentile(im, 90), np.percentile(im, 1)
    d = (paper - im.astype(np.float32)) / (paper - ink + 1e-6)
    m = d > 0.5
    xs, ys = np.where(m.any(0))[0], np.where(m.any(1))[0]
    return (xs[-1] - xs[0] + 1, ys[-1] - ys[0] + 1) if len(xs) else None


def main():
    size, style = sys.argv[1], sys.argv[2]
    own = f"work/{size}_{style}_avgF" if size != "pica" else REF[f"pica_{style}"]
    E = extents(own)
    P = extents(REF[f"pica_{style}"])
    xh_own = np.median([E[c][1] for c in "xuvwz" if c in E] or [E.get("x", (0, XH_PICA))[1]])
    xh_ref = np.median([P[c][1] for c in "xuvwz" if c in P])
    k = xh_own / xh_ref
    def expect(ch):
        if ch in E:
            return E[ch], "sheet"
        if ch in P:
            return (P[ch][0] * k, P[ch][1] * k), "pica"
        return None, None
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for pat in sys.argv[3:]:
        for d in sorted(glob.glob(pat)):
            jp = os.path.join(d, "instances.json")
            if not os.path.exists(jp):
                continue
            grp = os.path.basename(os.path.dirname(d.rstrip("/\\"))) if os.path.basename(d).startswith("n") else os.path.basename(d)
            for i in json.load(open(jp, encoding="utf-8"))["instances"]:
                ch = i["ch"]
                if len(ch) != 1 or not ch.isalnum():
                    continue
                ex, _ = expect(ch)
                if ex is None:
                    continue
                e = ink_extent(os.path.join(d, i["file"]))
                if e is None:
                    continue
                groups[grp][ch].append((e[0] / ex[0], e[1] / ex[1]))
    for grp, L in groups.items():
        allw = [w for v in L.values() for w, h in v]
        print(f"== {grp}: {len(allw)} impressions; width ratio median {np.median(allw):.2f}; under 0.8: {100 * np.mean(np.array(allw) < 0.8):.1f}%")
        bad = []
        for ch, v in sorted(L.items()):
            w = np.array([a for a, b in v]); h = np.array([b for a, b in v])
            fw, fh = np.mean(w < 0.8), np.mean(h < 0.8)
            if len(v) >= 5 and (fw > 0.25 or fh > 0.25):
                bad.append(f"{ch}({len(v)}: w{np.median(w):.2f} {100 * fw:.0f}%<0.8, h{np.median(h):.2f} {100 * fh:.0f}%<0.8, ref {expect(ch)[1]})")
        if bad:
            print("   letters often cut short:", " ".join(bad))


if __name__ == "__main__":
    main()
