"""Autoroute AC30.kicad_pcb with FreeRouting (Specctra DSN/SES round trip).
Run with the KiCad AppImage's python (needs its pcbnew module):
    kicad.AppImage python3.11 tools/route.py <board.kicad_pcb> <freerouting.jar> [passes]
Each round exports a DSN (existing tracks included), routes it, imports the SES and
removes the dangling stubs FreeRouting leaves behind. Rounds repeat until nothing is
left unrouted or the round limit is reached. The board is saved in place."""
import os, subprocess, sys, tempfile
import pcbnew

ROUNDS = 3


def connected_ends(board):
    """Map (layer, x, y) -> number of copper items touching that point."""
    hits = {}
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                k = (layer, t.GetPosition().x, t.GetPosition().y)
                hits[k] = hits.get(k, 0) + 1
        else:
            for p in (t.GetStart(), t.GetEnd()):
                k = (t.GetLayer(), p.x, p.y)
                hits[k] = hits.get(k, 0) + 1
    return hits


def on_pad(board, layer, pos, net):
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == net and pad.IsOnLayer(layer) and pad.HitTest(pos):
                return True
    return False


def remove_stubs(board):
    """Delete duplicate segments, then segments with an end that touches nothing and
    vias used on fewer than two layers; repeat until stable."""
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
        hits = connected_ends(board)
        dead = []
        for t in board.GetTracks():
            t = t.Cast()
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                # each layer: the via itself plus at least one track end
                if sum(hits[(layer, p.x, p.y)] > 1 for layer in (pcbnew.F_Cu, pcbnew.B_Cu)) < 2:
                    dead.append(t)
                continue
            for p in (t.GetStart(), t.GetEnd()):
                if hits[(t.GetLayer(), p.x, p.y)] == 1 and \
                        not on_pad(board, t.GetLayer(), p, t.GetNetCode()):
                    dead.append(t)
                    break
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
        with open(os.path.join(tmp, f'r{rnd}.log'), 'w') as log:
            subprocess.run(['java', '-jar', jar, '-de', dsn, '-do', ses, '-mp', str(passes),
                            '-mt', '1', '--gui.enabled=false', '--api_server.enabled=false'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        if not pcbnew.ImportSpecctraSES(board, ses):     # replaces all tracks and vias
            sys.exit('SES import failed')
        stubs = remove_stubs(board)
        left = unrouted(board)
        n = len(board.GetTracks())
        print(f'round {rnd}: {n} tracks/vias, {stubs} stubs removed, {left} unrouted')
        if left == 0:
            break
    board.Save(path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4]))
