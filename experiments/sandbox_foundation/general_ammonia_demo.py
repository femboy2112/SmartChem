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

from experiments.sandbox_foundation.ammonia_equilibrium import KW
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    EquilibriumCoupling,
    ExternalBoundary,
    InterfaceTransfer,
)
from experiments.sandbox_foundation.general_equilibrium import AmmoniaWaterEquilibriumOperator
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

NH3 = Species.of("NH3", {"N": 1, "H": 3}, charge=0, phase=Phase.AQUEOUS, substance="NH3")
NH4 = Species.of("NH4+", {"N": 1, "H": 4}, charge=1, phase=Phase.AQUEOUS)
Hp = Species.of("H+", {"H": 1}, charge=1, phase=Phase.AQUEOUS)
OHm = Species.of("OH-", {"H": 1, "O": 1}, charge=-1, phase=Phase.AQUEOUS)
H2O = Species.of("H2O", {"H": 2, "O": 1}, charge=0, phase=Phase.AQUEOUS)
Nap = Species.of("Na+", {"Na": 1}, charge=1, phase=Phase.AQUEOUS)
Clm = Species.of("Cl-", {"Cl": 1}, charge=-1, phase=Phase.AQUEOUS)
NH3g = Species.of("NH3(g)", {"N": 1, "H": 3}, charge=0, phase=Phase.GAS, substance="NH3")   # same substance as NH3(aq), differs only in phase (XVI-P0.1: the shared substance licenses the Henry transfer)

# a dimensionless gas/liquid partition for ammonia is an ASSUMED_PARAMETER here (literature conventions span ~6e-6 to
# ~1e-3 for c_gas/c_aq); the stripping demo proves the coupling ARCHITECTURE + conservation, not a validated rate/fraction
AMMONIA_PARTITION_AQ_OVER_GAS = 1000.0     # c_aq / c_gas at interface equilibrium (ammonia strongly favours water)


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


def build_full_ammonia_water_network(kf_prot=1.0e10, Ka=KA_NH4, kr_water=1.4e11, volume_L=1.0):
    """The FULL stiff ammonia-water kinetic network with EXPLICIT water (so E.N=0 holds over all species):

        R1: NH3 + H+ <=> NH4+        (kf_prot diffusion-limited; kr1 = kf_prot * Ka)
        R2: H2O <=> H+ + OH-         (kr_water diffusion-limited recombination; kf2 set so [H+][OH-] -> Kw at ~55.5 M)

    Cl- is an inert counter-ion (spectator) that keeps the declared buffer electroneutral.  Two reactions with a ~1e10
    rate ratio against the slow approach to the joint fixed point -> genuinely stiff; BDF resolves it."""
    water_M = 55.5
    kf_water = kr_water * KW / water_M        # so kf_water*[H2O] = kr_water*[H+][OH-] gives [H+][OH-] = Kw at 55.5 M
    sys = ChemicalSystem(
        [NH3, NH4, Hp, OHm, H2O, Clm],
        [Reaction("NH3+H+<=>NH4+", ((NH3, -1), (Hp, -1), (NH4, 1)),
                  MassActionReversible(kf=kf_prot, kr=kf_prot * Ka, tier=ASSUMED_PARAMETER)),
         Reaction("H2O<=>H+ + OH-", ((H2O, -1), (Hp, 1), (OHm, 1)),
                  MassActionReversible(kf=kf_water, kr=kr_water, tier=ASSUMED_PARAMETER))],
        volume_L=volume_L)
    return sys, water_M


def ammonia_network_vs_operator_crosscheck(total_ammonia_M=0.1, strong_acid_M=0.05, volume_L=1.0):
    """CROSS-CHECK binding Wave A (kinetics) and the Wave D operator (algebra): relax the full stiff network from an
    off-equilibrium buffer to its fixed point, and compare its NH3/NH4+/H+/OH- speciation to an INDEPENDENT one-shot
    AmmoniaWaterEquilibriumOperator solve on the SAME conserved totals.  Both describe the unique equilibrium for those
    totals, so they must agree -- a kinetic fixed point corroborated by an algebraic solve, neither derived from the
    other."""
    sys, _water_M = build_full_ammonia_water_network(volume_L=volume_L)
    V = volume_L
    nh4_0 = strong_acid_M * V           # start with NH4Cl (-> NH4+ + Cl-) + free NH3, electroneutral
    nh3_0 = (total_ammonia_M - strong_acid_M) * V
    n0 = {NH3: nh3_0, NH4: nh4_0, Clm: strong_acid_M * V, H2O: 55.5 * V, Hp: 1e-7 * V, OHm: 1e-7 * V}
    traj = sys.integrate(n0, duration=1.0, n_samples=40, method="BDF", declared_kinetic_tier=ASSUMED_PARAMETER)
    f = traj.amounts[-1]
    kinetic = {"NH3": f[NH3] / V, "NH4+": f[NH4] / V, "H+": f[Hp] / V, "OH-": f[OHm] / V}

    op = AmmoniaWaterEquilibriumOperator()
    st = op.speciate({"ammonia": total_ammonia_M * V, "strong_acid": strong_acid_M * V}, volume_L=V)
    operator = {k: st.species_amounts[k] / V for k in ("NH3", "NH4+", "H+", "OH-")}

    rel = {k: abs(kinetic[k] - operator[k]) / max(operator[k], 1e-30) for k in kinetic}
    return {"kinetic": kinetic, "operator": operator, "rel_residual": rel,
            "max_rel_residual": max(rel.values()), "conservation_drift": traj.max_component_drift,
            "kinetic_pH": -math.log10(kinetic["H+"]), "operator_pH": st.derived["pH"]}


