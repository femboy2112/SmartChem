"""OPERATION XIII P0 -- the MIXED vinegar/bicarbonate PHREEQC benchmark grid (single source of truth).

Both the PHREEQC-deck generator (`generate_inputs.py`) and the code-side runner (`run_code.py`) import CASES from
here, so the two sides can never drift.  All closed-liquid (fixed total DISSOLVED carbon) at T = 298.15 K; the
open-CO2 and sealed-headspace mixed decks arrive with P1 (the coupled gas-boundary modes).  Totals are in mol/L
solution (the code's basis); the PHREEQC decks carry them as mol/kgw to be MOLAR-MATCHED when actually run (the
acetate benchmark's A1/A2 amendments: `units mol/l` is not a true molar input, so a fixed point on mol/kgw input
reproduces the requested mol/L -- that step is part of the runner's recorded procedure, deferred with PHREEQC).

The label discipline the directive demanded: M5 (0.2 acetate / 0.05 carbon) is BICARBONATE-LIMITED, not
"acid-limiting" -- there is more weak acid than bicarbonate, bicarbonate is consumed first, and the residual pH is
acidic.  M6 is the mirror (acid-limited).  The prior coupled dossier mislabelled M5; it is corrected here.
"""
from __future__ import annotations

# id, description, C_Ac (total acetate mol/L), C_C (total dissolved carbon mol/L), Na (mol/L), expectation
CASES = [
    ("M1", "pure water (control)",                   0.00, 0.00, 0.00, "pH 7; both limits trivial"),
    ("M2", "vinegar only (acetate limit)",           0.10, 0.00, 0.00, "reduces to the acetate parent"),
    ("M3", "bicarbonate only (carbonate limit)",     0.00, 0.10, 0.10, "reduces to the carbonate closed parent"),
    ("M4", "stoichiometric mixed",                   0.10, 0.10, 0.10, "genuine mixed interior"),
    ("M5", "acid in excess -> BICARBONATE-LIMITED",  0.20, 0.05, 0.05, "bicarbonate consumed first; acidic residual"),
    ("M6", "bicarbonate in excess -> acid-limited",  0.05, 0.20, 0.20, "acid consumed first; buffered/basic residual"),
    ("M7", "dilute mixed",                           0.01, 0.01, 0.01, "low ionic strength interior"),
    ("M8", "intermediate ionic strength",            0.10, 0.10, 0.30, "I ~ 0.3 M interior"),
    ("M9", "high I near the Davies boundary",        0.20, 0.20, 0.40, "I ~ 0.45 M; expected still admitted"),
    ("M10", "extreme basicity numerical control",    0.00, 0.10, 0.30, "excess base over carbon; high pH, tiny [H+]"),
    ("M11", "refusal probe (I > Davies domain)",     0.30, 0.30, 0.60, "I > 0.5 M: code is EXPECTED TO REFUSE"),
]

T_K = 298.15
DATABASES = ("minteq.v4.dat", "llnl.dat")   # both carry acetate AND the carbonate system; minteq.v4 is primary
