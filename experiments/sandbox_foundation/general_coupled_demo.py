"""OPERATION XV Wave C (P2) -- committed demonstrations for the general coupled world.

Two UNRELATED coupled systems, both evolved by the SAME ``CoupledWorld.integrate`` with no edit to the integrator:

  (1) a synthetic two-cell REACTION-DIFFUSION network (2A -> B in cell 0, B -> 2A in cell 1, A and B diffusing across
      a membrane) -- a closed world with exact conservation, used to MEASURE the operator-splitting order; and
  (2) an ACETATE BUFFER under an acetic-acid feed with a fast-equilibrium PROJECTION (the Wave B operator composing in
      through an EquilibriumCoupling) -- an open world whose conserved components (C, Na) close while H/O/charge are
      reservoir-coupled to the implicit solvent.

Per the sandbox discipline (experiments-are-committed), every MEASURED number a Wave C claim rests on is produced by
this harness and pinned by test_general_coupled_xv.py.  Run as a script for the headline receipts.
"""
from __future__ import annotations

from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    EquilibriumCoupling,
    ExternalBoundary,
    InterfaceTransfer,
    splitting_convergence,
)
from experiments.sandbox_foundation.general_equilibrium import AcetateWaterEquilibriumOperator
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    MassActionIrreversible,
    Phase,
    Reaction,
    Species,
)

# --------------------------------------------------------------------------- (1) synthetic reaction-diffusion
# A conserved atom "R": A carries one, B carries two, so 2A <-> B balances R exactly.  Pure synthetic kinetics
# (ASSUMED_PARAMETER): the point is the coupling architecture and the measured splitting order, not real chemistry.
A = Species.of("A", {"R": 1}, charge=0, phase=Phase.AQUEOUS)
B = Species.of("B", {"R": 2}, charge=0, phase=Phase.AQUEOUS)


def build_reaction_diffusion_world():
    """Two cells (V0 = 1 L, V1 = 2 L); cell 0 runs 2A -> B, cell 1 runs B -> 2A; A and B diffuse across a membrane.

    R (reaction) and T (diffusion) genuinely do not commute (different reactions sit in the two cells the diffusion
    mixes), so the split is a real approximation -- exactly what makes the order measurement meaningful."""
    cell0 = ChemicalSystem(
        [A, B],
        [Reaction("2A->B", ((A, -2), (B, 1)), MassActionIrreversible(k=0.7, tier=ASSUMED_PARAMETER))],
        volume_L=1.0)
    cell1 = ChemicalSystem(
        [A, B],
        [Reaction("B->2A", ((B, -1), (A, 2)), MassActionIrreversible(k=0.4, tier=ASSUMED_PARAMETER))],
        volume_L=2.0)
    world = CoupledWorld(
        compartments=[Compartment("cell0", cell0), Compartment("cell1", cell1)],
        interfaces=[
            InterfaceTransfer("diffuse-A", "cell0", "cell1", A, A, k_transfer=0.5),
            InterfaceTransfer("diffuse-B", "cell0", "cell1", B, B, k_transfer=0.3),
        ])
    initial = {"cell0": {A: 1.0, B: 0.0}, "cell1": {A: 0.0, B: 0.5}}
    return world, initial


def build_pure_diffusion_world(V0=1.0, V1=3.0, k=0.8):
    """One species A diffusing between two cells, no reaction: the steady state is equal CONCENTRATION, i.e. the
    volume-weighted split n0 = total * V0 / (V0 + V1) -- a closed-form reference for the transport operator."""
    s0 = ChemicalSystem([A], [], volume_L=V0)
    s1 = ChemicalSystem([A], [], volume_L=V1)
    world = CoupledWorld(
        compartments=[Compartment("c0", s0), Compartment("c1", s1)],
        interfaces=[InterfaceTransfer("diffuse", "c0", "c1", A, A, k_transfer=k)])
    initial = {"c0": {A: 1.0}, "c1": {A: 0.0}}
    return world, initial


def build_single_reaction_compartment():
    """One compartment, 2A -> B, no interfaces/boundaries -- must reproduce the bare Wave A kernel integration."""
    sys = ChemicalSystem(
        [A, B],
        [Reaction("2A->B", ((A, -2), (B, 1)), MassActionIrreversible(k=0.9, tier=ASSUMED_PARAMETER))],
        volume_L=1.5)
    world = CoupledWorld(compartments=[Compartment("only", sys)])
    initial = {"only": {A: 2.0, B: 0.0}}
    return world, sys, initial


