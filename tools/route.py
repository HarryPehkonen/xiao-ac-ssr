#!/usr/bin/env python3
"""Grid maze router for the generated board (headless, via pcbnew).

KiCad has no autorouter.  This is a small A* over a 0.5 mm grid with two
copper layers and vias, which is enough for a small through-hole board and,
unlike a hand-written coordinate table, survives a placement change.

Obstacles: every footprint's bounding box (inflated by the net's clearance),
earlier routes, and the board edge.  A net's own pads are opened up on the
layer they sit on so the router can actually reach them.  Clearance is
per-net: mains nets keep 3 mm from everything that is not mains, so the DRC
rule and the router agree.

    from route import route
    report = route(board, netitems, nets)
"""
import heapq
import os

import pcbnew

GRID = 0.5                      # mm
W, H = 150.0, 45.0              # mm, board size.  Must track gen_pcb.py's
                                # BOARD_W / BOARD_H: this grid *is* the board,
                                # so a stale H would let the router lay copper
                                # past the edge (DRC would flag it, but only
                                # after the fact).
# Mains-referenced nets: the triac gate circuit is on the hot side of the
# opto, so MOC_MT2 and TRIAC_G carry mains potential and owe logic 3 mm too.
# Classifying them as signal made them demand 3 mm from the mains zone they
# live in -- unroutable by construction.
MAINS = {"L_IN", "L_FUSED", "N_AC", "LOAD_L", "MOC_MT2", "TRIAC_G"}

CLEAR_MAINS = 3.0               # mains <-> anything else
CLEAR_MAINS_LOCAL = 1.0         # mains <-> mains (the 3 mm rule is the barrier)
CLEAR_NORMAL = 0.4              # everything <-> everything.  DRC requires
                                # 0.2 mm for the default netclass, but this is
                                # not just that plus slack: the router reasons
                                # about cell centres, so a diagonal run can pass
                                # ~0.4 mm closer to a pad than the cell model
                                # says (measured: 0.25 gave 12 shorts against
                                # no-net pads, 0.5 gave none, 0.4 is the floor).
# Override with MAINS_WIDTH_MM to ask "would a wider trace route?" -- that is
# the failing test in docs/ninny-brief.md, and it must stay a single command
# rather than an edit/run/revert dance.  The value drives both the trace width
# and the .kicad_dru floor, so the rule always asserts what was routed.
WIDTH_MAINS = float(os.environ.get("MAINS_WIDTH_MM", "1.5"))
                                # 1.5 mm carries 3.21 A (IPC-2221, 1 oz external,
                                # 10 C rise), which is what the fuse allows.
                                # It is also the measured maximum here: the
                                # trace has to reach the triac's *middle* pad,
                                # and its two neighbours (1.905 mm pads, 2.54 mm
                                # pitch) leave 3.175 mm edge to edge there.
                                # Pure DRC geometry would allow 2.775 mm; the
                                # grid plus its slack caps it at 2.067 mm; on
                                # the board 1.5 mm routes and 2.0 mm does not
                                # (measured: 'no path J4.1 -> Q1.2, pad-veto
                                # 132/144, free 12 cells, no path').  Raising the
                                # ceiling needs a necked pad entry -- a router
                                # feature this board does not have yet -- or
                                # switching the load outside the board.
WIDTH_POWER = 0.6
WIDTH_SIGNAL = 0.4
VIA_R_MAINS, VIA_R_SIGNAL = 0.5, 0.4     # via copper radius: 1.0 / 0.8 mm
                                   # diameter vias.  Blocking them at the
                                   # *track* half-width left them 0.2 mm
                                   # under-sized and tracks clipped the vias.
VIA_COST = 12                   # in cells, so vias are used deliberately
QUANT = GRID * 0.71             # half a cell diagonal: blocking is per cell
                                # centre, so every radius needs this much
                                # slack or tracks clip pads between cells
MOUNT_KEEPOUT_R = 3.0           # copper-free radius around a mounting hole.
                                # gen_pcb.py specs a 6 mm copper-free disc
                                # (MOUNT_KEEPOUT) because an M3 screw head sits
                                # over the hole and must not find copper;
                                # check_board.py measures the finished board
                                # against that spec, so the two cannot drift.
