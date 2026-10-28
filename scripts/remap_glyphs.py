"""Reassign mislabelled glyphs to their true characters.

Usage: python -I remap_glyphs.py <font.otf> <mapping> [drop_chars]
       mapping: comma-separated "FROM>TO" pairs, e.g. "S>T,T>V" = the glyph now
       under S is really T. Applied simultaneously. drop_chars are unmapped.

For an alphabet line whose labels slid by one letter after a bad split (Brevier
roman: S and T merged, so every later capital took the next letter's label).
The glyph shapes are genuine impressions; only their character assignment moves.
"""
import sys
from fontTools.ttLib import TTFont


def main():
    fp, mapping = sys.argv[1], sys.argv[2]
    drop = sys.argv[3] if len(sys.argv) > 3 else ""
    f = TTFont(fp)
    cmap = f.getBestCmap()
    # a marker in the name table records that this remap was applied, so a
    # second final pass cannot shift the letters again
    MARK = 400
    if f["name"].getName(MARK, 3, 1, 0x409) is not None:
        print(fp.split("/")[-1], "already remapped; skipped")
        return
    pairs = [p.split(">") for p in mapping.split(",")]
    new = {ord(b): cmap[ord(a)] for a, b in pairs if ord(a) in cmap}
    for t in f["cmap"].tables:
        if t.isUnicode():
            for ch in drop:
                t.cmap.pop(ord(ch), None)
            for u, g in new.items():
                t.cmap[u] = g
    f["name"].setName("remapped " + mapping, MARK, 3, 1, 0x409)
    f.save(fp)
    print(fp.split("/")[-1], "remapped", mapping, "| dropped:", drop or "none")


if __name__ == "__main__":
    main()
