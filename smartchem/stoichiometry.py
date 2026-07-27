"""
Derive the admissible balanced reactions over a candidate species set. Never guess them.

``conserves`` in ``smartchem.category`` is the CHECKER: hand it a ``Reaction`` and it
re-verifies that atom counts and net charge balance. This module is that function's
INVERSE. Hand it the species and it returns every balanced reaction they admit -- the
complete set, with completeness proved rather than asserted.

THE LAW THIS IMPLEMENTS
-----------------------
``THE_COMPILER.md`` section III states the derived-menu law: every option offered to a
scientist must be the image of a DECLARED INVARIANT under a DECLARED OPERATION, and a
system that cannot enumerate the options must say so rather than improvise a plausible
list. This module is the first executable instance of that law.

    declared invariant : per-element atom counts, and net charge
    declared operation : the saturated integer kernel of the composition matrix
    completeness       : the returned vectors GENERATE ker(A) & Z^n as a lattice

With one row per element (plus a charge row) and one column per candidate species, a
balanced reaction is an integer vector ``nu`` with ``A @ nu == 0``. The admissible
completions are ``ker A`` intersected with the integer lattice, of rank ``n - rank(A)``.
Three ranks give three behaviours, and the entire user experience falls out of which one
you are in:

    freedom == 0   no non-trivial balance exists     REFUSE, and the refusal is a THEOREM
    freedom == 1   forced up to sign and scale       FILL IT IN; asking would be theatre
    freedom >= 2   a genuine choice                  ENUMERATE; this is the menu

The ``freedom == 0`` row is the one worth having. It is the smallest complete instance of
a specification that verifiably cannot be satisfied, where the impossibility is the result
rather than a failure to search hard enough.

WHY THE ARITHMETIC IS EXACT
---------------------------
The rank is computed over ``fractions.Fraction`` and the kernel over the integers alone, by
unimodular column reduction. ``numpy.linalg.matrix_rank`` would be faster and would agree on
every case in this repository, but a floating-point rank is a rank with a tolerance -- which
is to say a *plausible* rank. A module whose entire claim is "derived, never approximated"
has no business resting on a singular-value threshold.

THE DEFECT THIS SHIPPED WITH, AND WHY IT IS RECORDED RATHER THAN QUIETLY PATCHED
--------------------------------------------------------------------------------
The first release of this module, on 2026-07-26, computed the kernel over the RATIONALS and
then cleared each basis vector's denominators independently. That is not a lattice
operation. It multiplies individual generators by integers, and the group they generate
shrinks to a proper sublattice of ``ker(A) & Z^n`` -- so balanced reactions existed that the
menu never listed and could not reconstruct, while ``explain()`` printed "every other one is
an integer combination of these".

The smallest case, found by adversarial review the same day::

    species  : (O2, H2O, H2O2, H2)
    returned : (1, 2, -2, 0) and (1, -2, 0, 2)
    omitted  : (1, 0, -1, 1), which is H2 + O2 -> H2O2, and A @ nu is exactly [0, 0, 0]
    why      : it is (b0 + b1)/2; every integer combination has an even third component

Two things about that are worth keeping in front of anyone who edits this file. First, it
was **order-dependent**: 4 of the 24 orderings of those same four species lost a reaction,
because argument order decides which columns become pivots and therefore where denominators
appear. Completeness was a lottery on the caller's argument order and nothing in the
signature said so.

Second, and worse: the test suite had a class named ``TestCompleteness`` that asserted no
completeness. Its two tests were ``len(completions) == freedom``, which the constructor
already raises on, and ``A @ nu == 0``, which is SOUNDNESS -- and soundness was never the
hard part. A mutant returning an index-2 sublattice passed 28 of the 29 tests. **The module
whose thesis is "a plausible wrong menu is worse than no menu" shipped one, and the guard
that should have caught it was named after the property it did not test.**

THE INDEPENDENT CHECK, AND WHY IT IS NOT ``conserves``
------------------------------------------------------
``conserves(reaction)`` is tautologically ``True`` for any ``Reaction`` that exists, because
``Reaction.__post_init__`` already raises ``ConservationError`` on an unbalanced pair. Its
own docstring says so. Calling it on a reaction this module just built would check nothing.

So the independent check is the CONSTRUCTOR. Every derived ``nu`` is turned into real
``Config`` objects and pushed through ``Reaction(...)``, whose balance test re-derives atom
counts by dictionary accumulation over ``Molecule.formula`` and never touches a
``Fraction``. Different arithmetic, different code path, same claim. If the kernel says a
vector balances and the constructor says it does not, that is a contradiction between two
independent derivations and this module RAISES rather than picking a winner -- see
``MenuContradiction``.

WHAT THIS DOES NOT ESTABLISH
----------------------------
That the derived-menu law generalises. Stoichiometry is the friendly case: the invariant is
LINEAR, so the completion set is a lattice and "complete" means "spans the kernel". A
position constraint between two particles is not obviously linear in anything, and nothing
here says it yields to the same treatment.

It also does not establish that a balanced reaction is a REAL one. Balance is necessary and
nowhere near sufficient: nothing here consults thermodynamics, kinetics, or an oracle. A
completion is a statement about bookkeeping, not about chemistry.

THE SHARPEST LIMIT, AND IT IS VISIBLE IN THE OUTPUT
---------------------------------------------------
A menu is complete with respect to the DECLARED invariants and not one inch further. A
species' COLUMN is the whole of what mass and charge conservation know about it, and there
are two ways for that to be too little.

An all-zero column is a species the invariants cannot distinguish from *nothing* -- which
is how this package spells a photon -- so it lies in the kernel by itself and the
enumeration dutifully offers ``photon -> (nothing)`` as balanced. Under mass and charge
alone, it is. Those invariants cannot see energy.

IDENTICAL columns are species the invariants cannot distinguish from *each other*, and this
case is the more dangerous of the two because it does not look like a boundary.
``category.Molecule`` deliberately keeps ``state`` out of the conserved signature so that
``Na(*) -> Na`` can be expressed at all, so an excited atom and a relaxed one present the
same column by design. The menu therefore finds freedom 1 and reports ``Na(*) -> Na`` under
the FILL_IN verdict -- "forced up to sign and scale; offering a choice would be theatre" --
which is a confident statement about de-excitation derived from invariants that cannot see
excitation. The first release flagged only the zero-column case and let this one through
wearing the strongest verdict in the vocabulary.

Neither is a bug to be special-cased away; both are the law reporting the exact boundary of
what it was given. Such species are named in ``StoichiometryMenu.unconstrained``, every
completion touching one is flagged ``unconstrained=True``, and ``explain()`` prints which
of the two kinds of blindness applies, so a caller can never mistake "balanced under the
declared invariants" for "physical".
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from math import gcd

from .category import Config, ConservationError, Molecule, Reaction

__all__ = [
    "MAX_WRITTEN_WEIGHT",
    "Completion",
    "MenuContradiction",
    "StoichiometryMenu",
    "Written",
    "composition_matrix",
    "integer_kernel_basis",
    "stoichiometry_menu",
]

#: Row label used for the net-charge row of the composition matrix.
#:
#: **This comment used to claim the string was "deliberately unspellable" as an element
#: symbol, and that was false.** ``Molecule.__post_init__`` requires only that an atom label
#: be a non-empty string -- ``category.py`` says in its own docstring that labels are
#: domain-neutral, which is a deliberate choice and not an oversight -- so
#: ``Molecule.atom("(charge)")`` was legal and produced a composition matrix whose row
#: labels read ``("(charge)", "(charge)")``: one genuine atom-count row and the charge row,
#: carrying one label. Both downstream readers then lied. ``explain()`` filtered on
#: ``label != CHARGE_ROW`` and printed "atom counts for (none)" while a real atom invariant
#: was still deriving the menu, and ``Written.explain()`` reported two structurally
#: different broken conservation laws as ``(charge) off by +1; (charge) off by +1`` --
#: textually indistinguishable, in the one message whose documented job is to name which
#: quantity failed so the repair is arithmetic rather than guesswork.
#:
#: The claim is now ENFORCED by :func:`composition_matrix` rather than assumed here, and
#: :meth:`StoichiometryMenu.explain` no longer depends on the string at all -- it takes the
#: element rows by POSITION, which is how ``composition_matrix`` builds them. Either fix
#: alone would close the reported symptom; both are kept because they are independent, and
#: a label collision would still be a real defect even in a version of this file that never
#: rendered a row name.
CHARGE_ROW = "(charge)"


class MenuContradiction(AssertionError):
    """
    Two independent derivations disagreed about whether a vector balances.

    Raised, never swallowed. The exact kernel arithmetic and ``Reaction``'s dictionary
    accumulation are separate code paths over separate number types; if they disagree, one
    of them is wrong and the caller is entitled to find out which rather than receive a
    quietly shortened menu.
    """


def _rref(rows: list[list[Fraction]]) -> tuple[list[list[Fraction]], list[int]]:
    """Exact reduced row echelon form. Returns the matrix and its pivot columns."""
    mat = [list(r) for r in rows]
    pivots: list[int] = []
    r = 0
    for c in range(len(mat[0]) if mat else 0):
        pivot = next((i for i in range(r, len(mat)) if mat[i][c] != 0), None)
        if pivot is None:
            continue
        mat[r], mat[pivot] = mat[pivot], mat[r]
        lead = mat[r][c]
        mat[r] = [x / lead for x in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][c] != 0:
                factor = mat[i][c]
                mat[i] = [a - factor * b for a, b in zip(mat[i], mat[r])]
        pivots.append(c)
        r += 1
        if r == len(mat):
            break
    return mat, pivots


def _oriented(vec: tuple[int, ...]) -> tuple[int, ...]:
    """
    Fix the sign of the first nonzero entry, and verify the vector is primitive.

    The gcd check is an internal consistency assertion rather than a normalisation step.
    :func:`integer_kernel_basis` produces these as columns of a unimodular matrix, and the
    columns of a unimodular matrix are primitive by construction -- they are a ``Z``-basis
    of ``Z^n``, and no basis vector of a lattice can be a proper multiple. A common factor
    would therefore mean the column reduction lost unimodularity, which is exactly the kind
    of silent arithmetic failure this module refuses to absorb.
    """
    common = reduce(gcd, (abs(v) for v in vec if v), 0)
    if common > 1:
        raise MenuContradiction(
            f"kernel vector {vec} has common factor {common}; the column reduction was "
            "not unimodular and the returned lattice cannot be trusted"
        )
    if next((v for v in vec if v), 0) < 0:
        return tuple(-v for v in vec)
    return vec


def composition_matrix(
    species: tuple[Molecule, ...],
) -> tuple[tuple[str, ...], tuple[tuple[int, ...], ...]]:
    """
    ``(row labels, matrix)`` for a candidate species set.

    One row per element present anywhere in the set, sorted, plus one final row for net
    charge labelled ``CHARGE_ROW``. One column per species, in the order given. The charge
    row is not optional: ``conserves`` tests atom counts AND charge, so a matrix without it
    would be the inverse of a weaker checker and would offer completions that
    ``Reaction`` then rejects.
    """
    elements = tuple(sorted({s for molecule in species for s in molecule.formula}))
    if CHARGE_ROW in elements:
        raise ValueError(
            f"an atom label equal to {CHARGE_ROW!r} was declared, which is the reserved "
            f"label for the net-charge row. Two structurally different conserved "
            f"quantities -- a count of that element, and total charge -- would share one "
            f"row name, and every diagnosis downstream names the row. A refusal that "
            f"cannot be told from another refusal is worse than no diagnosis, so this is "
            f"refused at the point the collision is created. Rename the label.")
    rows = [tuple(molecule.formula.get(element, 0) for molecule in species)
            for element in elements]
    rows.append(tuple(molecule.charge for molecule in species))
    return elements + (CHARGE_ROW,), tuple(rows)


def integer_kernel_basis(
    matrix: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    """
    A ``Z``-basis of ``ker(matrix)`` INTERSECTED WITH THE INTEGER LATTICE. Exact.

    The distinction in that sentence is the whole function, and getting it wrong is how
    this module shipped a false completeness claim on 2026-07-26.

    THE BUG THIS REPLACES
    ---------------------
    The first version solved for the kernel over the RATIONALS by row reduction, then
    cleared each basis vector's denominators independently. Those vectors do span
    ``ker(A)`` over ``Q`` -- but the lattice they generate over ``Z`` is a proper
    sublattice of ``ker(A) & Z^n``, of finite index, and every integer point in the gap is
    a balanced reaction the menu could not name and could not reconstruct. Measured, on
    ``(O2, H2O, H2O2, H2)``::

        returned basis : (1, 2, -2, 0) and (1, -2, 0, 2)
        omitted        : (1, 0, -1, 1), which is H2 + O2 -> H2O2
        A @ nu         : [0, 0, 0]  -- exactly balanced
        the reason     : it is (b0 + b1)/2, and component 2 of any integer combination
                         is -2a, always even, while the target's is -1

    Clearing a denominator inside one vector is not a lattice operation. It multiplies
    that generator by an integer, which shrinks the group it generates. Worse, WHICH
    reactions vanished depended on the caller's argument order, because argument order
    decides which columns become pivots and therefore which denominators appear.

    THE FIX, AND WHY IT IS EXACT
    ----------------------------
    Unimodular column reduction. Reduce ``A`` to column echelon form over ``Z`` using only
    column operations that are invertible over ``Z`` -- integer multiples subtracted
    between columns, and swaps -- while applying the identical operations to an identity
    matrix ``U``. On exit ``A @ U`` has its first ``r`` columns independent and the rest
    zero, so for ``x = U @ y``::

        A @ x == 0   iff   (A @ U) @ y == 0   iff   y vanishes on the first r positions

    ``U`` is unimodular, so ``x`` is an integer vector exactly when ``y`` is. The trailing
    ``n - r`` columns of ``U`` are therefore a ``Z``-basis of ``ker(A) & Z^n`` itself, not
    of a sublattice of it. Completeness is now a property of the construction rather than
    a hope about denominators, and it no longer depends on argument order.

    Termination is the ordinary Euclidean argument: each inner pass replaces every other
    nonzero entry of the working row with its remainder modulo the smallest, so the
    smallest magnitude strictly decreases until one entry is left.
    """
    if not matrix:
        return ()
    width = len(matrix[0])
    for row in matrix:
        if len(row) != width:
            raise ValueError("composition matrix rows must all have the same length")
        for entry in row:
            # A float here would be silently swallowed by Fraction() and emerge as a
            # ratio of astronomical integers -- a plausible-looking kernel of a matrix
            # nobody supplied. The module docstring refuses a floating-point RANK for
            # exactly this reason; refusing the input is the same argument one step
            # earlier.
            if type(entry) is not int:
                raise TypeError(
                    f"composition matrix entries must be int, got {type(entry).__name__}"
                )

    work = [list(row) for row in matrix]
    unimodular = [[int(i == j) for j in range(width)] for i in range(width)]

    def combine(target: int, source: int, factor: int) -> None:
        for row in work:
            row[target] -= factor * row[source]
        for row in unimodular:
            row[target] -= factor * row[source]

    def swap(left: int, right: int) -> None:
        for row in work:
            row[left], row[right] = row[right], row[left]
        for row in unimodular:
            row[left], row[right] = row[right], row[left]

    pivot = 0
    for r in range(len(work)):
        if pivot >= width:
            break
        while True:
            nonzero = [c for c in range(pivot, width) if work[r][c]]
            if len(nonzero) <= 1:
                break
            smallest = min(nonzero, key=lambda c: abs(work[r][c]))
            for c in nonzero:
                if c == smallest:
                    continue
                quotient = work[r][c] // work[r][smallest]
                if quotient:
                    combine(c, smallest, quotient)
        remaining = [c for c in range(pivot, width) if work[r][c]]
        if remaining:
            if remaining[0] != pivot:
                swap(pivot, remaining[0])
            pivot += 1

    return tuple(
        _oriented(tuple(row[c] for row in unimodular)) for c in range(pivot, width)
    )


@dataclass(frozen=True)
class Completion:
    """
    One balanced reaction derived from a candidate species set.

    ``coefficients`` is aligned with the menu's ``species`` tuple and signed: positive
    entries are reactants, negative entries are products, zero means the species does not
    appear. ``reaction`` is the same statement as a real morphism, and the fact that it
    exists is the independent confirmation that the vector balances.
    """
    coefficients: tuple[int, ...]
    reaction: Reaction
    unconstrained: bool
    species: tuple[Molecule, ...]

    def equation(self, species: tuple[Molecule, ...] | None = None) -> str:
        """
        The balance written with integer coefficients, which is what a caller reads.

        ``Config.__repr__`` renders a multiset, so three waters print as ``H2O + H2O +
        H2O``. That is faithful to the object and useless as a menu entry.

        **The species are STORED, and the argument is now only a cross-check.** They used
        to be a required parameter, on the reasoning that a ``Completion`` is only ever
        handed out by the menu that owns the tuple. That reasoning was wrong twice over.
        A tuple of the wrong LENGTH let ``zip`` truncate in silence and render a shorter
        balance that reads as complete; guarding the length then left the worse case wide
        open, because a tuple of the RIGHT length and the wrong CONTENT renders a fully
        formed, entirely plausible equation for a reaction nobody derived. Reordering a
        species list is an ordinary mistake in a pipeline, not an attack::

            completion.equation((O2, CH4, H2O, CO2))   ->  'O2 + 2CH4 -> H2O + 2CO2'

        which is not mass-balanced and is indistinguishable, as a string, from something
        that came out of :meth:`StoichiometryMenu.equations`. Identity is the only guard
        that closes that, so the object carries what it renders against.
        """
        if species is not None and tuple(species) != self.species:
            raise ValueError(
                f"equation() was given a species tuple that is not the one these "
                f"coefficients were derived against. A same-length tuple in a different "
                f"order renders a complete, plausible, WRONG equation -- pass this "
                f"completion's own species, or pass nothing")
        species = self.species

        def side(keep) -> str:
            terms = [f"{abs(c) if abs(c) != 1 else ''}{m!r}"
                     for m, c in zip(species, self.coefficients) if keep(c)]
            # "(nothing)" is decided from the COEFFICIENTS, never from the joined text.
            # Those two predicates are not the same, and the difference shipped as a bug:
            # a species whose repr was the empty string made a populated side join to ""
            # and fall through to "(nothing)", so the kernel vector with coefficient 1 on
            # a bare quantum printed as "(nothing) -> (nothing)" -- the trivial reaction,
            # which is a confident false statement about a true basis vector. Molecule's
            # repr no longer returns "", so this branch is now belt and braces; it stays
            # because emptiness of a side IS a fact about the vector, and deriving a fact
            # from a rendering of itself is how the sublattice bug got in too.
            return " + ".join(terms) if terms else "(nothing)"
        return f"{side(lambda c: c > 0)} -> {side(lambda c: c < 0)}"

    def __repr__(self) -> str:
        flag = "  [UNCONSTRAINED: touches a species the invariants cannot see]" \
            if self.unconstrained else ""
        return f"{self.reaction.dom} -> {self.reaction.cod}{flag}"


#: The largest total coefficient weight this module will materialise as objects.
#: ``_configs`` builds ``abs(coefficient)`` molecule objects per species, so an unbounded
#: vector is an unbounded allocation. No balance in chemistry needs this much; the cap is a
#: statement about the arithmetic, not about the chemistry, and it refuses loudly.
#:
#: The name is historical and now slightly narrow: the cap is enforced inside ``_configs``
#: and therefore governs DERIVED vectors as well as written ones, which is the point --
#: guarding only the written path left ``stoichiometry_menu`` able to allocate hundreds of
#: gigabytes from a two-species input (see ``_configs``). :meth:`StoichiometryMenu.check`
#: keeps its own earlier test against this same constant so a scientist who types a large
#: vector gets a message about what they typed rather than a message about materialisation;
#: the two must never be given different thresholds, which is why there is only one.
MAX_WRITTEN_WEIGHT = 1000


@dataclass(frozen=True)
class Written:
    """
    A balance the scientist WROTE, judged by the rules that derived the menu.

    Section I's ask has two clauses -- *"choose one, or write one and I will check it
    against the same rules"* -- and only the first was implemented. This is the second.
    "The same rules" is meant literally: the verdict is ``A @ nu == 0`` against the menu's
    own ``matrix``, the identical object that produced ``completions``, not a second
    checker written to agree with the first.

    **Two claims, kept apart, because collapsing them is how a plausible wrong yes gets
    out.** ``admissible`` says the vector balances under the declared invariants.
    ``verified`` says that *and* that the invariants could actually see every species it
    touches -- an invariant-blind species contributes an all-zero column, so ``A @ nu``
    is silent about it and a balance that leans on one has not been checked, it has been
    unexamined. Same distinction as ``COMPILED`` against ``COMPILED_SUBJECT_TO``.

    ``trivial`` is the third thing a naive check gets wrong: the all-zero vector satisfies
    ``A @ nu == 0`` exactly and is not a reaction. Reporting it as admissible would be a
    confident yes about the empty statement.
    """
    coefficients: tuple[int, ...]
    residual: tuple[int, ...]
    violations: tuple[tuple[str, int], ...]
    unverifiable: tuple[Molecule, ...]
    trivial: bool
    reaction: Reaction | None

    @property
    def admissible(self) -> bool:
        """It balances under the declared invariants, and is not the empty statement."""
        return not self.violations and not self.trivial

    @property
    def verified(self) -> bool:
        """Admissible, AND every species it touches was visible to those invariants."""
        return self.admissible and not self.unverifiable

    def __bool__(self) -> bool:
        """
        Truthy on :attr:`verified`, the STRONGER of the two claims, never on the weaker.

        **This is deliberately the opposite convention from ``Session.__bool__``, which is
        truthy on ``COMPILED_SUBJECT_TO`` as well as ``COMPILED``, and the divergence is
        named here so nobody has to discover it.** The two weaker cases are not the same
        kind of thing. ``COMPILED_SUBJECT_TO`` is a *checked* result with a condition
        attached: the spec closed, and one binding needs re-reading after the run. An
        unverifiable balance is not a weaker yes at all -- it is the invariants being
        SILENT about part of the claim, because the columns they would have used are
        indistinguishable. Absence of evidence is not evidence with a caveat, so the
        careless ``if menu.check(nu):`` gets ``False`` here rather than a pass.
        """
        return self.verified

    def explain(self) -> str:
        if self.trivial:
            return ("REFUSED: the all-zero vector. It satisfies every invariant exactly, "
                    "which is why a bare residual test accepts it, and it states nothing. "
                    "A balance has to move at least one species.")
        if self.violations:
            broken = "; ".join(f"{label} off by {amount:+d}"
                               for label, amount in self.violations)
            return (f"REFUSED: what you wrote does not balance under the declared "
                    f"invariants. {broken}. This is the same matrix that derived the "
                    f"menu -- the row labels name which conserved quantity fails and by "
                    f"how much, so the repair is arithmetic rather than guesswork.")
        if self.unverifiable:
            names = ", ".join(repr(m) for m in self.unverifiable)
            return (f"ADMISSIBLE BUT NOT VERIFIED: the residual is zero on every row, and "
                    f"it touches {names} -- species the declared invariants cannot "
                    f"resolve, either from nothing (an all-zero column) or from each "
                    f"other (identical columns, which is how an excited atom and a "
                    f"relaxed one appear when state is kept out of the conserved "
                    f"signature). A @ nu is unchanged by those columns whatever the "
                    f"coefficients are, so a zero residual is not evidence about them; it "
                    f"is silence about them. Constrain them or say why they need not be.")
        return ("VERIFIED: the residual is zero on every row, every species it touches was "
                "visible to those rows, and Reaction's constructor re-derived the balance "
                "independently by accumulating formula dictionaries. Two derivations "
                "sharing no code agreed.")


@dataclass(frozen=True)
class StoichiometryMenu:
    """
    The complete set of balanced reactions over a candidate species set.

    ``freedom`` is ``len(species) - rank(A)``, the dimension of the solution space, and it
    is the field to branch on: 0 refuses by theorem, 1 is forced, 2 or more is a real
    choice. ``completions`` always has exactly ``freedom`` entries -- it is a BASIS of the
    solution lattice, not a sample of it, and every balanced reaction over these species is
    an integer combination of its members.
    """
    species: tuple[Molecule, ...]
    row_labels: tuple[str, ...]
    matrix: tuple[tuple[int, ...], ...]
    rank: int
    freedom: int
    completions: tuple[Completion, ...]
    unconstrained: tuple[Molecule, ...]

    def __bool__(self) -> bool:
        """True when at least one balanced reaction exists."""
        return bool(self.completions)

    @property
    def verdict(self) -> str:
        """Which of the three regimes this menu is in, as a bare token."""
        if self.freedom == 0:
            return "REFUSE"
        return "FILL_IN" if self.freedom == 1 else "ENUMERATE"

    def equations(self) -> tuple[str, ...]:
        """Every completion written with integer coefficients, in basis order."""
        return tuple(c.equation(self.species) for c in self.completions)

    def check(self, coefficients) -> "Written":
        """
        Section I's second clause: judge a balance the scientist wrote themselves.

        ``coefficients`` is aligned with :attr:`species` and signed exactly as
        :attr:`Completion.coefficients` is -- positive reactants, negative products, zero
        absent. The verdict is ``A @ nu`` against :attr:`matrix`, which is the object that
        derived :attr:`completions`; "checked against the same rules" is not a figure of
        speech here, it is the same array.

        **Nothing is asked about whether the vector is in the menu, because that question
        is already answered by a theorem.** :func:`integer_kernel_basis` returns a basis of
        ``ker(A) & Z^n``, so every balanced integer vector over these species IS an integer
        combination of :attr:`completions` -- that is the whole content of the sublattice
        repair. A written balance that passes here is therefore in the menu's span by
        construction, and re-deriving that would be asking the module to confirm its own
        theorem. What a scientist actually needs told is the opposite case: which conserved
        quantity their vector breaks, and by how much, which is what :class:`Written`
        carries.

        Raises rather than returning a verdict when the input is not a candidate balance at
        all: a wrong length, a non-integer, or a total weight past
        :data:`MAX_WRITTEN_WEIGHT`. Those are malformed questions, not wrong answers, and
        answering a malformed question with ``False`` would tell a scientist their
        chemistry is wrong when their typing was.
        """
        if not isinstance(coefficients, Sequence) or isinstance(coefficients, (str, bytes)):
            # A ``set`` has a length, holds integers, and passes every other guard here --
            # and ``tuple()`` freezes it in HASH order, which for these integers is not
            # insertion order. Measured: over 39 scalings of this menu's own derived
            # balance, 34 came back with a confident, specific, WRONG "no" carrying
            # fabricated row violations, purely because the container was unordered.
            # ``scale=1`` survived by hash-layout coincidence, which is worse than failing.
            raise TypeError(
                f"coefficients must be an ordered sequence (list or tuple), got "
                f"{type(coefficients).__name__}. An unordered container is silently "
                f"reordered by tuple(), and this method would then answer confidently "
                f"about a vector the caller never wrote")
        nu = tuple(coefficients)
        if len(nu) != len(self.species):
            raise ValueError(
                f"check() got {len(nu)} coefficients for {len(self.species)} species; "
                f"align them with this menu's own species tuple, in its order")
        if any(type(c) is not int for c in nu):
            # ``type(c) is int`` and not ``isinstance``, deliberately. bool is an int
            # subclass and True is a typo rather than a 1 -- but the sharper reason is
            # that an int SUBCLASS may lie. The weight cap below and ``_configs``'s
            # allocation each call ``abs()`` independently, so a stateful ``__abs__``
            # returning an honest value once and a huge one afterwards passes the cap and
            # then materialises the huge count. Measured: a subclass declaring weight 4
            # allocated 5,000,000 molecules, and the resulting mismatch was reported as a
            # MenuContradiction -- the module accusing its own two derivations of
            # disagreeing when neither was wrong and the TYPE had lied. An exactness
            # guarantee cannot be built on a value the caller can recompute differently.
            raise TypeError(
                f"coefficients must be exactly int, got "
                f"{[type(c).__name__ for c in nu]}. A float sums straight through the "
                f"residual test; bool is a typo, not a 1; and an int subclass can return "
                f"one value to the allocation guard and another to the allocator")
        weight = sum(abs(c) for c in nu)
        if weight > MAX_WRITTEN_WEIGHT:
            raise ValueError(
                f"total coefficient weight {weight} exceeds {MAX_WRITTEN_WEIGHT}; the "
                f"configurations built to confirm this balance materialise one molecule "
                f"object per unit of weight, so this is an allocation bound and not a "
                f"claim about chemistry")

        residual = tuple(sum(row[i] * nu[i] for i in range(len(nu)))
                         for row in self.matrix)
        violations = tuple((label, amount)
                           for label, amount in zip(self.row_labels, residual) if amount)
        trivial = not any(nu)
        # Only species the vector actually TOUCHES matter: a blind species with
        # coefficient zero is not being leaned on and its invisibility costs nothing here.
        unverifiable = tuple(molecule for molecule, c in zip(self.species, nu)
                             if c and molecule in self.unconstrained)

        reaction = None
        if not violations and not trivial:
            # The same independent confirmation the derived completions get. Reaction's
            # constructor re-derives the balance by accumulating formula dictionaries --
            # integer arithmetic sharing no code with the residual sum above. A
            # ConservationError escaping here is two derivations disagreeing, which is a
            # MenuContradiction and must not be swallowed into a False.
            dom, cod = _configs(self.species, nu)
            try:
                reaction = Reaction(dom, cod, name="written")
            except ConservationError as clash:
                raise MenuContradiction(
                    f"written nu={nu} has zero residual against every invariant row, and "
                    f"Reaction refused it: {clash}. Two derivations that share no code "
                    f"disagree about the same vector") from clash
        return Written(nu, residual, violations, unverifiable, trivial, reaction)

    def explain(self) -> str:
        """
        The derived-menu law, stated for this particular menu.

        Printed rather than assumed because the law's whole content is that the caller can
        see WHICH invariant and WHICH operation produced the options, and can therefore
        tell a derivation from a plausible-sounding list.
        """
        # By POSITION, not by string equality against CHARGE_ROW. ``composition_matrix``
        # builds the labels as ``elements + (CHARGE_ROW,)``, so the element rows are
        # everything but the last one, and that is a fact about the construction rather
        # than about how the last row happens to be spelled. The filter this replaces read
        # a fact off a rendering of itself -- the same shape as the sublattice bug and the
        # empty-side bug above -- and printed "atom counts for (none)" for a matrix that
        # had a genuine atom row, whenever a caller spelled an atom label "(charge)".
        elements = list(self.row_labels[:-1])
        lines = [
            f"invariants declared : atom counts for {', '.join(elements) or '(none)'}"
            f"; net charge",
            f"operation declared  : saturated integer kernel of the {len(self.matrix)}x"
            f"{len(self.species)} composition matrix, by unimodular column reduction",
            f"rank(A)={self.rank}  n={len(self.species)}  freedom={self.freedom}",
        ]
        if self.freedom == 0:
            lines.append(
                "verdict: REFUSE. No non-trivial balance exists over these species. This "
                "is a theorem about the declared invariants, not a failed search.")
        elif self.freedom == 1:
            lines.append(
                "verdict: FILL IN. The balance is forced up to sign and scale. Offering a "
                "choice here would be theatre.")
        else:
            lines.append(
                f"verdict: ENUMERATE. {self.freedom} independent balances; every other one "
                "is an integer combination of these.")
        if self.unconstrained:
            columns = list(zip(*self.matrix)) if self.matrix else []
            invisible, twinned = [], []
            for molecule, column in zip(self.species, columns):
                if molecule not in self.unconstrained:
                    continue
                (invisible if not any(column) else twinned).append(molecule)
            if invisible:
                lines.append(
                    f"BOUNDARY: {', '.join(repr(m) for m in invisible)} has no atoms and "
                    "no charge, so the declared invariants cannot see it at all. "
                    "Completions touching it are balanced only in the sense that mass and "
                    "charge say nothing about them.")
            if twinned:
                lines.append(
                    f"BOUNDARY: {', '.join(repr(m) for m in twinned)} share a composition "
                    "column, so the declared invariants cannot tell them apart. Any "
                    "completion converting one into another is balanced by construction "
                    "and says nothing about whether the conversion happens or what it "
                    "costs -- the difference between them is exactly what these "
                    "invariants do not model.")
        return "\n".join(lines)


def _invariant_blind(
    species: tuple[Molecule, ...], matrix: tuple[tuple[int, ...], ...]
) -> tuple[Molecule, ...]:
    """
    The species the declared invariants cannot tell apart -- from nothing, or from each other.

    A species' column IS everything mass and charge conservation know about it. Two
    consequences follow, and the first release of this module only implemented one of them:

    * an ALL-ZERO column is a species the invariants cannot distinguish from *nothing*.
      That is how this package spells a photon, and it is why ``photon -> (nothing)`` comes
      back as a balanced reaction.
    * IDENTICAL columns are species the invariants cannot distinguish from *each other*.
      ``category.Molecule`` deliberately keeps ``state`` out of the conserved signature so
      that ``Na(*) -> Na`` can be expressed at all, which means an excited atom and a
      relaxed one present the same column by design.

    The second case is the more dangerous of the two, because it does not look like a
    boundary. ``stoichiometry_menu((Na(*), Na))`` finds freedom 1 and reports ``Na(*) ->
    Na`` under the FILL_IN verdict -- "forced up to sign and scale, offering a choice would
    be theatre" -- which is a confident statement about de-excitation derived from
    invariants that cannot see excitation. The balance is real; what it is a balance OF is
    not what a reader assumes. Flagging it is the whole job.
    """
    if not matrix:
        return tuple(species)
    columns = list(zip(*matrix))
    tally: dict[tuple[int, ...], int] = {}
    for column in columns:
        tally[column] = tally.get(column, 0) + 1
    return tuple(
        molecule
        for molecule, column in zip(species, columns)
        if not any(column) or tally[column] > 1
    )


def _configs(species: tuple[Molecule, ...],
             nu: tuple[int, ...]) -> tuple[Config, Config]:
    """
    Split a signed coefficient vector into reactant and product configurations.

    THE CAP LIVES HERE BECAUSE THE ALLOCATION LIVES HERE. It used to live only at
    :meth:`StoichiometryMenu.check`, which guarded the vectors a scientist WRITES and left
    the vectors this module DERIVES completely unbounded -- and the derived path is
    reachable from ``stoichiometry_menu`` with nothing but an ordinary species tuple.

    MEASURED, 2026-07-27, by adversarial review of the unguarded code::

        Molecule.carrier(label="X", charge=999_937)     kernel basis (999999, -999937)
        Molecule.carrier(label="Y", charge=999_999)     weight 1,999,936
        stoichiometry_menu((X, Y))                      4.2 s, 215 MB RSS

    TWO species. The attack surface is charge MAGNITUDE, not species count: for a single
    charge row the kernel vector of two coprime charges is proportional to the charges
    themselves, so the weight is linear in a number the caller types. Raising the charges
    to ten digits extrapolates to roughly seventy minutes and two hundred gigabytes, and
    ``Molecule.carrier`` is this package's own documented idiom for ions with no magnitude
    bound anywhere between it and this line. A many-species construction also works --
    Fibonacci charges drive the column reduction into Euclid's worst case and reach weight
    1,134,903,171 at forty species -- but it is the weaker attack and needs the bigger setup.
    """
    weight = sum(abs(coefficient) for coefficient in nu)
    if weight > MAX_WRITTEN_WEIGHT:
        raise ValueError(
            f"refusing to materialise a coefficient vector of total weight {weight}; the "
            f"cap is {MAX_WRITTEN_WEIGHT}. This builds one Molecule object per unit of "
            f"weight. If this vector was DERIVED rather than written, the species set "
            f"carries charges or compositions whose exact kernel is enormous -- the "
            f"arithmetic is correct and the answer is simply too large to instantiate, "
            f"which is a fact about the input rather than a failure of the kernel.")
    reactants: list[Molecule] = []
    products: list[Molecule] = []
    for molecule, coefficient in zip(species, nu):
        target = reactants if coefficient > 0 else products
        target.extend([molecule] * abs(coefficient))
    return Config(tuple(reactants)), Config(tuple(products))


def stoichiometry_menu(species: tuple[Molecule, ...]) -> StoichiometryMenu:
    """
    Every balanced reaction admitted by ``species``, derived and never guessed.

    Raises ``ValueError`` on a repeated species: two identical columns would make the
    kernel report a spurious degree of freedom whose "reaction" is ``A -> A``, and a menu
    that offers the identity as a discovery has misread its own input rather than found
    something. Deduplicate before calling if that is what you meant.

    Raises ``MenuContradiction`` if the exact kernel and ``Reaction``'s own balance test
    ever disagree. That cannot happen and the check is cheap, which is exactly when an
    assertion is worth keeping.
    """
    if not isinstance(species, tuple) or any(
        not isinstance(molecule, Molecule) for molecule in species
    ):
        raise TypeError("species must be a tuple of Molecule values")
    canonical = [molecule.canonical() for molecule in species]
    seen: set = set()
    for molecule in canonical:
        key = (tuple(sorted(molecule.formula.items())), molecule.charge,
               tuple(sorted(molecule.bonds)), molecule.state)
        if key in seen:
            raise ValueError(f"species repeated in the candidate set: {molecule!r}")
        seen.add(key)

    row_labels, matrix = composition_matrix(species)
    rank = len(_rref([[Fraction(x) for x in row] for row in matrix])[1]) if matrix else 0
    basis = integer_kernel_basis(matrix)
    freedom = len(species) - rank
    if len(basis) != freedom:
        raise MenuContradiction(
            f"kernel basis has {len(basis)} vectors but rank-nullity requires {freedom}")

    blind = _invariant_blind(species, matrix)

    completions = []
    for nu in basis:
        residual = [sum(row[i] * nu[i] for i in range(len(nu))) for row in matrix]
        if any(residual):
            raise MenuContradiction(
                f"derived nu={nu} leaves residual {residual}; the kernel is wrong")
        dom, cod = _configs(species, nu)
        # The independent check. Reaction's constructor re-derives the balance by
        # accumulating Molecule.formula dictionaries -- integer arithmetic that shares no
        # code with the Fraction elimination above. A ConservationError here is a genuine
        # contradiction between two derivations and must not be caught.
        reaction = Reaction(dom, cod, name="derived")
        touches_blind = any(coefficient and molecule in blind
                            for molecule, coefficient in zip(species, nu))
        completions.append(Completion(nu, reaction, touches_blind, tuple(species)))

    return StoichiometryMenu(
        species=tuple(species),
        row_labels=row_labels,
        matrix=matrix,
        rank=rank,
        freedom=freedom,
        completions=tuple(completions),
        unconstrained=blind,
    )
