"""
The derived-menu law against a NON-LINEAR invariant: a position constraint.

``smartchem.stoichiometry`` implements ``THE_COMPILER.md`` section III's derived-menu law
for a LINEAR invariant, and says so in its own "what this does not establish" section, in
the same words the harness prints at ``experiments/stoichiometry_menu_rank.py:227``::

    A position constraint between two particles is not obviously linear in anything, and
    nothing here says it yields to the same treatment.

This module is that sentence, discharged. It declares the position constraint, applies the
same law, and reports which clauses of the law survive. The answer is not "yes" and it is
not "no", and the shape of the partial answer is the finding.

THE TWO INVARIANTS, SIDE BY SIDE
--------------------------------
::

    linear        declared invariant  per-element atom counts, and net charge
                  declared operation  the saturated integer kernel of A
                  admissible set      ker(A) & Z^n -- a LATTICE
                  the menu            a basis; finite, complete, generates everything

    non-linear    declared invariant  pairwise squared distances |p_i - p_j|^2 == d_ij^2
                  declared operation  ...this is the whole problem
                  admissible set      a real ALGEBRAIC VARIETY, modulo the isometries
                  the menu            see below; there is usually no such thing

A lattice is closed under addition and has a finite basis that generates every point.
A variety is closed under nothing. Two configurations satisfying the declared lengths do
not add to a third, so "here are X options, everything else is a combination of them" is
not a weaker claim in the non-linear case -- it is a *meaningless* one. The presentation
that made the linear menu useful presupposes the algebra that the non-linear case lacks.

WHAT IS STILL EXACT, AND EXACTLY WHERE IT STOPS
-----------------------------------------------
A squared-distance matrix over a COMPLETE set of pairs is decidable, exactly, in rational
arithmetic. Anchor at point 0 and form the Gram matrix

    G[i][j] = (d_0i^2 + d_0j^2 - d_ij^2) / 2

The points embed in ``R^k`` for some k if and only if G is positive semidefinite, and the
least such k is ``rank(G)``. Both are decided by symmetric elimination over
``fractions.Fraction`` with no tolerance anywhere -- the same discipline, and for the same
reason, as ``stoichiometry`` refusing ``numpy.linalg.matrix_rank``. A floating-point PSD
test is a PSD test with a threshold, which is to say a *plausible* verdict.

So on a complete constraint set both of the interesting rows survive, and both are
theorems:

    not PSD, or rank(G) > d    the lengths are unrealisable in R^d     REFUSE
    PSD and rank(G) <= d       realisable, and UNIQUELY up to isometry  FORCED

The second row is a theorem too, and it is where the trouble starts. A complete distance
matrix pins the configuration up to congruence -- the Gram matrix determines the points up
to an orthogonal transformation, which is classical. So a complete constraint set never
yields a menu with more than one entry.

**"Up to isometry" is load-bearing there, and in this domain it costs something.** ``O(d)``
contains reflections, so a chiral configuration and its mirror image satisfy the same
complete distance set exactly. They are one point up to isometry and two up to
orientation-preserving rigid motion, and in chemistry that pair is a pair of enantiomers --
different substances, not different views of one. A distance matrix cannot distinguish
them, and lacking a mirror symmetry is the generic case rather than an edge case. So even
the one decidable row reports a distinction it cannot see, which is the same shape as
``Na(*)`` and ``Na`` presenting identical composition columns in the linear module.

**AND THAT IS THE FINDING. The non-linear invariant is derivable exactly where it is not
doing any work.** The linear menu earned its keep at ``freedom >= 2``, the row where the
scientist has a genuine choice. In the non-linear case that row is precisely the row where
the constraint set is INCOMPLETE, and an incomplete squared-distance matrix is where every
exact method here stops. Deciding whether a partial distance matrix is realisable in a
fixed dimension is NP-hard -- Saxe 1979, cited, not measured here -- so the failure is not
an implementation gap that a better afternoon would close.

Note what does NOT transfer, because it is the sharpest half. The linear method's
completeness never depended on how many invariants were declared: ``ker(A) & Z^n`` is the
complete admissible set whether A has one row or forty, and a short invariant list makes
the menu LONGER, never less derivable. Here, declaring fewer constraints does not widen a
derivable menu; it destroys derivability outright.

THE TWO LINEAR PROXIES, AND THEY ARE WRONG IN OPPOSITE DIRECTIONS
------------------------------------------------------------------
Faced with an incomplete constraint set, the standard moves are both linearisations, and
this module implements both so that their failures can be MEASURED rather than argued:

``maxwell_freedom`` counts unknowns minus equations minus the isometries. It is a
NECESSARY condition and nothing more. The double banana -- two triangular bipyramids
glued at their two apexes, 8 points and 18 constraints in three dimensions -- is counted
at exactly zero internal freedom and is flexible; it hinges about the line through the
shared pair. See ``experiments/nonlinear_menu_rank.py`` for the measurement.

``infinitesimal_freedom`` is the rank of the rigidity matrix at a given configuration --
the Jacobian of the constraint map. It repairs the double banana and fails the other way.
At a configuration where the points do not affinely span the ambient space, the Jacobian
loses rank and reports a motion that the framework cannot perform: the degenerate triangle
with lengths 1, 1, 2 is read as having one internal degree of freedom, and it has none,
because those three lengths admit exactly one configuration up to isometry and the triangle
inequality is tight.

**A rank taken on a linearisation is a statement about the linearisation.** This repository
has already paid for that sentence once, at the value layer rather than the design layer:
``geometry.py:604`` documents 0.0476 eV of zero-point energy lost when a physically linear
molecule carrying a ten-millionth of an Angstrom of numerical noise was assigned six
external modes instead of five, and a real vibration vanished with no warning. The external
modes of ``_external_modes`` ARE the trivial infinitesimal motions of a framework; the
degenerate configurations of this module are the collinear geometries of that one. Same
phenomenon, two storeys apart, and nothing in the repository connected them until now.

WHAT SURVIVES INTACT: SECTION I'S SECOND CLAUSE
------------------------------------------------
*"Choose one, or write one and I will check it against the same rules."* The second clause
does not care that the invariant is non-linear. Evaluating ``|p_i - p_j|^2 - d_ij^2`` at a
written configuration is exact arithmetic and always terminates, so :meth:`RigidityMenu.check`
is total where :func:`rigidity_menu` is mostly undecided.

That asymmetry is the clean statement of the result. **The two clauses of section I have
different computability, and linearity was what made them look like a matched pair.** A
compiler built on the stoichiometric case would inherit the assumption that being able to
check implies being able to enumerate, and that assumption is an accident of the friendly
invariant.

:meth:`RigidityMenu.check` also reports ``degenerate``, which is the analogue of
``Written.unverifiable``: the configuration satisfies every declared length AND sits at a
point where the linearisation is not to be trusted. Satisfying the constraints and being a
place you may safely differentiate are two claims, and this module keeps them apart for the
same reason ``stoichiometry`` keeps ``admissible`` apart from ``verified``.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb

# The rank of a declared constraint matrix, computed exactly. This is the SAME object as
# the rank of a composition matrix -- an exact row reduction over Fraction -- and the
# derived-menu law's own argument against a second checker applies to it: a second
# elimination here would be a second thing to keep in sync, and the day it drifted one of
# the two modules would be reporting a rank the other would not recognise.
from .stoichiometry import _rref

__all__ = [
    "Framework",
    "Placement",
    "RigidityMenu",
    "gram_matrix",
    "infinitesimal_freedom",
    "psd_rank",
    "rigidity_matrix",
    "rigidity_menu",
]

#: Verdict tokens. The first two are theorems; the third is an admission.
REFUSED = "REFUSED"
FORCED = "FORCED"
UNDECIDED = "UNDECIDED"


# There is deliberately NO exception class for unrealisable lengths. The first draft
# exported one and nothing ever raised it: unrealisability is a VERDICT here (``REFUSED``,
# carrying its reason and its proof status), not an error, and an exported exception that
# no code path can produce is the same species as the retry that never retried -- a
# documented safety net doing nothing, which reads as coverage until someone checks.


@dataclass(frozen=True)
class Framework:
    """
    A declared position constraint: ``points`` particles in ``dimension`` dimensions.

    ``constraints`` are ``(i, j, squared_length)`` with ``i < j``, at most one per pair.
    Lengths are SQUARED and exact: a bond length of 1.143 Angstrom is
    ``Fraction(1143, 1000) ** 2``, not a float. The squaring is not a convenience -- the
    constraint ``|p_i - p_j|^2 == d^2`` is polynomial in the coordinates while
    ``|p_i - p_j| == d`` is not, and every exact method below needs the polynomial form.
    """
    points: int
    dimension: int
    constraints: tuple[tuple[int, int, Fraction], ...]

    def __post_init__(self) -> None:
        if isinstance(self.points, bool) or not isinstance(self.points, int) \
                or self.points < 1:
            raise ValueError(f"points must be a positive int, got {self.points!r}")
        if isinstance(self.dimension, bool) or not isinstance(self.dimension, int) \
                or self.dimension < 1:
            raise ValueError(f"dimension must be a positive int, got {self.dimension!r}")

        # MATERIALISE FIRST, VALIDATE SECOND, AND STORE THE MATERIALISED COPY.
        #
        # The first version validated whatever it was handed and kept the caller's object.
        # Two confirmed defects followed, both found by adversarial review on 2026-07-27:
        #
        #   a GENERATOR was consumed by the validation loop itself, so the field then held
        #   a spent iterator. ``rigidity_matrix`` iterates it and produced ZERO rows, and
        #   ``infinitesimal_freedom`` reported d*n -- "every direction is free" -- for a
        #   framework with three real constraints, silently, with no exception anywhere.
        #
        #   a LIST passed too, and ``frozen=True`` stops the field being REASSIGNED while
        #   doing nothing about the caller mutating the object it still points at. The same
        #   Framework returned FORCED and then UNDECIDED after an external append, and
        #   ``hash()`` raised, quietly costing the value semantics a frozen dataclass is
        #   asked for in the first place. This repository has already been bitten once by
        #   an object that was not the value it looked like -- see the fingerprint that
        #   ignored the wrapped oracle -- so the copy is not paranoia.
        #
        # ``tuple()`` on a tuple is the identity, so this costs nothing in the normal case.
        object.__setattr__(self, "constraints", tuple(self.constraints))

        seen: set[tuple[int, int]] = set()
        for entry in self.constraints:
            if not isinstance(entry, tuple) or len(entry) != 3:
                raise TypeError(
                    f"each constraint must be a 3-tuple (i, j, squared_length), got "
                    f"{entry!r}")
            i, j, squared = entry
            if isinstance(i, bool) or isinstance(j, bool) \
                    or not isinstance(i, int) or not isinstance(j, int):
                raise TypeError(
                    f"constraint indices must be int, got ({i!r}, {j!r}). A float or "
                    f"Fraction index fails much later with a bare indexing error, which "
                    f"names neither the constraint nor the reason")
            if not (0 <= i < self.points and 0 <= j < self.points):
                raise ValueError(
                    f"constraint ({i}, {j}) indexes a point outside 0..{self.points - 1}")
            if i >= j:
                raise ValueError(
                    f"constraint ({i}, {j}) must be given with i < j; an unordered pair "
                    f"written two ways is two rows for one physical constraint, and the "
                    f"count of rows is what every proxy in this module is built on")
            if (i, j) in seen:
                raise ValueError(f"pair ({i}, {j}) is constrained more than once")
            seen.add((i, j))
            if not isinstance(squared, Fraction):
                raise TypeError(
                    f"squared length for ({i}, {j}) is {squared!r} of type "
                    f"{type(squared).__name__}; distances here are exact rationals. A "
                    f"float length makes 'the residual is exactly zero' undecidable, and "
                    f"this module's whole claim is that the refusals are theorems")
            if squared < 0:
                raise ValueError(
                    f"squared length for ({i}, {j}) is {squared}, which is negative and so "
                    f"is not the square of any distance")

    @property
    def complete(self) -> bool:
        """True when every pair of points carries a declared length."""
        return len(self.constraints) == comb(self.points, 2)

    @property
    def trivial_freedom(self) -> int:
        """
        The dimension of the isometry group's ORBIT: motions that move no distance at all.

        ``d(d+1)/2`` once the points can affinely span the ambient space, and less when
        there are too few of them for every rotation to do anything -- a single point in
        three dimensions has three translations and a whole ``SO(3)`` that fixes it. The
        subtracted term is the stabiliser: points spanning a ``k``-dimensional affine
        subspace are held pointwise by ``SO(d - k)``, of dimension ``(d-k)(d-k-1)/2``.

        THE FIRST VERSION WAS ``min(d*n - comb(n, 2), d*(d+1)//2)`` AND IT WENT NEGATIVE.
        At eight points in three dimensions that first term is ``24 - 28 = -4``, so every
        freedom derived from it was ten too large. It was caught by
        ``experiments/nonlinear_menu_rank.py`` asserting the double banana's Maxwell count
        equals zero -- an ABSOLUTE value. The neighbouring claim in the same script, that
        the single banana's count and rank AGREE, passed the whole time: the error entered
        both sides through this one term and cancelled. **A relational check between two
        quantities that share a term cannot see an error in that term**, which is the same
        family as everything in [[checks-derived-from-their-own-subject]] and is why the
        control asserts its numbers rather than only their agreement.
        """
        d, n = self.dimension, self.points
        spanned = min(n - 1, d)
        free = d - spanned
        return d * (d + 1) // 2 - free * (free - 1) // 2

    @property
    def maxwell_freedom(self) -> int:
        """
        Unknowns minus equations minus isometries. **A necessary condition, not a verdict.**

        Counting says nothing about whether the equations are independent, and the double
        banana is the standard witness: 8 points, 18 constraints, three dimensions, count
        zero, and it hinges. Read this number as an upper bound that is often not attained
        and never as the freedom itself.
        """
        return self.dimension * self.points - self.trivial_freedom - len(self.constraints)

    def squared_matrix(self) -> tuple[tuple[Fraction, ...], ...]:
        """
        The full ``n x n`` squared-distance matrix. Requires :attr:`complete`.

        Raises rather than filling an undeclared pair with anything, because every value
        this module could invent for a missing distance would be a *plausible* one, and the
        derived-menu law is the rule against exactly that.
        """
        if not self.complete:
            missing = [pair for pair in combinations(range(self.points), 2)
                       if pair not in {(i, j) for i, j, _ in self.constraints}]
            raise ValueError(
                f"the constraint set is incomplete: {len(missing)} pair(s) undeclared, "
                f"first {missing[0]}. A squared-distance matrix cannot be formed without "
                f"inventing those entries, and an invented distance is precisely the "
                f"plausible option the derived-menu law forbids")
        table = [[Fraction(0)] * self.points for _ in range(self.points)]
        for i, j, squared in self.constraints:
            table[i][j] = table[j][i] = squared
        return tuple(tuple(row) for row in table)


def gram_matrix(
    squared: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    """
    The Gram matrix of the points relative to point 0, exactly.

    ``G[i][j] = (d_0i^2 + d_0j^2 - d_ij^2) / 2`` is the inner product
    ``(p_i - p_0) . (p_j - p_0)`` written purely in declared distances -- the polarisation
    identity, and the reason a distance problem can be answered by linear algebra at all
    once EVERY distance is declared. Shape is ``(n-1) x (n-1)``.
    """
    n = len(squared)
    return tuple(
        tuple((squared[0][i] + squared[0][j] - squared[i][j]) / 2
              for j in range(1, n))
        for i in range(1, n)
    )


def psd_rank(matrix: tuple[tuple[Fraction, ...], ...]) -> int | None:
    """
    ``rank`` if ``matrix`` is symmetric positive semidefinite, ``None`` if it is not.

    Exact symmetric elimination. Pivot on a positive diagonal entry and take the Schur
    complement; a negative diagonal entry refutes PSD immediately, and so does a zero
    diagonal entry whose row is not also zero -- the two-by-two minor ``[[0, x], [x, 0]]``
    has determinant ``-x^2``, so a nonzero off-diagonal in an otherwise dead row is a
    negative eigenvalue in disguise. That second case is the one a careless implementation
    drops, and dropping it turns "unrealisable" into a confident realisable.
    """
    n = len(matrix)
    work = [list(row) for row in matrix]
    rank = 0
    active = list(range(n))
    while active:
        pivot = next((k for k in active if work[k][k] > 0), None)
        if pivot is None:
            for k in active:
                if work[k][k] < 0:
                    return None
                if any(work[k][m] != 0 for m in active):
                    return None
            return rank
        active.remove(pivot)
        lead = work[pivot][pivot]
        for a in active:
            factor = work[a][pivot] / lead
            if factor:
                for b in active:
                    work[a][b] -= factor * work[pivot][b]
        rank += 1
    return rank


def rigidity_matrix(
    framework: Framework,
    coordinates: tuple[tuple[Fraction, ...], ...],
) -> tuple[tuple[Fraction, ...], ...]:
    """
    The Jacobian of the constraint map at ``coordinates``: one row per constraint.

    Row ``(i, j)`` carries ``p_i - p_j`` in the columns of point ``i`` and ``p_j - p_i`` in
    the columns of point ``j``. This is the derivative of ``|p_i - p_j|^2`` up to a factor
    of two, which is dropped because it scales every row alike and cannot change a rank.
    """
    d = framework.dimension
    rows = []
    for i, j, _ in framework.constraints:
        row = [Fraction(0)] * (d * framework.points)
        for axis in range(d):
            delta = coordinates[i][axis] - coordinates[j][axis]
            row[d * i + axis] = delta
            row[d * j + axis] = -delta
        rows.append(tuple(row))
    return tuple(rows)


def infinitesimal_freedom(
    framework: Framework,
    coordinates: tuple[tuple[Fraction, ...], ...],
) -> int:
    """
    ``d*n - rank`` of the rigidity matrix: every infinitesimal motion, trivial ones included.

    **This is a reading of a LINEARISATION at one point, not a property of the framework.**
    Subtract :attr:`Framework.trivial_freedom` for the internal count, and read even that
    with the caveat in this module's docstring: at a degenerate configuration the rank drops
    and this number reports motions the framework cannot actually perform.
    """
    matrix = rigidity_matrix(framework, coordinates)
    if not matrix:
        return framework.dimension * framework.points
    rank = len(_rref([list(row) for row in matrix])[1])
    return framework.dimension * framework.points - rank


def _exact(value, where: str) -> Fraction:
    """A coordinate, as an exact rational, or a loud refusal."""
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError(
            f"coordinate {where} is {value!r} of type {type(value).__name__}; coordinates "
            f"here must be int or Fraction. A float coordinate makes the residual "
            f"'exactly zero' undecidable -- 0.1 + 0.2 is not 0.3 -- and every verdict this "
            f"module returns is meant to be a theorem rather than a reading within a "
            f"tolerance")
    return Fraction(value)


@dataclass(frozen=True)
class Placement:
    """
    A configuration the scientist WROTE, judged by the constraints that derived the menu.

    Section I's second clause, for the non-linear invariant. ``residual`` carries the exact
    signed error ``|p_i - p_j|^2 - d_ij^2`` on every declared pair, so a refusal names which
    constraint fails and by how much rather than saying only *no*.

    ``degenerate`` is the analogue of ``Written.unverifiable`` and it is the whole reason
    this class is not a bare boolean. The points may satisfy every declared length and still
    sit where the constraint map's Jacobian loses rank -- at which point the linearised
    freedom is a statement about the linearisation, not about the framework. Satisfying the
    constraints and being safe to differentiate are two claims.

    **THE FLAG IS SUFFICIENT AND NOT NECESSARY, AND THE FIRST VERSION OF THIS DOCSTRING
    CLAIMED OTHERWISE.** ``degenerate`` tests whether the points span as much as this many
    of them could, which is a GLOBAL property, and adversarial review on 2026-07-27
    produced a framework where that is not enough: three points collinear with lengths
    1, 1, 2 -- the module's own worked counterexample -- plus a fourth point off the line.
    The whole set spans the plane, so the flag stays False, and ``linearised_freedom``
    still reports 1 for a framework that is rigid, because the tight sub-triangle is forced
    and the fourth point is then pinned by two distances. Confirmed against an independent
    numpy null-space computation sharing no code with ``_rref``.

    So the honest statement is the one-directional one, and it is worth more than the flag:

        ``linearised_freedom == 0``   the framework IS rigid. A theorem: infinitesimal
                                      rigidity implies continuous rigidity.
        ``linearised_freedom > 0``    NOTHING follows. It may be flexible; it may be rigid
                                      with the linearisation lying, and no cheap local test
                                      separates those.

    ``conclusive`` reports exactly that asymmetry. ``degenerate`` is demoted to what it
    always was: one detectable, common reason the second row is likely in play, never a
    certificate that it is not.
    """
    coordinates: tuple[tuple[Fraction, ...], ...]
    residual: tuple[tuple[int, int, Fraction], ...]
    violations: tuple[tuple[int, int, Fraction], ...]
    degenerate: bool
    affine_rank: int
    linearised_freedom: int

    @property
    def satisfies(self) -> bool:
        """Every declared squared distance is met exactly."""
        return not self.violations

    @property
    def conclusive(self) -> bool:
        """
        The linearised reading at this placement can be believed. A THEOREM when True.

        True exactly when the framework is infinitesimally rigid here, which IMPLIES it is
        rigid -- the implication runs one way only, so a ``False`` establishes nothing at
        all about flexibility. This is the claim that survived adversarial review;
        :attr:`degenerate` is the heuristic that did not.
        """
        return self.satisfies and self.linearised_freedom == 0

    @property
    def trustworthy(self) -> bool:
        """
        Satisfies the constraints, and no degeneracy was DETECTED. A weaker claim than
        it reads as: see :attr:`conclusive` and the class docstring.
        """
        return self.satisfies and not self.degenerate

    def __bool__(self) -> bool:
        """
        Truthy on :attr:`trustworthy` -- the constraints are met and nothing was flagged.

        Read this as "no objection was found", not as "the freedom count is right". The
        degeneracy detector is one-sided, so ``True`` here does not certify
        ``linearised_freedom``; only :attr:`conclusive` does, and only when it is zero.
        ``False`` remains the strong direction and is worth acting on: either the lengths
        are not met, or the linearisation is known to be unreliable.
        """
        return self.trustworthy

    def explain(self) -> str:
        if self.violations:
            # The sign is spelled out rather than asked for with a "+" format spec:
            # ``f"{Fraction(9):+}"`` RAISES, because Fraction only accepts float-style
            # specs and rejects a bare sign. That crash lived in ``explain()`` -- the one
            # method whose entire job is to make a refusal useful -- so the failure path
            # was the untested path, which is the usual way round.
            broken = "; ".join(
                f"|p{i} - p{j}|^2 off by {'+' if error > 0 else ''}{error}"
                for i, j, error in self.violations)
            return (f"REFUSED: what you placed does not meet the declared lengths. "
                    f"{broken}. These are the same constraints the menu was derived from, "
                    f"and the arithmetic is exact, so the errors are the errors and not a "
                    f"tolerance.")
        if self.degenerate:
            return (f"SATISFIED BUT DEGENERATE: every declared squared distance is met "
                    f"exactly, and the points affinely span only {self.affine_rank} of "
                    f"{len(self.coordinates[0])} dimensions. The constraint map's Jacobian "
                    f"loses rank on a set like this, so the linearised freedom reported "
                    f"here ({self.linearised_freedom}) counts directions the framework may "
                    f"well be unable to move in. The classic case is three points with "
                    f"lengths 1, 1, 2: the triangle inequality is tight, exactly one "
                    f"configuration exists up to isometry, and the linearisation still "
                    f"offers a motion. Ask for rigidity at a spanning configuration, or "
                    f"accept that the number above is about the derivative and not about "
                    f"the framework.")
        if self.conclusive:
            return ("SATISFIED AND CONCLUSIVE: every declared squared distance is met "
                    "exactly, in rational arithmetic with no tolerance, and the linearised "
                    "internal freedom is zero -- so the framework is rigid here, and that "
                    "is a theorem rather than a reading, because infinitesimal rigidity "
                    "implies rigidity.")
        return (f"SATISFIED, VERDICT INCONCLUSIVE: every declared squared distance is met "
                f"exactly, and no degeneracy was detected -- the points span as much as "
                f"{len(self.coordinates)} of them can. But the linearised internal freedom "
                f"is {self.linearised_freedom}, and a NONZERO linearised freedom "
                f"establishes nothing: infinitesimal rigidity implies rigidity and the "
                f"converse is false. The degeneracy test above is global, so it cannot see "
                f"a locally collinear sub-framework -- three points at lengths 1, 1, 2 "
                f"with a fourth off the line span the plane, clear this test, and still "
                f"report a motion that does not exist. Declare the remaining distances for "
                f"an exact verdict.")


@dataclass(frozen=True)
class RigidityMenu:
    """
    What the derived-menu law can and cannot assert about a position constraint.

    ``verdict`` is one of ``REFUSED``, ``FORCED``, ``UNDECIDED``. The first two are
    theorems and ``proved`` is True on them. ``UNDECIDED`` is the law's own required
    behaviour -- section III says a system that cannot enumerate the options must SAY so
    rather than improvise a plausible list -- and on a non-linear invariant it is the
    common case rather than the exceptional one.

    There is deliberately no ``ENUMERATE`` verdict. In the linear module that token means
    "here is a basis; every admissible point is an integer combination of these", and the
    admissible set here is not closed under any combination at all, so a token spelled the
    same way would be claiming something no method in this module establishes.
    """
    framework: Framework
    verdict: str
    proved: bool
    reason: str
    embedding_dimension: int | None
    maxwell_freedom: int

    def __bool__(self) -> bool:
        """True only when the constraints are known to be realisable. ``UNDECIDED`` is False."""
        return self.verdict == FORCED

    def check(self, coordinates: Sequence[Sequence]) -> Placement:
        """
        Section I's second clause. Total, exact, and indifferent to the verdict above.

        This method works on every framework, including the ones :func:`rigidity_menu`
        cannot decide. That is the asymmetry this module exists to record: checking a
        written answer is decidable for any computable invariant, while deriving the menu
        needed the invariant to be linear.
        """
        if not isinstance(coordinates, Sequence) or isinstance(coordinates, (str, bytes)):
            raise TypeError(
                f"coordinates must be an ordered sequence of points, got "
                f"{type(coordinates).__name__}. A set would pass a length check and then "
                f"be frozen in hash order, pairing point 3's position with point 0's "
                f"constraints and returning a confident wrong residual")
        d, n = self.framework.dimension, self.framework.points
        if len(coordinates) != n:
            raise ValueError(
                f"got {len(coordinates)} points, but this framework declares {n}")
        rows = []
        for index, point in enumerate(coordinates):
            if not isinstance(point, Sequence) or isinstance(point, (str, bytes)):
                raise TypeError(
                    f"point {index} must be an ordered sequence of {d} coordinates, got "
                    f"{type(point).__name__}")
            # Materialise FIRST and measure the result, never the reported length. An
            # object whose __len__ disagrees with what it yields passed the old check and
            # then either raised a bare IndexError downstream or quietly stored a
            # d+1-component "point"; the count that matters is the one that arrived.
            values = tuple(_exact(v, f"{index}[{axis}]")
                           for axis, v in enumerate(point))
            if len(values) != d:
                raise ValueError(
                    f"point {index} has {len(values)} coordinates; the framework is in "
                    f"{d} dimensions")
            rows.append(values)
        placed = tuple(rows)

        residual = tuple(
            (i, j,
             sum((placed[i][a] - placed[j][a]) ** 2 for a in range(d)) - squared)
            for i, j, squared in self.framework.constraints
        )
        violations = tuple(entry for entry in residual if entry[2] != 0)

        # Affine rank of the placed points, exactly: translate to point 0 and reduce.
        if n == 1:
            affine_rank = 0
        else:
            shifted = [[placed[i][a] - placed[0][a] for a in range(d)]
                       for i in range(1, n)]
            affine_rank = len(_rref(shifted)[1])
        degenerate = affine_rank < min(d, n - 1)

        return Placement(
            coordinates=placed,
            residual=residual,
            violations=violations,
            degenerate=degenerate,
            affine_rank=affine_rank,
            linearised_freedom=(infinitesimal_freedom(self.framework, placed)
                                - self.framework.trivial_freedom),
        )

    def explain(self) -> str:
        head = {
            REFUSED: "REFUSE, and the refusal is a THEOREM",
            FORCED: "FILL IT IN; there is nothing to choose",
            UNDECIDED: "CANNOT ENUMERATE, and says so",
        }[self.verdict]
        return f"{head}. {self.reason}"


def rigidity_menu(framework: Framework) -> RigidityMenu:
    """
    Apply the derived-menu law to a position constraint. Derive nothing that is not derived.

    On a COMPLETE constraint set this decides exactly, in rational arithmetic, and both
    outcomes are theorems. On an incomplete one it returns ``UNDECIDED`` carrying the
    Maxwell count as an explicitly-labelled upper bound -- because the alternative, dressing
    a count up as a freedom, is the confabulated menu the law exists to prevent, and the
    double banana is the standing proof that the count is not the freedom.
    """
    if not isinstance(framework, Framework):
        raise TypeError(f"expected a Framework, got {type(framework).__name__}")

    if not framework.complete:
        undeclared = comb(framework.points, 2) - len(framework.constraints)
        return RigidityMenu(
            framework=framework,
            verdict=UNDECIDED,
            proved=False,
            reason=(
                f"{undeclared} of {comb(framework.points, 2)} pairwise distances are "
                f"undeclared, so the squared-distance matrix is partial. Deciding whether "
                f"a partial distance matrix is realisable in a fixed dimension is NP-hard "
                f"(Saxe 1979), and no method in this module claims to. The Maxwell count "
                f"is {framework.maxwell_freedom}, which is an upper bound on the internal "
                f"freedom and is NOT the freedom: the double banana is counted at zero and "
                f"hinges. Declare the remaining distances for an exact verdict, or ask "
                f"check() about a specific configuration, which is always decidable."
            ),
            embedding_dimension=None,
            maxwell_freedom=framework.maxwell_freedom,
        )

    if framework.points == 1:
        return RigidityMenu(
            framework=framework, verdict=FORCED, proved=True,
            reason="one point, no constraints; the configuration is a point up to "
                   "translation.",
            embedding_dimension=0, maxwell_freedom=framework.maxwell_freedom)

    rank = psd_rank(gram_matrix(framework.squared_matrix()))
    if rank is None:
        return RigidityMenu(
            framework=framework, verdict=REFUSED, proved=True,
            reason=("the Gram matrix of the declared distances is not positive "
                    "semidefinite, so these lengths are realisable in no Euclidean space "
                    "of any dimension. The smallest instance is the violated triangle "
                    "inequality. This is the non-linear analogue of the linear module's "
                    "rank-0 row: a specification that verifiably cannot be satisfied, "
                    "where the impossibility is the result."),
            embedding_dimension=None, maxwell_freedom=framework.maxwell_freedom)

    if rank > framework.dimension:
        return RigidityMenu(
            framework=framework, verdict=REFUSED, proved=True,
            reason=(f"the declared distances are realisable, but only in {rank} dimensions, "
                    f"and this framework declares {framework.dimension}. The lengths are "
                    f"consistent; the ambient space is too small for them."),
            embedding_dimension=rank, maxwell_freedom=framework.maxwell_freedom)

    return RigidityMenu(
        framework=framework, verdict=FORCED, proved=True,
        reason=(f"every pairwise distance is declared and the Gram matrix is positive "
                f"semidefinite of rank {rank} <= {framework.dimension}, so a realisation "
                f"exists and is UNIQUE up to isometry -- the Gram matrix determines the "
                f"points up to an ORTHOGONAL transformation, reflections included. Note "
                f"what this costs twice over. A complete constraint set is the only case "
                f"decided here, and a complete constraint set can never present a choice. "
                f"AND 'up to isometry' is doing real work in that sentence: O(d) contains "
                f"reflections, so a CHIRAL configuration and its mirror image satisfy this "
                f"same distance set exactly and are not interconvertible by any rigid "
                f"motion. In chemistry those two are enantiomers -- different substances. "
                f"A distance matrix cannot tell them apart, so even this row hands back a "
                f"pair wherever the configuration lacks a mirror symmetry, which is the "
                f"generic case. Same boundary as identical composition columns in the "
                f"linear module: the declared invariants cannot see a real distinction."),
        embedding_dimension=rank, maxwell_freedom=framework.maxwell_freedom)
