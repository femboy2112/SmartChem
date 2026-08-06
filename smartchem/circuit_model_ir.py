"""Fused presentation-invariant identity of one decorated circuit (M-1a).

A :class:`CircuitModelIR` is the single value that answers "which circuit is this?"
for a decorated open-diagram model, independently of how the circuit happened to be
drawn.  Until now three faces of that answer lived apart:

* the **undecorated topology quotient** -- a :class:`~smartchem.structure_ir.StructureIR`
  plus the :class:`~smartchem.structure_ir.StructureAdapterWitness` that proves it was
  observed from a real presentation.  This is the exact face the plan seam already carries
  in a :class:`~smartchem.structure_ir.StructureAttachment`;
* the **decorated canonical form** -- the topology *and* the exact R/L/C decorations,
  carried together through the bounded alpha-invariant canonicalizer as
  declaration-aligned edge labels.  Its digest is the presentation-invariant
  **circuit identity**;
* the **explicit permutation witness** -- the model's own
  :class:`~smartchem.rlc_ac_schema.RLCEdgeBinding` tuple, retained verbatim so the map
  from model-declaration order to structural-edge order is an *explicit witness*, never
  an implicit reindex.

``smartchem.rlc_ac.analyze_rlc_ac`` already computes both canonical forms inline and
drops them, unnamed, into an :class:`~smartchem.rlc_ac_schema.RLCACAnalysis`; and it does
so *without* ever building a ``StructureIR`` -- so the plan-seam topology face and the
analysis topology face are two parallel worlds.  This module reconciles them into one
reusable, digest-round-trippable value, and reuses
:meth:`~smartchem.rlc_ac_schema.RLCModel.canonical_edge_labels` so the decorated form here
is *byte-identical* to the one the analysis pipeline produces (the stated M-1a congruence
risk, closed by reuse rather than a parallel implementation).

**Invariance contract (the reason this type exists).**  Two presentations of one circuit
-- alpha-renamed, junctions reordered, edges or model components declared in a different
order with compensating ``RLCEdgeBinding`` witnesses -- produce the SAME
:attr:`~CircuitModelIR.circuit_identity` and the SAME
:attr:`~CircuitModelIR.topology_identity`.  A genuine topology change, a changed decoration
value, or a changed element kind produces a different circuit identity; a topology change
also moves the topology identity, while a pure value/kind change does not (the undecorated
face is blind to parameters, by construction).  Nothing here solves, approximates, or
touches a numerical solver -- it is exact and presentation-only.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import Digestible, canonical_digest
from .open_diagram import CanonicalDiagram, OpenDiagram, canonicalize
from .rlc_ac_schema import RLCEdgeBinding, RLCModel
from .structure_ir import (
    StructureAdapterWitness,
    StructureIR,
    StructureObservationStatus,
    adapt_open_diagram,
)

__all__ = [
    "CIRCUIT_MODEL_IR_SCHEMA",
    "CircuitModelIR",
    "CircuitModelIRError",
    "observe_circuit_model_ir",
]

CIRCUIT_MODEL_IR_SCHEMA = "smartchem.circuit-model-ir/decorated-open-diagram-v1"


class CircuitModelIRError(ValueError):
    """A decorated circuit could not be observed as an exact fused identity."""


def _structure_degree_sequence(structure: StructureIR) -> tuple[int, ...]:
    """Sorted node-incidence multiset of a StructureIR (boundary maps count as incidences).

    This mirrors the incidence accounting in ``StructureIR.__post_init__`` exactly, so the
    two faces are compared on the same definition of a node's degree.
    """
    incidences = [0] * len(structure.node_kinds)
    for node in structure.input_nodes + structure.output_nodes:
        incidences[node] += 1
    for edge in structure.edges:
        incidences[edge.node_a] += 1
        incidences[edge.node_b] += 1
    return tuple(sorted(incidences))


def _decorated_degree_sequence(decorated: CanonicalDiagram) -> tuple[int, ...]:
    """Sorted node-incidence multiset of a decorated CanonicalDiagram (boundaries count)."""
    incidences = [0] * len(decorated.node_kinds)
    for node in decorated.input_nodes + decorated.output_nodes:
        incidences[node] += 1
    for _kind, _label, node_a, node_b in decorated.edges:
        incidences[node_a] += 1
        incidences[node_b] += 1
    return tuple(sorted(incidences))


@dataclass(frozen=True)
class CircuitModelIR(Digestible):
    """One decorated circuit's exact, presentation-invariant fused identity.

    The value's own :attr:`digest` covers every field, including the presentation-specific
    provenance (which raw presentation the adapter witness is bound to, and the model's
    declaration-order permutation), so it distinguishes *how* a circuit was fused.  The
    presentation-invariant answers are the two derived identities:
    :attr:`circuit_identity` (topology + decorations) and :attr:`topology_identity`
    (topology alone).
    """

    schema_version: str
    structure: StructureIR
    decorated_canonical_form: CanonicalDiagram
    adapter_witness: StructureAdapterWitness
    edge_witness: tuple[RLCEdgeBinding, ...]

    def __post_init__(self) -> None:
        if self.schema_version != CIRCUIT_MODEL_IR_SCHEMA:
            raise ValueError(
                f"schema_version must be exactly {CIRCUIT_MODEL_IR_SCHEMA!r}"
            )
        if type(self.structure) is not StructureIR:
            raise TypeError("structure must be an exact StructureIR")
        if type(self.decorated_canonical_form) is not CanonicalDiagram:
            raise TypeError(
                "decorated_canonical_form must be an exact CanonicalDiagram"
            )
        if type(self.adapter_witness) is not StructureAdapterWitness:
            raise TypeError("adapter_witness must be an exact StructureAdapterWitness")
        if type(self.edge_witness) is not tuple or any(
            type(x) is not RLCEdgeBinding for x in self.edge_witness
        ):
            raise TypeError("edge_witness must be an exact tuple of RLCEdgeBinding")

        # The witness must attest an OBSERVED quotient and name *this* topology face --
        # a forged or mismatched witness cannot ride along.
        if self.adapter_witness.status is not StructureObservationStatus.OBSERVED:
            raise ValueError("CircuitModelIR requires an OBSERVED adapter witness")
        if self.adapter_witness.structure_ir_digest != self.structure.digest:
            raise ValueError(
                "adapter witness does not identify the attached StructureIR"
            )

        edge_count = len(self.structure.edges)
        if (
            len(self.decorated_canonical_form.edges) != edge_count
            or len(self.edge_witness) != edge_count
        ):
            raise ValueError(
                "structure edges, decorated edges, and edge_witness must be equinumerous"
            )
        # edge_witness is a genuine permutation over both inventories (same law the model
        # itself enforces), so the model->structural map is total and injective.
        if (
            sorted(x.model_index for x in self.edge_witness) != list(range(edge_count))
            or sorted(x.structural_edge_index for x in self.edge_witness)
            != list(range(edge_count))
        ):
            raise ValueError(
                "edge_witness must permute the model and structural edge inventories exactly once"
            )

        # Necessary congruence between the two topology faces.  Both are derived from one
        # OpenDiagram in observe(), so full isomorphism holds by construction; these cheap
        # invariants catch a mispaired or foreign decorated form without re-running the
        # canonicalizer (which is itself the isomorphism oracle -- re-running it to "prove"
        # congruence would be circular).  The node numberings of the two faces may legitimately
        # differ: labels refine the WL colouring, so the decorated canonicalization can number
        # nodes differently from the undecorated one.  We therefore compare only face-invariant
        # quantities, never node indices.
        if (
            self.decorated_canonical_form.dom != self.structure.dom
            or self.decorated_canonical_form.cod != self.structure.cod
        ):
            raise ValueError("decorated form and structure disagree on boundaries")
        if len(self.decorated_canonical_form.node_kinds) != len(
            self.structure.node_kinds
        ):
            raise ValueError("decorated form and structure disagree on node count")
        # Degree-sequence (node-incidence multiset) congruence.  The two faces are two
        # canonicalizations of ONE topology under different node numberings (decorations
        # refine the WL colouring), so their node indices are not comparable -- but the
        # sorted multiset of node incidences is numbering-independent and identical for the
        # same topology, and it CAN differ for a mismatched pairing (unlike the edge-kind
        # multiset, which is a single-valued constant here and so could never go red).  This
        # is a necessary, not sufficient, congruence: it does not distinguish two distinct
        # topologies that happen to share a degree sequence.  Full topology congruence is a
        # construction invariant of ``observe_circuit_model_ir`` (both faces come from one
        # OpenDiagram); a hand-forged direct construction pairing a structure with a
        # different-topology decorated form of equal boundaries, node count, edge count, and
        # degree sequence is out of this guard's reach and is the direct constructor's caller
        # to keep honest.
        if _structure_degree_sequence(self.structure) != _decorated_degree_sequence(
            self.decorated_canonical_form
        ):
            raise ValueError(
                "decorated form and structure disagree on the node degree sequence"
            )
        # A decorated edge must actually carry its decoration; an unlabelled edge here would
        # mean the identity silently forgot a parameter.
        if any(edge[1] is None for edge in self.decorated_canonical_form.edges):
            raise ValueError("every decorated edge must carry a decoration label")

    @property
    def circuit_identity(self) -> str:
        """Presentation-invariant digest of the topology-and-decorations fused form.

        Equal across every presentation of the same decorated circuit; sensitive to any
        topology, element-kind, or exact-value change.  This is the "this circuit" key.
        """
        return canonical_digest(self.decorated_canonical_form)

    @property
    def topology_identity(self) -> str:
        """Presentation-invariant digest of the undecorated topology quotient alone.

        Equal across presentations *and* across circuits that share a wiring but differ in
        their R/L/C parameters -- the "same board, different parts" key.
        """
        return self.structure.digest


def observe_circuit_model_ir(
    diagram: OpenDiagram,
    model: RLCModel,
    *,
    budget: int = 100_000,
) -> CircuitModelIR:
    """Fuse one exact presentation and its RLC model into a ``CircuitModelIR``.

    Fails closed: if ``model`` is not bound to this exact presentation the model's own
    :meth:`~smartchem.rlc_ac_schema.RLCModel.validate_diagram` raises, and if the bounded
    canonicalizer refuses the topology (budget exhausted or exceeded) this raises
    :class:`CircuitModelIRError` carrying the adapter's refusal reason -- an unobservable
    topology has no identity, so no partially-built value is ever returned.
    """
    if type(diagram) is not OpenDiagram:
        raise TypeError("diagram must be an exact OpenDiagram")
    if type(model) is not RLCModel:
        raise TypeError("model must be an exact RLCModel")
    model.validate_diagram(diagram)
    structure, witness = adapt_open_diagram(diagram, budget=budget)
    if structure is None:
        raise CircuitModelIRError(
            f"topology is not observable for a fused identity: {witness.refusal_reason}"
        )
    decorated = canonicalize(
        diagram,
        budget=budget,
        edge_labels=model.canonical_edge_labels(),
    )
    return CircuitModelIR(
        CIRCUIT_MODEL_IR_SCHEMA,
        structure,
        decorated,
        witness,
        model.edge_bindings,
    )
