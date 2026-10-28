"""Set the release name records (copyright with Reserved Font Name, licence,
version, description) in fonts copied for publication.

Usage: python -I release_names.py <font.otf> ...      (edits the files in place)
"""
import sys, os
from fontTools.ttLib import TTFont

VERSION = "1.000"
URL = "https://github.com/nathanmsolomon/caslon-1734"
COPYRIGHT = 'Copyright (c) 2026, Nathan Solomon (' + URL + '), with Reserved Font Name "Caslon 1734".'
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")


def short_family(fam):
    """Windows cuts legacy family names (nameID 1) at 31 characters, so long ones are
    shortened step by step; the full name stays in the typographic family (nameID 16)."""
    for a, b in ((" Impression", " Imp"), ("No. ", ""), ("Two Lines ", "2L ")):
        if len(fam) <= 31:
            break
        fam = fam.replace(a, b)
    assert len(fam) <= 31, fam
    return fam


def describe(fn):
    imp = "Impression" in fn
    return ("Reconstructed from William Caslon's specimen sheet of 1734 (McGill University Library, "
            "600 ppi) with his 1764-85 specimens and books printed in the same cut. "
            + ("Each glyph is one typical real impression. " if imp else
               "Each glyph is the registered average of many real impressions. ")
            + "Letters without reliable impressions are left out. 1000 units = the measured body.")


def main():
    for fp in sys.argv[1:]:
        f = TTFont(fp)
        name = f["name"]
        fam = name.getDebugName(1)
        style = name.getDebugName(2)
        short = short_family(fam)
        recs = {0: COPYRIGHT, 1: short, 16: fam, 17: style, 3: f"{VERSION};{fam.replace(' ', '')}-{style}", 5: f"Version {VERSION}",
                10: describe(os.path.basename(fp)), 11: URL, 13: LICENSE, 14: "https://openfontlicense.org"}
        for nid, s in recs.items():
            name.setName(s, nid, 3, 1, 0x409)
            name.setName(s, nid, 1, 0, 0)
        f["head"].fontRevision = float(VERSION)
        # Windows header fixes (Oct 28: apps fell back to another font, and asking for
        # the roman gave the italic):
        ps = name.getDebugName(6)
        cff = f["CFF "].cff
        cff.fontNames = [ps]                      # CFF name = PostScript name, unique per style
        italic = bool(f["OS/2"].fsSelection & 1)
        f["head"].macStyle = 2 if italic else 0   # must agree with OS/2 fsSelection
        o = f["OS/2"]
        o.version = 4                             # fsSelection bit 7 (typo metrics) needs v4
        o.ulCodePageRange1 |= 1                   # Latin 1 (1252): apps use this to accept the font
        o.fsType = 0                              # installable embedding (OFL)
        f.save(fp)
    print(len(sys.argv) - 1, "fonts named, version", VERSION)


if __name__ == "__main__":
    main()
