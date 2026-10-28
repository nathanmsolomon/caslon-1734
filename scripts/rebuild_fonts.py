"""Rebuild a size's two fonts (clean + Impression) from its existing averages,
without re-averaging (run_size.py's last step only). Run finalize.sh afterwards.
Usage: python -I rebuild_fonts.py configs/<name>.json"""
import sys, os, json, subprocess, glob

S = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(sys.argv[1], encoding="utf-8"))
nm = os.path.basename(sys.argv[1])[:-5]
res = json.load(open(f"work/{nm}_result.json", encoding="utf-8"))
tpl, pitch = res["templates"], res["pitch_px"]
fam, style, slant = C["family"], C["style"], C.get("slant", 0)
common = [f"--family={fam}", f"--style={style}"] + ([f"--slant={slant}"] if slant else []) + \
         ([f"--descent={C['descent']}"] if "descent" in C else []) + \
         ([f"--extra={C['extra']}"] if C.get("extra") and os.path.exists(f"{C['extra']}/metrics.json") else [])
base = fam.replace(" ", "")
for v, sfx in (("clean", ""), ("impression", "Impression")):
    fn = f"fonts/{base}{sfx}-{style}.otf"
    subprocess.run([sys.executable, "-I", "-X", "utf8", f"{S}/build.py", tpl, v, str(pitch), fn] + common, check=True)
    print(fn)
