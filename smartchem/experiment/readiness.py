"""v0.8 Real Route Dossiers -- the pure readiness-obligation evaluator (Writer 1's one job).

Ugh, okay, so: this is the module that stops the compiler from cosplaying as a bench chemist.
Before 0.8, every route's ``readiness_tier`` was a hard-coded ``FORMAL_CANDIDATE`` -- a wall, not
a measurement. This replaces the wall with an honest ladder: a set of independently-visible
OBLIGATIONS (did we recognize the reaction type? do we have sourced conditions? a sourced,
COMPLETE process description? a described workup?), each read off facts that already exist on a
built :class:`~smartchem.experiment.step.ExperimentStep` -- never re-derived, never guessed, never
laundered from a stronger-sounding neighbor.

The one rule that matters (frozen contract, plan `docs/research/V0_8_REAL_ROUTE_DOSSIERS_PLAN_v0.1.md`
Secs 3/4/8): **the obligations are the truth; the coarse ``tier`` is a derived, cumulative,
conservative PROJECTION of them.** A step can carry ``conditions=SATISFIED`` while its tier is
only ``FORMAL_CANDIDATE`` -- because ``reaction_type`` is unrecognized -- and that is not a bug to
patch, it is the design working (Sec 4.1's non-monotonicity finding: paracetamol's anhydride step
is the best-sourced record in the corpus and the worst-recognized reaction). Never derive an
obligation FROM the tier; only ever derive the tier FROM the obligations.

This module is a pure function of its inputs. It does not run search, mutate anything, touch the
network, or read a single byte of ``RouteFit``/``Composability``/feasibility/equilibrium/kinetics/
selectivity/``ProcessFit``/``fit_status`` -- readiness is orthogonal to bench-fit and to chemical
favorability, on purpose (Sec 2's non-negotiable law: recognized-reaction-type never implies
conditions-known; a favorable route never implies a described procedure).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from ..contracts import Digestible

if TYPE_CHECKING:
    from ..identity import IdentityLoss
    from ..process_constraints import ProcessRequirements
    from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "ObligationStatus",
    "StepReadiness",
    "RouteReadiness",
    "FORMAL_CANDIDATE",
    "REACTION_VOUCHED",
    "CONDITIONS_SUPPORTED",
    "PROCESS_SPECIFIED",
    "READINESS_TIERS",
    "tier_rank",
    "min_tier",
    "process_representation_is_complete",
    "evaluate_step",
    "evaluate_route",
]


class ObligationStatus(str, Enum):
    """Whether one readiness obligation is discharged for a step -- a truth axis, not a strength
    axis (that is :class:`~smartchem.contracts.EvidenceStatus`) and not a bench-fit axis (that is
    :class:`~smartchem.process_constraints.ProcessFitStatus`). Deliberately its own enum so a
    reviewer can never confuse "sourced enough to be EXPERIMENTAL" with "the obligation this
    record needed to discharge is discharged"."""

    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


#: The total order of coarse readiness tiers (weakest first). Cumulative: a step earns tier N only
#: by first earning every tier below it (Sec 4). ``PROCESS_SPECIFIED`` is defined but DARK this
#: round (Sec 5) -- no record meets :func:`process_representation_is_complete`, so nothing built
#: today reaches it; it stays in the vocabulary so a future round can light it up without a
#: renegotiated wire format.
FORMAL_CANDIDATE = "FORMAL_CANDIDATE"
REACTION_VOUCHED = "REACTION_VOUCHED"
CONDITIONS_SUPPORTED = "CONDITIONS_SUPPORTED"
PROCESS_SPECIFIED = "PROCESS_SPECIFIED"

READINESS_TIERS: tuple[str, ...] = (
    FORMAL_CANDIDATE, REACTION_VOUCHED, CONDITIONS_SUPPORTED, PROCESS_SPECIFIED,
)
_TIER_RANK = {name: rank for rank, name in enumerate(READINESS_TIERS)}


def tier_rank(tier: str) -> int:
    """The tier's position in the total order (higher = stronger). Raises on an unknown tier name
    rather than silently ranking a typo as the weakest tier."""
    return _TIER_RANK[tier]


def min_tier(tiers: Iterable[str]) -> str:
    """The weakest tier among ``tiers`` -- route aggregation is a weakest-link ``min``, never an
    "any step is enough" ``max`` (an unready step must cap the whole route)."""
    names = list(tiers)
    if not names:
        raise ValueError("min_tier needs at least one tier")
    return min(names, key=tier_rank)


def process_representation_is_complete(process: "ProcessRequirements | None") -> bool:
    """Whether ``process`` is a COMPLETE bench-procedure representation -- the sufficient predicate
    for the ``process`` obligation (Sec 5, FROZEN: DARK this round).

    ``ProcessRequirements.is_sourced`` is necessary but not remotely sufficient: today's typed
    record has no structured field for scale/amounts/assay, addition order or rate, a reaction
    endpoint, a quench step, purification (distinct from ``workup_included``), analytical/
    acceptance criteria, waste routing, equipment PRESSURE/TEMPERATURE ratings (only whole-step
    extrema are declared), or emergency controls -- all of it lives, if anywhere, as unstructured
    free-text ``provenance``. So: always ``False``. Not "false until we get around to it" -- false
    because the fields this predicate would need to inspect do not exist yet. The day they do,
    this is the one place that flips, and every caller downstream just starts telling the truth.
    """
    return False


