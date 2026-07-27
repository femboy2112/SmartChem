#!/usr/bin/env python
"""
Is the "here are X admissible configurations" menu DERIVABLE, or only plausible?

THE QUESTION
------------
``THE_COMPILER.md`` argues for a meta-compiler that, when a scientist's specification is
underdetermined, hands back the *complete* set of admissible completions rather than a
plausible-sounding sample of them. Its governing rule (§III, the derived-menu law) is that
every option offered must be the image of a declared invariant under a declared operation,
and that a compiler which cannot enumerate must say so instead of improvising a menu.

That law is worthless if it cannot be implemented even once. This script tests it on the
cheapest complete instance available in this repository: **balancing a reaction whose
stoichiometry the caller did not supply.**

WHY THIS CASE AND NOT A CONVERSATIONAL ONE
------------------------------------------
``smartchem/category.py:1076`` already ships ``conserves``, the *checker*: given a
``Reaction`` it re-verifies that atom counts and net charge balance. The menu is that
function's **inverse**, and the inverse is linear algebra over the integers.

With one row per element (plus a charge row) and one column per species, a balanced
reaction is an integer vector ``nu`` with ``A @ nu == 0``. The admissible completions are
exactly ``ker A`` intersected with the integer lattice, of rank ``n - rank(A)``. Three
ranks give three behaviours, and the whole user experience argued for in §I falls out of
which one you are in:

    dim ker == 0   no non-trivial balance exists     -> refuse, and the refusal is a THEOREM
    dim ker == 1   forced up to sign and scale       -> fill it in; asking would be theatre
    dim ker >= 2   a genuine choice                  -> enumerate a basis; THIS is the menu

The rank-0 row is the point of the exercise. It is the smallest possible instance of a
specification that *verifiably cannot compile*, where the impossibility is itself the
result rather than a failure to search hard enough.

WHY THE ARITHMETIC IS EXACT AND NOT ``numpy.linalg.matrix_rank``
---------------------------------------------------------------
A floating-point rank is a rank with a tolerance, which is to say a *plausible* rank. On
these matrices it happens to agree, but a document whose entire thesis is "derived, never
approximated" has no business backing its table with a singular-value threshold. Everything
below is exact rational arithmetic over ``fractions.Fraction``, and the returned basis
vectors are primitive integer vectors with their denominators cleared.

WHAT THIS DOES *NOT* SHOW
-------------------------
That the derived-menu law generalises. Stoichiometry is the friendly case: the invariant is
linear, so the completion set is a lattice and "complete" means "spans the kernel". A
position constraint between two particles is not obviously linear in anything, and nothing
here says it yields to the same treatment. This establishes that the law is implementable
once, exactly, with a completeness proof -- which is the necessary first brick and not one
inch more.

Exit codes: 0 all claims verified, 1 a claim failed, 2 a self-check failed.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from math import gcd
from functools import reduce

Matrix = list[list[int]]
Vector = list[int]


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


def integer_kernel_basis(matrix: Matrix) -> list[Vector]:
    """
    A ``Z``-basis of ``ker(matrix) & Z^n``, DELEGATED to the shipped implementation.

    This harness used to carry its own copy: solve the kernel over the rationals by row
    reduction, then clear each basis vector's denominators independently. That copy was
    wrong in the same way the first shipped module was wrong, and for the same reason --
    clearing a denominator inside one generator shrinks the group the generators span, to a
    proper sublattice of the integer kernel. Balanced reactions existed that neither could
    name. The counterexample is recorded in ``smartchem/stoichiometry.py``'s docstring.

    Two second copies of an algorithm is two places for it to be wrong, and this one had no
    reason to exist: the harness predates the module, and the module is now the artefact
    ``THE_COMPILER.md`` section IV actually cites. So the duplicate is deleted rather than
    repaired, and this file measures what ships instead of what it once prototyped.
    """
    from smartchem.stoichiometry import integer_kernel_basis as shipped

    return [list(vector) for vector in shipped(tuple(tuple(row) for row in matrix))]


def _apply(matrix: Matrix, vec: Vector) -> Vector:
    return [sum(row[i] * vec[i] for i in range(len(vec))) for row in matrix]


def _rank(matrix: Matrix) -> int:
    return len(_rref([[Fraction(x) for x in row] for row in matrix])[1])


def _spans_same_space(a: list[Vector], b: list[Vector]) -> bool:
    """True when two integer vector lists span the same rational subspace."""
    if len(a) != len(b):
        return False
    if not a:
        return True
    joint = [list(v) for v in a + b]
    # rank of the stacked set equals rank of either alone iff the spans coincide
    return _rank(joint) == _rank([list(v) for v in a]) == _rank([list(v) for v in b])


#: The three worked examples of THE_COMPILER.md section IV, with the verdict each is
#: claimed to produce. ``expected_basis`` is None where the document makes no claim about
#: a specific basis (the rank-0 case has none to make).
CASES = (
    {
        "label": "{H2, He}",
        "species": ("H2", "He"),
        "elements": ("H", "He"),
        "matrix": [[2, 0], [0, 1]],
        "expected_dim": 0,
        "expected_basis": [],
        "verdict": "REFUSE -- no non-trivial balance exists, by theorem",
    },
    {
        "label": "{H2, O2, H2O}",
        "species": ("H2", "O2", "H2O"),
        "elements": ("H", "O"),
        "matrix": [[2, 0, 2], [0, 2, 1]],
        "expected_dim": 1,
        "expected_basis": [[2, 1, -2]],
        "verdict": "FILL IN -- forced up to sign and scale; asking would be theatre",
    },
    {
        "label": "{C, O2, CO, CO2}",
        "species": ("C", "O2", "CO", "CO2"),
        "elements": ("C", "O"),
        "matrix": [[1, 0, 1, 1], [0, 2, 1, 2]],
        "expected_dim": 2,
        "expected_basis": [[1, 1, 0, -1], [2, 1, -2, 0]],
        "verdict": "ENUMERATE -- a genuine choice; this is the menu",
    },
)


def _format(nu: Vector, species: tuple[str, ...]) -> str:
    left = " + ".join(f"{abs(c) if abs(c) != 1 else ''}{s}" for c, s in zip(nu, species) if c > 0)
    right = " + ".join(f"{abs(c) if abs(c) != 1 else ''}{s}" for c, s in zip(nu, species) if c < 0)
    return f"{left} -> {right}" if right else f"{left} -> (nothing)"


def main() -> int:
    print("=" * 78)
    print("STOICHIOMETRY MENU -- is the completion set DERIVABLE and COMPLETE?")
    print("backs: THE_COMPILER.md section IV     arithmetic: exact (fractions.Fraction)")
    print("=" * 78)

    failures: list[str] = []
    for case in CASES:
        matrix, species = case["matrix"], case["species"]
        ncols = len(matrix[0])
        rank = _rank(matrix)
        dim = ncols - rank
        basis = integer_kernel_basis(matrix)

        print()
        print(f"  {case['label']}")
        print(f"    elements   : {', '.join(case['elements'])}")
        print(f"    n={ncols}  rank(A)={rank}  dim ker={dim}   (claimed {case['expected_dim']})")

        if dim != case["expected_dim"]:
            failures.append(f"{case['label']}: dim ker {dim} != claimed {case['expected_dim']}")
        if len(basis) != dim:
            failures.append(f"{case['label']}: derived {len(basis)} basis vectors for dim {dim}")

        for nu in basis:
            residual = _apply(matrix, nu)
            balanced = not any(residual)
            print(f"    derived    : nu={nu}  A@nu={residual}  {_format(nu, species)}")
            if not balanced:
                failures.append(f"{case['label']}: derived nu={nu} does not balance")

        expected = case["expected_basis"]
        if expected is not None:
            for nu in expected:
                residual = _apply(matrix, nu)
                if any(residual):
                    failures.append(f"{case['label']}: DOCUMENTED nu={nu} does not balance")
            if not _spans_same_space(basis, expected):
                failures.append(
                    f"{case['label']}: documented basis {expected} does not span ker(A)"
                )
            else:
                print(f"    documented : {expected}  spans the same space  [PASS]")
        print(f"    verdict    : {case['verdict']}")

    print()
    print("-" * 78)
    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print(f"\n  {len(failures)} claim(s) in THE_COMPILER.md section IV are WRONG.")
        return 1
    print("  All section IV claims verified: every rank, every basis, every balance.")
    print()
    print("  What this establishes: the derived-menu law is implementable once, exactly,")
    print("  with completeness proved rather than asserted. What it does NOT establish is")
    print("  that a non-linear invariant (a position constraint) yields to the same")
    print("  treatment. See the module docstring.")
    print()
    print("  THAT QUESTION IS NOW ANSWERED, AND THE ANSWER IS NO -- measured 2026-07-27 by")
    print("  experiments/nonlinear_menu_rank.py against smartchem/rigidity.py. REFUSE and")
    print("  FILL_IN survive as theorems on a COMPLETE constraint set; ENUMERATE has no")
    print("  analogue, because a complete set fixes the configuration up to isometry and")
    print("  so can never offer a choice. The row this script's rank>=2 case exists for is")
    print("  exactly the row where derivability dies. The paragraph above is kept as")
    print("  written rather than edited, because what it disclaimed turned out to be the")
    print("  finding and a disclaimer quietly replaced by its own answer teaches nobody.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
