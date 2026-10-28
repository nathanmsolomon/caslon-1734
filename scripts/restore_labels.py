"""Label ligature candidates in a fresh harvest using the cluster decisions made
by eye in earlier rounds (matched by identical crop bytes), and re-split f/long-s
forms by crossbar score. Paths are normalised throughout.

Usage: python -I restore_labels.py <harvest_root>
"""
import sys, os, json, glob, hashlib, collections
sys.path.insert(0, os.path.dirname(__file__))
from crossbar import ff_score, fi_score  # noqa: E402

N = lambda p: os.path.normpath(p)
md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()

# decisions recorded from the reviewed contact sheets
ROUNDS = [
    ("work/lig/clusters.json", {"1": "ct", "8": "ct", "4": "fl", "5": "ſh", "6": "ſh", "10": "ſh", "12": "ſh", "13": "ſh"},
     ["0", "2", "3", "11", "18"]),
    ("work/lig2/clusters.json", {"3": "ct", "6": "ct", "11": "ct", "2": "fl", "20": "ſk",
                                 **{c: "ſh" for c in ["4", "7", "9", "12", "17", "21", "23", "30"]}},
     ["1", "5", "8", "10", "16", "18", "24"]),
]

named, crossbar = {}, set()
for path, names, split in ROUNDS:
    meta = json.load(open(path, encoding="utf-8"))
    for ci, m in meta.items():
        for d, f in m["members"]:
            p = os.path.join(d, f)
            if not os.path.exists(p):
                continue
            h = md5(p)
            if ci in names:
                named[h] = names[ci]
            elif ci in split:
                crossbar.add(h)

root = sys.argv[1]
count = collections.Counter()
for jp in glob.glob(os.path.join(root, "*", "instances.json")):
    d = N(os.path.dirname(jp))
    J = json.load(open(jp, encoding="utf-8"))
    for i in J["instances"]:
        p = os.path.join(d, i["file"])
        if i["ch"].startswith("LIG:"):
            h = md5(p)
            if h in named:
                i["ch"] = named[h]
            elif h in crossbar:
                s = ff_score(p)
                i["ch"] = "" if 0.35 <= s < 0.42 else ("ff" if s >= 0.42 else "ſſ")
            else:
                i["ch"] = ""
        elif i["ch"] in ("ſi", "ſſi"):
            s, ar = fi_score(p)
            if ar > 0.85:
                i["ch"] = "ffi" if s >= 0.45 else ""
            else:
                i["ch"] = "fi" if s >= 0.47 else ("ſi" if s < 0.43 else "")
        count[i["ch"]] += 1
    J["instances"] = [i for i in J["instances"] if i["ch"]]
    json.dump(J, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print({k: v for k, v in sorted(count.items()) if len(k) > 1 or k in "?!" or k == ""})
