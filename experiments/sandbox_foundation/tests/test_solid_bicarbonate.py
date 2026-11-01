"""OPERATION XIII P4 -- the solid sodium-bicarbonate phase (section 6 test list).

Load-bearing pins:
  * dissolution supplies Na and inorganic carbon in 1:1:1 stoichiometry; total sodium and total carbon
    (aqueous + solid) are conserved; charge is preserved (the solid is electroneutral);
  * EQUILIBRIUM (Ksp saturation) is separate from RATE (an ASSUMED k_diss): the thermo limit earns
    NUMERICALLY_VERIFIED when admitted; a finite-rate step is ASSUMED_PARAMETER and caps at saturation;
  * excess solid leaves an undissolved remainder at SI = 1 (solubility bound); insufficient solid dissolves fully;
  * in vinegar the acid consumes bicarbonate so the solid keeps dissolving and pH rises (the fizz, emergent).
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.solid_bicarbonate import (
    KSP_NAHCO3_25C,
    NAHCO3_SOLUBILITY_25C,
    SolidBicarbonateError,
    SolidBicarbonateSystem,
    _tier,
    dissolution_step,
    dissolve_to_saturation,
    saturation_index,
    within_empirical_solubility_domain,
)


def _sys(**kw):
    base = dict(volume_L=1.0, n_acetate_mol=0.0, n_carbon_aqueous_mol=0.0, n_sodium_aqueous_mol=0.0,
                n_solid_mol=0.0, activity_model="ideal")
    base.update(kw)
    return SolidBicarbonateSystem(**base)


def test_sourced_solubility_and_empirical_qsp_provenance():
    assert NAHCO3_SOLUBILITY_25C.status == "SOURCED" and NAHCO3_SOLUBILITY_25C.uncertainty > 0
    assert KSP_NAHCO3_25C.status == "DERIVED"
    assert abs(KSP_NAHCO3_25C.value - NAHCO3_SOLUBILITY_25C.value ** 2) < 1e-12
    # OPERATION XIV P0-1B: it is labelled an EMPIRICAL concentration product, NOT a thermodynamic activity Ksp.
    assert "EMPIRICAL" in KSP_NAHCO3_25C.units and "Ksp" in KSP_NAHCO3_25C.units  # "...NOT an activity-based Ksp"


def test_excess_solid_at_saturation_is_out_of_domain_so_tier_demotes():
    # OPERATION XIV P0-1B: dissolving to saturation drives [Na+]=[HCO3-]~1.2 M, an ionic strength FAR outside the
    # dilute domain where the empirical Qsp = S^2 proxy is defensible.  The conservation + the SI=1 bound still hold
    # (STRUCTURALLY conserving), but the saturation CLAIM demotes to UNVERIFIED -- it is model-level, never a
    # source-validated out-of-domain prediction.  (The old test over-claimed NUMERICALLY_VERIFIED here.)
    s = _sys(n_solid_mol=2.0)
    r = dissolve_to_saturation(s)
    assert r.saturated and not r.exhausted
    assert r.system_after.n_solid_mol > 0                 # a remainder stays undissolved
    assert abs(r.saturation_index_after - 1.0) < 1e-6     # the solubility bound (conservation is unaffected)
    assert r.claim_tier == claim_tiers.UNVERIFIED         # ~1.2 M is out of the dilute Qsp domain -> demoted


def test_insufficient_solid_dissolves_fully():
    s = _sys(n_solid_mol=0.3)
    r = dissolve_to_saturation(s)
    assert r.exhausted and not r.saturated
    assert abs(r.system_after.n_solid_mol) < 1e-12
    assert r.saturation_index_after < 1.0


def test_dissolution_conserves_sodium_and_carbon_in_1to1_stoichiometry():
    s = _sys(n_solid_mol=0.3, n_carbon_aqueous_mol=0.05, n_sodium_aqueous_mol=0.05)
    tot_na0, tot_c0 = s.total_sodium_mol, s.total_carbon_mol
    r = dissolve_to_saturation(s)
    a = r.system_after
    assert abs(a.total_sodium_mol - tot_na0) < 1e-12
    assert abs(a.total_carbon_mol - tot_c0) < 1e-12
    # 1:1:1 -- aqueous Na and aqueous C each rose by exactly the dissolved amount.
    assert abs((a.n_sodium_aqueous_mol - 0.05) - r.dissolved_mol) < 1e-12
    assert abs((a.n_carbon_aqueous_mol - 0.05) - r.dissolved_mol) < 1e-12


def test_dissolved_only_baseline_does_nothing():
    s = _sys(n_carbon_aqueous_mol=0.1, n_sodium_aqueous_mol=0.1, n_solid_mol=0.0)
    r = dissolve_to_saturation(s)
    assert r.dissolved_mol == 0.0 and not r.saturated and not r.exhausted


def test_vinegar_plus_solid_fizzes_pH_rises():
    s = _sys(volume_L=0.1, n_acetate_mol=0.02, n_solid_mol=0.05)   # 0.2 M acetic acid + powder
    pH0 = s.speciate().pH
    r = dissolve_to_saturation(s)
    assert r.system_after.speciate().pH > pH0
    assert r.dissolved_mol > 0


def test_different_solid_amounts_change_how_much_dissolves():
    little = dissolve_to_saturation(_sys(n_solid_mol=0.2)).dissolved_mol
    lots = dissolve_to_saturation(_sys(n_solid_mol=2.0)).dissolved_mol
    assert lots > little                                  # more available -> reach saturation (capped), more dissolves


def test_finite_rate_is_positive_assumed_and_capped_at_saturation():
    s = _sys(n_solid_mol=2.0)
    st = dissolution_step(s, k_diss_mol_per_s=0.1, dt=1.0)
    assert st.dissolved_mol > 0
    assert st.claim_tier == claim_tiers.ASSUMED_PARAMETER     # a rate step is never more than assumed
    cur = s
    for _ in range(400):
        cur = dissolution_step(cur, k_diss_mol_per_s=0.5, dt=1.0).system_after
    assert saturation_index(cur) <= 1.0 + 1e-6               # never overshoots the solubility bound
    assert cur.n_solid_mol > 0                               # excess remains undissolved


def test_saturated_solution_refuses_further_dissolution():
    # pre-saturate, then a further rate step dissolves nothing.
    sat = dissolve_to_saturation(_sys(n_solid_mol=2.0)).system_after
    st = dissolution_step(sat, k_diss_mol_per_s=1.0, dt=10.0)
    assert st.dissolved_mol == 0.0 and st.saturated


def test_rate_requires_positive_k_and_dt():
    s = _sys(n_solid_mol=1.0)
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(SolidBicarbonateError):
            dissolution_step(s, k_diss_mol_per_s=bad, dt=1.0)
    with pytest.raises(SolidBicarbonateError):
        dissolution_step(s, k_diss_mol_per_s=0.1, dt=-1.0)


def test_input_validation():
    with pytest.raises(SolidBicarbonateError):
        _sys(volume_L=0.0, n_solid_mol=1.0)
    with pytest.raises(SolidBicarbonateError):
        _sys(n_solid_mol=-1.0)


# ---------------------------------------------- OPERATION XIV P0-1B: the empirical Qsp applicability-domain matrix
def test_dilute_undersaturation_is_within_domain_and_verified():
    # a dilute solution (low ionic strength, undersaturated) is WHERE the empirical Qsp proxy is defensible.
    s = _sys(n_carbon_aqueous_mol=0.05, n_sodium_aqueous_mol=0.05, n_solid_mol=0.0)
    assert within_empirical_solubility_domain(s)
    assert saturation_index(s) < 1.0
    assert _tier(s) == claim_tiers.NUMERICALLY_VERIFIED


def test_high_ionic_strength_is_out_of_domain_and_demotes_even_in_ideal_model():
    # a high-salt matrix (common-ion sodium) pushes the ionic strength past the Davies domain; the ideal
    # concentration-product proxy is model-level only there, so the tier demotes regardless of activity_model.
    s = _sys(n_carbon_aqueous_mol=0.1, n_sodium_aqueous_mol=1.0, n_solid_mol=0.0, activity_model="ideal")
    assert not within_empirical_solubility_domain(s)
    assert _tier(s) == claim_tiers.UNVERIFIED


def test_dissolving_NaHCO3_raises_SI_but_bare_sodium_alkalinity_lowers_it():
    # The honest common-ion behaviour in this speciation model (OPERATION XIV P0-1B; measured, not assumed):
    #   * DISSOLVING NaHCO3 adds Na+ AND inorganic carbon 1:1, holding pH at the bicarbonate buffer point (~8.34),
    #     so [Na+][HCO3-] -- and thus SI -- rises monotonically toward saturation.  This is the ordering the
    #     dissolution solver (_si_after_dissolving / dissolve_to_saturation) relies on.
    #   * BARE sodium at FIXED carbon is NOT an inert common ion: with no counter-anion it is alkalinity, driving the
    #     pH past the HCO3- (Bjerrum) maximum so carbon converts HCO3- -> CO3^2- and [HCO3-] -- and SI -- FALL.  The
    #     naive "add Na+, SI goes up" intuition is wrong in this system, and the proxy is honest about it.
    base = saturation_index(_sys(n_carbon_aqueous_mol=0.05, n_sodium_aqueous_mol=0.05))
    co_dissolved = saturation_index(_sys(n_carbon_aqueous_mol=0.30, n_sodium_aqueous_mol=0.30))
    bare_sodium = saturation_index(_sys(n_carbon_aqueous_mol=0.05, n_sodium_aqueous_mol=0.30))
    assert co_dissolved > base               # dissolving more NaHCO3 (Na + C together) approaches saturation
    assert bare_sodium < base                # bare Na+ alkalinity past the bicarbonate maximum depletes HCO3-


def test_undersaturated_solid_fully_dissolves_within_domain_is_verified():
    # a small amount of solid into water: dissolves fully, stays dilute+undersaturated -> within domain, verified.
    r = dissolve_to_saturation(_sys(n_solid_mol=0.2))
    assert r.exhausted and r.saturation_index_after < 1.0
    assert r.claim_tier == claim_tiers.NUMERICALLY_VERIFIED       # dilute enough to stay in the Qsp domain
