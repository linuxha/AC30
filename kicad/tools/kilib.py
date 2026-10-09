"""Load KiCad library symbols, flatten 'extends', report pins."""
import copy, math, os, re
from sexp import parse, find, find1, Sym

LIBDIR = os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')
_cache = {}

def _lib(name, path=None):
    if name not in _cache:
        p = path or os.path.join(LIBDIR, name + '.kicad_sym')
        if path or os.path.exists(p):
            files = [p]
        else:   # KiCad 10 layout: <name>.kicad_symdir/ with one file per symbol
            d = os.path.join(LIBDIR, name + '.kicad_symdir')
            files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.kicad_sym')]
        _cache[name] = {s[1]: s for f in files for s in find(parse(open(f).read()), 'symbol')}
    return _cache[name]

def get(lib_id, path=None):
    """Return flattened symbol definition named lib_id ('Lib:Name')."""
    s = _get(lib_id, path)
    s[1] = lib_id
    return s

def _get(lib_id, path=None):
    lib, name = lib_id.split(':')
    syms = _lib(lib, path)
    s = copy.deepcopy(syms[name])
    ext = find1(s, 'extends')
    if ext:
        parent = _get(lib + ':' + ext[1], path)
        pname = parent[1]
        # child props override parent's
        cprops = {p[1]: p for p in find(s, 'property')}
        out = [Sym('symbol'), name]
        for item in parent[2:]:
            if isinstance(item, list) and item[0] == 'property' and item[1] in cprops:
                out.append(cprops.pop(item[1]))
            elif isinstance(item, list) and item[0] == 'symbol':
                sub = copy.deepcopy(item)
                sub[1] = name + sub[1][len(pname):]
                out.append(sub)
            else:
                out.append(item)
        # remaining new child props: insert before first sub-symbol
        idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == 'symbol')
        for p in cprops.values():
            out.insert(idx, p); idx += 1
        s = out
    return s

def pins(sym):
    """List of dicts: unit, number, name, x, y, angle (lib coords, Y up)."""
    res = []
    base = sym[1].split(':')[-1]
    for sub in find(sym, 'symbol'):
        m = re.search(r'_(\d+)_(\d+)$', sub[1])
        unit, style = int(m.group(1)), int(m.group(2))
        if style == 2:
            continue
        for p in find(sub, 'pin'):
            at = find1(p, 'at')
            res.append(dict(unit=unit, number=find1(p, 'number')[1], name=find1(p, 'name')[1],
                            x=float(at[1]), y=float(at[2]), angle=float(at[3]) if len(at) > 3 else 0.0,
                            etype=str(p[1])))
    return res

def units(sym):
    return sorted({p['unit'] for p in pins(sym)} - {0})


def body_bbox(sym, unit):
    """Bounding box (lib coords) of the graphic primitives of one unit (style 1)."""
    xs, ys = [], []
    for sub in find(sym, 'symbol'):
        m = re.search(r'_(\d+)_(\d+)$', sub[1])
        if int(m.group(1)) not in (0, unit) or int(m.group(2)) == 2:
            continue
        for g in sub[2:]:
            if not isinstance(g, list):
                continue
            if g[0] == 'rectangle':
                for k in ('start', 'end'):
                    v = find1(g, k); xs.append(float(v[1])); ys.append(float(v[2]))
            elif g[0] in ('polyline', 'bezier'):
                for xy in find(find1(g, 'pts'), 'xy'):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif g[0] == 'circle':
                c = find1(g, 'center'); r = float(find1(g, 'radius')[1])
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
            elif g[0] == 'arc':
                for k in ('start', 'mid', 'end'):
                    v = find1(g, k); xs.append(float(v[1])); ys.append(float(v[2]))
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))
