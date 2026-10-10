![SWTPC AC30 Cassette Interface](images/SWTPC_AC30_Cassette_Interface.jpg)

# SWTPC AC30 Reproduction
A reproduction SWTPC AC-30 Cassette Interface

## Description

I have a couple of Motorola MC6800, MC6802, and MC6809 machines from the 1970's. And I wanted to
setup a typical cassette plater/recorder setup to save and load code written on these machines.

**Note:**2026/10/10 - Both boards (through-hole `kicad/AC30` and SMT `kicad-smt/AC30_SMT`) now wire the front panel (switches, LEDs, motor jacks, MIC A/B and EAR A/B jacks) to labelled through-hole wire pads instead of the J1/J2 Molex connectors. Board details are in [AC30-settings.md](AC30-settings.md) and [AC30-SMT-settings.md](AC30-SMT-settings.md); the parts list is [docs/AC30-BOM.md](docs/AC30-BOM.md), with KiCad BOMs in `kicad/AC30-BOM.csv` and `kicad-smt/AC30_SMT-BOM.csv`.

Board sizes are now 173.0 x 126.5 mm (6.8" x 5.0") through-hole and 173.0 x 88.5 mm (6.8" x 3.5") SMT. Gerbers and drill files for both boards are ready for the board house: [kicad/AC30-gerbers.zip](kicad/AC30-gerbers.zip) (through-hole) and [kicad-smt/AC30_SMT-gerbers.zip](kicad-smt/AC30_SMT-gerbers.zip) (SMT, including the top paste layer for a stencil). `kicad/tools/build.sh` regenerates them on every build, or run `kicad/tools/gerbers.sh` (add `smt` for the SMT board).

2026/10/09 - I've update the PCB to add the mod/demod circuits and a molex for the power. Additionally I had a new SMT version created.

2026/10/08 - This is my first go around with Claude, Kicad and FreeCAD and creating a PCB to be sent off as gerbers. I have a lot of inspecting to do. But for a 1st go this is scary impressive.

## Claude created Kicad files

I gave Claude the following prompts:

```text
Create a kicad schematic for docs/AC30-BOM.md docs/ac30_schematica.jpg
```

and


```text
Save what you have but provide solder pads and labels for the missing power and mod/demod
```

and


```text
Now create the pcb from the schematics. Minimize the board size but leave a safe boarder along the edge.
```

After this I use a few suggested prompts.

Here's what the inside of the Original SWTPC AC30:

![SWTPC AC30 Cassette Interface insides](images/ac30_back_640.jpg)

I'd estimate the board to be about 9" x 9" (inches) in size. Here's the schematics I gave Claude:

![SWTPC AC30 Cassette Interface schematic](docs/ac30_schematica.jpg)

I gave it the [AC30/docs/AC30-BOM.md](BOM) file (simple markdown text file).

Claude started churning and created a 'schematic' (doesn't look like the above, hard to read) and I imported it into the PCB editor. Then didn't make any changes. Instead I let Claude do the rerouting.

I then found out I needed to upgrade Kicad to 10.7 and FreeCAD 26.3 so Claude could create Python 3.11 scripts to build a schematic, the PCB and routing. That was messy as I have Debian Trixie and the latest wants Debian Forky. Anyway, this is the final 1st round attempt. More cleanup to do yet before I ship off the gerbers.

I'd estimate the size of the new PCB to be about 3.5" x 7" (inches).

![New AC30 Cassette Interface part placement](images/AC30-PCB-Parts.png)

![New AC30 Cassette Interface Red/Blue](images/AC30-PCB-Red-Blue.png)

So after several hours, including the Kicad/FreeCAD SNAFU, those are the results. The TPx are where I just dumped a bunch of jumpers I hadn't decided on. I'll fix those later. While it's not done it's a huge jump. It would have taken me about two weeks to get all the parts on the schematic, connections defined and PCB routed.

## Credits

I stole this from [Deramp's AC30 (Mike)](https://www.swtpc.com/mholley/ac30/ac30_index.html) site.
And he saved it from Mike Holley's original SWTPC site.

## Links

- [Deramp's AC30 page](https://www.swtpc.com/mholley/ac30/ac30_index.html)
