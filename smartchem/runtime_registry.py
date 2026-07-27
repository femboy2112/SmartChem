"""Closed-world metadata for SmartChem's validated simulation executors.

The registry contains names, not Python object capabilities.  Importing this module does
not import any compiler, domain, or runtime module; type, contract-factory, and runner
references are resolved only when the caller explicitly asks for them.  This keeps the
registry usable from :mod:`smartchem.program` without creating an import cycle.

This is deliberately a static registry.  Adding an executor is a reviewed source change
that changes :func:`semantic_manifest_digest`; there is no third-party registration seam.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType

__all__ = [
    "ExecutorDescriptor",
    "FunctionReference",
    "TypeReference",
    "descriptor_for",
    "executor_ids",
    "extract_subject",
    "output_contract_error",
    "resolve_runner",
    "semantic_manifest",
    "semantic_manifest_digest",
    "validate_output_contract",
]


_MANIFEST_SCHEMA = "smartchem.runtime-registry/v1"
_EXACT_CONTRACT_ERROR = (
    "this narrow executor can honor only its exact default output contract; "
    "changing support, resolution, precision, coverage, diagnostics, retention, "
    "or observable membership requires a different validated executor"
)


def _qualified_name(value: object) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _validate_module_name(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or any(not part.isidentifier() for part in value.split("."))
    ):
        raise ValueError(f"{field_name} must be a dotted Python module name")


def _validate_qualified_name(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or any(not part.isidentifier() for part in value.split("."))
    ):
        raise ValueError(f"{field_name} must be a dotted Python qualified name")


def _resolve_qualified(module_name: str, qualname: str) -> object:
    value: object = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


@dataclass(frozen=True)
class TypeReference:
    """An import-lazy, exact nominal type reference."""

    module: str
    qualname: str

    def __post_init__(self) -> None:
        _validate_module_name(self.module, "module")
        _validate_qualified_name(self.qualname, "qualname")

    def resolve(self) -> type[object]:
        resolved = _resolve_qualified(self.module, self.qualname)
        if not isinstance(resolved, type):
            raise TypeError(f"{self.module}.{self.qualname} does not resolve to a type")
        if (
            resolved.__module__ != self.module
            or resolved.__qualname__ != self.qualname
        ):
            raise TypeError(
                f"{self.module}.{self.qualname} resolved to aliased type "
                f"{resolved.__module__}.{resolved.__qualname__}"
            )
        return resolved

    def manifest_record(self) -> dict[str, str]:
        return {"module": self.module, "qualname": self.qualname}


@dataclass(frozen=True)
class FunctionReference:
    """An import-lazy, module-level Python function reference."""

    module: str
    name: str

    def __post_init__(self) -> None:
        _validate_module_name(self.module, "module")
        if not isinstance(self.name, str) or not self.name.isidentifier():
            raise ValueError("name must be a Python identifier")

    def resolve(self) -> Callable[..., object]:
        resolved = getattr(importlib.import_module(self.module), self.name)
        if not inspect.isfunction(resolved):
            raise TypeError(f"{self.module}.{self.name} does not resolve to a function")
        if resolved.__module__ != self.module or resolved.__name__ != self.name:
            raise TypeError(
                f"{self.module}.{self.name} resolved to aliased function "
                f"{resolved.__module__}.{resolved.__name__}"
            )
        return resolved

    def manifest_record(self) -> dict[str, str]:
        return {"module": self.module, "name": self.name}


@dataclass(frozen=True)
class ExecutorDescriptor:
    """Immutable semantic and runtime references for one shipped executor."""

    executor_id: str
    resolved_container: TypeReference
    subject_type: TypeReference
    subject_attribute: str
    output_contract_factory: FunctionReference
    runner: FunctionReference
    implementation_modules: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.executor_id, str) or not self.executor_id:
            raise ValueError("executor_id must be a non-empty string")
        if not isinstance(self.subject_attribute, str) or not self.subject_attribute.isidentifier():
            raise ValueError("subject_attribute must be a Python identifier")
        if not isinstance(self.implementation_modules, tuple):
            raise TypeError("implementation_modules must be a tuple")
        for module_name in self.implementation_modules:
            _validate_module_name(module_name, "implementation_modules entry")
        if (
            len(self.implementation_modules) != len(set(self.implementation_modules))
            or self.implementation_modules != tuple(sorted(self.implementation_modules))
        ):
            raise ValueError("implementation_modules must be unique and sorted")

    def extract_subject(self, resolved: object) -> object:
        """Return the typed subject, rejecting nominally similar or subclass values."""
        expected_container = self.resolved_container.resolve()
        if type(resolved) is not expected_container:
            raise TypeError(
                f"executor {self.executor_id!r} requires exact resolved container "
                f"{self.resolved_container.module}.{self.resolved_container.qualname}; "
                f"received {_qualified_name(resolved)}"
            )
        try:
            subject = getattr(resolved, self.subject_attribute)
        except AttributeError as error:
            raise TypeError(
                f"resolved container for executor {self.executor_id!r} has no declared "
                f"subject attribute {self.subject_attribute!r}"
            ) from error
        expected_subject = self.subject_type.resolve()
        if type(subject) is not expected_subject:
            raise TypeError(
                f"executor {self.executor_id!r} requires exact subject "
                f"{self.subject_type.module}.{self.subject_type.qualname}; "
                f"received {_qualified_name(subject)}"
            )
        return subject

    def default_output_contract(self) -> object:
        """Construct the executor's canonical output contract on demand."""
        return self.output_contract_factory.resolve()()

    def output_contract_error(self, contract: object) -> str | None:
        expected = self.default_output_contract()
        if type(contract) is not type(expected) or contract != expected:
            return _EXACT_CONTRACT_ERROR
        return None

    def validate_output_contract(self, contract: object) -> None:
        error = self.output_contract_error(contract)
        if error is not None:
            raise ValueError(error)

    def resolve_runner(self) -> Callable[..., object]:
        return self.runner.resolve()

    def manifest_record(self) -> dict[str, object]:
        return {
            "executor_id": self.executor_id,
            "resolved_container": self.resolved_container.manifest_record(),
            "subject": {
                **self.subject_type.manifest_record(),
                "attribute": self.subject_attribute,
            },
            "output_contract_factory": self.output_contract_factory.manifest_record(),
            "runner": self.runner.manifest_record(),
            "implementation_modules": list(self.implementation_modules),
        }


