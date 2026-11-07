"""OPERATION XXIII -- the 2.0a0 research simulation-API candidate: spec validation, layers, and the COMPOSITION LAWS.

What these tests pin (and, just as much, what they refuse to pretend):
  (a) phase concatenation HOLDS (bitwise, including the recorded stitch events);
  (b) time-splitting is NOT a monoid homomorphism: on an unchanged step grid the cut costs only re-projection/stitch
      roundoff, but once the pieces carry their own dt the O(dt) splitting error shows -- shrinking under refinement,
      never zero;
  (c) observer invariance HOLDS: n_samples changes neither the final state nor any receipt verdict.
Simulations are kept tiny (tens of steps) -- the box is RAM-tight and these are law checks, not physics benchmarks.
"""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from experiments.sandbox_foundation.sim_api_v2alpha import (
    API_VERSION,
    LAYERS,
    BoundaryPhase,
    BoundarySchedule,
    ModelSpec,
    SimulationSpec,
    SimulationSpecError,
    SolverOptions,
    SpeciesInventory,
    continue_from,
    result_to_dict,
    run,
)
from experiments.sandbox_foundation.unified_chemical_world import UnifiedParams

INIT = (SpeciesInventory("A", "HAc", "aqueous", 0.5),
        SpeciesInventory("B", "NaHCO3(s)", "solid", 0.2),
        SpeciesInventory("B", "HCO3-", "aqueous", 0.1),
        SpeciesInventory("B", "Na+", "aqueous", 0.1))


def _spec(phases, *, n_samples=None, initial=INIT):
    return SimulationSpec(ModelSpec(params=UnifiedParams()), initial, BoundarySchedule(tuple(phases)),
                          SolverOptions(n_samples=n_samples))


def _vec(res):
    return np.array([v for _, v in sorted(res.stitched_final.items())])


P1 = BoundaryPhase("separate", 10.0, 5, "closed", True)
P2 = BoundaryPhase("mixing", 20.0, 10, "bulk", True)


@pytest.fixture(scope="module")
def two_phase():
    return run(_spec([P1, P2]))


# ------------------------------------------------------------------ the surface
def test_api_version_stamped_everywhere(two_phase):
    assert API_VERSION == "smartchem-sim-2.0a0-research"
    assert two_phase.api_version == API_VERSION
    assert all(f.api_version == API_VERSION for f in two_phase.frames)
    wire = result_to_dict(two_phase)
    assert wire["api_version"] == API_VERSION and "not stable" in wire["stability"]
    assert all(f["api_version"] == API_VERSION for f in wire["frames"])
    json.dumps(wire, allow_nan=False)        # strict JSON


def test_module_docstring_disclaims_stability():
    import experiments.sandbox_foundation.sim_api_v2alpha as m
    doc = m.__doc__
    assert "NOT a stable API" in doc and "NOT in the wheel" in doc and "NOT covered by COMPATIBILITY.md" in doc


def test_frames_and_receipts_are_immutable(two_phase):
    f = two_phase.frames[0]
    with pytest.raises(FrozenInstanceError):
        f.time_s = 1.0
    with pytest.raises(TypeError):
        f.amounts[("A", "HAc")] = 9.0
    with pytest.raises(TypeError):
        two_phase.receipts[0].component_resolution["C"] = "VERIFIED_WITHIN_RESOLUTION"


def test_layers_are_separate_and_reported(two_phase):
    assert set(LAYERS) == {"exact_conservation", "numerical_conservation", "rate_law_identity", "calibration",
                           "visual_output"}
    assert two_phase.structural_conservation["holds"] is True          # layer 1: exact integers
    for rc in two_phase.receipts:                                        # layer 2: error-bounded verdicts
        assert set(rc.component_resolution.values()) == {"VERIFIED_WITHIN_RESOLUTION"}
        assert rc.execution_identity_basis == "AUDITED_BUILTIN"          # layer 3: verbatim, not upgraded
        assert rc.admitted_tier == "ASSUMED_PARAMETER"                   # layer 4: nothing calibrated
    assert all(e.tier == "ASSUMED" for e in two_phase.spec.provenance.entries if e.name.startswith("k"))


def test_provenance_is_derived_not_caller_supplied():
    with pytest.raises(TypeError):
        SimulationSpec(ModelSpec(), INIT, BoundarySchedule((P1,)), SolverOptions(), provenance=None)
    prov = _spec([P1]).provenance.by_name()
    assert prov["KH_CO2_25C"].tier == "SOURCED" and prov["Qsp_NaHCO3_empirical"].tier == "DERIVED"
    assert prov["kLa"].tier == "ASSUMED" and prov["kLa"].value == UnifiedParams().kLa_per_s


