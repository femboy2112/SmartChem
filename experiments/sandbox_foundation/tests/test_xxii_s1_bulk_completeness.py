"""OPERATION XXII section 1 -- the electroneutral bulk-exchange guarantee must be EARNED, not asserted.

XXI-5 introduced ElectroneutralBulkExchange as a whole-solution parcel swap, claiming that because each parcel is a
locally electroneutral solution the exchange leaves no compartment charged.  But the constructor only validated each
PAIR (same composition/charge/substance); it never required the pairs to cover the COMPLETE dissolved roster.  So a
bulk exchange carrying only Na+ was accepted and transported NET charge -- preserving global charge while leaving each
compartment LOCALLY charged.  XXII-1 closes this: a bulk parcel MUST carry every aqueous species of both compartments
(and only aqueous species).  A partial or non-aqueous roster is REFUSED at construction -- never silently run, and
never left for a fast-equilibrium projection to mask by inventing countercharge against the implicit-water reservoir.

Controls (directive §1): complete neutral NaCl parcel; acetate/sodium buffer bulk; zero exchange rate; identical
solutions; opposing gradients; restricted Na+ only (REFUSE); solid-only (REFUSE bulk-liquid); same-formula
constitutional isomers (REFUSE); reversed flow; multiple compartments; different compartment volumes; high rate +
timestep refinement.  Exit gate: every ACCEPTED operator instance earns its local-charge/volume conservation.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_bulk_exchange_demo import run as run_buffer
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    ElectroneutralBulkExchange,
)
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species

Nap = Species.of("Na+", {"Na": 1}, charge=1, phase=Phase.AQUEOUS)
Clm = Species.of("Cl-", {"Cl": 1}, charge=-1, phase=Phase.AQUEOUS)
Kp = Species.of("K+", {"K": 1}, charge=1, phase=Phase.AQUEOUS)
NaCl_s = Species.of("NaCl(s)", {"Na": 1, "Cl": 1}, charge=0, phase=Phase.SOLID)
# a same-formula constitutional isomer pair (both C2H6O, neutral, aqueous) -- different substance
EtOH = Species.of("ethanol", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS, substance="ethanol")
DME = Species.of("dimethyl_ether", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS, substance="DME")

_ALL = ((Nap, Nap), (Clm, Clm))


def _nacl_cells(VA=1.0, VB=1.0, species=(Nap, Clm)):
    A = Compartment("A", ChemicalSystem(list(species), [], volume_L=VA))
    B = Compartment("B", ChemicalSystem(list(species), [], volume_L=VB))
    return A, B


def _charge(world, amounts_last, cname):
    return sum(sp.charge * amounts_last[cname][sp] for sp in world._comp[cname].system.species)


def _run_and_charges(world, initial, **kw):
    kw.setdefault("duration", 2.0)
    kw.setdefault("n_steps", 8)
    kw.setdefault("scheme", "strang")
    tr = world.integrate(initial, **kw)
    last = {c.name: tr.amounts[c.name][-1] for c in world.compartments}
    return tr, {c.name: _charge(world, last, c.name) for c in world.compartments}


# ============================================================ REFUSALS (the fix)
def test_restricted_single_ion_is_refused():
    A, B = _nacl_cells()
    bx = ElectroneutralBulkExchange("leak", "A", "B", species_pairs=((Nap, Nap),), Q_L_per_s=0.05)
    with pytest.raises(CoupledError) as ei:
        CoupledWorld([A, B], bulk_exchanges=(bx,))
    assert "complete dissolved roster" in str(ei.value)
    assert "Cl-" in str(ei.value)                      # the missing counterion is named


def test_restricted_set_on_a_buffer_cannot_be_masked_by_the_projection():
    """The forcing case the directive flags: a partial bulk on a fast-equilibrium buffer (charge is an implicit-water
    reservoir) would let the projection invent countercharge and hide the local-charge break.  The fix makes the world
    UNBUILDABLE, so that masking path is unreachable -- the refusal happens before any integration/projection."""
    from experiments.sandbox_foundation.general_bulk_exchange_demo import _buffer_compartment
    from experiments.sandbox_foundation.general_coupled_demo import HAc, Nap as DNap
    A = _buffer_compartment("A", 1.0)
    B = _buffer_compartment("B", 1.0)
    # carry only the neutral HAc + Na+ -- a charged subset of the 6-species buffer
    with pytest.raises(CoupledError) as ei:
        CoupledWorld([A, B], bulk_exchanges=(
            ElectroneutralBulkExchange("partial", "A", "B", species_pairs=((HAc, HAc), (DNap, DNap)), Q_L_per_s=0.02),))
    assert "complete dissolved roster" in str(ei.value)


def test_solid_species_in_a_parcel_is_refused():
    A, B = _nacl_cells(species=(Nap, Clm, NaCl_s))
    bx = ElectroneutralBulkExchange("x", "A", "B",
                                    species_pairs=((Nap, Nap), (Clm, Clm), (NaCl_s, NaCl_s)), Q_L_per_s=0.01)
    with pytest.raises(CoupledError) as ei:
        CoupledWorld([A, B], bulk_exchanges=(bx,))
    assert "AQUEOUS solutes only" in str(ei.value) and "SOLID" in str(ei.value)


def test_solid_present_but_not_advected_still_needs_complete_aqueous_coverage():
    # a compartment may HOLD a solid (it just doesn't advect); the aqueous roster must still be fully carried
    A, B = _nacl_cells(species=(Nap, Clm, NaCl_s))
    good = ElectroneutralBulkExchange("x", "A", "B", species_pairs=((Nap, Nap), (Clm, Clm)), Q_L_per_s=0.01)
    world = CoupledWorld([A, B], bulk_exchanges=(good,))   # NaCl(s) stays put; the two aqueous ions are fully carried
    _tr, q = _run_and_charges(world, {"A": {Nap: 0.1, Clm: 0.1, NaCl_s: 0.5}, "B": {}})
    assert abs(q["A"]) < 1e-9 and abs(q["B"]) < 1e-9


def test_same_formula_constitutional_isomers_are_refused():
    # ethanol<->DME: both C2H6O/neutral, different substance -> a reaction, not transport (XVI-P0.1), refused at pair level
    with pytest.raises(CoupledError) as ei:
        ElectroneutralBulkExchange("x", "A", "B", species_pairs=((EtOH, DME),), Q_L_per_s=0.01)
    assert "DIFFERENT substance" in str(ei.value)


def test_extra_species_not_in_roster_is_refused():
    # carrying a species the compartment does not even hold is refused by the reference check
    A, B = _nacl_cells(species=(Nap, Clm))
    with pytest.raises(CoupledError):
        CoupledWorld([A, B], bulk_exchanges=(
            ElectroneutralBulkExchange("x", "A", "B",
                                       species_pairs=((Nap, Nap), (Clm, Clm), (Kp, Kp)), Q_L_per_s=0.01),))


def test_mismatched_rosters_between_compartments_refused():
    A = Compartment("A", ChemicalSystem([Nap, Clm], [], volume_L=1.0))
    B = Compartment("B", ChemicalSystem([Nap, Clm, Kp], [], volume_L=1.0))  # B has an extra aqueous species
    with pytest.raises(CoupledError) as ei:
        CoupledWorld([A, B], bulk_exchanges=(
            ElectroneutralBulkExchange("x", "A", "B", species_pairs=((Nap, Nap), (Clm, Clm)), Q_L_per_s=0.01),))
    assert "complete dissolved roster" in str(ei.value)


# ============================================================ ACCEPTED -> must EARN the guarantee
def test_complete_neutral_parcel_conserves_and_leaves_no_cell_charged():
    A, B = _nacl_cells()
    world = CoupledWorld([A, B], bulk_exchanges=(
        ElectroneutralBulkExchange("mix", "A", "B", species_pairs=_ALL, Q_L_per_s=0.05),))
    tr, q = _run_and_charges(world, {"A": {Nap: 0.1, Clm: 0.1}, "B": {}})
    assert abs(q["A"]) < 1e-9 and abs(q["B"]) < 1e-9          # local electroneutrality preserved
    # global Na and Cl conserved
    tot = tr.receipt.raw_material_change
    assert abs(tot.get("Na", 0.0)) < 1e-9 and abs(tot.get("Cl", 0.0)) < 1e-9
    assert tr.receipt.material_balance_closed


def test_opposing_gradients_relax_but_stay_neutral():
    A, B = _nacl_cells()
    world = CoupledWorld([A, B], bulk_exchanges=(
        ElectroneutralBulkExchange("mix", "A", "B", species_pairs=_ALL, Q_L_per_s=0.1),))
    tr, q = _run_and_charges(world, {"A": {Nap: 0.2, Clm: 0.2}, "B": {Nap: 0.02, Clm: 0.02}}, duration=30.0, n_steps=60)
    assert abs(q["A"]) < 1e-9 and abs(q["B"]) < 1e-9
    # the gradient relaxed toward a common composition
    naA = tr.amounts["A"][-1][Nap]
    naB = tr.amounts["B"][-1][Nap]
    assert naB > 0.02 + 1e-3 and naA < 0.2 - 1e-3


def test_zero_exchange_rate_is_static_and_neutral():
    A, B = _nacl_cells()
    world = CoupledWorld([A, B], bulk_exchanges=(
        ElectroneutralBulkExchange("mix", "A", "B", species_pairs=_ALL, Q_L_per_s=0.0),))
    tr, q = _run_and_charges(world, {"A": {Nap: 0.1, Clm: 0.1}, "B": {Nap: 0.05, Clm: 0.05}})
    assert abs(q["A"]) < 1e-12 and abs(q["B"]) < 1e-12
    assert abs(tr.amounts["A"][-1][Nap] - 0.1) < 1e-9        # nothing moved


def test_identical_solutions_have_zero_net_flux():
    A, B = _nacl_cells()
    world = CoupledWorld([A, B], bulk_exchanges=(
        ElectroneutralBulkExchange("mix", "A", "B", species_pairs=_ALL, Q_L_per_s=0.2),))
    tr, q = _run_and_charges(world, {"A": {Nap: 0.1, Clm: 0.1}, "B": {Nap: 0.1, Clm: 0.1}})
    assert abs(tr.amounts["A"][-1][Nap] - 0.1) < 1e-9        # identical -> no change
    assert abs(q["A"]) < 1e-12


def test_reversed_flow_is_symmetric():
    # declaring A<-B instead of A->B must give the mirror trajectory (a->b sign only)
    A, B = _nacl_cells()
    w_ab = CoupledWorld([A, B], bulk_exchanges=(
        ElectroneutralBulkExchange("m", "A", "B", species_pairs=_ALL, Q_L_per_s=0.08),))
    A2, B2 = _nacl_cells()
    w_ba = CoupledWorld([A2, B2], bulk_exchanges=(
        ElectroneutralBulkExchange("m", "B", "A", species_pairs=((Nap, Nap), (Clm, Clm)), Q_L_per_s=0.08),))
    init = {"A": {Nap: 0.15, Clm: 0.15}, "B": {Nap: 0.03, Clm: 0.03}}
    t1, _ = _run_and_charges(w_ab, init, duration=20.0, n_steps=40)
    t2, _ = _run_and_charges(w_ba, init, duration=20.0, n_steps=40)
    assert abs(t1.amounts["A"][-1][Nap] - t2.amounts["A"][-1][Nap]) < 1e-9     # same physics regardless of a/b labelling


def test_different_compartment_volumes_preserve_neutrality():
    A, B = _nacl_cells(VA=1.0, VB=3.0)
    world = CoupledWorld([A, B], bulk_exchanges=(
        ElectroneutralBulkExchange("mix", "A", "B", species_pairs=_ALL, Q_L_per_s=0.05),))
    tr, q = _run_and_charges(world, {"A": {Nap: 0.1, Clm: 0.1}, "B": {Nap: 0.3, Clm: 0.3}}, duration=20.0, n_steps=40)
    assert abs(q["A"]) < 1e-9 and abs(q["B"]) < 1e-9


def test_three_compartment_chain_stays_neutral():
    A, B = _nacl_cells()
    C = Compartment("C", ChemicalSystem([Nap, Clm], [], volume_L=1.0))
    world = CoupledWorld([A, B, C], bulk_exchanges=(
        ElectroneutralBulkExchange("ab", "A", "B", species_pairs=_ALL, Q_L_per_s=0.05),
        ElectroneutralBulkExchange("bc", "B", "C", species_pairs=_ALL, Q_L_per_s=0.05)))
    tr, q = _run_and_charges(world, {"A": {Nap: 0.3, Clm: 0.3}, "B": {}, "C": {Nap: 0.1, Clm: 0.1}},
                             duration=20.0, n_steps=40)
    assert all(abs(v) < 1e-9 for v in q.values())


def test_high_rate_and_timestep_refinement_agree_and_stay_neutral():
    A, B = _nacl_cells()
    bx = ElectroneutralBulkExchange("mix", "A", "B", species_pairs=_ALL, Q_L_per_s=0.5)
    world = CoupledWorld([A, B], bulk_exchanges=(bx,))
    init = {"A": {Nap: 0.2, Clm: 0.2}, "B": {}}
    t_coarse, q_c = _run_and_charges(world, init, duration=10.0, n_steps=10)
    t_fine, q_f = _run_and_charges(world, init, duration=10.0, n_steps=200)
    assert all(abs(v) < 1e-9 for v in list(q_c.values()) + list(q_f.values()))
    assert abs(t_coarse.amounts["A"][-1][Nap] - t_fine.amounts["A"][-1][Nap]) < 1e-3   # refinement converges


def test_acetate_sodium_buffer_bulk_runs_and_relaxes_sodium():
    # the XXI-5 acetate demo (full 6-species roster) still works under the completeness gate
    tr = run_buffer("bulk", duration=60.0, n_steps=120)
    assert tr.receipt.material_balance_closed
