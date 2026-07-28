"""Versioned StructureIR for exact observations of the S0 open-diagram quotient.

The mathematical structure represented here is deliberately narrow.  Its objects are
ordered electrical :class:`~smartchem.open_diagram.Interface` values and its morphisms are
finite typed open multigraphs modulo construction-local names and declaration order.
Composition is boundary gluing and tensor is disjoint union.

Raw :class:`~smartchem.open_diagram.OpenDiagram` values are presentations, not quotient
values: they retain edge declaration order so E1/E2 models can bind parameters exactly.
Consequently ``StructureIR`` contains only the canonical quotient observation.  A separate
``StructureAdapterWitness`` binds that observation to one raw presentation and its resource
budget.  Neither record owns constitutive parameters, evidence, solver settings, approval,
or task scheduling.

The underlying finite diagram operations are total.  Producing a canonical ``StructureIR``
is resource-bounded and may therefore refuse.  The methods below preserve that distinction;
they never turn a budget refusal into approximate or identifier-dependent equality.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import Digestible, canonical_digest
from .open_diagram import (
    BoundaryRef,
    BoundarySide,
    CanonicalDiagram,
    CanonicalizationBudgetExceeded,
    ComponentKind,
    ComponentSlot,
    DiagramConstructionError,
    ElementPortRef,
    Interface,
    Junction,
    OpenDiagram,
    PortKind,
    braid,
    canonicalize,
    identity,
)

__all__ = [
    "STRUCTURE_ADAPTER_SCHEMA",
    "STRUCTURE_ATTACHMENT_SCHEMA",
    "STRUCTURE_IR_SCHEMA",
    "StructureAdapterWitness",
    "StructureAttachment",
    "StructureIREdge",
    "StructureIR",
    "StructureObservationStatus",
    "adapt_open_diagram",
    "structure_attachment_for_subject",
    "structure_braid",
    "structure_identity",
    "validate_structure_attachment",
]


STRUCTURE_IR_SCHEMA = "smartchem.structure-ir/open-diagram-v1"
STRUCTURE_ADAPTER_SCHEMA = "smartchem.structure-adapter/s0-canonical-v1"
STRUCTURE_ATTACHMENT_SCHEMA = "smartchem.structure-attachment/plan-v1"

_RESISTIVE_DC_EXECUTOR = "smartchem.resistive_dc/exact-relation-sparse-mna-v1"
_RLC_AC_EXECUTOR = "smartchem.rlc_ac/positive-frequency-passive-rlc-v1"
_STRUCTURE_IR_TOKEN = object()


def _sha256(value: object, name: str) -> None:
    if type(value) is not str or len(value) != 64:
        raise TypeError(f"{name} must be a SHA-256 hexadecimal digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{name} must be hexadecimal") from error


class StructureObservationStatus(str, Enum):
    """Whether a plan has an exact S0 quotient observation."""

    OBSERVED = "OBSERVED"
    REFUSED = "REFUSED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, order=True)
class StructureIREdge(Digestible):
    """One canonical undirected component incidence in quotient node coordinates."""

    kind: ComponentKind
    node_a: int
    node_b: int

    def __post_init__(self) -> None:
        if type(self.kind) is not ComponentKind:
            raise TypeError("StructureIREdge.kind must be an exact ComponentKind")
        if (
            type(self.node_a) is not int
            or type(self.node_b) is not int
            or self.node_a < 0
            or self.node_b < 0
        ):
            raise TypeError("StructureIREdge nodes must be non-negative exact integers")
        if self.node_a > self.node_b:
            raise ValueError(
                "StructureIREdge endpoints must be in canonical undirected order"
            )


@dataclass(frozen=True, init=False)
class StructureIR(Digestible):
    """Exact, versioned value for one successfully observed S0 quotient morphism."""

    schema_version: str
    dom: Interface
    cod: Interface
    input_nodes: tuple[int, ...]
    output_nodes: tuple[int, ...]
    node_kinds: tuple[PortKind, ...]
    edges: tuple[StructureIREdge, ...]

    def __init__(
        self,
        schema_version: str,
        dom: Interface,
        cod: Interface,
        input_nodes: tuple[int, ...],
        output_nodes: tuple[int, ...],
        node_kinds: tuple[PortKind, ...],
        edges: tuple[StructureIREdge, ...],
        *,
        _token: object | None = None,
    ) -> None:
        if _token is not _STRUCTURE_IR_TOKEN:
            raise DiagramConstructionError(
                "StructureIR values are canonical; use from_canonical or "
                "from_open_diagram"
            )
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "dom", dom)
        object.__setattr__(self, "cod", cod)
        object.__setattr__(self, "input_nodes", input_nodes)
        object.__setattr__(self, "output_nodes", output_nodes)
        object.__setattr__(self, "node_kinds", node_kinds)
        object.__setattr__(self, "edges", edges)
        self.__post_init__()

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURE_IR_SCHEMA:
            raise ValueError(f"schema_version must be exactly {STRUCTURE_IR_SCHEMA!r}")
        if type(self.dom) is not Interface or type(self.cod) is not Interface:
            raise TypeError("StructureIR boundaries must be exact Interface values")
        for name in ("input_nodes", "output_nodes", "node_kinds", "edges"):
            if type(getattr(self, name)) is not tuple:
                raise TypeError(f"StructureIR.{name} must be an exact tuple")
        if len(self.input_nodes) != len(self.dom.ports):
            raise ValueError("StructureIR input nodes must match its domain")
        if len(self.output_nodes) != len(self.cod.ports):
            raise ValueError("StructureIR output nodes must match its codomain")
        if any(type(kind) is not PortKind for kind in self.node_kinds):
            raise TypeError("StructureIR.node_kinds must contain exact PortKind values")
        if any(type(edge) is not StructureIREdge for edge in self.edges):
            raise TypeError(
                "StructureIR.edges must contain exact StructureIREdge values"
            )
        if self.edges != tuple(
            sorted(
                self.edges, key=lambda edge: (edge.kind.value, edge.node_a, edge.node_b)
            )
        ):
            raise ValueError("StructureIR edges must be in canonical sorted order")

        node_count = len(self.node_kinds)
        for node in self.input_nodes + self.output_nodes:
            if type(node) is not int or not 0 <= node < node_count:
                raise ValueError("StructureIR boundary maps must name retained nodes")
        for index, kind in enumerate(self.dom.ports):
            if self.node_kinds[self.input_nodes[index]] is not kind:
                raise ValueError("StructureIR input kind does not match its node")
        for index, kind in enumerate(self.cod.ports):
            if self.node_kinds[self.output_nodes[index]] is not kind:
                raise ValueError("StructureIR output kind does not match its node")
        for edge in self.edges:
            if edge.node_b >= node_count:
                raise ValueError("StructureIR edge names an unknown node")
            if (
                self.node_kinds[edge.node_a] is not PortKind.ELECTRICAL
                or self.node_kinds[edge.node_b] is not PortKind.ELECTRICAL
            ):
                raise ValueError(
                    "StructureIR electrical edge has a non-electrical endpoint"
                )

        incidences = [0] * node_count
        for node in self.input_nodes + self.output_nodes:
            incidences[node] += 1
        for edge in self.edges:
            incidences[edge.node_a] += 1
            incidences[edge.node_b] += 1
        if any(count < 2 for count in incidences):
            raise ValueError(
                "every StructureIR node must retain at least two incidences"
            )

    @classmethod
    def _from_canonical_observation(cls, value: CanonicalDiagram) -> "StructureIR":
        """Encode a canonicalizer-produced observation without repeating its search."""
        if type(value) is not CanonicalDiagram:
            raise TypeError("value must be an exact CanonicalDiagram")
        edges: list[StructureIREdge] = []
        for item in value.edges:
            if type(item) is not tuple or len(item) != 4:
                raise TypeError("canonical diagram edges must be exact four-tuples")
            kind, label, node_a, node_b = item
            if label is not None:
                raise ValueError("StructureIR cannot own domain/model edge decorations")
            try:
                exact_kind = ComponentKind(kind)
            except ValueError as error:
                raise ValueError(
                    f"unknown canonical component kind {kind!r}"
                ) from error
            edges.append(StructureIREdge(exact_kind, node_a, node_b))
        return cls(
            STRUCTURE_IR_SCHEMA,
            value.dom,
            value.cod,
            value.input_nodes,
            value.output_nodes,
            value.node_kinds,
            tuple(edges),
            _token=_STRUCTURE_IR_TOKEN,
        )

    @classmethod
    def from_canonical(
        cls,
        value: CanonicalDiagram,
        *,
        verification_budget: int = 100_000,
    ) -> "StructureIR":
        """Import and revalidate one exact undecorated canonical S0 observation."""
        structure = cls._from_canonical_observation(value)
        observed = canonicalize(
            structure.to_normalized_open_diagram(),
            budget=verification_budget,
        )
        if observed != value:
            raise ValueError(
                "value is well formed but is not the exact canonical S0 form"
            )
        return structure

    @classmethod
    def from_open_diagram(
        cls,
        diagram: OpenDiagram,
        *,
        budget: int = 100_000,
    ) -> "StructureIR":
        """Observe a raw presentation exactly, or propagate the named budget refusal."""
        if type(diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        return cls._from_canonical_observation(canonicalize(diagram, budget=budget))

    def to_canonical_diagram(self) -> CanonicalDiagram:
        """Decode the exact canonical S0 record; this is not a raw-presentation witness."""
        return CanonicalDiagram(
            self.dom,
            self.cod,
            self.input_nodes,
            self.output_nodes,
            self.node_kinds,
            tuple(
                (edge.kind.value, None, edge.node_a, edge.node_b) for edge in self.edges
            ),
        )

    def to_normalized_open_diagram(self) -> OpenDiagram:
        """Build one normalized presentation.

        This presentation is suitable for quotient operations.  It must not replace an
        E1/E2 subject presentation or its declaration-index model binding.
        """
        components = tuple(
            ComponentSlot(f"component-{index}", edge.kind)
            for index, edge in enumerate(self.edges)
        )
        endpoints: list[list[BoundaryRef | ElementPortRef]] = [
            [] for _ in self.node_kinds
        ]
        for index, node in enumerate(self.input_nodes):
            endpoints[node].append(BoundaryRef(BoundarySide.INPUT, index))
        for index, node in enumerate(self.output_nodes):
            endpoints[node].append(BoundaryRef(BoundarySide.OUTPUT, index))
        for index, edge in enumerate(self.edges):
            component_id = components[index].component_id
            endpoints[edge.node_a].append(ElementPortRef(component_id, "a"))
            endpoints[edge.node_b].append(ElementPortRef(component_id, "b"))
        junctions = tuple(
            Junction(f"node-{index}", kind, tuple(endpoints[index]))
            for index, kind in enumerate(self.node_kinds)
        )
        return OpenDiagram.build(self.dom, self.cod, components, junctions)

    def then(
        self,
        other: "StructureIR",
        *,
        budget: int = 100_000,
    ) -> "StructureIR":
        """Compose quotient morphisms through S0 gluing and exact re-observation."""
        if type(other) is not StructureIR:
            raise TypeError("other must be an exact StructureIR")
        return StructureIR.from_open_diagram(
            self.to_normalized_open_diagram().then(other.to_normalized_open_diagram()),
            budget=budget,
        )

    def tensor(
        self,
        other: "StructureIR",
        *,
        budget: int = 100_000,
    ) -> "StructureIR":
        """Tensor quotient morphisms through disjoint union and exact re-observation."""
        if type(other) is not StructureIR:
            raise TypeError("other must be an exact StructureIR")
        return StructureIR.from_open_diagram(
            self.to_normalized_open_diagram().tensor(
                other.to_normalized_open_diagram()
            ),
            budget=budget,
        )


def structure_identity(interface: Interface, *, budget: int = 100_000) -> StructureIR:
    """Identity in the resource-bounded StructureIR representation."""
    return StructureIR.from_open_diagram(identity(interface), budget=budget)


def structure_braid(
    left: Interface,
    right: Interface,
    *,
    budget: int = 100_000,
) -> StructureIR:
    """Symmetry in the resource-bounded StructureIR representation."""
    return StructureIR.from_open_diagram(braid(left, right), budget=budget)


@dataclass(frozen=True)
class StructureAdapterWitness(Digestible):
    """Presentation-specific evidence for one attempted S0-to-StructureIR observation."""

    schema_version: str
    source_presentation_digest: str
    canonicalization_budget: int
    status: StructureObservationStatus
    structure_ir_digest: str | None
    refusal_reason: str

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURE_ADAPTER_SCHEMA:
            raise ValueError(
                f"schema_version must be exactly {STRUCTURE_ADAPTER_SCHEMA!r}"
            )
        _sha256(self.source_presentation_digest, "source_presentation_digest")
        if (
            type(self.canonicalization_budget) is not int
            or self.canonicalization_budget < 0
        ):
            raise TypeError(
                "canonicalization_budget must be a non-negative exact integer"
            )
        if type(self.status) is not StructureObservationStatus or self.status not in (
            StructureObservationStatus.OBSERVED,
            StructureObservationStatus.REFUSED,
        ):
            raise TypeError("adapter witness status must be OBSERVED or REFUSED")
        if type(self.refusal_reason) is not str:
            raise TypeError("refusal_reason must be a string")
        if self.status is StructureObservationStatus.OBSERVED:
            _sha256(self.structure_ir_digest, "structure_ir_digest")
            if self.refusal_reason:
                raise ValueError(
                    "an observed adapter witness cannot carry a refusal reason"
                )
        elif self.structure_ir_digest is not None or not self.refusal_reason:
            raise ValueError(
                "a refused adapter witness needs a reason and no StructureIR digest"
            )

    def verify(self, diagram: OpenDiagram, structure: StructureIR | None) -> None:
        """Recompute and validate this witness against one exact presentation."""
        if type(diagram) is not OpenDiagram:
            raise TypeError("diagram must be an exact OpenDiagram")
        if canonical_digest(diagram) != self.source_presentation_digest:
            raise ValueError("adapter witness is bound to a different S0 presentation")
        observed, witness = adapt_open_diagram(
            diagram,
            budget=self.canonicalization_budget,
        )
        if witness != self or observed != structure:
            raise ValueError("adapter witness does not match a fresh exact observation")


def adapt_open_diagram(
    diagram: OpenDiagram,
    *,
    budget: int,
) -> tuple[StructureIR | None, StructureAdapterWitness]:
    """Return an exact quotient observation and witness, or a typed budget refusal."""
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be an exact OpenDiagram")
    if type(budget) is not int or budget < 0:
        raise TypeError("budget must be a non-negative exact integer")
    presentation_digest = canonical_digest(diagram)
    if budget < 1:
        return None, StructureAdapterWitness(
            STRUCTURE_ADAPTER_SCHEMA,
            presentation_digest,
            budget,
            StructureObservationStatus.REFUSED,
            None,
            "canonicalization-budget-exhausted",
        )
    try:
        structure = StructureIR.from_open_diagram(diagram, budget=budget)
    except CanonicalizationBudgetExceeded:
        return None, StructureAdapterWitness(
            STRUCTURE_ADAPTER_SCHEMA,
            presentation_digest,
            budget,
            StructureObservationStatus.REFUSED,
            None,
            "canonicalization-budget-exceeded",
        )
    return structure, StructureAdapterWitness(
        STRUCTURE_ADAPTER_SCHEMA,
        presentation_digest,
        budget,
        StructureObservationStatus.OBSERVED,
        structure.digest,
        "",
    )


@dataclass(frozen=True)
class StructureAttachment(Digestible):
    """Plan-bound statement of S0 structure contact, refusal, or non-applicability."""

    schema_version: str
    subject_digest: str
    status: StructureObservationStatus
    structure: StructureIR | None
    witness: StructureAdapterWitness | None
    reason: str

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURE_ATTACHMENT_SCHEMA:
            raise ValueError(
                f"schema_version must be exactly {STRUCTURE_ATTACHMENT_SCHEMA!r}"
            )
        _sha256(self.subject_digest, "subject_digest")
        if type(self.status) is not StructureObservationStatus:
            raise TypeError("status must be an exact StructureObservationStatus")
        if type(self.reason) is not str:
            raise TypeError("reason must be a string")
        if self.status is StructureObservationStatus.NOT_APPLICABLE:
            if (
                self.structure is not None
                or self.witness is not None
                or not self.reason
            ):
                raise ValueError(
                    "NOT_APPLICABLE attachments need a reason and no S0 records"
                )
            return
        if type(self.witness) is not StructureAdapterWitness:
            raise TypeError("S0 attachments must retain an exact adapter witness")
        if self.status is StructureObservationStatus.OBSERVED:
            if type(self.structure) is not StructureIR or self.reason:
                raise ValueError(
                    "OBSERVED attachments need an exact StructureIR and no reason"
                )
            if self.witness.status is not StructureObservationStatus.OBSERVED:
                raise ValueError("attachment and witness observation statuses differ")
            if self.witness.structure_ir_digest != self.structure.digest:
                raise ValueError(
                    "adapter witness does not identify the attached StructureIR"
                )
            return
        if self.status is StructureObservationStatus.REFUSED:
            if self.structure is not None or not self.reason:
                raise ValueError(
                    "REFUSED attachments need a reason and no StructureIR value"
                )
            if (
                self.witness.status is not StructureObservationStatus.REFUSED
                or self.witness.refusal_reason != self.reason
            ):
                raise ValueError("attachment and witness refusal records differ")
            return
        raise ValueError("unknown StructureAttachment status")


def structure_attachment_for_subject(
    executor_id: str,
    subject: object,
) -> StructureAttachment:
    """Derive the sole plan attachment for one registry-validated exact subject."""
    if type(executor_id) is not str or not executor_id:
        raise TypeError("executor_id must be a non-empty exact string")
    subject_digest = canonical_digest(subject)
    if executor_id == _RESISTIVE_DC_EXECUTOR:
        from .resistive_dc_schema import ResistiveDCSubject

        if type(subject) is not ResistiveDCSubject:
            raise TypeError("resistive-DC attachment requires exact ResistiveDCSubject")
        diagram = subject.diagram
        budget = subject.canonicalization_budget
    elif executor_id == _RLC_AC_EXECUTOR:
        from .rlc_ac_schema import RLCACSubject

        if type(subject) is not RLCACSubject:
            raise TypeError("RLC-AC attachment requires exact RLCACSubject")
        diagram = subject.diagram
        budget = subject.canonicalization_budget
    else:
        return StructureAttachment(
            STRUCTURE_ATTACHMENT_SCHEMA,
            subject_digest,
            StructureObservationStatus.NOT_APPLICABLE,
            None,
            None,
            "executor subject is not represented by the S0 electrical open-diagram kernel",
        )

    structure, witness = adapt_open_diagram(diagram, budget=budget)
    if structure is None:
        return StructureAttachment(
            STRUCTURE_ATTACHMENT_SCHEMA,
            subject_digest,
            StructureObservationStatus.REFUSED,
            None,
            witness,
            witness.refusal_reason,
        )
    return StructureAttachment(
        STRUCTURE_ATTACHMENT_SCHEMA,
        subject_digest,
        StructureObservationStatus.OBSERVED,
        structure,
        witness,
        "",
    )


def validate_structure_attachment(
    executor_id: str,
    subject: object,
    attachment: StructureAttachment,
) -> None:
    """Reject missing, foreign, stale, nominal, or forged plan attachments."""
    if type(attachment) is not StructureAttachment:
        raise TypeError("plan must retain an exact StructureAttachment")
    expected = structure_attachment_for_subject(executor_id, subject)
    if attachment != expected:
        raise ValueError(
            "plan StructureAttachment differs from the exact subject/adapter observation"
        )