def _blocked_on_conditions(identity_losses: "Iterable[IdentityLoss]") -> "IdentityLoss | None":
    """The first identity loss (if any) that BLOCKS the ``"conditions"`` claim -- section 5.3's
    "a sourced condition must not survive a loss marked BLOCKER for its matching key" rule, read
    the honest way round: a flattened stereocenter/isotope/local-charge distinction can silently
    invalidate a condition record that was written for a different (unflattened) species."""
    for loss in identity_losses:
        if loss.blocks("conditions"):
            return loss
    return None


def _reaction_type_obligation(step: "ExperimentStep") -> tuple[ObligationStatus, str | None]:
    from .reaction_type_oracle import recognize_reaction_type

    try:
        klass = recognize_reaction_type(step)
    except Exception:
        # belt-and-suspenders: recognize_reaction_type is already total/fail-closed (never raises,
        # never "refutes"), but a recognizer fault must demote here too, never spuriously vouch.
        klass = None
    status = ObligationStatus.SATISFIED if klass is not None else ObligationStatus.UNSATISFIED
    return status, klass


def _conditions_obligation(
    step: "ExperimentStep", identity_losses: "Iterable[IdentityLoss]",
) -> tuple[ObligationStatus, str | None, str | None]:
    """Returns ``(status, provenance_locator_or_None, open_obligation_reason_or_None)``."""
    envelope = step.envelope
    if envelope.is_sourced:
        status = ObligationStatus.SATISFIED
    elif envelope.is_declared:
        status = ObligationStatus.UNSATISFIED
    else:
        status = ObligationStatus.UNKNOWN

    blocker = _blocked_on_conditions(identity_losses)
    if blocker is not None:
        # The identity-loss blocker CAPS conditions regardless of how well-sourced the envelope
        # looked -- a sourced record for the unflattened species does not license the flattened one.
        status = ObligationStatus.UNSATISFIED
        return (
            status,
            None,
            f"conditions: blocked by identity loss '{blocker.feature}' -- {blocker.reason}",
        )

    if status is ObligationStatus.SATISFIED:
        locator = envelope.source.locator if envelope.source is not None else None
        return status, locator, None
    if status is ObligationStatus.UNSATISFIED:
        return status, None, "conditions: declared but not backed by an accepted source citation"
    return status, None, "conditions: no declared condition envelope (unknown)"


def _process_and_workup_obligations(
    step: "ExperimentStep",
) -> tuple[ObligationStatus, ObligationStatus, str | None, tuple[str, ...]]:
    """Returns ``(process_status, workup_status, provenance_locator_or_None, open_obligations)``."""
    process = step.envelope.process
    open_obligations: list[str] = []
    if process is None:
        return (
            ObligationStatus.UNKNOWN, ObligationStatus.UNKNOWN, None,
            (
                "process: no declared process requirements (unknown)",
                "workup_isolation: no declared process requirements (unknown)",
            ),
        )

    if process_representation_is_complete(process):
        process_status = ObligationStatus.SATISFIED
        provenance = process.source.locator if process.source is not None else None
    else:
        process_status = ObligationStatus.UNSATISFIED
        provenance = None
        note = (
            "process: declared but not a complete bench-procedure representation (scale/addition/"
            "endpoint/quench/purification/analytical-acceptance/waste/equipment-ratings not "
            "structurally represented)"
        )
        if process.is_sourced:
            # is_sourced is necessary-not-sufficient (process_constraints.py); say so, but it does
            # NOT earn provenance -- provenance is reserved for axes that actually reached SATISFIED.
            note += "; the record IS source-backed, which is necessary but not sufficient"
        open_obligations.append(note)

    workup_status = (
        ObligationStatus.SATISFIED if process.workup_included else ObligationStatus.UNSATISFIED
    )
    if workup_status is ObligationStatus.UNSATISFIED:
        open_obligations.append("workup_isolation: process record declares workup_included=False")

    return process_status, workup_status, provenance, tuple(open_obligations)