# The grid blocks cell *centres*, so a keepout has to be inflated by the widest
# copper that could pass on it (mains half-width; a mains via is only 0.5 mm
# radius) plus the half-cell diagonal, or a 1.5 mm mains track laid on the last
# free cell still puts its edge 0.75 mm inside the disc.  Measured on the dimmer,
# which this pass comes from: LOAD_L's edge came within 2.86 mm of H1 before the
# inflation.  On *this* board the corners were already clear -- every copper item
# is the pre-change routing translated 3 mm and L_IN's edge sits 6.05 mm from H1
# -- so the inflation is carried because the placement is free to move again,
# not because it was needed here.
MOUNT_BLOCK_R = MOUNT_KEEPOUT_R + WIDTH_MAINS / 2 + QUANT


def _c(v):
    return int(round(v / GRID))


def _mm(i):
    return i * GRID


class Grid:
    def __init__(self):
        self.nx, self.ny = _c(W) + 1, _c(H) + 1
        self.blocked = [bytearray(self.nx * self.ny), bytearray(self.nx * self.ny)]

    def idx(self, x, y):
        return y * self.nx + x

    def inside(self, x, y):
        return 2 <= x < self.nx - 2 and 2 <= y < self.ny - 2

    def block(self, x, y, layer=None):
        if not (0 <= x < self.nx and 0 <= y < self.ny):
            return
        if layer is None:
            self.blocked[0][self.idx(x, y)] = 1
            self.blocked[1][self.idx(x, y)] = 1
        else:
            self.blocked[layer][self.idx(x, y)] = 1

    def is_blocked(self, x, y, layer):
        # A cell that is not on the grid is not a cell this router may use, so
        # it reads as blocked -- the same refusal block(), unblock() and
        # inside() already make.  _open() walks a pad's opening box and its
        # escape spoke in cell coordinates and asks about every cell they land
        # on, so without this a pad within the opening's reach of an edge
        # indexes the bytearray off its end: IndexError from inside the router,
        # where the contract is the router's own "no path <ref>.<pad> ->
        # <ref>.<pad> [diagnosis]".
        if not (0 <= x < self.nx and 0 <= y < self.ny):
            return True
        return self.blocked[layer][self.idx(x, y)]

    def block_box(self, x0, y0, x1, y1, layer=None):
        for cx in range(_c(x0), _c(x1) + 1):
            for cy in range(_c(y0), _c(y1) + 1):
                self.block(cx, cy, layer)

    def block_disc(self, x0, y0, r, layer=None, clear=False):
        cr = _c(r)
        cx0, cy0 = _c(x0), _c(y0)
        for dx in range(-cr, cr + 1):
            for dy in range(-cr, cr + 1):
                if dx * dx + dy * dy <= cr * cr:
                    if clear:
                        self.unblock(cx0 + dx, cy0 + dy, layer)
                    else:
                        self.block(cx0 + dx, cy0 + dy, layer)

    def unblock(self, x, y, layer=None):
        if not (0 <= x < self.nx and 0 <= y < self.ny):
            return
        if layer is None:
            self.blocked[0][self.idx(x, y)] = 0
            self.blocked[1][self.idx(x, y)] = 0
        else:
            self.blocked[layer][self.idx(x, y)] = 0


def astar(grid, start, goal):
    """start/goal are (x, y, layer).  Returns a path or None."""
    def h(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) + 6 * abs(a[2] - b[2])

    openq = [(h(start, goal), 0, start)]
    came, cost = {}, {start: 0}
    while openq:
        _, g, cur = heapq.heappop(openq)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        if g > cost.get(cur, 1e18):
            continue
        x, y, layer = cur
        nbrs = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if grid.inside(nx, ny) and not grid.is_blocked(nx, ny, layer):
                nbrs.append(((nx, ny, layer), 1))
        other = 1 - layer
        if not grid.is_blocked(x, y, other):
            nbrs.append(((x, y, other), VIA_COST))
        for nxt, w in nbrs:
            ng = g + w
            if ng < cost.get(nxt, 1e18):
                cost[nxt] = ng
                came[nxt] = cur
                heapq.heappush(openq, (ng + h(nxt, goal), ng, nxt))
    return None


def _pad_box(pad, half, clear=CLEAR_NORMAL):
    """Axis-aligned keepout for a pad: its own copper, inflated by the board
    clearance, the routing half-width and the grid's half-diagonal.

    This was a disc of max(size)/2, which under-models two things at once: a
    TO-220 pad is a 1.905 x 2.0 mm rectangle whose corner sits 1.38 mm from the
    centre while the disc assumed 1.0 mm, and the track's own half-width was
    assumed to be WIDTH_SIGNAL/2 (0.2 mm) even for the 1.5 mm mains nets.
    Together that left ~0.9 mm of unmodelled metal -- measured here as LOAD_L
    running within 0.02 mm of Q1.1's pad.  A bounding box also handles rotated
    pads (a resistor on its side) for free.
    """
    bb = pad.GetBoundingBox()
    x0, y0 = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())
    x1 = x0 + pcbnew.ToMM(bb.GetWidth())
    y1 = y0 + pcbnew.ToMM(bb.GetHeight())
    r = clear + half + QUANT
    return (x0 - r, y0 - r, x1 + r, y1 + r)


