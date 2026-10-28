#!/bin/sh
# Small capitals for one size from its confirmed books: harvest every downloaded
# page with smallcaps_ocr.py, average, and give each small capital its capital's
# sidebearings scaled by the ink-width ratio (small caps were letterspaced in
# print, so abutment can't be measured). Result: work/<size>_sc_avg, used by
# build.py through the config key "extra".
# Usage: sh scripts/smallcaps_size.sh <size> "<page_dir>|<djvu.xml>|<ppi>|<xh>|<jpg prefix>" ...
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
s=$1; shift
# templates: the supplemented average where there is one (it has the book-only lowercase)
R=work/${s}_roman_avgS; [ -s $R/glyphs.json ] || R=work/${s}_roman_avgF
[ $s = pica ] && R=work/pica_roman_avg4      # Pica predates run_size.py
# SC_SKIP_HARVEST=1 redoes only the averaging and spacing from the existing harvest
[ -z "$SC_SKIP_HARVEST" ] && { rm -rf work/sc_$s; mkdir -p work/sc_$s; }
[ -n "$SC_SKIP_HARVEST" ] && set --
for spec in "$@"; do
  d=$(echo "$spec" | cut -d'|' -f1); x=$(echo "$spec" | cut -d'|' -f2); ppi=$(echo "$spec" | cut -d'|' -f3)
  xh=$(echo "$spec" | cut -d'|' -f4); pre=$(echo "$spec" | cut -d'|' -f5)
  b=$(basename $d)
  for f in $d/${pre}[0-9]*.jpg; do
    n=$(basename $f .jpg); n=${n#$pre}
    $PY scripts/smallcaps_ocr.py $f $x $n $ppi $R $xh work/sc_$s/${b}_n$n > /dev/null 2>&1
  done
done
# SC_PRIMARY: small capitals cut from the 1734 sheet itself (Pica: work/pica_sc_p0..2),
# averaged as primary copies alongside the book ones
( for d in $SC_PRIMARY; do echo $d; done; for d in work/sc_$s/*; do [ -s $d/instances.json ] && echo "+$d"; done ) > work/sc_${s}_dirs.txt
rm -rf work/${s}_sc_avg
$PY scripts/average.py work/${s}_sc_avg @work/sc_${s}_dirs.txt > work/sc_${s}_avg_log.txt 2>&1
$PY - $s <<'EOF'
import json, sys
s = sys.argv[1]
import os
# the supplemented average (sheet + books) has metrics for capitals the sheet lacks
md = f"work/{s}_roman_avgS" if os.path.exists(f"work/{s}_roman_avgS/metrics.json") else f"work/{s}_roman_avgF"
if s == "pica":
    md = "work/pica_roman_avg4"
R = json.load(open(f"{md}/metrics.json", encoding="utf-8"))["glyphs"]
G = json.load(open(f"work/{s}_sc_avg/glyphs.json", encoding="utf-8"))["glyphs"]
inkw = {}
for v in G.values():
    # small caps seen at least twice; a single impression is too likely a stray
    if v["ch"].endswith(".sc") and v["n"] >= 2 and v["ch"][0] in R:
        inkw[v["ch"]] = v
out = {}
for c, v in inkw.items():
    cap = R[c[0]]
    import cv2, numpy as np
    gid = next(k for k, g in G.items() if g["ch"] == c)
    up = json.load(open(f"work/{s}_sc_avg/glyphs.json", encoding="utf-8"))["up"]
    a = cv2.imread(f"work/{s}_sc_avg/avg_{gid}.png", -1)
    xs = np.where((a > 0.5 * 65535).any(0))[0]
    w = (xs.max() - xs.min() + 1) / up
    f = w / cap["inkw"]
    out[c] = dict(adv=cap["lsb"] * f + w + cap["rsb"] * f, lsb=cap["lsb"] * f, rsb=cap["rsb"] * f, inkw=w, pairs=0,
                  n=v["n"], source="estimated: capital sidebearings scaled by ink-width ratio (small caps were letterspaced in print)")
json.dump(dict(glyphs=out), open(f"work/{s}_sc_avg/metrics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(s, "small caps:", " ".join(f"{c[0]}{v['n']}" for c, v in sorted(out.items())) or "none")
EOF
