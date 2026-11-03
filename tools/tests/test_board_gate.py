#!/usr/bin/env python3
"""The gate's teeth: twenty-five ways to break this board's rules, each of which
`check_board.py` must report.

`check_board.py` gates what DRC has no rule for -- every footprint id names its
library, the four M3 mounting holes are where and what the design says with an
empty copper keepout, and the XIAO socket pair is a mating interface a module
actually fits.  A gate that has never been seen to fail is not a gate, so every
rule below is broken on a copy of the **committed** board and the failure is
asserted by what it says, not by the exit code alone.

The board is loaded from disk and mutated in memory: nothing is written, and no
board is regenerated.  The honest board must report nothing, so a test cannot
pass just because the gate complains about everything.

Mutating rather than deleting is deliberate.  In this KiCad binding,
`FOOTPRINT.Remove(pad)` and `BOARD.Remove(<drawing or group>)` free the object
out from under the swig wrapper: the test appears to pass and a *later* test
dies with a segmentation fault, which reads as a gate bug rather than a test
bug.  Every socket case below renames, moves, renumbers or adds instead.
"""
import os
import sys

import pcbnew
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import check_board
import gen_pcb
import gen_sch
import route


@pytest.fixture
def board():
    """A fresh copy of the committed board, per test."""
    b = pcbnew.LoadBoard(gen_pcb.BOARD)
    assert b is not None, f"cannot load {gen_pcb.BOARD}"
    return b


def _failures(board):
    """Every rule check_board.py asserts on a loaded board."""
    return check_board.geometry(board) + check_board.xiao_socket(board)


def _fp(board, ref):
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    raise AssertionError(f"the committed board has no {ref}")


def _pad(fp, number):
    for p in fp.Pads():
        if p.GetNumber() == number:
            return p
    raise AssertionError(f"{fp.GetReference()} has no pad {number}")


def _mount(board, ref):
    return _fp(board, ref)


def _says(failures, ref, text):
    hits = [f for f in failures if f.startswith(ref + ":") and text in f]
    assert hits, f"nothing said '{ref}: ... {text}':\n  " + "\n  ".join(failures)
    return hits[0]


def _mentions(failures, text):
    hits = [f for f in failures if text in f]
    assert hits, f"nothing said '{text}':\n  " + "\n  ".join(failures)
    return hits[0]


# ----------------------------------------------------------- the honest board
def test_honest_board_reports_no_geometry_problem(board):
    """The other half of every sabotage test: the gate must be quiet here."""
    assert _failures(board) == []


def test_the_board_carries_one_nicknamed_footprint_per_part(board):
    """The defect this board inherited: no `Lib:` prefix on any footprint id."""
    fps = list(board.GetFootprints())
    assert len(fps) == len(gen_pcb.MOUNTING) + len(
        [p for p in gen_sch.PARTS if p["fp"]])
    for fp in fps:
        assert str(fp.GetFPID().GetLibNickname()), \
            f"{fp.GetReference()} has no library nickname"


# ----------------------------------------------------------------- sabotage --
def test_a_footprint_with_no_library_nickname_fails(board):
    # the pre-fix state of every footprint on this board: loaded by bare name
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("X1")
    board.Add(fp)
    _says(_failures(board), "X1", "no library nickname")


def test_a_moved_mounting_hole_fails(board):
    fp = _mount(board, "H1")
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(6.5), pcbnew.FromMM(6.5)))
    failures = _failures(board)
    _says(failures, "H1", "table says")
    # and the edge inset is measured on the board, not read off the table
    _says(failures, "H1", "spec is 5 mm inset")


def test_a_renamed_mounting_hole_fails(board):
    _mount(board, "H1").SetReference("H9")
    _says(_failures(board), "H1", "no footprint with the reference")


def test_a_missing_mounting_hole_fails(board):
    board.Remove(_mount(board, "H4"))
    _mentions(_failures(board), "3 mounting hole footprint(s) on the board")


def test_a_track_inside_the_keepout_fails(board):
    fp = _mount(board, "H2")
    p = fp.GetPosition()
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(p.x - pcbnew.FromMM(1.5), p.y))
    t.SetEnd(pcbnew.VECTOR2I(p.x + pcbnew.FromMM(1.5), p.y))
    t.SetWidth(pcbnew.FromMM(0.4))
    t.SetLayer(pcbnew.F_Cu)
    board.Add(t)
    _says(_failures(board), "H2", "copper comes within")


def test_a_pad_inside_the_keepout_fails(board):
    src = "/usr/share/kicad/footprints/Resistor_SMD.pretty"
    fp = pcbnew.FootprintLoad(src, "R_0805_2012Metric")
    assert fp is not None
    p = _mount(board, "H3").GetPosition()
    fp.SetPosition(p)                       # an 0805 across the hole
    board.Add(fp)
    _says(_failures(board), "H3", "copper comes within")


