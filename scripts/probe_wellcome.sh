#!/bin/sh
# Skeleton-test candidate Wellcome Collection books for a 1734 cut.
# Usage: sh scripts/probe_wellcome.sh <list: "manifest page ppi" per line> <template avg> <x-height px@600> [pages around, default 2]
# Like probe_skel.sh, but pages and OCR come from Wellcome (scripts/wellcome_fetch.py).
# Wellcome records no scan resolution: give the ppi implied by the screen's scale
# (450 x scale); the skeleton test's fitted scale should then come out near 1.0.
cd "$(dirname "$0")/.."
LIST=$1; TPL=$2; XH=$3; K=${4:-2}
S="work/snap/en work/snap/pica work/snap/sp1 work/snap/sp2 work/snap/lp1 work/snap/lp2 work/snap/br work/snap/gp work/snap/dp"
tr -d '\r' < $LIST | while read man n ppi; do
  [ -n "$man" ] || continue
  d=source/books/wellcome/$man; w=work/probe_wellcome/${man}_k$K; mkdir -p $w
  pages=$(python -I -c "print(','.join(str(i) for i in range(max(0,$n-$K), $n+$K+1)))")
  python -I -X utf8 scripts/wellcome_fetch.py $man $pages $d > /dev/null 2>&1
  for i in $(echo $pages | tr ',' ' '); do
    [ -s $d/n$i.jpg ] && python -I -X utf8 scripts/segment_ocr.py $d/n$i.jpg $d/djvu.xml $i $ppi $TPL $w/n$i $XH > /dev/null 2>&1
  done
  for x in $w/n*; do [ -s $x/instances.json ] && echo $x; done > $w/dirs.txt
  rm -rf $w/avg; python -I -X utf8 scripts/average.py $w/avg @$w/dirs.txt > /dev/null 2>&1
  echo "== $man ($(python -I -X utf8 -c "import json;print(json.load(open('$d/source.json',encoding='utf-8'))['label'][:60])" 2>/dev/null)): $(python -I -X utf8 scripts/skel_match.py $w/avg $S 2>&1 | head -3 | sed 's|work/snap/||g' | awk '{printf "%s %s %s %s | ", $1, $2, $5, $6}')"
done
