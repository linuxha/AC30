#!/usr/bin/env python3
"""Generate the AC-30 KiCad project from netlist.py.

Each functional group is laid out on its own and its nets are drawn as wires
(schroute.py). Every routed net keeps one label (its name, matching the PCB's net
names); nets leaving a group are joined by those labels, power pins get power symbols
and unused pins no-connect flags.

Usage: python3 -I gen.py <output_dir>
"""
import math, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kilib, customlib, netlist, schroute
from sexp import q, dump, parse

PROJECT = os.environ.get('AC30_PROJECT', 'AC30')    # AC30_SMT for the surface-mount variant
NS = uuid.UUID('6f1d6c0e-5a3e-4c55-9d43-ac30ac30ac30')
GRID = 2.54
STUB = 2.54
CHAR_W = 1.15          # approx. width of one 1.27 mm label character
SPACING = 5.08


def uid(*parts):
    return str(uuid.uuid5(NS, '/'.join(map(str, parts))))


def snap(v):
    return round(v / GRID) * GRID


def f(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


FONT = '(effects (font (size 1.27 1.27)){})'


def eff(justify=None, hide=False):
    extra = ''
    if justify:
        extra += f' (justify {justify})'
    if hide:
        extra += ' (hide yes)'
    return FONT.format(extra)


class Sheet:
    def __init__(self, name, file, title, paper_choices):
        self.name, self.file, self.title = name, file, title
        self.paper_choices = paper_choices
        self.items = []
        self.lib_ids = set()
        self.uuid = uid('sheet', name)

    def add(self, s):
        self.items.append(s)


def outward(angle):
    """Unit vector (schematic coords, Y down) pointing away from body for a lib pin angle."""
    a = math.radians(angle + 180)
    return round(math.cos(a)), -round(math.sin(a))


def label_dir(dx, dy):
    """Label rotation/justification for text extending along (dx, dy)."""
    if dx > 0:
        return 0, 'left bottom'
    if dx < 0:
        return 180, 'right bottom'
    if dy < 0:
        return 90, 'left bottom'
    return 270, 'right bottom'


def instance_geometry(sym, unit, netmap):
    """Pins of one unit with stub ends and the bbox (relative to origin) including labels."""
    pins = [p for p in kilib.pins(sym) if p['unit'] in (unit, 0)]
    # stacked pins (same number listed twice) - keep first
    seen, uniq = set(), []
    for p in pins:
        if p['number'] not in seen:
            seen.add(p['number']); uniq.append(p)
    xs, ys = [], []
    geo = []
    for p in uniq:
        px, py = p['x'], -p['y']
        dx, dy = outward(p['angle'])
        net = netmap.get(p['number'], None)
        ex, ey = px + dx * STUB, py + dy * STUB
        if net in netlist.POWER:
            ext = 6.0
        elif net is None:
            ext = 0
        else:
            ext = len(net) * CHAR_W + 3
        xs += [px, ex + dx * ext]
        ys += [py, ey + dy * ext]
        if dx == 0 and net not in (None,):  # vertical labels have width
            xs += [ex - 1.5, ex + 1.5]
        if dy == 0 and net is not None:
            ys += [ey - 1.5, ey + 1.5]
        geo.append(dict(pin=p, px=px, py=py, dx=dx, dy=dy, ex=ex, ey=ey, net=net))
    # include rough body extents around the pins
    bx = [g['px'] for g in geo] or [0]
    by = [g['py'] for g in geo] or [0]
    gx1, gy1, gx2, gy2 = kilib.body_bbox(sym, unit)
    gx1, gx2, gy1, gy2 = gx1, gx2, -gy2, -gy1          # to schematic coords
    xs += [gx1, gx2]
    ys += [gy1, gy2]
    return geo, (min(xs), min(ys), max(xs), max(ys)), (gx1, gy1, gx2, gy2)


def field_layout(geo, bbox, body, ref, value):
    """Return ((rx, ry, justify), (vx, vy, justify), grown bbox) relative to origin."""
    x1, y1, x2, y2 = bbox
    if geo and not any(g['dx'] for g in geo):
        # only top/bottom pins: fields to the right of the body
        fx = body[2] + 1.27
        w = max(len(ref), len(value)) * CHAR_W
        return (fx, -1.27, 'left'), (fx, 1.27, 'left'), (x1, y1, max(x2, fx + w), y2)
    return ((0, y1 - 1.27, None), (0, y2 + 1.9, None), (x1, y1 - 2.54, x2, y2 + 3.81))


def sym_instance(sheet, path, lib_id, ref, value, unit, x, y, fp, fields, rot=0,
                 hide_ref=False, uid_key=None, in_bom=True):
    key = uid_key or (ref, unit)
    (rx, ry, rj), (vx, vy, vj) = fields
    props = [
        f'(property "Reference" {q(ref)} (at {f(x + rx)} {f(y + ry)} 0) {eff(rj, hide=hide_ref)})',
        f'(property "Value" {q(value)} (at {f(x + vx)} {f(y + vy)} 0) {eff(vj)})',
        f'(property "Footprint" {q(fp or "")} (at {f(x)} {f(y)} 0) {eff(hide=True)})',
        f'(property "Datasheet" "" (at {f(x)} {f(y)} 0) {eff(hide=True)})',
    ]
    sym = kilib.get(lib_id, custom_path(lib_id))
    pins = sorted({p['number'] for p in kilib.pins(sym) if p['unit'] in (unit, 0)})
    pin_s = ' '.join(f'(pin {q(n)} (uuid {q(uid("pin", *key, n))}))' for n in pins)
    bom = 'yes' if in_bom else 'no'
    board = 'yes' if fp else 'no'      # front-panel parts have no footprint
    sheet.add(f'(symbol (lib_id {q(lib_id)}) (at {f(x)} {f(y)} {rot}) (unit {unit}) '
              f'(exclude_from_sim no) (in_bom {bom}) (on_board {board}) (dnp no) '
              f'(uuid {q(uid("sym", *key))}) {" ".join(props)} {pin_s} '
              f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(ref)}) (unit {unit})))))')
    sheet.lib_ids.add(lib_id)


