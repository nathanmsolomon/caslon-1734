# Caslon 1734: processes and materials

Final, Oct 28 2026. README.md keeps the dated working log.

## 1. Aim

A historically faithful reconstruction of the types William Caslon showed on his
specimen sheet of 1734, size by size and cut by cut, built from impressions of the
real type rather than redrawn. Two versions of every face:

- **Clean**: the shape of the type itself, estimated by aligning and averaging many
  impressions.
- **Impression**: one real, typical impression of each sort, as it printed.

Nothing is invented. Characters for which no reliable impressions exist are left out
and listed (section 8). Estimated values (for example letterspaced small capitals)
are marked as estimated.

## 2. Materials

### 2.1 The 1734 specimen sheet (ground truth)
- McGill University Library copy, Internet Archive item
  `McGillLibrary-rbsc_caslon-william-speciman-colgate3-C377C377S51734-17593`,
  600 ppi, three copies of the sheet in one item.
- Every size on the sheet: French Cannon, Two Lines Great Primer, Two Lines English,
  Double Pica, Great Primer, English, Pica, Small Pica No. 1 and No. 2, Long Primer
  No. 1 and No. 2, Brevier (Nonpareil and Pearl dropped: too small for this scan),
  roman and italic, plus seven lines of titling capitals.
- Transcriptions of every block: transcriptions/*.txt.

### 2.2 Caslon's later specimen books (same cuts, more letters)
| Edition | Internet Archive id | ppi | Used for |
|---|---|---|---|
| 1764 | 6073_20220627 | 300 | titling alphabets (pp. 4, 6, 8); Double Pica Roman No. 2 (p. 14) |
| 1766 | 7518_20220627 | 300 | same pages |
| 1785 (University of California copy) | specimenofprinti00caslrich | 500 | titling (pp. 12, 14, 16); text blocks of Great Primer, English No. 2, Pica No. 1, Small Pica No. 2, Long Primer No. 1 and No. 2, Brevier No. 2 |

The 1764/1766/1785 display pages show the 1734 titling cuts under their names
(Five Lines Pica = Titling 1, Four Lines Pica = 2, Two Lines Great Primer = 3,
Two Lines English = 4, Two Lines Pica = 5, Two Lines Long Primer = 6, Two Lines
Brevier = 7), matched at the same size (scale 0.98–1.03, NCC 0.94–0.98).
The 1734 Double Pica is the 1760s "Double Pica Roman No. 2" (0.968 vs 0.919 for No. 1).

### 2.3 Books printed in the same cuts
Each book was confirmed as the same cut (section 4) before any letter was used.
| Size | Book | Source id | ppi | Tag |
|---|---|---|---|---|
| Pica | Nieuwentyt, *The Religious Philosopher* (W. Bowyer, 1730) | religiousphiloso1730nieu | 400 | rpA, riC |
| Pica | *Corruptae Latinitatis* | corruptaelatinit00massuoft | 400 | cl, cli |
| Pica (!) | Epictetus (1741) | (user-supplied PDF) | — | pica_excl |
| English | Drake, *Eboracum* (Bowyer, 1736) | bim_eighteenth-century_eboracum-or-the-history_drake-francis-frs_1736 | 888 | ebo, eboX, eboY, eboi… |
| English | Polybius vol. 2 (J. Hughs for Dodsley, 1761) | generalhistoryof02poly_0 | 500 | po, poi |
| Great Primer | *Caribbeana* (1741) | bim_eighteenth-century_caribbeana-containing-l_1741_2 | 862 | carib… |
| Great Primer | *Doctor King's Apology* (Oxford, 1755) | doctorkingsapolo00king | 400 | dk, dki |
| Small Pica No. 2 | *Faction Detected* (1743) | factiondetectedb00egmoiala | 400 | fd, fdi |
| Small Pica No. 2 | *Parliamentary History* vol. 23 | parliamentary23londiala | 400 | ph, phi |
| Small Pica No. 1 | *Parliamentary History* vol. 4 | parliamentarycon04londiala | 400 | pc, pci |
| Long Primer No. 1 | Vertot, *Knights Hospitallers* (Edinburgh, 1757) | historyofknights01vert | 500 | kh, khi |
| Long Primer No. 1 | *M. Tullii Ciceronis…* | mtulliiciceronis00cice | 500 | mt, mti |
| Long Primer No. 1 | *The Lady's Companion* | ladyscompanionco00lond | 500 | lc, lci |
| Long Primer No. 1 | Brightland, *Grammar of the English Tongue* | grammarofenglish00brig | 500 | ge, gei |
| Long Primer No. 1 | Wesley, *Select Hymns* | selecthymnswitht00wesl | 500 | sh, shi |
| Long Primer No. 1 | Cotton, *Scarronides* | scarronidesorvir00cott | 400 | sc, sci |
| Long Primer No. 1 | *Catalogus Bibliothecae* (Oxford) | catalogusbibliot04oxfo | 400 | cb, cbi |
| Long Primer No. 1 | *Collection of the Most…* | collectionofmost00mendiala | 400 | cm, cmi |
| Long Primer No. 1 | Dodd, *Sermons* vol. 3 | sermonsreligious03dodduoft | 500 | sr, sri |
| Long Primer No. 1 | Dodsley, *Collection of Poems* vol. 6 | collectionofpo06dodsuoft | 500 | cp, cpi |
| Brevier | Juvenal (Latin) | djuniijuvenalise00juve | 500 | juv, juvi |
| Brevier | Whatley, *England's Gazetteer* vol. 2 | englandsgazettee02whatiala | 400 | eg, egi |
| Long Primer No. 2 | Bailey, *Dictionarium Britannicum* (T. Cox, 1736) | Wellcome b30449698 | ≈ 405 | wdb, wdbi |
| Long Primer No. 2 | *Pharmacopoeia Officinalis et Extemporanea* (Longman, 1739) | Wellcome b30534951 | ≈ 495 | wpo, wpoi |
| Long Primer No. 2 | *Nevil-Holt Spaw-Water* (Corbett and Keith, 1749) | Wellcome b30782405_0001 | ≈ 495 | wnh, wnhi |
| Long Primer No. 2 | *A Complete English Dispensatory* (Hitch and Hawes, 1756) | Wellcome b30540835 | ≈ 513 | wce, wcei |
| Double Pica | Glynn, *The Day of Judgment* (Cambridge, J. Bentham, 1757) | Wellcome b31871872 | ≈ 405 | wgl, wgli |

Wellcome Collection images are full-resolution greyscale (IIIF) with Tesseract ALTO
OCR; no scan resolution is recorded, so it is taken from the screen's scale and each
book is calibrated again in averaging. The four Long Primer No. 2 books side with
No. 2 on the two-source letters (e, m, u, c: 4/4, 3/4, 4/4, 4/4; a known No. 1 book
gives 0/4).

Harvest page lists: work/hires/*plan*.txt; downloaded pages: source/books/.
Knights Hospitallers (Edinburgh, where close Caslon copies were cast) was checked
against the eight London/Oxford books: 0.45–0.71 % skeleton distance, the same range
as the London books among themselves, so it is the same cut.

### 2.4 Searched and rejected (summary)
- About 1,300 Internet Archive pages (1730–75, ≥ 400 ppi, no microfilm), 494 folio
  pages, 1,885 Wellcome Collection pages, 40 magazine pages, ~150 Latin books.
- Long Primer No. 2: about 60 Internet Archive candidates were all No. 1 (King Lear,
  Cruden and others decided on the two-source letters); the four confirmed books came
  from the Wellcome Collection.
- Double Pica: folio "hits" were Great Primer under a wrong catalogue resolution;
  Pope, *Horace Imitated* (1737) rejected (1.10 %, scale 0.96: another founder's type);
  Glynn's *Day of Judgment* (Wellcome) confirmed at 0.40 %, scale 1.004.
- Sources found unusable: Google Books (≈ 150–200 ppi or bitonal PDFs), HathiTrust
  (bot-verification on images), blurred microfilm magazines.

## 3. Pipeline (scripts/)
1. **Sheet segmentation** (run_size.py per configs/<size>.json): blocks cut from the
   sheet, letters located by forced alignment against the transcription, each ink
   pixel given to a letter (segment_align.py).
2. **Book harvests**: OCR word boxes (Internet Archive djvu.xml, or Wellcome ALTO via
   wellcome_fetch.py) → letters. Roman: segment_ocr.py (ink blobs, repair of touching
   letters, forced-alignment fallback; lines size-checked against the page's own
   x-height). Italic: segment_ocr_italic.py (page sheared upright, forced alignment;
   letters without a template get widths from the Pica italic and keep only their main
   shape). Long s is decided by template; ligatures are sorted by spelling
   (relabel_ligs.py: English word list, Latin Hunspell dictionary).
3. **Averaging** (average.py): impressions registered, outliers rejected, book
   impressions calibrated per book for size and weight, joint elastic alignment
   ("congealing": each impression gently warped towards the shared shape, smoothing
   wider than a stroke so weight cannot change; kept, see section 6), consensus rules
   for 2–3 impressions. Detached parts that move relative to the body are registered
   on their own and joined back: the Q's tail and the j's dot (a j impression without
   a detached dot is a misread long s or f and is dropped). Glyphs that pass the rules
   but were judged unreliable by eye are listed, with reasons, in
   scripts/reject_glyphs.json.
   Book-only characters with 1–4 impressions are saved for review (`<avg>/thin/`,
   review_singles.py) instead of being discarded silently.
4. **Spacing** (spacing.py): sidebearings solved from how neighbouring letters abut,
   per copy and line; book spacing mapped onto the sheet's (merge_metrics.py).
5. **Building** (build.py): traced at the ink area measured on real impressions;
   Impression version from one typical real impression (unwarped).
   For release (make_release.sh): name records and Windows header fields
   (release_names.py), and TrueType-outline copies for Microsoft Word, which lays out
   CFF fonts in Calibri (make_ttf.py: cu2qu, 1-unit tolerance, ink change at most
   0.65 %).
6. **Finishing** (finalize.sh): stray pieces, Q width, capital sidebearings, the
   plausibility check of book-only characters (check_plausible.py, with
   plausible_keep.json for characters confirmed by eye), italic punctuation from the
   roman, coverage synchronised between clean and Impression, the ligature check
   (check_ligs.py), titling lowercase spacing (fix_titling_lowercase.py), and the
   hand-checked corrections in overrides.py (each listed there with its reason).
7. Whole run: rebuild_all.sh; unattended chain: autopilot.sh. Partial re-runs that
   leave everything else as it is: rebuild_fonts.py (fonts from existing averages),
   redo_chars.py (re-average a few characters), add_singles.py (verified singles,
   section 5), then finalize.sh.

## 4. How a source is confirmed
- **Screen** (screen_all.py): template correlation over a page at the expected scale
  (blank-paper windows ignored).
- **Skeleton test** (skel_match.py / probe_skel.sh / probe_wellcome.sh): averaged
  letters reduced to centrelines and compared by chamfer distance after scaling to the
  sheet's x-height. Same cut: 0.5–1.1 % at scale 0.98–1.02 with a clear lead.
- **No. 1 vs No. 2**: judged only on letters where both the 1734 sheet and the 1785
  specimen agree on the difference (e, m, u, c). The a is excluded: the sheet's Long
  Primer No. 2 block is heavily inked and its a misleads.
- **Display sizes**: titling_match.py, at the scale implied by the scan resolution.

## 5. Rules and decisions
- The 1734 sheet is the ground truth for shape and weight; books and later specimens
  supply letters the sheet lacks and strengthen letters seen ≤ 3 times on the sheet.
- A letter from books alone needs ≥ 5 agreeing impressions and must pass the
  plausibility check.
- **Verified singles (Impression fonts only).** Five agreeing impressions are needed
  to *average* a letter; one real impression is enough to *show* one, provided it is
  certainly that letter of that fount. Book-only letters seen 1–4 times were
  therefore reviewed by eye (each candidate beside the same letter in the
  neighbouring sizes and two letters of its own face; review_singles.py). The 29
  accepted are listed in scripts/impression_singles.json with the impression chosen;
  they appear only in the Impression fonts, never in the clean ones. Their spacing
  cannot be measured from one impression and is estimated: a ligature takes its first
  letter's left and last letter's right sidebearing; other letters take the Pica's
  sidebearings scaled to their ink width; an italic "!" is spaced like the face's
  colon (the Pica "!" practice). Rejected candidates (recorded in the same file's
  `_note`): Double Pica italic S V x (fragments), Brevier and Pica "Œ" (O alone),
  "Æ" (bare A), Long Primer No. 1 italic œ (æ), Great Primer roman ſb (o), Long
  Primer No. 1 ffi roman and italic (italic sorts; wrong fount), Small Pica No. 1
  italic and Pica roman ffi (neighbour's ink), Small Pica No. 2 italic fl, Brevier
  italic ffl and fl, Long Primer No. 2 italic ffl (not that character).
- A mislabelled ligature is taken out rather than kept: all seven Pica "ſb" book
  impressions are ſt (OCR label), so ſb is removed from the Pica's ligature
  substitutions (overrides.py "unlig").
- Spacing that cannot be measured is estimated and said to be: capital left sides
  from the Pica (fix_capital_spacing.py), titling lowercase from the Double Pica
  scaled by x-height (fix_titling_lowercase.py), singles as above.
- Later Caslon specimens (1764–85) count like sheet copies (same foundry, same cuts).
- Small capitals: only sizes with a near-full set (Pica, Great Primer, English,
  Long Primer No. 1); spacing estimated from the capitals.
- Nothing after 1785 is used: the foundry recut its Old Face in 1893–1908
  (Mosley, "Recasting Caslon Old Face").
- French Cannon: its roman lowercase is Joseph Moxon's late-17th-century type, shown
  by Caslon with his own capitals (Mosley).

## 6. Quality checks
- **Fidelity** (fidelity.py: median IoU of the clean font's glyphs against each of the
  sheet's own impressions, measured exactly as one impression against another; the
  baseline is impression against impression). Every face beats its baseline:

  | Face | Roman: font / baseline | Italic: font / baseline |
  |---|---|---|
  | French Cannon | 0.920 / 0.897 | 0.922 / 0.891 |
  | Two Lines Great Primer | 0.916 / 0.899 | 0.911 / 0.887 |
  | Two Lines English | 0.909 / 0.884 | 0.906 / 0.876 |
  | Double Pica | 0.899 / 0.884 | 0.900 / 0.873 |
  | Great Primer | 0.890 / 0.872 | 0.876 / 0.846 |
  | English | 0.870 / 0.835 | 0.857 / 0.820 |
  | Pica | 0.868 / 0.833 | 0.831 / 0.731 |
  | Small Pica No. 1 | 0.845 / 0.803 | 0.839 / 0.785 |
  | Small Pica No. 2 | 0.845 / 0.809 | 0.845 / 0.806 |
  | Long Primer No. 1 | 0.849 / 0.811 | 0.842 / 0.787 |
  | Long Primer No. 2 | 0.846 / 0.795 | 0.832 / 0.786 |
  | Brevier | 0.850 / 0.810 | 0.836 / 0.784 |

  Titling 1–7 (one impression per sheet copy, so no baseline): 0.947, 0.937, 0.935,
  0.920, 0.900, 0.926, 0.911. The lowest single letters are listed per face in
  work/<face>_result.json; the very low ones are letters the sheet shows once or
  twice with a varying descender (J, j) or a ligature the sheet barely shows, not
  wrong glyphs (each was looked at). Fidelity rewards resemblance to blurred
  impressions, so it is not the only test.
- **Ligature check** (check_ligs.py): every book-sourced ligature is compared with the
  Pica's, or, where the Pica has none, with this face's own letters set on their own
  advances (as the compositor would set them without the sort). Below 0.6 it is set
  from its letters instead. Verified singles are exempt (they were judged by eye; a
  true ffl's joined hoods never resemble the separate letters).
- **Held-out test** (holdout_test.py): one source at a time (each sheet copy, the 1785
  block) is held out, letters are averaged from the rest with and without congealing,
  and both are scored against the unseen impressions (weight matched, shape only).
  Result: a tie (Small Pica No. 2: 0.8510 plain vs 0.8506 congealed; Long Primer No. 2:
  0.8329 vs 0.8335). Congealing does not cost accuracy and gives sharper letters, so it
  is kept for the clean fonts; the Impression fonts use unwarped impressions.
- **Truncation audit** (audit_truncation.py): each harvested letter's ink extent
  against the expected extent of that letter in that size. Sheet sources: under 4 %
  short, mostly under 1 %. Books: 1–13 %, almost all thin letters (i, l, r) narrowed by
  lighter inking, j without its offset dot, and kerned italic f/ſ trimmed; these
  letters come from the sheet, so they do not reach the fonts. Run after every harvest.
- **Plausibility check** of book-only characters against the Pica (finalize.sh);
  characters checked by eye are listed with reasons in scripts/plausible_keep.json.

## 7. Fixes found by checking (Oct 21–23)
- Line size gate relative to the page (heavily inked pages lost whole lines).
- Screen: blank-paper windows gave spurious perfect scores.
- Small caps: capitalised nouns ("Law", "Town") taken for small caps.
- Italic: wildcard letters cut short (w at a third of its width); trailing punctuation.
- Brevier: alphabet-line labels corrected at source (S and T had merged).
- Display rows resampled to the 1734 size before averaging (editions differ by ±3 %);
  registration allowed to move large letters further (5 % of their height).
- The old Brevier glyph remap moved correctly labelled book capitals into wrong slots
  once books supplied them; replaced by relabelling the sheet line at the source.
- Small-caps score: a missing lowercase template counted as a certain mismatch.
- Long Primer No. 1 vs No. 2: the a looked decisive but comes from one heavily inked
  block; the comparison now uses only letters confirmed by two independent sources.
- Specimen sources: unsorted ligature labels reached the font builder (now skipped).

## 7a. Fixes found by checking (Oct 24–28)
- Double Pica italic: Glynn's italic gave only 13 letters, too few to calibrate
  spacing (merge_metrics failed); the italic is built from the sheet alone.
- Plausibility false alarms judged by eye and kept (plausible_keep.json): Long Primer
  No. 2 roman 3 5, italic w; Great Primer italic "!" (sloped, wider than the
  reference). The check now skips verified singles in the Impression fonts
  altogether: it had also removed the English and Long Primer No. 1 italic "!".
- Italics now also borrow the roman full stop and apostrophe where the italic fount
  shows none (fill_from_roman.py; Great Primer, English, Double Pica italic had no
  full stop). A Long Primer No. 2 roman "!" was correctly removed (a misread l).
- **Ligature check bug.** Where the Pica had no ligature to compare with, the
  comparison row was built from the letters with their full render margins, ~2.7 ×
  the ligature's width, so every such ligature scored 0 and was replaced by its
  letters: all book ffi, ffl and ſk in English, Great Primer, Small Pica, Long Primer
  and Brevier since the check was written. Fixed (letters set on their own advances)
  and the romans rebuilt; the real ligatures are back. Still set from letters, on
  merit: Brevier Impression ct (0.56), Long Primer No. 1 Impression ſſi (a stray from
  the line above, fix_strays.py).
- **The j's dot.** It sits a little differently on each impression, so averaging
  spread it into a faint blur: the clean Brevier roman j lost its dot (dropped as a
  speck by the density rule), and the clean Great Primer italic j's blurred dot fused
  into a hook that made it look like a long s. The j is now averaged with its dot
  registered separately, and only impressions with a detached dot are kept (whenever
  at least two have one): book OCR reads the italic long s and f as j, often more
  often than real j's. Dropped as misreads: 12 of 26 in the Great Primer italic, 27 of
  88 in the Brevier roman, 152 of 189 in the Pica italic (whose clean j had been a
  long s too). The builder also keeps an i or j dot even when its mean density is low.
- **Brevier italic j removed.** Book-only; 292 of its 318 "j" impressions have no dot
  (misread long s) and the other 26 show fragments, not a dot, above a smeared stem.
  Judged unreliable by eye and listed in scripts/reject_glyphs.json, which average.py
  honours (a wrong glyph is worse than a missing one).
- **Titling lowercase spacing.** Titling 1 and 2 show their few lowercase letters in
  only 4–7 pairs: the solver could fix the gap between neighbours but not how to
  split it, and gave d, g, h large negative sidebearings (Titling 1 c d e g touched).
  Now estimated from the Double Pica roman, scaled by x-height.
- Pica "ſb": all seven book impressions labelled ſb are ſt (OCR); removed from the
  ligature substitutions.
- **Second look at the gaps (user's questions, Oct 28).** Each missing character was
  traced back through harvest, averaging and the checks:
  - English roman 0: 32 impressions, all from all-figure words; a genuine old-style
    zero rejected only for resembling a capital O. Restored (plausible_keep.json).
  - Small Pica No. 2 roman 3 5 ! ( (and so the italic's, borrowed from it): genuine in
    average and impression, false alarms of the plausibility check. Restored. Small
    Pica No. 1: 5 7 restored; its 3 6 9 averages mixed in other misread figures (one
    book, Parliamentary History vol. 4), so each of their 41 impressions was judged by
    eye and pairs, fragments, a 2 and smaller figures were set aside
    (scripts/label_fixes.json, applied by apply_label_fixes.py): 3 6 9 re-averaged from
    9, 9 and 5 impressions and restored. (Automatic sorting against the Small Pica No. 2
    figures was tried first and was not reliable enough.)
  - Brevier roman z: 47 impressions, a clear z, not the misread 2 an earlier note
    assumed. Restored.
  - Long Primer No. 2 "!": of 19 book "!" only 2 are real (the rest misread t and l);
    those 2 match Long Primer No. 1's "!" in height and shape, and the two founts'
    punctuation agrees closely (; : , & ( ) at 0.93–0.97, against 0.68–0.91 between
    different bodies): the founts shared their punctuation sorts, so No. 1's "!" is set
    (finalize.sh; the bogus average is in reject_glyphs.json).
  - Long Primer No. 2 apostrophe: half its 80 book impressions were misread letters
    standing on the baseline, which sank the agreement. Raised marks are now filtered
    by position (average.py RAISED: the mark's foot must stand well above the
    baseline); 63 kept, but these faint Wellcome impressions still averaged to a
    shapeless blob (no ball and tail), so, as with the "!", Long Primer No. 1's
    apostrophe is set, with its own spacing (insert_glyph.py "=").
  - Long Primer No. 2 italic hyphen: italics now borrow the roman hyphen too.
  - Small Pica No. 1 "!" and "(": borrowing No. 2's was considered (their punctuation
    shapes agree), but the shape score is size-normalised; measured directly, No. 1's
    genuine "!" (55 px) and "(" (70–76 px) are 5–10 % smaller than No. 2's (60–62,
    75–80 px), at a book scale of exactly 1.000: different sorts, so nothing is
    borrowed. (For Long Primer the heights match: 54 against 55 px.) Instead, of 73
    book "(" the 13 real ones were chosen by eye (the rest misread ft) and averaged:
    "(" restored. All 8 book "!" are l: Small Pica No. 1 "!" stays missing.
  - Great Primer X: the harvester takes capitals only from words, so Roman numerals
    were never collected; but searching both books' full OCR found no text-size X at
    all: the only candidates ("Mr. X.", Caribbeana pp. 372–373) are italic K's
    misread. X is genuinely unattested in the confirmed sources.
- **Degenerate spacing (found Oct 29 while making the reference documents).** Glyphs
  measured from only one pair got a 1:2 split of a negative gap from the spacing solver
  and overprinted their neighbours: Pica roman g (advance 140 units against 478 of ink),
  æ, œ; Small Pica No. 2 æ; Brevier Æ; English ſſi. fix_degenerate_spacing.py now
  re-estimates any glyph measured from at most 2 pairs whose advance is under half its
  ink: ligatures and æ œ Æ Œ from their components' sidebearings, other letters from a
  sibling size's proportions. It runs after every spacing merge (run_size.py,
  build_pica.sh).
- **Windows font headers (Oct 28).** Roman and italic shared one CFF font name, the
  italics' head.macStyle said upright, and no code page was declared: Windows apps
  substituted another font and drew the italic for the roman. Fixed in
  release_names.py.
- Brevier J, Pica ij, Titling 1 G–H, Titling 6 M, Small Pica No. 2 g and apostrophe:
  checked by eye, no change needed.

## 8. What each face contains, and what is missing

Generated from the fonts (scripts/coverage_report.py) against the standard set: A–Z
Æ Œ, a–z æ œ ſ, figures, . , ; : ? ! ' - ( ) &, and the ligatures ff fi fl ffi ffl ſt
ſi ſſ ſſi ſh ſk ſl ct. "Impression only" are verified single impressions (section 5).
Italic fonts carry their roman's . ' ; : ! ? ( ) & and figures where the italic
fount shows none (period practice for ; : ! ( ) and figures; the full stop and
apostrophe do not differ between roman and italic); those count as present. Small capitals (Great Primer,
English, Pica, Long Primer No. 1 romans) are not listed.

| Font | Missing (both versions) | In the Impression version only |
|---|---|---|
| French Cannon roman | all but these 18: C Q a b d e i l m n o q r t u ſ , - | — |
| French Cannon italic | all but these 21: C Q a b d e i l m n o p q r t u ſ , ? - ſt | — |
| Two Lines Great Primer roman | all but these 21: C Q a b d e i l m n o p q r s t u ſ , ? ſt | — |
| Two Lines Great Primer italic | all but these 23: C Q a b d e f i l m n o p q r s t u ſ , ? - ſt | — |
| Two Lines English roman | all but these 23: C Q a b d e f i l m n o p q r s t u ſ , ? - ſt | — |
| Two Lines English italic | all but these 23: C Q a b d e f i l m n o p q r s t u ſ , ? - ſt | — |
| Double Pica roman | X Z Æ Œ æ œ 0 1 2 3 4 6 7 8 9 ' & ffl ſſ ſſi ſl | U Y z fl ffi ſk |
| Double Pica italic | P R S T U V W X Y Z Æ Œ g h k v w x y z æ œ 0 1 2 3 4 6 7 8 9 ' & fl ffi ffl ſi ſſ ſſi ſh ſk ſl ct | — |
| Great Primer roman | X Æ Œ œ ſk | Z ffl ſl |
| Great Primer italic | X Æ Œ œ ffi ffl ſſ ſſi ſh ſk ſl | U Z |
| English roman | Æ Œ œ ffl ſk | — |
| English italic | X Z Æ Œ œ ffi ffl ſſ ſh ſk ſl | fl |
| Pica roman | Æ Œ ffi | ffl ſk |
| Pica italic | Æ Œ æ œ fi ffi ſh ſk ſl ct | ffl |
| Small Pica No. 1 roman | Æ Œ æ œ ! ffl | fl ſk |
| Small Pica No. 1 italic | Æ Œ æ œ ! ff fl ffi ffl ſſi ſh ſk ſl | — |
| Small Pica No. 2 roman | Æ Œ œ ffl | — |
| Small Pica No. 2 italic | Æ Œ œ ff fl ffl ſh ſk ſl | — |
| Long Primer No. 1 roman | Œ œ ffi | — |
| Long Primer No. 1 italic | Œ w œ ff fl ffi ffl ſſi ſh ſk ſl | — |
| Long Primer No. 2 roman | Œ œ ffl | ffi |
| Long Primer No. 2 italic | Œ œ ff fl ffl ſh ſk ſl | ſſi |
| Brevier roman | Œ | ffl ſk |
| Brevier italic | Œ h j w z œ ff ffl ſh ſk ſl | ffi ſſi |
| Titling 1 | all but these 8: A B C D E G H K | — |
| Titling 2 | all but these 11: A B C D E F G H I J K | — |
| Titling 3 | O P Q R S T U V W X Y Z Æ Œ | — |
| Titling 4 | P Q R S T U V W X Y Z Æ Œ | — |
| Titling 5 | U V W X Y Z Æ Œ | — |
| Titling 6 | X Y Z Æ Œ | — |
| Titling 7 | Æ Œ | — |

Where the gaps come from:
- **Display sizes** (French Cannon, Two Lines Great Primer, Two Lines English): the
  sheet shows each in a line or two of *Quousque tandem*, and no later specimen or
  book has yet been confirmed in these cuts. French Cannon's lowercase is Joseph
  Moxon's type (section 5).
- **Titling**: capitals from the sheet's lines and the 1764/1766/1785 display pages;
  Titling 1 and 2 show only the first part of the alphabet anywhere.
- **Double Pica**: one confirmed book (Glynn 1757, roman only); its italic is from the
  sheet alone.
- **Æ Œ œ** and some figures: rare in the confirmed books; the candidates found were
  other letters (section 5, rejected singles).
- **Italic ligatures** (ff, fl, ſh, ſk, ſl…) in the smaller sizes: rarely on the
  sheet, and book italic ligatures were mostly misread or too few.
- **Removed on checking**: Brevier italic h w z j, Long Primer No. 1 italic w,
  English italic Z, Small Pica No. 1 ! (all misread l): OCR misreads or impressions
  that do not look like the letter (finalize.log; check_plausible.py; reject_glyphs.json).
- **Great Primer X**: no text-size X in either confirmed book (section 7a).

## 8a. Reference documents
specimen/reference/ holds every font at its true size, each setting the 1734 sheet's
passage for its size, with its character set and what it lacks: a Word document with
the TrueType fonts embedded, an IDML for InDesign, and a PDF of each program's own
rendering. make_reference_docs.py writes them; reference_word.ps1 (Word embeds the
fonts and exports the PDF) and reference_indesign.vbs/.jsx (InDesign checks fonts and
overset text, saves the .indd, exports the PDF) finish them. InDesign was checked to
output the OpenType fonts correctly. In both, characters a font lacks are set in
another typeface (Cambria, Minion Pro), never in Caslon. The InDesign document with
its fonts in a Document Fonts folder is a Release download.

## 9. Reproducing
`sh scripts/rebuild_all.sh` (after any harvest change: `sh scripts/relabel_all.sh`
first). Harvests: reharvest_all.sh, italic_reharvest_all.sh, specimen_rows.sh,
harvest_latin.py, smallcaps_size.sh. Scans: `python -I scripts/fetch_sources.py`
(sources_manifest.json lists every page used). Setup, partial rebuilds and adding
sources: EXTENDING.md. Built with Python 3.14; the Kraken OCR engine was tested and
not used.
