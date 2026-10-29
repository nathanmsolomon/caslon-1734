"""Reference documents: every Caslon 1734 font at its true size, in Word and InDesign.

Usage: python -I make_reference_docs.py <release fonts dir> <out dir>
       then: cscript //nologo scripts\\reference_word.vbs <out dir>   (embeds the fonts, exports the PDF)

One page per size and style: the clean font, then the Impression font, each setting
the 1734 sheet's own text for that size (transcriptions/) at the measured body with
solid leading, then the font's character set at the same size and what it lacks.

Writes <out>/Caslon1734_reference_base.docx (Word then embeds the TrueType fonts and
saves Caslon1734_reference.docx + .pdf) and <out>/Caslon1734_reference.idml.
Font names are read from the release fonts: Word uses the legacy family (nameID 1,
shortened to 31 characters) with italic as a style flag; InDesign the typographic
family and style (nameIDs 16 and 17). Word sets type only in half points, so the
size is rounded there (the leading stays exact); InDesign takes the exact size.
"""
import sys, os, re, json, zipfile
from xml.sax.saxutils import escape, quoteattr
from fontTools.ttLib import TTFont

S = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(S)
sys.path.insert(0, S)
from gen_catalogue import UP, LOW, FIG, PUN, LIGS, FACES  # noqa: E402
from coverage_report import have  # noqa: E402

TRANS = {"French Cannon": "frenchcannon", "Two Lines Great Primer": "twolinesgp", "Two Lines English": "twolinesenglish",
         "Double Pica": "doublepica", "Great Primer": "greatprimer", "English": "english", "Pica": "pica",
         "Small Pica No. 1": "smallpica1", "Small Pica No. 2": "smallpica2", "Long Primer No. 1": "longprimer1",
         "Long Primer No. 2": "longprimer2", "Brevier": "brevier"}
LABEL = "Caslon 1734 Pica"          # labels: the most complete face
META_WORD, META_ID = "Cambria", "Minion Pro"   # lists of missing characters: deliberately not Caslon
BIG = 44                            # from this body up, the Impression version gets its own page


def sample(path):
    """The sheet's text for this size: markup resolved, line-end hyphens rejoined, the
    alphabet line left out (the character set is shown separately)."""
    if not os.path.exists(path):
        return ""
    lines = [l.rstrip() for l in open(path, encoding="utf-8") if l.strip()]
    text = [l for l in lines if not re.fullmatch(r"[A-ZÆŒ&]{8,}", l.replace(" ", ""))]
    lines = text or lines        # the titling lines are nothing but capitals: then that line is the sample
    txt = ""
    for l in lines:
        l = re.sub(r"\{([^}]*?)\.sc\}", r"\1", l)
        l = re.sub(r"\{([^}]*)\}", r"\1", l)
        txt = txt[:-1] + l if txt.endswith("-") else (txt + " " + l if txt else l)
    return txt


def split_missing(text, h):
    """Runs of (text, font has it): characters the font lacks are set in the meta typeface."""
    out = []
    for c in text:
        ok = c in h or c == " "
        if out and out[-1][1] == ok:
            out[-1][0] += c
        else:
            out.append([c, ok])
    return out


def charset(fp):
    h = have(fp)
    # characters spaced apart, so no kerned f or ligature runs into its neighbour
    groups = [" ".join(c for c in UP if c in h), " ".join(c for c in LOW if c in h),
              " ".join(c for c in FIG if c in h), " ".join(c for c in PUN if c in h),
              " ".join(seq for seq, _ in LIGS if seq in h)]
    return [g for g in groups if g]


