"""Harvest a confirmed Wellcome Collection book (roman and italic).

Usage: python -I wellcome_harvest.py <manifest> <tag> <size> <ppi> <x-height px@600> <slant> [npages=40]

Pages are spread evenly through the middle 85 % of the book (front and back
matter skipped), fetched with wellcome_fetch.py (images + OCR), and harvested
into work/<tag>/n<page> (roman) and work/<tag>i/n<page> (italic) with the
size's sheet templates. <ppi> is the resolution implied by the screen scale
(Wellcome records none); each book's size is calibrated again in average.py.
"""
import sys, os, json, subprocess, urllib.request

IIIF = "https://iiif.wellcomecollection.org/presentation/v2/"


def main():
    man, tag, size, ppi, xh, slant = sys.argv[1:7]
    npg = int(sys.argv[7]) if len(sys.argv) > 7 else 40
    req = urllib.request.Request(IIIF + man, headers={"User-Agent": "Caslon1734-research"})
    m = json.load(urllib.request.urlopen(req, timeout=120))
    if m.get("@type") == "sc:Collection":
        m = json.load(urllib.request.urlopen(urllib.request.Request(m["manifests"][0]["@id"], headers={"User-Agent": "x"}), timeout=120))
    n = len(m["sequences"][0]["canvases"])
    lo, hi = int(0.08 * n), int(0.93 * n)
    pages = sorted({lo + round(i * (hi - lo) / max(1, npg - 1)) for i in range(npg)})
    d = f"source/books/wellcome/{man}"
    py = [sys.executable, "-I", "-X", "utf8"]
    subprocess.run(py + ["scripts/wellcome_fetch.py", man, ",".join(map(str, pages)), d], stdout=subprocess.DEVNULL)
    R, I = f"work/{size}_roman_avgF", f"work/{size}_italic_avgF"
    if size == "pica":
        R, I = "work/pica_roman_avg4", "work/pica_italic_avg11"
    for p in pages:
        jpg = f"{d}/n{p}.jpg"
        if not os.path.exists(jpg):
            continue
        subprocess.run(py + ["scripts/segment_ocr.py", jpg, f"{d}/djvu.xml", str(p), ppi, R, f"work/{tag}/n{p}", xh],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(py + ["scripts/segment_ocr_italic.py", jpg, f"{d}/djvu.xml", str(p), ppi, slant, I, R, xh, f"work/{tag}i/n{p}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import glob, collections
    for sub in (tag, tag + "i"):
        c = collections.Counter(i["ch"] for q in glob.glob(f"work/{sub}/n*/instances.json") for i in json.load(open(q, encoding="utf-8"))["instances"])
        print(sub, n, "pages in book;", len(pages), "harvested;", sum(c.values()), "letters;",
              {k: c[k] for k in "kwxyzKWXYZJQ&0123456789æ" if c.get(k)})


if __name__ == "__main__":
    main()
