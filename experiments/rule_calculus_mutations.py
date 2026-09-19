"""Run a clean baseline and targeted mutants in isolated temporary workspaces.

No original source file is modified. A mutant counts as killed ONLY if pytest
reports ordinary test failures (a syntax/import crash is not a valid kill).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = (
    ("lost_context", "rule_calculus.py", "remaining | new)", "new)"),
    ("verifier_trusts_target", "rule_calculus.py",
     "return table == {e.pair: e.order for e in h.edges}", "return True"),
    ("budget_laundering", "rule_calculus.py",
     "return MatchReceipt(tuple(out), work, budget, False)",
     "return MatchReceipt(tuple(out), work, budget, True)"),
    ("false_independence", "rule_calculus.py",
     "return not (aw & br or bw & ar)", "return True"),
    ("unknown_is_free", "rule_semantics.py", "return None if missing else total", "return total"),
    ("lost_symbolic_cancellation", "rule_semantics.py",
     "for k, c in acc.items() if c", "for k, c in acc.items()"),
)


def trial(name, filename=None, old=None, new=None):
    with tempfile.TemporaryDirectory(prefix="smartchem-rule-mutation-") as directory:
        root = Path(directory)
        (root / "smartchem").mkdir()
        (root / "tests").mkdir()
        for module in ("rule_calculus.py", "rule_semantics.py"):
            shutil.copy2(ROOT / "smartchem" / module, root / "smartchem" / module)
        for test in ("test_rule_calculus.py", "test_rule_semantics.py"):
            shutil.copy2(ROOT / "tests" / test, root / "tests" / test)
        if filename:
            path = root / "smartchem" / filename
            content = path.read_text()
            if content.count(old) != 1:
                raise RuntimeError(f"{name}: mutation anchor changed; recalibrate, do not claim a kill")
            path.write_text(content.replace(old, new))
        environment = dict(os.environ, PYTHONPATH=str(root), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=root,
                             env=environment, capture_output=True, text=True, timeout=90)
        ordinary_failure = run.returncode == 1 and " failed" in run.stdout and "ERROR collecting" not in run.stdout
        return {"name": name, "returncode": run.returncode,
                "ordinary_test_failure": ordinary_failure,
                "stdout": run.stdout, "stderr": run.stderr}


def run():
    baseline = trial("baseline")
    if baseline["returncode"] != 0:
        raise RuntimeError("baseline is not green: mutation calibration invalid")
    trials = [trial(*mutation) for mutation in MUTANTS]
    return {"schema": "smartchem.rule-mutations/v1", "baseline": baseline,
            "mutants": trials, "all_killed": all(t["ordinary_test_failure"] for t in trials),
            "scope": "same-author executable mutation controls, not independent agents or chemistry evidence"}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_killed"] else 1)
