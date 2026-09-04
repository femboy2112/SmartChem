"""HOLDOUT-RXN-01: the frozen family-stratified coverage benchmark is a LIVE guard, not a throwaway script.

These tests pin the benchmark so it cannot silently drift: the frozen target set + its content hash + each target's
expected family attribution are asserted against the live compiler, the holdout subset is frozen separately, and the
set is verified NON-VACUOUS (every bucket populated, coverage strictly below 100%, and each algebra widening unlocks
at least one target). A wrong provider change moves a frozen attribution and fails HERE.
"""
from experiments.holdout_rxn_benchmark import (
    FROZEN_ATTRIB,
    FROZEN_HASH,
    HOLDOUT_HASH,
    TARGETS,
    _holdout_fingerprint,
    measure,
    target_fingerprint,
)


def test_the_frozen_target_hash_matches_the_live_set():
    # tamper-evidence: editing any target's structure or split moves this hash, so the frozen expectations below
    # cannot quietly diverge from the set they were frozen against.
    assert target_fingerprint() == FROZEN_HASH


def test_the_holdout_subset_hash_is_frozen():
    assert _holdout_fingerprint() == HOLDOUT_HASH


def test_live_attribution_equals_the_frozen_expectation():
    # the regression guard: the live compiler must attribute every target to exactly the family frozen for it.
    assert measure() == FROZEN_ATTRIB


def test_every_bucket_is_populated_so_coverage_is_not_vacuous():
    buckets = set(FROZEN_ATTRIB.values())
    for required in ("CONSTRUCTIBLE_BY_CAPPED", "UNLOCKED_BY_BOND_ORDER", "UNLOCKED_BY_HETEROLYTIC", "OUTSIDE_CLOSURE"):
        assert required in buckets, f"benchmark must exercise {required} (else coverage is vacuous)"
    # coverage is genuinely bounded: some targets are OUTSIDE the whole algebra, so it is never a vacuous 100%.
    outside = [t for t, a in FROZEN_ATTRIB.items() if a == "OUTSIDE_CLOSURE"]
    assert outside and len(outside) < len(FROZEN_ATTRIB)


def test_each_algebra_widening_unlocks_at_least_one_target():
    # the genericity payoff, MEASURED: widening capped -> +bond-order -> +heterolytic each strictly increases reach.
    attrib = list(FROZEN_ATTRIB.values())
    assert attrib.count("CONSTRUCTIBLE_BY_CAPPED") >= 1
    assert attrib.count("UNLOCKED_BY_BOND_ORDER") >= 1
    assert attrib.count("UNLOCKED_BY_HETEROLYTIC") >= 1


def test_the_holdout_split_spans_multiple_families():
    holdout = {t for t, (_b, split) in TARGETS.items() if split == "holdout"}
    assert holdout, "the benchmark declares a holdout split"
    holdout_buckets = {FROZEN_ATTRIB[t] for t in holdout}
    assert len(holdout_buckets) >= 3, "the holdout must be a real cross-family held-out set, not one family"


def test_the_split_partitions_the_whole_set():
    splits = {split for _b, split in TARGETS.values()}
    assert splits == {"train", "dev", "holdout"}
    assert set(TARGETS) == set(FROZEN_ATTRIB), "every target has a frozen attribution"
