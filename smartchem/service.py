"""SVC-REQ-01 (first brick) -- the one typed ``CompilationRequest``/``CompilationResponse`` the standard's
service contract (section 13) mandates, and the lever most CLI rows hang off (CLI-CAN/JSON/EXIT/ERR).

Why one typed request at all
----------------------------
Today ``compile`` and ``synthesize`` are two front doors that reach the same engine down slightly different
corridors with their own invisible defaults.  The standard's fear (section 13.1, verbatim):

    > Defaults MUST be explicit fields with ``origin=DEFAULT``, not invisible branches in commands.
    > Two request objects with the same semantic digest MUST execute the same search regardless of which CLI
    > alias created them.

So this module makes the request a first-class, digestible value with two deliberately different digests:

* :attr:`CompilationRequest.semantic_digest` -- the SEARCH identity.  The guarantee it makes is ONE-WAY, exactly
  the standard's (section 13.1): equal ``semantic_digest`` => the SAME search.  It covers every SEMANTIC input the
  standard (section 4.1) deems part of the request's meaning (identity, terminal policy, transform grammar,
  evidence provider, search bounds, constraints, ranking) and DELIBERATELY EXCLUDES only the audit/display metadata
  (per-field ``origins`` and the ``output_policy``).  It is deliberately a SUPERSET of what today's bounded engine
  happens to consume -- some semantic fields (the not-yet-wired policy placeholders; ``input_kind`` on a formula
  descent) are recorded in the identity but inert in the current engine.  That over-inclusion is safe and
  intentional: it can only ever SPLIT two requests (a spurious digest difference), never MERGE two different
  searches into one identity, which is the only direction section 13.1 forbids.  This is the load-bearing law: an
  alias that leaves ``cut_budget`` to its default and an alias that passes ``--cut-budget 20000`` explicitly resolve
  to the SAME value, so they share a ``semantic_digest`` and, run through :func:`run_compilation`, the same result
  -- "equal flags across aliases produce equal request/result digests" (the SVC-REQ-01 acceptance test).
* :attr:`CompilationRequest.digest` (inherited) -- the FULL identity, provenance included, for the audit trail.

The provenance itself is not thrown away: every defaultable knob records whether its value was ``EXPLICIT`` or
``DEFAULT`` in :attr:`~CompilationRequest.origins`, so a default is a *visible field*, never an invisible branch.
The origins ride in the full digest and the serialization; they are simply not part of the SEARCH identity,
because two requests that will run the identical search must not be split apart by how one of them happened to
arrive at a value.

Scope of THIS brick (named honestly, W3)
----------------------------------------
This brick builds the types, the digest laws, the origin discipline, fail-closed validation, canonical
serialization, and :func:`run_compilation` -- a deterministic producer that delegates to the EXISTING IR
producers (:func:`~smartchem.compilation_ir.recompile_to_ir` / ``decompile_to_ir``) and maps the outcome to the
standard's exit codes (section 14.4).  The live ``argv`` dispatch now routes through this service (CLI-CAN-01), the
ranked route dossiers are populated with the section-11 fit disposition (CLI-CAN-02 brick 2), and an uncaught bug
becomes an ``ERROR_INTERNAL`` receipt (CLI-EXIT-01).  It does NOT yet populate the affordability frontier
(COST-VEC-01), bind quantitative :class:`~smartchem.experiment.stock.StockMaterial` (STOCK-01), or fully resolve
INCHI/FORMULA targets into the digest (ID-PARSE-01).  Each open item is a named follow-on, not a silent gap.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .compilation_ir import (
    ChemicalCompilationIR,
    CompilationOperation,
    _structure_ident,
    decompile_to_ir,
    ir_from_payload,
    ir_to_payload,
    recompile_to_ir,
)
from .constraints import PhysicalBounds
from .process_constraints import (
    ProcessBounds, ProcessRequirements, ProcessFitStatus, Attention, Agitation,
    evaluate_process_requirements, evaluate_dag_process_requirements,
)
from .experiment.readiness import ObligationStatus, RouteReadiness, StepReadiness, evaluate_route
from .algebra_profiles import (
    DEFAULT_ALGEBRA_PROFILE,
    DEFAULT_ROUTE_ALGEBRA_PROFILE,
    LEGACY_MISSING_ALGEBRA_PROFILE,
    PROFILE_USES,
    resolve_algebra_profile,
)
from .contracts import Digestible, canonical_digest
from .identity import IdentityLoss, MatchLayer, refines
from .identity_parse import IdentityParseError, InputKind, resolve_target
from .transform_provider import ProviderUse, search_algebra_digest
from .search import REFUSED_8_2_STATUSES, STANDARD_8_2_STATUSES, section_8_3_label

__all__ = [
    "COMPILATION_REQUEST_SCHEMA",
    "COMPILATION_RESPONSE_SCHEMA",
    "COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR",
    "response_schema",
    "response_semantic_fields",
    "FieldOrigin",
    "TransformGrammar",
    "ResponseOutcome",
    "SearchBounds",
    "TerminalPolicy",
    "IdentityPolicy",
    "ConstraintPolicy",
    "RankingPolicy",
    "EvidenceProviderSelection",
    "OFFLINE_PROVIDER",
    "NETWORK_PROVIDER",
    "OutputPolicy",
    "CompilationRequest",
    "CompilationResponse",
    "build_recompile_request",
    "build_decompile_request",
    "run_compilation",
    "request_to_payload",
    "request_from_payload",
    "serialize_request",
    "deserialize_request",
    "response_to_payload",
    "response_from_payload",
    "serialize_response",
    "deserialize_response",
    "resolve_producer_key",
    "EXIT_SUCCESS",
    "EXIT_INVALID_INPUT",
    "EXIT_NO_ROUTE",
    "EXIT_INCOMPLETE",
    "EXIT_REFUSED",
    "EXIT_INTERNAL",
]

# v1alpha4 (CLI-CAN-02): ConstraintPolicy carries a real PhysicalBounds (T/P) box instead of a placeholder
# constraint_id string -- a genuine request-payload shape change.  (v1alpha3 added SVC-REQ-01's normalized_identity;
# v1alpha2 added ID-LAYER-02's match_layer.)
COMPILATION_REQUEST_SCHEMA = "smartchem.service/compilation-request-v1alpha5"
# v1alpha2 (SVC-REQ-01 alias-collapse): CompilationResponse gains a ``parse_receipt_summary`` field -- the section
# 14.2 identity-resolution echo, pulled OUT of ``diagnostics`` (where it rode as a free-text last line) into a
# first-class field, so it is surfaced as the section 14.3 receipt yet EXCLUDED from ``result_digest`` (it is
# provenance -- how the string was READ -- not part of the search RESULT).  (v1alpha1 was the first brick.)
# v1alpha3 (CLI-CAN-02 brick 2): ``ranked_route_dossiers`` is now POPULATED (routes mode) with typed
# ``RankedRouteSummary`` objects -- the section-11 bench-fit disposition per route -- so the array elements gain
# structure and the payload shape genuinely changes.
# v1alpha4 (SRCH-NO-01): the response gains a first-class ``search_space_status`` field -- the section-8.3
# no-route matrix label (NO_ROUTE_IN_DECLARED_SPACE / INCOMPLETE_NO_ROUTE_OBSERVED / COMPLETE_CANDIDATE_SET /
# PARTIAL_CANDIDATE_SET), so the four-outcome distinction rides the machine payload uniformly, not only the render.
# v1alpha5 (COST-VEC-01): ``affordability_frontier`` is now POPULATED (routes mode) with typed
# ``AffordabilityFrontierEntry`` objects -- the section-10.4 Pareto affordability frontier over the ranked routes --
# so the array elements gain structure (the old "must be empty" placeholder is retired).
# v1alpha6 (SNAPSHOT-13.2): the response gains a ``provider_snapshots`` field -- the dated section-13.2 provenance of
# any LIVE provider fetch that serviced the request (empty on an offline/default run), so a --network response is
# reproducible.  EXCLUDED from result_digest (a fetch time is provenance, not a search result).
# v1alpha7 (COST-VEC-01-coupled): the affordability_frontier's flattened CostVector gains a ``cash_floor`` axis (an
# honest partial-basket lower bound), so the response value shape changed.
# v1alpha8 (COST-VEC-01 quantity axis): the frontier's ``material_quantity`` axis is now POPULATED (routes mode) with
# each route's total external-leaf MOLES per mol product -- a previously-always-null field now carries a value.
# v1alpha10 (PROCESS-ADMIT-01): each ranked_route_dossiers entry now carries its per-step ``process_requirements`` so
# process admission is RE-DERIVED on load (the deserialization trust-boundary close), not trusted from ``fit_status``.
# v1alpha11 (COMBINED-VERDICT-AUTH): the payload carries a top-level ``producer_signature`` field (an optional HMAC over
# ``result_digest``; ``null`` unless signed) so a consumer with the producer key can reject an out-of-band tamper.
# v1alpha12 (DAG-ADMIT-01): the response gains a ``ranked_dag_dossiers`` field -- the FORMAL, load-re-derived PROCESS
# admission of each convergent-DAG candidate (was a throwaway diagnostic), so ``process_selection_status`` is no longer
# UNASSESSED for a DAG-mode compile.  Folded into ``result_digest`` ONLY when non-empty, so a linear/DAG-less response
# stays byte-identical to v1alpha11 (zero ripple); a DAG-mode process-constrained response's result_digest changes.
# v1alpha13 (TAMPER-HARDENING-01): NO new field -- a new ON-LOAD REFUSAL.  ``_check_frontier_coherence`` re-derives
# each affordability_frontier entry's ``hard_blockers`` (process exclusions + catalyst) and ``fiction_blockers``
# (reaction-type oracle) and REFUSES an entry whose claimed blockers are looser than the re-derivation -- closing the
# R59 disposition serialized-tamper (a stripped blocker flipping REAL_BUT_HARD/NOT_A_REACTION up to CLEAN, undetected
# because the frontier is EXCLUDED from result_digest).  FULLY closed on every transport: the process-exclusion
# channel (re-derived from digest-covered process_requirements, no replay needed).  The catalyst/fiction channels are
# closed on the THICK transport (include_replay=True, digest-bound) and, under verified admission, on the thin
# transport too -- a thin (replay-absent) load then fails CLOSED rather than trusting the unverifiable disposition
# (replay-MANDATORY-for-disposition-claims); a bare non-verified load keeps them ADVISORY.  The bump carries no shape
# change; it marks the version at/after which a loaded
# response is frontier-coherence-checked, so a pre-guarantee v1alpha12 payload is refused by the strict schema gate.
# v1alpha14 (v0.8 Real Route Dossiers, M10): NO new top-level field -- a new ON-LOAD REFUSAL, mirroring v1alpha13's own
# convention.  ``CompilationResponse._check_readiness_coherence`` (run unconditionally from ``response_from_payload``,
# UN-gated on ``fit_status`` or ``require_verified_admission`` -- readiness is orthogonal to bench-fit, Sec 2) re-derives
# each ranked route's typed readiness ladder from its thick ``replay_payload`` via ``evaluate_route`` and REFUSES a
# payload whose carried ``readiness`` disagrees with the re-derivation (a bumped tier, a stripped citation, a
# substituted per-step obligation).  Advisory (unenforceable) on a thin (replay-absent) route, exactly as the
# catalyst/fiction frontier channels are -- the bump marks the version at/after which a THICK-transport readiness claim
# is re-derived, so a pre-guarantee v1alpha13 payload is refused by the strict schema gate.
COMPILATION_RESPONSE_SCHEMA = "smartchem.service/compilation-response-v1alpha14"
# The versioned descriptor of the --json response SHAPE (standard 14.3 "stable versioned response schema").  It is
# bumped only when a field is added/removed/renamed -- never when a derived digest changes -- so it is the durable
# pin CLI-JSON-01's golden guards, distinct from the per-value response schema version above.  v1alpha9: the
# affordability_frontier cost_vector gains cash_floor (COST-VEC-01-coupled).  v1alpha8: the provider_snapshots field
# (SNAPSHOT-13.2).  v1alpha7: the affordability_frontier element shape (COST-VEC-01).  v1alpha6: the
# search_space_status section-8.3 field (SRCH-NO-01).  v1alpha5: the ranked_route_dossiers element shape (CLI-CAN-02
# brick 2).  (v1alpha4: the request schema bumped for ConstraintPolicy.bounds; v1alpha3: the parse_receipt_summary
# response field + the normalized_identity request field; v1alpha2: IR-LOSS-01's identity_losses.)  v1alpha11
# (PROCESS-ADMIT-01): the ranked_route_summary gains a per-step ``process_requirements`` field (re-derived on load).
# v1alpha12 (COMBINED-VERDICT-AUTH): the response gains a top-level ``producer_signature`` field.
# v1alpha13 (DAG-ADMIT-01): the response gains a ``ranked_dag_dossiers`` field (per-DAG process admission).
# v1alpha14 (DAG-BENCH-01): the ranked_dag_summary element's ``process_fit_status`` field is RENAMED to ``fit_status``
# and now carries the COMBINED section-11 verdict (composability + physical box + process), not the process axis alone.
# v1alpha15 (DAG-THERMO-01): the ranked_dag_summary element gains composability/selectivity/feasibility/equilibrium/
# kinetics verdict fields (the per-node thermochemical roll-up feeding the DAG ranking), reaching parity with the
# ranked_route_summary's verdict fields so a DAG dossier's best-first order is as inspectable as a linear one's.
# v1alpha16 (item 2b): the ranked_dag_summary element gains a machine-readable ``serial_holds`` field (the DAG-HOLD-01
# serial-schedule hold as (producer, consumer, minutes) triples) -- a descriptor-only bump (the field is disclosure,
# digest-excluded, so no result_digest ripple, and it is empty for every non-holding/linear-shaped DAG).
# TAMPER-HARDENING-01: the descriptor was NOT bumped for that round.  Its embedded ``response_schema_version`` VALUE
# read v1alpha13 (a derived-value change), but no descriptor FIELD was added/removed/renamed -- the on-load
# frontier-coherence refusal changed behaviour, not shape -- and this descriptor bumps ONLY on a shape change (its own
# stated convention).
# v1alpha17 (v0.8 Real Route Dossiers): a genuine SHAPE change -- ``ranked_route_summary_fields`` gains a typed
# ``readiness`` field (Sec 3/4/8's per-step obligation ladder; ``readiness_tier`` stays, now a documented DERIVED
# convenience alias of ``readiness.tier`` rather than a hard-coded floor).  Bumped per the descriptor's own convention.
COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR = "smartchem.service/compilation-response-schema-v1alpha17"
# CLI-CAN-02 brick 2: the thin, digestible per-route ranking summary that POPULATES the response's
# ``ranked_route_dossiers``.  It is projected off a drafter :class:`~smartchem.experiment.drafter.RouteFit` so the
# heavy ExperimentRoute/thermo object graph never enters the response payload; it carries the section-11 bench-fit
# disposition (FITS/EXCLUDED/UNKNOWN/UNCONSTRAINED with exact reasons) and the ranking's sourced verdicts.
# v1alpha3 (v0.8 Real Route Dossiers): gains a typed ``readiness`` field (``smartchem.experiment.readiness.
# RouteReadiness`` -- the Sec 3/4/8 per-step obligation ladder), digest-covered exactly like ``process_requirements``.
# ``readiness_tier`` is retired as a stored field (it was a hard-coded ``FORMAL_CANDIDATE`` floor -- READY-TIER-01 --
# no route could ever earn or lose) and is now a derived ``@property`` reading ``readiness.tier``; every existing
# ``.readiness_tier`` read keeps working, it just answers honestly now.
RANKED_ROUTE_SUMMARY_SCHEMA = "smartchem.service/ranked-route-summary-v1alpha3"
# DAG-BENCH-01 (was DAG-ADMIT-01): the thin, digestible per-DAG COMBINED section-11 admission that populates the
# response's ``ranked_dag_dossiers``.  Distinct from RANKED_ROUTE_SUMMARY_SCHEMA on purpose -- a DAG additionally
# carries its ``edges`` (so the critical-path PROCESS component is re-derived on load, the convergent PROCESS-ADMIT-01)
# -- but ``fit_status`` is now the SAME combined verdict (composability + physical box + process) a linear route
# carries, so a convergent DAG is a first-class bench citizen.  v1alpha2: ``process_fit_status`` renamed ``fit_status``
# and widened from the process axis alone to the combined bench fit.  v1alpha3 (DAG-THERMO-01): gains the five ranking
# verdict fields (composability/selectivity/feasibility/equilibrium/kinetics) so the DAG dossier exposes the same
# sourced tiebreakers the ranked_route_summary does -- parity, and the best-first order made inspectable.
# v1alpha4 (item 2b): gains a machine-readable ``serial_holds`` field -- the DAG-HOLD-01 serial-schedule hold as
# (producer, consumer, minutes) triples.  DISCLOSURE only (never changes fit_status) and digest-EXCLUDED (it is
# fully determined by edges + process_requirements), so no existing DAG digest moves; the version bumps because
# the element's serialized SHAPE gained a field.
RANKED_DAG_SUMMARY_SCHEMA = "smartchem.service/ranked-dag-summary-v1alpha4"

# The standard's section 14.4 exit codes.  One table so every front door (CLI-EXIT-01, later) reads them here.
EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
EXIT_NO_ROUTE = 3
EXIT_INCOMPLETE = 4
EXIT_REFUSED = 5
EXIT_INTERNAL = 70

_COMPLETE_8_2 = "COMPLETE_WITHIN_DECLARED_SPACE"
_INCOMPLETE_8_2 = frozenset(
    s for s in STANDARD_8_2_STATUSES if s.startswith("INCOMPLETE_")
)


class FieldOrigin(str, Enum):
    """Whether a request field carried a caller-supplied value or fell back to the service default (section 13.1).

    Recorded per field so a default is an explicit, auditable fact -- never an invisible branch buried in a
    command.  It is provenance, not search identity: it rides the full :attr:`CompilationRequest.digest` but is
    excluded from :attr:`CompilationRequest.semantic_digest`, because a value reached by default and the same
    value passed explicitly MUST execute the same search.
    """

    EXPLICIT = "EXPLICIT"
    DEFAULT = "DEFAULT"


class TransformGrammar(str, Enum):
    """Which transform grammar (section 8.4) the request selects -- the ``transform_registry_selection`` field.

    Maps 1:1 to the engine's search kind: ``FORMULA_DECOMPOSITION`` is the elemental descent (DECOMPILE);
    ``CAPPED_SCISSION_LINEAR``/``CAPPED_SCISSION_CONVERGENT`` are the linear route search and the convergent-DAG
    search (RECOMPILE, ``mode='routes'``/``'dags'``).
    """

    FORMULA_DECOMPOSITION = "FORMULA_DECOMPOSITION"
    CAPPED_SCISSION_LINEAR = "CAPPED_SCISSION_LINEAR"
    CAPPED_SCISSION_CONVERGENT = "CAPPED_SCISSION_CONVERGENT"


_GRAMMAR_TO_MODE = {
    TransformGrammar.CAPPED_SCISSION_LINEAR: "routes",
    TransformGrammar.CAPPED_SCISSION_CONVERGENT: "dags",
}
_RECOMPILE_GRAMMARS = frozenset(_GRAMMAR_TO_MODE)

# 0.7 Round II (Course-Correction 2): the SEARCH TOPOLOGY axis (route vs DAG) is orthogonal to the TRANSFORM
# ALGEBRA axis (which providers generate).  transform_grammar carries the topology; the new request field
# `algebra_profile` carries the algebra.  This maps a recompile grammar to the ProviderUse its topology needs, so a
# selected algebra profile is validated against the topology it will actually run in (a decompile-only profile is
# refused under a route grammar) and the search-engine's per-provider use-guard has the matching use.
_GRAMMAR_TO_MODE_TOPOLOGY = {"routes": "linear-route", "dags": "convergent-dag"}
_GRAMMAR_TO_USE = {
    TransformGrammar.CAPPED_SCISSION_LINEAR: ProviderUse.LINEAR_ROUTE,
    TransformGrammar.CAPPED_SCISSION_CONVERGENT: ProviderUse.CONVERGENT_DAG,
}

# The ONE identity layer each direction's engine can HONESTLY match at today (ID-LAYER-02).  A recompile's
# structural search matches terminals at CONSTITUTION (the atom/bond graph -- today's STRUCTURE layer); a
# formula descent matches at FORMULA.  A request that declares any OTHER layer is refused by run_compilation,
# because the engine cannot perceive a finer layer (stereo/isotope) and section 5.4 forbids a structure search
# terminating on a coarser (formula-only) match -- both would be a fabricated identity claim, not a real match.
_HONORED_MATCH_LAYER = {
    CompilationOperation.RECOMPILE: MatchLayer.CONSTITUTION,
    CompilationOperation.DECOMPILE: MatchLayer.FORMULA,
}

# The bound-name vocabulary each direction's engine looks up (run_compilation reads bounds BY NAME).  A request
# whose bound-names do not match its operation is incoherent and is refused at construction, so a tampered or
# deserialized payload fails CLOSED here rather than as a KeyError deep inside run_compilation.
_RECOMPILE_BOUND_NAMES = frozenset({"max_depth", "max_results", "cut_budget"})
_DECOMPILE_BOUND_NAMES = frozenset({"max_multiplicity", "budget", "max_edges"})


class ResponseOutcome(str, Enum):
    """The service-level classification of a compilation, and the sole driver of the exit code.

    It is TOTAL (every response has exactly one) and each maps to one section 14.4 code.  ``standard_status``
    carries the finer section 8.2 name where a search actually ran; the two are cross-checked for coherence in
    :meth:`CompilationResponse.__post_init__` so an outcome can never contradict the search status it reports
    (an ``INCOMPLETE`` outcome can never wear a completion status -- the "incomplete looks complete" defect
    section 8 forbids).
    """

    ROUTES_FOUND = "ROUTES_FOUND"                        # complete search, >=1 candidate            -> 0
    TARGET_ALREADY_AVAILABLE = "TARGET_ALREADY_AVAILABLE"  # target already in the terminal stock (s7) -> 0
    NO_ROUTE_COMPLETE = "NO_ROUTE_COMPLETE"              # complete search, zero candidates (s8.3)    -> 3
    INCOMPLETE = "INCOMPLETE"                            # a bound bit; result not certified          -> 4
    REFUSED = "REFUSED"                                  # refused at a model/identity/... boundary   -> 5
    INVALID_INPUT = "INVALID_INPUT"                      # unparseable/ambiguous identity             -> 2
    INTERNAL_ERROR = "INTERNAL_ERROR"                    # an internal bug (reserved; see module note)-> 70


_EXIT_BY_OUTCOME = {
    ResponseOutcome.ROUTES_FOUND: EXIT_SUCCESS,
    ResponseOutcome.TARGET_ALREADY_AVAILABLE: EXIT_SUCCESS,
    ResponseOutcome.NO_ROUTE_COMPLETE: EXIT_NO_ROUTE,
    ResponseOutcome.INCOMPLETE: EXIT_INCOMPLETE,
    ResponseOutcome.REFUSED: EXIT_REFUSED,
    ResponseOutcome.INVALID_INPUT: EXIT_INVALID_INPUT,
    ResponseOutcome.INTERNAL_ERROR: EXIT_INTERNAL,
}


# -- policy sub-records ------------------------------------------------------------------------------------------
# Each is a frozen, digestible semantic record carrying the knob(s) that have real meaning at the current build
# depth.  IdentityPolicy now ENFORCES its match_layer (ID-LAYER-02): it is no longer a pure placeholder.  The
# remaining placeholder members (ConstraintPolicy/RankingPolicy/EvidenceProviderSelection) default to today's
# behaviour and are typed/versionable now so the request shape is stable while the arcs they front (constraints,
# section 15 ranking, provider selection) are built out behind them.


@dataclass(frozen=True)
class SearchBounds(Digestible):
    """The declared search bounds as a canonical, positive-integer name->value map.

    A single record covers both directions because their bound knobs differ (recompile: ``max_depth``/
    ``max_results``/``cut_budget``; decompile: ``max_multiplicity``/``budget``/``max_edges``).  Storing them as a
    sorted tuple of ``(name, value)`` keeps the digest order-invariant and the set extensible without a tagged
    union.  Every value must be a positive int -- a zero or negative bound is a nonsensical search space.
    """

    bounds: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if type(self.bounds) is not tuple or not self.bounds:
            raise ValueError("search bounds must be a non-empty tuple of (name, value) pairs")
        names = []
        for pair in self.bounds:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("each bound must be a (name, value) pair")
            name, value = pair
            if not isinstance(name, str) or not name:
                raise ValueError("a bound name must be a non-empty string")
            if type(value) is not int or isinstance(value, bool) or value <= 0:
                raise ValueError(f"bound {name!r} must be a positive int, got {value!r}")
            names.append(name)
        if names != sorted(names):
            raise ValueError("bounds must be in canonical (name-sorted) order")
        if len(set(names)) != len(names):
            raise ValueError("bound names must be distinct")

    @classmethod
    def of(cls, **values: int) -> "SearchBounds":
        return cls(tuple(sorted(values.items())))

    def value(self, name: str) -> int:
        for key, val in self.bounds:
            if key == name:
                return val
        raise KeyError(f"no such search bound: {name!r}")


@dataclass(frozen=True)
class TerminalPolicy(Digestible):
    """The terminal/inventory policy (section 7): the match mode plus the direction-specific terminal declaration.

    For RECOMPILE the terminal set is a STRUCTURE-keyed union of the on-hand stock, the helper reagents, and --
    when :attr:`commodities_enabled` -- the poor-man's commodity buckets; the concrete stock and reagent
    identities live in the request's ``stock_materials``/``helper_reagents`` fields, so this record carries only
    the POLICY (mode + commodities toggle), not a copy of them.  For DECOMPILE the terminal set is the
    FORMULA-keyed :attr:`formula_inventory`.
    """

    match_mode: str
    commodities_enabled: bool = False
    formula_inventory: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.match_mode not in ("STRUCTURE", "FORMULA_ONLY"):
            raise ValueError("match_mode must be 'STRUCTURE' or 'FORMULA_ONLY'")
        if not isinstance(self.commodities_enabled, bool):
            raise TypeError("commodities_enabled must be a bool")
        if type(self.formula_inventory) is not tuple or any(
            not isinstance(x, str) or not x for x in self.formula_inventory
        ):
            raise TypeError("formula_inventory must be a tuple of non-empty strings")
        if list(self.formula_inventory) != sorted(self.formula_inventory):
            raise ValueError("formula_inventory must be in canonical (sorted) order")


@dataclass(frozen=True)
class IdentityPolicy(Digestible):
    """Identity-comparison policy (section 5): the LAYER at which this request's identity matches are made.

    ID-LAYER-02 wires the section 5.1 :class:`~smartchem.identity.MatchLayer` lattice into the request: a request
    DECLARES the layer at which terminal matching / route dedup are performed (``match_layer``).  It rides the
    :attr:`CompilationRequest.semantic_digest`, so two requests that match at different layers are different
    searches.  :func:`run_compilation` enforces that the engine only ever operates at a layer it can HONESTLY
    honor -- a declared layer finer than it can perceive, or one section 5.4 forbids, is REFUSED (exit 5), never
    silently matched at a coarser layer and reported as if it were the finer one.  Salt/mixture COMPONENT policy
    stays with the material model (StockMaterial); this record carries the layer knob that has meaning today.
    """

    policy_id: str = "DEFAULT"
    match_layer: MatchLayer = MatchLayer.CONSTITUTION

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise ValueError("policy_id must be a non-empty string")
        if not isinstance(self.match_layer, MatchLayer):
            raise TypeError("match_layer must be a MatchLayer")


@dataclass(frozen=True)
class ConstraintPolicy(Digestible):
    """The section-11 constraint box the request declares (CLI-CAN-02): the physical (T/P) bounds a route must fit.

    ``bounds`` is the shared :class:`~smartchem.constraints.PhysicalBounds` leaf (the SAME model
    :class:`~smartchem.experiment.drafter.ConstraintBox` validates through), so there is ONE T/P constraint model.
    It rides the :attr:`CompilationRequest.semantic_digest` -- two requests declaring different bounds are
    different searches (section 4.1: the constraint is part of the request's MEANING).

    APPLIED (CLI-CAN-02 brick 2): the bounds are DECLARED, identity-bearing, AND now applied to route ranking --
    ``run_compilation`` ranks the routes against ``ConstraintBox.of_bounds(bounds)`` and reports the per-route fit
    disposition in :attr:`CompilationResponse.ranked_route_dossiers` (FITS / EXCLUDED / UNKNOWN-fit / UNCONSTRAINED),
    with the DECLARED-vs-APPLIED tally in ``constraint_note``.  An all-``None`` box is UNCONSTRAINED (nothing
    declared), never a pass (section 11); a constrained dimension a route leaves undeclared is UNKNOWN-fit, a GAP,
    never a silent pass.  The bench's reagent and equipment inventory stay in the request's own
    ``helper_reagents``/``stock_materials`` fields, not here.
    """

    bounds: PhysicalBounds = field(default_factory=PhysicalBounds.unconstrained)
    process: ProcessBounds = field(default_factory=ProcessBounds.unconstrained)

    def __post_init__(self) -> None:
        if type(self.bounds) is not PhysicalBounds:
            raise TypeError("bounds must be a PhysicalBounds")
        if type(self.process) is not ProcessBounds:
            raise TypeError("process must be a ProcessBounds")


@dataclass(frozen=True)
class RankingPolicy(Digestible):
    """Ranking precedence (section 15).  Minimal first cut: the default precedence id; the ordering tuple is
    populated when ranked dossiers land (READY-TIER-01)."""

    policy_id: str = "DEFAULT_PRECEDENCE_V1"

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise ValueError("policy_id must be a non-empty string")


# The section-9 provider selection ids whose evidence autoload is permitted to reach the NETWORK.  Everything
# NOT in this set -- the offline default AND any unrecognised id -- resolves to offline in
# ``EvidenceProviderSelection.allow_network`` (fail-CLOSED): an unknown provider can never silently fetch.  An id
# is added here only once a real fetcher backs it, so the lever cannot outrun the capability.
_NETWORK_PROVIDER_IDS = frozenset({"DEFAULT_NETWORK"})


@dataclass(frozen=True)
class EvidenceProviderSelection(Digestible):
    """Which evidence/data providers are in play (section 9).

    ``selection_id`` is the SOLE digested field, and thus the provider identity: two requests naming different
    providers are different SEARCHES -- an online run may source evidence an offline run cannot -- so the id rides
    :attr:`CompilationRequest.semantic_digest` (and the offline default keeps its historical digest, byte for byte).

    :attr:`allow_network` is the LIVE section-9 lever DERIVED from that id through the closed, FAIL-CLOSED map
    :data:`_NETWORK_PROVIDER_IDS`: only an explicitly network-enabled selection permits fetching; the offline
    default and every unrecognised id resolve to offline -- the same conservative "decline the unknown rather than
    guess" rule the phase normaliser uses.  It is a PROPERTY, not a field, so it never enters the digest: the id
    alone is the identity.  Provider-VERSION sensitivity of the digest is still a later concern.
    """

    selection_id: str = "DEFAULT_OFFLINE"

    def __post_init__(self) -> None:
        if not isinstance(self.selection_id, str) or not self.selection_id:
            raise ValueError("selection_id must be a non-empty string")

    @property
    def allow_network(self) -> bool:
        """Whether this selection permits network evidence fetching (fail-closed on any unrecognised id)."""
        return self.selection_id in _NETWORK_PROVIDER_IDS


#: The two section-9 provider selections the CLI wires today: offline-only (seed + cache) and network-allowed.
#: ``OFFLINE_PROVIDER`` is byte-identical to the ``EvidenceProviderSelection()`` default, so it changes no digest.
OFFLINE_PROVIDER = EvidenceProviderSelection("DEFAULT_OFFLINE")
NETWORK_PROVIDER = EvidenceProviderSelection("DEFAULT_NETWORK")


@dataclass(frozen=True)
class OutputPolicy(Digestible):
    """How the response is to be RENDERED (section 14.3): human vs json, quiet or not.

    This is a display choice and is DELIBERATELY EXCLUDED from :attr:`CompilationRequest.semantic_digest`: it does
    not change what the engine searches, so two requests that differ only in output policy must share a search
    identity (and thus a result).  It is preserved in the full digest and the serialization for round-trip
    fidelity.
    """

    render_mode: str = "HUMAN"
    quiet: bool = False

    def __post_init__(self) -> None:
        if self.render_mode not in ("HUMAN", "JSON"):
            raise ValueError("render_mode must be 'HUMAN' or 'JSON'")
        if not isinstance(self.quiet, bool):
            raise TypeError("quiet must be a bool")


# -- the request -------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CompilationRequest(Digestible):
    """One typed request for either compiler direction (standard section 13.1).

    Two digests, on purpose (see the module docstring): :attr:`semantic_digest` is the alias-independent SEARCH
    identity (excludes ``origins`` and ``output_policy``); the inherited :attr:`digest` is the full identity
    including provenance.  ``stock_materials``/``helper_reagents`` are kept in canonical (sorted, de-duplicated)
    order and digested as sets, so listing the same bench in a different order does not change the search.

    ``normalized_identity`` (SVC-REQ-01 alias-collapse) is the canonical STRUCTURE identity the builder resolved the
    target to, stored so the :attr:`semantic_digest` can key on WHAT the target IS rather than HOW it was spelled --
    so ``paracetamol``, ``name:paracetamol`` and ``smiles:CC(=O)Nc1ccc(O)cc1`` (which run the byte-identical search)
    collapse to ONE search identity.  It is ``""`` when the builder could not resolve the target to a feature-free
    molecule (an unresolvable/formula/InChI target, or one declaring finer stereo/isotope/charge features that
    become section-5.3 losses); in that case the digest falls back to keying on the raw ``(target_input,
    input_kind)`` pair.  Because it is set ONLY for a feature-free molecule, keying on it can never MERGE two
    requests whose searches differ by a loss -- it only ever collapses genuine spelling aliases (the one-way law).
    """

    schema_version: str
    operation: CompilationOperation
    target_input: str
    input_kind: InputKind
    normalized_identity: str
    identity_policy: IdentityPolicy
    terminal_policy: TerminalPolicy
    stock_materials: tuple[str, ...]
    helper_reagents: tuple[str, ...]
    transform_grammar: TransformGrammar
    evidence_provider_selection: EvidenceProviderSelection
    search_bounds: SearchBounds
    constraints: ConstraintPolicy
    ranking_policy: RankingPolicy
    output_policy: OutputPolicy
    origins: tuple[tuple[str, FieldOrigin], ...]
    #: 0.7 Round II: the selected transform-algebra profile (a stable, closed, versioned ID resolved by
    #: smartchem.algebra_profiles).  Defaulted so pre-0.7 constructions and payloads stay valid on the legacy
    #: capped-scission algebra.  Orthogonal to transform_grammar (topology).
    algebra_profile: str = DEFAULT_ALGEBRA_PROFILE

    def __post_init__(self) -> None:
        if self.schema_version != COMPILATION_REQUEST_SCHEMA:
            raise ValueError(f"schema_version must be exactly {COMPILATION_REQUEST_SCHEMA!r}")
        if not isinstance(self.operation, CompilationOperation):
            raise TypeError("operation must be a CompilationOperation")
        if not isinstance(self.target_input, str) or not self.target_input.strip():
            raise ValueError("target_input must be a non-empty string")
        if not isinstance(self.input_kind, InputKind):
            raise TypeError("input_kind must be an InputKind")
        if not isinstance(self.normalized_identity, str):
            raise TypeError("normalized_identity must be a string ('' when the target keys on its raw input)")
        for name, typ in (
            ("identity_policy", IdentityPolicy),
            ("terminal_policy", TerminalPolicy),
            ("evidence_provider_selection", EvidenceProviderSelection),
            ("search_bounds", SearchBounds),
            ("constraints", ConstraintPolicy),
            ("ranking_policy", RankingPolicy),
            ("output_policy", OutputPolicy),
        ):
            if type(getattr(self, name)) is not typ:
                raise TypeError(f"{name} must be a {typ.__name__}")
        for name in ("stock_materials", "helper_reagents"):
            value = getattr(self, name)
            if type(value) is not tuple or any(not isinstance(x, str) or not x for x in value):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
            if list(value) != sorted(value):
                raise ValueError(f"{name} must be in canonical (sorted) order")
            if len(set(value)) != len(value):
                raise ValueError(f"{name} must be distinct")
        if not isinstance(self.transform_grammar, TransformGrammar):
            raise TypeError("transform_grammar must be a TransformGrammar")
        # operation <-> request-shape coherence: grammar, terminal-policy mode, bound-name vocabulary and the
        # direction-specific fields are NOT independent knobs.  A request whose shape contradicts its operation is
        # refused here, so an incoherent hand-built or deserialized payload fails CLOSED at construction rather than
        # surfacing as a spurious digest split (findings the request never actually searches on) or a KeyError deep
        # inside run_compilation.
        bound_names = frozenset(name for name, _ in self.search_bounds.bounds)
        if self.operation is CompilationOperation.DECOMPILE:
            if self.transform_grammar is not TransformGrammar.FORMULA_DECOMPOSITION:
                raise ValueError("a DECOMPILE request must select the FORMULA_DECOMPOSITION grammar")
            if self.terminal_policy.match_mode != "FORMULA_ONLY":
                raise ValueError("a DECOMPILE request must use a FORMULA_ONLY terminal policy")
            if self.terminal_policy.commodities_enabled or self.stock_materials or self.helper_reagents:
                raise ValueError("a DECOMPILE request carries no structural stock, reagents, or commodities")
            if bound_names != _DECOMPILE_BOUND_NAMES:
                raise ValueError(f"a DECOMPILE request's search bounds must be exactly {sorted(_DECOMPILE_BOUND_NAMES)}")
        else:
            if self.transform_grammar not in _RECOMPILE_GRAMMARS:
                raise ValueError("a RECOMPILE request must select a capped-scission grammar")
            if self.terminal_policy.match_mode != "STRUCTURE":
                raise ValueError("a RECOMPILE request must use a STRUCTURE terminal policy")
            if self.terminal_policy.formula_inventory:
                raise ValueError("a RECOMPILE request has no formula inventory (that is a decompile terminal set)")
            if bound_names != _RECOMPILE_BOUND_NAMES:
                raise ValueError(f"a RECOMPILE request's search bounds must be exactly {sorted(_RECOMPILE_BOUND_NAMES)}")
        # algebra_profile (0.7 Round II): a KNOWN, closed profile id, coherent with the request's operation/topology.
        # An unknown/incompatible profile fails CLOSED at construction (a typed error), never a KeyError deep in the
        # engine or a dynamic provider import.
        if not isinstance(self.algebra_profile, str):
            raise TypeError("algebra_profile must be a string profile id")
        if self.algebra_profile not in PROFILE_USES:
            raise ValueError(
                f"unknown transform-algebra profile {self.algebra_profile!r}; known profiles: {tuple(PROFILE_USES)}"
            )
        if self.operation is CompilationOperation.DECOMPILE:
            if self.algebra_profile != DEFAULT_ALGEBRA_PROFILE:
                raise ValueError(
                    "a DECOMPILE request performs a formula descent and does not select a route transform-algebra "
                    f"profile (must be {DEFAULT_ALGEBRA_PROFILE!r})"
                )
        else:
            needed_use = _GRAMMAR_TO_USE[self.transform_grammar]
            if needed_use not in PROFILE_USES[self.algebra_profile]:
                raise ValueError(
                    f"transform-algebra profile {self.algebra_profile!r} does not support the {needed_use.value!r} "
                    f"topology this request selects (it supports "
                    f"{sorted(u.value for u in PROFILE_USES[self.algebra_profile])})"
                )
        # origins: a canonical (field-name-sorted) map of provenance; structural check only, since which fields
        # are tracked differs by direction.
        if type(self.origins) is not tuple:
            raise TypeError("origins must be a tuple of (field, FieldOrigin) pairs")
        origin_names = []
        for pair in self.origins:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("each origin must be a (field, FieldOrigin) pair")
            fname, forigin = pair
            if not isinstance(fname, str) or not fname:
                raise ValueError("an origin field name must be a non-empty string")
            if not isinstance(forigin, FieldOrigin):
                raise TypeError("an origin value must be a FieldOrigin")
            origin_names.append(fname)
        if origin_names != sorted(origin_names):
            raise ValueError("origins must be in canonical (field-name-sorted) order")
        if len(set(origin_names)) != len(origin_names):
            raise ValueError("origins must name each field at most once")

    @property
    def _target_identity_key(self) -> tuple:
        """The target's contribution to the SEARCH identity (SVC-REQ-01 alias-collapse).

        When the builder resolved the target to a feature-free molecule it stored the canonical STRUCTURE identity
        in :attr:`normalized_identity`; the digest keys on THAT, so every spelling of the same molecule
        (``paracetamol`` / ``name:paracetamol`` / ``smiles:CC(=O)Nc1ccc(O)cc1``) -- which run the byte-identical
        search -- shares one identity.  ``input_kind`` (which spelling was used) is provenance here and is
        DROPPED, exactly as :func:`run_compilation` drops it once the molecule is resolved.  When
        ``normalized_identity`` is ``""`` (an unresolvable/formula/InChI target, or one declaring finer features
        that become section-5.3 losses) the key falls back to the raw ``(target_input, input_kind)`` pair -- so a
        feature-bearing input keeps its own identity and can never be MERGED with a bare one.
        """
        if self.normalized_identity:
            return ("normalized-identity", self.normalized_identity)
        return ("raw-input", self.target_input, self.input_kind)

    @property
    def semantic_digest(self) -> str:
        """The alias-independent SEARCH identity, with a ONE-WAY guarantee: equal ``semantic_digest`` => the SAME
        search (standard section 13.1).

        It hashes every SEMANTIC field (section 4.1's list) and DELIBERATELY EXCLUDES ``origins`` (provenance) and
        ``output_policy`` (a display choice), so a value reached by default and the same value passed explicitly,
        or a JSON vs human render choice, never split the search identity.  It is deliberately a SUPERSET of what
        the current bounded engine consumes (the placeholder policies are hashed but not yet read by
        :func:`run_compilation`); that can only SPLIT requests, never MERGE two different searches, so the one-way
        law is never violated.  ``stock_materials``/``helper_reagents`` enter as frozensets, so bench ORDER is not
        part of the search identity (matching the IR's terminal-policy discipline).

        The TARGET enters via :attr:`_target_identity_key` (SVC-REQ-01 alias-collapse): a resolvable feature-free
        molecule keys on its canonical STRUCTURE identity, so spellings of the same target collapse and the digest
        finally matches the search :func:`run_compilation` actually runs; every other target keys on the raw
        ``(target_input, input_kind)`` pair.  Collapse is set ONLY for a feature-free molecule (see
        :meth:`_recompile_normalized_identity`), so it never merges two requests whose searches differ by a loss --
        keeping the collapse strictly on the safe (only-SPLIT-relative-to-execution) side of the one-way law.

        BOUNDARY (decompile): only RECOMPILE targets collapse in this brick.  A DECOMPILE has no CLI aliases (a
        single ``decompile`` command), so no alias-equality property rides on it, and its target is a FORMULA-layer
        identity, not a structure -- so it keeps the raw keying (which only ever SPLITS, preserving the one-way
        law).  Collapsing the formula-layer descent is a named follow-on.
        """
        return canonical_digest(
            (
                "compilation-request-semantic-v1alpha3",
                self.schema_version,
                self.operation,
                self._target_identity_key,
                self.identity_policy,
                self.terminal_policy,
                frozenset(self.stock_materials),
                frozenset(self.helper_reagents),
                self.transform_grammar,
                # 0.7 Round II: the SELECTED ALGEBRA enters the search identity, as its RESOLVED registry digest (a
                # recomputable closed-profile mapping) -- so widening the algebra necessarily changes semantic_digest
                # (the pre-0.7 gap: identity was frozen to one algebra, so "equal digest => same search" was only
                # accidentally true).  The registry digest is itself content-bound (provider semantic descriptors),
                # so a change to a provider's rule/guard also moves it.
                resolve_algebra_profile(self.algebra_profile).digest,
                self.evidence_provider_selection,
                self.search_bounds,
                self.constraints,
                self.ranking_policy,
            )
        )


def _origins(explicit: "dict[str, bool]") -> tuple[tuple[str, FieldOrigin], ...]:
    """Turn a field->was-explicit map into the canonical origins tuple."""
    return tuple(
        sorted(
            (name, FieldOrigin.EXPLICIT if was_explicit else FieldOrigin.DEFAULT)
            for name, was_explicit in explicit.items()
        )
    )


def _canon(values: "tuple[str, ...]") -> tuple[str, ...]:
    """Canonicalise an identity list: sorted and de-duplicated (order/duplicates are not search identity)."""
    return tuple(sorted(set(values)))


def _resolve_identity_policy(
    identity_policy: "IdentityPolicy | None",
    match_layer: "MatchLayer | None",
    default_layer: MatchLayer,
) -> IdentityPolicy:
    """Resolve the request's :class:`IdentityPolicy` (ID-LAYER-02): an explicit policy wins whole; else a bare
    ``match_layer`` sets just the layer; else the operation's honest default layer.  A caller may not pass both."""
    if identity_policy is not None:
        if match_layer is not None:
            raise ValueError("pass either identity_policy or match_layer, not both")
        return identity_policy
    if match_layer is not None:
        return IdentityPolicy(match_layer=match_layer)
    return IdentityPolicy(match_layer=default_layer)


def _resolve_constraints(
    constraints: "ConstraintPolicy | None",
    max_temperature_k: "float | None",
    min_pressure_atm: "float | None",
    max_pressure_atm: "float | None",
    process: "ProcessBounds | None" = None,
) -> "tuple[ConstraintPolicy, bool]":
    """Resolve the request's :class:`ConstraintPolicy` (CLI-CAN-02) from an explicit policy OR bare T/P bound
    kwargs (a caller may not pass both).  Returns ``(policy, was_explicit)`` -- ``was_explicit`` is the
    ``constraints`` field's origin (a declared bound OR a passed policy is EXPLICIT; the unconstrained default is
    DEFAULT)."""
    any_bound = any(b is not None for b in (max_temperature_k, min_pressure_atm, max_pressure_atm, process))
    if constraints is not None:
        if any_bound:
            raise ValueError("pass either constraints or the T/P bound and process kwargs, not both")
        return constraints, True
    if any_bound:
        return ConstraintPolicy(
            PhysicalBounds.of(
                max_temperature_k=max_temperature_k,
                min_pressure_atm=min_pressure_atm,
                max_pressure_atm=max_pressure_atm,
            ),
            process=process if process is not None else ProcessBounds.unconstrained(),
        ), True
    return ConstraintPolicy(), False


def _recompile_normalized_identity(target_input: str, input_kind: InputKind) -> str:
    """The canonical STRUCTURE identity for the semantic-digest alias-collapse, or ``""`` if it must not collapse.

    Best-effort: resolve the target through the ONE parser service (the same resolution :func:`run_compilation`
    runs) and return :func:`~smartchem.compilation_ir._structure_ident` of the perceived molecule -- but ONLY when
    the input declares NO finer feature that would become a section-5.3 loss.  A SMILES stashes its stereo/isotope/
    charge in ``features`` while its ``losses`` stay empty, so a ``losses``-only gate would wrongly collapse a
    stereo SMILES with its flat twin; the gate therefore MIRRORS the run path (``_run_recompile``) and computes
    ``representation_losses_for(target_input, features)``, refusing to collapse when it is non-empty.  Any of
    (unresolvable, no molecule perceived, parser losses, feature losses) yields ``""`` -- the digest then keys on
    the raw input, so this can never MERGE two requests whose IRs differ by a loss.  It NEVER raises: a resolution
    failure is a normal "does not collapse" signal here, resolved for real (and refused if truly invalid) at run
    time.
    """
    from .identity import representation_losses_for
    from .identity_parse import IdentityParseError, resolve_identity
    # A TARGET_FILE is a MUTABLE external source: the file's contents can differ between this build-time resolution
    # and run_compilation's re-resolution, so a build-time normalized_identity could go stale and MERGE with a name
    # request that no longer names the same molecule (a build/run skew, red-team fix).  Its identity is the path, so
    # it keeps raw keying and never collapses -- the same "only a form the string fully determines may collapse" rule.
    if input_kind is InputKind.TARGET_FILE:
        return ""
    try:
        resolved = resolve_identity(target_input, input_kind)
    except IdentityParseError:
        return ""
    if resolved.molecule is None or resolved.losses:
        return ""
    feature_losses = representation_losses_for(target_input, resolved.features) if resolved.features else ()
    if feature_losses:
        return ""
    return _structure_ident(resolved.molecule)


def build_recompile_request(
    target_input: str,
    *,
    input_kind: "InputKind | None" = None,
    helper_reagents: "tuple[str, ...] | None" = None,
    stock_materials: "tuple[str, ...] | None" = None,
    commodities_enabled: "bool | None" = None,
    grammar: "TransformGrammar | None" = None,
    max_depth: "int | None" = None,
    max_routes: "int | None" = None,
    cut_budget: "int | None" = None,
    identity_policy: "IdentityPolicy | None" = None,
    match_layer: "MatchLayer | None" = None,
    constraints: "ConstraintPolicy | None" = None,
    process: "ProcessBounds | None" = None,
    max_temperature_k: "float | None" = None,
    min_pressure_atm: "float | None" = None,
    max_pressure_atm: "float | None" = None,
    ranking_policy: "RankingPolicy | None" = None,
    evidence_provider_selection: "EvidenceProviderSelection | None" = None,
    output_policy: "OutputPolicy | None" = None,
    algebra_profile: "str | None" = None,
) -> CompilationRequest:
    """Build a RECOMPILE request, recording each defaulted knob's origin as ``DEFAULT`` (section 13.1).

    This is the alias-independence engine: ``compile``, ``synthesize`` and ``recompile`` all build their request
    HERE, from ONE default table, so equal explicit flags always resolve to equal values and thus an equal
    :attr:`~CompilationRequest.semantic_digest`.  A value passed explicitly and the same value reached by default
    share the search identity but differ in :attr:`~CompilationRequest.origins`.  The section-11 T/P constraint is
    supplied either as a whole ``constraints`` policy or via the ``max_temperature_k``/``*_pressure_atm`` bound
    kwargs (CLI-CAN-02); it rides the search identity but is not yet applied to route grading (a follow-on).
    """
    resolved_constraints, constraints_explicit = _resolve_constraints(
        constraints, max_temperature_k, min_pressure_atm, max_pressure_atm, process
    )
    explicit = {
        "input_kind": input_kind is not None,
        "helper_reagents": helper_reagents is not None,
        "stock_materials": stock_materials is not None,
        "commodities_enabled": commodities_enabled is not None,
        "transform_grammar": grammar is not None,
        "max_depth": max_depth is not None,
        "max_routes": max_routes is not None,
        "cut_budget": cut_budget is not None,
        # one origin covers the identity policy however it was set -- as a whole object or via the match_layer knob.
        "identity_policy": identity_policy is not None or match_layer is not None,
        "constraints": constraints_explicit,
        "ranking_policy": ranking_policy is not None,
        "evidence_provider_selection": evidence_provider_selection is not None,
        "output_policy": output_policy is not None,
        "algebra_profile": algebra_profile is not None,
    }
    grammar = grammar if grammar is not None else TransformGrammar.CAPPED_SCISSION_LINEAR
    if grammar not in _RECOMPILE_GRAMMARS:
        raise ValueError("a recompile grammar must be CAPPED_SCISSION_LINEAR or CAPPED_SCISSION_CONVERGENT")
    # The SERVICE/CLI route builder stamps the PROMOTABLE route default (0.7 Round III): the one constant a
    # default-promotion commit flips to certified-route-v07.  It is deliberately NOT the frozen missing-field law
    # (request_from_payload) nor the low-level dataclass default -- so promoting the route default never changes what
    # a direct CompilationRequest or a pre-0.7 payload means.  Ships == legacy this round.
    algebra_profile = algebra_profile if algebra_profile is not None else DEFAULT_ROUTE_ALGEBRA_PROFILE
    effective_kind = input_kind if input_kind is not None else InputKind.AUTO
    return CompilationRequest(
        COMPILATION_REQUEST_SCHEMA,
        CompilationOperation.RECOMPILE,
        target_input,
        effective_kind,
        # SVC-REQ-01 alias-collapse: the canonical structure identity of the resolved target (or "" if it must
        # keep raw keying), so the semantic digest keys on WHAT the target is, not HOW it was spelled.
        _recompile_normalized_identity(target_input, effective_kind),
        # default recompile matching is at CONSTITUTION (the IdentityPolicy dataclass default), the one layer the
        # structural engine honestly honors; an explicit match_layer or identity_policy overrides.
        _resolve_identity_policy(identity_policy, match_layer, MatchLayer.CONSTITUTION),
        TerminalPolicy(
            "STRUCTURE",
            commodities_enabled if commodities_enabled is not None else True,
            (),
        ),
        _canon(stock_materials if stock_materials is not None else ()),
        _canon(helper_reagents if helper_reagents is not None else ("water",)),
        grammar,
        evidence_provider_selection if evidence_provider_selection is not None else EvidenceProviderSelection(),
        SearchBounds.of(
            max_depth=max_depth if max_depth is not None else 3,
            max_results=max_routes if max_routes is not None else 100,
            cut_budget=cut_budget if cut_budget is not None else 20_000,
        ),
        resolved_constraints,
        ranking_policy if ranking_policy is not None else RankingPolicy(),
        output_policy if output_policy is not None else OutputPolicy(),
        _origins(explicit),
        algebra_profile=algebra_profile,
    )


def build_decompile_request(
    target_input: str,
    *,
    input_kind: "InputKind | None" = None,
    formula_inventory: "tuple[str, ...] | None" = None,
    max_multiplicity: "int | None" = None,
    budget: "int | None" = None,
    max_edges: "int | None" = None,
    identity_policy: "IdentityPolicy | None" = None,
    match_layer: "MatchLayer | None" = None,
    ranking_policy: "RankingPolicy | None" = None,
    evidence_provider_selection: "EvidenceProviderSelection | None" = None,
    output_policy: "OutputPolicy | None" = None,
) -> CompilationRequest:
    """Build a DECOMPILE request (formula descent).  ``formula_inventory`` are the buckets to bottom out at
    (default: pure elements, ``()``).

    NOTE (CLI-CAN-01): the ``decompile`` CLI command defaults its inventory to the richer *example inventory*;
    the service default here is pure elements.  ``decompile`` is a single command with no aliases, so no
    alias-equality property rides on it; reconciling the two defaults belongs to routing the ``decompile`` argv
    through this service (CLI-CAN-01), not this first brick.
    """
    explicit = {
        "input_kind": input_kind is not None,
        "formula_inventory": formula_inventory is not None,
        "max_multiplicity": max_multiplicity is not None,
        "budget": budget is not None,
        "max_edges": max_edges is not None,
        "identity_policy": identity_policy is not None or match_layer is not None,
        "ranking_policy": ranking_policy is not None,
        "evidence_provider_selection": evidence_provider_selection is not None,
        "output_policy": output_policy is not None,
    }
    return CompilationRequest(
        COMPILATION_REQUEST_SCHEMA,
        CompilationOperation.DECOMPILE,
        target_input,
        input_kind if input_kind is not None else InputKind.AUTO,
        # SVC-REQ-01 alias-collapse is RECOMPILE-only in this brick: a decompile has no CLI aliases and its target
        # is a FORMULA-layer identity, so it keeps raw keying ("") -- collapsing the formula descent is a follow-on.
        "",
        # a formula descent matches at FORMULA -- the one layer it perceives; an explicit override is enforced
        # (a decompile declaring a structural layer is refused by run_compilation, since a formula cannot see it).
        _resolve_identity_policy(identity_policy, match_layer, MatchLayer.FORMULA),
        TerminalPolicy(
            "FORMULA_ONLY",
            False,
            _canon(formula_inventory if formula_inventory is not None else ()),
        ),
        (),  # stock_materials: a formula descent has no structural stock
        (),  # helper_reagents: a formula descent consumes no cutting reagent
        TransformGrammar.FORMULA_DECOMPOSITION,
        evidence_provider_selection if evidence_provider_selection is not None else EvidenceProviderSelection(),
        SearchBounds.of(
            max_multiplicity=max_multiplicity if max_multiplicity is not None else 1,
            budget=budget if budget is not None else 100_000,
            max_edges=max_edges if max_edges is not None else 5_000,
        ),
        ConstraintPolicy(),
        ranking_policy if ranking_policy is not None else RankingPolicy(),
        output_policy if output_policy is not None else OutputPolicy(),
        _origins(explicit),
    )


# -- the response ------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RankedRouteSummary(Digestible):
    """One route's section-11 bench-fit disposition, ranked best-first in the response (CLI-CAN-02 brick 2).

    A thin, presentation-invariant projection of a drafter :class:`~smartchem.experiment.drafter.RouteFit`: it keeps
    the decision-relevant facts (the candidate identity, the fit verdict with exact reasons, the readiness floor, and
    the ranking's sourced verdicts) WITHOUT dragging the full ``ExperimentRoute``/thermo object graph into the
    response.  ``route_digest`` is byte-identical to the matching IR :class:`CandidateSummary.candidate_digest`, so a
    ranked entry links back to its candidate.  ``fit_status`` is the applied section-11 verdict: ``FITS`` (within
    every declared bound), ``EXCLUDED`` (a hard over/under-bound, in ``exclusions``), ``UNKNOWN`` (a constrained
    dimension the route leaves undeclared -- a ``gaps`` entry, NEVER a silent pass), or ``UNCONSTRAINED`` (the bench
    box declares nothing to fit).  ``readiness_tier`` is DERIVED, never stored -- a ``@property`` reading straight off
    ``readiness.tier`` (v0.8 Real Route Dossiers: the old READY-TIER-01 wall, a hard-coded ``FORMAL_CANDIDATE`` no
    route could ever earn or lose, is retired). The four verdict strings are the ranking tiebreakers, exposed so the
    order is inspectable (a ranking you cannot read is multiple choice); they are ranking-only and NEVER a
    bench-readiness grade.
    """

    schema_version: str
    route_digest: str
    equation: str
    fit_status: str
    #: The typed Sec 3/4/8 obligation ladder for this route (``smartchem.experiment.readiness.RouteReadiness``) --
    #: the SOURCE OF TRUTH; ``readiness_tier`` below is a derived projection of it, never the reverse. Digest-covered
    #: (``compare=True``, the default) so a readiness claim is part of route identity -- tampering with it is a
    #: detectable identity change, not a silent relabel, mirroring ``process_requirements`` exactly.
    readiness: RouteReadiness
    exclusions: tuple[str, ...]
    gaps: tuple[str, ...]
    composability_verdict: str
    selectivity_verdict: str
    feasibility_verdict: str
    equilibrium_verdict: str
    kinetics_verdict: str
    #: The per-step declared process facts the section-11 fit was computed from, one entry per route step in order
    #: (``None`` = an undeclared step, exactly as ``envelope.process`` is ``None``).  Carried so process admission is
    #: RE-DERIVED on load (PROCESS-ADMIT-01) via ``evaluate_process_requirements`` rather than trusting ``fit_status``:
    #: a declared FITS/UNKNOWN whose evidence re-derives to a stricter PROCESS verdict is refused (see
    #: ``CompilationResponse._check_process_admission_coherence``).  Part of route identity -- folded into
    #: ``result_digest`` -- so tampering with the evidence is a detectable identity change, not a silent relabel.
    process_requirements: "tuple[ProcessRequirements | None, ...]"
    #: ONLOAD-REDERIVE (item 2): the COMPLETE steps of the route this summary projects, as a thick replay payload
    #: (each step's target/reactants/products/reagents + full 10-field envelope).  Carried so a verified-admission
    #: consumer can RECONSTRUCT the exact ``ExperimentRoute`` and re-derive the WHOLE combined verdict (composability +
    #: physical + process) AND the ranking verdicts on load -- not just the process axis -- binding the evidence to
    #: ``route_digest`` (reconstruct(payload).digest == route_digest).  DIGEST-EXCLUDED (``compare=False``): route
    #: identity stays byte-stable, so it is re-derived-and-checked at load, never trusted by hash.  ``None`` when the
    #: producer did not attach it; a verified-admission consumer treats a FITS route without it as UNVERIFIED.
    replay_payload: "list | None" = field(default=None, compare=False, repr=False)

    _FIT_STATUSES = ("FITS", "EXCLUDED", "UNKNOWN", "UNCONSTRAINED")

    def __post_init__(self) -> None:
        if self.schema_version != RANKED_ROUTE_SUMMARY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {RANKED_ROUTE_SUMMARY_SCHEMA!r}")
        if self.fit_status not in self._FIT_STATUSES:
            raise ValueError(f"fit_status must be one of {self._FIT_STATUSES}")
        if type(self.readiness) is not RouteReadiness:
            raise TypeError("readiness must be a RouteReadiness")
        for name in ("route_digest", "equation", "composability_verdict", "selectivity_verdict",
                     "feasibility_verdict", "equilibrium_verdict", "kinetics_verdict"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("exclusions", "gaps"):
            seq = getattr(self, name)
            if type(seq) is not tuple or any(not isinstance(x, str) or not x for x in seq):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
        if type(self.process_requirements) is not tuple or any(
            r is not None and type(r) is not ProcessRequirements for r in self.process_requirements
        ):
            raise TypeError("process_requirements must be a tuple of ProcessRequirements or None values")
        # The FULL structural coherence table the producer (drafter fit_route) guarantees, enforced so a hand-built or
        # deserialized summary can never contradict its own reasons (the no-laundering discipline, section 11; red-team
        # fold). fit_route sets: EXCLUDED iff exclusions; else UNKNOWN iff gaps; else FITS (box constrains) /
        # UNCONSTRAINED. So a PASS disposition (FITS/UNCONSTRAINED) has NEITHER a hard exclusion NOR a gap -- a FITS or
        # UNCONSTRAINED with a gap would be a silent pass over an unassessed dimension. EXCLUDED must give a reason;
        # UNKNOWN must give the gap that makes it unknown and must NOT carry a hard exclusion (that would be EXCLUDED).
        if self.fit_status == "EXCLUDED":
            if not self.exclusions:
                raise ValueError("an EXCLUDED route must carry at least one exclusion reason")
        elif self.exclusions:
            raise ValueError(f"a {self.fit_status} route cannot carry exclusion reasons (only EXCLUDED may)")
        if self.fit_status == "UNKNOWN" and not self.gaps:
            raise ValueError("an UNKNOWN-fit route must carry at least one gap (the unassessed dimension)")
        if self.fit_status in ("FITS", "UNCONSTRAINED") and self.gaps:
            raise ValueError(f"a {self.fit_status} route cannot carry gaps -- a gap is an UNKNOWN-fit, not a pass")

    @property
    def readiness_tier(self) -> str:
        """Backward-compat alias: the coarse tier, read straight off the typed ``readiness`` record.  Kept as a
        derived property (not a stored field) so ``readiness_tier`` can never disagree with ``readiness`` -- there
        is only one place a caller can construct a lie, and it is ``readiness`` itself (which ``evaluate_route``'s
        own dataclasses refuse to build incoherently)."""
        return self.readiness.tier

    @classmethod
    def of_fit(cls, fit: "object", *, identity_losses: "tuple[IdentityLoss, ...]" = ()) -> "RankedRouteSummary":
        """Project a drafter ``RouteFit`` (already box-checked and ranked) onto the thin response summary.

        ``identity_losses`` is the route's already-computed section-5.3 loss tuple (the SAME tuple the caller threads
        into ``rank_routes``); readiness's ``conditions`` obligation is capped by any loss that blocks it (Sec 5.3),
        so the readiness record must see the identical evidence the ranking did.  Defaults to ``()`` for callers that
        genuinely have none in scope (the overwhelming majority of today's corpus)."""
        return cls(
            RANKED_ROUTE_SUMMARY_SCHEMA,
            fit.route.digest,
            " ; ".join(fit.route.equation_lines()) or repr(fit.route),
            fit.status.value,
            # v0.8 Real Route Dossiers: readiness is RE-DERIVED from the route's own steps (Sec 3/4), never a
            # hard-coded stamp -- ``evaluate_route`` reads only conservation-certified facts already on each built
            # ``ExperimentStep`` (reaction-type recognition, sourced conditions, process/workup declarations).
            evaluate_route(fit.route, identity_losses=identity_losses),
            tuple(fit.exclusions),
            tuple(fit.gaps),
            fit.composability.verdict,
            fit.selectivity.verdict,
            fit.feasibility.verdict,
            fit.equilibrium.verdict,
            fit.kinetics.verdict,
            # The exact per-step process evidence the fit was computed from, so admission is re-derivable on load.
            tuple(step.envelope.process for step in fit.route.steps),
            # ONLOAD-REDERIVE (item 2): the thick replay payload -- the route's complete steps -- so a verified-admission
            # consumer can reconstruct the exact route and re-derive ALL axes on load.  Built here (cheap serialization,
            # no re-analysis); emitted to the wire only when the producer serializes with include_replay=True.
            replay_payload=_steps_to_replay_payload(fit.route.steps),
        )


def _validate_dag_edges(edges: "tuple[tuple[int, int], ...]", n: int) -> None:
    """Validate that ``edges`` form a LEGAL DAG SHAPE over ``n`` step indices (DAG-ADMIT-01): unique pairs of distinct
    in-range indices, acyclic, with exactly ONE sink (out-degree-0 final target) that every step reaches.

    This is the convergent analogue of a linear route's implicit "tuple order IS the topology" -- the shape a carried
    ``edges`` field must satisfy before its critical path means anything.  It enforces exactly the structural
    invariants :meth:`SynthesisDAG.__post_init__` does (acyclic / single sink / no orphan branch), on bare indices
    rather than ExperimentStep objects, so a deserialized or hand-built DAG summary fails CLOSED on a malformed graph.
    It does NOT (cannot) check the carried edges match the real molecule flow -- that residual is closed by the
    ``result_digest`` the edges are folded into plus the opt-in producer signature, exactly as for the linear axis.
    """
    if type(edges) is not tuple or any(
        type(e) is not tuple or len(e) != 2 or type(e[0]) is not int or type(e[1]) is not int for e in edges
    ):
        raise TypeError("edges must be a tuple of (int, int) index pairs")
    if type(n) is not int or n <= 0:
        raise ValueError("a DAG summary must carry at least one process step")
    for a, b in edges:
        if not (0 <= a < n) or not (0 <= b < n):
            raise ValueError(f"edge ({a}, {b}) is out of range for {n} steps")
        if a == b:
            raise ValueError(f"edge ({a}, {b}) is a self-loop")
    if len(set(edges)) != len(edges):
        raise ValueError("edges must be unique")
    outdeg = [0] * n
    indeg = [0] * n
    succ: "list[list[int]]" = [[] for _ in range(n)]
    for a, b in edges:
        outdeg[a] += 1
        indeg[b] += 1
        succ[a].append(b)
    # Kahn pass: a leftover node means a cycle (longest-path/critical-path would be ill-defined).
    work = list(indeg)
    queue = [i for i in range(n) if work[i] == 0]
    seen = 0
    while queue:
        i = queue.pop()
        seen += 1
        for j in succ[i]:
            work[j] -= 1
            if work[j] == 0:
                queue.append(j)
    if seen != n:
        raise ValueError("edges contain a cycle; a synthesis DAG must be acyclic")
    sinks = [i for i in range(n) if outdeg[i] == 0]
    if len(sinks) != 1:
        raise ValueError(f"a DAG must have exactly one sink (final target); found {len(sinks)}")
    reaching = {sinks[0]}
    changed = True
    while changed:
        changed = False
        for a, b in edges:
            if b in reaching and a not in reaching:
                reaching.add(a)
                changed = True
    if len(reaching) != n:
        raise ValueError("every step must reach the final target; a DAG may not carry an orphan branch")


@dataclass(frozen=True)
class RankedDAGSummary(Digestible):
    """One convergent-DAG candidate's COMBINED section-11 bench admission, carried so a DAG-mode compile's bench gate
    is a FORMAL, load-re-derived admission rather than a throwaway diagnostic (DAG-BENCH-01, superseding the
    process-axis-only DAG-ADMIT-01).

    Now a TRUE analogue of :class:`RankedRouteSummary`: a linear route carries the COMBINED section-11 verdict
    (composability + physical box + process), and this DAG summary carries the SAME combined verdict, re-shaped for the
    convergent structure -- :func:`~smartchem.experiment.drafter.dag_bench_fit` folds E1 composability across the DAG's
    edges, the per-step physical box, and the critical-path-aware process axis into one ``fit_status``.  It ALSO carries
    the per-step ``process_requirements`` AND the DAG ``edges`` (producer->consumer index pairs, indexing the DAG's own
    step order) so the PROCESS COMPONENT of that combined verdict is RE-DERIVED on load via
    :func:`~smartchem.process_constraints.evaluate_dag_process_requirements` (the convergent analogue of
    PROCESS-ADMIT-01, which the critical-path elapsed aggregation needs the topology for).  ``route_digest`` is
    byte-identical to the DAG's IR :class:`CandidateSummary.candidate_digest` (both ``SynthesisDAG.digest``), so a
    dossier links back to its candidate.

    SOUNDNESS BOUNDARY (identical in kind to the linear axis): ``fit_status`` is the combined verdict, but only its
    PROCESS component is re-derived on load; the composability and physical/reagent/equipment components ride as
    free-text ``exclusions``/``gaps`` (re-deriving them needs the full ExperimentStep graph the thin projection omits),
    exactly as :class:`RankedRouteSummary` leaves those two axes un-re-derived.  And ``edges`` is carried, not
    re-derived from the molecule graph, so ``__post_init__`` validates only that ``edges`` form a LEGAL DAG SHAPE
    (:func:`_validate_dag_edges`).  A forger who relabels ``edges`` to a DIFFERENT legal DAG (shortening the critical
    path to dodge an EXCLUDE), or who bare-relabels a composability/physical EXCLUDE to FITS, is caught exactly as the
    linear forger is -- by the ``result_digest`` the ``edges``/``fit_status`` are folded into, closed by the opt-in
    producer signature (COMBINED-VERDICT-AUTH).  A FITS is SOUND to admit as a bench pass: ``dag_process_fit``'s FITS is
    the SERIAL-sum ceiling, so it is achievable one-step-at-a-time by a single operator -- the joint-concurrent-
    schedulability boundary bites only the UNKNOWN band, never a FITS.  ONE strengthening a linear FITS does not carry
    (evil-morty fold): a serial schedule of a convergent DAG HOLDS an early branch's intermediate through its sibling
    branches, and E1 composability is time-blind (adjacent-handoff only), so that serial-hold stability is UNVERIFIED --
    unmodeled until the stability model grows a time / max-hold axis.
    """

    schema_version: str
    route_digest: str
    equation: str
    fit_status: str
    exclusions: tuple[str, ...]
    gaps: tuple[str, ...]
    process_requirements: "tuple[ProcessRequirements | None, ...]"
    edges: "tuple[tuple[int, int], ...]"
    # DAG-THERMO-01: the five ranking verdict strings, projected off dag_bench_fit -- parity with RankedRouteSummary.
    # RANKING-ONLY (they order otherwise-tied DAGs; they NEVER change fit_status) and part of identity (folded into the
    # digest, so a forger cannot relabel a DISFAVORED/UNFAVORABLE verdict to a favorable one without the digest moving).
    composability_verdict: str = "UNKNOWN"
    selectivity_verdict: str = "UNKNOWN"
    feasibility_verdict: str = "UNKNOWN"
    equilibrium_verdict: str = "UNKNOWN"
    kinetics_verdict: str = "UNKNOWN"
    # DAG-HOLD-01 made machine-readable (item 2b): the per-edge serial-schedule hold as (producer, consumer,
    # hold_minutes) triples, so a consumer reads the hold structurally instead of parsing the human note.  It is
    # DISCLOSURE, not a gate (it never changes fit_status), and it is FULLY DETERMINED by the digest-bearing
    # ``edges`` + ``process_requirements`` (via _serial_hold_minutes) -- so it adds no identity and is EXCLUDED
    # from the digest (compare=False): existing DAG digests are byte-stable, and a consumer who distrusts it can
    # re-derive it from the digest-protected fields.
    serial_holds: "tuple[tuple[int, int, float], ...]" = field(default=(), compare=False)
    #: ONLOAD-REDERIVE (item 2): the DAG's COMPLETE steps as a thick replay payload (mirrors
    #: :attr:`RankedRouteSummary.replay_payload`), so a verified-admission consumer reconstructs the exact
    #: ``SynthesisDAG`` and re-derives the whole combined verdict + edge/process projection + ranking verdicts on
    #: load.  DIGEST-EXCLUDED (``compare=False``): DAG identity stays byte-stable; re-derived-and-checked, never trusted.
    replay_payload: "list | None" = field(default=None, compare=False, repr=False)

    _FIT_STATUSES = ("FITS", "EXCLUDED", "UNKNOWN", "UNCONSTRAINED")

    def __post_init__(self) -> None:
        if self.schema_version != RANKED_DAG_SUMMARY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {RANKED_DAG_SUMMARY_SCHEMA!r}")
        if self.fit_status not in self._FIT_STATUSES:
            raise ValueError(f"fit_status must be one of {self._FIT_STATUSES}")
        for name in ("route_digest", "equation", "composability_verdict", "selectivity_verdict",
                     "feasibility_verdict", "equilibrium_verdict", "kinetics_verdict"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("exclusions", "gaps"):
            seq = getattr(self, name)
            if type(seq) is not tuple or any(not isinstance(x, str) or not x for x in seq):
                raise TypeError(f"{name} must be a tuple of non-empty strings")
        if type(self.process_requirements) is not tuple or any(
            r is not None and type(r) is not ProcessRequirements for r in self.process_requirements
        ):
            raise TypeError("process_requirements must be a tuple of ProcessRequirements or None values")
        # The fit coherence table (mirrors RankedRouteSummary/RouteFit): EXCLUDED iff exclusions; UNKNOWN iff gaps;
        # FITS/UNCONSTRAINED carry NEITHER -- so a hand-built/deserialized summary can never launder a lenient status.
        if self.fit_status == "EXCLUDED":
            if not self.exclusions:
                raise ValueError("an EXCLUDED DAG must carry at least one exclusion reason")
        elif self.exclusions:
            raise ValueError(f"a {self.fit_status} DAG cannot carry exclusion reasons (only EXCLUDED may)")
        if self.fit_status == "UNKNOWN" and not self.gaps:
            raise ValueError("an UNKNOWN-fit DAG must carry at least one gap (the unassessed dimension)")
        if self.fit_status in ("FITS", "UNCONSTRAINED") and self.gaps:
            raise ValueError(f"a {self.fit_status} DAG cannot carry gaps -- a gap is an UNKNOWN-fit, not a pass")
        _validate_dag_edges(self.edges, len(self.process_requirements))
        # serial_holds: well-formed (producer, consumer, minutes>=0) triples, each over a REAL carried edge
        # (a hold is the extra hold on an existing producer->consumer intermediate), never a fabricated pair.
        if type(self.serial_holds) is not tuple:
            raise TypeError("serial_holds must be a tuple of (producer, consumer, hold_minutes) triples")
        edge_set = set(self.edges)
        for hold in self.serial_holds:
            if type(hold) is not tuple or len(hold) != 3:
                raise TypeError("each serial_holds entry must be a (producer, consumer, hold_minutes) triple")
            i, j, minutes = hold
            if isinstance(i, bool) or isinstance(j, bool) or type(i) is not int or type(j) is not int:
                raise TypeError("serial_holds producer/consumer indices must be ints")
            if (i, j) not in edge_set:
                raise ValueError(f"serial_holds entry {(i, j)} is not one of the DAG's carried edges")
            if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes < 0:
                raise ValueError("serial_holds hold_minutes must be a non-negative real number")

    @classmethod
    def of_dag(cls, dag: "object", box: "object", *, phases: "object" = None) -> "RankedDAGSummary":
        """Project a SynthesisDAG's COMBINED section-11 bench fit (:func:`dag_bench_fit`) onto the thin response summary.

        ``box`` is the full :class:`~smartchem.experiment.drafter.ConstraintBox` (physical bounds + process), so the
        carried ``fit_status``/``exclusions``/``gaps`` are the combined verdict (composability + physical + process) --
        the SAME combined disposition a linear :class:`RankedRouteSummary` carries.  The ``process_requirements`` and
        ``edges`` are taken in the DAG's OWN step order (``dag.steps`` / ``dag.edges``), the exact indexing
        :func:`~smartchem.process_constraints.evaluate_dag_process_requirements` uses, so the load-time re-derivation of
        the PROCESS COMPONENT reproduces that component byte-for-byte.

        ``phases`` (ITEM5-DAG-PHASE-01): the optional ``{Molecule: phase}`` declaration is forwarded to
        :func:`dag_bench_fit`, so the projected FEASIBILITY ranking verdict reflects the DECLARED phase of any
        dual-phase species -- the seam that makes :func:`rank_dags`'s ``phases`` sound.  The RANKER and THIS projection
        must be driven by the SAME declaration or the dossier's feasibility verdict would disagree with the rank that
        produced it (the exact ROUND-15 re-projection divergence); :func:`ranked_dag_dossiers` is the seam that passes
        one dict into both.  ``phases`` never touches ``fit_status`` (it is a ranking-only verdict), so a phase-declared
        dossier's PASS/EXCLUDED disposition is unchanged.  BOUNDARY (fail-closed): :func:`_check_verified_admission`
        re-projects phase-blind, so a phase-DECLARED FITS dossier round-tripped through ``require_verified_admission`` is
        REFUSED (a false-REJECT, never a false-ACCEPT -- the status is phase-invariant); production is unaffected
        (``_run_recompile`` passes no phases).  See :func:`ranked_dag_dossiers` and the scope doc Boundary 4.  Default
        ``None`` is byte-identical."""
        from .experiment.dag import _serial_hold_minutes
        from .experiment.drafter import dag_bench_fit
        fit = dag_bench_fit(dag, box, phases=phases)
        edges = tuple((producer, consumer) for producer, consumer, _intermediate in dag.edges)
        equation = " ; ".join(s.equation() for s in dag.topological_order())
        # DAG-HOLD-01 made machine-readable (item 2b): the same per-edge serial-schedule hold ROUND 15 surfaced
        # as a human note, now as sorted (producer, consumer, minutes) triples over the edges that actually hold
        # (> 0).  Disclosure only -- it does not touch fit_status -- so a zero-hold linear-shaped DAG carries ().
        serial_holds = tuple(
            (i, j, minutes) for (i, j), minutes in sorted(_serial_hold_minutes(dag).items()) if minutes > 0
        )
        return cls(
            RANKED_DAG_SUMMARY_SCHEMA,
            dag.digest,
            equation or repr(dag),
            fit.status.value,
            tuple(fit.exclusions),
            tuple(fit.gaps),
            tuple(step.envelope.process for step in dag.steps),
            edges,
            # DAG-THERMO-01: the five ranking verdicts, the SAME dag_bench_fit that decided fit_status.  composability
            # comes off the DAGComposability object; the four thermo verdicts ride on the DAGBenchFit itself.
            fit.composability.verdict,
            fit.selectivity_verdict,
            fit.feasibility_verdict,
            fit.equilibrium_verdict,
            fit.kinetics_verdict,
            serial_holds,
            # ONLOAD-REDERIVE (item 2): the thick replay payload -- the DAG's complete steps in its own step order --
            # so a verified-admission consumer reconstructs the exact SynthesisDAG and re-derives all axes on load.
            replay_payload=_steps_to_replay_payload(dag.steps),
        )


def ranked_dag_dossiers(dags, box: "object", *, phases: "object" = None) -> "tuple[RankedDAGSummary, ...]":
    """Rank convergent DAGs best-first AND project each into a :class:`RankedDAGSummary`, under ONE phase declaration.

    This is the co-call SEAM the ROUND-15 ``of_dag`` re-projection fold named as the unlock for DAG phase-awareness
    (ITEM5-DAG-PHASE-01): :func:`~smartchem.experiment.drafter.rank_dags` ranks the DAGs and
    :meth:`RankedDAGSummary.of_dag` re-projects each dossier, and passing the SAME ``phases`` into both is exactly what
    makes a phase-declared DAG ranking SOUND -- the rank and the dossier read the identical declaration, so a dossier's
    feasibility verdict can never disagree with the rank that produced it.  Threading ``phases`` into only one side
    would reopen the precise divergence the fold prevented; keeping the two behind one seam that takes one dict makes
    "both move together" structural AT THIS SEAM (the birdperson alignment discipline).  It is NOT a global invariant:
    :func:`~smartchem.experiment.drafter.rank_dags` and :meth:`RankedDAGSummary.of_dag` stay independently public, so a
    caller that BYPASSES this seam and calls them with mismatched (or one-sided) ``phases`` still owns the consistency
    obligation -- prefer this seam.  ``phases=None`` (the default, and every current caller) is byte-identical to the
    prior inline ``of_dag(d, box) for d in rank_dags(dags, box)``.

    VERIFIED-ADMISSION BOUNDARY (evil-morty/dalembert R44, fail-closed): the on-load re-projection
    (:func:`_check_verified_admission`) recomputes ``of_dag(dag, box)`` PHASE-BLIND, so a phase-DECLARED FITS dossier
    this seam emits does NOT equal its phase-blind re-projection and is REFUSED on a ``require_verified_admission``
    round-trip.  This is FAIL-CLOSED (a false-REJECT, never a false-ACCEPT -- a phase never moves a section-11 status,
    so it can never admit a forged route) and at exact parity with the R43 linear side.  Production never hits it
    (``_run_recompile`` passes no phases); it unparks with the request-level phase field that would carry ``phases``
    into the replay payload + the re-projection (the named next brick).  See
    ``docs/research/ITEM5_DAG_PHASE_AWARE_RANKING_SCOPE_v0.1.md`` Boundary 4."""
    from .experiment.drafter import rank_dags
    return tuple(RankedDAGSummary.of_dag(d, box, phases=phases) for d in rank_dags(dags, box, phases=phases))


@dataclass(frozen=True)
class CompilationResponse:
    """One typed response for either compiler direction (standard section 13.2).

    It wraps the request, the produced :class:`~smartchem.compilation_ir.ChemicalCompilationIR` (the core of the
    section 13.2 fields -- ``normalized_target``, ``identity_losses`` and ``candidates`` read through to it in
    full), a TOTAL :class:`ResponseOutcome`, and the section 8.2 ``standard_status`` where a search ran.  The
    section 13.2 ``search_receipt`` now rides in FULL inside the IR (``compilation_ir.search_receipt``, a
    :class:`~smartchem.compilation_ir.Section81ReceiptView` with the ~20 mandated counters -- IR-CHEM-01), so the
    receipt CONTENT is recoverable from the response's machine payload; :attr:`search_receipt_digest` remains as a
    convenience digest of that view.
    ``ranked_route_dossiers`` (section 13.2) is POPULATED on a routes-mode search (CLI-CAN-02 brick 2) with typed
    :class:`RankedRouteSummary` values -- the per-route section-11 bench-fit disposition, best-first.
    ``affordability_frontier`` (section 13.2) is POPULATED on a routes-mode search (COST-VEC-01) with typed
    ``AffordabilityFrontierEntry`` values -- the section-10.4 Pareto affordability frontier over the ranked routes;
    empty when no route carries affordability signal (honest, not "unbuilt").  ``provider_snapshots`` (SNAPSHOT-13.2)
    is the dated section-13.2 provenance seam for a response whose RESULT depends on a live provider fetch; the alpha
    machine search is offline-deterministic and consumes no fetched evidence, so it is present-and-empty on every
    current path (a named limitation -- the synthesize HUMAN dossier is where a fetch's snapshot is rendered).  Both
    are DELIBERATELY EXCLUDED from :attr:`result_digest` (a price/fetch-time is dated data, not search identity, so
    two aliases that ran the same search share a result_digest regardless of them).

    ``parse_receipt_summary`` (SVC-REQ-01 alias-collapse) is the section-14.2 identity-resolution echo (how the
    target STRING was read: source, normalised form, layer).  It is a FIRST-CLASS field, not a line buried in
    ``diagnostics``, precisely because it is PROVENANCE: it is surfaced in both views (the section 14.3 receipt) but
    is DELIBERATELY EXCLUDED from :attr:`result_digest`, because two spellings of the same target run the same
    search and MUST share a result even though they were read differently.  ``diagnostics`` therefore carries only
    genuine search facts (the IR's own diagnostics), which is exactly what :attr:`result_digest` may hash.

    Not a :class:`~smartchem.contracts.Digestible`: it has nullable fields (``standard_status``,
    ``compilation_ir``) that the canonical encoder rejects, so identity is exposed as :attr:`result_digest`, which
    handles the null cases explicitly.
    """

    schema_version: str
    request: CompilationRequest
    outcome: ResponseOutcome
    standard_status: "str | None"
    compilation_ir: "ChemicalCompilationIR | None"
    diagnostics: tuple[str, ...] = ()
    ranked_route_dossiers: tuple = ()
    affordability_frontier: tuple = ()
    provider_snapshots: tuple = ()
    parse_receipt_summary: "str | None" = None
    #: DAG-BENCH-01: the per-DAG COMBINED section-11 bench admission for a convergent (DAG-mode) compile -- typed
    #: ``RankedDAGSummary`` values carrying each candidate's ``dag_bench_fit`` combined verdict (composability + physical
    #: + process) + its per-step ``process_requirements`` + ``edges``, so the PROCESS component is RE-DERIVED on load
    #: (the convergent analogue of ``ranked_route_dossiers``).  Empty in routes/decompile mode and on an
    #: unconstrained-bench request; present-and-populated for a bench-constrained DAG-mode compile.  Folded into
    #: ``result_digest`` ONLY when non-empty (zero linear ripple).
    ranked_dag_dossiers: tuple = ()

    def __post_init__(self) -> None:
        if self.schema_version != COMPILATION_RESPONSE_SCHEMA:
            raise ValueError(f"schema_version must be exactly {COMPILATION_RESPONSE_SCHEMA!r}")
        if type(self.request) is not CompilationRequest:
            raise TypeError("request must be a CompilationRequest")
        if not isinstance(self.outcome, ResponseOutcome):
            raise TypeError("outcome must be a ResponseOutcome")
        if self.compilation_ir is not None and type(self.compilation_ir) is not ChemicalCompilationIR:
            raise TypeError("compilation_ir must be a ChemicalCompilationIR or None")
        if self.standard_status is not None and self.standard_status not in STANDARD_8_2_STATUSES:
            raise ValueError("standard_status must be a section 8.2 status or None")
        if type(self.diagnostics) is not tuple or any(not isinstance(x, str) for x in self.diagnostics):
            raise TypeError("diagnostics must be a tuple of strings")
        if self.parse_receipt_summary is not None and not isinstance(self.parse_receipt_summary, str):
            raise TypeError("parse_receipt_summary must be a string or None")
        # CLI-CAN-02 brick 2: ``ranked_route_dossiers`` is populated (routes mode) with typed RankedRouteSummary
        # values -- the section-11 fit disposition per route.  The type is guarded so a hand-built/deserialized
        # response cannot smuggle an untyped blob past the coherence checks.  ``affordability_frontier`` stays empty
        # (COST-VEC-01 unbuilt): present-and-empty, never absent, so the shape is stable and the empty is HONEST.
        if type(self.ranked_route_dossiers) is not tuple or any(
            type(r) is not RankedRouteSummary for r in self.ranked_route_dossiers
        ):
            raise TypeError("ranked_route_dossiers must be a tuple of RankedRouteSummary values")
        if self.ranked_route_dossiers and self.compilation_ir is not None:
            candidate_ids = {c.candidate_digest for c in self.compilation_ir.candidates}
            ranked_ids = tuple(r.route_digest for r in self.ranked_route_dossiers)
            if len(ranked_ids) != len(set(ranked_ids)):
                raise ValueError("ranked route digests must be unique")
            if not set(ranked_ids) <= candidate_ids:
                raise ValueError("ranked route digest must identify a returned IR candidate")
        # COST-VEC-01: ``affordability_frontier`` is now POPULATED (routes mode) with typed AffordabilityFrontierEntry
        # values -- the section-10.4 Pareto frontier.  The type is guarded (like ranked_route_dossiers) so a
        # hand-built/deserialized response cannot smuggle an untyped blob past the coherence checks.  The import is
        # lazy AND only on a non-empty frontier, so the common empty-frontier path never drags the experiment layer
        # (the service's layering discipline).  An empty frontier is HONEST: no route carried affordability signal.
        if type(self.affordability_frontier) is not tuple:
            raise TypeError("affordability_frontier must be a tuple")
        if self.affordability_frontier:
            from .experiment.affordability import AffordabilityFrontierEntry
            if any(type(e) is not AffordabilityFrontierEntry for e in self.affordability_frontier):
                raise TypeError("affordability_frontier must be a tuple of AffordabilityFrontierEntry values")
            frontier_ids = tuple(e.route_digest for e in self.affordability_frontier)
            candidate_ids = set() if self.compilation_ir is None else {
                c.candidate_digest for c in self.compilation_ir.candidates
            }
            if len(frontier_ids) != len(set(frontier_ids)) or not set(frontier_ids) <= candidate_ids:
                raise ValueError("affordability frontier must identify unique returned IR candidates")
            # FRONTIER<=DOSSIERS (TAMPER-HARDENING-01, thin-transport-closure fold).  Every honest frontier entry is
            # built from a ranked route summary and keyed by that summary's ``route_digest`` (``_affordability_frontier``),
            # so a frontier entry ALWAYS has a matching ``ranked_route_dossiers`` entry -- the authority its disposition
            # is re-derived against on load.  Enforce that here, UNCONDITIONALLY (not only under a process box): an entry
            # whose ``route_digest`` matches no dossier is UNVERIFIABLE, and a tamperer who DELETES the matching dossier
            # (the frontier is digest-excluded, so the deletion is otherwise only caught if it perturbs the digest-covered
            # dossier list) would otherwise reach the ``summary is None`` skip in ``_check_frontier_coherence`` and slip a
            # forged CLEAN disposition past even verified admission.  Making the state unrepresentable closes that on
            # every transport and every load mode; the fail-closed skip below is the defence-in-depth backstop.
            dossier_ids = {r.route_digest for r in self.ranked_route_dossiers}
            if not set(frontier_ids) <= dossier_ids:
                raise ValueError(
                    "affordability frontier must reference ranked_route_dossiers routes -- an entry whose route_digest "
                    "matches no dossier is UNVERIFIABLE (its disposition cannot be re-derived); refused "
                    "(TAMPER-HARDENING-01, frontier<=dossiers)"
                )
            if self.request.constraints.process.constrains_anything and not set(frontier_ids) <= set(
                self._frontier_admissible_route_digests
            ):
                raise ValueError(
                    "process-constrained affordability frontier may contain only FITS or process-EXCLUDED "
                    "(REAL_BUT_HARD) routes"
                )
        # SNAPSHOT-13.2: provider_snapshots carries the dated provenance of any LIVE fetch that serviced the request
        # (empty on an offline/default run).  Typed-guarded like the tuples above; the lazy import stays off the
        # common empty path (the layering discipline).  It is NOT in result_digest -- a fetch time is provenance.
        if type(self.provider_snapshots) is not tuple:
            raise TypeError("provider_snapshots must be a tuple")
        if self.provider_snapshots:
            from .data.provider_snapshot import ProviderSnapshot
            if any(type(s) is not ProviderSnapshot for s in self.provider_snapshots):
                raise TypeError("provider_snapshots must be a tuple of ProviderSnapshot values")
        # DAG-ADMIT-01: ranked_dag_dossiers is the per-DAG process admission (DAG mode).  Typed-guarded like the tuples
        # above, and each dossier's route_digest must identify a returned IR DAG candidate (both are SynthesisDAG.digest)
        # -- so a hand-built/deserialized response cannot smuggle a dossier for a candidate the search never produced.
        if type(self.ranked_dag_dossiers) is not tuple or any(
            type(d) is not RankedDAGSummary for d in self.ranked_dag_dossiers
        ):
            raise TypeError("ranked_dag_dossiers must be a tuple of RankedDAGSummary values")
        if self.ranked_dag_dossiers and self.compilation_ir is not None:
            candidate_ids = {c.candidate_digest for c in self.compilation_ir.candidates}
            dag_ids = tuple(d.route_digest for d in self.ranked_dag_dossiers)
            if len(dag_ids) != len(set(dag_ids)):
                raise ValueError("ranked DAG digests must be unique")
            if not set(dag_ids) <= candidate_ids:
                raise ValueError("ranked DAG digest must identify a returned IR candidate")
        self._check_process_admission_coherence()
        self._check_dag_process_admission_coherence()
        self._check_outcome_coherence()

    def _check_process_admission_coherence(self) -> None:
        """Re-derive each route's PROCESS fit from its carried per-step ``process_requirements`` and refuse a
        ``fit_status`` the evidence cannot support (PROCESS-ADMIT-01 -- the deserialization trust-boundary close).

        ``fit_status`` is the COMBINED section-11 verdict (composability + physical bounds + process), so the process
        component is a LOWER BOUND on it: an honest combined status is always at least as severe as its process
        component (the drafter takes ``EXCLUDED`` > ``UNKNOWN`` > ``FITS`` over all components).  This enforces exactly
        that ONE direction on the PROCESS component, so it never rejects a producer's honest response, but it DOES
        catch a relabel that hides a stricter PROCESS verdict (a process-``UNKNOWN``/``EXCLUDED`` route relabeled to
        ``FITS``, or a hidden process gap/exclusion) because the carried requirements still re-derive to that verdict
        via :func:`evaluate_process_requirements` -- the SAME function the drafter's fit used.  Fires wherever a
        response is built, so an in-memory ``replace`` relabel is caught, not only a deserialized one.  Gated on a
        process-constrained request: with no process bounds every route is process-``UNCONSTRAINED`` and there is
        nothing to re-derive (zero overhead on the default path).

        BOUNDARY -- this checks ONLY the process component of the combined verdict:
        * The OTHER two components (composability, and the physical/reagent/equipment box) are NOT re-derived here.
          They carry only free-text ``exclusions``/``gaps``, so a route that is non-``FITS`` for one of THOSE reasons
          (e.g. a reaction over a bench temperature cap) can still be bare-relabeled to ``FITS`` and admitted --
          re-deriving them needs the per-step physical conditions and the full ExperimentRoute graph the thin
          RankedRouteSummary projection deliberately omits.
        * Even on the process axis, the carried evidence is not cryptographically bound to the route structure, so a
          fully controlling forger who fabricates internally coherent lenient ``process_requirements`` AND recomputes
          ``result_digest`` can still mint a FITS.
        Both gaps close only with a producer signature over the payload (an authentication layer, out of scope here).
        Pinned by tests/test_process_service.py.
        """
        if not self.request.constraints.process.constrains_anything:
            return
        bounds = self.request.constraints.process
        for r in self.ranked_route_dossiers:
            proc = evaluate_process_requirements(r.process_requirements, bounds)
            status = proc.status
            if r.fit_status == "FITS":
                if status not in (ProcessFitStatus.FITS, ProcessFitStatus.UNCONSTRAINED):
                    raise ValueError(
                        f"route {r.route_digest} declares fit_status FITS but its carried process requirements "
                        f"re-derive to {status.value} (a forged or inconsistent process admission)"
                    )
            elif r.fit_status == "UNCONSTRAINED":
                if status is not ProcessFitStatus.UNCONSTRAINED:
                    raise ValueError(
                        f"route {r.route_digest} declares fit_status UNCONSTRAINED but its carried process "
                        f"requirements re-derive to {status.value}"
                    )
            elif r.fit_status == "UNKNOWN":
                if status is ProcessFitStatus.EXCLUDED:
                    raise ValueError(
                        f"route {r.route_digest} declares fit_status UNKNOWN but its carried process requirements "
                        f"re-derive to EXCLUDED (a hidden hard process violation)"
                    )
                hidden = sorted(set(proc.gaps) - set(r.gaps))
                if hidden:
                    raise ValueError(
                        f"route {r.route_digest} (UNKNOWN) hides re-derived process gaps: {hidden}"
                    )
            else:  # EXCLUDED
                hidden = sorted(set(proc.exclusions) - set(r.exclusions))
                if hidden:
                    raise ValueError(
                        f"route {r.route_digest} (EXCLUDED) hides re-derived process exclusions: {hidden}"
                    )

    def _check_dag_process_admission_coherence(self) -> None:
        """Re-derive each DAG's PROCESS COMPONENT from its carried ``process_requirements`` + ``edges`` and refuse a
        combined ``fit_status`` the process evidence cannot support (DAG-BENCH-01 -- the convergent PROCESS-ADMIT-01).

        Mirrors :meth:`_check_process_admission_coherence` exactly (``fit_status`` is now the COMBINED verdict, so its
        PROCESS component is a LOWER BOUND on it), re-deriving via
        :func:`~smartchem.process_constraints.evaluate_dag_process_requirements` (critical-path elapsed, serial active)
        so the load-time verdict is the SOUND convergent one.  Enforces the same ONE direction -- an honest combined
        status is at least as severe as its process component -- so it never rejects an honest response but catches a
        relabel that hides a stricter PROCESS verdict (a process-``UNKNOWN``/``EXCLUDED`` DAG relabeled to ``FITS``, or a
        hidden process gap/exclusion).  The carried ``edges`` are already shape-validated in
        ``RankedDAGSummary.__post_init__`` (:func:`_validate_dag_edges`), so the critical path is well-defined here.
        Gated on a process-constrained request (zero overhead otherwise).

        BOUNDARY -- identical in kind to the linear check: only the PROCESS component is re-derived; the composability
        and physical/reagent/equipment components ride as free-text and are NOT re-derived here (re-deriving them needs
        the full ExperimentStep graph the thin projection omits), so a composability/physical EXCLUDE bare-relabeled to
        FITS still passes this gate.  And the carried evidence is not cryptographically bound to the DAG structure, so a
        fully controlling forger who fabricates internally coherent lenient ``process_requirements`` AND ``edges`` (any
        legal DAG shape) AND recomputes ``result_digest`` can still mint a FITS.  Both close only with the opt-in
        producer signature (COMBINED-VERDICT-AUTH).  Pinned by tests/test_process_service.py.
        """
        if not self.request.constraints.process.constrains_anything:
            return
        bounds = self.request.constraints.process
        for d in self.ranked_dag_dossiers:
            proc = evaluate_dag_process_requirements(d.process_requirements, d.edges, bounds)
            status = proc.status
            if d.fit_status == "FITS":
                if status not in (ProcessFitStatus.FITS, ProcessFitStatus.UNCONSTRAINED):
                    raise ValueError(
                        f"DAG {d.route_digest} declares fit_status FITS but its carried process requirements "
                        f"re-derive to {status.value} (a forged or inconsistent DAG process admission)"
                    )
            elif d.fit_status == "UNCONSTRAINED":
                if status is not ProcessFitStatus.UNCONSTRAINED:
                    raise ValueError(
                        f"DAG {d.route_digest} declares fit_status UNCONSTRAINED but its carried process "
                        f"requirements re-derive to {status.value}"
                    )
            elif d.fit_status == "UNKNOWN":
                if status is ProcessFitStatus.EXCLUDED:
                    raise ValueError(
                        f"DAG {d.route_digest} declares fit_status UNKNOWN but its carried process "
                        f"requirements re-derive to EXCLUDED (a hidden hard process violation)"
                    )
                hidden = sorted(set(proc.gaps) - set(d.gaps))
                if hidden:
                    raise ValueError(f"DAG {d.route_digest} (UNKNOWN) hides re-derived process gaps: {hidden}")
            else:  # EXCLUDED
                hidden = sorted(set(proc.exclusions) - set(d.exclusions))
                if hidden:
                    raise ValueError(f"DAG {d.route_digest} (EXCLUDED) hides re-derived process exclusions: {hidden}")

    def _check_readiness_coherence(self) -> None:
        """Re-derive each ranked route's typed READINESS from its carried thick ``replay_payload`` and refuse a
        payload whose carried ``readiness`` disagrees with the re-derivation (v0.8 Real Route Dossiers, M10 -- the
        deserialization trust-boundary close for the Sec 3/4/8 obligation ladder).

        Called from :func:`response_from_payload` (the DESERIALIZATION trust boundary), like
        :meth:`_check_frontier_coherence` -- NOT from ``__post_init__`` -- because it too reconstructs a route from
        the thick replay payload, a load-time authority rather than an in-memory-construction invariant (an honest
        producer's freshly-built summary is trusted; ``RankedRouteSummary.of_fit`` already computed ``readiness`` via
        the SAME ``evaluate_route`` this re-derives with, so re-checking it on construction would be redundant work).

        UNCONDITIONAL -- unlike :meth:`_check_process_admission_coherence`, this is NOT gated on ``fit_status`` or on
        a process-constrained request, and unlike :meth:`_check_frontier_coherence`'s catalyst/fiction channels it is
        NOT gated on ``require_verified_admission`` either. Readiness is explicitly orthogonal to bench-fit (Sec 2's
        non-negotiable law -- a favorable route never implies a described procedure, and the reverse): an
        EXCLUDED/UNKNOWN route can carry a forged CONDITIONS_SUPPORTED/PROCESS_SPECIFIED claim exactly as easily as a
        FITS one, so gating this on ``fit_status`` would leave every non-FITS route's readiness claim unchecked.

        THE RE-DERIVATION.  ``evaluate_route`` is a PURE function of the reconstructed steps plus the response's own
        ``identity_losses`` (Sec 5.3's conditions-blocker), so an HONEST producer's carried ``readiness`` is always
        BYTE-EQUAL to the re-derivation -- ``StepReadiness``/``RouteReadiness`` structural equality, not just a tier
        comparison, catches a per-step obligation swap (e.g. a stripped source citation that would have demoted
        ``conditions``) even where the coarse projected tier happens not to move on its own; and because ``tier`` is a
        MONOTONIC projection of the per-step obligations (Sec 4), exact per-step equality also implies the coarse
        tier can never be claimed stronger than the re-derivation. ``route.digest == route_digest`` is bound FIRST, so
        the evidence used for the re-derivation cannot be a different (substituted) route's replay wearing this
        entry's identity.

        BOUNDARY -- what this needs, and what it leaves open (stated plainly, no edge-case framing):
        * A summary with NO carried ``replay_payload`` (the DEFAULT thin wire, ``include_replay=False``) has nothing
          to reconstruct a route FROM -- its readiness claim stays UNVERIFIABLE and this check is silent on it, the
          exact same advisory boundary the frontier's catalyst/fiction channels carry on the thin transport. A
          consumer that needs the guarantee asks for a THICK transport (``include_replay=True``); nothing here
          promotes that to a hard requirement the way ``_check_verified_admission`` does for FITS routes (readiness
          coherence is not currently threaded through ``require_verified_admission`` -- a future round could add that
          gate if the residual matters enough to close).
        * Even with a replay present, the evidence is not cryptographically bound to the route structure beyond the
          digest bind above -- a fully controlling forger who fabricates an internally coherent lenient replay (one
          that genuinely re-derives to the stronger tier it claims) AND recomputes ``result_digest`` is the same
          irreducible keyless-consumer residual every other axis in this module already lives with (closed only by
          ``verification_key`` / COMBINED-VERDICT-AUTH).
        Pinned by tests/test_v0_8_readiness_transport.py.
        """
        for r in self.ranked_route_dossiers:
            if r.replay_payload is None:
                continue
            route = _reconstruct_route(r.replay_payload)
            if route.digest != r.route_digest:
                raise ValueError(
                    f"ranked route {r.route_digest} carries replay evidence that reconstructs to a DIFFERENT route "
                    f"({route.digest}) -- substituted readiness evidence; refused (v0.8 M10)"
                )
            rederived = evaluate_route(route, identity_losses=self.identity_losses)
            if r.readiness != rederived:
                raise ValueError(
                    f"ranked route {r.route_digest} claims a readiness (tier {r.readiness.tier}) its replayed "
                    f"evidence does not support (re-derives to tier {rederived.tier}) -- a forged, stale, or "
                    f"evidence-stripped readiness claim; refused (v0.8 M10)"
                )

    def _check_frontier_coherence(self, *, require_verified_admission: bool = False) -> None:
        """Re-derive each affordability_frontier entry's DISPOSITION blockers and refuse an entry whose claimed
        blockers are looser than the re-derivation (TAMPER-HARDENING-01 -- the R59 disposition serialized-tamper close).

        Called from :func:`response_from_payload` (the DESERIALIZATION trust boundary), AFTER
        :func:`_check_verified_admission` -- NOT from ``__post_init__``.  Like ``_check_verified_admission`` it
        reconstructs routes from the thick replay payload, so it belongs at the load seam, not on every in-memory
        construction: an honest producer's freshly-built response is trusted (and re-checking it would be redundant
        work + would fire on the ``replace``-forged responses the red-team tests build).  Ordering it after
        ``_check_verified_admission`` keeps that check's route-BINDING message authoritative for a FITS-route evidence
        substitution; this method then covers the NON-FITS frontier tampers (REAL_BUT_HARD / NOT_A_REACTION strips)
        that ``_check_verified_admission`` -- scoped to FITS dossiers -- does not reach.  It runs unconditionally on
        load (not gated on ``require_verified_admission``), so a bare ``response_from_payload`` still refuses the strip.

        THE HOLE.  ``affordability_frontier`` is DELIBERATELY EXCLUDED from :attr:`result_digest` (a price is dated
        data, not search identity), and until now it was never re-derived on load.  So an out-of-band editor could
        strip a frontier entry's ``hard_blockers`` (or ``fiction_blockers``) and the entry's disposition would flip up
        to a BETTER tier -- REAL_BUT_HARD or NOT_A_REACTION silently becoming CLEAN -- with ``result_digest`` still
        byte-identical and every other coherence gate silent.  The disposition is the ranking answer, so that is a
        forged verdict.  This method shuts it, mirroring :func:`_affordability_frontier`'s OWN blocker computation so a
        HONEST response is always self-consistent (re-derived == claimed) and only a tampered one raises.

        WHAT IS RE-DERIVED, and from what authority:
        * ``hard_blockers`` (REAL_BUT_HARD): under a process box, the process EXCLUSIONS re-derived from the matching
          summary's per-step ``process_requirements`` (digest-covered, the SAME evidence PROCESS-ADMIT-01 authenticates
          -- so this needs no replay), PLUS ``route_catalyst_blockers`` over the route reconstructed from the thick
          ``replay_payload``.
        * ``fiction_blockers`` (NOT_A_REACTION): ``route_reaction_type_blockers`` over that reconstructed route.  The
          recognizers FAIL CLOSED on an absent reaction centre (TAMPER-HARDENING-01, oracle side), so a replay whose
          ``reaction_center`` was nulled DEMOTES rather than census-vouching -- the fiction channel cannot be evaded by
          centre-omission.

        THE POLARITY (fail-closed, one-directional).  We raise iff a re-derived blocker is MISSING from the claimed
        tuple (claimed is a strict subset / looser).  A claim with EXTRA blockers (a worse disposition than reality)
        is a self-suppression, not an admission -- out of scope, exactly as the process/verified-admission checks treat
        hide-good.  So an honest producer response passes (re-derived == claimed) and only a loosened one is refused.

        BOUNDARY -- what this does and does NOT close, stated plainly (NO edge-case framing):
        * FULLY CLOSED, every transport -- the PROCESS-EXCLUSION ``hard_blockers`` channel.  It re-derives from the
          digest-covered per-step ``process_requirements`` and needs NO replay, so a REAL_BUT_HARD process strip is
          caught even on a DEFAULT (thin) serialization.  (The catalyst channel appends nothing today -- no registered
          reaction declares a metal catalyst -- so process exclusions are the whole of the hard channel in practice.)
        * FULLY CLOSED, thick transport -- the CATALYST and FICTION channels, WHEN a digest-bound ``replay_payload`` is
          present.  KILL 1 binds ``route.digest == e.route_digest``, so the evidence cannot be substituted or nulled
          (PIECE 2 demotes a centre-less step); the re-derivation reads the REAL route, so any strip is caught, down to
          a SHA-256 collision on the route digest (cryptographic, out of scope).
        * THE THIN TRANSPORT, UNDER VERIFIED ADMISSION -- now CLOSED, fail-closed (``require_verified_admission=True``).
          ``response_to_payload`` emits the replay only on ``include_replay=True`` (DEFAULT ``False``), so on the thin
          transport the catalyst/fiction channels have no evidence to re-derive from.  Rather than trust the
          unverifiable claim (fail-open, the old boundary), a verified-admission load now REFUSES any frontier entry
          whose summary carries no ``replay_payload`` -- replay-MANDATORY-for-disposition-claims, mirroring
          ``_check_verified_admission``'s own "FITS route with no replay -> UNVERIFIED -> refused".  This is
          false-reject-free by construction: an in-memory summary ALWAYS carries its replay (``of_fit``), and a thick
          serialization round-trips it, so only a genuinely thin (evidence-stripped) transport trips the refusal.
        * THE THIN TRANSPORT, WITHOUT VERIFIED ADMISSION (a bare ``response_from_payload``) -- still ADVISORY, by design.
          A consumer that does not ask for verified admission is not promised re-derivation; the thin frontier's
          catalyst/fiction dispositions remain producer-declared (the process ``hard_blockers`` channel below still
          bites on every transport).  A consumer who needs the guarantee passes ``require_verified_admission=True`` and
          the producer serves ``include_replay=True`` -- the same contract the route/DAG admission axis already uses.
        * OFF a process box, ``hard_blockers`` are the summary's FREE-TEXT physical/composability ``exclusions`` (not
          re-derivable from the thin projection), so a non-process hard blocker stripped off-box is not caught -- the
          same free-text boundary :meth:`_check_process_admission_coherence` carries.
        Pinned by tests/test_poor_man_tamper_hardening.py.
        """
        if not self.affordability_frontier:
            return
        # lazy imports stay off the common (empty-frontier) path -- the service's layering discipline.
        from .experiment.catalyst_availability import route_catalyst_blockers
        from .experiment.reaction_type_oracle import route_reaction_type_blockers
        process = self.request.constraints.process
        process_active = process.constrains_anything
        by_digest = {r.route_digest: r for r in self.ranked_route_dossiers}
        for e in self.affordability_frontier:
            summary = by_digest.get(e.route_digest)
            if summary is None:
                # UNREACHABLE after the __post_init__ FRONTIER<=DOSSIERS guard (every frontier entry has a matching
                # dossier).  Kept as the fail-CLOSED backstop: with no matching summary there is NO authority to
                # re-derive the disposition against, so the entry is UNVERIFIABLE -- refuse it rather than skip (a skip
                # is fail-OPEN, the hole a dossier-deletion tamper drove through before the __post_init__ guard closed
                # it).  Fail closed at every layer -- do not trust a single guard to stay in place.
                raise ValueError(
                    f"affordability frontier entry {e.route_digest} has no matching ranked_route_dossier -- its "
                    f"disposition is UNVERIFIABLE (no authority to re-derive against); refused (TAMPER-HARDENING-01)"
                )
            # THIN-TRANSPORT CLOSURE.  Under verified admission the fiction/catalyst channel MUST be re-derivable, and
            # that re-derivation needs the thick ``replay_payload`` (the route to reconstruct).  A missing payload leaves
            # the entry's fiction/catalyst disposition UNVERIFIED -- so a stripped ``fiction_blockers`` (the DEFAULT-thin
            # forgery the old boundary left open) could pass.  Fail CLOSED, mirroring ``_check_verified_admission``'s
            # own "FITS route with no replay -> UNVERIFIED -> refused" rule: a verified-admission consumer that cannot
            # verify a disposition refuses it, rather than trusting the unverifiable claim.  (The process ``hard_blockers``
            # channel re-derives WITHOUT replay and is still checked on every transport below -- but the process channel
            # alone cannot rule out a hidden fiction blocker, so verified admission requires the replay regardless.)
            if require_verified_admission and summary.replay_payload is None:
                raise ValueError(
                    f"verified admission: affordability frontier entry {e.route_digest} carries no replay_payload -- its "
                    f"fiction/catalyst disposition is UNVERIFIED (the DEFAULT thin transport omits the replay, so a "
                    f"stripped fiction/catalyst blocker cannot be re-derived and refuted; the producer must serialize "
                    f"with include_replay=True); refused (TAMPER-HARDENING-01, thin-transport closure)"
                )
            rederived_hard: set[str] = set()
            rederived_fiction: set[str] = set()
            # process-exclusion hardness: authenticated from the digest-covered per-step requirements (no replay
            # needed), exactly as ``_affordability_frontier`` sources channel-1 hardness under a process box.
            if process_active:
                proc = evaluate_process_requirements(summary.process_requirements, process)
                if proc.status is ProcessFitStatus.EXCLUDED:
                    rederived_hard |= set(proc.exclusions)
            # catalyst + fiction: re-derived from the route reconstructed out of the thick replay payload.  A missing
            # payload leaves these two channels unverifiable (see the BOUNDARY) -- the process channel above still bites.
            if summary.replay_payload is not None:
                route = _reconstruct_route(summary.replay_payload)
                # KILL 1 -- digest-BIND the reconstructed evidence to the entry identity (key-free), mirroring
                # ``_check_verified_admission``'s FITS bind.  Without it, an attacker substitutes ANY recognized route's
                # replay under this entry's route_digest: the fiction/catalyst re-derives to zero, so a stripped
                # disposition passes.  ``route.digest`` is the ExperimentRoute identity; the entry and its matched
                # summary share ``route_digest``, and every HONEST reconstructed replay binds (verified: 0 false-reject).
                if route.digest != e.route_digest:
                    raise ValueError(
                        f"affordability frontier entry {e.route_digest} carries replay evidence that reconstructs to a "
                        f"DIFFERENT route ({route.digest}) -- substituted disposition evidence; refused "
                        f"(TAMPER-HARDENING-01, KILL 1)"
                    )
                rederived_hard |= set(route_catalyst_blockers(route))
                rederived_fiction |= set(route_reaction_type_blockers(route))
            missing_hard = rederived_hard - set(e.cost_vector.hard_blockers)
            missing_fiction = rederived_fiction - set(e.cost_vector.fiction_blockers)
            if missing_hard or missing_fiction:
                raise ValueError(
                    f"affordability frontier entry {e.route_digest} claims blockers looser than the re-derivation -- "
                    f"a forged disposition (missing hard_blockers {sorted(missing_hard)}; missing fiction_blockers "
                    f"{sorted(missing_fiction)}); refused (TAMPER-HARDENING-01)"
                )

    def _check_outcome_coherence(self) -> None:
        """The no-laundering guard: an outcome can never contradict the search status it reports.

        This is the section-8 heart of the response -- a partial search must never surface as a completion, and a
        no-route claim must rest on a genuinely complete, empty search.  It reads only STRUCTURED facts
        (``complete_within_bounds``, ``candidate_count``, ``standard_status``), never diagnostic text.
        """
        o = self.outcome
        ir = self.compilation_ir
        searched = {
            ResponseOutcome.ROUTES_FOUND,
            ResponseOutcome.TARGET_ALREADY_AVAILABLE,
            ResponseOutcome.NO_ROUTE_COMPLETE,
            ResponseOutcome.INCOMPLETE,
        }
        if o in searched:
            if ir is None:
                raise ValueError(f"{o.value} requires a compilation_ir")
            # The wrapped IR is the source of truth for the search status: the response may not report a section 8.2
            # status that contradicts it (a hand-built or deserialized response could otherwise smuggle an
            # engine-impossible stop reason -- e.g. INCOMPLETE_CANDIDATE_LIMIT -- past the family checks below).
            if self.standard_status != ir.standard_status:
                raise ValueError(
                    f"response standard_status {self.standard_status!r} must equal the wrapped IR's "
                    f"standard_status {ir.standard_status!r}"
                )
            if o is ResponseOutcome.INCOMPLETE:
                if ir.complete_within_bounds:
                    raise ValueError("INCOMPLETE must not carry a complete-within-bounds IR")
                if self.standard_status not in _INCOMPLETE_8_2:
                    raise ValueError("INCOMPLETE must report an INCOMPLETE_* section 8.2 status")
            else:
                if not ir.complete_within_bounds:
                    raise ValueError(f"{o.value} requires a complete-within-bounds IR")
                if self.standard_status != _COMPLETE_8_2:
                    raise ValueError(f"{o.value} must report {_COMPLETE_8_2}")
                if o is ResponseOutcome.ROUTES_FOUND and ir.candidate_count == 0:
                    raise ValueError("ROUTES_FOUND requires at least one candidate")
                if o is ResponseOutcome.NO_ROUTE_COMPLETE and ir.candidate_count != 0:
                    raise ValueError("NO_ROUTE_COMPLETE requires zero candidates")
        else:
            if ir is not None:
                raise ValueError(f"{o.value} must not carry a compilation_ir")
            # No IR means no search ran, so there are no routes to rank: an unsearched outcome
            # (REFUSED/INVALID_INPUT/INTERNAL_ERROR) MUST carry no ranked_route_dossiers, or a hand-built/deserialized
            # response could smuggle a dossier past the guard and into result_digest (red-team fold).
            if self.ranked_route_dossiers:
                raise ValueError(f"{o.value} ran no search, so it must carry no ranked_route_dossiers")
            # DAG-ADMIT-01 (evil-morty fold): the SAME fence on the convergent dossiers -- with ir None the __post_init__
            # membership check (gated on ir is not None) is skipped, so without THIS an unsearched outcome could smuggle
            # a fabricated ranked_dag_dossier (a ghost route_digest identifying no candidate) into result_digest.
            if self.ranked_dag_dossiers:
                raise ValueError(f"{o.value} ran no search, so it must carry no ranked_dag_dossiers")
            if not self.diagnostics:
                raise ValueError(f"{o.value} must state a diagnostic reason")
            if o is ResponseOutcome.INVALID_INPUT and self.standard_status != "REFUSED_INVALID_REQUEST":
                raise ValueError("INVALID_INPUT must report REFUSED_INVALID_REQUEST")
            if o is ResponseOutcome.REFUSED and self.standard_status is not None and (
                self.standard_status not in REFUSED_8_2_STATUSES
            ):
                # A model/scission-boundary refusal has no dedicated section 8.2 name yet (the 8.2 refusal vocab is
                # REFUSED_INVALID_REQUEST/REFUSED_IDENTITY_UNSUPPORTED); None is the honest value until the recompile
                # front door classifies boundary refusals like decompile_or_refuse does (a named follow-on).
                raise ValueError("REFUSED must report a REFUSED_* section 8.2 status or None")
            if o is ResponseOutcome.INTERNAL_ERROR and self.standard_status not in (None, "ERROR_INTERNAL"):
                raise ValueError("INTERNAL_ERROR must report ERROR_INTERNAL or None")

    @property
    def exit_code(self) -> int:
        # Search outcome remains structural; process admission is a separate decision.
        # A partial search stays partial even when no returned route fits.
        if self.outcome is ResponseOutcome.ROUTES_FOUND:
            if self.request.constraints.process.constrains_anything:
                # SUCCESS requires a candidate that passed the COMBINED section-11 bench admission -- linear combined-FITS
                # (admissible_route_digests) OR, since DAG-BENCH-01, a convergent-DAG combined-FITS (admissible_dag_digests:
                # composability + physical + process, with the process axis serial-achievable, so a real single-operator
                # bench pass).  Before DAG-BENCH-01 a DAG assessed only its process axis and could NOT flip the exit; now
                # its bench fit is combined, so a combined-FITS DAG is a first-class bench-usable route.  With no combined
                # admission on either axis the process-constrained compile stays REFUSED (the search is complete but nothing
                # is bench-usable), never over-claiming success on a partial admission.
                if not self.admissible_route_digests and not self.admissible_dag_digests:
                    return EXIT_REFUSED
            else:
                # No process box (physical-only or unconstrained): REFUSED only if EVERYTHING ranked on either axis is a
                # hard EXCLUDE -- a lone FITS/UNKNOWN keeps the success outcome (the linear physical-only rule, extended to
                # the DAG axis so a DAG-mode physical-only compile is judged by the same standard).
                ranked = self.ranked_route_dossiers or self.ranked_dag_dossiers
                if ranked and all(r.fit_status == "EXCLUDED" for r in self.ranked_route_dossiers) and all(
                    d.fit_status == "EXCLUDED" for d in self.ranked_dag_dossiers
                ):
                    return EXIT_REFUSED
        return _EXIT_BY_OUTCOME[self.outcome]

    @property
    def admissible_dag_digests(self) -> tuple[str, ...]:
        """Returned convergent-DAG candidates that pass the COMBINED section-11 bench fit (DAG-BENCH-01).

        The convergent analogue of :attr:`admissible_route_digests`: each dossier's ``fit_status`` is the combined
        verdict (composability + physical + process), and only its PROCESS component is re-derived on load (the same
        boundary the linear list carries -- see :meth:`_check_dag_process_admission_coherence`).  A DAG combined-FITS is
        SOUND to treat as a bench pass because ``dag_process_fit``'s FITS is serial-achievable by a single operator --
        with the ONE unmodeled caveat that serial execution holds an early branch's intermediate through its siblings
        and E1 is time-blind, so that serial-hold stability is UNVERIFIED (see :class:`RankedDAGSummary`).
        Gated on a process-constrained request exactly like :attr:`admissible_route_digests` (a physical-only compile is
        judged by :attr:`exit_code`'s all-EXCLUDED rule instead), so the two lists stay symmetrical.
        """
        if not self.request.constraints.process.constrains_anything:
            return ()
        return tuple(d.route_digest for d in self.ranked_dag_dossiers if d.fit_status == "FITS")

    @property
    def admissible_route_digests(self) -> tuple[str, ...]:
        """Returned candidates satisfying every assessed limit; never a bench-readiness claim.

        Derived from each route's ``fit_status``.  That ``fit_status`` is the COMBINED section-11 verdict
        (composability + physical bounds + process), and only its PROCESS component is re-derived on load:
        every ranked route carries its per-step ``process_requirements``, and
        :meth:`_check_process_admission_coherence` (run at construction AND on load) RE-DERIVES the process fit
        from that evidence and refuses a ``FITS``/``UNKNOWN`` whose PROCESS evidence cannot support it
        (PROCESS-ADMIT-01).  So a bare relabel of a route that is non-``FITS`` on the PROCESS axis can no longer
        inflate this list.  It does NOT authenticate the other two axes: a route EXCLUDED for a physical/reagent/
        equipment bound or a composability defect can still be bare-relabeled to ``FITS`` (those axes carry only
        free-text ``exclusions``/``gaps``, and re-deriving them needs the per-step physical conditions and the full
        ExperimentRoute graph the thin projection deliberately omits).  So a deserialized ``admissible_route_digests``
        is authenticated on the process axis only; the complete close (all axes + a controlling forger) needs a
        producer signature -- see :func:`response_from_payload`.
        """
        if not self.request.constraints.process.constrains_anything:
            return ()
        return tuple(r.route_digest for r in self.ranked_route_dossiers if r.fit_status == "FITS")

    @property
    def _frontier_admissible_route_digests(self) -> tuple[str, ...]:
        """Route digests admissible to the process-constrained affordability frontier (DISPOSITION-ACTIVATE-01): the
        FITS routes (:attr:`admissible_route_digests`) PLUS the routes whose RE-DERIVED process status is EXCLUDED
        (genuine reactions the bench cannot run -> ranked REAL_BUT_HARD).  Both halves are re-derived on load from the
        carried per-step ``process_requirements`` via :func:`evaluate_process_requirements` -- the SAME authority
        PROCESS-ADMIT-01 uses (:meth:`_check_process_admission_coherence` already refuses a ``fit_status`` inconsistent
        with that re-derivation) -- so this bound is authenticated on the process axis: a forger cannot admit a route to
        the frontier without carried process evidence that itself re-derives to FITS or EXCLUDED.  This is the widened
        successor to the old FITS-only frontier gate, which structurally hid every real-but-unrunnable route.  Unlike
        :attr:`admissible_route_digests` (a bench-readiness list -- FITS only, an EXCLUDED route is NOT admitted for
        the bench), this is purely the frontier-membership bound; a REAL_BUT_HARD route is shown, ranked below the
        runnable ones, never claimed to fit."""
        if not self.request.constraints.process.constrains_anything:
            return ()
        bounds = self.request.constraints.process
        out: "list[str]" = []
        for r in self.ranked_route_dossiers:
            if r.fit_status == "FITS":
                out.append(r.route_digest)
            elif evaluate_process_requirements(r.process_requirements, bounds).status is ProcessFitStatus.EXCLUDED:
                out.append(r.route_digest)
        return tuple(out)

    @property
    def process_selection_status(self) -> str:
        if not self.request.constraints.process.constrains_anything:
            return "NOT_REQUESTED"
        if self.outcome is ResponseOutcome.TARGET_ALREADY_AVAILABLE:
            return "NOT_REQUIRED"
        if self.compilation_ir is None:
            return "UNASSESSED"
        if self.admissible_route_digests:
            return "FITS_FOUND"
        # DAG-BENCH-01: convergent DAGs are now FORMALLY admitted on the COMBINED section-11 bench fit (composability +
        # physical + process), the same combined selection the linear ``admissible_route_digests`` path above encodes.
        # A DAG whose combined fit is FITS makes the selection FITS_FOUND; an assessed DAG set with none combined-FITS is
        # NO_FIT_FOUND.  This is what flips DAG mode off UNASSESSED; the per-DAG dossiers carry the exact verdicts and
        # their boundary (a FITS is serial-achievable, so a real single-operator bench pass).
        if self.ranked_dag_dossiers:
            return "FITS_FOUND" if self.admissible_dag_digests else "NO_FIT_FOUND"
        if self.compilation_ir.candidate_count and not self.ranked_route_dossiers:
            return "UNASSESSED"
        return "NO_FIT_FOUND"

    @property
    def normalized_target(self):
        return None if self.compilation_ir is None else self.compilation_ir.target

    @property
    def identity_losses(self) -> tuple[IdentityLoss, ...]:
        """The wrapped IR's first-class typed section-5.3 loss records (IR-LOSS-01)."""
        return () if self.compilation_ir is None else self.compilation_ir.identity_losses

    @property
    def identity_loss_summaries(self) -> tuple[str, ...]:
        """The one-line human/JSON-agreement string of each loss (CLI-JSON-01) -- derived from the typed records."""
        return () if self.compilation_ir is None else self.compilation_ir.identity_loss_summaries

    @property
    def candidates(self) -> tuple:
        return () if self.compilation_ir is None else self.compilation_ir.candidates

    @property
    def search_receipt_digest(self) -> "str | None":
        # a convenience digest of the full section 8.1 receipt view the IR now carries (IR-CHEM-01); the content
        # itself is compilation_ir.search_receipt, recoverable from the machine payload.
        return None if self.compilation_ir is None else self.compilation_ir.search_receipt.digest

    @property
    def search_space_status(self) -> "str | None":
        """The section-8.3 no-route matrix label for this response, or ``None`` when no route search ran (SRCH-NO-01).

        DERIVED (never stored) from the wrapped IR's ``(complete_within_bounds, candidate_count)`` so it can never
        drift from the search it reports -- one of NO_ROUTE_IN_DECLARED_SPACE / INCOMPLETE_NO_ROUTE_OBSERVED /
        COMPLETE_CANDIDATE_SET / PARTIAL_CANDIDATE_SET.  ``None`` for a refusal/invalid/internal response or a
        TARGET_ALREADY_AVAILABLE match, where there was no bounded route search to label (the four labels are about
        the route search, not "the target was already on the shelf").  It is a deterministic function of the outcome
        and the IR, both already folded into :attr:`result_digest`, so it adds no new identity term.
        """
        searched = {ResponseOutcome.ROUTES_FOUND, ResponseOutcome.NO_ROUTE_COMPLETE, ResponseOutcome.INCOMPLETE}
        if self.outcome not in searched or self.compilation_ir is None:
            return None
        return section_8_3_label(self.compilation_ir.complete_within_bounds, self.compilation_ir.candidate_count)

    @property
    def result_digest(self) -> str:
        """The result identity: a deterministic function of the request's SEARCH identity and the produced IR.

        Because :func:`run_compilation` reads ONLY the request's resolved semantic fields (never its origins or
        output policy), equal :attr:`CompilationRequest.semantic_digest` => equal execution => equal
        ``result_digest``.  That is the "equal result digests across aliases" half of the SVC-REQ-01 acceptance.

        PROVENANCE IS EXCLUDED (SVC-REQ-01 alias-collapse): it hashes ``diagnostics`` (genuine search facts) but
        NOT :attr:`parse_receipt_summary`, which lives in its own field.  This is load-bearing now that the target
        collapses: ``paracetamol`` and ``smiles:CC(=O)Nc1ccc(O)cc1`` share a ``semantic_digest``, so they MUST
        share a ``result_digest`` -- but they were READ differently (their receipts differ), so the receipt cannot
        enter the result identity or the one-way law would break the moment the aliases collapsed.
        """
        return canonical_digest(
            (
                # v1alpha2 (CLI-CAN-02 brick 2): the ranked dossiers' digests are folded in so the result identity is
                # a TRUE content hash of the whole payload.  They are a deterministic function of inputs already
                # covered (the routes come from the IR-packaged search; the section-11 box rides semantic_digest), so
                # this never splits two aliases that share a semantic_digest -- it only makes a tamper detectable.
                "compilation-result-v1alpha2",
                self.request.semantic_digest,
                self.outcome,
                self.standard_status or "",
                "" if self.compilation_ir is None else self.compilation_ir.digest,
                self.diagnostics,
                tuple(r.digest for r in self.ranked_route_dossiers),
                # DAG-ADMIT-01: the DAG process admissions fold in the SAME way (a deterministic function of the IR's
                # DAG candidates + the request's process bounds -- never splits an alias, only makes a tamper
                # detectable), but ONLY when present, so a linear/decompile/DAG-less response stays byte-identical to
                # the v1alpha2 formula (zero ripple); a process-constrained DAG-mode response's digest changes here.
                *((tuple(d.digest for d in self.ranked_dag_dossiers),) if self.ranked_dag_dossiers else ()),
            )
        )


# -- the service producer ----------------------------------------------------------------------------------------


def _invalid(request: CompilationRequest, reason: str) -> CompilationResponse:
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA,
        request,
        ResponseOutcome.INVALID_INPUT,
        "REFUSED_INVALID_REQUEST",
        None,
        (reason,),
    )


def _refused(
    request: CompilationRequest, reason: str, *, standard_status: "str | None" = None
) -> CompilationResponse:
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA, request, ResponseOutcome.REFUSED, standard_status, None, (reason,)
    )


def _check_identity_layer(request: CompilationRequest) -> "CompilationResponse | None":
    """Enforce ID-LAYER-02: refuse a request whose declared match layer the engine cannot HONESTLY honor.

    Returns a REFUSED response (``REFUSED_IDENTITY_UNSUPPORTED``, exit 5) when the declared
    :attr:`IdentityPolicy.match_layer` is not the single layer this operation's engine matches at, else ``None``
    (the request proceeds).  THREE distinct failures, each with its own HONEST reason (never conflated), and the
    reason turns on the OPERATION, not on whether perception exists -- because after ID-STEREO-02 it does:

    * a finer layer on a DECOMPILE (CONSTITUTION/CONFIGURATION/ISOTOPIC on a formula descent): a formula descent
      constructs NO structure at all, so there is nothing to match at any finer layer -- refused (section 5.4);
    * a finer layer on a RECOMPILE (CONFIGURATION/ISOTOPIC): the identity MODEL now PERCEIVES these layers
      (ID-STEREO-02 -- enantiomers get distinct :class:`~smartchem.identity.LayeredIdentity`), but the SEARCH still
      matches terminals on the achiral ``Molecule`` (CONSTITUTION), so a finer match in the SEARCH is not yet honored
      -- refused, and honestly named as "perceivable but not wired into terminal matching" (a named next-step, §5.3),
      NEVER the false "stereo perception is unbuilt";
    * a layer COARSER than honored (recompile declaring FORMULA): section 5.4 forbids a structure search
      terminating on formula-only equality -- refused, never allowed to collapse isomers.
    """
    honored = _HONORED_MATCH_LAYER[request.operation]
    declared = request.identity_policy.match_layer
    op = request.operation.value
    if declared is honored:
        return None
    if refines(declared, honored):                           # declared is FINER than the engine's honored layer
        if request.operation is CompilationOperation.DECOMPILE:
            # a formula descent constructs NO structure at all -- nothing to match at constitution or any finer layer.
            reason = (
                f"a {op} search matches identity at the {honored.value} layer and constructs no {declared.value}-layer "
                f"representation (a formula descent yields only the elemental formula, not a structure), so a "
                f"{declared.value}-layer match is not available on this path -- refused rather than silently matched at "
                f"{honored.value} (section 5.4)"
            )
        else:
            # RECOMPILE: perception of the finer layer IS built (ID-STEREO-02), but the search matches terminals at
            # constitution (the achiral Molecule model), so a finer match in the SEARCH is not yet honored -- the
            # honest wall is "perceivable but not wired into terminal matching" (a named next-step), never "unbuilt".
            reason = (
                f"a {op} search matches terminals at the {honored.value} layer; the identity model can perceive the "
                f"finer {declared.value} layer (ID-STEREO-02: enantiomers/isotopologues get distinct identities) but "
                f"the search does not yet match terminals there (the achiral structure model is the search identity), "
                f"so a {declared.value}-layer search match is not honored here -- refused rather than silently matched "
                f"at {honored.value} (section 5.3; wiring perception into the search is a named next-step)"
            )
    else:
        reason = (
            f"a {op} search matches identity at the {honored.value} layer; it must not terminate on the coarser "
            f"{declared.value} layer, because formula-only equality does not fix a structure (section 5.4 / gate G3) "
            f"-- refused"
        )
    return _refused(request, reason, standard_status="REFUSED_IDENTITY_UNSUPPORTED")


def _classify(ir: ChemicalCompilationIR, target_available: bool) -> ResponseOutcome:
    if target_available:
        return ResponseOutcome.TARGET_ALREADY_AVAILABLE
    if not ir.complete_within_bounds:
        return ResponseOutcome.INCOMPLETE
    return ResponseOutcome.ROUTES_FOUND if ir.candidate_count > 0 else ResponseOutcome.NO_ROUTE_COMPLETE


def _fit_counts(fits: "tuple") -> "tuple[int, int, int]":
    """(fits, excluded, unknown) over a tuple of RankedRouteSummary (or drafter RouteFit) dispositions.

    Reads the string ``fit_status`` / enum ``status.value`` structurally.  ``UNCONSTRAINED`` is neither a fit nor a
    miss (there was nothing to fit), so it is counted nowhere -- an unconstrained bench yields (0, 0, 0)."""
    fit = exc = unk = 0
    for f in fits:
        status = getattr(f, "fit_status", None) or f.status.value
        if status == "FITS":
            fit += 1
        elif status == "EXCLUDED":
            exc += 1
        elif status == "UNKNOWN":
            unk += 1
    return fit, exc, unk


def constraint_note(bounds: PhysicalBounds, *, fit_counts: "tuple[int, int, int] | None",
                    process: "ProcessBounds | None" = None) -> "str | None":
    """The ONE section-11 constraint disclosure (CLI-CAN-02), or ``None`` when nothing is declared.

    ONE caveat text for every surface -- the ``run_compilation`` response diagnostic (recompile human AND --json)
    and the ``compile`` human dossier both call it -- so the disclosure can never drift between them.  It reports the
    TRUTH of what happened, per path:

    * ``fit_counts is None`` -- the constraint is DECLARED and part of the request identity, but no routes were
      ranked against it here (a no-route/refusal result, or a path that does not rank -- e.g. DAG mode).  Never
      implies the routes honor a bench limit they were not checked against.
    * ``fit_counts = (fits, excluded, unknown)`` -- the constraint was APPLIED: the routes are ranked against the
      bench box, ``excluded`` fall outside a hard bound, and ``unknown`` leave a constrained dimension undeclared
      (a GAP -- never a silent pass, section 11).
    """
    process = process if process is not None else ProcessBounds.unconstrained()
    if not bounds.constrains_anything and not process.constrains_anything:
        return None
    description = bounds.describe()
    if process.constrains_anything:
        description += "; process: " + process.describe()
    selection = (
        "; process selection admits only FITS routes; UNKNOWN and EXCLUDED remain diagnostics. "
        "Fit compares declared requirements including workup; it does not validate a bench procedure"
        if process.constrains_anything else ""
    )
    if fit_counts is None:
        return (
            f"section-11 constraint DECLARED ({description}): part of the request identity, but no routes "
            "were ranked against it here (a no-route result, or a path that does not rank the routes)" + selection
        )
    fits, excluded, unknown = fit_counts
    return (
        f"section-11 constraint APPLIED ({description}): the routes are ranked against the bench -- "
        f"{fits} FIT, {excluded} EXCLUDED (outside a hard bound), {unknown} UNKNOWN-fit (a constrained dimension "
        "the route leaves undeclared -- never a silent pass); see ranked_route_dossiers" + selection
    )


def _dag_bench_note(dags: "tuple", box: "object") -> "str | None":
    """The human-readable summary of the DAG-mode COMBINED bench admission (DAG-BENCH-01, superseding _dag_process_note).

    Convergent DAGs are now FORMALLY admitted on the COMBINED section-11 bench fit: each carries a
    :class:`RankedDAGSummary` (in ``ranked_dag_dossiers``) whose ``fit_status`` is the combined verdict from
    :func:`~smartchem.experiment.drafter.dag_bench_fit` -- E1 composability across the edges, the per-step physical box,
    and the critical-path process axis, folded exactly as a linear route's.  ``process_selection_status`` reflects it
    (FITS_FOUND / NO_FIT_FOUND) and a combined-FITS DAG is a first-class bench pass (it can flip a complete search's
    ``exit_code`` to success), because a process FITS is serial-achievable.  This line is the one-string tally for both
    views, and it names the residual boundaries so a FITS is never over-read.
    """
    from .experiment.dag import _serial_hold_minutes
    from .experiment.drafter import RouteFitStatus, dag_bench_fit
    if not dags or not box.constrains_anything:
        return None
    verdicts = [dag_bench_fit(d, box).status for d in dags]
    fits = sum(1 for s in verdicts if s is RouteFitStatus.FITS)
    excluded = sum(1 for s in verdicts if s is RouteFitStatus.EXCLUDED)
    unknown = sum(1 for s in verdicts if s is RouteFitStatus.UNKNOWN)
    # The FIT parenthetical is PROCESS-axis language ("serial-achievable"), so it is only honest when the process box
    # actually constrains the time/attention axis; a physical-only compile assessed no time axis (evil-morty cosmetic fold).
    fit_note = "serial-achievable" if box.process.constrains_anything else "within the physical bench"
    # DAG-HOLD-01 (evil-morty fold: the disclosure must reach a real product surface, not just a dead explain()): surface
    # the CONCRETE serial-schedule hold here, in the one human tally DAG mode actually emits -- not merely the generic
    # boundary sentence.  Observation-only (it never changed a verdict) and schedule-relative.  A no-hold DAG set (e.g. a
    # single-step or timing-free route) yields the byte-identical generic clause below, so it ripples nothing.
    hold_vals = [v for d in dags for v in _serial_hold_minutes(d).values() if v > 0]
    if hold_vals:
        hold_clause = (
            f"serial-hold stability is UNVERIFIED and now DISCLOSED (DAG-HOLD-01): {len(hold_vals)} intermediate "
            f"handoff(s) across the assessed routes wait up to {max(hold_vals):g} min through sibling branches under "
            "the serial schedule computed here (schedule-relative -- a different valid order shifts WHICH intermediate "
            "waits; E1 is time-blind, so survival over the hold is unmodeled until a max-hold stability axis exists)"
        )
    else:
        hold_clause = ("serial-hold stability is UNVERIFIED (a strengthening a linear FITS does not carry, unmodeled "
                       "until a max-hold stability axis exists)")
    return (
        f"section-11 bench (DAG mode): {len(dags)} convergent route(s) SOUNDLY assessed and FORMALLY admitted on the "
        f"COMBINED fit (composability + physical + process) -- {fits} FIT ({fit_note}), {excluded} EXCLUDED (a hard "
        f"composability/physical/process bound), {unknown} UNKNOWN-fit (an undeclared constrained dimension or a fit "
        "that needs branch overlap; never a silent pass); see ranked_dag_dossiers. BOUNDARY: only the PROCESS component "
        "is re-derived on load (composability/physical ride as free-text, as for a linear route); a FITS assumes each "
        "step's attention is legal in isolation, NOT joint single-operator schedulability of concurrent branches (that "
        "band is the UNKNOWN, never a FITS); and 'serial-achievable' is certified on the MODELED axes (time/attention/"
        f"equipment) only -- serial execution of a convergent DAG HOLDS an early branch's intermediate through its "
        f"sibling branches, and E1 composability is time-blind (adjacent-handoff only), so that {hold_clause}"
    )


def _ranked_summaries(
    routes: "tuple", bounds: PhysicalBounds, losses: "tuple",
    process: "ProcessBounds | None" = None,
) -> "tuple[RankedRouteSummary, ...]":
    """Rank ``routes`` against the section-11 bench ``bounds`` and project to thin response summaries (CLI-CAN-02).

    The drafter (the heavy analysis layer: composability/thermo/selectivity/kinetics) is imported LAZILY here so
    ``smartchem.service`` never drags that object graph at module load (the layering discipline).  ``losses``
    threads the target's section-5.3 blockers into the sourced verdicts (EVD-KEY-01), so a loss-bearing target
    never floats on a sourced verdict its dropped feature forbids.  An empty route set yields ``()`` -- there is
    nothing to rank, which the caller discloses via ``constraint_note(..., fit_counts=None)``.
    """
    if not routes:
        return ()
    from .experiment.drafter import ConstraintBox, rank_routes
    fits = rank_routes(routes, box=ConstraintBox.of_bounds(bounds, process=process), losses=losses)
    return tuple(RankedRouteSummary.of_fit(f, identity_losses=losses) for f in fits)


def _route_shopping_requirements(route: "object") -> "tuple[tuple[object, float], ...] | None":
    """The route's per-external-leaf ``(molecule, moles)`` shopping requirement per 1 mol of final product.

    A conserved 100%-efficiency LOWER BOUND from ``dag_shopping_requirement`` (by-products credited).  ``None`` (an
    honest UNKNOWN, never a fabricated allocation) for the EXPECTED structural-refusal domains: shopping is
    UNDERDETERMINED (a coupled multi-net-producer fan-out -> ``ShoppingUnderdeterminedError``), the steps do not form a
    valid DAG (``DAGError`` -- duplicate target / cycle / no single sink), or a DEGENERATE step has no net species
    (``CeilingError`` -- e.g. an identity/spectator-only rewrite, so there is no material requirement to compute).
    Only those expected fault domains are caught -- an unexpected fault propagates (an internal bug is never laundered
    into a scientific "unknown"; the ERR-EVIDENCE-01 discipline).  It is the shared worker behind both the
    ``material_quantity`` axis (total moles) and the TERM-MAT quantity-weighted cash floor (per-leaf moles x price)."""
    steps = getattr(route, "steps", None)
    if not steps:
        return None
    from fractions import Fraction

    from .experiment.ceiling import CeilingError
    from .experiment.dag import DAGError, SynthesisDAG, dag_shopping_requirement
    try:
        req = dag_shopping_requirement(SynthesisDAG.of(*steps), Fraction(1))
    except (DAGError, CeilingError):
        # DAGError covers ShoppingUnderdeterminedError (the coupled refusal) AND the DAG-construction guards; CeilingError
        # (a SIBLING of DAGError, NOT a subclass -- red-team fold) covers a degenerate no-net-species step.  All are
        # honest UNKNOWN cases; without catching CeilingError a degenerate-but-valid-DAG route crashes the whole response.
        return None
    return tuple((m, float(amount)) for m, amount in req.requirements)


def _route_material_quantity(route: "object") -> "float | None":
    """The route's TOTAL external-leaf MOLES per 1 mol of final product (COST-VEC-01 quantity/stoich axis).

    The sum of :func:`_route_shopping_requirements` -- a conserved 100%-efficiency LOWER BOUND, a stoichiometric
    material-burden weight the per-unit cash axis is blind to.  ``None`` (honest UNKNOWN) in exactly the shopping's
    refusal domains (see the worker).  It is deliberately a MOL count, NOT a cash: the quantity-weighted CASH version
    (per-leaf moles x price_per_mol, via the TERM-MAT molar-mass + price-unit layer) rides the cash axis instead, wired
    below through ``basket_cost_vector``'s ``weighted_cash_leaves``."""
    reqs = _route_shopping_requirements(route)
    if reqs is None:
        return None
    return float(sum(amount for _m, amount in reqs))


def _affordability_frontier(routes: "tuple", ranked: "tuple", *, process_bounds: "ProcessBounds | None" = None) -> "tuple":
    """The section-10.4 Pareto affordability frontier over the ranked routes (COST-VEC-01 live wiring).

    For each ranked route, price its commodity leaf inputs into a CostVector (``basket_cost_vector``) -- plus its
    stoichiometric ``material_quantity`` (total external-leaf moles per mol product, a conserved lower bound via
    ``_route_material_quantity``; None when the route's shopping is underdetermined) -- and wrap it in an
    ``AffordabilityFrontierEntry`` keyed by the SAME ``route_digest`` the ranked summary carries, so a consumer links a
    frontier entry back to its ranked route.  A route whose RE-DERIVED process status is EXCLUDED (a genuine reaction
    the bench cannot run) carries those exclusions as ``hard_blockers`` (disposition REAL_BUT_HARD), so it is
    G6-dominated (a hard blocker dominates cost) by any in-bound (CLEAN) route yet ranked ABOVE a NOT_A_REACTION
    fiction -- and, crucially, it now REACHES the frontier at all (DISPOSITION-ACTIVATE-01 lifted the old FITS-only
    admission gate, which structurally hid every real-but-unrunnable route so R59's REAL_BUT_HARD tier could never be
    populated).  ``process_bounds`` (passed by ``run_compilation`` only on a process-constrained routes-mode search)
    is the authenticated source: the process exclusion is re-derived here via ``evaluate_process_requirements`` over
    the route's carried per-step requirements -- the SAME verdict PROCESS-ADMIT-01 re-checks on load -- so the hardness
    is trust-boundary-safe, unlike the physical/composability exclusion axes (which stay diagnostics-only, not
    re-derivable from the thin projection, hence not admitted).

    The SIGNAL GATE (honest emptiness): run dominance FIRST, then return the Pareto set only if at least one
    SURVIVING entry carries affordability SIGNAL -- a known cost axis OR a hard blocker.  Gating the survivors (not
    all entries) is load-bearing: G6 can dominate the only signal-bearing entry off the frontier (a hard-blocked
    route beaten by a clean one), and returning the blank survivors would be exactly the "list of every route wearing
    a blank vector" that falsely implies a cost ranking happened.  When signal survives, the full Pareto set is
    returned, and UNKNOWN-cost routes stay on it (incomparable, never over- or under-ranked; section 10.4).  This is
    populated only in routes mode (DAG-mode/decompile rank nothing, so ``ranked`` is empty there) -- the same scope as
    ``ranked_route_dossiers``, introducing no new asymmetry.
    """
    if not routes or not ranked:
        return ()
    from .experiment.affordability import AffordabilityFrontierEntry, basket_cost_vector, pareto_frontier
    from .experiment.catalyst_availability import route_catalyst_blockers
    from .experiment.reaction_type_oracle import route_reaction_type_blockers
    by_digest = {r.digest: r for r in routes}
    entries = []
    for summary in ranked:
        route = by_digest.get(summary.route_digest)
        if route is None:
            continue  # a ranked summary with no matching route object (should not happen) contributes nothing
        # The two DISPOSITION channels are kept DISJOINT (DISPOSITION-01): a REAL-BUT-HARD constraint (a genuine
        # reaction that is merely costly / out of reach) and a NOT-A-REACTION fiction (Problem A) no longer flatten
        # into one tuple, so the frontier can rank a real-but-hard route STRICTLY above a not-a-reaction one
        # (:class:`~smartchem.experiment.affordability.Disposition`) instead of G6-sinking both equally.
        # -- channel 1, REAL-BUT-HARD: section-11 bench exclusions ...
        # DISPOSITION-ACTIVATE-01: when a process box is active, source channel-1 hardness from the RE-DERIVED process
        # exclusion (the SAME evaluate_process_requirements verdict PROCESS-ADMIT-01 authenticates on load), NOT the
        # untrusted free-text summary.exclusions -- so an admitted process-EXCLUDED route rides REAL_BUT_HARD on an
        # authenticated reason.  A physical/composability-only EXCLUDED route re-derives to a non-EXCLUDED process
        # status here, so it contributes no hardness and is not admitted (see run_compilation's frontier admission).
        if process_bounds is not None and process_bounds.constrains_anything:
            _proc = evaluate_process_requirements(summary.process_requirements, process_bounds)
            hard = tuple(_proc.exclusions) if _proc.status is ProcessFitStatus.EXCLUDED else ()
        else:
            hard = tuple(summary.exclusions) if summary.fit_status == "EXCLUDED" else ()
        # ... plus CATALYST-OBTAIN-01: a step declaring a catalyst the poor man cannot positively obtain -- an
        # industrial metal catalyst, or a declared-but-unrecognized one (the burden-of-proof flip) -- a route needing
        # an unobtainable catalyst sinks on the frontier (G6) even when it FITS the bench box.  A catalyst is
        # regenerated, so it is never a `leaf_input` and the cost axes never see it: this is the only channel that
        # carries catalyst obtainability into the poor-man frontier.  (No registered reaction declares a metal
        # catalyst today, so this appends nothing for every current route -- a guard ahead of its data.)  All of these
        # are REAL reactions that are just hard, so they ride ``hard_blockers`` (disposition tier REAL_BUT_HARD).
        hard = hard + route_catalyst_blockers(route)
        # -- channel 2, NOT-A-REACTION: REACTION-TYPE-ORACLE-01 (R56) -- a step that matches NO attested reaction class
        # is a reaction-TYPE FICTION, a formula-balanced graph move that is no real reaction at all (Problem A; R55
        # measured 72% of the frontier was such fiction, un-blocked).  This rides the DISTINCT ``fiction_blockers``
        # channel (disposition tier NOT_A_REACTION -- strictly worse than any real-but-hard route), demoting the
        # fiction as "not a known reaction" (honest coverage loss NOT false-VOUCH, and explicitly NOT a feasibility
        # claim -- that stays feasibility.py's job).
        fiction = route_reaction_type_blockers(route)
        # compute the shopping requirement ONCE and feed both the material_quantity axis (total moles) AND the
        # TERM-MAT quantity-weighted cash floor (per-leaf moles x price_per_mol); basket_cost_vector prefers the
        # weighted floor over the per-unit package cash when it is computable, else the per-unit path stands.
        reqs = _route_shopping_requirements(route)
        mq = None if reqs is None else float(sum(amount for _m, amount in reqs))
        vector = basket_cost_vector(
            list(route.leaf_inputs), material_quantity=mq,
            weighted_cash_leaves=(list(reqs) if reqs is not None else None),
            hard_blockers=hard, fiction_blockers=fiction,
        )
        entries.append(AffordabilityFrontierEntry.of(summary.route_digest, vector))
    # Run dominance FIRST, then gate on the SURVIVORS.  The signal must be checked on the POST-dominance frontier,
    # not on all entries: G6 can strip the only signal-bearing entry (a hard-blocked route dominated by a clean one),
    # leaving a frontier of blank UNKNOWN vectors -- exactly the "list of every route wearing a blank vector" the
    # honest-emptiness rule forbids.  Gating the survivors returns () in that case (no affordability info survived),
    # never a blank-vector list (red-team fold).
    frontier = pareto_frontier(entries)
    if not any(e.cost_vector.has_cost_signal() for e in frontier):
        return ()
    return tuple(frontier)


def run_compilation(
    request: CompilationRequest, *, provider_snapshots: tuple = (),
) -> CompilationResponse:
    """Execute ``request`` and return the typed response, delegating to the existing IR producers.

    Determinism is load-bearing: this reads ONLY the request's resolved semantic fields, so equal
    :attr:`CompilationRequest.semantic_digest` guarantees an equal response (section 13.1, "same semantic digest
    MUST execute the same search").  The outcome maps to the section 14.4 exit codes via :attr:`ResponseOutcome`.

    ``provider_snapshots`` (SNAPSHOT-13.2) is the seam for a caller to carry the dated provenance of a LIVE provider
    fetch onto a response whose RESULT depends on that fetch.  In the alpha the machine search here is
    offline-deterministic and consumes NO fetched provider evidence, so no CLI path passes a snapshot (the --json
    response is present-and-empty -- a named limitation, honest: a result that depends on no fetch has nothing to
    stamp).  The synthesize HUMAN dossier is where fetched stability actually feeds grading, and it renders the
    fetch's snapshot there.  Whatever IS passed here enters neither the search nor ``result_digest`` (a fetch date is
    provenance, not identity), so a fetch-dependent response would still be reproducible run-to-run.  Empty by default.
    """
    if type(request) is not CompilationRequest:
        raise TypeError("run_compilation needs a CompilationRequest")
    # ID-LAYER-02: refuse (exit 5) a declared match layer the engine cannot honestly honor, BEFORE any search runs.
    layer_refusal = _check_identity_layer(request)
    if layer_refusal is not None:
        response = layer_refusal
    elif request.operation is CompilationOperation.RECOMPILE:
        response = _run_recompile(request)
    else:
        response = _run_decompile(request)
    if provider_snapshots:
        from dataclasses import replace
        response = replace(response, provider_snapshots=tuple(provider_snapshots))
    return response


def _run_recompile(request: CompilationRequest) -> CompilationResponse:
    from .identity import representation_losses_for
    from .identity_parse import resolve_identity
    from .structure_descent import ScissionError

    try:
        # the STRUCTURE layer keeps the target's constitution but drops finer features it may declare (stereo,
        # isotope, net-neutral local charge).  Resolve the target through the ONE parser service (ID-PARSE-01) so
        # the IR carries the typed section-5.3 blockers (ID-STEREO-01) -- an enantiomer/isotopologue/zwitterion
        # target no longer flattens silently -- AND the response echoes how the input string was read (the
        # ParseReceipt).  A structure search needs a perceived structure, so a FORMULA/INCHI target (which perceives
        # composition, not a molecule) is a loud INVALID here: a bare formula does not name a structure (section 5.4).
        # A registered name declares no finer features (features is None); reagents/available are helper inputs whose
        # finer features do not bear on the TARGET's identity claims, so they resolve plainly.
        resolved = resolve_identity(request.target_input, request.input_kind)
        if resolved.molecule is None:
            return _invalid(
                request,
                f"a structure search (recompile) needs a perceived structure, but the "
                f"{resolved.receipt.requested_kind.value} target resolved to a {resolved.receipt.identity_layer}-"
                f"layer identity ({resolved.receipt.normalized}) with no molecule; use NAME or SMILES (section 5.4)",
            )
        # CANONICALISE every molecule entering the search (SVC-REQ-01 alias-collapse, red-team fix).  The route/
        # candidate digests recompile_to_ir emits embed each Molecule POSITIONALLY (its atom tuple), so a molecule
        # in a different atom ORDER yields different candidate digests -> a different IR digest -> a different
        # result_digest, EVEN for the identical species and route.  The offline NAME registry stores non-canonical
        # atom orders while the SMILES parser canonicalises, so ``name:X`` and ``smiles:X`` -- which the semantic
        # digest COLLAPSES onto the canonical structure identity -- would otherwise produce diverging result_digests
        # (a one-way-law break, invisible on paracetamol only because its search is INCOMPLETE with zero candidates).
        # Canonicalising here makes the EXECUTION presentation-invariant, so the collapse the digest claims is real.
        target, target_features = resolved.molecule.canonical(), resolved.features
        reagents = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in request.helper_reagents)
        available = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in request.stock_materials)
    except IdentityParseError as exc:
        return _invalid(request, str(exc))
    identity_losses = (
        () if target_features is None else representation_losses_for(request.target_input, target_features)
    )

    # Resolve the SELECTED transform algebra (0.7 Round II).  __post_init__ already validated the profile id + its
    # topology-coherence, so this cannot raise for a well-formed request; the registry flows through the search, the
    # IR, and the receipt so the exact algebra the caller chose is what actually runs (no silent DEFAULT fallback).
    registry = resolve_algebra_profile(request.algebra_profile)

    # An empty helper-reagent pool is a runnable search ONLY if the selected algebra has a reagentless-capable
    # provider.  The legacy capped-scission algebra needs a cutting reagent, so it still fails CLOSED (exit 2) on an
    # empty pool -- but a certified profile carrying reagentless families (Diels-Alder) may run, and we do NOT invent
    # water to satisfy the capped provider.  The CLI coerces an empty `--reagents` to the water default upstream, so
    # this guards only non-CLI callers.  (Registry/profile-aware, not a hardcoded profile-name check.)
    if not reagents and not any(p.reagentless_capable for p in registry.providers):
        return _invalid(
            request,
            "the selected transform algebra has no reagentless-capable provider and the helper-reagent pool is "
            "empty; capped-scission requires at least one cutting reagent",
        )

    if request.terminal_policy.commodities_enabled:
        from .data.reagents import commodity_inventory
        commodities = tuple(m.canonical() for m in commodity_inventory())  # canonical, per the target/reagent note above
    else:
        commodities = ()

    # Section 7: a target already on the terminal stock terminates before any expansion.  Checked structurally
    # (canonical STRUCTURE identity), never by parsing a diagnostic string -- the same identity the search uses.
    terminal_idents = {_structure_ident(m) for m in (*available, *reagents, *commodities)}
    target_available = _structure_ident(target) in terminal_idents

    mode = _GRAMMAR_TO_MODE[request.transform_grammar]
    max_depth = request.search_bounds.value("max_depth")
    max_results = request.search_bounds.value("max_results")
    cut_budget = request.search_bounds.value("cut_budget")
    try:
        # Search ONCE and reuse it BOTH ways (CLI-CAN-02 brick 2): the very same RouteSearchResult packages the IR
        # (its constraint-FREE candidates) AND is ranked against the section-11 bench box (the constraint-DEPENDENT
        # ranking).  No second search: the ranked dossiers describe exactly the candidates the IR carries.  The
        # section-11 box is deliberately NOT inside the IR -- the IR is the presentation-invariant search artifact
        # that two different constraints share; the constraint lives in the RESPONSE's ranked_route_dossiers.
        from .experiment.routes import search_dags, search_routes
        if mode == "routes":
            search_result = search_routes(
                target, reagents=reagents, available=available, commodities=commodities,
                max_depth=max_depth, max_routes=max_results, cut_budget=cut_budget, registry=registry,
            )
            routes_for_ranking: tuple = search_result.routes
        else:
            search_result = search_dags(
                target, reagents=reagents, available=available, commodities=commodities,
                max_depth=max_depth, max_dags=max_results, cut_budget=cut_budget, registry=registry,
            )
            # rank_routes fits LINEAR ExperimentRoutes; convergent-DAG bench fitting is a separate roadmap item, so
            # a DAG-mode search ranks nothing here -- the constraint is DECLARED (constraint_note fit_counts=None),
            # never silently reported as applied.
            routes_for_ranking = ()
        # BINDING INVARIANT (0.7 Round II): the packaged search MUST have run under the SELECTED algebra.  The
        # receipt stamps search_algebra_digest(topology, the-registry-it-used); assert it equals the digest of the
        # registry we resolved for THIS request, so a profile-A search can never be packaged/replayed as profile-B --
        # the mismatch is made a refusal, not a silent relabel.
        expected_algebra_digest = search_algebra_digest(_GRAMMAR_TO_MODE_TOPOLOGY[mode], registry)
        if search_result.receipt.transform_registry_digest != expected_algebra_digest:
            return _refused(
                request,
                "algebra-binding mismatch: the search receipt's transform-registry digest does not match the "
                "selected algebra profile (a search under one algebra cannot be packaged as another)",
            )
        ir = recompile_to_ir(
            target,
            reagents=reagents,
            available=available,
            commodities=commodities,
            max_depth=max_depth,
            max_results=max_results,
            cut_budget=cut_budget,
            mode=mode,
            registry=registry,
            identity_losses=identity_losses,
            search_result=search_result,
        )
    except ScissionError as exc:  # a ValueError subclass -> caught FIRST: a model-boundary refusal (exit 5)
        return _refused(request, f"refused at the chemistry-model boundary: {exc}")

    outcome = _classify(ir, target_available)
    # CLI-CAN-02 brick 2: APPLY the section-11 T/P constraint -- rank the routes against the bench box and populate
    # ranked_route_dossiers with the per-route fit disposition.  The DECLARED-vs-APPLIED disclosure rides the RESPONSE
    # diagnostics (not just the CLI render) so BOTH the human and --json views agree (CLI-JSON-01): fit_counts=None
    # when nothing was ranked (no routes, or DAG mode), else the (fit/excluded/unknown) tally.  A consumer can now
    # read which routes fall inside the bench and which are EXCLUDED -- and can never mistake an UNKNOWN-fit for a pass.
    ranked = _ranked_summaries(routes_for_ranking, request.constraints.bounds, identity_losses,
                               process=request.constraints.process)
    # COST-VEC-01: the section-10.4 Pareto affordability frontier over the SAME ranked routes -- each route's
    # commodity leaves priced into a CostVector, EXCLUDED routes G6-dominated by their hard bounds.  Empty when no
    # route carries affordability signal (honest), so this never fabricates a cost ranking from absent price data.
    if request.constraints.process.constrains_anything:
        # DISPOSITION-ACTIVATE-01: admit a route to the process-constrained affordability frontier iff it is FITS OR its
        # RE-DERIVED process status is EXCLUDED (a genuine reaction the bench cannot run -> REAL_BUT_HARD).  The old gate
        # admitted FITS-only, which structurally hid every real-but-unrunnable route (R59's REAL_BUT_HARD tier could
        # never be populated).  Admitting the process-EXCLUDED set is SOUND because that exclusion is re-derived from the
        # carried per-step process_requirements (PROCESS-ADMIT-01) and re-checked on load, so it does not reopen the
        # free-text forge the FITS-only gate closed; the physical/composability EXCLUDED axes stay OUT (not re-derivable
        # from the thin projection, so their hardness would be untrusted).
        _pbounds = request.constraints.process
        def _frontier_admit(r: "object") -> bool:
            if r.fit_status == "FITS":
                return True
            return evaluate_process_requirements(r.process_requirements, _pbounds).status is ProcessFitStatus.EXCLUDED
        admitted = tuple(r for r in ranked if _frontier_admit(r))
        admitted_ids = {r.route_digest for r in admitted}
        frontier = _affordability_frontier(
            tuple(r for r in routes_for_ranking if r.digest in admitted_ids), admitted, process_bounds=_pbounds
        )
    else:
        frontier = _affordability_frontier(routes_for_ranking, ranked)
    diagnostics = tuple(ir.diagnostics)
    _note = constraint_note(
        request.constraints.bounds, fit_counts=_fit_counts(ranked) if ranked else None,
        process=request.constraints.process,
    )
    if _note is not None:
        diagnostics = (*diagnostics, _note)
    # DAG-BENCH-01 + DAG-RANK-01: each convergent route's COMBINED section-11 bench fit is formally admitted -- a
    # RankedDAGSummary per DAG (composability + physical + process), the process component re-derived on load, so
    # process_selection_status is no longer UNASSESSED and a combined-FITS DAG can flip exit to success -- AND the DAGs
    # are now RANKED best-first (rank_dags), the DAG analogue of the linear route ranking, so a chemist handed several
    # admissible convergent routes sees the best-evidenced one first (the "DAG mode ranked nothing" gap, closed).
    # Built when the bench box constrains ANYTHING (physical OR process) -- the same standard the linear ranking uses --
    # so a physical-only DAG constraint is admitted too; the human-readable tally rides _dag_bench_note.
    dag_dossiers: tuple = ()
    if mode == "dags":
        from .experiment.drafter import ConstraintBox
        _dags = getattr(search_result, "dags", ())
        _box = ConstraintBox.of_bounds(request.constraints.bounds, process=request.constraints.process)
        if _box.constrains_anything:
            # The rank+project seam moves together under one phase declaration (ITEM5-DAG-PHASE-01).  The recompile
            # request carries no phase field yet, so this passes none -- exactly as the linear rank_routes production
            # call likewise passes none; a request-level phase declaration (+ its replay/verified-admission carry) is
            # the named follow-up.  Byte-identical to the prior inline of_dag/rank_dags co-call.
            dag_dossiers = ranked_dag_dossiers(_dags, _box)
        _dag_note = _dag_bench_note(_dags, _box)
        if _dag_note is not None:
            diagnostics = (*diagnostics, _dag_note)
    # echo the identity resolution (ID-PARSE-01) as the FIRST-CLASS parse_receipt_summary, NOT a diagnostics line
    # (SVC-REQ-01 alias-collapse): both views still report how the target string was read, but it is provenance --
    # kept out of ``diagnostics`` so it never enters ``result_digest`` and the aliased spellings share a result.
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA, request, outcome, ir.standard_status, ir,
        diagnostics,
        ranked_route_dossiers=ranked,
        affordability_frontier=frontier,
        parse_receipt_summary=resolved.receipt.summary(),
        ranked_dag_dossiers=dag_dossiers,
    )


