# Parts List AC-30 Audio Cassette Interface

## # Resistors

|-----------------------------+----------------------------+---------------------------------------+---|
|                             |                            |                                       |   |
|-----------------------------+----------------------------+---------------------------------------+---|
| R1                          | 33K ohm 1/4 watt resistor  | Mouser Part # 660-MF1/4LCT52R333J %5  |   |
|                             |                            | Mouser Part # 660-MF1/4DCT52R3302F %1 |   |
| R2, R3, R9, R11, R12, R15   | 10K ohm 1/4 watt resistor  |                                       |   |
| R19-R22, R27 R29, R32-R34   | 10K ohm 1/4 watt resistor  |                                       |   |
| R36, R40-R42, R44-R47       | 10K ohm 1/4 watt resistor  |                                       |   |
| R4, R48, R49                | 330 ohm 1/4 watt resistor  | PS R48 R49                            |   |
| R5 2.2K                     | ohm l/4 watt resistor      |                                       |   |
| R6 4.7K                     | ohm 1/4 watt resistor      |                                       |   |
| R7, R30, R31, R35, R37, R43 | 470 ohm 1/4 watt resistor  |                                       |   |
| R8, R17, R18, R23-R26       | 100K ohm 1/4 watt resistor |                                       |   |
| R10                         | 330K ohm 1/4 watt resistor |                                       |   |
| R13, R14                    | 22K ohm 1/4 watt resistor  |                                       |   |
| R16                         | 20K ohm trimmer resistor   |                                       |   |
| R38                         | 47K ohm 1/4 watt resistor  |                                       |   |
| R39                         | 200K ohm trimmer resistor  |                                       |   |
|-----------------------------+----------------------------+---------------------------------------+---|

## Capacitors

|-----------------|-----------------------------------------|----------|---|
|                 |                                         |          |   |
|-----------------|-----------------------------------------|----------|---|
| C1, C6, C12-C15 | 1000 pfd capacitor                      |          |   |
| C2              | 2000 pfd capacitor                      |          |   |
| C3, C8          | O.022 mfd capacitor                     |          |   |
| C4              | 1 mfd @15 VDC electrolytic capacitor    |          |   |
| C5, C18         | 0.01 mfd capacitor                      |          |   |
| C7, C9          | 0.047 mfd capacitor                     |          |   |
| C10             | 2700 pfd capacitor                      |          |   |
| C11, C19, C20   | 470 pfd capacitor                       |          |   |
| C16, C22        | 100 mfd @16 VDC electrolytic capacitor  | PS - C22 |   |
| C17             | 10 mfd @10 VDC tantalum, capacitor      |          |   |
| C21             | 1000 mfd @25 VDC electrolytic capacitor | PS       |   |
| C23-C25         | 0.1 mfd disc capacitor                  | PS       |   |
|-----------------|-----------------------------------------|----------|---|


## Semiconductors

|--------------------+---------------------------------+---------------------+-----|
|                    |                                 |                     |     |
|--------------------+---------------------------------+---------------------+-----|
| ICI, IC5, IC8      | CD4013 dual D flip-flop         | Digi                | ✅ |
| IC2, IC11          | CD4001 quad NOR gate            | Digi                | ✅ |
| IC3, IC13          | CD4070 quad EX-OR gate          | Digi                | ✅ |
| IC4                | CD4558 dual op amp              | EBay                | ✅ |
| IC6, IC14          | CD4053 triple multiplexer       |                     | ✅ |
| IC7                | CD4049 hex buffer               |                     | ✅ |
| IC9                | CD4023 triple 3-input NAND gate |                     | ✅ |
| IC10               | 555 timer                       |                     | ✅ |
| IC12               | 1489 quad RS-232 receiver       |                     | ✅ |
| IC15               | 1488 quad RS-232 transmitter    |                     | ✅ |
| IC16               | 7805 5 VDC regulator            |                     | ✅ |
| D1, D2, D4, D5-D11 | 1N4148 silicon diode            |                     |     |
| D3                 | 4.7 volt zener diode IN5230     | 1N4732 or IN5230    |     |
| D12, D13           | 7.5 volt zener diode 1N4737     | PS 1N4737 or 1N5236 |     |
| D14-D17            | 1N4003 silicon rectifier        | PS                  |     |
| D18-D22            | light emitting diode            |                     |     |
| Q1, Q2, Q4-Q8      | 2N5210 NPN transistor           |                     |     |
| Q3, Q9-Q11         | 2N5087 PNP transistor           |                     |     |
|--------------------+---------------------------------+---------------------+-----|


## Misc.

|------------|-----------------------------------------|-------|---|
|            |                                         |       |   |
|------------|-----------------------------------------|-------|---|
| RLY1, RLY2 | 6 VDC reed relay                        |       |   |
| S1-S3      | DPDT miniature toggle switch            |       |   |
| S4, SS     | SPDT center off miniature toggle switch |       |   |
| S6, S7     | SPDT miniature toggle switch            | PS S6 |   |
| T1         | 18 VAC @300 Ma. secondary 120/240 VAC   | PS    |   |
|            | 50-60 Hz primary power transformer      |       |   |
| F1         | 1 amp standard fuse                     | PS    |   |
|------------|-----------------------------------------|-------|---|


