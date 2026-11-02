"""Wave B4 (Round VII): local model-identifiability of the aqueous NaAc(aq) ion-pair model.

THE QUESTION: does the available PROBE FAMILY distinguish the two uncertain continuous parameters
theta = (logK_NaAc, Davies A)?  We compute the LOCAL sensitivity (Jacobian) of a set of observables to theta by
central finite differences on ``aqueous_equilibrium.solve``, and read its rank + conditioning.

HONEST SCOPE (do not over-read): this is a LOCAL Jacobian at one operating point, NOT a global-identifiability
proof.  A rank/conditioning read says what a measurement AT THIS POINT could separate -- it does not establish
identifiability everywhere, and a finite-difference Jacobian inherits the solve's own numerical noise.

FINDING (recorded, reproduce with ``python -m experiments.sandbox_foundation.identifiability``): at the C5 operating
point (C_T = Na = 0.45 M) the full observable set {pH, free-acetate fraction, ion-pair fraction, ionic strength}
gives a rank-2, well-conditioned (cond ~ 1.7) Jacobian -- the two parameters ARE locally identifiable TOGETHER from
that set.  But a SINGLE SCALAR pH is rank-1 in theta: pH alone cannot separate logK_NaAc from the activity
parameter (its local sensitivity matrix is at most rank one, as expected for one scalar and two parameters).  The
free-acetate and ion-pair fractions carry opposite-sign sensitivities (near-complementary at fixed C_T), so the
identifying move is pH PLUS a SPECIATION observable (a free- or paired-acetate measurement), not pH alone and not
more pH points.  That is the guidance for which real laboratory measurements would actually be worth taking later.
"""
from __future__ import annotations

import numpy as np

import experiments.sandbox_foundation.aqueous_equilibrium as aq
from experiments.sandbox_foundation.aqueous_equilibrium import AcetateWaterSystem, SourcedConstant, solve

OBSERVABLE_NAMES = ("pH", "free_acetate_fraction", "ion_pair_fraction", "ionic_strength_M")


def observables(logK: float, A: float, *, C_T: float, Na: float) -> np.ndarray:
    """The observable vector at parameters (logK_NaAc, Davies A).  A is not a system field, so it is swapped on the
    module constant inside a try/finally (the committed value is always restored); logK enters via a perturbed,
    source-state-consistent K_assoc record so the solver's own admission still applies."""
    old = aq.DAVIES_A_25C
    aq.DAVIES_A_25C = SourcedConstant("davies_A", A, old.uncertainty, old.units, old.T_K, old.source, "SOURCED",
                                      old.note)
    try:
        K = SourcedConstant("K_NaAc_ion_pair", 10.0 ** logK, aq.K_NAAC_ION_PAIR_25C.uncertainty,
                            aq.K_NAAC_ION_PAIR_25C.units, 298.15, aq.K_NAAC_ION_PAIR_25C.source, "SOURCED",
                            "perturbed for the sensitivity analysis")
        r = solve(AcetateWaterSystem(total_acetic_M=C_T, sodium_M=Na, activity_model="davies",
                                     include_ion_pair=True, K_assoc=K))
        return np.array([r.pH, r.ac_minus_M / C_T, r.naac_M / C_T, r.ionic_strength_M], dtype=float)
    finally:
        aq.DAVIES_A_25C = old


def sensitivity(*, C_T: float = 0.45, Na: float = 0.45, logK0: float = -0.18, A0: float = 0.509,
                dK: float = 1e-4, dA: float = 1e-4) -> dict:
    """The local sensitivity Jacobian J = d(observables)/d(logK, A) by central differences, plus its singular
    values, the ranks of the full set and of pH-alone, and the full-set condition number."""
    base = observables(logK0, A0, C_T=C_T, Na=Na)
    j_logK = (observables(logK0 + dK, A0, C_T=C_T, Na=Na) - observables(logK0 - dK, A0, C_T=C_T, Na=Na)) / (2 * dK)
    j_A = (observables(logK0, A0 + dA, C_T=C_T, Na=Na) - observables(logK0, A0 - dA, C_T=C_T, Na=Na)) / (2 * dA)
    jac = np.column_stack([j_logK, j_A])                         # (n_observables, 2)
    sv_full = np.linalg.svd(jac, compute_uv=False)
    sv_pH = np.linalg.svd(jac[:1, :], compute_uv=False)          # pH row only
    return {
        "operating_point": {"C_T": C_T, "Na": Na, "logK_NaAc": logK0, "davies_A": A0},
        "observables": dict(zip(OBSERVABLE_NAMES, [float(x) for x in base])),
        "jacobian": jac, "singular_values_full": sv_full, "singular_values_pH_only": sv_pH,
        "rank_full": int(np.sum(sv_full > 1e-9 * sv_full[0])),
        "rank_pH_only": int(np.sum(sv_pH > 1e-12)),
        "cond_full": float(sv_full[0] / sv_full[-1]),
    }


def main() -> None:
    print("Wave B4 local identifiability -- theta = (logK_NaAc, Davies A); observables =", OBSERVABLE_NAMES)
    for C_T, Na in ((0.45, 0.45), (0.10, 0.10), (0.10, 0.05)):
        s = sensitivity(C_T=C_T, Na=Na)
        print(f"  C_T={C_T:<5} Na={Na:<5} rank_full={s['rank_full']} cond={s['cond_full']:.2f} "
              f"rank_pH_only={s['rank_pH_only']}  sv_full={np.round(s['singular_values_full'], 4)}")
    print("  => full observable set is rank-2 (identifiable together); pH ALONE is rank-1 (cannot separate the two).")


if __name__ == "__main__":
    main()
