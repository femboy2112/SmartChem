"""Wave B2 -- physical units for mass-action rate constants, and the concentration-standard INVARIANCE of the
Wegscheider cycle constraint.

Ooh yeah, can do!  SYNTHETIC / idealized; a finite numerical check is NOT a universal proof.

A mass-action rate r_j [mol/(m^3 s)] of total concentration-order m_j has a rate constant k_j of units
        (mol/m^3)^(1 - m_j) / s,
so k's concentration-exponent is (1 - m_j).  A UNIMOLECULAR k (m=1 -> exponent 0, units 1/s) and a BIMOLECULAR k
(m=2 -> exponent -1, units (mol/m^3)^-1 / s) are NOT interchangeable just because both are Python floats:
`assert_interchangeable` refuses the swap.

For a reversible reaction the concentration equilibrium ratio Kc_j = k_f,j / k_r,j has concentration-exponent
        (m_r,j - m_f,j)   [= the net mole change dnu_j = sum_i N_ij for an ELEMENTARY law],
so Kc_j is DIMENSIONAL unless dnu_j = 0.  The dimensionless THERMODYNAMIC constant divides by a reference c^o:
        K^o_j = (k_f,j / k_r,j) / (c^o)^{dnu_j}.
k_f/k_r is NOT 'inherently dimensionless' -- only K^o is.

INVARIANCE THEOREM (proved, then checked exactly).  For every stoichiometric cycle gamma in ker(N),
        gamma . dnu = gamma^T (N^T ones) = (N gamma)^T ones = ones^T (N gamma) = ones^T 0 = 0
(because dnu = N^T ones as a per-reaction vector, and N gamma = 0).  A change of reference c^o shifts each
log K^o_j by -dnu_j log c^o, but the CYCLE sum sum_j gamma_j log K^o_j is unchanged (= sum_j gamma_j log Kc_j).
Hence the Wegscheider / detailed-balance cycle condition is INVARIANT under a consistent concentration-standard
change -- a different statement from the false claim that k_f/k_r is itself dimensionless.

EMPIRICAL CAVEAT.  For empirical kinetic orders the elementary identity dnu = m_r - m_f need NOT hold; the
detailed-balance relation must NOT be applied with N automatically.  `thermodynamic_K` returns a RESTRICTED
verdict (raises) when the kinetic mole change (m_r - m_f) disagrees with the structural dnu = sum_i N.
"""
from __future__ import annotations

import numpy as np

from experiments.sandbox_foundation.detailed_balance import exact_kernel, to_exact_int_matrix
from experiments.sandbox_foundation.twocell import InvalidParameterError, Mechanism


def forward_order_total(mech: Mechanism) -> np.ndarray:
    """m_f per reaction: the total forward concentration order (sum over species of order_f)."""
    return np.asarray(mech.order_f, float).sum(axis=0)


def reverse_order_total(mech: Mechanism) -> np.ndarray:
    """m_r per reaction: the total reverse concentration order (sum over species of order_r)."""
    return np.asarray(mech.order_r, float).sum(axis=0)


def rate_constant_conc_exponent(order_total) -> np.ndarray:
    """The power of (mol/m^3) in k's units, = 1 - m, for a rate in mol/(m^3 s)."""
    return 1.0 - np.asarray(order_total, float)


def rate_constant_units(order_total) -> str:
    """Human-readable units of a mass-action k of total order m: (mol/m^3)^(1-m) / s."""
    m = float(np.asarray(order_total, float))
    p = 1.0 - m
    if p == 0.0:
        return "1/s"
    ps = str(int(p)) if float(p).is_integer() else repr(p)
    return f"(mol/m^3)^{ps} / s"


def assert_interchangeable(order_total_a, order_total_b) -> None:
    """Refuse to treat two rate constants as the same quantity unless they have the SAME total order (hence the
    same units).  A unimolecular and a bimolecular constant are both floats but dimensionally distinct."""
    a = float(np.asarray(order_total_a, float))
    b = float(np.asarray(order_total_b, float))
    if a != b:
        raise InvalidParameterError(
            f"rate constants of order {a} ({rate_constant_units(a)}) and {b} ({rate_constant_units(b)}) are "
            "dimensionally distinct and cannot be interchanged")


def net_mole_change(mech: Mechanism) -> np.ndarray:
    """dnu per reaction = sum_i N_ij = (ones^T N)_j (the structural net change in mole number)."""
    return np.asarray(mech.N, float).sum(axis=0)


