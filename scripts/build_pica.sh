#!/bin/sh
# Pica roman + italic, rebuilt with the current averaging (stain-robust consensus,
# grain matching, Q tails, book calibration). Pica predates run_size.py: its
# sources are the 1734 sheet plus Bowyer's Religious Philosopher (rpA roman, riC
# italic); small caps come from work/pica_sc_avg (estimated spacing, unchanged).
# Run scripts/finalize.sh afterwards (it also inserts the Epictetus "!").
cd "$(dirname "$0")/.."
PY="python -I -X utf8"

# roman
A=work/pica_roman_avg4; rm -rf $A
# Corruptae Latinitatis (work/cl, cli; confirmed as Pica Oct 21) adds æ œ Æ: averaging only
(echo work/pica_roman_p0; echo work/pica_roman_p1; echo work/pica_roman_p2; cat work/rpA_dirs.txt; ls -d work/cl/n* 2>/dev/null | sed 's/^/+/') > work/pica_roman_sources.txt
$PY scripts/average.py $A @work/pica_roman_sources.txt > work/pica_roman_avg4_log.txt 2>&1
$PY scripts/spacing.py $A 7 work/pica_roman_p0 work/pica_roman_p1 work/pica_roman_p2 | head -1
cp $A/metrics.json $A/metrics_1734.json
$PY scripts/spacing.py $A 7 @work/rpA_dirs.txt | head -1
cp $A/metrics.json $A/metrics_book.json
$PY scripts/merge_metrics.py $A 97.1 | tail -1
for v in clean impression; do
  sfx=""; [ $v = impression ] && sfx=Impression
  $PY scripts/build.py $A $v 97.1 fonts/Caslon1734Pica${sfx}-Roman.otf --descent=-262 --extra=work/pica_sc_avg | tail -1
done

# italic
I=work/pica_italic_avg11; rm -rf $I
(cat work/isourcesC.txt; ls -d work/cli/n* 2>/dev/null | sed 's/^/+/') > work/pica_italic_sources.txt
$PY scripts/average.py $I @work/pica_italic_sources.txt > work/pica_italic_avg11_log.txt 2>&1
$PY scripts/spacing.py $I 7 work/ital_al_p0 work/ital_al_p1 work/ital_al_p2 | head -1
cp $I/metrics.json $I/metrics_1734.json
$PY scripts/spacing.py $I 7 @work/riC_dirs.txt | head -1
cp $I/metrics.json $I/metrics_book.json
$PY scripts/merge_metrics.py $I 97.1 | tail -1
for v in clean impression; do
  sfx=""; [ $v = impression ] && sfx=Impression
  $PY scripts/build.py $I $v 97.1 fonts/Caslon1734Pica${sfx}-Italic.otf --slant=16.5 --style=Italic --descent=-262 | tail -1
done
