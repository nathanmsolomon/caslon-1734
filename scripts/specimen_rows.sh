#!/bin/sh
# Display alphabets from Caslon's later specimen books (1764, 1766, 1785), which
# show the 1734 titling cuts with longer alphabets. Each page's rows are cut
# into letters, resampled to the 1734 size, and filed by the titling face they
# match (scripts/titling_match.py; the configs' "specimen" key picks them up).
#   page 4/6/8 in 1764 and 1766 (300 ppi) = pages 12/14/16 in 1785 (500 ppi)
#   Five Lines Pica = Titling 1, Four Lines Pica = 2, Two Lines Great Primer = 3,
#   Two Lines English = 4, Two Lines Pica = 5, Two Lines Long Primer = 6,
#   Two Lines Brevier = 7. Two Lines Double Pica and Two Lines Small Pica are not
#   on the 1734 sheet and are skipped.
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
R4="ABCD|EGHK|abcdeg|ABCDE|FGHIJK|abcdefgh"
R6="ABCDEF|GHIJKL|ABCDEFG|HIJKLMN|ABCDEFGJ|HIKLMNO"
R8="ABCDEFGHIM|JKLNOPQRST|ABCDEFGHIKL|MNOPQRSTUV|ABCDEFGHIJKM|LNOPQRSTUVW|ABCDEFGHIKLMN|OPQRSTUVWXYZJ"
rm -rf work/spec_rows work/spec_t?
for ed in 1764 1766 1785; do
  D=source/specimens_later/$ed; ppi=300; off=0
  [ $ed = 1785 ] && { D=source/specimens_later/1785_uc; ppi=500; off=8; }
  for p in 4 6 8; do
    eval R=\$R$p
    $PY scripts/titling_match.py $D/n$((p + off)).jpg $ppi "$R" work/spec_rows/${ed}_p$p > work/spec_rows_${ed}_p$p.log
  done
done
row() { mkdir -p work/spec_t$3; [ -d work/spec_rows/$1/row$2 ] && cp -r work/spec_rows/$1/row$2 work/spec_t$3/${1}_row$2; }
for ed in 1764 1766 1785; do
  for r in 0 1 2; do row ${ed}_p4 $r 1; done
  for r in 3 4 5; do row ${ed}_p4 $r 2; done
  for r in 2 3; do row ${ed}_p6 $r 3; done
  for r in 4 5; do row ${ed}_p6 $r 4; done
  for r in 0 1; do row ${ed}_p8 $r 5; done
  for r in 4 5; do row ${ed}_p8 $r 6; done
  for r in 6 7; do row ${ed}_p8 $r 7; done
done
for t in 1 2 3 4 5 6 7; do echo "titling$t: $(ls -d work/spec_t$t/* | wc -l) rows"; done
