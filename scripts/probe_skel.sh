#!/bin/sh
# Skeleton-test candidate books for a 1734 cut (scripts/skel_match.py).
# Usage: sh scripts/probe_skel.sh <list: "ia_id page ppi" per line> <template avg> <x-height px@600> [pages around page, default 2]
# For each book: fetch the OCR layer and pages page-k..page+k from the Internet
# Archive, harvest roman letters with the template, average them, and print the
# three closest 1734 cuts (skeleton distance in % of x-height, fitted scale).
# A same-cut book gives about 0.5-1.1 % at scale 0.98-1.02 with a clear lead.
# Compares against snapshots in work/snap/ (take them first: the rebuild rewrites
# the live averages).
cd "$(dirname "$0")/.."
LIST=$1; TPL=$2; XH=$3; K=${4:-2}
S="work/snap/en work/snap/pica work/snap/sp1 work/snap/sp2 work/snap/lp1 work/snap/lp2 work/snap/br work/snap/gp work/snap/dp"
tr -d '\r' < $LIST | while read id n ppi; do
  [ -n "$id" ] || continue
  d=source/books/probe_hires/$id; w=work/probe_hires/${id}_k$K; mkdir -p $d $w
  if [ ! -s $d/djvu.xml ]; then
    f=$(curl -s "https://archive.org/metadata/$id" | python -I -c "import json,sys;print(next((x['name'] for x in json.load(sys.stdin)['files'] if x['name'].endswith('_djvu.xml')),''))")
    [ -n "$f" ] && curl -sL -o $d/djvu.xml "https://archive.org/download/$id/$f"
  fi
  i=$((n - K)); while [ $i -le $((n + K)) ]; do
    [ -s $d/n$i.jpg ] || curl -sfL -o $d/n$i.jpg "https://archive.org/download/$id/page/n$i.jpg"
    python -I -X utf8 scripts/segment_ocr.py $d/n$i.jpg $d/djvu.xml $i $ppi $TPL $w/n$i $XH > /dev/null 2>&1
    i=$((i + 1))
  done
  for x in $w/n*; do [ -s $x/instances.json ] && echo $x; done > $w/dirs.txt
  rm -rf $w/avg; python -I -X utf8 scripts/average.py $w/avg @$w/dirs.txt > /dev/null 2>&1
  echo "== $id: $(python -I -X utf8 scripts/skel_match.py $w/avg $S 2>&1 | head -3 | sed 's|work/snap/||g' | awk '{printf "%s %s %s %s | ", $1, $2, $5, $6}')"
done
