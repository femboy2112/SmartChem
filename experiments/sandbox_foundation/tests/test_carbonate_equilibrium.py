"""Tests for the source-backed carbonate / CO2 gas-partition 0-D equilibrium (`carbonate_equilibrium.py`).

The discipline mirrors `test_aqueous_equilibrium.py`: the famous pH anchors are equation/implementation VERIFICATION
against the SAME constants (NOT independent experimental validation -- that stays EXTERNAL_VALIDATION_UNAVAILABLE);
every solved result must satisfy the always-on invariants (charge balance, the mode's carbon balance, route
agreement, nonnegativity); and the fail-closed gate is tested to actually REFUSE, so these checks are not vacuous.
"""
import math

import pytest

import experiments.sandbox_foundation.carbonate_equilibrium as cb
from experiments.sandbox_foundation.aqueous_equilibrium import (
    NumericalVerificationError,
    OutOfSourceDomainError,
    SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
    SOLVED_WITHIN_IDEAL_MODEL,
    SourcedConstant,
)
from experiments.sandbox_foundation.carbonate_equilibrium import CarbonateWaterSystem, solve
from experiments.sandbox_foundation.twocell import InvalidParameterError

P_ATM = 10 ** (-3.5)  # atmospheric CO2 partial pressure ~ 3.16e-4 atm (log P_CO2 = -3.5)


# --------------------------------------------------------------------------------- always-on invariants helper
def _assert_invariants(r, *, mode):
    """Every admitted result obeys these regardless of how good the pH looks (V3_0 section 4.0, scaled to 0-D)."""
    assert r.verdict in (SOLVED_WITHIN_IDEAL_MODEL, SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL)
    # charge balance (divalent CO3 weighted x2), closed to a tight bound.
    cb_direct = abs((r.na_plus_M + r.h_plus_M) - (r.oh_minus_M + r.hco3_M + 2.0 * r.co3_M))
    assert cb_direct < 1e-9 * max(1.0, r.na_plus_M + r.h_plus_M + r.oh_minus_M + r.hco3_M + 2.0 * r.co3_M)
    # the two independent solver routes agreed.
    assert r.solver_agreement_residual < cb.AGREEMENT_RTOL * max(1e-30, r.h_plus_M)
    # no negative concentration.
    for c in (r.co2aq_M, r.hco3_M, r.co3_M, r.h_plus_M, r.oh_minus_M, r.na_plus_M):
        assert c >= -cb.NONNEGATIVITY_ATOL
    # all finite, pH consistent with [H+].
    assert math.isfinite(r.pH) and math.isfinite(r.pH_concentration) and math.isfinite(r.pH_activity)
    assert abs(r.pH_concentration - (-math.log10(r.h_plus_M / r.c_ref_M))) < 1e-12


# --------------------------------------------------------------------------------- the textbook anchors (VERIFICATION)
# The bands are intentionally generous: these are ROUNDED textbook values, so an exact equilibrium solve is expected
# to sit near but not exactly on them.  The point is reproduction of known chemistry, not a tuned match.
def test_open_pure_water_atmospheric_co2_is_about_5_6():
    r = solve(CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM))
    assert 5.5 < r.pH < 5.8, r.pH          # the classic ~5.6 of rainwater in equilibrium with air
    _assert_invariants(r, mode="open")
    assert r.total_dissolved_carbon_M > 0  # C_T is an OUTPUT here


def test_open_one_atm_co2_is_acidic_soda_water():
    r = solve(CarbonateWaterSystem(mode="open", p_co2_atm=1.0))
    assert 3.8 < r.pH < 4.0, r.pH          # ~3.9 for water saturated at 1 atm CO2
    _assert_invariants(r, mode="open")


