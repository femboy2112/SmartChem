"""OPERATION XXIV-2B/2C -- molal <-> molar standard-state transport of log K, and the four-rung claim ladder."""
from __future__ import annotations

import math

import pytest

from experiments.sandbox_foundation import admissibility as adm
from experiments.sandbox_foundation import sim_api_v2alpha as api
from experiments.sandbox_foundation import standard_state as ss
from experiments.sandbox_foundation.general_kernel import Phase, Species

CA = Species.of("Ca+2", {"Ca": 1}, 2, Phase.AQUEOUS)
CO3 = Species.of("CO3-2", {"C": 1, "O": 3}, -2, Phase.AQUEOUS)
CAL = Species.of("CaCO3(s)", {"Ca": 1, "C": 1, "O": 3}, 0, Phase.SOLID)
H2O = Species.of("H2O", {"H": 2, "O": 1}, 0, Phase.PURE_LIQUID)
H = Species.of("H+", {"H": 1}, 1, Phase.AQUEOUS)
OH = Species.of("OH-", {"H": 1, "O": 1}, -1, Phase.AQUEOUS)


def test_nu_counts_aqueous_solutes_only():
    assert ss.aqueous_nu(((CAL, -1), (CA, 1), (CO3, 1))) == 2
    assert ss.aqueous_nu(((H, -1), (OH, -1), (H2O, 1)), unit_activity=(H2O,)) == -2


def test_round_trip_and_zero_exponent_is_identity():
    assert ss.molar_to_molal_logK(ss.molal_to_molar_logK(-8.48, 2), 2) == pytest.approx(-8.48, abs=1e-15)
    assert ss.molal_to_molar_logK(3.2, 0) == 3.2


def test_ideal_dilute_saturation_index_is_basis_invariant():
    """Independent dimensional check: the SAME dilute state expressed on both bases gives the SAME saturation index
    once K is transported -- and a DIFFERENT one if the molal K is reused on molar concentrations."""
    logK_m = -8.48
    m_ca, m_co3 = 3.1e-4, 1.9e-5                                   # mol/kg
    c_ca, c_co3 = m_ca * ss.RHO_W_25C_KG_PER_L, m_co3 * ss.RHO_W_25C_KG_PER_L      # dilute: c = m rho_w*
    si_m = math.log10(m_ca * m_co3) - logK_m
    si_c = math.log10(c_ca * c_co3) - ss.molal_to_molar_logK(logK_m, 2)
    assert si_c == pytest.approx(si_m, abs=1e-12)
    assert abs((math.log10(c_ca * c_co3) - logK_m) - si_m) == pytest.approx(-2 * math.log10(0.997047), rel=1e-9)


def test_calcite_world_closes_the_basis_gap_against_phreeqc():
    init = (api.SpeciesInventory("cell", "CaCO3(s)", "solid", 0.01),
            api.SpeciesInventory("cell", "H2O", "pure_liquid", 55.34),
            api.SpeciesInventory("cell", "H+", "aqueous", 1e-7), api.SpeciesInventory("cell", "OH-", "aqueous", 1e-7))
    sched = api.BoundarySchedule((api.BoundaryPhase("d", 6000.0, 60, "closed", False),))
    ca = {}
    for basis in ("as_tabulated_molal", "converted_to_molar"):
        res = api.run(api.SimulationSpec(model=api.ModelSpec("calcite_closed_dissolution",
                                                             api.CalciteParams(standard_state_basis=basis)),
                                         initial=init, schedule=sched, solver=api.SolverOptions(rtol=1e-10, atol=1e-18)))
        ca[basis] = sum(res.final_frame.amount("cell", s) for s in ("Ca+2", "CaCO3(aq)", "CaHCO3+", "CaOH+"))
        ladder = dict(res.validation_ladder)
        assert ladder["EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND"] is False
        assert "model-vs-model" in ladder["COMPARED_TO_REFERENCE_IMPLEMENTATION"]
    phreeqc_molar = 1.23007e-4 * ss.RHO_W_25C_KG_PER_L          # XXIII-S4 PHREEQC Ca (mol/kgw) -> mol/L
    assert ca["as_tabulated_molal"] / phreeqc_molar - 1 == pytest.approx(0.0030, abs=2e-4)   # the disclosed bias
    assert abs(ca["converted_to_molar"] / phreeqc_molar - 1) < 2e-4                           # closed by transport


def test_claim_ladder_has_four_distinct_rungs():
    assert len(set(adm.CLAIM_LADDER)) == 4 and adm.CLAIM_LADDER[-1] == adm.EMPIRICALLY_VALIDATED_WITHIN_MEASURED_BAND
