"""
The derived-menu law, machine-checked.

``THE_COMPILER.md`` section III claims every option offered to a scientist is the image of
a declared invariant under a declared operation, and section IV claims three rank regimes
produce three behaviours. ``smartchem.stoichiometry`` implements that. These tests are what
stop the claim from being prose.

The load-bearing property is COMPLETENESS, not correctness: it is easy to return balanced
reactions and hard to return all of them. Every completeness assertion below is over exact
integer arithmetic, because a menu that is complete to within a floating-point tolerance is
not complete.
"""
import pytest
from hypothesis import given, settings, strategies as st

from smartchem.category import Bond, Molecule, Reaction, conserves
from smartchem.stoichiometry import (
    CHARGE_ROW,
    MenuContradiction,
    composition_matrix,
    integer_kernel_basis,
    stoichiometry_menu,
)

H2 = Molecule.diatomic("H", "H")
O2 = Molecule.diatomic("O", "O")
N2 = Molecule.diatomic("N", "N")
CO = Molecule.diatomic("C", "O")
He = Molecule.atom("He")
C = Molecule.atom("C")
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))
CO2 = Molecule(("C", "O", "O"), frozenset({Bond(0, 1, 2), Bond(0, 2, 2)}))


def _apply(matrix, nu):
    return [sum(row[i] * nu[i] for i in range(len(nu))) for row in matrix]


class TestTheThreeRegimes:
    """THE_COMPILER.md section IV: dim ker 0, 1 and >=2 give refuse, fill in, enumerate."""

    def test_rank_zero_refuses_and_the_refusal_is_a_theorem(self):
        """{H2, He} admits no non-trivial balance. Nothing to search; it cannot exist."""
        menu = stoichiometry_menu((H2, He))
        assert menu.freedom == 0
        assert menu.verdict == "REFUSE"
        assert menu.completions == ()
        assert not menu
        assert "theorem" in menu.explain()

    def test_rank_one_is_forced_and_asking_would_be_theatre(self):
        """{H2, O2, H2O} balances exactly one way up to sign and scale."""
        menu = stoichiometry_menu((H2, O2, H2O))
        assert menu.freedom == 1
        assert menu.verdict == "FILL_IN"
        assert menu.completions[0].coefficients == (2, 1, -2)
        assert menu.equations() == ("2H2 + O2 -> 2H2O",)

    def test_rank_two_enumerates_a_lattice_basis(self):
        """{C, O2, CO, CO2} has a genuine choice, and the menu is a BASIS of it."""
        menu = stoichiometry_menu((C, O2, CO, CO2))
        assert menu.freedom == 2
        assert menu.verdict == "ENUMERATE"
        assert len(menu.completions) == 2
        assert set(menu.equations()) == {"2C + O2 -> 2CO", "C + O2 -> CO2"}


class TestCompleteness:
    """The menu is a basis of ker(A), not a sample of it. That is the whole claim."""

    @pytest.mark.parametrize("species", [
        (H2, He), (H2, O2, H2O), (C, O2, CO, CO2), (N2, CO, CO2, O2, C),
    ])
    def test_basis_size_equals_rank_nullity(self, species):
        menu = stoichiometry_menu(species)
        assert len(menu.completions) == menu.freedom == len(species) - menu.rank

    @pytest.mark.parametrize("species", [
        (H2, O2, H2O), (C, O2, CO, CO2), (N2, CO, CO2, O2, C),
    ])
    def test_every_derived_vector_is_exactly_in_the_kernel(self, species):
        """A@nu == 0 in integers. Not 'close to zero' -- zero."""
        menu = stoichiometry_menu(species)
        for completion in menu.completions:
            assert _apply(menu.matrix, completion.coefficients) == [0] * len(menu.matrix)

    def test_coefficients_are_integers_not_floats(self):
        """A rational menu with a tolerance is a plausible menu. Guard the type."""
        menu = stoichiometry_menu((C, O2, CO, CO2))
        for completion in menu.completions:
            assert all(type(c) is int for c in completion.coefficients)


class TestTheIndependentCheck:
    """
    Every completion carries a real Reaction, and its constructor is the second derivation.

    ``conserves`` cannot serve as the independent check -- it is tautologically True on any
    Reaction that exists, because ``Reaction.__post_init__`` already raised otherwise. The
    check that has teeth is that construction SUCCEEDED at all, over dictionary arithmetic
    that shares no code with the Fraction elimination.
    """

    @pytest.mark.parametrize("species", [
        (H2, O2, H2O), (C, O2, CO, CO2), (N2, CO, CO2, O2, C),
    ])
    def test_every_completion_carries_a_constructed_reaction(self, species):
        menu = stoichiometry_menu(species)
        for completion in menu.completions:
            assert isinstance(completion.reaction, Reaction)
            assert conserves(completion.reaction)

    def test_the_reaction_endpoints_match_the_coefficients(self):
        """The Reaction is the same statement as the vector, not a second opinion."""
        menu = stoichiometry_menu((H2, O2, H2O))
        completion = menu.completions[0]
        assert completion.reaction.dom.formula == {"H": 4, "O": 2}
        assert completion.reaction.cod.formula == {"H": 4, "O": 2}
        assert len(completion.reaction.dom) == 3      # 2 H2 + 1 O2
        assert len(completion.reaction.cod) == 2      # 2 H2O


