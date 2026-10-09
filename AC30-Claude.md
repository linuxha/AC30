# AC-30 KiCad Schematic: Claude Code Session Log

Session dates: 2026-10-08 to 2026-10-09 (sections 1–16 on the 8th, 17–29 on the 9th). Model: Claude Opus 5.5 (Claude Code CLI).

This is a record of the chat that produced the KiCad project in `kicad/`. User messages are reproduced exactly, typos included. Claude's answers are in full for sections 1–3 and condensed from section 4 on. Claude's intermediate tool work (shell commands, image crops, file edits) is summarized rather than shown verbatim.

---

## 1. User

> Create a kicad schematic for docs/AC30-BOM.md docs/ac30_schematica.jpg

### Work done (summary)

1. **Read the inputs.** Claude read `docs/AC30-BOM.md`, the "How It Works" section of `docs/AC30-AssemblyInstruction.md` and `docs/ac30_schematica.jpg` (3300×2456). The image is titled *SWTPC AC-30 Cassette Tape Switching Schematic* and shows only the switching circuitry. The modulator/demodulator appears only as a block, and the power supply is not drawn.
2. **Traced the drawing.** Claude cropped and zoomed about 25 regions of the image with ImageMagick and traced every net by hand. It treated gaps in a line as crossings and dots as junctions. Gate pin numbers were checked against the real CMOS pinouts (4001, 4013, 4023, 4049, 4053, 4070, 555, 1488, 1489).
3. **Read the board connectors.** From `docs/ac30_wiring1a.jpg`, Claude took the signal order of board connectors J1–J5 and the front-panel parts (S1–S7, D19–D22, jacks J6–J11).
4. **Wrote a generator.** The tooling lives in `kicad/tools/`:
   - `sexp.py`: a minimal S-expression parser/writer.
   - `kilib.py`: loads stock KiCad library symbols, flattens `extends`, and reports pins and body bounding boxes.
   - `customlib.py`: writes `AC30.kicad_sym` with the MC1488, MC1489 and SPST reed relay symbols, which are missing from the stock libraries.
   - `netlist.py`: the hand-transcribed netlist. Each part has its value, footprint and a per-unit pin→net map.
   - `gen.py`: places each unit in grouped rows. Every pin gets a short wire stub ending in a net label, a power symbol or a no-connect flag. It writes the root and sub sheets, `sym-lib-table` and `AC30.kicad_pro`.
5. **Verified the result.**
   - `kicad-cli sch upgrade` converted the files to the KiCad 10 format.
   - `kicad-cli sch erc` was run on the result.
   - A netlist exported with `kicad-cli sch export netlist` was compared pin for pin against `netlist.py`. This caught one real error: the drawing labels IC13C's inputs as 7/8, but 4070 pin 7 is VSS. It was fixed to 8/9.
   - A PDF render was inspected, and the Ref/Value field placement and power-symbol text collisions were fixed.
   - A check confirmed that every BOM designator appears exactly once.

### Claude's answer

I've created a KiCad 10 project in `kicad/`. One big caveat first: the image only contains the **switching** circuit, so that's the only part that's actually wired. The modulator/demodulator and power supply aren't drawn anywhere in `docs/`, so those parts are placed but have no connections.

**What's in it**
- **`AC30.kicad_sch` (sheet 1, A1): the switching circuit, fully wired.** It covers IC6–IC15, Q5–Q11, the latches, power-on reset, LED and relay drivers, the 555 carrier-enable delay, the RS-232 parts and the front-panel switches, LEDs and jacks.
- **Board connectors J1–J5.** I took their signal lists from `docs/ac30_wiring1a.jpg`.
- **`AC30_moddemod_power.kicad_sch` (sheet 2): the rest of the BOM, unwired.** That's IC1–IC5, IC16, R1–R22, C1–C11, T1, F1 and so on. The only connections are the obvious ones: CMOS supply pins and the 7805 output. A note on the sheet summarizes the theory-of-operation text to help with wiring it later.
- **`AC30.kicad_sym`:** custom symbols for the MC1488, MC1489 and the reed relay, which aren't in the stock KiCad libraries.
- **`tools/`:** the generator scripts. The transcribed netlist is in `tools/netlist.py`, and `python3 -I tools/gen.py .` rebuilds the files.

