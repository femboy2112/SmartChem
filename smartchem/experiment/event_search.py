"""Bounded typed-event route search (#104 / #123 / #125) -- the 1.4 opt-in lateral/event frontier.

WHY THIS MODULE EXISTS (the obstruction, read across the three issues).
``search_routes`` (:mod:`smartchem.experiment.routes`) is a bounded retrosynthesis whose ONLY event is a
capped scission, and its termination rests on invariant **W1**: every precursor has *strictly fewer atoms*
than the target (``structure_descent.py`` enforces ``len(product.atoms) < len(reactant.atoms)``).  Two
independent walls follow (the coverage audit's W0.1 and #125):

* **#104 -- the rank wall.**  A rank-FLAT isomerization (a [3,3] sigmatropic shift, an electrocyclization)
  preserves atom count, so W1 is unsatisfiable for it; forcing one through the decompiler calls ``forget()``,
  which a :class:`~smartchem.lateral_rewrite.LateralRewriteEdge` refuses *by design*.  The sigmatropic /
  electrocyclic families are therefore oracle-VOUCHED (:mod:`smartchem.lateral_rewrite`) yet UNREACHABLE from
  the route search (#123 sub-gap a).
* **#125 -- the arity wall.**  Even with the rank relaxed, a ``CappedScission`` structurally requires >=2
  disconnected product components and a consumed mediator, so it can represent neither a connected 1->1
  rearrangement nor an intramolecular conversion that keeps its skeleton together and expels a coproduct.

THE TYPED-EVENT TAXONOMY (#125 acceptance clause 1 -- distinct typed classes, scission NOT overloaded).
This module keeps the strict scission contract untouched and classifies every search event into exactly one
of (:class:`EventType`):

* ``SCISSION`` -- assembled from >=2 strictly-smaller fragments (the inherited W1 grammar; rank-descending).
* ``CONNECTED_LATERAL`` -- a single connected precursor of the SAME atom count (a [3,3] sigmatropic or an
  electrocyclic ring open/close); rank-flat, reagentless, no coproduct.
* ``INTRAMOLECULAR_COPRODUCT`` -- a single connected principal precursor LARGER than the target, expelling a
  conserved coproduct (lactonization, Dieckmann, intramolecular aldol condensation).  **Representation
  DEFERRED** (the 2.0 reaction-event-calculus obligation): no generator in the repo emits such a transform
  today -- ``CappedScission``'s >=2-component contract (#125) structurally forbids it and no lateral family
  expels a coproduct -- so the search never yields one.  The category is DEFINED and :func:`classify_event`
  recognizes its shape (so the taxonomy is complete and the deferral is exhibited, not hand-waved), but it
  has ZERO producers here; wiring a generator for it is future work.  See the findings doc.

THE TERMINATION PROOF (#125 acceptance clause 4; the #104 "well-founded non-atom-count measure").  Termination
is OVERDETERMINED -- two independent well-founded measures each strictly decrease on every recursion edge.  Be
precise about which one the code OPERATIVELY enforces (d'Alembert's correction -- the prose matches the code):

* THE OPERATIVE BOUND (what the recursion actually enforces): ``max_depth - depth``.  EVERY recursion edge --
  SCISSION and CONNECTED_LATERAL alike -- recurses through ``_branch`` at ``depth + 1`` (a lateral hop costs a
  depth increment, not only a hop), and ``routes_making`` returns at ``depth > max_depth``.  So ``max_depth -
  depth`` strictly decreases on every edge and bounds the recursion depth; with finite branching at each node
  (``cut_budget`` bounds the scission candidates, ``lateral_match_budget`` x the family set bounds the lateral
  candidates) the whole search tree is finite.  This is the guard that halts the search in practice.

* THE INDEPENDENT CHEMICAL CERTIFICATE: the LEXICOGRAPHIC pair ``M(t, hops_left) = (len(t.atoms), hops_left)``
  on ``N x N``.  A SCISSION edge recurses onto a precursor with ``len < len(t.atoms)`` (W1) at the SAME
  ``hops_left`` (first component drops); a CONNECTED_LATERAL edge recurses onto an isomer of the SAME atom count
  with ``hops_left - 1`` (first component unchanged, second drops).  ``M`` strictly decreases on every edge, so
  the search would terminate even with ``max_depth`` UNBOUNDED -- a single monotone atom-count measure could not
  admit a rank-flat hop, but this lexicographic pair does, WITHOUT weakening W1 for scission.  ``M`` is what
  makes ``lateral_hops`` a meaningful COMPLETENESS parameter (a genuine per-route bound on lateral events)
  rather than a termination crutch.

CONSEQUENCE (stated so the prose does not hide it).  Because a lateral hop consumes a depth increment as well
as a hop, a route of k scissions plus a lateral whose COMBINED recursion depth exceeds ``max_depth`` is
unreachable even though ``M`` alone would admit it.  This is not silent: such a cut increments ``depth_truncated``
and the receipt reports ``complete == False`` (fail-closed).  The ISSUE-124 ancestor guard (inherited from
``search_routes``) additionally refuses a precursor equal to one of the branch's own non-stock ancestors, so a
rank-flat inverse cycle ``A -> B -> A`` is cut outright (belt and suspenders -- though ``M`` already kills it,
since every lateral hop spends a hop).

THE OPT-IN / REPLAY-INTEGRITY BOUNDARY (#125 acceptance clause 4; the V1_5 program's 1.4 scope).
``search_routes`` and its frozen :class:`RouteSearchReceipt` schema are **not touched** -- this is a separate
opt-in entry point with its own :class:`EventRouteSearchReceipt` (not part of the 1.0 replay surface).  A
CONNECTED_LATERAL step is assembled with ``ExperimentStep.from_transform(edge, envelope=None)``, the
``forget()``-FREE path (#123): a lateral edge NEVER enters the decompiler / conditions path.  Setting
``lateral_hops=0`` reproduces exactly the pure-scission grammar of ``search_routes`` (a tested equivalence).

STRUCTURAL TYPE-VALIDITY ONLY (Problem A).  A found route is a chain of conservation-valid, oracle-vouchable
events; reachability here is NEVER feasibility, rate, selectivity, or thermal allowedness.  Everything fails
CLOSED: a truncated search reports INCOMPLETE and never claims it found every route.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..category import Molecule
from ..contracts import Digestible, canonical_digest
from ..lateral_rewrite import LATERAL_FAMILIES, _SigmatropicFamily, guarded_isomer_edges
from ..transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    ProviderUse,
    TransformProviderRegistry,
    assert_registry_supports_use,
    search_algebra_digest,
)
from .routes import _conditions_for, _ident, _refuse_charged_target
from .step import ExperimentRoute, ExperimentStep

#: Receipt schema id (opt-in; deliberately NOT the frozen RouteSearchReceipt schema -- replay integrity).
EVENT_ROUTE_SEARCH_RECEIPT_SCHEMA = "smartchem.experiment.event-route-search-receipt/v1"
EVENT_ROUTE_SEARCH_RESULT_SCHEMA = "smartchem.experiment.event-route-search-result/v1"


class EventClassificationError(ValueError):
    """A step's reactant/product shape matches none of the three typed event classes (fail-closed)."""


