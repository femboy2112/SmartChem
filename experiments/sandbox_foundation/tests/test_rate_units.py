"""Wave B2 -- rate-constant units + the concentration-standard invariance of the Wegscheider cycle condition.

SYNTHETIC / idealized.  The theorems live in rate_units.py's docstring; here we pin the dimensional facts and
check the invariance identity gamma . dnu = ones^T (N gamma) = 0 EXACTLY on real cycles."""
import math

import numpy as np
import pytest

from experiments.sandbox_foundation.rate_units import (
    assert_interchangeable, equilibrium_conc_exponent, net_mole_change, rate_constant_conc_exponent,
    rate_constant_units, standard_state_invariance_residual, thermodynamic_K)
from experiments.sandbox_foundation.twocell import InvalidParameterError, Mechanism, ReactionRate


def _ab(k_f=2.0, k_r=1.0):
    # A <-> B, dnu = 0 (isomerization): Kc = k_f/k_r is dimensionless already.
    return Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X", "charge"),
                     [[1, 1], [0, 0]], (ReactionRate(k_f=k_f, k_r=k_r, reversible=True),))


def _a_to_b_plus_c(k_f=4.0, k_r=2.0):
    # A <-> B + C, dnu = +1: A = XY splits into B = X and C = Y (conserving); Kc has concentration-exponent +1,
    # so K^o = (k_f/k_r)/c_ref.
    return Mechanism(("A", "B", "C"), [[1.0], [0.0], [0.0]], [[0.0], [1.0], [1.0]],
                     ("X", "Y", "charge"), [[1, 1, 0], [1, 0, 1], [0, 0, 0]],
                     (ReactionRate(k_f=k_f, k_r=k_r, reversible=True),))


# ---- rate-constant units: a unimolecular k is not a bimolecular k --------------------------------------------
def test_rate_constant_units_depend_on_order():
    assert rate_constant_conc_exponent(1.0) == 0.0 and rate_constant_units(1.0) == "1/s"            # unimolecular
    assert rate_constant_conc_exponent(2.0) == -1.0 and rate_constant_units(2.0) == "(mol/m^3)^-1 / s"  # bimolecular
    assert rate_constant_conc_exponent(0.0) == 1.0 and rate_constant_units(0.0) == "(mol/m^3)^1 / s"  # zero-order


def test_unimolecular_and_bimolecular_constants_cannot_be_interchanged():
    assert_interchangeable(2.0, 2.0)                       # same order: fine
    with pytest.raises(InvalidParameterError):
        assert_interchangeable(1.0, 2.0)                   # dimensionally distinct: refused


# ---- thermodynamic K^o: dimensional Kc, dimensionless K^o ----------------------------------------------------
def test_isomerization_K_is_reference_independent():
    m = _ab(k_f=2.0, k_r=1.0)
    assert net_mole_change(m)[0] == 0.0
    for c_ref in (1.0, 55_000.0):                          # dnu = 0 -> no c_ref dependence
        assert thermodynamic_K(m, c_ref)[0] == pytest.approx(2.0)


def test_dissociation_K_divides_by_reference_to_the_mole_change():
    m = _a_to_b_plus_c(k_f=4.0, k_r=2.0)
    assert net_mole_change(m)[0] == 1.0
    assert equilibrium_conc_exponent(m)[0] == 1.0          # elementary: m_r - m_f = 2 - 1 = dnu
    assert thermodynamic_K(m, 1.0)[0] == pytest.approx(2.0)        # (k_f/k_r)/1^1
    assert thermodynamic_K(m, 10.0)[0] == pytest.approx(0.2)       # (k_f/k_r)/10^1


def test_empirical_order_mismatch_gives_a_restricted_verdict():
    # structural A <-> B + C (dnu = +1) but an empirical law whose orders do NOT match the complexes:
    m = Mechanism(("A", "B", "C"), [[1.0], [0.0], [0.0]], [[0.0], [1.0], [1.0]],
                  ("X", "Y", "charge"), [[1, 1, 0], [1, 0, 1], [0, 0, 0]],
                  (ReactionRate(k_f=1.0, k_r=1.0, reversible=True),),
                  kinetics="empirical", forward_orders=[[1.0], [0.0], [0.0]],
                  reverse_orders=[[0.0], [0.5], [0.5]], rate_law_note="SYNTHETIC half-order reverse")
    assert equilibrium_conc_exponent(m)[0] == 0.0 and net_mole_change(m)[0] == 1.0   # kinetic != structural
    with pytest.raises(InvalidParameterError):
        thermodynamic_K(m, 1.0)                             # the elementary relation does not apply -> refuse


