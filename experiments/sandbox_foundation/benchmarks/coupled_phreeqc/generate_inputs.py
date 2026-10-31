"""Emit the MIXED vinegar/bicarbonate PHREEQC input decks (one per case x database) under inputs/.

Deterministic; run from the sandbox venv (needs nothing but the stdlib + local cases.py):
    python generate_inputs.py
These `.pqi` decks are the committed, reproducible PROBE: PHREEQC is absent on the baseline, so no reference pH is
produced here, but the exact inputs an external PHREEQC run would consume are pinned.  The decks carry totals as
mol/kgw with `pH <guess> charge` (electroneutrality closure, matching the code's charge balance); the molar-matching
fixed point (acetate benchmark A1/A2) is the runner's job when PHREEQC is actually available.
"""
from __future__ import annotations

import os

from cases import CASES, DATABASES, T_K

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(HERE, "inputs")

_SELECTED = """SELECTED_OUTPUT
  -file {stem}.sel
  -reset false
  -ph true
  -ionic_strength true
  -totals C(4)
  -molalities H+ OH- Na+ Acetate- CO2 HCO3- CO3-2
  -activities H+ OH- Na+ Acetate-
END
"""


def deck(case_id: str, desc: str, c_ac: float, c_c: float, na: float, database: str) -> str:
    stem = f"{database.replace('.dat', '')}_{case_id}"
    lines = [f"DATABASE {database}",
             f"# mixed case {case_id} {desc}: C_Ac={c_ac} C_C={c_c} Na={na} mol/L "
             f"(mol/kgw here; molar-match per PREREGISTRATION A1/A2 when run)",
             "SOLUTION 1",
             "  units mol/kgw",
             f"  temp {int(T_K - 273.15)}",
             "  pH 7 charge"]
    if na > 0:
        lines.append(f"  Na {na}")
    if c_ac > 0:
        lines.append(f"  Acetate {c_ac}")
    if c_c > 0:
        lines.append(f"  C(4) {c_c}")
    return "\n".join(lines) + "\n" + _SELECTED.format(stem=stem)


def main() -> None:
    os.makedirs(INPUTS, exist_ok=True)
    n = 0
    for database in DATABASES:
        for case_id, desc, c_ac, c_c, na, _exp in CASES:
            stem = f"{database.replace('.dat', '')}_{case_id}"
            with open(os.path.join(INPUTS, f"{stem}.pqi"), "w") as f:
                f.write(deck(case_id, desc, c_ac, c_c, na, database))
            n += 1
    print(f"wrote {n} decks under {INPUTS}")


if __name__ == "__main__":
    main()