def _run_decompile(request: CompilationRequest) -> CompilationResponse:
    from .compilation_ir import ChemicalIdentity
    from .decompiler import DecompilerError, Formula

    # A decompile normally reads the target as FORMULA TEXT.  A SMILES target is resolved to its formula HERE, and
    # that structure->formula reduction is RECORDED as a typed section-5.3 IdentityLoss (a BLOCKER) carried into the
    # IR, so the machine response surfaces exactly the loss the human render shows -- structure is never silently
    # discarded on the machine path (section 5.3), and the two views agree (CLI-JSON-01).  NAME/InChI remain a named
    # follow-on (ID-PARSE-01) and are refused rather than mis-parsed.
    decompile_target = request.target_input
    identity_losses: tuple[IdentityLoss, ...] = ()
    receipt_summary: "str | None" = None
    if request.input_kind is InputKind.SMILES:
        from .identity import formula_reduction_loss, representation_losses_for
        from .identity_parse import resolve_identity
        try:
            resolved = resolve_identity(request.target_input, InputKind.SMILES)
        except IdentityParseError as exc:
            return _invalid(request, str(exc))
        molecule, features = resolved.molecule, resolved.features
        decompile_target = "".join(
            f"{el}{n if n > 1 else ''}" for el, n in sorted(molecule.formula.items())
        )
        # the TYPED section-5.3 records (IR-LOSS-01), not summary strings -- the IR carries the first-class losses.
        # The formula reduction is the coarse blocker (structure -> formula); the ID-STEREO-01 finer losses NAME the
        # specific dropped features (which stereocentre/isotope/charge) the input actually declared -- additive and
        # fail-closed (features is a SmilesFeatures for a SMILES input, never None).
        identity_losses = (
            formula_reduction_loss(request.target_input, decompile_target),
            *representation_losses_for(request.target_input, features),
        )
        receipt_summary = resolved.receipt.summary()
    elif request.input_kind in (InputKind.INCHI, InputKind.TARGET_FILE):
        # ID-PARSE-01: an InChI resolves via its FORMULA SUBLAYER (its /c connectivity + any /t,/b,/i stereo/isotope
        # recorded as section-5.3 BLOCKERS the parser already built); a TARGET_FILE resolves its contents (a molecule
        # -> reduced to formula exactly like the SMILES path, or a formula used directly).  Both descend by formula
        # here, carrying the parser's typed losses into the IR so the machine and human views agree on the drop.
        from .identity import formula_reduction_loss, representation_losses_for
        from .identity_parse import resolve_identity
        try:
            resolved = resolve_identity(request.target_input, request.input_kind)
        except IdentityParseError as exc:
            return _invalid(request, str(exc))
        if resolved.molecule is not None:                # a file that named a NAME/SMILES: reduce structure->formula
            decompile_target = "".join(
                f"{el}{n if n > 1 else ''}" for el, n in sorted(resolved.molecule.formula.items())
            )
            identity_losses = (
                formula_reduction_loss(request.target_input, decompile_target),
                *(representation_losses_for(request.target_input, resolved.features) if resolved.features else ()),
            )
        else:                                            # a formula-layer identity (formula-only file, or an InChI)
            decompile_target = "".join(
                f"{el}{n if n > 1 else ''}" for el, n in resolved.formula.counts
            )
            identity_losses = resolved.losses
        receipt_summary = resolved.receipt.summary()
    elif request.input_kind is InputKind.NAME:
        return _invalid(
            request,
            "decompile reads the target as formula text or a resolved structure; a bare NAME is resolved by "
            "recompile (a structure search), not by a formula descent -- give the formula or use recompile",
        )
    else:
        # AUTO / FORMULA: the target is read as formula text.  Echo the resolution (best-effort: a genuinely bad
        # formula still reaches decompile_to_ir's canonical parse error below, so its exact message is preserved).
        from .identity_parse import resolve_identity
        try:
            receipt_summary = resolve_identity(request.target_input, InputKind.FORMULA).receipt.summary()
        except IdentityParseError:
            receipt_summary = None

    try:
        ir = decompile_to_ir(
            decompile_target,
            request.terminal_policy.formula_inventory,
            max_multiplicity=request.search_bounds.value("max_multiplicity"),
            budget=request.search_bounds.value("budget"),
            max_edges=request.search_bounds.value("max_edges"),
            identity_losses=identity_losses,
        )
    except (DecompilerError, ValueError) as exc:
        return _invalid(request, f"invalid chemistry input: {exc}")

    # Section 7 vs 8.3: a target that is ITSELF one of the declared terminal buckets is trivially on hand, not a
    # no-route dead end.  Distinguish them by canonical FORMULA identity (H2O == OH2) -- the same identity the IR
    # keys on -- so an already-a-bucket target reports TARGET_ALREADY_AVAILABLE (exit 0), not the section 8.3
    # NO_ROUTE_COMPLETE (exit 3) claim of absence over something already in the inventory.
    inventory_ids = set()
    for inv in request.terminal_policy.formula_inventory:
        try:
            inventory_ids.add(ChemicalIdentity.of_formula(Formula.parse(inv)).identity_digest)
        except (DecompilerError, ValueError):
            continue
    # A decompile target is "already available" when it is a declared bucket OR an INTRINSIC terminal -- a bare
    # element (a universal atom bucket the decompiler bottoms out at) or a formula that needs no decomposition.  The
    # tell for the intrinsic case is a COMPLETE search that produced ZERO edges: the target did not (need to)
    # decompose, so it is terminal, exactly what the human edge-list path reports as "already a bucket" (exit 0).
    # Without this, a bare element absent from the DECLARED inventory (e.g. `decompile He`/`Fe`) was miscoded
    # NO_ROUTE_COMPLETE -- a confident section-8.3 claim of absence over something already elemental, and a drift
    # from the human path the CLI-CAN-01 routing promises cannot happen (exit 0 vs 3 for one command).
    already_terminal = ir.complete_within_bounds and ir.candidate_count == 0
    target_available = (ir.target.identity_digest in inventory_ids) or already_terminal
    outcome = _classify(ir, target_available=target_available)
    # the identity-resolution echo rides the first-class parse_receipt_summary field (SVC-REQ-01 alias-collapse),
    # not diagnostics, so diagnostics stays receipt-free and the receipt is provenance excluded from result_digest.
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA, request, outcome, ir.standard_status, ir, tuple(ir.diagnostics),
        parse_receipt_summary=receipt_summary,
    )


