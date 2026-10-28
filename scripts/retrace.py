"""Re-trace every clean font from its existing averages (no re-averaging).

Usage: python -I retrace.py [config_name ...]

For changes to build.py's tracing only: reads each size's result.json (template
dir, pitch) and config (family, style, slant, descent) and rebuilds the clean
.otf exactly as run_size.py would. Pica (built by build_pica.sh) is included.
Run finalize.sh afterwards.
"""
import sys, os, json, glob, subprocess

PY = [sys.executable, "-I", "-X", "utf8"]
S = os.path.dirname(os.path.abspath(__file__))


def main():
    names = sys.argv[1:] or [os.path.basename(p)[:-5] for p in sorted(glob.glob("configs/*.json"))]
    for nm in names:
        if not os.path.exists(f"work/{nm}_result.json"):
            continue
        C = json.load(open(f"configs/{nm}.json", encoding="utf-8"))
        R = json.load(open(f"work/{nm}_result.json", encoding="utf-8"))
        fam, style = C["family"], C["style"]
        common = [f"--family={fam}", f"--style={style}"] + ([f"--slant={C['slant']}"] if C.get("slant") else []) + \
                 ([f"--descent={C['descent']}"] if "descent" in C else [])
        fn = f"fonts/{fam.replace(' ', '')}-{style}.otf"
        r = subprocess.run(PY + [f"{S}/build.py", R["templates"], "clean", str(R["pitch_px"]), fn] + common,
                           capture_output=True, text=True, encoding="utf-8")
        print(nm, (r.stdout.strip().splitlines() or ["?"])[-1] if r.returncode == 0 else "FAILED " + r.stderr[-300:])
    # Pica
    for args in (["work/pica_roman_avg4", "clean", "97.1", "fonts/Caslon1734Pica-Roman.otf", "--descent=-262", "--extra=work/pica_sc_avg"],
                 ["work/pica_italic_avg11", "clean", "97.1", "fonts/Caslon1734Pica-Italic.otf", "--slant=16.5", "--style=Italic", "--descent=-262"]):
        if os.path.exists(args[0] + "/metrics.json"):
            r = subprocess.run(PY + [f"{S}/build.py"] + args, capture_output=True, text=True, encoding="utf-8")
            print(args[3], (r.stdout.strip().splitlines() or ["?"])[-1] if r.returncode == 0 else "FAILED " + r.stderr[-300:])


if __name__ == "__main__":
    main()
