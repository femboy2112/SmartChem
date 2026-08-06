"""The auditor: run every rule over a manifest and bind the result certificate.

Aggregation policy:

* **Any REFUSE ⇒ refused certificate.** No partial green; the certificate lists
  every refusing rule and the records that tripped it.
* **Evidence ledger is aggregated from DECLARED statuses only.** The auditor never
  invents or raises a status — the no-label-borrowing invariant.  Because rule 2
  already refuses a common-mode agreement that over-reports, a *certified* manifest
  cannot contain a status the auditor would need to downgrade.
* **Tier reported.** ``claimed_tier`` on certify (it passed the tier rule and thus
  earned the label); ``floor_tier`` on refusal (never report a promoted claim over
  a refusal).
"""
from __future__ import annotations

from collections import Counter

from .certificate import (
    AUDIT_CERTIFICATE_SCHEMA,
    HYGIENE_NOT_PHYSICS_BANNER,
    AuditCertificate,
    AuditOutcome,
)
from .records import ProbeManifest
from .rules import RULES

__all__ = ["audit_manifest"]


def audit_manifest(manifest: ProbeManifest) -> AuditCertificate:
    """Audit one probe manifest and return a bound :class:`AuditCertificate`."""
    if type(manifest) is not ProbeManifest:
        raise TypeError("audit_manifest requires an exact ProbeManifest")

    results = tuple(rule(manifest) for rule in RULES)
    refusing = tuple(r for r in results if r.outcome is AuditOutcome.REFUSE)
    certified = not refusing

    ledger_counts = Counter(record.evidence_status.value for record in manifest.records)
    evidence_ledger = tuple(sorted(ledger_counts.items()))

    casualties = tuple(
        sorted(
            {
                record.scope_boundary.strip()
                for record in manifest.records
                if record.scope_boundary.strip()
            }
        )
    )

    refusals = tuple(f"{r.rule}: {r.detail}" for r in refusing)
    tier_reported = manifest.claimed_tier if certified else manifest.floor_tier

    return AuditCertificate(
        schema=AUDIT_CERTIFICATE_SCHEMA,
        program=manifest.program,
        manifest_digest=manifest.digest,
        certified=certified,
        tier_reported=tier_reported,
        rule_results=results,
        evidence_ledger=evidence_ledger,
        casualties=casualties,
        refusals=refusals,
        banner=HYGIENE_NOT_PHYSICS_BANNER,
    )
