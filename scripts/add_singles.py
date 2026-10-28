"""Add the by-eye verified single impressions (impression_singles.json) to a size's
existing averages, without re-averaging the whole size.

Usage: python -I add_singles.py <avg dir> <sources list> <pica avg dir of the same style>

Runs average.py on the same sources with CASLON_ONLY_THIN (the canvas geometry
depends only on the sources, so it matches the existing averages), copies the
single glyphs' images into <avg dir> and adds them to its glyphs.json (flagged
"single": Impression font only) and metrics.json. Spacing, since one or two
impressions measure nothing reliable: a ligature takes its first letter's left
and last letter's right sidebearing around its own ink (as merge_metrics.py does
for thinly measured ligatures); any other glyph takes Pica's sidebearings as
fractions of its ink width. Rebuild the fonts and run finalize.sh afterwards.
"""
import sys, os, json, shutil, subprocess
import numpy as np, cv2

S = os.path.dirname(os.path.abspath(__file__))


def main():
    avg, srcs, pica = sys.argv[1:4]
    key = os.path.basename(os.path.normpath(avg))
    want = json.load(open(f"{S}/impression_singles.json", encoding="utf-8")).get(key, {})
    if not want:
        print(key, "no singles"); return
    tmp = f"work/singles_{key}"
    shutil.rmtree(tmp, ignore_errors=True)
    env = dict(os.environ, CASLON_ONLY_THIN="1", CASLON_SINGLES_KEY=key)
    subprocess.run([sys.executable, "-I", "-X", "utf8", f"{S}/average.py", tmp, "@" + srcs], env=env,
                   stdout=open(tmp + ".log", "w"), stderr=subprocess.STDOUT, check=True)
    gt = json.load(open(f"{tmp}/glyphs.json", encoding="utf-8"))
    gp = f"{avg}/glyphs.json"; g = json.load(open(gp, encoding="utf-8"))
    mp = f"{avg}/metrics.json"; m = json.load(open(mp, encoding="utf-8"))
    pm = json.load(open(f"{pica}/metrics.json", encoding="utf-8"))["glyphs"]
    assert (gt["width"], gt["height"], gt["base_row"]) == (g["width"], g["height"], g["base_row"]), "canvas differs"
    up = g["up"]
    for gid, v in gt["glyphs"].items():
        if not v.get("single"):
            continue
        ch = v["ch"]
        for pre in ("avg_", "std_", "inst_"):
            shutil.copy(f"{tmp}/{pre}{gid}.png", f"{avg}/{pre}{gid}.png")
        g["glyphs"][gid] = v
        a = cv2.imread(f"{avg}/avg_{gid}.png", -1).astype(np.float32) / 65535
        xs = np.where((a > 0.5).any(0))[0]
        inkw = (xs[-1] - xs[0] + 1) / up
        M = m["glyphs"]
        if len(ch) > 1 and ch[0] in M and ch[-1] in M:
            lsb, rsb, src = M[ch[0]]["lsb"], max(M[ch[-1]]["rsb"], 0.0), "single impression; component sidebearings around own ink"
        elif ch in pm:
            f = inkw / pm[ch]["inkw"]
            lsb, rsb, src = pm[ch]["lsb"] * f, pm[ch]["rsb"] * f, "single impression; Pica's sidebearings scaled to the ink width"
        elif ch == "!" and ":" in M:
            # Pica's italic has no "!" of its own; spaced like this face's colon, as the Pica "!" is (finalize.sh)
            lsb, rsb, src = M[":"]["lsb"], M[":"]["rsb"], "single impression; spaced like this face's colon"
        else:
            print(ch, "no spacing reference: left out"); g["glyphs"].pop(gid); continue
        M[ch] = dict(adv=float(lsb + inkw + rsb), lsb=float(lsb), rsb=float(rsb), inkw=float(inkw), pairs=0, source=src)
        print(key, ch, "added from", v["single"], "|", src)
    json.dump(g, open(gp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
