#!/bin/sh
# Assemble the public repository in ../caslon-1734-release (fonts with release name
# records, specimens, documentation, the pipeline, the source manifest; no scans and
# no work/ data). Run after finalize.sh, gen_catalogue.py and the typst compiles.
cd "$(dirname "$0")/.."
R=../caslon-1734-release
mkdir -p $R/fonts $R/specimen $R/scripts $R/configs $R/transcriptions
cp fonts/Caslon1734*.otf $R/fonts/
python -I -X utf8 scripts/release_names.py $R/fonts/*.otf
cp specimen/Caslon1734_catalogue.pdf specimen/Caslon1734_specimen.pdf specimen/catalogue.typ specimen/specimen.typ \
   specimen/page1.png specimen/page2.png specimen/page3.png $R/specimen/
cp scripts/*.py scripts/*.sh scripts/*.json $R/scripts/
rm -f $R/scripts/autopilot.sh      # local unattended chain (machine-specific paths)
cp configs/*.json $R/configs/
rm -f $R/configs/np_*.json $R/configs/pr_*.json      # Nonpareil and Pearl: dropped (too small for the scan)
cp transcriptions/*.txt $R/transcriptions/
cp sources_manifest.json DOCUMENTATION.md $R/
cp README.md $R/WORKLOG.md
cp release/README.md release/EXTENDING.md release/OFL.txt release/LICENSE release/.gitignore $R/
echo "release assembled in $R: $(ls $R/fonts | wc -l) fonts"
