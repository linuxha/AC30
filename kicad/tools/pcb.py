#!/usr/bin/env python3
"""Build AC30.kicad_pcb from the schematic netlist without the pcbnew module
(its Python bindings crash on this KiCad build).

Footprints are read from the stock libraries, nets are assigned to pads, parts
are placed compactly by functional cluster and a board outline is drawn with a
safe border.  The file is written in the KiCad 9 format; run
`kicad-cli pcb upgrade` afterwards to convert it to the current format.

Usage: python3 -I pcb.py <netlist.net> <out.kicad_pcb> [gap_mm]
"""
import copy, json, math, os, random, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, dump, find, find1, Sym

FPDIR = os.environ.get('KICAD_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
NS = uuid.UUID('6f1d6c0e-5a3e-4c55-9d43-ac30ac30ac31')
BORDER = 3.0                       # mm between outermost courtyard and board edge
ORIGIN = 30.0                      # board top-left on the drawing sheet
HOLE_INSET = 6.35                  # mounting hole centres 1/4" in from each edge (artwork)
POWER_NETS = {'+5V', 'GND', '+13V', '-13V', '+7.5V', '-7.5V'}
SCH_FILE = {'/': 'AC30.kicad_sch'}


def uid(*p):
    return str(uuid.uuid5(NS, '/'.join(map(str, p))))


# --------------------------------------------------------------------------- netlist
def read_netlist(path):
    t = parse(open(path).read())
    sheets = {}
    for s in find(find1(t, 'design'), 'sheet'):
        tb = find1(s, 'title_block')
        sheets[find1(s, 'name')[1]] = find1(tb, 'source')[1]
    comps = []
    for c in find(find1(t, 'components'), 'comp'):
        fp = find1(c, 'footprint')
        if not fp or not fp[1]:
            continue
        sp = find1(c, 'sheetpath')
        sname = find1(sp, 'names')[1]
        comps.append(dict(ref=find1(c, 'ref')[1], value=find1(c, 'value')[1], fp=fp[1],
                          path=find1(sp, 'tstamps')[1] + find1(c, 'tstamps')[1],
                          sheetname=sname, sheetfile=sheets.get(sname, 'AC30.kicad_sch')))
    pinnet, netnames = {}, []
    for n in find(find1(t, 'nets'), 'net'):
        name = find1(n, 'name')[1]
        netnames.append(name)
        for node in find(n, 'node'):
            pinnet[(find1(node, 'ref')[1], find1(node, 'pin')[1])] = name
    return comps, pinnet, netnames


# --------------------------------------------------------------------------- footprints
class Part:
    def __init__(self, comp, pinnet):
        self.c = comp
        self.ref = comp['ref']
        lib, name = comp['fp'].split(':')
        self.tree = parse(open(os.path.join(FPDIR, lib + '.pretty', name + '.kicad_mod')).read())
        self.rot = 0
        self.x = self.y = 0.0
        self.nets = {p[1]: pinnet.get((self.ref, p[1])) for p in find(self.tree, 'pad')}
        self.local_bbox = self._courtyard()

    def _courtyard(self):
        xs, ys = [], []
        for g in self.tree:
            if not (isinstance(g, list) and g and g[0] in ('fp_line', 'fp_rect', 'fp_circle', 'fp_poly', 'fp_arc')):
                continue
            layer = find1(g, 'layer')
            if not layer or layer[1] != 'F.CrtYd':
                continue
            if g[0] == 'fp_circle':
                c, e = find1(g, 'center'), find1(g, 'end')
                r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
            elif g[0] == 'fp_poly':
                for xy in find(find1(g, 'pts'), 'xy'):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            else:
                for k in ('start', 'end', 'mid'):
                    v = find1(g, k)
                    if v:
                        xs.append(float(v[1])); ys.append(float(v[2]))
        if not xs:   # no courtyard: use pads
            for p in find(self.tree, 'pad'):
                at, sz = find1(p, 'at'), find1(p, 'size')
                xs += [float(at[1]) - float(sz[1]) / 2, float(at[1]) + float(sz[1]) / 2]
                ys += [float(at[2]) - float(sz[2]) / 2, float(at[2]) + float(sz[2]) / 2]
        return min(xs), min(ys), max(xs), max(ys)

    def bbox(self):
        """Courtyard bbox in board coordinates for the current position/rotation."""
        x1, y1, x2, y2 = self.local_bbox
        pts = [self._xf(x, y) for x, y in ((x1, y1), (x1, y2), (x2, y1), (x2, y2))]
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))

    def _xf(self, x, y):
        r = math.radians(self.rot)
        return (self.x + x * math.cos(r) + y * math.sin(r),
                self.y - x * math.sin(r) + y * math.cos(r))

    def size(self):
        x1, y1, x2, y2 = self.bbox()
        return x2 - x1, y2 - y1

    def move_to(self, x, y):
        """Put the courtyard's top-left corner at (x, y), on a 0.05 mm grid."""
        x1, y1, _, _ = self.bbox()
        self.x = round((self.x + x - x1) / 0.05) * 0.05
        self.y = round((self.y + y - y1) / 0.05) * 0.05

    def pad_positions(self):
        return [(p[1], self._xf(float(find1(p, 'at')[1]), float(find1(p, 'at')[2])))
                for p in find(self.tree, 'pad')]

    def emit(self, netcode):
        t = copy.deepcopy(self.tree)
        name = t[1]
        lib = self.c['fp'].split(':')[0]
        out = [Sym('footprint'), f'{lib}:{name}']
        body = [x for x in t[2:] if not (isinstance(x, list) and x[0] in
                                          ('version', 'generator', 'generator_version'))]
        for item in body:
            if isinstance(item, list) and item[0] in ('property', 'fp_text', 'pad'):
                at = find1(item, 'at')
                if at is not None:
                    ang = float(at[3]) if len(at) > 3 else 0.0
                    a = (ang + self.rot) % 360
                    del at[3:]
                    if a:
                        at.append(a)
            if isinstance(item, list) and item[0] == 'property':
                if item[1] == 'Reference':
                    item[2] = self.ref
                    if self.ref.startswith('TP'):        # power pads: only the rail name on silk
                        layer = find1(item, 'layer')
                        if layer is not None:
                            layer[1] = 'F.Fab'
                elif item[1] == 'Value':
                    item[2] = self.c['value']
                    if self.ref.startswith('TP'):        # power pads: rail name on the silkscreen
                        layer = find1(item, 'layer')
                        if layer is not None:
                            layer[1] = 'F.SilkS'
            if isinstance(item, list) and item[0] == 'pad':
                net = self.nets.get(item[1])
                item[:] = [x for x in item if not (isinstance(x, list) and x[0] == 'net')]
                if net:
                    item.append([Sym('net'), netcode[net], net])
                item.append([Sym('uuid'), uid('pad', self.ref, item[1], len(item))])
            out.append(item)
            if isinstance(item, list) and item[0] == 'layer':
                out.append([Sym('uuid'), uid('fp', self.ref)])
                at = [Sym('at'), round(self.x, 4), round(self.y, 4)]
                if self.rot:
                    at.append(self.rot)
                out.append(at)
        # path/sheet info so "Update PCB from Schematic" matches symbols
        idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == 'attr')
        out[idx:idx] = [[Sym('path'), self.c['path']],
                        [Sym('sheetname'), self.c['sheetname']],
                        [Sym('sheetfile'), self.c['sheetfile']]]
        return out


