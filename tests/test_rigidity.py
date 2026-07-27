"""
Tests for the derived-menu law against a non-linear invariant.

The classes are named for the claims rather than the functions, because the claims are what
a future edit can quietly break. Two of them assert that a linear proxy gives the WRONG
answer -- those are the finding, and a well-meaning repair that made them pass would be
deleting the result.
"""
from __future__ import annotations

import random
from fractions import Fraction as F
from itertools import combinations

import pytest

from smartchem.category import Bond, Molecule
from smartchem.rigidity import (
    FORCED,
    Framework,
    REFUSED,
    UNDECIDED,
    infinitesimal_freedom,
    psd_rank,
    rigidity_matrix,
    rigidity_menu,
)
from smartchem.stoichiometry import (
    CHARGE_ROW,
    StoichiometryMenu,
    composition_matrix,
    stoichiometry_menu,
)

H2 = Molecule.diatomic("H", "H")
O2 = Molecule.diatomic("O", "O")
H2O = Molecule(("O", "H", "H"), frozenset({Bond(0, 1, 1), Bond(0, 2, 1)}))


def triangle(a, b, c, dimension=2) -> Framework:
    return Framework(3, dimension,
                     ((0, 1, F(a) ** 2), (1, 2, F(b) ** 2), (0, 2, F(c) ** 2)))


def complete_from(points, dimension) -> tuple[Framework, tuple]:
    """A framework declaring EVERY pairwise distance of a chosen realisation."""
    placed = tuple(tuple(F(v) for v in p) for p in points)
    constraints = tuple(
        (i, j, sum((placed[i][a] - placed[j][a]) ** 2 for a in range(dimension)))
        for i, j in combinations(range(len(placed)), 2)
    )
    return Framework(len(placed), dimension, constraints), placed


def _determinant(rows) -> F:
    """
    An exact determinant, written independently of anything in the module under test.

    Plain fraction Gaussian elimination. It exists so the PSD test below can be checked
    against a characterisation that shares no code with it.
    """
    mat = [list(r) for r in rows]
    n = len(mat)
    result = F(1)
    for column in range(n):
        pivot = next((r for r in range(column, n) if mat[r][column] != 0), None)
        if pivot is None:
            return F(0)
        if pivot != column:
            mat[column], mat[pivot] = mat[pivot], mat[column]
            result = -result
        result *= mat[column][column]
        lead = mat[column][column]
        for r in range(column + 1, n):
            factor = mat[r][column] / lead
            if factor:
                for c in range(column, n):
                    mat[r][c] -= factor * mat[column][c]
    return result


def _psd_by_all_principal_minors(matrix) -> bool:
    """
    A symmetric matrix is PSD exactly when EVERY principal minor is non-negative.

    Note this is all principal minors and not merely the LEADING ones -- the leading-minor
    (Sylvester) test characterises positive DEFINITE, and using it for semidefinite is the
    classic wrong shortcut: ``[[0, 0], [0, -1]]`` has leading minors 0 and 0 and is not PSD.
    Exponential in the size, which is fine at the sizes here and is the price of an
    independent check.
    """
    n = len(matrix)
    for size in range(1, n + 1):
        for subset in combinations(range(n), size):
            block = [[matrix[i][j] for j in subset] for i in subset]
            if _determinant(block) < 0:
                return False
    return True


