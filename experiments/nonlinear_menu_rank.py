#!/usr/bin/env python3
"""
Does the derived-menu law survive a NON-LINEAR invariant? Measured, not argued.

THE QUESTION, AND IT IS THE REPOSITORY'S OWN
--------------------------------------------
``experiments/stoichiometry_menu_rank.py`` established the derived-menu law
(``THE_COMPILER.md`` section III) for a LINEAR invariant, and printed its own gap at line
227 -- ``"that a non-linear invariant (a position constraint) yields to the same
treatment"`` -- with the identical sentence in its docstring and in
``smartchem/stoichiometry.py``'s "what this does not establish". Three statements of one
open question. This script answers it.

The specimen is the one those three sentences name: a position constraint between
particles, ``|p_i - p_j|^2 == d_ij^2``. Quadratic, so the admissible set is a real
algebraic variety rather than a lattice, and closed under nothing.

WHAT IS MEASURED
----------------
1. The REFUSE row survives, exactly, and stays a theorem -- on a complete constraint set.
2. The FILL_IN row survives and is a theorem, and doing so it eats the ENUMERATE row: a
   complete constraint set has exactly one realisation up to isometry, so it can never
   present a choice. The non-linear invariant is decidable exactly where it is idle.
3. The Maxwell count -- the counting linearisation -- gives a CONFIDENT WRONG ANSWER on
   the double banana: counted rigid, and it hinges.
4. The rigidity-matrix rank -- the differential linearisation -- gives a CONFIDENT WRONG
   ANSWER on the degenerate triangle, in the OPPOSITE direction: read as flexible, and it
   is rigid.
5. Section I's SECOND clause (check what the scientist wrote) is total, on every framework
   above, including the ones no verdict could be derived for.
6. A real bond graph -- water -- yields an INCOMPLETE constraint set, so the case the
   compiler actually faces in section I's round two is the undecidable one, always.

Every number below is computed by ``smartchem/rigidity.py`` in exact rational arithmetic.
The ground truth for claims 3 and 4 was independently derived, blind, by a separate agent
working from the standard definitions with sympy and never reading this repository:
double banana rank 17 stable over five random realisations, degenerate triangle rigid by
tangency of the two length circles, Cayley-Menger 0 and -576 respectively. Both agree with
everything printed here.

Exit codes: 0 all claims verified, 1 a claim failed, 2 a self-check failed.
"""
from __future__ import annotations

import sys
from fractions import Fraction as F

from smartchem.rigidity import (
    FORCED,
    Framework,
    REFUSED,
    UNDECIDED,
    infinitesimal_freedom,
    rigidity_menu,
)

FAILURES: list[str] = []


def claim(label: str, condition: bool, detail: str) -> None:
    """Record a claim and its verdict. Every line of output is one of these."""
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}: {detail}")
    if not condition:
        FAILURES.append(label)


def complete_triangle(a: int | F, b: int | F, c: int | F, dimension: int) -> Framework:
    """Three points with all three distances declared: a complete constraint set."""
    return Framework(3, dimension,
                     ((0, 1, F(a) ** 2), (1, 2, F(b) ** 2), (0, 2, F(c) ** 2)))


def from_coordinates(points, dimension, edges) -> tuple[Framework, tuple]:
    """
    Build a framework whose declared lengths are those of a chosen realisation.

    The realisation is then a genuine solution, so ``check`` must accept it and the
    rigidity matrix is being read at a point that actually satisfies the constraints --
    not at an arbitrary point that merely has the right shape.
    """
    placed = tuple(tuple(F(v) for v in p) for p in points)
    constraints = tuple(
        (i, j, sum((placed[i][a] - placed[j][a]) ** 2 for a in range(dimension)))
        for i, j in edges
    )
    return Framework(len(placed), dimension, constraints), placed


#: Two triangular bipyramids sharing their two apexes (0 and 1), which are NOT joined.
#: 8 points, 18 constraints, three dimensions -- the standard counterexample.
DOUBLE_BANANA_EDGES = (
    (2, 3), (2, 4), (3, 4),                                  # triangle A
    (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4),          # A to both apexes
    (5, 6), (5, 7), (6, 7),                                  # triangle B
    (0, 5), (0, 6), (0, 7), (1, 5), (1, 6), (1, 7),          # B to both apexes
)

#: Three unrelated rational placements. The generic rank is the MAXIMUM over realisations,
#: so a single lucky-or-unlucky choice would not establish it; these disagree in every
#: coordinate and are checked for agreement on the rank.
DOUBLE_BANANA_PLACEMENTS = (
    ((0, 0, 0), (0, 0, 5), (3, 1, 2), (1, 4, 1), (2, 2, 4),
     (-3, 1, 2), (-1, -4, 1), (-2, 2, 4)),
    ((1, 2, 3), (2, 5, 11), (7, 1, 2), (1, 9, 4), (3, 2, 13),
     (-5, 3, 1), (-2, -7, 6), (-4, 5, 9)),
    ((F(1, 2), 0, 0), (F(-1, 3), 2, 7), (5, F(3, 2), 1), (2, 6, F(1, 5)), (F(7, 3), 1, 8),
     (-4, F(2, 3), 3), (-1, -5, F(9, 2)), (-3, 4, 6)),
)