# --------------------------------------------------------------------------- placement
def pack_rows(parts, x0, y0, width, gap):
    x, y, row_h, used_w = x0, y0, 0, 0
    for p in parts:
        w, h = p.size()
        if x > x0 and x + w > x0 + width:
            x, y, row_h = x0, y + row_h + gap, 0
        p.move_to(x, y)
        used_w = max(used_w, x + w - x0)
        x += w + gap
        row_h = max(row_h, h)
    return used_w, y + row_h - y0


def place(parts, pinnet, gap):
    def signal_nets(ref):
        return {n for (r, _), n in pinnet.items() if r == ref and n not in POWER_NETS
                and not n.startswith('unconnected')}

    ics = sorted((r for r in parts if r.startswith('IC')), key=lambda r: int(r[2:]))
    conns = [r for r in ('J3', 'J4', 'J5', 'J1', 'J2') if r in parts]
    pads = sorted((r for r in parts if r.startswith('TP')), key=lambda r: int(r[2:]))
    holes = [r for r in parts if is_hole(r)]
    others = [r for r in parts if r not in ics + conns + pads + holes]

    # each discrete joins the IC it shares most signal nets with
    icnets = {r: signal_nets(r) for r in ics}
    assigned = {}
    for _ in range(3):
        for r in others:
            if r in assigned:
                continue
            nets = signal_nets(r)
            score, best = max(((len(nets & icnets[ic]), ic) for ic in ics), default=(0, None))
            if score:
                assigned[r] = best
                icnets[best] |= nets
    cluster = {ic: [r for r in others if assigned.get(r) == ic] for ic in ics}
    loose = [r for r in others if r not in assigned]

    # discretes stand upright to save area
    for r in others:
        w, h = parts[r].size()
        if w > h + 1 and not r.startswith('RLY'):
            parts[r].rot = 90

    top = [parts[r] for r in conns if r in ('J3', 'J4', 'J5')]
    bot = [parts[r] for r in conns if r in ('J1', 'J2')]
    width = max(sum(p.size()[0] for p in top) + 2 * gap * (len(top) - 1),
                sum(p.size()[0] for p in bot) + 2 * gap * (len(bot) - 1))
    # the connector rows start clear of the corner mounting holes
    hx = 0.0
    if holes:
        hx = max(0.0, HOLE_INSET + parts[holes[0]].size()[0] / 2 + gap - BORDER)
    width += 2 * hx
    x0 = y0 = ORIGIN + BORDER
    _, th = pack_rows(top, x0 + hx, y0, width - 2 * hx + 1, 2 * gap)
    y = y0 + th + 1.5 * gap

    blocks = [[parts[ic]] + sorted((parts[r] for r in cluster[ic]), key=lambda p: -p.size()[1])
              for ic in ics]
    if loose:
        blocks.append([parts[r] for r in loose])
    blocks.append([parts[r] for r in pads])

    # each block: choose the internal width that gives the smallest bounding area
    dims = []
    for members in blocks:
        w0 = members[0].size()[0]
        best = None
        for bw in range(int(w0) + 1, int(width) + 1, 2):
            w, h = pack_rows(members, 0, 0, bw, gap)
            cost = (w + 1.5 * gap) * (h + 1.5 * gap)
            if best is None or cost < best[0] - 1e-6:
                best = (cost, bw)
        w, h = pack_rows(members, 0, 0, best[1], gap)
        dims.append((members, w, h))

    # Wirelength model: signal-net pin positions, block pins relative to the block origin.
    sig = {}                       # +5V and GND go everywhere; every other net counts
    for (r, _), n in pinnet.items():
        if n not in ('+5V', 'GND') and not n.startswith('unconnected'):
            sig.setdefault(n, set()).add(r)
    sig = {n: rs for n, rs in sig.items() if len(rs) > 1}

    def centre(p):
        x1, y1, x2, y2 = p.bbox()
        return (x1 + x2) / 2, (y1 + y2) / 2

    rel = [[(p.ref, *centre(p)) for p in members] for members, _, _ in dims]
    fixed = {p.ref: centre(p) for p in top}

    def hpwl(pos):
        total = 0.0
        for rs in sig.values():
            pts = [pos[r] for r in rs if r in pos]
            if len(pts) > 1:
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                total += max(xs) - min(xs) + max(ys) - min(ys)
        return total

    # Skyline packing: each block goes to the column that minimises its height on the
    # skyline plus the wire it adds to blocks already placed. Many block orders are
    # tried; the layout with the best mix of board height and wirelength is kept.
    step = 0.5
    cols = int(math.ceil(width / step)) + 1
    HEIGHT_W = float(os.environ.get('AC30_HEIGHT_W', 25.0))  # mm of wire per mm of board height

    def skyline(order, commit):
        sky = [y] * cols
        pos = dict(fixed)
        for i in order:
            members, w, h = dims[i]
            wc = min(int(math.ceil((w + 1.5 * gap) / step)), cols)
            nets = {n for r, _, _ in rel[i] for n, rs in sig.items() if r in rs}
            best = None
            for c in range(0, cols - wc + 1, 2):
                t = max(sky[c:c + wc])
                bx, by = x0 + c * step, t
                trial = dict(pos)
                trial.update({r: (bx + cx, by + cy) for r, cx, cy in rel[i]})
                wire = sum(_span(trial, sig[n]) for n in nets)
                cost = HEIGHT_W * (t + h) + wire
                if best is None or cost < best[0]:
                    best = (cost, c, t)
            _, c, t = best
            bx, by = x0 + c * step, t
            pos.update({r: (bx + cx, by + cy) for r, cx, cy in rel[i]})
            if commit:
                for p in members:
                    x1, y1, _, _ = p.bbox()
                    p.move_to(x1 + bx, y1 + by)
            for k in range(c, c + wc):
                sky[k] = t + h + 1.5 * gap
        bottom = max(sky)
        return HEIGHT_W * bottom + hpwl(pos), bottom

    n = len(dims)
    orders = [list(range(n)), sorted(range(n), key=lambda i: -dims[i][2]),
              sorted(range(n), key=lambda i: -dims[i][1]),
              sorted(range(n), key=lambda i: -dims[i][1] * dims[i][2])]
    rng = random.Random(30)
    for _ in range(int(os.environ.get('AC30_ORDERS', 300))):
        o = list(range(n))
        rng.shuffle(o)
        orders.append(o)
    best = min(orders, key=lambda o: skyline(o, False)[0])
    score, bottom = skyline(best, True)
    print(f'estimated signal wire {score - HEIGHT_W * bottom:.0f} mm', file=sys.stderr)
    pack_rows(bot, x0 + hx, bottom, width - 2 * hx + 1, 2 * gap)
    return x0, x0 + width


