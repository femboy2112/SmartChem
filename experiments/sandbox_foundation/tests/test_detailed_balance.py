"""Detailed-balance / Wegscheider instrument: red/green tests.  Ooh yeah, can do!

Three reversible isomerizations A<->B, B<->C, C<->A.  Reaction columns: [-1,1,0], [0,-1,1], [1,0,-1].
"""
import math

import numpy as np
import pytest

from experiments.sandbox_foundation.detailed_balance import (
    DetailedBalanceError, WegscheiderVerdict, check_detailed_balance)

TOL = 1e-9
N3 = np.array([[-1, 0, 1],
               [1, -1, 0],
               [0, 1, -1]])  # rows A,B,C; columns r1 A->B, r2 B->C, r3 C->A


def test_consistent_cycle_passes_with_both_routes_agreeing():
    v = check_detailed_balance(N3, [2.0, 3.0, 1.0 / 6.0], tol=TOL)
    assert isinstance(v, WegscheiderVerdict)
    assert v.consistent is True
    assert v.residual <= TOL and v.residual_image <= TOL
    assert v.method_agreement is True
    assert v.offending_cycles == []
    assert v.n_cycles == 1


def test_inconsistent_cycle_fails_with_log8_imbalance():
    v = check_detailed_balance(N3, [2.0, 2.0, 2.0], tol=TOL)
    assert v.consistent is False
    assert v.method_agreement is True
    assert v.residual > TOL and v.residual_image > TOL       # BOTH routes flag it (not one lucky route)
    assert len(v.offending_cycles) == 1
    gamma, imbalance = v.offending_cycles[0]
    # Normalization: gamma is UNIT-norm, so gamma ~ +-(1,1,1)/sqrt(3) and gamma.logK = +-log(8)/sqrt(3).
    assert np.linalg.norm(gamma) == pytest.approx(1.0)
    assert np.allclose(np.abs(gamma), 1 / math.sqrt(3))
    assert abs(imbalance) == pytest.approx(math.log(8.0) / math.sqrt(3.0))
    # Rescaled to the integer cycle (1,1,1): the raw cycle dot equals |log 8| (up to sign).
    raw = float(np.dot(gamma / gamma[0], np.log([2.0, 2.0, 2.0])))
    assert raw == pytest.approx(math.log(8.0))
    assert v.residual == pytest.approx(abs(imbalance))


def test_reversed_direction_cycle_also_detected():
    # Product K1*K2*K3 = 1/8 != 1: the other sign of imbalance must also fail.
    v = check_detailed_balance(N3, [0.5, 0.5, 0.5], tol=TOL)
    assert v.consistent is False and v.method_agreement is True


def test_no_cycle_network_is_vacuously_consistent_for_any_positive_K():
    N = np.array([[-1], [1]])  # A<->B, rank R=1, ker(N) trivial
    for k in (7.0, 1e-6, 1e6):
        v = check_detailed_balance(N, [k], tol=TOL)
        assert v.consistent is True and v.method_agreement is True
        assert v.n_cycles == 0 and v.residual == 0.0 and v.offending_cycles == []


def test_tolerance_is_respected():
    K = [2.0, 3.0, 1.0 / 6.0 * (1 + 1e-6)]
    assert check_detailed_balance(N3, K, tol=1e-9).consistent is False
    assert check_detailed_balance(N3, K, tol=1e-3).consistent is True


@pytest.mark.parametrize("K", [[2.0, 0.0, 3.0], [2.0, -1.0, 3.0]])
def test_nonpositive_K_raises(K):
    with pytest.raises(DetailedBalanceError):
        check_detailed_balance(N3, K)


@pytest.mark.parametrize("K", [[2.0, 3.0], [2.0, 3.0, 4.0, 5.0]])
def test_length_mismatch_raises(K):
    with pytest.raises(ValueError):
        check_detailed_balance(N3, K)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_K_raises(bad):
    with pytest.raises(DetailedBalanceError):
        check_detailed_balance(N3, [2.0, bad, 3.0])


def test_nonfinite_N_and_bad_shapes_raise():
    with pytest.raises(DetailedBalanceError):
        check_detailed_balance(np.array([[np.nan, 1.0], [1.0, -1.0]]), [1.0, 1.0])
    with pytest.raises(DetailedBalanceError):
        check_detailed_balance(np.array([-1, 1]), [1.0])          # N not 2-D
    with pytest.raises(DetailedBalanceError):
        check_detailed_balance(N3, [[2.0, 3.0, 4.0]])             # K not 1-D


def test_bimolecular_stoichiometric_cycle_not_graph_cycle():
    # 2A->B (r1) and A+A->B written as a second reaction (r2) share a stoichiometric cycle (1,-1) in ker N.
    N = np.array([[-2, -2], [1, 1]])
    assert check_detailed_balance(N, [5.0, 5.0]).consistent is True
    assert check_detailed_balance(N, [5.0, 6.0]).consistent is False


