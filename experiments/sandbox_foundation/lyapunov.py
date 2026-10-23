"""Wave C -- a free-energy / Lyapunov law for the closed, ideal, isothermal, fixed-volume sandbox.

Ooh yeah, can do!  Everything here is SYNTHETIC / idealized and says so.  A finite numerical check is NOT a
universal proof; the theorems below are proved analytically under EXPLICIT hypotheses, and the module also
computes the analytical time-derivative INDEPENDENTLY of any time integrator so a test can confirm the algebra
(not merely observe a decreasing trajectory).

THE FUNCTIONAL (relative free energy / volume-weighted generalized free energy; a Lyapunov candidate):

    Phi = sum_cells V_cell sum_species [ c log(c/c*) - c + c* ],     reference convention c* > 0 (declared).

Each per-species term h(c) = c log(c/c*) - c + c* is CONVEX in c (h'' = 1/c > 0 for c > 0), has h(c*) = 0 and
h'(c) = log(c/c*), and h(c) >= 0 with equality iff c = c* (extended continuously by h(0) = c*, since
c log c -> 0).  So Phi >= 0, = 0 iff c == c* everywhere.

HYPOTHESES (the closed passive world): closed system (no external flows), ideal (activity = concentration),
isothermal, fixed cell volumes, Fickian interface transport inflow_into_self = g (c_other - c_self) with
g >= 0, and -- for the reaction term only -- reversible ELEMENTARY mass action possessing a positive
DETAILED-BALANCED equilibrium c* (v_f,j(c*) = v_r,j(c*) for every reaction j; exactly the Wegscheider-consistent
case certified by detailed_balance.check_detailed_balance).  Both hypotheses are ENFORCED by refusal:
reaction_dissipation_rate raises for a non-elementary (empirical) mechanism and for a non-detailed-balanced c*,
because the closed form below is derived from orders = complexes and can INVERT the sign otherwise.  Driven / open
systems are OUT OF SCOPE and legitimately let Phi rise.

THEOREM C2 (diffusion dissipation, continuous).  Under the transport law alone,
    dPhi/dt|diff = - sum_faces sum_species g_i (c_i,A - c_i,B)(log c_i,A - log c_i,B)  <=  0,
because (a-b)(log a - log b) >= 0 for a,b > 0 (log is increasing, so the two factors share a sign).
Proof: dPhi/dt = sum_cells V_cell sum_i log(c_i,cell/c*_i) dc_i,cell/dt with dc_i,A/dt = (g_i/V_A)(c_i,B - c_i,A)
(and the mirror for B).  The V_cell cancels the 1/V_cell, the two cells' log(.../c*) combine, and c*_i cancels
within the difference, leaving the stated bilinear form.  (Diffusion drives toward spatial uniformity; the
equilibrium reference drops out of the diffusion term -- but Phi uses the SAME c* that the reaction term needs.)

THEOREM C1 (reaction dissipation, continuous).  For reversible elementary mass action with a detailed-balanced c*,
    dPhi/dt|rxn = - sum_cells V_cell sum_reactions (v_f,j - v_r,j) log(v_f,j / v_r,j)  <=  0,
because (v_f - v_r) log(v_f/v_r) >= 0.  Proof: log(v_f,j/v_r,j) = log K_j - sum_i N_ij log c_i (mass action), and
detailed balance at c* gives sum_i N_ij log c*_i = log K_j, so sum_i N_ij log(c_i/c*_i) = -log(v_f,j/v_r,j); multiply
by the net rate (v_f,j - v_r,j) and the volume, sum.  (This is why C1 NEEDS a Wegscheider-consistent K: no
detailed-balanced c* exists otherwise, and the functional is not a Lyapunov function -- see is_detailed_balance_eq.)

THEOREM C3 (discrete monotonicity of the two-cell diffusion update, Jensen).  The explicit-Euler face update is,
per species, c_A' = (1-alpha) c_A + alpha c_B and c_B' = (1-beta) c_B + beta c_A with alpha = h g / V_A,
beta = h g / V_B; under the supported positivity bound h <= dt_max = min(V_A,V_B)/g both lie in [0,1] (convex).
Then by Jensen on the convex h and the EXACT mass-transfer identity V_A alpha = V_B beta = h g:
    V_A h(c_A') + V_B h(c_B') <= V_A[(1-alpha)h(c_A)+alpha h(c_B)] + V_B[(1-beta)h(c_B)+beta h(c_A)]
                               =  V_A h(c_A) + V_B h(c_B),
the cross-terms cancelling exactly (coeff of h(c_A) is V_A(1-alpha)+V_B beta = V_A, and symmetrically).  So the
volume-weighted Phi cannot increase under a supported passive diffusion step.  (Per face; the chain in mesh.py
inherits it face by face.)  This is a DISCRETE statement for the supported dt range -- distinct from an
observation about a particular solver's trajectory.
"""
from __future__ import annotations

import numpy as np
from scipy.special import xlogy

