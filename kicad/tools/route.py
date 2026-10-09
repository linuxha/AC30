"""Autoroute AC30.kicad_pcb with FreeRouting (Specctra DSN/SES round trip).
Run with the KiCad AppImage's python (needs its pcbnew module):
    kicad.AppImage python3.11 tools/route.py <board.kicad_pcb> <freerouting launcher or .jar> [passes]
Each round exports a DSN (existing tracks included), routes it, imports the SES and
removes the dangling stubs FreeRouting leaves behind. By default there is one round.
A round on a board that already has tracks (a finishing pass, or ROUTE_ROUNDS=n)
marks the existing wiring as protected, so FreeRouting only adds what is missing.
build.sh retries from the unrouted board and keeps a DRC-clean result. The board is
saved in place."""
import math, os, subprocess, sys, tempfile
import pcbnew

ROUNDS = int(os.environ.get('ROUTE_ROUNDS', 1))   # >1 re-routes on top of earlier rounds


def _dist(px, py, x1, y1, x2, y2):
    """Distance from point (px, py) to the segment (x1, y1)-(x2, y2)."""
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _copper(board):
    """Segments and vias grouped by (layer, net), plus same-net pads per layer."""
    segs, vias = {}, {}
    for t in board.GetTracks():
        t = t.Cast()
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                vias.setdefault((layer, t.GetNetCode()), []).append((t, p.x, p.y, t.GetWidth(pcbnew.F_Cu) / 2))
        else:
            a, b = t.GetStart(), t.GetEnd()
            segs.setdefault((t.GetLayer(), t.GetNetCode()), []).append((t, a.x, a.y, b.x, b.y, t.GetWidth() / 2))
    pads = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(layer):
                    pads.setdefault((layer, pad.GetNetCode()), []).append(pad)
    return segs, vias, pads


def _touches(key, x, y, me, segs, vias, pads):
    """Is (x, y) on layer/net `key` touched by copper other than item `me`?"""
    for (t, x1, y1, x2, y2, hw) in segs.get(key, ()):
        if t is not me and _dist(x, y, x1, y1, x2, y2) <= hw + 1:
            return True
    for (v, vx, vy, r) in vias.get(key, ()):
        if v is not me and math.hypot(x - vx, y - vy) <= r + 1:
            return True
    pos = pcbnew.VECTOR2I(int(x), int(y))
    return any(pad.HitTest(pos) for pad in pads.get(key, ()))


def remove_stubs(board):
    """Delete duplicate segments, then segments with an end that touches no other copper
    (pad, via, or any point of another same-net track: FreeRouting makes T-junctions)
    and vias used on fewer than two layers; repeat until stable."""
    removed = 0
    seen = set()
    for t in list(board.GetTracks()):
        t = t.Cast()
        if t.Type() == pcbnew.PCB_VIA_T:
            continue
        a, b = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
        key = (t.GetLayer(), t.GetNetCode(), min(a, b), max(a, b))
        if key in seen or a == b:
            board.Delete(t)
            removed += 1
        seen.add(key)
    while True:
        segs, vias, pads = _copper(board)
        dead = []
        for key, items in segs.items():
            for (t, x1, y1, x2, y2, hw) in items:
                if not (_touches(key, x1, y1, t, segs, vias, pads) and
                        _touches(key, x2, y2, t, segs, vias, pads)):
                    dead.append(t)
        done = set()
        for key, items in vias.items():
            for (v, vx, vy, r) in items:
                if id(v) in done:
                    continue
                done.add(id(v))
                net = key[1]
                used = sum(_touches((layer, net), vx, vy, v, segs, vias, pads)
                           for layer in (pcbnew.F_Cu, pcbnew.B_Cu))
                if used < 2:
                    dead.append(v)
        if not dead:
            return removed
        for t in dead:
            board.Delete(t)
        removed += len(dead)


def unrouted(board):
    board.BuildConnectivity()
    return board.GetConnectivity().GetUnconnectedCount(False)


def main(path, jar, passes=100):
    board = pcbnew.LoadBoard(path)
    tmp = tempfile.mkdtemp()
    for rnd in range(1, ROUNDS + 1):
        dsn, ses = os.path.join(tmp, f'r{rnd}.dsn'), os.path.join(tmp, f'r{rnd}.ses')
        if not pcbnew.ExportSpecctraDSN(board, dsn):
            sys.exit('DSN export failed')
        before = len(board.GetTracks())
        mp = passes
        if before:
            # Finishing round: protect the existing wiring so FreeRouting only adds the
            # missing connections (re-optimising everything is slow and can drop wires).
            text = open(dsn).read().replace('(type route)', '(type protect)')
            open(dsn, 'w').write(text)
            mp = min(passes, 20)
        with open(os.path.join(tmp, f'r{rnd}.log'), 'w') as log:
            cmd = ['java', '-jar', jar] if jar.endswith('.jar') else [jar]   # 2.4+: native launcher
            subprocess.run(cmd + ['-de', dsn, '-do', ses, '-mp', str(mp),
                                  '-mt', '1', '--gui.enabled=false', '--api_server.enabled=false'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        saved = os.path.join(tmp, f'r{rnd}_before.kicad_pcb')
        board.Save(saved)
        if not pcbnew.ImportSpecctraSES(board, ses):     # replaces all tracks and vias
            sys.exit('SES import failed')
        if before and len(board.GetTracks()) < before:
            # the session lost existing wiring: keep the board as it was
            print(f'round {rnd}: session dropped wiring ({len(board.GetTracks())} < {before}); kept previous')
            board = pcbnew.LoadBoard(saved)
            break
        stubs = remove_stubs(board)
        left = unrouted(board)
        n = len(board.GetTracks())
        print(f'round {rnd}: {n} tracks/vias, {stubs} stubs removed, {left} unrouted')
        if left == 0:
            break
    board.Save(path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4]))