class TestThePsdTestIsExactAndIndependentlyConfirmed:
    def test_agrees_with_all_principal_minors_over_random_rationals(self):
        rng = random.Random(20260727)
        disagreements = []
        for _ in range(300):
            n = rng.randint(1, 4)
            rows = [[F(0)] * n for _ in range(n)]
            for i in range(n):
                for j in range(i, n):
                    value = F(rng.randint(-4, 4), rng.randint(1, 3))
                    rows[i][j] = rows[j][i] = value
            matrix = tuple(tuple(r) for r in rows)
            if (psd_rank(matrix) is not None) != _psd_by_all_principal_minors(matrix):
                disagreements.append(matrix)
        assert not disagreements, f"psd_rank disagreed with minors on {disagreements[:2]}"

    def test_agrees_on_matrices_built_to_be_psd(self):
        """``B^T B`` is PSD by construction, and its rank is the rank of ``B``."""
        rng = random.Random(11)
        for _ in range(120):
            rows, cols = rng.randint(1, 4), rng.randint(1, 4)
            b = [[F(rng.randint(-3, 3)) for _ in range(cols)] for _ in range(rows)]
            gram = tuple(
                tuple(sum(b[k][i] * b[k][j] for k in range(rows)) for j in range(cols))
                for i in range(cols)
            )
            assert psd_rank(gram) is not None, f"B^T B judged not PSD: {gram}"

    def test_the_zero_diagonal_trap(self):
        """
        A dead diagonal with a live off-diagonal is a negative eigenvalue in disguise.

        ``[[0, 1], [1, 0]]`` has eigenvalues +1 and -1. An elimination that skips rows
        whose pivot is zero, without checking the rest of the row, calls this PSD -- and
        that is a confident "these lengths are realisable" about lengths that are not.
        """
        assert psd_rank(((F(0), F(1)), (F(1), F(0)))) is None
        assert psd_rank(((F(0), F(0)), (F(0), F(0)))) == 0
        assert psd_rank(((F(0), F(0)), (F(0), F(-1)))) is None
        assert psd_rank(((F(2), F(0)), (F(0), F(0)))) == 1


class TestTheRefusalIsATheorem:
    def test_violated_triangle_inequality(self):
        menu = rigidity_menu(triangle(1, 1, 3))
        assert menu.verdict == REFUSED
        assert menu.proved
        assert not menu

    def test_lengths_consistent_but_ambient_space_too_small(self):
        unit = Framework(4, 2, tuple((i, j, F(1))
                                     for i, j in combinations(range(4), 2)))
        menu = rigidity_menu(unit)
        assert menu.verdict == REFUSED
        assert menu.embedding_dimension == 3, "a unit tetrahedron needs three dimensions"

    def test_the_same_lengths_are_accepted_when_the_space_is_big_enough(self):
        unit = Framework(4, 3, tuple((i, j, F(1))
                                     for i, j in combinations(range(4), 2)))
        assert rigidity_menu(unit).verdict == FORCED


class TestACompleteConstraintSetCanNeverOfferAChoice:
    """The headline. Decidable exactly where the invariant is doing no work."""

    def test_a_realisable_complete_set_is_forced(self):
        menu = rigidity_menu(triangle(3, 5, 4))
        assert menu.verdict == FORCED
        assert menu.proved
        assert menu.embedding_dimension == 2

    def test_there_is_no_enumerate_verdict(self):
        """
        Deliberately absent, and this test is the guard against adding one.

        In the linear module ENUMERATE means "here is a basis; every admissible point is
        an integer combination of these". The admissible set here is a variety, closed
        under no combination at all, so a token spelled the same way would claim something
        no method in the module establishes.
        """
        verdicts = set()
        for lengths in [(1, 1, 3), (3, 5, 4), (1, 1, 2)]:
            verdicts.add(rigidity_menu(triangle(*lengths)).verdict)
        verdicts.add(rigidity_menu(Framework(3, 2, ((0, 1, F(1)),))).verdict)
        assert verdicts <= {REFUSED, FORCED, UNDECIDED}
        assert "ENUMERATE" not in verdicts

    def test_the_tight_triangle_inequality_is_caught_exactly(self):
        menu = rigidity_menu(triangle(1, 1, 2))
        assert menu.verdict == FORCED
        assert menu.embedding_dimension == 1, "collinear, so it embeds only in a line"

    def test_an_incomplete_set_is_undecided_and_says_why(self):
        menu = rigidity_menu(Framework(3, 2, ((0, 1, F(1)), (1, 2, F(1)))))
        assert menu.verdict == UNDECIDED
        assert not menu.proved
        assert not menu
        assert "NP-hard" in menu.reason


