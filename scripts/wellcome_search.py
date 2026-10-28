"""List Wellcome Collection's digitised English books of 1730-1770 and fetch one
middle page of each for screening.

Usage: python -I wellcome_search.py [from_year] [to_year]

Writes work/wellcome/works.json (work id, title, date, IIIF manifest) and
downloads page images + OCR with wellcome_fetch.py into source/books/wellcome/<manifest>/.
Wellcome records no scan resolution, so screening assumes 450 ppi with a wide
scale sweep; the skeleton test then fixes each book's true scale.
"""
import sys, os, json, subprocess, urllib.request, urllib.parse

API = "https://api.wellcomecollection.org/catalogue/v2/works"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Caslon1734-research"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def main():
    y0, y1 = (sys.argv[1:3] + ["1730", "1770"])[:2] if len(sys.argv) > 2 else ("1730", "1770")
    os.makedirs("work/wellcome", exist_ok=True)
    works = []
    for a, b in [(y, min(y + 4, int(y1))) for y in range(int(y0), int(y1) + 1, 5)]:
        page = 1
        while True:
            q = urllib.parse.urlencode({"production.dates.from": f"{a}-01-01", "production.dates.to": f"{b}-12-31",
                                        "availabilities": "online", "languages": "eng", "workType": "a",
                                        "include": "items,production", "pageSize": 100, "page": page})
            d = get(f"{API}?{q}")
            for w in d.get("results", []):
                man = [loc.get("url") for it in w.get("items", []) for loc in it.get("locations", [])
                       if "iiif.wellcomecollection.org/presentation" in str(loc.get("url"))]
                if man:
                    works.append(dict(id=w["id"], title=w.get("title", "")[:120],
                                      production=[p.get("label") for p in w.get("production", [])][:1],
                                      manifest=man[0].rsplit("/", 1)[-1]))
            if page >= d.get("totalPages", 1):
                break
            page += 1
    seen, uniq = set(), []
    for w in works:
        if w["manifest"] not in seen:
            seen.add(w["manifest"]); uniq.append(w)
    json.dump(uniq, open("work/wellcome/works.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(uniq), "digitised works")
    # one middle page of each (the fetcher needs the canvas count: read the manifest first)
    for w in uniq:
        out = f"source/books/wellcome/{w['manifest']}"
        if os.path.exists(os.path.join(out, "djvu.xml")):
            continue
        try:
            m = get(f"https://iiif.wellcomecollection.org/presentation/v2/{w['manifest']}")
            if m.get("@type") == "sc:Collection":
                m = get(m["manifests"][0]["@id"]); w["manifest"] = m["@id"].rsplit("/", 1)[-1]
                out = f"source/books/wellcome/{w['manifest']}"
            n = len(m["sequences"][0]["canvases"])
            if n < 12:
                continue
            mid = n // 2
            subprocess.run([sys.executable, "-I", "-X", "utf8", "scripts/wellcome_fetch.py", w["manifest"], str(mid), out],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
            w["sample_page"] = mid
        except Exception as e:
            print("skip", w["manifest"], e)
    json.dump(uniq, open("work/wellcome/works.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("sampled", sum(1 for w in uniq if "sample_page" in w))


if __name__ == "__main__":
    main()
