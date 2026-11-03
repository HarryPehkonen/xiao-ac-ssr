#!/bin/sh
# Gate for this repo.  Six checks, all machine-verifiable:
#   1. the committed schematic is exactly what the generator produces
#   2. the netlist exported from it equals the intended netlist
#   3. ERC reports no violations
#   4. the board passes DRC with no violations, and honours the rules DRC has
#      no rule for (every footprint id names its library, the mounting holes
#      are where the design says with an empty copper keepout)
#   5. the committed board is the one the generator produces (placement + copper)
#   6. the rules in 4 have been seen to fail -- each is broken in
#      tools/tests/test_board_gate.py and check_board.py must report it
# Run from anywhere:  ./tools/ci.sh
set -eu
cd "$(dirname "$0")/.."

echo "== committed schematic matches the generator"
before=$(sha256sum xiao-ac-ssr.kicad_sch | cut -d' ' -f1)
python3 tools/gen_sch.py > /dev/null
after=$(sha256sum xiao-ac-ssr.kicad_sch | cut -d' ' -f1)
if [ "$before" != "$after" ]; then
    echo "FAIL: xiao-ac-ssr.kicad_sch was stale -- regenerated, review and commit"
    exit 1
fi

echo "== netlist matches intent"
python3 tools/check_netlist.py

echo "== ERC"
kicad-cli sch erc --severity-all --exit-code-violations \
    -o /dev/null xiao-ac-ssr.kicad_sch

echo "== board DRC"
/usr/bin/python3 tools/check_board.py

echo "== committed board matches the generator"
# Quiet when it passes (pcbnew prints image-handler noise on stdout), loud when
# it fails -- which is the only time a person needs to read it.
/usr/bin/python3 tools/check_regen.py > /dev/null 2>&1 || {
    /usr/bin/python3 tools/check_regen.py
    exit 1
}

echo "== the board gate's own tests (each gate rule, seen to fail)"
/usr/bin/python3 -m pytest tools/tests -q > /dev/null 2>&1 || {
    /usr/bin/python3 -m pytest tools/tests -q
    exit 1
}

echo "OK"
