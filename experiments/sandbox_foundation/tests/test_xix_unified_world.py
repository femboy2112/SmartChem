"""OPERATION XIX Track A -- the unified world's IDENTITY, pH CONVENTION, TEMPERATURE domain and PHASE scheduler are
honest:

  * 1A  a RUN digest that binds the initial-value problem (inventories + schedule + solver config), a MODEL digest
        that binds the physical model (incl. the Ka/K1/K2/Kw set) but not the inventories, and a separate EVIDENCE
        digest -- so two runs with different acid no longer collide on one `model_run_digest`.
  * 1B  the frame reports the AUTHORITATIVE activity pH the solver computed, labels its convention, and emits the
        concentration pH alongside -- never a renderer recompute presented as the primary value.
  * 1C  an off-25 C world is refused (every constant is 25 C-sourced), not run as a mixed-temperature simulation.
  * 1E  inputs are validated and the phase stitch is a MEASURED, BOUNDED, RECORDED roundoff correction that refuses a
        real positivity excursion instead of silently clipping it.
"""
from __future__ import annotations

import json

import pytest

from experiments.sandbox_foundation.aqueous_equilibrium import OutOfSourceDomainError
from experiments.sandbox_foundation.unified_chemical_world import (
    Phase_,
    UnifiedParams,
    _build_species,
    _digest,
    _restitch,
    model_identity,
    run_identity,
    simulate,
)

PHASES = (Phase_("closed", valve_open=False, sealed=False, duration_s=10.0, n_steps=20),
          Phase_("open", valve_open=True, sealed=False, duration_s=40.0, n_steps=60))


def _run(**kw):
    base = dict(acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1)
    base.update(kw)
    return simulate(UnifiedParams(), PHASES, **base)


# ---------------------------------------------------------------- 1A: model / run / evidence identity
def test_1a_run_digest_varies_with_each_initial_inventory():
    """The XVIII collision: identical config + different acid returned an IDENTICAL `model_run_digest` over different
    initial-value problems.  The run digest is a pure function of the inputs, so it is pinned HERE directly (robust to
    whether an extreme inventory happens to land in the solver's verified regime) -- and the emitted run_digest from a
    real run is confirmed to equal that direct computation."""
    def rd(**kw):
        base = dict(acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1,
                    n_samples=None, scheme="strang", rtol=1e-10, atol=1e-14)
        base.update(kw)
        return _digest(run_identity(UnifiedParams(), PHASES, **base))
    base = rd()
    assert base != rd(acid_mol=1.0)
    assert base != rd(bicarb_solid_mol=0.9)
    assert base != rd(bicarb_dissolved_mol=0.25)
    assert base == _run()["identity"]["run_digest"]         # the emitted digest matches the direct computation


def test_1a_model_digest_invariant_under_inventory_but_moves_with_the_model():
    base = _run()["identity"]["model_digest"]
    assert base == _run(acid_mol=1.0)["identity"]["model_digest"]        # inventory is RUN identity, not MODEL
    moved = simulate(UnifiedParams(k_diss_molpLps=0.1), PHASES, acid_mol=0.5, bicarb_solid_mol=0.2,
                     bicarb_dissolved_mol=0.1)["identity"]["model_digest"]
    assert base != moved                                                # a changed rate coefficient moves the model


def test_1a_model_identity_binds_the_equilibrium_constant_set():
    mid = model_identity(UnifiedParams(), PHASES)
    assert set(mid["equilibrium_operator"]["K_set"]) == {"Ka", "K1", "K2", "Kw"}
    assert mid["identity_version"] == "xix-1"


def test_1a_model_run_alias_equals_run_digest():
    idy = _run()["identity"]
    assert idy["model_run_digest"] == idy["run_digest"]
    for k in ("model_digest", "run_digest", "evidence_digest", "model_identity", "run_identity", "evidence_identity"):
        assert k in idy


# ---------------------------------------------------------------- 1B: authoritative activity pH, convention labelled
def test_1b_frame_reports_activity_ph_with_convention():
    fr = _run()["frames"][-1]
    assert fr["activity_model"] == "davies"
    assert fr["pH_B"] == fr["pH_B_activity"]                             # primary == the solver's chosen convention
    assert fr["pH_A"] == fr["pH_A_activity"]
    assert abs(fr["pH_B_activity"] - fr["pH_B_concentration"]) > 1e-6    # the two conventions are genuinely different
    assert fr["ionic_strength_B_M"] is not None


# ---------------------------------------------------------------- 1C: off-25 C refusal (flagship)
def test_1c_flagship_refuses_off_25C():
    with pytest.raises(OutOfSourceDomainError):
        simulate(UnifiedParams(temperature_K=305.0), PHASES, acid_mol=0.5, bicarb_solid_mol=0.2,
                 bicarb_dissolved_mol=0.1)


def test_1c_at_25C_runs():
    assert _run()["temperature_K"] == 298.15


# ---------------------------------------------------------------- 1E: input validation + recorded, bounded stitch
def test_1e_empty_phases_refused():
    with pytest.raises(ValueError):
        simulate(UnifiedParams(), (), acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1)


def test_1e_bad_schedule_and_inventory_refused():
    with pytest.raises(ValueError):
        _run(acid_mol=-1.0)
    with pytest.raises(ValueError):
        simulate(UnifiedParams(), (Phase_("x", False, False, 10.0, 0),), acid_mol=0.5, bicarb_solid_mol=0.2,
                 bicarb_dissolved_mol=0.1)
    with pytest.raises(ValueError):
        simulate(UnifiedParams(), (Phase_("x", False, False, -1.0, 10),), acid_mol=0.5, bicarb_solid_mol=0.2,
                 bicarb_dissolved_mol=0.1)


def test_1e_nonfinite_or_nonpositive_params_refused():
    with pytest.raises(ValueError):
        simulate(UnifiedParams(V_B_L=0.0), PHASES, acid_mol=0.5, bicarb_solid_mol=0.2, bicarb_dissolved_mol=0.1)
    with pytest.raises(ValueError):
        simulate(UnifiedParams(V_A_L=float("inf")), PHASES, acid_mol=0.5, bicarb_solid_mol=0.2,
                 bicarb_dissolved_mol=0.1)


def test_1e_stitch_clamp_is_recorded_and_dust_sized():
    res = _run()
    wr = res["whole_run"]
    assert wr["stitch_clamp_total_mol"] is not None and wr["stitch_clamp_total_mol"] < 1e-9
    for pr in res["phase_reports"]:
        assert "stitch_clamp_total_mol" in pr and "stitch_clamp_max_mol" in pr


def test_1e_restitch_clamps_dust_but_refuses_a_real_excursion():
    """The stitch is a bounded roundoff correction: dust within the scale-aware budget is clamped and logged; a
    negative larger than the budget is flagged as a violation (simulate then raises instead of clipping it away)."""
    sp = _build_species()
    vols = {"B": 1.0}
    clean, tot, mx, viol, _events = _restitch({"B": {sp.HCO3: -1e-14, sp.Nap: 0.1}}, vols)
    assert not viol and clean["B"][sp.HCO3] == 0.0 and tot == pytest.approx(1e-14)
    clean2, _tot2, _mx2, viol2, _events2 = _restitch({"B": {sp.HCO3: -0.3, sp.Nap: 0.1}}, vols)
    assert viol2 and clean2["B"][sp.HCO3] == 0.0          # clamped in the returned state, but flagged for refusal


# ---------------------------------------------------------------- strict JSON (no NaN/Inf anywhere)
def test_result_is_strict_json():
    json.dumps(_run(), allow_nan=False)
