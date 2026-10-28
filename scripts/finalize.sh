#!/bin/sh
# Final pass over fonts/ (run after any rebuild):
#  0. stray pieces above the tallest ascender removed (fix_strays.py)
#  1. implausible capital sidebearings -> the Pica's (estimates; see fix_capital_spacing.py)
#  2. Q spaced on O's set width (fix_q.py)
#  3. every italic gets the punctuation and figures it lacks from its roman (period practice)
cd "$(dirname "$0")/.."
for f in fonts/*.otf; do python -I -X utf8 scripts/fix_strays.py "$f"; done
for f in fonts/*.otf; do
  case "$f" in *Titling*) continue ;; *-Italic.otf) qref=fonts/Caslon1734Pica-Italic.otf ;; *) qref=fonts/Caslon1734Pica-Roman.otf ;; esac
  python -I -X utf8 scripts/fix_q.py "$f" 60 "$qref"
done
for f in fonts/*-Roman.otf fonts/*-Italic.otf; do
  case "$f" in *Titling*|*/Caslon1734Pica-*|*/Caslon1734PicaImpression-*) continue ;; esac
  case "$f" in *-Italic.otf) ref=fonts/Caslon1734Pica-Italic.otf ;; *) ref=fonts/Caslon1734Pica-Roman.otf ;; esac
  b=$(basename "$f" .otf | sed -e 's/^Caslon1734//' -e 's/Impression//')
  case "$b" in Brevier-*) k=br;; DoublePica-*) k=dp;; English-*) k=en;; FrenchCannon-*) k=fc;; GreatPrimer-*) k=gp;;
    LongPrimerNo.1-*) k=lp1;; LongPrimerNo.2-*) k=lp2;; SmallPicaNo.1-*) k=sp1;; SmallPicaNo.2-*) k=sp2;;
    TwoLinesEnglish-*) k=tle;; TwoLinesGreatPrimer-*) k=tlgp;; *) k=x;; esac
  case "$b" in *-Italic) k=${k}_italic;; *) k=${k}_roman;; esac
  m=work/${k}_avgS/metrics.json; [ -f "$m" ] || m=work/${k}_avgF/metrics.json
  python -I -X utf8 scripts/fix_capital_spacing.py "$f" "$ref" 150 "$m"
done
# Brevier roman alphabet line: its slid labels (S and T merged on the sheet, so each
# later capital took the previous letter's label) are now corrected at the source,
# before averaging (configs/br_roman.json "relabel"); the old glyph remap and the
# separately averaged S are no longer needed (books supply plenty of S).
for f in fonts/Caslon1734Brevier-Roman.otf fonts/Caslon1734BrevierImpression-Roman.otf; do
  python -I -X utf8 scripts/fix_capital_spacing.py "$f" fonts/Caslon1734Pica-Roman.otf
done
# titling lowercase (Titling 1 and 2: a few letters in 4-7 pairs, too few to measure
# sidebearings): Double Pica roman's, scaled by x-height (estimates)
for f in fonts/Caslon1734Titling*-Roman.otf; do
  python -I -X utf8 scripts/fix_titling_lowercase.py "$f" fonts/Caslon1734DoublePica-Roman.otf