from experiments.sandbox_foundation.twocell import InvalidParameterError, System, State


def _h(c: np.ndarray, c_star: np.ndarray) -> np.ndarray:
    """Per-species convex free-energy density c log(c/c*) - c + c*, extended by h(0) = c* (xlogy(0, .) = 0)."""
    c = np.asarray(c, float)
    c_star = np.asarray(c_star, float)
    return xlogy(c, c / c_star) - c + c_star


def _check_c_star(system: System, c_star) -> np.ndarray:
    cs = np.asarray(c_star, float)
    if cs.shape != (len(system.species),) or not np.all(np.isfinite(cs)) or np.any(cs <= 0):
        raise ValueError("c_star must be a finite, strictly positive reference, one per species")
    return cs


def relative_free_energy(system: System, state: State, c_star) -> float:
    """Phi = sum_cells V_cell sum_species h(c).  >= 0, and 0 iff every cell sits at c_star."""
    cs = _check_c_star(system, c_star)
    V = np.asarray(system.volumes_m3, float)
    c = state.concentration(system)                      # (2, S)
    return float(np.sum(V[:, None] * _h(c, cs[None, :])))


def diffusion_dissipation_rate(system: System, state: State) -> float:
    """Analytical INTERNAL diffusion contribution to dPhi/dt across the single interface (no c* -- it cancels):
        - sum_species g_i (c_A,i - c_B,i)(log c_A,i - log c_B,i)  <= 0.
    This is the diffusion term ONLY, not a whole-system passivity certificate (see total_dissipation_rate /
    is_closed_passive for the open/driven guard).  Independent of any integrator.  Limits made EXPLICIT:
      * g_i == 0 (immobile species): contribution is EXACTLY 0 -- zero diffusivity = no flux = no dissipation,
        computed BEFORE any multiply so the degenerate 0*inf never produces a NaN;
      * c_A,i == c_B,i: 0 (no concentration gradient -> no flux);
      * otherwise g_i (c_A - c_B)(log c_A - log c_B) >= 0, and -> +inf as a cell empties -- the ideal-dilute log
        singularity of the chemical potential: the dissipation is then unbounded but its SIGN is right (<= 0).
    Non-finite or negative concentrations are refused (fail closed)."""
    g = np.asarray(system.g, float)                      # (S,) m^3/s
    c = state.concentration(system)                      # (2, S)
    if not np.all(np.isfinite(c)) or np.any(c < 0.0):
        raise InvalidParameterError("diffusion_dissipation_rate needs finite, non-negative concentrations")
    cA, cB = c[0], c[1]
    dc = cA - cB
    with np.errstate(divide="ignore", invalid="ignore"):
        dlog = np.log(cA) - np.log(cB)
        # mask the degenerate cells (g==0 or no gradient) to 0 FIRST; np.where still evaluates the other branch,
        # but the errstate suppresses its 0*inf warning and np.where discards that masked NaN.
        contrib = np.where((g == 0.0) | (dc == 0.0), 0.0, g * dc * dlog)
    return float(-np.sum(contrib))


def _forward_reverse_rates(mech, c: np.ndarray, T_K=None):
    """(v_f, v_r) per reaction at concentration c (>=0 clip), both mol/(m^3 s).  v_r = 0 for an irreversible step.
    Admission-gated like Mechanism.rate_vector: a mechanism carrying an Applicability needs T_K and is refused
    (AdmissionDomainError) out of window / retracted; a plain mechanism is unaffected."""
    mech.require_complete()
    mech.require_admitted(T_K=T_K, conc_mol_m3=np.asarray(c, float))
    c = np.clip(np.asarray(c, float), 0.0, None)
    R = mech.n_reactions
    v_f = np.empty(R)
    v_r = np.zeros(R)
    for j, rate in enumerate(mech.rates):
        v_f[j] = rate.k_f * np.prod(c ** mech.order_f[:, j])
        if rate.reversible:
            v_r[j] = rate.k_r * np.prod(c ** mech.order_r[:, j])
    return v_f, v_r


def is_detailed_balance_equilibrium(system: System, c_star, *, tol: float = 1e-9, T_K=None) -> bool:
    """True iff c_star is a positive detailed-balanced equilibrium of the mechanism: v_f,j(c*) = v_r,j(c*) for
    every reversible reaction (the hypothesis C1 needs).  No mechanism / an irreversible step -> False."""
    cs = _check_c_star(system, c_star)
    mech = system.mechanism
    if mech is None or not all(r.reversible for r in mech.rates):
        return False
    v_f, v_r = _forward_reverse_rates(mech, cs, T_K)
    scale = np.maximum(np.abs(v_f), np.abs(v_r))
    scale = np.where(scale == 0.0, 1.0, scale)
    return bool(np.all(np.abs(v_f - v_r) / scale <= tol))