**Layout:** this is not a redraw of the original drawing. Each pin has a short wire ending in a net label, and parts are grouped by function. Connections are exact, but you read it like a netlist rather than tracing wires.

**Checks I ran**
- Every BOM designator appears exactly once. J1–J11 are extra, since they're on the drawings but not in the BOM.
- The netlist exported from KiCad matches my transcription pin for pin.
- ERC shows no problems on sheet 1 except nets that lead to the unwired sheet 2. Sheet 2 reports about 180 unconnected pins, which is expected.
- It opens and plots in KiCad 10.0.4.

**Things to check, since I read them off a scanned drawing (also noted on the sheet):**
- **Two pin-number errors on the drawing.** I corrected them to the real chip pinouts:
  - IC7D is labelled 8→9; on a 4049 that section is 9→10.
  - IC13C's inputs are labelled 7 and 8; on a 4070 they're 8 and 9, and pin 7 is ground.
- **Assumed, not shown on the drawing:**
  - The 4053 INH and VEE pins are tied to ground.
  - The 555's pins 4 and 8 go to +5V.
  - The 1488's supply pins are brought out as `V_RS232+` and `V_RS232-`, with the source unknown.
- **Pin numbers on J1–J5** follow the order on the wiring diagram and haven't been checked against a real board.
- **MIC/EAR jacks:** I assigned J6–J9 arbitrarily; J10 and J11 are the motor jacks.
- **Switch S6** isn't on the switching schematic, so I left it unwired on sheet 2.
- **R39 (200K trim)** isn't on the drawing either; it may belong in the 555 timing circuit. It's on sheet 2 for now.

Nothing is committed yet. If you can find the mod/demod and power supply schematic, I can wire sheet 2 the same way.

---

## 2. User

> Save what you have but provide solder pads and labels for the missing power and mod/demod

### Work done (summary)

1. **Saved the current state.** Claude created branch `kicad-schematic` and committed the project as it stood (`5476760`).
2. **Replaced the unwired parts with pads.** In `netlist.py`, the unwired mod/demod and power BOM parts were moved to sheet `'omitted'`, so they are kept for reference but not placed. Fifteen `Connector:TestPoint` solder pads (TP1–TP15) were added on sheet 2, using footprint `Connector_Wire:SolderWire-0.5sqmm_1x01_D0.9mm_OD2.1mm`.
3. **Fixed power flags.** PWR_FLAGs went on +5V, GND, V_RS232+ and V_RS232−, because the supplies now enter through pads.
4. **Verified and committed.** ERC exited with 0 violations. Claude regenerated, rendered and checked sheet 2, then committed (`ab95554`).

### Claude's answer

Both changes are committed on a new branch, `kicad-schematic`. I branched instead of committing to `main`, and nothing is pushed. Your edit to `README.md` is still uncommitted.

**Commits**
1. `5476760`: the schematic as it was, with the mod/demod and power parts placed but unwired.
2. `ab95554`: sheet 2 is now **Mod/Demod & Power pads**. Each signal or supply that crosses into the missing circuits goes to its own labelled solder pad, using a 0.9 mm drill / 2.1 mm wire pad footprint:

| Pad | Net | Direction |
|---|---|---|
| TP1 | DATA_IN | to modulator |
| TP2 | CLOCK_IN (16X) | to modulator |
| TP3 | CARRIER_EN_N | to modulator |
| TP4 | AUDIO_OUT | from modulator |
| TP5 | AUDIO_IN | to demodulator |
| TP6 | DATA_OUT | from demodulator |
| TP7 | CLOCK_OUT (16X) | from demodulator |
| TP8 | CARRIER_DETECT | from demodulator |
| TP9 | GND | mod/demod ground |
| TP10, TP11 | 18VAC_A, 18VAC_B | from J2 / T1 |
| TP12 | +5V | regulated supply in |
| TP13 | GND | power ground |
| TP14, TP15 | V_RS232+, V_RS232− | 1488 supply rails (pins 14 and 1) |

