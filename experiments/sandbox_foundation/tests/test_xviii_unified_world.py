"""OPERATION XVIII §5 -- the unified vinegar/bicarbonate world runs end to end, through ONE generic integrator, and
its chemical inventories reconcile with the signed external-flux ledger.

These pins exercise the headline deliverable: a two-liquid-cell + gas-headspace world where solid NaHCO3 dissolution
(a kernel reaction), mixed acetate/carbonate fast equilibrium (a projection), gas-liquid Henry transfer and an
inter-cell valve all compose, and an open-vessel CO2 export is INDEPENDENTLY ledgered (XVIII-3).  Reduced durations/
step counts keep them fast; conservation closure is a step-count-independent identity, so a short run proves it.
"""
from __future__ import annotations

import json

import pytest

from experiments.sandbox_foundation.unified_chemical_world import Phase_, UnifiedParams, simulate


@pytest.fixture(scope="module")
def open_run():
    """Acid isolated (valve closed), then the valve opens into bicarbonate-containing water, open vessel (CO2 exports)."""
    phases = (Phase_("closed", valve_open=False, sealed=False, duration_s=10.0, n_steps=20),
              Phase_("open", valve_open=True, sealed=False, duration_s=40.0, n_steps=60))
    return simulate(UnifiedParams(), phases, acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1)


def test_material_balance_closes_every_phase(open_run):
    wr = open_run["whole_run"]
    assert wr["material_balance_closed_every_phase"] is True
    assert wr["worst_ledger_residual"] < 1e-9, "the checked (C, Na) material balance must close to ~machine zero"
    assert wr["positivity_held_every_phase"] is True


def test_exported_carbon_is_independently_ledgered(open_run):
    """§3 in the flagship: the carbon that fizzed out of the open vessel is accounted as a signed external flux, and
    reconciles with the measured whole-system carbon change -- not inferred from an endpoint diff."""
    ext = open_run["whole_run"]["external_flux_total"]
    raw = open_run["whole_run"]["raw_material_change_total"]
    assert ext["C"] < -1e-4, "carbon must leave the open vessel as CO2"
    # O leaves as 2x C (CO2 carries two oxygens) -- a cross-check the ledger gets right
    assert abs(ext["O"] - 2.0 * ext["C"]) < 1e-9
    # the measured whole-system carbon change equals the integrated boundary flux (the balance, not a tautology)
    assert abs(raw["C"] - ext["C"]) < 1e-6


def test_solid_dissolves_and_co2_evolves(open_run):
    first, last = open_run["frames"][0], open_run["frames"][-1]
    assert first["solid_NaHCO3_mol"] > 0.0 and last["solid_NaHCO3_mol"] < 1e-6   # solid is consumed
    assert last["CO2_gas_mol"] > 1e-4 and last["p_CO2_atm"] > 0.0                 # gas emerges from equilibrium+transport
    assert last["pH_B"] < first["pH_B"]                                          # acid drove the bicarbonate cell down


def test_charge_claim_is_demoted_against_neutral_water(open_run):
    assert any("DEMOTED" in pr["charge_balance_claim"] for pr in open_run["phase_reports"])


def test_result_is_strict_json(open_run):
    json.dumps(open_run, allow_nan=False)   # no NaN/Infinity anywhere in the emitted frame


def test_sealed_vessel_exports_no_carbon():
    phases = (Phase_("open_sealed", valve_open=True, sealed=True, duration_s=30.0, n_steps=45),)
    res = simulate(UnifiedParams(), phases, acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1)
    ext = res["whole_run"]["external_flux_total"]
    assert res["whole_run"]["material_balance_closed_every_phase"] is True
    assert abs(ext.get("C", 0.0)) < 1e-9, "a sealed vessel exports no carbon -- the CO2 stays in the headspace"
    # carbon is internally conserved (no boundary): the measured whole-system carbon change is ~0
    assert abs(res["whole_run"]["raw_material_change_total"].get("C", 0.0)) < 1e-6


def test_no_carbon_makes_no_gas():
    phases = (Phase_("open", valve_open=True, sealed=False, duration_s=30.0, n_steps=45),)
    res = simulate(UnifiedParams(), phases, acid_mol=0.5, bicarb_solid_mol=0.0, bicarb_dissolved_mol=0.0)
    assert res["frames"][-1]["CO2_gas_mol"] < 1e-9, "no carbon in the world -> no CO2 can evolve"
    assert abs(res["whole_run"]["external_flux_total"].get("C", 0.0)) < 1e-9
    assert res["whole_run"]["material_balance_closed_every_phase"] is True
