#!/bin/sh
# Re-average the j of every text face (dot presence + dot registration, average.py
# DOTTED, Oct 28), rebuild the fonts (build.py keeps the i/j dot), finalize.
# Log: work/redo_j_all.log
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
one() {
  case $1 in pica_roman) A=work/pica_roman_avg4;; pica_italic) A=work/pica_italic_avg11;; *) A=work/$1_avgS;; esac
  $PY scripts/redo_chars.py $A work/$1_sources.txt j
}
FACES="br_roman br_italic lp1_roman lp1_italic lp2_roman lp2_italic sp1_roman sp1_italic sp2_roman sp2_italic pica_roman pica_italic en_roman en_italic gp_roman gp_italic dp_roman dp_italic"
set -- $FACES
while [ $# -gt 0 ]; do
  one $1 & [ $# -gt 1 ] && { one $2 & }; [ $# -gt 2 ] && one $3; wait
  shift; [ $# -gt 0 ] && shift; [ $# -gt 0 ] && shift
done
for v in clean impression; do sfx=; [ $v = impression ] && sfx=Impression
  $PY scripts/build.py work/pica_roman_avg4 $v 97.1 fonts/Caslon1734Pica${sfx}-Roman.otf --descent=-262 --extra=work/pica_sc_avg | tail -1
  $PY scripts/build.py work/pica_italic_avg11 $v 97.1 fonts/Caslon1734Pica${sfx}-Italic.otf --slant=16.5 --style=Italic --descent=-262 | tail -1
done
for f in $FACES fc_roman fc_italic tlgp_roman tlgp_italic tle_roman tle_italic; do
  case $f in pica_*) ;; *) $PY scripts/rebuild_fonts.py configs/$f.json | tail -2;; esac
done
sh scripts/finalize.sh > work/finalize.log 2>&1
grep -E "ligatures:|removed:|unmapped|lowercase side|dot" work/finalize.log | grep -v "removed: none" | grep -v "stray pieces" | grep -v "both: none" | cut -c1-220
echo "redo j done $(date)"
