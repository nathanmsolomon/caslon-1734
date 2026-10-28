#!/bin/sh
# Sort the harvesters' unresolved ligatures (LIG:xx) in every book harvest, by
# spelling (scripts/relabel_ligs.py), using each size's own font for the ſt test.
# Roman and italic harvests of the same book are sorted with their own style.
cd "$(dirname "$0")/.."
PY="python -I -X utf8"
F=fonts/Caslon1734
sort_() { font=$1; shift; dirs=""; for g in "$@"; do dirs="$dirs $(ls -d work/$g/n* 2>/dev/null)"; done; [ -n "$dirs" ] && $PY scripts/relabel_ligs.py $font $dirs; }
sort_ ${F}English-Roman.otf ebo eboX eboY po k85_en_roman
sort_ ${F}English-Italic.otf eboi eboXi eboYi poi k85_en_italic
sort_ ${F}GreatPrimer-Roman.otf carib caribX caribY dk k85_gp_roman
sort_ ${F}GreatPrimer-Italic.otf caribi caribXi caribYi dki k85_gp_italic
sort_ ${F}SmallPicaNo.2-Roman.otf fd ph k85_sp2_roman
sort_ ${F}SmallPicaNo.2-Italic.otf fdi phi k85_sp2_italic
sort_ ${F}SmallPicaNo.1-Roman.otf pc
sort_ ${F}SmallPicaNo.1-Italic.otf pci
sort_ ${F}LongPrimerNo.1-Roman.otf kh mt k85_lp1_roman lc ge sh sc cb cm sr cp
sort_ ${F}LongPrimerNo.1-Italic.otf khi mti k85_lp1_italic lci gei shi sci cbi cmi sri cpi
sort_ ${F}LongPrimerNo.2-Roman.otf k85_lp2_roman wdb wpo wnh wce
sort_ ${F}LongPrimerNo.2-Italic.otf k85_lp2_italic wdbi wpoi wnhi wcei
sort_ ${F}Brevier-Roman.otf juv eg k85_br_roman
sort_ ${F}Brevier-Italic.otf juvi egi k85_br_italic
sort_ ${F}Pica-Roman.otf rpA cl k85_pica_roman
sort_ ${F}Pica-Italic.otf riC cli k85_pica_italic
sort_ ${F}DoublePica-Roman.otf wgl
sort_ ${F}DoublePica-Italic.otf wgli
