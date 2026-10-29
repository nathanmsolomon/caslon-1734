"""TrueType-outline copies of finished fonts, for Microsoft Word.

Word on Windows (Microsoft 365, tested Oct 28 2026) lays out text in OpenType fonts
with CFF (PostScript) outlines in Calibri instead: the released Caslon fonts and
Adobe's Source Code Pro alike, while the same Pica converted to TrueType outlines
renders. These copies keep every table except the outlines; curves are converted
with cu2qu at a tolerance of 1 unit (1/1000 of the body).

Usage: python -I make_ttf.py <out_dir> <font.otf> ...
"""
import sys, os
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

MAXP_TT = ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs",
           "maxStackElements", "maxSizeOfInstructions", "maxComponentElements", "maxPoints",
           "maxContours", "maxCompositePoints", "maxCompositeContours", "maxComponentDepth")


def to_ttf(src, dst):
    f = TTFont(src)
    order = f.getGlyphOrder(); gs = f.getGlyphSet()
    glyf = newTable("glyf"); glyf.glyphOrder = order; glyf.glyphs = {}
    for g in order:
        pen = TTGlyphPen(None)
        gs[g].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))   # TrueType winds the other way
        glyf.glyphs[g] = pen.glyph()
    del f["CFF "]
    f["glyf"] = glyf; f["loca"] = newTable("loca")
    m = f["maxp"]; m.tableVersion = 0x00010000
    for k in MAXP_TT:
        setattr(m, k, 0)
    m.maxZones = 1
    f["post"].formatType = 2.0; f["post"].extraNames = []; f["post"].mapping = {}
    f["head"].glyphDataFormat = 0; f["head"].indexToLocFormat = 0
    f.sfntVersion = "\x00\x01\x00\x00"
    f.save(dst)                         # recalculates bounds, maxp counts and loca


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for fp in sys.argv[2:]:
        to_ttf(fp, os.path.join(out, os.path.splitext(os.path.basename(fp))[0] + ".ttf"))
    print(len(sys.argv) - 2, "fonts ->", out)


if __name__ == "__main__":
    main()
