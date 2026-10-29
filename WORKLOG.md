# Caslon 1734: reconstruction from William Caslon's first specimen sheet

## Source
McGill University Library, Colgate Collection, *A Specimen* (1734). Internet Archive item
`McGillLibrary-rbsc_caslon-william-speciman-colgate3-C377C377S51734-17593`, 600 ppi, public domain.
The item holds **three separate copies** of the sheet (pages 0–2). The copies carry the Cyclopaedia
note "to be placed in the Middle of the Sheet 5 U u, Vol. II", but the type is the same.

## Pipeline (scripts/)
1. `segment.py`: binarize a block, find lines, group components into glyphs, split the line into words, and label each glyph from
   `transcriptions/*.txt` (ligature sorts written in {braces}). It repairs specks, broken letters and touching letters,
   fits a sloped baseline per line, and writes `instances.json` plus crops.
2. `average.py`: convert to ink density per copy, upsample 4×, derotate, place on the baseline, align to the class mean with sub-pixel accuracy,
   reject outliers (NCC), and write `avg_*` (mean), `inst_*` (most typical single impression) and the target ink area.
3. `spacing.py`: metal bodies abut, so `inkleft(B) − inkleft(A) = r_A + lsb_B`. Least squares over every neighbour
   pair on all copies; gauge fixed by symmetric lowercase. Capitals seen only in the spaced alphabet line get a weak shape prior.
   Q→R is excluded because Q's tail is a kern; pairs before : ; ? ! are excluded because compositors added a thin space there.