**Other changes**
- **Mod/demod and power BOM parts:** IC1–IC5, IC16, R1–R22, T1, F1 and the rest are no longer on the schematic. Unwired parts would just turn into dead footprints on a PCB. They're still listed in `kicad/tools/netlist.py`; changing `S = 'omitted'` back to `'moddemod'` there and rerunning `gen.py` places them again.
- **Unknown parts:** S6 and R39 went off the schematic with that group, since their function wasn't shown.
- **ERC is now completely clean.** It reports no violations, including none for unconnected pins. Since nothing on the board drives +5V, GND or the RS-232 rails any more, I added PWR_FLAGs to those nets.

The open questions from last time haven't changed:
- the J1–J5 pin order
- which of J6–J9 is which MIC/EAR jack
- the two pin-number slips I corrected on the original drawing (IC7D and IC13C)
- the 1488's supply voltages

---

## 3. User

> Save this entire chat to AC30-Claude.md

### Claude's answer

Saved to `AC30-Claude.md` in the repository root (this file).

---

## 4. User

> Now create the pcb from the schematics. Minimize the board size but leave a safe boarder along the edge.

### Work done (summary)

1. **Writing the board file directly.** The `pcbnew` Python module on the system was broken: SWIG type errors, then a segfault. Claude wrote `kicad/tools/pcb.py`, which builds `AC30.kicad_pcb` straight from KiCad's exported netlist as S-expression text. Each footprint carries `path`/`sheetname`/`sheetfile`, so the schematic–PCB parity check passes.
2. **Placement.**
   - Each discrete part joins the IC it shares the most signal nets with, and parts stand upright to save area.
   - Each cluster picks the internal width that gives it the smallest area.
   - Clusters are packed with a skyline packer, trying several block orders.
   - J3–J5 run along the top edge and J1/J2 along the bottom.
3. **Outline and rules.** The outline is a rectangle with a **3 mm border** around the outermost courtyards, snapped to 0.5 mm. A Power net class was set: 0.6 mm tracks for +5V, GND and the supply nets, against 0.25 mm and 0.2 mm clearance for the Default class. Copper-to-edge clearance is 0.5 mm.
4. **Routing question.** The FreeRouting jar already on the machine is an old GUI-only build. Claude asked how to route. The user chose **"Leave unrouted for now"**.

### Claude's answer (condensed)

The board was placed and outlined at **115.5 × 122 mm** with 80 footprints, but not routed. DRC showed no placement errors and 0 parity issues; the only items flagged were 212 unrouted connections. Nothing was committed. Claude also noted that this overwrote the raw-import board the user had committed in `60d7180`, and gave the command to restore it.

---

## 5. User

> Make J3, J4 and J5 match the original artwork

### Work done (summary)

Claude read the connector labels on `docs/ac30_redblue150.jpg`, the original board artwork, top view:
- J3 (COMP) and J5 (TERM) are 10-position headers and J4 is a 15-position header, Molex KK-396 at 3.96 mm pitch.
- Each signal was moved to its pad position on the artwork, with unused positions marked no-connect.

### Claude's answer (condensed)

- **J3:** 1 GND, 2 computer 16X clock out, 3 computer 16X clock in, 5 RS-232 in, 6 RS-232 out.
- **J4:** 2 GND, 4 LOCAL/REMOTE, 5 STOP RECORD, 6 +5, 7 STOP READ, 8 CONTROL INVERT, 9 START READ, 10 START RECORD, 11 terminal 16X clock out, 12 terminal clock in, 13 CARRIER DETECT, 14 CARRIER DELAY ENABLE.
- **J5:** 1 GND, 5 terminal RS-232 out, 6 terminal RS-232 in.

The wider top row reflowed the board to **156 × 98 mm**. ERC and parity were clean, and the board was still unrouted.

---

## 6. User

> Check J1 and J2 against the artwork too

### Claude's answer (condensed)

