#!/bin/bash
# Regenerate the schematic and PCB and run ERC/DRC using the KiCad AppImage
# (its kicad-cli and its bundled symbol/footprint libraries).
# <project>-BOM.csv is exported from the schematic.
# The board is autorouted with FreeRouting (ROUTE=0 places only), then <project>.step
# is exported and checked in FreeCAD (AppImage, headless freecadcmd), and the Gerbers,
# drill files and <project>-gerbers.zip are written by tools/gerbers.sh.
# Usage: tools/build.sh            through-hole board, kicad/AC30.*
#        tools/build.sh smt        surface-mount board, kicad-smt/AC30_SMT.*
#        KICAD_APPIMAGE=... FREECAD_APPIMAGE=... FREEROUTING=... tools/build.sh
#        PCB_GAP=mm (space between parts, default 2.0), ROUTE=0, ROUTE_ATTEMPTS=n
set -euo pipefail
TOOLS=$(cd "$(dirname "$0")" && pwd)
export AC30_VARIANT=${1:-${AC30_VARIANT:-tht}}
if [ "$AC30_VARIANT" = smt ]; then
  export AC30_PROJECT=AC30_SMT; DIR=$TOOLS/../../kicad-smt
else
  export AC30_PROJECT=AC30; DIR=$TOOLS/..
  # the larger through-hole parts need board height weighted more heavily against wire
  export AC30_HEIGHT_W=${AC30_HEIGHT_W:-60}
fi
P=$AC30_PROJECT
mkdir -p "$DIR"; cd "$DIR"
K=${KICAD_APPIMAGE:-$HOME/bin/kicad.AppImage}
FC=${FREECAD_APPIMAGE:-$HOME/bin/FreeCAD_26.3rc1-Linux-x86_64.AppImage}
# FreeRouting 2.4.1 (bundled Java 25 runtime). 2.1.0 reported SMT boards complete but
# wrote sessions with segments missing.
FR=${FREEROUTING:-${FREEROUTING_JAR:-$HOME/bin/freerouting-2.4.1/freerouting-2.4.1-linux-x64/bin/freerouting}}
OUT=$(mktemp -d)

# Keep the AppImage mounted for the whole run to reach its libraries.
coproc MNT { exec "$K" --appimage-mount; }
read -r ROOT <&"${MNT[0]}"
MPID=${MNT_PID:-}   # empty if a mount of this AppImage was already running
trap 'if [ -n "$MPID" ]; then kill "$MPID" 2>/dev/null || true; fi; rm -rf "$OUT"' EXIT
export KICAD_SYMBOL_DIR=$ROOT/share/kicad/symbols
export KICAD_FOOTPRINT_DIR=$ROOT/share/kicad/footprints
# Private config whose global library tables are the AppImage's own (KiCad 10
# .kicad_symdir libraries), so ERC does not depend on ~/.config/kicad.
mkdir -p "$OUT/cfg/10.0"
for t in sym-lib-table fp-lib-table; do
  cp "$ROOT/share/kicad/template/$t" "$OUT/cfg/10.0/$t"
done
cli() { KICAD_CONFIG_HOME="$OUT/cfg" "$K" kicad-cli "$@"; }

echo "kicad-cli $(cli version)  libraries: $ROOT/share/kicad"
python3 -I "$TOOLS/gen.py" . >/dev/null
for f in "$P.kicad_sch" "${P}_moddemod_power.kicad_sch" "${P}_power_supply.kicad_sch"; do cli sch upgrade "$f" >/dev/null; done
cli sch erc --exit-code-violations -o "$OUT/erc.rpt" "$P.kicad_sch" | grep -i "violations" || true
cli sch export netlist --format kicadsexpr -o "$OUT/$P.net" "$P.kicad_sch" >/dev/null
# BOM from the schematic: every part, with front-panel and power-supply parts marked
# "Excluded from board"
cli sch export bom -o "$P-BOM.csv" --ref-range-delimiter '' \
  --fields 'Reference,Value,Footprint,${QUANTITY},${EXCLUDE_FROM_BOARD}' \
  --labels 'Reference,Value,Footprint,Qty,Excluded from board' \
  --group-by 'Value,Footprint,${EXCLUDE_FROM_BOARD}' "$P.kicad_sch" >/dev/null
