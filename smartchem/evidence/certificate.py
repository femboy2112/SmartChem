"""The auditor's output types: per-rule results and the audit certificate.

Mirrors the *shape* of the SmartChem ``Certificate`` (``program.py`` — a frozen
``Digestible`` binding a manifest digest, per-check verdicts, an aggregated
evidence ledger, and a casualty list) **without importing it**, because this
certificate makes a strictly weaker claim: epistemic hygiene of an external probe
suite, never SmartChem scientific authority.  The banner rides on every
certificate to keep that distinction impossible to misread.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..contracts import Digestible

__all__ = [
    "AUDIT_CERTIFICATE_SCHEMA",
    "HYGIENE_NOT_PHYSICS_BANNER",
    "AuditCertificate",
    "AuditOutcome",
    "RuleResult",
]

AUDIT_CERTIFICATE_SCHEMA = "smartchem.evidence/audit-certificate-v1"

HYGIENE_NOT_PHYSICS_BANNER = (
    "This certificate attests the EPISTEMIC HYGIENE of a probe suite "
    "(teeth, provenance independence, source locks, scope, tier boundary) — "
    "NOT the correctness of the physics, and NOT any SmartChem scientific "
    "authority. The evidence-status labels report what the probe author DECLARED; "
    "the auditor never raises a declared status and its approval/verifier seam does "
    "not run over an external manifest. A refusal is a success of this tool. "
    "DECLARED-CONTRACT BOUNDARY: this auditor consumes a declared manifest and "
    "cannot see past it — it cannot detect two provenance tokens that alias the "
    "same underlying root, an empirical value hidden in numeric_result instead of "
    "empirical_values, or a rubber-stamp mutation it did not re-execute (Mode B). "
    "Those remain the emitter's honesty obligation."
)


class AuditOutcome(str, Enum):
    """The verdict of one auditor rule."""

    PASS = "PASS"
    FLAG = "FLAG"  # certifiable, but carries a required downgrade/annotation
    REFUSE = "REFUSE"  # blocks certification; never a partial green


@dataclass(frozen=True)
class RuleResult(Digestible):
    """The verdict of a single named auditor rule over the whole manifest."""

    rule: str
    outcome: AuditOutcome
    detail: str
    offending: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.rule, str) or not self.rule:
            raise ValueError("rule must be a non-empty string")
        if not isinstance(self.outcome, AuditOutcome):
            raise TypeError("outcome must be an AuditOutcome")
        if not isinstance(self.detail, str):
            raise TypeError("detail must be a string")
        if not isinstance(self.offending, tuple) or any(
            not isinstance(item, str) for item in self.offending
        ):
            raise TypeError("offending must be a tuple of strings")


@dataclass(frozen=True)
class AuditCertificate(Digestible):
    """The bound, digestible result of auditing one probe manifest."""

    schema: str
    program: str
    manifest_digest: str
    certified: bool
    tier_reported: str
    rule_results: tuple[RuleResult, ...]
    evidence_ledger: tuple[tuple[str, int], ...]
    casualties: tuple[str, ...]
    refusals: tuple[str, ...]
    banner: str

    def __post_init__(self) -> None:
        for name in ("schema", "program", "manifest_digest", "tier_reported", "banner"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.certified) is not bool:
            raise TypeError("certified must be a boolean")
        if not isinstance(self.rule_results, tuple) or any(
            type(item) is not RuleResult for item in self.rule_results
        ):
            raise TypeError("rule_results must be a tuple of RuleResult")
        if not isinstance(self.evidence_ledger, tuple) or any(
            not (isinstance(item, tuple) and len(item) == 2) for item in self.evidence_ledger
        ):
            raise TypeError("evidence_ledger must be a tuple of (status, count) pairs")
        for name in ("casualties", "refusals"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(
                not isinstance(item, str) for item in value
            ):
                raise TypeError(f"{name} must be a tuple of strings")
        # A certified certificate must carry no refusals, and a refused one must.
        if self.certified and self.refusals:
            raise ValueError("a certified certificate cannot carry refusals")
        if not self.certified and not self.refusals:
            raise ValueError("a refused certificate must record at least one refusal")

    def render(self) -> str:
        """Human-readable summary; the machine identity is :attr:`digest`."""
        header = "CERTIFIED" if self.certified else "REFUSED"
        lines = [
            f"[{header}] probe-evidence audit — program {self.program!r}",
            f"  manifest digest : {self.manifest_digest}",
            f"  tier reported   : {self.tier_reported}",
            "  rules:",
        ]
        for result in self.rule_results:
            mark = {
                AuditOutcome.PASS: "ok",
                AuditOutcome.FLAG: "flag",
                AuditOutcome.REFUSE: "REFUSE",
            }[result.outcome]
            lines.append(f"    - {result.rule:<24} {mark:<6} {result.detail}")
        if self.evidence_ledger:
            ledger = ", ".join(f"{name}={count}" for name, count in self.evidence_ledger)
            lines.append(f"  declared evidence ledger: {ledger}")
        if self.casualties:
            lines.append("  casualties / scope boundaries:")
            lines.extend(f"    · {item}" for item in self.casualties)
        if self.refusals:
            lines.append("  refusals:")
            lines.extend(f"    ✗ {item}" for item in self.refusals)
        lines.append(f"  NOTE: {self.banner}")
        return "\n".join(lines)