def _block_pad(pad, grid, layer, half):
    grid.block_box(*_pad_box(pad, half), layer=layer)


def _in(box, x, y):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def _mounting_holes(board):
    """Centres of this board's mounting holes, in mm.

    Found on the board by footprint id, not from a table here: gen_pcb.py
    placed the holes, and a second table would be a second source of truth for
    something that already exists in exactly one place.
    """
    out = []
    for fp in board.GetFootprints():
        if str(fp.GetFPID().GetLibItemName()).startswith("MountingHole"):
            p = fp.GetPosition()
            out.append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))
    return out


def _to_segments(path):
    """Merge collinear grid steps into single track segments.

    One PCB_TRACK per 0.5 mm grid step produced 2,161 segments for 16 nets --
    file bloat, slow DRC, and a board nobody can read.  Merge runs instead.
    """
    segs, start, d0 = [], path[0], None
    for a, b in zip(path, path[1:]):
        if a[2] != b[2]:                      # layer change closes the run
            if d0 is not None:
                segs.append((start, a))
            start, d0 = b, None
            continue
        d = (b[0] - a[0], b[1] - a[1])
        if d0 is not None and d != d0:
            segs.append((start, a))
            start = a
        d0 = d
    if d0 is not None:
        segs.append((start, path[-1]))
    return segs


def _diagnose(grid, pad, mine, all_pads, vetoes, half):
    """Why a pad cannot be reached: how its opening survives the vetoes.

    Returns a short string for the failure message.  Guessing at placement
    changes without this wasted several rounds.
    """
    boxes = [_pad_box(q, half) for q, key in all_pads if key not in mine]
    x0, y0, x1, y1 = _pad_box(pad, half)
    tot = padveto = 0
    cop = [0, 0]
    free = [0, 0]
    for cx in range(_c(x0), _c(x1) + 1):
        for cy in range(_c(y0), _c(y1) + 1):
            tot += 1
            mx, my = _mm(cx), _mm(cy)
            if any(_in(b, mx, my) for b in boxes):
                padveto += 1
                continue
            for l in (0, 1):
                if any(v.is_blocked(cx, cy, l) for v in vetoes):
                    cop[l] += 1
                else:
                    free[l] += 1
    return (f"cells={tot} pad-veto={padveto} copper-veto L0={cop[0]}/L1={cop[1]} "
            f"free L0={free[0]}/L1={free[1]}")


def _open(grid, pad, mine, all_pads, vetoes, half):
    """Make a net's own pad reachable without opening a hole over a neighbour.

    A pad's keepout box overlaps the next pad's at 2.54 mm pitch, so simply
    clearing around my pad would free cells that sit on someone else's copper.
    Every other pad therefore vetoes the cells its own box owns.
    """
    boxes = [_pad_box(q, half) for q, key in all_pads if key not in mine]
    x0, y0, x1, y1 = _pad_box(pad, half)
    cr = max(_c(x1 - x0), _c(y1 - y0)) // 2 + 1
    for cx in range(_c(x0), _c(x1) + 1):
        for cy in range(_c(y0), _c(y1) + 1):
            mx, my = _mm(cx), _mm(cy)
            if any(_in(b, mx, my) for b in boxes):
                continue
            # per layer: copper on the other layer is no obstacle here
            if not any(v.is_blocked(cx, cy, 0) for v in vetoes):
                grid.unblock(cx, cy, 0)
            if not any(v.is_blocked(cx, cy, 1) for v in vetoes):
                grid.unblock(cx, cy, 1)

    # an escape spoke perpendicular to the nearest neighbour.  A pad in a
    # 2.54 mm pin column has most of its opening vetoed by its own neighbours
    # (the boxes of a TO-220's three pads overlap), so every pad gets a
    # channel out sideways.
    p = pad.GetPosition()
    mx0, my0 = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    cx0, cy0 = _c(mx0), _c(my0)
    near = None
    for q, key in all_pads:
        if key in mine:
            continue
        qx, qy = pcbnew.ToMM(q.GetPosition().x), pcbnew.ToMM(q.GetPosition().y)
        ddx, ddy = qx - mx0, qy - my0
        dist = (ddx * ddx + ddy * ddy) ** 0.5
        if 0 < dist < 4.0 and (near is None or dist < near[0]):
            near = (dist, ddx / dist, ddy / dist)

    if near is not None:
        ux, uy = -near[2], near[1]          # perpendicular to the neighbour
        for sgn in (1, -1):
            for k in range(1, cr + 2):
                cx = cx0 + int(round(sgn * ux * k))
                cy = cy0 + int(round(sgn * uy * k))
                mx, my = _mm(cx), _mm(cy)
                if any(_in(b, mx, my) for b in boxes):
                    break                    # runs into another pad: stop
                for l in (0, 1):
                    if not any(v.is_blocked(cx, cy, l) for v in vetoes):
                        grid.unblock(cx, cy, l)