def pages(fontdir):
    out = []
    faces = [(lab, stem, note) for lab, stem, _, note in FACES]
    faces += [(f"Titling {n}", f"Titling{n}", "capitals from the 1734 sheet and Caslon's 1764, 1766 and 1785 specimens") for n in range(1, 8)]
    sizes = json.load(open(os.path.join(P, "..", "Type Templates", "cuts_caslon.json"), encoding="utf-8"))["cuts"]
    body = {(c["family"].replace(" Impression", ""), c["style"]): c["size_pt"] for c in sizes}
    for lab, stem, note in faces:
        for style in ("Roman", "Italic"):
            fp = os.path.join(fontdir, f"Caslon1734{stem}-{style}.otf")
            if not os.path.exists(fp):
                continue
            trans = os.path.join(P, "transcriptions", (TRANS.get(lab, stem.lower()) + ("_" + style.lower() if lab in TRANS else "")) + ".txt")
            variants = []
            for var, vlab in (("", "clean"), ("Impression", "Impression")):
                f = os.path.join(fontdir, f"Caslon1734{stem}{var}-{style}.otf")
                n = TTFont(f)["name"]
                variants.append(dict(label=vlab, word_family=n.getDebugName(1), id_family=n.getDebugName(16) or n.getDebugName(1),
                                     id_style=n.getDebugName(17) or n.getDebugName(2), italic=style == "Italic",
                                     charset=charset(f), path=f, have=have(f)))
            hc, hi = have(variants[0]["path"]), have(variants[1]["path"])
            full = list(UP + LOW + FIG + PUN) + [s for s, _ in LIGS]
            lacks = [c for c in full if c not in hc and c not in hi]
            imp_only = [c for c in full if c in hi and c not in hc]
            size = body.get((f"Caslon 1734 {lab}", style)) or body.get((f"Caslon 1734 {lab}", "Roman"))
            out.append(dict(size_label=lab, style=style, size=size, note=note.replace(" + ", ", ").replace("“", "").replace("”", ""), text=sample(trans),
                            variants=variants, lacks=lacks, imp_only=imp_only))
    return out


INTRO = [
    ("Caslon 1734: reference", "title"),
    ("Every font of the Caslon 1734 reconstruction, set at its true size: the body measured on "
     "William Caslon's specimen sheet of 1734, with solid leading (leading equal to the body, as the "
     "metal was set). Each page shows one size and style twice, as the clean font (the type itself, "
     "averaged from many impressions) and as the Impression font (one typical real impression), "
     "each setting the passage Caslon printed in that size on the 1734 sheet, then its character set.", "p"),
    ("Microsoft Word sets type only in half points, so in the Word version each size is rounded to the "
     "nearest half point; the line spacing keeps the exact body. The InDesign version uses the exact "
     "sizes. Characters for which no reliable impression survives are missing from the fonts and "
     "listed on each page, in a different typeface.", "p"),
    ("Fonts: github.com/nathanmsolomon/caslon-1734. Use fonts/ttf (TrueType) for Word, fonts/ (OpenType) "
     "for InDesign and everything else. The Word document embeds the fonts.", "p"),
]


# ------------------------------------------------------------------------------------ Word
W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" mc:Ignorable="w14"')


def w_run(text, font, size, italic=False, ligs=True, proof=False):
    rpr = (f'<w:rFonts w:ascii={quoteattr(font)} w:hAnsi={quoteattr(font)} w:cs={quoteattr(font)} w:eastAsia={quoteattr(font)}/>'
           + ('<w:i/><w:iCs/>' if italic else '') + ('<w:noProof/>' if proof else '')
           + f'<w:sz w:val="{round(size * 2)}"/><w:szCs w:val="{round(size * 2)}"/>'
           + ('<w14:ligatures w14:val="all"/>' if ligs else ''))
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def w_par(runs, lead=None, before=0, after=0, keep=False, brk=False):
    sp = f'<w:spacing w:before="{round(before * 20)}" w:after="{round(after * 20)}"' + \
         (f' w:line="{round(lead * 20)}" w:lineRule="exact"/>' if lead else ' w:line="240" w:lineRule="auto"/>')
    ppr = ('<w:pageBreakBefore/>' if brk else '') + ('<w:keepNext/>' if keep else '') + sp
    return f'<w:p><w:pPr>{ppr}</w:pPr>{"".join(runs)}</w:p>'