J2's 12 positions already matched the artwork. J1 has **15 pads** on the artwork, and only the first 14 are labelled, in the same order as the schematic. J1 became a 1×15 header with pin 15 unused.

During this check Claude found that `kicad 9.0.2` had been installed in place of 10.0.4 during the session. KiCad 9 had no global symbol library table, so ERC produced 206 "library not found" warnings. With a temporary library config, ERC was clean.

---

## 7. User

> Use /home/njc/bin/FreeCAD_26.3rc1-Linux-aarch64.AppImage and /home/njc/bin/kicad.AppImage instead

### Work done (summary)

- **FreeCAD:** the FreeCAD AppImage is an **aarch64** build and the machine is x86_64, so it can't run.
- **KiCad:** the KiCad AppImage is **10.0.7**. Its `AppRun` passes a tool name through, so `kicad.AppImage kicad-cli …` works, and the image bundles its own libraries.
- **Library layout:** KiCad 10 stores each stock symbol library as a `.kicad_symdir` folder, one file per symbol. Claude taught `kilib.py` to read that layout and made the library paths overridable (`KICAD_SYMBOL_DIR`, `KICAD_FOOTPRINT_DIR`).
- **New `tools/build.sh`:** mounts the AppImage for the whole run, so the generators read its KiCad 10 libraries. It runs `kicad-cli` with a private config pointing at the AppImage's own library tables. It then regenerates the schematic and board and runs ERC and DRC with the parity check.
- **Sub-sheet format:** `sch upgrade` only rewrites the root sheet, so the sub-sheet is now upgraded explicitly too.

### Claude's answer (condensed)

The project builds and checks with KiCad 10.0.7, and the files are back in KiCad 10 format. ERC was clean, and DRC showed 0 violations and 0 parity issues besides the 212 unrouted connections. Claude noted that the user's `~/.config/kicad/10.0` tables now point at the Debian 9 template, so the KiCad 10 GUI would not find the stock symbols. The config was left unchanged.

---

## 8. User

> Use /home/njc/bin/FreeCAD_26.3rc1-Linux-x86_64.AppImag

### Claude's answer (condensed)

The path was missing its final "e". The x86_64 AppImage wasn't executable, so Claude ran `chmod +x` on it. It reports **FreeCAD 26.3.0** and runs headless as `freecadcmd`.

A STEP export from KiCad loaded cleanly in FreeCAD, with 136 solids. The PCB body measured **156.0 × 101.0 × 1.51 mm**, matching the outline. The KK-396 connectors and the solder-wire pads have no 3D models in the KiCad library.

---

## 9. User

> Add the STEP export and FreeCAD check to build.sh

### Claude's answer (condensed)

- `build.sh` now writes `kicad/AC30.step` and lists the parts with no 3D model.
- It then runs `tools/fc_check.py` in headless FreeCAD. The check confirms one assembly with a PCB body whose size matches the board outline, and fails the build if it doesn't.
- `freecadcmd` doesn't pass script arguments through or show printed output, so the script takes its input and output paths from environment variables.

---

## 10. User

> Add AC30.step to .gitignore and commit

### Claude's answer (condensed)

Claude created the root `.gitignore` and committed the PCB work as **`0bced8b`** on `kicad-schematic`. It left out KiCad's local `.history/` folder.

---

## 11. User

> Add .history to .gitignore too

### Claude's answer (condensed)

Claude added `.history/` to `.gitignore` and left the change uncommitted.

---

## 12. User

> Run ERC

### Claude's answer (condensed)

ERC with the KiCad 10.0.7 AppImage: **0 errors and 0 warnings** on both sheets. The four ignored checks listed in the report are KiCad's defaults.

---

## 13. User

> Run DRC

### Claude's answer (condensed)

DRC: **0 violations and 0 parity issues**. The 212 unrouted connections remained.

---

## 14. User

> Do routing

### Work done (summary)