## Reproduction PCB additions (both boards)

These parts aren't on the original parts list above. They come from the reproduction
boards (`kicad/AC30.kicad_pcb` through-hole, `kicad-smt/AC30_SMT.kicad_pcb` SMT).

|-----------------------|--------------------------------------------------|----------------------------------------------|---|
| Ref                   | Part                                             | Notes                                        |   |
|-----------------------|--------------------------------------------------|----------------------------------------------|---|
| J3, J5                | Molex KK-396 1x10 vertical header (A-41791-0010) | COMP and TERM interfaces, top edge           |   |
| J4                    | Molex KK-396 1x15 vertical header (A-41791-0015) | Control interface, top edge                  |   |
| J12                   | Molex KK-396 1x6 vertical header (A-41791-0006)  | Power input from the external supply         |   |
|                       | Molex KK-396 crimp housings and terminals        | One mating housing each for J3, J4, J5, J12  |   |
| J1                    | SWITCHES wire pads, 19 x 0.1 in, 1.0 mm holes    | Front panel; no part, solder wires (*)       |   |
| J2                    | LEDS wire pads, 5 x 0.1 in                       | Front panel; no part, solder wires (*)       |   |
| J13                   | MOTOR wire pads, 4 x 0.1 in                      | Motor jacks J10/J11; no part (*)             |   |
| J14                   | MIC wire pads, 4 x 0.1 in                        | MIC A/B jacks J6/J7; no part (*)             |   |
| J15                   | EAR wire pads, 4 x 0.1 in                        | EAR A/B jacks J8/J9; no part (*)             |   |
| J6-J9                 | Mono phone jack                                  | Front panel: MIC A, MIC B, EAR A, EAR B      |   |
| J10, J11              | Mono phone jack                                  | Front panel: MOTOR A, MOTOR B (remote)       |   |
| C23-C25               | 0.1 mfd capacitor                                | On the board as +5 V bypass, not on the PS   |   |
| H1-H4                 | #4 or M3 screw and standoff                      | 3.2 mm mounting holes, 1/4 in from corners   |   |
|                       | Hook-up wire, 22-24 AWG                          | Front panel to the wire pads                 |   |
|-----------------------|--------------------------------------------------|----------------------------------------------|---|

(*) The wire pads fit a 0.1 in single-row pin header (1x19, 1x5, 1x4) if you'd rather
plug the front panel in than solder it. The original J1/J2 front-panel harness headers
and the J2 18 VAC pins are not used: the power supply is a separate unit.

R39 (200K trimmer) is on the parts list but on no schematic, so it isn't on either board.

## SMT board substitutions

The SMT board (`kicad-smt/AC30_SMT.kicad_pcb`) uses these parts in place of the
through-hole ones. Everything else on the list above is the same, and the connectors,
wire pads, front panel and power supply are identical on both boards.

|------------------------------------|--------------------------------|------------------------------|---|
| Refs                               | SMT part                       | Package                      |   |
|------------------------------------|--------------------------------|------------------------------|---|
| R1-R15, R17-R38, R40-R47           | 1/8 watt resistor, same values | 0805                         |   |
| R16                                | 20K trimmer, Bourns 3314G      | 3314G                        |   |
| C1-C3, C5-C15, C18-C20, C23-C25    | Ceramic capacitor, same values | 0805                         |   |
| C4, C17                            | 1 mfd 15 V / 10 mfd 10 V tant. | EIA-3216 (A case)            |   |
| C16                                | 100 mfd 16 V aluminium         | 6.3 x 7.7 mm can             |   |
| D1, D2, D4-D11                     | 1N4148W                        | SOD-123                      |   |
| D3                                 | BZT52C4V7 4.7 V zener          | SOD-123                      |   |
| D18                                | LED                            | 1206                         |   |
| Q1, Q2, Q4-Q8                      | MMBT5088 (for 2N5210)          | SOT-23                       |   |
| Q3, Q9-Q11                         | MMBT5087                       | SOT-23                       |   |
| IC1-IC3, IC5, IC8, IC9, IC11-IC13, IC15 | SOIC versions (CD4013BM, MC1488D, MC1489D ...) | SOIC-14  |   |
| IC6, IC7, IC14                     | CD4053BM, CD4049UBM            | SOIC-16                      |   |
| IC4, IC10                          | RC4558D, NE555D                | SOIC-8                       |   |
| RLY1, RLY2                         | Omron G6K-2F-Y 5 VDC (for 6 V reed relay) | SMD DPDT, check coil polarity |   |
|------------------------------------|--------------------------------|------------------------------|---|

## KiCad BOM files

`kicad/tools/build.sh` exports a BOM from each schematic on every build:
`kicad/AC30-BOM.csv` (through-hole) and `kicad-smt/AC30_SMT-BOM.csv` (SMT). They list
every part with its value and footprint; front-panel and power-supply parts are marked
"Excluded from board".