def word_doc(pgs, out):
    ps = []
    for t, kind in INTRO:
        ps.append(w_par([w_run(t, LABEL, 26 if kind == "title" else 11.5)], after=10 if kind == "p" else 18))
    for pg in pgs:
        wsz = round(pg["size"] * 2) / 2
        ps.append(w_par([w_run(f'{pg["size_label"]}, {pg["style"]}', LABEL, 18)], after=2, brk=True, keep=True))
        info = f'Measured body {pg["size"]:g} pt' + (f' (set here at {wsz:g} pt: Word uses half points)' if wsz != pg["size"] else '') + \
               f', solid leading. Sources: {pg["note"]}.'
        ps.append(w_par([w_run(info, LABEL, 9.5, italic=True)], after=2, keep=True))
        lack = [w_run("Lacks: ", LABEL, 9.5, italic=True), w_run(" ".join(pg["lacks"]) or "nothing in the basic set", META_WORD, 9)]
        if pg["imp_only"]:
            lack += [w_run("   In the Impression version only: ", LABEL, 9.5, italic=True), w_run(" ".join(pg["imp_only"]), META_WORD, 9)]
        ps.append(w_par(lack, after=10))
        for k, v in enumerate(pg["variants"]):
            if k and pg["size"] >= BIG:
                # display sizes: the Impression version on its own page
                ps.append(w_par([w_run(f'{pg["size_label"]}, {pg["style"]} (continued)', LABEL, 18)], after=10, brk=True, keep=True))
            ps.append(w_par([w_run(f'{v["label"]}: font {v["word_family"]}' + (', italic' if v["italic"] else ''), LABEL, 9.5, italic=True)],
                            before=6, after=3, keep=True))
            if pg["text"]:
                runs = [w_run(t, v["word_family"] if ok else META_WORD, pg["size"], v["italic"], proof=True) for t, ok in split_missing(pg["text"], v["have"])]
                ps.append(w_par(runs, lead=pg["size"], after=pg["size"] * 0.5))
            ps.append(w_par([w_run("   ".join(v["charset"]), v["word_family"], pg["size"], v["italic"], proof=True)], lead=pg["size"] * 1.15, after=4))
    sect = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" '
            'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {W_NS}><w:body>{"".join(ps)}{sect}</w:body></w:document>'
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:styles {W_NS}><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="{LABEL}" w:hAnsi="{LABEL}"/><w:sz w:val="22"/><w:lang w:val="la"/></w:rPr></w:rPrDefault>'
              '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings {W_NS}><w:embedTrueTypeFonts/>'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, s in (("[Content_Types].xml", ct), ("_rels/.rels", rels), ("word/document.xml", doc),
                     ("word/styles.xml", styles), ("word/settings.xml", settings), ("word/_rels/document.xml.rels", drels)):
            z.writestr(n, s)


# -------------------------------------------------------------------------------- InDesign
PKG = 'xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="8.0"'
PW, PH, M = 612, 792, 54


def id_csr(text, family, style, size, lead=None):
    lead = lead or size
    return (f'<CharacterStyleRange AppliedCharacterStyle="CharacterStyle/$ID/[No character style]" FontStyle={quoteattr(style)} '
            f'PointSize="{size:g}" Ligatures="true"><Properties><Leading type="unit">{lead:g}</Leading>'
            f'<AppliedFont type="string">{escape(family)}</AppliedFont></Properties><Content>{escape(text)}</Content></CharacterStyleRange>')


def id_par(csrs, before=0, after=0, keep=False):
    return (f'<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle" SpaceBefore="{before:g}" '
            f'SpaceAfter="{after:g}" KeepWithNext="{1 if keep else 0}">{"".join(csrs)}<Br/></ParagraphStyleRange>')


