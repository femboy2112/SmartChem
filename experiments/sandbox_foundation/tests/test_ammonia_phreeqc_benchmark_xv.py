"""OPERATION XV Wave D / Wave E -- benchmark the ammonia equilibrium solver against PHREEQC (reference solver).

PHREEQC is a DEV-VENV-ONLY oracle, ABSENT from the committed baseline, so this whole module importorskips phreeqpython
-- CI (which has no PHREEQC) skips it, exactly as the RDKit-dependent tests skip.  This is the preregistered
reference-solver cross-check, now RUNNABLE because phreeqpython was installed this session.

WHAT TIER THIS EARNS, AND ITS CAVEAT.  Agreement with PHREEQC is BENCHMARKED_AGAINST_REFERENCE_SOLVER: solver
corroboration, NOT measured-chemistry validation.  It is COMMON-MODE in two declared ways: (1) constant lineage --
PHREEQC's phreeqc.dat uses pKa(AmmH+) ~ 9.28 and its own Kw, vs this solver's sourced pKa 9.25; (2) activity model --
PHREEQC applies an ion-activity (Davies/Debye-Huckel) correction while this solver is ideal.  So the two will NOT agree
to machine precision even when both are correct; the benchmark is run DILUTE (low ionic strength, where activities ->
1) and the residual is bounded by, and attributed to, those two stated common-mode differences -- never papered over.
"""
from __future__ import annotations

import math

import pytest

pytest.importorskip("phreeqpython")   # dev-venv-only oracle; absent from the committed baseline -> CI skips

from experiments.sandbox_foundation.ammonia_equilibrium import AmmoniaWaterSystem, solve   # noqa: E402


def _phreeqc_ammonia_pH(total_ammonia_mmol: float) -> float:
    import phreeqpython
    pp = phreeqpython.PhreeqPython()
    sol = pp.add_solution({"Amm": total_ammonia_mmol, "pH": "7.0 charge"})   # let PHREEQC charge-balance for pH
    ph = sol.pH
    pp.remove_solutions([sol.number])
    return ph


@pytest.mark.parametrize("mmol", [1.0, 5.0, 10.0])
def test_ammonia_pH_corroborated_by_phreeqc_dilute(mmol):
    mine = solve(AmmoniaWaterSystem(mmol / 1000.0)).pH          # mol/L; dilute so ideal ~ Davies
    theirs = _phreeqc_ammonia_pH(mmol)
    # both must agree it is a basic ammonia solution, and within the stated common-mode budget (constants + activity)
    assert mine > 7.5 and theirs > 7.5
    assert abs(mine - theirs) < 0.05, f"mine={mine:.4f} phreeqc={theirs:.4f} delta={mine - theirs:+.4f}"


def test_phreeqc_speciation_shape_matches():
    # at a charge-balanced 10 mmol ammonia point, [NH3] >> [NH4+] (basic side of pKa) in BOTH solvers
    import phreeqpython
    pp = phreeqpython.PhreeqPython()
    sol = pp.add_solution({"Amm": 10.0, "pH": "7.0 charge"})
    nh3_p, nh4_p = sol.species.get("Amm", 0.0), sol.species.get("AmmH+", 0.0)
    pp.remove_solutions([sol.number])
    r = solve(AmmoniaWaterSystem(0.01))
    assert nh3_p > nh4_p and r.nh3_M > r.nh4_M                  # same qualitative speciation
    # the NH3/NH4+ ratio agrees within the constant-lineage + activity budget (~15%)
    assert math.isclose(r.nh3_M / r.nh4_M, nh3_p / nh4_p, rel_tol=0.15)