class TestTrivialFreedomIsConfirmedAgainstTheRigidityMatrix:
    """
    The formula was wrong once, on 2026-07-27, and went NEGATIVE at eight points in three
    dimensions. It is now checked against a quantity derived a different way: at a generic
    spanning realisation, a COMPLETE framework has no internal freedom, so the nullity of
    its rigidity matrix is exactly the trivial freedom.
    """

    @pytest.mark.parametrize("dimension", [1, 2, 3, 4])
    @pytest.mark.parametrize("points", [1, 2, 3, 4, 5, 6])
    def test_nullity_of_a_complete_generic_framework_equals_trivial_freedom(
            self, points, dimension):
        rng = random.Random(1000 * points + dimension)
        best = None
        for _ in range(6):                      # generic rank is the MAX over placements
            coordinates = [[F(rng.randint(-40, 40), rng.randint(1, 5))
                            for _ in range(dimension)] for _ in range(points)]
            framework, placed = complete_from(coordinates, dimension)
            nullity = infinitesimal_freedom(framework, placed)
            best = nullity if best is None else min(best, nullity)
        assert best == framework.trivial_freedom, (
            f"n={points} d={dimension}: nullity {best} but trivial_freedom "
            f"{framework.trivial_freedom}")

    def test_it_is_never_negative(self):
        for points in range(1, 10):
            for dimension in range(1, 6):
                framework = Framework(points, dimension, ())
                assert framework.trivial_freedom >= 0
                assert framework.trivial_freedom <= dimension * points


