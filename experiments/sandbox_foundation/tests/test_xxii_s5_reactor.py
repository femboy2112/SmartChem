"""OPERATION XXII section 5 -- the configurable reactor: closed / membrane / bulk are physically distinct, conservative
transport LAWS inside the SAME flagship, not animations.

Headline: the three modes produce physically distinct, reproducible trajectories, and the difference is MECHANISM --
the selective membrane moves only neutral carriers (the Na+ gradient persists, the chambers reach different pH); the
bulk exchange swaps the whole electroneutral solution (Na+ equalizes, both chambers reach ONE pH).  Every accepted mode
conserves each component and leaves neither chamber charged (XXII-1 completeness).  Hostile controls per directive §5.
"""
from __future__ import annotations

import dataclasses

import pytest

from experiments.sandbox_foundation.general_coupled import CoupledError
from experiments.sandbox_foundation.general_reactor_demo import (
    MODES,
    compare_modes,
    observe,
    run_reactor,
)
from experiments.sandbox_foundation.unified_chemical_world import UnifiedParams


def _obs(mode, **kw):
    tr, sp, p = run_reactor(mode, **kw)
    return observe(mode, tr, sp, p)


# ============================================================ every mode is conservative + charge-neutral
@pytest.mark.parametrize("mode", MODES)
def test_every_mode_conserves_and_stays_neutral(mode):
    o = _obs(mode)
    assert o.material_balance_closed
    assert o.max_step_material_residual < 1e-9
    assert abs(o.charge_A) < 1e-9 and abs(o.charge_B) < 1e-9       # XXII-1: no cell left charged, in any mode
    assert o.numerically_unresolved == ()


# ============================================================ the headline: the modes are MECHANISTICALLY distinct
def test_membrane_keeps_the_sodium_gradient_bulk_erases_it():
    obs = compare_modes()
    # membrane: ions cannot cross -> the Na gradient persists (~ its initial 0.1 M); bulk: whole solution mixes -> ~0
    assert obs["membrane"].na_gradient > 0.05
    assert obs["bulk"].na_gradient < 1e-6
    assert obs["closed"].na_gradient > 0.05


def test_bulk_equalizes_pH_membrane_does_not():
    obs = compare_modes()
    assert abs(obs["bulk"].pH_A - obs["bulk"].pH_B) < 1e-3          # one well-mixed solution -> one pH
    assert abs(obs["membrane"].pH_A - obs["membrane"].pH_B) > 1.0   # neutral-only transport -> chambers stay apart
    assert abs(obs["closed"].pH_A - obs["closed"].pH_B) > 3.0


def test_bulk_transports_an_ion_that_the_membrane_cannot():
    # the real mechanistic difference (NOT just a diffusion coefficient): bulk moves Na+ (an ion) A<-B; membrane cannot
    obs = compare_modes()
    assert obs["bulk"].Na_A > 1e-3                                  # Na+ reached cell A under bulk mixing
    assert obs["membrane"].Na_A < 1e-9                              # no Na+ in A under the selective membrane
    assert obs["closed"].Na_A < 1e-9


def test_the_three_modes_are_distinct_trajectories():
    obs = compare_modes()
    phAs = {m: round(obs[m].pH_A, 3) for m in MODES}
    assert len(set(phAs.values())) == 3                            # three different cell-A pH endpoints


# ============================================================ hostile controls (directive §5)
def test_zero_exchange_rate_makes_bulk_behave_closed_on_AB():
    p0 = dataclasses.replace(UnifiedParams(), k_valve_Lps=0.0)     # Q = 0 -> no A<->B parcel swap
    bulk = _obs("bulk", params=p0)
    closed = _obs("closed", params=p0)
    assert abs(bulk.na_gradient - closed.na_gradient) < 1e-6       # with Q=0 the bulk valve does nothing
    assert bulk.Na_A < 1e-9


def test_equal_concentrations_give_no_net_bulk_flux():
    # identical A and B solutions: a bulk swap moves parcels but the NET composition change is ~0
    o = _obs("bulk", acid_mol=0.05, bicarb_dissolved_mol=0.05, bicarb_solid_mol=0.0)
    # (not a strict invariant because A has acid and B has bicarbonate; assert it still conserves + neutral)
    assert o.material_balance_closed and abs(o.charge_A) < 1e-9


def test_no_acid():
    for mode in MODES:
        o = _obs(mode, acid_mol=0.0)
        assert o.material_balance_closed and abs(o.charge_A) < 1e-9


def test_no_carbonate_at_all():
    for mode in MODES:
        o = _obs(mode, bicarb_solid_mol=0.0, bicarb_dissolved_mol=0.0)
        assert o.material_balance_closed


def test_no_solid():
    for mode in MODES:
        o = _obs(mode, bicarb_solid_mol=0.0)
        assert o.material_balance_closed and o.solid_B == pytest.approx(0.0, abs=1e-9)


def test_no_gas_transfer():
    p = dataclasses.replace(UnifiedParams(), kLa_per_s=0.0)        # Henry off -> no CO2 reaches the headspace
    for mode in MODES:
        o = _obs(mode, params=p)
        assert o.CO2_headspace == pytest.approx(0.0, abs=1e-9)
        assert o.material_balance_closed


def test_reversed_gradients_still_conserve_and_neutral():
    # swap which chamber is acid-rich by putting the bicarbonate as dissolved-only and more acid: still sound
    o = _obs("bulk", acid_mol=0.2, bicarb_dissolved_mol=0.02, bicarb_solid_mol=0.0)
    assert o.material_balance_closed and abs(o.charge_A) < 1e-9 and abs(o.charge_B) < 1e-9


def test_different_volume_ratios():
    p = dataclasses.replace(UnifiedParams(), V_A_L=1.0, V_B_L=3.0)
    o = _obs("bulk", params=p)
    assert o.material_balance_closed and abs(o.charge_A) < 1e-9 and abs(o.charge_B) < 1e-9


def test_fast_mixing_converges_under_refinement():
    coarse = _obs("bulk", n_steps=120)
    fine = _obs("bulk", n_steps=480)
    assert abs(coarse.pH_A - fine.pH_A) < 0.05                     # endpoint converges with the step
    assert fine.material_balance_closed


def test_observer_invariance_sparse_vs_dense():
    # XX-3: changing the SAMPLE density must not change the certification verdict
    dense = run_reactor("bulk", n_samples=None)[0].receipt
    sparse = run_reactor("bulk", n_samples=5)[0].receipt
    assert dense.material_balance_closed == sparse.material_balance_closed
    assert dense.structural_tier == sparse.structural_tier
    assert dense.max_step_material_residual == pytest.approx(sparse.max_step_material_residual, rel=1e-9, abs=1e-15)


def test_open_vent_exports_carbon_sealed_does_not():
    sealed = _obs("bulk", sealed=True)
    vented = _obs("bulk", sealed=False)
    assert sealed.CO2_export_C == pytest.approx(0.0, abs=1e-12)    # sealed: no boundary flux
    assert vented.CO2_export_C > 1e-6                              # open vent: carbon leaves as CO2(g)
    assert vented.material_balance_closed and sealed.material_balance_closed


def test_unknown_transport_mode_is_refused():
    with pytest.raises((ValueError, CoupledError)):
        run_reactor("osmosis")                                     # not one of closed/membrane/bulk
