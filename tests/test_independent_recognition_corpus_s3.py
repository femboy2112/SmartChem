"""Regression lock for INDEPENDENT-RECOGNITION-CORPUS-S3 (OPERATION §3 -- the held-out recognition benchmark).

This is the second, independent bearing on recognition coverage: unlike :mod:`experiments.synthesis_coverage_corpus`
(whose positives are the generator's own scissions), every case here is HAND-AUTHORED and labelled from chemistry
before the oracle runs.  The test pins the soundness floor and makes any coverage drift LOUD -- in particular, when
issue #110 (activated acyl transfer) or #114 (hydrogenation) later gains a recognizer, the corresponding gap
assertion flips and this test must be updated deliberately, which is the intended signal, not an accident.
"""
from __future__ import annotations

import experiments.independent_recognition_corpus_s3 as bench


def test_no_false_vouch_full_recall_and_no_drift():
    m = bench.measure()
    assert m["false_vouch"] == 0, (
        f"CARDINAL: a fiction/mutation was vouched -- {[r[0].name for r in m['rows'] if r[4] == bench.FALSE_VOUCH]}")
    assert m["recall_hits"] == m["recall_total"] == 9, f"recall regressed: {m['recall_hits']}/{m['recall_total']}"
    assert not m["mismatches"], f"coverage drifted from the recorded labels: {m['mismatches']}"
    assert bench.validate() is True


def test_documented_coverage_gaps_are_the_expected_four():
    # These are REAL reactions with NO attested recognizer: honest abstention, surfaced as findings.  When a
    # recognizer is added for one (e.g. #110 Friedel-Crafts / #114 hydrogenation), remove it here deliberately.
    gaps = set(bench.measure()["coverage_gaps"])
    assert any("Friedel-Crafts" in g for g in gaps), "#110 activated acyl transfer should still be an open gap"
    assert any("hydrogenation" in g for g in gaps), "#114 hydrogenation should still be an open gap"
    assert any("aldol" in g for g in gaps)
    assert any("nucleophilic substitution (charged)" in g for g in gaps)
    assert len(gaps) == 4, f"coverage-gap set changed: {sorted(gaps)}"


def test_pericyclic_centreless_residual_is_132():
    # The #132 residual, surfaced as data: a genuine Diels-Alder with a carried centre VOUCHES, but the SAME
    # reaction hand-built without a centre abstains (pericyclic Layer-C fail-closes on an absent centre).  When
    # #132 makes the pericyclic families content-deterministic (Layer A alone), this residual must disappear.
    residuals = bench.measure()["pericyclic_residuals"]
    assert len(residuals) == 1 and "centre-less" in residuals[0], residuals


def test_isomer_mutations_flip_recognition_off():
    # Structural discrimination: an isomeric target the precursors do NOT assemble (ethyl formate vs methyl acetate;
    # propanamide vs N-methylacetamide) must flip recognition OFF even though the whole-molecule census fires.
    rows = {c.name: outcome for c, _b, _k, _e, outcome in bench.measure()["rows"]}
    assert rows["mutation: acetic acid + methanol -> ethyl formate (isomer of methyl acetate)"] == bench.MUTATION_OFF
    assert rows["mutation: acetic acid + methylamine -> propanamide (isomer of N-methylacetamide)"] == bench.MUTATION_OFF
