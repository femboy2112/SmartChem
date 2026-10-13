"""Regression lock for ACTIVATED-ACYL-TRANSFER-110 (OPERATION §5(A), issue #110) -- the first new-chemistry win.

An anhydride / acyl halide acylating an O/N/S nucleophile (coproduct a carboxylic acid / H-X, not water) is now a
recognized reaction class, so the already-generated activated route stops being demoted as "unrecognized" -- WITHOUT
lifting any unrelated fiction (the cardinal no-false-vouch holds).
"""
from __future__ import annotations

import experiments.activated_acyl_transfer_110 as bench


def test_recognizer_matrix_and_no_false_vouch():
    m = bench.recognizer_matrix()
    assert m["passed"] == m["total"], f"recognizer matrix regressed: {[r for r in m['rows'] if not r[3]]}"
    assert m["recognized_activated"] == 6, "an activated-transfer positive stopped being recognized"
    assert m["false_vouch_as_activated"] == 0, "a fiction was vouched AS activated acyl transfer (CARDINAL)"


def test_does_not_poach_the_free_acid_condensation_or_fictions():
    rows = {name: klass for name, _expect, klass, _ok in bench.recognizer_matrix()["rows"]}
    # the free-acid esterification stays the condensation class, NOT activated transfer (no poach)
    assert rows["free-acid esterification -> acyl condensation (not activated)"] == \
        "acyl condensation (esterification/amidation)"
    # the C-nucleophile Friedel-Crafts acylation is out of scope -> abstains (deferred to #107, never a false-vouch)
    assert rows["Friedel-Crafts C-acylation (out of scope -> abstain)"] is None


def test_generated_but_demoted_route_now_vouches_reachability():
    r = bench.reachability_demo()
    assert r["won"], "the genuine 1-step Ac2O->ethyl-acetate route is not vouched end-to-end"
    assert r["genuine_vouched"], r
    # content-determinism keeps the win honest: isomer/glue C4H6O3 routes are NOT lifted
    assert r["isomer_or_glue_demoted"] >= 1, "the isomer/glue fictions should still be demoted (no blanket lift)"


def test_validate_is_green():
    assert bench.validate() is True
