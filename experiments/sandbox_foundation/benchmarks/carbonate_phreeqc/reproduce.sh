#!/usr/bin/env bash
# Reproduce the carbonate/CO2 vs PHREEQC benchmark.  PHREEQC runs in an ISOLATED venv; the SmartChem venv stays free
# of phreeqpython.  The committed reference is comparison_table.json (strict JSON).  Deterministic.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../.." && pwd)"   # .../ (repo root containing experiments/)

# 1) isolated venv with phreeqpython (NOT the SmartChem .venv)
PHVENV="${PHVENV:-/tmp/carbonate_phreeqc_venv}"
python3 -m venv "$PHVENV"
"$PHVENV/bin/pip" install --quiet phreeqpython
"$PHVENV/bin/pip" freeze | grep -i phreeqpython   # record the version

# 2) PHREEQC side -> phreeqc_results.json (not committed)
"$PHVENV/bin/python" "$HERE/run_phreeqc.py"

# 3) code side -> code_results.json  (uses the repo module; numpy/scipy only)
PYTHONPATH="$REPO_ROOT" python3 "$HERE/run_code.py"

# 4) compare -> comparison_table.json (the committed reference)
python3 "$HERE/compare.py"
