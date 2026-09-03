"""An exact-rational linear-programming kernel: ``max c.x  s.t.  A x <= b, x >= 0``.

A leaf module (standard library + :class:`fractions.Fraction` only, no chemistry types) so any layer can use
it without a coupling cycle.  Its whole reason to exist is EXACTNESS: the DAG-FLOW-01 conserved quantity-flow
ceiling is a ``CONSERVATION`` bound that the repo labels "exact rational", and a float LP (scipy) would import
binary imprecision into a bound whose entire claim is exactness.  So this solves the LP in :class:`~fractions.Fraction`
arithmetic, with Bland's rule for guaranteed termination (no cycling).

The API is deliberately narrow -- exactly the shape the max-yield ceiling needs:

* the objective is MAXIMIZED;
* every structural variable is ``>= 0`` (reaction extents are non-negative);
* the constraints are ``<=`` with a NON-NEGATIVE right-hand side ``b`` (a feed amount is ``>= 0`` and an
  intermediate's "consumed <= produced" bound is ``0``).

``b >= 0`` is what makes this a SINGLE-PHASE simplex: the all-slack basis (``x = 0``, slacks ``= b``) is already
feasible, so there is no Phase-I / artificial-variable machinery to get wrong.  An unbounded objective (a variable
that can grow with no constraint stopping it) is reported by raising :class:`LPUnbounded` -- never a silent clip,
a hang, or a fabricated finite number.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Sequence

__all__ = ["LPUnbounded", "maximize"]


class LPUnbounded(Exception):
    """The objective is unbounded above on the feasible region (no finite maximum)."""


def _F(x: "int | Fraction") -> Fraction:
    if isinstance(x, bool) or not isinstance(x, (int, Fraction)):
        raise TypeError(f"exact_lp needs int/Fraction coefficients, got {type(x).__name__}")
    return Fraction(x)


def maximize(
    c: Sequence["int | Fraction"],
    A: Sequence[Sequence["int | Fraction"]],
    b: Sequence["int | Fraction"],
) -> "tuple[Fraction, list[Fraction]]":
    """Maximize ``c . x`` subject to ``A x <= b``, ``x >= 0``, with every ``b_i >= 0``.

    Returns ``(optimal_value, x)`` as exact :class:`~fractions.Fraction` values.  Raises :class:`LPUnbounded`
    if the objective has no finite maximum, :class:`ValueError` on a shape mismatch or a negative ``b`` (which
    would break the single-phase feasible start this kernel relies on).
    """
    c = [_F(x) for x in c]
    A = [[_F(x) for x in row] for row in A]
    b = [_F(x) for x in b]
    n = len(c)
    m = len(A)
    if any(len(row) != n for row in A):
        raise ValueError("every row of A must have len == len(c)")
    if len(b) != m:
        raise ValueError("b must have one entry per row of A")
    if any(bi < 0 for bi in b):
        raise ValueError("this single-phase kernel requires b >= 0 (the all-slack basis must start feasible)")

    if m == 0:
        # No constraints: unbounded unless every objective coefficient is <= 0 (then the optimum is 0 at x = 0).
        if any(ci > 0 for ci in c):
            raise LPUnbounded()
        return Fraction(0), [Fraction(0)] * n

    # Tableau: n structural columns (x) + m slack columns (identity) + 1 rhs column.
    # Row i:  A[i] | e_i (slack identity) | b[i].   Basis starts as the slacks (columns n .. n+m-1).
    width = n + m
    tableau: list[list[Fraction]] = []
    for i in range(m):
        slack = [Fraction(1) if j == i else Fraction(0) for j in range(m)]
        tableau.append(A[i] + slack + [b[i]])
    # Objective (reduced-cost) row: positive entry => bringing that variable in increases the maximand.
    obj = list(c) + [Fraction(0)] * m + [Fraction(0)]  # trailing entry tracks the running objective value
    basis = list(range(n, n + m))  # the slack variable in each row

    max_iters = 1000 * (width + 1)  # Bland's rule cannot cycle; this is only a runaway backstop.
    for _ in range(max_iters):
        # Entering variable: Bland's rule -- the SMALLEST index with a positive reduced cost.
        entering = next((j for j in range(width) if obj[j] > 0), None)
        if entering is None:
            break  # optimal: no reduced cost improves the maximand
        # Leaving variable: min ratio b_i / a_ij over a_ij > 0; Bland tie-break by smallest basis index.
        leaving = None
        best: "Fraction | None" = None
        for i in range(m):
            a = tableau[i][entering]
            if a > 0:
                ratio = tableau[i][-1] / a
                if best is None or ratio < best or (ratio == best and basis[i] < basis[leaving]):
                    best = ratio
                    leaving = i
        if leaving is None:
            raise LPUnbounded()  # the entering column has no positive coefficient: an unbounded ray
        # Pivot on (leaving, entering).
        pivot = tableau[leaving][entering]
        tableau[leaving] = [v / pivot for v in tableau[leaving]]
        for i in range(m):
            if i != leaving and tableau[i][entering] != 0:
                factor = tableau[i][entering]
                tableau[i] = [tableau[i][k] - factor * tableau[leaving][k] for k in range(width + 1)]
        if obj[entering] != 0:
            factor = obj[entering]
            obj = [obj[k] - factor * tableau[leaving][k] for k in range(width + 1)]
        basis[leaving] = entering
    else:  # pragma: no cover -- Bland's rule guarantees termination; reaching here is a coded-wrong simplex
        raise RuntimeError("exact_lp simplex did not converge (Bland's rule should preclude cycling)")

    x = [Fraction(0)] * n
    for i in range(m):
        if basis[i] < n:
            x[basis[i]] = tableau[i][-1]
    value = sum((c[j] * x[j] for j in range(n)), Fraction(0))
    return value, x