class EventType(Enum):
    """The three typed event classes (#125).  Each search step is exactly one; the scission contract is kept
    strict rather than overloaded with the laterals' arity."""

    #: assembled from >=2 strictly-smaller fragments -- the inherited W1 rank-descending grammar.
    SCISSION = "SCISSION"
    #: one connected precursor, SAME atom count, no coproduct -- a [3,3] sigmatropic / electrocyclic rank-flat hop.
    CONNECTED_LATERAL = "CONNECTED_LATERAL"
    #: one connected principal precursor LARGER than the target, expelling a conserved coproduct.  DEFERRED
    #: (no generator emits it here -- the 2.0 event-calculus obligation); defined so the taxonomy is complete.
    INTRAMOLECULAR_COPRODUCT = "INTRAMOLECULAR_COPRODUCT"


def classify_event(step: ExperimentStep) -> EventType:
    """Classify a SYNTHESIS :class:`ExperimentStep` into its :class:`EventType` by reactant/product shape alone.

    Fail-closed: a shape matching none of the three classes raises :class:`EventClassificationError` -- an
    unrecognized event is refused, never silently bucketed.  Used for the per-event-type receipt counts and as
    the structural witness that the taxonomy is complete (a hand-built intramolecular-coproduct step classifies
    as the DEFERRED class, exhibiting that the category exists but has no producer in the shipped search)."""
    if type(step) is not ExperimentStep:
        raise EventClassificationError("classify_event expects an ExperimentStep")
    # ARITY by MULTIPLICITY, not distinct identity: a scission into two IDENTICAL fragments (AcOH + AcOH -> Ac2O +
    # H2O) has one distinct id but is plainly an arity->=2 assembly.  A lateral / intramolecular event is a single
    # input molecule (an isomerization or an intramolecular rearrangement is 1->1 or 1->1+coproduct, reagentless),
    # so exactly-one reactant MOLECULE is the clean separator; a scission always has >=2 (capped-scission's
    # >=2-component contract, read backward, yields >=2 precursor molecules even when they coincide).
    if len(step.reactants) >= 2:
        return EventType.SCISSION                      # assembled from >=2 fragment molecules (arity->=2 scission)
    # exactly one precursor molecule from here
    precursor = step.reactants[0]
    target_atoms = len(step.target.atoms)
    precursor_atoms = len(precursor.atoms)
    target_id = _ident(step.target)
    coproducts = [p for p in step.products if _ident(p) != target_id]
    if not coproducts and precursor_atoms == target_atoms:
        return EventType.CONNECTED_LATERAL             # 1->1 rank-flat isomerization / ring open-close
    if coproducts and precursor_atoms > target_atoms:
        return EventType.INTRAMOLECULAR_COPRODUCT       # 1 larger principal -> target + coproduct (DEFERRED)
    raise EventClassificationError(
        f"step shape (precursor atoms={precursor_atoms}, target atoms={target_atoms}, "
        f"coproducts={len(coproducts)}) matches no typed event class"
    )


