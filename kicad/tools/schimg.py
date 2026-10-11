#!/usr/bin/env python3
"""Schematic images: one PNG per sheet and one per functional block, cut from the
schematic PDF (kicad-cli sch export pdf) at the block positions gen.py recorded.

Usage: python3 -I schimg.py <schematic.pdf> <groups.json> <out_dir> <prefix>
Needs pdftoppm (poppler-utils).
"""
import json, os, re, subprocess, sys

SHEET_DPI = 100          # whole sheets (A0 at 100 dpi is about 4700 x 3300 px)
BLOCK_DPI = 150          # functional blocks, readable on screen
PAD = 5.0                # mm around each block


def slug(s):
    s = re.sub(r'[^A-Za-z0-9]+', '-', s.split(':')[0]).strip('-')
    return s[:40].rstrip('-')


def main(pdf, groups, out, prefix):
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith('.png'):
            os.remove(os.path.join(out, f))
    boxes = json.load(open(groups))
    sheets = list(dict.fromkeys(b['sheet'] for b in boxes))    # page order = first appearance
    # the root sheet is page 1, then the sub-sheets in gen.py's order
    root = [s for s in sheets if s == prefix + '.kicad_sch']
    pages = {s: i + 1 for i, s in enumerate(root + [s for s in sheets if s not in root])}
    for s, page in pages.items():
        name = f'{prefix}-sheet{page}'
        subprocess.run(['pdftoppm', '-png', '-singlefile', '-r', str(SHEET_DPI), '-f', str(page),
                        '-l', str(page), pdf, os.path.join(out, name)], check=True)
    n = 0
    for b in boxes:
        n += 1
        k = BLOCK_DPI / 25.4
        x, y = max(0, b['x'] - PAD) * k, max(0, b['y'] - PAD) * k
        w, h = (b['w'] + 2 * PAD) * k, (b['h'] + 2 * PAD) * k
        name = f'{prefix}-{n:02d}-{slug(b["group"])}'
        page = pages[b['sheet']]
        subprocess.run(['pdftoppm', '-png', '-singlefile', '-r', str(BLOCK_DPI), '-f', str(page),
                        '-l', str(page), '-x', str(int(x)), '-y', str(int(y)), '-W', str(int(w)),
                        '-H', str(int(h)), pdf, os.path.join(out, name)], check=True)
    print(f'schematic images: {len(pages)} sheets, {n} blocks in {os.path.basename(out)}/')


if __name__ == '__main__':
    main(*sys.argv[1:5])