def test_closed_bicarbonate_is_amphoteric_buffer_near_half_pk_sum():
    # pH ~ (pK1 + pK2)/2 = (6.35 + 10.33)/2 = 8.34, and nearly concentration-independent.
    r_tenth = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.1))
    r_hundredth = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.01, sodium_M=0.01))
    assert 8.2 < r_tenth.pH < 8.5, r_tenth.pH
    assert 8.2 < r_hundredth.pH < 8.5, r_hundredth.pH
    # near-concentration-independence: a 10x dilution barely moves it.
    assert abs(r_tenth.pH - r_hundredth.pH) < 0.05
    _assert_invariants(r_tenth, mode="closed")
    _assert_invariants(r_hundredth, mode="closed")


def test_closed_carbonate_is_strongly_basic():
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.2))  # 0.1 M Na2CO3
    assert 11.4 < r.pH < 11.8, r.pH
    _assert_invariants(r, mode="closed")


def test_closed_dissolved_co2_no_base_is_acidic():
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.01, sodium_M=0.0))
    assert 4.0 < r.pH < 4.4, r.pH
    _assert_invariants(r, mode="closed")


def test_closed_carbon_balance_closes_exactly():
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.1))
    assert abs((r.co2aq_M + r.hco3_M + r.co3_M) - 0.1) < 1e-9
    assert r.carbon_balance_residual < 1e-9


# --------------------------------------------------------------------------------- Davies activity model
def test_davies_lowers_buffer_ph_vs_ideal():
    ideal = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.1))
    davies = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.1, activity_model="davies"))
    assert davies.activity_model == "davies"
    assert davies.pH < ideal.pH            # activity correction lowers the apparent pH of a nonzero-I buffer
    assert davies.davies_iterations >= 1
    _assert_invariants(davies, mode="closed")


def test_davies_divalent_gamma_is_monovalent_to_the_fourth():
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.2, activity_model="davies"))
    assert r.gamma_divalent == pytest.approx(r.gamma_monovalent ** 4, rel=1e-12)
    assert 0.0 < r.gamma_monovalent < 1.0  # a real ionic-strength depression


def test_ideal_gammas_are_unity():
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.1))
    assert r.gamma_monovalent == 1.0 and r.gamma_divalent == 1.0


# --------------------------------------------------------------------------------- the divalent is actually weighted x2
def test_ionic_strength_weights_carbonate_divalently():
    # In 0.1 M Na2CO3 the CO3(2-) term dominates I; a monovalent (x1) mis-weighting would give a visibly smaller I.
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=0.2))
    i_divalent = 0.5 * (r.h_plus_M + r.oh_minus_M + r.hco3_M + 4.0 * r.co3_M + r.na_plus_M)
    i_if_monovalent = 0.5 * (r.h_plus_M + r.oh_minus_M + r.hco3_M + 1.0 * r.co3_M + r.na_plus_M)
    assert r.ionic_strength_M == pytest.approx(i_divalent, rel=1e-12)
    assert r.ionic_strength_M - i_if_monovalent > 0.1   # the x2 (z^2=4) weighting is material, not cosmetic


# --------------------------------------------------------------------------------- open vs sealed discriminator (B6)
def test_sealed_retains_carbon_and_builds_pressure_vs_open():
    """V3_0 benchmark B6: for a carbon-rich, un-buffered system, a SEALED vessel keeps CO2 dissolved and builds a
    partial pressure far above the atmospheric reservoir an OPEN system vents to.  A model with no gas partition
    would give the two the same dissolved CO2 -- this asserts they differ by a lot."""
    sealed = solve(CarbonateWaterSystem(mode="sealed", total_carbon_mol=0.05, v_liquid_L=1.0, v_gas_L=0.5, sodium_M=0.0))
    open_air = solve(CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM, sodium_M=0.0))
    # sealed builds pressure orders of magnitude above the atmospheric reservoir...
    assert sealed.p_co2_atm > 100 * P_ATM
    # ...and holds far more dissolved CO2 than the vented-to-air case.
    assert sealed.co2aq_M > 100 * open_air.co2aq_M
    # carbon conserves across liquid + headspace.
    assert abs((sealed.dissolved_carbon_mol + sealed.gas_carbon_mol) - 0.05) < 1e-9
    assert sealed.gas_carbon_mol > 0 and sealed.dissolved_carbon_mol > 0
    _assert_invariants(sealed, mode="sealed")
    _assert_invariants(open_air, mode="open")