1. **Getting a working router.**
   - FreeRouting 2.5.0 and 2.4.1 both need Java 25, and the machine has Java 22. Claude deleted the jars it had downloaded.
   - **FreeRouting 2.1.0** (April 2025, Java 21) went to `~/bin`. It routes headless (`-de … -do … -mp 100 --gui.enabled=false`).
   - The KiCad AppImage's bundled Python 3.11 has a working `pcbnew`, which does the Specctra DSN export and SES import.
2. **Layer fix.** The PCB header copied from the KiCad demo marked F.Cu as a *power* layer, which stopped FreeRouting from routing on it. Both copper layers became signal layers.
3. **Placement fix.** On the first route, three nets could not be completed: C12–C15 sat about 110 mm from IC13. Claude made the skyline packer **wirelength-aware**:
   - each block goes to the column that minimizes height plus the wire it adds;
   - 300 random block orders are tried;
   - the score weighs 25 mm of wire against 1 mm of board height.
   The board grew to 156 × 101 mm, and the estimated signal wire fell by about 16%.
4. **New `tools/route.py`.**
   - It exports the DSN, runs FreeRouting and imports the SES.
   - It removes the duplicate and dead-end stubs FreeRouting leaves behind; those had caused "track has unconnected end" warnings.
   - It repeats while anything is unrouted.
   - `build.sh` runs it after placement; `ROUTE=0` skips routing.
5. **Build-script fix.** The exit trap failed under `set -e` when the AppImage mount had already gone; Claude fixed it.

### Claude's answer (condensed)

**Fully routed: 0 unrouted connections, 0 DRC violations and 0 parity issues.** The routing had 1,085 segments and 50 vias, with 0.6 mm tracks on the power nets. Routing changes on every build. Nothing was committed.

---

## 15. User

> Create an AC30-settings.md file with all the settings, drill bits, trace minimus, measurements, etc.

### Claude's answer (condensed)

Claude created `AC30-settings.md`, with every value read from the board using KiCad's own tools. It covers:
- board size and stackup;
- DRC rules in mm and mils;
- net classes;
- a drill table: each hole size with its inch and number-drill equivalents, hole counts, and which parts use it;
- annular rings;
- routing figures;
- connector positions;
- a pin-1 placement table for every part;
- tool versions and generator settings.

It flagged that the board had no mounting holes and no ground fill.

---

## 16. User

> Add the four corner mounting holes to match the artwork

### Work done (summary)

1. **Measuring the artwork.** Claude used the 3.96 mm connector pitch as the scale (5.754 px/mm). It fitted each skewed edge of the board outline and measured each hole from its two nearest edges. The holes came out 5.7–6.5 mm in, averaging 6.2 mm, which points to a **¼ in (6.35 mm) inset**. The pads are about 4.6 mm across, which suits a ⅛ in / 3.2 mm hole.
2. **Adding the holes.**
   - H1–H4 went on the schematic as `Mechanical:MountingHole` symbols, excluded from the BOM, so parity stays clean.
   - They use the 3.2 mm unplated M3 footprint.
   - `pcb.py` places them 6.35 mm in from each corner of the final outline.
   - The connector rows are moved in to clear the holes.

### Claude's answer (condensed)

The holes were placed exactly 6.35 mm in from each edge, and the board became **173.0 × 97.5 mm**. It was routed with ERC, DRC and parity clean, and `AC30-settings.md` gained a Mounting holes section.

---

## 17. User

> Update kicad with @docs/ac30_mod_demod.pdf

### Work done (summary)

1. **Reading the scan.** The PDF is a single scanned page, white on black and rotated. Claude extracted it, inverted and rotated it, and traced every net at full resolution. Gaps in a line are crossings, as on the switching drawing.
2. **Wiring sheet 2.**
   - **Modulator:** IC5B divides CLOCK IN by 2 and clocks IC5A, which divides by 1 or 2 under DATA IN, through IC2A and C1/R1. IC4A with R2, R3, C2 and C3 is a 2-pole filter, feeding the R6/R7 divider and C4 to AUDIO OUT.
   - **Demodulator:**
     - IC4B is a comparator with R10 hysteresis, D1/D2 input clamps and a D3 4.7 V clamp;
     - IC3C/D generate a pulse on each edge;
     - carrier detect is D4, C7, Q3, IC3A and the IC2B/Q2 missing-pulse detector;
     - the 1200 Hz timer is Q1, C8 and R16;
     - IC1A gives DATA OUT, and IC2D/IC3B/Q4 give the 16X CLOCK OUT.
