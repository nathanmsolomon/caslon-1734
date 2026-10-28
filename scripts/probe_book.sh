#!/bin/sh
# Probe a candidate book's type size by its letter proportions.
# Usage: sh scripts/probe_book.sh <ia_id_without_bim_prefix> <page_n> [avg_dir]
# Downloads the OCR layer and 4 pages around <page_n> into source/books/probe/<id>/,
# harvests roman letters, averages them and prints proportions + line pitch.
id=$1; n=$2; avg=${3:-work/sp1_roman_avgF}
full=bim_eighteenth-century_$id
d=source/books/probe/$id; w=work/probe/$id
mkdir -p $d $w
[ -s $d/djvu.xml ] || curl -sL -o $d/djvu.xml "https://archive.org/download/$full/${full}_djvu.xml"
for k in $((n-2)) $((n-1)) $((n+1)) $((n+2)); do
  [ -s $d/n$k.jpg ] || curl -sL -o $d/n$k.jpg "https://archive.org/download/$full/page/n$k.jpg"
  python -I -X utf8 scripts/segment_ocr.py $d/n$k.jpg $d/djvu.xml $k 888 $avg $w/n$k > /dev/null 2>&1
done
ls -d $w/n* > $w/dirs.txt
python -I -X utf8 scripts/average.py $w/avg @$w/dirs.txt > /dev/null 2>&1
echo "== $id"
python -I -X utf8 scripts/proportions.py $w/avg | tail -1
python -I scripts/line_pitch.py $d/n$((n-1)).jpg $d/n$((n+1)).jpg
