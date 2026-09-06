"""ProcessObservationIR -- a read-only evidence-ingress sibling of the SmartChem compiler.

Chemistry-creator footage (NileRed, Applied Science, ...) and institutional/metrology sources are a
source of SCOPED OPERATIONAL OBSERVATIONS, never a recipe corpus.  This subpackage records what one
source actually shows or states about one run, under one context, with explicit gaps -- and reframes
the poor-man buckets as whole-path capability bundles (material / capability / verification / closure
/ scale) evaluated fail-closed.

What it is **not**: a procedure generator, a safety clearance, a tenth executor, or a claim that any
route is safe/practical/legal.  Like :mod:`smartchem.evidence`, it reuses
:mod:`smartchem.contracts` digest primitives and reads :class:`ReactionDirection`, but it never
enters the closed executor registry, never mutates a compiler record, and is never imported back by
the compiler.  See ``docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md`` for the full
contract, invariants, and acceptance probes.

P1 (this subpackage): the immutable IR + source-fragment validation + the read-only capability-bucket
findings and projection readout.  P2/P3 (reviewed transport bridges, a ``BenchCapability`` passport,
a verified operation graph) are later work and deliberately absent here.
"""
from __future__ import annotations

from .process_observation import (
    PROCESS_OBSERVATION_SCHEMA,
    BucketFinding,
    BucketStatus,
    CapabilityBucket,
    ClaimStatus,
    ContextScope,
    FrankenprocedureError,
    ObservationClaim,
    ObservationPhase,
    ProcessObservationIR,
    ProjectionDisposition,
    ProjectionReadout,
    SourceFragment,
    SourceRole,
    Transport,
    TransportDisposition,
    capability_bundle,
    capability_hard_blockers,
    merge_observations,
    operationally_complete,
    projection_gate,
)
from .observability import (
    OBSERVABILITY_SCHEMA,
    OBSERVABLE_SIGNATURES,
    ObservabilityAxis,
    ObservabilityProfile,
    ObservableModality,
    ObservableSignature,
    SignalCost,
    observability_dominates,
    observability_frontier,
    observability_profile,
    observation_corroborates,
    signatures_for,
)

__all__ = [
    "OBSERVABILITY_SCHEMA",
    "OBSERVABLE_SIGNATURES",
    "ObservabilityAxis",
    "ObservabilityProfile",
    "ObservableModality",
    "ObservableSignature",
    "SignalCost",
    "observability_dominates",
    "observability_frontier",
    "observability_profile",
    "observation_corroborates",
    "signatures_for",
    "PROCESS_OBSERVATION_SCHEMA",
    "BucketFinding",
    "BucketStatus",
    "CapabilityBucket",
    "ClaimStatus",
    "ContextScope",
    "FrankenprocedureError",
    "ObservationClaim",
    "ObservationPhase",
    "ProcessObservationIR",
    "ProjectionDisposition",
    "ProjectionReadout",
    "SourceFragment",
    "SourceRole",
    "Transport",
    "TransportDisposition",
    "capability_bundle",
    "capability_hard_blockers",
    "merge_observations",
    "operationally_complete",
    "projection_gate",
]
