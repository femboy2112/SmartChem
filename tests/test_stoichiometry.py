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
from dataclasses import replace
from hypothesis import given, settings, strategies as st

from smartchem.category import Bond, Config, Molecule, Reaction, conserves
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
#: The set that exposed the 2026-07-26 completeness defect; see TestCompleteness.
H2O2 = Molecule(("O", "O", "H", "H"),
                frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(1, 3, 1)}))


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
        """
        {C, O2, CO, CO2} has a genuine choice, and the menu is a BASIS of it.

        Asserted as a property of the LATTICE rather than as two expected equation strings.
        Which basis vectors come back is a fact about the elimination order, and pinning
        the strings makes an honest change of algorithm look like a regression -- it is
        exactly what this assertion did when the kernel was corrected on 2026-07-26. The
        durable claim is that the reactions a chemist expects are *reachable*, which is a
        statement about the group the basis generates.
        """
        menu = stoichiometry_menu((C, O2, CO, CO2))
        assert menu.freedom == 2
        assert menu.verdict == "ENUMERATE"
        assert len(menu.completions) == 2
        basis = [c.coefficients for c in menu.completions]
        for expected in ((2, 1, -2, 0), (1, 1, 0, -1), (1, 0, -2, 1)):
            assert _apply(menu.matrix, expected) == [0] * len(menu.matrix)
            assert _integer_combination(basis, expected) is not None, (
                f"{expected} is balanced but unreachable from the returned basis"
            )


def _integer_combination(basis, target):
    """
    The integer coefficients expressing ``target`` over ``basis``, or None if there are none.

    Exact elimination over ``Fraction``; a rational solution with any denominator other
    than 1 means the target lies in the rational span but OUTSIDE the lattice the basis
    generates, which is precisely the failure this file exists to detect.
    """
    from fractions import Fraction

    width, height = len(basis), len(target)
    augmented = [
        [Fraction(basis[j][i]) for j in range(width)] + [Fraction(target[i])]
        for i in range(height)
    ]
    row, pivots = 0, []
    for column in range(width):
        found = next((i for i in range(row, height) if augmented[i][column] != 0), None)
        if found is None:
            continue
        augmented[row], augmented[found] = augmented[found], augmented[row]
        lead = augmented[row][column]
        augmented[row] = [x / lead for x in augmented[row]]
        for i in range(height):
            if i != row and augmented[i][column] != 0:
                factor = augmented[i][column]
                augmented[i] = [a - factor * b for a, b in zip(augmented[i], augmented[row])]
        pivots.append(column)
        row += 1
    if any(augmented[i][width] != 0 for i in range(row, height)):
        return None                                   # not even in the rational span
    solution = [Fraction(0)] * width
    for i, column in enumerate(pivots):
        solution[column] = augmented[i][width]
    if any(value.denominator != 1 for value in solution):
        return None                                   # in the span, outside the lattice
    return tuple(int(value) for value in solution)


