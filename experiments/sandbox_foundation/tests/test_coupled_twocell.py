"""OPERATION XIII P3 -- the two-cell reactive vinegar/bicarbonate world (section 5 scenario list).

Load-bearing pins:
  * acid-rich beside bicarbonate-rich: neutral HAc and CO2(aq) cross down their gradients, pH trajectories separate,
    and global acetate/carbon/sodium are invariant under internal transport (every face cancels in the ledger);
  * a diffusive membrane moves ONLY the neutral carriers -- sodium NEVER crosses it (Nernst-Planck obstruction);
  * bulk mixing swaps balanced parcels: all components (incl. sodium) move, charge is preserved, compositions
    converge, and conservation holds;
  * valve closed = null; valve scales the flux; a donor never loses more than it owns; dt refinement converges.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation import claim_tiers
from experiments.sandbox_foundation.coupled_twocell import (
    CoupledCell,
    CoupledTwoCellError,
    CoupledWorld,
    DiffusiveMembrane,
    simulate_diffusive,
    step_diffusive,
    step_mixing,
)


def _acid_vs_bicarb(vA=0.1, vB=0.1):
    A = CoupledCell(volume_L=vA, n_acetate_mol=0.2 * vA, n_carbon_mol=0.0, n_sodium_mol=0.0, activity_model="ideal")
    B = CoupledCell(volume_L=vB, n_acetate_mol=0.0, n_carbon_mol=0.2 * vB, n_sodium_mol=0.2 * vB, activity_model="ideal")
    return CoupledWorld(cellA=A, cellB=B)


_MEM = DiffusiveMembrane(g_HAc_L_per_s=0.01, g_CO2_L_per_s=0.01, valve=1.0)


def test_diffusion_conserves_globally_and_separates_pH():
    w = _acid_vs_bicarb()
    g0 = w.global_totals()
    pHA0, pHB0 = w.cellA.speciate().pH, w.cellB.speciate().pH
    w2 = simulate_diffusive(w, _MEM, duration_s=20.0, dt=0.5)
    g1 = w2.global_totals()
    for k in g0:
        assert abs(g1[k] - g0[k]) < 1e-12, (k, g0[k], g1[k])
    assert w2.cellA.speciate().pH > pHA0      # acid cell loses HAc -> pH rises
    assert w2.cellB.speciate().pH < pHB0      # bicarb cell gains acid -> pH falls
    assert max(w2.ledger[-1].charge_residual_M) < 1e-9


def test_diffusive_membrane_never_moves_sodium():
    w = _acid_vs_bicarb()
    w2 = simulate_diffusive(w, _MEM, duration_s=50.0, dt=0.5)
    assert abs(w2.cellA.n_sodium_mol - 0.0) < 1e-15
    assert abs(w2.cellB.n_sodium_mol - 0.2 * 0.1) < 1e-12
    # acetate crossed A->B, carbon crossed B->A
    assert w2.cellB.n_acetate_mol > 0 and w2.cellA.n_carbon_mol > 0


def test_valve_closed_is_a_null_step():
    w = _acid_vs_bicarb()
    closed = DiffusiveMembrane(g_HAc_L_per_s=0.01, g_CO2_L_per_s=0.01, valve=0.0)
    w2 = step_diffusive(w, closed, 10.0)
    assert abs(w2.cellA.n_acetate_mol - w.cellA.n_acetate_mol) < 1e-15
    assert abs(w2.cellA.n_carbon_mol - w.cellA.n_carbon_mol) < 1e-15


def test_valve_scales_the_transfer():
    w = _acid_vs_bicarb()
    half = step_diffusive(w, DiffusiveMembrane(0.01, 0.01, valve=0.5), 1.0).cellB.n_acetate_mol
    full = step_diffusive(w, DiffusiveMembrane(0.01, 0.01, valve=1.0), 1.0).cellB.n_acetate_mol
    assert full > half > 0


def test_different_volumes_and_concentrations_still_conserve():
    w = _acid_vs_bicarb(vA=0.05, vB=0.2)
    g0 = w.global_totals()
    w2 = simulate_diffusive(w, _MEM, duration_s=10.0, dt=0.25)
    for k in g0:
        assert abs(w2.global_totals()[k] - g0[k]) < 1e-12


def test_reversed_gradient_reverses_the_flux():
    w = _acid_vs_bicarb()
    rev = CoupledWorld(cellA=w.cellB, cellB=w.cellA)   # bicarb now in A, acid in B
    w2 = step_diffusive(rev, _MEM, 5.0)
    assert w2.cellA.n_acetate_mol > 0        # acetate now flows B->A


def test_a_donor_never_loses_more_than_it_owns():
    # a huge permeability over a long dt must substep, never drive a total negative.
    w = _acid_vs_bicarb()
    hot = DiffusiveMembrane(g_HAc_L_per_s=10.0, g_CO2_L_per_s=10.0, valve=1.0)
    w2 = step_diffusive(w, hot, 100.0)
    assert w2.cellA.n_acetate_mol >= -1e-15
    assert w2.cellB.n_carbon_mol >= -1e-15
    for k, v in w2.ledger[-1].global_residual_mol.items():
        assert v < 1e-12, (k, v)


def test_bulk_mixing_conserves_moves_sodium_and_converges():
    w = _acid_vs_bicarb()
    g0 = w.global_totals()
    wm = w
    for _ in range(300):
        wm = step_mixing(wm, exchange_rate_L_per_s=0.001, dt=1.0, valve=1.0)
    for k in g0:
        assert abs(wm.global_totals()[k] - g0[k]) < 1e-11
    # unlike diffusion, mixing carries sodium (balanced parcels) and converges compositions toward a common value.
    assert abs(wm.cellA.Na - wm.cellB.Na) < 0.03
    assert abs(wm.cellA.C_Ac - wm.cellB.C_Ac) < 0.05
    assert max(wm.ledger[-1].charge_residual_M) < 1e-9


def test_different_mixing_timescales():
    w = _acid_vs_bicarb()
    slow = step_mixing(w, exchange_rate_L_per_s=0.0001, dt=1.0).cellA.n_sodium_mol
    fast = step_mixing(w, exchange_rate_L_per_s=0.01, dt=1.0).cellA.n_sodium_mol
    # A starts with zero sodium; a faster exchange brings more sodium into A in one step.
    assert fast > slow >= 0


def test_dt_refinement_converges():
    w = _acid_vs_bicarb()
    ends = [simulate_diffusive(w, _MEM, duration_s=20.0, dt=dt).cellB.n_acetate_mol for dt in (2.0, 1.0, 0.5, 0.25)]
    diffs = [abs(ends[i + 1] - ends[i]) for i in range(3)]
    assert diffs[0] > diffs[1] > diffs[2]


def test_claim_tier_is_assumed_parameter_for_prescribed_transport():
    w = _acid_vs_bicarb()
    w2 = step_diffusive(w, _MEM, 1.0)
    assert w2.ledger[-1].claim_tier == claim_tiers.ASSUMED_PARAMETER


def test_input_validation():
    with pytest.raises(CoupledTwoCellError):
        CoupledCell(volume_L=0.0, n_acetate_mol=0.1, n_carbon_mol=0.0, n_sodium_mol=0.0)
    with pytest.raises(CoupledTwoCellError):
        CoupledCell(volume_L=0.1, n_acetate_mol=-0.1, n_carbon_mol=0.0, n_sodium_mol=0.0)
    with pytest.raises(CoupledTwoCellError):
        DiffusiveMembrane(g_HAc_L_per_s=-1.0)
    with pytest.raises(CoupledTwoCellError):
        DiffusiveMembrane(valve=1.5)
    with pytest.raises(CoupledTwoCellError):
        step_diffusive(_acid_vs_bicarb(), _MEM, -1.0)