@pytest.mark.parametrize("bad, msg", [
    ((SpeciesInventory("B", "NaHCO3(s)", "aqueous", 0.1),), "declared 'solid'"),
    ((SpeciesInventory("A", "CO2(g)", "gas", 0.1),), "does not live in"),
    ((SpeciesInventory("A", "HAc", "aqueous", -1.0),), ">= 0"),
    ((SpeciesInventory("A", "unobtainium", "aqueous", 1.0),), "unknown species"),
])
def test_initial_inventory_phase_is_explicit_and_checked(bad, msg):
    with pytest.raises(SimulationSpecError, match=msg):
        _spec([P1], initial=bad)


def test_schedule_and_domain_fail_closed():
    with pytest.raises(SimulationSpecError):
        _spec([BoundaryPhase("x", 1.0, 1, "teleport", True)])
    with pytest.raises(SimulationSpecError):
        _spec([])
    with pytest.raises(SimulationSpecError, match="25 C"):
        SimulationSpec(ModelSpec(params=UnifiedParams(temperature_K=320.0)), INIT, BoundarySchedule((P1,)))


# ------------------------------------------------------------------ law (a): phase concatenation HOLDS
def test_law_a_phase_concatenation_holds(two_phase):
    first = run(_spec([P1]))
    second = run(continue_from(first.spec, first, BoundarySchedule((P2,))))
    # bitwise: the stitched state is fed back verbatim and the integrator is deterministic
    assert dict(second.stitched_final) == dict(two_phase.stitched_final)
    assert dict(second.frames[-1].amounts) == dict(two_phase.frames[-1].amounts)
    assert second.receipts[0] == two_phase.receipts[1]
    # "up to the recorded stitch events": the boundary clamp is in BOTH runs, identically
    ev_concat = [e for e in two_phase.stitch_events if e.after_phase == "separate"]
    assert [(e.compartment, e.species, e.added_mol) for e in first.stitch_events] == \
           [(e.compartment, e.species, e.added_mol) for e in ev_concat]


# ------------------------------------------------------------------ law (b): time-splitting is NOT a homomorphism
T = 40.0
SPLIT_NS = (8, 16, 32)


@pytest.fixture(scope="module")
def splitting_measurements():
    out = {}
    for n in SPLIT_NS:
        one = _vec(run(_spec([BoundaryPhase("whole", T, n, "bulk", True)])))
        own = _vec(run(_spec([BoundaryPhase("h1", T / 2, n, "bulk", True),
                              BoundaryPhase("h2", T / 2, n, "bulk", True)])))
        out[n] = float(np.max(np.abs(own - one)))
    aligned_one = _vec(run(_spec([BoundaryPhase("whole", T, 8, "bulk", True)])))
    aligned_two = _vec(run(_spec([BoundaryPhase("h1", T / 2, 4, "bulk", True),
                                  BoundaryPhase("h2", T / 2, 4, "bulk", True)])))
    out["aligned"] = float(np.max(np.abs(aligned_two - aligned_one)))
    return out


def test_law_b_split_on_unchanged_grid_costs_only_roundoff(splitting_measurements):
    # same dt, cut on the step grid: only re-projection + stitch-clamp roundoff (measured ~1e-12 mol)
    assert splitting_measurements["aligned"] < 1e-9


def test_law_b_split_with_own_dt_is_nonzero_and_shrinks_under_refinement(splitting_measurements):
    errs = [splitting_measurements[n] for n in SPLIT_NS]
    assert all(e > 1e-5 for e in errs), errs                # NOT zero: no homomorphism
    assert errs[0] > errs[1] > errs[2], errs                # shrinks under refinement
    for a, b in zip(errs, errs[1:]):                        # ~first order (SNIA projection), ratio ~2 per halving
        assert 1.4 < a / b < 3.0, errs


# ------------------------------------------------------------------ law (c): observer invariance HOLDS
def test_law_c_observer_invariance(two_phase):
    sparse = run(_spec([P1, P2], n_samples=2))
    assert len(sparse.frames) < len(two_phase.frames)
    assert dict(sparse.stitched_final) == dict(two_phase.stitched_final)
    assert dict(sparse.frames[-1].amounts) == dict(two_phase.frames[-1].amounts)
    for a, b in zip(sparse.receipts, two_phase.receipts):
        assert a == b                                        # every verdict, residual and ledger value
    ids_s, ids_d = sparse.identities, two_phase.identities
    assert ids_s["run_digest"] == ids_d["run_digest"] and ids_s["model_digest"] == ids_d["model_digest"]
    assert ids_s["observation_digest"] != ids_d["observation_digest"]


def test_run_identity_moves_with_inventory_not_with_cadence():
    from experiments.sandbox_foundation.sim_api_v2alpha import spec_identities
    s1 = _spec([P1])
    s2 = _spec([P1], initial=(SpeciesInventory("A", "HAc", "aqueous", 0.4),) + INIT[1:])
    i1, i2 = spec_identities(s1), spec_identities(s2)
    assert i1["model_digest"] == i2["model_digest"] and i1["run_digest"] != i2["run_digest"]
