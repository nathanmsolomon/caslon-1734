#!/bin/sh
# Zips for a GitHub Release, from the assembled release folder (make_release.sh) and the
# InDesign package (reference_indesign.vbs):
#   Caslon1734-<v>-OpenType.zip   fonts/*.otf + INSTALL.txt, OFL.txt, README.md
#   Caslon1734-<v>-TrueType.zip   fonts/ttf/*.ttf + the same texts
#   Caslon1734-<v>-InDesign-reference.zip   InDesign's package of the reference document
# Usage: sh scripts/make_release_assets.sh <version>   -> ../caslon-1734-dist/
cd "$(dirname "$0")/.."
V=${1:?version}
R=../caslon-1734-release
D=../caslon-1734-dist
rm -rf $D; mkdir -p $D
py() { python -I -X utf8 - "$@"; }
py "$R" "$D" "$V" "work/reference/pkg/Caslon 1734 Reference" <<'EOF'
import sys, os, glob, zipfile
R, D, V, PK = sys.argv[1:5]
texts = ["release/INSTALL.txt", f"{R}/OFL.txt", f"{R}/README.md"]
def z(name, files, root):
    with zipfile.ZipFile(os.path.join(D, name), "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, os.path.join(root, os.path.basename(f)))
        for t in texts:
            zf.write(t, os.path.join(root, os.path.basename(t)))
    print(name, len(files), "fonts")
z(f"Caslon1734-{V}-OpenType.zip", sorted(glob.glob(f"{R}/fonts/*.otf")), f"Caslon1734-{V}-OpenType")
z(f"Caslon1734-{V}-TrueType.zip", sorted(glob.glob(f"{R}/fonts/ttf/*.ttf")), f"Caslon1734-{V}-TrueType")
name = f"Caslon1734-{V}-InDesign-reference.zip"
with zipfile.ZipFile(os.path.join(D, name), "w", zipfile.ZIP_DEFLATED) as zf:
    n = 0
    for dp, _, fs in os.walk(PK):
        for f in fs:
            p = os.path.join(dp, f)
            zf.write(p, os.path.join("Caslon 1734 Reference", os.path.relpath(p, PK))); n += 1
print(name, n, "files")
EOF
ls -l $D
