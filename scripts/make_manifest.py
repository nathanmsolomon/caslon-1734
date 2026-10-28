"""Write sources_manifest.json: every scan page that went into the fonts, for
fetch_sources.py (the release carries this list instead of the scans).

Usage: python -I make_manifest.py

Pages are read from the averaging inputs (work/*_sources.txt): a book page is
work/<tag>/n<page> (the italic harvest of the same book has the tag + "i", and
X/Y are further harvest passes of the same book); a 1785 block is
work/k85_<size>_<style>/n<page><block, 2 digits>. Display and titling rows come
from fixed pages of the 1764/1766/1785 specimens (specimen_rows.sh).
"""
import glob, json, re

# tag -> (provider, item id, local folder the harvest scripts read)
H = "source/books/probe_hires/"
BOOKS = {
    "rpA": ("ia", "religiousphiloso1730nieu", "source/books/religious"),
    "cl": ("ia", "corruptaelatinit00massuoft", H + "corruptaelatinit00massuoft"),
    "ebo": ("ia", "bim_eighteenth-century_eboracum-or-the-history_drake-francis-frs_1736", "source/books/eboracum"),
    "po": ("ia", "generalhistoryof02poly_0", H + "generalhistoryof02poly_0"),
    "carib": ("ia", "bim_eighteenth-century_caribbeana-containing-l_1741_2", "source/books/caribbeana"),
    "dk": ("ia", "doctorkingsapolo00king", H + "doctorkingsapolo00king"),
    "fd": ("ia", "factiondetectedb00egmoiala", H + "factiondetectedb00egmoiala"),
    "ph": ("ia", "parliamentary23londiala", H + "parliamentary23londiala"),
    "pc": ("ia", "parliamentarycon04londiala", H + "parliamentarycon04londiala"),
    "kh": ("ia", "historyofknights01vert", H + "historyofknights01vert"),
    "mt": ("ia", "mtulliiciceronis00cice", H + "mtulliiciceronis00cice"),
    "lc": ("ia", "ladyscompanionco00lond", H + "ladyscompanionco00lond"),
    "ge": ("ia", "grammarofenglish00brig", H + "grammarofenglish00brig"),
    "sh": ("ia", "selecthymnswitht00wesl", H + "selecthymnswitht00wesl"),
    "sc": ("ia", "scarronidesorvir00cott", H + "scarronidesorvir00cott"),
    "cb": ("ia", "catalogusbibliot04oxfo", H + "catalogusbibliot04oxfo"),
    "cm": ("ia", "collectionofmost00mendiala", H + "collectionofmost00mendiala"),
    "sr": ("ia", "sermonsreligious03dodduoft", H + "sermonsreligious03dodduoft"),
    "cp": ("ia", "collectionofpo06dodsuoft", H + "collectionofpo06dodsuoft"),
    "juv": ("ia", "djuniijuvenalise00juve", H + "djuniijuvenalise00juve"),
    "eg": ("ia", "englandsgazettee02whatiala", H + "englandsgazettee02whatiala"),
    "wdb": ("wellcome", "b30449698", "source/books/wellcome/b30449698"),
    "wpo": ("wellcome", "b30534951", "source/books/wellcome/b30534951"),
    "wnh": ("wellcome", "b30782405_0001", "source/books/wellcome/b30782405_0001"),
    "wce": ("wellcome", "b30540835", "source/books/wellcome/b30540835"),
    "wgl": ("wellcome", "b31871872", "source/books/wellcome/b31871872"),
    "k85": ("ia", "specimenofprinti00caslrich", "source/specimens_later/1785_uc"),
}
SPECIMENS = [  # display/titling rows (specimen_rows.sh): fixed pages
    ("ia", "6073_20220627", "source/specimens_later/1764", [4, 6, 8, 14]),
    ("ia", "7518_20220627", "source/specimens_later/1766", [4, 6, 8, 14]),
    ("ia", "specimenofprinti00caslrich", "source/specimens_later/1785_uc", [12, 14, 16]),
]
SHEET = ("ia", "McGillLibrary-rbsc_caslon-william-speciman-colgate3-C377C377S51734-17593", "source/jp2")


def base(tag):
    if tag == "riC":            # the Religious Philosopher's italic harvest
        return "rpA"
    if tag.startswith("k85_"):
        return "k85"
    t = re.sub(r"[XY]?i?$", "", tag) if tag not in BOOKS else tag
    if t not in BOOKS:
        t = re.sub(r"[XY]$", "", t)
    return t


def main():
    pages = {}
    for f in glob.glob("work/*_sources.txt"):
        if "with_glynn" in f:
            continue
        for l in open(f, encoding="utf-8"):
            p = l.strip().lstrip("+").replace("\\", "/").split("/")
            if len(p) < 3 or not p[2].startswith("n"):
                continue
            t = base(p[1])
            if t not in BOOKS:
                raise SystemExit(f"unmapped source tag {p[1]} ({f})")
            n = int(p[2][1:])
            if t == "k85":
                n //= 100           # n<page><block:02d>
            pages.setdefault(t, set()).add(n)
    items = [dict(provider=SHEET[0], id=SHEET[1], dir=SHEET[2], what="1734 specimen sheet (three copies)", pages="jp2 zip")]
    for t, (prov, iid, d) in BOOKS.items():
        if t in pages:
            items.append(dict(provider=prov, id=iid, dir=d, tag=t, pages=sorted(pages[t])))
    for prov, iid, d, pg in SPECIMENS:
        hit = next((it for it in items if it["id"] == iid), None)
        if hit:
            hit["pages"] = sorted(set(hit["pages"]) | set(pg))
        else:
            items.append(dict(provider=prov, id=iid, dir=d, pages=pg))
    json.dump(dict(note="Pages are Internet Archive leaf indexes (n<k>) or Wellcome IIIF canvas indexes.",
                   items=items), open("sources_manifest.json", "w", encoding="utf-8"), indent=1)
    print(len(items), "items,", sum(len(it["pages"]) for it in items if isinstance(it["pages"], list)), "pages")


if __name__ == "__main__":
    main()
