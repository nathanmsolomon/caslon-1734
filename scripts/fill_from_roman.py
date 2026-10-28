"""Give an italic font the punctuation and figures it lacks, from its roman.

Usage: python -I fill_from_roman.py <italic.otf> <roman.otf> [chars]

Printers of the period set roman ; : ! ( ) and figures inside italic text when
the italic fount had none, so that is what this does (also the full stop and
apostrophe, whose roman and italic forms do not differ; user's decision Oct 28): each character the
italic's cmap lacks is copied (outline + advance) from the roman of the same
size. The font is rewritten in place; the copied glyphs are listed.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen

DEFAULT = ".';:!?()&0123456789"


def main():
    ip, rp = sys.argv[1], sys.argv[2]
    chars = sys.argv[3] if len(sys.argv) > 3 else DEFAULT
    it, ro = TTFont(ip), TTFont(rp)
    icmap, rcmap = it.getBestCmap(), ro.getBestCmap()
    rgs = ro.getGlyphSet()
    cff = it["CFF "].cff
    top = cff.topDictIndex[0]
    cs = top.CharStrings
    order = it.getGlyphOrder()
    added = []
    for ch in chars:
        u = ord(ch)
        if u in icmap or u not in rcmap:
            continue
        rname = rcmap[u]
        name = rname if rname not in order else rname + ".roman"
        pen = T2CharStringPen(ro["hmtx"][rname][0], None)
        rgs[rname].draw(pen)
        c = pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs)
        cs.charStrings[name] = len(cs.charStringsIndex)
        cs.charStringsIndex.append(c)
        order.append(name)
        it["hmtx"][name] = ro["hmtx"][rname]
        for t in it["cmap"].tables:
            if t.isUnicode():
                t.cmap[u] = name
        added.append(ch)
    if added:
        top.charset = order
        it.setGlyphOrder(order)
        it["maxp"].numGlyphs = len(order)
        it.save(ip)
    print(ip.split("/")[-1], "added from roman:", "".join(added) or "(nothing missing)")


if __name__ == "__main__":
    main()