def custom_path(lib_id):
    return CUSTOM_LIB if lib_id.startswith('AC30:') else None


class Counter:
    n = 0


def place_power(sheet, path, net, x, y, dx, dy):
    Counter.n += 1
    ref = '#PWR%03d' % Counter.n
    lib_id = netlist.POWER[net]
    up = net != 'GND'
    # default orientation: +5V points up (0,-1), GND points down (0,1)
    if up:
        rot = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}[(dx, dy)]
    else:
        rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[(dx, dy)]
    vx, vy = x + dx * 4.5, y + dy * 4.5
    if dy == 0:
        vy = y - 1.0 if up else y + 1.0
    sheet.add(f'(symbol (lib_id {q(lib_id)}) (at {f(x)} {f(y)} {rot}) (unit 1) '
              f'(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid {q(uid("pwr", ref))}) '
              f'(property "Reference" {q(ref)} (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
              f'(property "Value" {q(net)} (at {f(vx)} {f(vy)} 0) {eff(hide=dy == 0)}) '
              f'(property "Footprint" "" (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
              f'(property "Datasheet" "" (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
              f'(pin "1" (uuid {q(uid("pwrpin", ref))})) '
              f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(ref)}) (unit 1)))))')
    sheet.lib_ids.add(lib_id)


def wire(sheet, x1, y1, x2, y2):
    sheet.add(f'(wire (pts (xy {f(x1)} {f(y1)}) (xy {f(x2)} {f(y2)})) (stroke (width 0) (type default)) '
              f'(uuid {q(uid("wire", sheet.name, x1, y1, x2, y2))}))')


def label(sheet, net, x, y, dx, dy):
    rot, just = label_dir(dx, dy)
    key = uid('label', sheet.name, net, x, y)
    if net in netlist.GLOBAL:
        gj = 'left' if rot in (0, 90) else 'right'
        sheet.add(f'(global_label {q(net)} (shape {netlist.GLOBAL[net]}) (at {f(x)} {f(y)} {rot}) '
                  f'(fields_autoplaced yes) {eff(gj)} (uuid {q(key)}) '
                  f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {f(x)} {f(y)} 0) {eff(gj, hide=True)}))')
    else:
        sheet.add(f'(label {q(net)} (at {f(x)} {f(y)} {rot}) {eff(just)} (uuid {q(key)}))')


def no_connect(sheet, x, y):
    sheet.add(f'(no_connect (at {f(x)} {f(y)}) (uuid {q(uid("nc", sheet.name, x, y))}))')


def text(sheet, s, x, y, size=1.27, bold=False):
    b = ' (bold yes)' if bold else ''
    sheet.add(f'(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} 0) '
              f'(effects (font (size {size} {size}){b}) (justify left top)) (uuid {q(uid("text", sheet.name, s[:40], x, y))}))')