class TestChargeIsLoadBearing:
    """
    The charge row is not decoration: it changes verdicts.

    ``conserves`` tests atom counts AND charge, so a composition matrix without the charge
    row would be the inverse of a weaker checker and would offer completions that
    ``Reaction`` then rejects.
    """

    def test_charge_row_is_present_and_labelled(self):
        labels, matrix = composition_matrix((H2, O2, H2O))
        assert labels[-1] == CHARGE_ROW
        assert len(matrix) == len(labels)

    def test_charge_turns_a_forced_balance_into_a_refusal(self):
        """Na+ and Na have identical formulas; only charge separates them."""
        na = Molecule.atom("Na")
        na_plus = Molecule(("Na",), frozenset(), charge=1)
        menu = stoichiometry_menu((na_plus, na))
        assert menu.verdict == "REFUSE"
        # and the reason is charge alone: drop that row and a balance appears
        _labels, matrix = composition_matrix((na_plus, na))
        assert len(integer_kernel_basis(matrix[:-1])) == 1
        assert len(integer_kernel_basis(matrix)) == 0


class TestTheDeclaredBoundary:
    """
    A menu is complete with respect to the DECLARED invariants and not one inch further.

    A photon has no atoms and no charge, so its column is zero and it sits in the kernel by
    itself. Mass and charge conservation genuinely cannot see it. The menu must say so
    rather than hide the completion or pretend it is chemistry.
    """

    def test_a_species_the_invariants_cannot_see_is_named(self):
        photon = Molecule((), frozenset(), state="photon@589nm")
        menu = stoichiometry_menu((Molecule.atom("Na"), photon))
        assert menu.unconstrained == (photon.canonical(),)
        assert "BOUNDARY" in menu.explain()

    def test_completions_touching_it_are_flagged(self):
        photon = Molecule((), frozenset(), state="photon@589nm")
        menu = stoichiometry_menu((Molecule.atom("Na"), photon))
        assert [c.unconstrained for c in menu.completions] == [True]

    def test_ordinary_species_are_not_flagged(self):
        menu = stoichiometry_menu((H2, O2, H2O))
        assert menu.unconstrained == ()
        assert not any(c.unconstrained for c in menu.completions)


class TestInputDiscipline:
    def test_a_repeated_species_is_rejected(self):
        """Two identical columns fake a degree of freedom whose reaction is A -> A."""
        with pytest.raises(ValueError, match="repeated"):
            stoichiometry_menu((H2, Molecule.diatomic("H", "H")))

    def test_non_molecules_are_rejected(self):
        with pytest.raises(TypeError, match="tuple of Molecule"):
            stoichiometry_menu(("H2", "O2"))

    def test_empty_candidate_set_refuses(self):
        menu = stoichiometry_menu(())
        assert menu.freedom == 0
        assert menu.verdict == "REFUSE"


class TestKernelArithmetic:
    """The elimination itself, away from any chemistry."""

    def test_zero_matrix_kernel_is_everything(self):
        assert len(integer_kernel_basis(((0, 0, 0),))) == 3

    def test_basis_vectors_are_primitive(self):
        """Denominators cleared and the gcd divided out, so (2,4) never appears for (1,2)."""
        from math import gcd
        from functools import reduce
        for nu in integer_kernel_basis(((2, 0, 2), (0, 2, 1))):
            assert reduce(gcd, (abs(v) for v in nu if v)) == 1

    def test_contradiction_is_a_distinct_error_type(self):
        assert issubclass(MenuContradiction, AssertionError)


@st.composite
def _species_sets(draw):
    """Small candidate sets drawn from a fixed, chemically real pool."""
    pool = [H2, O2, N2, CO, CO2, H2O, C, He]
    size = draw(st.integers(min_value=1, max_value=5))
    indices = draw(st.lists(st.integers(min_value=0, max_value=len(pool) - 1),
                            min_size=size, max_size=size, unique=True))
    return tuple(pool[i] for i in indices)


class TestProperties:
    @settings(max_examples=200, deadline=None)
    @given(_species_sets())
    def test_every_completion_balances_exactly(self, species):
        menu = stoichiometry_menu(species)
        for completion in menu.completions:
            assert _apply(menu.matrix, completion.coefficients) == [0] * len(menu.matrix)

    @settings(max_examples=200, deadline=None)
    @given(_species_sets())
    def test_rank_nullity_always_holds(self, species):
        menu = stoichiometry_menu(species)
        assert menu.rank + menu.freedom == len(species)
        assert len(menu.completions) == menu.freedom

    @settings(max_examples=200, deadline=None)
    @given(_species_sets())
    def test_the_menu_never_lies_about_its_verdict(self, species):
        menu = stoichiometry_menu(species)
        assert (menu.verdict == "REFUSE") == (menu.freedom == 0)
        assert bool(menu) == (menu.freedom > 0)