# ---- the invariance theorem: gamma . dnu = ones^T (N gamma) = 0 on real cycles -------------------------------
def test_cycle_mole_change_vanishes_even_when_each_reaction_changes_mole_number():
    # r1: A -> 2B (dnu=+1), r2: A -> 2B again (dnu=+1); cycle gamma=(1,-1).  dnu is nonzero per reaction,
    # yet gamma . dnu = 1 - 1 = 0, and ones^T (N gamma) = 0 exactly.
    N = np.array([[-1, -1], [2, 2]])
    assert standard_state_invariance_residual(N) == 0.0
    # for the 3-cycle isomerization each dnu is already 0; the residual is still exactly 0.
    N3 = np.array([[-1, 0, 1], [1, -1, 0], [0, 1, -1]])
    assert standard_state_invariance_residual(N3) == 0.0


def test_cycle_logK_sum_is_independent_of_the_reference_concentration():
    # two A<->2B reactions with different constants; the cycle (1,-1) log-K^o sum must not depend on c_ref.
    def mech(kf, kr):
        # A = X2 <-> 2 B (B = X): conserving, dnu = +1.
        return Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [2.0]], ("X", "charge"),
                         [[2, 1], [0, 0]], (ReactionRate(k_f=kf, k_r=kr, reversible=True),))
    m1, m2 = mech(3.0, 1.0), mech(5.0, 2.0)
    cycle = np.array([1.0, -1.0])                           # ker of the stacked [N1 N2] = [[-1,-1],[2,2]]
    sums = []
    for c_ref in (1.0, 55_000.0):
        logKo = np.array([math.log(thermodynamic_K(m1, c_ref)[0]), math.log(thermodynamic_K(m2, c_ref)[0])])
        sums.append(float(cycle @ logKo))
    assert sums[0] == pytest.approx(sums[1])                # invariant under the concentration-standard change


# ---- Round IV B1: thermodynamic_K must be SPECIESWISE, not merely total-order --------------------------------
def _ab_empirical(fo, ro, k_f=4.0, k_r=1.0):
    """A <-> B with empirical orders fo/ro (A row then B row).  E@N = 0 by X-conservation."""
    return Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X", "charge"), [[1, 1], [0, 0]],
                     (ReactionRate(k_f=k_f, k_r=k_r, reversible=True),), kinetics="empirical",
                     forward_orders=fo, reverse_orders=ro, rate_law_note="SYNTHETIC empirical")


def test_RIV_B1_matching_total_but_mismatched_specieswise_is_restricted():
    """THE counterexample: v_f = 4[A]^2, v_r = [B]^2.  Total orders match (m_f=m_r=2), dnu=0 -- the OLD total-order
    test admitted it and returned K=4, but the true positive ratio is [B]/[A]=2.  Specieswise orr-of = [-2,+2] !=
    N = [-1,+1], so it must be RESTRICTED (raise)."""
    m = _ab_empirical(fo=[[2.0], [0.0]], ro=[[0.0], [2.0]])
    with pytest.raises(InvalidParameterError):
        thermodynamic_K(m, 1.0)


def test_RIV_B1_elementary_is_admitted_and_equals_kf_over_kr():
    m = _ab(k_f=4.0, k_r=1.0)                               # elementary A<->B, dnu=0
    assert thermodynamic_K(m, 1.0) == pytest.approx([4.0])


def test_RIV_B1_empirical_with_valid_specieswise_orders_is_admitted():
    # empirical orders that DO equal the complexes (orr-of == N): first-order both ways -> K = kf/kr
    m = _ab_empirical(fo=[[1.0], [0.0]], ro=[[0.0], [1.0]], k_f=3.0, k_r=1.5)
    assert thermodynamic_K(m, 1.0) == pytest.approx([2.0])


def test_RIV_B1_irreversible_or_incomplete_is_refused():
    m = Mechanism(("A", "B"), [[1.0], [0.0]], [[0.0], [1.0]], ("X", "charge"), [[1, 1], [0, 0]],
                  (ReactionRate(k_f=2.0, k_r=None, reversible=False),))
    with pytest.raises(InvalidParameterError):
        thermodynamic_K(m, 1.0)                            # needs every reaction reversible (k_f and k_r)


def test_RIV_B1_reversed_orientation_gives_the_reciprocal_K():
    fwd = _ab(k_f=4.0, k_r=1.0)                             # A -> B
    rev = Mechanism(("A", "B"), [[0.0], [1.0]], [[1.0], [0.0]], ("X", "charge"), [[1, 1], [0, 0]],
                    (ReactionRate(k_f=1.0, k_r=4.0, reversible=True),))   # B -> A, swapped constants
    assert thermodynamic_K(fwd, 1.0)[0] == pytest.approx(1.0 / thermodynamic_K(rev, 1.0)[0])