# -- serialization (the request/response are transportable artifacts: CLI-JSON-01 leans on this) -----------------


def _process_to_payload(bounds: ProcessBounds) -> dict:
    from dataclasses import asdict
    payload = asdict(bounds)
    for name in ("allowed_attention", "allowed_agitation"):
        value = payload[name]
        payload[name] = None if value is None else [x.value for x in value]
    value = payload["available_equipment"]
    payload["available_equipment"] = None if value is None else list(value)
    return payload


def _process_from_payload(payload: dict) -> ProcessBounds:
    if type(payload) is not dict or set(payload) != set(_process_to_payload(ProcessBounds())):
        raise ValueError("process bounds must contain exactly the versioned fields")
    values = dict(payload)
    for name, enum in (("allowed_attention", Attention), ("allowed_agitation", Agitation)):
        if values[name] is not None:
            if type(values[name]) is not list:
                raise TypeError(f"{name} must be an array or null")
            values[name] = tuple(enum(x) for x in values[name])
    if values["available_equipment"] is not None:
        if type(values["available_equipment"]) is not list:
            raise TypeError("available_equipment must be an array or null")
        values["available_equipment"] = tuple(values["available_equipment"])
    return ProcessBounds(**values)


def _interval_to_payload(interval) -> "dict | None":
    return None if interval is None else {"lo": interval.lo, "hi": interval.hi, "unit": interval.unit}


