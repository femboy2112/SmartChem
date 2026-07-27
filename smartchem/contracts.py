"""
Shared, immutable contracts for the simulation compiler.

This module is intentionally smaller than the compiler built on top of it.  It owns the
things that must mean exactly the same thing in the shepherd, planner, runtime, and result
certificate:

* canonical content digests;
* inference/evidence classifications that cannot alias one another;
* executable-obligation *identities* (the evaluator itself belongs to the runtime); and
* run states in which an interrupted calculation cannot masquerade as a smaller success.

The digest is an identity and integrity aid, not an authentication boundary.  It rejects
unsupported values rather than falling back to ``repr`` because two semantic objects that
happen to print alike must never share an approval or cache identity.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum

__all__ = [
    "ClaimKind",
    "DerivationRef",
    "Digestible",
    "EvidenceStatus",
    "ExecutionLane",
    "InferenceKind",
    "ObligationOutcome",
    "ObligationResult",
    "ObligationStage",
    "RunStatus",
    "ValidityObligation",
    "canonical_digest",
    "canonical_payload",
    "freeze_semantic_value",
    "oracle_implementation_digest",
]


class InferenceKind(str, Enum):
    """How a proposed value was obtained; these are deliberately non-interchangeable."""

    DERIVED_COMPLETE = "DERIVED_COMPLETE"
    WRITTEN_CHECKED = "WRITTEN_CHECKED"
    SEARCHED_INCOMPLETE = "SEARCHED_INCOMPLETE"
    QUESTION_CONFIRMED = "QUESTION_CONFIRMED"
    UNDECIDABLE = "UNDECIDABLE"
    UNSUPPORTED = "UNSUPPORTED"


class EvidenceStatus(str, Enum):
    """Strength of evidence, independent of what a claim refers to."""

    ESTABLISHED = "ESTABLISHED"
    VALIDATED_WITHIN_REGIME = "VALIDATED_WITHIN_REGIME"
    CALIBRATED = "CALIBRATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    STRUCTURAL_TOY = "STRUCTURAL_TOY"
    UNSUPPORTED = "UNSUPPORTED"


class ClaimKind(str, Enum):
    """The referent of a claim; an analogue never becomes literal by gaining evidence."""

    LITERAL = "LITERAL"
    ANALOGUE = "ANALOGUE"
    EXPERIMENTAL_PROXY = "EXPERIMENTAL_PROXY"


class ExecutionLane(str, Enum):
    CERTIFIED = "CERTIFIED"
    EXPERIMENTAL = "EXPERIMENTAL"


class ObligationStage(str, Enum):
    PRE = "PRE"
    POST = "POST"


class ObligationOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REFINE = "REFINE"
    REFUSE = "REFUSE"
    NOT_RUN = "NOT_RUN"


class RunStatus(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"
    REFUSED = "REFUSED"
    FAILED = "FAILED"


def _qualified_name(value: object) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def canonical_payload(value: object) -> object:
    """
    Return a deterministic, type-tagged JSON-compatible representation.

    Type tags keep values such as ``1``, ``1.0`` and ``True`` distinct and preserve the
    semantic difference between tuples, lists, sets, mappings, enums, and dataclasses.
    Callables and arbitrary objects are refused: a digest that silently depends on their
    display text would be an unsafe approval identity.
    """
    if value is None:
        return {"type": "none"}
    if isinstance(value, Enum):
        return {
            "type": "enum",
            "class": _qualified_name(value),
            "value": canonical_payload(value.value),
        }
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": value}
    if isinstance(value, float):
        if math.isnan(value):
            raise ValueError("semantic records cannot contain NaN")
        # Existing oracle specs use +inf as a deliberate, typed "no illumination" sentinel.
        # Preserve signed infinity explicitly; unlike NaN it is equal to itself and has a
        # stable semantic meaning in that public calculation contract.
        return {
            "type": "float",
            "value": value if math.isfinite(value) else ("+inf" if value > 0 else "-inf"),
        }
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, type):
        return {
            "type": "type",
            "class": f"{value.__module__}.{value.__qualname__}",
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": "dataclass",
            "class": _qualified_name(value),
            "fields": [
                [field.name, canonical_payload(getattr(value, field.name))]
                for field in fields(value)
                if not field.name.startswith("_") and field.compare
            ],
        }
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("semantic mapping keys must be strings")
        return {
            "type": "mapping",
            "items": [
                [key, canonical_payload(value[key])]
                for key in sorted(value)
            ],
        }
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [canonical_payload(item) for item in value]}
    if isinstance(value, list):
        return {"type": "list", "items": [canonical_payload(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        encoded = [canonical_payload(item) for item in value]
        encoded.sort(key=lambda item: json.dumps(item, separators=(",", ":"), sort_keys=True))
        return {
            "type": "frozenset" if isinstance(value, frozenset) else "set",
            "items": encoded,
        }
    raise TypeError(
        "semantic record contains unsupported value "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def canonical_digest(value: object) -> str:
    """SHA-256 over :func:`canonical_payload`, with no display-string fallback."""
    encoded = json.dumps(
        canonical_payload(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def freeze_semantic_value(value: object) -> object:
    """
    Convert JSON-like settings into a deeply immutable, type-preserving tuple structure.

    This is used when a calculation specification must retain its settings as part of a
    frozen dataclass.  The representation is intentionally internal-looking; callers should
    compare or digest it, not infer physics from its tuple layout.
    """
    payload = canonical_payload(value)

    def freeze(item: object) -> object:
        if isinstance(item, dict):
            return tuple((key, freeze(item[key])) for key in sorted(item))
        if isinstance(item, list):
            return tuple(freeze(member) for member in item)
        return item

    return freeze(payload)


def oracle_implementation_digest(oracle: object) -> str:
    """
    Hash every implementation module in an ``.inner`` oracle-wrapper chain.

    The calculation settings and implementation are separate identity axes.  A wrapper may
    delegate its settings correctly while accidentally hiding a changed inner implementation;
    walking the chain prevents that exact stale-plan failure.  This remains a source digest,
    not a security signature or a complete fingerprint of undeclared external state.
    """
    digest = hashlib.sha256()
    seen_objects: set[int] = set()
    seen_modules: set[str] = set()
    current = oracle
    while current is not None and id(current) not in seen_objects:
        seen_objects.add(id(current))
        target = inspect.getmodule(type(current)) or type(current)
        name = getattr(target, "__name__", None) or _qualified_name(current)
        if name not in seen_modules:
            seen_modules.add(name)
            try:
                source = inspect.getsource(target).encode("utf-8")
            except (OSError, TypeError):
                source = b"unavailable"
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(source).digest())
        current = getattr(current, "inner", None)
    return digest.hexdigest()


class Digestible:
    """Mixin for frozen semantic records whose public fields define their identity."""

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class DerivationRef(Digestible):
    """Machine-readable provenance for one proposed or checked binding."""

    kind: InferenceKind
    source: str
    source_digest: str
    scope: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, InferenceKind):
            raise TypeError("kind must be an InferenceKind")
        for name in ("source", "source_digest", "scope"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class ValidityObligation(Digestible):
    """
    A named runtime check.

    ``evaluator_id`` is resolved by the approved runtime registry.  Storing a callable here
    would make plans process-local and undigestible, and would let implementation mutation
    escape the plan identity.
    """

    name: str
    stage: ObligationStage
    evaluator_id: str
    description: str
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ObligationStage):
            raise TypeError("stage must be an ObligationStage")
        for name in ("name", "evaluator_id", "description"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.required) is not bool:
            raise TypeError("required must be a boolean")


@dataclass(frozen=True)
class ObligationResult(Digestible):
    obligation_digest: str
    outcome: ObligationOutcome
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ObligationOutcome):
            raise TypeError("outcome must be an ObligationOutcome")
        if not isinstance(self.obligation_digest, str) or not self.obligation_digest:
            raise ValueError("obligation_digest must be a non-empty string")
        if not isinstance(self.detail, str):
            raise TypeError("detail must be a string")
