"""Harvest the Latin books confirmed as 1734 cuts, reading every "ae"/"oe" as æ/œ.

Usage: python -I harvest_latin.py <ia_id> <tag> <size> <ppi> <xheight_px600> <npages> [<slant>]

The Internet Archive OCR spells the æ and œ sorts as two letters. In Latin set
in these years nearly every ae/oe digraph was the single sort, so each OCR word
containing ae/oe is rewritten with æ/œ (CASLON_WORDFIX). segment_ocr.py then
expects one glyph fewer: a word actually printed with separate letters fails the
glyph count and is dropped. Afterwards an æ/œ must also look like one: height
within 25% of the x-height and at least 1.25 times as wide as high.
Pages are spread evenly through the book (skipping the first and last 5%).
Roman goes to work/<tag>/n<page>, italic to work/<tag>i/n<page>.
"""
import sys, os, re, html, json, subprocess, urllib.request
import cv2

AVG = {"pica": ("work/pica_roman_avg3", "work/pica_italic_avg11")}
FIX = [("AE", "Æ"), ("Ae", "Æ"), ("OE", "Œ"), ("Oe", "Œ"), ("ae", "æ"), ("oe", "œ")]


def main():
    iaid, tag, size, ppi, xh, npg = sys.argv[1:7]
    slant = sys.argv[7] if len(sys.argv) > 7 else None
    ppi, xh, npg = float(ppi), float(xh), int(npg)
    ravg, iavg = AVG.get(size, (f"work/{size}_roman_avgF", f"work/{size}_italic_avgF"))
    d = f"source/books/probe_hires/{iaid}"
    objs = re.split(r"<OBJECT ", open(f"{d}/djvu.xml", encoding="utf-8").read())[1:]
    N = len(objs)
    lo, hi = int(0.05 * N), int(0.95 * N)
    pages = sorted({lo + round(i * (hi - lo) / max(1, npg - 1)) for i in range(npg)})
    wf = {}
    for n in pages:
        m = {}
        for w in re.findall(r"<WORD [^>]*>([^<]*)</WORD>", objs[n]):
            t = html.unescape(w).strip()
            u = t
            for a, b in FIX:
                u = u.replace(a, b)
            if u != t:
                m[t] = u
        wf[str(n)] = m
    fixp = f"work/{tag}_wordfix.json"
    json.dump(wf, open(fixp, "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ, CASLON_WORDFIX=fixp)
    py = [sys.executable, "-I", "-X", "utf8"]
    for n in pages:
        jpg = f"{d}/n{n}.jpg"
        if not os.path.exists(jpg) or os.path.getsize(jpg) == 0:
            try:
                urllib.request.urlretrieve(f"https://archive.org/download/{iaid}/page/n{n}.jpg", jpg)
            except Exception as e:
                print("download failed", n, e); continue
        subprocess.run(py + ["scripts/segment_ocr.py", jpg, f"{d}/djvu.xml", str(n), str(ppi), ravg, f"work/{tag}/n{n}", str(xh)],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if slant:
            subprocess.run(py + ["scripts/segment_ocr_italic.py", jpg, f"{d}/djvu.xml", str(n), str(ppi), slant, iavg, ravg,
                                 str(xh), f"work/{tag}i/n{n}"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # æ/œ must look like a single wide sort
    counts, dropped = {}, 0
    for sub in (tag, tag + "i"):
        for n in pages:
            p = f"work/{sub}/n{n}/instances.json"
            if not os.path.exists(p):
                continue
            meta = json.load(open(p, encoding="utf-8"))
            keep = []
            for i in meta["instances"]:
                if i["ch"] in "æœ":
                    h, w = i["y1"] - i["y0"], i["x1"] - i["x0"]
                    if not (abs(h / xh - 1) <= 0.25 and w / max(1, h) >= 1.25):
                        dropped += 1; continue
                keep.append(i)
                counts[i["ch"]] = counts.get(i["ch"], 0) + 1
            meta["instances"] = keep
            json.dump(meta, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    want = "æœÆŒkwyzKWYZXJU&!'0123456789"
    print(tag, size, len(pages), "pages;", {c: counts.get(c, 0) for c in want if counts.get(c)}, "| æ/œ dropped by shape:", dropped,
          "| total", sum(counts.values()))


if __name__ == "__main__":
    main()