class TestBothLinearProxiesGiveConfidentWrongAnswers:
    """
    THIS IS THE FINDING. A repair that made these pass would be deleting the result.

    Independently derived blind by a separate agent on 2026-07-27, from the standard
    definitions with sympy, never having read this repository: double banana rank 17
    stable over five random realisations; degenerate triangle rigid because the two length
    circles are externally tangent.
    """

    DOUBLE_BANANA = (
        (2, 3), (2, 4), (3, 4),
        (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4),
        (5, 6), (5, 7), (6, 7),
        (0, 5), (0, 6), (0, 7), (1, 5), (1, 6), (1, 7),
    )

    def _banana(self, placement):
        placed = tuple(tuple(F(v) for v in p) for p in placement)
        constraints = tuple(
            (i, j, sum((placed[i][a] - placed[j][a]) ** 2 for a in range(3)))
            for i, j in self.DOUBLE_BANANA
        )
        return Framework(8, 3, constraints), placed

    def test_the_counting_proxy_says_rigid_and_it_hinges(self):
        framework, placed = self._banana(
            ((0, 0, 0), (0, 0, 5), (3, 1, 2), (1, 4, 1), (2, 2, 4),
             (-3, 1, 2), (-1, -4, 1), (-2, 2, 4)))
        assert len(framework.constraints) == 18
        assert framework.maxwell_freedom == 0, "3*8 - 6 - 18 = 0: counted rigid"
        internal = infinitesimal_freedom(framework, placed) - framework.trivial_freedom
        assert internal == 1, "and it has one internal degree of freedom"

    def test_the_flex_is_generic_and_not_an_unlucky_placement(self):
        placements = [
            ((0, 0, 0), (0, 0, 5), (3, 1, 2), (1, 4, 1), (2, 2, 4),
             (-3, 1, 2), (-1, -4, 1), (-2, 2, 4)),
            ((1, 2, 3), (2, 5, 11), (7, 1, 2), (1, 9, 4), (3, 2, 13),
             (-5, 3, 1), (-2, -7, 6), (-4, 5, 9)),
            ((F(1, 2), 0, 0), (F(-1, 3), 2, 7), (5, F(3, 2), 1), (2, 6, F(1, 5)),
             (F(7, 3), 1, 8), (-4, F(2, 3), 3), (-1, -5, F(9, 2)), (-3, 4, 6)),
        ]
        seen = set()
        for placement in placements:
            framework, placed = self._banana(placement)
            seen.add(infinitesimal_freedom(framework, placed)
                     - framework.trivial_freedom)
        assert seen == {1}

    def test_the_control_where_the_count_is_right(self):
        """One bipyramid alone: count 0, truth 0. The count is not always wrong."""
        placed = tuple(tuple(F(v) for v in p) for p in
                       ((0, 0, 0), (0, 0, 5), (3, 1, 2), (1, 4, 1), (2, 2, 4)))
        edges = ((2, 3), (2, 4), (3, 4),
                 (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4))
        constraints = tuple(
            (i, j, sum((placed[i][a] - placed[j][a]) ** 2 for a in range(3)))
            for i, j in edges)
        framework = Framework(5, 3, constraints)
        assert framework.maxwell_freedom == 0
        assert infinitesimal_freedom(framework, placed) - framework.trivial_freedom == 0

    def test_the_differential_proxy_says_flexible_and_it_is_rigid(self):
        menu = rigidity_menu(triangle(1, 1, 2))
        placement = menu.check(((F(0), F(0)), (F(1), F(0)), (F(2), F(0))))
        assert placement.satisfies, "the collinear placement meets all three lengths"
        assert placement.linearised_freedom == 1, "the rank offers a motion"
        assert menu.verdict == FORCED and menu.proved, "and there is nowhere to move"
        assert placement.degenerate, "the module flags the linearisation as untrustworthy"
        assert not placement, "and refuses to be truthy about it"

    def test_too_few_points_to_span_is_not_the_same_as_degenerate(self):
        """
        Two points can never affinely span three dimensions, and that is not a defect.

        ``degenerate`` asks whether the points span as much as this MANY of them could,
        which is ``min(d, n-1)``, not whether they span the ambient space. Comparing
        against ``d`` alone flags every two-point framework in 3D, and a warning that
        fires on ordinary input stops being read -- which is how a real one gets ignored.
        """
        menu = rigidity_menu(Framework(2, 3, ((0, 1, F(4)),)))
        placement = menu.check(((F(0), F(0), F(0)), (F(2), F(0), F(0))))
        assert placement.satisfies
        assert placement.affine_rank == 1
        assert not placement.degenerate
        assert placement

    def test_the_control_where_the_rank_is_right(self):
        menu = rigidity_menu(triangle(3, 5, 4))
        placement = menu.check(((F(0), F(0)), (F(3), F(0)), (F(0), F(4))))
        assert placement.satisfies and not placement.degenerate
        assert placement.linearised_freedom == 0
        assert placement


class TestSectionIsSecondClauseIsTotal:
    """Checking is decidable for any computable invariant. Deriving the menu was not."""

    def test_check_works_on_a_framework_whose_menu_is_undecidable(self):
        framework = Framework(4, 3, ((0, 1, F(1)), (1, 2, F(1)), (2, 3, F(1))))
        menu = rigidity_menu(framework)
        assert menu.verdict == UNDECIDED
        placed = ((F(0), F(0), F(0)), (F(1), F(0), F(0)),
                  (F(1), F(1), F(0)), (F(1), F(1), F(1)))
        assert menu.check(placed).satisfies

    def test_a_refusal_names_the_constraint_and_the_exact_error(self):
        menu = rigidity_menu(triangle(3, 5, 4))
        bad = menu.check(((F(0), F(0)), (F(3), F(0)), (F(0), F(5))))
        assert not bad.satisfies
        assert bad.violations
        for i, j, error in bad.violations:
            assert isinstance(error, F) and error != 0
        assert "off by" in bad.explain()

    def test_the_two_clauses_agree_where_both_apply(self):
        """
        Whatever the menu calls realisable, the check must accept a realisation of.

        The analogue of the linear module's test that every option the menu OFFERS passes
        the check the menu APPLIES. If these two ever disagreed, one of them would be
        lying about which rules it used.
        """
        rng = random.Random(4242)
        for _ in range(40):
            points, dimension = rng.randint(2, 5), rng.randint(1, 3)
            coordinates = [[F(rng.randint(-9, 9)) for _ in range(dimension)]
                           for _ in range(points)]
            framework, placed = complete_from(coordinates, dimension)
            menu = rigidity_menu(framework)
            assert menu.verdict == FORCED, "built from a real realisation, so realisable"
            assert menu.check(placed).satisfies


