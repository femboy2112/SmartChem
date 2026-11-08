"""OPERATION XXIV Phase IV -- the 2.0 research simulation API carries a SECOND, genuinely distinct world.

Acceptance matrix (docs/research/OPERATION_XXIV_HANDOFF.md, Phase IV): typed species/phases, exact stoichiometric
conservation, explicit inventories, bound sources, boundary schedules, solver settings, source-domain refusals,
per-component receipts, model/run/evidence/observation identities, deterministic frames, and the composition laws --
including what does NOT compose exactly.
"""
from __future__ import annotations

import inspect

import pytest

from experiments.sandbox_foundation import sim_api_v2alpha as api

W = "calcite_closed_dissolution"
INIT = (api.SpeciesInventory("cell", "CaCO3(s)", "solid", 0.01),
        api.SpeciesInventory("cell", "H2O", "pure_liquid", 55.34),
        api.SpeciesInventory("cell", "H+", "aqueous", 1e-7),
        api.SpeciesInventory("cell", "OH-", "aqueous", 1e-7))
CA = ("Ca+2", "CaCO3(aq)", "CaHCO3+", "CaOH+")
# XXV-1 flipped the API default to converted_to_molar; this file pins the XXIII-replay numbers, so it says so explicitly
LEGACY = api.CalciteParams(standard_state_basis="as_tabulated_molal")


def _spec(phases=(("dissolve", 6000.0, 60),), params=None, n_samples=None, initial=INIT):
    sched = api.BoundarySchedule(tuple(api.BoundaryPhase(n, d, k, "closed", False) for n, d, k in phases))
    return api.SimulationSpec(model=api.ModelSpec(W, params or LEGACY), initial=initial, schedule=sched,
                              solver=api.SolverOptions(rtol=1e-10, atol=1e-18, n_samples=n_samples))


def _ca(frame_or_map, get=None):
    if get is None:
        return sum(frame_or_map.amount("cell", s) for s in CA)
    return sum(frame_or_map[("cell", s)] for s in CA)


@pytest.fixture(scope="module")
def base():
    return api.run(_spec())


def test_two_distinct_builders_are_registered_and_run_names_no_chemistry():
    assert set(api._WORLD_BUILDERS) == {"unified_vinegar_bicarbonate", W}
    src = inspect.getsource(api.run)
    for chem in ("Ca", "CO2", "HAc", "NaHCO3", "acet", "calcite", '"A"', '"gas"'):
        assert chem not in src, f"run() names {chem!r}: the shared run path must stay chemistry-free"


def test_calcite_equilibrium_reproduces_the_xxiii_harness(base):
    # the XXIII-S4 harness's own converged value (NOTES.md: Ca 1.23009e-4 mol vs PHREEQC 1.23007e-4) -- model-vs-model
    assert _ca(base.final_frame) == pytest.approx(1.23009e-4, rel=2e-5)


def test_receipts_are_per_component_and_audited(base):
    r = base.receipts[0]
    assert r.execution_identity_basis == "AUDITED_BUILTIN" and r.execution_identity_certified is True
    assert r.material_balance_closed and r.positivity_held
    assert set(r.component_resolution.values()) == {"VERIFIED_WITHIN_RESOLUTION"}
    assert {"Ca", "C", "charge"} <= set(r.component_resolution)
    assert base.structural_conservation["holds"] is True


def test_global_totals_are_conserved_frame_to_frame(base):
    first, last = api.global_totals(base.frames[0], W), api.global_totals(base.final_frame, W)
    for el in ("Ca", "C", "O", "H"):
        assert last[el] == pytest.approx(first[el], rel=1e-9, abs=1e-15)
    assert abs(last["charge"] - first["charge"]) < 1e-12


def test_provenance_is_derived_and_tiered():
    prov = _spec().provenance.by_name()
    assert prov["Ksp_calcite"].tier == "SOURCED" and "minteq" in prov["Ksp_calcite"].source
    assert prov["k_diss"].tier == "ASSUMED" and prov["kf_fast"].tier == "ASSUMED"
    assert "NOT an accuracy claim" in prov["ionic_strength_max"].source


