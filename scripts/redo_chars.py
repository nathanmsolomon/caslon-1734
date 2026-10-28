"""Re-average a few characters of a size into its existing averages, without
re-averaging the whole size (e.g. after a change to how one letter is averaged).

Usage: python -I redo_chars.py <avg dir> <sources list> <chars>

Runs average.py on the same sources with CASLON_ONLY_CHARS (the canvas geometry
depends only on the sources, so it matches the existing averages), then replaces
those characters' images and glyphs.json entries in <avg dir>. Spacing
(metrics.json) is kept. A character the new run drops is removed. Rebuild the
fonts and run finalize.sh afterwards.
"""
import sys, os, json, shutil, subprocess

S = os.path.dirname(os.path.abspath(__file__))


def main():
    avg, srcs, chars = sys.argv[1:4]
    key = os.path.basename(os.path.normpath(avg))
    tmp = f"work/redo_{key}"
    shutil.rmtree(tmp, ignore_errors=True)
    env = dict(os.environ, CASLON_ONLY_CHARS=chars, CASLON_SINGLES_KEY=key)
    subprocess.run([sys.executable, "-I", "-X", "utf8", f"{S}/average.py", tmp, "@" + srcs], env=env,
                   stdout=open(tmp + ".log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, check=True)
    gt = json.load(open(f"{tmp}/glyphs.json", encoding="utf-8"))
    gp = f"{avg}/glyphs.json"; g = json.load(open(gp, encoding="utf-8"))
    assert (gt["width"], gt["height"], gt["base_row"]) == (g["width"], g["height"], g["base_row"]), "canvas differs"
    new = {v["ch"]: gid for gid, v in gt["glyphs"].items()}
    for ch in chars:
        if ch not in new:
            # dropped by the new averaging rules: the old glyph goes too
            for gid, v in list(g["glyphs"].items()):
                if v["ch"] == ch:
                    g["glyphs"].pop(gid)
            print(key, ch, "dropped by the new run (see", tmp + ".log): removed"); continue
        gid = new[ch]
        for pre in ("avg_", "std_", "inst_"):
            shutil.copy(f"{tmp}/{pre}{gid}.png", f"{avg}/{pre}{gid}.png")
        old = g["glyphs"].get(gid, {})
        g["glyphs"][gid] = gt["glyphs"][gid]
        print(key, ch, "re-averaged: n", old.get("n"), "->", gt["glyphs"][gid]["n"])
    json.dump(g, open(gp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
