# AC-30 KiCad Schematic: Claude Code Session Log

Session date: 2026-10-08. Model: Claude Opus 5.5 (Claude Code CLI).

This is a record of the chat that produced the KiCad project in `kicad/`. User messages and Claude's final answers are reproduced in full. Claude's intermediate tool work (shell commands, image crops, file edits) is summarized rather than shown verbatim.

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

## Appendix: transcribed switching-circuit nets

The authoritative copy is `kicad/tools/netlist.py`. Key nets, named from the AC-30's point of view:

| Net | Connections |
|---|---|
| LOCAL_REMOTE | R41 (pull-up), S7, J1.8, J4.2, IC11D.13, IC11B.6, IC6.11, IC6.9, IC7E.11, IC14.10, IC14.11 |
| REMOTE_N | IC7E.12 → IC11A.1 |
| READ_ACTIVE_N | IC9A.9 → IC11B.5, IC11A.2 |
| SEL_CPU_CLK / SEL_TERM_CLK | IC11B.4 → IC6.10 / IC11A.3 → IC14.9 |
| READ_EN / READ_EN_N | IC8A Q (1) → IC9A.1, IC9B.5, R29 / IC8A Q̅ (2) → R33 → Q10 |
| REC_EN / REC_EN_N | IC8B Q (13) → IC9C.12, R28, Q11 base, IC10.2 / IC8B Q̅ (12) → R32 → Q9 |
| CPU_DATA | IC12A out (3) → IC6.12, IC14.12 |
| TERM_DATA | IC12B out (6) → IC7D in, IC14.1, IC6.13 |
| TAPE_DATA_N / TAPE_DATA | IC9B.6 → IC7B.5, IC14.13 / IC7B.4 → IC11C.9, R36 (READ DATA LED) |
| DATA_SEL → DATA_IN | IC6.14 → IC7F → IC9C.11; IC9C.10 → IC7C → DATA_IN (modulator), R34 (REC DATA LED) |
| CLOCK_OUT (demod) | IC6.1, IC14.3 |
| CLOCK_IN (mod) | IC6.4 |
| CPU_CLK_OUT / TERM_CLK_OUT | D8/D9 clamps, IC6.2, IC6.5 / D10/D11 clamps, IC14.5, IC6.3 |
| CARRIER_DETECT | IC9A.2, IC9B.4, J4.11 |
| CARRIER_EN_N | R40 (from 555 out), S1 pole 1 (MAN → GND), J2.9, J4.12, modulator |
| Latch set/reset | IC13 XOR (CTRL_INVERT common input) → C12/C13/C14/C15 → IC8 S/R; R23–R26, S4/S5; power-on reset via C16/D5/R27 |
| Relay drive | Q9/Q10 collectors → S2/S3 A/B poles → RELAY_1/RELAY_2 → RLY1/RLY2 coils; MAN_MOTOR via D6/D7 |
| Audio | AUDIO_OUT → S2 → MIC A/B; EAR A/B → S3 → AUDIO_IN |
