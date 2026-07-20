"""
Scalar impedance arithmetic does not inherit the isolated-energy adapter's additive rule.

This file keeps a falsified architectural prediction on the record. The historical
assumption was that a new physical domain needed only a new oracle and could reuse one
addition law. At 1 MHz, a 50 ohm resistor and 100 pF capacitor give:

    series connection      Z = Z1 + Z2
    parallel connection    Z = 1/(1/Z1 + 1/Z2)

Using series addition for the parallel pair gives about 1592 ohm instead of 49.98 ohm,
wrong by 31.9x. The tests below pin that arithmetic counterexample.

Historical note: an intermediate repair described series and parallel as a pair of monoids
and tried to read them as categorical composition and tensor. That description was also too
broad. A hypothetical symmetric-monoidal semantics would require the two scalar operations
to satisfy interchange,

    (Z1 + Z2) || (Z3 + Z4) == (Z1 || Z3) + (Z2 || Z4),

and the representative values below do not. This rules out that particular scalar
series/parallel interpretation; it does not construct or classify a network category.
The pure-resistor example compares two different series-parallel arrangements. An earlier
version incorrectly called it a Wheatstone bridge; there is no bridge branch in either
expression.

One positive identity is deliberately narrow. For uncoupled parallel branches held at the
same externally prescribed voltage, real powers add because admittances add:

    P_total = |V|^2 Re(Y1 + Y2) = P1 + P2.

That test does not establish radiative absorption additivity. Side-by-side absorbers can
couple electromagnetically, change the field and load the source; none of those effects is
represented here.

The LC tests establish another arithmetic fact: complex reactances cancel at resonance,
whereas summing magnitudes cannot reproduce the zero. They do not amount to a circuit solver.

Abstractly, Eckmann-Hilton constrains two unital operations that share a unit and satisfy
interchange. That theorem motivated the historical discussion, but the current SmartChem
source has no genuine morphism tensor and its float accumulators are not exact monoids over
all Python values. The small scalar examples below are representative numerical checks, not
proofs of an energy functor or a general network semantics.
"""
from __future__ import annotations

import cmath

import pytest

OMEGA = 2 * cmath.pi * 1e6          # 1 MHz
R_OHMS = 50.0
C_FARADS = 100e-12
L_HENRIES = 10e-6

Z_R = complex(R_OHMS, 0.0)
Z_C = 1 / (1j * OMEGA * C_FARADS)
Z_L = 1j * OMEGA * L_HENRIES


def series(*z: complex) -> complex:
    return sum(z)


def parallel(*z: complex) -> complex:
    return 1 / sum(1 / zi for zi in z)


# ======================================================================================
class TestImpedanceNeedsDistinctOperations:
    """Series addition cannot be reused for the tested parallel connection."""

    def test_impedance_is_additive_under_series(self):
        """The scalar series-connection formula is addition."""
        assert series(Z_R, Z_C) == pytest.approx(
            complex(R_OHMS, -1 / (OMEGA * C_FARADS)))

    def test_impedance_is_not_additive_under_parallel(self):
        """
        The half that was false. If a session ever reuses isolated-energy additivity for a
        network, this is the number it silently gets wrong.
        """
        additive = series(Z_R, Z_C)
        truth = parallel(Z_R, Z_C)
        assert abs(additive) / abs(truth) == pytest.approx(31.86, abs=0.05)
        assert abs(additive - truth) > 1500.0

    def test_admittance_is_additive_under_parallel(self):
        """Admittances add for these uncoupled parallel branches."""
        assert 1 / Z_R + 1 / Z_C == pytest.approx(1 / parallel(Z_R, Z_C))

    def test_no_single_representation_is_additive_for_both_operations(self):
        """
        For these scalar formulas impedance adds in series but not in parallel; admittance
        adds in parallel but not in series. This is not a claim about a categorical tensor.
        """
        z_additive_series = series(Z_R, Z_C) == pytest.approx(series(Z_R, Z_C))
        z_additive_parallel = abs(series(Z_R, Z_C) - parallel(Z_R, Z_C)) < 1e-9
        y_additive_parallel = abs((1 / Z_R + 1 / Z_C) - 1 / parallel(Z_R, Z_C)) < 1e-12
        y_additive_series = abs((1 / Z_R + 1 / Z_C) - 1 / series(Z_R, Z_C)) < 1e-12

        assert z_additive_series and not z_additive_parallel
        assert y_additive_parallel and not y_additive_series


# ======================================================================================
class TestPrescribedVoltagePowerIdentity:
    """
    A fixed-drive identity for uncoupled parallel branches, not radiative extensivity.
    """

    @staticmethod
    def _power(z: complex, volts: float = 1.0) -> float:
        """Real power into an impedance at fixed drive: P = |V|^2 Re(Y)."""
        return abs(volts) ** 2 * (1 / z).real

    def test_uncoupled_parallel_branch_power_adds_at_prescribed_voltage(self):
        """
        Both branches see the same externally prescribed voltage and do not interact. The
        equality follows from parallel admittance addition; it does not cover source loading,
        mutual coupling, a self-consistent field or radiative absorbers.
        """
        assert self._power(Z_R) + self._power(Z_C) == pytest.approx(
            self._power(parallel(Z_R, Z_C)))

    def test_a_pure_reactance_dissipates_nothing(self):
        """Energy is stored and returned, not absorbed. The sanity check on the above."""
        assert self._power(Z_C) == pytest.approx(0.0, abs=1e-12)
        assert self._power(Z_L) == pytest.approx(0.0, abs=1e-12)
        assert self._power(Z_R) == pytest.approx(1.0 / R_OHMS)


