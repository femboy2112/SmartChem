"""Run the MIXED vinegar/bicarbonate decks through PHREEQC (the INDEPENDENT instrument) -- WHEN it is available.

Run ONLY in an isolated scratch venv that has `phreeqpython` -- NEVER the SmartChem .venv (the committed baseline
stays free of it, exactly like the acetate/carbonate benchmarks).  PHREEQC is ABSENT on the committed baseline, so
this is the reproducible recipe, not a run that happened here: it is why `comparison_table.json`'s PHREEQC column is
null (EXTERNAL_VALIDATION_UNAVAILABLE).  Writes `phreeqc_results.json` (NOT committed -- the committed reference,
once a run exists, is the pH column merged into comparison_table.json by a future compare.py).

minteq.v4.dat carries BOTH acetate (H(Acetate), NIST46.4 logK 4.757; Na(Acetate) logK -0.18) AND the carbonate
system (CO2/HCO3-/CO3-2) -- the single database that supports the mixed family (llnl.dat is the secondary).  Pin the
database sha256 (printed) into README.md on the first real run.  Deterministic.

Usage (from an isolated venv):  python run_phreeqc.py
"""
from __future__ import annotations

import hashlib
import json
import os

from cases import CASES, DATABASES

HERE = os.path.dirname(os.path.abspath(__file__))

_SELECTED = """
SELECTED_OUTPUT 1
    -reset false
    -pH true
    -ionic_strength true
    -totals C(4)
    -molalities H+ OH- Na+ Acetate- CO2 HCO3- CO3-2
"""


def _solution(c_ac, c_c, na):
    lines = ["SOLUTION 1", "    units mol/kgw", "    temp 25", "    pH 7 charge"]
    if na > 0:
        lines.append(f"    Na {na}")
    if c_ac > 0:
        lines.append(f"    Acetate {c_ac}")
    if c_c > 0:
        lines.append(f"    C(4) {c_c}")
    lines.append("END")
    return "\n".join(lines)


def main() -> None:
    from phreeqpython import PhreeqPython   # noqa: F401 (import here so absence is a clear runtime message)

    results = {"databases": {}}
    for database in DATABASES:
        pp = PhreeqPython(database=database)
        db_path = os.path.join(os.path.dirname(__import__("phreeqpython").__file__), "database", database)
        db_sha = hashlib.sha256(open(db_path, "rb").read()).hexdigest() if os.path.exists(db_path) else "UNKNOWN"
        rows = {}
        for case_id, desc, c_ac, c_c, na, _exp in CASES:
            pp.ip.run_string(_SELECTED + "\n" + _solution(c_ac, c_c, na))
            out = pp.ip.get_selected_output_array()
            r = dict(zip(out[0], out[-1]))
            rows[case_id] = {"desc": desc, "pH": r.get("pH"), "I": r.get("mu")}
        results["databases"][database] = {"database_sha256": db_sha, "rows": rows}
        print(f"{database}: {len(rows)} cases; sha256 {db_sha}")
    with open(os.path.join(HERE, "phreeqc_results.json"), "w") as f:
        json.dump(results, f, indent=2, allow_nan=False)
    print("wrote phreeqc_results.json")


if __name__ == "__main__":
    main()
