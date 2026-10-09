"""Minimal S-expression reader/writer for KiCad files."""
import re

class Sym(str):
    """Unquoted atom."""

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))', re.S)

def parse(text):
    stack, cur = [], []
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError("bad sexp at %d" % pos)
        pos = m.end()
        if m.group(1):
            stack.append(cur); cur = []
        elif m.group(2):
            done = cur; cur = stack.pop(); cur.append(done)
        elif m.group(3) is not None:
            s = m.group(3)[1:-1].replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
            cur.append(s)
        else:
            cur.append(Sym(m.group(4)))
    return cur[0] if len(cur) == 1 else cur

def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def dump(e, ind=0):
    if isinstance(e, list):
        if not any(isinstance(x, list) for x in e):
            return '(' + ' '.join(dump(x) for x in e) + ')'
        pad = '\t' * (ind + 1)
        out = '('
        first = True
        for x in e:
            if isinstance(x, list):
                out += '\n' + pad + dump(x, ind + 1)
            else:
                out += ('' if first else ' ') + dump(x)
            first = False
        return out + '\n' + '\t' * ind + ')'
    if isinstance(e, Sym):
        return str(e)
    if isinstance(e, (int, float)):
        return fmt(e)
    return q(e)

def fmt(v):
    if isinstance(v, float):
        s = ('%.4f' % v).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(v)

def find(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]

def find1(e, key):
    r = find(e, key)
    return r[0] if r else None
