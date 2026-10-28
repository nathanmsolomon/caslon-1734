#!/bin/sh
# Re-run every book harvest with the current harvesters, into the same folders
# (folder names carry the per-book calibration groups). Needed after the Oct 21
# fixes: lines are size-checked against the page's own x-height (the old fixed
# window around the sheet's x-height dropped good lines on heavily inked
# pages), touching letters fall back to forced alignment, and the italic
# harvester now keeps ligatures. Only pages already harvested are redone.
# ITALIC_ONLY=1 redoes only the italic harvests (e.g. after the Oct 23 fix giving
# wildcard letters realistic widths from the Pica italic).
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
H=source/books/probe_hires
JOBS=work/reharvest_jobs.txt; : > $JOBS

# roman: tag | page jpg (N = page index) | djvu | ppi | template avg | x-height px@600
roman() {
  for d in work/$1/n*; do
    [ -d "$d" ] || continue
    n=${d##*/n}; jpg=$(echo "$2" | sed "s/N/$n/")
    echo "R $jpg $3 $n $4 $5 $d $6" >> $JOBS
  done
}
# italic: tag | page jpg | djvu | ppi | slant | italic avg | roman avg | x-height
italic() {
  for d in work/$1/n*; do
    [ -d "$d" ] || continue
    n=${d##*/n}; jpg=$(echo "$2" | sed "s/N/$n/")
    echo "I $jpg $3 $n $4 $5 $6 $7 $8 $d" >> $JOBS
  done
}
for t in ebo eboX eboY; do roman $t source/books/eboracum/b_nN.jpg source/books/eboracum/ebo_djvu.xml 888 work/en_roman_avgF 47; done
for t in eboi eboXi eboYi; do italic $t source/books/eboracum/b_nN.jpg source/books/eboracum/ebo_djvu.xml 888 18.5 work/en_italic_avgF work/en_roman_avgF 47; done
for t in carib caribX caribY; do roman $t source/books/caribbeana/nN.jpg source/books/caribbeana/djvu.xml 862 work/gp_roman_avgF 57; done
for t in caribi caribXi caribYi; do italic $t source/books/caribbeana/nN.jpg source/books/caribbeana/djvu.xml 862 21.5 work/gp_italic_avgF work/gp_roman_avgF 57; done
roman rpA source/books/religious/nN.jpg source/books/religious/religiousphiloso1730nieu_djvu.xml 400 work/pica_roman_avg4 44
italic riC source/books/religious/nN.jpg source/books/religious/religiousphiloso1730nieu_djvu.xml 400 16.5 work/pica_italic_avg11 work/pica_roman_avg4 44
F=factiondetectedb00egmoiala; P=parliamentary23londiala; K=historyofknights01vert; O=generalhistoryof02poly_0; C=parliamentarycon04londiala; D=doctorkingsapolo00king
roman fd $H/$F/nN.jpg $H/$F/djvu.xml 400 work/sp2_roman_avgF 38
italic fdi $H/$F/nN.jpg $H/$F/djvu.xml 400 17.5 work/sp2_italic_avgF work/sp2_roman_avgF 38
roman ph $H/$P/nN.jpg $H/$P/djvu.xml 400 work/sp2_roman_avgF 38
italic phi $H/$P/nN.jpg $H/$P/djvu.xml 400 17.5 work/sp2_italic_avgF work/sp2_roman_avgF 38
roman kh $H/$K/nN.jpg $H/$K/djvu.xml 500 work/lp1_roman_avgF 35
italic khi $H/$K/nN.jpg $H/$K/djvu.xml 500 19.0 work/lp1_italic_avgF work/lp1_roman_avgF 35
roman po $H/$O/nN.jpg $H/$O/djvu.xml 500 work/en_roman_avgF 48
italic poi $H/$O/nN.jpg $H/$O/djvu.xml 500 18.5 work/en_italic_avgF work/en_roman_avgF 48
roman pc $H/$C/nN.jpg $H/$C/djvu.xml 400 work/sp1_roman_avgF 40
italic pci $H/$C/nN.jpg $H/$C/djvu.xml 400 18.0 work/sp1_italic_avgF work/sp1_roman_avgF 40
roman dk $H/$D/nN.jpg $H/$D/djvu.xml 400 work/gp_roman_avgF 57
italic dki $H/$D/nN.jpg $H/$D/djvu.xml 400 21.5 work/gp_italic_avgF work/gp_roman_avgF 57
echo "$(wc -l < $JOBS) pages to re-harvest"

# each job writes to a fresh folder, then replaces the old one (3 at a time)
$PY - $JOBS <<'EOF2'
import sys, os, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
py = [sys.executable, "-I", "-X", "utf8"]
def run(line):
    f = line.split()
    if f[0] == "R":
        _, jpg, xml, n, ppi, avg, out, xh = f
        cmd = py + ["scripts/segment_ocr.py", jpg, xml, n, ppi, avg, out + "_new", xh]
    else:
        _, jpg, xml, n, ppi, slant, iavg, ravg, xh, out = f
        cmd = py + ["scripts/segment_ocr_italic.py", jpg, xml, n, ppi, slant, iavg, ravg, xh, out + "_new"]
    tmp = out + "_new"
    shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(os.path.join(tmp, "instances.json")):
        shutil.rmtree(out, ignore_errors=True); os.replace(tmp, out); return 1
    shutil.rmtree(tmp, ignore_errors=True); return 0
jobs = [l for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
if os.environ.get("ITALIC_ONLY"):     # e.g. after an italic-harvester fix
    jobs = [l for l in jobs if l.startswith("I ")]
with ThreadPoolExecutor(3) as ex:
    ok = sum(ex.map(run, jobs))
print(ok, "of", len(jobs), "pages re-harvested")
EOF2

# the 1785 specimen blocks and the Latin books have their own drivers
[ -n "$ITALIC_ONLY" ] && { echo "italic re-harvest done"; exit 0; }
$PY scripts/harvest_1785.py > work/reharvest_1785.log 2>&1
$PY scripts/harvest_latin.py djuniijuvenalise00juve juv br 500 28.5 60 18.5
$PY scripts/harvest_latin.py mtulliiciceronis00cice mt lp1 500 35 40 19.0
$PY scripts/harvest_latin.py corruptaelatinit00massuoft cl pica 400 44 40 16.5
echo "re-harvest done"
