# Extending Caslon 1734

How to add a source, fill a missing letter, or rebuild. Read DOCUMENTATION.md first:
its rules (section 5) decide what may go into a font.

## Setup

- Python 3.12+ (built with 3.14) and `pip install numpy opencv-python fonttools potracer spylls`
  (spylls reads the Hunspell dictionaries used to sort ligatures by spelling;
  wordlists go in source/wordlists). The `.sh` scripts need a POSIX shell (Git Bash
  on Windows).
- `python -I scripts/fetch_sources.py` downloads the scans (~1,500 pages, several GB)
  into `source/`. Pass tags (`rpA`, `wdb`, …, see sources_manifest.json) for a subset.
- Typst (for the catalogue and specimen PDFs).

All intermediate data goes to `work/` (not in the repository): harvested letters per
page, averages (`work/<face>_avgS/`: avg_/std_/inst_<glyph>.png, glyphs.json,
metrics.json) and run results (`work/<face>_result.json`).

## Rebuild everything

```sh
sh scripts/rebuild_all.sh        # averages, spacing, fonts, finalize (hours)
```

Partial runs (minutes), each followed by `sh scripts/finalize.sh`:

| To | Run |
|---|---|
| rebuild a size's fonts from its averages | `python -I scripts/rebuild_fonts.py configs/<face>.json` |
| re-average a few characters | `python -I scripts/redo_chars.py work/<face>_avgS work/<face>_sources.txt <chars>` |
| add verified single impressions | `python -I scripts/add_singles.py work/<face>_avgS work/<face>_sources.txt work/pica_<style>_avg…` |
| Pica (built separately) | the `build.py` lines in `scripts/build_pica.sh` |

`finalize.sh` always runs over every font; its log (work/finalize.log) lists every
removal, estimate and override. Read it after each run.

## Add a book

1. **Find and confirm it is the same cut.** Screen pages at the expected scale
   (`scripts/screen_all.py`), then the skeleton test (`scripts/probe_skel.sh`, or
   `probe_wellcome.sh` for Wellcome items). Same cut means 0.5–1.1 % chamfer distance at
   scale 0.98–1.02 with a clear lead over the neighbouring sizes. For Long Primer and
   Small Pica, decide No. 1 vs No. 2 on the letters both the sheet and the 1785
   specimen agree on (e, m, u, c; DOCUMENTATION.md section 4).
2. **Harvest.** Internet Archive: add a line to a plan file and run
   `scripts/harvest_hires.sh <plan>` (roman + italic per page). Latin text:
   `scripts/harvest_latin.py`. Wellcome: `scripts/wellcome_fetch.py` then
   `scripts/wellcome_harvest.py`. Letters land in `work/<tag>/n<page>/`
   (`<tag>i` for the italic).
3. **Sort ligatures** by spelling: `sh scripts/relabel_all.sh` (add the tag to its
   size's line).
4. **Add the tag** to the size's `configs/<face>.json` `"supp"` list (average.py
   treats `<tag>`, `<tag>i`, `<tag>X`, `<tag>Y` as one book when calibrating size and
   weight) and to `scripts/make_manifest.py` (BOOKS), then
   `python -I scripts/make_manifest.py`.
5. **Audit**: `python -I scripts/audit_truncation.py` (letters cut short by the
   harvester).
6. **Rebuild** the size (`python -I scripts/run_size.py configs/<face>.json --reuse`)
   and finalize. Check the fidelity line in work/<face>_result.json and the
   plausibility lines in work/finalize.log.
7. Record the source in DOCUMENTATION.md (section 2.3: id, ppi, pages, tag, what it
   supplied, how it was confirmed).

## Fill a missing letter

- **From books, clean font**: it needs ≥ 5 agreeing impressions (average.py) and must
  pass the plausibility check (check_plausible.py). A genuine letter that fails only
  because it differs from the Pica reference can be confirmed by eye and listed, with
  the reason, in `scripts/plausible_keep.json`.
- **One or a few impressions, Impression font only**: the averaging run saves every
  thinly attested book-only letter under `<avg>/thin/` (with thin.json). Make a review
  sheet with `scripts/review_singles.py` (candidates beside the same letter in the
  neighbouring sizes), judge by eye, list the accepted impression in
  `scripts/impression_singles.json` (and rejections in its `_note`), then run
  `add_singles.py`. Beware labels: OCR reads ſ as f and l as !, so a "fl" may be ſl.
- **Never** draw, borrow from another size, or adapt another letter.

## Correct a glyph

Hand-checked corrections go in `scripts/overrides.py`, one line each with its reason
(sidebearing, rebuild a ligature from its letters, take a mislabelled ligature out of
the substitutions). They are reapplied by every finalize.

## Check

- `python -I scripts/fidelity.py <upright font> <pitch_px> <sheet instance dirs>`:
  font against the sheet's impressions vs impression against impression.
- `scripts/holdout_test.py`: averaging method against unseen impressions.
- `python -I scripts/gen_catalogue.py` then
  `typst compile --font-path fonts specimen/catalogue.typ specimen/Caslon1734_catalogue.pdf`:
  every font, every character, what each lacks (no fallback font).

## Publish a change

Bump the version in `scripts/release_names.py`, run `sh scripts/make_release.sh`, and
describe the change in WORKLOG.md and DOCUMENTATION.md.
