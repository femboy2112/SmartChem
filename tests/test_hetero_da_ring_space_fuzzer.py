"""Fast regression pins over the committed generative hetero-DA ring-space fuzzer
(:mod:`experiments.hetero_da_ring_space_fuzzer`).

Kept independent of the harness so a refactor cannot silently drop the generative evidence.  The four invariants
(I1 soundness, I2 guard-2c generativity, I3 heteroatom lock, I4 the diene/dienophile Layer-A separation) must stay
at ZERO violations over the whole enumerated ``5C + 1X`` ring space; the frozen summary hash trips on any drift of
the coverage counts (re-audit before re-freezing).
"""
from __future__ import annotations

import experiments.hetero_da_ring_space_fuzzer as fuzz


def test_fuzzer_validates_and_frozen_hash_stable():
    assert fuzz.validate() is True
    assert fuzz.content_hash() == fuzz.FROZEN_HASH


def test_every_family_algebra_invariant_holds_with_zero_violations():
    s = fuzz.summary()
    assert s["violation_I1_unsound_emission"] == 0
    assert s["violation_I2_over_valence_emitted"] == 0    # guard 2c drops every charged fiction, not just 3 cases
    assert s["violation_I3_heteroatom_leak"] == 0
    assert s["violation_I4_double_vouch"] == 0             # the crown: shared centre, still no diene<->dnp poach


def test_the_sweep_is_non_vacuous():
    # it must actually MATCH real adducts and actually GENERATE charged-fiction rings, or the zero-violation result
    # would be vacuously true (nothing tested).
    s = fuzz.summary()
    assert 0 < s["rings_matched_by_some_family"] < s["rings_enumerated"]     # some match, some don't
    assert 0 < s["rings_over_neutral_valence"] < s["rings_enumerated"]       # some fictions were generated
    assert s["total_emissions"] > 0
