#!/bin/sh
# Probe a high-resolution book scan for design match with a 1734 face.
# Usage: sh scripts/probe_hires.sh <ia_identifier> <page_n> <ppi> <sheet_avg_dir>
# Downloads the OCR layer and 4 pages around <page_n> into source/books/probe_hires/<id>/,
# harvests roman letters with that face's templates, averages them and runs
# design_match.py against all sheet faces.
id=$1; n=$2; ppi=$3; avg=$4
d=source/books/probe_hires/$id; w=work/probe_hires/$id
mkdir -p $d $w
if [ ! -s $d/djvu.xml ]; then
  f=$(curl -s "https://archive.org/metadata/$id" | python -I -c "import json,sys;print(next((x['name'] for x in json.load(sys.stdin)['files'] if x['name'].endswith('_djvu.xml')),''))")
  [ -n "$f" ] && curl -sL -o $d/djvu.xml "https://archive.org/download/$id/$f"
fi
for k in $((n-2)) $((n-1)) $((n+1)) $((n+2)); do
  [ -s $d/n$k.jpg ] || curl -sL -o $d/n$k.jpg "https://archive.org/download/$id/page/n$k.jpg"
  python -I -X utf8 scripts/segment_ocr.py $d/n$k.jpg $d/djvu.xml $k $ppi $avg $w/n$k > /dev/null 2>&1
done
ls -d $w/n* > $w/dirs.txt 2>/dev/null
python -I -X utf8 scripts/average.py $w/avg @$w/dirs.txt > /dev/null 2>&1
echo "== $id (screen: $(basename $avg))"
python -I -X utf8 scripts/design_match.py $w/avg work/en_roman_avgF work/pica_roman_avg4 work/sp1_roman_avgF work/sp2_roman_avgF work/lp1_roman_avgF work/lp2_roman_avgF work/br_roman_avgF work/gp_roman_avgF | head -3