3. **Interface.** The interface nets now join the switching circuit directly, and the nine mod/demod solder pads were removed.
4. **Placement fix.** The first route left one 18 VAC connection unrouted. The placer now weighs every net except +5V and GND.
5. **Build fix.** A stale AppImage mount from an earlier check made a new mount exit immediately. `build.sh` now tolerates an existing mount.

### Claude's answer (condensed)

All 436 board pins matched the transcription. The board became **173.0 × 121.5 mm**, fully routed with ERC, DRC and parity clean.

Assumptions:
- IC4 runs from the ±7.5 V zener rails, per the assembly manual.
- R16's unlabelled far end is +5 V.
- IC1B's unused inputs are tied to GND.
- The manual's "IC2A" pulse inverter is IC2C on the schematic.

---

## 18. User

> Update kicad and pcb with an external power supply from @docs/ac_PS.pdf. Provide through hole pads for the power.

### Work done (summary)

1. **Transcription.** The file is `docs/ac30_PS.pdf`, with outputs **+5, +13, +7.5, −13, −7.5 VDC and GND**.
   - 120 VAC goes through S6 and F1 to T1's two 120 V primaries, which are wired in parallel.
   - The 18 VAC centre-tapped secondary, tap to GND, feeds the D14–D17 bridge, giving +13 V on C21 and −13 V on C22.
   - R48/D12 and R49/D13 make ±7.5 V, and IC16 (7805) makes +5 V.
2. **Drafting error corrected.** The drawing joins IC16's GND and C23–C25 return line to the bridge's −13 V corner, through two crossings. That would make the 7805 put out about −8 V, so it was taken as GND.
3. **Sheet 3, "Power supply (external)".**
   - Its parts have **no footprints**: they're in the schematic and BOM but not on the PCB.
   - `gen.py` was generalized to write any number of sub-sheets and set the project's sheet list.
   - PWR_FLAGs went on GND, the ±13 V and ±7.5 V rails, and the mains L line. The plug's L pin is a power input.
4. **Board side.**
   - Six through-hole pads (TP1–TP6: +5V, GND, +13V, −13V, +7.5V, −7.5V).
   - C23–C25 stay on the board as +5 V bypass, as on the artwork.
   - IC4 moved to ±7.5 V, and IC15 (1488) went on ±13 V, the only load left for those outputs.
   - J2's 18 VAC pins became unused.
5. **Verification.** KiCad's XML netlist, which includes parts that aren't on the board, matched the transcription on all 518 pins.

---

## 19. User

> ave you updated the PCB with everything to this point?

### Claude's answer (condensed)

Not yet. The schematic and placement were done, but the routed build was still running. The settings document still described the earlier board.

---

## 20. User

> ok, finish it and then commit

### Work done (summary)

1. **A short in the routing.** The routed build finished with 0 unrouted, but its later rounds had added 4 clearance violations and a **short (TERM_CLK_OUT/TERM_ECHO)**. FreeRouting re-routing on top of its own tracks causes these.
2. **Retrying from scratch.** `build.sh` now routes the placed board from scratch up to 4 times, one round each, and keeps the first result whose KiCad DRC is completely clean. Otherwise it keeps the fewest-items result and warns.
3. **Pad labels.**
   - The TP pads show their rail name on the silkscreen.
   - The labels first overlapped the next pad's reference text, causing 4 `silk_overlap` warnings. The pad references were moved to the fab layer in `pcb.py`.
   - The same edit was applied to the routed board, rather than re-routing for 40 minutes.
4. **Commit.** `AC30-settings.md` was updated with a Power input section. Claude committed **`2b26e99`** on a new branch, `kicad-moddemod-psu`, since the repo was on `main`.