PAPERS = {'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594), 'A0': (1189, 841)}


def layout(sheet, path, plist, wired, x0=20.32, y0=25.4):
    """Shelf-pack all units, grouped; returns used height."""
    for paper in sheet.paper_choices:
        W, H = PAPERS[paper]
        maxw = W - 2 * x0
        ok = try_layout(sheet, path, plist, wired, x0, y0, maxw, dry=True) < H - 45
        if ok or paper == sheet.paper_choices[-1]:
            sheet.paper = paper
            try_layout(sheet, path, plist, wired, x0, y0, maxw, dry=False)
            return


def try_layout(sheet, path, plist, wired, x0, y0, maxw, dry):
    y = y0
    group = None
    x = x0
    row_h = 0
    for part in plist:
        if part['group'] != group:
            group = part['group']
            y += row_h + (10.16 if row_h else 0)
            if not dry:
                text(sheet, group, x0, y, 2.54, True)
            y += 7.62
            x, row_h = x0, 0
        sym = kilib.get(part['lib'], custom_path(part['lib']))
        units = sorted(u for u in part['units'] if u != 0) or [1]
        for u in units:
            netmap = dict(part['units'].get(0, {}))
            netmap.update(part['units'].get(u, {}))
            geo, bbox, body = instance_geometry(sym, u, netmap)
            rf, vf, (bx1, by1, bx2, by2) = field_layout(geo, bbox, body, part['ref'], part['value'])
            fields = (rf, vf)
            w, h = bx2 - bx1, by2 - by1
            if x + w > x0 + maxw and x > x0:
                y += row_h + SPACING
                x, row_h = x0, 0
            ox, oy = snap(x - bx1 + GRID / 2), snap(y - by1 + GRID / 2)
            if not dry:
                emit_unit(sheet, path, part, u, ox, oy, geo, wired, fields)
            x = ox + bx2 + SPACING
            row_h = max(row_h, oy + by2 - y)
    return y + row_h


def emit_unit(sheet, path, part, unit, ox, oy, geo, wired, fields):
    sym_instance(sheet, path, part['lib'], part['ref'], part['value'], unit, ox, oy, part['fp'], fields,
                 in_bom=part['lib'] not in ('Connector:TestPoint', 'Mechanical:MountingHole'))
    for g in geo:
        px, py = ox + g['px'], oy + g['py']
        ex, ey = ox + g['ex'], oy + g['ey']
        net = g['net']
        explicit = g['pin']['number'] in part['units'].get(unit, {}) or \
            g['pin']['number'] in part['units'].get(0, {})
        if net is None:
            if wired or explicit:
                no_connect(sheet, px, py)
            continue
        wire(sheet, px, py, ex, ey)
        if net in netlist.POWER:
            place_power(sheet, path, net, ex, ey, g['dx'], g['dy'])
        else:
            label(sheet, net, ex, ey, g['dx'], g['dy'])


# --------------------------------------------------------------------------- wired layout
# Each functional group is laid out on its own: its units in rows ordered by shared
# nets, nets with two or more pins in the group drawn as real wires (schroute.py), and
# labels only where a net leaves the group. The finished groups are then shelf-packed.
GAP = 6                # cells of routing room between units
MARGIN = 4             # cells of routing room around a group


def _cells(v):
    return int(round(v / GRID))


def _pin_counts():
    total = {}
    for part in netlist.parts:
        for pins in part['units'].values():
            for net in pins.values():
                if net:
                    total[net] = total.get(net, 0) + 1
    return total


TOTAL = None


def _label_len(net):
    return (len(net) * CHAR_W + (5 if net in netlist.GLOBAL else 2)) / GRID


def _unit_geometry(part, u):
    sym = kilib.get(part['lib'], custom_path(part['lib']))
    netmap = dict(part['units'].get(0, {}))
    netmap.update(part['units'].get(u, {}))
    geo, _, body = instance_geometry(sym, u, netmap)
    lens = {p['number']: p['length'] for p in kilib.pins(sym) if p['unit'] in (u, 0)}
    for g in geo:
        g['len'] = lens.get(g['pin']['number'], 2.54)
    # pin tips must land on the grid: offset the origin by the fraction of a cell most
    # tips share; a tip left off the grid keeps a plain stub and a label
    frac = [(round((g['px'] / GRID) % 1, 2) % 1, round((g['py'] / GRID) % 1, 2) % 1) for g in geo]
    fx, fy = max(set(frac), key=frac.count) if frac else (0.0, 0.0)
    for g, fr in zip(geo, frac):
        g['offgrid'] = fr != (fx, fy)
    return dict(part=part, unit=u, geo=geo, body=body, off=(-fx * GRID, -fy * GRID))


def _group(plist):
    """Lay out and route one group. Returns (drawing, w, h) in mm, origin top-left."""
    units = []
    for part in plist:
        for u in sorted(k for k in part['units'] if k != 0) or [1]:
            units.append(_unit_geometry(part, u))
    count = {}
    for un in units:
        for g in un['geo']:
            if g['net'] and g['net'] not in netlist.POWER and not g['offgrid']:
                count[g['net']] = count.get(g['net'], 0) + 1
    routed = {n for n, c in count.items() if c >= 2}
    leaving = routed       # every routed net keeps one label: its name, and the PCB's net name
    labelled = set()
    # one label per routed net, on a horizontal pin of a part other than a connector where
    # possible (a connector's closely spaced pins need their way out for the wires)
    cand = sorted(((un['part']['ref'].startswith('J'), g['dy'] != 0, i, g)
                   for i, un in enumerate(units) for g in un['geo']), key=lambda t: t[:3])
    for *_, g in cand:
        n = g['net']
        if n in leaving and n not in labelled:
            g['label'] = True
            labelled.add(n)
    for un in units:
        for g in un['geo']:
            n = g['net']
            if n and n not in netlist.POWER and (n not in routed or g['offgrid']):
                g['label'] = True

    # unit extents (cells, relative to the unit origin) including stubs, labels, fields
    for un in units:
        ox, oy = un['off']
        xs, ys = [], []
        b = un['body']
        xs += [(b[0] + ox) / GRID, (b[2] + ox) / GRID]
        ys += [(b[1] + oy) / GRID, (b[3] + oy) / GRID]
        for g in un['geo']:
            tx, ty = (g['px'] + ox) / GRID, (g['py'] + oy) / GRID
            ext = 1
            if g.get('label'):
                ext += _label_len(g['net'])
            elif g['net'] in netlist.POWER:
                ext += 2
            xs += [tx, tx + g['dx'] * ext]
            ys += [ty, ty + g['dy'] * ext]
            if g.get('label') and g['dx'] == 0:
                xs += [tx - 1, tx + 1]
            if g.get('label') and g['dy'] == 0:
                ys += [ty - 1]
        ref, val = un['part']['ref'], un['part']['value']
        bb = (min(xs) * GRID, min(ys) * GRID, max(xs) * GRID, max(ys) * GRID)
        rf, vf, grown = field_layout(un['geo'], bb, b, ref, val)
        un['fields'] = rf, vf
        tw = max(len(ref), len(val)) * CHAR_W / 2
        un['ext'] = (grown[0] / GRID - tw / GRID, grown[1] / GRID, grown[2] / GRID + tw / GRID,
                     grown[3] / GRID)

    # order: greedy chain by shared routed nets, starting from the most connected unit
    def nets(un):
        return {g['net'] for g in un['geo'] if g['net'] in routed}
    order, rest = [], units[:]
    if rest:
        cur = max(rest, key=lambda un: len(nets(un)))
        while rest:
            rest.remove(cur)
            order.append(cur)
            if not rest:
                break
            placed = set().union(*(nets(u) for u in order))
            cur = max(rest, key=lambda un: (len(nets(un) & nets(order[-1])),
                                            len(nets(un) & placed), -units.index(un)))

    # rows of units, each unit origin on a whole cell
    maxw = _cells(GROUP_MAXW)
    x = y = MARGIN
    row_h = 0
    for un in order:
        x1, y1, x2, y2 = un['ext']
        w, h = x2 - x1, y2 - y1
        if x > MARGIN and x + w > maxw:
            x, y, row_h = MARGIN, y + row_h + GAP, 0
        un['cx'], un['cy'] = int(math.ceil(x - x1)), int(math.ceil(y - y1))
        x = un['cx'] + x2 + GAP
        row_h = max(row_h, un['cy'] + y2 - y)

    grid = schroute.Grid()
    pins = {}
    for un in order:
        ox, oy = un['off']
        cx, cy = un['cx'], un['cy']
        b = un['body']
        bx1, bx2 = math.ceil((b[0] + ox) / GRID - 0.01), math.floor((b[2] + ox) / GRID + 0.01)
        by1, by2 = math.ceil((b[1] + oy) / GRID - 0.01), math.floor((b[3] + oy) / GRID + 0.01)
        grid.block_rect(cx + bx1, cy + by1, cx + bx2, cy + by2)
        for (fx, fy, fj), txt in zip(un['fields'], (un['part']['ref'], un['part']['value'])):
            w = len(txt) * CHAR_W / GRID
            xa = fx / GRID if fj == 'left' else fx / GRID - w / 2
            grid.block_rect(cx + math.floor(xa), cy + _cells(fy) - 1,
                            cx + math.ceil(xa + w), cy + _cells(fy))
        for g in un['geo']:
            tip = (cx + _cells(g['px'] + ox), cy + _cells(g['py'] + oy))
            d = (g['dx'], g['dy'])
            for k in range(1, max(1, _cells(g['len'])) + 1):      # the pin itself
                grid.block((tip[0] - d[0] * k, tip[1] - d[1] * k))
            g['tip'] = tip
            if g['net'] is None:
                grid.block(tip)
                continue
            end = (tip[0] + d[0], tip[1] + d[1])
            g['end'] = end
            if g['offgrid']:
                grid.block(tip)
                grid.block(end)
            else:
                grid.stub(g['net'], tip, end)
                grid.block(tip)                       # wires join a pin at its stub end only
            if g.get('label'):
                n = int(math.ceil(_label_len(g['net'])))
                for k in range(1, n + 1):
                    grid.block((end[0] + d[0] * k, end[1] + d[1] * k))
            elif g['net'] in netlist.POWER:
                for k in (1, 2):
                    grid.block((end[0] + d[0] * k, end[1] + d[1] * k))
            if g['net'] in routed and not g['offgrid']:
                pins.setdefault(g['net'], []).append(g)

    xs = [un['cx'] + un['ext'][2] for un in order] + [0]
    ys = [un['cy'] + un['ext'][3] for un in order] + [0]
    bounds = (0, 0, int(max(xs)) + MARGIN, int(max(ys)) + MARGIN)

    def span(n):
        c = [g['end'] for g in pins[n]]
        return max(p[0] for p in c) - min(p[0] for p in c) + max(p[1] for p in c) - min(p[1] for p in c)

    failed = []
    joined = {}
    for n in sorted(pins, key=span):
        first = pins[n][0]
        tree = {first['end']}                         # the part of the net joined so far
        joined[n] = [first]
        todo = pins[n][1:]
        while todo:
            todo.sort(key=lambda g: min(abs(g['end'][0] - c[0]) + abs(g['end'][1] - c[1]) for c in tree))
            g = todo.pop(0)
            path = grid.route(n, g['end'], (g['dx'], g['dy']), bounds, tree)
            if path:
                grid.commit(n, path)
                tree |= set(path)
                joined[n].append(g)
            else:
                failed.append(g)
    for g in failed:                                  # unroutable: fall back to labels
        g['label'] = True
        if not any(h.get('label') for h in joined[g['net']]):
            joined[g['net']][0]['label'] = True       # the wired part needs its label too

    wires, junctions = grid.segments()
    cells = [c for _, a, b in wires for c in (a, b)]
    w = max([bounds[2]] + [c[0] + MARGIN for c in cells]) * GRID
    h = max([bounds[3]] + [c[1] + MARGIN for c in cells]) * GRID
    return dict(units=order, wires=wires, junctions=junctions, failed=len(failed)), w, h


def _emit_group(sheet, path, grp, gx, gy):
    for un in grp['units']:
        part, u = un['part'], un['unit']
        ox, oy = gx + un['cx'] * GRID + un['off'][0], gy + un['cy'] * GRID + un['off'][1]
        sym_instance(sheet, path, part['lib'], part['ref'], part['value'], u, ox, oy, part['fp'],
                     un['fields'], in_bom=part['lib'] not in ('Connector:TestPoint',
                                                             'Mechanical:MountingHole'))
        for g in un['geo']:
            tx, ty = gx + g['tip'][0] * GRID, gy + g['tip'][1] * GRID
            if g['offgrid']:                          # exact tip, stub drawn here
                tx, ty = ox + g['px'], oy + g['py']
            if g['net'] is None:
                no_connect(sheet, tx, ty)
                continue
            ex, ey = gx + g['end'][0] * GRID, gy + g['end'][1] * GRID
            if g['offgrid']:
                ex, ey = tx + g['dx'] * STUB, ty + g['dy'] * STUB
                wire(sheet, tx, ty, ex, ey)
            if g['net'] in netlist.POWER:
                place_power(sheet, path, g['net'], ex, ey, g['dx'], g['dy'])
            elif g.get('label'):
                label(sheet, g['net'], ex, ey, g['dx'], g['dy'])
    for net, a, b in grp['wires']:
        wire(sheet, gx + a[0] * GRID, gy + a[1] * GRID, gx + b[0] * GRID, gy + b[1] * GRID)
    for net, c in grp['junctions']:
        x, y = gx + c[0] * GRID, gy + c[1] * GRID
        sheet.add(f'(junction (at {f(x)} {f(y)}) (diameter 0) (color 0 0 0 0) '
                  f'(uuid {q(uid("junction", sheet.name, x, y))}))')


GROUP_MAXW = 200.0
GROUP_BOXES = []       # where each group landed (mm), for tools/schimg.py


def notes_bottom(s, y):
    """Y just below a notes text block starting at y."""
    return snap(y + (s.count('\n') + 1) * 1.27 * 1.65 + 10.16)


def layout_wired(sheet, path, plist, x0=20.32, y0=25.4):
    """Group by group, wired; shelf-pack the groups on the smallest paper that fits."""
    global TOTAL, GROUP_MAXW
    TOTAL = TOTAL or _pin_counts()
    groups = {}
    for part in plist:
        groups.setdefault(part['group'], []).append(part)
    for paper in sheet.paper_choices:
        W, H = PAPERS[paper]
        GROUP_MAXW = min(W - 2 * x0, 280.0)
        built = [(name, *_group(parts)) for name, parts in groups.items()]
        # shelf-pack the groups (each with a 7.62 mm heading)
        x, y, row_h, place = x0, y0, 0, []
        for name, grp, w, h in built:
            if x > x0 and x + w > W - x0:
                x, y, row_h = x0, y + row_h + 5.08, 0
            place.append((name, grp, snap(x), snap(y)))
            x += w + 10.16
            row_h = max(row_h, h + 7.62)
        if y + row_h < H - 45 or paper == sheet.paper_choices[-1]:
            break
    sheet.paper = paper
    failed = 0
    for (name, grp, gx, gy), (_, _, w, h) in zip(place, built):
        text(sheet, name, gx, gy, 2.54, True)
        _emit_group(sheet, path, grp, gx, gy + 7.62)
        failed += grp['failed']
        GROUP_BOXES.append(dict(sheet=sheet.file, group=name, x=gx, y=gy, w=w, h=h + 7.62))
    print(f'{sheet.name}: {paper}, {failed} connections left as labels', file=sys.stderr)


def lib_symbols(ids):
    out = []
    for lid in sorted(ids):
        out.append(dump(kilib.get(lid, custom_path(lid)), 1))
    return '(lib_symbols\n\t' + '\n\t'.join(out) + ')'


def title_block(title, comments):
    c = ' '.join(f'(comment {i} {q(t)})' for i, t in enumerate(comments, 1))
    return (f'(title_block (title {q(title)}) (date "2026-10-08") (rev "A") '
            f'(company "SWTPC AC-30 reproduction") {c})')


def write_sheet(path, sheet, root_uuid, extra='', comments=(), sheet_instances=True):
    body = '\n'.join(sheet.items)
    si = '(sheet_instances (path "/" (page "1")))' if sheet_instances else ''
    s = (f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") '
         f'(uuid {q(sheet.uuid if sheet_instances else sheet.uuid)}) (paper {q(sheet.paper)}) '
         f'{title_block(sheet.title, comments)}\n{lib_symbols(sheet.lib_ids)}\n{body}\n{extra}\n{si} (embedded_fonts no))')
    # round-trip through the parser to pretty print
    with open(path, 'w') as fh:
        fh.write(dump(parse(s)) + '\n')


NOTES_MAIN = """Generated from docs/ac30_schematica.jpg (SWTPC AC-30 Cassette Tape Switching Schematic),
docs/AC30-BOM.md and docs/ac30_wiring1a.jpg. Each block is wired; net labels join the blocks and sheets
(identical labels are connected).
Transcription notes / assumptions:
 - Drawing pin-number slips corrected to the real pinouts: IC7D drawn 8->9 (4049: 9->10);\n   IC13C drawn inputs 7,8 (4070: 8,9).
 - 4053 INH (pin 6) and VEE (pin 7) are not shown on the drawing; tied to GND.
 - IC10 pins 4/8 tie to the R38 supply node, assumed +5V.
 - IC15 (1488) supply pins are not shown; taken as +13V / -13V from the power supply (sheet 3).
 - CONTROL INVERT: drawn as R42 pull-up; it is also brought out on J4.
 - J3-J5 pin positions match the original artwork (docs/ac30_redblue150.jpg).
 - The front panel is wired to five rows of 0.1 in through-hole pads instead of the artwork's
   J1/J2 harness headers: J1 SWITCHES, J2 LEDS, J13 MOTOR, J14 MIC (MIC A/B jacks) and
   J15 EAR (EAR A/B jacks). The S2/S3 audio poles wire to the SWITCHES pads (AUDIO_OUT,
   MIC_A/B, AUDIO_IN, EAR_A/B); the board joins them.
 - MIC/EAR jack reference designators J6-J9 are assigned arbitrarily; J10/J11 are the motor jacks.
 - Trimmer R39 (DELAY, next to IC10 on the artwork) is not on any schematic; it is listed,\n   not placed, in tools/netlist.py.
 - The artwork's J2 pins 11/12 (18 VAC A/B) are gone: the power supply is external."""

NOTES_SMT = """
SMT variant (kicad-smt/AC30_SMT): every on-board part is surface mount except the Molex KK-396
connectors (J3-J5, J12), the front-panel jumper pads and the mounting holes. 0805 R/C, SOD-123 diodes (1N4148W, BZT52C4V7), SOT-23
transistors (MMBT5088 for 2N5210, MMBT5087), SOIC ICs, tantalum EIA-3216 (C4, C17),
6.3x7.7 mm aluminium C16, Bourns 3314G trimmer R16, 1206 LED D18. RLY1/RLY2 are Omron
G6K-2F-Y (5 V coil, DPDT 1 A, both poles in parallel as the motor contact) instead of
6 V SIL reed relays; check the coil polarity mark (pin 1 to RELAY_x)."""

NOTES_SUB = """Generated from docs/ac30_mod_demod.pdf (SWTPC AC-30 Cassette Tape Modulator/Demodulator
Schematic). Each block is wired; net labels join the blocks and sheets (identical labels are connected).
Transcription notes / assumptions:
 - IC4 (4558) supply pins are not drawn. The assembly manual says IC4 runs from the +/-7.5 V
   zener rails (D12/D13 on the power supply sheet).
 - R16's far end has a terminal dot with no label; taken as +5V (Q1/C8 timer pull-up).
 - IC1B is unused and not drawn: its inputs are tied to GND, its outputs left open.
 - The manual's text calls the pulse inverter IC2A; the schematic (followed here) uses IC2C.
Power input: the supply (sheet 3) is built as a separate unit. Its six DC outputs come onto
the board on J12, a 6-pin KK-396 header (1 GND, 2 +5V, 3 +13V, 4 -13V, 5 +7.5V, 6 -7.5V). C23-C25 are +5 V bypass capacitors on the board
(drawn at the regulator on docs/ac30_PS.pdf; next to IC1, IC7 and IC13 on the original artwork)."""

NOTES_PSU = """Generated from docs/ac30_PS.pdf (SWTPC AC-30 Audio Cassette Power Supply Schematic).
Built as an EXTERNAL unit: these parts have no footprints and are not on the PC board. Wire the
six outputs to the board's power input J12 (KK-396: 1 GND, 2 +5V, 3 +13V, 4 -13V, 5 +7.5V, 6 -7.5V).
Transcription notes / corrections:
 - The drawing joins the IC16 GND / C23-C25 return line to the bridge's negative corner (-13 V)
   through two crossings. That would put the 7805's ground at -13 V, so IC16 GND is taken as GND.
 - T1's two 120 V primaries are drawn in parallel (120 VAC); drawn here as one primary. The
   18 VAC secondary is centre-tapped, tap to GND: the bridge gives +13 V (C21) and -13 V (C22).
 - D14-D17 numbering within the bridge is not shown on the drawing; assigned here.
 - S6 is an SPDT toggle (BOM) used as an on/off switch; one throw is unused.
 - IC15 (1488) supply pins are not drawn on the switching schematic; taken as +/-13 V, the only
   load for those outputs. IC4 (4558) uses +/-7.5 V (assembly manual)."""


# Sub-sheets: (sheet key, file, title, sheet-symbol name, notes, title-block comment)
SUBSHEETS = [
    ('moddemod', f'{PROJECT}_moddemod_power.kicad_sch', 'SWTPC AC-30 - Modulator/Demodulator & power input',
     'Mod/Demod & power input', 'NOTES_SUB',
     'Source: docs/ac30_mod_demod.pdf; power input J12 for the external supply'),
    ('psu', f'{PROJECT}_power_supply.kicad_sch', 'SWTPC AC-30 - Power supply (external, not on PCB)',
     'Power supply (external)', 'NOTES_PSU',
     'Source: docs/ac30_PS.pdf; parts have no footprints - built as a separate unit'),
]


def pwr_flags(sheet, path, nets):
    """PWR_FLAGs for supplies that no power-output pin drives."""
    W, H = PAPERS[sheet.paper]
    gx, gy = snap(W - 110), snap(17.78)
    for i, net in enumerate(nets):
        x, y = gx - 40.64, gy + i * 10.16
        Counter.n += 1
        ref = '#FLG%02d' % (i + 1)
        sheet.add(f'(symbol (lib_id "power:PWR_FLAG") (at {f(x)} {f(y)} 0) (unit 1) (exclude_from_sim no) '
                  f'(in_bom yes) (on_board yes) (dnp no) (uuid {q(uid("flag", ref))}) '
                  f'(property "Reference" {q(ref)} (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
                  f'(property "Value" "PWR_FLAG" (at {f(x)} {f(y - 3.81)} 0) {eff()}) '
                  f'(property "Footprint" "" (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
                  f'(property "Datasheet" "" (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
                  f'(pin "1" (uuid {q(uid("flagpin", ref))})) '
                  f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(ref)}) (unit 1)))))')
        sheet.lib_ids.add('power:PWR_FLAG')
        wire(sheet, x, y, x + 5.08, y)
        if net in netlist.POWER:
            place_power(sheet, path, net, x + 5.08, y, 0, 1 if net == 'GND' else -1)
        else:
            label(sheet, net, x + 5.08, y, 1, 0)