_SHARED_IMPLEMENTATION_MODULES = (
    "smartchem.category",
    "smartchem.contracts",
    "smartchem.diagnosis",
    "smartchem.ledger",
    "smartchem.oracle.base",
    "smartchem.oracle.caching",
    "smartchem.oracle.persistent",
    "smartchem.program",
    "smartchem.runtime_registry",
    "smartchem.thermo",
)

_DESCRIPTORS = (
    ExecutorDescriptor(
        executor_id="smartchem.program/reaction-energy-v1",
        resolved_container=TypeReference("smartchem.program", "ResolvedProgram"),
        subject_type=TypeReference("smartchem.category", "Reaction"),
        subject_attribute="reaction",
        output_contract_factory=FunctionReference(
            "smartchem.program",
            "_default_output_contract",
        ),
        runner=FunctionReference("smartchem.program", "_execute_reaction_energy"),
        implementation_modules=_SHARED_IMPLEMENTATION_MODULES,
    ),
    ExecutorDescriptor(
        executor_id="smartchem.water_wave/shallow-water-horizon-v1",
        resolved_container=TypeReference("smartchem.program", "ResolvedDomainProgram"),
        subject_type=TypeReference("smartchem.water_wave_domain", "WaterWaveSpec"),
        subject_attribute="subject",
        output_contract_factory=FunctionReference(
            "smartchem.water_wave",
            "_default_output_contract",
        ),
        runner=FunctionReference(
            "smartchem.water_wave",
            "_execute_water_wave_horizon",
        ),
        implementation_modules=tuple(sorted((
            *_SHARED_IMPLEMENTATION_MODULES,
            "smartchem.water_wave",
            "smartchem.water_wave_domain",
        ))),
    ),
    ExecutorDescriptor(
        executor_id="smartchem.water_wave/finite-section-compatibility-v2",
        resolved_container=TypeReference("smartchem.program", "ResolvedDomainProgram"),
        subject_type=TypeReference(
            "smartchem.water_wave_validation_domain",
            "WaterWaveValidationSpec",
        ),
        subject_attribute="subject",
        output_contract_factory=FunctionReference(
            "smartchem.water_wave_validation",
            "_default_output_contract",
        ),
        runner=FunctionReference(
            "smartchem.water_wave_validation",
            "_execute_water_wave_validation",
        ),
        implementation_modules=tuple(sorted((
            *_SHARED_IMPLEMENTATION_MODULES,
            "smartchem.water_wave_validation",
            "smartchem.water_wave_validation_domain",
        ))),
    ),
    ExecutorDescriptor(
        executor_id="smartchem.human_isotope/identifiability-v1",
        resolved_container=TypeReference("smartchem.program", "ResolvedDomainProgram"),
        subject_type=TypeReference("smartchem.human_isotope_domain", "HumanIsotopeSpec"),
        subject_attribute="subject",
        output_contract_factory=FunctionReference(
            "smartchem.human_isotope",
            "_default_output_contract",
        ),
        runner=FunctionReference(
            "smartchem.human_isotope",
            "_execute_human_isotope_identifiability",
        ),
        implementation_modules=tuple(sorted((
            *_SHARED_IMPLEMENTATION_MODULES,
            "smartchem.human_isotope",
            "smartchem.human_isotope_domain",
        ))),
    ),
)