def test_a_mounting_hole_tied_to_a_net_fails(board):
    fp = _mount(board, "H1")
    net = pcbnew.NETINFO_ITEM(board, "GND")
    board.Add(net)
    next(iter(fp.Pads())).SetNet(net)
    _says(_failures(board), "H1", "must be isolated")


def test_a_plated_mounting_hole_fails(board):
    fp = _mount(board, "H2")
    next(iter(fp.Pads())).SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    _says(_failures(board), "H2", "not non-plated")


def test_a_shrunk_mounting_hole_fails(board):
    fp = _mount(board, "H4")
    pad = next(iter(fp.Pads()))
    pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(2.2), pcbnew.FromMM(2.2)))
    _says(_failures(board), "H4", "mm drill, spec is 3.2 mm")


# ------------------------------------------------------------ the socket pair --
# The rules that made this board's inherited defect visible.  J1/J2 used to be
# two free 1x7 headers 6.1 mm apart; the module needs 15.24 mm.  Every case here
# breaks one thing check_board.xiao_socket() measures.
def test_the_socket_pair_is_one_locked_group(board):
    """The honest shape of the fix: one group, both rows locked, 15.24 apart."""
    spec = gen_pcb.XIAO
    groups = [g for g in board.Groups() if g.GetName() == gen_pcb.XIAO_GROUP]
    assert len(groups) == 1, [g.GetName() for g in board.Groups()]
    members = sorted(i.GetReference() for i in groups[0].GetItems()
                     if isinstance(i, pcbnew.FOOTPRINT))
    assert members == sorted(spec["rows"])
    for ref in spec["rows"]:
        fp = _fp(board, ref)
        assert fp.IsLocked(), f"{ref} must be locked"
        cols = {round(pcbnew.ToMM(p.GetPosition().x), 4) for p in fp.Pads()}
        assert len(cols) == 1, f"{ref} is not a straight column: {cols}"
    xs = sorted(round(pcbnew.ToMM(_pad(_fp(board, r), "1").GetPosition().x), 4)
                for r in spec["rows"])
    assert xs[1] - xs[0] == pytest.approx(spec["row_sep"], abs=0.01)


def test_the_rows_too_close_fail(board):
    """The defect this board shipped with, put back."""
    fp = _fp(board, "J2")
    p = fp.GetPosition()
    fp.SetPosition(pcbnew.VECTOR2I(p.x - pcbnew.FromMM(9.14), p.y))
    _mentions(_failures(board), "a XIAO needs 15.24 mm")


def test_a_pin_that_is_not_in_the_row_fails(board):
    """A row with a hole that is not one of the module's 7 pins.

    Not simulated by deleting a pad: `FOOTPRINT.Remove(pad)` frees the pad out
    from under the swig wrapper and the interpreter dies later, in a different
    test, looking like a gate bug.  Renumbering is the same defect to the gate
    and leaves the binding alive.
    """
    _pad(_fp(board, "J1"), "4").SetNumber("8")
    _says(_failures(board), "J1", "a XIAO row is 1..7")


def test_an_extra_pin_fails(board):
    fp = _fp(board, "J1")
    src = _pad(fp, "1")
    p = pcbnew.PAD(fp)
    p.SetNumber("8")
    p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.7), pcbnew.FromMM(1.7)))
    p.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
    q = src.GetPosition()
    p.SetPosition(pcbnew.VECTOR2I(q.x, q.y + pcbnew.FromMM(7 * 2.54)))
    fp.Add(p)
    _mentions(_failures(board), "a XIAO row is 7 (7 + 7 = the module's 14)")


def test_a_reversed_row_fails(board):
    """A row in the other way round fires the wrong pin and nothing else sees it."""
    fp = _fp(board, "J1")
    fp.SetOrientationDegrees(180)       # the footprint's origin is its pad 1
    _says(_failures(board), "J1", "the row is in the other way round")


def test_a_row_in_the_other_way_round_by_number_fails(board):
    """The same defect without moving anything: pad 1 and pad 7 swapped."""
    fp = _fp(board, "J1")
    for a, b in (("1", "7"), ("2", "6"), ("3", "5")):
        pa, pb = _pad(fp, a), _pad(fp, b)
        na, nb = pa.GetNumber(), pb.GetNumber()
        pa.SetNumber(nb)
        pb.SetNumber(na)
    failures = _failures(board)
    _says(failures, "J1", "the row is in the other way round")
    _mentions(failures, "one row is reversed relative to the other")