def _span(pos, refs):
    pts = [pos[r] for r in refs if r in pos]
    if len(pts) < 2:
        return 0.0
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return max(xs) - min(xs) + max(ys) - min(ys)


# --------------------------------------------------------------------------- output
HEADER = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pcb_header.txt')).read()


def is_hole(ref):
    return ref.startswith('H') and ref[1:].isdigit()


def outline(parts, frame):
    """Board edge: parts (not the mounting holes) plus the border, snapped to 0.5 mm."""
    bx = [p.bbox() for r, p in parts.items() if not is_hole(r)]
    ex1 = math.floor((min([b[0] for b in bx] + [frame[0]]) - BORDER) * 2) / 2
    ey1 = math.floor((min(b[1] for b in bx) - BORDER) * 2) / 2
    ex2 = math.ceil((max([b[2] for b in bx] + [frame[1]]) + BORDER) * 2) / 2
    ey2 = math.ceil((max(b[3] for b in bx) + BORDER) * 2) / 2
    return ex1, ey1, ex2, ey2


def place_holes(parts, edge):
    """H1..H4 clockwise from top left, HOLE_INSET in from each edge."""
    ex1, ey1, ex2, ey2 = edge
    corners = [(ex1 + HOLE_INSET, ey1 + HOLE_INSET), (ex2 - HOLE_INSET, ey1 + HOLE_INSET),
               (ex2 - HOLE_INSET, ey2 - HOLE_INSET), (ex1 + HOLE_INSET, ey2 - HOLE_INSET)]
    for ref, (x, y) in zip(sorted((r for r in parts if is_hole(r)), key=lambda r: int(r[1:])), corners):
        parts[ref].x, parts[ref].y, parts[ref].rot = x, y, 0


