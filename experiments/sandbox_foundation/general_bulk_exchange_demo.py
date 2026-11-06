"""OPERATION XXI section 5 -- bulk-liquid exchange vs a selective membrane, on ONE generic integrator.

Two well-mixed, constant-volume aqueous acetate-buffer compartments A and B, started at DIFFERENT compositions, run
under three interface regimes with NO change to the integrator (only the declared operators differ):

  Mode "membrane"  SELECTIVE MEMBRANE  -- InterfaceTransfer of the NEUTRAL acetic acid only (HAc); the IONS (Na+, Ac-)
                                          cannot cross, so the two compartments keep different ionic strengths and the
                                          sodium gradient never relaxes.
  Mode "bulk"      BULK EXCHANGE       -- ElectroneutralBulkExchange swaps equal LIQUID PARCELS: the WHOLE dissolved
                                          set (HAc, Ac-, H+, OH-, Na+, NaAc) advects together at one Q, so Na and total
                                          acetate BOTH relax toward a common well-mixed composition, and no compartment
                                          is left charged.
  Mode "closed"    CLOSED              -- no transfer.

Every mode conserves the non-reservoir components C and Na globally and leaves each compartment electroneutral (charge
is the implicit-water reservoir's to close); only the TRANSPORT regime differs.  This is the Wave-B demonstration that
the one generic CoupledWorld.integrate distinguishes a membrane from bulk mixing.
"""
from __future__ import annotations

from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledWorld,
    ElectroneutralBulkExchange,
    EquilibriumCoupling,
    InterfaceTransfer,
)
from experiments.sandbox_foundation.general_coupled_demo import Acm, HAc, Hp, NaAc, Nap, OHm, _ACETATE_TABLE
from experiments.sandbox_foundation.general_equilibrium import AcetateWaterEquilibriumOperator
from experiments.sandbox_foundation.general_kernel import ChemicalSystem

_ACETATE_SPECIES = [HAc, Acm, Hp, OHm, Nap, NaAc]
_FULL_SOLUTION_PAIRS = tuple((s, s) for s in _ACETATE_SPECIES)   # bulk parcel carries EVERY dissolved species


def _buffer_compartment(name, volume_L):
    sys = ChemicalSystem(list(_ACETATE_SPECIES), [], volume_L=volume_L)
    coupling = EquilibriumCoupling(
        operator=AcetateWaterEquilibriumOperator(activity_model="ideal"),
        species_table=dict(_ACETATE_TABLE),
        reservoir_components=frozenset({"H", "O", "charge"}))
    return Compartment(name, sys, equilibrium=coupling)


def build_two_buffer_world(mode="bulk", *, Q=0.02, k_mem=0.02, VA=1.0, VB=1.0, initial=None):
    """Two acetate buffers A (acid-rich) and B (sodium-rich) under one of the three interface regimes.

    ``Q`` is the bulk volumetric exchange rate (L/s); ``k_mem`` the selective-membrane coefficient (L/s).  The default
    initial state puts a gradient in BOTH acetate and sodium so membrane vs bulk are clearly distinguishable."""
    A = _buffer_compartment("A", VA)
    B = _buffer_compartment("B", VB)
    interfaces, bulk = (), ()
    if mode == "membrane":
        interfaces = (InterfaceTransfer("mem-HAc", "A", "B", HAc, HAc, k_transfer=k_mem),)
    elif mode == "bulk":
        bulk = (ElectroneutralBulkExchange("bulk-mix", "A", "B", species_pairs=_FULL_SOLUTION_PAIRS, Q_L_per_s=Q),)
    elif mode != "closed":
        raise ValueError(f"unknown mode {mode!r}")
    world = CoupledWorld([A, B], interfaces=interfaces, bulk_exchanges=bulk)
    if initial is None:
        # Both compartments stay in the buffer regime (Na < total acetate, so Na+ is balanced by Ac-, not alkalinity),
        # with a gradient in BOTH total acetate and sodium to drive transport.
        initial = {"A": {HAc: 0.20 * VA, Nap: 0.08 * VA},     # concentrated, acetate-rich
                   "B": {HAc: 0.05 * VB, Nap: 0.04 * VB}}      # dilute
    return world, initial


def run(mode="bulk", *, duration=60.0, n_steps=120, n_samples=None, **kw):
    world, initial = build_two_buffer_world(mode, **kw)
    return world.integrate(initial, duration=duration, n_steps=n_steps, n_samples=n_samples, scheme="strang")


if __name__ == "__main__":
    import math
    for mode in ("closed", "membrane", "bulk"):
        tr = run(mode)
        hA = tr.amounts["A"][-1][Hp] / 1.0
        hB = tr.amounts["B"][-1][Hp] / 1.0
        naA = tr.amounts["A"][-1][Nap] / 1.0
        naB = tr.amounts["B"][-1][Nap] / 1.0
        print(f"{mode:9s}: pH_A={-math.log10(hA):.3f} pH_B={-math.log10(hB):.3f}  "
              f"Na+_A={naA:.4f} Na+_B={naB:.4f}  tier={tr.tier}")
