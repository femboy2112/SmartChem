"""
The energy functor laws.

``smartchem.thermo`` claims to be a strong monoidal functor from the category of chemical
configurations to the additive reals. This file checks that claim, and checks the thing
underneath it that makes the categorical framing load-bearing rather than decorative:

**conservation is what licenses the subtraction.**

Total energy has an arbitrary zero fixed by atom content. ``E(B) - E(A)`` is physically
meaningful only when A and B contain the same atoms -- which is exactly what
``Reaction.__post_init__`` enforces. Without that guarantee the subtraction would silently
compare two different reference points and produce a confident, meaningless number.

A ``StubOracle`` is used rather than PySCF: these are *algebraic* laws, and they must hold
for any oracle obeying the contract. Checking them against a real quantum chemistry backend
would be slower, flakier, and would test the backend rather than the structure.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from smartchem.category import (
    Bond, Config, Molecule, Reaction, UNIT, identity, reaction_residue, tensor_obj,
)
from smartchem.oracle.base import BaseOracle, Estimate
from smartchem.thermo import (
    bonding_energy,
    configuration_energy,
    favourability,
    is_exothermic,
    reaction_energy,
)


# ======================================================================================
# A stub obeying the oracle contract: one consistent, arbitrary zero.
# ======================================================================================
class StubOracle(BaseOracle):
    """
    Deterministic fake with a deliberately absurd per-atom offset.

    The offset is the point. Each element carries a large arbitrary constant, exactly as a
    real total-energy oracle does (PySCF puts CO near -3074 eV). If any law below holds
    only because the offsets happen to be small, these numbers will expose it.
    """

    name = "stub"
    nominal_accuracy_ev = 0.1

    #: absurd, element-specific, and nothing cancels them except conservation
    OFFSET = {"H": -13.6, "C": -1029.8, "O": -2043.2, "N": -1485.3,
              "Na": -4412.0, "Cl": -12530.7, "S": -10831.4, "Fe": -34567.1}
    #: energy released per unit of bond order
    BOND = 2.5

    def energy(self, molecule: Molecule) -> Estimate | None:
        if any(s not in self.OFFSET for s in molecule.atoms):
            return None
        total = sum(self.OFFSET[s] for s in molecule.atoms)
        total -= self.BOND * sum(b.order for b in molecule.bonds)
        total += 5.0 * molecule.charge
        return Estimate(total, 0.05, self.name, 0.0, str(molecule.atoms))


class RefusingOracle(BaseOracle):
    """Declines everything. Used to check refusal propagates rather than becoming zero."""
    name = "refusing"
    nominal_accuracy_ev = float("inf")

    def energy(self, molecule: Molecule) -> Estimate | None:
        return None


ORACLE = StubOracle()


# ======================================================================================
# strategies
# ======================================================================================
ELEMENTS = sorted(StubOracle.OFFSET)
atoms_st = st.sampled_from(ELEMENTS)


@st.composite
def molecules(draw):
    """A connected molecule of 1-3 atoms with a random bond order."""
    n = draw(st.integers(min_value=1, max_value=3))
    syms = tuple(draw(st.lists(atoms_st, min_size=n, max_size=n)))
    if n == 1:
        return Molecule.atom(syms[0])
    order = draw(st.integers(min_value=1, max_value=3))
    if n == 2:
        return Molecule.diatomic(syms[0], syms[1], order=order)
    return Molecule(syms, frozenset({Bond(0, 1, order), Bond(1, 2)}))


@st.composite
def configs(draw):
    return Config.of(*draw(st.lists(molecules(), min_size=0, max_size=3)))


# ======================================================================================
# The object half: E is monoidal
# ======================================================================================
class TestMonoidalFunctor:
    def test_unit_has_zero_energy(self):
        """``E(I) = 0`` -- the empty vessel. A real value, not a refusal."""
        est = configuration_energy(UNIT, ORACLE)
        assert est is not None
        assert est.value_ev == 0.0

    @settings(max_examples=150, deadline=None)
    @given(configs(), configs())
    def test_tensor_maps_to_addition(self, a: Config, b: Config):
        """``E(A (x) B) = E(A) + E(B)`` -- the monoidal law."""
        ea, eb = configuration_energy(a, ORACLE), configuration_energy(b, ORACLE)
        both = configuration_energy(tensor_obj(a, b), ORACLE)
        assert ea is not None and eb is not None and both is not None
        assert both.value_ev == pytest.approx(ea.value_ev + eb.value_ev, abs=1e-9)

    @settings(max_examples=100, deadline=None)
    @given(configs())
    def test_unit_law(self, a: Config):
        """``E(A (x) I) = E(A)``."""
        left = configuration_energy(tensor_obj(a, UNIT), ORACLE)
        right = configuration_energy(a, ORACLE)
        assert left.value_ev == pytest.approx(right.value_ev, abs=1e-9)

    @settings(max_examples=100, deadline=None)
    @given(configs())
    def test_uncertainty_accumulates_with_the_value(self, a: Config):
        """The certificate has to survive the functor, not just the central value."""
        est = configuration_energy(a, ORACLE)
        assert est.uncertainty_ev >= 0.0
        if len(a.species) > 1:
            assert est.uncertainty_ev > 0.0


# ======================================================================================
# The morphism half: dE is functorial
# ======================================================================================
def _h2():
    return Config.atoms("H", "H"), Config.of(Molecule.diatomic("H", "H"))


class TestFunctoriality:
    def test_identity_has_zero_energy(self):
        """``dE(id_A) = 0``."""
        free, _ = _h2()
        est = reaction_energy(identity(free), ORACLE)
        assert est is not None
        assert est.value_ev == pytest.approx(0.0, abs=1e-12)

    def test_composition_maps_to_addition(self):
        """``dE(g . f) = dE(f) + dE(g)`` -- energy is a path integral, by law."""
        free, bound = _h2()
        f = Reaction(free, bound, "associate")
        g = Reaction(bound, free, "dissociate")
        ef = reaction_energy(f, ORACLE).value_ev
        eg = reaction_energy(g, ORACLE).value_ev
        egf = reaction_energy(f.then(g), ORACLE).value_ev
        assert egf == pytest.approx(ef + eg, abs=1e-9)

    def test_a_round_trip_costs_nothing(self):
        """Forming then breaking the same bond must return exactly to zero."""
        free, bound = _h2()
        loop = Reaction(free, bound, "associate").then(Reaction(bound, free, "dissociate"))
        assert reaction_energy(loop, ORACLE).value_ev == pytest.approx(0.0, abs=1e-9)

    def test_tensor_of_morphisms_maps_to_addition(self):
        """``dE(f (x) g) = dE(f) + dE(g)``."""
        free_h, bound_h = _h2()
        free_n = Config.atoms("N", "N")
        bound_n = Config.of(Molecule.diatomic("N", "N", order=3))
        f = Reaction(free_h, bound_h, "make H2")
        g = Reaction(free_n, bound_n, "make N2")
        ef = reaction_energy(f, ORACLE).value_ev
        eg = reaction_energy(g, ORACLE).value_ev
        both = reaction_energy(f.tensor(g), ORACLE).value_ev
        assert both == pytest.approx(ef + eg, abs=1e-9)

    @settings(max_examples=50, deadline=None)
    @given(st.integers(min_value=2, max_value=6))
    def test_long_chains_stay_additive(self, n: int):
        """Functoriality has to survive depth, not just one composition."""
        free, bound = _h2()
        steps, chain, expected = [], None, 0.0
        for i in range(n):
            step = (Reaction(free, bound, f"a{i}") if i % 2 == 0
                    else Reaction(bound, free, f"d{i}"))
            steps.append(step)
            expected += reaction_energy(step, ORACLE).value_ev
            chain = step if chain is None else chain.then(step)
        assert reaction_energy(chain, ORACLE).value_ev == pytest.approx(expected, abs=1e-9)


# ======================================================================================
# The load-bearing claim: conservation is what makes the subtraction meaningful
# ======================================================================================
class TestConservationLicensesSubtraction:
    """
    The heart of it. ``E`` carries an arbitrary per-atom offset. ``dE`` is only physical
    because that offset cancels, and it cancels only because ``dom`` and ``cod`` hold the
    same atoms -- which the category enforces at construction.
    """

    def test_the_offsets_are_enormous(self):
        """Establish the premise: absolute energies are dominated by arbitrary offsets."""
        co = configuration_energy(Config.of(Molecule.diatomic("C", "O", order=3)), ORACLE)
        assert abs(co.value_ev) > 3000.0, "the arbitrary zero must dwarf the chemistry"

    def test_yet_the_reaction_energy_is_small_and_physical(self):
        """The same offsets cancel exactly, leaving only the bonding term."""
        free = Config.atoms("C", "O")
        bound = Config.of(Molecule.diatomic("C", "O", order=3))
        est = reaction_energy(Reaction(free, bound), ORACLE)
        # three units of bond order at 2.5 eV each, released
        assert est.value_ev == pytest.approx(-7.5, abs=1e-9)

    def test_offsets_cancel_regardless_of_their_size(self):
        """
        Shift every offset by a huge constant. Absolute energies move; every reaction
        energy must not move at all. This is the invariance conservation buys.
        """
        free = Config.atoms("Na", "Cl")
        bound = Config.of(Molecule.diatomic("Na", "Cl"))
        rxn = Reaction(free, bound)
        before = reaction_energy(rxn, ORACLE).value_ev

        shifted = StubOracle()
        shifted.OFFSET = {k: v - 1_000_000.0 for k, v in StubOracle.OFFSET.items()}
        after = reaction_energy(rxn, shifted).value_ev

        assert configuration_energy(bound, shifted).value_ev < -1_000_000.0
        assert after == pytest.approx(before, abs=1e-6), (
            "a change of energy zero altered a reaction energy; the offsets are not "
            "cancelling, which means conservation is not doing the work it is claimed to"
        )

    def test_a_non_conserving_reaction_cannot_be_built_to_be_asked_about(self):
        """
        The guarantee is structural, not a runtime check inside thermo. There is no way to
        hand ``reaction_energy`` a morphism whose atom sets differ, because such a morphism
        is unconstructible.
        """
        from smartchem.category import ConservationError
        with pytest.raises(ConservationError):
            Reaction(Config.atoms("Fe", "O", "Cl"),
                     Config.of(Molecule.diatomic("Fe", "O")))


# ======================================================================================
# Bond order is now priced, because the object carries it
# ======================================================================================
class TestBondOrderIsPriced:
    """
    The old interface asked the oracle about an atom *pair*, which carries no order, so a
    C-C single bond and a C=C double bond were indistinguishable. The primitive is now a
    species, and a species carries its topology.
    """

    def test_single_and_double_bonds_differ(self):
        single = Config.of(Molecule.diatomic("C", "C", order=1))
        double = Config.of(Molecule.diatomic("C", "C", order=2))
        e1 = configuration_energy(single, ORACLE).value_ev
        e2 = configuration_energy(double, ORACLE).value_ev
        assert e1 != e2, "bond order is in the object; it must reach the oracle"
        assert e2 < e1, "a higher bond order must be more strongly bound"

    def test_the_order_reaches_the_reaction_energy(self):
        free = Config.atoms("C", "C")
        make_single = Reaction(free, Config.of(Molecule.diatomic("C", "C", order=1)))
        make_double = Reaction(free, Config.of(Molecule.diatomic("C", "C", order=2)))
        assert (reaction_energy(make_double, ORACLE).value_ev
                < reaction_energy(make_single, ORACLE).value_ev)


# ======================================================================================
# Refusal still propagates rather than degrading into a number
# ======================================================================================
class TestRefusalPropagates:
    def test_configuration_declines_when_a_species_cannot_be_priced(self):
        assert configuration_energy(Config.atoms("H", "H"), RefusingOracle()) is None

    def test_partial_pricing_refuses_the_whole_configuration(self):
        """One unpriceable species must not be silently skipped."""
        mixed = Config.of(Molecule.diatomic("H", "H"), Molecule.atom("Xx"))
        assert configuration_energy(mixed, ORACLE) is None

    def test_reaction_declines_rather_than_returning_zero(self):
        free, bound = _h2()
        assert reaction_energy(Reaction(free, bound), RefusingOracle()) is None

    def test_is_exothermic_returns_none_not_false(self):
        free, bound = _h2()
        assert is_exothermic(Reaction(free, bound), RefusingOracle()) is None

    def test_favourability_says_unknown(self):
        free, bound = _h2()
        assert "UNKNOWN" in favourability(Reaction(free, bound), RefusingOracle())


# ======================================================================================
# Derived quantities
# ======================================================================================
class TestBondingEnergy:
    def test_bound_species_are_negative(self):
        bound = Config.of(Molecule.diatomic("H", "H"))
        assert bonding_energy(bound, ORACLE).value_ev < 0.0

    def test_free_atoms_have_zero_bonding_energy(self):
        est = bonding_energy(Config.atoms("H", "H"), ORACLE)
        assert est.value_ev == pytest.approx(0.0, abs=1e-9)

    def test_it_matches_the_reaction_from_free_atoms(self):
        """bonding_energy is dE of a morphism, so it must agree with reaction_energy."""
        free = Config.atoms("N", "N")
        bound = Config.of(Molecule.diatomic("N", "N", order=3))
        assert (bonding_energy(bound, ORACLE).value_ev
                == pytest.approx(reaction_energy(Reaction(free, bound), ORACLE).value_ev,
                                 abs=1e-9))


# ======================================================================================
# Systematic corrections cancel; random errors do not
# ======================================================================================
class TestSystematicVsRandomError:
    """
    ``Estimate`` carries two different kinds of error and must not conflate them.

    ``uncertainty_ev`` is random: it combines in quadrature and never cancels.
    ``extrapolation_ev`` is a signed systematic model correction: it combines additively
    and DOES cancel between the two sides of a conserving difference, exactly as the
    arbitrary energy zero does.

    Getting this wrong is not academic. Treating the per-species CBS correction as random
    and combining it in quadrature produced +/-1.4 eV error bars on a method whose measured
    accuracy is 0.04 eV -- a 35x inflation, caused entirely by discarding a cancellation of
    about 97%.
    """

    def test_random_uncertainty_grows_in_quadrature(self):
        a = Estimate(1.0, 0.3, "m")
        b = Estimate(2.0, 0.4, "m")
        assert (a + b).uncertainty_ev == pytest.approx(0.5)

    def test_systematic_correction_cancels_in_a_difference(self):
        """Two species with the same correction leave nothing behind when subtracted."""
        a = Estimate(10.0, 0.04, "m", extrapolation_ev=1.37)
        b = Estimate(3.0, 0.04, "m", extrapolation_ev=1.37)
        assert (a - b).extrapolation_ev == pytest.approx(0.0)

    def test_random_uncertainty_does_not_cancel_in_a_difference(self):
        a = Estimate(10.0, 0.3, "m")
        b = Estimate(3.0, 0.4, "m")
        assert (a - b).uncertainty_ev == pytest.approx(0.5)

    def test_the_bar_widens_only_to_what_survives_cancellation(self):
        residual = Estimate(7.0, 0.04, "m", extrapolation_ev=0.13).with_honest_uncertainty()
        assert residual.uncertainty_ev == pytest.approx(0.13)

    def test_a_converged_result_keeps_its_tight_bar(self):
        """No widening when the extrapolation barely moved anything."""
        tight = Estimate(4.478, 0.041, "m", extrapolation_ev=0.001).with_honest_uncertainty()
        assert tight.uncertainty_ev == pytest.approx(0.041)

    def test_widening_never_narrows(self):
        """with_honest_uncertainty is a floor, never a replacement."""
        wide = Estimate(1.0, 2.0, "m", extrapolation_ev=0.1).with_honest_uncertainty()
        assert wide.uncertainty_ev == pytest.approx(2.0)

    def test_a_large_surviving_correction_is_reported_not_hidden(self):
        """
        The NaCl case. cbs(TZ,QZ) lands 3.38 kcal/mol out while plain cc-pVQZ lands 0.39
        out -- the extrapolation degraded a good answer. Reporting that with the tier's
        nominal +/-0.041 eV would be the oracle inventing confidence it has not got.
        """
        nacl = Estimate(4.3806, 0.041, "CCSD(T)/cbs(TZ,QZ)",
                        extrapolation_ev=0.1299).with_honest_uncertainty()
        assert nacl.uncertainty_ev > 3 * 0.041
        assert abs(nacl.value_ev - 4.234) < 1.5 * nacl.uncertainty_ev, (
            "the widened bar must actually cover the experimental value"
        )
        assert "widened" in nacl.notes, "a widened bar must say why"


# ======================================================================================
# Spectator cancellation: the category deciding what NOT to compute
# ======================================================================================
class CountingOracle(StubOracle):
    """StubOracle that records which species it was asked to price."""

    name = "counting"

    def __init__(self):
        self.asked: list[tuple[str, ...]] = []

    def energy(self, molecule: Molecule) -> Estimate | None:
        self.asked.append(molecule.atoms)
        return super().energy(molecule)


class WideSpectatorOracle(StubOracle):
    """
    Prices Fe with a huge uncertainty and everything else tightly.

    Fe is the stand-in for the realistic case: the catalyst is the biggest, least
    well-known species in the vessel, and it is exactly the one that cancels.
    """

    name = "wide-spectator"

    def energy(self, molecule: Molecule) -> Estimate | None:
        est = super().energy(molecule)
        if est is not None and "Fe" in molecule.atoms:
            return Estimate(est.value_ev, 5.0, self.name, est.seconds, est.notes)
        return est


def _n2_from_atoms(*spectators: Molecule) -> Reaction:
    """2 N -> N2, optionally with unchanging spectators on both sides."""
    n, n2 = Molecule.atom("N"), Molecule.diatomic("N", "N", order=3)
    return Reaction(Config.of(n, n, *spectators), Config.of(n2, *spectators))


class TestSpectatorsAreCancelledStructurally:
    """
    A species present unchanged on both sides of a morphism contributes exactly zero to
    dE, by the monoidal law. The category can see that before any oracle runs, so the
    species is never priced.

    This is the "prune by type ahead of the expensive layer" claim applied to the energy
    itself, and unlike the basis-set policy it is exact rather than empirical: it does not
    approximate the answer, it declines to compute a number that provably cannot move it.
    """

    def test_a_spectator_is_never_priced(self):
        bare, withcat = CountingOracle(), CountingOracle()
        reaction_energy(_n2_from_atoms(), bare)
        reaction_energy(_n2_from_atoms(Molecule.atom("Fe")), withcat)
        assert ("Fe",) not in withcat.asked, "the catalyst was priced despite cancelling"
        assert withcat.asked == bare.asked, "adding a spectator changed the work done"

    def test_a_spectator_does_not_change_the_value(self):
        plain = reaction_energy(_n2_from_atoms(), ORACLE)
        caged = reaction_energy(_n2_from_atoms(Molecule.atom("Fe")), ORACLE)
        assert caged.value_ev == plain.value_ev, "bit-identical, not merely close"

    def test_a_spectator_does_not_widen_the_error_bar(self):
        """
        The rigor half, and the sharper of the two claims.

        Quadrature is valid only for *independent* errors. A spectator's energy is not two
        independent samples -- it is one number appearing twice, minus itself. Summing both
        sides before subtracting adds 2*u(Fe)^2 of variance that physically cancels to
        zero, reporting an interval too wide by a factor that grows with the spectator.
        """
        oracle = WideSpectatorOracle()
        plain = reaction_energy(_n2_from_atoms(), oracle)
        caged = reaction_energy(_n2_from_atoms(Molecule.atom("Fe")), oracle)
        assert caged.uncertainty_ev == pytest.approx(plain.uncertainty_ev)
        # and the fiction it avoids is not a rounding detail: on this reaction the naive
        # bar is 7.0716 eV against a true 0.0866, a factor of ~82, and it grows without
        # bound as the spectator gets larger.
        naive = (2 * 5.0**2 + plain.uncertainty_ev**2) ** 0.5
        assert naive > 50 * plain.uncertainty_ev

    def test_more_spectators_cost_nothing_extra(self):
        oracle = WideSpectatorOracle()
        one = reaction_energy(_n2_from_atoms(Molecule.atom("Fe")), oracle)
        many = reaction_energy(
            _n2_from_atoms(*(Molecule.atom("Fe"),) * 5), oracle)
        assert many.value_ev == one.value_ev
        assert many.uncertainty_ev == pytest.approx(one.uncertainty_ev)

    def test_an_unpriceable_spectator_does_not_block_the_answer(self):
        """
        A capability increase, not merely a saving. Refusing because an *irrelevant*
        species is unknown would be over-refusal: the answer does not depend on it.
        """
        unknown = Molecule.atom("Xx")           # absent from StubOracle.OFFSET
        assert ORACLE.energy(unknown) is None
        est = reaction_energy(_n2_from_atoms(unknown), ORACLE)
        assert est is not None, "an unpriceable spectator blocked a computable reaction"
        assert est.value_ev == reaction_energy(_n2_from_atoms(), ORACLE).value_ev

    def test_a_participating_species_still_blocks(self):
        """The saving must not become a licence to skip species that actually change."""
        unknown = Molecule.atom("Xx")
        rxn = Reaction(Config.of(unknown, Molecule.atom("N")),
                       Config.of(Molecule.diatomic("Xx", "N")))
        assert reaction_energy(rxn, ORACLE) is None

    def test_identity_has_empty_residue_and_exactly_zero_energy(self):
        obj = Config.of(Molecule.diatomic("N", "N", order=3), Molecule.atom("Fe"))
        left, right = reaction_residue(identity(obj))
        assert left == UNIT and right == UNIT
        oracle = CountingOracle()
        est = reaction_energy(identity(obj), oracle)
        assert est.value_ev == 0.0
        assert oracle.asked == [], "an identity morphism priced something"

    def test_residue_is_still_a_conserving_pair(self):
        """Removing the same multiset from both sides cannot unbalance the equation."""
        left, right = reaction_residue(_n2_from_atoms(Molecule.atom("Fe")))
        assert left.formula == right.formula
        assert left.charge == right.charge

    @settings(max_examples=50, deadline=None)
    @given(spectator=molecules())
    def test_any_spectator_leaves_the_answer_bit_identical(self, spectator):
        plain = reaction_energy(_n2_from_atoms(), ORACLE)
        caged = reaction_energy(_n2_from_atoms(spectator), ORACLE)
        assert caged is not None
        assert caged.value_ev == plain.value_ev
        assert caged.uncertainty_ev == pytest.approx(plain.uncertainty_ev)


# ======================================================================================
# The codomain is a monoid, and that is what makes the fold well defined
# ======================================================================================
class TestEstimateIsAMonoid:
    """
    ``E`` is usually described here as a functor into ``(R, +)``. That is a simplification:
    it lands in ``Estimate``, which is a product of THREE monoids --

        value_ev         (R, +)
        uncertainty_ev   (R>=0, hypot)      associative, commutative, identity 0
        extrapolation_ev (R, +)

    -- and ``configuration_energy`` folds over a configuration's species with it. The fold
    is only well defined if those laws hold, so they are checked rather than assumed.

    The quadrature component carries a precondition the other two do not: hypot is the
    correct combination ONLY for INDEPENDENT errors. That is exactly the precondition a
    spectator violates, since its energy appears on both sides as one number rather than
    two samples. Hence ``reaction_residue`` runs BEFORE the fold, not after -- the monoid
    is sound on the residue and unsound on the raw configuration.
    """

    @staticmethod
    def _e(v, u, x=0.0):
        return Estimate(v, u, "m", 0.0, "", x)

    def test_identity_is_a_left_and_right_unit(self):
        z = Estimate.zero("m")
        a = self._e(3.0, 0.4, 0.1)
        for combined in (z + a, a + z):
            assert combined.value_ev == pytest.approx(a.value_ev)
            assert combined.uncertainty_ev == pytest.approx(a.uncertainty_ev)
            assert combined.extrapolation_ev == pytest.approx(a.extrapolation_ev)

    @settings(max_examples=100, deadline=None)
    @given(
        v=st.tuples(*[st.floats(-1e4, 1e4, allow_nan=False)] * 3),
        u=st.tuples(*[st.floats(0.0, 1e3, allow_nan=False)] * 3),
        x=st.tuples(*[st.floats(-1e2, 1e2, allow_nan=False)] * 3),
    )
    def test_addition_is_associative(self, v, u, x):
        a, b, c = (self._e(v[i], u[i], x[i]) for i in range(3))
        left, right = (a + b) + c, a + (b + c)
        assert left.value_ev == pytest.approx(right.value_ev)
        assert left.uncertainty_ev == pytest.approx(right.uncertainty_ev)
        assert left.extrapolation_ev == pytest.approx(right.extrapolation_ev)

    @settings(max_examples=100, deadline=None)
    @given(
        v=st.tuples(*[st.floats(-1e4, 1e4, allow_nan=False)] * 2),
        u=st.tuples(*[st.floats(0.0, 1e3, allow_nan=False)] * 2),
        x=st.tuples(*[st.floats(-1e2, 1e2, allow_nan=False)] * 2),
    )
    def test_addition_is_commutative(self, v, u, x):
        a, b = (self._e(v[i], u[i], x[i]) for i in range(2))
        assert (a + b).value_ev == pytest.approx((b + a).value_ev)
        assert (a + b).uncertainty_ev == pytest.approx((b + a).uncertainty_ev)
        assert (a + b).extrapolation_ev == pytest.approx((b + a).extrapolation_ev)

    def test_quadrature_not_linear_addition(self):
        """The uncertainty component is hypot, not +. Three at 0.3 give 0.5196, not 0.9."""
        total = self._e(0, 0.3) + self._e(0, 0.3) + self._e(0, 0.3)
        assert total.uncertainty_ev == pytest.approx(0.5196152, abs=1e-6)

    def test_the_fold_does_not_depend_on_species_order(self):
        """
        What associativity and commutativity buy in practice: a configuration is a
        multiset, so the fold must not care which order its species come out in.
        """
        parts = [self._e(1.0, 0.2), self._e(-3.0, 0.5), self._e(7.5, 0.1)]
        forward = parts[0] + parts[1] + parts[2]
        backward = parts[2] + parts[1] + parts[0]
        assert forward.value_ev == pytest.approx(backward.value_ev)
        assert forward.uncertainty_ev == pytest.approx(backward.uncertainty_ev)

    def test_negation_preserves_uncertainty_but_flips_the_systematic_part(self):
        """
        The asymmetry that makes the difference honest. Random error has no sign, so
        negation leaves it alone; the systematic correction does, so it flips and can
        cancel in a conserving difference.
        """
        a = self._e(3.0, 0.4, 0.1)
        assert (-a).uncertainty_ev == pytest.approx(a.uncertainty_ev)
        assert (-a).extrapolation_ev == pytest.approx(-a.extrapolation_ev)
        assert (a + (-a)).extrapolation_ev == pytest.approx(0.0)
