#!/usr/bin/env python3
"""Generate the PCB for the XIAO AC dimmer board (headless, via pcbnew).

Nets come from the *schematic* (kicad-cli netlist export), so the board can
never disagree with the design about connectivity.  Placement and routing are
explicit tables here, the same way the schematic is generated.

    python3 tools/gen_pcb.py            # write xiao-ac-dimmer.kicad_pcb
    python3 tools/gen_pcb.py --dump     # print pad coordinates per net
"""
import os
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_sch
import kicadlib as kl
import route as router

ROOT = gen_sch.ROOT
PROJECT = gen_sch.PROJECT
BOARD = os.path.join(ROOT, PROJECT + ".kicad_pcb")
SCH = os.path.join(ROOT, PROJECT + ".kicad_sch")
MM = pcbnew.FromMM


def mm(v):
    return round(float(v), 3)


# ---------------------------------------------------------------- placement --
# Board is 150 x 45 mm in five vertical strips.  Mains lives on the left;
# PS1 and U2 straddle the middle strip because their own creepage is the
# barrier; logic sits on the right.  Parts are *packed* inside their strip
# (row by row, no overlaps by construction) rather than hand-placed, so the
# same script keeps working when the part list changes.
#
# A strip is (x0, y0, x1): packing starts at y0 and wraps to a new row once it
# would cross x1.  Rows run downwards until the part list is exhausted, so the
# board height is sized around the packed result (see BOARD_H) instead of the
# packing being fenced in by a height chosen first.
GROUPS = [
    # mains: cord in -> fuse -> protection -> cord out, with the triac beside
    # the outlet so its load pad (Q1.2) is a short hop from J4.  The dimmer's
    # board failed to route LOAD_L when the triac sat at the far end of the
    # mains strip; here the ordering puts them together.
    ((4, 6, 50), [("J3", 0), ("F1", 0), ("MOV1", 0), ("J4", 0), ("Q1", 0)]),
    # the triac's gate resistor, in its own strip against the barrier: it is
    # mains-referenced (gate-side of the opto) so it owes logic 3 mm
    ((52, 6, 58), [("R4", 90)]),
    # parts that straddle the barrier, U2 first so its logic pins face the
    # logic-side cluster and its mains pins face the resistor strip
    ((62, 6, 96), [("U2", 180), ("PS1", 0)]),
    # logic-side resistors and the 5 V rail, right of the barrier
    ((100, 6, 126), [("R3", 90), ("D5", 0), ("C1", 0), ("C2", 0)]),
    ((130, 6, 147), [("J1", 0), ("J2", 0)]),
]
MARGIN = 2.5          # mm between packed parts
# The outline is sized to the packed parts, not chosen up front.  The 14 parts
# span 33.8 mm (first row top at y = 6, deepest part at y = 39.8).  45 mm keeps
# that 6 mm at the top and leaves 5.2 mm below the last row -- 15% spare on that
# side, the same rule the dimmer's 57 mm came from (Harri's tolerance is
# 10-20%, and this board is the sibling of that one).  150 x 45 mm = 67.5 cm2,
# down from 150 x 95 mm = 142.5 cm2, which the board carried because it was
# built before the calibration existed.
#
# The measured floor for this part list is 40 mm (11/11 routed, DRC clean);
# 39 mm starts warning.  45 stays clear of it rather than spending a reroute
# defending 5 mm.
BOARD_W, BOARD_H = 150.0, 45.0


def place_all(fps):
    """Pack each group's parts into rows inside its zone.  Returns
    {ref: (x, y, rot)} for reporting."""
    out = {}
    for (x0, y0, x1), parts in GROUPS:
        cx, cy, rowh = x0, y0, 0.0
        for ref, rot in parts:
            fp = fps[ref]
            fp.SetOrientationDegrees(rot)
            bb = fp.GetBoundingBox(False, False)
            pos = fp.GetPosition()
            w = pcbnew.ToMM(bb.GetWidth())
            h = pcbnew.ToMM(bb.GetHeight())
            if cx + w > x1 and cx > x0:
                cx, cy, rowh = x0, cy + rowh + MARGIN, 0.0
            fp.SetPosition(pcbnew.VECTOR2I(
                MM(cx - (pcbnew.ToMM(bb.GetX()) - pcbnew.ToMM(pos.x))),
                MM(cy - (pcbnew.ToMM(bb.GetY()) - pcbnew.ToMM(pos.y)))))
            out[ref] = (round(cx, 2), round(cy, 2), rot)
            cx += w + MARGIN
            rowh = max(rowh, h)
    return out


# Every net is routed on whichever layer the maze router finds; there is no
# fixed per-layer assignment (the dimmer carried a BOTTOM table that nothing
# read).