@pytest.mark.parametrize("bad, match", [
    (dict(phases=(("v", 10.0, 2),)), None),                              # filled below with a vented phase
    (dict(params=api.CalciteParams(temperature_K=320.0)), "SOURCE_DOMAIN_UNSUPPORTED"),
    (dict(initial=(api.SpeciesInventory("cell", "CaCO3(s)", "aqueous", 0.01),)), "phase is part of chemical identity"),
    (dict(initial=(api.SpeciesInventory("A", "CaCO3(s)", "solid", 0.01),)), "unknown compartment"),
    (dict(params=api.CalciteParams(constants_mode="tuned")), "constants_mode"),
])
def test_source_domain_and_typing_refusals(bad, match):
    if match is None:
        sched = api.BoundarySchedule((api.BoundaryPhase("v", 10.0, 2, "closed", True),))
        with pytest.raises(api.SimulationSpecError, match="vented=False"):
            api.SimulationSpec(model=api.ModelSpec(W, api.CalciteParams()), initial=INIT, schedule=sched)
        return
    with pytest.raises(api.SimulationSpecError, match=match):
        _spec(**bad)


def test_ionic_strength_domain_refuses_during_integration():
    from experiments.sandbox_foundation.solid_equilibrium import OutOfDomainError
    with pytest.raises(OutOfDomainError):
        api.run(_spec(params=api.CalciteParams(ionic_strength_max=1e-4)))


def test_identities_separate_model_run_evidence_observation(base):
    ids = base.identities
    ids_obs = api.run(_spec(n_samples=6)).identities
    assert ids_obs["run_digest"] == ids["run_digest"] and ids_obs["model_digest"] == ids["model_digest"]
    assert ids_obs["observation_digest"] != ids["observation_digest"]
    ids_k = api.spec_identities(_spec(params=api.CalciteParams(k_diss_molpLps=2e-6,
                                                               standard_state_basis="as_tabulated_molal")))
    assert ids_k["model_digest"] != ids["model_digest"]
    vinegar = api.spec_identities(api.SimulationSpec(
        model=api.ModelSpec(), initial=(api.SpeciesInventory("A", "HAc", "aqueous", 0.1),),
        schedule=api.BoundarySchedule((api.BoundaryPhase("p", 1.0, 1),))))
    assert vinegar["model"]["world"] != ids["model"]["world"] and vinegar["model_digest"] != ids["model_digest"]


def test_frames_are_deterministic_and_derived_only_from_state(base):
    again = api.run(_spec())
    assert [api.frame_to_dict(f) for f in again.frames] == [api.frame_to_dict(f) for f in base.frames]
    assert all(dict(f.derived) == {"cell": {}} for f in base.frames)    # no projection -> nothing invented


def test_continuation_composes_exactly_at_equal_macro_step(base):
    two = api.run(_spec(phases=(("a", 3000.0, 30), ("b", 3000.0, 30))))
    first = api.run(_spec(phases=(("a", 3000.0, 30),)))
    cont = api.run(api.continue_from(first.spec, first, api.BoundarySchedule(
        (api.BoundaryPhase("b", 3000.0, 30, "closed", False),))))
    assert dict(cont.stitched_final) == dict(two.stitched_final)          # law (a): bit-identical
    assert dict(two.stitched_final) == dict(base.stitched_final)          # same dt sequence as one 60-step phase
    assert not two.stitch_events


def test_what_does_not_compose_exactly_a_different_macro_step(base):
    fine = api.run(_spec(phases=(("dissolve", 6000.0, 120),)))
    d = abs(_ca(fine.stitched_final, True) - _ca(base.stitched_final, True))
    assert d != 0.0                                                       # NOT exact: per-step solves differ ...
    assert d / _ca(base.stitched_final, True) < 1e-6                      # ... at solver-tolerance level
