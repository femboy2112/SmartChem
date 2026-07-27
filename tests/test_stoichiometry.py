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

from smartchem.category import (
    Bond,
    Config,
    ConservationError,
    Molecule,
    Reaction,
    conserves,
)
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

    Both are replaced together, deliberately. ``equation`` now refuses a species tuple that
    is not the one its coefficients were derived against, so replacing only the
    coefficients would be constructing exactly the mismatch that guard exists to refuse.
    """
    seed = stoichiometry_menu((H2, O2, H2O)).completions[0]
    return replace(seed, coefficients=tuple(coefficients),
                   species=tuple(species)).equation()


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


CH4 = Molecule(("C", "H", "H", "H", "H"),
               frozenset({Bond(0, 1, 1), Bond(0, 2, 1), Bond(0, 3, 1), Bond(0, 4, 1)}))
#: Section I's own example set. Order matters: check() aligns with the menu's species.
COMBUSTION = (CH4, O2, CO2, H2O)


class TestSectionIsSecondClause:
    """
    "Choose one, **or write one and I will check it against the same rules.**"

    The first clause has been implemented since Brick 0; the second had not been, and a
    menu without it is a multiple-choice question wearing the costume of a dialogue. The
    phrase "the same rules" is enforced literally here: ``check`` evaluates ``A @ nu``
    against the menu's own ``matrix``, the identical object that produced ``completions``,
    rather than a second checker written to agree with the first.
    """

    MENU = stoichiometry_menu(COMBUSTION)

    def test_the_menu_is_the_fill_in_regime_so_writing_one_is_the_only_choice(self):
        """Freedom 1: there is nothing to pick between, which is when clause two matters."""
        assert self.MENU.verdict == "FILL_IN"
        assert self.MENU.equations() == ("CH4 + 2O2 -> CO2 + 2H2O",)

    def test_a_correct_written_balance_is_verified(self):
        written = self.MENU.check((1, 2, -1, -2))
        assert written.admissible and written.verified and bool(written)
        assert written.residual == (0, 0, 0, 0)
        assert written.reaction is not None and conserves(written.reaction)

    def test_a_wrong_one_names_which_invariant_broke_and_by_how_much(self):
        """
        Section IX: a refusal that says only "no" sends a scientist back to guess. The
        row labels come from ``composition_matrix``, so the diagnosis is derived.
        """
        written = self.MENU.check((1, 1, -1, -2))       # under-oxidised by one O2
        assert not written.admissible
        assert written.violations == (("O", -2),)
        assert "O off by -2" in written.explain()

    def test_the_all_zero_vector_is_refused_although_it_balances(self):
        """
        The trap a bare residual test walks into. ``A @ 0 == 0`` exactly, on every row, in
        every menu that has ever existed. Reporting it as admissible would be a confident
        yes about the empty statement.
        """
        written = self.MENU.check((0, 0, 0, 0))
        assert written.residual == (0, 0, 0, 0), "it really does satisfy every invariant"
        assert written.trivial and not written.admissible and not bool(written)
        assert written.reaction is None, "and nothing was constructed from it"

    def test_admissible_and_verified_are_two_claims_and_stay_apart(self):
        """
        ``Na(*) -> Na``. The columns are identical because ``state`` is deliberately kept
        out of the conserved signature, so the invariants cannot resolve these two species
        from each other and ``A @ nu`` is unchanged by either column. The balance is real;
        it is not evidence about de-excitation, and the weaker claim must not wear the
        stronger one's name.
        """
        excited, relaxed = Molecule(("Na",), state="*"), Molecule.atom("Na")
        menu = stoichiometry_menu((excited, relaxed))
        written = menu.check((1, -1))
        assert written.admissible, "the residual is zero on every row"
        assert not written.verified, "and no row could see what it is a balance OF"
        assert bool(written) is False, "truthiness follows the STRONGER claim"
        assert "silence about them" in written.explain()

    def test_a_blind_species_only_costs_a_verdict_when_the_vector_touches_it(self):
        """
        The distinction between *present in the candidate set* and *leaned on*.

        Found by ``experiments/ledger_mutation_probe.py``: the mutant that drops the
        ``c and`` guard -- flagging every invariant-blind species rather than the ones with
        a nonzero coefficient -- SURVIVED all 69 tests written for this brick. The code was
        right and the suite could not see it, which is a coverage hole and not a shipped
        defect, but the two are only distinguishable by measuring.

        A bare quantum has an all-zero column, so it is in the kernel by itself and
        contributes nothing to ``A @ nu`` whatever its coefficient. With coefficient zero
        the balance does not rest on it at all and the verdict must not be downgraded;
        with a nonzero one it does, and must be.
        """
        photon = Molecule(())
        menu = stoichiometry_menu(COMBUSTION + (photon,))
        assert menu.unconstrained == (photon,), "the blind species really is flagged"

        untouched = menu.check((1, 2, -1, -2, 0))
        assert untouched.unverifiable == (), "coefficient zero is not leaning on it"
        assert untouched.verified and bool(untouched) is True

        touched = menu.check((1, 2, -1, -2, 1))
        assert touched.admissible, "the all-zero column keeps the residual at zero"
        assert touched.unverifiable == (photon,)
        assert not touched.verified, "and that zero is silence, not evidence"

    @pytest.mark.parametrize("nu, exception", [
        ((1, 2, -1), ValueError),           # wrong length -- would silently zip-truncate
        ((1, 2.0, -1, -2), TypeError),      # a float sums straight through the residual
        ((1, True, -1, -2), TypeError),     # True is a typo, not a 1
        ((900, 900, -900, -900), ValueError),   # past MAX_WRITTEN_WEIGHT
    ])
    def test_a_malformed_question_raises_rather_than_answering_false(self, nu, exception):
        """
        Returning ``False`` here would tell a scientist their chemistry is wrong when
        their typing was. The weight cap is an allocation bound, not a claim about
        chemistry, and its message says so.
        """
        with pytest.raises(exception):
            self.MENU.check(nu)

    def test_the_two_clauses_agree_with_each_other(self):
        """
        Every option the menu OFFERS must pass the check the menu APPLIES. If these two
        ever disagreed, one of the clauses would be lying about the same rules.
        """
        for completion in self.MENU.completions:
            written = self.MENU.check(completion.coefficients)
            assert written.admissible, f"{completion!r} is offered but fails its own check"

    @pytest.mark.parametrize("multiple", [1, -1, 2, -3, 7])
    def test_every_integer_multiple_of_an_offered_balance_also_passes(self, multiple):
        """
        The kernel is a lattice, so scaling and reversal stay inside it. This is the
        cheap half of the completeness theorem, asserted on the written-check path
        because that path is new and the theorem is what makes it complete.
        """
        base = self.MENU.completions[0].coefficients
        written = self.MENU.check(tuple(multiple * c for c in base))
        assert written.admissible

    def test_the_check_shares_the_matrix_it_claims_to_share(self):
        """
        "The same rules" asserted against the object rather than the prose: the residual
        is recomputed here from ``menu.matrix`` by an independent expression and must
        agree term for term with what ``check`` reported.
        """
        nu = (1, 1, -1, -2)
        assert self.MENU.check(nu).residual == tuple(_apply(self.MENU.matrix, nu))


class TestEquationCannotBeHandedTheWrongSpecies:
    """
    A rendered equation must be about the reaction whose coefficients rendered it.

    Two rounds of this. The first guard checked only the LENGTH, because ``zip`` truncates
    in silence and a shorter equation reads as a complete one. Adversarial review then
    showed the length check leaves the worse case wide open: a tuple of the RIGHT length
    and the wrong CONTENT renders a fully formed, plausible equation for a reaction nobody
    derived -- and reordering a species list is an ordinary pipeline mistake, not an
    attack. Identity is the only guard that closes it, so the species are stored now.
    """

    MENU = stoichiometry_menu(COMBUSTION)

    def test_a_short_species_tuple_is_refused(self):
        with pytest.raises(ValueError):
            self.MENU.completions[0].equation(COMBUSTION[:3])

    def test_a_reordered_tuple_of_the_right_length_is_refused(self):
        """The case the length guard could not see, and the likelier of the two."""
        with pytest.raises(ValueError, match="different order"):
            self.MENU.completions[0].equation((O2, CH4, H2O, CO2))

    def test_an_unrelated_tuple_of_the_right_length_is_refused(self):
        with pytest.raises(ValueError):
            self.MENU.completions[0].equation((N2, C, He, H2))

    def test_what_the_length_only_guard_would_have_rendered(self):
        """
        The stake, made concrete rather than described. Building the mismatch deliberately
        via ``replace`` shows what the old signature handed back for a reordered tuple: a
        well-formed string, indistinguishable from a menu entry, for a reaction that does
        not even balance.
        """
        rogue = replace(self.MENU.completions[0], species=(O2, CH4, H2O, CO2))
        assert rogue.equation() == "O2 + 2CH4 -> H2O + 2CO2"
        with pytest.raises(ConservationError):
            Reaction(Config.of(O2, CH4, CH4), Config.of(H2O, CO2, CO2))

    def test_the_menus_own_tuple_still_works_and_so_does_no_tuple(self):
        completion = self.MENU.completions[0]
        assert completion.equation(self.MENU.species) == "CH4 + 2O2 -> CO2 + 2H2O"
        assert completion.equation() == "CH4 + 2O2 -> CO2 + 2H2O"


class TestTheWrittenCheckRefusesTypesThatCanLie:
    """
    Both found by adversarial review of the check itself. Neither is about arithmetic --
    each is a container or a type producing a confident verdict about a vector nobody wrote.
    """

    MENU = stoichiometry_menu(COMBUSTION)

    def test_an_unordered_container_is_refused_rather_than_silently_sorted(self):
        """
        A ``set`` has a length, holds ints, and passes every other guard. ``tuple()``
        freezes it in HASH order. MEASURED over 39 scalings of this menu's own derived
        balance: 34 came back with a confident, specific, WRONG refusal carrying fabricated
        row violations. ``scale=1`` survived by hash-layout coincidence, which is worse
        than failing, because it makes the bug look like it is not there.
        """
        with pytest.raises(TypeError, match="ordered sequence"):
            self.MENU.check({1, 2, -1, -2})
        assert self.MENU.check([1, 2, -1, -2]).admissible, "a list is ordered and fine"

    def test_a_set_really_does_reorder_this_vector(self):
        """The premise of the guard above, asserted rather than assumed."""
        assert tuple({2, 4, -2, -4}) != (2, 4, -2, -4)

    def test_an_int_subclass_is_refused_because_it_can_answer_twice(self):
        """
        ``MAX_WRITTEN_WEIGHT`` is justified as an allocation bound, and that bound is only
        real if the value it measures is the value the allocator sees. ``abs()`` is called
        once at the gate and again inside ``_configs``. MEASURED: a subclass declaring
        weight 4 to the gate allocated 5,000,000 molecules, and the mismatch surfaced as a
        ``MenuContradiction`` -- the module accusing its own two derivations of disagreeing
        when neither was wrong and the TYPE had lied.

        The payload below is 50,000 rather than the 5,000,000 that was measured. It is
        still fifty times ``MAX_WRITTEN_WEIGHT`` and proves the identical point, and it
        keeps the mutation harness -- which runs this test against a build with the guard
        removed, where the allocation really happens -- from spending gigabytes and half a
        minute to establish what a smaller number establishes.
        """
        class Toggle(int):
            def __new__(cls, value, big):
                obj = int.__new__(cls, value)
                obj._big, obj._calls = big, 0
                return obj

            def __abs__(self):
                self._calls += 1
                return abs(int(self)) if self._calls == 1 else self._big

        poison = Toggle(2, 50_000)
        assert isinstance(poison, int), "isinstance would have waved this through"
        with pytest.raises(TypeError, match="exactly int"):
            self.MENU.check((1, poison, -1, -2))

    def test_a_plain_int_is_still_fine(self):
        assert self.MENU.check((1, 2, -1, -2)).verified
