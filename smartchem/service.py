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
standard's exit codes (section 14.4).  It does NOT yet rewire the live ``argv`` dispatch onto this service
(CLI-CAN-01), populate ranking dossiers or the affordability frontier (READY-TIER-01 / COST-VEC-01), bind
quantitative :class:`~smartchem.experiment.stock.StockMaterial` (STOCK-01), resolve INCHI/FORMULA/name-normalised
targets into the digest (ID-PARSE-01), or turn an uncaught bug into an ``ERROR_INTERNAL`` receipt (the top-level
guarded service).  Each of those is a named follow-on, not a silent gap.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .compilation_ir import (
    ChemicalCompilationIR,
    CompilationOperation,
    _structure_ident,
    decompile_to_ir,
    ir_from_payload,
    ir_to_payload,
    recompile_to_ir,
)
from .contracts import Digestible, canonical_digest
from .identity_parse import IdentityParseError, InputKind, resolve_target
from .search import REFUSED_8_2_STATUSES, STANDARD_8_2_STATUSES

__all__ = [
    "COMPILATION_REQUEST_SCHEMA",
    "COMPILATION_RESPONSE_SCHEMA",
    "FieldOrigin",
    "TransformGrammar",
    "ResponseOutcome",
    "SearchBounds",
    "TerminalPolicy",
    "IdentityPolicy",
    "ConstraintPolicy",
    "RankingPolicy",
    "EvidenceProviderSelection",
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
    "EXIT_SUCCESS",
    "EXIT_INVALID_INPUT",
    "EXIT_NO_ROUTE",
    "EXIT_INCOMPLETE",
    "EXIT_REFUSED",
    "EXIT_INTERNAL",
]

COMPILATION_REQUEST_SCHEMA = "smartchem.service/compilation-request-v1alpha1"
COMPILATION_RESPONSE_SCHEMA = "smartchem.service/compilation-response-v1alpha1"

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
# Each is a frozen, digestible semantic record.  The placeholder members (IdentityPolicy/ConstraintPolicy/
# RankingPolicy/EvidenceProviderSelection) carry the ONE knob that has real meaning at the current build depth and
# default to today's behaviour; they are typed and versionable now so the request shape is stable while the arcs
# they front (ID-LAYER-01, constraints, section 15 ranking, provider selection) are built out behind them.


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
    """Identity-comparison policy (section 5).  Minimal first cut: one id; the full stereo/isotope/salt/mixture
    model is ID-LAYER-01 (TODO)."""

    policy_id: str = "DEFAULT"

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise ValueError("policy_id must be a non-empty string")


@dataclass(frozen=True)
class ConstraintPolicy(Digestible):
    """Constraint box (section 11).  Minimal first cut: ``UNCONSTRAINED`` by default; the typed T/P/selectivity
    box is wired in a later brick."""

    constraint_id: str = "UNCONSTRAINED"

    def __post_init__(self) -> None:
        if not isinstance(self.constraint_id, str) or not self.constraint_id:
            raise ValueError("constraint_id must be a non-empty string")


@dataclass(frozen=True)
class RankingPolicy(Digestible):
    """Ranking precedence (section 15).  Minimal first cut: the default precedence id; the ordering tuple is
    populated when ranked dossiers land (READY-TIER-01)."""

    policy_id: str = "DEFAULT_PRECEDENCE_V1"

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise ValueError("policy_id must be a non-empty string")