def route(board, netitems, nets, verbose=True):
    """Route every net.  Returns {'routed': n, 'failed': {net: reason}}."""
    g_sig, g_mains = Grid(), Grid()        # keepout the active net obeys
    # Four records of routed copper, one per (copper class, consumer class)
    # clearance pair, so that opening a pad never shaves the outer ring off an
    # earlier route's clearance and never over-vetoes a pad either.
    cop_m2m, cop_m2s = Grid(), Grid()      # mains copper, for mains / logic
    cop_s2s, cop_s2m = Grid(), Grid()      # signal copper, for logic / mains

    # Copper, not bodies, is what matters: block every pad's keepout box on
    # both layers.  Blocking whole footprint bounding boxes instead traps a
    # pad inside its own box and nothing routes.  This first pass uses the
    # signal width; each net re-asserts it with its own half-width.
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            _block_pad(pad, g_sig, None, WIDTH_SIGNAL / 2)
            _block_pad(pad, g_mains, None, WIDTH_SIGNAL / 2)

    # A mounting hole is a keepout, not an obstacle to route around: an M3
    # screw head sits over it, so no copper may come within MOUNT_KEEPOUT_R.
    # Blocked on both occupancy grids *and* kept as a veto below, because
    # _open() clears cells around a net's own pads and would otherwise punch a
    # pad's escape spoke straight through the disc.
    holes = _mounting_holes(board)
    keepout = Grid()
    for hx, hy in holes:
        for g in (g_sig, g_mains, keepout):
            g.block_disc(hx, hy, MOUNT_BLOCK_R)

    def span(n):
        """How far apart this net's own pads are: the longest pad-to-pad hop.

        Short nets route first, while there is still room, instead of being
        walled in by the long ones.  The longest hop -- not the shortest -- is
        the right measure: a net with one tight pair and one far pad still has
        to reach the far pad, and that is what blocks other pads' escapes.
        (Measured on this board: ordering by the *shortest* hop put TRIAC_G,
        whose far hop is 20 mm, ahead of LOAD_L, whose pads are 41 mm apart but
        whose local hop is only 16 mm -- and TRIAC_G's 2.8 mm track up the side
        of Q1 then sealed LOAD_L's only escape.)
        """
        ps = _pads(board, n)
        if len(ps) < 2:
            return 0
        far = 0
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                pa, pb = a.GetPosition(), b.GetPosition()
                d = ((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2) ** 0.5
                far = max(far, d)
        return far

    order = sorted(nets, key=lambda n: (n not in MAINS, span(n)))
    failed = {}
    routed = 0
    all_pads = []

    for fp in board.GetFootprints():
        for pad in fp.Pads():
            all_pads.append((pad, (fp.GetReference(), pad.GetNumber())))

    for net in order:
        pads = [p for p in _pads(board, net)]
        if len(pads) < 2:
            continue
        mains = net in MAINS
        width = (WIDTH_MAINS if mains else
                 WIDTH_POWER if net in ("GND", "+5V_PS", "+5V_XIAO")
                 else WIDTH_SIGNAL)
        clear = CLEAR_MAINS if mains else CLEAR_NORMAL
        half = width / 2
        # Two occupancy grids: g_sig holds what a *logic* net must avoid (mains
        # copper plus the barrier), g_mains what a *mains* net must avoid.  One
        # grid would fence the mains nets off from each other by their own 3 mm
        # keepout and nothing in the mains zone would route.
        grid = g_mains if mains else g_sig
        own = CLEAR_MAINS_LOCAL if mains else CLEAR_NORMAL
        via_r = VIA_R_MAINS if mains else VIA_R_SIGNAL

        # every pad keeps its keepout; this net's own pads are then opened --
        # re-asserting first means an earlier net cannot have left a hole.
        # Both steps use *this* net's half-width: a 1.5 mm mains track needs a
        # wider berth round a neighbouring pad than a 0.4 mm signal does.
        for q, _key in all_pads:
            _block_pad(q, grid, None, half)
        mine = {(p.GetParentFootprint().GetReference(), p.GetNumber())
                for p in pads}
        for pad in pads:
            _open(grid, pad, mine, all_pads,
                  (cop_m2m, cop_s2m, keepout) if mains
                  else (cop_m2s, cop_s2s, keepout), half)

        ok = True
        segs, vias = [], []
        anchor = pads[0]
        for pad in pads[1:]:
            s = (_c(pcbnew.ToMM(anchor.GetPosition().x)),
                 _c(pcbnew.ToMM(anchor.GetPosition().y)), 0)
            g = (_c(pcbnew.ToMM(pad.GetPosition().x)),
                 _c(pcbnew.ToMM(pad.GetPosition().y)), 0)
            grid.unblock(s[0], s[1], None)
            grid.unblock(g[0], g[1], None)
            path = astar(grid, s, g)
            if path is None:
                vet = ((cop_m2m, cop_s2m, keepout) if mains
                       else (cop_m2s, cop_s2s, keepout))
                why = _diagnose(grid, pad, mine, all_pads, vet, half)
                failed[net] = (f"no path {_ref(anchor)}.{anchor.GetNumber()}"
                               f" -> {_ref(pad)}.{pad.GetNumber()} [{why}]")
                ok = False
                break
            for i, (prev, cur) in enumerate(zip(path, path[1:])):
                if prev[2] != cur[2]:
                    if i < 2 or i > len(path) - 3:
                        continue        # a pad already joins the two layers,
                                        # and a via on top of a pad's hole
                                        # breaks the hole-to-hole rule
                    vias.append((cur[0], cur[1]))
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(_mm(cur[0])),
                                                    pcbnew.FromMM(_mm(cur[1]))))
                    via.SetWidth(pcbnew.FromMM(0.8 if not mains else 1.0))
                    via.SetDrill(pcbnew.FromMM(0.4 if not mains else 0.5))
                    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    via.SetNet(netitems[net])
                    board.Add(via)
            for a, b in _to_segments(path):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(_mm(a[0])),
                                           pcbnew.FromMM(_mm(a[1]))))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(_mm(b[0])),
                                         pcbnew.FromMM(_mm(b[1]))))
                t.SetWidth(pcbnew.FromMM(width))
                t.SetLayer(pcbnew.F_Cu if a[2] == 0 else pcbnew.B_Cu)
                t.SetNet(netitems[net])
                board.Add(t)
            segs.extend(path)
            anchor = pad
        # the new copper becomes an obstacle for later nets, on the layer it
        # sits on; a via blocks both.  Each grid takes the clearance this net
        # owes the other class.
        for g, r in ((g_sig, clear), (g_mains, own)):
            for x, y, l in segs:
                g.block_disc(_mm(x), _mm(y), half + r + QUANT, l)
            for x, y in vias:
                g.block_disc(_mm(x), _mm(y), max(half, via_r) + r + QUANT)

        # record the new copper at the spacing it owes each class
        for g, r in ((cop_m2m, CLEAR_MAINS_LOCAL), (cop_m2s, CLEAR_MAINS)) \
                if mains else ((cop_s2s, CLEAR_NORMAL), (cop_s2m, CLEAR_MAINS)):
            for x, y, l in segs:
                g.block_disc(_mm(x), _mm(y), half + r + QUANT, l)
            for x, y in vias:
                g.block_disc(_mm(x), _mm(y), max(half, via_r) + r + QUANT)

        # close the net's own pads again, inflated by this net's clearance
        for pad in pads:
            for g, r in ((g_sig, clear), (g_mains, own)):
                g.block_box(*_pad_box(pad, half, r))
        if ok:
            routed += 1
    if verbose:
        print(f"routed {routed}/{len(nets)} nets"
              + (f", failed: {failed}" if failed else ""))
    return {"routed": routed, "failed": failed}


def _ref(pad):
    try:
        return pad.GetParentFootprint().GetReference()
    except AttributeError:
        return "?"


def _pads(board, net):
    """Pads of a net, in a stable order (schematic order would be nicer, but
    footprint order keeps re-runs deterministic)."""
    out = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        for pad in fp.Pads():
            if pad.GetNetname().lstrip("/") == net:
                out.append(pad)
    return out