def test_sealed_alkaline_keeps_more_carbon_dissolved_than_acidic():
    """The partition depends on CHEMISTRY, not a switch: with alkalinity the carbon stays as HCO3-/CO3 in solution;
    without it, volatile CO2(aq) drives off to the headspace at higher pressure."""
    alkaline = solve(CarbonateWaterSystem(mode="sealed", total_carbon_mol=0.05, v_liquid_L=1.0, v_gas_L=0.5, sodium_M=0.05))
    acidic = solve(CarbonateWaterSystem(mode="sealed", total_carbon_mol=0.05, v_liquid_L=1.0, v_gas_L=0.5, sodium_M=0.0))
    assert alkaline.gas_carbon_mol < acidic.gas_carbon_mol
    assert alkaline.p_co2_atm < acidic.p_co2_atm
    assert alkaline.pH > acidic.pH


# --------------------------------------------------------------------------------- monotonicities (sanity physics)
def test_more_base_raises_closed_ph():
    phs = [solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.1, sodium_M=na)).pH
           for na in (0.05, 0.10, 0.15, 0.20)]
    assert phs == sorted(phs)          # adding base monotonically raises pH


def test_higher_pco2_lowers_open_ph():
    phs = [solve(CarbonateWaterSystem(mode="open", p_co2_atm=p)).pH for p in (1e-4, 1e-3, 1e-2, 1e-1, 1.0)]
    assert phs == sorted(phs, reverse=True)   # more CO2 -> more acidic


# --------------------------------------------------------------------------------- fail-closed behaviour (NON-vacuous)
def test_off_source_temperature_is_refused_at_construction():
    with pytest.raises(OutOfSourceDomainError):
        CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM, temperature_K=310.0)


def test_davies_out_of_ionic_strength_domain_is_refused():
    # 1 M Na2CO3 -> I ~ 3 M, far past DAVIES_I_MAX = 0.5; the gate must refuse rather than extrapolate the activity.
    with pytest.raises(NumericalVerificationError):
        solve(CarbonateWaterSystem(mode="closed", total_carbon_M=1.0, sodium_M=2.0, activity_model="davies"))


def test_missing_mode_input_is_rejected():
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="open")                      # no p_co2_atm
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="closed")                    # no total_carbon_M
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="sealed", total_carbon_mol=0.01, v_liquid_L=1.0)  # no v_gas_L


def test_bad_parameters_rejected():
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="open", p_co2_atm=-1.0)
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM, sodium_M=-0.1)
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="banana", p_co2_atm=P_ATM)
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM, activity_model="quantum")


# --------------------------------------------------------------------------------- provenance discipline (inherited)
def test_fabricated_zero_uncertainty_constant_is_refused():
    # A SOURCED constant with a zero (decorative) error bar is banned -- worse than UNKNOWN (SourcedConstant invariant).
    with pytest.raises(InvalidParameterError):
        SourcedConstant("K1_fake", 1e-6, 0.0, "dimensionless (molar)", 298.15, "a citation", "SOURCED")


def test_off_temperature_constant_is_refused():
    bad_k1 = SourcedConstant("K1_hot", 1e-6, 1e-8, "dimensionless (molar)", 310.0, "some 37C source", "SOURCED")
    with pytest.raises(OutOfSourceDomainError):
        CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM, K1=bad_k1)


