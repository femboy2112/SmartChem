"""Adversarial tests for the exact-rational LP kernel (smartchem.experiment.exact_lp).

A wrong LP silently returns a wrong ceiling -- worse than refusing to answer -- so this kernel is pinned hard,
in isolation from any chemistry, against hand-computed optima, the unbounded ray, degeneracy, and the shape/sign
contracts it relies on.
"""
from fractions import Fraction

import pytest

from smartchem.experiment.exact_lp import LPUnbounded, maximize


class TestKnownOptima:
    def test_a_single_binding_constraint(self):
        # max 3x + 2y  s.t.  x + y <= 4, x <= 2, y <= 3  ->  x=2, y=2, value 10
        value, x = maximize([3, 2], [[1, 1], [1, 0], [0, 1]], [4, 2, 3])
        assert value == Fraction(10)
        assert x == [Fraction(2), Fraction(2)]

    def test_classic_2x2_lp(self):
        # max x + y  s.t.  x + 2y <= 4, 3x + 2y <= 6  ->  x=1, y=3/2, value 5/2
        value, x = maximize([1, 1], [[1, 2], [3, 2]], [4, 6])
        assert value == Fraction(5, 2)
        assert x == [Fraction(1), Fraction(3, 2)]

    def test_fractional_optimum_is_exact_not_float(self):
        # max y s.t. 2y <= 1  ->  y = 1/2 exactly (a float LP would give 0.4999.../0.5000...)
        value, x = maximize([0, 1], [[0, 2]], [1])
        assert value == Fraction(1, 2)
        assert isinstance(value, Fraction) and value.denominator == 2

    def test_allocation_of_a_shared_resource(self):
        # the fan-out shape in the small: max min-ish -- max z s.t. z<=a, z<=b, a+b<=1  (via a,b,z >= 0)
        # variables x=(a,b,z); maximize z: a+b<=1, z-a<=0, z-b<=0  -> a=b=1/2, z=1/2
        value, x = maximize([0, 0, 1], [[1, 1, 0], [-1, 0, 1], [0, -1, 1]], [1, 0, 0])
        assert value == Fraction(1, 2)
        assert x[2] == Fraction(1, 2)


class TestUnbounded:
    def test_a_free_growing_variable_is_unbounded(self):
        # max x  s.t.  -x <= 0  (i.e. x >= 0 only) -> unbounded
        with pytest.raises(LPUnbounded):
            maximize([1], [[-1]], [0])

    def test_no_constraints_with_a_positive_objective_is_unbounded(self):
        with pytest.raises(LPUnbounded):
            maximize([1, 0], [], [])

    def test_no_constraints_with_nonpositive_objective_is_zero_at_origin(self):
        value, x = maximize([-1, 0], [], [])
        assert value == Fraction(0)
        assert x == [Fraction(0), Fraction(0)]

    def test_one_bounded_one_free_stays_unbounded(self):
        # max x + y s.t. x <= 5 (y unconstrained above) -> unbounded via y
        with pytest.raises(LPUnbounded):
            maximize([1, 1], [[1, 0]], [5])


class TestDegeneracyTerminates:
    def test_a_degenerate_problem_does_not_cycle(self):
        # a classic degenerate LP (b has a zero, several constraints tie); Bland's rule must terminate.
        value, x = maximize(
            [10, -57, -9, -24],
            [[Fraction(1, 2), Fraction(-11, 2), Fraction(-5, 2), 9],
             [Fraction(1, 2), Fraction(-3, 2), Fraction(-1, 2), 1],
             [1, 0, 0, 0]],
            [0, 0, 1],
        )
        assert value == Fraction(1)     # the known optimum of this textbook anti-cycling example
        assert all(isinstance(v, Fraction) for v in x)

    def test_all_zero_feasible_start_when_every_objective_coeff_is_nonpositive(self):
        value, x = maximize([-1, -2], [[1, 1]], [5])
        assert value == Fraction(0)
        assert x == [Fraction(0), Fraction(0)]


class TestContracts:
    def test_negative_b_is_refused(self):
        # a negative rhs would break the single-phase feasible start; refuse it rather than solve wrongly
        with pytest.raises(ValueError):
            maximize([1], [[1]], [-1])

    def test_shape_mismatch_is_refused(self):
        with pytest.raises(ValueError):
            maximize([1, 2], [[1]], [1])
        with pytest.raises(ValueError):
            maximize([1], [[1]], [1, 2])

    def test_float_coefficients_are_refused_for_exactness(self):
        with pytest.raises(TypeError):
            maximize([1.0], [[1]], [1])
        with pytest.raises(TypeError):
            maximize([1], [[1.0]], [1])