class TestCompleteness:
    """
    The menu generates ker(A) INTERSECTED WITH THE INTEGER LATTICE, not a sublattice of it.

    This class previously asserted no such thing, and the gap shipped a real defect. Its
    two tests were ``len(completions) == freedom`` -- which ``stoichiometry_menu`` already
    raises on, so the assertion restated two implementation lines and could error but never
    fail -- and ``A @ nu == 0``, which is SOUNDNESS. Soundness was never the hard part. A
    mutant returning a generating set of an index-2 sublattice is still sound, still
    count-correct, still primitive, and passed 28 of the 29 tests in this file.

    So the test below is the one that kills that mutant: enumerate every integer point of
    the kernel inside a box and require each to be an integer combination of what the menu
    returned. Exhaustive over a bounded region rather than proved for all of ``Z^n``, and
    the box is stated rather than implied.
    """

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
        """A@nu == 0 in integers. Not 'close to zero' -- zero. This is SOUNDNESS."""
        menu = stoichiometry_menu(species)
        for completion in menu.completions:
            assert _apply(menu.matrix, completion.coefficients) == [0] * len(menu.matrix)

    @pytest.mark.parametrize("species,bound", [
        ((H2, O2, H2O), 3),
        ((C, O2, CO, CO2), 3),
        ((O2, H2O, H2O2, H2), 3),
        ((N2, CO, CO2, O2, C), 2),
    ])
    def test_no_balanced_reaction_in_the_box_is_unreachable(self, species, bound):
        """
        THE test. Every integer kernel point in [-bound, bound]^n must be generated.

        ``(O2, H2O, H2O2, H2)`` is in the roster because it is the set that exposed the
        original defect: the rational-basis version returned (1,2,-2,0) and (1,-2,0,2) and
        could not reach (1,0,-1,1), which is ``H2 + O2 -> H2O2``, a balanced reaction any
        chemist would name first.
        """
        from itertools import product

        menu = stoichiometry_menu(species)
        basis = [c.coefficients for c in menu.completions]
        zero = [0] * len(menu.matrix)
        checked = 0
        for point in product(range(-bound, bound + 1), repeat=len(species)):
            if not any(point) or _apply(menu.matrix, point) != zero:
                continue
            checked += 1
            assert _integer_combination(basis, point) is not None, (
                f"{point} balances over {species} but is not an integer combination of "
                f"the returned basis {basis} -- the menu is incomplete"
            )
        assert checked > 0, "the box contained no balanced reactions; the test proves nothing"

    def test_completeness_does_not_depend_on_argument_order(self):
        """
        The lattice is a property of the species set, not of how the caller listed them.

        The original defect made this false: 4 of the 24 orderings of this set returned a
        basis generating a different sublattice, and ``C + O2 -> CO2`` was unreachable from
        several of them. Mutual integer containment is the exact check -- two bases generate
        the same lattice precisely when each spans the other over ``Z``.
        """
        from itertools import permutations

        species = (C, O2, CO, CO2)
        reference = [c.coefficients for c in stoichiometry_menu(species).completions]
        for order in permutations(range(len(species))):
            shuffled = tuple(species[i] for i in order)
            menu = stoichiometry_menu(shuffled)
            # Re-express in the reference species order before comparing lattices.
            realigned = [
                tuple(vector[order.index(i)] for i in range(len(species)))
                for vector in (c.coefficients for c in menu.completions)
            ]
            for vector in realigned:
                assert _integer_combination(reference, vector) is not None, order
            for vector in reference:
                assert _integer_combination(realigned, vector) is not None, order

    def test_coefficients_are_integers_not_floats(self):
        """A rational menu with a tolerance is a plausible menu. Guard the type."""
        menu = stoichiometry_menu((C, O2, CO, CO2))
        for completion in menu.completions:
            assert all(type(c) is int for c in completion.coefficients)

    def test_float_input_is_refused_rather_than_silently_widened(self):
        """
        ``Fraction(0.1)`` is a ratio of astronomical integers, and the kernel of that is a
        kernel of a matrix nobody supplied. The module refuses a floating-point RANK on
        exactly this argument; refusing the input is the same argument one step earlier.
        """
        with pytest.raises(TypeError):
            integer_kernel_basis(((0.1, 0.3),))
        with pytest.raises(ValueError):
            integer_kernel_basis(((1, 2, 3), (1, 2)))


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


#: Deliberately includes the BARE quantum. Every boundary test above uses a *labelled*
#: photon (``state="photon@589nm"``), which renders as ``(photon@589nm)`` and is therefore
#: the one photon that could never expose the defect below. The species that broke the
#: renderer was the only one no test had ever rendered.
_RENDER_POOL = (
    Molecule.quantum(),                 # no atoms, no charge, no state -- used to render ""
    Molecule.quantum("589nm"),
    Molecule.atom("Na"),
    Molecule.carrier("", charge=-1),
    H2O,
)


def _render(coefficients, species=_RENDER_POOL):
    """
    Render a coefficient vector the way the menu would, without requiring it to balance.

    ``Completion.equation`` is a pure function of ``(coefficients, species)`` -- the
    ``reaction`` field plays no part in it -- so driving it over vectors no real menu would
    ever emit is strictly more coverage than only rendering what some menu happened to
    produce. That is the point: the defect this guards lived in vectors the fixtures never
    generated.
    """
    seed = stoichiometry_menu((H2, O2, H2O)).completions[0]
    return replace(seed, coefficients=tuple(coefficients)).equation(tuple(species))


