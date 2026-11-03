"""Insert a ligature glyph (outline, advance and side bearings) from a donor font into a
target font, and register its substitution, without touching any other glyph.

Usage: python -I insert_lig.py <target.otf> <donor.otf> <glyph_name> <feature> <component> [<component> ...]
   e.g. insert_lig.py fonts/Caslon1734Pica-Italic.otf rebuilt/Caslon1734Pica-Italic.otf c_t hlig c t

Why (Oct 30 2026): rebuilding the Pica with build_pica.sh to add book-harvested
ligatures also changed 21-45 existing glyphs, because the published fonts carry later
hand fixes that a plain rebuild does not reproduce. So the new sort is moved into the
published font on its own. The donor was built at the same body (1000 units) from the
same sources plus the new impressions, so its own side bearings are kept.
The substitution goes into the first ligature lookup of <feature> (liga or hlig);
longer sequences are ordered first. A code point is mapped where Unicode has one
(ff fi fl ffi ffl ſt).
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib.tables import otTables

CODEPOINT = {"f_f": 0xFB00, "f_i": 0xFB01, "f_l": 0xFB02, "f_f_i": 0xFB03, "f_f_l": 0xFB04, "longs_t": 0xFB05}


def main():
    tp, dp, name, feat = sys.argv[1:5]
    comps = sys.argv[5:]
    t, d = TTFont(tp), TTFont(dp)
    if name not in d.getGlyphOrder():
        raise SystemExit(f"{name} not in donor")
    if name in t.getGlyphOrder():
        raise SystemExit(f"{name} already in target; not replacing")
    missing = [c for c in comps if c not in t.getGlyphOrder()]
    if missing:
        raise SystemExit(f"components missing in target: {missing}")
    adv, lsb = d["hmtx"][name]
    pen = T2CharStringPen(adv, None)
    d.getGlyphSet()[name].draw(pen)
    cs = pen.getCharString()
    cff = t["CFF "].cff; top = cff.topDictIndex[0]
    cs.private = top.Private; cs.globalSubrs = cff.GlobalSubrs
    top.CharStrings.charStrings[name] = len(top.CharStrings.charStringsIndex)
    top.CharStrings.charStringsIndex.append(cs)
    order = t.getGlyphOrder() + [name]
    top.charset = order
    t.setGlyphOrder(order)
    t["hmtx"][name] = (adv, lsb)
    t["maxp"].numGlyphs = len(order)
    if name in CODEPOINT:
        for sub in t["cmap"].tables:
            if sub.isUnicode():
                sub.cmap[CODEPOINT[name]] = name
    # substitution
    gsub = t["GSUB"].table
    done = False
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag != feat or done:
            continue
        for li in fr.Feature.LookupListIndex:
            lk = gsub.LookupList.Lookup[li]
            for st in lk.SubTable:
                st = getattr(st, "ExtSubTable", st)
                if hasattr(st, "ligatures"):
                    L = otTables.Ligature(); L.LigGlyph = name; L.Component = comps[1:]; L.CompCount = len(comps)
                    st.ligatures.setdefault(comps[0], []).append(L)
                    st.ligatures[comps[0]].sort(key=lambda x: -len(x.Component))
                    done = True
                    break
            if done:
                break
    if not done:
        # e.g. the published italics' hlig holds only a single substitution: add a
        # ligature lookup and attach it to every record of <feature>
        recs = [fr for fr in gsub.FeatureList.FeatureRecord if fr.FeatureTag == feat]
        if not recs:
            raise SystemExit(f"no {feat} feature in target")
        st = otTables.LigatureSubst(); st.Format = 1
        L = otTables.Ligature(); L.LigGlyph = name; L.Component = comps[1:]; L.CompCount = len(comps)
        st.ligatures = {comps[0]: [L]}
        lk = otTables.Lookup(); lk.LookupType = 4; lk.LookupFlag = 0; lk.SubTable = [st]; lk.SubTableCount = 1
        gsub.LookupList.Lookup.append(lk); gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
        for fr in recs:
            fr.Feature.LookupListIndex.append(len(gsub.LookupList.Lookup) - 1)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
    t.save(tp)
    print(f"{tp}: inserted {name} ({' + '.join(comps)} under {feat}), advance {adv}")


if __name__ == "__main__":
    main()