EDGE = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H), (0, 0)]


def schematic_nets():
    """{net: [(ref, pad)]} straight from the verified schematic."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "net.net")
        subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format",
                        "kicadsexpr", "-o", out, SCH], check=True,
                       capture_output=True)
        text = open(out, encoding="utf-8").read()
    tree = kl.parse(text)[0]
    nets = {}
    for net in kl.kids(kl.kid(tree, "nets"), "net"):
        name = kl.unquote(kl.kid(net, "name")[1]).lstrip("/")
        if name.startswith("unconnected-"):
            continue
        nets[name] = [(kl.unquote(kl.kid(n, "ref")[1]),
                       kl.unquote(kl.kid(n, "pin")[1]))
                      for n in kl.kids(net, "node")
                      if not kl.unquote(kl.kid(n, "ref")[1]).startswith("#")]
    return nets


def build():
    board = pcbnew.BOARD()
    board.SetFileName(BOARD)

    # --- nets, taken from the schematic -----------------------------------
    netitems = {}
    for name in schematic_nets():
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        netitems[name] = item

    # --- footprints --------------------------------------------------------
    by_ref, fps = {}, {}
    for part in gen_sch.PARTS:
        if not part["fp"]:
            continue
        lib, name = part["fp"].split(":")
        src = os.path.join("/usr/share/kicad/footprints", lib + ".pretty")
        fp = pcbnew.FootprintLoad(src, name)
        if fp is None:
            raise SystemExit(f"cannot load footprint {part['fp']}")
        fp.SetReference(part["ref"])
        fp.SetValue(part["val"])
        fps[part["ref"]] = fp
    placed = place_all(fps)
    for ref, fp in fps.items():
        try:
            fp.AutoPlaceFields()          # keeps reference text off the
        except AttributeError:            # neighbouring part's silk
            pass
        board.Add(fp)
        by_ref[ref] = fp
    if "--dump" in sys.argv or "-v" in sys.argv:
        for ref, (x, y, rot) in sorted(placed.items()):
            print(f"  {ref:<5} at ({x:>6}, {y:>6}) rot {rot}")

    # --- assign pads to their nets -----------------------------------------
    for net, members in schematic_nets().items():
        for ref, pad in members:
            fp = by_ref.get(ref)
            if fp is None:
                continue
            for p in fp.Pads():
                if p.GetNumber() == pad:
                    p.SetNet(netitems[net])

    # --- board outline -----------------------------------------------------
    for (x0, y0), (x1, y1) in zip(EDGE, EDGE[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
        seg.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(MM(0.15))
        board.Add(seg)

    if "--no-route" not in sys.argv:
        import route as router
        router.route(board, netitems, schematic_nets())
    write_rules()
    pcbnew.SaveBoard(BOARD, board)
    return board


M = ("L_IN|L_FUSED|N_AC|LOAD_L|MOC_MT2|TRIAC_G")
RULES = f'''(version 1)
(rule "mains isolation barrier (mains vs logic, 3 mm)"
\t(constraint clearance (min 3mm))
\t(condition "(A.NetName =~ '^/?({M})$' && !(B.NetName =~ '^/?({M})$')) || (B.NetName =~ '^/?({M})$' && !(A.NetName =~ '^/?({M})$'))"))
(rule "mains track width"
\t(constraint track_width (min {router.WIDTH_MAINS:g}mm))
\t(condition "A.NetName =~ '^/?({M})$'"))
'''


def write_rules():
    """Custom DRC rules: the isolation barrier as machine-checked geometry."""
    path = os.path.join(ROOT, PROJECT + ".kicad_dru")
    open(path, "w").write(RULES)
    print(f"wrote {os.path.basename(path)} (3 mm mains clearance rule)")


def dump():
    board = pcbnew.LoadBoard(BOARD)
    print(f"{'net':<10} {'ref.pad':<10} x      y")
    for net in sorted(schematic_nets()):
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname().lstrip("/") == net:
                    p = pad.GetPosition()
                    print(f"{net:<10} {fp.GetReference() + '.' + pad.GetNumber():<10} "
                          f"{mm(pcbnew.ToMM(p.x)):<6} {mm(pcbnew.ToMM(p.y))}")


if __name__ == "__main__":
    if "--dump" in sys.argv:
        dump()
    else:
        build()
        print(f"wrote {BOARD}")
        fp_count = len(list(pcbnew.LoadBoard(BOARD).GetFootprints()))
        print(f"  {fp_count} footprints, {len(schematic_nets())} nets, "
              f"board outline {BOARD_W:g} x {BOARD_H:g} mm")
