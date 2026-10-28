#!/bin/sh
# Rebuild the roman sizes whose book ligatures check_ligs.py had wrongly set from
# their letters (component comparison bug, fixed Oct 28), then finalize.
cd "$(dirname "$0")/.."
until grep -q "bang done" work/singles_bang.log 2>/dev/null; do sleep 30; done
for f in en_roman gp_roman sp1_roman sp2_roman lp1_roman lp2_roman br_roman; do python -I -X utf8 scripts/rebuild_fonts.py configs/$f.json | tail -2; done
sh scripts/finalize.sh > work/finalize.log 2>&1
grep -E "ligatures:|removed:|unmapped" work/finalize.log | grep -v "removed: none" | grep -v "stray pieces" | cut -c1-220
echo "relig done $(date)"
