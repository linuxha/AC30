"""FreeCAD check of the exported board STEP (run with freecadcmd).
freecadcmd swallows stdout and script arguments, so input and output go through
environment variables: AC30_STEP (STEP file in), AC30_FC_OUT (report out).
Report lines: 'pcb <x> <y> <z>' (board body size, mm), 'solids <n>',
'assembly <x> <y> <z>'; or 'error <message>'."""
import os, traceback
import FreeCAD, Import

with open(os.environ['AC30_FC_OUT'], 'w') as out:
    try:
        doc = FreeCAD.newDocument('AC30')
        Import.insert(os.environ['AC30_STEP'], doc.Name)
        pcb = [o for o in doc.Objects if o.Label.endswith('_PCB')]
        top = [o for o in doc.Objects if not o.InList]
        if not pcb or len(top) != 1:
            raise RuntimeError(f'expected one assembly with a _PCB body, got {[o.Label for o in top]}')
        solids = [o for o in doc.Objects if o.TypeId == 'Part::Feature' and o.Shape.Solids]
        for name, b in (('pcb', pcb[0].Shape.BoundBox), ('assembly', top[0].Shape.BoundBox)):
            print(f'{name} {b.XLength:.1f} {b.YLength:.1f} {b.ZLength:.2f}', file=out)
        print(f'solids {len(solids)}', file=out)
    except Exception:
        print('error ' + traceback.format_exc().replace('\n', ' | '), file=out)
