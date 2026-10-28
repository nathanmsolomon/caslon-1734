#!/bin/sh
# Add the by-eye verified single impressions (scripts/impression_singles.json) to
# every face that has some, rebuild those fonts and finalize. Log: work/singles_all.log
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
one() {
  f=$1
  case $f in pica_roman) A=work/pica_roman_avg4 P=work/pica_roman_avg4;; pica_italic) A=work/pica_italic_avg11 P=work/pica_italic_avg11;;
    *_roman) A=work/${f}_avgS P=work/pica_roman_avg4;; *) A=work/${f}_avgS P=work/pica_italic_avg11;; esac
  $PY scripts/add_singles.py $A work/${f}_sources.txt $P
}
FACES="dp_roman gp_roman gp_italic pica_roman pica_italic br_roman br_italic lp1_italic lp2_italic lp2_roman en_italic en_roman sp1_roman"
set -- $FACES
while [ $# -gt 0 ]; do
  one $1 & p1=$!
  [ $# -gt 1 ] && { one $2 & p2=$!; }
  [ $# -gt 2 ] && one $3
  wait
  shift; [ $# -gt 0 ] && shift; [ $# -gt 0 ] && shift
done
for f in $FACES; do
  case $f in
    pica_roman) for v in clean impression; do sfx=; [ $v = impression ] && sfx=Impression
                  $PY scripts/build.py work/pica_roman_avg4 $v 97.1 fonts/Caslon1734Pica${sfx}-Roman.otf --descent=-262 --extra=work/pica_sc_avg | tail -1; done;;
    pica_italic) for v in clean impression; do sfx=; [ $v = impression ] && sfx=Impression
                  $PY scripts/build.py work/pica_italic_avg11 $v 97.1 fonts/Caslon1734Pica${sfx}-Italic.otf --slant=16.5 --style=Italic --descent=-262 | tail -1; done;;
    *) $PY scripts/rebuild_fonts.py configs/$f.json | tail -2;;
  esac
done
sh scripts/finalize.sh > work/finalize.log 2>&1
grep -E "removed:|unmapped|override" work/finalize.log | grep -v "removed: none" | grep -v "stray pieces" | cut -c1-200
echo "singles done $(date)"
