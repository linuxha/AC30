"""Orthogonal wire router for the generated schematics.

Works on the 2.54 mm grid in integer cells. KiCad joins a wire end to anything it
touches, so the rules are:
  - wires of different nets may cross only straight through each other, never
    overlap, bend, end or branch on another net's cell;
  - no wire may pass through a symbol body, a pin, a label or a power symbol;
  - a net is a tree: each pin is joined to the nearest part of the tree already built.
"""
import heapq

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
BEND, CROSS, NEAR = 4, 3, 1          # extra costs: a bend, crossing a wire, hugging an obstacle


def axis(d):
    return 'h' if d[1] == 0 else 'v'


class Grid:
    def __init__(self):
        self.blocked = set()          # cells no wire may enter
        self.edges = {}               # (cell, cell) sorted -> net
        self.used = {}                # cell -> {net: set of axes}
        self.nodes = {}               # cell -> net: wire ends, bends, junctions, pin stubs

    # ---- obstacles and fixed wiring
    def block(self, c):
        self.blocked.add(c)

    def block_rect(self, x1, y1, x2, y2):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.blocked.add((x, y))

    def free(self, c):
        return c not in self.blocked and c not in self.used and c not in self.nodes

    def _edge(self, net, a, b):
        self.edges[tuple(sorted((a, b)))] = net
        ax = 'h' if a[1] == b[1] else 'v'
        for c in (a, b):
            self.used.setdefault(c, {}).setdefault(net, set()).add(ax)

    def stub(self, net, tip, end):
        """The fixed wire from a pin tip to its stub end."""
        self._edge(net, tip, end)
        self.nodes[tip] = net
        self.nodes[end] = net

    def node(self, net, c):
        self.nodes[c] = net

    # ---- routing
    def _others(self, c, net):
        return {m: a for m, a in self.used.get(c, {}).items() if m != net}

    def tree(self, net):
        return {c for c, nets in self.used.items() if net in nets} | \
               {c for c, m in self.nodes.items() if m == net}

    def route(self, net, start, came, bounds, tree):
        """Cells from start (a stub end, entered along direction `came`) to a cell of
        `tree` (the part of the net already joined up), or None.
        bounds = (x1, y1, x2, y2) in cells."""
        targets = {c for c in tree if not self._others(c, net)} - {start}
        if not targets:
            return None
        x1, y1, x2, y2 = bounds
        tx = [c[0] for c in targets]
        ty = [c[1] for c in targets]

        def h(c):                                   # distance to the targets' bbox
            dx = max(min(tx) - c[0], 0, c[0] - max(tx))
            dy = max(min(ty) - c[1], 0, c[1] - max(ty))
            return dx + dy

        start_state = (start, came)
        best = {start_state: 0}
        prev = {}
        heap = [(h(start), 0, start, came)]
        while heap:
            _, g, c, d = heapq.heappop(heap)
            if best.get((c, d), 1e9) < g:
                continue
            if c != start and c in targets:
                path = [c]
                s = (c, d)
                while s in prev:
                    s = prev[s]
                    path.append(s[0])
                return path[::-1]
            crossing = bool(self._others(c, net)) and c != start
            for nd in DIRS:
                if nd == (-d[0], -d[1]):
                    continue
                if crossing and nd != d:               # straight through other nets only
                    continue
                n = (c[0] + nd[0], c[1] + nd[1])
                if not (x1 <= n[0] <= x2 and y1 <= n[1] <= y2):
                    continue
                if n in self.blocked and n not in targets:
                    continue
                if self.edges.get(tuple(sorted((c, n))), net) != net:
                    continue
                others = self._others(n, net)
                if others:
                    if n in self.nodes and self.nodes[n] != net:
                        continue
                    if any(axis(nd) in a for a in others.values()):
                        continue                       # would run along another wire
                elif n in self.nodes and self.nodes[n] != net:
                    continue
                cost = g + 1 + (BEND if nd != d else 0) + (CROSS if others else 0)
                if any((n[0] + e[0], n[1] + e[1]) in self.blocked for e in DIRS):
                    cost += NEAR
                if cost < best.get((n, nd), 1e9):
                    best[(n, nd)] = cost
                    prev[(n, nd)] = (c, d)
                    heapq.heappush(heap, (cost + h(n), cost, n, nd))
        return None

    def commit(self, net, path):
        for a, b in zip(path, path[1:]):
            self._edge(net, a, b)
        self.nodes[path[0]] = net
        self.nodes[path[-1]] = net
        for a, b, c in zip(path, path[1:], path[2:]):
            if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                self.nodes[b] = net                    # bend

    # ---- output
    def segments(self):
        """Per net: maximal straight wires between nodes, and the junction cells."""
        adj = {}
        for (a, b), net in self.edges.items():
            adj.setdefault((net, a), set()).add(b)
            adj.setdefault((net, b), set()).add(a)
        wires, junctions = [], []
        seen = set()
        for (net, c), nbrs in adj.items():
            if len(nbrs) >= 3:
                junctions.append((net, c))
        for (a, b), net in self.edges.items():
            if (a, b) in seen:
                continue
            # extend the run both ways while the cell is a plain straight pass-through
            d = (b[0] - a[0], b[1] - a[1])
            run = [a, b]
            for end, step in ((b, d), (a, (-d[0], -d[1]))):
                c = end
                while True:
                    nbrs = adj[(net, c)]
                    n = (c[0] + step[0], c[1] + step[1])
                    if self.nodes.get(c) == net or len(nbrs) != 2 or n not in nbrs:
                        break
                    seen.add(tuple(sorted((c, n))))
                    c = n
                if end is b:
                    run[1] = c
                else:
                    run[0] = c
            seen.add((a, b))
            # mark every unit edge of the run as done
            x0, y0 = run[0]
            x1, y1 = run[1]
            sx = (x1 > x0) - (x1 < x0)
            sy = (y1 > y0) - (y1 < y0)
            c = run[0]
            while c != run[1]:
                n = (c[0] + sx, c[1] + sy)
                seen.add(tuple(sorted((c, n))))
                c = n
            wires.append((net, run[0], run[1]))
        return wires, junctions
