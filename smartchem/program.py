"""
The first typed simulation-program seam and its narrow chemistry vertical.

This is deliberately not a general simulator.  It makes the approval boundary and result
lineage real for three narrow calculations: a closed conserving reaction's endpoint energy,
a prescribed-background shallow-water characteristic diagnostic, and a structural
human-isotope identifiability diagnostic.  The general records are present so later domains
do not have to smuggle their meaning into strings; none of these verticals licenses broader
chemistry, fluid dynamics, literal-gravity claims, or human mortality prediction.

The governing rule is that execution accepts an :class:`ApprovedPlan`, never a raw request.
Changing an input, model, solver, calculation setting, obligation, output, tolerance, support,
or retention rule changes the plan digest and invalidates the approval.  A timeout/resource
wall becomes ``INCOMPLETE`` with a durable artifact inventory; it never becomes a successful
calculation with fewer outputs.

Python object capabilities are an API boundary, not a hostile-process security mechanism.
The private construction token prevents ordinary accidental bypass; cryptographic authority
and multi-user identity are outside this local library's present scope.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable
from uuid import uuid4

try:
    import resource
except ImportError:  # pragma: no cover - non-POSIX fallback
    resource = None

from .category import Config, Molecule, Reaction, conserves, reaction_residue
from .contracts import (
    ClaimKind,
    Digestible,
    EvidenceStatus,
    ExecutionLane,
    ObligationOutcome,
    ObligationResult,
    ObligationStage,
    RunStatus,
    ValidityObligation,
    canonical_digest,
    freeze_semantic_value,
    oracle_implementation_digest,
)
from .diagnosis import diagnose
from .oracle.base import Estimate
from .oracle.caching import CachingOracle
from .oracle.persistent import species_signature
from .structure_ir import (
    StructureAttachment,
    structure_attachment_for_subject,
    validate_structure_attachment,
)
from .thermo import reaction_energy

__all__ = [
    "Adapter",
    "Approval",
    "ApprovedPlan",
    "Artifact",
    "AssemblyEvidence",
    "AssemblyHypothesis",
    "AssemblySpec",
    "Boundary",
    "CalculationSpec",
    "CalibrationSpec",
    "CandidatePlan",
    "Certificate",
    "ClaimScope",
    "Component",
    "Connection",
    "EquivalenceContract",
    "ExecutionReport",
    "Identity",
    "Invariant",
    "ModelPatch",
    "ModelSpec",
    "ObservableRequest",
    "ObservableValue",
    "OutputContract",
    "PhysicalIR",
    "Port",
    "Quantity",
    "ReactionResidueTransform",
    "ResolvedDomainProgram",
    "ResolvedProgram",
    "Reservoir",
    "RunJournal",
    "RunRecord",
    "RuntimeLimits",
    "SimulationRequest",
    "SimulationResult",
    "SolverSpec",
    "SourceProgram",
    "SourceTheory",
    "StructuredObservableValue",
    "TargetIntent",
    "Transform",
    "TransportEvidence",
    "TransportMap",
    "approve",
    "compile_reaction_energy",
    "compile_session_reaction_energy",
    "execute",
    "record_approval",
]


def _nonempty(value: object, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _strings(values: tuple[str, ...], name: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError(f"{name} must contain non-empty strings")


def _unique(
    values: tuple[object, ...], key: Callable[[object], object], name: str
) -> None:
    seen = [key(value) for value in values]
    if len(seen) != len(set(seen)):
        raise ValueError(f"{name} must be unique")


def _compiler_source_paths() -> tuple[Path, ...]:
    """Return the closed source manifest that can affect compiler/runtime semantics.

    The first compiler seam listed a handful of files manually.  That was too weak:
    chemistry execution also depends on category, diagnosis, thermochemistry, and oracle
    adapter code.  Over-invalidation is safer than allowing an approved plan to survive a
    material implementation change, so the narrow local runtime binds every shipped Python
    module of THIS package.

    0.9.5 (S12): the manifest is the package's own ``.py`` files and nothing else.  It used
    to also fold in ``<package parent>/pyproject.toml`` when one existed -- present in a
    source checkout, absent beside ``site-packages/smartchem`` -- so byte-identical code
    digested differently from a checkout and from an installed wheel (and a stray
    ``site-packages/pyproject.toml`` would have moved it).  Nothing ambient may enter.
    """
    package = Path(__file__).resolve().parent
    return tuple(
        sorted(package.rglob("*.py"), key=lambda item: item.relative_to(package).as_posix())
    )


def _compiler_implementation_digest() -> str:
    """Bind approval to the complete shipped compiler/runtime source manifest.

    Preimage: for each package ``.py`` file (sorted, path relative to the package root),
    ``relpath \\0 sha256(content)``; then the declared ``smartchem.__version__``.
    """
    from . import __version__

    digest = hashlib.sha256()
    root = Path(__file__).resolve().parent
    for path in _compiler_source_paths():
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    digest.update(b"\0version\0")
    digest.update(__version__.encode("utf-8"))
    return digest.hexdigest()


_REACTION_EXECUTOR = "smartchem.program/reaction-energy-v1"
_WATER_WAVE_EXECUTOR = "smartchem.water_wave/shallow-water-horizon-v1"
_WATER_WAVE_VALIDATION_EXECUTOR = "smartchem.water_wave/finite-section-compatibility-v2"
_WATER_WAVE_CONTINUOUS_EXECUTOR = (
    "smartchem.water_wave_continuous/manufactured-steady-v1"
)
_HUMAN_ISOTOPE_EXECUTOR = "smartchem.human_isotope/identifiability-v1"
_HUMAN_SURVIVAL_EXECUTOR = (
    "smartchem.human_survival/synthetic-weibull-interval-recovery-v1"
)
_ISING_LATTICE_GAS_EXECUTOR = "smartchem.ising_lattice_gas/finite-c3-equilibrium-map-v1"
_RESISTIVE_DC_EXECUTOR = "smartchem.resistive_dc/exact-relation-sparse-mna-v1"
_RLC_AC_EXECUTOR = "smartchem.rlc_ac/positive-frequency-passive-rlc-v1"
_RUNTIME_DISPATCH_TOKEN = object()


def _require_runtime_dispatch(token: object) -> None:
    """Keep registry runners behind :func:`execute`'s validated dispatch path."""
    if token is not _RUNTIME_DISPATCH_TOKEN:
        raise ValueError(
            "runtime runners are internal capabilities; dispatch through smartchem.execute"
        )


def _executor_observables(executor_id: str) -> frozenset[str]:
    """Return the exact output capability of one closed-world registry entry."""
    from .runtime_registry import descriptor_for

    try:
        contract = descriptor_for(executor_id).default_output_contract()
    except KeyError as error:
        raise ValueError(str(error)) from error
    return frozenset(contract.observable_ids)


def _executor_contract_error(
    executor_id: str,
    contract: "OutputContract",
) -> str | None:
    """Return why the narrow executor cannot honor this semantic output contract."""
    from .runtime_registry import output_contract_error

    try:
        return output_contract_error(executor_id, contract)
    except KeyError as error:
        raise ValueError(str(error)) from error


@dataclass(frozen=True)
class Quantity(Digestible):
    value: float
    dimension: str
    unit: str
    frame: str = ""
    uncertainty: float | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("value must be a real scalar")
        if not math.isfinite(float(self.value)):
            raise ValueError("value must be finite")
        object.__setattr__(self, "value", float(self.value))
        _nonempty(self.dimension, "dimension")
        _nonempty(self.unit, "unit")
        if self.uncertainty is not None:
            if isinstance(self.uncertainty, bool) or not isinstance(
                self.uncertainty, (int, float)
            ):
                raise TypeError("uncertainty must be a real scalar or None")
            if self.uncertainty < 0:
                raise ValueError("uncertainty must be non-negative")
            if not math.isfinite(float(self.uncertainty)):
                raise ValueError("uncertainty must be finite")
            object.__setattr__(self, "uncertainty", float(self.uncertainty))


@dataclass(frozen=True)
class Identity(Digestible):
    stable_id: str
    kind: str
    state: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.stable_id, "stable_id")
        _nonempty(self.kind, "kind")
        if not isinstance(self.state, tuple):
            raise TypeError("state must be a tuple of key/value pairs")
        keys: list[str] = []
        for item in self.state:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("state must contain (key, value) pairs")
            key, value = item
            _nonempty(key, "state key")
            if not isinstance(value, str):
                raise TypeError("state values must be strings")
            keys.append(key)
        if len(keys) != len(set(keys)):
            raise ValueError("state keys must be unique")


@dataclass(frozen=True)
class Port(Digestible):
    port_id: str
    component_id: str
    variable: str
    dimension: str
    orientation: str
    connection_type: str

    def __post_init__(self) -> None:
        for name in (
            "port_id",
            "component_id",
            "variable",
            "dimension",
            "orientation",
            "connection_type",
        ):
            _nonempty(getattr(self, name), name)


@dataclass(frozen=True)
class Component(Digestible):
    component_id: str
    kind: str
    identity: Identity
    ports: tuple[Port, ...] = ()
    parameters: tuple[Quantity, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.component_id, "component_id")
        _nonempty(self.kind, "kind")
        if type(self.identity) is not Identity:
            raise TypeError("identity must be an Identity")
        if type(self.ports) is not tuple or type(self.parameters) is not tuple:
            raise TypeError("ports and parameters must be tuples")
        if any(type(port) is not Port for port in self.ports):
            raise TypeError("ports must contain Port values")
        if any(type(parameter) is not Quantity for parameter in self.parameters):
            raise TypeError("parameters must contain Quantity values")
        _unique(self.ports, lambda port: port.port_id, "component port IDs")
        if any(port.component_id != self.component_id for port in self.ports):
            raise ValueError("every port must name its owning component")


@dataclass(frozen=True)
class Connection(Digestible):
    connection_id: str
    port_ids: tuple[str, ...]
    law: str

    def __post_init__(self) -> None:
        _nonempty(self.connection_id, "connection_id")
        _strings(self.port_ids, "port_ids")
        if len(self.port_ids) < 2:
            raise ValueError("a connection requires at least two ports")
        _nonempty(self.law, "law")


@dataclass(frozen=True)
class Reservoir(Digestible):
    reservoir_id: str
    exchanges: tuple[str, ...]
    state: tuple[Quantity, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.reservoir_id, "reservoir_id")
        _strings(self.exchanges, "exchanges")
        if type(self.state) is not tuple:
            raise TypeError("state must be a tuple")
        if any(type(item) is not Quantity for item in self.state):
            raise TypeError("state must contain Quantity values")


@dataclass(frozen=True)
class Boundary(Digestible):
    boundary_id: str
    target_ids: tuple[str, ...]
    condition: str

    def __post_init__(self) -> None:
        _nonempty(self.boundary_id, "boundary_id")
        _strings(self.target_ids, "target_ids")
        _nonempty(self.condition, "condition")


@dataclass(frozen=True)
class SourceTheory(Digestible):
    name: str
    axioms: tuple[str, ...]
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.name, "name")
        _strings(self.axioms, "axioms")
        _strings(self.provenance, "provenance")


@dataclass(frozen=True)
class TargetIntent(Digestible):
    statement: str
    target_scale: str
    requested_meaning: str

    def __post_init__(self) -> None:
        for name in ("statement", "target_scale", "requested_meaning"):
            _nonempty(getattr(self, name), name)


@dataclass(frozen=True)
class TransportMap(Digestible):
    source_theory_digest: str
    target_intent_digest: str
    preserved: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    discarded: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.source_theory_digest, "source_theory_digest")
        _nonempty(self.target_intent_digest, "target_intent_digest")
        for name in ("preserved", "modified", "discarded", "unknown"):
            _strings(getattr(self, name), name)


@dataclass(frozen=True)
class ClaimScope(Digestible):
    kind: ClaimKind
    referent: str
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ClaimKind):
            raise TypeError("kind must be a ClaimKind")
        _nonempty(self.referent, "referent")
        _strings(self.exclusions, "exclusions")


@dataclass(frozen=True)
class AssemblySpec(Digestible):
    name: str
    granularity: str
    rules: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty(self.name, "name")
        _nonempty(self.granularity, "granularity")
        _strings(self.rules, "rules")


@dataclass(frozen=True)
class AssemblyHypothesis(Digestible):
    spec: AssemblySpec
    missing_evidence: tuple[str, ...]
    falsifiers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, AssemblySpec):
            raise TypeError("spec must be an AssemblySpec")
        _strings(self.missing_evidence, "missing_evidence")
        _strings(self.falsifiers, "falsifiers")