class TestTheCheckRefusesInputThatCanLie:
    def test_a_set_of_points_is_refused(self):
        menu = rigidity_menu(triangle(3, 5, 4))
        with pytest.raises(TypeError, match="ordered sequence"):
            menu.check({(F(0), F(0)), (F(3), F(0)), (F(0), F(4))})

    def test_a_float_coordinate_is_refused(self):
        menu = rigidity_menu(triangle(3, 5, 4))
        with pytest.raises(TypeError, match="int or Fraction"):
            menu.check(((0.0, 0.0), (3.0, 0.0), (0.0, 4.0)))

    def test_a_bool_coordinate_is_refused(self):
        """``True`` is an ``int`` and would silently place a point at 1."""
        menu = rigidity_menu(triangle(1, 1, 2))
        with pytest.raises(TypeError, match="int or Fraction"):
            menu.check(((False, False), (True, False), (2, 0)))

    def test_wrong_point_count_and_wrong_dimension_are_refused(self):
        menu = rigidity_menu(triangle(3, 5, 4))
        with pytest.raises(ValueError, match="declares 3"):
            menu.check(((F(0), F(0)), (F(3), F(0))))
        with pytest.raises(ValueError, match="coordinates"):
            menu.check(((F(0), F(0), F(0)), (F(3), F(0), F(0)), (F(0), F(4), F(0))))


class TestTheFrameworkRefusesMalformedDeclarations:
    def test_a_float_length_is_refused(self):
        with pytest.raises(TypeError, match="exact rationals"):
            Framework(2, 2, ((0, 1, 1.5),))

    def test_a_negative_squared_length_is_refused(self):
        with pytest.raises(ValueError, match="not the square"):
            Framework(2, 2, ((0, 1, F(-1)),))

    def test_an_unordered_or_repeated_pair_is_refused(self):
        with pytest.raises(ValueError, match="i < j"):
            Framework(2, 2, ((1, 0, F(1)),))
        with pytest.raises(ValueError, match="more than once"):
            Framework(3, 2, ((0, 1, F(1)), (0, 1, F(4))))

    def test_an_out_of_range_index_is_refused(self):
        with pytest.raises(ValueError, match="outside"):
            Framework(2, 2, ((0, 5, F(1)),))

    def test_an_incomplete_set_refuses_to_invent_the_missing_distance(self):
        framework = Framework(3, 2, ((0, 1, F(1)),))
        with pytest.raises(ValueError, match="inventing"):
            framework.squared_matrix()


