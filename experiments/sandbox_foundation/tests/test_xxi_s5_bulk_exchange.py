"""OPERATION XXI section 5 -- ElectroneutralBulkExchange: a real bulk-liquid mixing operator, distinct from a
selective membrane, on the ONE generic integrator.

The headline physics (test_three_modes_...): a selective membrane (InterfaceTransfer of neutral HAc) leaves the SODIUM
gradient untouched -- ions cannot cross -- while a bulk exchange relaxes it -- the whole electroneutral solution moves.
A closed interface moves nothing.  Every mode conserves C and Na globally and leaves each compartment electroneutral.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_bulk_exchange_demo import (
    _ACETATE_SPECIES,
    _FULL_SOLUTION_PAIRS,
    build_two_buffer_world,
    run,
)
from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    ElectroneutralBulkExchange,
)
from experiments.sandbox_foundation.general_coupled_demo import Acm, HAc, Hp, NaAc, Nap, OHm
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species


def _amt(traj, comp, species):
    return traj.amounts[comp][-1][species]


def _net_charge(traj, comp):
    return sum(sp.charge * traj.amounts[comp][-1][sp] for sp in _ACETATE_SPECIES)


def _total(traj, comp, element):
    return sum(sp.count(element) * traj.amounts[comp][-1][sp] for sp in _ACETATE_SPECIES)


# ------------------------------------------------------------- the headline: membrane vs bulk vs closed
def test_three_modes_are_physically_distinguishable():
    closed = run("closed")
    membrane = run("membrane")
    bulk = run("bulk")

    # closed: nothing moves -- the sodium gradient is exactly the initial 0.08 / 0.04
    assert _amt(closed, "A", Nap) == pytest.approx(0.08) and _amt(closed, "B", Nap) == pytest.approx(0.04)

    # selective membrane (neutral HAc only): the IONS cannot cross, so the Na+ gradient is UNCHANGED ...
    assert _amt(membrane, "A", Nap) == pytest.approx(0.08) and _amt(membrane, "B", Nap) == pytest.approx(0.04)

    # ... but the BULK exchange carries the whole solution, so the Na+ gradient RELAXES toward the well-mixed mean (0.06)
    na_a, na_b = _amt(bulk, "A", Nap), _amt(bulk, "B", Nap)
    assert na_a < 0.08 and na_b > 0.04                       # moved toward each other
    assert abs(na_a - 0.06) < abs(0.08 - 0.06)               # A's Na+ moved toward the 0.06 mean
    # the regimes are genuinely different trajectories
    assert abs(na_a - _amt(membrane, "A", Nap)) > 1e-3


def test_Q_zero_recovers_the_closed_case():
    closed = run("closed")
    zeroQ = run("bulk", Q=0.0)
    for comp in ("A", "B"):
        for sp in _ACETATE_SPECIES:
            assert _amt(zeroQ, comp, sp) == pytest.approx(_amt(closed, comp, sp), abs=1e-12)


# ------------------------------------------------------------- conservation + electroneutrality
def test_bulk_exchange_conserves_C_and_Na_globally():
    tr = run("bulk")
    assert tr.receipt.material_balance_closed is True
    assert tr.tier == "STRUCTURALLY_CONSERVING"
    # global totals equal the initial (A: C=2*0.20, Na=0.08 ; B: C=2*0.05, Na=0.04) within the per-component tol
    tot_C = _total(tr, "A", "C") + _total(tr, "B", "C")
    tot_Na = _total(tr, "A", "Na") + _total(tr, "B", "Na")
    assert tot_C == pytest.approx(2 * 0.20 + 2 * 0.05, rel=1e-6)
    assert tot_Na == pytest.approx(0.08 + 0.04, rel=1e-6)


def test_each_compartment_stays_electroneutral_under_bulk_exchange():
    tr = run("bulk")
    # moving the WHOLE solution (not selected ions) cannot leave a compartment charged
    assert abs(_net_charge(tr, "A")) < 1e-9
    assert abs(_net_charge(tr, "B")) < 1e-9


def test_identical_compositions_exchange_nothing():
    same = {"A": {HAc: 0.1, Nap: 0.05}, "B": {HAc: 0.1, Nap: 0.05}}
    tr = run("bulk", initial=same)
    for sp in _ACETATE_SPECIES:
        assert _amt(tr, "A", sp) == pytest.approx(_amt(tr, "B", sp), abs=1e-10)  # no gradient -> no net flux


def test_fast_exchange_approaches_the_well_mixed_limit():
    # a large Q over the run drives Na+ in A and B to the common volume-weighted mean (0.06 at equal volumes)
    tr = run("bulk", Q=1.0, duration=120.0, n_steps=240)
    assert _amt(tr, "A", Nap) == pytest.approx(0.06, abs=2e-3)
    assert _amt(tr, "B", Nap) == pytest.approx(0.06, abs=2e-3)


# ------------------------------------------------------------- the certificate binds the operator
def test_certificate_binds_Q_and_the_advected_set():
    w_slow, _ = build_two_buffer_world("bulk", Q=0.02)
    w_fast, _ = build_two_buffer_world("bulk", Q=0.04)
    w_closed, _ = build_two_buffer_world("closed")
    assert w_slow._world_certificate != w_fast._world_certificate      # Q is bound
    assert w_slow._world_certificate != w_closed._world_certificate    # the operator's presence is bound


def test_rendering_cadence_does_not_change_the_endpoint():
    dense = run("bulk", n_samples=None)
    sparse = run("bulk", n_samples=5)
    for comp in ("A", "B"):
        for sp in _ACETATE_SPECIES:
            assert _amt(dense, comp, sp) == pytest.approx(_amt(sparse, comp, sp), abs=1e-12)
    assert dense.receipt.material_balance_closed == sparse.receipt.material_balance_closed


# ------------------------------------------------------------- construction-time validation (fail closed)
def test_validation_rejects_malformed_operators():
    sysA = ChemicalSystem(list(_ACETATE_SPECIES), [], volume_L=1.0)
    sysB = ChemicalSystem(list(_ACETATE_SPECIES), [], volume_L=1.0)
    A, B = Compartment("A", sysA), Compartment("B", sysB)

    with pytest.raises(CoupledError):   # self-loop
        ElectroneutralBulkExchange("x", "A", "A", species_pairs=((HAc, HAc),), Q_L_per_s=0.01)
    with pytest.raises(CoupledError):   # negative Q
        ElectroneutralBulkExchange("x", "A", "B", species_pairs=((HAc, HAc),), Q_L_per_s=-0.01)

    # different-substance pair: a transfer that would transmute one compound into another is a reaction, not transport
    dme = Species.of("DME", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS)
    etoh = Species.of("EtOH", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS)
    with pytest.raises(CoupledError):
        ElectroneutralBulkExchange("x", "A", "B", species_pairs=((dme, etoh),), Q_L_per_s=0.01)

    # unknown compartment / absent species are refused at world construction
    with pytest.raises(CoupledError):
        CoupledWorld([A, B], bulk_exchanges=[
            ElectroneutralBulkExchange("x", "A", "C", species_pairs=((HAc, HAc),), Q_L_per_s=0.01)])
    absent = Species.of("ZZ", {"C": 1}, charge=0, phase=Phase.AQUEOUS)
    with pytest.raises(CoupledError):
        CoupledWorld([A, B], bulk_exchanges=[
            ElectroneutralBulkExchange("x", "A", "B", species_pairs=((absent, absent),), Q_L_per_s=0.01)])


def test_full_solution_pairs_covers_every_dissolved_species():
    # the demo's bulk operator advects the WHOLE dissolved set -- that is what makes it electroneutral bulk transport
    assert {sa for sa, _ in _FULL_SOLUTION_PAIRS} == set(_ACETATE_SPECIES)
    assert all(sa is sb for sa, sb in _FULL_SOLUTION_PAIRS)       # same shared Species object both sides
    assert set(_ACETATE_SPECIES) == {HAc, Acm, Hp, OHm, Nap, NaAc}
