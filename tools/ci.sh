#!/bin/sh
# Gate for this repo.  Four checks, all machine-verifiable:
#   1. the committed schematic is exactly what the generator produces
#   2. the netlist exported from it equals the intended netlist
#   3. ERC reports no violations
#   4. the board passes DRC with no violations
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

echo "OK"