@dataclass(frozen=True)
class TransportEvidence(Digestible):
    transport_digest: str
    regime_predicates: tuple[str, ...]
    evidence: tuple[str, ...]
    remaining_obligations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.transport_digest, "transport_digest")
        for name in ("regime_predicates", "evidence", "remaining_obligations"):
            _strings(getattr(self, name), name)


@dataclass(frozen=True)
class AssemblyEvidence(Digestible):
    assembly_digest: str
    evidence: tuple[str, ...]
    remaining_obligations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.assembly_digest, "assembly_digest")
        _strings(self.evidence, "evidence")
        _strings(self.remaining_obligations, "remaining_obligations")


@dataclass(frozen=True)
class ModelPatch(Digestible):
    name: str
    changes: tuple[str, ...]
    casualties: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonempty(self.name, "name")
        _strings(self.changes, "changes")
        _strings(self.casualties, "casualties")


@dataclass(frozen=True)
class CalibrationSpec(Digestible):
    population: str
    protocol: str
    endpoints: tuple[str, ...]
    identifiability: str
    validation_split: str
    uncertainty_treatment: str

    def __post_init__(self) -> None:
        for name in (
            "population",
            "protocol",
            "identifiability",
            "validation_split",
            "uncertainty_treatment",
        ):
            _nonempty(getattr(self, name), name)
        _strings(self.endpoints, "endpoints")


@dataclass(frozen=True)
class Invariant(Digestible):
    name: str
    statement: str
    scope: str
    checker_id: str

    def __post_init__(self) -> None:
        for name in ("name", "statement", "scope", "checker_id"):
            _nonempty(getattr(self, name), name)


@dataclass(frozen=True)
class ModelSpec(Digestible):
    name: str
    equations: tuple[str, ...]
    assumptions: tuple[str, ...]
    valid_if: tuple[str, ...]
    postconditions: tuple[str, ...]
    conserved: tuple[str, ...]
    version: str

    def __post_init__(self) -> None:
        _nonempty(self.name, "name")
        _nonempty(self.version, "version")
        for name in (
            "equations",
            "assumptions",
            "valid_if",
            "postconditions",
            "conserved",
        ):
            _strings(getattr(self, name), name)


@dataclass(frozen=True)
class SolverSpec(Digestible):
    name: str
    algorithm: str
    version: str
    tolerances: tuple[tuple[str, float], ...] = ()
    stopping_policy: str = "backend-declared"
    reproducibility: str = "backend-declared"

    def __post_init__(self) -> None:
        for name in (
            "name",
            "algorithm",
            "version",
            "stopping_policy",
            "reproducibility",
        ):
            _nonempty(getattr(self, name), name)
        if not isinstance(self.tolerances, tuple):
            raise TypeError("tolerances must be a tuple")
        names: list[str] = []
        for item in self.tolerances:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("tolerances must contain (name, value) pairs")
            name, value = item
            _nonempty(name, "tolerance name")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise ValueError("tolerances must be non-negative real numbers")
            names.append(name)
        if len(names) != len(set(names)):
            raise ValueError("tolerance names must be unique")


@dataclass(frozen=True)
class CalculationSpec(Digestible):
    engine_class: str
    engine_name: str
    settings: object
    implementation_digest: str

    def __post_init__(self) -> None:
        for name in ("engine_class", "engine_name", "implementation_digest"):
            _nonempty(getattr(self, name), name)
        # Re-run the canonical encoder at the boundary so a hand-built spec cannot smuggle
        # a mutable/unsupported object into an approval identity.
        canonical_digest(self.settings)

    @classmethod
    def from_oracle(cls, oracle: object) -> "CalculationSpec":
        provider = getattr(oracle, "calculation_spec", None)
        if not callable(provider):
            raise TypeError("an executable oracle must expose calculation_spec()")
        settings = freeze_semantic_value(provider())
        return cls(
            engine_class=f"{type(oracle).__module__}.{type(oracle).__qualname__}",
            engine_name=getattr(oracle, "name", type(oracle).__qualname__),
            settings=settings,
            implementation_digest=oracle_implementation_digest(oracle),
        )


@dataclass(frozen=True)
class Adapter(Digestible):
    name: str
    source_representation: str
    target_representation: str
    exchanged_observables: tuple[str, ...]
    validity: tuple[str, ...]
    discrepancy: str

    def __post_init__(self) -> None:
        for name in (
            "name",
            "source_representation",
            "target_representation",
            "discrepancy",
        ):
            _nonempty(getattr(self, name), name)
        _strings(self.exchanged_observables, "exchanged_observables")
        _strings(self.validity, "validity")


@dataclass(frozen=True)
class ObservableRequest(Digestible):
    observable_id: str
    kind: str
    unit: str
    support: str
    resolution: str
    precision: str
    coverage: str
    diagnostics: tuple[str, ...] = ()
    retention: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "observable_id",
            "kind",
            "unit",
            "support",
            "resolution",
            "precision",
            "coverage",
        ):
            _nonempty(getattr(self, name), name)
        _strings(self.diagnostics, "diagnostics")
        _strings(self.retention, "retention")


@dataclass(frozen=True)
class OutputContract(Digestible):
    observables: tuple[ObservableRequest, ...]
    diagnostics: tuple[str, ...]
    retention: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observables, tuple) or not self.observables:
            raise ValueError("observables must be a non-empty tuple")
        if any(not isinstance(item, ObservableRequest) for item in self.observables):
            raise TypeError("observables must contain ObservableRequest values")
        _unique(self.observables, lambda item: item.observable_id, "observable IDs")
        _strings(self.diagnostics, "diagnostics")
        _strings(self.retention, "retention")

    @property
    def observable_ids(self) -> tuple[str, ...]:
        return tuple(item.observable_id for item in self.observables)


@dataclass(frozen=True)
class EquivalenceContract(Digestible):
    relation: str
    numeric_tolerances: tuple[tuple[str, float], ...]
    ordering: str
    rng_policy: str
    checkpoint_policy: str
    allowed_provenance_differences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("relation", "ordering", "rng_policy", "checkpoint_policy"):
            _nonempty(getattr(self, name), name)
        SolverSpec(
            "equivalence-validation",
            "none",
            "1",
            self.numeric_tolerances,
        )
        _strings(self.allowed_provenance_differences, "allowed_provenance_differences")


