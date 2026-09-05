"""SNAPSHOT-13.2: a dated provenance stamp on live-fetched provider data (standard section 13.2 / 14.1 / G8).

Section 13.2: *"Provider data and dynamic price/availability inputs MUST carry snapshot IDs or timestamps so a
response is reproducible."*  Standard section 16 G8 records the alpha gap plainly: it value-caches fetched data but
"does not yet stamp a dated snapshot."  This is that stamp.

A snapshot is produced ONLY for a genuine LIVE network fetch -- never for a seed or on-disk-cache read, which is
already dated by its own source -- and records:

* ``provider_ids`` -- which providers were consulted (PubChem/Wikidata/Bradley, ...);
* ``record_count`` -- how many records the fetch yielded;
* ``content_digest`` -- a DETERMINISTIC hash of the fetched records: the same fetched data yields the same id, so it
  is the reproducibility ANCHOR (a re-fetch that returns identical data is recognisably the same snapshot);
* ``fetched_at`` -- the ISO-8601 UTC wall-clock of the fetch.  This is the only run-to-run-varying field; because the
  whole ``provider_snapshots`` tuple is EXCLUDED from :attr:`~smartchem.service.CompilationResponse.result_digest`,
  a --network response stays reproducible (equal result_digest run-to-run) while still carrying the honest date.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..contracts import canonical_digest

PROVIDER_SNAPSHOT_SCHEMA = "smartchem.data/provider-snapshot-v1alpha1"


@dataclass(frozen=True)
class ProviderSnapshot:
    """One live provider fetch's dated provenance (section 13.2).  A plain value: it is carried on the response but
    never enters ``result_digest`` (a fetch time is provenance, not a search result)."""

    schema_version: str
    provider_ids: tuple[str, ...]
    record_count: int
    content_digest: str
    fetched_at: str
    allow_network: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_SNAPSHOT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {PROVIDER_SNAPSHOT_SCHEMA!r}")
        if type(self.provider_ids) is not tuple or any(
            not isinstance(p, str) or not p for p in self.provider_ids
        ):
            raise TypeError("provider_ids must be a tuple of non-empty strings")
        if not isinstance(self.record_count, int) or isinstance(self.record_count, bool) or self.record_count < 0:
            raise ValueError("record_count must be a non-negative int")
        if not isinstance(self.content_digest, str) or not self.content_digest:
            raise ValueError("content_digest must be a non-empty string")
        if not isinstance(self.fetched_at, str) or not self.fetched_at:
            raise ValueError("fetched_at must be a non-empty ISO-8601 timestamp string")
        if type(self.allow_network) is not bool:
            raise TypeError("allow_network must be a bool")


def provider_snapshot(
    fetched_record_digests: "tuple[str, ...]",
    provider_ids: "tuple[str, ...]",
    *,
    fetched_at: str,
    allow_network: bool = True,
) -> ProviderSnapshot:
    """Build a snapshot from the digests of the records a live fetch produced.

    ``content_digest`` is the canonical hash of the SORTED record digests, so it is order-independent and
    deterministic: two fetches that return the same records get the same ``content_digest`` (the reproducibility
    anchor), regardless of ``fetched_at``.  ``fetched_at`` is supplied by the caller (the fetch boundary stamps the
    real wall-clock; a test injects a fixed value through the loader seam) so this factory stays pure and testable.
    """
    content_digest = canonical_digest(tuple(sorted(fetched_record_digests)))
    return ProviderSnapshot(
        PROVIDER_SNAPSHOT_SCHEMA,
        tuple(provider_ids),
        len(fetched_record_digests),
        content_digest,
        fetched_at,
        allow_network,
    )