# --------------------------------------------------------------------------- (2) acetate buffer + feed + equilibrium
HAc = Species.of("HAc", {"C": 2, "H": 4, "O": 2}, charge=0, phase=Phase.AQUEOUS)
Acm = Species.of("Ac-", {"C": 2, "H": 3, "O": 2}, charge=-1, phase=Phase.AQUEOUS)
Hp = Species.of("H+", {"H": 1}, charge=1, phase=Phase.AQUEOUS)
OHm = Species.of("OH-", {"H": 1, "O": 1}, charge=-1, phase=Phase.AQUEOUS)
Nap = Species.of("Na+", {"Na": 1}, charge=1, phase=Phase.AQUEOUS)
NaAc = Species.of("NaAc", {"C": 2, "H": 3, "Na": 1, "O": 2}, charge=0, phase=Phase.AQUEOUS)

_ACETATE_TABLE = {"HAc": HAc, "Ac-": Acm, "H+": Hp, "OH-": OHm, "Na+": Nap, "NaAc": NaAc}


def build_acetate_buffer_world(volume_L=1.0, feed_rate=2.0e-4):
    """An acetate buffer (no kinetic reactions -- a pure fast-equilibrium compartment) fed acetic acid, with the Wave B
    acetate-water operator as its projection P.  Conserved: C (= 2 x acetate) and Na.  Reservoir-coupled: H, O, charge
    (set by the implicit water reservoir + electroneutrality).  Feed raises total acetate linearly; the SNIA-coupled
    final speciation must equal a one-shot Wave B solve at the net totals."""
    sys = ChemicalSystem([HAc, Acm, Hp, OHm, Nap, NaAc], [], volume_L=volume_L)
    coupling = EquilibriumCoupling(
        operator=AcetateWaterEquilibriumOperator(activity_model="ideal"),
        species_table=_ACETATE_TABLE,
        reservoir_components=frozenset({"H", "O", "charge"}))
    world = CoupledWorld(
        compartments=[Compartment("buffer", sys, equilibrium=coupling)],
        boundaries=[ExternalBoundary("HAc-feed", "buffer", HAc, mode="feed", rate=feed_rate)])
    initial = {"buffer": {HAc: 0.1 * volume_L, Nap: 0.05 * volume_L}}
    return world, sys, coupling, initial


def _fmt(d):
    return ", ".join(f"{getattr(k, 'name', k)}={v:.6g}" for k, v in d.items())


def main():
    print("=" * 96)
    print("WAVE C (1) synthetic two-cell reaction-diffusion -- operator-splitting order (MEASURED)")
    print("=" * 96)
    world, initial = build_reaction_diffusion_world()
    conv = splitting_convergence(world, initial, duration=4.0,
                                 steps_list=[2, 4, 8, 16, 32, 64, 128])
    for scheme in ("lie", "strang"):
        info = conv[scheme]
        print(f"  {scheme:7s} fitted order = {info['fitted_order']:.3f}")
        for dt, e in zip(info["dts"], info["errors"]):
            print(f"      dt={dt:8.4f}  Linf-error={e:.3e}")
    traj = world.integrate(initial, duration=4.0, n_steps=200, scheme="strang")
    print(f"  conservation drift (closed): {traj.max_conserved_drift:.3e}   tier={traj.tier}")
    print(f"  final cell0: {_fmt(traj.amounts['cell0'][-1])}")
    print(f"  final cell1: {_fmt(traj.amounts['cell1'][-1])}")

    print("=" * 96)
    print("WAVE C (2) acetate buffer + acetic-acid feed + fast-equilibrium projection (Wave B composes in)")
    print("=" * 96)
    bworld, bsys, coupling, binitial = build_acetate_buffer_world()
    btraj = bworld.integrate(binitial, duration=100.0, n_steps=200, scheme="strang")
    final = btraj.amounts["buffer"][-1]
    print(f"  final speciation: {_fmt(final)}")
    print(f"  conserved drift (C, Na): {btraj.max_conserved_drift:.3e}   feed-ledger resid: "
          f"{btraj.feed_ledger_residual:.3e}")
    print(f"  reservoir exchange (H/O/charge): {btraj.receipt.reservoir_exchange}")
    print(f"  tier={btraj.tier}")
    # one-shot Wave B cross-check at the net totals
    op = coupling.operator
    acetate_final = final[HAc] + final[Acm] + final[NaAc]
    sodium_final = final[Nap] + final[NaAc]
    direct = op.speciate({"acetate": acetate_final, "sodium": sodium_final}, volume_L=bsys.volume_L)
    print(f"  one-shot Wave B at net totals: {_fmt(direct.species_amounts)}")


if __name__ == "__main__":
    main()
