"""Detailed-balance / Wegscheider consistency instrument for the two-cell sandbox (standalone, additive).

Ooh yeah, can do!  Look at me: I check whether a set of reversible-reaction equilibrium constants can
EVER sit at a detailed-balanced equilibrium.  Existence is pain, so here is the whole argument, compactly.

Setting.  CLOSED reversible network, stoichiometric matrix N (S x R; column j = net stoichiometry of
reaction j, products positive, reactants negative), equilibrium constants K_j = k_f,j / k_r,j > 0.

Wegscheider condition:   log K  in  im(N^T)     <=>     gamma . log K = 0   for every gamma in ker(N).

Proof sketch.
  1. Let a_ij / b_ij be the reactant / product complex coefficients of species i in reaction j, so
     N_ij = b_ij - a_ij.
  2. Detailed balance at an equilibrium c > 0 means each reversible reaction j is separately balanced:
         k_f,j * prod_i c_i^a_ij  =  k_r,j * prod_i c_i^b_ij.
  3. Divide and take logs:  log K_j = sum_i (b_ij - a_ij) log c_i = (N^T log c)_j.
  4. So log K = N^T mu with mu = log c, i.e. log K lies in im(N^T).            (necessity)
  5. (im N^T)^perp = ker(N) (fundamental theorem of linear algebra), so log K in im(N^T) iff
     gamma . log K = 0 for all gamma in ker(N).  This is the cycle form of the condition.
  6. Conversely, any mu solving N^T mu = log K gives c = exp(mu) as a detailed-balanced state of the
     rate laws, so the condition is also sufficient for existence of such a state (up to the
     conservation-law fibre, which does not change the verdict).                 (sufficiency)

The "cycles" here are STOICHIOMETRIC cycles (ker N: integer combinations of reactions whose net
stoichiometry vanishes), NOT graph-theoretic cycles of a species/complex graph.  The two can differ
(e.g. two distinct rate constants for the same net reaction 2A->B give the stoichiometric cycle (1,-1)
with no loop of distinct species); it is ker N that carries the condition.

WHY AN EXACT KERNEL (the Round-III repair).  ker(N) is a STRUCTURAL object: for an integer stoichiometric
matrix it is exactly determined, with no notion of "numerical rank".  The previous implementation computed
it with a floating SVD null-space threshold (scipy.linalg.null_space) and cross-checked with floating least
squares (numpy.linalg.lstsq).  BOTH share the same floating-rank assumption, so they are NOT independent and
can agree on a WRONG verdict: an ill-conditioned but mathematically FULL-RANK integer N (ker = {0}, hence NO
Wegscheider constraint, every positive K admissible) can make the SVD hallucinate a null vector and report a
FALSE INCONSISTENCY.  So the verdict is now driven by an EXACT integer kernel computed by resource-bounded
rational Gaussian elimination (fractions, not floats); the exact rank and kernel are the authority.  The log-K
cycle residual gamma . log K is then evaluated against a SEPARATELY declared numerical tolerance `tol`:
the kernel STRUCTURE is exact, only the comparison of log K (an inherently floating quantity) is numerical.
This cleanly separates a real chemical-model contradiction (an exact cycle whose log-K product is off) from
numerical uncertainty (ill-conditioning that moves only the floating diagnostics).

The SVD null-space rank (`float_rank`) and the lstsq image residual (`residual_image`) are RETAINED, but only
as DIAGNOSTICS -- never the sole authority, and never claimed to be independent of each other.  When they
disagree with the exact verdict (`method_agreement=False`, or `float_rank != exact_rank`), that is a flag of
numerical conditioning, not a model contradiction.

Source relied on:  M. Feinberg, "Foundations of Chemical Reaction Network Theory", Applied Mathematical
Sciences 202, Springer (2019); historical origin R. Wegscheider, Z. Phys. Chem. 39, 257-303 (1901).
(Cited from memory of the standard result; the proof above is self-contained and does not depend on
page-level citation.)

SCOPE NOTE.  This instrument speaks ONLY to closed-system detailed-balance admissibility.  Driven / open
systems (chemostats, external work, light, imposed reservoirs) legitimately sustain nonequilibrium cycles and
are OUT OF SCOPE; a failed Wegscheider check must NOT be read as forbidding them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd
from typing import List, Tuple

import numpy as np
from scipy.linalg import null_space

# Resource bound: exact rational elimination is for the SMALL experimental networks.  A larger / malformed
# structural input is a bounded typed refusal, never a silent approximate rank or an unbounded computation.
MAX_DIM = 64


class DetailedBalanceError(ValueError):
    """Raised (fail-closed) on malformed N / K input; nothing is silently coerced."""


@dataclass(frozen=True)
class WegscheiderVerdict:
    """Verdict of the Wegscheider check.

    consistent         True iff log K is orthogonal to every vector of the EXACT integer kernel of N within tol
                       (the authoritative verdict; driven by exact rational elimination, not a floating rank).
    residual           max over the exact unit-normalized ker(N) basis of |gamma . log K| (0.0 if ker N is trivial).
    offending_cycles   list of (gamma, imbalance): UNIT-norm exact-kernel basis vectors with |gamma . log K| > tol
                       and the signed value gamma . log K (the cycle's log-product imbalance; basis sign is
                       arbitrary -- compare magnitudes).
    method_agreement   True iff the floating lstsq diagnostic reaches the SAME consistent/inconsistent verdict as
                       the exact kernel.  False = numerical conditioning disagreement (a diagnostic flag), NOT a
                       chemical contradiction; the exact verdict still governs `consistent`.
    residual_image     DIAGNOSTIC (floating lstsq): || N^T mu* - log K ||_inf.  Not authoritative.
    n_cycles           dim ker(N), computed EXACTLY (= R - exact_rank).
    exact_rank         column rank of N from exact rational elimination (the authority).
    float_rank         DIAGNOSTIC: rank implied by the floating SVD null space.  float_rank != exact_rank signals
                       ill-conditioning (the SVD mis-ranked N); it does NOT change the verdict.
    """
    consistent: bool
    residual: float
    offending_cycles: List[Tuple[np.ndarray, float]] = field(default_factory=list)
    cycles: List[np.ndarray] = field(default_factory=list)   # the EXACT primitive-integer ker(N) basis (chemically legible)
    method_agreement: bool = True
    residual_image: float = 0.0
    n_cycles: int = 0
    exact_rank: int = 0
    float_rank: int = 0


def _validate(N, K) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    try:
        Nm = np.array(N, dtype=float)
        Kv = np.array(K, dtype=float)
    except (TypeError, ValueError) as exc:
        raise DetailedBalanceError(f"N and K must be numeric arrays: {exc}") from exc
    if Nm.ndim != 2:
        raise DetailedBalanceError(f"N must be a 2-D (species x reactions) matrix, got ndim={Nm.ndim}")
    if Kv.ndim != 1:
        raise DetailedBalanceError(f"K must be a 1-D vector of per-reaction constants, got ndim={Kv.ndim}")
    if Kv.shape[0] != Nm.shape[1]:
        raise DetailedBalanceError(f"len(K)={Kv.shape[0]} must equal the number of reactions N.shape[1]={Nm.shape[1]}")
    if not np.all(np.isfinite(Nm)):
        raise DetailedBalanceError("N must be all finite")
    if not np.all(np.isfinite(Kv)):
        raise DetailedBalanceError("K must be all finite")
    if not np.all(Kv > 0.0):
        raise DetailedBalanceError("K must be strictly positive (K_j = k_f/k_r > 0)")
    if max(Nm.shape, default=0) > MAX_DIM:
        raise DetailedBalanceError(f"N dimension {Nm.shape} exceeds MAX_DIM={MAX_DIM} (bounded refusal; this exact "
                                   "instrument is for small experimental networks)")
    # An exact kernel needs an exact object: the stoichiometric matrix must be integer-valued.  Refuse a
    # non-integer N rather than silently treating an approximate rank as structural truth.
    if not np.all(Nm == np.round(Nm)):
        raise DetailedBalanceError("N must be integer-valued (exact stoichiometry) to certify an exact kernel")
    Nint = np.round(Nm).astype(np.int64)
    if not np.all(Nint == Nm):  # overflow / huge magnitudes that do not round-trip through int64
        raise DetailedBalanceError("N entries are too large for the exact integer kernel (bounded refusal)")
    return Nm, Kv, Nint


def _exact_kernel(Nint: np.ndarray) -> Tuple[List[np.ndarray], int]:
    """Exact integer kernel of integer matrix Nint (S x R): a primitive-integer basis of {x in Q^R : N x = 0},
    plus the column rank.  Rational (Fraction) Gauss-Jordan elimination -- no floats, no threshold."""
    S, R = Nint.shape
    M = [[Fraction(int(Nint[i, j])) for j in range(R)] for i in range(S)]
    pivots: List[int] = []
    r = 0
    for c in range(R):
        piv = next((i for i in range(r, S) if M[i][c] != 0), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = M[r][c]
        M[r] = [x / inv for x in M[r]]
        for i in range(S):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [a - f * b for a, b in zip(M[i], M[r])]
        pivots.append(c)
        r += 1
        if r == S:
            break
    rank = len(pivots)
    pivset = set(pivots)
    basis: List[np.ndarray] = []
    for fcol in (c for c in range(R) if c not in pivset):
        x = [Fraction(0)] * R
        x[fcol] = Fraction(1)
        for ri, pc in enumerate(pivots):
            x[pc] = -M[ri][fcol]
        lcm = 1
        for v in x:
            d = v.denominator
            lcm = lcm * d // gcd(lcm, d)
        xi = [int(v * lcm) for v in x]
        g = 0
        for v in xi:
            g = gcd(g, abs(v))
        if g > 1:
            xi = [v // g for v in xi]
        basis.append(np.array(xi, dtype=float))
    return basis, rank


def check_detailed_balance(N, K, *, tol: float = 1e-9) -> WegscheiderVerdict:
    """Wegscheider / detailed-balance consistency of equilibrium constants K for stoichiometry N (closed system).

    The verdict is driven by the EXACT integer kernel of N (rational elimination); the floating SVD null space
    and lstsq membership are kept only as diagnostics.  Raises DetailedBalanceError on non-finite / non-positive
    K, shape mismatch, a non-integer or over-large N, or a dimension beyond MAX_DIM.
    """
    Nm, Kv, Nint = _validate(N, K)
    if not (np.isfinite(tol) and tol >= 0.0):
        raise DetailedBalanceError("tol must be a finite non-negative number")
    logK = np.log(Kv)

    # (authority) EXACT integer kernel: structural, no numerical rank.
    basis, exact_rank = _exact_kernel(Nint)
    res_a = 0.0
    offending: List[Tuple[np.ndarray, float]] = []
    for gi in basis:
        nrm = float(np.linalg.norm(gi))
        ghat = gi / nrm if nrm else gi
        d = float(np.dot(ghat, logK))
        res_a = max(res_a, abs(d))
        if abs(d) > tol:
            offending.append((ghat, d))
    ok_exact = res_a <= tol
    n_cycles = len(basis)

    # (diagnostic, NOT independent) floating lstsq image-membership residual.
    if Nm.shape[0] == 0:
        res_b = float(np.max(np.abs(logK))) if logK.size else 0.0
    else:
        mu, *_ = np.linalg.lstsq(Nm.T, logK, rcond=None)
        res_b = float(np.max(np.abs(Nm.T @ mu - logK))) if logK.size else 0.0
    ok_b = res_b <= tol

    # (diagnostic, NOT independent) floating SVD null-space rank.
    fbasis = null_space(Nm) if Nm.size else np.zeros((Nm.shape[1], 0))
    float_rank = int(Nm.shape[1] - fbasis.shape[1])

    return WegscheiderVerdict(
        consistent=bool(ok_exact),             # EXACT kernel is the authority, not a floating-rank cross-check
        residual=res_a,
        offending_cycles=offending,
        cycles=[g.astype(np.int64) for g in basis],   # legible integer cycles, e.g. (1,-1) for a duplicate reaction
        method_agreement=bool(ok_b == ok_exact),
        residual_image=res_b,
        n_cycles=int(n_cycles),
        exact_rank=int(exact_rank),
        float_rank=float_rank,
    )