def _interval_from_payload(payload) -> "object | None":
    if payload is None:
        return None
    from .conditions import Interval
    if type(payload) is not dict or set(payload) != {"lo", "hi", "unit"}:
        raise ValueError("interval must contain exactly lo, hi, unit")
    return Interval(payload["lo"], payload["hi"], payload["unit"])


def _source_to_payload(source) -> "dict | None":
    return None if source is None else {"locator": source.locator, "review": source.review.value}


def _source_from_payload(payload) -> "object | None":
    if payload is None:
        return None
    from .provenance import SourceCitation, SourceReview
    if type(payload) is not dict or set(payload) != {"locator", "review"}:
        raise ValueError("source citation must contain exactly locator, review")
    return SourceCitation(payload["locator"], SourceReview(payload["review"]))


def _process_requirements_to_payload(req: "ProcessRequirements | None") -> "dict | None":
    """A canonical JSON-ready dict for one step's declared process facts (PROCESS-ADMIT-01), or ``null`` for an
    undeclared step.  Intervals/enums/citation are flattened; unknown fields stay ``null``, never a fabricated 0."""
    if req is None:
        return None
    return {
        "elapsed_minutes": _interval_to_payload(req.elapsed_minutes),
        "active_minutes": _interval_to_payload(req.active_minutes),
        "attention": None if req.attention is None else req.attention.value,
        "check_interval_minutes": req.check_interval_minutes,
        "agitation": None if req.agitation is None else req.agitation.value,
        "equipment": None if req.equipment is None else list(req.equipment),
        "workup_included": req.workup_included,
        "provenance": req.provenance,
        "source": _source_to_payload(req.source),
        "peak_temperature_k": req.peak_temperature_k,
        "min_pressure_atm": req.min_pressure_atm,
        "max_pressure_atm": req.max_pressure_atm,
        "min_elapsed_minutes": req.min_elapsed_minutes,
        "min_active_minutes": req.min_active_minutes,
    }


