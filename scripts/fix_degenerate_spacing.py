"""Re-estimate spacing the solver could not measure.

Usage: python -I fix_degenerate_spacing.py <avg dir> <reference avg dir>

A glyph seen in only one or two pairs gives the spacing solver one equation for two
unknowns; it then splits the gap at a fixed ratio and can return negative
sidebearings, so the glyph overprints its neighbours (Pica g: advance 140 units
against 478 of ink). Any glyph measured from at most 2 pairs whose advance is under
half its ink width is re-estimated, in metrics.json:
  ligatures, and æ œ Æ Œ (as a+e, o+e, A+E, O+E): the first component's left and the
      last component's right sidebearing around the glyph's own ink;
  other glyphs: the reference size's sidebearings for the same character, as
      fractions of the ink width.
Changed glyphs are listed; these are estimates. Idempotent (fixed glyphs no longer
match). Rebuild the fonts afterwards.
"""
import sys, os, json

PARTS = {"æ": "ae", "œ": "oe", "Æ": "AE", "Œ": "OE"}


def main():
    avg, ref = sys.argv[1], sys.argv[2]
    mp = os.path.join(avg, "metrics.json")
    m = json.load(open(mp, encoding="utf-8"))
    g = m["glyphs"]
    r = json.load(open(os.path.join(ref, "metrics.json"), encoding="utf-8"))["glyphs"]
    changed = []
    for c, v in list(g.items()):
        ink = v.get("inkw", 0)
        if v.get("pairs", 99) > 2 or ink <= 0 or v["adv"] >= 0.5 * ink:
            continue
        parts = PARTS.get(c, c if len(c) > 1 else "")
        if parts and all(p in g for p in parts):
            lsb, rsb = g[parts[0]]["lsb"], max(g[parts[-1]]["rsb"], 0.0)
            src = f"estimated: {parts[0]}'s left and {parts[-1]}'s right sidebearing (measured from {v.get('pairs')} pair)"
        elif c in r and r[c].get("inkw"):
            f = ink / r[c]["inkw"]
            lsb, rsb = r[c]["lsb"] * f, r[c]["rsb"] * f
            src = f"estimated: {os.path.basename(os.path.normpath(ref))}'s sidebearings, scaled (measured from {v.get('pairs')} pair)"
        else:
            print(c, "degenerate spacing and no reference: left as it is")
            continue
        g[c] = dict(v, adv=float(lsb + ink + rsb), lsb=float(lsb), rsb=float(rsb), source=src)
        changed.append(f"{c}({v['adv']:.1f}->{lsb + ink + rsb:.1f})")
    json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(os.path.basename(os.path.normpath(avg)), "degenerate spacing re-estimated:", " ".join(changed) or "none")


if __name__ == "__main__":
    main()