class TestTheAdversarialFindingsOf20260727:
    """
    Five defects found by pointing an adversary at this module the day it was written.
    Every brick in this project has shipped one; the budget is for it, not against it.
    """

    def test_a_generator_of_constraints_cannot_be_silently_exhausted(self):
        """
        The validation loop consumed it, and the field then held a spent iterator.

        ``rigidity_matrix`` produced ZERO rows and ``infinitesimal_freedom`` answered
        ``d*n`` -- every direction free -- for a framework carrying three real constraints,
        with no exception anywhere. A confident wrong answer from a public function.
        """
        def constraints():
            yield (0, 1, F(1))
            yield (1, 2, F(1))
            yield (0, 2, F(4))

        framework = Framework(3, 2, constraints())
        assert len(framework.constraints) == 3
        placed = ((F(0), F(0)), (F(1), F(0)), (F(2), F(0)))
        assert infinitesimal_freedom(framework, placed) < 2 * 3
        assert len(rigidity_matrix(framework, placed)) == 3

    def test_a_list_of_constraints_cannot_be_mutated_afterwards(self):
        """
        ``frozen=True`` stops the field being reassigned, not the caller's list changing.

        The same object answered FORCED and then UNDECIDED after an external append, and
        ``hash()`` raised, so the value semantics a frozen dataclass exists for were gone.
        """
        mutable = [(0, 1, F(1)), (1, 2, F(1)), (0, 2, F(4))]
        framework = Framework(3, 2, mutable)
        before = rigidity_menu(framework).verdict
        mutable.append((0, 1, F(999)))
        assert rigidity_menu(framework).verdict == before
        assert isinstance(framework.constraints, tuple)
        hash(framework)

    def test_a_locally_collinear_subframework_clears_the_degeneracy_flag(self):
        """
        THE FLAG IS SUFFICIENT AND NOT NECESSARY, and this records the counterexample.

        Three points collinear at lengths 1, 1, 2 -- the module's own worked case -- plus
        a fourth off the line. The whole set spans the plane, so ``degenerate`` stays
        False, and the linearised freedom is still 1 for a framework that is rigid.

        This test asserts the DEFECT's shape, not its absence, because there is no cheap
        local test that would close it. What it pins is that the module no longer CLAIMS
        to have closed it: ``conclusive`` is False here, and ``explain()`` says so.
        """
        points = ((F(0), F(0)), (F(1), F(0)), (F(2), F(0)), (F(0), F(1)))
        edges = ((0, 1), (1, 2), (0, 2), (0, 3), (2, 3))
        constraints = tuple(
            (i, j, sum((points[i][a] - points[j][a]) ** 2 for a in range(2)))
            for i, j in edges)
        menu = rigidity_menu(Framework(4, 2, constraints))
        placement = menu.check(points)

        assert placement.satisfies
        assert not placement.degenerate, "the global span test cannot see the local one"
        assert placement.linearised_freedom == 1, "and the rank still offers a motion"
        assert not placement.conclusive, "so the module reports the reading as inconclusive"
        assert "INCONCLUSIVE" in placement.explain()

    def test_conclusive_is_the_one_directional_claim_that_survives(self):
        """Zero linearised freedom implies rigid. Nonzero implies nothing."""
        rigid = rigidity_menu(triangle(3, 5, 4)).check(
            ((F(0), F(0)), (F(3), F(0)), (F(0), F(4))))
        assert rigid.linearised_freedom == 0
        assert rigid.conclusive

        tight = rigidity_menu(triangle(1, 1, 2)).check(
            ((F(0), F(0)), (F(1), F(0)), (F(2), F(0))))
        assert tight.linearised_freedom == 1
        assert not tight.conclusive, "nonzero freedom certifies nothing either way"

    def test_a_chiral_configuration_and_its_mirror_share_one_distance_matrix(self):
        """
        "There is exactly one option" is true up to ISOMETRY and O(d) contains reflections.

        In chemistry the two are enantiomers -- different substances. The declared
        invariant cannot see the distinction, which is the same boundary as ``Na(*)`` and
        ``Na`` presenting identical composition columns.
        """
        points = ((F(0), F(0), F(0)), (F(4), F(0), F(0)),
                  (F(1), F(3), F(0)), (F(1), F(1), F(2)))
        framework, placed = complete_from(points, 3)
        menu = rigidity_menu(framework)
        assert menu.verdict == FORCED and menu.embedding_dimension == 3

        mirrored = tuple((x, y, -z) for x, y, z in placed)
        assert menu.check(mirrored).satisfies, "the mirror meets every declared length"
        assert mirrored != placed, "and it is a different configuration"
        assert "enantiomers" in menu.reason

    def test_a_lying_length_cannot_smuggle_an_extra_coordinate(self):
        class Liar(tuple):
            def __len__(self):
                return 2

        menu = rigidity_menu(triangle(3, 5, 4))
        with pytest.raises(ValueError, match="coordinates"):
            menu.check((Liar((F(0), F(0), F(9))), (F(3), F(0)), (F(0), F(4))))

    def test_malformed_constraint_entries_are_refused(self):
        with pytest.raises(TypeError, match="3-tuple"):
            Framework(3, 2, ((0, 1),))
        with pytest.raises(TypeError, match="indices must be int"):
            Framework(3, 2, ((0, F(1), F(1)),))
        with pytest.raises(TypeError, match="indices must be int"):
            Framework(3, 2, ((False, True, F(1)),))

    def test_bool_is_refused_for_the_scalar_fields_too(self):
        with pytest.raises(ValueError, match="positive int"):
            Framework(True, 2, ())
        with pytest.raises(ValueError, match="positive int"):
            Framework(2, True, ())