_PROCESS_REQUIREMENTS_FIELDS = frozenset(_process_requirements_to_payload(ProcessRequirements()))


def _process_requirements_from_payload(payload: "dict | None") -> "ProcessRequirements | None":
    """Reconstruct one step's process requirements; ``ProcessRequirements.__post_init__`` re-validates every field.
    An exact field-set guard means a payload cannot silently drop or smuggle a requirement past the re-derivation."""
    if payload is None:
        return None
    if type(payload) is not dict or set(payload) != _PROCESS_REQUIREMENTS_FIELDS:
        raise ValueError("process requirements must contain exactly the versioned fields")
    values = dict(payload)
    values["elapsed_minutes"] = _interval_from_payload(values["elapsed_minutes"])
    values["active_minutes"] = _interval_from_payload(values["active_minutes"])
    values["attention"] = None if values["attention"] is None else Attention(values["attention"])
    values["agitation"] = None if values["agitation"] is None else Agitation(values["agitation"])
    if values["equipment"] is not None:
        if type(values["equipment"]) is not list:
            raise TypeError("equipment must be an array or null")
        values["equipment"] = tuple(values["equipment"])
    values["source"] = _source_from_payload(values["source"])
    return ProcessRequirements(**values)


# ---------------------------------------------------------------------------------------------------------------------
# v0.8 Real Route Dossiers: the typed readiness-ladder codecs.  Modeled EXACTLY on the process-requirements pair above
# (an exact-field-set guard so a payload cannot drop or smuggle an obligation past reconstruction) -- reconstructing
# through the REAL ``StepReadiness``/``RouteReadiness`` constructors means their own ``__post_init__`` re-validates the
# coherence table (e.g. a ``reaction_class_name`` orphaned from a non-SATISFIED ``reaction_type``) on every load, not
# only at production time.
# ---------------------------------------------------------------------------------------------------------------------


