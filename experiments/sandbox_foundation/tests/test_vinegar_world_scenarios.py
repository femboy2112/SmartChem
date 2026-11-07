"""OPERATION XXIII -- vented vs sealed vinegar world (scenario harness + HTML projection).

Coarse resolution (dt = 10 s, 30 steps per regime) to respect the RAM budget; the directional physics is checked,
not assumed: sealed must end with more gas AND more dissolved carbon AND lower pH than vented, because that is what
the model does (measured at the committed default resolution too -- see the benchmark README).
"""
from __future__ import annotations

import json
import math

import pytest

from experiments.sandbox_foundation.carbonate_equilibrium import R_GAS_L_ATM
from experiments.sandbox_foundation.snapshot import QuantityKind
from experiments.sandbox_foundation.vinegar_world_scenarios import (
    SAFETY_NOTICE,
    DeclaredChemistry,
    run_both,
    scenario_spec,
)
from experiments.sandbox_foundation.vinegar_world_viz import BANNER, ILLUSTRATION_LABEL, build_payload, render_html

CHEM = DeclaredChemistry(steps_per_10s=1)
KINDS = {k.value for k in QuantityKind}


@pytest.fixture(scope="module")
def both():
    return run_both(CHEM)


def test_regimes_share_chemistry_and_differ_by_boundary_only():
    v, s = scenario_spec("vented", CHEM), scenario_spec("sealed", CHEM)
    assert v.model == s.model and v.initial == s.initial and v.solver == s.solver
    assert v.provenance == s.provenance
    for pv, ps in zip(v.schedule.phases, s.schedule.phases):
        assert (pv.name, pv.duration_s, pv.n_steps, pv.transport_mode) == \
               (ps.name, ps.duration_s, ps.n_steps, ps.transport_mode)
        assert pv.vented is True and ps.vented is False


def test_model_identity_differs_only_in_boundary_topology(both):
    mv, ms = both["vented"]["model_identity"], both["sealed"]["model_identity"]
    uv, us = dict(mv["unified_model_identity"]), dict(ms["unified_model_identity"])
    assert uv.pop("phase_topology") != us.pop("phase_topology")
    assert uv == us                                              # species, reactions, K-set, constants, params
    assert [p[:2] for p in mv["phase_topology_v2"]] == [p[:2] for p in ms["phase_topology_v2"]]


def test_sealed_ends_with_more_gas_more_dic_lower_ph(both):
    v, s = both["vented"]["end_state"], both["sealed"]["end_state"]
    assert s["CO2_gas_mol"] > v["CO2_gas_mol"]
    assert s["p_CO2_atm"] > v["p_CO2_atm"]
    assert s["DIC_A_mol"] + s["DIC_B_mol"] > v["DIC_A_mol"] + v["DIC_B_mol"]
    assert s["pH_B"] < v["pH_B"] and s["pH_A"] < v["pH_A"]
    assert s["cumulative_C_exported_mol"] == pytest.approx(0.0, abs=1e-12)
    assert v["cumulative_C_exported_mol"] > 0.1


def test_henry_back_pressure_slows_degassing(both):
    # same time, mixing phase: the sealed headspace pushes back, so its B->gas flux is lower once p_CO2 builds
    fv = [f for f in both["vented"]["frames"] if f["phase"] == "mixing"]
    fs = [f for f in both["sealed"]["frames"] if f["phase"] == "mixing"]
    later = [(a, b) for a, b in zip(fv, fs) if a["time_s"] >= 60.0]
    assert later and all(b["quantities"]["henry_flux_B_to_gas_mol_per_s"]["value"]
                         < a["quantities"]["henry_flux_B_to_gas_mol_per_s"]["value"] for a, b in later)


def test_p_co2_is_exactly_nrt_over_v(both):
    p = CHEM.params
    for r in ("vented", "sealed"):
        for f in both[r]["frames"]:
            q = f["quantities"]
            assert q["p_CO2_atm"]["value"] == q["CO2_gas_mol"]["value"] * R_GAS_L_ATM.value * p.temperature_K / p.V_gas_L
            assert "Air is NOT modeled" in q["p_CO2_atm"]["label"]


def test_every_frame_value_is_typed_with_kind_and_tier(both):
    for r in ("vented", "sealed"):
        for f in both[r]["frames"]:
            for name, q in f["quantities"].items():
                assert q["kind"] in KINDS, name
                assert isinstance(q["tier"], str) and q["tier"], name


def test_unmodeled_quantities_are_unsupported_null_never_invented(both):
    for r in ("vented", "sealed"):
        for f in both[r]["frames"]:
            for name in ("bubble_diameter_m", "foam_height_m", "total_headspace_pressure_atm"):
                q = f["quantities"][name]
                assert q["kind"] == "UNSUPPORTED" and q["value"] is None
            for q in f["quantities"].values():
                if q["kind"] == "UNSUPPORTED":
                    assert q["value"] is None


def test_frames_are_strict_json(both):
    json.dumps(both, allow_nan=False)


def test_sealed_carries_safety_text(both):
    assert SAFETY_NOTICE == "computational only — not a laboratory safety certification"
    assert both["sealed"]["safety_notice"] == SAFETY_NOTICE and SAFETY_NOTICE in both["sealed"]["notices"]


def test_cumulative_export_matches_receipt_ledger(both):
    sc = both["vented"]
    led = -sum(r["external_flux"]["C"] for r in sc["receipts"])
    assert sc["end_state"]["cumulative_C_exported_mol"] == pytest.approx(led, rel=1e-6, abs=1e-12)


def test_receipts_surface_numerical_verdicts_and_identity_basis(both):
    for r in ("vented", "sealed"):
        q = both[r]["frames"][-1]["quantities"]
        assert q["material_balance_closed"]["value"] is True
        assert all(v["resolution"] == "VERIFIED_WITHIN_RESOLUTION" for v in q["numerical_balance"]["value"].values())
        assert q["claim_tier"]["value"] == "ASSUMED_PARAMETER"
        names = {a["name"] for a in q["active_assumptions"]["value"]}
        assert {"k_diss", "kLa", "k_export"} <= names


def test_html_is_self_contained_deterministic_and_labeled(both):
    payload = build_payload(both)
    a, b = render_html(payload), render_html(build_payload(run_both(CHEM)))
    assert a == b                                                  # deterministic end to end
    assert BANNER in a and ILLUSTRATION_LABEL in a and "bubble geometry not modeled" in a
    assert "prefers-color-scheme" in a and 'name="viewport"' in a
    for forbidden in ("http://", "https://", "<link", "src="):
        assert forbidden not in a.replace("http://www.w3.org/2000/svg", "")
    for key, panel in payload["regimes"]["sealed"]["panels"].items():
        assert panel["kind"] and panel["tier"], key
    assert not any(isinstance(v, float) and not math.isfinite(v) for v in payload["difference"].values()
                   if v is not None)
