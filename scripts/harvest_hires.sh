#!/bin/sh
# Harvest roman + italic from confirmed high-resolution books (work/hires/harvest_plan.txt:
# "<ia_id> <tag> <xheight> <pages...>"). Book -> 1734 size, ppi below.
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
size_of() { case $1 in fd|ph) echo sp2;; kh) echo lp1;; po) echo en;; pc) echo sp1;; dk) echo gp;; esac; }
ppi_of() { case $1 in fd|ph|pc|dk) echo 400;; kh|po) echo 500;; esac; }
while read id tag xh pages; do
  s=$(size_of $tag); ppi=$(ppi_of $tag); d=source/books/probe_hires/$id
  slant=$(python -I -c "import json;print(json.load(open('configs/${s}_italic.json')).get('slant',18))")
  for n in $pages; do
    [ -s $d/n$n.jpg ] || curl -sL -o $d/n$n.jpg "https://archive.org/download/$id/page/n$n.jpg"
    $PY scripts/segment_ocr.py $d/n$n.jpg $d/djvu.xml $n $ppi work/${s}_roman_avgF work/$tag/n$n $xh > /dev/null 2>&1
    $PY scripts/segment_ocr_italic.py $d/n$n.jpg $d/djvu.xml $n $ppi $slant work/${s}_italic_avgF work/${s}_roman_avgF $xh work/${tag}i/n$n > /dev/null 2>&1
  done
  echo "$id ($tag -> $s) done"
done < ${1:-work/hires/harvest_plan.txt}