def build_ammonia_stripping_world(volume_L=1.0, gas_volume_L=1.0, naoh_M=0.05, total_ammonia_M=0.1,
                                  k_interface=0.2, purge=False, k_purge=0.5):
    """A MULTIPHASE Wave C world: an aqueous ammonia buffer (with the Wave D equilibrium operator as its projection)
    over a gas headspace, coupled by an NH3(aq) <=> NH3(g) interface at a declared Henry partition.  NaOH makes it
    basic so free NH3 exists to transfer.  ``purge=True`` adds a fixed-activity boundary holding NH3(g) ~ 0 (a sweep
    gas) -> continuous STRIPPING; nitrogen then leaves via the (ledgered) purge, otherwise N is conserved across the
    two phases.  Henry partition + mass-transfer coefficient are ASSUMED_PARAMETER (the dynamics are not validated)."""
    liq = ChemicalSystem([NH3, NH4, Hp, OHm, Nap, Clm], [], volume_L=volume_L)
    coupling = EquilibriumCoupling(
        operator=AmmoniaWaterEquilibriumOperator(),
        species_table={"NH3": NH3, "NH4+": NH4, "H+": Hp, "OH-": OHm, "Na+": Nap, "Cl-": Clm},
        reservoir_components=frozenset({"H", "O", "charge"}))
    gas = ChemicalSystem([NH3g], [], volume_L=gas_volume_L)
    boundaries = []
    if purge:
        boundaries.append(ExternalBoundary("sweep", "gas", NH3g, mode="fixed_activity",
                                           k_transfer=k_purge, target_conc=0.0))
    world = CoupledWorld(
        compartments=[Compartment("liq", liq, equilibrium=coupling), Compartment("gas", gas)],
        interfaces=[InterfaceTransfer("NH3-volatilization", "liq", "gas", NH3, NH3g,
                                      k_transfer=k_interface, partition=AMMONIA_PARTITION_AQ_OVER_GAS)],
        boundaries=boundaries)
    initial = {"liq": {NH4: 0.0, NH3: total_ammonia_M * volume_L, Nap: naoh_M * volume_L}, "gas": {NH3g: 0.0}}
    return world, coupling, initial


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

    print("=" * 96)
    print("WAVE D -- full stiff ammonia-water network (explicit water) vs the equilibrium operator (cross-check)")
    print("=" * 96)
    x = ammonia_network_vs_operator_crosscheck()
    print(f"  kinetic fixed point:  NH3={x['kinetic']['NH3']:.6g} NH4+={x['kinetic']['NH4+']:.6g} "
          f"H+={x['kinetic']['H+']:.4g} OH-={x['kinetic']['OH-']:.4g}  (pH {x['kinetic_pH']:.4f})")
    print(f"  operator (one-shot):  NH3={x['operator']['NH3']:.6g} NH4+={x['operator']['NH4+']:.6g} "
          f"H+={x['operator']['H+']:.4g} OH-={x['operator']['OH-']:.4g}  (pH {x['operator_pH']:.4f})")
    print(f"  max relative residual kinetic-vs-operator: {x['max_rel_residual']:.3e}")
    print(f"  full-network conservation drift (N,H,O,charge, explicit water): {x['conservation_drift']:.3e}")

    print("=" * 96)
    print("WAVE D -- multiphase NH3(g) stripping (Wave C coupling: liquid buffer + gas headspace + Henry interface)")
    print("=" * 96)
    # the Henry partition + mass-transfer coefficients are ASSUMED_PARAMETER, so the DYNAMIC prediction is capped there
    # (weakest-premise); the conservation bookkeeping is still exact and visible in the drift number reported below
    cworld, _c, cinit = build_ammonia_stripping_world(purge=False)
    ctraj = cworld.integrate(cinit, duration=200.0, n_steps=200, scheme="strang",
                             declared_kinetic_tier=ASSUMED_PARAMETER)
    lf, gf = ctraj.amounts["liq"][-1], ctraj.amounts["gas"][-1]
    c_aq, c_gas = lf[NH3] / 1.0, gf[NH3g] / 1.0
    print(f"  CLOSED partitioning: NH3(aq)={c_aq:.6g} M  NH3(g)={c_gas:.6g} M  ratio c_aq/c_gas={c_aq / c_gas:.4g} "
          f"(declared {AMMONIA_PARTITION_AQ_OVER_GAS:.4g})")
    tot_N = lf[NH3] + lf[NH4] + gf[NH3g]
    print(f"  total N across phases conserved: drift {ctraj.max_conserved_drift:.3e}  (N_final={tot_N:.6g})  "
          f"tier={ctraj.tier}")

    oworld, _o, oinit = build_ammonia_stripping_world(purge=True)
    otraj = oworld.integrate(oinit, duration=200.0, n_steps=200, scheme="strang",
                             declared_kinetic_tier=ASSUMED_PARAMETER)
    lo = otraj.amounts["liq"]
    n0 = lo[0][NH3] + lo[0][NH4]
    nf = lo[-1][NH3] + lo[-1][NH4]
    print(f"  OPEN stripping (sweep gas): liquid total ammonia {n0:.6g} -> {nf:.6g} mol "
          f"({100 * (n0 - nf) / n0:.2f}% stripped)")
    print(f"    reservoir/ledgered exchange: {otraj.receipt.reservoir_exchange}  tier={otraj.tier}")


if __name__ == "__main__":
    main()