@dataclass(frozen=True)
class EvidenceProviderSelection(Digestible):
    """Which evidence/data providers are in play (section 9).  Minimal first cut: an offline-default selection
    id; provider-version sensitivity of the digest is a later concern."""

    selection_id: str = "DEFAULT_OFFLINE"

    def __post_init__(self) -> None:
        if not isinstance(self.selection_id, str) or not self.selection_id:
            raise ValueError("selection_id must be a non-empty string")


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
    """

    schema_version: str
    operation: CompilationOperation
    target_input: str
    input_kind: InputKind
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

    def __post_init__(self) -> None:
        if self.schema_version != COMPILATION_REQUEST_SCHEMA:
            raise ValueError(f"schema_version must be exactly {COMPILATION_REQUEST_SCHEMA!r}")
        if not isinstance(self.operation, CompilationOperation):
            raise TypeError("operation must be a CompilationOperation")
        if not isinstance(self.target_input, str) or not self.target_input.strip():
            raise ValueError("target_input must be a non-empty string")
        if not isinstance(self.input_kind, InputKind):
            raise TypeError("input_kind must be an InputKind")
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
    def semantic_digest(self) -> str:
        """The alias-independent SEARCH identity, with a ONE-WAY guarantee: equal ``semantic_digest`` => the SAME
        search (standard section 13.1).

        It hashes every SEMANTIC field (section 4.1's list) and DELIBERATELY EXCLUDES ``origins`` (provenance) and
        ``output_policy`` (a display choice), so a value reached by default and the same value passed explicitly,
        or a JSON vs human render choice, never split the search identity.  It is deliberately a SUPERSET of what
        the current bounded engine consumes (the placeholder policies and ``input_kind`` on a formula descent are
        hashed but not yet read by :func:`run_compilation`); that can only SPLIT requests, never MERGE two different
        searches, so the one-way law is never violated.  ``stock_materials``/``helper_reagents`` enter as
        frozensets, so bench ORDER is not part of the search identity (matching the IR's terminal-policy discipline).

        BOUNDARY (ID-PARSE-01): the target enters as the raw ``(target_input, input_kind)`` pair, so alias
        equality holds for equal flag values.  Collapsing ``name:paracetamol`` and ``paracetamol`` to one
        normalised identity in this digest requires the unified identity parser to be the single normalisation
        authority and is deferred to ID-PARSE-01; until then this digest keys on the input as typed.
        """
        return canonical_digest(
            (
                "compilation-request-semantic-v1alpha1",
                self.schema_version,
                self.operation,
                self.target_input,
                self.input_kind,
                self.identity_policy,
                self.terminal_policy,
                frozenset(self.stock_materials),
                frozenset(self.helper_reagents),
                self.transform_grammar,
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
    constraints: "ConstraintPolicy | None" = None,
    ranking_policy: "RankingPolicy | None" = None,
    evidence_provider_selection: "EvidenceProviderSelection | None" = None,
    output_policy: "OutputPolicy | None" = None,
) -> CompilationRequest:
    """Build a RECOMPILE request, recording each defaulted knob's origin as ``DEFAULT`` (section 13.1).

    This is the alias-independence engine: ``compile``, ``synthesize`` and ``recompile`` all build their request
    HERE, from ONE default table, so equal explicit flags always resolve to equal values and thus an equal
    :attr:`~CompilationRequest.semantic_digest`.  A value passed explicitly and the same value reached by default
    share the search identity but differ in :attr:`~CompilationRequest.origins`.
    """
    explicit = {
        "input_kind": input_kind is not None,
        "helper_reagents": helper_reagents is not None,
        "stock_materials": stock_materials is not None,
        "commodities_enabled": commodities_enabled is not None,
        "transform_grammar": grammar is not None,
        "max_depth": max_depth is not None,
        "max_routes": max_routes is not None,
        "cut_budget": cut_budget is not None,
        "identity_policy": identity_policy is not None,
        "constraints": constraints is not None,
        "ranking_policy": ranking_policy is not None,
        "evidence_provider_selection": evidence_provider_selection is not None,
        "output_policy": output_policy is not None,
    }
    grammar = grammar if grammar is not None else TransformGrammar.CAPPED_SCISSION_LINEAR
    if grammar not in _RECOMPILE_GRAMMARS:
        raise ValueError("a recompile grammar must be CAPPED_SCISSION_LINEAR or CAPPED_SCISSION_CONVERGENT")
    return CompilationRequest(
        COMPILATION_REQUEST_SCHEMA,
        CompilationOperation.RECOMPILE,
        target_input,
        input_kind if input_kind is not None else InputKind.AUTO,
        identity_policy if identity_policy is not None else IdentityPolicy(),
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
        constraints if constraints is not None else ConstraintPolicy(),
        ranking_policy if ranking_policy is not None else RankingPolicy(),
        output_policy if output_policy is not None else OutputPolicy(),
        _origins(explicit),
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
        "identity_policy": identity_policy is not None,
        "ranking_policy": ranking_policy is not None,
        "evidence_provider_selection": evidence_provider_selection is not None,
        "output_policy": output_policy is not None,
    }
    return CompilationRequest(
        COMPILATION_REQUEST_SCHEMA,
        CompilationOperation.DECOMPILE,
        target_input,
        input_kind if input_kind is not None else InputKind.AUTO,
        identity_policy if identity_policy is not None else IdentityPolicy(),
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
class CompilationResponse:
    """One typed response for either compiler direction (standard section 13.2).

    It wraps the request, the produced :class:`~smartchem.compilation_ir.ChemicalCompilationIR` (the core of the
    section 13.2 fields -- ``normalized_target``, ``identity_losses`` and ``candidates`` read through to it in
    full), a TOTAL :class:`ResponseOutcome`, and the section 8.2 ``standard_status`` where a search ran.  The
    section 13.2 ``search_receipt`` is exposed here only as its DIGEST (:attr:`search_receipt_digest`): the IR
    carries the receipt's digest, not the full ``SearchReceipt`` object, so the mandated receipt CONTENT (per-limit
    counters/flags) is not yet recoverable from the response -- embedding it is a named follow-on.
    ``ranked_route_dossiers`` and ``affordability_frontier`` are section 13.2 fields whose producers are not built
    yet (READY-TIER-01 / COST-VEC-01); they are present and empty rather than absent, so the shape is stable.

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
        if self.ranked_route_dossiers != () or self.affordability_frontier != ():
            raise ValueError(
                "ranked_route_dossiers/affordability_frontier are not populated in this brick "
                "(READY-TIER-01 / COST-VEC-01); they must be empty"
            )
        self._check_outcome_coherence()

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
        return _EXIT_BY_OUTCOME[self.outcome]

    @property
    def normalized_target(self):
        return None if self.compilation_ir is None else self.compilation_ir.target

    @property
    def identity_losses(self) -> tuple[str, ...]:
        return () if self.compilation_ir is None else self.compilation_ir.identity_losses

    @property
    def candidates(self) -> tuple:
        return () if self.compilation_ir is None else self.compilation_ir.candidates

    @property
    def search_receipt_digest(self) -> "str | None":
        return None if self.compilation_ir is None else self.compilation_ir.search_receipt_digest

    @property
    def result_digest(self) -> str:
        """The result identity: a deterministic function of the request's SEARCH identity and the produced IR.

        Because :func:`run_compilation` reads ONLY the request's resolved semantic fields (never its origins or
        output policy), equal :attr:`CompilationRequest.semantic_digest` => equal execution => equal
        ``result_digest``.  That is the "equal result digests across aliases" half of the SVC-REQ-01 acceptance.
        """
        return canonical_digest(
            (
                "compilation-result-v1alpha1",
                self.request.semantic_digest,
                self.outcome,
                self.standard_status or "",
                "" if self.compilation_ir is None else self.compilation_ir.digest,
                self.diagnostics,
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


def _refused(request: CompilationRequest, reason: str) -> CompilationResponse:
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA, request, ResponseOutcome.REFUSED, None, None, (reason,)
    )


def _classify(ir: ChemicalCompilationIR, target_available: bool) -> ResponseOutcome:
    if target_available:
        return ResponseOutcome.TARGET_ALREADY_AVAILABLE
    if not ir.complete_within_bounds:
        return ResponseOutcome.INCOMPLETE
    return ResponseOutcome.ROUTES_FOUND if ir.candidate_count > 0 else ResponseOutcome.NO_ROUTE_COMPLETE


def run_compilation(request: CompilationRequest) -> CompilationResponse:
    """Execute ``request`` and return the typed response, delegating to the existing IR producers.

    Determinism is load-bearing: this reads ONLY the request's resolved semantic fields, so equal
    :attr:`CompilationRequest.semantic_digest` guarantees an equal response (section 13.1, "same semantic digest
    MUST execute the same search").  The outcome maps to the section 14.4 exit codes via :attr:`ResponseOutcome`.
    """
    if type(request) is not CompilationRequest:
        raise TypeError("run_compilation needs a CompilationRequest")
    if request.operation is CompilationOperation.RECOMPILE:
        return _run_recompile(request)
    return _run_decompile(request)


def _run_recompile(request: CompilationRequest) -> CompilationResponse:
    from .structure_descent import ScissionError

    try:
        target = resolve_target(request.target_input, request.input_kind)
        reagents = tuple(resolve_target(s, InputKind.AUTO) for s in request.helper_reagents)
        available = tuple(resolve_target(s, InputKind.AUTO) for s in request.stock_materials)
    except IdentityParseError as exc:
        return _invalid(request, str(exc))

    if request.terminal_policy.commodities_enabled:
        from .data.reagents import commodity_inventory
        commodities = commodity_inventory()
    else:
        commodities = ()

    # Section 7: a target already on the terminal stock terminates before any expansion.  Checked structurally
    # (canonical STRUCTURE identity), never by parsing a diagnostic string -- the same identity the search uses.
    terminal_idents = {_structure_ident(m) for m in (*available, *reagents, *commodities)}
    target_available = _structure_ident(target) in terminal_idents

    mode = _GRAMMAR_TO_MODE[request.transform_grammar]
    try:
        ir = recompile_to_ir(
            target,
            reagents=reagents,
            available=available,
            commodities=commodities,
            max_depth=request.search_bounds.value("max_depth"),
            max_results=request.search_bounds.value("max_results"),
            cut_budget=request.search_bounds.value("cut_budget"),
            mode=mode,
        )
    except ScissionError as exc:  # a ValueError subclass -> caught FIRST: a model-boundary refusal (exit 5)
        return _refused(request, f"refused at the chemistry-model boundary: {exc}")

    outcome = _classify(ir, target_available)
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA, request, outcome, ir.standard_status, ir, tuple(ir.diagnostics)
    )


def _run_decompile(request: CompilationRequest) -> CompilationResponse:
    from .compilation_ir import ChemicalIdentity
    from .decompiler import DecompilerError, Formula

    # This brick reads the decompile target as FORMULA TEXT (the standard's --formula form).  Resolving a
    # NAME/SMILES/InChI target to a formula is CLI-CAN-01 (the decompile argv path); until then a declared
    # non-formula input_kind is REFUSED, never silently treated as a formula -- a silently-discarded kind on a
    # formula-parseable string would ship a WRONG species as a green result (the forbidden confident-wrong answer).
    if request.input_kind not in (InputKind.AUTO, InputKind.FORMULA):
        return _invalid(
            request,
            f"decompile currently reads the target as formula text; input_kind {request.input_kind.value} is not "
            "yet resolved for a formula descent (CLI-CAN-01)",
        )

    try:
        ir = decompile_to_ir(
            request.target_input,
            request.terminal_policy.formula_inventory,
            max_multiplicity=request.search_bounds.value("max_multiplicity"),
            budget=request.search_bounds.value("budget"),
            max_edges=request.search_bounds.value("max_edges"),
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
    target_available = ir.target.identity_digest in inventory_ids
    outcome = _classify(ir, target_available=target_available)
    return CompilationResponse(
        COMPILATION_RESPONSE_SCHEMA, request, outcome, ir.standard_status, ir, tuple(ir.diagnostics)
    )


# -- serialization (the request/response are transportable artifacts: CLI-JSON-01 leans on this) -----------------


def request_to_payload(request: CompilationRequest) -> dict:
    """A canonical JSON-ready dict for a request; ``canonical_digest`` of the round-trip is stable."""
    return {
        "schema_version": request.schema_version,
        "operation": request.operation.value,
        "target_input": request.target_input,
        "input_kind": request.input_kind.value,
        "identity_policy": {"policy_id": request.identity_policy.policy_id},
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
        "constraints": {"constraint_id": request.constraints.constraint_id},
        "ranking_policy": {"policy_id": request.ranking_policy.policy_id},
        "output_policy": {
            "render_mode": request.output_policy.render_mode,
            "quiet": request.output_policy.quiet,
        },
        "origins": [[name, origin.value] for name, origin in request.origins],
    }


def request_from_payload(payload: dict) -> CompilationRequest:
    """Reconstruct a request from :func:`request_to_payload`; re-validates via the frozen records' guards."""
    tp = payload["terminal_policy"]
    return CompilationRequest(
        payload["schema_version"],
        CompilationOperation(payload["operation"]),
        payload["target_input"],
        InputKind(payload["input_kind"]),
        IdentityPolicy(payload["identity_policy"]["policy_id"]),
        TerminalPolicy(
            tp["match_mode"], tp["commodities_enabled"], tuple(tp["formula_inventory"])
        ),
        tuple(payload["stock_materials"]),
        tuple(payload["helper_reagents"]),
        TransformGrammar(payload["transform_grammar"]),
        EvidenceProviderSelection(payload["evidence_provider_selection"]["selection_id"]),
        SearchBounds(tuple((name, value) for name, value in payload["search_bounds"])),
        ConstraintPolicy(payload["constraints"]["constraint_id"]),
        RankingPolicy(payload["ranking_policy"]["policy_id"]),
        OutputPolicy(payload["output_policy"]["render_mode"], payload["output_policy"]["quiet"]),
        tuple((name, FieldOrigin(origin)) for name, origin in payload["origins"]),
    )


def serialize_request(request: CompilationRequest) -> str:
    return json.dumps(request_to_payload(request), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def deserialize_request(text: str) -> CompilationRequest:
    return request_from_payload(json.loads(text))


def response_to_payload(response: CompilationResponse) -> dict:
    """A canonical JSON-ready dict for a response (CLI-JSON-01 leans on this)."""
    return {
        "schema_version": response.schema_version,
        "request": request_to_payload(response.request),
        "outcome": response.outcome.value,
        "standard_status": response.standard_status,
        "exit_code": response.exit_code,
        "compilation_ir": None if response.compilation_ir is None else ir_to_payload(response.compilation_ir),
        "diagnostics": list(response.diagnostics),
        "ranked_route_dossiers": list(response.ranked_route_dossiers),
        "affordability_frontier": list(response.affordability_frontier),
        "result_digest": response.result_digest,
    }


def response_from_payload(payload: dict) -> CompilationResponse:
    """Reconstruct a response from :func:`response_to_payload`; re-validates via the coherence guard."""
    ir_payload = payload["compilation_ir"]
    return CompilationResponse(
        payload["schema_version"],
        request_from_payload(payload["request"]),
        ResponseOutcome(payload["outcome"]),
        payload["standard_status"],
        None if ir_payload is None else ir_from_payload(ir_payload),
        tuple(payload["diagnostics"]),
        tuple(payload["ranked_route_dossiers"]),
        tuple(payload["affordability_frontier"]),
    )


def serialize_response(response: CompilationResponse) -> str:
    return json.dumps(response_to_payload(response), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def deserialize_response(text: str) -> CompilationResponse:
    return response_from_payload(json.loads(text))
