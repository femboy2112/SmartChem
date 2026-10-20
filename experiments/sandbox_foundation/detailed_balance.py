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

The "cycles" here are STOICHIOMETRIC cycles (ker N: integer/real combinations of reactions whose net
stoichiometry vanishes), NOT graph-theoretic cycles of a species/complex graph.  The two can differ
(e.g. two distinct rate constants for the same net reaction 2A->B give the stoichiometric cycle (1,-1) with no loop of distinct species); it is
ker N that carries the condition.

Source relied on:  M. Feinberg, "Foundations of Chemical Reaction Network Theory", Applied Mathematical
Sciences 202, Springer (2019), the treatment of detailed balancing / the Wegscheider conditions for
reversible mass-action networks.  Historical origin: R. Wegscheider, Z. Phys. Chem. 39, 257-303 (1901).
(Cited from memory of the standard result; the proof above is self-contained and does not depend on
page-level citation.)

Two independent routes are computed and cross-checked:
  (a) ker(N) cycle route: orthonormal null-space basis (scipy.linalg.null_space, SVD-based);
      residual = max_k |gamma_k . log K| with each gamma_k unit-norm.
  (b) im(N^T) membership route: least-squares N^T mu = log K (numpy.linalg.lstsq);
      residual = || N^T mu* - log K ||_inf.
If the two routes disagree on the verdict the instrument FAILS CLOSED (consistent=False,
method_agreement=False).

SCOPE NOTE.  This instrument speaks ONLY to closed-system detailed-balance admissibility.  Driven /
open systems (chemostats, external work, light, imposed reservoirs) legitimately sustain nonequilibrium
cycles and are OUT OF SCOPE; a failed Wegscheider check must NOT be read as forbidding them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from scipy.linalg import null_space


class DetailedBalanceError(ValueError):
    """Raised (fail-closed) on malformed N / K input; nothing is silently coerced."""


@dataclass(frozen=True)
class WegscheiderVerdict:
    """Verdict of the Wegscheider check.

    consistent         True iff BOTH routes pass within tol (and so agree).
    residual           route (a): max over unit-norm ker(N) basis vectors of |gamma . log K| (0.0 if ker N is trivial).
    offending_cycles   list of (gamma, imbalance): unit-norm ker(N) basis vectors with |gamma . log K| > tol and the
                       signed value gamma . log K (the cycle's log-product imbalance; basis sign/scale is arbitrary,
                       up to a unit-norm convention -- compare magnitudes).
    method_agreement   True iff routes (a) and (b) give the same consistent/inconsistent verdict.
    residual_image     route (b): || N^T mu* - log K ||_inf.
    n_cycles           dim ker(N).
    """
    consistent: bool
    residual: float
    offending_cycles: List[Tuple[np.ndarray, float]] = field(default_factory=list)
    method_agreement: bool = True
    residual_image: float = 0.0
    n_cycles: int = 0


def _validate(N, K) -> Tuple[np.ndarray, np.ndarray]:
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
    return Nm, Kv


def check_detailed_balance(N, K, *, tol: float = 1e-9) -> WegscheiderVerdict:
    """Wegscheider / detailed-balance consistency of equilibrium constants K for stoichiometry N (closed system).

    Raises DetailedBalanceError on non-finite / non-positive K, shape mismatch, or malformed N.
    """
    Nm, Kv = _validate(N, K)
    if not (np.isfinite(tol) and tol >= 0.0):
        raise DetailedBalanceError("tol must be a finite non-negative number")
    logK = np.log(Kv)

    # (a) ker(N) cycle route.  null_space returns an orthonormal basis, shape (R, dim ker N).
    basis = null_space(Nm) if Nm.size else np.eye(Nm.shape[1])
    dots = basis.T @ logK if basis.shape[1] else np.zeros(0)
    res_a = float(np.max(np.abs(dots))) if dots.size else 0.0
    ok_a = res_a <= tol
    offending = [(basis[:, k].copy(), float(dots[k])) for k in range(dots.size) if abs(dots[k]) > tol]

    # (b) im(N^T) membership route: min_mu || N^T mu - log K ||.
    if Nm.shape[0] == 0:
        res_b = float(np.max(np.abs(logK))) if logK.size else 0.0
    else:
        mu, *_ = np.linalg.lstsq(Nm.T, logK, rcond=None)
        res_b = float(np.max(np.abs(Nm.T @ mu - logK))) if logK.size else 0.0
    ok_b = res_b <= tol

    agree = ok_a == ok_b
    return WegscheiderVerdict(
        consistent=bool(ok_a and ok_b),   # fail closed: a split verdict is never "consistent"
        residual=res_a,
        offending_cycles=offending,
        method_agreement=bool(agree),
        residual_image=res_b,
        n_cycles=int(basis.shape[1]),
    )
