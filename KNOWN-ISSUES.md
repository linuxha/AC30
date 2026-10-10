# AC-30 Reproduction: Known Issues

Status on 2026-10-10. This file covers both boards: through-hole (`kicad/AC30.*`) and SMT (`kicad-smt/AC30_SMT.*`). Both currently build from scratch with `kicad/tools/build.sh` (add `smt` for the SMT board) and pass ERC, DRC at every severity and the schematic parity check, with every connection routed.

Board details are in `AC30-settings.md` and `AC30-SMT-settings.md`. The full history is in `AC30-Claude.md`.

---

## Check before ordering

1. **The Gerbers haven't been checked in a Gerber viewer or by the board house.** They are exported from boards that pass DRC, the drill counts match the drill reports, and KiCad's copper renders look right. Run them through the board house's preview or DFM check before paying.

2. **Some connections are interpretations of the original drawings.** Check them against `docs/ac30_schematica.jpg`, `docs/ac30_mod_demod.pdf` and `docs/ac30_PS.pdf`:

   | Item | Taken as | Why |
   |---|---|---|
   | IC16 (7805) ground | GND | The PS drawing joins it to the −13 V corner of the bridge, which would make the regulator put out about −8 V |
   | IC15 (1488) supply | +13 V (pin 14), −13 V (pin 1) | Not drawn on any schematic; the only load left for those rails |
   | IC4 (4558) supply | +7.5 V (pin 8), −7.5 V (pin 4) | Not drawn; the assembly manual says it runs from the zener rails |
   | R16 far end | +5V | A terminal dot with no label |
   | IC10 (555) pins 4 and 8 | +5V | Tied to the R38 supply node on the drawing |
   | 4053 INH (pin 6) and VEE (pin 7) | GND | Not shown on the drawing |
   | IC1B | Unused, inputs to GND | Not drawn |
   | IC7D, IC13C pin numbers | Corrected to the real pinouts (IC7D 9→10; IC13C inputs 8, 9) | Drawing slips |

3. **R39 (200K DELAY trimmer) isn't on either board.** It is on the parts list and next to IC10 on the original artwork, but on no schematic, so its connections are unknown.

4. **SMT part substitutions** (SMT board only):
   - **RLY1/RLY2:** Omron G6K-2F-Y, 5 V coil, DPDT, contacts rated 1 A, both poles in parallel. The original is a 6 V SIL reed relay. Check the coil polarity mark against the datasheet (pin 1 goes to RELAY_x).
   - **Q1, Q2, Q4–Q8:** MMBT5088 stands in for the 2N5210. It is close but not identical; check the demodulator's behaviour.
   - **C4 (1 µF 15 V) and C17 (10 µF 10 V):** tantalum, EIA-3216 (A case), with little voltage margin. Consider higher-voltage parts.

5. **SMT assembly.** `kicad-smt/AC30_SMT-top-pos.csv` uses KiCad's rotations; many assembly houses apply their own offset per package, so check their placement preview. The position file covers only the SMD parts: the KK-396 connectors and the front-panel wire pads are soldered by hand.

## Board design

6. **Neither board fits the original enclosure.** The original board was about 194 × 187 mm; these are 173.0 × 126.5 mm (through-hole) and 173.0 × 88.5 mm (SMT), with the mounting holes ¼ in from their own corners.

7. **The audio lines cross the board.** Each wire has its own pad, so AUDIO_OUT, MIC_A/B, AUDIO_IN and EAR_A/B run between the SWITCHES row and the MIC/EAR rows, near digital signals. The GND fill helps.

8. **Tracks run under the pad labels** on the top layer. The labels still print over them, but are harder to read.

9. **A few GND pads are solid-connected to the copper fill** instead of using a thermal relief: D11.2, IC8.7, IC8.11 and Q7.1 on the through-hole board, and J14.2 on the SMT board. They need more heat to solder. The list depends on the routing and can change with any re-route (`build.sh` prints it).

10. **The through-hole board's TO-92 pads have a narrow annular ring:** 0.15 mm on the narrow side, the smallest on the board.

11. **The 3D models are incomplete.** The KK-396 connectors and the through-hole R16 trimmer have no model, and the wire-pad rows appear as 0.1 in pin headers.

12. **The power supply and front panel have no board.** Both are wired by hand: the supply to J12, the switches, LEDs and jacks to the wire pads.

## Tools and repository

13. **Every build changes files that haven't really changed:**
    - `kicad-cli` gives schematic pins new random IDs;
    - the Gerbers and drill maps carry timestamps;
    - routed tracks can be written in a different order.

    Compare boards by content, not by diff size.

14. **The files are in KiCad 10 format.** The system Debian KiCad (9.0.2) can't open them, and its Python module is broken. Use the KiCad 10.0.7 AppImage (`~/bin/kicad.AppImage`).

15. **Reload open boards after a build.** `build.sh` rewrites the board files; a board left open in KiCad will write its old version back when saved. `kicad/AC30.kicad_prl` (local view settings) is left uncommitted.

16. **Routing depends on the placement seed.** `build.sh` tries seeds in turn (`AC30_SEEDS`: 31, 32, 34 for the through-hole board; 30, 31, 32 for SMT) until the routing is clean. Changing the parts or the placement code can change which seed works and the whole layout.

17. **Minor:**
    - A leftover AppImage mount process can block new mounts; kill it if `build.sh` stops right after start-up.
    - Commit `1f0a4a8` wrongly says ".history already in .gitignore".
    - The earlier text in `README.md` (TPx pads, the 3.5" × 7" estimate) describes the first version.

---

## Resolved

| Issue | Fix |
|---|---|
| A fresh through-hole build left R35–Q8 unrouted | New placement seed (31); `build.sh` tries other seeds, and finishing passes free the wiring near unrouted ends |
| The early stop for repeated routing results never fired | Compares route summaries instead of board files |
| No ground plane | GND fill on both layers of both boards |
| Motor and relay lines on 0.25 mm tracks | Power class, 0.6 mm tracks (about 1.5 A) |
| FreeRouting 2.1.0 wrote incomplete sessions on the SMT board | FreeRouting 2.4.1 |
| One MIC and one EAR pad group for four jacks | Separate MIC A/B and EAR A/B pads, each with its own GND |
| BOM typos ("S4, SS"; 1N4148 count 9 for ten diodes) | Corrected |