def test_molal_standard_state_constant_is_refused():
    molal_k1 = SourcedConstant("K1_molal", 1e-6, 1e-8, "mol/kg (molal)", 298.15, "a molal source", "SOURCED")
    with pytest.raises(InvalidParameterError):
        CarbonateWaterSystem(mode="open", p_co2_atm=P_ATM, K1=molal_k1)


# --------------------------------------------------------------------------------- verdict vocabulary + benchmark honesty
def test_verdicts_are_the_shared_vocabulary():
    assert cb.VERDICTS == {
        SOLVED_WITHIN_IDEAL_MODEL, SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL, cb.EXTERNAL_VALIDATION_UNAVAILABLE,
    }


def test_phreeqc_obligation_is_external_validation_unavailable_with_no_fabricated_comparison():
    ob = cb.phreeqc_benchmark_obligation()
    assert ob.tool == "PHREEQC"
    assert ob.verdict == cb.EXTERNAL_VALIDATION_UNAVAILABLE
    assert ob.comparison is None               # no numbers fabricated while the tool is absent


def test_sourced_constants_carry_positive_uncertainty_and_citations():
    for const in (cb.K1_CARBONIC_25C, cb.K2_CARBONIC_25C, cb.KH_CO2_25C):
        assert const.status == "SOURCED"
        assert const.uncertainty > 0 and math.isfinite(const.uncertainty)
        assert const.source.strip()
        assert const.T_K == 298.15
    # R is the one exact-by-definition constant, so it alone is allowed a zero error bar.
    assert cb.R_GAS_L_ATM.status == "EXACT" and cb.R_GAS_L_ATM.uncertainty == 0.0


# --------------------------------------------------------------------------------- caveat above the agreement domain
# --------------------------------------------------------------------------- basic-regime regression (adversary-found)
# d'Alembert and Evil Morty INDEPENDENTLY found that the two solver routes lost RELATIVE precision for the tiny [H+]
# of strongly basic solutions (np.roots eigenvalue conditioning on the quartic, plus an absolute brentq xtol floor),
# so the two-route agreement -- and the charge residual, amplified by Kw_c/h^2 -- falsely tripped the gate and
# REFUSED legitimate chemistry.  Fixed by Newton-polishing the polynomial root and driving brentq xtol -> 0 so rtol
# governs.  Each case below RAISED NumericalVerificationError before that fix: non-vacuous proof the gate is now
# satisfied by genuine accuracy, not a widened tolerance (AGREEMENT_RTOL is unchanged).
@pytest.mark.parametrize("kw,expected_pH", [
    (dict(mode="closed", total_carbon_M=1.0, sodium_M=2.0), 12.162),    # 1 M Na2CO3 (washing soda)
    (dict(mode="closed", total_carbon_M=0.0, sodium_M=0.01), 12.000),   # 0.01 M NaOH, zero carbon
    (dict(mode="closed", total_carbon_M=0.01, sodium_M=0.1), 12.903),   # dilute carbonate, large excess base
    (dict(mode="closed", total_carbon_M=0.1, sodium_M=1.0), 13.903),
    (dict(mode="open", sodium_M=1.0, p_co2_atm=1e-10), 13.745),         # strongly basic open
])
def test_strongly_basic_solutions_solve_not_falsely_refused(kw, expected_pH):
    r = solve(CarbonateWaterSystem(**kw))
    assert abs(r.pH - expected_pH) < 0.01, (r.pH, expected_pH)
    _assert_invariants(r, mode=kw["mode"])


def test_high_ionic_strength_result_carries_a_caveat_but_still_solves():
    # 0.2 M Na2CO3 ideal: I ~ 0.6 > the salting-out threshold; ideal mode has no Davies domain cap, so it SOLVES but
    # must carry the honest caveat that the result is model-only out there.
    r = solve(CarbonateWaterSystem(mode="closed", total_carbon_M=0.2, sodium_M=0.4))
    assert r.verdict == SOLVED_WITHIN_IDEAL_MODEL
    assert r.caveats and any("salting-out" in c for c in r.caveats)
