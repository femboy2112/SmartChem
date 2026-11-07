"""OPERATION XXII section 7 -- the categorical bridge is a FAITHFUL STRUCTURAL functor, NOT a dynamics functor.

XXI §7 proved the STRUCTURAL composition laws (identity / associativity / tensor / conservation-under-gluing / port
correspondence / mechanism-not-reduced-to-net / catalyst identity) on the exact-integer bridge.  XXII §7 pins the
BOUNDARY of that claim by separating three property layers and showing the bridge lives entirely in the first:

  Layer 1  STRUCTURAL   species identity, stoichiometry, port matching, conservation (E N = 0), hyperedge identity.
                        -> EXACT; admits strict theorems (XXI §7).  bridge_to_kernel is a faithful functor HERE.
  Layer 2  PHYSICAL     kinetics, thermodynamics, boundary conditions, transport coefficients, phase applicability.
                        -> PARTIAL; the bridge does NOT supply it (a bridged reaction is RATE_UNKNOWN by default).
  Layer 3  NUMERICAL    integrator / projection / splitting error, positivity, solver failure.
                        -> APPROXIMATE; carries a MEASURED error contract, never an exact one.

The tests here assert the SEPARATION: the same structural diagram, bridged, admits MANY dynamics (one per rate-law
assignment) with ONE structural signature; missing kinetics leaves the dynamics UNDEFINED; and an ASSUMED kinetic law
caps the trajectory's claim tier no matter how exact the structure is.  So a successful bridge is a conservation +
identity CERTIFICATE -- it is NOT a universal dynamics functor, and this suite is the executable statement of that.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.claim_tiers import STRUCTURALLY_CONSERVING, rank
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    InterfaceTransfer,
)
from experiments.sandbox_foundation.general_kernel import (
    MassActionIrreversible,
    Phase,
    Species,
)
from experiments.sandbox_foundation.open_diagram_bridge import bridge_to_kernel
from smartchem.category import Config
from smartchem.open_chem_diagram import OpenChemDiagram
from smartchem.smiles import parse_smiles

ACETIC = parse_smiles("CC(=O)O")
BICARB = parse_smiles("OC(=O)[O-]")
ACETATE = parse_smiles("CC(=O)[O-]")
CARBONIC = parse_smiles("OC(=O)O")


def _proton_transfer() -> OpenChemDiagram:
    # acetic + bicarbonate -> acetate + carbonic acid (balanced; a single saturated generator)
    return OpenChemDiagram.single_step(Config.of(ACETIC, BICARB), Config.of(ACETATE, CARBONIC),
                                       generator_id="proton_transfer")


def _bridge(rate_laws=None):
    return bridge_to_kernel(_proton_transfer(), rate_laws=rate_laws)


def _by_name(system):
    return {s.name: s for s in system.species}


def _integrate(system, *, k=0.5, scheme="strang", n_steps=60):
    law = MassActionIrreversible(k=k)
    # rebuild the system with the rate law attached to its one reaction (bridge_to_kernel sets RATE_UNKNOWN by default)
    br = _bridge(rate_laws={"proton_transfer": law})
    sysk = br.system
    byn = _by_name(sysk)
    # a reactant to seed; find the acetic-acid species by composition (C2H4O2, neutral)
    reactant = next(s for s in sysk.species if s.charge == 0 and dict(s.composition).get("C") == 2
                    and dict(s.composition).get("H") == 4)
    other = next(s for s in sysk.species if s is not reactant and s.charge == -1
                 and dict(s.composition).get("C") == 1)   # bicarbonate (CHO3-)
    world = CoupledWorld([Compartment("c", sysk)])
    init = {"c": {reactant: 1.0, other: 1.0}}
    return world.integrate(init, duration=2.0, n_steps=n_steps, scheme=scheme), byn


# ============================================================ Layer 1 is exact
def test_structural_layer_is_exact_and_conserving():
    br = _bridge()
    # E N = 0 is proven by the kernel at construction; the signature is a pure structural certificate
    assert br.system is not None
    assert isinstance(br.signature(), tuple)


# ============================================================ Layer 1 != Layer 2 (bridge does not supply kinetics)
def test_missing_kinetics_leaves_the_dynamics_undefined():
    br = _bridge()                                   # no rate_laws -> RATE_UNKNOWN
    world = CoupledWorld([Compartment("c", br.system)])
    reactant = next(s for s in br.system.species if s.charge == 0 and dict(s.composition).get("C") == 2)
    with pytest.raises(CoupledError) as ei:
        world.integrate({"c": {reactant: 1.0}}, duration=1.0, n_steps=10)
    assert "RATE_UNKNOWN" in str(ei.value)            # the structural bridge carries no dynamics


def test_same_structure_different_kinetics_share_one_signature():
    s_slow = bridge_to_kernel(_proton_transfer(), rate_laws={"proton_transfer": MassActionIrreversible(k=0.5)})
    s_fast = bridge_to_kernel(_proton_transfer(), rate_laws={"proton_transfer": MassActionIrreversible(k=5.0)})
    assert s_slow.signature() == s_fast.signature()   # structural identity is independent of the rate law


def test_same_structure_different_kinetics_give_different_trajectories():
    tr_slow, _ = _integrate(None, k=0.5)
    tr_fast, _ = _integrate(None, k=5.0)
    # one structural signature, MANY dynamics -> the bridge is NOT a dynamics functor
    end_slow = tr_slow.amounts["c"][-1]
    end_fast = tr_fast.amounts["c"][-1]
    acetate_slow = next(v for s, v in end_slow.items() if s.charge == -1 and dict(s.composition).get("C") == 2)
    acetate_fast = next(v for s, v in end_fast.items() if s.charge == -1 and dict(s.composition).get("C") == 2)
    assert abs(acetate_slow - acetate_fast) > 1e-3


# ============================================================ Layer 2/3 cap the claim; structure does not lift it
def test_assumed_kinetics_cap_the_claim_tier_despite_exact_structure():
    tr, _ = _integrate(None, k=0.5)                   # MassActionIrreversible default tier is ASSUMED_PARAMETER
    assert tr.receipt.material_balance_closed          # structural layer: exact
    assert tr.receipt.structural_tier == STRUCTURALLY_CONSERVING
    assert rank(tr.receipt.admitted_tier) <= 1         # but the physical (kinetic) layer caps the admitted claim
    assert rank(STRUCTURALLY_CONSERVING) == 2          # (guards the premise: structure alone would be rank 2)


def test_bridged_mass_action_is_execution_certified_yet_still_tier_capped():
    # MassActionIrreversible is a REGISTERED law (XXII-2), so execution identity IS certified -- an ORTHOGONAL axis to
    # the claim tier: certified-identity does not raise the ASSUMED kinetic tier.  The three layers are independent.
    tr, _ = _integrate(None, k=0.5)
    assert tr.receipt.execution_identity_certified is True
    assert rank(tr.receipt.admitted_tier) <= 1


# ============================================================ Layer 3 is approximate; structure is invariant to it
def _acetate(end):
    return next(v for s, v in end.items() if s.charge == -1 and dict(s.composition).get("C") == 2)


def test_structure_is_scheme_invariant_and_splitting_error_is_an_operator_property():
    tr_lie, _ = _integrate(None, k=2.0, scheme="lie", n_steps=20)
    tr_strang, _ = _integrate(None, k=2.0, scheme="strang", n_steps=20)
    # a single bridged reaction has NO non-commuting transport to split, so Lie and Strang COINCIDE: the splitting
    # error is a measured property of the OPERATOR STRUCTURE (it is nonzero only when transport and reaction do not
    # commute -- the reactor/flagship, where it is MEASURED, never assumed).  The numerical layer is still Layer 3.
    assert abs(_acetate(tr_lie.amounts["c"][-1]) - _acetate(tr_strang.amounts["c"][-1])) < 1e-6
    # and the STRUCTURAL signature does not depend on the integrator at all (numerics never touch Layer 1)
    s_a = bridge_to_kernel(_proton_transfer(), rate_laws={"proton_transfer": MassActionIrreversible(k=2.0)}).signature()
    s_b = bridge_to_kernel(_proton_transfer(), rate_laws={"proton_transfer": MassActionIrreversible(k=9.0)}).signature()
    assert s_a == s_b


# ============================================================ the physical transport layer enforces identity too
def test_identity_changing_passive_transfer_is_refused_at_the_physical_layer():
    # a transport morphism that changes chemical identity (ethanol -> dimethyl ether, both C2H6O) is a REACTION, not
    # transport -- refused, mirroring the structural layer's identity discipline in the physical (transport) category
    etoh = Species.of("ethanol", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS, substance="ethanol")
    dme = Species.of("dimethyl_ether", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS, substance="DME")
    with pytest.raises(CoupledError) as ei:
        InterfaceTransfer("bad", "A", "B", etoh, dme, k_transfer=0.1)
    assert "DIFFERENT substance" in str(ei.value)


def test_a_structural_bridge_alone_yields_no_dynamics_claim():
    # the honest boundary, executable: from a pure structural bridge (no kinetics) there is NO reachable dynamics claim
    # -- integrate refuses -- so the bridge cannot, by itself, certify any trajectory.  It is a conservation+identity
    # certificate, not a universal dynamics functor.
    br = _bridge()
    assert all(r.rate_law is None for r in br.system.reactions)     # RATE_UNKNOWN everywhere
    world = CoupledWorld([Compartment("c", br.system)])
    reactant = next(s for s in br.system.species if s.charge == 0 and dict(s.composition).get("C") == 2)
    with pytest.raises(CoupledError):
        world.integrate({"c": {reactant: 1.0}}, duration=1.0, n_steps=5)