@dataclass(frozen=True)
class Transform(Digestible):
    name: str
    exactness_class: str
    input_model_digest: str
    output_model_digest: str
    applicability: tuple[str, ...]
    evidence: tuple[str, ...]
    casualties: tuple[str, ...]
    output_contract_digest: str = field(default="", kw_only=True)
    equivalence_contract_digest: str = field(default="", kw_only=True)

    def __post_init__(self) -> None:
        for name in (
            "name",
            "exactness_class",
            "input_model_digest",
            "output_model_digest",
        ):
            _nonempty(getattr(self, name), name)
        for name in ("applicability", "evidence", "casualties"):
            _strings(getattr(self, name), name)
        for name in ("output_contract_digest", "equivalence_contract_digest"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")


@dataclass(frozen=True)
class ReactionResidueTransform(Transform):
    """Class-A spectator cancellation proof object for the separable energy model."""

    original_reaction_digest: str
    residual_left: Config
    residual_right: Config
    eliminated_species: tuple[tuple[Molecule, int], ...]
    workset: tuple[Molecule, ...]
    verifier_id: str

    def __post_init__(self) -> None:
        super().__post_init__()
        _nonempty(self.original_reaction_digest, "original_reaction_digest")
        if (
            type(self.residual_left) is not Config
            or type(self.residual_right) is not Config
        ):
            raise TypeError(
                "reaction-residue transform requires exact residual Config values"
            )
        if not isinstance(self.eliminated_species, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or type(item[0]) is not Molecule
            or type(item[1]) is not int
            or item[1] < 1
            for item in self.eliminated_species
        ):
            raise TypeError(
                "eliminated_species must contain exact (Molecule, positive int) pairs"
            )
        if len({item[0] for item in self.eliminated_species}) != len(
            self.eliminated_species
        ):
            raise ValueError("eliminated species identities must be unique")
        if not isinstance(self.workset, tuple) or any(
            type(item) is not Molecule for item in self.workset
        ):
            raise TypeError("workset must contain exact Molecule values")
        if len(set(self.workset)) != len(self.workset):
            raise ValueError("workset species must be unique")
        _nonempty(self.verifier_id, "verifier_id")


@dataclass(frozen=True)
class SourceProgram(Digestible):
    text: str
    spans: tuple[str, ...] = ()
    scientist: str = "unspecified"

    def __post_init__(self) -> None:
        _nonempty(self.text, "text")
        _strings(self.spans, "spans")
        _nonempty(self.scientist, "scientist")


@dataclass(frozen=True)
class ResolvedProgram(Digestible):
    source_digest: str
    reaction: Reaction
    target: TargetIntent
    source_theory: SourceTheory
    shepherd_session_digest: str

    def __post_init__(self) -> None:
        _nonempty(self.source_digest, "source_digest")
        _nonempty(self.shepherd_session_digest, "shepherd_session_digest")
        if not isinstance(self.reaction, Reaction):
            raise TypeError("reaction must be a Reaction")


@dataclass(frozen=True)
class ResolvedDomainProgram(Digestible):
    """A non-chemical semantic subject closed by a typed shepherd session."""

    source_digest: str
    subject: object
    target: TargetIntent
    source_theory: SourceTheory
    shepherd_session_digest: str

    def __post_init__(self) -> None:
        _nonempty(self.source_digest, "source_digest")
        _nonempty(self.shepherd_session_digest, "shepherd_session_digest")
        if not isinstance(self.target, TargetIntent):
            raise TypeError("target must be a TargetIntent")
        if not isinstance(self.source_theory, SourceTheory):
            raise TypeError("source_theory must be a SourceTheory")
        canonical_digest(self.subject)


@dataclass(frozen=True)
class PhysicalIR(Digestible):
    resolved_digest: str
    components: tuple[Component, ...]
    connections: tuple[Connection, ...]
    reservoirs: tuple[Reservoir, ...]
    boundaries: tuple[Boundary, ...]
    models: tuple[ModelSpec, ...]
    adapters: tuple[Adapter, ...]
    invariants: tuple[Invariant, ...]
    transport_maps: tuple[TransportMap, ...]
    transport_evidence: tuple[TransportEvidence, ...]
    assemblies: tuple[AssemblySpec | AssemblyHypothesis, ...]
    assembly_evidence: tuple[AssemblyEvidence, ...]
    claim_scope: ClaimScope
    evidence_status: EvidenceStatus
    calibrations: tuple[CalibrationSpec, ...] = ()
    model_patches: tuple[ModelPatch, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.resolved_digest, "resolved_digest")
        for name in (
            "components",
            "connections",
            "reservoirs",
            "boundaries",
            "models",
            "adapters",
            "invariants",
            "transport_maps",
            "transport_evidence",
            "assemblies",
            "assembly_evidence",
            "calibrations",
            "model_patches",
        ):
            if type(getattr(self, name)) is not tuple:
                raise TypeError(f"{name} must be a tuple")
        if not self.models:
            raise ValueError("PhysicalIR requires at least one model")
        member_types = (
            ("components", Component),
            ("connections", Connection),
            ("reservoirs", Reservoir),
            ("boundaries", Boundary),
            ("models", ModelSpec),
            ("adapters", Adapter),
            ("invariants", Invariant),
            ("transport_maps", TransportMap),
            ("transport_evidence", TransportEvidence),
            ("assembly_evidence", AssemblyEvidence),
        )
        for name, expected in member_types:
            if any(type(item) is not expected for item in getattr(self, name)):
                raise TypeError(f"{name} must contain {expected.__name__} values")
        if any(
            type(item) not in (AssemblySpec, AssemblyHypothesis)
            for item in self.assemblies
        ):
            raise TypeError(
                "assemblies must contain AssemblySpec or AssemblyHypothesis values"
            )
        _unique(self.components, lambda item: item.component_id, "component IDs")
        _unique(self.connections, lambda item: item.connection_id, "connection IDs")
        _unique(self.reservoirs, lambda item: item.reservoir_id, "reservoir IDs")
        _unique(self.boundaries, lambda item: item.boundary_id, "boundary IDs")
        component_ids = {item.component_id for item in self.components}
        ports = tuple(port for component in self.components for port in component.ports)
        _unique(ports, lambda item: item.port_id, "PhysicalIR port IDs")
        port_by_id = {item.port_id: item for item in ports}
        targets = component_ids | set(port_by_id)
        for connection in self.connections:
            if len(set(connection.port_ids)) != len(connection.port_ids):
                raise ValueError(
                    "a connection cannot name the same port more than once"
                )
            try:
                connected = tuple(port_by_id[item] for item in connection.port_ids)
            except KeyError as error:
                raise ValueError(
                    f"connection {connection.connection_id!r} names an unknown port {error.args[0]!r}"
                ) from error
            if len({item.dimension for item in connected}) != 1:
                raise ValueError("connected ports must have one shared dimension")
            if len({item.connection_type for item in connected}) != 1:
                raise ValueError("connected ports must have one shared connection_type")
        for boundary in self.boundaries:
            unknown = sorted(set(boundary.target_ids) - targets)
            if unknown:
                raise ValueError(
                    f"boundary {boundary.boundary_id!r} names unknown target(s): "
                    + ", ".join(unknown)
                )
        for reservoir in self.reservoirs:
            unknown = sorted(set(reservoir.exchanges) - targets)
            if unknown:
                raise ValueError(
                    f"reservoir {reservoir.reservoir_id!r} names unknown exchange target(s): "
                    + ", ".join(unknown)
                )
        transport_digests = tuple(item.digest for item in self.transport_maps)
        assembly_digests = tuple(item.digest for item in self.assemblies)
        if len(transport_digests) != len(set(transport_digests)):
            raise ValueError("transport maps must have unique digests")
        if len(assembly_digests) != len(set(assembly_digests)):
            raise ValueError("assemblies must have unique digests")
        evidence_digests = tuple(
            item.transport_digest for item in self.transport_evidence
        )
        assembly_evidence_digests = tuple(
            item.assembly_digest for item in self.assembly_evidence
        )
        if len(evidence_digests) != len(set(evidence_digests)):
            raise ValueError(
                "transport evidence must target each transport at most once"
            )
        if len(assembly_evidence_digests) != len(set(assembly_evidence_digests)):
            raise ValueError("assembly evidence must target each assembly at most once")
        if set(evidence_digests) != set(transport_digests):
            raise ValueError(
                "transport evidence must target every and only declared transport"
            )
        if set(assembly_evidence_digests) != set(assembly_digests):
            raise ValueError(
                "assembly evidence must target every and only declared assembly"
            )
        if type(self.claim_scope) is not ClaimScope:
            raise TypeError("claim_scope must be a ClaimScope")
        if type(self.evidence_status) is not EvidenceStatus:
            raise TypeError("evidence_status must be an EvidenceStatus")
        if any(
            type(calibration) is not CalibrationSpec
            for calibration in self.calibrations
        ):
            raise TypeError("calibrations must contain CalibrationSpec values")
        if any(type(patch) is not ModelPatch for patch in self.model_patches):
            raise TypeError("model_patches must contain ModelPatch values")
        if any(
            type(assembly) is AssemblyHypothesis for assembly in self.assemblies
        ) and self.evidence_status not in (
            EvidenceStatus.EXPERIMENTAL,
            EvidenceStatus.STRUCTURAL_TOY,
            EvidenceStatus.UNSUPPORTED,
        ):
            raise ValueError(
                "an AssemblyHypothesis carries missing evidence and cannot have calibrated "
                "or established evidence status"
            )


@dataclass(frozen=True)
class SimulationRequest(Digestible):
    source: SourceProgram
    resolved: ResolvedProgram | ResolvedDomainProgram
    physical_ir: PhysicalIR
    output_contract: OutputContract
    equivalence_contract: EquivalenceContract
    obligations: tuple[ValidityObligation, ...]

    def __post_init__(self) -> None:
        if type(self.source) is not SourceProgram:
            raise TypeError("source must be a SourceProgram")
        if type(self.resolved) not in (ResolvedProgram, ResolvedDomainProgram):
            raise TypeError(
                "resolved must be a ResolvedProgram or ResolvedDomainProgram"
            )
        if type(self.physical_ir) is not PhysicalIR:
            raise TypeError("physical_ir must be a PhysicalIR")
        if type(self.output_contract) is not OutputContract:
            raise TypeError("output_contract must be an OutputContract")
        if type(self.equivalence_contract) is not EquivalenceContract:
            raise TypeError("equivalence_contract must be an EquivalenceContract")
        if self.resolved.source_digest != self.source.digest:
            raise ValueError("resolved program is not bound to this source")
        if self.physical_ir.resolved_digest != self.resolved.digest:
            raise ValueError("PhysicalIR is not bound to this resolved program")
        for transport in self.physical_ir.transport_maps:
            if transport.source_theory_digest != self.resolved.source_theory.digest:
                raise ValueError(
                    "transport map is not bound to this resolved source theory"
                )
            if transport.target_intent_digest != self.resolved.target.digest:
                raise ValueError(
                    "transport map is not bound to this resolved target intent"
                )
        if type(self.obligations) is not tuple:
            raise TypeError("obligations must be a tuple")
        if any(type(item) is not ValidityObligation for item in self.obligations):
            raise TypeError("obligations must contain ValidityObligation values")
        _unique(self.obligations, lambda item: item.name, "obligation names")


@dataclass(frozen=True)
class RuntimeLimits(Digestible):
    """Approved hard stops.

    ``wall_seconds`` is elapsed time from durable run creation. ``memory_bytes`` is an
    absolute process peak-RSS ceiling (not an incremental allocation budget).  Both are
    checked before and after each indivisible oracle call.  The current oracle protocol has
    no cancellation hook, so a single call may cross a limit before the runtime can observe
    it; its completed artifact is then retained and quarantined in an ``INCOMPLETE`` run.
    """

    max_species_calls: int | None = None
    wall_seconds: float | None = None
    memory_bytes: int | None = None
    max_engine_calls: int | None = None

    def __post_init__(self) -> None:
        for name in ("max_species_calls", "max_engine_calls", "memory_bytes"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None")
        if self.wall_seconds is not None and (
            isinstance(self.wall_seconds, bool)
            or not isinstance(self.wall_seconds, (int, float))
            or not math.isfinite(float(self.wall_seconds))
            or self.wall_seconds < 0
        ):
            raise ValueError("wall_seconds must be a non-negative real number or None")


@dataclass(frozen=True)
class CandidatePlan(Digestible):
    request: SimulationRequest
    model: ModelSpec
    solver: SolverSpec
    calculation: CalculationSpec
    compiler_implementation_digest: str
    executor_id: str
    transforms: tuple[Transform, ...]
    predicted_resources: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]
    execution_lane: ExecutionLane
    limits: RuntimeLimits
    structure_attachment: StructureAttachment | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not SimulationRequest:
            raise TypeError("request must be a SimulationRequest")
        if type(self.model) is not ModelSpec:
            raise TypeError("model must be a ModelSpec")
        if type(self.solver) is not SolverSpec:
            raise TypeError("solver must be a SolverSpec")
        if type(self.calculation) is not CalculationSpec:
            raise TypeError("calculation must be a CalculationSpec")
        if type(self.limits) is not RuntimeLimits:
            raise TypeError("limits must be RuntimeLimits")
        if self.model not in self.request.physical_ir.models:
            raise ValueError("selected model is not present in the PhysicalIR")
        _nonempty(self.compiler_implementation_digest, "compiler_implementation_digest")
        _nonempty(self.executor_id, "executor_id")
        supported_outputs = _executor_observables(self.executor_id)
        from .runtime_registry import extract_subject

        try:
            subject = extract_subject(self.executor_id, self.request.resolved)
        except (KeyError, TypeError) as error:
            raise ValueError(str(error)) from error
        expected_structure = structure_attachment_for_subject(
            self.executor_id,
            subject,
        )
        if self.structure_attachment is None:
            object.__setattr__(self, "structure_attachment", expected_structure)
        elif type(self.structure_attachment) is not StructureAttachment:
            raise TypeError("structure_attachment must be an exact StructureAttachment")
        elif self.structure_attachment != expected_structure:
            raise ValueError(
                "structure_attachment differs from the exact subject/adapter observation"
            )
        if not isinstance(self.transforms, tuple):
            raise TypeError("transforms must be a tuple")
        if any(not isinstance(item, Transform) for item in self.transforms):
            raise TypeError("transforms must contain Transform values")
        if not isinstance(self.predicted_resources, tuple):
            raise TypeError("predicted_resources must be a tuple")
        resource_names: list[str] = []
        for item in self.predicted_resources:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError(
                    "predicted_resources must contain (name, estimate) pairs"
                )
            name, estimate = item
            _nonempty(name, "resource name")
            _nonempty(estimate, "resource estimate")
            resource_names.append(name)
        if len(resource_names) != len(set(resource_names)):
            raise ValueError("predicted resource names must be unique")
        _strings(self.blockers, "blockers")
        unsupported = sorted(
            set(self.request.output_contract.observable_ids) - supported_outputs
        )
        if unsupported and not self.blockers:
            raise ValueError(
                "candidate plan requests unsupported observables without a planning blocker: "
                + ", ".join(unsupported)
            )
        if not isinstance(self.execution_lane, ExecutionLane):
            raise TypeError("execution_lane must be an ExecutionLane")
        if (
            self.execution_lane is ExecutionLane.CERTIFIED
            and self.request.physical_ir.evidence_status
            in (
                EvidenceStatus.EXPERIMENTAL,
                EvidenceStatus.STRUCTURAL_TOY,
                EvidenceStatus.UNSUPPORTED,
            )
        ):
            raise ValueError(
                "uncertified evidence cannot enter the certified execution lane"
            )
        if self.execution_lane is ExecutionLane.CERTIFIED:
            ir = self.request.physical_ir
            if any(isinstance(item, AssemblyHypothesis) for item in ir.assemblies):
                raise ValueError(
                    "an AssemblyHypothesis cannot enter the certified lane"
                )
            transport_evidence = {
                item.transport_digest: item for item in ir.transport_evidence
            }
            assembly_evidence = {
                item.assembly_digest: item for item in ir.assembly_evidence
            }
            missing_transport = [
                item.digest
                for item in ir.transport_maps
                if item.digest not in transport_evidence
                or transport_evidence[item.digest].remaining_obligations
            ]
            missing_assembly = [
                item.digest
                for item in ir.assemblies
                if item.digest not in assembly_evidence
                or assembly_evidence[item.digest].remaining_obligations
            ]
            if missing_transport or missing_assembly:
                raise ValueError(
                    "certified execution requires closed transport and assembly evidence; "
                    f"transport={missing_transport}, assembly={missing_assembly}"
                )


_APPROVAL_RECORD_TOKEN = object()


@dataclass(frozen=True, init=False)
class Approval(Digestible):
    principal: str
    plan_digest: str
    scope: str
    approved_deltas: tuple[str, ...]
    timestamp: str

    def __init__(
        self,
        principal: str,
        plan_digest: str,
        scope: str,
        approved_deltas: tuple[str, ...],
        timestamp: str,
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _APPROVAL_RECORD_TOKEN:
            raise PermissionError("Approval can only be created by record_approval()")
        object.__setattr__(self, "principal", principal)
        object.__setattr__(self, "plan_digest", plan_digest)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "approved_deltas", approved_deltas)
        object.__setattr__(self, "timestamp", timestamp)
        for name in ("principal", "plan_digest", "scope", "timestamp"):
            _nonempty(getattr(self, name), name)
        _strings(self.approved_deltas, "approved_deltas")
        try:
            parsed = datetime.fromisoformat(self.timestamp)
        except ValueError as error:
            raise ValueError("timestamp must be ISO-8601") from error
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")


_APPROVAL_TOKEN = object()


@dataclass(frozen=True, init=False)
class ApprovedPlan(Digestible):
    plan: CandidatePlan
    approval: Approval
    approval_record_digest: str

    def __init__(
        self,
        plan: CandidatePlan,
        approval: Approval,
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _APPROVAL_TOKEN:
            raise PermissionError("ApprovedPlan can only be created by approve()")
        if type(plan) is not CandidatePlan:
            raise TypeError("plan must be a CandidatePlan")
        if type(approval) is not Approval:
            raise TypeError("approval must be an Approval")
        object.__setattr__(self, "plan", plan)
        object.__setattr__(self, "approval", approval)
        object.__setattr__(self, "approval_record_digest", approval.digest)


def record_approval(
    plan: CandidatePlan,
    principal: str,
    scope: str,
    *,
    approved_deltas: tuple[str, ...] = (),
    timestamp: str | None = None,
) -> Approval:
    """Record explicit authority for exactly this candidate-plan digest."""
    if type(plan) is not CandidatePlan:
        raise TypeError("plan must be a CandidatePlan")
    return Approval(
        principal=principal,
        plan_digest=plan.digest,
        scope=scope,
        approved_deltas=approved_deltas,
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        _token=_APPROVAL_RECORD_TOKEN,
    )


def approve(plan: CandidatePlan, approval: Approval) -> ApprovedPlan:
    if type(plan) is not CandidatePlan:
        raise TypeError("plan must be a CandidatePlan")
    if type(approval) is not Approval:
        raise TypeError("approval must be an Approval")
    if plan.blockers:
        raise ValueError(
            "a candidate with blockers cannot be approved: " + "; ".join(plan.blockers)
        )
    if approval.plan_digest != plan.digest:
        raise ValueError("approval does not name this candidate-plan digest")
    return ApprovedPlan(plan, approval, _token=_APPROVAL_TOKEN)


@dataclass(frozen=True)
class _ExecutionAdmissionSnapshot:
    """Pre-backend identity of every authority-bearing execution input."""

    plan_digest: str
    approval_digest: str
    approval_record_digest: str
    resolved_digest: str
    subject_digest: str
    calculation_digest: str
    compiler_implementation_digest: str


def _capture_execution_admission(
    approved: ApprovedPlan,
    subject: object,
) -> _ExecutionAdmissionSnapshot:
    """Freeze admission before any in-process backend callback can mutate it."""
    if type(approved) is not ApprovedPlan:
        raise TypeError("execution admission requires an exact ApprovedPlan")
    return _ExecutionAdmissionSnapshot(
        approved.plan.digest,
        approved.approval.digest,
        approved.approval_record_digest,
        canonical_digest(approved.plan.request.resolved),
        canonical_digest(subject),
        approved.plan.calculation.digest,
        approved.plan.compiler_implementation_digest,
    )


def _execution_admission_error(
    approved: ApprovedPlan,
    subject: object,
    expected: _ExecutionAdmissionSnapshot,
) -> str | None:
    """Name post-callback approval drift; return ``None`` only for exact identity."""
    if type(expected) is not _ExecutionAdmissionSnapshot:
        return "execution admission snapshot has the wrong exact type"
    try:
        current = _capture_execution_admission(approved, subject)
    except Exception as error:
        return (
            "approved execution identity is no longer digestible after backend callback: "
            f"{type(error).__name__}: {error}"
        )
    if current != expected:
        return (
            "approved execution identity changed during an in-process backend callback"
        )
    if approved.approval.plan_digest != approved.plan.digest:
        return "approval no longer names the admitted candidate plan"
    if approved.approval.digest != approved.approval_record_digest:
        return "approval record changed after execution admission"
    return None


@dataclass(frozen=True)
class Artifact(Digestible):
    artifact_id: str
    kind: str
    content_digest: str
    complete: bool
    quarantined: bool
    path: str = ""
    detail: str = ""
    payload: object | None = None

    def __post_init__(self) -> None:
        for name in ("artifact_id", "kind", "content_digest"):
            _nonempty(getattr(self, name), name)
        if type(self.complete) is not bool or type(self.quarantined) is not bool:
            raise TypeError("complete and quarantined must be booleans")
        if self.kind == "observable" and self.payload is None:
            raise ValueError(
                "a complete observable identity is insufficient: observable artifacts "
                "must retain a schema-checkable payload"
            )
        if self.payload is not None:
            if canonical_digest(self.payload) != self.content_digest:
                raise ValueError(
                    "content_digest must identify the retained artifact payload"
                )


@dataclass(frozen=True)
class RunRecord(Digestible):
    run_id: str
    plan_digest: str
    approval_digest: str
    status: RunStatus
    started_at: str
    updated_at: str
    backend: str
    cache_state: tuple[str, ...]
    artifacts: tuple[Artifact, ...]
    checkpoints: tuple[Artifact, ...]
    obligation_results: tuple[ObligationResult, ...]
    diagnostics: tuple[str, ...]
    failures: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "run_id",
            "plan_digest",
            "approval_digest",
            "started_at",
            "updated_at",
            "backend",
        ):
            _nonempty(getattr(self, name), name)
        for name in ("cache_state", "diagnostics", "failures"):
            _strings(getattr(self, name), name)
        for name in ("artifacts", "checkpoints", "obligation_results"):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be a tuple")
        if not isinstance(self.status, RunStatus):
            raise TypeError("status must be a RunStatus")
        result_digests = [
            result.obligation_digest for result in self.obligation_results
        ]
        if len(result_digests) != len(set(result_digests)):
            raise ValueError("a RunRecord cannot contain duplicate obligation results")

    @property
    def output_inventory(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                artifact.artifact_id.removeprefix("observable:")
                for artifact in self.artifacts
                if artifact.kind == "observable"
                and artifact.complete
                and not artifact.quarantined
            )
        )