done
# Pica "!" from Epictetus 1741 (5 agreeing impressions; work/pica_excl_avg), spaced like ":"
python -I -X utf8 scripts/insert_glyph.py fonts/Caslon1734Pica-Roman.otf work/pica_excl/pica_excl_clean.otf "!" ":"
python -I -X utf8 scripts/insert_glyph.py fonts/Caslon1734PicaImpression-Roman.otf work/pica_excl/pica_excl_imp.otf "!" ":"
# book-sourced glyphs that do not look like their letter (OCR misreads, mislabels) are removed
for f in fonts/Caslon1734English*-*.otf fonts/Caslon1734GreatPrimer*-*.otf fonts/Caslon1734SmallPicaNo.*-*.otf fonts/Caslon1734LongPrimerNo.*-*.otf fonts/Caslon1734Brevier*-*.otf; do
  case "$f" in *-Italic.otf) ref=fonts/Caslon1734Pica-Italic.otf ;; *) ref=fonts/Caslon1734Pica-Roman.otf ;; esac
  # judge only letters that came from a book, never the sheet's own
  b=$(basename "$f" .otf | sed -e 's/^Caslon1734//' -e 's/Impression//')
  case "$b" in Brevier-*) k=br;; English-*) k=en;; GreatPrimer-*) k=gp;; LongPrimerNo.1-*) k=lp1;; LongPrimerNo.2-*) k=lp2;; SmallPicaNo.2-*) k=sp2;; SmallPicaNo.1-*) k=sp1;; esac
  case "$b" in *-Italic) k=${k}_italic;; *) k=${k}_roman;; esac
  gj=work/${k}_avgS/glyphs.json
  [ -f "$gj" ] || continue
  bl=$(python -I -X utf8 scripts/book_chars.py "$gj" "kwxyzKUVWXYZhj&!'?:;()")
  bf=$(python -I -X utf8 scripts/book_chars.py "$gj" "0123456789")
  [ -n "$bl" ] && python -I -X utf8 scripts/check_plausible.py "$f" "$ref" "$bl" 0.55
  [ -n "$bf" ] && python -I -X utf8 scripts/check_plausible.py "$f" "$ref" "$bf" 0.72   # figures: stricter
done
for f in fonts/Caslon1734English-*.otf fonts/Caslon1734GreatPrimer-*.otf fonts/Caslon1734SmallPicaNo.1-*.otf fonts/Caslon1734SmallPicaNo.2-*.otf fonts/Caslon1734LongPrimerNo.1-*.otf fonts/Caslon1734LongPrimerNo.2-*.otf fonts/Caslon1734Brevier-*.otf; do
  python -I -X utf8 scripts/sync_coverage.py "$f" "$(echo "$f" | sed -e s/-Roman.otf$/Impression-Roman.otf/ -e s/-Italic.otf$/Impression-Italic.otf/)"
done
# book-sourced ligatures that do not look like themselves are set from their own letters
for f in fonts/Caslon1734English*-Roman.otf fonts/Caslon1734GreatPrimer*-Roman.otf fonts/Caslon1734SmallPicaNo.*-Roman.otf fonts/Caslon1734LongPrimerNo.*-Roman.otf fonts/Caslon1734Brevier*-Roman.otf; do
  b=$(basename "$f" .otf | sed -e 's/^Caslon1734//' -e 's/Impression//')
  case "$b" in Brevier-*) k=br;; English-*) k=en;; GreatPrimer-*) k=gp;; LongPrimerNo.1-*) k=lp1;; LongPrimerNo.2-*) k=lp2;; SmallPicaNo.2-*) k=sp2;; SmallPicaNo.1-*) k=sp1;; esac
  [ -f work/${k}_roman_avgS/glyphs.json ] && python -I -X utf8 scripts/check_ligs.py "$f" work/${k}_roman_avgS/glyphs.json fonts/Caslon1734Pica-Roman.otf
done
# Long Primer No. 2 "!": No. 1's sort (same body; the 2 real No. 2 impressions match it, and
# the two founts share their punctuation; scripts/reject_glyphs.json)
python -I -X utf8 scripts/insert_glyph.py fonts/Caslon1734LongPrimerNo.2-Roman.otf fonts/Caslon1734LongPrimerNo.1-Roman.otf "!" "="
python -I -X utf8 scripts/insert_glyph.py fonts/Caslon1734LongPrimerNo.2Impression-Roman.otf fonts/Caslon1734LongPrimerNo.1Impression-Roman.otf "!" "="
# and its apostrophe (the 55 book impressions average to a blob; reject_glyphs.json)
python -I -X utf8 scripts/insert_glyph.py fonts/Caslon1734LongPrimerNo.2-Roman.otf fonts/Caslon1734LongPrimerNo.1-Roman.otf "'" "="
python -I -X utf8 scripts/insert_glyph.py fonts/Caslon1734LongPrimerNo.2Impression-Roman.otf fonts/Caslon1734LongPrimerNo.1Impression-Roman.otf "'" "="
# hand-checked corrections (scripts/overrides.py lists each, with the reason)
python -I -X utf8 scripts/overrides.py
for it in fonts/*-Italic.otf; do
  ro=$(echo "$it" | sed 's/-Italic.otf$/-Roman.otf/')
  [ -f "$ro" ] && python -I -X utf8 scripts/fill_from_roman.py "$it" "$ro"
done