class TestNothingRendersAsNothing:
    """
    A species whose text form is empty DISAPPEARS from every statement it is part of.

    This is the second defect Brick 0 shipped, and it is the same shape as the first: the
    module answered a question about the data by inspecting a *rendering* of the data.
    ``side()`` decided "there is nothing here" from the joined string being falsy rather
    than from the coefficients being zero, and ``Molecule.__repr__`` returned "" for the one
    species with no atoms, no charge and no state. Composed, they printed the kernel vector
    with coefficient 1 on a bare quantum as ``(nothing) -> (nothing)`` -- the trivial
    reaction, which is a confident false statement about a true basis vector -- and printed
    ``quantum -> Na`` as ``(nothing) -> Na``, which is a module whose entire subject is
    conservation announcing that matter came from nowhere.

    Soundness could not catch it either. Every rendered equation was a *correct* equation
    about the species it still mentioned.
    """

    def test_no_molecule_renders_as_the_empty_string(self):
        """The root invariant. "" is indistinguishable from absence, so it is never a name."""
        sample = [
            Molecule.quantum(), Molecule.quantum("589nm"), Molecule.atom("Na"),
            Molecule.carrier("", charge=-1), Molecule.carrier("", charge=2),
            Molecule.carrier("phonon", charge=0), H2, H2O, CO2,
        ]
        for molecule in sample:
            assert repr(molecule) != "", f"{molecule!r} renders as nothing"
            assert repr(molecule).strip() == repr(molecule)

    def test_the_bare_quantum_is_named_and_cannot_be_confused(self):
        """
        Lower case so no formula can collide, unbracketed so no state can.

        Element symbols are capitalised and states render as ``(state)``, so ``quantum``
        occupies a slot neither can reach -- including ``Molecule.quantum("quantum")``.
        """
        assert repr(Molecule.quantum()) == "quantum"
        assert repr(Molecule.quantum("quantum")) == "(quantum)"
        assert repr(Molecule.quantum()) != repr(Molecule.quantum("quantum"))

    def test_a_config_holding_only_a_quantum_is_not_the_identity(self):
        """``Config(())`` is ``I``; a Config with a photon in it must not print as nothing."""
        assert repr(Config(())) == "I"
        assert repr(Config((Molecule.quantum(),))) not in ("", "I")

    @settings(max_examples=300, deadline=None)
    @given(st.lists(st.integers(min_value=-3, max_value=3),
                    min_size=len(_RENDER_POOL), max_size=len(_RENDER_POOL)))
    def test_every_nonzero_coefficient_reaches_the_side_it_belongs_on(self, coefficients):
        """
        The external property. Not "does this string look right" but: is every species the
        vector mentions actually present in the rendering, on the correct side?

        A renderer that drops a species passes every soundness check ever written about the
        equations it still prints. Only an independent enumeration of what OUGHT to appear
        can fail on a dropped term, which is exactly the lesson of the sublattice defect.

        THE COUNT IS LOAD-BEARING AND THE SUBSTRING CHECK ALONE IS NOT. The first version
        of this test asserted only ``repr(molecule) in side``, and against the very defect
        it was written for that assertion is VACUOUS: the dropped species is the one whose
        repr is ``""``, and ``"" in anything`` is True. It was the single test in this class
        the mutant survived. Counting terms cannot be satisfied by dropping one.
        """
        rendered = _render(coefficients)
        left, _, right = rendered.partition(" -> ")
        for side, wanted in ((left, [c > 0 for c in coefficients]),
                             (right, [c < 0 for c in coefficients])):
            expected = sum(wanted)
            actual = 0 if side == "(nothing)" else len(side.split(" + "))
            assert actual == expected, f"{expected} term(s) owed, {actual} rendered in {side!r}"
        for molecule, c in zip(_RENDER_POOL, coefficients):
            if c:
                assert repr(molecule), f"{molecule.atoms}/{molecule.state} has no name to print"
                assert repr(molecule) in (left if c > 0 else right)

    @settings(max_examples=300, deadline=None)
    @given(st.lists(st.integers(min_value=-3, max_value=3),
                    min_size=len(_RENDER_POOL), max_size=len(_RENDER_POOL)))
    def test_nothing_is_printed_exactly_when_the_side_is_empty(self, coefficients):
        """``(nothing)`` is a claim about the COEFFICIENTS, so it must be decided by them."""
        left, _, right = _render(coefficients).partition(" -> ")
        assert (left == "(nothing)") == (not any(c > 0 for c in coefficients))
        assert (right == "(nothing)") == (not any(c < 0 for c in coefficients))

    @settings(max_examples=300, deadline=None)
    @given(st.lists(st.integers(min_value=-3, max_value=3),
                    min_size=len(_RENDER_POOL), max_size=len(_RENDER_POOL)))
    def test_no_side_is_blank_or_has_a_dangling_separator(self, coefficients):
        """``' + Na -> (nothing)'`` was a real output. A dangling ``+`` is a dropped term."""
        for side in _render(coefficients).partition(" -> ")[::2]:
            assert side.strip() == side and side != ""
            assert not side.startswith("+") and not side.endswith("+")
            assert " +  + " not in side

    def test_the_shipped_regressions_by_name(self):
        """The four literal wrong renderings, so a reader can see what was fixed."""
        hv, na = Molecule.quantum(), Molecule.atom("Na")
        pair = (hv, na)
        assert _render((1, 0), pair) == "quantum -> (nothing)"    # was '(nothing) -> (nothing)'
        assert _render((2, 0), pair) == "2quantum -> (nothing)"   # was '2 -> (nothing)'
        assert _render((1, 1), pair) == "quantum + Na -> (nothing)"  # was ' + Na -> (nothing)'
        assert _render((1, -1), pair) == "quantum -> Na"          # was '(nothing) -> Na'

    def test_the_documented_boundary_output_is_the_actual_output(self):
        """
        ``THE_COMPILER.md`` section VII says the menu offers ``photon -> (nothing)`` and
        calls it "measured, not argued: that is the literal output". It was measured with a
        labelled photon. With the bare quantum the species used to vanish, so the document's
        own load-bearing example was the one case that did not hold.
        """
        menu = stoichiometry_menu((Molecule.atom("Na"), Molecule.quantum()))
        assert "quantum -> (nothing)" in menu.equations()
        assert "quantum has no atoms and no charge" in menu.explain()


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