@dataclass(frozen=True)
class ObservableValue(Digestible):
    observable_id: str
    value: float
    unit: str
    uncertainty: float
    method: str
    support: str
    seconds: float
    notes: str
    systematic_ev: float
    methods: tuple[str, ...]
    systematic_terms: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        for name in ("observable_id", "unit", "method", "support"):
            _nonempty(getattr(self, name), name)
        for name in ("value", "uncertainty", "seconds", "systematic_ev"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, float(value))
        if self.uncertainty < 0 or self.seconds < 0:
            raise ValueError("uncertainty and seconds must be non-negative")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")
        _strings(self.methods, "methods")
        if not isinstance(self.systematic_terms, tuple):
            raise TypeError("systematic_terms must be a tuple")
        for item in self.systematic_terms:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError(
                    "systematic_terms must contain (source, coefficient) pairs"
                )
            source, coefficient = item
            _nonempty(source, "systematic source")
            if (
                isinstance(coefficient, bool)
                or not isinstance(coefficient, (int, float))
                or not math.isfinite(float(coefficient))
            ):
                raise ValueError("systematic coefficients must be finite real numbers")


@dataclass(frozen=True)
class StructuredObservableValue(Digestible):
    """A complete non-scalar observable whose typed payload is retained verbatim."""

    observable_id: str
    payload: object
    unit: str
    method: str
    support: str
    seconds: float
    uncertainty_note: str
    notes: str = ""

    def __post_init__(self) -> None:
        for name in ("observable_id", "unit", "method", "support", "uncertainty_note"):
            _nonempty(getattr(self, name), name)
        if (
            isinstance(self.seconds, bool)
            or not isinstance(self.seconds, (int, float))
            or not math.isfinite(float(self.seconds))
            or self.seconds < 0
        ):
            raise ValueError("seconds must be a non-negative finite real number")
        object.__setattr__(self, "seconds", float(self.seconds))
        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")
        canonical_digest(self.payload)


@dataclass(frozen=True)
class Certificate(Digestible):
    source_digest: str
    request_digest: str
    plan_digest: str
    approval_digest: str
    calculation_digest: str
    compiler_implementation_digest: str
    run_id: str
    run_status: RunStatus
    claim_scope: ClaimScope
    evidence_status: EvidenceStatus
    validity_results: tuple[ObligationResult, ...]
    output_inventory: tuple[str, ...]
    casualties: tuple[str, ...]
    omissions: tuple[str, ...]
    failures: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "source_digest",
            "request_digest",
            "plan_digest",
            "approval_digest",
            "calculation_digest",
            "compiler_implementation_digest",
            "run_id",
        ):
            _nonempty(getattr(self, name), name)
        for name in ("output_inventory", "casualties", "omissions", "failures"):
            _strings(getattr(self, name), name)
        if not isinstance(self.validity_results, tuple) or any(
            not isinstance(result, ObligationResult) for result in self.validity_results
        ):
            raise TypeError(
                "validity_results must be a tuple of ObligationResult values"
            )
        _unique(
            self.validity_results,
            lambda result: result.obligation_digest,
            "certificate obligation results",
        )
        if not isinstance(self.run_status, RunStatus):
            raise TypeError("run_status must be a RunStatus")
        if not isinstance(self.claim_scope, ClaimScope):
            raise TypeError("claim_scope must be a ClaimScope")
        if not isinstance(self.evidence_status, EvidenceStatus):
            raise TypeError("evidence_status must be an EvidenceStatus")


@dataclass(frozen=True)
class SimulationResult(Digestible):
    run_id: str
    values: tuple[ObservableValue | StructuredObservableValue, ...]
    certificate_digest: str

    def __post_init__(self) -> None:
        _nonempty(self.run_id, "run_id")
        _nonempty(self.certificate_digest, "certificate_digest")
        if (
            not isinstance(self.values, tuple)
            or not self.values
            or any(
                not isinstance(value, (ObservableValue, StructuredObservableValue))
                for value in self.values
            )
        ):
            raise ValueError(
                "values must be a non-empty tuple of supported observable values"
            )
        _unique(self.values, lambda item: item.observable_id, "result observable IDs")


@dataclass(frozen=True)
class ExecutionReport(Digestible):
    record: RunRecord
    result: SimulationResult | None
    certificate: Certificate | None

    def __post_init__(self) -> None:
        if not isinstance(self.record, RunRecord):
            raise TypeError("record must be a RunRecord")
        if self.record.status is RunStatus.COMPLETE:
            if self.result is None or self.certificate is None:
                raise ValueError("a complete run requires a result and certificate")
            if self.result.run_id != self.record.run_id:
                raise ValueError("result run_id does not name the RunRecord")
            if self.certificate.run_id != self.record.run_id:
                raise ValueError("certificate run_id does not name the RunRecord")
            if self.certificate.run_status is not self.record.status:
                raise ValueError("certificate status does not match the RunRecord")
            if self.result.certificate_digest != self.certificate.digest:
                raise ValueError("result does not name the supplied certificate")
        elif self.result is not None:
            raise ValueError("a non-complete run cannot carry a SimulationResult")
        elif self.certificate is not None:
            raise ValueError("a non-complete run cannot carry a Certificate")


