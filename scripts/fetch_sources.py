"""Download every scan page the fonts were made from (sources_manifest.json), into
the folders the harvest scripts read. The scans themselves are not redistributed.

Usage: python -I scripts/fetch_sources.py [tag ...]      (no tags: everything, ~1,500 pages)

Internet Archive: page images from https://archive.org/download/<id>/page/n<k>.jpg
(full resolution, as used) and the item's OCR (<id>_djvu.xml). Wellcome
Collection: scripts/wellcome_fetch.py (IIIF images + ALTO OCR converted to the
same layout). The 1734 sheet: McGill's jp2 zip from the Internet Archive. Also the
English and Latin word lists relabel_ligs.py uses.
Existing files are skipped, so an interrupted run can simply be repeated.
"""
import sys, os, json, zipfile, subprocess, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Caslon1734-fetch"}
# local OCR file names the harvest scripts expect (default: djvu.xml)
XML_NAME = {"source/books/religious": "religiousphiloso1730nieu_djvu.xml", "source/books/eboracum": "ebo_djvu.xml"}
PAGE_NAME = {"source/books/eboracum": "b_n{}.jpg"}
# word lists for sorting ligatures by spelling (relabel_ligs.py)
WORDLISTS = [
    ("https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt", "source/wordlists/words_alpha.txt"),  # Unlicense
    ("https://unpkg.com/dictionary-la@2.0.0/index.aff", "source/wordlists/la/index.aff"),   # dictionary-la, GPL-2.0
    ("https://unpkg.com/dictionary-la@2.0.0/index.dic", "source/wordlists/la/index.dic"),
]


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(path + ".part", "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(path + ".part", path)


def ia_files(iid):
    with urllib.request.urlopen(urllib.request.Request(f"https://archive.org/metadata/{iid}/files", headers=UA), timeout=120) as r:
        return [f["name"] for f in json.load(r)["result"]]


def main():
    m = json.load(open(os.path.join(ROOT, "sources_manifest.json"), encoding="utf-8"))
    want = set(sys.argv[1:])
    if not want:
        for url, path in WORDLISTS:
            get(url, os.path.join(ROOT, path))
    for it in m["items"]:
        if want and it.get("tag") not in want:
            continue
        d = os.path.join(ROOT, it["dir"])
        print(it["id"], "->", it["dir"], flush=True)
        if it["provider"] == "wellcome":
            subprocess.run([sys.executable, "-I", os.path.join(ROOT, "scripts", "wellcome_fetch.py"), it["id"],
                            ",".join(map(str, it["pages"])), d], check=True)
            continue
        files = ia_files(it["id"])
        if it["pages"] == "jp2 zip":
            z = next(f for f in files if f.endswith("_jp2.zip"))
            zp = os.path.join(ROOT, "source", "mcgill_jp2.zip")
            get(f"https://archive.org/download/{it['id']}/{z}", zp)
            with zipfile.ZipFile(zp) as zf:
                zf.extractall(d)
            continue
        xml = next(f for f in files if f.endswith("_djvu.xml"))
        get(f"https://archive.org/download/{it['id']}/{xml}", os.path.join(d, XML_NAME.get(it["dir"], "djvu.xml")))
        pat = PAGE_NAME.get(it["dir"], "n{}.jpg")
        for k in it["pages"]:
            get(f"https://archive.org/download/{it['id']}/page/n{k}.jpg", os.path.join(d, pat.format(k)))
    print("done")


if __name__ == "__main__":
    main()