def reaction_dissipation_rate(system: System, state: State, c_star) -> float:
    """Analytical dPhi/dt from reaction, summed over cells:
        - sum_cells V_cell sum_reactions (v_f - v_r) log(v_f / v_r)  <= 0,
    VALID only when c_star is a detailed-balanced equilibrium (raises otherwise -- the theorem does not hold).
    Independent of any integrator."""
    cs = _check_c_star(system, c_star)
    mech = system.mechanism
    if mech is None:
        return 0.0
    if mech.kinetics != "elementary":
        raise ValueError(
            "the C1 reaction-dissipation theorem is proved ONLY for elementary mass action (kinetic orders = "
            "complex multiplicities); an empirical rate law needs a SEPARATELY derived generalization and is "
            "refused here. Applying -(v_f-v_r)log(v_f/v_r) with supplied empirical orders makes the closed form "
            "disagree with the true grad(Phi).(N@r) and can INVERT the sign of dPhi/dt")
    V = np.asarray(system.volumes_m3, float)
    c = state.concentration(system)                      # (2, S)
    Tc = state.temperature(system)                       # (2,) per-cell T feeds the admission gate
    if not is_detailed_balance_equilibrium(system, cs, T_K=float(Tc[0])):
        raise ValueError("reaction_dissipation_rate requires a detailed-balanced c_star (v_f(c*) = v_r(c*)); "
                         "without it Phi is not a Lyapunov function -- certify K with check_detailed_balance first")
    total = 0.0
    for cell in range(2):
        v_f, v_r = _forward_reverse_rates(mech, c[cell], float(Tc[cell]))
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.log(v_f) - np.log(v_r)
        d = v_f - v_r
        term = np.where(d == 0.0, 0.0, d * lr)
        total += V[cell] * float(np.sum(term))
    return float(-total)


def dPhi_dt_chain_rule(system: System, state: State, c_star) -> float:
    """dPhi/dt computed the GENERIC way: grad Phi . (dc/dt) = sum_cells V_cell sum_i log(c_i/c*_i) dc_i/dt, with
    dc/dt the FULL right-hand side (diffusion + reaction source).  This is independent of the simplified closed
    forms above; their agreement with this IS the proof's algebra, verified numerically in the tests."""
    cs = _check_c_star(system, c_star)
    V = np.asarray(system.volumes_m3, float)
    c = state.concentration(system)                      # (2, S)
    g = system.g
    dcdt = np.zeros_like(c)
    # diffusion: dc_A/dt = (g/V_A)(c_B - c_A), mirror for B
    dcdt[0] += (g / V[0]) * (c[1] - c[0])
    dcdt[1] += (g / V[1]) * (c[0] - c[1])
    # reaction source N @ r is already a concentration rate mol/(m^3 s)
    if system.mechanism is not None:
        for cell in range(2):
            dcdt[cell] += system.mechanism.source_density(c[cell], float(state.temperature(system)[cell]))
    with np.errstate(divide="ignore", invalid="ignore"):
        grad = np.log(c / cs[None, :])                   # h'(c) = log(c/c*)
    return float(np.sum(V[:, None] * grad * dcdt))


def is_closed_passive(system: System) -> bool:
    """True iff the system satisfies the CLOSED, PASSIVE hypotheses the dissipation theorem rests on: NO external
    species drive (every species boundary closed) AND no thermal drive (every thermal boundary adiabatic -- a
    heater or a fixed-T reservoir breaks the isothermal hypothesis).  A driven/open system can legitimately RAISE
    Phi, so its internal diffusion+reaction terms alone are NOT a whole-system passivity certificate."""
    sb_ok = all(b.kind == "closed" for b in system.species_boundaries)
    tb_ok = all(b.kind == "adiabatic" for b in system.thermal_boundaries)
    return bool(sb_ok and tb_ok)


def total_dissipation_rate(system: System, state: State, c_star) -> float:
    """WHOLE-SYSTEM passivity certificate dPhi/dt = internal diffusion + internal reaction (the reaction term only
    when c_star is detailed-balanced), which is <= 0 under the closed-passive hypotheses.

    FAIL-CLOSED on an open/driven system: if any species boundary carries an external flow or any thermal boundary
    drives the cell, the sum of the INTERNAL terms is not the complete dPhi/dt (an external source can make Phi
    rise legitimately), so certifying passivity from it would be a false claim from an incomplete ledger.  For a
    driven system use diffusion_dissipation_rate / reaction_dissipation_rate -- the labelled internal contributions
    that make no whole-system claim."""
    if not is_closed_passive(system):
        raise InvalidParameterError(
            "total_dissipation_rate certifies passivity only for a CLOSED, PASSIVE system (all species boundaries "
            "closed, all thermal boundaries adiabatic); this system is externally driven/open and an external "
            "source can legitimately raise Phi. Use diffusion_dissipation_rate / reaction_dissipation_rate for the "
            "internal contributions, which make no whole-system passivity claim")
    rxn = reaction_dissipation_rate(system, state, c_star) if system.mechanism is not None else 0.0
    return diffusion_dissipation_rate(system, state) + rxn