def _step_readiness_to_payload(step: "StepReadiness") -> dict:
    """A canonical JSON-ready dict for one step's readiness obligations."""
    return {
        "formal_candidate": step.formal_candidate.value,
        "reaction_type": step.reaction_type.value,
        "reaction_class_name": step.reaction_class_name,
        "conditions": step.conditions.value,
        "process": step.process.value,
        "workup_isolation": step.workup_isolation.value,
        "provenance": list(step.provenance),
        "open_obligations": list(step.open_obligations),
    }


_STEP_READINESS_FIELDS = frozenset(_step_readiness_to_payload(
    StepReadiness(
        formal_candidate=ObligationStatus.SATISFIED, reaction_type=ObligationStatus.UNSATISFIED,
        reaction_class_name=None, conditions=ObligationStatus.UNKNOWN, process=ObligationStatus.UNKNOWN,
        workup_isolation=ObligationStatus.UNKNOWN, provenance=(), open_obligations=("x",),
    )
))


def _step_readiness_from_payload(payload: dict) -> "StepReadiness":
    """Reconstruct one step's readiness; ``StepReadiness.__post_init__`` re-validates every coherence rule (the
    SATISFIED-reaction_type-iff-a-class-name rule, canonical sort/distinctness of the obligation tuples)."""
    if type(payload) is not dict or set(payload) != _STEP_READINESS_FIELDS:
        raise ValueError("step readiness must contain exactly the versioned fields")
    for name in ("provenance", "open_obligations"):
        if type(payload[name]) is not list or any(type(x) is not str for x in payload[name]):
            raise TypeError(f"step readiness {name} must be an array of strings")
    if payload["reaction_class_name"] is not None and type(payload["reaction_class_name"]) is not str:
        raise TypeError("step readiness reaction_class_name must be a string or null")
    return StepReadiness(
        formal_candidate=ObligationStatus(payload["formal_candidate"]),
        reaction_type=ObligationStatus(payload["reaction_type"]),
        reaction_class_name=payload["reaction_class_name"],
        conditions=ObligationStatus(payload["conditions"]),
        process=ObligationStatus(payload["process"]),
        workup_isolation=ObligationStatus(payload["workup_isolation"]),
        provenance=tuple(payload["provenance"]),
        open_obligations=tuple(payload["open_obligations"]),
    )


def _route_readiness_to_payload(readiness: "RouteReadiness") -> dict:
    """A canonical JSON-ready dict for a route's whole readiness ladder (one entry per step, in route order)."""
    return {
        "per_step": [_step_readiness_to_payload(s) for s in readiness.per_step],
        "route_open_obligations": list(readiness.route_open_obligations),
    }


_ROUTE_READINESS_FIELDS = frozenset({"per_step", "route_open_obligations"})


def _route_readiness_from_payload(payload: dict) -> "RouteReadiness":
    """Reconstruct a route's readiness; ``RouteReadiness.__post_init__`` re-validates the non-empty-tuple and
    canonical-sort/distinctness rules on ``route_open_obligations``."""
    if type(payload) is not dict or set(payload) != _ROUTE_READINESS_FIELDS:
        raise ValueError("route readiness must contain exactly per_step, route_open_obligations")
    if type(payload["per_step"]) is not list:
        raise TypeError("route readiness per_step must be an array")
    if type(payload["route_open_obligations"]) is not list or any(
        type(x) is not str for x in payload["route_open_obligations"]
    ):
        raise TypeError("route readiness route_open_obligations must be an array of strings")
    return RouteReadiness(
        per_step=tuple(_step_readiness_from_payload(s) for s in payload["per_step"]),
        route_open_obligations=tuple(payload["route_open_obligations"]),
    )