def main(outdir):
    global CUSTOM_LIB
    os.makedirs(outdir, exist_ok=True)
    CUSTOM_LIB = os.path.join(outdir, 'AC30.kicad_sym')
    customlib.write(CUSTOM_LIB)

    title = 'SWTPC AC-30 Cassette Interface - Switching' + (' (SMT)' if netlist.SMT else '')
    root = Sheet('main', f'{PROJECT}.kicad_sch', title, ['A1', 'A0'])
    root_path = '/' + root.uuid
    notes = NOTES_MAIN + (NOTES_SMT if netlist.SMT else '')
    layout_wired(root, root_path, [p for p in netlist.parts if p['sheet'] == 'main'],
                 y0=notes_bottom(notes, 20.32))
    text(root, notes, 20.32, 20.32)

    W, H = PAPERS[root.paper]
    sheet_syms, project_sheets = [], [[root.uuid, 'Root']]
    for page, (key, file, title, symname, notes, comment) in enumerate(SUBSHEETS, 2):
        sub = Sheet(key, file, title, ['A3', 'A2', 'A1'])
        sheet_uuid = uid('sheetsym', key)
        sub_path = f'/{root.uuid}/{sheet_uuid}'
        layout_wired(sub, sub_path, [p for p in netlist.parts if p['sheet'] == key],
                     y0=max(60, notes_bottom(globals()[notes], 15.24)))
        text(sub, globals()[notes], 20.32, 15.24)
        if key == 'psu':
            # +5V is driven by IC16's output; the other rails only by diodes and zeners,
            # and the mains plug's L pin is a power input
            pwr_flags(sub, sub_path, ['GND', '+13V', '-13V', '+7.5V', '-7.5V', 'AC_LINE'])
        write_sheet(os.path.join(outdir, file), sub, root.uuid, comments=[comment], sheet_instances=False)

        sx, sy = W - 90, 22.86 + (page - 2) * 25.4
        sheet_syms.append(
            f'(sheet (at {f(sx)} {f(sy)}) (size 60.96 15.24) (exclude_from_sim no) (in_bom yes) '
            f'(on_board yes) (dnp no) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) '
            f'(fill (color 0 0 0 0.0000)) (uuid {q(sheet_uuid)}) '
            f'(property "Sheetname" {q(symname)} (at {f(sx)} {f(sy - 0.71)} 0) {eff("left bottom")}) '
            f'(property "Sheetfile" {q(file)} (at {f(sx)} {f(sy + 15.95)} 0) {eff("left top")}) '
            f'(instances (project {q(PROJECT)} (path {q(root_path)} (page {q(str(page))})))))')
        project_sheets.append([sheet_uuid, symname])

    comments = ['Source: docs/ac30_schematica.jpg, docs/ac30_mod_demod.pdf, docs/ac30_PS.pdf, '
                'docs/AC30-BOM.md, docs/ac30_redblue150.jpg',
                'Generated by kicad/tools/gen.py - edit netlist.py and regenerate, or edit in KiCad']
    write_sheet(os.path.join(outdir, root.file), root, root.uuid, '\n'.join(sheet_syms), comments)

    with open(os.path.join(outdir, 'sym-lib-table'), 'w') as fh:
        fh.write('(sym_lib_table\n  (version 7)\n  (lib (name "AC30")(type "KiCad")(uri "${KIPRJMOD}/AC30.kicad_sym")'
                 '(options "")(descr "AC-30 parts missing from stock libraries"))\n)\n')
    import json
    pro = os.path.join(outdir, PROJECT + '.kicad_pro')
    data = json.load(open(pro)) if os.path.exists(pro) else {"meta": {"filename": PROJECT + ".kicad_pro",
                                                                        "version": 3}}
    data['sheets'] = project_sheets
    json.dump(data, open(pro, 'w'), indent=2)
    if os.environ.get('AC30_GROUPS_JSON'):
        json.dump(GROUP_BOXES, open(os.environ['AC30_GROUPS_JSON'], 'w'), indent=1)
    print('main sheet paper', root.paper)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..'))
