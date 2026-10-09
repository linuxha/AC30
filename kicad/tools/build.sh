#!/bin/bash
# Regenerate the schematic and PCB and run ERC/DRC using the KiCad AppImage
# (its kicad-cli and its bundled symbol/footprint libraries).
# The board is autorouted with FreeRouting (ROUTE=0 places only), then AC30.step
# is exported and checked in FreeCAD (AppImage, headless freecadcmd).
# Usage: tools/build.sh            (run from the kicad/ directory)
#        KICAD_APPIMAGE=... FREECAD_APPIMAGE=... FREEROUTING_JAR=... tools/build.sh
set -euo pipefail
cd "$(dirname "$0")/.."
K=${KICAD_APPIMAGE:-$HOME/bin/kicad.AppImage}
FC=${FREECAD_APPIMAGE:-$HOME/bin/FreeCAD_26.3rc1-Linux-x86_64.AppImage}
FR=${FREEROUTING_JAR:-$HOME/bin/freerouting-2.1.0.jar}
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
python3 -I tools/gen.py . >/dev/null
for f in AC30.kicad_sch AC30_moddemod_power.kicad_sch AC30_power_supply.kicad_sch; do cli sch upgrade "$f" >/dev/null; done
cli sch erc --exit-code-violations -o "$OUT/erc.rpt" AC30.kicad_sch | grep -i "violations" || true
cli sch export netlist --format kicadsexpr -o "$OUT/AC30.net" AC30.kicad_sch >/dev/null
python3 -I tools/pcb.py "$OUT/AC30.net" AC30.kicad_pcb | tee "$OUT/pcb.txt"
cli pcb upgrade AC30.kicad_pcb >/dev/null
if [ "${ROUTE:-1}" != 0 ]; then
  # FreeRouting results vary from run to run: route the placed board afresh up to
  # ROUTE_ATTEMPTS times and keep the first result with a completely clean DRC
  # (or, failing that, the one with the fewest DRC items).
  cp AC30.kicad_pcb "$OUT/placed.kicad_pcb"
  best=-1
  for attempt in $(seq 1 "${ROUTE_ATTEMPTS:-4}"); do
    cp "$OUT/placed.kicad_pcb" AC30.kicad_pcb
    KICAD_CONFIG_HOME="$OUT/cfg" "$K" python3.11 tools/route.py AC30.kicad_pcb "$FR" 2>&1 |
      grep -v '^swig/python' | sed "s/^/attempt $attempt: /"
    cli pcb drc --schematic-parity -o "$OUT/drc_try.rpt" AC30.kicad_pcb >/dev/null
    n=$(grep -c '^\[' "$OUT/drc_try.rpt" || true)
    echo "attempt $attempt: $n DRC items"
    if [ "$best" -lt 0 ] || [ "$n" -lt "$best" ]; then best=$n; cp AC30.kicad_pcb "$OUT/best.kicad_pcb"; fi
    [ "$n" -eq 0 ] && break
  done
  # Still not clean: finishing passes route only what is left on the best result
  # (re-routing on top can add clearance errors, so each pass must pass DRC).
  for pass in 1 2 3; do
    [ "$best" -eq 0 ] && break
    cp "$OUT/best.kicad_pcb" AC30.kicad_pcb
    KICAD_CONFIG_HOME="$OUT/cfg" "$K" python3.11 tools/route.py AC30.kicad_pcb "$FR" 2>&1 |
      grep -v '^swig/python' | sed "s/^/finish $pass: /"
    cli pcb drc --schematic-parity -o "$OUT/drc_try.rpt" AC30.kicad_pcb >/dev/null
    n=$(grep -c '^\[' "$OUT/drc_try.rpt" || true)
    echo "finish $pass: $n DRC items"
    if [ "$n" -lt "$best" ]; then best=$n; cp AC30.kicad_pcb "$OUT/best.kicad_pcb"; fi
  done
  cp "$OUT/best.kicad_pcb" AC30.kicad_pcb
  [ "$best" -eq 0 ] || echo "WARNING: no DRC-clean routing; kept the best ($best items)"
fi
cli pcb drc --schematic-parity -o "$OUT/drc.rpt" AC30.kicad_pcb | grep -E "Found" || true
grep "^\[" "$OUT/erc.rpt" "$OUT/drc.rpt" | cut -d: -f2- | sort | uniq -c || true

# 3D: STEP export (models missing from the KiCad library are reported, not fatal)
cli pcb export step --subst-models -f -o AC30.step AC30.kicad_pcb > "$OUT/step.log" 2>&1
grep -E "created|error" "$OUT/step.log" | grep -v "^$" | sed "s|'.*/|'|" || true
missing=$(grep "File not found" "$OUT/step.log" | sed 's|.*/||' | sort | uniq -c || true)
[ -n "$missing" ] && echo "parts without a 3D model:" && echo "$missing"

# FreeCAD: the PCB body must match the board outline written by pcb.py
AC30_STEP=$PWD/AC30.step AC30_FC_OUT=$OUT/fc.txt "$FC" freecadcmd tools/fc_check.py >/dev/null 2>&1 || true
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
