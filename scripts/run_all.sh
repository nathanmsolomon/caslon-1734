#!/bin/sh
# Re-run every sheet size with the current pipeline, 3 at a time.
# Phase A has no dependencies on other new results; phase B (the large sizes)
# borrows templates from the Double Pica results of phase A.
cd "$(dirname "$0")/.." || exit 1
run() { python -I -X utf8 scripts/run_size.py "configs/$1.json" > "work/$1_run.log" 2>&1; echo "done $1"; }
export -f run 2>/dev/null
A="gp_roman gp_italic dp_roman dp_italic sp1_roman sp2_roman sp1_italic sp2_italic lp1_roman lp2_roman lp1_italic lp2_italic br_roman br_italic np_roman np_italic pr_roman pr_italic titling1 titling2 titling3 titling4 titling5 titling6 titling7"
B="fc_roman tlgp_roman tle_roman fc_italic tlgp_italic tle_italic"
for phase in "$A" "$B"; do
  echo $phase | tr ' ' '\n' | xargs -P 3 -I{} sh -c 'python -I -X utf8 scripts/run_size.py configs/{}.json > work/{}_run.log 2>&1; echo "done {}"'
done
echo "== summary"
for c in $A $B; do
  printf '%-12s ' "$c"
  grep -E '"pitch_px"|IoU median|lowest|step failed' "work/${c}_run.log" | tr -d '\n' | sed 's/  */ /g'
  echo
done
