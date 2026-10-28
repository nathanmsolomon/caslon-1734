#!/bin/sh
# Collect every face's thinly attested book-only glyphs (1-4 impressions) and make
# a review sheet per face, for the by-eye check (scripts/impression_singles.json).
# Waits for running builds first. Output: work/thinprobe_<face>/review.png
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
running() { powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -match '$1' } | Select-Object -First 1" 2>/dev/null | grep -q python; }
clear=0
while [ $clear -lt 3 ]; do
  if running 'wellcome_harvest|segment_ocr|run_size.py|finalize|relabel_ligs|average.py work/[a-z0-9]*_(roman|italic)'; then clear=0; else clear=$((clear + 1)); fi
  sleep 120
done
avgdir() { case $1 in pica_roman) echo work/pica_roman_avg4;; pica_italic) echo work/pica_italic_avg11;; *) echo work/$1_avgS;; esac; }
refs() { case $1 in br) echo "lp2 lp1";; lp1) echo "lp2 sp1";; lp2) echo "lp1 sp1";; sp1) echo "sp2 lp1";; sp2) echo "sp1 pica";;
                     pica) echo "sp2 en";; en) echo "pica gp";; gp) echo "en dp";; dp) echo "gp en";; esac; }
probe() {
  f=$1; [ -f work/${f}_sources.txt ] || return
  rm -rf work/thinprobe_$f
  CASLON_ONLY_THIN=1 $PY scripts/average.py work/thinprobe_$f @work/${f}_sources.txt > work/thinprobe_$f.log 2>&1
}
FACES="br_roman br_italic lp1_roman lp1_italic lp2_roman lp2_italic sp1_roman sp1_italic sp2_roman sp2_italic pica_roman pica_italic en_roman en_italic gp_roman gp_italic dp_roman dp_italic"
# two at a time
set -- $FACES
while [ $# -gt 0 ]; do
  probe $1 & [ $# -gt 1 ] && probe $2; wait
  shift; [ $# -gt 0 ] && shift
done
for f in $FACES; do
  [ -f work/thinprobe_$f/thin/thin.json ] || { echo "$f: no thin glyphs"; continue; }
  s=${f%_*}; st=${f#*_}; R=""
  for r in $(refs $s); do d=$(avgdir ${r}_$st); [ -f $d/glyphs.json ] && R="$R $d"; done
  $PY scripts/review_singles.py $(avgdir $f) work/thinprobe_$f/review.png $R --thin=work/thinprobe_$f
done
echo "thin review done $(date)"
