#!/bin/sh
# Rebuild every font from the current harvests and averaging, then finish them.
# Uses each size's existing sheet segmentation (run_size.py --reuse), so it is
# the step to run after re-harvesting books, changing average.py/build.py, or
# adding sources to a config ("supp" = books, "specimen" = Caslon's later
# specimen books, "extra" = small capitals). Order:
#   1. every run_size.py size (2 at a time), titling included
#   2. Pica (scripts/build_pica.sh; it predates run_size.py)
#   3. scripts/finalize.sh (strays, Q width, capital spacing, checks; idempotent)
# Run scripts/relabel_all.sh first if any harvest was redone.
cd "$(dirname "$0")/.." || exit 1
L="gp_roman gp_italic en_roman en_italic dp_roman dp_italic sp2_roman sp2_italic sp1_roman sp1_italic lp1_roman lp1_italic lp2_roman lp2_italic br_roman br_italic fc_roman fc_italic tlgp_roman tlgp_italic tle_roman tle_italic titling1 titling2 titling3 titling4 titling5 titling6 titling7"
echo $L | tr ' ' '\n' | xargs -P 2 -I{} sh -c 'python -I -X utf8 scripts/run_size.py configs/{}.json --reuse > work/{}_reuse.log 2>&1'
sh scripts/build_pica.sh > work/build_pica.log 2>&1
sh scripts/finalize.sh > work/finalize.log 2>&1
echo "== summary (fidelity: font vs impression, then impression vs impression)"
for c in $L; do
  printf '%-12s ' "$c"
  grep -E 'IoU median|step failed|Traceback' "work/${c}_reuse.log" | tr -d '\n' | sed 's/  */ /g' | cut -c1-140
  echo
done
tail -n 3 work/build_pica.log
grep -c . work/finalize.log
