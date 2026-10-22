"""Wave F -- the source-backed acetic acid / acetate / water 0-D equilibrium.

SYNTHETIC/experimental.  The equilibrium CONSTANTS are sourced (CRC 84th ed. / standard Kw); the pH predictions
are validated against (a) the agreement of two INDEPENDENT solver algorithms on the same sourced data and (b)
SOURCED textbook pH anchors.  The Reaktoro cross-tool is unavailable here, so its benchmark is an explicit UNKNOWN
obligation, never a fabricated number.
"""
import math

import pytest

from experiments.sandbox_foundation.aqueous_equilibrium import (
    DAVIES_A_25C, KA_ACETIC_25C, KW_25C, AcetateWaterSystem, SourcedConstant, reaktoro_benchmark_obligation, solve)
from experiments.sandbox_foundation.twocell import InvalidParameterError


# ---- provenance discipline: a sourced constant carries real provenance; a fabricated one is refused ----------
def test_sourced_constants_carry_provenance():
    for c in (KA_ACETIC_25C, KW_25C, DAVIES_A_25C):
        assert c.status == "SOURCED" and c.source.strip() and c.uncertainty > 0 and c.value > 0
    assert abs(-math.log10(KA_ACETIC_25C.value) - 4.756) < 0.01      # pKa 4.756
    assert abs(-math.log10(KW_25C.value) - 14.0) < 0.01             # pKw ~ 14


def test_a_fabricated_zero_uncertainty_constant_is_refused():
    with pytest.raises(InvalidParameterError):
        SourcedConstant("fake", 1.0e-5, 0.0, "x", 298.15, "")       # no source + decorative error bar


# ---- the two independent solver routes must agree (a SOLVER cross-check) --------------------------------------
@pytest.mark.parametrize("C_T,Na", [(0.1, 0.0), (1.0, 0.0), (0.01, 0.0), (0.1, 0.05), (0.2, 0.1)])
def test_two_routes_agree_and_charge_balances(C_T, Na):
    r = solve(AcetateWaterSystem(C_T, sodium_M=Na))
    assert r.solver_agreement_residual <= 1e-12 * max(1.0, r.h_plus_M)   # numpy.roots vs brentq agree
    assert r.charge_balance_residual <= 1e-12                            # the solution satisfies charge balance
    # mass balance: HAc + Ac- == C_T
    assert abs((r.hac_M + r.ac_minus_M) - C_T) <= 1e-12 * max(1.0, C_T)


# ---- SOURCED textbook pH anchors (ideal model) ----------------------------------------------------------------
def test_pure_water_is_pH_7():
    r = solve(AcetateWaterSystem(0.0, 0.0))
    assert abs(r.pH - 7.0) < 1e-6


def test_tenth_molar_acetic_acid_is_about_pH_2_87():
    # standard general-chemistry result: 0.1 M acetic acid -> pH ~ 2.87-2.88
    r = solve(AcetateWaterSystem(0.1))
    assert 2.86 <= r.pH <= 2.89, r.pH
    assert r.hac_M > r.ac_minus_M > r.oh_minus_M                     # weakly dissociated, acidic


def test_one_molar_acetic_acid_is_about_pH_2_38():
    r = solve(AcetateWaterSystem(1.0))
    assert 2.36 <= r.pH <= 2.40, r.pH


def test_equimolar_acetate_buffer_sits_at_the_pKa():
    # 0.05 M acetic acid + 0.05 M acetate (as NaAc) -> [HAc]=[Ac-] -> pH = pKa = 4.756 (Henderson-Hasselbalch)
    r = solve(AcetateWaterSystem(total_acetic_M=0.1, sodium_M=0.05))
    assert abs(r.pH - 4.756) < 0.02, r.pH
    assert abs(r.hac_M - r.ac_minus_M) < 1e-3                        # genuinely at the half-neutralisation point


# ---- the Davies nonideal correction shifts pH (documented, not claimed exact) ---------------------------------
def test_davies_correction_shifts_pH_and_lowers_gamma():
    ideal = solve(AcetateWaterSystem(0.1, sodium_M=0.1, activity_model="ideal"))
    davies = solve(AcetateWaterSystem(0.1, sodium_M=0.1, activity_model="davies"))
    assert davies.gamma_monovalent < 1.0                            # activity coefficient below 1 at finite I
    assert ideal.gamma_monovalent == 1.0
    assert abs(davies.pH - ideal.pH) > 1e-3                         # a real, documented shift
    assert davies.activity_model == "davies"


def test_davies_off_25C_is_refused_not_extrapolated():
    with pytest.raises(InvalidParameterError):
        AcetateWaterSystem(0.1, temperature_K=310.0, activity_model="davies")


# ---- the independent benchmark is preserved as an explicit UNKNOWN, never fabricated --------------------------
def test_reaktoro_benchmark_is_an_unknown_obligation_not_a_fabricated_number():
    ob = reaktoro_benchmark_obligation()
    assert ob.tool == "Reaktoro" and ob.status == "UNAVAILABLE_UNKNOWN"
    assert ob.verdict is None                                       # no fabricated comparison
    assert "activity_model" in ob.recipe and "independence_caveat" in ob.recipe


# ---- the species set is CURATED (fixed), not arbitrary chemistry by formula similarity ------------------------
def test_negative_inputs_are_refused():
    for kw in (dict(total_acetic_M=-0.1), dict(total_acetic_M=0.1, sodium_M=-0.01)):
        with pytest.raises(InvalidParameterError):
            AcetateWaterSystem(**kw)
