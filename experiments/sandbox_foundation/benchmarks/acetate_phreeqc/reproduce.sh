#!/usr/bin/env bash
# Reproduce Wave D (read-only wrt the repo).  Run from this directory.
set -euo pipefail
python3 -m venv venv && venv/bin/pip install phreeqpython==1.6.2        # isolated; NEVER the SmartChem .venv
mkdir -p db_dl && for f in minteq.v4.dat llnl.dat; do curl -sS -o db_dl/$f https://raw.githubusercontent.com/usgs-coupled/phreeqc3/master/database/$f; done
sha256sum db_dl/*.dat   # expect minteq 4a48bf5c...ca3 ; llnl 1324b807...819b  (master as of 2026-10-22)
# db_variants/*.noNaAcPair.dat are scratch copies with the Na-acetate ion-pair reactions' logK (and -analytic for llnl) set to -40/-80 (see PREREGISTRATION amendments)
venv/bin/python -I run_phreeqc.py grid.json phreeqc_results.json
venv/bin/python -I run_phreeqc.py grid_scan.json phreeqc_scan.json
(cd /home/leah/SmartChem && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -I "$OLDPWD/run_code.py" "$OLDPWD/grid.json" "$OLDPWD/code_results.json")
venv/bin/python -I compare.py ; venv/bin/python -I diagnostics.py