def idml(pgs, out):
    stories, spreads = [], []
    plain = ("Regular", "Italic")
    blocks = [[id_par([id_csr(t, LABEL, plain[0], 26 if k == "title" else 11.65, 30 if k == "title" else 14)], after=12 if k == "p" else 18)
               for t, k in INTRO]]
    for pg in pgs:
        b = [id_par([id_csr(f'{pg["size_label"]}, {pg["style"]}', LABEL, plain[0], 18, 22)], after=2, keep=True),
             id_par([id_csr(f'Measured body {pg["size"]:g} pt, solid leading. Sources: {pg["note"]}.', LABEL, plain[1], 9.5, 12)], after=2, keep=True)]
        lack = [id_csr("Lacks: ", LABEL, plain[1], 9.5, 12), id_csr(" ".join(pg["lacks"]) or "nothing in the basic set", META_ID, "Regular", 9, 12)]
        if pg["imp_only"]:
            lack += [id_csr("   In the Impression version only: ", LABEL, plain[1], 9.5, 12), id_csr(" ".join(pg["imp_only"]), META_ID, "Regular", 9, 12)]
        b.append(id_par(lack, after=10))
        for k, v in enumerate(pg["variants"]):
            if k and pg["size"] >= BIG:
                # display sizes: the Impression version on its own page
                blocks.append(b)
                b = [id_par([id_csr(f'{pg["size_label"]}, {pg["style"]} (continued)', LABEL, plain[0], 18, 22)], after=10, keep=True)]
            b.append(id_par([id_csr(f'{v["label"]}: font {v["id_family"]} {v["id_style"]}', LABEL, plain[1], 9.5, 12)], before=6, after=3, keep=True))
            if pg["text"]:
                b.append(id_par([id_csr(t, v["id_family"] if ok else META_ID, v["id_style"] if ok else "Regular", pg["size"])
                                 for t, ok in split_missing(pg["text"], v["have"])], after=pg["size"] * 0.5))
            b.append(id_par([id_csr("   ".join(v["charset"]), v["id_family"], v["id_style"], pg["size"], pg["size"] * 1.15)], after=4))
        blocks.append(b)
    pts = "".join(f'<PathPointType Anchor="{x} {y}" LeftDirection="{x} {y}" RightDirection="{x} {y}"/>'
                  for x, y in ((M, -PH / 2 + M), (M, PH / 2 - M), (PW - M, PH / 2 - M), (PW - M, -PH / 2 + M)))
    for k, b in enumerate(blocks):
        sid, fid, pid, spid = f"st{k}", f"tf{k}", f"pg{k}", f"sp{k}"
        stories.append((sid, f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<idPkg:Story {PKG}>'
                        f'<Story Self="{sid}" AppliedTOCStyle="n" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n">'
                        + "".join(b) + '</Story></idPkg:Story>'))
        spreads.append((spid, f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<idPkg:Spread {PKG}>'
                        f'<Spread Self="{spid}" PageCount="1" BindingLocation="0" ItemTransform="1 0 0 1 0 0" ShowMasterItems="true">'
                        f'<Page Self="{pid}" Name="{k + 1}" GeometricBounds="0 0 {PH} {PW}" ItemTransform="1 0 0 1 0 -{PH / 2:g}" AppliedMaster="n"/>'
                        f'<TextFrame Self="{fid}" ParentStory="{sid}" ContentType="TextType" ItemLayer="ub" '
                        'AppliedObjectStyle="ObjectStyle/$ID/[Normal Text Frame]" ItemTransform="1 0 0 1 0 0">'
                        f'<Properties><PathGeometry><GeometryPathType PathOpen="false"><PathPointArray>{pts}</PathPointArray>'
                        '</GeometryPathType></PathGeometry></Properties><TextFramePreference TextColumnCount="1"/></TextFrame>'
                        '</Spread></idPkg:Spread>'))
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<idPkg:Styles {PKG}>'
              '<RootCharacterStyleGroup Self="u79"><CharacterStyle Self="CharacterStyle/$ID/[No character style]" '
              'Imported="false" Name="$ID/[No character style]"/></RootCharacterStyleGroup>'
              '<RootParagraphStyleGroup Self="u78"><ParagraphStyle Self="ParagraphStyle/$ID/[No paragraph style]" '
              'Name="$ID/[No paragraph style]" Imported="false" FillColor="Color/Black" StrokeColor="Swatch/None" '
              'PointSize="12" Ligatures="true" Hyphenation="false"><Properties><Leading type="enumeration">Auto</Leading>'
              f'<AppliedFont type="string">{LABEL}</AppliedFont></Properties></ParagraphStyle>'
              '<ParagraphStyle Self="ParagraphStyle/$ID/NormalParagraphStyle" Name="$ID/NormalParagraphStyle" Imported="false" '
              'NextStyle="ParagraphStyle/$ID/NormalParagraphStyle" Hyphenation="false"><Properties><BasedOn type="string">$ID/[No paragraph style]'
              '</BasedOn></Properties></ParagraphStyle></RootParagraphStyleGroup>'
              '<RootTableStyleGroup Self="u7b"><TableStyle Self="TableStyle/$ID/[Basic Table]" Name="$ID/[Basic Table]"/></RootTableStyleGroup>'
              '<RootCellStyleGroup Self="u7a"><CellStyle Self="CellStyle/$ID/[None]" Name="$ID/[None]" '
              'AppliedParagraphStyle="ParagraphStyle/$ID/[No paragraph style]"/></RootCellStyleGroup>'
              '<RootObjectStyleGroup Self="u7c"><ObjectStyle Self="ObjectStyle/$ID/[None]" Name="$ID/[None]"/>'
              '<ObjectStyle Self="ObjectStyle/$ID/[Normal Text Frame]" Name="$ID/[Normal Text Frame]"/></RootObjectStyleGroup>'
              '</idPkg:Styles>')
    graphic = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<idPkg:Graphic {PKG}>'
               '<Color Self="Color/Black" Model="Process" Space="CMYK" ColorValue="0 0 0 100" Name="Black"/>'
               '<Color Self="Color/Paper" Model="Process" Space="CMYK" ColorValue="0 0 0 0" Name="Paper"/>'
               '<Color Self="Color/Registration" Model="Registration" Space="CMYK" ColorValue="100 100 100 100" Name="Registration"/>'
               '<Swatch Self="Swatch/None" Name="None"/><StrokeStyle Self="StrokeStyle/$ID/Solid" Name="$ID/Solid"/></idPkg:Graphic>')
    prefs = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<idPkg:Preferences {PKG}>'
             f'<DocumentPreference PageHeight="{PH}" PageWidth="{PW}" PagesPerDocument="1" FacingPages="false"/>'
             f'<MarginPreference ColumnCount="1" Top="{M}" Bottom="{M}" Left="{M}" Right="{M}"/>'
             '<ViewPreference HorizontalMeasurementUnits="Points" VerticalMeasurementUnits="Points"/></idPkg:Preferences>')
    fonts = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<idPkg:Fonts {PKG}/>'
    design = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
              '<?aid style="50" type="document" readerVersion="6.0" featureSet="257" product="8.0(370)" ?>\n'
              f'<Document {PKG} Self="d" StoryList="{" ".join(s for s, _ in stories)}" ActiveLayer="ub">'
              '<idPkg:Graphic src="Resources/Graphic.xml"/><idPkg:Fonts src="Resources/Fonts.xml"/>'
              '<idPkg:Styles src="Resources/Styles.xml"/><idPkg:Preferences src="Resources/Preferences.xml"/>'
              '<Layer Self="ub" Name="Layer 1" Visible="true" Locked="false" IgnoreWrap="false" ShowGuides="true" '
              'LockGuides="false" UI="true" Expendable="true" Printable="true"/>'
              + "".join(f'<idPkg:Spread src="Spreads/Spread_{s}.xml"/>' for s, _ in spreads)
              + "".join(f'<idPkg:Story src="Stories/Story_{s}.xml"/>' for s, _ in stories) + '</Document>')
    container = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                 '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="designmap.xml" media-type="text/xml"/></rootfiles></container>')
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.adobe.indesign-idml-package")   # first, stored
        files = [("META-INF/container.xml", container), ("designmap.xml", design), ("Resources/Graphic.xml", graphic),
                 ("Resources/Fonts.xml", fonts), ("Resources/Styles.xml", styles), ("Resources/Preferences.xml", prefs)]
        files += [(f"Spreads/Spread_{s}.xml", x) for s, x in spreads] + [(f"Stories/Story_{s}.xml", x) for s, x in stories]
        for n, s in files:
            z.writestr(n, s, zipfile.ZIP_DEFLATED)


def main():
    fontdir, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    pgs = pages(fontdir)
    word_doc(pgs, os.path.join(out, "Caslon1734_reference_base.docx"))
    idml(pgs, os.path.join(out, "Caslon1734_reference.idml"))
    missing = []
    for pg in pgs:
        for v in pg["variants"]:
            h = have(v["path"])
            gone = sorted({c for c in pg["text"] if c.strip() and c not in h})
            if gone:
                missing.append(f'{os.path.basename(v["path"])}: {"".join(gone)}')
    print(len(pgs), "pages (+ intro) ->", out)
    print("sample characters a font lacks (Word fills them from another font):", "; ".join(missing) or "none")


if __name__ == "__main__":
    main()
