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
import numpy as np, cv2

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
    # the canvas is sized from all the sources, so setting impressions aside can change its
    # width; a glyph's ink starts at a third of the width, so it moves across exactly
    assert (gt["height"], gt["base_row"]) == (g["height"], g["base_row"]), "canvas height or baseline differs"
    dx = int(round(g["width"] / 3 - gt["width"] / 3))
    if gt["width"] != g["width"]:
        print(key, f"canvas width {gt['width']} -> {g['width']}: images shifted by {dx} px")
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
            if gt["width"] == g["width"]:
                shutil.copy(f"{tmp}/{pre}{gid}.png", f"{avg}/{pre}{gid}.png")
                continue
            im = cv2.imread(f"{tmp}/{pre}{gid}.png", cv2.IMREAD_UNCHANGED)
            out = np.zeros((im.shape[0], g["width"]) + im.shape[2:], im.dtype)
            src0, dst0 = max(0, -dx), max(0, dx)
            w = min(im.shape[1] - src0, g["width"] - dst0)
            out[:, dst0:dst0 + w] = im[:, src0:src0 + w]
            cv2.imwrite(f"{avg}/{pre}{gid}.png", out)
        old = g["glyphs"].get(gid, {})
        g["glyphs"][gid] = gt["glyphs"][gid]
        print(key, ch, "re-averaged: n", old.get("n"), "->", gt["glyphs"][gid]["n"])
    json.dump(g, open(gp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
