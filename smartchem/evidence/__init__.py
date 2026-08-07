"""Probe-evidence contract auditor — a decoupled sibling of the SmartChem compiler.

SmartChem already enforces, in code, the discipline whose *absence* caused a
retraction in a sibling research program: *"a check derived from its own subject
checks nothing."*  This subpackage points that discipline at any external project's
numerical *probes*, auditing the epistemic contract around them — teeth, provenance
independence, source locks, scope, and tier boundary — and either **certifying** or
**refusing** it.

What it is **not**: a physics checker, a tenth executor, or a claim of SmartChem
scientific authority.  It reuses :mod:`smartchem.contracts` primitives but never
enters the closed executor registry, and it never raises a declared evidence
status.  Every certificate carries :data:`HYGIENE_NOT_PHYSICS_BANNER`.

Reusability: the integration contract is the JSON manifest schema
(``smartchem.evidence/probe-manifest-v1``; see ``manifest.schema.json``).  A project
emits a conformant manifest and runs ``python -m smartchem.evidence verify-probes``;
it imports nothing from SmartChem and SmartChem imports nothing from it.  The tier
vocabulary is caller-declared (``floor_tier`` / ``promoted_tier``), so the auditor is
not fine-man-specific.
"""
from __future__ import annotations

from .auditor import audit_manifest
from .certificate import (
    AUDIT_CERTIFICATE_SCHEMA,
    HYGIENE_NOT_PHYSICS_BANNER,
    AuditCertificate,
    AuditOutcome,
    RuleResult,
)
from .example import example_manifest
from .manifest_io import (
    ManifestError,
    load_manifest,
    load_manifest_dir,
    manifest_from_mapping,
    manifest_to_mapping,
)
from .records import (
    MANIFEST_SCHEMA,
    EvidenceRecord,
    ProbeManifest,
    ProvenanceTag,
    Role,
    SourceLockedValue,
    evidence_rank,
)
from .rules import (
    RULES,
    rule_provenance_independence,
    rule_scope,
    rule_source_lock,
    rule_teeth,
    rule_tier_boundary,
)

__all__ = [
    "AUDIT_CERTIFICATE_SCHEMA",
    "HYGIENE_NOT_PHYSICS_BANNER",
    "MANIFEST_SCHEMA",
    "RULES",
    "AuditCertificate",
    "AuditOutcome",
    "EvidenceRecord",
    "ManifestError",
    "ProbeManifest",
    "ProvenanceTag",
    "Role",
    "RuleResult",
    "SourceLockedValue",
    "audit_manifest",
    "evidence_rank",
    "example_manifest",
    "load_manifest",
    "load_manifest_dir",
    "manifest_from_mapping",
    "manifest_to_mapping",
    "rule_provenance_independence",
    "rule_scope",
    "rule_source_lock",
    "rule_teeth",
    "rule_tier_boundary",
]
