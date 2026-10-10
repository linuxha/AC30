#!/bin/bash
# Fabrication outputs for one board: Gerbers (X2, Protel extensions, job file),
# Excellon drill files (PTH and NPTH separate, mm) with a drill map and report,
# all in <project dir>/gerbers/ and zipped as <project>-gerbers.zip for the board house.
# Usage: tools/gerbers.sh            through-hole board, kicad/gerbers/
#        tools/gerbers.sh smt        SMT board, kicad-smt/gerbers/ (adds top paste)
#        KICAD_APPIMAGE=... tools/gerbers.sh
set -euo pipefail
TOOLS=$(cd "$(dirname "$0")" && pwd)
VARIANT=${1:-${AC30_VARIANT:-tht}}
LAYERS=F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts
if [ "$VARIANT" = smt ]; then
  P=AC30_SMT; DIR=$TOOLS/../../kicad-smt; LAYERS=$LAYERS,F.Paste
else
  P=AC30; DIR=$TOOLS/..
fi
K=${KICAD_APPIMAGE:-$HOME/bin/kicad.AppImage}
cd "$DIR"
rm -rf gerbers "$P-gerbers.zip"
mkdir gerbers
"$K" kicad-cli pcb export gerbers -o gerbers/ --layers "$LAYERS" --subtract-soldermask \
  "$P.kicad_pcb" >/dev/null
"$K" kicad-cli pcb export drill -o gerbers/ --format excellon --excellon-units mm \
  --excellon-separate-th --generate-map --map-format pdf \
  --generate-report --report-path gerbers/"$P"-drill-report.txt "$P.kicad_pcb" >/dev/null
(cd gerbers && zip -q -X "../$P-gerbers.zip" ./*)
echo "gerbers: $(ls gerbers | wc -l) files in $(basename "$(pwd)")/gerbers, $P-gerbers.zip"
