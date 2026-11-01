"""OPERATION XV Wave D PREP (first consumer) -- the ammonia protonation buffer as a STIFF kinetic network.

Wave D's spine is an NH3 / NH4+ buffer and a stiff reaction network.  This module is the bounded, honest FIRST step:
it declares ammonia protonation

    NH3 + H+  <=>  NH4+          (reversible mass action; kf diffusion-limited, kr = kf * Ka(NH4+))

through the Wave A general kernel -- a DISTINCT base-buffer chemistry from the acetate work, proving the kernel
generalizes.  Two honest properties are demonstrated, not asserted:

  * STIFFNESS: proton transfer is near diffusion-limited (kf ~ 1e10 /M/s), so the protonation relaxes on a ~1e-5 s
    timescale while the run spans ~1 s -- a timescale separation of ~1e5.  The implicit BDF integrator (the kernel's
    default) resolves it; the trajectory reaches a finite-time fixed point with conservation intact.
  * DETAILED BALANCE as the cross-check: the kinetic fixed point is NOT read off a fitted curve -- at r_vol = 0 the
    mass-action law forces  [NH4+] / ([NH3] [H+]) = kf / kr = 1 / Ka(NH4+)  EXACTLY, so the measured fixed-point ratio
    is checked against the declared 1/Ka (the equilibrium relation the rate constants' RATIO encodes).

PROVENANCE / HONESTY: kf is an ASSUMED_PARAMETER (a representative diffusion-limited value, not sourced for THIS
system); only the RATIO kf/kr is pinned to a literature Ka(NH4+) (pKa 9.25).  So the trajectory's admitted tier is
ASSUMED_PARAMETER -- the kinetics are a representative model, and no stronger claim is made.  Ka is used to set the
fixed point the kinetics relax to, exactly as the acetate work used its Ka.

NOT built here (declared Wave D next steps, not faked): the full multiphase consumer.  NH3(aq) <=> NH3(g) stripping
attaches through the Wave C ``InterfaceTransfer`` (an aqueous<->gas phase pair with a Henry partition) and a gas
headspace compartment -- but a SOURCED, verified Henry constant for ammonia is not established in this sandbox, so the
gas coupling is left as a declared extension rather than a fabricated parameter.
"""
from __future__ import annotations

import math

from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    MassActionReversible,
    Phase,
    Reaction,
    Species,
)

# pKa of the ammonium ion NH4+ at 25 C ~ 9.25  ->  Ka = 10^-9.25.  Literature tertiary value; used to set kf/kr.
PKA_NH4 = 9.25
KA_NH4 = 10.0 ** (-PKA_NH4)

NH3 = Species.of("NH3", {"N": 1, "H": 3}, charge=0, phase=Phase.AQUEOUS)
NH4 = Species.of("NH4+", {"N": 1, "H": 4}, charge=1, phase=Phase.AQUEOUS)
Hp = Species.of("H+", {"H": 1}, charge=1, phase=Phase.AQUEOUS)


def build_ammonia_protonation_system(kf: float = 1.0e10, Ka: float = KA_NH4, volume_L: float = 1.0) -> ChemicalSystem:
    """NH3 + H+ <=> NH4+ as reversible mass action, with kr = kf * Ka so the fixed point sits at the declared Ka.

    kf is a representative diffusion-limited proton-transfer constant (ASSUMED_PARAMETER); only kf/kr = 1/Ka is
    pinned to chemistry."""
    kr = kf * Ka
    rxn = Reaction(
        "NH3+H+<=>NH4+",
        ((NH3, -1), (Hp, -1), (NH4, 1)),
        MassActionReversible(kf=kf, kr=kr, tier=ASSUMED_PARAMETER,
                             source=f"kf diffusion-limited (assumed); kf/kr = 1/Ka, pKa(NH4+)={PKA_NH4}"))
    return ChemicalSystem([NH3, NH4, Hp], [rxn], volume_L=volume_L)


def run_ammonia_buffer(kf: float = 1.0e10, Ka: float = KA_NH4, *, nh3_M: float = 0.1, h_M: float = 0.1,
                       duration: float = 1.0):
    """Integrate the stiff protonation from an off-equilibrium start and return the fixed point + its detailed-balance
    residual.  Returns (trajectory, info) with info carrying the measured fixed-point ratio vs the declared 1/Ka."""
    sys = build_ammonia_protonation_system(kf=kf, Ka=Ka)
    traj = sys.integrate({NH3: nh3_M * sys.volume_L, Hp: h_M * sys.volume_L}, duration=duration,
                         n_samples=60, method="BDF", declared_kinetic_tier=ASSUMED_PARAMETER)
    final = traj.amounts[-1]
    V = sys.volume_L
    c_nh3, c_nh4, c_h = final[NH3] / V, final[NH4] / V, final[Hp] / V
    measured_ratio = c_nh4 / (c_nh3 * c_h) if c_nh3 * c_h > 0 else float("inf")
    target_ratio = 1.0 / Ka
    rel = abs(measured_ratio - target_ratio) / target_ratio
    info = {
        "measured_ratio": measured_ratio, "target_ratio_1_over_Ka": target_ratio,
        "detailed_balance_rel_residual": rel, "fixed_point": {"NH3": c_nh3, "NH4+": c_nh4, "H+": c_h},
        "stiffness_timescale_s": 1.0 / (kf * max(h_M, 1e-12)), "run_duration_s": duration,
        "conservation_drift": traj.max_component_drift, "tier": traj.tier,
    }
    return traj, info


def main():
    print("=" * 96)
    print("WAVE D PREP -- ammonia protonation NH3 + H+ <=> NH4+ as a stiff kinetic network (general kernel)")
    print("=" * 96)
    _traj, info = run_ammonia_buffer()
    print(f"  fixed point (mol/L): NH3={info['fixed_point']['NH3']:.6g}  NH4+={info['fixed_point']['NH4+']:.6g}  "
          f"H+={info['fixed_point']['H+']:.6g}")
    print(f"  detailed balance:  measured [NH4+]/([NH3][H+]) = {info['measured_ratio']:.6g}")
    print(f"                     declared 1/Ka               = {info['target_ratio_1_over_Ka']:.6g}")
    print(f"                     relative residual           = {info['detailed_balance_rel_residual']:.3e}")
    print(f"  stiffness: relax timescale ~{info['stiffness_timescale_s']:.2e} s over a {info['run_duration_s']:.3g} s "
          f"run (separation ~{info['run_duration_s'] / info['stiffness_timescale_s']:.1e})")
    print(f"  conservation drift (N, H, charge): {info['conservation_drift']:.3e}")
    print(f"  admitted tier: {info['tier']}  (kf assumed; only kf/kr is pinned to Ka)")
    assert info["detailed_balance_rel_residual"] < 1e-6
    assert math.isfinite(info["measured_ratio"])


if __name__ == "__main__":
    main()
