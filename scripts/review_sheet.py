"""Contact sheet of instances per label: python -I review_sheet.py <out.png> <labels|ALL-NEW> <instances_dir>..."""
import sys, os, json
import cv2, numpy as np
outp, labels, dirs = sys.argv[1], sys.argv[2], sys.argv[3:]
NEW = set("kwxyzYZ0123456789")
rows = {}
for d in dirs:
    for i in json.load(open(os.path.join(d, "instances.json"), encoding="utf-8"))["instances"]:
        ch = i["ch"]
        if (labels == "ALL-NEW" and (ch in NEW or ch.startswith("LIG"))) or ch in labels.split(","):
            im = cv2.imread(os.path.join(d, i["file"]), 0)
            rows.setdefault(ch, []).append(im)
H = 90
strips = []
for ch in sorted(rows):
    cells = []
    for im in rows[ch][:28]:
        s = H / max(im.shape[0], 1) if im.shape[0] > H else 1.0
        im = cv2.resize(im, None, fx=s, fy=s) if s != 1.0 else im
        c = np.full((H, im.shape[1] + 6), 255, np.uint8)
        c[H - im.shape[0]:, 3:3 + im.shape[1]] = im
        cells.append(c)
    lab = np.full((H, 110), 255, np.uint8)
    cv2.putText(lab, f"{ch} ({len(rows[ch])})", (3, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 2)
    strips.append(np.hstack([lab] + cells))
W = max(s.shape[1] for s in strips)
cv2.imwrite(outp, np.vstack([np.pad(s, ((2, 2), (0, W - s.shape[1])), constant_values=255) for s in strips]))