# --------------------------------------------------------------------------------------------------------------------
# Honest completeness receipt (opt-in schema; fail-closed).
# --------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class EventRouteSearchReceipt(Digestible):
    """What was searched and whether the bounded typed-event grammar was exhausted -- an HONEST completeness
    fact, never a claim about chemistry.  ``complete`` is ``True`` only when NOTHING was truncated: no scission
    cut-budget hit, no lateral match-budget hit, no depth truncation, no lateral-hop truncation, and the result
    limit was not saturated.  A declared ``lateral_hops`` bound that some node WANTED to exceed is a truncation
    (like ``max_depth``) -- a search that explored <=H hops cannot claim it found every lateral route."""

    schema_version: str
    max_depth: int
    max_routes: int
    cut_budget: int
    lateral_hops: int
    lateral_match_budget: int
    expansions_attempted: int
    incomplete_expansions: int           # scission cut-budget hit at some node
    lateral_match_truncated: int         # a lateral family's kernel match enumeration hit lateral_match_budget
    depth_truncated: int                 # a linear-expandable branch cut solely by max_depth
    lateral_hops_truncated: int          # a node had lateral edges but hops_left == 0 (declared-bound truncation)
    result_limit_saturated: bool
    results_returned: int
    nodes_visited: int
    scission_events_considered: int
    lateral_events_considered: int
    candidates_emitted: int
    target_identity_digest: str
    terminal_policy_digest: str
    transform_grammar_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != EVENT_ROUTE_SEARCH_RECEIPT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {EVENT_ROUTE_SEARCH_RECEIPT_SCHEMA!r}")
        for name in ("max_depth", "max_routes", "cut_budget", "lateral_match_budget"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.lateral_hops) is not int or self.lateral_hops < 0:
            raise ValueError("lateral_hops must be a non-negative integer")

    @property
    def complete(self) -> bool:
        """``True`` iff the bounded typed-event grammar was exhausted with NO truncation of any kind."""
        return (
            self.incomplete_expansions == 0
            and self.lateral_match_truncated == 0
            and self.depth_truncated == 0
            and self.lateral_hops_truncated == 0
            and not self.result_limit_saturated
        )

    def summary(self) -> str:
        done = "COMPLETE within grammar" if self.complete else "INCOMPLETE (truncated)"
        return (
            f"event-route search: {self.results_returned} route(s), {done}; depth<={self.max_depth}, "
            f"lateral_hops<={self.lateral_hops}; nodes visited={self.nodes_visited}; scission events="
            f"{self.scission_events_considered}, lateral events={self.lateral_events_considered}; "
            f"truncations: scission-budget={self.incomplete_expansions}, lateral-match="
            f"{self.lateral_match_truncated}, depth={self.depth_truncated}, hops={self.lateral_hops_truncated}, "
            f"result-limit={self.result_limit_saturated}."
        )