def evaluate_step(
    step: "ExperimentStep", *, identity_losses: "tuple[IdentityLoss, ...]" = (),
) -> "StepReadiness":
    """Evaluate the readiness obligations of one already-built ``step``, from facts alone.

    Never re-derives chemistry, never reruns search, never mutates ``step``. ``identity_losses``
    is the route's already-computed loss tuple (Sec 4's identity-loss blocker on ``conditions``);
    pass ``()`` when there are none (the overwhelming majority of today's corpus).
    """
    formal_candidate = ObligationStatus.SATISFIED  # step.__post_init__ already ran the conservation cert

    reaction_type, reaction_class_name = _reaction_type_obligation(step)
    conditions, conditions_locator, conditions_obligation = _conditions_obligation(
        step, identity_losses,
    )
    process, workup_isolation, process_locator, process_obligations = (
        _process_and_workup_obligations(step)
    )

    provenance = tuple(
        sorted(loc for loc in (conditions_locator, process_locator) if loc is not None)
    )
    open_obligations: list[str] = []
    if reaction_type is not ObligationStatus.SATISFIED:
        open_obligations.append(
            "reaction_type: not recognized by the production oracle"
            if reaction_type is ObligationStatus.UNSATISFIED
            else "reaction_type: unknown"
        )
    if conditions_obligation is not None:
        open_obligations.append(conditions_obligation)
    open_obligations.extend(process_obligations)

    return StepReadiness(
        formal_candidate=formal_candidate,
        reaction_type=reaction_type,
        reaction_class_name=reaction_class_name,
        conditions=conditions,
        process=process,
        workup_isolation=workup_isolation,
        provenance=provenance,
        open_obligations=tuple(sorted(set(open_obligations))),
    )


def evaluate_route(
    route: "ExperimentRoute", *, identity_losses: "tuple[IdentityLoss, ...]" = (),
) -> "RouteReadiness":
    """Evaluate every step of ``route`` with the SAME per-step evaluator and aggregate.

    ``identity_losses`` applies to the whole route (today's callers compute it once per route, not
    per step); every step sees the same tuple.
    """
    per_step = tuple(evaluate_step(step, identity_losses=identity_losses) for step in route.steps)
    route_open_obligations = tuple(
        sorted({reason for step_readiness in per_step for reason in step_readiness.open_obligations})
    )
    return RouteReadiness(per_step=per_step, route_open_obligations=route_open_obligations)


@dataclass(frozen=True)
class StepReadiness(Digestible):
    """One step's readiness obligations -- the source of truth (Sec 3). ``tier`` is DERIVED, never
    stored: storing it would let a caller construct an incoherent record (a tier claim unsupported
    by its own obligations), which is exactly the laundering path M11 exists to kill."""

    formal_candidate: ObligationStatus
    reaction_type: ObligationStatus
    reaction_class_name: "str | None"
    conditions: ObligationStatus
    process: ObligationStatus
    workup_isolation: ObligationStatus
    provenance: "tuple[str, ...]"
    open_obligations: "tuple[str, ...]"

    def __post_init__(self) -> None:
        for name in (
            "formal_candidate", "reaction_type", "conditions", "process", "workup_isolation",
        ):
            if not isinstance(getattr(self, name), ObligationStatus):
                raise TypeError(f"{name} must be an ObligationStatus")
        if self.reaction_class_name is not None and not isinstance(self.reaction_class_name, str):
            raise TypeError("reaction_class_name must be a str or None")
        if (self.reaction_type is ObligationStatus.SATISFIED) != (
            self.reaction_class_name is not None
        ):
            raise ValueError(
                "reaction_class_name must be set iff reaction_type is SATISFIED (no orphaned class "
                "name, no SATISFIED without a witness)"
            )
        for name in ("provenance", "open_obligations"):
            value = getattr(self, name)
            if type(value) is not tuple or any(type(item) is not str or not item for item in value):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
        if list(self.open_obligations) != sorted(self.open_obligations):
            raise ValueError("open_obligations must be in canonical (sorted) order")
        if len(set(self.open_obligations)) != len(self.open_obligations):
            raise ValueError("open_obligations must be distinct")

    @property
    def tier(self) -> str:
        """The cumulative coarse projection (Sec 4) -- derived FROM the obligations, never the
        reverse. Each rung requires every rung below it PLUS its own obligation."""
        if self.reaction_type is not ObligationStatus.SATISFIED:
            return FORMAL_CANDIDATE
        if self.conditions is not ObligationStatus.SATISFIED:
            return REACTION_VOUCHED
        if self.process is not ObligationStatus.SATISFIED:
            return CONDITIONS_SUPPORTED
        return PROCESS_SPECIFIED


@dataclass(frozen=True)
class RouteReadiness(Digestible):
    """A route's readiness: every step's obligations, plus the weakest-link coarse tier."""

    per_step: "tuple[StepReadiness, ...]"
    route_open_obligations: "tuple[str, ...]"

    def __post_init__(self) -> None:
        if type(self.per_step) is not tuple or not self.per_step or any(
            type(item) is not StepReadiness for item in self.per_step
        ):
            raise TypeError("per_step must be a non-empty tuple of StepReadiness values")
        if type(self.route_open_obligations) is not tuple or any(
            type(item) is not str or not item for item in self.route_open_obligations
        ):
            raise TypeError("route_open_obligations must be a tuple of non-empty strings")
        if list(self.route_open_obligations) != sorted(self.route_open_obligations):
            raise ValueError("route_open_obligations must be in canonical (sorted) order")
        if len(set(self.route_open_obligations)) != len(self.route_open_obligations):
            raise ValueError("route_open_obligations must be distinct")

    @property
    def tier(self) -> str:
        """The route's coarse tier: the MIN over its steps' tiers (Sec 4) -- a weakest-link
        aggregation, never an "any step is enough" one."""
        return min_tier(step.tier for step in self.per_step)
