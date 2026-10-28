#!/bin/sh
# Re-add the four italic "!" singles (spaced like the colon), rebuild those fonts, finalize.
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
$PY scripts/add_singles.py work/gp_italic_avgS work/gp_italic_sources.txt work/pica_italic_avg11 &
$PY scripts/add_singles.py work/pica_italic_avg11 work/pica_italic_sources.txt work/pica_italic_avg11 &
wait
$PY scripts/add_singles.py work/lp1_italic_avgS work/lp1_italic_sources.txt work/pica_italic_avg11 &
$PY scripts/add_singles.py work/en_italic_avgS work/en_italic_sources.txt work/pica_italic_avg11 &
wait
for v in clean impression; do sfx=; [ $v = impression ] && sfx=Impression
  $PY scripts/build.py work/pica_italic_avg11 $v 97.1 fonts/Caslon1734Pica${sfx}-Italic.otf --slant=16.5 --style=Italic --descent=-262 | tail -1; done
for f in gp_italic lp1_italic en_italic; do $PY scripts/rebuild_fonts.py configs/$f.json | tail -2; done
sh scripts/finalize.sh > work/finalize.log 2>&1
grep -E "removed:|unmapped|override" work/finalize.log | grep -v "removed: none" | grep -v "stray pieces" | cut -c1-200
echo "bang done $(date)"