def write(parts, netnames, out, edge):
    netcode = {n: i + 1 for i, n in enumerate(sorted(netnames))}
    ex1, ey1, ex2, ey2 = edge
    s = [HEADER, '\t(net 0 "")']
    for n, i in sorted(netcode.items(), key=lambda kv: kv[1]):
        s.append(f'\t(net {i} {dump(n)})')
    for ref in sorted(parts, key=lambda r: (r.rstrip('0123456789'), int(r[len(r.rstrip('0123456789')):]))):
        s.append('\t' + dump(parts[ref].emit(netcode), 1))
    s.append(f'\t(gr_rect (start {ex1} {ey1}) (end {ex2} {ey2}) (stroke (width 0.1) (type default)) '
             f'(fill no) (layer "Edge.Cuts") (uuid "{uid("edge")}"))')
    s.append(f'\t(gr_text "SWTPC AC-30 reproduction" (at {ex1 + 1.5} {ey2 - 1.5} 0) (layer "F.Fab") '
             f'(uuid "{uid("title")}") (effects (font (size 1 1) (thickness 0.15)) (justify left bottom)))')
    s.append(')')
    with open(out, 'w') as fh:
        fh.write('\n'.join(s) + '\n')
    return ex2 - ex1, ey2 - ey1


def update_project(pro):
    """Design rules and a Power netclass in the .kicad_pro."""
    d = json.load(open(pro)) if os.path.exists(pro) else {}
    base = {"bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": 0.25, "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6}
    d.setdefault('net_settings', {})
    d['net_settings']['classes'] = [dict(base, name='Default', priority=2147483647),
                                    dict(base, name='Power', priority=0, track_width=0.6,
                                         via_diameter=1.0, via_drill=0.5)]
    d['net_settings']['meta'] = {"version": 4}
    d['net_settings']['netclass_patterns'] = [{"netclass": "Power", "pattern": n}
                                              for n in sorted(POWER_NETS)]
    rules = d.setdefault('board', {}).setdefault('design_settings', {}).setdefault('rules', {})
    rules.update({"min_clearance": 0.2, "min_track_width": 0.25, "min_copper_edge_clearance": 0.5,
                  "min_via_diameter": 0.8, "min_through_hole_diameter": 0.4, "min_hole_clearance": 0.25,
                  "min_hole_to_hole": 0.25})
    json.dump(d, open(pro, 'w'), indent=2)


def main(netlist, out, gap=2.0):
    comps, pinnet, netnames = read_netlist(netlist)
    parts = {c['ref']: Part(c, pinnet) for c in comps}
    frame = place(parts, pinnet, gap)
    edge = outline(parts, frame)
    place_holes(parts, edge)
    w, h = write(parts, netnames, out, edge)
    update_project(os.path.splitext(out)[0] + '.kicad_pro')
    print('board %.1f x %.1f mm, %d footprints, %d nets' % (w, h, len(parts), len(netnames)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 2.0)
