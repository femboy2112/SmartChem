"""SNAPSHOT-13.2 / G8: live-fetched provider data carries a dated snapshot, threaded onto the response.

Pins: (1) autoload_stability STAMPS a dated ProviderSnapshot on the returned table when (and only when) a LIVE fetch
produced records -- a seed/cache/offline read is NEVER stamped, so a reproducible offline run carries no spurious
fetch time; (2) content_digest is DETERMINISTIC (same fetched records -> same id, order-independent) while fetched_at
is the honest wall-clock; (3) CompilationResponse carries provider_snapshots, they round-trip through the JSON payload
exactly (provider_ids stays a tuple), and they are EXCLUDED from result_digest -- two fetches with different
fetched_at but identical data share a result_digest, so a --network response stays reproducible.
"""
from __future__ import annotations

import dataclasses

from smartchem.conditions import Interval
from smartchem.data.autoload import StabilityCache, autoload_stability
from smartchem.data.provider_snapshot import PROVIDER_SNAPSHOT_SCHEMA, ProviderSnapshot, provider_snapshot
from smartchem.data.providers.base import PropertyProvider, PropertyRecord
from smartchem.service import (
    build_recompile_request,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.smiles import parse_smiles


class _StubProvider(PropertyProvider):
    name = "StubProvider"

    def fetch(self, *, identifier, formula=None):  # a clean, sourced hit for any query -> one live record
        return PropertyRecord(
            boiling=Interval(390.0, 391.0, "K"),
            isolable=True,
            sources={"boiling": "stub-source", "isolable": "stub-source"},
            source_name="StubProvider",
        )


def _fresh_cache(tmp_path) -> StabilityCache:
    return StabilityCache.load(str(tmp_path / "cache.json"))  # empty, isolated -- never touches the real cache


def test_a_live_fetch_stamps_a_dated_snapshot_on_the_table(tmp_path):
    mol = parse_smiles("CCCCCCCCO")  # octan-1-ol: off-seed, so resolution reaches the live-fetch step
    table = autoload_stability(
        [mol], identifiers={mol: "octan-1-ol"}, providers=(_StubProvider(),),
        cache=_fresh_cache(tmp_path), allow_network=True,
    )
    snap = table.provider_snapshot
    assert type(snap) is ProviderSnapshot
    assert snap.record_count == 1
    assert "_StubProvider" in snap.provider_ids
    assert snap.content_digest and snap.fetched_at and snap.allow_network is True


def test_a_seed_or_offline_read_is_never_stamped(tmp_path):
    water = parse_smiles("O")  # water is in the SEED -> no fetch -> no snapshot
    table = autoload_stability([water], cache=_fresh_cache(tmp_path), allow_network=False)
    assert table.provider_snapshot is None


def test_a_cache_hit_on_the_second_run_is_never_stamped(tmp_path):
    # anti-fabrication (red-team Finding 1): a cache HIT is not a live fetch, so a second run over the SAME molecule
    # (served from the cache the first run populated) must NOT stamp a fresh "we fetched at T" snapshot.  A mutant
    # that appended the cached ref to fetched_refs would be CAUGHT here.
    mol = parse_smiles("CCCCCCCCO")
    cache = _fresh_cache(tmp_path)
    first = autoload_stability([mol], identifiers={mol: "octan-1-ol"}, providers=(_StubProvider(),),
                               cache=cache, allow_network=True)
    assert first.provider_snapshot is not None  # first run genuinely fetched
    second = autoload_stability([mol], identifiers={mol: "octan-1-ol"}, providers=(_StubProvider(),),
                                cache=cache, allow_network=True)  # served from cache now
    assert second.provider_snapshot is None  # a cache hit is not a fetch -> no spurious stamp


class _EmptyProvider(PropertyProvider):
    name = "EmptyProvider"

    def fetch(self, *, identifier, formula=None):  # a clean MISS -- nothing sourced
        return None


def test_a_live_query_that_sources_nothing_is_never_stamped(tmp_path):
    # anti-fabrication (red-team Finding 1): allow_network with an off-seed compound but a provider that yields NO
    # record produces no StabilityRef -> no snapshot.  A mutant that stamped whenever the network was merely
    # CONSULTED (rather than when a record was actually produced) would be CAUGHT here.
    mol = parse_smiles("CCCCCCCCCCO")  # decan-1-ol: off-seed
    table = autoload_stability([mol], identifiers={mol: "decan-1-ol"}, providers=(_EmptyProvider(),),
                               cache=_fresh_cache(tmp_path), allow_network=True)
    assert table.provider_snapshot is None


def test_content_digest_is_deterministic_and_order_independent():
    a = provider_snapshot(("d1", "d2", "d3"), ("P",), fetched_at="2026-01-01T00:00:00+00:00")
    b = provider_snapshot(("d3", "d1", "d2"), ("P",), fetched_at="2026-06-06T12:00:00+00:00")  # diff order + time
    assert a.content_digest == b.content_digest  # same records -> same reproducibility id, regardless of order/time
    assert a.fetched_at != b.fetched_at          # ... but the honest wall-clock is preserved distinctly
    c = provider_snapshot(("d1", "d2"), ("P",), fetched_at="2026-01-01T00:00:00+00:00")
    assert c.content_digest != a.content_digest  # different records -> different id


def test_run_compilation_carries_provider_snapshots():
    snap = ProviderSnapshot(PROVIDER_SNAPSHOT_SCHEMA, ("PubChem",), 2, "abc123", "2026-01-01T00:00:00+00:00")
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2), provider_snapshots=(snap,))
    assert resp.provider_snapshots == (snap,)


def test_provider_snapshots_are_excluded_from_result_digest():
    base = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    s1 = ProviderSnapshot(PROVIDER_SNAPSHOT_SCHEMA, ("PubChem",), 1, "sameid", "2026-01-01T00:00:00+00:00")
    s2 = ProviderSnapshot(PROVIDER_SNAPSHOT_SCHEMA, ("PubChem",), 1, "sameid", "2026-09-09T09:09:09+00:00")  # later
    r1 = dataclasses.replace(base, provider_snapshots=(s1,))
    r2 = dataclasses.replace(base, provider_snapshots=(s2,))
    # a fetch time is provenance, not identity: same search -> same result_digest regardless of when/whether it fetched
    assert r1.result_digest == r2.result_digest == base.result_digest


def test_a_snapshot_round_trips_through_the_json_payload():
    snap = ProviderSnapshot(
        PROVIDER_SNAPSHOT_SCHEMA, ("PubChem", "Wikidata"), 3, "digest123", "2026-05-05T05:05:05+00:00",
    )
    base = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    injected = dataclasses.replace(base, provider_snapshots=(snap,))
    back = response_from_payload(response_to_payload(injected))
    assert back.provider_snapshots == (snap,)
    assert back.provider_snapshots[0].provider_ids == ("PubChem", "Wikidata")  # a tuple, not a list -- exact round-trip


def test_response_rejects_an_untyped_provider_snapshot():
    import pytest
    base = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    with pytest.raises(TypeError, match="ProviderSnapshot"):
        dataclasses.replace(base, provider_snapshots=("not a snapshot",))
