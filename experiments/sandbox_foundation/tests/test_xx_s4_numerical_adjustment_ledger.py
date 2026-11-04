"""OPERATION XX section 4 -- phase-stitch roundoff corrections CONSERVE MATTER explicitly.

Clamping a negative inventory up to 0 at a phase boundary ADDS a small amount of matter.  That correction is now an
EXPLICIT numerical-adjustment EVENT in the global ledger: per species and per element/charge, time-stamped, a DISTINCT
category from physical boundary flux, never silently clipped and never disguised as chemistry or a feed.  The whole-run
global balance then shows the roundoff clamp is EXACTLY the inventory change the external flux alone cannot explain, and
accounting for it closes the balance.

The first target named by the operation is solid-bicarbonate exhaustion -- and that is exactly where the natural clamp
occurs here (NaHCO3(s) -> 0 at the valve-closed boundary).
"""
from __future__ import annotations

import json

import pytest

from experiments.sandbox_foundation.unified_chemical_world import (
    _build_species,
    _restitch,
    _scenario,
    simulate,
)


# -------------------------------------------------------- the event mechanism (direct, magnitude-independent)
def test_restitch_emits_explicit_adjustment_events_with_element_and_charge_impact():
    sp = _build_species()
    # a roundoff-scale negative solid (scale 10 -> budget ~1e-8) is clamped and recorded as ONE adjustment event
    clean, tot, mx, viol, events = _restitch({"B": {sp.solid: -1e-9, sp.Nap: 10.0}}, {"B": 1.0})
    assert not viol
    assert len(events) == 1
    e = events[0]
    assert e["compartment"] == "B" and e["species"] == "NaHCO3(s)"
    assert e["added_mol"] == pytest.approx(1e-9)                         # matter CREATED by clamping up to 0
    # NaHCO3 = C1 H1 Na1 O3, charge 0: the element impact is the exact composition times the added amount
    assert e["element_impact"] == pytest.approx({"C": 1e-9, "H": 1e-9, "Na": 1e-9, "O": 3e-9})
    assert e["charge_impact"] == 0.0
    assert e["budget"] > 1e-9                                            # the clamp was within the scale-aware budget
    assert "numerical adjustment" in e["reason"].lower()                # distinguishable from chemistry / feed
    assert clean["B"][sp.solid] == 0.0 and clean["B"][sp.Nap] == 10.0   # the next phase starts from the corrected state

    # a CHARGED species carries a charge impact too (Na+ : +1)
    _c, _t, _m, viol2, ev2 = _restitch({"B": {sp.Nap: -2e-9, sp.HCO3: 10.0}}, {"B": 1.0})
    assert not viol2 and len(ev2) == 1
    assert ev2[0]["element_impact"] == pytest.approx({"Na": 2e-9})
    assert ev2[0]["charge_impact"] == pytest.approx(2e-9)


def test_restitch_beyond_budget_is_a_violation_not_a_silent_adjustment():
    sp = _build_species()
    _c, _t, _m, viol, events = _restitch({"B": {sp.solid: -1.0, sp.Nap: 10.0}}, {"B": 1.0})
    assert viol                                                         # a real excursion -> the caller raises
    assert events == []                                                 # NOT recorded as an admissible adjustment


# -------------------------------------------------------- the whole-run global balance (solid-exhaustion case)
def test_simulate_threads_the_clamp_into_an_explicit_global_balance():
    r = simulate(**_scenario("excess_acid"), n_samples=5)               # acid-excess -> NaHCO3(s) exhausts and clamps
    wr = r["whole_run"]
    adjustments = wr["numerical_adjustments"]
    assert len(adjustments) >= 1
    ev = adjustments[0]
    assert ev["species"] == "NaHCO3(s)" and ev["compartment"] == "B"
    assert ev["added_mol"] > 0.0
    # the per-element impact is the solid's exact composition
    assert ev["element_impact"]["C"] == pytest.approx(ev["added_mol"])
    assert ev["element_impact"]["O"] == pytest.approx(3 * ev["added_mol"])

    gb = wr["global_balance"]
    assert gb["closed"] is True
    assert set(gb["checked_components"]) == {"C", "Na"}                  # H/O/charge are implicit-reservoir, excluded
    adj_total = wr["numerical_adjustment_total"]
    for k in gb["checked_components"]:
        adj = adj_total[k]
        assert adj > 0.0
        # LOAD-BEARING: the numerical adjustment is EXACTLY the gap between the flux-only and the accounted residual,
        # i.e. the clamp is precisely the inventory change external boundary flux cannot explain.
        assert gb["residual_flux_only"][k] - gb["residual_accounted"][k] == pytest.approx(adj, rel=1e-9, abs=1e-20)
        # ignoring the clamp leaves a LARGER residual; accounting for it shrinks it to per-phase ledger noise within tol
        assert abs(gb["residual_accounted"][k]) < abs(gb["residual_flux_only"][k])
        assert abs(gb["residual_accounted"][k]) <= gb["tolerance"]
        # the clamp is NOT disguised as boundary flux: the flux-only residual still carries the full adjustment
        assert gb["residual_flux_only"][k] == pytest.approx(adj, abs=gb["tolerance"])


def test_simulate_adjustment_ledger_is_strict_json():
    r = simulate(**_scenario("excess_acid"), n_samples=5)
    json.dumps(r, allow_nan=False)                                      # every adjustment field is finite + serialisable
