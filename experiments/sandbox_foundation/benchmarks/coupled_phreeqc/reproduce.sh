#!/usr/bin/env bash
# Regenerate the committed code-side artifacts for the mixed vinegar/bicarbonate benchmark.
# PHREEQC is NOT required (and is absent on the baseline); this only runs the code side + deck generator.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"   # repo root (contains experiments/)
cd "$HERE"
PYTHONPATH="$ROOT" python generate_inputs.py
PYTHONPATH="$ROOT" python run_code.py
echo "done. PHREEQC column stays EXTERNAL_VALIDATION_UNAVAILABLE until run_phreeqc.py is run in a phreeqpython venv."
