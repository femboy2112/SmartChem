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
    declared operation : the integer kernel of the composition matrix
    completeness       : the returned vectors span ker(A) exactly, over the rationals

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
Every rank here is computed over ``fractions.Fraction`` and every returned vector is a
primitive integer vector with denominators cleared. ``numpy.linalg.matrix_rank`` would be
faster and would agree on every case in this repository, but a floating-point rank is a
rank with a tolerance -- which is to say a *plausible* rank. A module whose entire claim is
"derived, never approximated" has no business resting on a singular-value threshold.

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
species with no atoms and no charge -- which is how this package spells a photon -- has an
all-zero column, so it lies in the kernel by itself and the enumeration will dutifully
offer ``photon -> (nothing)`` as a balanced reaction. Under mass and charge conservation
alone, it is. Those invariants cannot see energy.

That is not a bug to be special-cased away; it is the law reporting the exact boundary of
what it was given. Such species are named in ``StoichiometryMenu.unconstrained`` and every
completion touching one is flagged ``unconstrained=True``, so a caller can never mistake
"balanced under the declared invariants" for "physical".
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from math import gcd

from .category import Config, Molecule, Reaction

__all__ = [
    "Completion",
    "MenuContradiction",
    "StoichiometryMenu",
    "composition_matrix",
    "integer_kernel_basis",
    "stoichiometry_menu",
]

#: Row label used for the net-charge row of the composition matrix. Not an element symbol,
#: and deliberately unspellable as one, so it can never collide with a real row.
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


def _primitive(vec: list[Fraction]) -> tuple[int, ...]:
    """Clear denominators, divide out the gcd, and fix the sign of the first nonzero."""
    multiplier = reduce(lambda a, b: a * b // gcd(a, b), (x.denominator for x in vec), 1)
    ints = [int(x * multiplier) for x in vec]
    common = reduce(gcd, (abs(v) for v in ints if v), 0)
    if common:
        ints = [v // common for v in ints]
    if next((v for v in ints if v), 0) < 0:
        ints = [-v for v in ints]
    return tuple(ints)


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
    rows = [tuple(molecule.formula.get(element, 0) for molecule in species)
            for element in elements]
    rows.append(tuple(molecule.charge for molecule in species))
    return elements + (CHARGE_ROW,), tuple(rows)


def integer_kernel_basis(
    matrix: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    """A primitive integer basis of ``ker(matrix)``. Exact; no tolerance anywhere."""
    if not matrix:
        return ()
    ncols = len(matrix[0])
    reduced, pivots = _rref([[Fraction(x) for x in row] for row in matrix])
    basis = []
    for free in (c for c in range(ncols) if c not in pivots):
        vec = [Fraction(0)] * ncols
        vec[free] = Fraction(1)
        for r, p in enumerate(pivots):
            vec[p] = -reduced[r][free]
        basis.append(_primitive(vec))
    return tuple(basis)


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

    def equation(self, species: tuple[Molecule, ...]) -> str:
        """
        The balance written with integer coefficients, which is what a caller reads.

        ``Config.__repr__`` renders a multiset, so three waters print as ``H2O + H2O +
        H2O``. That is faithful to the object and useless as a menu entry. Takes the
        species tuple rather than storing it because a ``Completion`` is only ever handed
        out by the menu that owns that tuple.
        """
        def side(keep) -> str:
            terms = [f"{abs(c) if abs(c) != 1 else ''}{m!r}"
                     for m, c in zip(species, self.coefficients) if keep(c)]
            return " + ".join(terms) or "(nothing)"
        return f"{side(lambda c: c > 0)} -> {side(lambda c: c < 0)}"

    def __repr__(self) -> str:
        flag = "  [UNCONSTRAINED: touches a species the invariants cannot see]" \
            if self.unconstrained else ""
        return f"{self.reaction.dom} -> {self.reaction.cod}{flag}"


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

    def explain(self) -> str:
        """
        The derived-menu law, stated for this particular menu.

        Printed rather than assumed because the law's whole content is that the caller can
        see WHICH invariant and WHICH operation produced the options, and can therefore
        tell a derivation from a plausible-sounding list.
        """
        elements = [label for label in self.row_labels if label != CHARGE_ROW]
        lines = [
            f"invariants declared : atom counts for {', '.join(elements) or '(none)'}"
            f"; net charge",
            f"operation declared  : integer kernel of the {len(self.matrix)}x"
            f"{len(self.species)} composition matrix, exact rational arithmetic",
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
            names = ", ".join(repr(m) for m in self.unconstrained)
            lines.append(
                f"BOUNDARY: {names} has no atoms and no charge, so the declared invariants "
                "cannot see it. Completions touching it are balanced only in the sense "
                "that mass and charge say nothing about them.")
        return "\n".join(lines)


def _configs(species: tuple[Molecule, ...],
             nu: tuple[int, ...]) -> tuple[Config, Config]:
    """Split a signed coefficient vector into reactant and product configurations."""
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

    blind = tuple(molecule for molecule, column in zip(species, zip(*matrix) if matrix
                                                       else [()] * len(species))
                  if not any(column))

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
        completions.append(Completion(nu, reaction, touches_blind))

    return StoichiometryMenu(
        species=tuple(species),
        row_labels=row_labels,
        matrix=matrix,
        rank=rank,
        freedom=freedom,
        completions=tuple(completions),
        unconstrained=blind,
    )
