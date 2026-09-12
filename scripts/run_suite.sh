#!/usr/bin/env bash
# OOM-safe full-suite runner for SmartChem.
#
# WHY THIS EXISTS: the box OOM-kills a monolithic `pytest` run — and even large
# alphabetical letter-batches — because one long-lived pytest process accumulates
# memory across 200+ test files until the kernel reaps it (and, when it reaps the
# process group, the parent shell with it). The fix, re-derived painfully every
# session before this script existed: run the suite in small, SHORT-LIVED batches,
# each a FRESH pytest process that releases all its memory on exit, with the known
# memory-heavy files isolated to run ALONE.
#
# HARD RULES encoded here (learned the expensive way):
#   * Foreground + strictly sequential. One pytest process at a time.
#   * NEVER `pkill`/`kill -9` a pytest run — it self-kills this runner's own
#     process group (the exit-144 trap). If a batch hangs, Ctrl-C it; the sweep
#     resumes are per-batch, so just re-run with the remaining files.
#   * RDKit is a DEV-VENV-ONLY oracle. The committed baseline runs WITHOUT it
#     (rdkit tests `importorskip`-skip). Do not install it to make this pass.
#
# USAGE:
#   scripts/run_suite.sh                       # whole suite, OOM-safe
#   scripts/run_suite.sh tests/test_routes.py  # only the named files
#   CHUNK_SIZE=6 scripts/run_suite.sh          # smaller batches (tighter memory)
#   PY=/path/to/python scripts/run_suite.sh    # override the interpreter
#
# EXIT CODE: 0 iff every batch collected and passed (no failures, no errors).
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || { echo "cannot cd to repo root $ROOT" >&2; exit 2; }

PY="${PY:-.venv/bin/python}"
CHUNK_SIZE="${CHUNK_SIZE:-10}"
# -q quiet, no cache (the cache plugin is a small but needless allocation here).
PYTEST_ARGS="${PYTEST_ARGS:--q -p no:cacheprovider}"

if [ ! -x "$PY" ]; then
  echo "interpreter not found/executable: $PY  (set PY=... to override)" >&2
  exit 2
fi

# Memory-heavy files, PROVEN to OOM the box when batched with others — run ALONE,
# each in its own process. Keep this list in sync with the memory index's
# "Standing build constraints" note.
HEAVY=(
  tests/test_structure_descent.py
  tests/test_synthesize_provider.py
  tests/test_routes.py
  tests/test_resonance_identity.py
  tests/test_resonance_actual_work.py
  tests/test_resonance_cost.py
)

is_heavy() {
  local f="$1" h
  for h in "${HEAVY[@]}"; do [ "$f" = "$h" ] && return 0; done
  return 1
}

# Build the file list: explicit args, else every test file, sorted for determinism.
declare -a ALL=()
if [ "$#" -gt 0 ]; then
  ALL=("$@")
else
  while IFS= read -r f; do ALL+=("$f"); done < <(ls tests/test_*.py 2>/dev/null | sort)
fi
if [ "${#ALL[@]}" -eq 0 ]; then
  echo "no test files found" >&2
  exit 2
fi

# Partition into heavy (run alone) and light (run in chunks); preserve order.
declare -a LIGHT=() HEAVY_PRESENT=()
for f in "${ALL[@]}"; do
  if is_heavy "$f"; then HEAVY_PRESENT+=("$f"); else LIGHT+=("$f"); fi
done

LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/smartchem_suite.XXXXXX")"
echo "OOM-safe suite runner"
echo "  interpreter : $PY"
echo "  files       : ${#ALL[@]} (${#HEAVY_PRESENT[@]} heavy solo, ${#LIGHT[@]} chunked @ $CHUNK_SIZE)"
echo "  logs + xml  : $LOGDIR"
echo

batch=0
fail_batches=0

run_batch() {
  # $1 = human label, rest = files
  local label="$1"; shift
  batch=$((batch + 1))
  local xml="$LOGDIR/batch_$(printf '%03d' "$batch").xml"
  local log="$LOGDIR/batch_$(printf '%03d' "$batch").log"
  printf '[batch %3d] %-40s ' "$batch" "$label"
  # Fresh, short-lived process. Memory is fully released when it exits.
  "$PY" -m pytest $PYTEST_ARGS --junit-xml="$xml" "$@" >"$log" 2>&1
  local rc=$?
  # rc 0 = passed, 5 = no tests collected (treat as ok/empty), else failure.
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 5 ]; then
    # Echo pytest's own summary tail for the batch.
    local tail_line
    tail_line="$(grep -oE '[0-9]+ (passed|failed|error|skipped|xfailed|xpassed)[^$]*' "$log" | tail -1)"
    echo "ok    ${tail_line:-(no tests)}"
  else
    echo "FAIL  (rc=$rc) -> $log"
    fail_batches=$((fail_batches + 1))
  fi
}

# Heavy files first, each alone.
for f in "${HEAVY_PRESENT[@]}"; do
  run_batch "$(basename "$f") [heavy/solo]" "$f"
done

# Light files in chunks of CHUNK_SIZE.
i=0
n=${#LIGHT[@]}
while [ "$i" -lt "$n" ]; do
  chunk=("${LIGHT[@]:i:CHUNK_SIZE}")
  run_batch "${chunk[0]##*/} +$(( ${#chunk[@]} - 1 )) more" "${chunk[@]}"
  i=$((i + CHUNK_SIZE))
done

echo
echo "=== aggregate (from junit xml) ==="
"$PY" - "$LOGDIR" <<'PY'
import sys, glob, os
import xml.etree.ElementTree as ET
tot = dict(tests=0, failures=0, errors=0, skipped=0)
bad_files = []
for x in sorted(glob.glob(os.path.join(sys.argv[1], "batch_*.xml"))):
    try:
        root = ET.parse(x).getroot()
    except ET.ParseError:
        bad_files.append(os.path.basename(x))
        continue
    # junit root may be <testsuites> wrapping <testsuite>, or a bare <testsuite>.
    suites = root.iter("testsuite")
    for s in suites:
        for k in tot:
            tot[k] += int(s.get(k, 0) or 0)
passed = tot["tests"] - tot["failures"] - tot["errors"] - tot["skipped"]
print(f"  collected : {tot['tests']}")
print(f"  passed    : {passed}")
print(f"  failed    : {tot['failures']}")
print(f"  errors    : {tot['errors']}")
print(f"  skipped   : {tot['skipped']}")
if bad_files:
    print(f"  UNPARSEABLE xml (batch crashed/OOM before writing?): {bad_files}")
sys.exit(1 if (tot["failures"] or tot["errors"] or bad_files) else 0)
PY
agg_rc=$?

echo
if [ "$fail_batches" -eq 0 ] && [ "$agg_rc" -eq 0 ]; then
  echo "SUITE GREEN. logs in $LOGDIR"
  exit 0
else
  echo "SUITE NOT GREEN ($fail_batches batch(es) failed). Inspect logs in $LOGDIR"
  exit 1
fi
