#!/usr/bin/env python3
"""The gate's teeth: nine ways to break this board's rules, each of which
`check_board.geometry()` must report.

`check_board.py` gates two things DRC has no rule for -- every footprint id
names its library, and the four M3 mounting holes are where and what the design
says with an empty copper keepout.  A gate that has never been seen to fail is
not a gate, so every rule below is broken on a copy of the **committed** board
and the failure is asserted by what it says, not by the exit code alone.

The board is loaded from disk and mutated in memory: nothing is written, and no
board is regenerated.  The honest board must report nothing, so a test cannot
pass just because the gate complains about everything.
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
    return check_board.geometry(board)


def _mount(board, ref):
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    raise AssertionError(f"the committed board has no {ref}")


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