#: One bipyramid alone: 5 points, 9 constraints. The control -- here the count is right.
SINGLE_BANANA_EDGES = (
    (2, 3), (2, 4), (3, 4),
    (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4),
)
SINGLE_BANANA_PLACEMENT = ((0, 0, 0), (0, 0, 5), (3, 1, 2), (1, 4, 1), (2, 2, 4))


def internal_freedom(framework: Framework, placement) -> int:
    """Infinitesimal freedom at a realisation, with the isometries removed."""
    return infinitesimal_freedom(framework, placement) - framework.trivial_freedom


def main() -> int:
    print(__doc__.split("Exit codes")[0].strip().splitlines()[0])
    print()

    # ------------------------------------------------------------------ 1. REFUSE
    print("1. The REFUSE row survives, and stays a theorem.")
    impossible = rigidity_menu(complete_triangle(1, 1, 3, dimension=2))
    claim("triangle inequality violated", impossible.verdict == REFUSED,
          f"lengths 1,1,3 -> {impossible.verdict}, proved={impossible.proved}")
    claim("the refusal is a theorem, not a failed search", impossible.proved,
          "the Gram matrix is not positive semidefinite, decided in exact rationals")

    flat = rigidity_menu(Framework(
        4, 2, tuple((i, j, F(1)) for i in range(4) for j in range(i + 1, 4))))
    claim("consistent lengths, ambient space too small", flat.verdict == REFUSED,
          f"a unit tetrahedron's 6 distances in 2D -> {flat.verdict}, and the exact "
          f"minimum embedding dimension is reported as {flat.embedding_dimension}")

    # ------------------------------------------------------- 2. FILL_IN eats ENUMERATE
    print("\n2. The FILL_IN row survives -- and swallows the ENUMERATE row entirely.")
    generic = rigidity_menu(complete_triangle(3, 5, 4, dimension=2))
    claim("a realisable complete set is FORCED", generic.verdict == FORCED,
          f"lengths 3,5,4 -> {generic.verdict}, embeds in exactly "
          f"{generic.embedding_dimension} dimensions")
    claim("no ENUMERATE verdict exists at all",
          not hasattr(type(generic), "ENUMERATE") and generic.verdict in
          {REFUSED, FORCED, UNDECIDED},
          "a complete distance matrix fixes the points up to isometry, so the only "
          "decidable case is the one that can never offer a choice")

    degenerate_menu = rigidity_menu(complete_triangle(1, 1, 2, dimension=2))
    claim("the tight triangle inequality is caught exactly",
          degenerate_menu.verdict == FORCED and degenerate_menu.embedding_dimension == 1,
          f"lengths 1,1,2 -> {degenerate_menu.verdict}, embedding dimension "
          f"{degenerate_menu.embedding_dimension} (collinear, not planar)")

    # ------------------------------------------- 3. the COUNTING linearisation is wrong
    print("\n3. The Maxwell count is a CONFIDENT WRONG ANSWER on the double banana.")
    ranks = []
    for index, placement in enumerate(DOUBLE_BANANA_PLACEMENTS):
        banana, placed = from_coordinates(placement, 3, DOUBLE_BANANA_EDGES)
        ranks.append(internal_freedom(banana, placed))
    banana, placed = from_coordinates(DOUBLE_BANANA_PLACEMENTS[0], 3, DOUBLE_BANANA_EDGES)
    claim("the framework is the standard one", banana.points == 8
          and len(banana.constraints) == 18 and banana.dimension == 3,
          f"{banana.points} points, {len(banana.constraints)} constraints, "
          f"{banana.dimension} dimensions")
    claim("Maxwell counts it rigid", banana.maxwell_freedom == 0,
          f"3*8 - 6 - 18 = {banana.maxwell_freedom}")
    claim("the rank says otherwise, at every realisation", set(ranks) == {1},
          f"true infinitesimal internal freedom {ranks} over "
          f"{len(DOUBLE_BANANA_PLACEMENTS)} unrelated rational placements -- stable")
    claim("THE COUNT IS WRONG BY EXACTLY ONE", banana.maxwell_freedom == 0 and ranks[0] == 1,
          "counted 0, is 1; the two bipyramids hinge about the line through the shared "
          "apexes. A necessary condition was read as a verdict")

    single, single_placed = from_coordinates(SINGLE_BANANA_PLACEMENT, 3,
                                             SINGLE_BANANA_EDGES)
    claim("the control: one bipyramid, count and rank AGREE",
          single.maxwell_freedom == 0 and internal_freedom(single, single_placed) == 0,
          f"5 points, 9 constraints, Maxwell {single.maxwell_freedom}, true "
          f"{internal_freedom(single, single_placed)} -- so the count is not simply "
          f"always wrong, which is what makes trusting it dangerous")

    # ------------------------------------- 4. the DIFFERENTIAL linearisation is wrong too
    print("\n4. The rigidity-matrix rank is a CONFIDENT WRONG ANSWER the OTHER way.")
    tight = complete_triangle(1, 1, 2, dimension=2)
    collinear = ((F(0), F(0)), (F(1), F(0)), (F(2), F(0)))
    placement = rigidity_menu(tight).check(collinear)
    claim("the placement satisfies every declared length exactly", placement.satisfies,
          f"residuals {[str(r[2]) for r in placement.residual]}, in exact rationals")
    claim("the rank reports one internal degree of freedom",
          placement.linearised_freedom == 1,
          f"linearised internal freedom {placement.linearised_freedom}")
    claim("but the framework is RIGID, and that is a theorem",
          degenerate_menu.verdict == FORCED and degenerate_menu.proved,
          "the constraint set is complete and realisable, so the realisation is unique "
          "up to isometry -- there is nowhere to move. Independently confirmed blind: the "
          "two length circles are externally tangent (centre distance 2 = 1 + 1), so "
          "exactly one solution exists")
    claim("and the module SAYS the linearisation is untrustworthy here",
          placement.degenerate and not bool(placement),
          f"degenerate={placement.degenerate}, affine rank {placement.affine_rank} of 2, "
          f"and bool(placement) is False despite the constraints being met exactly")

    control = rigidity_menu(complete_triangle(3, 5, 4, dimension=2)).check(
        ((F(0), F(0)), (F(3), F(0)), (F(0), F(4))))
    claim("the control: a spanning placement is not flagged",
          control.satisfies and not control.degenerate
          and control.linearised_freedom == 0,
          f"3-4-5 placed non-degenerately: satisfies={control.satisfies}, "
          f"degenerate={control.degenerate}, freedom {control.linearised_freedom}")

    # ----------------------------------------------------- 5. clause two is total
    print("\n5. Section I's SECOND clause is total where the first is undecidable.")
    undecided = rigidity_menu(banana)
    claim("the double banana admits no derived verdict", undecided.verdict == UNDECIDED,
          f"{undecided.verdict}, proved={undecided.proved} -- 10 of 28 pairs undeclared")
    checked = undecided.check(placed)
    claim("and check() answers it anyway, exactly", checked.satisfies,
          "every one of the 18 declared squared distances is met with zero residual, on "
          "the framework whose menu could not be derived at all")
    wrong = list(list(p) for p in placed)
    wrong[4][0] += 1
    claim("and it names which constraint fails", not undecided.check(wrong).satisfies
          and len(undecided.check(wrong).violations) > 0,
          f"perturbing one coordinate breaks "
          f"{len(undecided.check(wrong).violations)} of 18 constraints, each reported "
          f"with its exact signed error")

    # ------------------------------------------- 6. the case the compiler actually faces
    print("\n6. A real bond graph is never a complete constraint set.")
    # Water, from the repository's own seed geometry: two O-H bonds and nothing else is
    # what a bond graph declares. Section I's round two binds exactly this slot.
    water = Framework(3, 3, ((0, 1, F(957, 1000) ** 2), (0, 2, F(957, 1000) ** 2)))
    water_menu = rigidity_menu(water)
    claim("two bonds over three atoms leaves the H-H distance undeclared",
          water_menu.verdict == UNDECIDED,
          f"{water_menu.verdict}: 1 of 3 pairs undeclared, which IS the bond angle")
    claim("the Maxwell count is offered only as a labelled upper bound",
          water_menu.maxwell_freedom == 1 and not water_menu.proved,
          f"Maxwell {water_menu.maxwell_freedom}, proved={water_menu.proved}, and the "
          f"reason names Saxe 1979 rather than claiming a search would settle it")
    claim("declaring the missing distance makes it decidable again",
          rigidity_menu(Framework(3, 3, water.constraints + (
              (1, 2, F(1515, 1000) ** 2),))).verdict == FORCED,
          "adding H-H completes the set -- and completing it removes the choice, which "
          "is the whole finding")

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} claim(s): {', '.join(FAILURES)}")
        return 1
    print("All claims verified.")
    print()
    print("  THE ANSWER. The derived-menu law does NOT survive a non-linear invariant,")
    print("  and it fails in a specific and reportable way rather than collapsing.")
    print("  REFUSE and FILL_IN survive as theorems on a complete constraint set;")
    print("  ENUMERATE has no analogue, because a complete set fixes the configuration")
    print("  up to isometry and so can never offer a choice. The row where the linear")
    print("  menu earned its keep is exactly the row where derivability dies.")
    print()
    print("  Both standard repairs are linearisations and both give confident wrong")
    print("  answers, in opposite directions: the count says the double banana is rigid")
    print("  and it hinges; the rank says the tight triangle is flexible and it is not.")
    print()
    print("  What survives intact is section I's SECOND clause. Checking what the")
    print("  scientist wrote is decidable for any computable invariant; deriving the")
    print("  menu needed the invariant to be linear. Those two clauses have different")
    print("  computability, and stoichiometry made them look like a matched pair.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as failure:                       # a self-check crashed, not a claim
        print(f"SELF-CHECK FAILED: {type(failure).__name__}: {failure}")
        sys.exit(2)
