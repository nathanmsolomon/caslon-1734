#!/bin/sh
# Re-run every italic book harvest with the current italic harvester (Oct 23:
# wildcard letters get realistic widths from the Pica italic and keep only their
# main shape, so a following full stop or comma is not taken in). Covers the
# books in reharvest_all.sh, the eight Long Primer No. 1 books, England's
# Gazetteer and the three Latin books (their ae/oe map is applied by
# harvest_latin.py, run by the autopilot afterwards).
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
ITALIC_ONLY=1 sh scripts/reharvest_all.sh > work/reharvest_italic.log 2>&1
H=source/books/probe_hires
it() { id=$1; tag=$2; ppi=$3; slant=$4; iavg=$5; ravg=$6; xh=$7
  for x in work/$tag/n*; do
    n=${x##*/n}; [ -s $H/$id/n$n.jpg ] || continue
    rm -rf ${x}_new
    $PY scripts/segment_ocr_italic.py $H/$id/n$n.jpg $H/$id/djvu.xml $n $ppi $slant $iavg $ravg $xh ${x}_new > /dev/null 2>&1
    if [ -s ${x}_new/instances.json ]; then rm -rf $x; mv ${x}_new $x; else rm -rf ${x}_new; fi
  done
  echo "$tag done" >> work/reharvest_italic.log; }
for b in "ladyscompanionco00lond lci 500" "grammarofenglish00brig gei 500" "selecthymnswitht00wesl shi 500" "scarronidesorvir00cott sci 400" \
         "catalogusbibliot04oxfo cbi 400" "collectionofmost00mendiala cmi 400" "sermonsreligious03dodduoft sri 500" "collectionofpo06dodsuoft cpi 500"; do
  set -- $b; it $1 $2 $3 19.0 work/lp1_italic_avgF work/snap/lp1 35
done
it englandsgazettee02whatiala egi 400 18.5 work/br_italic_avgF work/snap/br 28.5
echo "italic re-harvest (all) done" >> work/reharvest_italic.log