### Claude's answer (condensed)

The board was 173.0 × 121.5 mm, fully routed, with ERC, DRC (all severities) and parity clean. The user's README and BOM edits were left uncommitted. The KiCad GUI had the project open, so Claude warned against saving from it before reloading.

---

## 21. User

> Check your current task stack or running bash commands and report whether anything is deadlocked or waiting for input.

### Claude's answer (condensed)

Nothing was waiting for input, but two of Claude's background "wait for the build" loops were stuck. They used `until ! pgrep -f "tools/build.sh"`, and that pattern also matched the loop's own command line, so they could never end. Claude stopped both, and no processes were left running. The loops had never touched any files.

---

## 22. User

> merge it into main

### Claude's answer (condensed)

KiCad had re-saved `AC30.kicad_pro` after the commit; the re-save only reorders keys. Claude stashed that file, fast-forwarded `main` to `2b26e99`, and restored the re-save unchanged.

---

## 23. User

> push it

### Claude's answer (condensed)

Pushed `main` to `github.com:linuxha/AC30` (`e8dbe58..2b26e99`).

---

## 24. User

> Has the mod demod and power supply connectors been added to the PCB. I don't see power connectors

### Claude's answer (condensed)

The mod/demod is built on the board, so it needs no connector. The power input was six small solder pads (TP1–TP6) in the middle-left of the board, which are easy to miss. Claude offered a 6-pin KK-396 header on the board edge, or a 5.08 mm screw terminal.

---

## 25. User

> Use a 6-pin KK-396 connector on the board edge

### Work done (summary)

**J12** (Molex KK-396 A-41791-0006) replaced TP1–TP6, in the bottom connector row next to J2 and clear of the corner hole. Its pinout is **1 GND, 2 +5V, 3 +13V, 4 −13V, 5 +7.5V, 6 −7.5V**, with GND on pin 1 as on J3 and J5. The KK housing is keyed. A placement-only build was clean.

---

## 26. User

> ok, finish it and then commit

## 27. User

> push it

### Work done (summary)

1. **Routing.** None of the 4 fresh attempts was clean; the best one left one connection unrouted (LED_READ_DATA, J1 pin 3 to R37).
2. **Finishing pass.** One that kept the existing tracks and routed only that connection gave a **completely clean DRC**. `build.sh` now runs up to 3 such finishing passes, each checked by DRC.
3. **Settings.** `AC30-settings.md` was updated:
   - the J12 pinout replaced the pad table;
   - the drill table went to 542 holes, with six more 1.7 mm holes and no 1.15 mm holes;
   - the routing figures and positions were refreshed.