# ---------------------------------------------------------------------------------------------------------------------
# ONLOAD-REDERIVE (queue item 2): the thick per-step REPLAY payload + conservation-certified reconstruction.
#
# These codecs are the load-bearing new machinery for the composability + physical re-derivation on load.  A summary's
# ``replay_payload`` carries the COMPLETE steps (target/reactants/products/reagents + full 10-field envelope), so the
# loader can reconstruct the exact ``ExperimentRoute``/``SynthesisDAG`` and require ``reconstruct.digest == route_digest``
# (the ROUTE-BINDING invariant, v0.2 scope decision).  Two rules keep the round trip DIGEST-STABLE and safe:
#   * molecules are encoded POSITIONALLY (atoms tuple order + sorted bonds + charge + state), mirroring
#     ``compilation_ir._graph_payload`` -- route_digest is over the raw positional graph, so re-parsing from SMILES or
#     canonicalising would make an HONEST route fail the binding (a false reject).  Never canonicalise here.
#   * every reconstruction runs the real constructor (``ExperimentStep.__post_init__`` conservation certificate,
#     ``ConditionEnvelope.__post_init__`` unit/status/provenance validation), so a forged non-conserving step or an
#     out-of-band unit swap is refused at reconstruction, not trusted.
# ---------------------------------------------------------------------------------------------------------------------

_MOLECULE_PAYLOAD_FIELDS = frozenset({"atoms", "bonds", "charge", "state"})


def _molecule_to_payload(mol) -> dict:
    """Order-PRESERVING structural encoding of a Molecule (mirrors ``compilation_ir._graph_payload``): the raw atoms
    tuple, sorted ``[i, j, order]`` bonds, charge, and state.  Digest-identical on reconstruction (no canonical remap)."""
    return {
        "atoms": list(mol.atoms),
        "bonds": sorted([b.i, b.j, b.order] for b in mol.bonds),
        "charge": mol.charge,
        "state": mol.state,
    }


def _molecule_from_payload(payload) -> "object":
    """Rebuild a Molecule from its positional payload; wire types validated BEFORE construction (so a bool/float/str
    can never be silently coerced into an atom index or charge -- the edges int-coercion trap, avoided here)."""
    from .category import Bond, Molecule
    if type(payload) is not dict or set(payload) != _MOLECULE_PAYLOAD_FIELDS:
        raise ValueError("molecule payload must contain exactly atoms, bonds, charge, state")
    atoms, bonds, charge, state = payload["atoms"], payload["bonds"], payload["charge"], payload["state"]
    if type(atoms) is not list or any(type(a) is not str for a in atoms):
        raise TypeError("molecule atoms must be a list of element strings")
    if type(bonds) is not list:
        raise TypeError("molecule bonds must be a list of [i, j, order] triples")
    bond_objs = []
    for b in bonds:
        if type(b) is not list or len(b) != 3 or any(isinstance(x, bool) or type(x) is not int for x in b):
            raise TypeError("each bond must be a [i, j, order] triple of ints")
        bond_objs.append(Bond(b[0], b[1], b[2]))
    if isinstance(charge, bool) or type(charge) is not int:
        raise TypeError("molecule charge must be an int")
    if type(state) is not str:
        raise TypeError("molecule state must be a string")
    return Molecule(tuple(atoms), frozenset(bond_objs), charge, state)


_CONDITION_ENVELOPE_PAYLOAD_FIELDS = frozenset(
    {"temperature", "pressure", "duration", "medium", "catalysts", "applied_field",
     "status", "provenance", "source", "process"}
)


def _condition_envelope_to_payload(env) -> dict:
    """Flatten all 10 condition-envelope fields.  Intervals/enum/citation/process reuse the existing flat codecs, so a
    lossy round trip (an averaged interval, a promoted status, a dropped source review) cannot slip past reconstruction."""
    return {
        "temperature": _interval_to_payload(env.temperature),
        "pressure": _interval_to_payload(env.pressure),
        "duration": _interval_to_payload(env.duration),
        "medium": env.medium,
        "catalysts": list(env.catalysts),
        "applied_field": env.applied_field,
        "status": env.status.value,
        "provenance": env.provenance,
        "source": _source_to_payload(env.source),
        "process": _process_requirements_to_payload(env.process),
    }


def _condition_envelope_from_payload(payload) -> "object":
    """Rebuild a ConditionEnvelope; its ``__post_init__`` re-validates K/atm/min units, the EvidenceStatus cap, and the
    declaration/provenance/source consistency, so a payload cannot smuggle an invalid or promoted envelope past load."""
    from .conditions import ConditionEnvelope, EvidenceStatus
    if type(payload) is not dict or set(payload) != _CONDITION_ENVELOPE_PAYLOAD_FIELDS:
        raise ValueError("condition envelope payload must contain exactly the versioned fields")
    catalysts = payload["catalysts"]
    if type(catalysts) is not list or any(type(c) is not str for c in catalysts):
        raise TypeError("catalysts must be a list of strings")
    for name in ("medium", "applied_field", "provenance", "status"):
        if type(payload[name]) is not str:
            raise TypeError(f"envelope {name} must be a string")
    return ConditionEnvelope(
        _interval_from_payload(payload["temperature"]),
        _interval_from_payload(payload["pressure"]),
        _interval_from_payload(payload["duration"]),
        payload["medium"],
        tuple(catalysts),
        payload["applied_field"],
        EvidenceStatus(payload["status"]),
        payload["provenance"],
        _source_from_payload(payload["source"]),
        _process_requirements_from_payload(payload["process"]),
    )


_STEP_REQUIRED_PAYLOAD_FIELDS = frozenset(
    {"schema_version", "target", "reactants", "products", "reagents", "envelope"}
)
#: ``reaction_center`` (R58) is an OPTIONAL step-payload field: only serialised when the step carries one, and a
#: payload without it (an older replay envelope, or a hand-built step) reconstructs a centre-less step. Keeping it
#: optional means adding it did NOT change the bytes of any centre-less step's payload, and -- because the centre is
#: a non-identity annotation -- it never enters the step's content digest either way.
_STEP_OPTIONAL_PAYLOAD_FIELDS = frozenset({"reaction_center"})
_STEP_PAYLOAD_FIELDS = _STEP_REQUIRED_PAYLOAD_FIELDS | _STEP_OPTIONAL_PAYLOAD_FIELDS


def _step_to_payload(step) -> dict:
    """Encode one complete ExperimentStep: ordered reactant/product/reagent molecule multisets (multiplicity and
    byproducts preserved -- never a set) + the full envelope, plus the R58 reaction centre when the step carries one
    (so a centre-carrying step reads identically live and on replay)."""
    payload = {
        "schema_version": step.schema_version,
        "target": _molecule_to_payload(step.target),
        "reactants": [_molecule_to_payload(m) for m in step.reactants],
        "products": [_molecule_to_payload(m) for m in step.products],
        "reagents": [_molecule_to_payload(m) for m in step.reagents],
        "envelope": _condition_envelope_to_payload(step.envelope),
    }
    center = getattr(step, "reaction_center", None)
    if center is not None:
        payload["reaction_center"] = center.to_payload()
    return payload


def _step_from_payload(payload) -> "object":
    """Rebuild one ExperimentStep; its ``__post_init__`` re-runs the mass+charge conservation certificate, the
    target-in-products check, and the reagent-multiset-subset check -- a forged non-conserving step is refused here.
    The R58 ``reaction_center`` is optional: absent -> a centre-less step (the whole-molecule recognizer fallback)."""
    from .experiment.step import ExperimentStep
    from .reaction_center import ReactionCenter
    keys = set(payload) if type(payload) is dict else None
    if keys is None or not (_STEP_REQUIRED_PAYLOAD_FIELDS <= keys) or (keys - _STEP_PAYLOAD_FIELDS):
        raise ValueError("step payload must contain exactly the versioned fields (reaction_center optional)")
    for name in ("reactants", "products", "reagents"):
        if type(payload[name]) is not list:
            raise TypeError(f"step {name} must be a list of molecule payloads")
    if type(payload["schema_version"]) is not str:
        raise TypeError("step schema_version must be a string")
    center_payload = payload.get("reaction_center")
    center = ReactionCenter.from_payload(center_payload) if center_payload is not None else None
    return ExperimentStep(
        payload["schema_version"],
        _molecule_from_payload(payload["target"]),
        tuple(_molecule_from_payload(m) for m in payload["reactants"]),
        tuple(_molecule_from_payload(m) for m in payload["products"]),
        tuple(_molecule_from_payload(m) for m in payload["reagents"]),
        _condition_envelope_from_payload(payload["envelope"]),
        center,
    )


def _steps_to_replay_payload(steps) -> list:
    """The thick replay payload for a route/DAG: its complete steps, in the route/DAG's own step order."""
    return [_step_to_payload(s) for s in steps]


def _replay_payload_to_steps(payload) -> tuple:
    """Reconstruct the ordered step tuple from a replay payload (each step conservation-certified on the way in)."""
    if type(payload) is not list or not payload:
        raise ValueError("a replay payload must be a non-empty list of step payloads")
    return tuple(_step_from_payload(sp) for sp in payload)


def _reconstruct_route(payload) -> "object":
    """Reconstruct the ExperimentRoute from a replay payload; ``__post_init__`` re-checks linearity (net-consumption)."""
    from .experiment.step import ROUTE_SCHEMA, ExperimentRoute
    return ExperimentRoute(ROUTE_SCHEMA, _replay_payload_to_steps(payload))


def _reconstruct_dag(payload) -> "object":
    """Reconstruct the SynthesisDAG from a replay payload; ``__post_init__`` re-checks the DAG shape (acyclic/single-sink)."""
    from .experiment.dag import DAG_SCHEMA, SynthesisDAG
    return SynthesisDAG(DAG_SCHEMA, _replay_payload_to_steps(payload))


def request_to_payload(request: CompilationRequest) -> dict:
    """A canonical JSON-ready dict for a request; ``canonical_digest`` of the round-trip is stable."""
    return {
        "schema_version": request.schema_version,
        "operation": request.operation.value,
        "target_input": request.target_input,
        "input_kind": request.input_kind.value,
        "normalized_identity": request.normalized_identity,
        "identity_policy": {
            "policy_id": request.identity_policy.policy_id,
            "match_layer": request.identity_policy.match_layer.value,
        },
        "terminal_policy": {
            "match_mode": request.terminal_policy.match_mode,
            "commodities_enabled": request.terminal_policy.commodities_enabled,
            "formula_inventory": list(request.terminal_policy.formula_inventory),
        },
        "stock_materials": list(request.stock_materials),
        "helper_reagents": list(request.helper_reagents),
        "transform_grammar": request.transform_grammar.value,
        "evidence_provider_selection": {"selection_id": request.evidence_provider_selection.selection_id},
        "search_bounds": [list(pair) for pair in request.search_bounds.bounds],
        "constraints": {
            "schema_version": request.constraints.bounds.schema_version,
            "max_temperature_k": request.constraints.bounds.max_temperature_k,
            "min_pressure_atm": request.constraints.bounds.min_pressure_atm,
            "max_pressure_atm": request.constraints.bounds.max_pressure_atm,
            "process": _process_to_payload(request.constraints.process),
        },
        "ranking_policy": {"policy_id": request.ranking_policy.policy_id},
        "output_policy": {
            "render_mode": request.output_policy.render_mode,
            "quiet": request.output_policy.quiet,
        },
        "origins": [[name, origin.value] for name, origin in request.origins],
        "algebra_profile": request.algebra_profile,
    }


def request_from_payload(payload: dict) -> CompilationRequest:
    """Reconstruct a request from :func:`request_to_payload`; re-validates via the frozen records' guards.

    ``normalized_identity`` is DERIVED, not trusted: it is RECOMPUTED from ``(operation, target_input, input_kind)``
    and a payload whose stored value disagrees is REFUSED (red-team fix).  Because it is the target's contribution
    to the SEARCH identity, a hand-forged value could otherwise give one molecule's request another molecule's
    ``normalized_identity`` -> an equal ``semantic_digest`` over two DIFFERENT searches (a section-13.1 break: "same
    semantic digest MUST execute the same search").  Recomputing here makes deserialization authoritative.
    """
    if payload.get("schema_version") != COMPILATION_REQUEST_SCHEMA:
        raise ValueError(f"request schema_version must be exactly {COMPILATION_REQUEST_SCHEMA!r}")
    tp = payload["terminal_policy"]
    operation = CompilationOperation(payload["operation"])
    target_input = payload["target_input"]
    input_kind = InputKind(payload["input_kind"])
    expected_normalized = (
        _recompile_normalized_identity(target_input, input_kind)
        if operation is CompilationOperation.RECOMPILE
        else ""
    )
    if payload["normalized_identity"] != expected_normalized:
        raise ValueError(
            f"normalized_identity {payload['normalized_identity']!r} does not match the target's resolution "
            f"{expected_normalized!r} (a forged or stale search identity)"
        )
    return CompilationRequest(
        payload["schema_version"],
        operation,
        target_input,
        input_kind,
        expected_normalized,
        IdentityPolicy(
            payload["identity_policy"]["policy_id"],
            MatchLayer(payload["identity_policy"]["match_layer"]),
        ),
        TerminalPolicy(
            tp["match_mode"], tp["commodities_enabled"], tuple(tp["formula_inventory"])
        ),
        tuple(payload["stock_materials"]),
        tuple(payload["helper_reagents"]),
        TransformGrammar(payload["transform_grammar"]),
        EvidenceProviderSelection(payload["evidence_provider_selection"]["selection_id"]),
        SearchBounds(tuple((name, value) for name, value in payload["search_bounds"])),
        ConstraintPolicy(
            PhysicalBounds(
                payload["constraints"]["schema_version"],
                payload["constraints"]["max_temperature_k"],
                payload["constraints"]["min_pressure_atm"],
                payload["constraints"]["max_pressure_atm"],
            ),
            process=_process_from_payload(payload["constraints"]["process"]),
        ),
        RankingPolicy(payload["ranking_policy"]["policy_id"]),
        OutputPolicy(payload["output_policy"]["render_mode"], payload["output_policy"]["quiet"]),
        tuple((name, FieldOrigin(origin)) for name, origin in payload["origins"]),
        # FROZEN wire-migration law (0.7 Round III): a pre-0.7 payload has no algebra_profile field and historically
        # meant the capped algebra, so a MISSING field reconstructs as LEGACY_MISSING_ALGEBRA_PROFILE -- NOT the
        # (promotable) build default.  This is what keeps promoting the route default from silently reinterpreting an
        # old serialized request as the wider algebra.  An unknown/incompatible id is refused by
        # CompilationRequest.__post_init__ (fail-closed, so a tampered profile string cannot select a hidden algebra).
        algebra_profile=payload.get("algebra_profile", LEGACY_MISSING_ALGEBRA_PROFILE),
    )


