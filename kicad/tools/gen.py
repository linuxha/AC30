#!/usr/bin/env python3
"""Generate the AC-30 KiCad project from netlist.py.

Every pin gets a short wire stub ending in a net label (or a power symbol /
no-connect flag), so connectivity is exact while the layout stays simple.

Usage: python3 -I gen.py <output_dir>
"""
import math, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kilib, customlib, netlist
from sexp import q, dump, parse

PROJECT = 'AC30'
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
docs/AC30-BOM.md and docs/ac30_wiring1a.jpg. Connectivity is by net label: identical labels are connected.
Transcription notes / assumptions:
 - Drawing pin-number slips corrected to the real pinouts: IC7D drawn 8->9 (4049: 9->10);\n   IC13C drawn inputs 7,8 (4070: 8,9).
 - 4053 INH (pin 6) and VEE (pin 7) are not shown on the drawing; tied to GND.
 - IC10 pins 4/8 tie to the R38 supply node, assumed +5V.
 - IC15 (1488) supply pins are not shown; brought out as V_RS232+ / V_RS232- (source on power sheet, unknown).
 - CONTROL INVERT: drawn as R42 pull-up; it is also brought out on J4.
 - J1-J5 pin positions match the original artwork (docs/ac30_redblue150.jpg); J1 pin 15 is\n   unlabelled there and left unused.
 - MIC/EAR jack reference designators J6-J9 are assigned arbitrarily; J10/J11 are the motor jacks.
 - BOM switch S6 does not appear on the switching schematic (placed unwired on sheet 2)."""

NOTES_SUB = """The modulator/demodulator and power supply schematics are NOT in docs/ - only the
switching schematic is. Until they are, the board brings every signal and supply
that crosses into those circuits out to a labelled solder pad (TP1-TP15), so the
switching section can be built and tested with an external mod/demod and supply.
The mod/demod and power BOM parts are listed (not placed) in tools/netlist.py.
Theory of operation (assembly manual): IC5B divides the 4800 Hz 16X clock, IC5A gives
1200/2400 Hz, IC4A is a 2-pole filter; R5/C5 high-pass into comparator IC4B,
D3 clamp, IC3C/D pulse generator, D4/C7 + IC3A carrier detect, Q2/IC2B missing
pulse detector, R16 1200 Hz timer, IC1A data out, IC2D/IC3B 16X clock out.
IC4 runs from +/-7.5 V zener (D12, D13) supplies; IC16 7805 makes +5 V from 18 VAC (T1)."""


def main(outdir):
    global CUSTOM_LIB
    os.makedirs(outdir, exist_ok=True)
    CUSTOM_LIB = os.path.join(outdir, 'AC30.kicad_sym')
    customlib.write(CUSTOM_LIB)

    root = Sheet('main', 'AC30.kicad_sch', 'SWTPC AC-30 Cassette Interface - Switching', ['A1', 'A0'])
    sub = Sheet('moddemod', 'AC30_moddemod_power.kicad_sch',
                'SWTPC AC-30 - Mod/Demod & Power interface pads', ['A3', 'A2', 'A1'])
    sheet_uuid = uid('sheetsym', 'moddemod')
    root_path = '/' + root.uuid
    sub_path = f'/{root.uuid}/{sheet_uuid}'

    main_parts = [p for p in netlist.parts if p['sheet'] == 'main']
    sub_parts = [p for p in netlist.parts if p['sheet'] == 'moddemod']

    layout(root, root_path, main_parts, wired=True, y0=60)
    text(root, NOTES_MAIN, 20.32, 20.32)
    layout(sub, sub_path, sub_parts, wired=True, y0=60)
    text(sub, NOTES_SUB, 20.32, 15.24)

    # PWR_FLAGs: supplies come in through pads, so nothing on the board drives them
    W, H = PAPERS[sub.paper]
    gx, gy = snap(W - 110), snap(17.78)
    for i, net in enumerate(['+5V', 'GND', 'V_RS232+', 'V_RS232-']):
        x, y = gx - 40.64, gy + i * 10.16
        Counter.n += 1
        ref = '#FLG%02d' % (i + 1)
        sub.add(f'(symbol (lib_id "power:PWR_FLAG") (at {f(x)} {f(y)} 0) (unit 1) (exclude_from_sim no) '
                f'(in_bom yes) (on_board yes) (dnp no) (uuid {q(uid("flag", ref))}) '
                f'(property "Reference" {q(ref)} (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
                f'(property "Value" "PWR_FLAG" (at {f(x)} {f(y - 3.81)} 0) {eff()}) '
                f'(property "Footprint" "" (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
                f'(property "Datasheet" "" (at {f(x)} {f(y)} 0) {eff(hide=True)}) '
                f'(pin "1" (uuid {q(uid("flagpin", ref))})) '
                f'(instances (project {q(PROJECT)} (path {q(sub_path)} (reference {q(ref)}) (unit 1)))))')
        sub.lib_ids.add('power:PWR_FLAG')
        wire(sub, x, y, x + 5.08, y)
        if net in netlist.POWER:
            place_power(sub, sub_path, net, x + 5.08, y, 0, 1 if net == 'GND' else -1)
        else:
            label(sub, net, x + 5.08, y, 1, 0)

    # sheet symbol on root
    W, H = PAPERS[root.paper]
    sx, sy = W - 90, 22.86
    sheet_sym = (f'(sheet (at {f(sx)} {f(sy)}) (size 60.96 15.24) (exclude_from_sim no) (in_bom yes) '
                 f'(on_board yes) (dnp no) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) '
                 f'(fill (color 0 0 0 0.0000)) (uuid {q(sheet_uuid)}) '
                 f'(property "Sheetname" "Mod/Demod & Power pads" (at {f(sx)} {f(sy - 0.71)} 0) {eff("left bottom")}) '
                 f'(property "Sheetfile" {q(sub.file)} (at {f(sx)} {f(sy + 15.95)} 0) {eff("left top")}) '
                 f'(instances (project {q(PROJECT)} (path {q(root_path)} (page "2")))))')
    comments = ['Source: docs/ac30_schematica.jpg, docs/AC30-BOM.md, docs/ac30_wiring1a.jpg',
                'Generated by kicad/tools/gen.py - edit netlist.py and regenerate, or edit in KiCad']
    write_sheet(os.path.join(outdir, root.file), root, root.uuid, sheet_sym, comments)
    write_sheet(os.path.join(outdir, sub.file), sub, root.uuid,
                comments=['Solder pads for the mod/demod and power supply (schematic not available in docs/)'],
                sheet_instances=False)

    with open(os.path.join(outdir, 'sym-lib-table'), 'w') as fh:
        fh.write('(sym_lib_table\n  (version 7)\n  (lib (name "AC30")(type "KiCad")(uri "${KIPRJMOD}/AC30.kicad_sym")'
                 '(options "")(descr "AC-30 parts missing from stock libraries"))\n)\n')
    pro = os.path.join(outdir, PROJECT + '.kicad_pro')
    if not os.path.exists(pro):
        import json
        json.dump({"meta": {"filename": PROJECT + ".kicad_pro", "version": 3},
                   "sheets": [[root.uuid, "Root"], [sheet_uuid, "Mod/Demod & Power"]]},
                  open(pro, 'w'), indent=2)
    print('main sheet paper', root.paper, 'sub sheet paper', sub.paper)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..'))