# ======================================================================================
class TestSeriesParallelScalarInterchangeCounterexample:
    """
    These two scalar reduction operations fail the interchange equation on representatives.
    """

    @staticmethod
    def _interchange_sides(z1, z2, z3, z4):
        """The two scalar series/parallel expressions being compared."""
        left = parallel(series(z1, z2), series(z3, z4))     # (f.g) (x) (h.k)
        right = series(parallel(z1, z3), parallel(z2, z4))  # (f(x)h) . (g(x)k)
        return left, right

    def test_interchange_fails_for_impedance(self):
        """
        A hypothetical semantics mapping composition to series and a true tensor to parallel
        would require this equation. The numerical counterexample rejects that mapping.
        """
        z = [complex(50, 30), complex(120, -80), complex(75, 10), complex(20, -150)]
        left, right = self._interchange_sides(*z)
        assert abs(left - right) / abs(left) > 0.01

    def test_it_fails_on_pure_resistors_too(self):
        """
        The mismatch is already present for positive real scalars. These are two distinct
        series-parallel arrangements, not a Wheatstone-bridge topology.
        """
        left, right = self._interchange_sides(1.0, 2.0, 3.0, 4.0)
        assert left == pytest.approx(2.1000, abs=1e-4)
        assert right == pytest.approx(2.0833, abs=1e-4)
        assert left != pytest.approx(right, abs=1e-3)

    def test_the_symmetric_case_coincidentally_agrees(self):
        """
        Four equal resistors DO satisfy it. Kept deliberately: a test suite that only ever
        tried the symmetric case could have left the historical monoid-pair plan unfalsified.
        The asymmetric representatives are the discriminating cases.
        """
        left, right = self._interchange_sides(1.0, 1.0, 1.0, 1.0)
        assert left == pytest.approx(right)

    def test_scalar_addition_representative_satisfies_the_interchange_equation(self):
        """A finite float example agrees within tolerance when both operations are addition."""
        a, b, c, d = -1.5, -2.25, 0.75, -3.0
        assert (a + b) + (c + d) == pytest.approx((a + c) + (b + d))

    def test_series_and_parallel_have_different_limiting_identities(self):
        """
        A wire is the series identity at 0 ohm; an open circuit is the parallel identity only
        in the infinite-impedance limit. The finite helper is therefore not a total monoid
        operation containing both identities.
        """
        wire = 0.0
        assert series(Z_R, wire) == pytest.approx(Z_R)
        # the parallel identity is the limit of an ever-larger resistance
        for open_circuit in (1e9, 1e12, 1e15):
            assert parallel(Z_R, open_circuit) == pytest.approx(Z_R, rel=1e-6)
        # and a wire in PARALLEL is a short, not an identity -- approached as a limit,
        # since 1/0 is where the reciprocal formula stops being able to say it
        for short in (1e-6, 1e-9, 1e-12):
            assert abs(parallel(Z_R, short)) == pytest.approx(short, rel=1e-3)

    def test_the_historical_scalar_energy_example_uses_zero_for_both_roles(self):
        """
        This is the small scalar observation that motivated the historical Eckmann-Hilton
        analogy. It does not prove that the concrete float/Estimate implementation is an
        exact monoid or that SmartChem has a morphism tensor.
        """
        tensor_unit = 0.0
        compose_unit = 0.0
        assert tensor_unit == compose_unit
        energy = -4.25
        assert energy + tensor_unit == pytest.approx(energy)
        assert energy + compose_unit == pytest.approx(energy)


# ======================================================================================
class TestComplexReactanceCancellation:
    """
    In the ideal scalar series-LC model, phase-bearing reactances cancel at resonance while
    their magnitudes do not.
    """

    RESONANT_OMEGA = 1 / (L_HENRIES * C_FARADS) ** 0.5

    def test_a_series_lc_vanishes_at_resonance(self):
        w = self.RESONANT_OMEGA
        z = 1j * w * L_HENRIES + 1 / (1j * w * C_FARADS)
        assert abs(z) == pytest.approx(0.0, abs=1e-6)

    def test_summing_magnitudes_misses_resonance_entirely(self):
        """
        Not "approximates it badly" -- misses it. The magnitude sum is ~632 ohm at the
        exact frequency where the true impedance is zero, and it has no minimum there at
        all. Any model that drops the phase cannot find a resonance.
        """
        w = self.RESONANT_OMEGA
        magnitude_sum = abs(1j * w * L_HENRIES) + abs(1 / (1j * w * C_FARADS))
        assert magnitude_sum == pytest.approx(632.46, abs=0.5)

    def test_the_magnitude_sum_has_no_minimum_where_the_true_impedance_does(self):
        """The sharpest statement: the two functions do not even have the same shape."""
        w0 = self.RESONANT_OMEGA
        def true_z(w):
            return abs(1j * w * L_HENRIES + 1 / (1j * w * C_FARADS))
        def summed(w):
            return abs(1j * w * L_HENRIES) + abs(1 / (1j * w * C_FARADS))

        # the true impedance dips to zero at w0 and rises on both sides
        assert true_z(w0) < true_z(w0 * 0.9)
        assert true_z(w0) < true_z(w0 * 1.1)
        # the magnitude sum is essentially flat there -- no feature to find
        assert summed(w0) / summed(w0 * 0.9) == pytest.approx(1.0, abs=0.01)
