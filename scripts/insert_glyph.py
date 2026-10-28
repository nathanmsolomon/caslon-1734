"""Insert one character's outline from a donor font, spaced like another character.

Usage: python -I insert_glyph.py <target.otf> <donor.otf> <char> <space_like_char | =>

For a glyph harvested and averaged separately (e.g. Pica "!" from Epictetus):
the outline comes from the donor (built at the same body, 1000 units), and its
side bearings are set equal to <space_like_char>'s in the target (an estimate;
book spacing cannot be mapped onto the sheet's for a lone mark). Replaces the
character if the target already has it. "=" keeps the donor's own sidebearings
(the same sort on the same body).
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen


def main():
    tp, dp, ch, like = sys.argv[1:5]
    t, d = TTFont(tp), TTFont(dp)
    tc, dc = t.getBestCmap(), d.getBestCmap()
    dname = dc[ord(ch)]
    dgs, tgs = d.getGlyphSet(), t.getGlyphSet()
    b = BoundsPen(dgs); dgs[dname].draw(b)
    if like == "=":
        # the same sort on the same body (e.g. a fount sharing another's punctuation):
        # keep the donor's own sidebearings
        lsb, rsb = b.bounds[0], d["hmtx"][dname][0] - b.bounds[2]
    else:
        lb = BoundsPen(tgs); tgs[tc[ord(like)]].draw(lb)
        lsb = lb.bounds[0]
        rsb = t["hmtx"][tc[ord(like)]][0] - lb.bounds[2]
    ink = b.bounds[2] - b.bounds[0]
    adv = int(round(lsb + ink + rsb))
    pen = T2CharStringPen(adv, None)
    dgs[dname].draw(TransformPen(pen, (1, 0, 0, 1, lsb - b.bounds[0], 0)))
    top = t["CFF "].cff.topDictIndex[0]
    cs = top.CharStrings
    # replace the glyph the target maps this character to; otherwise add a new
    # glyph under a name nothing else uses (after a remap, glyph names and
    # characters no longer coincide)
    name = tc.get(ord(ch))
    if name is None:
        name = dname
        while name in t.getGlyphOrder():
            name += ".alt"
    cff = t["CFF "].cff
    c = pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs)
    order = t.getGlyphOrder()
    if name in cs.charStrings:
        cs[name] = c
    else:
        cs.charStrings[name] = len(cs.charStringsIndex)
        cs.charStringsIndex.append(c)
        order.append(name)
        top.charset = order
        t.setGlyphOrder(order)
        t["maxp"].numGlyphs = len(order)
        for tb in t["cmap"].tables:
            if tb.isUnicode():
                tb.cmap[ord(ch)] = name
    t["hmtx"][name] = (adv, int(round(lsb)))
    t.save(tp)
    print(tp.split("/")[-1], f"inserted {ch} (spaced like {like}: lsb {int(lsb)}, rsb {int(rsb)})")


if __name__ == "__main__":
    main()
