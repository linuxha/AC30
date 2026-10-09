"""Writes AC30.kicad_sym: symbols missing from the stock KiCad libraries."""
from sexp import q

def _font():
    return '(effects (font (size 1.27 1.27)))'

def _prop(name, val, x=0, y=0, hide=False):
    h = ' (hide yes)' if hide else ''
    return f'(property {q(name)} {q(val)} (at {x} {y} 0) (effects (font (size 1.27 1.27)){h}))'

def _pin(num, name, etype, x, y, ang, length=2.54):
    return (f'(pin {etype} line (at {x} {y} {ang}) (length {length}) '
            f'(name {q(name)} {_font()}) (number {q(num)} {_font()}))')

def _box(x1, y1, x2, y2):
    return (f'(rectangle (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width 0.254) (type default)) (fill (type background)))')

def _poly(pts, fill='none'):
    p = ' '.join(f'(xy {x} {y})' for x, y in pts)
    return f'(polyline (pts {p}) (stroke (width 0.254) (type default)) (fill (type {fill})))'

def _unit(name, u, body):
    return f'(symbol {q(f"{name}_{u}_1")} {" ".join(body)})'

def _sym(name, ref, desc, units, fp=''):
    return (f'(symbol {q(name)} (pin_names (offset 0.254)) (exclude_from_sim no) (in_bom yes) (on_board yes) '
            + _prop('Reference', ref, 0, 8.89) + _prop('Value', name, 0, -8.89)
            + _prop('Footprint', fp, hide=True) + _prop('Datasheet', '', hide=True)
            + _prop('Description', desc, hide=True) + ' '.join(units) + ' (embedded_fonts no))')

def mc1488():
    tri = _poly([(-5.08, 5.08), (5.08, 0), (-5.08, -5.08), (-5.08, 5.08)], 'background')
    circ = '(circle (center 5.715 0) (radius 0.635) (stroke (width 0.254) (type default)) (fill (type none)))'
    units = []
    gates = [('2',), ('4', '5'), ('9', '10'), ('12', '13')]
    outs = ['3', '6', '8', '11']
    for i, (ins, out) in enumerate(zip(gates, outs), 1):
        body = [tri, circ, _pin(out, '~', 'output', 8.89, 0, 180, 2.54)]
        ys = [0] if len(ins) == 1 else [2.54, -2.54]
        for n, y in zip(ins, ys):
            body.append(_pin(n, '~', 'input', -7.62, y, 0, 2.54 if y == 0 else 3.81))
        units.append(_unit('MC1488', i, body))
    units.append(_unit('MC1488', 5, [_box(-5.08, 5.08, 5.08, -5.08),
                                     _pin('14', 'VCC', 'power_in', 0, 7.62, 270),
                                     _pin('1', 'VEE', 'power_in', -2.54, -7.62, 90),
                                     _pin('7', 'GND', 'power_in', 2.54, -7.62, 90)]))
    return _sym('MC1488', 'U', 'Quad RS-232 line driver (NAND), +/-V supply',
                units, 'Package_DIP:DIP-14_W7.62mm')

def mc1489():
    tri = _poly([(-5.08, 5.08), (5.08, 0), (-5.08, -5.08), (-5.08, 5.08)], 'background')
    circ = '(circle (center 5.715 0) (radius 0.635) (stroke (width 0.254) (type default)) (fill (type none)))'
    units = []
    for i, (inp, ctl, out) in enumerate([('1', '2', '3'), ('4', '5', '6'), ('10', '9', '8'), ('13', '12', '11')], 1):
        units.append(_unit('MC1489', i, [tri, circ,
                                         _pin(inp, '~', 'input', -7.62, 0, 0),
                                         _pin(ctl, 'RC', 'input', 0, -7.62, 90, 5.08),
                                         _pin(out, '~', 'output', 8.89, 0, 180)]))
    units.append(_unit('MC1489', 5, [_box(-5.08, 5.08, 5.08, -5.08),
                                     _pin('14', 'VCC', 'power_in', 0, 7.62, 270),
                                     _pin('7', 'GND', 'power_in', 0, -7.62, 90)]))
    return _sym('MC1489', 'U', 'Quad RS-232 line receiver (inverting)',
                units, 'Package_DIP:DIP-14_W7.62mm')

def reed_relay():
    body = [_box(-7.62, 2.54, -2.54, -2.54),
            _poly([(-6.35, -2.54), (-3.81, 2.54)]),
            _poly([(5.08, 5.08), (5.08, 2.54)]),
            _poly([(5.08, -5.08), (5.08, -2.54), (3.81, 2.54)]),
            _poly([(-2.54, 0), (4.445, 0)]),
            _pin('1', '~', 'passive', -5.08, 7.62, 270, 5.08),
            _pin('2', '~', 'passive', -5.08, -7.62, 90, 5.08),
            _pin('3', '~', 'passive', 5.08, 7.62, 270, 2.54),
            _pin('4', '~', 'passive', 5.08, -7.62, 90, 2.54)]
    return _sym('Reed_Relay_SPST_NO', 'RLY', 'Reed relay, SPST-NO, coil 1-2, contact 3-4',
                [_unit('Reed_Relay_SPST_NO', 1, body)])

def write(path):
    with open(path, 'w') as f:
        f.write('(kicad_symbol_lib (version 20241209) (generator "ac30_gen") (generator_version "1.0")\n')
        for s in (mc1488(), mc1489(), reed_relay()):
            f.write('  ' + s + '\n')
        f.write(')\n')