python3 -I "$TOOLS/pcb.py" "$OUT/$P.net" "$P.kicad_pcb" "${PCB_GAP:-2.0}" | tee "$OUT/pcb.txt"
cli pcb upgrade "$P.kicad_pcb" >/dev/null
if [ "${ROUTE:-1}" != 0 ]; then
  # FreeRouting results vary from run to run: route the placed board afresh up to
  # ROUTE_ATTEMPTS times and keep the first result with a completely clean DRC
  # (or, failing that, the one with the fewest DRC items).
  cp "$P.kicad_pcb" "$OUT/placed.kicad_pcb"
  best=-1
  for attempt in $(seq 1 "${ROUTE_ATTEMPTS:-4}"); do
    cp "$OUT/placed.kicad_pcb" "$P.kicad_pcb"
    KICAD_CONFIG_HOME="$OUT/cfg" "$K" python3.11 "$TOOLS/route.py" "$P.kicad_pcb" "$FR" 2>&1 |
      grep -v '^swig/python' | sed "s/^/attempt $attempt: /"
    cli pcb drc --schematic-parity -o "$OUT/drc_try.rpt" "$P.kicad_pcb" >/dev/null
    n=$(grep -c '^\[' "$OUT/drc_try.rpt" || true)
    echo "attempt $attempt: $n DRC items"
    if [ "$best" -lt 0 ] || [ "$n" -lt "$best" ]; then best=$n; cp "$P.kicad_pcb" "$OUT/best.kicad_pcb"; fi
    [ "$n" -eq 0 ] && break
    # FreeRouting 2.4 is deterministic: a repeat result means retrying won't help
    if [ "${prev:-}" = "$n" ] && cmp -s "$P.kicad_pcb" "$OUT/prev.kicad_pcb"; then break; fi
    prev=$n; cp "$P.kicad_pcb" "$OUT/prev.kicad_pcb"
  done
  # Still not clean: finishing passes route only what is left on the best result
  # (re-routing on top can add clearance errors, so each pass must pass DRC).
  for pass in 1 2 3; do
    [ "$best" -eq 0 ] && break
    cp "$OUT/best.kicad_pcb" "$P.kicad_pcb"
    KICAD_CONFIG_HOME="$OUT/cfg" "$K" python3.11 "$TOOLS/route.py" "$P.kicad_pcb" "$FR" 2>&1 |
      grep -v '^swig/python' | sed "s/^/finish $pass: /"
    cli pcb drc --schematic-parity -o "$OUT/drc_try.rpt" "$P.kicad_pcb" >/dev/null
    n=$(grep -c '^\[' "$OUT/drc_try.rpt" || true)
    echo "finish $pass: $n DRC items"
    if [ "$n" -lt "$best" ]; then best=$n; cp "$P.kicad_pcb" "$OUT/best.kicad_pcb"; fi
  done
  cp "$OUT/best.kicad_pcb" "$P.kicad_pcb"
  [ "$best" -eq 0 ] || echo "WARNING: no DRC-clean routing; kept the best ($best items)"
fi
cli pcb drc --schematic-parity -o "$OUT/drc.rpt" "$P.kicad_pcb" | grep -E "Found" || true
grep "^\[" "$OUT/erc.rpt" "$OUT/drc.rpt" | cut -d: -f2- | sort | uniq -c || true

# 3D: STEP export (models missing from the KiCad library are reported, not fatal)
cli pcb export step --subst-models -f -o "$P.step" "$P.kicad_pcb" > "$OUT/step.log" 2>&1
grep -E "created|error" "$OUT/step.log" | grep -v "^$" | sed "s|'.*/|'|" || true
missing=$(grep "File not found" "$OUT/step.log" | sed 's|.*/||' | sort | uniq -c || true)
[ -n "$missing" ] && echo "parts without a 3D model:" && echo "$missing"

# FreeCAD: the PCB body must match the board outline written by pcb.py
AC30_STEP=$PWD/$P.step AC30_FC_OUT=$OUT/fc.txt "$FC" freecadcmd "$TOOLS/fc_check.py" >/dev/null 2>&1 || true
[ -s "$OUT/fc.txt" ] || { echo "FreeCAD check: no report"; exit 1; }
if grep -q '^error' "$OUT/fc.txt"; then echo "FreeCAD check: $(cat "$OUT/fc.txt")"; exit 1; fi
read -r W H < <(sed -n 's/^board \([0-9.]*\) x \([0-9.]*\) mm.*/\1 \2/p' "$OUT/pcb.txt")
read -r _ PW PH PZ < <(grep '^pcb' "$OUT/fc.txt")
read -r _ AW AH AZ < <(grep '^assembly' "$OUT/fc.txt")
read -r _ NS < <(grep '^solids' "$OUT/fc.txt")
echo "FreeCAD $("$FC" freecadcmd --version 2>/dev/null | grep -o '[0-9][0-9.]*' | head -1): PCB ${PW} x ${PH} x ${PZ} mm, ${NS} solids, assembly height ${AZ} mm"
if [ "$PW" != "$W" ] || [ "$PH" != "$H" ]; then
  echo "FreeCAD check FAILED: STEP board ${PW} x ${PH} mm, outline ${W} x ${H} mm"; exit 1
fi
echo "FreeCAD check: OK"

# Fabrication outputs: Gerbers, drill files and the zip for the board house
KICAD_APPIMAGE="$K" "$TOOLS/gerbers.sh" "$AC30_VARIANT"
