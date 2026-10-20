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