def test_a_part_inside_the_module_envelope_fails(board):
    src = "/usr/share/kicad/footprints/Resistor_SMD.pretty"
    fp = pcbnew.FootprintLoad(src, "R_0805_2012Metric")
    assert fp is not None
    x0, y0, x1, y1 = gen_pcb.xiao_envelope()
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM((x0 + x1) / 2),
                                   pcbnew.FromMM((y0 + y1) / 2)))
    board.Add(fp)
    _mentions(_failures(board), "reaches to")


def test_a_wrong_pitch_fails(board):
    p = _pad(_fp(board, "J1"), "5")
    q = p.GetPosition()
    p.SetPosition(pcbnew.VECTOR2I(q.x, q.y + pcbnew.FromMM(0.7)))
    _mentions(_failures(board), "the module's pitch is 2.54 mm")


def test_a_row_out_of_the_group_fails(board):
    group = next(g for g in board.Groups() if g.GetName() == gen_pcb.XIAO_GROUP)
    group.RemoveItem(_fp(board, "J2"))
    _mentions(_failures(board), "the socket rows are ['J1', 'J2']")


def test_a_missing_group_fails(board):
    """Renamed rather than deleted: removing a board-owned group is unsafe.

    To the gate a group under another name is a socket pair that is no longer
    one object, which is the defect.
    """
    group = next(g for g in board.Groups() if g.GetName() == gen_pcb.XIAO_GROUP)
    group.SetName("J1_J2_loose")
    _mentions(_failures(board), "0 group(s) with that name")


def test_an_unlocked_row_fails(board):
    _fp(board, "J2").SetLocked(False)
    _says(_failures(board), "J2", "not locked")


def test_swapped_rows_fail(board):
    """Reproducible: the module's left column must be the left row."""
    a, z = _fp(board, "J1"), _fp(board, "J2")
    pa, pz = a.GetPosition(), z.GetPosition()
    a.SetPosition(pcbnew.VECTOR2I(pz.x, pa.y))
    z.SetPosition(pcbnew.VECTOR2I(pa.x, pz.y))
    _says(_failures(board), "J1", "right of J2")


def test_a_missing_envelope_fails(board):
    """The keepout marker is what a reviewer looks for; parked off-layer = gone."""
    rect = next(d for d in board.GetDrawings()
                if d.GetLayer() == pcbnew.F_CrtYd)
    rect.SetLayer(pcbnew.F_Fab)         # not deleted: removing a board-owned
    _mentions(_failures(board), "0 rectangle(s) on F.CrtYd")   # item is unsafe


def test_a_moved_envelope_fails(board):
    rect = next(d for d in board.GetDrawings()
                if d.GetLayer() == pcbnew.F_CrtYd)
    rect.Move(pcbnew.VECTOR2I(pcbnew.FromMM(2), pcbnew.FromMM(2)))
    _mentions(_failures(board), "the F.CrtYd rectangle is")


def test_a_socket_hole_that_is_too_small_fails(board):
    p = _pad(_fp(board, "J2"), "3")
    p.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.6), pcbnew.FromMM(0.6)))
    _mentions(_failures(board), "mm hole, spec is 1 mm")


def test_an_smd_socket_pad_fails(board):
    _pad(_fp(board, "J1"), "6").SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    _mentions(_failures(board), "the module's pins need a hole to go in")


def test_a_socket_pad_on_the_wrong_net_fails(board):
    """The pins the geometry has to agree with: D1 is the trigger, and 5V/GND
    are the first two of the right-hand column -- so swapping them is the
    right column running the other way, which nothing else would catch."""
    a, z = _pad(_fp(board, "J2"), "1"), _pad(_fp(board, "J2"), "2")
    five, gnd = board.GetNetsByName()["+5V_XIAO"], board.GetNetsByName()["GND"]
    a.SetNet(gnd)
    z.SetNet(five)
    failures = _failures(board)
    _says(failures, "J2.1", "the intent for this pin is")
    _says(failures, "J2.2", "the intent for this pin is")


# ------------------------------------------------- the rule the router obeys --
def test_the_keepout_is_inflated_by_the_copper_it_has_to_clear():
    """Blocking cell *centres* at the spec radius is not enough.

    The router blocks cell centres, so a 1.5 mm mains track laid on the last
    free cell still puts its edge 0.75 mm inside the disc -- measured on the
    dimmer, where LOAD_L came within 2.86 mm of H1 before the inflation.  On
    this board the corners happened to be clear, so nothing here would fail if
    the inflation were dropped; that is exactly why the rule is pinned.
    """
    assert route.MOUNT_BLOCK_R == pytest.approx(
        route.MOUNT_KEEPOUT_R + route.WIDTH_MAINS / 2 + route.QUANT)
    assert route.MOUNT_BLOCK_R > route.MOUNT_KEEPOUT_R