# ============================================================================================================
# Round III -- the EXACT-integer-kernel repair (red-before-green by an independent adversary).
# The committed float instrument (scipy null_space + numpy lstsq) returned a FALSE inconsistency on an
# ill-conditioned but mathematically FULL-RANK integer matrix: ker(N) = {0} means NO Wegscheider constraint,
# so every positive K is admissible, yet the SVD hallucinated a phantom cycle and BOTH routes agreed on the
# wrong verdict (they share one SVD rank cutoff -- not independent).  The fix decides the rank/kernel EXACTLY
# (rational elimination); the floating routes are retained only as diagnostics.
# ============================================================================================================
def test_C5_full_rank_integer_matrix_is_consistent_not_a_phantom_cycle():
    """THE headline regression.  N=[[1,0],[9e15,1]] is unimodular (det=1), exact column rank 2, ker={0}.
    The committed float code returned consistent=False (a fabricated detailed-balance contradiction) with
    residual == residual_image to the last digit (the two 'independent' routes were one SVD decision read
    twice).  The exact kernel says: no cycle, so EVERY positive K is admissible."""
    N = np.array([[1.0, 0.0], [9.0e15, 1.0]])   # 9e15 < 2^53 -> exact integer float
    v = check_detailed_balance(N, [2.0, 5.0])
    assert v.consistent is True                 # was False under the floating-rank bug
    assert v.exact_rank == 2 and v.n_cycles == 0 and v.offending_cycles == []
    assert v.residual == 0.0
    # the floating SVD route genuinely mis-ranks this matrix (drops the ~1.1e-16 singular value); the exact
    # route corrects it.  float_rank can only UNDER-count (SVD over-counts nulls), never exceed exact_rank.
    assert v.float_rank <= v.exact_rank
    assert v.float_rank == 1                     # pins the SVD mis-rank in the pinned CI scipy (demonstration of the bug)


def test_non_integer_stoichiometry_is_refused_not_silently_rationalized():
    """A 'stoichiometric' matrix with a 1+1e-15 entry is not real integer stoichiometry; the exact instrument
    refuses it fail-closed rather than letting invisible float noise at 1e-15 decide a verdict (the adversary's
    C5'/C6b near-collinear floats).  Real Mechanism.N is integer-valued and passes."""
    for bad in ([[1.0, 1.0], [1.0, 1.0 + 1e-15]], [[1.0, 0.0], [0.0, 1.0 + 1e-12]]):
        with pytest.raises(DetailedBalanceError):
            check_detailed_balance(np.array(bad), [2.0, 5.0])


def test_C2_duplicate_reaction_requires_equal_K_and_reports_the_integer_cycle():
    N = np.array([[-1, -1], [1, 1]])            # A->B written twice: cycle (1,-1)
    ok = check_detailed_balance(N, [3.0, 3.0])
    assert ok.consistent is True and ok.n_cycles == 1
    assert tuple(int(x) for x in ok.cycles[0]) in {(1, -1), (-1, 1)}   # LEGIBLE integer cycle, not a unit float
    assert check_detailed_balance(N, [3.0, 5.0]).consistent is False


def test_C3_reversed_direction_pair_requires_K1_K2_equals_one():
    N = np.array([[-1, 1], [1, -1]])            # A->B, B->A: cycle (1,1) => K1*K2 = 1
    assert check_detailed_balance(N, [4.0, 0.25]).consistent is True
    assert check_detailed_balance(N, [4.0, 4.0]).consistent is False


def test_C4_extreme_scaled_full_rank_has_no_cycle():
    N = np.array([[1000.0, 0.0], [0.0, 1.0]])   # full rank, wildly scaled, no cycle
    v = check_detailed_balance(N, [7.0, 0.1])
    assert v.consistent is True and v.n_cycles == 0 and v.exact_rank == 2


def test_C6a_independent_reactions_distinguished_from_rank_collapse():
    v = check_detailed_balance(np.array([[1.0, 0.0], [0.0, 1.0]]), [2.0, 5.0])
    assert v.consistent is True and v.n_cycles == 0 and v.exact_rank == 2


def test_integer_cycle_is_reported_for_the_triangle():
    v = check_detailed_balance(N3, [2.0, 2.0, 2.0], tol=TOL)
    assert len(v.cycles) == 1
    assert tuple(int(x) for x in v.cycles[0]) in {(1, 1, 1), (-1, -1, -1)}


def test_oversized_matrix_is_a_bounded_refusal():
    from experiments.sandbox_foundation.detailed_balance import MAX_DIM
    big = np.eye(MAX_DIM + 1)
    with pytest.raises(DetailedBalanceError):
        check_detailed_balance(big, np.full(MAX_DIM + 1, 2.0))