def serialize_request(request: CompilationRequest) -> str:
    return json.dumps(request_to_payload(request), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def deserialize_request(text: str) -> CompilationRequest:
    return request_from_payload(json.loads(text))


def ranked_summary_to_payload(summary: RankedRouteSummary, *, include_replay: bool = False) -> dict:
    """A canonical JSON-ready dict for one ranked-route summary (CLI-CAN-02 brick 2).

    ``include_replay`` (default False) controls whether the ONLOAD-REDERIVE thick ``replay_payload`` is emitted to the
    wire.  Off by default so an ordinary response is byte-identical to the pre-item-2 form (the payload is
    ``compare=False`` -- outside ``result_digest`` -- so its presence/absence never moves route identity); a producer
    serialising for a verified-admission consumer passes True."""
    payload = {
        "schema_version": summary.schema_version,
        "route_digest": summary.route_digest,
        "equation": summary.equation,
        "fit_status": summary.fit_status,
        # v0.8 Real Route Dossiers: "readiness" is the typed Sec 3/4/8 obligation ladder (the source of truth);
        # "readiness_tier" rides alongside it as a DERIVED convenience field (summary.readiness_tier is a @property
        # reading straight off readiness.tier) so a thin consumer that only wants the coarse tier need not decode the
        # full ladder -- it is re-derived on load and refused if it disagrees (never trusted on its own).
        "readiness": _route_readiness_to_payload(summary.readiness),
        "readiness_tier": summary.readiness_tier,
        "exclusions": list(summary.exclusions),
        "gaps": list(summary.gaps),
        "composability_verdict": summary.composability_verdict,
        "selectivity_verdict": summary.selectivity_verdict,
        "feasibility_verdict": summary.feasibility_verdict,
        "equilibrium_verdict": summary.equilibrium_verdict,
        "kinetics_verdict": summary.kinetics_verdict,
        "process_requirements": [_process_requirements_to_payload(r) for r in summary.process_requirements],
    }
    if include_replay and summary.replay_payload is not None:
        payload["replay_payload"] = summary.replay_payload
    return payload


def ranked_summary_from_payload(payload: dict) -> RankedRouteSummary:
    """Reconstruct a ranked-route summary; re-validates via its __post_init__ coherence checks.  ``replay_payload`` is
    optional (absent -> None): a verified-admission consumer treats a FITS route lacking it as UNVERIFIED, never admitted.

    The convenience ``readiness_tier`` field is NOT trusted -- it is a derived redundant field on the wire, and
    ``RankedRouteSummary`` does not even accept it as a constructor argument (``readiness_tier`` is a ``@property``).
    A payload whose carried ``readiness_tier`` disagrees with ``readiness``'s own ``.tier`` is refused here, at the
    seam, rather than silently discarded -- a mismatch means SOMETHING in the payload was hand-edited."""
    readiness = _route_readiness_from_payload(payload["readiness"])
    if payload["readiness_tier"] != readiness.tier:
        raise ValueError(
            f"ranked route summary readiness_tier {payload['readiness_tier']!r} disagrees with its own carried "
            f"readiness ladder (which derives to {readiness.tier!r}); refused"
        )
    return RankedRouteSummary(
        payload["schema_version"],
        payload["route_digest"],
        payload["equation"],
        payload["fit_status"],
        readiness,
        tuple(payload["exclusions"]),
        tuple(payload["gaps"]),
        payload["composability_verdict"],
        payload["selectivity_verdict"],
        payload["feasibility_verdict"],
        payload["equilibrium_verdict"],
        payload["kinetics_verdict"],
        tuple(_process_requirements_from_payload(p) for p in payload["process_requirements"]),
        replay_payload=payload.get("replay_payload"),
    )


def ranked_dag_summary_to_payload(summary: RankedDAGSummary, *, include_replay: bool = False) -> dict:
    """A canonical JSON-ready dict for one convergent-DAG COMBINED bench admission (DAG-BENCH-01).

    ``include_replay`` (default False) controls emission of the ONLOAD-REDERIVE thick ``replay_payload`` -- off by
    default so a response is byte-identical to the pre-item-2 form (compare=False, outside the digest)."""
    payload = {
        "schema_version": summary.schema_version,
        "route_digest": summary.route_digest,
        "equation": summary.equation,
        "fit_status": summary.fit_status,
        "exclusions": list(summary.exclusions),
        "gaps": list(summary.gaps),
        "process_requirements": [_process_requirements_to_payload(r) for r in summary.process_requirements],
        "edges": [[a, b] for a, b in summary.edges],
        "composability_verdict": summary.composability_verdict,
        "selectivity_verdict": summary.selectivity_verdict,
        "feasibility_verdict": summary.feasibility_verdict,
        "equilibrium_verdict": summary.equilibrium_verdict,
        "kinetics_verdict": summary.kinetics_verdict,
        "serial_holds": [[i, j, minutes] for i, j, minutes in summary.serial_holds],
    }
    if include_replay and summary.replay_payload is not None:
        payload["replay_payload"] = summary.replay_payload
    return payload


def _exact_int_pair(pair) -> "tuple[int, int]":
    """An ``[i, j]`` edge as an exact-int 2-tuple, validating wire types BEFORE coercion so a bool/float/str index
    (``[true, 1.9]``, ``["1", "2"]``) is REFUSED rather than silently coerced (the edges int-coercion trap)."""
    if type(pair) not in (list, tuple) or len(pair) != 2:
        raise TypeError("each edge must be an [i, j] pair")
    a, b = pair
    if isinstance(a, bool) or isinstance(b, bool) or type(a) is not int or type(b) is not int:
        raise TypeError("edge indices must be exact ints (not bool/float/str)")
    return (a, b)


def ranked_dag_summary_from_payload(payload: dict) -> RankedDAGSummary:
    """Reconstruct a DAG combined bench admission; re-validates via its __post_init__ (edge-shape + coherence) guards.
    ``edges`` wire types are validated BEFORE coercion (:func:`_exact_int_pair`), so a bool/float/string index cannot
    be silently truncated into a legal-looking edge.  ``replay_payload`` is optional (absent -> None)."""
    return RankedDAGSummary(
        payload["schema_version"],
        payload["route_digest"],
        payload["equation"],
        payload["fit_status"],
        tuple(payload["exclusions"]),
        tuple(payload["gaps"]),
        tuple(_process_requirements_from_payload(p) for p in payload["process_requirements"]),
        tuple(_exact_int_pair(e) for e in payload["edges"]),
        payload["composability_verdict"],
        payload["selectivity_verdict"],
        payload["feasibility_verdict"],
        payload["equilibrium_verdict"],
        payload["kinetics_verdict"],
        # serial_holds is optional for backward tolerance; coerce back to (int,int,float) triples (the shape
        # guard rejects a list, so the round-trip is exact).  Absent -> () (a pre-2b payload had no holds field).
        tuple((int(i), int(j), float(m)) for i, j, m in payload.get("serial_holds", [])),
        replay_payload=payload.get("replay_payload"),
    )


def affordability_entry_to_payload(entry) -> dict:
    """A canonical JSON-ready dict for one affordability-frontier entry (COST-VEC-01).  The CostVector is flattened
    inline; a ``None`` axis stays ``null`` (UNKNOWN), never a fabricated 0."""
    v = entry.cost_vector
    return {
        "schema_version": entry.schema_version,
        "route_digest": entry.route_digest,
        "cost_vector": {
            "cash": v.cash,
            "cash_floor": v.cash_floor,
            "access_difficulty": v.access_difficulty,
            "evidence_tier_rank": v.evidence_tier_rank,
            "new_equipment": v.new_equipment,
            "material_quantity": v.material_quantity,
            "energy": v.energy,
            "labor_time": v.labor_time,
            "preprocessing": v.preprocessing,
            "analytical": v.analytical,
            "waste_disposal": v.waste_disposal,
            "hard_blockers": list(v.hard_blockers),
            "fiction_blockers": list(v.fiction_blockers),
            "currency": v.currency,
            "unit": v.unit,
            "region": v.region,
        },
    }


def affordability_entry_from_payload(payload: dict):
    """Reconstruct an affordability-frontier entry; re-validates via its (and the CostVector's) __post_init__.
    ``hard_blockers`` and ``fiction_blockers`` are coerced back to tuples -- the CostVector guard rejects a list, so
    the round-trip is exact; ``fiction_blockers`` reads via ``.get`` so a pre-DISPOSITION-01 payload still revives."""
    from .experiment.affordability import AffordabilityFrontierEntry, CostVector
    cv = payload["cost_vector"]
    return AffordabilityFrontierEntry(
        payload["schema_version"],
        payload["route_digest"],
        CostVector(
            cash=cv["cash"],
            cash_floor=cv["cash_floor"],
            access_difficulty=cv["access_difficulty"],
            evidence_tier_rank=cv["evidence_tier_rank"],
            new_equipment=cv["new_equipment"],
            material_quantity=cv["material_quantity"],
            energy=cv["energy"],
            labor_time=cv["labor_time"],
            preprocessing=cv["preprocessing"],
            analytical=cv["analytical"],
            waste_disposal=cv["waste_disposal"],
            hard_blockers=tuple(cv["hard_blockers"]),
            fiction_blockers=tuple(cv.get("fiction_blockers", ())),
            currency=cv["currency"],
            unit=cv["unit"],
            region=cv["region"],
        ),
    )


def provider_snapshot_to_payload(snap) -> dict:
    """A canonical JSON-ready dict for one dated provider snapshot (SNAPSHOT-13.2)."""
    return {
        "schema_version": snap.schema_version,
        "provider_ids": list(snap.provider_ids),
        "record_count": snap.record_count,
        "content_digest": snap.content_digest,
        "fetched_at": snap.fetched_at,
        "allow_network": snap.allow_network,
    }


def provider_snapshot_from_payload(payload: dict):
    """Reconstruct a provider snapshot; re-validates via its __post_init__.  ``provider_ids`` is coerced back to a
    tuple (the guard rejects a list), so the round-trip is exact."""
    from .data.provider_snapshot import ProviderSnapshot
    return ProviderSnapshot(
        payload["schema_version"],
        tuple(payload["provider_ids"]),
        payload["record_count"],
        payload["content_digest"],
        payload["fetched_at"],
        payload["allow_network"],
    )


# -- COMBINED-VERDICT-AUTH: an optional producer signature over the response identity ----------------------------
#
# ``response_from_payload`` already RE-DERIVES process admission on load (PROCESS-ADMIT-01), but that binds only the
# PROCESS axis, and every other self-declared field is trusted from a payload anyone can mint.  A producer signature
# closes the OUT-OF-BAND tamper: the producer signs ``result_digest`` -- a content hash that transitively covers every
# ranked route's ``fit_status``/``process_requirements``/``exclusions``/``gaps`` (see ``result_digest``) -- with a secret
# key; a consumer holding the same key verifies it and REFUSES a payload whose bytes were altered without the key.
#
# HONEST SCOPE -- what a signature can and cannot do:
#   * CLOSES: an attacker WITHOUT the key who edits a serialized response (relabel a route's ``fit_status`` to FITS, swap
#     the admissible list, even coherently recompute ``result_digest``) -- the HMAC no longer matches, so verification
#     with ``require_signature`` raises.  This is the transport/storage-tamper threat.
#   * DOES NOT CLOSE: a controlling forger who runs code INSIDE the producing process (or holds the key) can always
#     construct-then-sign a lie -- a signature proves "these bytes came from a key-holder, unmodified", NEVER "this
#     verdict was honestly derived".  That residual (test_admission_residual_needs_a_signature_to_close) is not closable
#     by ANY signature; it would need an independent re-derivation service the thin projection deliberately omits.
#   * It is a SYMMETRIC, same-owner tag: it does not defend against an attacker who can read the key.
#
# Signing is strictly OPT-IN: with no key the payload is byte-identical to the unsigned form (``producer_signature`` is
# ``null``), so every existing caller and golden fixture is unchanged.

_PRODUCER_KEY_ENV = "SMARTCHEM_PRODUCER_KEY"
_PRODUCER_KEY_PATH = Path.home() / ".smartchem" / "producer.key"
_PRODUCER_KEY_MIN_BYTES = 16


def resolve_producer_key(*, create: bool = False) -> bytes | None:
    """The local producer key for signing/verifying responses, or ``None`` when unavailable.

    Resolution order: the ``SMARTCHEM_PRODUCER_KEY`` env var (hex-encoded), then a ``~/.smartchem/producer.key``
    keyfile (raw bytes).  With ``create=True`` a fresh 32-byte key is written to the keyfile (mode ``0600``) if none
    exists -- the zero-config path for a same-machine producer/consumer.  Returns ``None`` for a missing key (never
    raises), so an unsigned default stays the graceful, explicit fallback rather than a crash; it raises only for a
    malformed env value, which is an operator error worth surfacing loudly.
    """
    env = os.environ.get(_PRODUCER_KEY_ENV)
    if env:
        try:
            key = bytes.fromhex(env.strip())
        except ValueError as exc:
            raise ValueError(f"{_PRODUCER_KEY_ENV} must be hex-encoded") from exc
        if len(key) < _PRODUCER_KEY_MIN_BYTES:
            raise ValueError(f"{_PRODUCER_KEY_ENV} must decode to at least {_PRODUCER_KEY_MIN_BYTES} bytes")
        return key
    if _PRODUCER_KEY_PATH.exists():
        return _PRODUCER_KEY_PATH.read_bytes()
    if create:
        _PRODUCER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        _PRODUCER_KEY_PATH.write_bytes(key)
        _PRODUCER_KEY_PATH.chmod(0o600)
        return key
    return None


def _sign_result_digest(result_digest: str, key: bytes) -> str:
    """The producer signature: an HMAC-SHA256 over the response's ``result_digest`` (hex).

    ``result_digest`` transitively covers every admission-bearing field, so signing it authenticates the whole
    admissible verdict without carrying the heavy ExperimentRoute graph the thin projection omits.
    """
    return hmac.new(key, result_digest.encode("utf-8"), hashlib.sha256).hexdigest()


def _check_verified_admission(response: "CompilationResponse") -> None:
    """ONLOAD-REDERIVE (item 2): the STRUCTURAL close of the composability + physical + ranking axes, with NO key.

    For every ADMITTED (FITS) route/DAG dossier, RECONSTRUCT the exact route/DAG from its thick ``replay_payload``,
    re-PROJECT it through the SAME producer path (``rank_routes`` -> ``RankedRouteSummary.of_fit``; ``RankedDAGSummary.of_dag``)
    under the response's OWN eval-context, and require the re-projected summary to EQUAL the claimed one.  That single
    equality subsumes every binding this round adds:

    * ``reconstruct(payload).digest == route_digest`` -- the ROUTE-BINDING invariant (route_digest is a compared field
      of the summary), closing the evidence-SUBSTITUTION hole: another route's genuinely-FITS payload under a different
      route_digest re-projects to a summary with a different route_digest, so the equality fails.
    * ``fit_status`` == the freshly re-folded COMBINED verdict (composability + physical box + process), closing the
      bare-relabel hole the process-only re-derivation left open.
    * the ``composability_verdict`` and the four ranking verdicts (selectivity/feasibility/equilibrium/kinetics), plus
      the per-step ``process_requirements`` and (DAG) ``edges`` projection -- all re-derived and compared, closing the
      ranking-fabrication gap.

    A FITS dossier with NO ``replay_payload`` is UNVERIFIED and REFUSED (fail-CLOSED), so stripping the payload (the
    deletion door) cannot admit a bare-relabel.

    HONEST SCOPE (do NOT overclaim -- the residuals are two, not one):
    * This re-derives every axis AGAINST THE RESPONSE'S OWN DECLARED CONTEXT -- the bench box built from
      ``response.request.constraints`` (bounds + process), the ``identity_losses`` from the IR, and ``DEFAULT_STABILITY``
      (the service never injects an extended table).  It authenticates that the verdicts are COHERENT with the routes
      UNDER THAT CONTEXT; it does NOT authenticate the CONTEXT itself.  A keyless attacker who RELAXES the request in the
      payload (e.g. drops a bench temperature cap) and recomputes the free public ``result_digest`` makes a genuinely
      out-of-bounds route re-derive FITS against the relaxed box -- a false ACCEPT this check does NOT catch on its own
      (evil-morty Finding 1, VERIFIED).  Closing it needs the request BOUND: pass ``expected_request_digest`` to
      :func:`response_from_payload` (the consumer pins their own request's ``semantic_digest``), or a ``verification_key``
      (the request is folded into ``result_digest``, so the HMAC breaks on relaxation).  A producer that judged against a
      caller-injected extended stability table or an inventory box the request does not carry is likewise out of scope.
    * A key-holding forger stays irreducible (as for the process axis / the signature -- unchanged).
    This is structural (no key) coherence between the verdicts and the routes; it COMPLEMENTS, never replaces, the
    request-binding and the producer signature.  Scoped to FITS dossiers: item 2 closes admit-bad, not hide-good (a
    conservative FITS->EXCLUDED relabel is a suppression, not an admission, and is out of scope).  For a DAG it also
    re-derives ``serial_holds`` (digest-excluded disclosure) and refuses a tampered hold value, closing that R19
    disclosure-integrity gap for a verified-admission consumer.  Pinned by tests/test_onload_rederivation.py.
    """
    from .experiment.drafter import ConstraintBox, rank_routes
    box = ConstraintBox.of_bounds(response.request.constraints.bounds,
                                  process=response.request.constraints.process)
    losses = response.identity_losses
    for r in response.ranked_route_dossiers:
        if r.fit_status != "FITS":
            continue
        if r.replay_payload is None:
            raise ValueError(
                f"verified admission: FITS route {r.route_digest} carries no replay_payload -- UNVERIFIED "
                f"(a stripped or never-attached payload cannot be admitted; the producer must serialize with "
                f"include_replay=True)"
            )
        route = _reconstruct_route(r.replay_payload)
        resummary = RankedRouteSummary.of_fit(rank_routes((route,), box=box, losses=losses)[0], identity_losses=losses)
        if resummary != r:
            raise ValueError(
                f"verified admission: route {r.route_digest} re-projects to a DIFFERENT summary than declared -- the "
                f"replay evidence does not support the claimed verdict (a forged verdict, substituted evidence, or "
                f"tampered ranking); refused"
            )
    for d in response.ranked_dag_dossiers:
        if d.fit_status != "FITS":
            continue
        if d.replay_payload is None:
            raise ValueError(
                f"verified admission: FITS DAG {d.route_digest} carries no replay_payload -- UNVERIFIED"
            )
        dag = _reconstruct_dag(d.replay_payload)
        resummary = RankedDAGSummary.of_dag(dag, box)
        # resummary != d compares the compare=True fields (verdict + edges + verdicts); serial_holds is compare=False
        # (disclosure), so re-derive it explicitly -- a verified-admission consumer trusting a displayed hold gets an
        # authenticated one (evil-morty Finding 2).
        if resummary != d or resummary.serial_holds != d.serial_holds:
            raise ValueError(
                f"verified admission: DAG {d.route_digest} re-projects to a DIFFERENT summary than declared -- the "
                f"replay evidence does not support the claimed verdict or serial-hold disclosure; refused"
            )


def response_to_payload(response: CompilationResponse, *, signing_key: bytes | None = None,
                        include_replay: bool = False) -> dict:
    """A canonical JSON-ready dict for a response (CLI-JSON-01 leans on this).

    When ``signing_key`` is given, ``producer_signature`` carries an HMAC-SHA256 over ``result_digest``
    (COMBINED-VERDICT-AUTH); with no key it is ``null`` and the payload is byte-identical to the unsigned form.

    ``include_replay`` (ONLOAD-REDERIVE, item 2; default False) emits each dossier's thick ``replay_payload`` so a
    verified-admission consumer can reconstruct and re-derive every axis on load.  OFF by default: the replay payload
    is ``compare=False`` (outside ``result_digest``), so an ordinary response stays byte-identical to the pre-item-2
    form and existing goldens are unchanged.  A producer serving a verified-admission consumer passes True.
    """
    digest = response.result_digest
    return {
        "schema_version": response.schema_version,
        "request": request_to_payload(response.request),
        "outcome": response.outcome.value,
        "standard_status": response.standard_status,
        "exit_code": response.exit_code,
        "compilation_ir": None if response.compilation_ir is None else ir_to_payload(response.compilation_ir),
        "diagnostics": list(response.diagnostics),
        "parse_receipt_summary": response.parse_receipt_summary,
        "search_space_status": response.search_space_status,
        "process_selection_status": response.process_selection_status,
        "admissible_route_digests": list(response.admissible_route_digests),
        "ranked_route_dossiers": [ranked_summary_to_payload(r, include_replay=include_replay)
                                  for r in response.ranked_route_dossiers],
        "ranked_dag_dossiers": [ranked_dag_summary_to_payload(d, include_replay=include_replay)
                                for d in response.ranked_dag_dossiers],
        "affordability_frontier": [affordability_entry_to_payload(e) for e in response.affordability_frontier],
        "provider_snapshots": [provider_snapshot_to_payload(s) for s in response.provider_snapshots],
        "result_digest": digest,
        "producer_signature": None if signing_key is None else _sign_result_digest(digest, signing_key),
    }


def response_from_payload(payload: dict, *, verification_key: bytes | None = None,
                          require_signature: bool = False,
                          require_verified_admission: bool = False,
                          expected_request_digest: str | None = None) -> CompilationResponse:
    """Reconstruct a response from :func:`response_to_payload`; re-runs the coherence guard.

    Two layers now guard admission on load.  (1) The round-trip check below re-derives
    ``process_selection_status``, ``admissible_route_digests``, ``exit_code`` and ``result_digest``
    and REFUSES a payload whose stored values disagree -- catching an INCONSISTENT edit (e.g. an
    admissible list edited without editing the ``fit_status`` it derives from) and, via the
    ``__post_init__`` guard, a non-member or duplicate route digest.  (2) PROCESS-ADMIT-01: each
    ranked route now carries its per-step ``process_requirements``, so the ``__post_init__`` guard
    (:meth:`CompilationResponse._check_process_admission_coherence`) RE-DERIVES the process fit from
    that evidence via :func:`evaluate_process_requirements` and refuses a ``FITS``/``UNKNOWN`` whose
    PROCESS evidence cannot support it.  This closes the LOCKSTEP forgery ON THE PROCESS AXIS -- relabel a
    route that is process-``UNKNOWN``/``EXCLUDED`` to ``FITS`` and recompute the derived fields -- because
    the carried requirements still re-derive to the stricter PROCESS verdict.  (2b) v0.8 M10:
    :meth:`CompilationResponse._check_readiness_coherence` runs right after the algebra-rebind check, UNCONDITIONALLY
    (not gated on ``fit_status`` or ``require_verified_admission`` -- readiness is orthogonal to bench-fit), and
    RE-DERIVES each ranked route's typed Sec 3/4/8 readiness ladder from its thick ``replay_payload`` (when carried)
    via :func:`~smartchem.experiment.readiness.evaluate_route`, refusing a carried ``readiness`` that disagrees with
    the re-derivation. Advisory (unenforceable) on a replay-absent (thin) route, the same boundary the frontier's
    catalyst/fiction channels carry below.  (3) TAMPER-HARDENING-01:
    :meth:`CompilationResponse._check_frontier_coherence` runs at the END of every load (after any verified-admission
    pass) and re-derives each affordability_frontier entry's DISPOSITION blockers (the frontier is EXCLUDED from
    ``result_digest``, so this is the only guard on it).  It FULLY closes the process-exclusion ``hard_blockers`` strip
    on EVERY transport (that channel needs no replay), and the CATALYST/FICTION strip on the THICK transport
    (``include_replay=True``, digest-bound via KILL 1).  Under ``require_verified_admission`` the thin transport is
    ALSO closed: a frontier entry with no ``replay_payload`` is UNVERIFIED and REFUSED (replay-MANDATORY-for-
    disposition-claims), fail-closed exactly as a FITS route with no replay is.  A bare (non-verified) load keeps the
    thin catalyst/fiction dispositions ADVISORY (see the BOUNDARY on ``_check_frontier_coherence``).
    RESIDUAL WITHOUT A SIGNATURE (two parts, both closed by COMBINED-VERDICT-AUTH's ``verification_key`` path below):
    (a) ``fit_status`` is the COMBINED verdict, and its OTHER two components -- composability and the
    physical/reagent/equipment box -- are NOT re-derived (they carry only free-text ``exclusions``/``gaps``,
    and re-deriving them needs the per-step physical conditions and the full ExperimentRoute graph the thin
    projection omits), so a route EXCLUDED for a NON-process reason can still be bare-relabeled to ``FITS``.
    (b) even on the process axis, the evidence is not cryptographically bound to the route STRUCTURE, so a
    fully controlling forger who ALSO fabricates coherent lenient ``process_requirements`` and recomputes
    ``result_digest`` can still mint a FITS.
    COMBINED-VERDICT-AUTH: pass a ``verification_key`` to check the payload's ``producer_signature`` (an HMAC over the
    RECONSTRUCTED ``result_digest``); an OUT-OF-BAND tamper by an attacker WITHOUT the key -- including a coherent one
    that recomputes ``result_digest`` -- is then refused, closing (a) and the keyless part of (b).  With
    ``require_signature`` an unsigned payload is itself refused.  What NO signature can close (see the honest-scope
    note above the signing helpers) is a controlling forger who runs code inside the producing process or holds the
    key -- test_key_holding_forger_residual_is_not_closable_by_a_signature pins that irreducible residual.  With no key
    the signature is not checked (an unsigned response stays producer-declared, as before).  Boundary pins:
    tests/test_process_service.py (test_deserialized_admission_is_re_derived_not_blindly_trusted +
    test_non_process_axis_relabel_is_not_yet_authenticated + test_signed_response_rejects_out_of_band_tamper).
    """
    if require_signature and verification_key is None:
        raise ValueError("require_signature needs a verification_key")
    ir_payload = payload["compilation_ir"]
    response = CompilationResponse(
        payload["schema_version"],
        request_from_payload(payload["request"]),
        ResponseOutcome(payload["outcome"]),
        payload["standard_status"],
        None if ir_payload is None else ir_from_payload(ir_payload),
        tuple(payload["diagnostics"]),
        tuple(ranked_summary_from_payload(r) for r in payload["ranked_route_dossiers"]),
        tuple(affordability_entry_from_payload(e) for e in payload["affordability_frontier"]),
        tuple(provider_snapshot_from_payload(s) for s in payload.get("provider_snapshots", [])),
        parse_receipt_summary=payload["parse_receipt_summary"],
        ranked_dag_dossiers=tuple(
            ranked_dag_summary_from_payload(d) for d in payload.get("ranked_dag_dossiers", [])
        ),
    )
    for name in ("process_selection_status", "admissible_route_digests", "exit_code", "result_digest"):
        expected = list(response.admissible_route_digests) if name == "admissible_route_digests" else getattr(response, name)
        if payload[name] != expected:
            raise ValueError(f"{name} does not match the reconstructed response")
    # ALGEBRA-REBIND-ON-LOAD (0.7 Round III): the runtime binding invariant (see the BINDING INVARIANT in
    # _run_recompile) proves a search ran under the SELECTED algebra at PRODUCE time, but a transported response
    # independently deserializes its request, its IR registry digest, and its search-receipt digest.  Re-derive the
    # coherence on LOAD: for a RECOMPILE response carrying an IR, the algebra the REQUEST names must equal the algebra
    # the RECEIPT says ran.  ChemicalCompilationIR.__post_init__ already forces ir.transform_registry_digest ==
    # search_receipt.transform_registry_digest (those two can't disagree with each other); the MISSING leg -- closed
    # here -- is that both equal search_algebra_digest(topology, resolve(request.algebra_profile)).  This is internal
    # semantic coherence (a search under profile A cannot be LOADED as profile B), NOT cryptographic authentication --
    # a fully controlling forger who rebuilds a self-consistent response is a different threat model, handled by the
    # producer_signature / expected_request_digest paths above.  (DECOMPILE responses are pinned to the legacy default
    # and go through a formula descent with no topology, so this route/DAG check does not apply to them.)
    if (response.request.operation is CompilationOperation.RECOMPILE
            and response.compilation_ir is not None
            and response.request.transform_grammar in _GRAMMAR_TO_MODE):
        _topology = _GRAMMAR_TO_MODE_TOPOLOGY[_GRAMMAR_TO_MODE[response.request.transform_grammar]]
        _expected_algebra_digest = search_algebra_digest(
            _topology, resolve_algebra_profile(response.request.algebra_profile)
        )
        _ir = response.compilation_ir
        if (_ir.transform_registry_digest != _expected_algebra_digest
                or _ir.search_receipt.transform_registry_digest != _expected_algebra_digest):
            raise ValueError(
                "algebra-rebind mismatch on load: the response's IR / search-receipt transform-registry digest "
                "does not match the algebra its request selects (a search under one algebra cannot be loaded as "
                "another; the request, the IR digest, and the receipt digest disagree)"
            )
    # v0.8 Real Route Dossiers, M10: the readiness-ladder deserialization trust-boundary close.  Same seam as
    # PROCESS-ADMIT-01 and the algebra-rebind check just above -- UNCONDITIONAL (not gated on require_verified_admission
    # or fit_status; see the method docstring for why) -- re-derives every ranked route's typed readiness from its
    # thick replay evidence (when carried) and refuses a claim the re-derivation cannot support.
    response._check_readiness_coherence()
    if verification_key is not None:
        signature = payload.get("producer_signature")
        if signature is None:
            if require_signature:
                raise ValueError("producer_signature is required but the payload is unsigned")
        elif not hmac.compare_digest(str(signature), _sign_result_digest(response.result_digest, verification_key)):
            raise ValueError("producer_signature does not verify: the payload was tampered or signed by another key")
    # ONLOAD-REDERIVE (item 2): bind the REQUEST the re-derivation trusts.  The verified-admission re-derivation uses
    # the response's OWN request as the bench box; a keyless attacker who relaxes that request (and recomputes the free
    # public result_digest) could otherwise re-derive an out-of-bounds route to FITS (evil-morty Finding 1).  A consumer
    # who knows their request pins it here (its semantic_digest); a mismatch means the response answers a DIFFERENT
    # question than was asked.  Independent of verified-admission (useful in any mode); a verification_key closes the
    # same gap cryptographically (the request is folded into result_digest).
    if expected_request_digest is not None and response.request.semantic_digest != expected_request_digest:
        raise ValueError(
            "response.request does not match expected_request_digest: the response answers a DIFFERENT request than "
            "the consumer asked for (e.g. relaxed bench bounds); refused"
        )
    # The opt-in STRUCTURAL close of the composability/physical/ranking axes (no key).  A verified-admission consumer
    # requires every FITS route/DAG to carry a replay_payload that re-projects to the exact claimed summary; a missing
    # payload is fail-closed (UNVERIFIED).  Off by default -> pre-item-2 behaviour.  NOTE the honest scope in
    # _check_verified_admission: this authenticates verdict<->route COHERENCE under the response's declared context, not
    # the context itself -- pass expected_request_digest (above) or a verification_key to bind the request too.
    if require_verified_admission:
        _check_verified_admission(response)
    # TAMPER-HARDENING-01: the R59 disposition serialized-tamper close.  RUN ON EVERY LOAD (not gated on
    # require_verified_admission) and AFTER _check_verified_admission, so a FITS-route evidence substitution keeps that
    # check's route-binding message while this one covers the NON-FITS frontier tampers (a REAL_BUT_HARD / NOT_A_REACTION
    # entry whose blockers were stripped to forge a better disposition).  It lives here, at the deserialization seam,
    # rather than in __post_init__ because -- like _check_verified_admission -- it reconstructs routes from the replay
    # payload, which is a load-time authority, not an in-memory-construction invariant.
    response._check_frontier_coherence(require_verified_admission=require_verified_admission)
    return response


def serialize_response(response: CompilationResponse, *, signing_key: bytes | None = None,
                       include_replay: bool = False) -> str:
    return json.dumps(response_to_payload(response, signing_key=signing_key, include_replay=include_replay),
                      ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def deserialize_response(text: str, *, verification_key: bytes | None = None,
                         require_signature: bool = False,
                         require_verified_admission: bool = False,
                         expected_request_digest: str | None = None) -> CompilationResponse:
    return response_from_payload(json.loads(text), verification_key=verification_key,
                                 require_signature=require_signature,
                                 require_verified_admission=require_verified_admission,
                                 expected_request_digest=expected_request_digest)


# -- the versioned JSON schema + the semantic-field projection (CLI-JSON-01) -------------------------------------


def response_schema() -> dict:
    """A versioned, introspectable descriptor of the ``--json`` response SHAPE (standard 14.3).

    It names every field and its type at each nesting level, plus the three schema versions the payload carries.
    It DELIBERATELY excludes the derived digests (they are values, not schema), so it changes only when a field is
    added/removed/renamed -- which is exactly what a golden pin should force to be intentional (CLI-JSON-01).  A
    test cross-checks these field names against a REAL payload so the descriptor can never silently drift from what
    :func:`response_to_payload` actually emits.
    """
    return {
        "descriptor_version": COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR,
        "response_schema_version": COMPILATION_RESPONSE_SCHEMA,
        "request_schema_version": COMPILATION_REQUEST_SCHEMA,
        "response_fields": {
            "schema_version": "str",
            "request": "object(compilation-request-v1alpha5)",
            "outcome": "enum(ResponseOutcome)",
            "standard_status": "str|null (section 8.2 status)",
            "exit_code": "int (section 14.4: 0/2/3/4/5/70)",
            "compilation_ir": "object(chemical-compilation-ir)|null",
            "diagnostics": "array[str] (blockers)",
            "parse_receipt_summary": "str|null (section 14.2 identity-resolution receipt; provenance)",
            "search_space_status": "str|null (section 8.3 no-route matrix: NO_ROUTE_IN_DECLARED_SPACE/"
                                   "INCOMPLETE_NO_ROUTE_OBSERVED/COMPLETE_CANDIDATE_SET/PARTIAL_CANDIDATE_SET; "
                                   "null when no route search ran)",
            "ranked_route_dossiers": "array[object(ranked-route-summary)] (section-11 fit, best-first; CLI-CAN-02)",
            "ranked_dag_dossiers": "array[object(ranked-dag-summary)] (DAG-BENCH-01: per-DAG COMBINED section-11 bench "
                                   "admission for a convergent (DAG-mode) compile, the process component re-derived on "
                                   "load; empty in routes/decompile mode and on an unconstrained-bench request)",
            "process_selection_status": "enum(NOT_REQUESTED/NOT_REQUIRED/UNASSESSED/NO_FIT_FOUND/FITS_FOUND)",
            "admissible_route_digests": "array[str] (FITS returned candidates under requested process constraints; not bench validation)",
            "affordability_frontier": "array[object(affordability-frontier-entry)] (section-10.4 Pareto frontier "
                                      "over the ranked routes; COST-VEC-01. Empty when no route carries "
                                      "affordability signal -- a known cost axis or a hard blocker)",
            "provider_snapshots": "array[object(provider-snapshot)] (section-13.2 dated provenance of any LIVE "
                                  "provider fetch; SNAPSHOT-13.2. Empty on an offline/default run)",
            "result_digest": "str (sha256)",
            "producer_signature": "str|null (optional HMAC-SHA256 over result_digest; null unless signed; "
                                  "COMBINED-VERDICT-AUTH out-of-band-tamper close)",
        },
        "compilation_ir_fields": {
            "schema_version": "str",
            "tool_version": "str",
            "operation": "enum(CompilationOperation)",
            "target": "object(chemical-identity)",
            "request_digest": "str (sha256)",
            "identity_losses": "array[object(identity-loss)]",
            "terminal_policy_digest": "str (sha256)",
            "transform_registry_digest": "str (sha256)",
            "search_status": "enum(SearchStatus)",
            "standard_status": "str (section 8.2 status)",
            "search_receipt": "object(search-receipt-view) (the full section 8.1 receipt; IR-CHEM-01)",
            "candidates": "array[object(candidate-summary)]",
            "diagnostics": "array[str]",
            "structural_candidates": "array[object(structural-candidate)] (structure-preserving decompile; IR-STRUCT-01)",
        },
        "search_receipt_view_fields": {
            "schema_version": "str",
            "search_kind": "str",
            "status": "enum(SearchStatus)",
            "standard_status": "str (section 8.2 status)",
            "cut_budget_scope": "enum(PER_NODE/GLOBAL)",
            "target_identity_digest": "str|null",
            "terminal_policy_digest": "str|null",
            "transform_registry_digest": "str|null",
            "max_depth": "int|null (null for the formula descent -- no depth bound)",
            "cut_budget": "int|null",
            "candidate_limit": "int|null (null: no engine stops on a distinct emitted-candidate cap)",
            "result_limit": "int|null",
            "nodes_visited": "int|null",
            "transforms_considered": "int|null",
            "candidates_emitted": "int|null (null for the formula descent)",
            "results_returned": "int|null",
            "candidates_rejected_by_reason": "array[[str, int]] (sorted, distinct, positive counts)",
            "cut_enumeration_complete": "bool",
            "candidate_enumeration_complete": "bool",
            "result_limit_saturated": "bool",
            "stop_reason": "str ('' when complete)",
        },
        "chemical_identity_fields": {
            "schema_version": "str",
            "layer": "enum(IdentityLayer)",
            "canonical_repr": "str",
            "identity_digest": "str (sha256)",
        },
        "identity_loss_fields": {
            "schema_version": "str",
            "feature": "str",
            "input_representation": "str",
            "retained_representation": "str",
            "reason": "str",
            "affected_claims": "array[str] (sorted, distinct)",
            "severity": "enum(WARNING/BLOCKER)",
        },
        "candidate_summary_fields": {
            "schema_version": "str",
            "candidate_kind": "enum(FORMULA_EDGE/ROUTE/DAG)",
            "candidate_digest": "str (sha256; the stable route/candidate ID)",
            "equation": "str",
            # This is the IR-side candidate tier -- distinct from the ranked_route_summary_fields readiness below.
            # It stays PINNED to FORMAL_CANDIDATE (an IR CandidateSummary carries no per-step evidence to derive a
            # stronger tier from); the honest, DERIVED ladder lives on the ranked route dossier once a route is built
            # and box-checked, not on the bare formula-edge/route/DAG candidate the IR enumerates.
            "readiness_tier": "str (readiness/epistemic tier; IR CandidateSummary -- always FORMAL_CANDIDATE)",
        },
        "ranked_route_summary_fields": {
            "schema_version": "str",
            "route_digest": "str (sha256; == the matching candidate_digest)",
            "equation": "str",
            "fit_status": "enum(FITS/EXCLUDED/UNKNOWN/UNCONSTRAINED)",
            # v0.8 Real Route Dossiers: DERIVED from "readiness" (see below), never a hard floor -- the ladder is
            # FORMAL_CANDIDATE/REACTION_VOUCHED/CONDITIONS_SUPPORTED/PROCESS_SPECIFIED (Sec 4's cumulative,
            # weakest-link tiers). Kept for a thin consumer that wants the coarse tier without decoding the ladder.
            "readiness_tier": "str (enum(FORMAL_CANDIDATE/REACTION_VOUCHED/CONDITIONS_SUPPORTED/PROCESS_SPECIFIED); "
                              "DERIVED -- see readiness, the source of truth)",
            "readiness": "object(RouteReadiness: per_step + route_open_obligations -- the typed Sec 3/4/8 obligation "
                        "ladder this route's readiness_tier is projected from; RE-DERIVED on load from the thick "
                        "replay_payload when present)",
            "exclusions": "array[str] (hard section-11 over/under-bounds)",
            "gaps": "array[str] (undeclared constrained dimensions / composability UNKNOWNs)",
            "composability_verdict": "str",
            "selectivity_verdict": "str",
            "feasibility_verdict": "str",
            "equilibrium_verdict": "str",
            "kinetics_verdict": "str (ranking-only; NEVER a grade)",
            "process_requirements": "array[object(per-step declared process facts)|null] (PROCESS-ADMIT-01: the "
                                    "evidence process admission is RE-DERIVED from on load, one entry per route step "
                                    "in order, null for an undeclared step; part of route identity)",
        },
        "ranked_dag_summary_fields": {
            "schema_version": "str",
            "route_digest": "str (sha256; == the matching DAG candidate_digest)",
            "equation": "str",
            "fit_status": "enum(FITS/EXCLUDED/UNKNOWN/UNCONSTRAINED) (DAG-BENCH-01: the COMBINED section-11 verdict -- "
                          "composability + physical box + process -- the SAME combined fit a linear route carries; only "
                          "the PROCESS component is re-derived on load)",
            "exclusions": "array[str] (hard composability/physical/process over/under-bounds)",
            "gaps": "array[str] (undeclared constrained composability/physical/process dimensions)",
            "process_requirements": "array[object(per-step declared process facts)|null] (DAG-BENCH-01: the PROCESS "
                                    "component is re-derived on load via evaluate_dag_process_requirements, one entry "
                                    "per DAG step in the DAG's own order, null for an undeclared step; part of identity)",
            "edges": "array[[int, int]] (producer->consumer step-index pairs -- the DAG topology the critical-path "
                     "elapsed aggregation re-derives against; shape-validated on load)",
            "composability_verdict": "str (DAG-THERMO-01: worst-edge E1 composability verdict)",
            "selectivity_verdict": "str (DAG-THERMO-01: worst-node sourced selectivity)",
            "feasibility_verdict": "str (DAG-THERMO-01: worst-node thermodynamic feasibility)",
            "equilibrium_verdict": "str (DAG-THERMO-01: worst-node equilibrium extent)",
            "kinetics_verdict": "str (DAG-THERMO-01: worst-node rate regime; ranking-only, NEVER a grade)",
            "serial_holds": "array[[int, int, number]] (item 2b: the DAG-HOLD-01 serial-schedule hold as "
                            "(producer, consumer, hold_minutes) triples over the edges that hold; DISCLOSURE only "
                            "-- never changes fit_status -- and digest-EXCLUDED, so it is re-derivable from "
                            "edges + process_requirements and does not move the route identity)",
        },
        "affordability_frontier_entry_fields": {
            "schema_version": "str",
            "route_digest": "str (sha256; == the matching ranked_route_dossiers.route_digest)",
            "cost_vector": "object(cost-vector): 10 minimized section-10.4 axes (cash/access_difficulty/"
                           "evidence_tier_rank/new_equipment/material_quantity/energy/labor_time/preprocessing/"
                           "analytical/waste_disposal), each number|null (UNKNOWN); cash_floor number|null (an honest "
                           "partial-basket LOWER BOUND when the exact cash is UNKNOWN, mutually exclusive with cash -- "
                           "COST-VEC-01-coupled); hard_blockers array[str] (REAL-BUT-HARD constraints -- disposition "
                           "tier REAL_BUT_HARD); fiction_blockers array[str] (Problem-A not-a-reaction fictions -- "
                           "disposition tier NOT_A_REACTION, strictly worse than real-but-hard; DISPOSITION-01); "
                           "currency/unit str (must match for cash comparison); region str",
        },
        "provider_snapshot_fields": {
            "schema_version": "str",
            "provider_ids": "array[str] (the providers consulted in the live fetch)",
            "record_count": "int (records the fetch yielded)",
            "content_digest": "str (sha256; deterministic over the fetched records -- the reproducibility anchor)",
            "fetched_at": "str (ISO-8601 UTC wall-clock; provenance, NOT in result_digest)",
            "allow_network": "bool",
        },
    }


def response_semantic_fields(response: CompilationResponse) -> dict:
    """Project a response onto its SEMANTIC facts -- the standard 14.3 list: identity, receipt, tier, blockers, and
    route IDs, plus the outcome/exit/status the verdict rests on.

    This is the single source both the ``--json`` payload and the human render must AGREE on (CLI-JSON-01's
    acceptance, "human and JSON agree on all semantic fields"): a field present here must be recoverable from the
    JSON and surfaced in the human render, so neither view can silently carry a fact the other drops.
    """
    ir = response.compilation_ir
    return {
        "outcome": response.outcome.value,
        "exit_code": response.exit_code,
        "standard_status": response.standard_status,
        "target_repr": None if ir is None else ir.target.canonical_repr,
        "target_layer": None if ir is None else ir.target.layer.value,
        # the one-line summary strings: the surface both views must AGREE on (CLI-JSON-01). The structured records
        # ride the machine payload (ir_to_payload); the human render prints these same summaries.
        "identity_losses": tuple(response.identity_loss_summaries),
        "blockers": tuple(response.diagnostics),
        # the section-14.2 identity-resolution echo (how the target was READ) -- provenance surfaced in both views
        # (SVC-REQ-01 alias-collapse); distinct from search_receipt_digest (the section-8.1 search receipt).
        "parse_receipt": response.parse_receipt_summary,
        "search_receipt_digest": response.search_receipt_digest,
        # the section-8.3 no-route matrix label -- the surface both views must AGREE on (SRCH-NO-01): the --json
        # payload carries it and every human renderer that ran a search prints it, so an incomplete-empty search is
        # never shown as a complete no-route on one view and hidden on the other.
        "search_space_status": response.search_space_status,
        "candidate_ids": () if ir is None else tuple(c.candidate_digest for c in ir.candidates),
        "candidate_tiers": () if ir is None else tuple(sorted({c.readiness_tier for c in ir.candidates})),
        "result_digest": response.result_digest,
    }