_BY_EXECUTOR_ID = MappingProxyType({
    descriptor.executor_id: descriptor
    for descriptor in _DESCRIPTORS
})

if len(_BY_EXECUTOR_ID) != len(_DESCRIPTORS):  # pragma: no cover - import-time invariant
    raise RuntimeError("runtime registry contains duplicate executor IDs")


def executor_ids() -> tuple[str, ...]:
    """Return the exact closed set of shipped executor IDs."""
    return tuple(sorted(_BY_EXECUTOR_ID))


def descriptor_for(executor_id: str) -> ExecutorDescriptor:
    """Look up one shipped executor or reject the unknown ID."""
    try:
        return _BY_EXECUTOR_ID[executor_id]
    except (KeyError, TypeError) as error:
        raise KeyError(f"no runtime is registered for executor_id {executor_id!r}") from error


def extract_subject(executor_id: str, resolved: object) -> object:
    return descriptor_for(executor_id).extract_subject(resolved)


def output_contract_error(executor_id: str, contract: object) -> str | None:
    return descriptor_for(executor_id).output_contract_error(contract)


def validate_output_contract(executor_id: str, contract: object) -> None:
    descriptor_for(executor_id).validate_output_contract(contract)


def resolve_runner(executor_id: str) -> Callable[..., object]:
    return descriptor_for(executor_id).resolve_runner()


def semantic_manifest() -> dict[str, object]:
    """Return a detached, JSON-compatible snapshot of registry semantics."""
    return {
        "schema": _MANIFEST_SCHEMA,
        "executors": [
            descriptor.manifest_record()
            for descriptor in sorted(_DESCRIPTORS, key=lambda item: item.executor_id)
        ],
    }


def semantic_manifest_digest() -> str:
    """Return a deterministic SHA-256 identity for all registry semantics."""
    encoded = json.dumps(
        semantic_manifest(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