4. **Commit and push.** Committed **`53b935b`** on `kicad-power-connector`, fast-forwarded `main`, and pushed (`2b26e99..53b935b`, including the user's own README commit `ae7fbe3`).

### Claude's answer (condensed)

The board is **173.5 × 122.0 mm** with 119 footprints, fully routed:

| Check | Result |
|---|---|
| ERC | 0 violations |
| Unrouted connections | 0 |
| DRC | 0 violations at every severity |
| Schematic parity | 0 issues |
| FreeCAD check | OK |

---

## 28. User

> delete the merged branches

### Claude's answer (condensed)

Deleted the local branches `kicad-moddemod-psu` and `kicad-power-connector` with `git branch -d`; both were already merged. Only `main` remains, matching `origin/main`.

---

## 29. User

> update AC30-Claude.md with this session

### Claude's answer

Added sections 4–29 to this file and brought the appendix up to date.

---

## State at the end of the session

| Item | State |
|---|---|
| Schematic sheet 1 | Switching circuit (`docs/ac30_schematica.jpg`) |
| Schematic sheet 2 | Modulator/demodulator (`docs/ac30_mod_demod.pdf`), power input J12, C23–C25 bypass, H1–H4 |
| Schematic sheet 3 | Power supply (`docs/ac30_PS.pdf`), external: no footprints |
| PCB | 173.5 × 122.0 mm, 2 layers, 119 through-hole footprints, fully routed; ERC, DRC and parity clean |
| Connectors | J1–J5 match the original artwork; J12 is the new power input |
| Mounting holes | 4 × 3.2 mm, 6.35 mm in from each corner |
| Build | `cd kicad && tools/build.sh`: regenerate, ERC, place, route (retry plus finishing passes), DRC, STEP export, FreeCAD check |
| Tools | KiCad 10.0.7 AppImage, FreeRouting 2.1.0 (Java 22), FreeCAD 26.3.0 AppImage |
| Reference | `AC30-settings.md`: rules, drill table, holes, connectors, placement |
| Not placed | R39 (200K DELAY trimmer), which is on no schematic |

---

## Appendix: key nets

The authoritative copy is `kicad/tools/netlist.py`. Key nets, named from the AC-30's point of view. Connector pin numbers are as on the final board, with J1–J5 matching the artwork (sections 5–6):

| Net | Connections |
|---|---|
| LOCAL_REMOTE | R41 (pull-up), S7, J1.8, J4.4, IC11D.13, IC11B.6, IC6.11, IC6.9, IC7E.11, IC14.10, IC14.11 |
| REMOTE_N | IC7E.12 → IC11A.1 |
| READ_ACTIVE_N | IC9A.9 → IC11B.5, IC11A.2 |
| SEL_CPU_CLK / SEL_TERM_CLK | IC11B.4 → IC6.10 / IC11A.3 → IC14.9 |
| READ_EN / READ_EN_N | IC8A Q (1) → IC9A.1, IC9B.5, R29 / IC8A Q̅ (2) → R33 → Q10 |
| REC_EN / REC_EN_N | IC8B Q (13) → IC9C.12, R28, Q11 base, IC10.2 / IC8B Q̅ (12) → R32 → Q9 |
| CPU_DATA | IC12A out (3) → IC6.12, IC14.12 |
| TERM_DATA | IC12B out (6) → IC7D in, IC14.1, IC6.13 |
| TAPE_DATA_N / TAPE_DATA | IC9B.6 → IC7B.5, IC14.13 / IC7B.4 → IC11C.9, R36 (READ DATA LED) |
| DATA_SEL → DATA_IN | IC6.14 → IC7F → IC9C.11; IC9C.10 → IC7C → DATA_IN (IC2A pin 1), R34 (REC DATA LED) |
| CLOCK_OUT (demod) | Q4 collector / R22, IC6.1, IC14.3 |
| CLOCK_IN (mod) | IC6.4 → IC5B C (pin 11) |
| CPU_CLK_OUT / TERM_CLK_OUT | D8/D9 clamps, IC6.2, IC6.5 / D10/D11 clamps, IC14.5, IC6.3 |
| CARRIER_DETECT | IC3A.3 (demod), IC9A.2, IC9B.4, J4.13 |
| CARRIER_EN_N | R40 (from 555 out), S1 pole 1 (MAN → GND), J2.9, J4.14, IC5B R (pin 10) |
| Latch set/reset | IC13 XOR (CTRL_INVERT common input) → C12/C13/C14/C15 → IC8 S/R; R23–R26, S4/S5; power-on reset via C16/D5/R27 |
| Relay drive | Q9/Q10 collectors → S2/S3 A/B poles → RELAY_1/RELAY_2 → RLY1/RLY2 coils; MAN_MOTOR via D6/D7 |
| Audio | AUDIO_OUT → S2 → MIC A/B; EAR A/B → S3 → AUDIO_IN |
| DATA_OUT (demod) | IC1A Q (pin 1) → IC9.3 |
| AUDIO_OUT / AUDIO_IN | C4 → J2.7 → S2 → MIC A/B; EAR A/B → S3 → J2.8 → R8, C5 |
| DEM_PULSE | IC2C out (pin 10) → IC1A C, IC2D.12, R13 (Q1 timer), R14 (Q2 missing-pulse) |
| Power rails | J12: 1 GND, 2 +5V, 3 +13V (IC15.14), 4 −13V (IC15.1), 5 +7.5V (IC4.8), 6 −7.5V (IC4.4) |
