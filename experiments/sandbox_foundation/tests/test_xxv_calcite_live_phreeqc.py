"""OPERATION XXV-1 (#165) -- LIVE calcite world vs PHREEQC, both standard-state bases.  MODEL-vs-MODEL.

Both sides read the SAME pinned phreeqc.dat constants, so agreement verifies a common standard-state basis + the
Davies-vs-WATEQ activity model + the kernel integration.  It is NOT a measurement and NOT empirical validation.

Hosted ci.yml has no phreeqpython, so this module skips there; the science workflow (.github/workflows/science.yml)
installs a hash-locked phreeqpython and FAILS on any skip of this file.

Metric (as in OPERATION_XXIV_SOURCE_GROUNDING.md II-B): kernel Ca_total (mol/L) / (PHREEQC Ca_total (mol/kgw) * rho_w*)
- 1, rho_w* = 0.997047 kg/L.  Recorded: molar -0.0071%, legacy molal +0.298%.  Tolerances below are stated, not fitted.
"""
from __future__ import annotations

import pytest

pytest.importorskip("phreeqpython")

from experiments.sandbox_foundation import admissibility as adm  # noqa: E402
from experiments.sandbox_foundation import sim_api_v2alpha as api  # noqa: E402
from experiments.sandbox_foundation import standard_state as ss  # noqa: E402
from experiments.sandbox_foundation.benchmarks.solid_equilibrium_xxiii import (  # noqa: E402
    run_solid_equilibrium_xxiii as h,
)

PHREEQC_CA_MOLAL_FROZEN = 1.2300690436987488e-4      # XXIII-S4 frozen reference (test_xxiii_s4_solid_equilibrium.py)
MOLAR_REL_DOCUMENTED, MOLAR_TOL = -7.1e-5, 1.0e-5     # -0.0071% +/- 0.001 percentage points
LEGACY_REL_DOCUMENTED, LEGACY_TOL = 2.98e-3, 1.0e-4   # +0.298% +/- 0.01 percentage points
INIT = (api.SpeciesInventory("cell", "CaCO3(s)", "solid", 0.01),
        api.SpeciesInventory("cell", "H2O", "pure_liquid", 55.34),
        api.SpeciesInventory("cell", "H+", "aqueous", 1e-7),
        api.SpeciesInventory("cell", "OH-", "aqueous", 1e-7))
CA = ("Ca+2", "CaCO3(aq)", "CaHCO3+", "CaOH+")


@pytest.fixture(scope="module")
def ref():
    return h.phreeqc_reference()


def _kernel_ca(basis):
    sched = api.BoundarySchedule((api.BoundaryPhase("dissolve", 6000.0, 60, "closed", False),))
    res = api.run(api.SimulationSpec(
        model=api.ModelSpec("calcite_closed_dissolution", api.CalciteParams(standard_state_basis=basis)),
        initial=INIT, schedule=sched, solver=api.SolverOptions(rtol=1e-10, atol=1e-18)))
    return sum(res.final_frame.amount("cell", s) for s in CA), res


def test_live_phreeqc_reproduces_the_frozen_reference(ref):
    assert ref["Ca_total_molal"] == pytest.approx(PHREEQC_CA_MOLAL_FROZEN, rel=1e-9)
    assert ref["SI_calcite"] == pytest.approx(0.0, abs=1e-9)


def test_molar_basis_agrees_with_live_phreeqc_model_vs_model(ref):
    ca, res = _kernel_ca("converted_to_molar")
    rel = ca / (ref["Ca_total_molal"] * ss.RHO_W_25C_KG_PER_L) - 1.0
    assert rel == pytest.approx(MOLAR_REL_DOCUMENTED, abs=MOLAR_TOL), f"MODEL-vs-MODEL Ca rel diff {rel:.3e}"
    assert res.validation_ladder[adm.COMPARED_TO_REFERENCE_IMPLEMENTATION]["holds"] is True
    assert res.validation_ladder[adm.EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND]["holds"] is False


def test_legacy_basis_shows_the_disclosed_gap_against_live_phreeqc(ref):
    ca, res = _kernel_ca("as_tabulated_molal")
    rel = ca / (ref["Ca_total_molal"] * ss.RHO_W_25C_KG_PER_L) - 1.0
    assert rel == pytest.approx(LEGACY_REL_DOCUMENTED, abs=LEGACY_TOL), f"MODEL-vs-MODEL Ca rel diff {rel:.3e}"
    assert res.validation_ladder[adm.WITHIN_DECLARED_FORMULA_DOMAIN]["holds"] is False
    assert res.validation_ladder[adm.EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND]["holds"] is False