def _plain(value: object) -> object:
    """Human-readable JSON form for durable run journals; digests use canonical_payload."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _plain(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_")
        }
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_plain(item) for item in value), key=repr)
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("run journal mapping keys must be strings")
        return {key: _plain(value[key]) for key in sorted(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"run journal cannot serialize {type(value).__qualname__}")


def _observable_payload_error(
    plan: CandidatePlan,
    artifacts: tuple[Artifact, ...],
) -> str | None:
    """Validate executor-specific observable payload schemas before completion."""
    payloads = {
        artifact.artifact_id.removeprefix("observable:"): artifact.payload
        for artifact in artifacts
        if artifact.kind == "observable"
        and artifact.complete
        and not artifact.quarantined
    }
    if plan.executor_id == _REACTION_EXECUTOR:
        payload = payloads.get("reaction_energy")
        if not isinstance(payload, Estimate):
            return "reaction_energy must retain a typed Estimate payload"
        return None
    if plan.executor_id == _WATER_WAVE_EXECUTOR:
        from .water_wave_domain import (
            CharacteristicSample,
            HorizonDiagnostic,
            WaterWaveSpec,
            diagnose_horizon,
        )

        resolved = plan.request.resolved
        if not isinstance(resolved, ResolvedDomainProgram) or not isinstance(
            resolved.subject, WaterWaveSpec
        ):
            return "water-wave plan has no typed WaterWaveSpec subject"
        diagnostic = payloads.get("water_wave_horizon")
        profile = payloads.get("water_wave_characteristic_profile")
        if not isinstance(diagnostic, HorizonDiagnostic):
            return "water_wave_horizon must retain a typed HorizonDiagnostic payload"
        if not isinstance(profile, tuple) or any(
            not isinstance(item, CharacteristicSample) for item in profile
        ):
            return (
                "water_wave_characteristic_profile must retain every typed "
                "CharacteristicSample"
            )
        try:
            reference = diagnose_horizon(resolved.subject)
        except ValueError as error:
            return f"approved water-wave subject is unclassifiable: {error}"
        if diagnostic != reference:
            return "water_wave_horizon does not equal the independently recomputed diagnostic"
        if profile != diagnostic.samples:
            return "water-wave characteristic profile does not equal the diagnostic samples"
        return None
    if plan.executor_id == _WATER_WAVE_VALIDATION_EXECUTOR:
        from .water_wave_validation_domain import (
            CrossingBracket,
            SampleDiagnostic,
            ValidationDiagnostic,
            WaterWaveValidationSpec,
            diagnose_water_wave_background,
        )

        resolved = plan.request.resolved
        if (
            type(resolved) is not ResolvedDomainProgram
            or type(resolved.subject) is not WaterWaveValidationSpec
        ):
            return "water-background plan has no exact WaterWaveValidationSpec subject"
        diagnostic = payloads.get("water_background_validation")
        samples = payloads.get("water_background_sample_diagnostics")
        crossings = payloads.get("water_background_crossing_brackets")
        regime = payloads.get("water_background_regime_inventory")
        if type(diagnostic) is not ValidationDiagnostic:
            return (
                "water_background_validation must retain an exact ValidationDiagnostic"
            )
        if type(samples) is not tuple or any(
            type(item) is not SampleDiagnostic for item in samples
        ):
            return (
                "water_background_sample_diagnostics must retain every exact "
                "SampleDiagnostic"
            )
        if type(crossings) is not tuple or any(
            type(item) is not CrossingBracket for item in crossings
        ):
            return (
                "water_background_crossing_brackets must retain every exact "
                "CrossingBracket"
            )
        try:
            reference = diagnose_water_wave_background(resolved.subject)
        except ValueError as error:
            return f"approved water-background subject is unclassifiable: {error}"
        expected_regime = (
            reference.status,
            reference.continuity_gate_passed,
            reference.head_gate_passed,
            reference.shallow_water_gate_passed,
            reference.gravity_capillarity_gate_passed,
            reference.uncertainty_resolved_bracket_gate_passed,
            reference.position_order_resolved_gate_passed,
            reference.orientation_gate_passed,
        )
        if canonical_digest(diagnostic) != canonical_digest(reference):
            return (
                "water_background_validation does not equal the independently "
                "recomputed diagnostic"
            )
        if samples != reference.samples:
            return "water-background sample inventory differs from the diagnostic"
        if crossings != reference.crossings:
            return "water-background crossing inventory differs from the diagnostic"
        if regime != expected_regime:
            return "water-background regime inventory differs from the diagnostic"
        return None
    if plan.executor_id == _WATER_WAVE_CONTINUOUS_EXECUTOR:
        from .water_wave_continuous import ContinuousWaterSubject
        from .water_wave_continuous_verifier import continuous_payload_error

        resolved = plan.request.resolved
        if (
            type(resolved) is not ResolvedDomainProgram
            or type(resolved.subject) is not ContinuousWaterSubject
        ):
            return "continuous-water plan has no exact ContinuousWaterSubject"
        diagnostic = payloads.get("water_wave_continuous_diagnostic")
        meshes = payloads.get("water_wave_continuous_meshes")
        comparison = payloads.get("water_wave_finite_v2_comparison")
        return continuous_payload_error(
            resolved.subject,
            diagnostic,
            meshes,
            comparison,
        )
    if plan.executor_id == _HUMAN_ISOTOPE_EXECUTOR:
        from .human_isotope_domain import (
            ConstraintInventory,
            FamilyWitness,
            HumanIsotopeSpec,
            IdentifiabilityDiagnostic,
            diagnose_human_isotope,
        )

        resolved = plan.request.resolved
        if not isinstance(resolved, ResolvedDomainProgram) or not isinstance(
            resolved.subject, HumanIsotopeSpec
        ):
            return "human-isotope plan has no typed HumanIsotopeSpec subject"
        diagnostic = payloads.get("human_isotope_identifiability")
        inventory = payloads.get("human_isotope_constraint_inventory")
        witnesses = payloads.get("human_isotope_family_witnesses")
        if type(diagnostic) is not IdentifiabilityDiagnostic:
            return (
                "human_isotope_identifiability must retain an exact "
                "IdentifiabilityDiagnostic payload"
            )
        if type(inventory) is not ConstraintInventory:
            return (
                "human_isotope_constraint_inventory must retain an exact "
                "ConstraintInventory payload"
            )
        if type(witnesses) is not tuple or any(
            type(item) is not FamilyWitness for item in witnesses
        ):
            return (
                "human_isotope_family_witnesses must retain every exact FamilyWitness"
            )
        reference = diagnose_human_isotope(resolved.subject)
        if canonical_digest(diagnostic) != canonical_digest(reference):
            return (
                "human_isotope_identifiability does not equal the independently "
                "recomputed diagnostic"
            )
        if canonical_digest(inventory) != canonical_digest(
            diagnostic.constraint_inventory
        ):
            return "human-isotope constraint inventory is not the diagnostic inventory"
        if canonical_digest(witnesses) != canonical_digest(diagnostic.family_witnesses):
            return "human-isotope family witnesses are not the diagnostic witnesses"
        return None
    if plan.executor_id == _HUMAN_SURVIVAL_EXECUTOR:
        from .human_survival import _payloads as human_survival_payloads
        from .human_survival_domain import (
            SurvivalCalibrationResult,
            SurvivalCalibrationSpec,
            fit_synthetic_survival,
        )

        resolved = plan.request.resolved
        if (
            type(resolved) is not ResolvedDomainProgram
            or type(resolved.subject) is not SurvivalCalibrationSpec
        ):
            return "human-survival plan has no exact SurvivalCalibrationSpec subject"
        diagnostic = payloads.get("human_survival_synthetic_fit")
        if type(diagnostic) is not SurvivalCalibrationResult:
            return (
                "human_survival_synthetic_fit must retain an exact "
                "SurvivalCalibrationResult"
            )
        reference = fit_synthetic_survival(resolved.subject)
        if canonical_digest(diagnostic) != canonical_digest(reference):
            return (
                "human-survival fit does not equal the independently recomputed result"
            )
        expected_payloads = human_survival_payloads(reference, resolved.subject)
        for observable_id, expected in expected_payloads.items():
            if observable_id not in payloads:
                return f"human-survival output omitted {observable_id}"
            if canonical_digest(payloads[observable_id]) != canonical_digest(expected):
                return (
                    f"human-survival output {observable_id} differs from the "
                    "independently recomputed payload"
                )
        return None
    if plan.executor_id == _ISING_LATTICE_GAS_EXECUTOR:
        from .ising_lattice_gas import (
            _finite_c3_model,
            _payloads as ising_lattice_gas_payloads,
        )
        from .ising_lattice_gas_domain import (
            ExactEquilibriumMap,
            IsingLatticeGasSpec,
            exact_equilibrium_map_error,
        )

        resolved = plan.request.resolved
        if (
            type(resolved) is not ResolvedDomainProgram
            or type(resolved.subject) is not IsingLatticeGasSpec
        ):
            return "Ising-lattice-gas plan has no exact IsingLatticeGasSpec subject"
        exact_model = _finite_c3_model()
        if plan.model != exact_model or plan.request.physical_ir.models != (
            exact_model,
        ):
            return (
                "Ising-lattice-gas plan does not retain the runtime-owned exact model"
            )
        diagnostic = payloads.get("ising_lattice_gas_state_map")
        if type(diagnostic) is not ExactEquilibriumMap:
            return (
                "ising_lattice_gas_state_map must retain an exact ExactEquilibriumMap"
            )
        verification_error = exact_equilibrium_map_error(
            diagnostic,
            resolved.subject,
        )
        if verification_error is not None:
            return (
                "Ising-lattice-gas state map failed the separate direct verifier: "
                + verification_error
            )
        expected_payloads = ising_lattice_gas_payloads(diagnostic)
        for observable_id, expected in expected_payloads.items():
            if observable_id not in payloads:
                return f"Ising-lattice-gas output omitted {observable_id}"
            if canonical_digest(payloads[observable_id]) != canonical_digest(expected):
                return (
                    f"Ising-lattice-gas output {observable_id} differs from the "
                    "independently recomputed payload"
                )
        return None
    if plan.executor_id == _RESISTIVE_DC_EXECUTOR:
        from .resistive_dc import ResistiveDCAnalysis, ResistiveDCSubject, _payloads
        from .resistive_dc_verifier import (
            DirectVerificationReport,
            verify_resistive_dc_analysis,
        )

        resolved = plan.request.resolved
        if (
            type(resolved) is not ResolvedDomainProgram
            or type(resolved.subject) is not ResistiveDCSubject
        ):
            return "resistive-DC plan has no exact ResistiveDCSubject"
        analysis = payloads.get("resistive_dc_analysis")
        if type(analysis) is not ResistiveDCAnalysis:
            return "resistive_dc_analysis must retain an exact ResistiveDCAnalysis"
        verification = verify_resistive_dc_analysis(resolved.subject, analysis)
        if not verification.passed:
            return (
                "resistive-DC analysis failed the production-independent direct "
                f"verifier: {'; '.join(verification.reasons)}"
            )
        retained_verification = payloads.get("resistive_dc_direct_verification")
        if type(retained_verification) is not DirectVerificationReport:
            return (
                "resistive_dc_direct_verification must retain an exact "
                "DirectVerificationReport"
            )
        if canonical_digest(retained_verification) != canonical_digest(verification):
            return (
                "resistive_dc_direct_verification differs from the fresh "
                "production-independent verifier report"
            )
        for observable_id, expected in _payloads(analysis, verification).items():
            if observable_id not in payloads:
                return f"resistive-DC output omitted {observable_id}"
            if canonical_digest(payloads[observable_id]) != canonical_digest(expected):
                return (
                    f"resistive-DC output {observable_id} differs from the "
                    "directly verified analysis payload"
                )
        return None
    if plan.executor_id == _RLC_AC_EXECUTOR:
        from .rlc_ac import _payloads
        from .rlc_ac_schema import RLCACAnalysis, RLCACSubject
        from .rlc_ac_verifier import (
            DirectACVerificationReport,
            verify_rlc_ac_analysis,
        )

        resolved = plan.request.resolved
        if (
            type(resolved) is not ResolvedDomainProgram
            or type(resolved.subject) is not RLCACSubject
        ):
            return "RLC-AC plan has no exact RLCACSubject"
        analysis = payloads.get("rlc_ac_analysis")
        if type(analysis) is not RLCACAnalysis:
            return "rlc_ac_analysis must retain an exact RLCACAnalysis"
        verification = verify_rlc_ac_analysis(resolved.subject, analysis)
        if not verification.passed:
            return (
                "RLC-AC analysis failed the production-independent direct "
                f"verifier: {'; '.join(verification.reasons)}"
            )
        retained_verification = payloads.get("rlc_ac_direct_verification")
        if type(retained_verification) is not DirectACVerificationReport:
            return (
                "rlc_ac_direct_verification must retain an exact "
                "DirectACVerificationReport"
            )
        if canonical_digest(retained_verification) != canonical_digest(verification):
            return (
                "rlc_ac_direct_verification differs from the fresh "
                "production-independent verifier report"
            )
        for observable_id, expected in _payloads(analysis, verification).items():
            if observable_id not in payloads:
                return f"RLC-AC output omitted {observable_id}"
            if canonical_digest(payloads[observable_id]) != canonical_digest(expected):
                return (
                    f"RLC-AC output {observable_id} differs from the "
                    "directly verified analysis payload"
                )
        return None
    return f"no observable payload validator for executor {plan.executor_id!r}"


class RunJournal:
    """
    Durable lifecycle tracker for one approved calculation.

    Every state transition atomically replaces the JSON record.  A completed species result
    may be reused by an independently approved resume plan through the ordinary calculation
    cache, but artifacts from an incomplete run remain quarantined and are never presented as
    the requested simulation result.
    """

    def __init__(
        self,
        approved: ApprovedPlan,
        *,
        backend: str,
        path: str | os.PathLike[str] | None = None,
        run_id: str | None = None,
    ) -> None:
        if not isinstance(approved, ApprovedPlan):
            raise TypeError("RunJournal requires an ApprovedPlan")
        _nonempty(backend, "backend")
        now = datetime.now(timezone.utc).isoformat()
        self.approved = approved
        self.path = Path(path) if path is not None else None
        self._record = RunRecord(
            run_id=run_id or uuid4().hex,
            plan_digest=approved.plan.digest,
            approval_digest=approved.approval.digest,
            status=RunStatus.RUNNING,
            started_at=now,
            updated_at=now,
            backend=backend,
            cache_state=(),
            artifacts=(),
            checkpoints=(),
            obligation_results=(),
            diagnostics=(),
            failures=(),
        )
        self._reserve_path()
        self._persist()

    @property
    def record(self) -> RunRecord:
        return self._record

    def _reserve_path(self) -> None:
        """Claim a journal path exactly once so concurrent runs cannot erase each other."""
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        descriptor = os.open(self.path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(
                    {
                        "run_id": self._record.run_id,
                        "status": "RESERVED",
                    },
                    stream,
                    sort_keys=True,
                )
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            self.path.unlink(missing_ok=True)
            raise

    def _assert_path_owned(self) -> None:
        if self.path is None:
            return
        try:
            persisted = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            raise RuntimeError("run journal path was removed or corrupted") from error
        if persisted.get("run_id") != self._record.run_id:
            raise RuntimeError(
                "run journal path is no longer owned by this run; refusing to overwrite it"
            )

    def _transition(self, **changes: object) -> RunRecord:
        if self._record.status is not RunStatus.RUNNING:
            raise RuntimeError(f"run is already terminal: {self._record.status.value}")
        following = replace(
            self._record,
            updated_at=datetime.now(timezone.utc).isoformat(),
            **changes,
        )
        self._persist(following)
        self._record = following
        return self._record

    def add_artifact(self, artifact: Artifact) -> RunRecord:
        if any(
            existing.artifact_id == artifact.artifact_id
            for existing in self._record.artifacts
        ):
            raise ValueError(f"artifact {artifact.artifact_id!r} already exists")
        return self._transition(artifacts=self._record.artifacts + (artifact,))

    def add_checkpoint(self, artifact: Artifact) -> RunRecord:
        if artifact.kind != "checkpoint":
            raise ValueError("checkpoint artifacts must have kind='checkpoint'")
        return self._transition(checkpoints=self._record.checkpoints + (artifact,))

    def add_obligation_result(self, result: ObligationResult) -> RunRecord:
        declared = {
            obligation.digest for obligation in self.approved.plan.request.obligations
        }
        if result.obligation_digest not in declared:
            raise ValueError(
                "obligation result is not declared by the approved request"
            )
        if any(
            existing.obligation_digest == result.obligation_digest
            for existing in self._record.obligation_results
        ):
            raise ValueError(
                "an obligation may have exactly one result in a run; contradictory or "
                "duplicate verdicts require a new run"
            )
        return self._transition(
            obligation_results=self._record.obligation_results + (result,)
        )

    def add_cache_state(self, detail: str) -> RunRecord:
        _nonempty(detail, "cache state")
        return self._transition(cache_state=self._record.cache_state + (detail,))

    def add_diagnostic(self, detail: str) -> RunRecord:
        _nonempty(detail, "diagnostic")
        return self._transition(diagnostics=self._record.diagnostics + (detail,))

    @staticmethod
    def _quarantine_artifact(artifact: Artifact) -> Artifact:
        """Quarantine even when an in-process engine mutated a retained payload.

        The ordinary path preserves the approved content digest.  If the payload's
        current digest no longer matches, retain the mutated payload under its actual
        digest and record the originally observed digest in the detail rather than
        allowing quarantine itself to fail.
        """
        try:
            return replace(artifact, quarantined=True)
        except ValueError:
            if artifact.payload is None:
                raise
            original_digest = artifact.content_digest
            current_digest = canonical_digest(artifact.payload)
            detail = (f"{artifact.detail}; " if artifact.detail else "") + (
                "payload identity changed after retention; "
                f"original_digest={original_digest}"
            )
            return replace(
                artifact,
                content_digest=current_digest,
                quarantined=True,
                detail=detail,
            )

    def incomplete(self, reason: str) -> RunRecord:
        _nonempty(reason, "reason")
        quarantined = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.artifacts
        )
        quarantined_checkpoints = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.checkpoints
        )
        return self._transition(
            status=RunStatus.INCOMPLETE,
            artifacts=quarantined,
            checkpoints=quarantined_checkpoints,
            failures=self._record.failures + (reason,),
        )

    def refused(self, reason: str) -> RunRecord:
        _nonempty(reason, "reason")
        quarantined = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.artifacts
        )
        quarantined_checkpoints = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.checkpoints
        )
        return self._transition(
            status=RunStatus.REFUSED,
            artifacts=quarantined,
            checkpoints=quarantined_checkpoints,
            failures=self._record.failures + (reason,),
        )

    def invalid(self, reason: str) -> RunRecord:
        _nonempty(reason, "reason")
        quarantined = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.artifacts
        )
        quarantined_checkpoints = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.checkpoints
        )
        return self._transition(
            status=RunStatus.INVALID,
            artifacts=quarantined,
            checkpoints=quarantined_checkpoints,
            failures=self._record.failures + (reason,),
        )

    def failed(self, reason: str) -> RunRecord:
        _nonempty(reason, "reason")
        quarantined = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.artifacts
        )
        quarantined_checkpoints = tuple(
            self._quarantine_artifact(artifact) for artifact in self._record.checkpoints
        )
        return self._transition(
            status=RunStatus.FAILED,
            artifacts=quarantined,
            checkpoints=quarantined_checkpoints,
            failures=self._record.failures + (reason,),
        )

    def complete(self) -> RunRecord:
        expected = tuple(
            sorted(self.approved.plan.request.output_contract.observable_ids)
        )
        actual = self._record.output_inventory
        if actual != expected:
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            return self.incomplete(
                f"output inventory mismatch; missing={missing}, extra={extra}"
            )
        payload_error = _observable_payload_error(
            self.approved.plan,
            self._record.artifacts,
        )
        if payload_error is not None:
            return self.invalid("observable payload schema mismatch: " + payload_error)
        required = {
            obligation.digest
            for obligation in self.approved.plan.request.obligations
            if obligation.required
        }
        results = {
            result.obligation_digest: result
            for result in self._record.obligation_results
        }
        missing_or_failed = {
            digest
            for digest in required
            if digest not in results
            or results[digest].outcome is not ObligationOutcome.PASS
        }
        if missing_or_failed:
            return self.invalid(
                "required obligations did not all pass: "
                + ", ".join(sorted(missing_or_failed))
            )
        return self._transition(status=RunStatus.COMPLETE)

    def _persist(self, record: RunRecord | None = None) -> None:
        if self.path is None:
            return
        self._assert_path_owned()
        record = self._record if record is None else record
        handle, temporary = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=self.path.name + ".",
            suffix=".tmp",
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(_plain(record), stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise


def _molecule_identity(molecule: Molecule) -> Identity:
    return Identity(
        stable_id=canonical_digest(molecule),
        kind="chemical-species",
        state=(
            ("signature", species_signature(molecule)),
            ("phase", "unspecified"),
            ("geometry", "fixed protocol geometry where the oracle requires one"),
        ),
    )


def _default_output_contract() -> OutputContract:
    return OutputContract(
        observables=(
            ObservableRequest(
                observable_id="reaction_energy",
                kind="closed-reaction endpoint energy difference",
                unit="eV",
                support="one conserving reaction at the oracle's declared fixed protocol",
                resolution="one scalar endpoint difference",
                precision="preserve the oracle value and reported uncertainty scale",
                coverage="all non-spectator endpoint species or refuse",
                diagnostics=(
                    "oracle method",
                    "reported uncertainty scale",
                    "systematic sensitivities",
                    "runtime seconds",
                ),
                retention=("run record", "certificate"),
            ),
        ),
        diagnostics=(
            "pre/post validity outcomes",
            "cache hits and misses",
            "artifact inventory",
            "refusals and failures",
        ),
        retention=(
            "source program",
            "approved plan",
            "run record",
            "completed species checkpoints",
            "result certificate",
        ),
    )


def _reaction_obligations() -> tuple[ValidityObligation, ...]:
    return (
        ValidityObligation(
            "reaction-conserves",
            ObligationStage.PRE,
            "smartchem.program/reaction-conserves-v1",
            "the closed reaction conserves atom inventory and net charge",
        ),
        ValidityObligation(
            "oracle-admits-every-species",
            ObligationStage.PRE,
            "smartchem.program/oracle-domain-v1",
            "one oracle admits every non-spectator endpoint species without obstruction",
        ),
        ValidityObligation(
            "oracle-returned-endpoint-energy",
            ObligationStage.POST,
            "smartchem.program/result-present-v1",
            "the oracle returned a finite endpoint estimate rather than declining",
        ),
        ValidityObligation(
            "output-inventory-exact",
            ObligationStage.POST,
            "smartchem.program/output-inventory-v1",
            "emitted observable identities exactly equal the frozen output contract",
        ),
    )


def _reaction_energy_model() -> ModelSpec:
    """Return the exact runtime-owned model that licenses spectator cancellation."""
    return ModelSpec(
        name="closed-separable-endpoint-energy",
        equations=(
            "E(configuration) = sum(count_i * E(species_i))",
            "delta_E(reaction) = E(products) - E(reactants)",
        ),
        assumptions=(
            "isolated noninteracting species at each endpoint",
            "one consistent oracle reference and calculation protocol",
            "spectator cancellation is used only inside this separable model",
        ),
        valid_if=(
            "Reaction construction and independent conserves() check pass",
            "the selected oracle admits and returns every non-spectator species",
        ),
        postconditions=(
            "a finite Estimate is returned",
            "the output inventory exactly matches the approved contract",
        ),
        conserved=("atom inventory", "net charge"),
        version="1",
    )


def _build_reaction_residue_transform(
    reaction: Reaction,
    model: ModelSpec,
    output_contract_digest: str = "",
    equivalence_contract_digest: str = "",
) -> ReactionResidueTransform | None:
    """Construct the exact Class-A transform when a shared multiset exists."""
    left_counts = Counter(reaction.dom.species)
    right_counts = Counter(reaction.cod.species)
    shared = left_counts & right_counts
    if not shared:
        return None
    residual_left, residual_right = reaction_residue(reaction)
    eliminated = tuple(
        (molecule, shared[molecule])
        for molecule in dict.fromkeys(reaction.dom.species)
        if shared[molecule]
    )
    workset = tuple(dict.fromkeys(residual_left.species + residual_right.species))
    return ReactionResidueTransform(
        name="reaction-residue-v1",
        exactness_class="A_IDENTITY_PRESERVING",
        input_model_digest=model.digest,
        output_model_digest=model.digest,
        applicability=(
            "closed Reaction",
            "E(configuration) is the sum of isolated species energies",
            "the same immutable oracle calculation specification prices both endpoints",
        ),
        evidence=(
            "multiset intersection recomputed from the approved raw Reaction",
            "E(S+R)-E(S+L)=E(R)-E(L) in the declared separable model",
            "residual workset and multiplicities retained exactly",
        ),
        casualties=(),
        output_contract_digest=output_contract_digest,
        equivalence_contract_digest=equivalence_contract_digest,
        original_reaction_digest=canonical_digest(reaction),
        residual_left=residual_left,
        residual_right=residual_right,
        eliminated_species=eliminated,
        workset=workset,
        verifier_id="smartchem.category/reaction-residue-v1",
    )


def _verified_reaction_residue(
    reaction: Reaction,
    model: ModelSpec,
    transforms: tuple[Transform, ...],
    output_contract: OutputContract,
    equivalence_contract: EquivalenceContract,
) -> tuple[Config, Config, tuple[Molecule, ...], ReactionResidueTransform | None]:
    """Recompute the only supported transform and reject any forged plan record."""
    expected = _build_reaction_residue_transform(
        reaction,
        model,
        output_contract.digest,
        equivalence_contract.digest,
    )
    if expected is None:
        if transforms:
            raise ValueError(
                "reaction has no shared spectator multiset but the plan names a transform"
            )
        left, right = reaction_residue(reaction)
        return left, right, tuple(dict.fromkeys(left.species + right.species)), None
    if len(transforms) != 1 or type(transforms[0]) is not ReactionResidueTransform:
        raise ValueError(
            "reaction with shared spectators requires exactly one "
            "ReactionResidueTransform"
        )
    planned = transforms[0]
    if planned != expected:
        raise ValueError(
            "planned reaction-residue transform differs from independent recomputation"
        )
    return expected.residual_left, expected.residual_right, expected.workset, expected


def compile_reaction_energy(
    source: SourceProgram | str,
    reaction: Reaction,
    oracle: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
    shepherd_session_digest: str = "directly-resolved-without-a-shepherd-session",
) -> CandidatePlan:
    """
    Compile one closed reaction-energy request without executing the oracle.

    The plan is certified only inside the current isolated-species endpoint adapter and the
    oracle's declared domain.  It does not claim Gibbs free energy, spontaneity, kinetics,
    an interacting vessel, or accuracy outside the oracle's validation statement.
    """
    if isinstance(source, str):
        source = SourceProgram(source)
    if not isinstance(source, SourceProgram):
        raise TypeError("source must be SourceProgram or str")
    if not isinstance(reaction, Reaction):
        raise TypeError("reaction must be a Reaction")

    source_theory = SourceTheory(
        name="closed separable endpoint-energy model",
        axioms=(
            "the Reaction carries equal atom inventories and equal net charge at both endpoints",
            "configuration energy is the sum of isolated species energies",
            "one immutable oracle calculation specification prices every retained species",
        ),
        provenance=(
            "smartchem.category.Reaction",
            "smartchem.thermo.reaction_energy",
        ),
    )
    target = TargetIntent(
        statement=source.text,
        target_scale="one closed chemical reaction",
        requested_meaning=(
            "endpoint delta-E under the selected oracle; not delta-G, spontaneity, or kinetics"
        ),
    )
    resolved = ResolvedProgram(
        source.digest,
        reaction,
        target,
        source_theory,
        shepherd_session_digest,
    )

    species = tuple(dict.fromkeys(reaction.dom.species + reaction.cod.species))
    components = tuple(
        Component(
            component_id=f"species-{index}",
            kind="chemical-species",
            identity=_molecule_identity(molecule),
        )
        for index, molecule in enumerate(species)
    )
    model = _reaction_energy_model()
    solver = SolverSpec(
        name=getattr(oracle, "name", type(oracle).__qualname__),
        algorithm="existing SmartChem EnergyOracle",
        version="1",
        tolerances=(),
        stopping_policy="oracle-declared; any decline refuses the whole endpoint difference",
        reproducibility="immutable CalculationSpec plus implementation digest",
    )
    calculation = CalculationSpec.from_oracle(oracle)
    residue_transform = _build_reaction_residue_transform(reaction, model)
    residual_left, residual_right = reaction_residue(reaction)
    residual_reaction = Reaction(residual_left, residual_right)
    residual_workset = tuple(
        dict.fromkeys(residual_left.species + residual_right.species)
    )
    claim_scope = ClaimScope(
        ClaimKind.LITERAL,
        "endpoint delta-E under the closed separable species model and named oracle",
        exclusions=(
            "Gibbs free energy",
            "thermodynamic spontaneity",
            "kinetics or mechanism",
            "interacting-vessel effects",
            "human or environmental safety",
        ),
    )
    nominal_accuracy = getattr(oracle, "nominal_accuracy_ev", float("inf"))
    measured_evidence = (
        isinstance(nominal_accuracy, (int, float))
        and not isinstance(nominal_accuracy, bool)
        and math.isfinite(float(nominal_accuracy))
    )
    evidence_status = (
        EvidenceStatus.CALIBRATED if measured_evidence else EvidenceStatus.EXPERIMENTAL
    )
    physical_ir = PhysicalIR(
        resolved_digest=resolved.digest,
        components=components,
        connections=(),
        reservoirs=(),
        boundaries=(),
        models=(model,),
        adapters=(
            Adapter(
                "isolated-species endpoint adapter",
                "closed Reaction",
                "scalar endpoint energy difference",
                ("reaction_energy",),
                (
                    "closed conserved inventory",
                    "one reference-compatible oracle",
                ),
                "inter-species interaction and finite-temperature terms omitted",
            ),
        ),
        invariants=(
            Invariant(
                "closed inventory",
                "reactant and product atom counts and net charge agree",
                "this Reaction",
                "smartchem.category/conserves-v1",
            ),
        ),
        transport_maps=(),
        transport_evidence=(),
        assemblies=(),
        assembly_evidence=(),
        claim_scope=claim_scope,
        evidence_status=evidence_status,
    )
    obligations = _reaction_obligations()
    request = SimulationRequest(
        source=source,
        resolved=resolved,
        physical_ir=physical_ir,
        output_contract=output_contract or _default_output_contract(),
        equivalence_contract=equivalence_contract
        or EquivalenceContract(
            relation=(
                "exact equality of every reaction_energy ObservableValue field under "
                "the approved raw Reaction and CalculationSpec"
            ),
            numeric_tolerances=(),
            ordering="observable IDs sorted for comparison; source order retained in records",
            rng_policy="no RNG in this vertical",
            checkpoint_policy=(
                "completed species estimates may be reused only under an identical "
                "CalculationSpec and a newly approved resume plan"
            ),
            allowed_provenance_differences=(
                "one verified transform artifact may be added to the retained RunRecord",
                "the oracle-domain obligation detail names the verified residual workset",
                "plan, approval, run, artifact, and certificate identities bind the "
                "retained transform record and therefore differ from a transform-free plan",
                "timing and cache counters are execution provenance, not scientific outputs",
            ),
        ),
        obligations=obligations,
    )
    if residue_transform is not None:
        residue_transform = replace(
            residue_transform,
            output_contract_digest=request.output_contract.digest,
            equivalence_contract_digest=request.equivalence_contract.digest,
        )
    inspection = diagnose(residual_reaction, (oracle,))
    blockers = tuple(repr(obstruction) for obstruction in inspection.obstructions)
    unsupported = tuple(
        observable
        for observable in request.output_contract.observable_ids
        if observable != "reaction_energy"
    )
    if unsupported:
        blockers += (
            "this vertical cannot emit requested observable(s): "
            + ", ".join(unsupported),
        )
    contract_error = _executor_contract_error(
        _REACTION_EXECUTOR,
        request.output_contract,
    )
    if contract_error is not None:
        blockers += (contract_error,)
    return CandidatePlan(
        request=request,
        model=model,
        solver=solver,
        calculation=calculation,
        compiler_implementation_digest=_compiler_implementation_digest(),
        executor_id=_REACTION_EXECUTOR,
        transforms=((residue_transform,) if residue_transform is not None else ()),
        predicted_resources=(
            (
                "structural residual species calls",
                str(len(residual_workset)),
            ),
            ("wall/memory", "oracle-dependent; measured by RunRecord, not guessed"),
        ),
        blockers=blockers,
        execution_lane=(
            ExecutionLane.CERTIFIED if measured_evidence else ExecutionLane.EXPERIMENTAL
        ),
        limits=limits or RuntimeLimits(),
    )


def compile_session_reaction_energy(
    source: SourceProgram | str,
    session: object,
    reaction_slot_name: str,
    oracle: object,
    *,
    output_contract: OutputContract | None = None,
    equivalence_contract: EquivalenceContract | None = None,
    limits: RuntimeLimits | None = None,
) -> CandidatePlan:
    """
    Bridge a closed typed shepherd session into the executable reaction-energy vertical.

    Only an outright ``COMPILED`` session is accepted here.  A
    ``COMPILED_SUBJECT_TO`` session carries post-run obligations that must first be mapped
    into the runtime registry; silently discarding them while crossing this seam would
    upgrade conditional coherence into an executable plan.
    """
    from .ledger import COMPILED, Session

    _nonempty(reaction_slot_name, "reaction_slot_name")
    if not isinstance(session, Session):
        raise TypeError("session must be a shepherd Session")
    if session.outcome != COMPILED:
        raise ValueError(
            "this vertical requires an outright COMPILED typed session; "
            f"received {session.outcome}"
        )
    if session.spec.measure() != 0 or session.spec.subject_to():
        raise ValueError(
            "this vertical independently requires a closed shepherd spec with no "
            "unmapped post-run obligations"
        )
    slot = next(
        (
            candidate
            for candidate in session.spec.slots
            if candidate.name == reaction_slot_name
        ),
        None,
    )
    if slot is None:
        raise KeyError(f"compiled session has no slot named {reaction_slot_name!r}")
    if slot.typed_binding is None:
        raise TypeError(
            f"slot {reaction_slot_name!r} has no typed binding; text cannot authorize "
            "reaction execution"
        )
    reaction = slot.typed_binding.value
    if not isinstance(reaction, Reaction):
        raise TypeError(
            f"slot {reaction_slot_name!r} is bound to {type(reaction).__name__}, "
            "not a Reaction"
        )
    return compile_reaction_energy(
        source,
        reaction,
        oracle,
        output_contract=output_contract,
        equivalence_contract=equivalence_contract,
        limits=limits,
        shepherd_session_digest=canonical_digest(session),
    )


def _obligation(
    obligation: ValidityObligation,
    outcome: ObligationOutcome,
    detail: str,
) -> ObligationResult:
    return ObligationResult(obligation.digest, outcome, detail)


def _pre_result(
    obligation: ValidityObligation,
    reaction: Reaction,
    oracle: object,
    residual_reaction: Reaction | None = None,
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.program/reaction-conserves-v1":
        passed = conserves(reaction)
        return _obligation(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            "conserves(reaction) returned true"
            if passed
            else "conserves(reaction) returned false",
        )
    if obligation.evaluator_id == "smartchem.program/oracle-domain-v1":
        inspection = diagnose(residual_reaction or reaction, (oracle,))
        return _obligation(
            obligation,
            ObligationOutcome.PASS if inspection else ObligationOutcome.REFUSE,
            inspection.explain(),
        )
    return _obligation(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _post_result(
    obligation: ValidityObligation,
    estimate: Estimate | None,
    output_ids: tuple[str, ...],
    expected_ids: tuple[str, ...],
) -> ObligationResult:
    if obligation.evaluator_id == "smartchem.program/result-present-v1":
        return _obligation(
            obligation,
            ObligationOutcome.PASS
            if estimate is not None
            else ObligationOutcome.REFUSE,
            "oracle returned an Estimate"
            if estimate is not None
            else "oracle declined",
        )
    if obligation.evaluator_id == "smartchem.program/output-inventory-v1":
        passed = tuple(sorted(output_ids)) == tuple(sorted(expected_ids))
        return _obligation(
            obligation,
            ObligationOutcome.PASS if passed else ObligationOutcome.FAIL,
            f"expected={sorted(expected_ids)}, emitted={sorted(output_ids)}",
        )
    return _obligation(
        obligation,
        ObligationOutcome.REFUSE,
        f"no approved evaluator registered for {obligation.evaluator_id}",
    )


def _estimate_artifact(artifact_id: str, kind: str, estimate: Estimate) -> Artifact:
    return Artifact(
        artifact_id=artifact_id,
        kind=kind,
        content_digest=canonical_digest(estimate),
        complete=True,
        quarantined=False,
        detail=(
            f"{estimate.value_ev:+.12g} eV via {estimate.method}; "
            f"reported scale {estimate.uncertainty_ev:.12g} eV"
        ),
        payload=estimate,
    )


def _peak_rss_bytes() -> int | None:
    """Best available process peak RSS, or ``None`` where the platform exposes none."""
    if resource is None:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes.  ``sys.platform`` would add another import,
    # while /proc is the more direct discriminator on the supported Linux CI/runtime.
    return int(peak * 1024) if Path("/proc/self/statm").exists() else int(peak)


def _resource_wall(
    limits: RuntimeLimits,
    *,
    started: float,
    completed_calls: int,
    call_label: str = "species calls",
) -> str | None:
    elapsed = time.monotonic() - started
    if limits.wall_seconds is not None and elapsed >= limits.wall_seconds:
        return (
            f"approved wall_seconds={limits.wall_seconds} reached after "
            f"{elapsed:.6f}s and {completed_calls} completed {call_label}"
        )
    peak = _peak_rss_bytes()
    if limits.memory_bytes is not None:
        if peak is None:
            return (
                "approved memory_bytes limit cannot be monitored on this platform; "
                "refusing to run past an unenforceable hard stop"
            )
        if peak >= limits.memory_bytes:
            return (
                f"approved memory_bytes={limits.memory_bytes} reached at peak_rss={peak} "
                f"after {completed_calls} completed {call_label}"
            )
    return None


def _preflight_reaction_energy(plan: CandidatePlan) -> None:
    """Reject a forged reaction plan before it can claim a run journal."""
    if plan.executor_id != _REACTION_EXECUTOR:
        raise ValueError("reaction preflight received a different executor plan")
    if type(plan.request.resolved) is not ResolvedProgram:
        raise ValueError("reaction executor requires an exact chemical ResolvedProgram")
    runtime_model = _reaction_energy_model()
    if plan.model != runtime_model or plan.request.physical_ir.models != (
        runtime_model,
    ):
        raise ValueError(
            "reaction executor model differs from the exact runtime-owned "
            "closed-separable endpoint-energy model"
        )
    try:
        _verified_reaction_residue(
            plan.request.resolved.reaction,
            plan.model,
            plan.transforms,
            plan.request.output_contract,
            plan.request.equivalence_contract,
        )
    except ValueError as error:
        raise ValueError(
            f"Class-A transform verification failed before journal creation: {error}"
        ) from error


def execute(
    approved: ApprovedPlan,
    oracle: object,
    *,
    journal_path: str | os.PathLike[str] | None = None,
) -> ExecutionReport:
    """Validate and dispatch one approved plan through the closed executor registry."""
    if type(approved) is not ApprovedPlan:
        raise TypeError("execute requires an ApprovedPlan")
    plan = approved.plan
    if type(plan) is not CandidatePlan:
        raise TypeError("approved plan must contain a CandidatePlan")
    if type(approved.approval) is not Approval:
        raise TypeError("approved plan must contain an Approval")
    if approved.approval.digest != approved.approval_record_digest:
        raise ValueError(
            "approved plan integrity check failed; approval record changed after "
            "authorization"
        )
    if approved.approval.plan_digest != plan.digest:
        raise ValueError(
            "approved plan integrity check failed; approval no longer names this plan"
        )
    if _compiler_implementation_digest() != plan.compiler_implementation_digest:
        raise ValueError(
            "compiler/runtime implementation changed after approval; re-plan and obtain "
            "new approval"
        )
    from .runtime_registry import descriptor_for

    try:
        descriptor = descriptor_for(plan.executor_id)
        subject = descriptor.extract_subject(plan.request.resolved)
    except (KeyError, TypeError) as error:
        raise ValueError(str(error)) from error
    try:
        validate_structure_attachment(
            plan.executor_id,
            subject,
            plan.structure_attachment,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"StructureIR plan admission failed: {error}") from error
    supported_outputs = frozenset(descriptor.default_output_contract().observable_ids)
    unsupported_outputs = sorted(
        set(plan.request.output_contract.observable_ids) - supported_outputs
    )
    if unsupported_outputs:
        raise ValueError(
            "approved executor cannot emit requested observables: "
            + ", ".join(unsupported_outputs)
        )
    contract_error = descriptor.output_contract_error(plan.request.output_contract)
    if contract_error is not None:
        raise ValueError(contract_error)
    descriptor.resolve_plan_preflight()(plan)
    admission_snapshot = _capture_execution_admission(approved, subject)
    actual_calculation = CalculationSpec.from_oracle(oracle)
    admission_error = _execution_admission_error(
        approved,
        subject,
        admission_snapshot,
    )
    if admission_error is not None:
        raise ValueError(admission_error)
    if actual_calculation.digest != plan.calculation.digest:
        raise ValueError(
            "oracle CalculationSpec changed after approval; re-plan and obtain new approval"
        )
    runner = descriptor.resolve_runner()
    return runner(
        approved,
        oracle,
        actual_calculation=actual_calculation,
        journal_path=journal_path,
        _dispatch_token=_RUNTIME_DISPATCH_TOKEN,
        _admission_snapshot=admission_snapshot,
    )


def _execute_reaction_energy(
    approved: ApprovedPlan,
    oracle: object,
    *,
    actual_calculation: CalculationSpec,
    journal_path: str | os.PathLike[str] | None = None,
    _dispatch_token: object = None,
    _admission_snapshot: _ExecutionAdmissionSnapshot | None = None,
) -> ExecutionReport:
    """Run the already validated reaction-energy plan."""
    _require_runtime_dispatch(_dispatch_token)
    plan = approved.plan
    _preflight_reaction_energy(plan)
    if plan.executor_id != _REACTION_EXECUTOR:
        raise ValueError("reaction-energy runner received a different executor plan")
    if type(plan.request.resolved) is not ResolvedProgram:
        raise ValueError("reaction executor requires an exact chemical ResolvedProgram")
    started_monotonic = time.monotonic()
    journal = RunJournal(
        approved,
        backend=actual_calculation.engine_name,
        path=journal_path,
    )
    reaction = plan.request.resolved.reaction
    if type(_admission_snapshot) is not _ExecutionAdmissionSnapshot:
        raise TypeError("reaction executor requires an execution admission snapshot")
    try:
        for artifact_id, kind, payload in (
            ("source-program", "source", plan.request.source),
            ("candidate-plan", "plan", plan),
            ("approval", "approval", approved.approval),
        ):
            journal.add_artifact(
                Artifact(
                    artifact_id=artifact_id,
                    kind=kind,
                    content_digest=payload.digest,
                    complete=True,
                    quarantined=False,
                    payload=payload,
                )
            )

        runtime_model = _reaction_energy_model()
        if plan.model != runtime_model or plan.request.physical_ir.models != (
            runtime_model,
        ):
            return ExecutionReport(
                journal.invalid(
                    "reaction executor model differs from the exact runtime-owned "
                    "closed-separable endpoint-energy model"
                ),
                None,
                None,
            )
        try:
            left, right, species, residue_transform = _verified_reaction_residue(
                reaction,
                plan.model,
                plan.transforms,
                plan.request.output_contract,
                plan.request.equivalence_contract,
            )
        except ValueError as error:
            return ExecutionReport(
                journal.invalid(f"Class-A transform verification failed: {error}"),
                None,
                None,
            )
        residual_reaction = Reaction(left, right)
        if residue_transform is not None:
            journal.add_artifact(
                Artifact(
                    artifact_id="transform:reaction-residue-v1",
                    kind="transform",
                    content_digest=residue_transform.digest,
                    complete=True,
                    quarantined=False,
                    detail=(
                        f"Class A; eliminated={sum(count for _, count in residue_transform.eliminated_species)} "
                        f"molecules; residual_distinct_species={len(species)}"
                    ),
                    payload=residue_transform,
                )
            )
            journal.add_cache_state(
                "verified Class-A reaction-residue-v1 spectator cancellation applied"
            )
        else:
            journal.add_cache_state(
                "Class-A reaction-residue-v1 not applicable: no shared spectator multiset"
            )

        for obligation in plan.request.obligations:
            if obligation.stage is not ObligationStage.PRE:
                continue
            result = _pre_result(
                obligation,
                reaction,
                oracle,
                residual_reaction,
            )
            journal.add_obligation_result(result)
            if obligation.required and result.outcome is not ObligationOutcome.PASS:
                record = journal.refused(
                    f"precondition {obligation.name} ended {result.outcome.value}: "
                    f"{result.detail}"
                )
                return ExecutionReport(record, None, None)

        cached = CachingOracle(oracle)
        calls = 0
        for molecule in species:
            breach = _resource_wall(
                plan.limits,
                started=started_monotonic,
                completed_calls=calls,
            )
            if breach is not None:
                record = journal.incomplete(breach)
                return ExecutionReport(record, None, None)
            cap = plan.limits.max_species_calls
            if cap is not None and calls >= cap:
                record = journal.incomplete(
                    f"approved max_species_calls={cap} reached after {calls} completed calls"
                )
                return ExecutionReport(record, None, None)
            estimate = cached.energy(molecule)
            calls += 1
            admission_error = _execution_admission_error(
                approved,
                reaction,
                _admission_snapshot,
            )
            if admission_error is not None:
                return ExecutionReport(journal.invalid(admission_error), None, None)
            if estimate is None:
                observed_calculation = CalculationSpec.from_oracle(oracle)
                admission_error = _execution_admission_error(
                    approved,
                    reaction,
                    _admission_snapshot,
                )
                if admission_error is not None:
                    return ExecutionReport(journal.invalid(admission_error), None, None)
                if observed_calculation.digest != plan.calculation.digest:
                    raise RuntimeError(
                        "oracle CalculationSpec changed during an approved species call"
                    )
                record = journal.refused(
                    f"oracle declined endpoint species {species_signature(molecule)}"
                )
                return ExecutionReport(record, None, None)
            checkpoint = _estimate_artifact(
                "checkpoint:species:" + canonical_digest(molecule),
                "checkpoint",
                estimate,
            )
            journal.add_checkpoint(checkpoint)
            journal.add_artifact(
                replace(
                    checkpoint,
                    artifact_id="intermediate:species:" + canonical_digest(molecule),
                    kind="intermediate",
                )
            )
            observed_calculation = CalculationSpec.from_oracle(oracle)
            admission_error = _execution_admission_error(
                approved,
                reaction,
                _admission_snapshot,
            )
            if admission_error is not None:
                return ExecutionReport(journal.invalid(admission_error), None, None)
            if observed_calculation.digest != plan.calculation.digest:
                raise RuntimeError(
                    "oracle CalculationSpec changed during an approved species call"
                )
            breach = _resource_wall(
                plan.limits,
                started=started_monotonic,
                completed_calls=calls,
            )
            if breach is not None:
                record = journal.incomplete(breach)
                return ExecutionReport(record, None, None)

        estimate = reaction_energy(reaction, cached)
        emitted: tuple[str, ...] = ()
        if estimate is not None:
            observable = _estimate_artifact(
                "observable:reaction_energy",
                "observable",
                estimate,
            )
            journal.add_artifact(observable)
            emitted = ("reaction_energy",)

        journal.add_cache_state(
            f"in-memory canonical cache: hits={cached.hits}, misses={cached.misses}, "
            f"distinct_species={cached.distinct_species}"
        )

        for obligation in plan.request.obligations:
            if obligation.stage is not ObligationStage.POST:
                continue
            result = _post_result(
                obligation,
                estimate,
                emitted,
                plan.request.output_contract.observable_ids,
            )
            journal.add_obligation_result(result)
            if obligation.required and result.outcome is not ObligationOutcome.PASS:
                record = journal.invalid(
                    f"postcondition {obligation.name} ended {result.outcome.value}: "
                    f"{result.detail}"
                )
                return ExecutionReport(record, None, None)

        if estimate is None:
            record = journal.refused("oracle declined the endpoint reaction energy")
            return ExecutionReport(record, None, None)

        # The certificate is prepared from the still-running record, then its digest is
        # inventoried before the run becomes COMPLETE.  It intentionally does not contain
        # the RunRecord digest, avoiding a certificate<->record digest cycle.
        admission_error = _execution_admission_error(
            approved,
            reaction,
            _admission_snapshot,
        )
        if admission_error is not None:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        certificate = Certificate(
            source_digest=plan.request.source.digest,
            request_digest=plan.request.digest,
            plan_digest=plan.digest,
            approval_digest=approved.approval.digest,
            calculation_digest=actual_calculation.digest,
            compiler_implementation_digest=plan.compiler_implementation_digest,
            run_id=journal.record.run_id,
            run_status=RunStatus.COMPLETE,
            claim_scope=plan.request.physical_ir.claim_scope,
            evidence_status=plan.request.physical_ir.evidence_status,
            validity_results=journal.record.obligation_results,
            output_inventory=emitted,
            casualties=plan.request.physical_ir.claim_scope.exclusions,
            omissions=(),
            failures=(),
        )
        journal.add_artifact(
            Artifact(
                artifact_id="certificate",
                kind="certificate",
                content_digest=certificate.digest,
                complete=True,
                quarantined=False,
                payload=certificate,
            )
        )
        record = journal.complete()
        if record.status is not RunStatus.COMPLETE:
            return ExecutionReport(record, None, None)
        value = ObservableValue(
            observable_id="reaction_energy",
            value=estimate.value_ev,
            unit="eV",
            uncertainty=estimate.uncertainty_ev,
            method=estimate.method,
            support=plan.request.output_contract.observables[0].support,
            seconds=estimate.seconds,
            notes=estimate.notes,
            systematic_ev=estimate.systematic_ev,
            methods=tuple(sorted(estimate.methods or ())),
            systematic_terms=tuple(estimate.systematic_terms or ()),
        )
        result = SimulationResult(record.run_id, (value,), certificate.digest)
        return ExecutionReport(record, result, certificate)
    except Exception as error:
        admission_error = _execution_admission_error(
            approved,
            reaction,
            _admission_snapshot,
        )
        if admission_error is not None and journal.record.status is RunStatus.RUNNING:
            return ExecutionReport(journal.invalid(admission_error), None, None)
        if journal.record.status is RunStatus.RUNNING:
            record = journal.failed(f"{type(error).__name__}: {error}")
            return ExecutionReport(record, None, None)
        raise
