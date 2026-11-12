r"""Per-project settings for the shared type-revival library (N:\Claude Work\_typelib).

The three projects (Caslon 1734, Garamont, Colines) ran diverged copies of the same scripts. The
library is their union; every place where the copies BEHAVED differently is a setting here, and
each project's profile reproduces what its own copy did. Changing a setting for a project is a
decision (it changes that project's results), so it is made in the profile, not in the code.

Where the profile comes from: <project>\scripts\typelib.json if present, else
_typelib\profiles\<first word of the project folder, lower case>.json, else DEFAULTS.
The project is TYPELIB_PROJECT (set by each project's stub scripts), else the parent of the
running script's folder.

Old environment variables still override, so existing job scripts keep working:
  CASLON_BELOW, GARAMONT_MIN_BOOK, COLINES_AVG_JOBS, COLINES_JOBS (GARAMONT_SHEET_DROP is read
  where it always was).
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(
    name="generic",
    description="Each glyph is the registered average of its printed impressions; spacing solved from printed neighbours. 1000 units = measured body.",
    win_meta=True,              # build.py: Windows naming/OS2 fixes (Regular/Italic linking, Latin-1 code page, OS/2 v4)
    ascii_names=True,           # glyphnames.py: non-ASCII single letters get uniXXXX glyph names (CFF needs ASCII)
    min_area=30,                # segment.py / segment_align.py: smallest ink piece kept, px at 600 ppi
    drop_extra_lines=True,      # segment.py: drop a smudge "line" when there are more line groups than transcribed lines
    min_book=3,                 # average.py: fewest agreeing impressions for a letter only the books supply
    below=0.36,                 # average.py: ink further below the baseline than this x line pitch is the next line
    medoid_ref=True,            # average.py: for >= 6 crops take the outlier reference from the crops agreeing with the medoid
    per_letter_rng=True,        # average.py: sample over-attested letters with a per-letter seed (needed for avg_jobs > 1)
    avg_jobs=3,                 # average.py: worker processes (only with per_letter_rng and no book sources)
    align_jobs=4,               # run_size.py: copies segmented/aligned side by side
    split_half=True,            # average.py: record each glyph's split-half agreement in glyphs.json (adds a field only)
    sb_mode="offset",           # merge_metrics.py: book capital sides mapped to the sheet by "offset" or "scale"
    median_capital=True,        # merge_metrics.py: book-only capital in < 15 pairs gets the median capital right side
    unseen_median=True,         # spacing.py: a sort in no measured pair gets the median sidebearings
    fix_degenerate=None,        # run_size.py: reference avg dir pattern for fix_degenerate_spacing.py, or None
    check_build=True,           # run_size.py: run check_build.py (when the project has one) at the end
    check_glyphs=True,          # run_size.py: run check_glyphs.py at the end (result under "glyph_checks")
    check_refs={},              # check_glyphs references: {"Roman": [avg dirs], "Italic": [avg dirs]}
)
_ENV = dict(below=("CASLON_BELOW", float), min_book=("GARAMONT_MIN_BOOK", int), avg_jobs=("COLINES_AVG_JOBS", int),
            align_jobs=("COLINES_JOBS", int))
_cache = None


def project_root():
    r = os.environ.get("TYPELIB_PROJECT")
    if r:
        return r
    return os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))) if sys.argv and sys.argv[0] else os.getcwd()


def load():
    global _cache
    if _cache is not None:
        return _cache
    root = project_root(); P = dict(DEFAULTS); src = "defaults"
    for p in (os.path.join(root, "scripts", "typelib.json"),
              os.path.join(HERE, "profiles", (os.path.basename(os.path.normpath(root)).split() or ["x"])[0].lower() + ".json")):
        if os.path.exists(p):
            P.update(json.load(open(p, encoding="utf-8"))); src = p
            break
    for k, (ev, cast) in _ENV.items():
        if os.environ.get(ev):
            P[k] = cast(os.environ[ev])
    P["_source"] = src; P["_root"] = root
    _cache = P
    return P


def get(key):
    return load()[key]


if __name__ == "__main__":
    print(json.dumps(load(), ensure_ascii=False, indent=1))
