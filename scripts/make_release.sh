#!/bin/sh
# Assemble the public repository in ../caslon-1734-release (fonts with release name
# records, specimens, documentation, the pipeline, the source manifest; no scans and
# no work/ data). Run after finalize.sh, gen_catalogue.py and the typst compiles.
cd "$(dirname "$0")/.."
R=../caslon-1734-release
mkdir -p $R/fonts $R/specimen $R/scripts $R/configs $R/transcriptions
cp fonts/Caslon1734*.otf $R/fonts/
python -I -X utf8 scripts/release_names.py $R/fonts/*.otf
# TrueType-outline copies for Microsoft Word, which lays out CFF .otf fonts in Calibri
rm -rf $R/fonts/ttf
python -I -X utf8 scripts/make_ttf.py $R/fonts/ttf $R/fonts/*.otf
cp specimen/Caslon1734_catalogue.pdf specimen/Caslon1734_specimen.pdf specimen/catalogue.typ specimen/specimen.typ \
   specimen/page1.png specimen/page2.png specimen/page3.png $R/specimen/
mkdir -p $R/specimen/reference
cp specimen/reference/* $R/specimen/reference/   # reference documents (make_reference_docs.py)
cp scripts/*.sh scripts/*.json $R/scripts/
# Since Nov 12 2026 scripts/*.py are stubs that run the shared library (N:\Claude Work\_typelib,
# one copy for Caslon, Garamont and Colines; the originals are in scripts/_pre_typelib). The
# release ships the real code: the library's version of every script this project had, its glyph
# checker, and this project's settings as scripts/typelib.json (read by typelib_profile.py).
L=../_typelib
for f in scripts/*.py; do
  b=$(basename "$f")
  if head -n 1 "$f" | grep -q "typelib stub"; then
    if [ -f "scripts/_pre_typelib/$b" ] || [ "$b" = check_glyphs.py ]; then cp "$L/$b" $R/scripts/; fi
  else
    cp "$f" $R/scripts/
  fi
done
cp $L/typelib_profile.py $R/scripts/
cp $L/profiles/caslon.json $R/scripts/typelib.json
rm -f $R/scripts/autopilot.sh      # local unattended chain (machine-specific paths)
cp configs/*.json $R/configs/
rm -f $R/configs/np_*.json $R/configs/pr_*.json      # Nonpareil and Pearl: dropped (too small for the scan)
cp transcriptions/*.txt $R/transcriptions/
cp sources_manifest.json DOCUMENTATION.md $R/
cp README.md $R/WORKLOG.md
cp release/README.md release/EXTENDING.md release/OFL.txt release/LICENSE release/.gitignore $R/
echo "release assembled in $R: $(ls $R/fonts/*.otf | wc -l) fonts + $(ls $R/fonts/ttf/*.ttf | wc -l) TrueType"