class TestTheInheritedStoichiometryDefects:
    """
    Two claims in ``stoichiometry.py`` that were false until 2026-07-27, both proven by
    adversarial review rather than by the module's own tests.
    """

    def test_an_atom_label_colliding_with_the_charge_row_is_refused(self):
        """
        ``CHARGE_ROW`` claimed to be "deliberately unspellable" as an element symbol.

        It was not: ``Molecule`` requires only a non-empty string. The collision produced
        row labels ``('(charge)', '(charge)')`` for two structurally different conserved
        quantities, and ``Written.explain`` then reported them as ``(charge) off by +1;
        (charge) off by +1`` -- indistinguishable, in the message whose documented job is
        to name which quantity failed.
        """
        colliding = Molecule.atom(CHARGE_ROW)
        with pytest.raises(ValueError, match="reserved label"):
            composition_matrix((colliding, Molecule.carrier(charge=-1)))

    def test_explain_reports_the_element_rows_by_position(self):
        """The filter is no longer a string comparison against the sentinel."""
        menu = stoichiometry_menu((H2, O2, H2O))
        text = menu.explain()
        assert "atom counts for H, O" in text
        assert "(none)" not in text

    def test_explain_does_not_depend_on_how_the_last_row_is_spelled(self):
        """
        Reached by a route ``explain`` does not control, because it has to be.

        ``composition_matrix`` now REFUSES a colliding atom label, so no public input can
        put two ``(charge)`` labels into a menu any more -- which means a test that goes
        through the constructor cannot tell the position filter from the string filter.
        They agree on every input the constructor still admits. The two fixes are
        independent defences and this exercises the second one directly, by building the
        menu whose labels collide and asking only what ``explain`` does with them.
        """
        menu = StoichiometryMenu(
            species=(Molecule.carrier(charge=1), Molecule.carrier(charge=-1)),
            row_labels=(CHARGE_ROW, CHARGE_ROW),
            matrix=((1, 1), (1, -1)),
            rank=2, freedom=0, completions=(), unconstrained=(),
        )
        text = menu.explain()
        assert f"atom counts for {CHARGE_ROW}" in text, (
            "the element row was taken by position, so it survives being spelled like "
            "the charge row")
        assert "(none)" not in text, (
            "a string filter strips both labels and claims there are no atom invariants "
            "at all, for a matrix that has one")

    def test_the_derived_path_cannot_allocate_without_bound(self):
        """
        The weight cap guarded only what a scientist WROTE, never what the module DERIVED.

        Measured on the unguarded code: two carriers with six-digit charges produced a
        kernel vector of weight 1,999,936 and cost 4.2 s and 215 MB; ten-digit charges
        extrapolate to roughly seventy minutes and two hundred gigabytes.
        """
        species = (Molecule.carrier(label="X", charge=999_937),
                   Molecule.carrier(label="Y", charge=999_999))
        with pytest.raises(ValueError, match="refusing to materialise"):
            stoichiometry_menu(species)

    def test_ordinary_chemistry_is_unaffected_by_the_cap(self):
        menu = stoichiometry_menu((H2, O2, H2O))
        assert menu.freedom == 1
        assert menu.completions
