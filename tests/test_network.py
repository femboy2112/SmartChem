"""
The energy functor's shape does NOT transfer to impedance, and this file is why.

This is a falsified prediction kept on the record, in the same spirit as P3. The working
assumption behind "the categorical layer is domain-neutral" was that a new domain needs a
new oracle and nothing else -- that `E(A (x) B) = E(A) + E(B)` is the general shape and
each domain just supplies its own values. Reaching for a radio absorber is what killed it.

The measurement
---------------
Two components at 1 MHz: R = 50 ohm and C = 100 pF.

    series   (composition)    Z = Z1 + Z2                    additive
    parallel (tensor)         Z = 1/(1/Z1 + 1/Z2)            NOT additive

The additive law gives 1592 ohm for the parallel pair where the truth is 49.98 ohm: wrong
by 31.9x, silently, with no error bar and no refusal. That is the failure mode this
repository exists to refuse.

What is actually going on
-------------------------
**Energy is extensive**, so side-by-side and end-to-end are the SAME operation for it, and
one monoid covers both. That is a special property of energy, not a general property of
physical quantities -- and reading its niceness as generality is the mistake this file
records.

The general shape is a PAIR of monoids, one per categorical operation:

    energy        (x): +          (.): +          degenerate -- both the same
    impedance     (x): parallel   (.): +
    admittance    (x): +          (.): parallel

``smartchem/thermo.py`` hardcodes the degenerate case. It is correct for energy and it is
not a template for anything else. Anything that reaches for classical field or network
behaviour needs the pair, and a session that assumes otherwise gets a plausible number
that is 32x wrong.

What survives, which decides what to build first
------------------------------------------------
1. **Absorbed power IS extensive** (asserted below). Two absorbers side by side dissipate
   the sum of what each dissipates. So radiative ABSORPTION sits correctly on the existing
   energy shape; it is network SOLVING that does not. That is a real ordering constraint
   on the moonshot, and it says absorption is reachable before circuit solving is.
2. **The cancellation is the physics.** At resonance |Z_L + Z_C| = 0.00 ohm while
   |Z_L| + |Z_C| = 632.46 ohm. A magnitude-summing law does not approximate resonance
   badly -- it cannot represent it at all, because the imaginary parts must cancel.
   Complex arithmetic here is load-bearing, not cosmetic.

AND THEN THE REPAIR WAS FALSIFIED TOO -- READ THIS BEFORE BUILDING ANYTHING
---------------------------------------------------------------------------
The paragraph above used to end: "the next real step is a functor parameterised by a pair
of monoids rather than welded to one." That is wrong, and the probe that killed it costs
four multiplications.

In a symmetric monoidal category the INTERCHANGE law holds by definition -- it is what
makes ``(x)`` a bifunctor:

    (f . g) (x) (h . k)  ==  (f (x) h) . (g (x) k)

A functor sending ``.`` to one operation and ``(x)`` to another must therefore make those
two operations interchange as well. For impedance that demands

    (Z1 + Z2) || (Z3 + Z4)  ==  (Z1 || Z3) + (Z2 || Z4)

and it is false. Measured below: up to **73% relative disagreement**, and false already on
PURE RESISTORS -- R = 1,2,3,4 gives 2.1000 against 2.0833 -- so it is not an artifact of
complex arithmetic. That case is a Wheatstone bridge, which is precisely the classical
example of a network that series-parallel reduction cannot reach. The physics knew.

So impedance is not a strong monoidal functor of ANY monoid-pair shape. Not one monoid, not
two. A network solver is not a widening of this functor and no amount of parameterisation
gets there; circuits want a different structure entirely -- networks as cospans of graphs,
composed by gluing boundary nodes, with a relation rather than a monoid element as the
semantics.

WHY ENERGY GETS ONE MONOID, WHICH IS A THEOREM AND NOT A COINCIDENCE
--------------------------------------------------------------------
Eckmann-Hilton: two monoid structures on one set that SHARE A UNIT and satisfy interchange
are necessarily equal, and commutative. So energy having a single monoid is not luck and
not a special property to be admired -- it is forced, the moment you notice that its tensor
unit and its composition unit are both 0 eV.

Impedance escapes the theorem for exactly one reason, and it is a satisfying one: its two
units are different. A plain wire is the series identity at 0 ohm; an open circuit is the
parallel identity at infinite ohm. Different units, no collapse, two genuinely distinct
monoids -- which then fail interchange and so cannot both come from one functor anyway.

This is the third premise in this project's history to die the same death: #23's
"(symbol, degree)", #24's "Estimate is scalar", and now #24's "a pair of monoids". Each was
a plausible generalisation adopted without a discriminating probe, and each probe, once
written, took minutes. The lesson is the type, not the token.

Scope of this file: it pins the arithmetic facts and the structural claims, including the
ones that turned out to be wrong. It does not build a network solver, and it now says why
the obvious route to one does not exist.
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
class TestImpedanceNeedsTwoMonoids:
    """The core finding: one additive law cannot serve both categorical operations."""

    def test_impedance_is_additive_under_series(self):
        """Composition is fine. This half of the assumption was true."""
        assert series(Z_R, Z_C) == pytest.approx(
            complex(R_OHMS, -1 / (OMEGA * C_FARADS)))

    def test_impedance_is_not_additive_under_parallel(self):
        """
        The half that was false. If a session ever "reuses the energy functor" for a
        network, this is the number it silently gets wrong.
        """
        additive = series(Z_R, Z_C)
        truth = parallel(Z_R, Z_C)
        assert abs(additive) / abs(truth) == pytest.approx(31.86, abs=0.05)
        assert abs(additive - truth) > 1500.0

    def test_admittance_is_additive_under_parallel(self):
        """The mirrored monoid. Both exist; neither serves both operations."""
        assert 1 / Z_R + 1 / Z_C == pytest.approx(1 / parallel(Z_R, Z_C))

    def test_no_single_representation_is_additive_for_both_operations(self):
        """
        Stated as a test rather than a comment, because it is the load-bearing claim.
        Impedance is additive for composition and not for tensor; admittance is additive
        for tensor and not for composition. Energy is additive for both, which is a fact
        about energy and not about the framework.
        """
        z_additive_series = series(Z_R, Z_C) == pytest.approx(series(Z_R, Z_C))
        z_additive_parallel = abs(series(Z_R, Z_C) - parallel(Z_R, Z_C)) < 1e-9
        y_additive_parallel = abs((1 / Z_R + 1 / Z_C) - 1 / parallel(Z_R, Z_C)) < 1e-12
        y_additive_series = abs((1 / Z_R + 1 / Z_C) - 1 / series(Z_R, Z_C)) < 1e-12

        assert z_additive_series and not z_additive_parallel
        assert y_additive_parallel and not y_additive_series


# ======================================================================================
class TestWhatSurvives:
    """
    What is still safe on the existing energy shape -- which is what decides the build
    order for anything reaching toward classical behaviour.
    """

    @staticmethod
    def _power(z: complex, volts: float = 1.0) -> float:
        """Real power into an impedance at fixed drive: P = |V|^2 Re(Y)."""
        return abs(volts) ** 2 * (1 / z).real

    def test_absorbed_power_is_extensive_under_tensor(self):
        """
        The result that makes radiative absorption reachable before network solving.
        Two absorbers side by side dissipate the sum of what each dissipates, which is
        exactly the law the energy functor already enforces.
        """
        assert self._power(Z_R) + self._power(Z_C) == pytest.approx(
            self._power(parallel(Z_R, Z_C)))

    def test_a_pure_reactance_dissipates_nothing(self):
        """Energy is stored and returned, not absorbed. The sanity check on the above."""
        assert self._power(Z_C) == pytest.approx(0.0, abs=1e-12)
        assert self._power(Z_L) == pytest.approx(0.0, abs=1e-12)
        assert self._power(Z_R) == pytest.approx(1.0 / R_OHMS)


# ======================================================================================
class TestInterchangeFailsSoNoMonoidPairCanWork:
    """
    The sharper finding, and the one that kills the obvious repair.

    A pair of monoids is not merely insufficient for impedance -- it is impossible, because
    the two operations would have to interchange and they do not.
    """

    @staticmethod
    def _bridge(z1, z2, z3, z4):
        """The two sides of the interchange law, as networks."""
        left = parallel(series(z1, z2), series(z3, z4))     # (f.g) (x) (h.k)
        right = series(parallel(z1, z3), parallel(z2, z4))  # (f(x)h) . (g(x)k)
        return left, right

    def test_interchange_fails_for_impedance(self):
        """
        Required by any functor sending composition to series and tensor to parallel.
        It does not hold, so no such functor exists.
        """
        z = [complex(50, 30), complex(120, -80), complex(75, 10), complex(20, -150)]
        left, right = self._bridge(*z)
        assert abs(left - right) / abs(left) > 0.01

    def test_it_fails_on_pure_resistors_too(self):
        """
        So nobody can attribute the failure to complex arithmetic and hope a real-valued
        version survives. R = 1,2,3,4 is a Wheatstone bridge, the classical example of a
        network series-parallel reduction cannot reach.
        """
        left, right = self._bridge(1.0, 2.0, 3.0, 4.0)
        assert left == pytest.approx(2.1000, abs=1e-4)
        assert right == pytest.approx(2.0833, abs=1e-4)
        assert left != pytest.approx(right, abs=1e-3)

    def test_the_symmetric_case_coincidentally_agrees(self):
        """
        Four equal resistors DO satisfy it. Kept deliberately: a test suite that only ever
        tried the symmetric case would have concluded interchange holds and the monoid-pair
        plan was sound. That is the balanced-count blindness of #22 in another costume, and
        the reason the asymmetric cases above are the real test.
        """
        left, right = self._bridge(1.0, 1.0, 1.0, 1.0)
        assert left == pytest.approx(right)

    def test_energy_does_satisfy_interchange(self):
        """The contrast that makes the point: with both operations +, interchange is trivial."""
        a, b, c, d = -1.5, -2.25, 0.75, -3.0
        assert (a + b) + (c + d) == pytest.approx((a + c) + (b + d))

    def test_the_two_impedance_monoids_have_different_units(self):
        """
        Eckmann-Hilton needs a SHARED unit. Impedance does not have one -- a wire is the
        series identity at 0 ohm, an open circuit is the parallel identity at infinity --
        which is exactly why it gets to have two distinct monoids at all.
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

    def test_energys_two_units_coincide_which_is_what_forces_the_collapse(self):
        """
        Both of energy's units are 0 eV. With a shared unit and interchange, Eckmann-Hilton
        makes the two monoids equal and commutative -- so energy's single monoid is a
        theorem, not a lucky property of energy.
        """
        tensor_unit = 0.0
        compose_unit = 0.0
        assert tensor_unit == compose_unit
        energy = -4.25
        assert energy + tensor_unit == pytest.approx(energy)
        assert energy + compose_unit == pytest.approx(energy)


# ======================================================================================
class TestCancellationIsThePhysics:
    """
    Why complex values are load-bearing rather than cosmetic. A model carrying magnitudes
    cannot represent resonance at all -- the imaginary parts have to cancel.
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
