#!/usr/bin/env bash
# Reproduce the MIXED vinegar/bicarbonate benchmark.  Run from this directory.
#
# Two tiers, mirroring ../acetate_phreeqc and ../carbonate_phreeqc:
#   CODE SIDE (no PHREEQC needed): regenerate the decks + the code column.
#   PHREEQC SIDE (needs phreeqpython + network): fetch the pinned DBs, run them, merge the pH.
# PHREEQC is ABSENT on the committed baseline on purpose, so the DBs are fetched into the
# gitignored db_dl/ and the phreeqc column is signed only by a real run -- never fabricated.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"   # repo root (contains experiments/)
cd "$HERE"

# --- CODE SIDE -------------------------------------------------------------------------------
PYTHONPATH="$ROOT" python generate_inputs.py
PYTHONPATH="$ROOT" python run_code.py          # -> code_results.json + comparison_table.json (phreeqc col null)

# --- PHREEQC SIDE ----------------------------------------------------------------------------
# Fetch the pinned USGS phreeqc3 databases (master as of 2026-10-22).  VERIFY the sha256 before use.
mkdir -p db_dl
for f in minteq.v4.dat llnl.dat; do
  curl -sS -o "db_dl/$f" "https://raw.githubusercontent.com/usgs-coupled/phreeqc3/master/database/$f"
done
echo "4a48bf5c357b3da3084606a5e322426c3ab1e969dd1c86f9c62a3a7995836ca3  db_dl/minteq.v4.dat" | sha256sum -c -
echo "1324b807f0f864806fc42df308f6ca7c5e8ce2ed8060d76351452f76beeb819b  db_dl/llnl.dat"      | sha256sum -c -

# Run PHREEQC in a venv that HAS phreeqpython (never the committed baseline, which stays free of it).
python -I run_phreeqc.py                       # -> phreeqc_results.json (gitignored)
python -I compare.py                           # -> comparison_table.json (phreeqc pH + abs_dpH merged)
echo "done.  comparison_table.json now BENCHMARKED_AGAINST_REFERENCE_SOLVER (solver corroboration, common-mode)."
