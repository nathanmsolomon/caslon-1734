"""Cluster ligature candidates (LIG:<ocr> labels) by shape so each cluster can be
named by eye. Writes a contact sheet with cluster ids and clusters.json.

Usage: python -I cluster_ligs.py <out_dir> <instances_dir> [...]
Then label: python -I cluster_ligs.py --apply <out_dir> <names.json>
  names.json maps cluster id -> glyph label (e.g. "fi", "ſſ", "ct") or "" to drop.
"""
import sys, os, json
import cv2
import numpy as np

S = 64  # normalised cell size


def norm(im):
    d = 255 - im.astype(np.float32)
    ys, xs = np.where(d > 60)
    if len(xs) == 0:
        return None
    d = d[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = d.shape
    sc = S / max(h, w)
    d = cv2.resize(d, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_AREA)
    c = np.zeros((S, S), np.float32)
    c[S - d.shape[0]:, :d.shape[1]] = d  # bottom-left anchored (baseline-ish)
    c -= c.mean()
    return c / (np.linalg.norm(c) + 1e-9), (h, w)


def run(out, dirs):
    items = []
    for d in dirs:
        for i in json.load(open(os.path.join(d, "instances.json"), encoding="utf-8"))["instances"]:
            if i["ch"].startswith("LIG:"):
                im = cv2.imread(os.path.join(d, i["file"]), 0)
                r = norm(im)
                if r is not None:
                    items.append((d, i["file"], i["ch"], r[0], r[1], im))
    # greedy leader clustering on NCC, separately per aspect class
    clusters = []
    for it in items:
        best, bv = None, 0.0
        for c in clusters:
            v = float((it[3] * c["lead"]).sum())
            ar = it[4][1] / it[4][0]
            if v > bv and abs(ar / c["ar"] - 1) < 0.25:
                best, bv = c, v
        if best is not None and bv > 0.80:
            best["members"].append(it)
        else:
            clusters.append(dict(lead=it[3], ar=it[4][1] / it[4][0], members=[it]))
    clusters.sort(key=lambda c: -len(c["members"]))
    os.makedirs(out, exist_ok=True)
    rows, meta = [], {}
    for ci, c in enumerate(clusters):
        ocr = {}
        for m in c["members"]:
            ocr[m[2]] = ocr.get(m[2], 0) + 1
        meta[ci] = dict(n=len(c["members"]), ocr=ocr, members=[[m[0], m[1]] for m in c["members"]])
        if len(c["members"]) < 2:
            continue
        cells = []
        for m in c["members"][:16]:
            im = m[5]
            s = 80 / im.shape[0] if im.shape[0] > 80 else 1.0
            im = cv2.resize(im, None, fx=s, fy=s) if s != 1 else im
            cell = np.full((80, im.shape[1] + 4), 255, np.uint8); cell[80 - im.shape[0]:, 2:2 + im.shape[1]] = im
            cells.append(cell)
        lab = np.full((80, 190), 255, np.uint8)
        cv2.putText(lab, f"#{ci} n={len(c['members'])}", (3, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 0, 2)
        cv2.putText(lab, " ".join(f"{k[4:]}:{v}" for k, v in sorted(ocr.items(), key=lambda t: -t[1])[:3]),
                    (3, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 0, 1)
        rows.append(np.hstack([lab] + cells))
    W = max(r.shape[1] for r in rows)
    cv2.imwrite(os.path.join(out, "lig_clusters.png"),
                np.vstack([np.pad(r, ((2, 2), (0, W - r.shape[1])), constant_values=255) for r in rows]))
    json.dump(meta, open(os.path.join(out, "clusters.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(len(items), "candidates in", len(clusters), "clusters;", len(rows), "with 2+ members")


def apply(out, names_file):
    meta = json.load(open(os.path.join(out, "clusters.json"), encoding="utf-8"))
    names = json.load(open(names_file, encoding="utf-8"))
    relabel = {}
    for ci, name in names.items():
        for d, f in meta[ci]["members"]:
            relabel[(d, f)] = name
    touched = {d for d, _ in relabel}
    for d in touched:
        p = os.path.join(d, "instances.json")
        J = json.load(open(p, encoding="utf-8"))
        for i in J["instances"]:
            if i["ch"].startswith("LIG:"):
                i["ch"] = relabel.get((d, i["file"]), "")  # unnamed clusters are dropped
        J["instances"] = [i for i in J["instances"] if i["ch"]]
        json.dump(J, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("relabelled", len(relabel), "in", len(touched), "dirs")


if __name__ == "__main__":
    if sys.argv[1] == "--apply":
        apply(sys.argv[2], sys.argv[3])
    else:
        run(sys.argv[1], sys.argv[2:])