4. `build.py`: trace with potracer (threshold chosen so ink area = the real impressions' mean). 1000 units = the measured
   Pica body (line pitch 97.1 px at 600 ppi = 0.162 in; Moxon gives 0.160 in). Q body = O body. `liga` covers ſi ſt ſſi; `hist` gives long s.
5. `proof.py` (overlay, optional `align`), `fidelity.py` (like-for-like IoU), `setline.py` (text rendering).

## Pica Roman, v0.1 results
- 974 impressions (3 copies); 712 of 729 neighbour pairs used, spacing rms 1.1 px (about 11 units).
- Font vs real impression IoU **0.874**, against real impression vs real impression **0.833**.
- Placement scatter of real sorts is about 1.5 px horizontal and 1 px vertical.

## v0.2: missing glyphs from a 1730 book (Oct 12 2026)
Supplementary source: Nieuwentyt, *The Religious Philosopher*, printed by **William Bowyer**, London 1730
(Princeton Theological Seminary copy, IA `religiousphiloso1730nieu`, 400 ppi). Bowyer was one of Caslon's backers.
- **Screening** (`screen.py`): the 1734 average templates are slid over the page at a sweep of scales. This book matched at
  scale 1.00 with NCC 0.958, against 0.964 for the 1734 Pica on itself and 0.931 for 1734 Small Pica. Rejected: *British Apollo*
  (Bettenham 1740, Long Primer leaded, 0.78), Cheselden *Anatomy* (Bowyer 1741, ~1.08, 0.90). Possible: *Impartial Examination* (0.97, 0.91).
- **Harvest** (`segment_ocr.py`): the IA OCR layer (djvu.xml) gives words and boxes for the 50 pages richest in target glyphs.
  Pages are resampled to 600 ppi. Filters: count match, letters only from all-letter words and figures only from figure tokens,
  roman check against the 1734 templates (drops italics), and a line x-height gate at 44 px ±5% (drops the smaller preface/notes type).
  ſ vs f is re-decided by shape. Ligatures were clustered (`cluster_ligs.py`), checked by eye, and ff/ſſ and fi/ſi split by a crossbar measure.
- **Averaging**: book instances are used **only** for glyphs absent from the 1734 sheet (`+dir` = supplementary).
- **Spacing**: the book is set about 6% looser than the specimen and noisier (rms 1.9 px against 1.1). The 1734 metrics are kept
  for sheet glyphs. New glyphs are mapped by a linear fit over shared lowercase (`merge_metrics.py`, rms 1.7 px ≈ ±18 units).
  Figures sit on an en (500 units), which the book also measures (0.49–0.52 em). Thinly measured ligatures get their own ink plus the
  first/last component's sidebearings.
- **Fidelity of new glyphs** vs book impressions: 0.838 against 0.782 for impression vs impression; every class beats its own impressions.

## v0.3: completing the roman (Oct 12 2026)
- Harvest widened to 150 pages of the Bowyer book (`work/rpA`, 4 pages in parallel). A lone ? ! ; : is now its own token,
  and the glyph built from two stacked parts is picked out of the OCR's loose box. Many questions in this book are italic
  quotations, so they are correctly rejected by the roman check.
- Ligature labels from the two reviewed cluster rounds are re-applied by identical crop bytes (`restore_labels.py`).
  The earlier rounds silently lost labels to a Windows path mismatch; paths are normalised now.
  ff/ſſ and fi/ſi/ffi/ſſi are re-split by crossbar score (`crossbar.py`).
- Added: ? (100 of 111 impressions kept) and ſk; more instances of every ligature (ct 70, ſh 105, ſſ 70, fi 150, ff 48, fl 32, ffi 24).
  At most 400 instances per glyph are averaged (memory).
- **Capitals**: in running text only a capital's RIGHT side ever abuts a letter. The right side comes from 1734 text where present,
  otherwise from the book (scaled to 1734 sidebearings). The left side is inferred: symmetric letters mirror their right side (not J),
  straight-stemmed lefts take H's, round lefts take O's. The final width is the mean of this and the 1734 alphabet-line width
  (they agree to 4.1 px rms, n = 22).
- 1734 glyph fidelity unchanged: 0.876 against 0.833 for impression vs impression.

## Still missing
! (only 2-3 real impressions in 150 pages; dropped), ffl (1 in the whole book), ſl/ſb (too few), æ œ (the OCR never reports them;
need a Latin-heavy Pica text), quotes other than ', other punctuation. The italic is a separate job.
Capital *spacing* is measured only for C D F H M (plus Y Z from the book); the rest are estimated from the alphabet line plus a prior.

## Rebuild
```
python -I -X utf8 scripts/segment.py work/page1.png 2700 5250 4900 6050 transcriptions/pica_roman.txt work/pica_roman_p1
(page0: 2680 5120 4920 5945; page2: 2920 5420 5160 6245)
python -I -X utf8 scripts/average.py work/pica_roman_avg work/pica_roman_p0 work/pica_roman_p1 work/pica_roman_p2
python -I -X utf8 scripts/spacing.py work/pica_roman_avg 7 work/pica_roman_p0 work/pica_roman_p1 work/pica_roman_p2
python -I -X utf8 scripts/build.py work/pica_roman_avg clean 97.1 fonts/Caslon1734Pica-Roman.otf
python -I -X utf8 scripts/build.py work/pica_roman_avg impression 97.1 fonts/Caslon1734PicaImpression-Roman.otf
```
`-X utf8` is required (ſ in output); `-I` ignores PYTHONIOENCODING.

### Rebuild v0.2 (after the v0.1 steps; work/sources.txt lists the 3 specimen dirs + '+work/rp/nNN' book dirs)
```
python -I -X utf8 scripts/average.py work/pica_roman_avg2 @work/sources.txt
python -I -X utf8 scripts/spacing.py work/pica_roman_avg2 7 work/pica_roman_p0 work/pica_roman_p1 work/pica_roman_p2   # then copy metrics.json -> metrics_1734.json
python -I -X utf8 scripts/spacing.py work/pica_roman_avg2 7 @work/rp_dirs.txt                                         # then copy metrics.json -> metrics_book.json
python -I -X utf8 scripts/merge_metrics.py work/pica_roman_avg2 97.1
python -I -X utf8 scripts/build.py work/pica_roman_avg2 clean 97.1 fonts/Caslon1734Pica-Roman.otf
```

## Pica Italic v0.1 (Oct 12 2026)
- Source: the 1734 sheet's "Pica Italick" block, all three copies (`transcriptions/pica_italic.txt`; the colon follows a
  compositor's thin space, so it is written ` :`). The capitals line includes Y and Z.
- **Slant 16.5°**, measured line by line (projection sharpness of the sheared x-height band). Each block is cropped, the
  neighbouring Syriac column is blanked (`ital_geometry.json`: boxes, column cut), sheared upright (x' = x + tan a · y) and
  saved as `work/ital_p{0,1,2}.png`. Everything downstream works upright; `build.py --slant=16.5` leans the traced outlines
  back about the baseline, which leaves advances and baseline positions unchanged.
- **Forced alignment** (`segment_align.py`): italic letters touch constantly (ud, nt, oſt, qu), so gap-based cutting fails.
  Each word's letter templates (from the previous averages) are placed by DP on NCC, with a weak spacing prior (a tie-breaker:
  W_PEN 0.1, sigma 10 px). Pixels go to the template whose blurred ink is strongest; unclaimed ink follows the letter owning
  most of its connected stroke. Word windows have a fixed ascender-to-descender height. These three rules stop a clipped
  template from clipping its next average. Bad first-pass templates get stand-ins (`--synth=ſſi:ſ+ſi`).
  Four rounds of alignment and averaging; median alignment NCC 0.957, 2 of 347 letters below 0.5.
- Spacing: 796 of 817 pairs, rms 1.26 px. ſ, f and j come out with negative sidebearings: kerned sorts, as in metal.
- Fidelity: font vs impression 0.860, against 0.810 for impression vs impression (fonts built upright for this test).
- Open: italic capitals' spacing rests on the alphabet line plus a prior (the set looks crowded); take right sides from Bowyer's
  italic, as for the roman. Missing: k w x y z, ligatures beyond ſi ſt ſſi, ?, figures (italic text used the roman figures).
  The roman and italic vertical metrics differ slightly (738/-262 vs 712/-288); unify them for a family.

## Pica Italic v0.2 (Oct 12 2026)
- Bowyer's italic harvested from the same 150 pages (`segment_ocr_italic.py`, `align_core.py`; no new downloads): each page
  is sheared upright by 16.5° and the OCR boxes mapped through the shear. Words are force-aligned with the 1734 italic
  templates. A word is kept only if its known letters match the italic (NCC ≥ 0.6) better than the roman, and its x-height
  is within 8% of 44 px. Letters with no template (k w x y z) are wildcards: a neutral score, a 0.3 claim on their expected
  span within the letter band, keeping only strokes that touch their x-height band. A second pass used the new averages as
  real templates. Partial z crops (width < 0.85 × height) are dropped.
  A lone ?/! straight after an accepted italic word is taken as the stacked glyph in its box.
- Added: k (35), w (169), x (32), y (107), z (17), ? (10). Fidelity against Bowyer's impressions beats impression vs impression
  for all five letters.
- Italic capitals: right sides from 9,885 book pairs; left sides inferred as for the roman; widths averaged with the 1734
  alphabet line (agreement 5.5 px rms).
- **Build rules** (both styles): in the clean version, components must reach density 0.55 in the mean, i.e. real ink in most
  impressions. Capitals keep only pieces of at least 25% of the main body, because neighbours repeated in every copy of one
  forme (the q descender over W, the italic Q's tail under R) are dropped this way.
- **Family metrics**: roman and italic share ascent 738 / descent -262 (`--descent=-262`).
- Still missing in italic: ; ! and the f-ligatures; the italic text also needs the roman figures (Caslon cast no italic figures).

## Pica small capitals v0.1 (Oct 13 2026)
- 1734: the "Pica Roman." heading is the only heading set in Pica (P and R match the Pica averages at scale 0.98–1.00,
  NCC 0.96; the other headings match other sizes). It supplies small caps A C I M N O (`pica_sc_p0..2`,
  `transcriptions/pica_roman_heading_sc.txt`).
- Bowyer book (`smallcaps_ocr.py`, same 150 pages): the OCR spells small caps as lowercase, so a word counts as small caps when
  each glyph matches its roman capital scaled to the glyph's height clearly better than the lowercase letter does
  (mean NCC ≥ 0.65 and a margin ≥ 0.08), and it has the pattern full capital + ≥ 2 small capitals ("Sect.", "Vol.", paragraph
  openings). The required capital excludes old-style figures (1 and 0 look like small-cap I and O) and lowercase words.
  Trailing punctuation is a separate token.
- **Spacing is estimated**: compositors letterspaced small caps (the heading and "S E C T." are both spaced), so abutment can't be
  measured. Each small cap takes its capital's measured sidebearings scaled by the ink-width ratio.
- Built into the roman (`--extra=work/pica_sc_avg`) as a.sc … y.sc with `smcp` and `c2sc`.
- Have 19: A C D E F G H I L M N O R S T U V W Y (F G U V Y from only 1–2 impressions). **Missing: B J K P Q X Z**;
  small caps are rare, and the other 269 pages of the book would likely supply most of them.

## English Roman v0.1 (Oct 13 2026)
- Block on all three copies (`transcriptions/english_roman.txt`; boxes p0 2704,4196–4904,5011 · p1 2700,4315–4900,5130 ·
  p2 2940,4488–5140,5303). Ligatures confirmed by glyph counts: ſt fi ff ct æ ſi ſſi.
- Body = line pitch 107.3 px (0.179 in, 1.10 × Pica; Moxon's English is 0.1875 in). x-height 47 px against Pica's 44.
  Scored against the Pica templates the block matches at only NCC 0.836 (best scale 1.05), so it is a separate cut, not an
  enlarged Pica.
- Forced alignment with templates **borrowed** from Pica (`--borrow=X:dir:scale`, `X!` = replace a bad template), used only to
  locate; shapes come from English impressions. Needed because the capitals line failed in the first pass and Q's tail touches
  its neighbours; without it the labels shifted by one letter and the errors fed on themselves.
- New general fixes: averaging starts from the ink's left edge and registers on the part above the baseline (Q's bowl only);
  the aligner drops small detached specks outside a letter's body; spacing has a very weak lsb ≈ rsb prior (round s never has
  a right neighbour in text set with long s).
- 573/578 pairs, rms 1.18 px. Fidelity 0.879 against 0.832 for impression vs impression.

## Bowyer book, all 419 pages (Oct 13 2026)
- Small caps re-averaged from the whole book: 21 of 26 (B and P from 1 impression each). Still missing: J K Q X Z.
- No ! and no ffl anywhere in the book; italic harvest added more k w x y z (riD).

## English Italic v0.1 (Oct 13 2026)
- Slant **18.5°** (Pica italic is 16.5°, another sign of a separate cut). Geometry is in `work/eital_geometry.json`;
  sheared blocks are `work/eital_p*.png`.
- Round 1 used templates borrowed from the Pica italic (×1.07) for every letter, with stand-ins for missing ligatures
  (`--synth=ff:f+f,fi:f+i,ct:c+t,æ:a+e`); later rounds used its own templates, with `Q!` borrowed again to stop "Qu" contamination.
- New general rule in `segment_align.py`: **geodesic ownership**. Each letter grows from its template core through the ink, so
  connected strokes stay with their own letter.
- 590/595 pairs, rms 1.29 px. Fidelity 0.866 against 0.815 for impression vs impression. Known flaw: the ſſi descender kerns
  too far left (3 impressions).
- `sheet.py` now sizes its window from the glyphs (the fixed window had clipped the tall English letters in the preview only).

## Great Primer and Double Pica v0.1 (Oct 13 2026), via `scripts/run_size.py configs/<name>.json`
| font | body px | fidelity (font vs impr. / impr. vs impr.) | weak glyphs |
|---|---|---|---|
| Great Primer Roman | 138.0 | 0.897 / 0.870 | Q 0.66, N 0.70 |
| Great Primer Italic (slant 21.5°) | 137.9 | 0.882 / 0.846 | N 0.72; ê missing (no template) |
| Double Pica Roman | 170.2 | 0.908 / 0.883 | none below 0.88 |
| Double Pica Italic (slant 23.5°) | 169.7 | 0.900 / 0.871 | N 0.69 |
- Italic blocks: `prepare_italic.py` (slant, locate, blank the neighbouring column, deslant).
- Aligner: geodesic ownership bounded by each letter's claim zone; capitals borrowed from the next size down in every round.
- TODO: GP Q/N (Q's tail touches u and P; N weak in all italics, so check the alphabet-line N crops); add ê to italic
  (synth e+circumflex or borrow from the roman); proofs for GP and DP not yet rendered.

## All sheet sizes configured (Oct 14 2026)
Every Latin size on the 1734 sheet now has a transcription (`transcriptions/`), a config (`configs/`) and prepared italic blocks.
`sh scripts/run_all.sh` rebuilds everything with the current pipeline (3 parallel workers; the large sizes run after Double Pica).

| config | size | notes |
|---|---|---|
| gp_*, dp_* | Great Primer, Double Pica | |
| sp1_*, sp2_* | Small Pica No. 1 / No. 2 | separate cuts on one body |
| lp1_*, lp2_* | Long Primer No. 1 / No. 2 | separate cuts; alphabet includes Æ |
| fc_*, tlgp_*, tle_* | French Cannon, Two Lines Great Primer, Two Lines English | no alphabet line: only the letters of "Quousque tandem…" plus Q and C |
| titling1–7 | titling capitals, about 75 down to 21 pt | **body estimated** as cap height / 0.72 (single line, no pitch) |
| br_*, np_*, pr_* | Brevier, Nonpareil, Pearl | **low fidelity** (x-height 28 / 25 / 22 px at 600 ppi); Nonpareil italic writes "ae" and "et", and its alphabet has no X |

Aligner fixes from this round (`segment_align.py`):
- the spacing penalty is capped, so a strong shape match always wins (Q's tail had pushed every following letter out of place);
- the vertical search is ±10 px, and the best offset per letter is kept and used for pixel ownership (long words such as the
  alphabet line span the sheet's tilt);
- geodesic growth stays inside each letter's own claim zone, and every letter is clipped to its template's vertical extent
  (in tightly set sizes descenders touch the next line).

Other changes:
- `spacing.py`: a side never seen abutting in running text is pinned by the shape prior (weight 3), scaled to the size;
  otherwise neighbouring alphabet-line sides trade off freely (GP H/I had come out at −44 px each).
- `build.py`: advance safety floor with a warning.
- `prepare_italic.py`: optional forced slant. For the small sizes the projection measure is flat, so a stroke-edge measure
  (bias −2.25°) was used and the two averaged. The exact slant barely matters, because the shear is undone on build.

## Status after the full sheet pass (Oct 14 2026)
Pipeline additions:
- Alphabet lines come from gap-based cutting, trusted per copy only when glyph widths agree across copies **and** with the expected
  capital proportions (`work/width_ratios.json`, from the Pica averages); otherwise alignment is used.
- The cutting repair uses those proportions to pick which glyph to split or merge, and where.
- Alignment: a letter may not start inside the previous one (minimum step: 0.8 × its width, 0.5 for Q, 0.4 for kerned f ſ j).
- Build: hairline recovery (centreline of faint connected ink, drawn at the letter's thinnest stroke width); capitals drop only
  pieces outside their own body.
- Large sizes (`prefer_seg`): cleanly gap-cut words come from segmentation, the rest from alignment.
- `run_size.py --reuse` redoes merge, spacing and build without re-aligning.

| quality | fonts |
|---|---|
| good (proof checked) | Pica R/I, English R/I, Great Primer R/I, Double Pica R/I, Small Pica No.1 & No.2 R/I, Long Primer No.1 & No.2 R, Two Lines Great Primer R/I, titling 1–7 |
| usable, flaws | Brevier R (S/T merge on 2 copies: re-run with the new proportion check; hyphen, ? and round s weak), Pearl R (f), Nonpareil R (h, j, commas) |
| **not acceptable yet** | Long Primer No.1/No.2 Italic (& ſt X Y Z broken, too heavy), Brevier Italic (Z N M), Pearl Italic, Nonpareil Italic (fragments; marked experimental: needs better scans) |
| re-running | French Cannon R/I, Two Lines English R/I (swash-Q fix) |

## Status, end of Oct 14 2026 (all 31 sheet fonts built)
Added since the table above: best-copy fallback for alphabet lines (with a per-glyph proportion filter), a forced final
re-average, horizontal registration shifts clipped to ±4 px (a round o could lock onto a wrong peak), a Q min-step of 0.38,
and Q/ſ/q borrowed in every round where "Quouſque" is their only word (fc_italic, tle_roman).

| quality | fonts |
|---|---|
| good | Pica R/I, English R/I, Great Primer R/I, Double Pica R/I, Small Pica 1 & 2 R/I, Long Primer 1 & 2 R, French Cannon R/I, Two Lines GP R/I, Two Lines English R, titling 1–7 |
| flaws | Two Lines English I (comma is a fragment), Brevier R (S T W X Æ left out; hyphen, ? and round s weak; f advance), Long Primer 2 R (h), Pearl R (f), Nonpareil R (h j x commas), titling 1–2 rough edges and a stray mark on A (only 3 impressions each) |
| not acceptable | Long Primer 1 & 2 I (alignment mislabels: ſt includes neighbours, h/u confused), Brevier I, Pearl I, Nonpareil I (experimental) |

Family overview: `proofs/family_overview.png`.

## Decision, Oct 14 2026: smallest sizes dropped

Nonpareil and Pearl (roman and italic) are not being developed further. Their sheet impressions are too small and too faint for an accurate build, and there are no suitable book sources at these sizes. Their sheet-only builds are kept, unfinished, in `fonts/experimental/`. Brevier stays in the family, built from the sheet only.

## Where things stand (paused Oct 14 2026)

**Done**
- Every size and style on the sheet is built in clean and Impression versions (fonts/). Every one matches the impressions more closely than the impressions match each other.
- Fixes made this session:
  - local baseline per letter (the printed lines bend), which fixed doubled italic capitals;
  - aligned words whose labels shifted against a cleanly cut copy are now dropped;
  - single capitals rescued from untrusted alphabet lines;
  - a vertical clip at -0.85/+0.36 of the line pitch;
  - for 2 disagreeing impressions, keep the fuller one;
  - OCR junk is filtered out of book sources;
  - **book weight calibration**: book-only glyphs are traced to sheet/book ink area, measured on n o e a h d m u.
- English v0.2, Roman and Italic: w y k x z W Y K and the figures come from Eboracum (work/ebo, work/eboi). Config key `supp`.
- Nonpareil and Pearl were dropped (fonts/experimental/). Brevier is sheet-only.

**Book candidates.** The scans are about 888 ppi, so screen with `screen_all.py 888` (env CASLON_DOWN=0.5 CASLON_SWEEP=0.94,1.07,0.03). A true match is at about x1.0.
- Epictetus 1741 is Pica (0.920 at x1.0). It is a second Pica source; the full PDF is in source/books/epictetus.
- Caribbeana 1741 looks like Great Primer. Whitefield, Christian's Companion 1738, looks like English or Great Primer. Wentworth, Letters 1739 (folio), is a small size, possibly Small Pica 2 (0.856). All of these still need confirming.
- work/screen3_results.txt holds partial results: 64 of 138 pages from source/books/screen3 (120 random books from 1734–44) and screen2. Re-run the remaining pages.

**Next**
1. Finish screening.
2. Choose books for Great Primer, Double Pica, Small Pica 1 and 2, and Long Primer 1 and 2.
3. For each: download about 60 pages, harvest with segment_ocr.py / segment_ocr_italic.py at the measured ppi, set `supp` in the config, run `run_size.py --reuse`.
4. Small caps for other sizes; italic semicolon (fall back to the roman); Pica Italic W right sidebearing; English k and italic Y slightly heavy; family naming; final specimen.

## Decision, Oct 15 2026: no book sources for Small Pica, Long Primer, Double Pica

I screened 138 random pages from 1734–44 books (work/screen3_results.txt) and probed 10 candidates. Great Primer is clear: five books match at x1.0 with a wide margin. Caribbeana 1741 was harvested (work/carib, work/caribi).

The Small Pica and Long Primer sizes could not be identified:
- Template matching slides to the edge of any scale sweep, because microfilm blur favours enlarged smaller templates.
- The letter-proportion test (scripts/proportions.py, compare_probe.py), corrected using Eboracum, failed its known-Pica control (Epictetus came out as English).
- Most 1730s octavos screened are Pica anyway.

Small Pica 1/2, Long Primer 1/2, Brevier and Double Pica therefore stay sheet-only. To add a book later, set `supp` in the config to the harvest dirs (segment_ocr.py / segment_ocr_italic.py) and run `run_size.py --reuse`.

## Final state (Oct 15 2026)

**Fonts** (`fonts/`, 56 files: 28 faces, each in a clean version and an Impression version, i.e. one typical real impression). Family names are "Caslon 1734 <size>" and "Caslon 1734 <size> Impression".
- Roman and italic: French Cannon, Two Lines Great Primer, Two Lines English, Double Pica, Great Primer, English, Pica, Small Pica No. 1 and No. 2, Long Primer No. 1 and No. 2, Brevier.
- Titling 1–7 (capitals only).
- Every face matches the 1734 impressions more closely than the impressions match each other (font-vs-impression IoU is above impression-vs-impression for every size).
- Nonpareil and Pearl were dropped (fonts/experimental/, unfinished).

**Where the letters come from**
- Everything is from the 1734 sheet, except the letters the sheet does not show:
  - Pica: The Religious Philosopher (Bowyer 1730).
  - English: Eboracum (Bowyer 1736).
  - Great Primer: Caribbeana (1741).
- Book letters are size- and weight-calibrated against letters shared with the sheet, and are dropped unless at least 5 impressions agree.
- Other sizes are sheet-only. They lack w y k z and figures, among others, wherever the sheet lacks them.

**Final pass** (`scripts/finalize.sh`, run after any rebuild; the outputs below are estimates, not measurements):
- stray pieces above the ascender are removed; a ligature that carries a fused stray is rebuilt from its own letters (Small Pica No. 2 ſt, Small Pica No. 1 italic ſi);
- Q is spaced on O's set width (the tail kerns). Where the fount has no O, the O is estimated from Pica's proportions;
- implausible capital sidebearings are replaced by Pica's (mainly Great Primer italic);
- italics borrow roman ; ( ) and figures where they have none, as printers of the period did.

**Specimen**: `specimen/Caslon1734_specimen.pdf` (scripts/gen_specimen.py, then `typst compile --font-path fonts specimen/specimen.typ`). Every face is set at its measured body. The bodies measure about 3% under nominal (Pica 11.65 pt), probably because of the scan scale or paper shrinkage.

**Known flaws**
- Great Primer figures: only 0, 2 and 6 (the rest were dropped as unreliable). Great Primer U and italic U V, and English italic z, were also dropped for the same reason.
- No "!" in any face.
- Two Lines English ſt has a small hook; Great Primer italic d has a mark at its top; Long Primer No. 2 italic ſ is spaced loosely.
- The titling sizes are estimated (no running text). Titling 1–2 are rough (3 impressions each).

## Update, Oct 15 2026 (evening): gap-filling pass

**Added**
- "!" in Pica (from Epictetus 1741, 5 agreeing impressions; Pica italic uses the roman "!") and in Great Primer.
- English roman: X and &.
- Great Primer: k w x y z K W Y, figures 1 4 6, and ":" in italic.
- Brevier S. It was found on the sheet under the label R: Q's tail joins Q and R in the alphabet line, so every later capital took the next letter's label. The capitals were reassigned (scripts/remap_glyphs.py) and S was averaged from its two impressions.

**New safeguards in the pipeline**
- average.py calibrates each book's letter size (capitals and lowercase separately) and weight against letters it shares with the sheet.
- A book-only glyph needs at least 5 impressions, with agreement measured after outlier rejection and a bar relative to that book (capped at 0.5). Weakly registered microfilm glyphs keep only their best quarter.
- check_plausible.py compares each book glyph with the Pica glyph for the same character and with every other Pica letter. It removed the garbled Great Primer U and 7, Great Primer 3 and 5 (stricter figure bar of 0.72), and two mislabels: English italic "Z" (really a Y) and Great Primer italic "V" (really a W, from the sheet).
- sync_coverage.py gives clean and Impression versions identical coverage.
- The segment_ocr.py harvester now accepts "&", "&c." and æ œ Æ Œ.
- English italic uses only the original 60 Eboracum pages: the added pages gave noisy italic labels.

finalize.sh is idempotent (the Brevier remap writes a marker into the name table) and must be run after any rebuild.

**Still missing in the book-filled faces**
- Pica: æ œ Æ Œ, and the italic apostrophe.
- English: Z, ! and '; italic X and Z; œ Æ Œ.
- Great Primer: U X Z, figures 0 2 3 5 7 8 9, ' and &; italic V; œ Æ Œ.

Sheet-only sizes lack what the sheet does not show (see the coverage list in scripts/check output).

## Update, Oct 16 2026: stains, grain, Q tails, capital spacing

- **Paper stains** (titling 1 A and C, titling 3 C). With only 2–3 impressions a mean kept one copy's stain. Now the clean versions use the median of 3, or the intersection of 2, and the trace's ink-area match restores the weight. Impression versions pick the impression nearest the consensus and blank anything outside the consensus letter shape.
- **Grain** (lumpy italic Q). Letters seen fewer than about 20 times keep the grain of ink and paper that averaging removes from common letters. The clean versions now get the smoothing their average lacks, with sigma 2.0 × sqrt(1 − n/20) scan px.
- **Q tails** are registered separately from the bowl and joined. The averaging canvas is 1.5× wider, because the long tails were being clipped. Impressions per glyph are capped by memory (2.5 GB).
- **Capital spacing check.** A right sidebearing measured in running text (≥ 3 pairs) is kept unless it is more than 150 units from Pica's. Pica's value is first adjusted for the font's steeper italic slant (overhang at cap height).
- **Remaining small flaws:** Great Primer italic R is a little loose; the Great Primer Q tail has a small knot at its end.

## Update, Oct 16 2026 (later): Pica rebuilt, specks, last blemishes

- **Pica** is rebuilt with the current averaging: `scripts/build_pica.sh` (sheet + rpA/riC book dirs, merged metrics, small caps from work/pica_sc_avg). Its "!" is inserted by finalize.sh.
- **White specks and nibbles.** Paper showing through thin inking, or a dented sort (titling 1 B, titling 2 D, titling 3 D), are handled in build.py for the clean versions:
  - small edge notches are closed (radius ≈ a quarter of the stroke);
  - enclosed holes smaller than about 1.5 stroke half-widths are filled;
  - real counters are kept.
  - Impression versions keep their specks.
- **`scripts/retrace.py`** re-traces every clean font from existing averages when only the tracing changes.
- **Double Pica J**: the block's crop box cut its descender off; the box was extended by 45 px.
- **Hand-checked overrides** (`scripts/overrides.py`, run by finalize.sh; all three are estimates):
  - Great Primer italic R: right side set from Pica's, adjusted for slant;
  - Long Primer No. 2 italic ſ: right side set to 0.42 of its ink width, as in No. 1;
  - Two Lines English ſt: rebuilt from its own ſ and t.
- **Great Primer** has only the figures 3 4 5 6, plus "!" (a figure that fails in either version is dropped from both).
- **Known and kept:** the Great Primer italic Q ends in a small ball (genuine); Small Pica No. 2 S is heavy, as its impressions are.

## Update, Oct 16 2026 (evening): hairlines, weight of book letters, stray lines

- **Small-n consensus is now hairline-safe** (average.py). Where every copy has ink within ~2 scan px the mean is kept; elsewhere the median (3) or intersection (2) is used. Stains still drop out. Thin hairlines that never land on the same pixels twice survive: the French Cannon long s's arch had been erased.
- **Notch closing** (build.py) is applied only to glyphs with 3 or fewer impressions (dented sorts), so the narrow crotches of the Great Primer w are no longer filled. The speck filler now fills only holes under (0.8 × stroke half-width)² π.
- **Book letters' weight** (build.py + scripts/stroke_ratios.json). Each book-only glyph's main-stroke thickness (90th percentile of the distance ridge) is held to the ratio to this size's n that Pica shows, and may only get thinner. This fixes the heavy x y z w k in Great Primer and English.
- **Hairline recovery** never draws inside an enclosed counter: it had joined specks in the Great Primer Q's bowl to the top.
- **Plausibility bar for letters** is now 0.55 (figures 0.72). The garbled glyphs it catches score ≤ 0.51; the genuine English italic y scores 0.59.
- **Book-filled coverage now:**
  - Great Primer adds U, ! and the figures 0 2 3 4 5 6.
  - English italic keeps k y z.
  - Missing: Pica æ œ Æ Œ; English Z ! ' (italic also X); Great Primer X Z, figures 1 7 8 9, ' & (italic also U).

## Survey, Oct 20 2026: later Caslon specimen books (1764, 1766, 1785)

Scans are on the Internet Archive, downloaded to source/specimens_later/:
- 1785, University of California copy (specimenofprinti00caslrich): 500 ppi, 148 pages, with OCR.
- 1764 (6073_20220627) and 1766 (7518_20220627): 300 ppi.

**Same cuts as 1734.** scripts/survey_later.py splits each page into blocks at its headings and screens every roman block against the 1734 averages (work/survey_1785.txt):

| 1734 face | 1785 block | NCC at x1.00 |
|---|---|---|
| Great Primer | Great Primer Roman | 0.974 |
| English | English Roman No 2 (and Pica Body English No 2) | 0.969 |
| Pica | Pica Roman No 1 | 0.966 |
| Small Pica 2 | Small Pica Roman No 2 | 0.970 |
| Long Primer 1 | Long Primer Roman No 1 | 0.967 |
| Long Primer 2 | Long Primer Roman No 2 | 0.967 |
| Brevier | Brevier Roman No 2 | 0.969 |
| Small Pica 1 | Small Pica No 1 | 0.935 (uncertain) |
| Double Pica | neither 1785 Double Pica | 0.82 (not the same cut) |

**Figures.** No edition shows a figure line for each size. 1764 and 1766 have figure lines and fractions only on the Nonpareil/Pearl/Minion page.

**Text.** Every size is still set in Cicero (Latin), except a Minion block (Acts 26, in English). So these books cannot supply k w y z or figures for our sizes.

**What they would add** (block text vs. font gaps):
- Great Primer: &
- English: : !
- Small Pica 1 and 2: ? !
- Long Primer 1 and 2: x ? !
- Brevier: h j : !
- Every matched size: roughly double the impressions, from clean foundry printing.

## 1785 harvest (Oct 20 2026)

The matched 1785 blocks (survey above) were harvested with their OCR, block by block (`scripts/harvest_1785.py`, CASLON_YRANGE; dirs work/k85_<size>_<style>/n<page><k>):
- 17 roman blocks, about 90% of words accepted, 350–950 impressions each;
- 7 italic blocks.

They were added to `supp` for Great Primer, English, Small Pica 2, Long Primer 1 and 2, and Brevier, roman and italic.
- average.py calibrates each book separately: group = book dir without the X/Y/i suffix.
- As agreed with the user, the 1785 letters fill only characters our fonts lack; the 1734 letters are not re-averaged with them.

**Added**
- Brevier roman: h j ? :
- Brevier italic: h (its j was rejected; it resembled f)
- "?" in Long Primer 1 and 2, and in Small Pica 2 roman and italic
- ":" in English roman and italic

The resemblance check now judges only book-sourced glyphs (`scripts/book_chars.py`), never sheet letters. It also covers the four newly book-filled sizes.

"!" occurs 1–3 times per size in 1785, too few to pass. Small Pica 1 and Double Pica were not harvested (not confirmed as the same cuts). The current coverage list is in work/coverage_after_1785.txt.

## High-resolution book search (Oct 20–21 2026)

**Search.** 360 English books from 1730–70, all scans at ≥ 400 ppi and no microfilm, were drawn from the IA collections bostonpubliclibrary, getty, americana, cdl, toronto and library_of_congress (work/hires/). One page of each was screened. Candidates were then confirmed with **scripts/design_match.py**: a few pages are harvested and averaged, and the averaged letters are compared shape by shape (IoU) with the sheet averages. Calibration on the known-genuine 1785 blocks: the true face tops the list at IoU 0.84–0.90, scale ≈ 1.0, with a clear lead. This test also separates No. 1 from No. 2 cuts. Probes: scripts/probe_hires.sh.

**Confirmed and harvested** (scripts/harvest_hires.sh, 40 pages per book, roman + italic):
| Book | Face | IoU | Tag |
|---|---|---|---|
| Faction Detected (London 1743), 400 ppi | Small Pica 2 | 0.885 | fd |
| Parliamentary History of England vol. 23 (Osborne & Sandby 1751–61), 400 ppi | Small Pica 2 | 0.867 | ph |
| Parliamentary History of England vol. 4 (same printers), 400 ppi | Small Pica 1 | 0.834 (lead 0.10) | pc |
| Vertot, Knights Hospitallers (Edinburgh 1757), 500 ppi | Long Primer 1 | 0.883 | kh |
| Polybius vol. 2 (J. Hughs for Dodsley 1761), 500 ppi | English | 0.877 | po |
| Doctor King's Apology (Oxford, at the Theatre, 1755), 400 ppi | Great Primer | 0.853 | dk |

Caveat: the Knights Hospitallers is an Edinburgh book, and Scottish founders cast close Caslon copies; its design match is as strong as the 1785 calibration.

Probable but not used: Philalethes Again (Pica 0.832), Modern Gazetteer (Brevier 0.80), Annual Register 1758 (Long Primer 1 0.81). Not found: Long Primer 2, Double Pica.

**Added**
- Small Pica 2 roman is now complete apart from ' æ œ Æ Œ: k w y z K W Y, all figures, ; ! ( ). Its italic gains k w y.
- Small Pica 1 roman: k w y z ; ' ) and figures 0 8. Its "(" was removed because it resembled ſ.
- Long Primer 1 roman: k w x y z ; ' and figures 1 4 6 8.
- Great Primer: figures 0–6 and the apostrophe.
- English: Polybius added as a second book for its existing book letters.

The resemblance check now covers ; ( ) ' too and builds references for any character asked about. Coverage is in work/coverage_after_books.txt.

## Oct 28 2026: singles, ligature-check bug, the j's dot, titling lowercase, release prep
- **Verified singles** (Impression fonts only): book-only letters seen 1–4 times reviewed by
  eye (review_singles.py); 29 accepted + 4 italic "!" (scripts/impression_singles.json,
  rejections in its `_note`), added with add_singles.py; spacing estimated (ligature:
  component sidebearings; others: Pica's scaled; italic "!": the colon's).
- **check_ligs.py bug**: the letter-row comparison kept render margins (~2.7x wide), so every
  book ffi/ffl/ſk without a Pica counterpart scored 0 and was replaced by its letters. Fixed
  (letters on their own advances, setline render ligs=False); singles exempt ("by eye");
  romans rebuilt (relig_all.sh). Pica "ſb" (all ſt) unligated (overrides.py).
- **j dot**: average.py registers the dot on its own (DOTTED) and keeps only impressions with
  a detached dot (misread ſ/f dropped: GP italic 12/26, Brevier roman 27/88, Pica italic
  152/189); build.py keeps an i/j dot of low mean density and sizes a lost j dot from the
  impression (_j_dot). Brevier italic j rejected by eye (scripts/reject_glyphs.json).
  redo_chars.py re-averages chosen characters in place; redo_j_all.sh did all 18 faces.
- **Titling lowercase**: Titling 1/2 sidebearings were unmeasurable (4–7 pairs, fixed 1:2
  split); now Double Pica's scaled by x-height (fix_titling_lowercase.py, in finalize.sh).
- Plausibility keeps: LP2 roman 3 5, italic w; GP italic "!". DP italic built sheet-only
  (Glynn italic too thin); work/dp_italic_sources.txt corrected.
- Checked, no change: Brevier J, Pica ij, Titling 1 G–H, Titling 6 M, SP2 g and apostrophe.
- DOCUMENTATION.md finished (fidelity table, section 7a, section 8 from coverage_report.py).
- Release prep: sources_manifest.json (make_manifest.py; 1,520 pages) + fetch_sources.py
  (tested byte-identical), release_names.py, make_release.sh, release/ (README, EXTENDING,
  OFL with RFN "Caslon 1734", MIT LICENSE).
- Later Oct 28: italics borrow the roman "." and "'" too (user's decision; fill_from_roman.py);
  check_plausible.py skips verified singles in Impression fonts (it had removed the English and
  LP1 italic "!"); those two italics rebuilt. Published as github.com/nathanmsolomon/caslon-1734.
- Gap review (user's questions): restored English roman 0, SP2 roman 3 5 ! (, SP1 roman 5 7,
  Brevier roman z (plausible_keep.json, all checked by eye); LP2 "!" = LP1's sort (shared
  punctuation; insert_glyph in finalize.sh, bogus average in reject_glyphs.json); LP2
  apostrophe re-averaged with the new RAISED position filter (average.py); GP X confirmed
  unattested (the "Mr. X." candidates are italic K).
- Follow-ups: italics borrow the hyphen too; SP1 3 6 9 re-averaged from impressions chosen by eye
  (label_fixes.json + apply_label_fixes.py, hooked into relabel_all.sh); LP2 apostrophe average
  was a blob, so LP1's is set (reject_glyphs.json; insert_glyph.py "=" keeps the donor's spacing).
- SP1 "(" from its 13 genuine book impressions (by eye; label_fixes.json); SP1 "!" has none (all l).
  Not borrowed from SP2: SP1's marks measure 5-10% smaller (different sorts), unlike LP1/LP2.
- Oct 29: release adds fonts/ttf/ (TrueType copies from make_ttf.py, for Word; README says install
  one set only). Installed on this PC: the 62 TTFs in the C: per-user Fonts folder (user's choice).
- Oct 29: reference documents (specimen/reference: Word with embedded fonts, IDML, both PDFs;
  InDesign 2026 installed and used to verify). Found and fixed degenerate spacing (Pica g æ œ,
  SP2 æ, Brevier Æ, English ſſi; fix_degenerate_spacing.py after every merge). InDesign outputs
  our OTFs correctly (test vs Minion control); Document Fonts don't activate for documents
  opened by script, so the reference build uses session-loaded fonts. Release v1.0 with
  OpenType/TrueType zips and the InDesign package. SP1 roman X fixed (book "X" were Y, Y, T; label_fixes.json; redo_chars.py now shifts results onto a wider canvas).