@dataclass(frozen=True)
class EventRouteSearchResult(Digestible):
    """The candidate typed-event routes plus the completeness receipt.  A route is a chain of oracle-vouchable
    events (scission + lateral); evidence rungs judge feasibility -- this only enumerates conservation-valid,
    structurally-valid assemblies within the declared bounded grammar."""

    schema_version: str
    routes: tuple[ExperimentRoute, ...]
    receipt: EventRouteSearchReceipt
    searched_target_on_hand: bool

    def __post_init__(self) -> None:
        if self.schema_version != EVENT_ROUTE_SEARCH_RESULT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {EVENT_ROUTE_SEARCH_RESULT_SCHEMA!r}")

    def event_type_counts(self) -> dict[EventType, int]:
        """Per-:class:`EventType` count over every step of every returned route (reporting only; fail-closed via
        :func:`classify_event`)."""
        counts: dict[EventType, int] = {t: 0 for t in EventType}
        for route in self.routes:
            for step in route.steps:
                counts[classify_event(step)] += 1
        return counts


def search_event_routes(
    target: Molecule,
    *,
    reagents: tuple[Molecule, ...],
    available: tuple[Molecule, ...] = (),
    commodities: tuple[Molecule, ...] = (),
    max_depth: int = 2,
    max_routes: int = 100,
    cut_budget: int = 20_000,
    lateral_families: tuple[_SigmatropicFamily, ...] = LATERAL_FAMILIES,
    lateral_hops: int = 1,
    lateral_match_budget: int = 100_000,
    registry: TransformProviderRegistry = DEFAULT_TRANSFORM_REGISTRY,
) -> EventRouteSearchResult:
    """Bounded typed-event retrosynthesis: find routes to ``target`` that interleave rank-descending SCISSION
    events with up to ``lateral_hops`` rank-flat CONNECTED_LATERAL hops, terminating on the lexicographic
    ``(atom_count, hops_left)`` measure (see the module docstring's proof).  Opt-in; ``search_routes`` and its
    frozen receipt are untouched.

    ``reagents`` / ``available`` / ``commodities`` terminate a branch exactly as in ``search_routes`` (keyed by
    canonical identity, never by formula).  ``lateral_hops`` is the per-ROUTE budget of lateral events (default
    1; ``0`` reproduces the pure-scission grammar).  ``lateral_families`` defaults to every vouched lateral
    family (the [3,3] sigmatropics + electrocyclizations -- the forcing consumers #123 names).  The receipt is
    an honest completeness fact: INCOMPLETE whenever any budget, the depth, the lateral-hop bound, or the result
    limit truncated the search.
    """
    if type(target) is not Molecule:
        raise TypeError("target must be a Molecule")
    assert_registry_supports_use(registry, ProviderUse.LINEAR_ROUTE)
    for name, value in (("max_depth", max_depth), ("max_routes", max_routes), ("cut_budget", cut_budget),
                        ("lateral_match_budget", lateral_match_budget)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if type(lateral_hops) is not int or lateral_hops < 0:
        raise ValueError("lateral_hops must be a non-negative integer")

    on_hand = {_ident(m) for m in (*available, *reagents, *commodities)}
    grammar_digest = canonical_digest((
        "event-route",
        search_algebra_digest("linear-route", registry),
        tuple(sorted(f.provider_id for f in lateral_families)),
        lateral_hops,
    ))
    identity = dict(
        target_identity_digest=_ident(target),
        terminal_policy_digest=canonical_digest(("terminal-policy", "STRUCTURE", frozenset(on_hand))),
        transform_grammar_digest=grammar_digest,
    )

    def _receipt(*, expansions, incomplete, lat_trunc, depth_trunc, hops_trunc, result_sat, results,
                 nodes, scission_ev, lateral_ev, emitted) -> EventRouteSearchReceipt:
        return EventRouteSearchReceipt(
            EVENT_ROUTE_SEARCH_RECEIPT_SCHEMA, max_depth, max_routes, cut_budget, lateral_hops,
            lateral_match_budget, expansions, incomplete, lat_trunc, depth_trunc, hops_trunc, result_sat,
            results, nodes, scission_ev, lateral_ev, emitted, **identity,
        )

    if _ident(target) in on_hand:
        # the search ran and terminated immediately: the zero counters are a measurement, not UNKNOWN.
        return EventRouteSearchResult(
            EVENT_ROUTE_SEARCH_RESULT_SCHEMA, (),
            _receipt(expansions=0, incomplete=0, lat_trunc=0, depth_trunc=0, hops_trunc=0, result_sat=False,
                     results=0, nodes=0, scission_ev=0, lateral_ev=0, emitted=0),
            True,
        )

    seen_routes: dict[str, ExperimentRoute] = {}
    expansions_attempted = 0
    incomplete_expansions = 0
    lateral_match_truncated = 0
    depth_truncated = 0
    lateral_hops_truncated = 0
    result_limit_saturated = False
    nodes_visited = 0
    scission_events_considered = 0
    lateral_events_considered = 0
    candidates_emitted = 0

    def _branch(step: ExperimentStep, t: Molecule, depth: int, hops_left: int, ancestors: frozenset[str]):
        """Yield every completed route that ends in ``step`` (which makes ``t``), recursing linearly to make a
        single still-missing precursor.  Shared by the scission and lateral branches -- the ISSUE-124 ancestor
        guard (the rank-flat/reversible safety net) and the linear-expansion rule are identical for both."""
        nonlocal depth_truncated
        distinct: dict[str, Molecule] = {}
        for m in step.reactants:
            distinct.setdefault(_ident(m), m)
        # ISSUE-124: a precursor equal to one of this branch's OWN non-stock ancestors is a self-referential
        # (cyclic) dependency -- REFUSE it (never treat it as available).  Under pure W1 scission an ancestor can
        # never reappear; with a rank-flat lateral hop it CAN (a Cope inverse A->B->A), so this guard is what cuts
        # the inverse cycle rather than merely letting the hop budget bound it.
        if any(k in ancestors and k not in on_hand for k in distinct):
            return
        missing = [m for k, m in distinct.items() if k not in on_hand]
        if not missing:
            yield ExperimentRoute.of(step)
        elif len(missing) == 1 and depth < max_depth:
            for sub in routes_making(missing[0], depth + 1, hops_left, ancestors | {_ident(t)}):
                yield ExperimentRoute.of(*sub.steps, step)
        elif len(missing) == 1:
            depth_truncated += 1
        # len(missing) >= 2 is a convergent (DAG) boundary, not a depth limit -- not this linear search's job.

    def routes_making(t: Molecule, depth: int, hops_left: int, ancestors: frozenset[str]):
        nonlocal expansions_attempted, incomplete_expansions, lateral_match_truncated, lateral_hops_truncated
        nonlocal nodes_visited, scission_events_considered, lateral_events_considered
        nodes_visited += 1
        if depth > max_depth:
            return
        expansions_attempted += 1
        _refuse_charged_target(t)   # neutral-only search: a charged species is a model-boundary refusal
        # -- SCISSION events (the inherited W1 rank-descending grammar; atom_count strictly drops) --
        cleavages, complete = registry.enumerate(t, reagents, budget=cut_budget)
        if not complete:
            incomplete_expansions += 1
        for et in cleavages:
            scission_events_considered += 1
            cs = et.transform
            step = ExperimentStep.from_transform(cs, envelope=_conditions_for(cs))
            yield from _branch(step, t, depth, hops_left, ancestors)
        # -- CONNECTED_LATERAL events (rank-flat; atom_count equal, consume one hop) --
        if hops_left > 0:
            for family in lateral_families:
                edges, fam_complete = guarded_isomer_edges(family, t, budget=lateral_match_budget)
                if not fam_complete:
                    lateral_match_truncated += 1
                for edge in edges:
                    lateral_events_considered += 1
                    # the forget()-FREE path (#123): envelope=None, so a lateral edge never enters the decompiler.
                    step = ExperimentStep.from_transform(edge, envelope=None)
                    yield from _branch(step, t, depth, hops_left - 1, ancestors)
        elif lateral_families and lateral_hops > 0:
            # laterals were ENABLED (lateral_hops>0) but this branch spent them all, yet a deeper node could still
            # have a lateral successor -- an honest declared-bound truncation, the lateral analogue of depth_truncated
            # (we do NOT enumerate the successors; recording the possibility keeps `complete` from over-claiming).
            # When lateral_hops==0 the user opted OUT of laterals, so scission-only IS their complete grammar and
            # we never pay to probe (search_event_routes(..., lateral_hops=0) then matches the search_routes grammar).
            # We MUST read each family's completeness flag, not merely whether it found edges: a budget-truncated
            # enumeration that returns ZERO edges is NOT evidence of "no successor" -- trusting its emptiness would let
            # `complete` over-claim over a silently-cut node (an evil-morty finding; today only an accident of
            # enumeration cost -- edge-found-before-complete -- keeps it honest, and honesty must not rest on an
            # unasserted accident).  So a truncated probe flags lateral_match_truncated (fail-closed INCOMPLETE) even
            # when it found nothing; a non-empty probe flags the hop truncation.  No early break -- skipping a later
            # family would skip reading its flag.
            found_successor = False
            for family in lateral_families:
                edges, fam_complete = guarded_isomer_edges(family, t, budget=lateral_match_budget)
                if not fam_complete:
                    lateral_match_truncated += 1
                if edges:
                    found_successor = True
            if found_successor:
                lateral_hops_truncated += 1

    for route in routes_making(target, 1, lateral_hops, frozenset()):
        candidates_emitted += 1
        if route.digest in seen_routes:
            continue                                   # repeated-state: distinct histories, same route -> dedup
        if len(seen_routes) == max_routes:
            result_limit_saturated = True
            break
        seen_routes[route.digest] = route

    routes = tuple(seen_routes.values())
    return EventRouteSearchResult(
        EVENT_ROUTE_SEARCH_RESULT_SCHEMA, routes,
        _receipt(expansions=expansions_attempted, incomplete=incomplete_expansions,
                 lat_trunc=lateral_match_truncated, depth_trunc=depth_truncated, hops_trunc=lateral_hops_truncated,
                 result_sat=result_limit_saturated, results=len(routes), nodes=nodes_visited,
                 scission_ev=scission_events_considered, lateral_ev=lateral_events_considered,
                 emitted=candidates_emitted),
        False,
    )
