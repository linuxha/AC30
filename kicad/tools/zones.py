#!/usr/bin/env python3
"""Add the GND copper fill to a routed board: one zone on F.Cu and B.Cu covering the
whole board outline. The zone is written unfilled; `kicad-cli pcb drc --refill-zones
--save-board` fills it (build.sh).

GND pads connect to the fill through thermal reliefs (easier hand soldering, less
tombstoning). Where routed tracks leave a relief with only a spoke into an isolated
scrap of fill, DRC reports a starved thermal; --solid gives just those pads a solid
connection instead.

Usage: python3 -I zones.py <board.kicad_pcb>
       python3 -I zones.py --solid <board.kicad_pcb> <drc.json>
"""
import json, re, sys, uuid

NS = uuid.UUID('6f1d6c0e-5a3e-4c55-9d43-ac30ac30ac31')
CLEARANCE = 0.3          # mm, zone to other nets
MIN_WIDTH = 0.25         # mm, thinnest fill
THERMAL_GAP = 0.5        # mm, pad to fill gap in the thermal relief
THERMAL_SPOKE = 0.5      # mm, thermal relief spoke width


def main(path):
    text = open(path).read()
    if '(name "GND fill")' in text:
        sys.exit('zones.py: board already has the GND fill')
    m = re.search(r'\(gr_rect\s+\(start ([\d.]+) ([\d.]+)\)\s+\(end ([\d.]+) ([\d.]+)\)'
                  r'(?:(?!\(gr_rect).)*?\(layer "Edge\.Cuts"\)', text, re.S)
    x1, y1, x2, y2 = (float(v) for v in m.groups())
    zone = f'''	(zone
		(net "GND")
		(layers "F.Cu" "B.Cu")
		(uuid "{uuid.uuid5(NS, 'zone/GND')}")
		(name "GND fill")
		(hatch edge 0.5)
		(connect_pads
			(clearance {CLEARANCE})
		)
		(min_thickness {MIN_WIDTH})
		(filled_areas_thickness no)
		(fill yes
			(thermal_gap {THERMAL_GAP})
			(thermal_bridge_width {THERMAL_SPOKE})
			(island_removal_mode 0)
		)
		(polygon
			(pts
				(xy {x1} {y1}) (xy {x2} {y1}) (xy {x2} {y2}) (xy {x1} {y2})
			)
		)
	)
'''
    end = text.rstrip().rfind(')')            # the board's closing parenthesis
    open(path, 'w').write(text[:end] + zone + text[end:])


def _blocks(text, head, start=0, end=None):
    """(start, end) of each "(<head>" element in text[start:end], matched parentheses."""
    end = len(text) if end is None else end
    for m in re.finditer(r'\(' + head + r'\b', text[start:end]):
        a = start + m.start()
        depth, b = 0, a
        while True:
            depth += {'(': 1, ')': -1}.get(text[b], 0)
            b += 1
            if depth == 0:
                break
        yield a, b


def solid(path, report):
    """Solid zone connection for the GND pads DRC reports as starved thermals."""
    pads = set()
    for v in json.load(open(report))['violations']:
        if v['type'] == 'starved_thermal':
            for it in v['items']:
                m = re.search(r'pad (\S+) \[GND\] of (\S+)', it['description'])
                if m:
                    pads.add((m.group(2), m.group(1)))
    text = open(path).read()
    edits = []
    for a, b in _blocks(text, 'footprint'):
        ref = re.search(r'\(property "Reference" "([^"]+)"', text[a:b]).group(1)
        for pa, pb in _blocks(text, 'pad', a, b):
            num = re.match(r'\(pad "([^"]*)"', text[pa:pb]).group(1)
            if (ref, num) in pads and '(zone_connect' not in text[pa:pb]:
                edits.append(pb - 1)                        # before the pad's ")"
    for pos in sorted(edits, reverse=True):
        text = text[:pos] + '\t(zone_connect 2)\n\t\t' + text[pos:]
    open(path, 'w').write(text)
    print(f'GND fill: solid connection for {len(edits)} pads '
          f'({", ".join(f"{r}.{n}" for r, n in sorted(pads))})')


if __name__ == '__main__':
    if sys.argv[1] == '--solid':
        solid(sys.argv[2], sys.argv[3])
    else:
        main(sys.argv[1])
