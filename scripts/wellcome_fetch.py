"""Fetch a Wellcome Collection book as page images + an OCR file the harvesters read.

Usage: python -I wellcome_fetch.py <manifest_id> [page,page,... | all] [out_dir]

<manifest_id> is the IIIF manifest id (e.g. b30530751_0002, or b12345678 for a
one-volume work). Pages are canvas indexes (0-based), saved as n<idx>.jpg at
full resolution (Wellcome serves true greyscale/colour JPEGs, about 400-450
ppi). Wellcome's OCR is Tesseract ALTO (word boxes in image pixels, long s read
as "f", like the Internet Archive's); it is converted to the Internet Archive
djvu.xml layout the harvesters parse: one <OBJECT> per canvas, in canvas order,
with <LINE> and <WORD coords="left,bottom,right,top">. Pages not requested get
an empty OBJECT so that page indexes still line up.
"""
import sys, os, re, json, html, urllib.request

IIIF = "https://iiif.wellcomecollection.org/presentation/v2/"


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Caslon1734-research"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def alto_to_object(alto, w, h):
    """One ALTO page -> a djvu.xml <OBJECT> with LINE/WORD elements."""
    out = [f'<OBJECT data="alto" type="image/x.djvu" width="{w}" height="{h}">']
    for line in re.findall(r"<TextLine\b.*?</TextLine>", alto, re.S):
        words = []
        for s in re.findall(r"<String\b[^>]*/?>", line):
            a = dict(re.findall(r'(\w+)="([^"]*)"', s))
            try:
                l, t = int(float(a["HPOS"])), int(float(a["VPOS"]))
                r, b = l + int(float(a["WIDTH"])), t + int(float(a["HEIGHT"]))
            except (KeyError, ValueError):
                continue
            txt = html.escape(html.unescape(a.get("CONTENT", "")), quote=False)
            words.append(f'<WORD coords="{l},{b},{r},{t}">{txt}</WORD>')
        if words:
            out.append("<LINE>" + " ".join(words) + "</LINE>")
    out.append("</OBJECT>")
    return "\n".join(out)


def main():
    mid = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else "all"
    out = sys.argv[3] if len(sys.argv) > 3 else f"source/books/wellcome/{mid}"
    os.makedirs(out, exist_ok=True)
    m = json.loads(get(IIIF + mid))
    if m.get("@type") == "sc:Collection":        # multi-volume work: first volume unless an id was given
        m = json.loads(get(m["manifests"][0]["@id"]))
    canvases = m["sequences"][0]["canvases"]
    pages = range(len(canvases)) if want == "all" else [int(p) for p in want.split(",") if p]
    objs = []
    for i, c in enumerate(canvases):
        w, h = c.get("width", 0), c.get("height", 0)
        if i not in pages:
            objs.append(f'<OBJECT data="none" type="image/x.djvu" width="{w}" height="{h}">\n</OBJECT>'); continue
        img = c["images"][0]["resource"]["service"]["@id"]
        jpg = os.path.join(out, f"n{i}.jpg")
        if not os.path.exists(jpg) or os.path.getsize(jpg) == 0:
            open(jpg, "wb").write(get(img + "/full/full/0/default.jpg", binary=True))
        alto = ""
        sa = c.get("seeAlso")
        if isinstance(sa, dict) and "alto" in sa.get("@id", ""):
            try:
                alto = get(sa["@id"])
            except Exception as e:
                print("no OCR for page", i, e)
        objs.append(alto_to_object(alto, w, h))
    open(os.path.join(out, "djvu.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<DjVuXML><BODY>\n' + "\n".join(objs) + "\n</BODY></DjVuXML>\n")
    json.dump(dict(manifest=mid, label=m.get("label"), pages=len(canvases)),
              open(os.path.join(out, "source.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(mid, len(canvases), "pages;", len(list(pages)), "fetched ->", out)


if __name__ == "__main__":
    main()
