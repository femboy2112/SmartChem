"""Wave D (Round VII) tests -- the living chamber's observation boundary.

The frame is strict JSON, carries the conserved totals / derived species / activity pH / membrane transfer ledger /
receipt + numerics disclosure / unsupported-as-null, and is honest about being a model prediction under caller-
declared transport -- never a physical measurement.  The presenter refuses a broken frame and never shows a
prediction as a sensor reading.
"""
import json
import math

import pytest

from experiments.sandbox_foundation.chamber_frame import (
    ChamberFrameError, ChamberPresenter, LIBGIBSON_FRAME_FIELDS, SCHEMA, chamber_frame, chamber_receipt,
    validate_chamber_frame)
from experiments.sandbox_foundation.living_chamber import make_chamber, run, two_chamber_world


def _world():
    return two_chamber_world(left=make_chamber(acetate_M=0.1, sodium_M=0.0),
                             right=make_chamber(acetate_M=0.1, sodium_M=0.05), g_HAc_m3_per_s=1e-9)


def _stepped_state():
    # a state AFTER a real step, so it carries a non-trivial transfer ledger
    return run(_world(), dt=2.0, n_steps=3, policy="substep")[-1]


def test_frame_is_strict_json_and_validates_clean():
    f = chamber_frame(_stepped_state())
    text = json.dumps(f, allow_nan=False)                    # strict: raises if any NaN/Infinity slipped in
    assert "NaN" not in text and "Infinity" not in text
    assert json.loads(text) == f                             # round-trips
    assert validate_chamber_frame(f) == []


def test_frame_carries_the_documented_fields():
    f = chamber_frame(_stepped_state())
    assert f["schema_version"] == SCHEMA and isinstance(f["tick"], int)
    assert set(f["global_totals_mol"]) == {"acetate", "sodium"}
    for c in f["cells"]:
        assert set(c["totals_mol"]) == {"acetate", "sodium"}
        assert set(c["concentrations_mol_per_L"]) == {"HAc", "Ac-", "H+", "OH-", "Na+", "NaAc"}
        assert math.isfinite(c["pH"]) and math.isfinite(c["pH_activity"])
        assert c["verdict"].startswith("SOLVED_")
    assert len(f["membranes"]) == 1
    m = f["membranes"][0]
    assert m["tail"] == 0 and m["head"] == 1 and abs(m["last_transfer_mol"]) > 0.0   # a real transfer this step
    # the A2 numerics disclosure travels in the receipt
    disc = f["receipt"]["numerics_disclosure"]
    assert "truncation error vs the exact solution (no a-posteriori bound)" in disc["unbounded_errors"]
    assert set(disc["checked_residuals"]) == {"charge_residual_M", "component_identity_mol"}
    assert "transport conductances are CALLER-DECLARED, not source-verified" in " || ".join(f["assumptions"])
    assert set(LIBGIBSON_FRAME_FIELDS)                       # the field doc exists for epic #125


def test_frame_is_a_prediction_never_a_measurement():
    f = chamber_frame(_stepped_state())
    t = f["trust"]
    assert t["observed_measurement"] is False                # a simulation never observes
    assert t["supported_prediction"] is False                # transport is caller-declared (SYNTHETIC admission)
    assert f["receipt"]["admitted"] is False
    screen = ChamberPresenter().render(json.dumps(f))
    assert "NOT A PHYSICAL MEASUREMENT" in screen
    assert "pH=" in screen and "last transfer=" in screen    # it DOES show pH and the transfer ledger


def test_unsupported_quantities_are_null_never_zero():
    f = chamber_frame(_stepped_state())
    for nm, q in f["unsupported"].items():
        assert q["value"] is None and q["kind"] == "UNSUPPORTED"


def test_building_a_frame_is_a_pure_read():
    st = _stepped_state()
    before = (st.world.chambers[0].n_acetate_mol, st.world.chambers[1].n_acetate_mol)
    f1 = chamber_frame(st)
    f2 = chamber_frame(st)
    after = (st.world.chambers[0].n_acetate_mol, st.world.chambers[1].n_acetate_mol)
    assert f1 == f2 and before == after                      # no mutation, deterministic


def test_forged_observed_measurement_is_refused():
    f = chamber_frame(_stepped_state())
    f["trust"]["observed_measurement"] = True                # forge an observation that never happened
    probs = validate_chamber_frame(f)
    assert any("observed_measurement" in p for p in probs)
    with pytest.raises(ChamberFrameError):
        ChamberPresenter().render(json.dumps(f))


def test_a_nan_in_the_frame_is_caught_by_the_strict_contract():
    f = chamber_frame(_stepped_state())
    f["cells"][0]["pH"] = float("nan")                       # a strict consumer must reject this
    assert any("strict JSON" in p or "finite" in p for p in validate_chamber_frame(f))


def test_receipt_numerically_verified_from_tiny_residuals():
    r = chamber_receipt(_stepped_state())
    assert r.numerically_verified is True                    # charge + component residuals are far within tolerance
    assert r.admitted is False and r.observed_measurement is False