def equilibrium_conc_exponent(mech: Mechanism) -> np.ndarray:
    """Concentration-exponent of Kc_j = k_f,j/k_r,j, from the KINETIC orders: (m_r - m_f).  For an elementary law
    this equals the structural dnu; for an empirical law it may not."""
    return reverse_order_total(mech) - forward_order_total(mech)


def thermodynamic_K(mech: Mechanism, c_ref_mol_per_m3: float) -> np.ndarray:
    """Dimensionless K^o_j = (k_f,j/k_r,j) / (c^o)^{dnu_j} for every reversible reaction, c^o = c_ref.

    Requires complete, reversible rate constants.  Refuses (RESTRICTED verdict) unless the SPECIESWISE condition
            reverse_orders[i,j] - forward_orders[i,j] == N[i,j]   for EVERY species i and reaction j
    holds.  This is strictly stronger than the earlier total-order test (m_r - m_f == dnu), which is only
    NECESSARY, not sufficient: the counterexample A<->B with v_f = k_f[A]^2, v_r = k_r[B]^2 has equal total orders
    (m_f = m_r = 2) and dnu = 0, so the total test ADMITS it, yet the positive equilibrium ratio is
    [B]/[A] = sqrt(k_f/k_r), NOT k_f/k_r -- the elementary relation K^o = (k_f/k_r)/(c^o)^dnu is simply wrong for
    it.  The specieswise condition is exactly what makes k_f/k_r the mass-action equilibrium constant of the net
    reaction.  For an ELEMENTARY law it holds by construction (orders = complexes, N = product - reactant).

    SCOPE: this establishes only the STRUCTURAL compatibility of the claimed elementary equilibrium relation under
    the declared IDEAL (activity = concentration), isothermal standard-state assumptions.  It does NOT establish
    the physical validity of an arbitrary empirical rate law, nor admit non-ideal activities."""
    if not np.isfinite(c_ref_mol_per_m3) or c_ref_mol_per_m3 <= 0:
        raise InvalidParameterError("c_ref must be a finite positive reference concentration (mol/m^3)")
    mech.require_complete()
    if not all(r.reversible for r in mech.rates):
        raise InvalidParameterError("thermodynamic_K needs every reaction reversible (k_f and k_r)")
    N = np.asarray(mech.N, float)
    specieswise = np.asarray(mech.order_r, float) - np.asarray(mech.order_f, float)   # (S, R)
    if not np.allclose(specieswise, N, rtol=0, atol=1e-12):
        mism = specieswise - N
        bad = [(int(i), int(j)) for i, j in zip(*np.nonzero(np.abs(mism) > 1e-12))]
        raise InvalidParameterError(
            "specieswise (reverse_orders - forward_orders) != N per species; the elementary detailed-balance "
            f"relation K^o = (k_f/k_r)/(c^o)^dnu does not apply to these orders (RESTRICTED verdict). "
            f"Offending (species, reaction) indices: {bad}; mismatch (orr - of - N):\n{mism}")
    dnu = N.sum(axis=0)
    kf = np.array([r.k_f for r in mech.rates], float)
    kr = np.array([r.k_r for r in mech.rates], float)
    return (kf / kr) / (float(c_ref_mol_per_m3) ** dnu)


def standard_state_invariance_residual(N) -> float:
    """max over the EXACT integer kernel of N of |gamma . dnu|, dnu = sum_i N.  Exactly 0 by the invariance
    theorem (gamma . dnu = ones^T (N gamma) = 0).  Computed ENTIRELY in exact Python ints (the same exact kernel
    object as the Wegscheider check), so a stoichiometry above 2**53 / a kernel coordinate above int64 range stays
    exact -- no float64, no int64, no overflow."""
    Nint = to_exact_int_matrix(N)                       # exact Python ints (refuses non-integer / out-of-budget)
    basis, _ = exact_kernel(N)                           # exact Python-int kernel basis
    S = len(Nint)
    R = len(Nint[0]) if S else 0
    dnu = [sum(Nint[i][j] for i in range(S)) for j in range(R)]            # exact per-reaction net mole change
    res = 0
    for gamma in basis:
        a = sum(g * d for g, d in zip(gamma, dnu))                         # gamma . dnu                (exact int)
        ngamma = [sum(Nint[i][j] * gamma[j] for j in range(R)) for i in range(S)]
        b = sum(ngamma)                                                    # ones^T (N gamma)           (exact int)
        res = max(res, abs(a), abs(a - b))
    return float(res)
