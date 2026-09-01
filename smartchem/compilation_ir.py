"""IR-CHEM-01 (first brick) -- the shared ``ChemicalCompilationIR`` both compiler directions speak.

The standard (section 4.1) requires ONE versioned intermediate representation that ``decompile`` emits and
``recompile`` consumes, so the two operations are views of a single typed artifact rather than two adjacent
search kinds.  This module builds the IR *envelope* and wires the formula decompiler to emit it; the structural
producer, the recompiler's consumption of a serialized artifact, and the full identity/loss records remain
open (IR-LOSS-01, IR-INV-01, ID-LAYER-01), and are named as such.

The one property that makes this an IR and not a display struct (section 4.1, verbatim)
------------------------------------------------------------------------------------------
> The serialized digest MUST change when any semantic input changes, including identity state, transform/evidence
> provider version, terminal policy, search bound, constraint, or evidence grade. Display labels and ordering
> MUST NOT change a semantic digest.

So every field here is a *semantic* fact -- a canonical identity digest, a canonical terminal-policy digest, the
declared search bounds, the search status, and the candidate set in canonical (digest-sorted) order.  No display
label, no presentation order, and no wall-clock enters the value.  Two IRs built from the same semantic request
over the same registry share a digest; changing the target, the inventory, or a search bound changes it -- even
when the change does not happen to alter the candidate set (the bounds ride in ``request_digest``, a field, so
they are part of the value's own digest).

What this is NOT (stated loudly, W3): the IR certifies the *bookkeeping* of a bounded search -- what was asked,
what was searched, how complete it was, and which conservation-valid candidates came back.  It asserts nothing
about chemistry.  A formula-level candidate is ``FORMAL_CANDIDATE`` and is never lifted to a structure claim.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from .contracts import Digestible, canonical_digest
from .decompiler import DecompositionGraph, Formula, search_decomposition
from .search import SearchStatus

__all__ = [
    "CHEMICAL_COMPILATION_IR_SCHEMA",
    "CHEMICAL_IDENTITY_SCHEMA",
    "CANDIDATE_SUMMARY_SCHEMA",
    "CompilationOperation",
    "IdentityLayer",
    "ChemicalIdentity",
    "CandidateSummary",
    "ChemicalCompilationIR",
    "InverseStatus",
    "InverseResult",
    "decompile_to_ir",
    "recompile_to_ir",
    "ir_to_payload",
    "ir_from_payload",
    "serialize_ir",
    "deserialize_ir",
    "recompile_from_serialized",
]

CHEMICAL_COMPILATION_IR_SCHEMA = "smartchem.compilation-ir/chemical-compilation-ir-v1alpha1"
CHEMICAL_IDENTITY_SCHEMA = "smartchem.compilation-ir/chemical-identity-v1alpha1"
CANDIDATE_SUMMARY_SCHEMA = "smartchem.compilation-ir/candidate-summary-v1alpha1"


class CompilationOperation(str, Enum):
    DECOMPILE = "DECOMPILE"
    RECOMPILE = "RECOMPILE"


class IdentityLayer(str, Enum):
    """The identity layer a claim is made at -- a minimal first cut of section 5.1's FormulaIdentity/
    MoleculeIdentity distinction.  It records WHICH layer a species is known at so a formula-level target is never
    silently treated as a structure-level one; the full stereo/isotope/salt/mixture model is ID-LAYER-01 (TODO).
    """

    FORMULA = "FORMULA"        # elemental counts + charge, no topology claim
    STRUCTURE = "STRUCTURE"    # an atom/bond graph (a Molecule)


@dataclass(frozen=True)
class ChemicalIdentity(Digestible):
    """A typed target identity: the layer it is known at, a canonical string, and the underlying value's digest."""

    schema_version: str
    layer: IdentityLayer
    canonical_repr: str
    identity_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != CHEMICAL_IDENTITY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CHEMICAL_IDENTITY_SCHEMA!r}")
        if not isinstance(self.layer, IdentityLayer):
            raise TypeError("layer must be an IdentityLayer")
        for name in ("canonical_repr", "identity_digest"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")

    @classmethod
    def of_formula(cls, formula: Formula) -> "ChemicalIdentity":
        if type(formula) is not Formula:
            raise TypeError("of_formula needs a Formula")
        return cls(CHEMICAL_IDENTITY_SCHEMA, IdentityLayer.FORMULA, repr(formula), canonical_digest(formula))

    @classmethod
    def of_molecule(cls, molecule: "object") -> "ChemicalIdentity":
        """A STRUCTURE-layer identity for a :class:`~smartchem.category.Molecule`.

        The ``identity_digest`` is byte-congruent with the pipeline's own molecular identity
        (:func:`_structure_ident`, the same ``canonical()``/``asgiven:`` fallback that
        :mod:`smartchem.experiment.routes`/``step``/``dag`` use), so a structural IR target is the SAME
        value the route/DAG search keys on -- a same-formula isomer is a distinct identity here (section 5.4),
        never collapsed to its formula.
        """
        from .category import Molecule
        if type(molecule) is not Molecule:
            raise TypeError("of_molecule needs a smartchem.category.Molecule")
        return cls(CHEMICAL_IDENTITY_SCHEMA, IdentityLayer.STRUCTURE, repr(molecule), _structure_ident(molecule))


@dataclass(frozen=True)
class CandidateSummary(Digestible):
    """A presentation-invariant summary of one candidate in the IR: its kind, its canonical digest, its balanced
    equation (already canonical, sorted at the source), and the readiness tier it was generated at.

    The ``candidate_digest`` -- not the equation string -- is the identity; the equation is a human convenience
    that rides along.  A formula edge is a ``FORMAL_CANDIDATE`` (conservation only), never a structure claim.
    """

    schema_version: str
    candidate_kind: str
    candidate_digest: str
    equation: str
    readiness_tier: str

    _KINDS = ("FORMULA_EDGE", "ROUTE", "DAG")

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_SUMMARY_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CANDIDATE_SUMMARY_SCHEMA!r}")
        if self.candidate_kind not in self._KINDS:
            raise ValueError(f"candidate_kind must be one of {self._KINDS}")
        for name in ("candidate_digest", "equation", "readiness_tier"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class ChemicalCompilationIR(Digestible):
    """The versioned shared artifact both compiler directions consume or emit (standard section 4.1).

    DEFINING PROPERTY: the value's :attr:`digest` changes when any SEMANTIC input changes -- the target identity,
    the terminal policy, the transform-registry (grammar) version, a search bound (carried in
    :attr:`request_digest`), the search status, the candidate set, or the diagnostics -- and NEVER for a
    display-only or ordering difference.  ``request_digest`` identifies the REQUEST (target + terminal policy +
    transform registry + bounds) and is stable across re-runs; the full value digest additionally covers the
    result (candidates, status, diagnostics).  ``transform_registry_digest`` names WHICH grammar generated the
    candidates -- the identity section 8.4's "all pathways generated by transform registry <digest>" refers to.
    """

    schema_version: str
    tool_version: str
    operation: CompilationOperation
    target: ChemicalIdentity
    request_digest: str
    identity_losses: tuple[str, ...]
    terminal_policy_digest: str
    transform_registry_digest: str
    search_status: SearchStatus
    search_receipt_digest: str
    candidates: tuple[CandidateSummary, ...]
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != CHEMICAL_COMPILATION_IR_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CHEMICAL_COMPILATION_IR_SCHEMA!r}")
        if not isinstance(self.tool_version, str) or not self.tool_version:
            raise ValueError("tool_version must be a non-empty string")
        if not isinstance(self.operation, CompilationOperation):
            raise TypeError("operation must be a CompilationOperation")
        if type(self.target) is not ChemicalIdentity:
            raise TypeError("target must be a ChemicalIdentity")
        if not isinstance(self.search_status, SearchStatus):
            raise TypeError("search_status must be a SearchStatus")
        for name in ("request_digest", "terminal_policy_digest", "transform_registry_digest", "search_receipt_digest"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("identity_losses", "diagnostics"):
            value = getattr(self, name)
            if type(value) is not tuple or any(not isinstance(x, str) for x in value):
                raise TypeError(f"{name} must be a tuple of strings")
        if type(self.candidates) is not tuple or any(type(c) is not CandidateSummary for c in self.candidates):
            raise TypeError("candidates must be a tuple of CandidateSummary values")
        # canonical order: candidates are sorted by their digest, so presentation order is not part of identity
        digests = [c.candidate_digest for c in self.candidates]
        if digests != sorted(digests):
            raise ValueError("candidates must be in canonical (digest-sorted) order; display order is not identity")
        if len(set(digests)) != len(digests):
            raise ValueError("candidates must be distinct by digest")

    @property
    def complete_within_bounds(self) -> bool:
        return self.search_status is SearchStatus.COMPLETE_WITHIN_BOUNDS

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    def render(self) -> str:
        return (
            f"CHEMICAL COMPILATION IR ({self.operation.value}, {self.schema_version}, tool {self.tool_version})\n"
            f"  target: {self.target.canonical_repr} [{self.target.layer.value}]\n"
            f"  search: {self.search_status.value}; candidates: {self.candidate_count}\n"
            f"  request digest: {self.request_digest}\n"
            f"  transform registry: {self.transform_registry_digest}\n"
            f"  losses: {len(self.identity_losses)}; diagnostics: {len(self.diagnostics)}\n"
            "  Scope: bounded-search bookkeeping (what was asked / searched / found), conservation only -- "
            "NOT a chemistry claim."
        )


def _tool_version() -> str:
    from . import __version__
    return __version__


def _structure_ident(molecule: "object") -> str:
    """The pipeline's presentation-invariant molecular identity: canonical digest, ``asgiven:`` for a graph the
    canonicaliser refuses (a symmetric ring).  Byte-for-byte the ``_ident`` used in routes/step/dag, so a
    structural IR keys on the SAME identity the search does."""
    from .category import Molecule
    if type(molecule) is not Molecule:
        raise TypeError("_structure_ident needs a smartchem.category.Molecule")
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)


def _terminal_policy_digest(inventory: tuple[Formula, ...]) -> str:
    """A canonical digest of the declared formula terminal policy: the match mode plus the canonical inventory.

    Formula decompile uses ``FORMULA_ONLY`` matching by construction (section 7).  The inventory is already
    canonicalized/deduplicated by :func:`~smartchem.decompiler.search_decomposition`, so this is order-invariant.
    """
    return canonical_digest(("terminal-policy", "FORMULA_ONLY") + tuple(inventory))


# The transform registry (grammar) each producer runs, as a DECLARED descriptor keyed by search kind.  A grammar
# here is imperative code (there is no enumerable rule table to hash), so its identity is a declared version
# token -- the same discipline as every ``schema_version`` in this codebase.  The descriptor names the grammar,
# its version, and the section it is specified in; ``canonical_digest`` turns it into the stable identity that
# section 8.4 ("all pathways generated by transform registry <digest>") refers to.  LIMITATION (documented, W3):
# the digest changes only when this descriptor's version token is bumped -- an operator MUST bump it when the
# grammar's rules change, exactly as a ``schema_version`` must be bumped on a schema change.  A structural output
# change is caught downstream (it bumps STEP/ROUTE schemas, which changes candidate digests); a pure rule-set
# change with identical output structure needs the manual bump.
_TRANSFORM_REGISTRIES: dict[str, tuple] = {
    "formula-decomposition": (
        "transform-registry", "formula-decomposition", "v1",
        "conservation-descending element-bucket decomposition edges (section 7)",
    ),
    "capped-scission-linear": (
        "transform-registry", "capped-scission-linear", "v1",
        "valence-capped bond-scission retro-steps, linear acyclic routes (section 8)",
    ),
    "capped-scission-convergent": (
        "transform-registry", "capped-scission-convergent", "v1",
        "valence-capped bond-scission retro-steps, convergent synthesis DAGs (section 8)",
    ),
}


def _transform_registry_digest(kind: str) -> str:
    """The canonical digest identifying the transform grammar that generates candidates for ``kind``.

    ``kind`` is one of :data:`_TRANSFORM_REGISTRIES`' keys; an unknown kind is a programming error and refused.
    """
    try:
        descriptor = _TRANSFORM_REGISTRIES[kind]
    except KeyError:
        raise ValueError(f"unknown transform-registry kind {kind!r}; expected one of {sorted(_TRANSFORM_REGISTRIES)}")
    return canonical_digest(descriptor)


def decompile_to_ir(
    target: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    max_multiplicity: int = 1,
    budget: int = 100_000,
    max_edges: int = 5_000,
    tool_version: str | None = None,
) -> ChemicalCompilationIR:
    """Emit a :class:`ChemicalCompilationIR` for the formula decomposition of ``target`` over ``inventory``.

    The first concrete producer of the shared IR (IR-CHEM-01): it runs :func:`~smartchem.decompiler.search_decomposition`
    and packages the target identity, the terminal policy, the search status/receipt, and the conservation-valid
    decomposition edges as canonical, digest-identified candidates.  The IR's own digest is presentation-invariant
    and semantic-input-sensitive (see the class docstring).
    """
    result = search_decomposition(
        target, inventory, max_multiplicity=max_multiplicity, budget=budget, max_edges=max_edges
    )
    graph: DecompositionGraph = result.graph
    receipt = result.receipt
    target_id = ChemicalIdentity.of_formula(graph.target)
    terminal_digest = _terminal_policy_digest(graph.inventory)
    # candidates in canonical (digest-sorted) order -- display order is never part of the IR identity
    candidates = tuple(
        sorted(
            (
                CandidateSummary(
                    CANDIDATE_SUMMARY_SCHEMA, "FORMULA_EDGE", edge.digest, edge.equation(), "FORMAL_CANDIDATE"
                )
                for edge in graph.edges
            ),
            key=lambda c: c.candidate_digest,
        )
    )
    registry_digest = _transform_registry_digest("formula-decomposition")
    # the request digest covers exactly the semantic REQUEST inputs, so changing a bound (or the transform
    # registry version) changes the IR digest even when the returned candidate set happens to be identical.
    request_digest = canonical_digest(
        (
            "decompile-request",
            target_id.identity_digest,
            terminal_digest,
            ("transform-registry", registry_digest),
            ("bounds", max_multiplicity, budget, max_edges),
        )
    )
    diagnostics = () if receipt.complete_within_bounds else (receipt.stop_reason,)
    return ChemicalCompilationIR(
        CHEMICAL_COMPILATION_IR_SCHEMA,
        tool_version or _tool_version(),
        CompilationOperation.DECOMPILE,
        target_id,
        request_digest,
        (),  # identity_losses -- formula decompile forgets topology; first-class loss records are IR-LOSS-01 (TODO)
        terminal_digest,
        registry_digest,
        receipt.status,
        receipt.digest,
        candidates,
        diagnostics,
    )
    # -- decompile_to_ir sentinel above; the recompile producer is below ------------------------------------


def _recompile_terminal_policy_digest(
    reagents: tuple, available: tuple, commodities: tuple
) -> str:
    """A canonical digest of the structural terminal policy: match mode plus the SET of terminal identities.

    Section 7: a structural search terminates a branch at any node whose canonical STRUCTURE identity is on
    hand.  :func:`~smartchem.experiment.routes.search_routes`/``search_dags`` put every one of
    ``available``/``reagents``/``commodities`` into that on-hand set, so the *terminal set* is their union,
    keyed by :func:`_structure_ident` (never by formula -- a same-formula isomer does not terminate).  A
    frozenset makes the digest order-invariant, so permuting any inventory list leaves the policy unchanged.
    """
    terminals = frozenset(_structure_ident(m) for m in (*available, *reagents, *commodities))
    return canonical_digest(("terminal-policy", "STRUCTURE", terminals))


def recompile_to_ir(
    target: "object",
    *,
    reagents: tuple,
    available: tuple = (),
    commodities: tuple = (),
    max_depth: int = 2,
    max_results: int = 100,
    cut_budget: int = 20_000,
    mode: str = "routes",
    tool_version: str | None = None,
) -> ChemicalCompilationIR:
    """Emit a :class:`ChemicalCompilationIR` for the *structural* recompilation (synthesis) of ``target``.

    The second concrete producer of the shared IR (advancing IR-CHEM-01): where :func:`decompile_to_ir` packages
    the formula decomposition, this packages the recompiler's route or DAG search
    (:func:`~smartchem.experiment.routes.search_routes` when ``mode='routes'``,
    :func:`~smartchem.experiment.routes.search_dags` when ``mode='dags'``) as canonical, digest-identified
    ``ROUTE``/``DAG`` candidates over a STRUCTURE-layer target identity.

    The IR's digest keeps the section 4.1 discipline: it is presentation-invariant (permuting ``reagents`` or
    ``available`` does not change it -- the terminal policy is a frozenset and candidates are digest-sorted) and
    semantic-input-sensitive (a search-bound change alters ``request_digest``, hence the value digest, even when
    the returned candidate set is byte-for-byte identical).  ``request_digest`` additionally distinguishes the
    reagent HELPER pool from the plain terminal stock, because moving a molecule from ``reagents`` (a pool the
    cleavage may consume) to ``available`` (mere on-hand stock) genuinely changes which candidates exist.

    W3 unchanged: every candidate is a ``FORMAL_CANDIDATE`` -- a conservation-valid assembly within the current
    capped-scission grammar and the declared search bounds, never a claim that the synthesis works.
    """
    from .category import Molecule
    if type(target) is not Molecule:
        raise TypeError("recompile_to_ir target must be a smartchem.category.Molecule")
    if mode not in ("routes", "dags"):
        raise ValueError("mode must be 'routes' or 'dags'")
    from .experiment.routes import search_dags, search_routes

    if mode == "routes":
        result = search_routes(
            target, reagents=reagents, available=available, commodities=commodities,
            max_depth=max_depth, max_routes=max_results, cut_budget=cut_budget,
        )
        candidate_kind = "ROUTE"
        candidate_objs: tuple = result.routes
        def _equation(obj) -> str:
            return " ; ".join(obj.equation_lines())
    else:
        result = search_dags(
            target, reagents=reagents, available=available, commodities=commodities,
            max_depth=max_depth, max_dags=max_results, cut_budget=cut_budget,
        )
        candidate_kind = "DAG"
        candidate_objs = result.dags
        def _equation(obj) -> str:
            return " ; ".join(s.equation() for s in obj.topological_order())

    receipt = result.receipt
    target_id = ChemicalIdentity.of_molecule(target)
    terminal_digest = _recompile_terminal_policy_digest(reagents, available, commodities)
    candidates = tuple(
        sorted(
            (
                CandidateSummary(
                    CANDIDATE_SUMMARY_SCHEMA, candidate_kind, obj.digest,
                    _equation(obj) or repr(obj), "FORMAL_CANDIDATE",
                )
                for obj in candidate_objs
            ),
            key=lambda c: c.candidate_digest,
        )
    )
    registry_digest = _transform_registry_digest(
        "capped-scission-linear" if mode == "routes" else "capped-scission-convergent"
    )
    # request_digest identifies the REQUEST: target + terminal set + the reagent HELPER pool (distinct from
    # plain stock) + the transform registry + mode + bounds -- so a bound change (or a reagent-vs-available move,
    # or a transform-registry version bump) changes the IR digest even when the candidate set is identical.
    reagent_pool = frozenset(_structure_ident(m) for m in reagents)
    request_digest = canonical_digest(
        (
            "recompile-request",
            target_id.identity_digest,
            terminal_digest,
            ("reagent-pool", reagent_pool),
            ("transform-registry", registry_digest),
            ("mode", mode),
            ("bounds", max_depth, max_results, cut_budget),
        )
    )
    if result.target_in_terminal_stock:
        diagnostics: tuple[str, ...] = (
            "target is already present in the active terminal stock; no synthesis is required (section 7)",
        )
    elif not receipt.complete_within_bounds:
        diagnostics = (f"search incomplete within bounds: {receipt.status.value}",)
    elif not candidates:
        # complete-within-bounds AND zero candidates AND not in stock: NO limit fired, so this mode's search
        # EXHAUSTED its grammar at these bounds and found no conservation-valid assembly terminating in stock.
        # This MUST be said precisely -- a silent "complete + empty" is indistinguishable from a truncated
        # search that gave up (the laundering SRCH-DEPTH-01 outlawed one layer down).  But the claim is scoped
        # EXACTLY to what the receipt proves: exhaustion of THIS mode's grammar at THESE bounds -- NOT a
        # registry-wide "no route exists anywhere" (a different mode or higher bounds is not excluded; the same
        # request under mode='dags' can still be truncated).  Overclaiming that scope was a red-team finding.
        diagnostics = (
            f"no route to the target from the declared terminals exists within the '{mode}' search grammar at "
            f"the declared bounds (max_depth={max_depth}); the search was exhaustive there (no limit fired), but "
            f"that is exhaustion of THIS grammar/mode at THESE bounds -- not a proof that no route exists under a "
            f"different mode or higher bounds (section 8.3, no-route: exhaustive-within-bounds)",
        )
    else:
        diagnostics = ()
    return ChemicalCompilationIR(
        CHEMICAL_COMPILATION_IR_SCHEMA,
        tool_version or _tool_version(),
        CompilationOperation.RECOMPILE,
        target_id,
        request_digest,
        (),  # identity_losses -- structural assembly forgets nothing at the structure layer; IR-LOSS-01 (TODO)
        terminal_digest,
        registry_digest,
        receipt.status,
        receipt.digest,
        candidates,
        diagnostics,
    )


# -- serialization (advancing IR-CHEM-01: the IR is a transportable artifact, not just an in-memory value) --
#
# The one property that must survive the round trip is IDENTITY: deserialize(serialize(ir)).digest == ir.digest.
# So the payload captures exactly the semantic fields (enums by their .value, nested records as nested dicts,
# tuples as lists) and from_payload rebuilds the SAME frozen dataclasses -- which re-run their __post_init__
# invariants, so a tampered payload (unsorted/duplicate candidates, an unknown enum, a bad schema) is REFUSED on
# read rather than silently trusted. json is written sort_keys=True, so the serialized string is canonical too.


def ir_to_payload(ir: ChemicalCompilationIR) -> dict:
    """A JSON-compatible dict capturing every SEMANTIC field of ``ir`` (enums by value, tuples as lists)."""
    if type(ir) is not ChemicalCompilationIR:
        raise TypeError("ir_to_payload needs a ChemicalCompilationIR")
    return {
        "schema_version": ir.schema_version,
        "tool_version": ir.tool_version,
        "operation": ir.operation.value,
        "target": {
            "schema_version": ir.target.schema_version,
            "layer": ir.target.layer.value,
            "canonical_repr": ir.target.canonical_repr,
            "identity_digest": ir.target.identity_digest,
        },
        "request_digest": ir.request_digest,
        "identity_losses": list(ir.identity_losses),
        "terminal_policy_digest": ir.terminal_policy_digest,
        "transform_registry_digest": ir.transform_registry_digest,
        "search_status": ir.search_status.value,
        "search_receipt_digest": ir.search_receipt_digest,
        "candidates": [
            {
                "schema_version": c.schema_version,
                "candidate_kind": c.candidate_kind,
                "candidate_digest": c.candidate_digest,
                "equation": c.equation,
                "readiness_tier": c.readiness_tier,
            }
            for c in ir.candidates
        ],
        "diagnostics": list(ir.diagnostics),
    }


def ir_from_payload(payload: dict) -> ChemicalCompilationIR:
    """Rebuild a :class:`ChemicalCompilationIR` from :func:`ir_to_payload`'s dict, re-validating every invariant.

    Every frozen record is reconstructed and its ``__post_init__`` re-runs, so a payload that violates a schema
    string, an enum domain, or the canonical/distinct candidate ordering is REFUSED here -- deserialization never
    trusts a value it would not have constructed itself.
    """
    if not isinstance(payload, dict):
        raise TypeError("ir_from_payload needs a dict")
    t = payload["target"]
    target = ChemicalIdentity(
        t["schema_version"], IdentityLayer(t["layer"]), t["canonical_repr"], t["identity_digest"]
    )
    candidates = tuple(
        CandidateSummary(
            c["schema_version"], c["candidate_kind"], c["candidate_digest"], c["equation"], c["readiness_tier"]
        )
        for c in payload["candidates"]
    )
    return ChemicalCompilationIR(
        payload["schema_version"],
        payload["tool_version"],
        CompilationOperation(payload["operation"]),
        target,
        payload["request_digest"],
        tuple(payload["identity_losses"]),
        payload["terminal_policy_digest"],
        payload["transform_registry_digest"],
        SearchStatus(payload["search_status"]),
        payload["search_receipt_digest"],
        candidates,
        tuple(payload["diagnostics"]),
    )


def serialize_ir(ir: ChemicalCompilationIR) -> str:
    """A canonical JSON string for ``ir`` -- deterministic (``sort_keys``) and round-trip identity-preserving."""
    return json.dumps(ir_to_payload(ir), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def deserialize_ir(text: str) -> ChemicalCompilationIR:
    """Parse a :func:`serialize_ir` string back into a validated :class:`ChemicalCompilationIR`."""
    if not isinstance(text, str):
        raise TypeError("deserialize_ir needs a str")
    return ir_from_payload(json.loads(text))


# == IR-INV-01: the recompiler consumes a SERIALIZED decompile artifact, end to end =======================
#
# This is where the two compiler directions actually MEET across the serialization boundary (section 4.1): a
# decompile artifact is emitted, serialized to a transportable string, and then a recompile is driven FROM it.
#
# The load-bearing honesty is the formula->structure gap (section 5.4).  A decompile artifact is a FORMULA-layer
# fact ("H2O decomposes to the {H, O} buckets"); the recompiler is a STRUCTURE-layer search (it needs a Molecule
# and structural terminals).  A formula does NOT determine a structure -- so the caller MUST supply the structural
# hypothesis, and the bridge's one non-trivial consumption of the artifact is to GATE that hypothesis on the
# decompiled formula: the reconstitution target's formula must equal the formula the decompile analysed, or the
# request is not an inverse of that artifact at all and is refused.
#
# The named acceptance (IR-INV-01): water.  ``recompile`` cannot build H2O from H2/O2 terminals -- elemental
# redox is outside the capped-scission organic grammar.  We do NOT invent a water transform (that would fabricate
# a reaction, W3-forbidden); instead the bridge classifies the outcome and, for water, returns a PRECISE
# unsupported-transform refusal (``NO_ROUTE_IN_GRAMMAR``).  The one distinction that makes the refusal honest is
# separating an EXHAUSTIVE empty search (a real grammar dead end) from a TRUNCATED empty search (inconclusive) --
# the same split SRCH-DEPTH-01 enforced one layer down; a truncated search is NEVER reported as a dead end.


class InverseStatus(str, Enum):
    """The verdict of driving a recompile FROM a decompile artifact (section 4.1 / IR-INV-01).

    Two of these are pre-search refusals (no recompile IR is produced); the rest classify a recompile that ran.
    Only ``ROUTES_FOUND`` and ``TARGET_ALREADY_TERMINAL`` are successes; every other member carries a ``refusal``
    explaining precisely why the inverse did not (or could not) reconstitute the target.
    """

    NOT_A_DECOMPILE_ARTIFACT = "NOT_A_DECOMPILE_ARTIFACT"  # the serialized IR is not a DECOMPILE/FORMULA artifact
    FORMULA_MISMATCH = "FORMULA_MISMATCH"                  # the structural hypothesis is not the decompiled species
    TARGET_ALREADY_TERMINAL = "TARGET_ALREADY_TERMINAL"    # trivially reconstituted: target is itself on-hand stock
    ROUTES_FOUND = "ROUTES_FOUND"                          # >=1 formal-candidate route/DAG (completeness: see the IR)
    NO_ROUTE_IN_GRAMMAR = "NO_ROUTE_IN_GRAMMAR"            # EXHAUSTIVE empty search: a real grammar-level dead end
    INCONCLUSIVE_BOUNDS_HIT = "INCONCLUSIVE_BOUNDS_HIT"    # TRUNCATED empty search: cannot conclude no-route


@dataclass(frozen=True)
class InverseResult:
    """The end-to-end outcome of consuming a serialized decompile artifact and driving a recompile from it.

    ``decompile_ir`` is always the (re-validated) artifact that was consumed.  ``recompile_ir`` is the structural
    recompilation that ran, or ``None`` for a pre-search refusal (``NOT_A_DECOMPILE_ARTIFACT``/``FORMULA_MISMATCH``).
    ``refusal`` is a precise, human-readable explanation for every non-success status and ``None`` for a success.

    This is deliberately NOT a :class:`Digestible`: it is a report bundling two already-identified IRs plus a
    verdict, not a new identity.  The transportable identities are the two IRs it carries.
    """

    decompile_ir: ChemicalCompilationIR
    recompile_ir: "ChemicalCompilationIR | None"
    inverse_status: InverseStatus
    refusal: "str | None"

    def __post_init__(self) -> None:
        if type(self.decompile_ir) is not ChemicalCompilationIR:
            raise TypeError("decompile_ir must be a ChemicalCompilationIR")
        if self.recompile_ir is not None and type(self.recompile_ir) is not ChemicalCompilationIR:
            raise TypeError("recompile_ir must be a ChemicalCompilationIR or None")
        if not isinstance(self.inverse_status, InverseStatus):
            raise TypeError("inverse_status must be an InverseStatus")
        # the two slots must actually carry the operations the field names advertise -- a DECOMPILE artifact in
        # the recompile slot (or vice versa) is an incoherent bundle even if every other invariant holds
        # (red-team finding: enforce the coherence the docstring promises, do not merely document it).  The ONE
        # exemption is NOT_A_DECOMPILE_ARTIFACT, whose whole job is to report the wrong-operation artifact it was
        # handed -- so the decompile slot there deliberately carries a non-DECOMPILE op.
        if self.inverse_status is not InverseStatus.NOT_A_DECOMPILE_ARTIFACT:
            if self.decompile_ir.operation is not CompilationOperation.DECOMPILE:
                raise ValueError("decompile_ir must carry the DECOMPILE operation")
        if self.recompile_ir is not None and self.recompile_ir.operation is not CompilationOperation.RECOMPILE:
            raise ValueError("recompile_ir must carry the RECOMPILE operation")
        _successes = (InverseStatus.ROUTES_FOUND, InverseStatus.TARGET_ALREADY_TERMINAL)
        if self.inverse_status in _successes:
            if self.refusal is not None:
                raise ValueError("a success status carries no refusal")
        elif not isinstance(self.refusal, str) or not self.refusal:
            raise ValueError("a non-success status must carry a non-empty refusal string")
        # a pre-search refusal produced no recompile IR; a post-search status must carry one
        _pre_search = (InverseStatus.NOT_A_DECOMPILE_ARTIFACT, InverseStatus.FORMULA_MISMATCH)
        if self.inverse_status in _pre_search and self.recompile_ir is not None:
            raise ValueError("a pre-search refusal must not carry a recompile IR")
        if self.inverse_status not in _pre_search and self.recompile_ir is None:
            raise ValueError("a post-search status must carry a recompile IR")

    @property
    def reconstituted(self) -> bool:
        """True iff the inverse produced at least one route (or the target was already terminal stock)."""
        return self.inverse_status in (InverseStatus.ROUTES_FOUND, InverseStatus.TARGET_ALREADY_TERMINAL)

    def render(self) -> str:
        head = (
            f"INVERSE COMPILATION ({self.inverse_status.value})\n"
            f"  decompiled: {self.decompile_ir.target.canonical_repr} "
            f"[{self.decompile_ir.target.layer.value}] -> {self.decompile_ir.candidate_count} bucket edge(s)\n"
        )
        if self.recompile_ir is not None:
            head += (
                f"  recompiled: {self.recompile_ir.target.canonical_repr} "
                f"[{self.recompile_ir.target.layer.value}]; search {self.recompile_ir.search_status.value}; "
                f"{self.recompile_ir.candidate_count} candidate(s)\n"
            )
        # NB: a decompile artifact is formula-level, so a success confirms only that the SUPPLIED structural
        # hypothesis routes -- never that the artifact was about that specific isomer (a formula does not fix
        # one). Say exactly that, so the word does not read as structure-level identity confirmation.
        head += f"  refusal: {self.refusal}" if self.refusal else "  refusal: none (routes for the supplied structure)"
        return head


def recompile_from_serialized(
    decompile_ir_text: str,
    *,
    structure: "object",
    reagents: tuple,
    available: tuple = (),
    commodities: tuple = (),
    max_depth: int = 2,
    max_results: int = 100,
    cut_budget: int = 20_000,
    mode: str = "routes",
    tool_version: str | None = None,
) -> InverseResult:
    """Consume a SERIALIZED decompile artifact and drive a recompile from it, end to end (IR-INV-01).

    ``decompile_ir_text`` is a :func:`serialize_ir` string of a DECOMPILE artifact (as produced by
    :func:`decompile_to_ir`); ``structure`` is the caller's STRUCTURE-layer hypothesis (a
    :class:`~smartchem.category.Molecule`) for the decompiled species.  The bridge:

    1. deserializes and re-validates the artifact (a tampered payload is refused on read);
    2. refuses unless the artifact is a DECOMPILE at the FORMULA layer (``NOT_A_DECOMPILE_ARTIFACT``);
    3. gates the structural hypothesis on the decompiled formula -- the reconstitution target's formula MUST
       equal the analysed formula, else the request is not an inverse of THIS artifact (``FORMULA_MISMATCH``);
       this is the one place the artifact genuinely CONSTRAINS the recompile across the section 5.4 gap;
    4. runs :func:`recompile_to_ir` over the structural hypothesis and terminals; and
    5. classifies the outcome, keeping the honest distinction between an EXHAUSTIVE empty search
       (``NO_ROUTE_IN_GRAMMAR`` -- a real grammar dead end, e.g. water from H2/O2) and a TRUNCATED empty
       search (``INCONCLUSIVE_BOUNDS_HIT`` -- cannot conclude no-route).

    W3 unchanged: a ``ROUTES_FOUND`` verdict means conservation-valid formal candidates exist within the grammar
    and bounds, never that any synthesis is validated; read ``recompile_ir.search_status`` for completeness.
    """
    from .category import Molecule

    decompile_ir = deserialize_ir(decompile_ir_text)

    if decompile_ir.operation is not CompilationOperation.DECOMPILE or decompile_ir.target.layer is not IdentityLayer.FORMULA:
        return InverseResult(
            decompile_ir,
            None,
            InverseStatus.NOT_A_DECOMPILE_ARTIFACT,
            (
                f"the serialized artifact is {decompile_ir.operation.value} at the "
                f"{decompile_ir.target.layer.value} layer; recompile_from_serialized inverts a DECOMPILE/FORMULA "
                f"artifact (section 4.1)"
            ),
        )

    if type(structure) is not Molecule:
        raise TypeError("structure must be a smartchem.category.Molecule (the structural hypothesis)")

    struct_formula = ChemicalIdentity.of_formula(Formula.of(structure.formula, structure.charge))
    if struct_formula.identity_digest != decompile_ir.target.identity_digest:
        return InverseResult(
            decompile_ir,
            None,
            InverseStatus.FORMULA_MISMATCH,
            (
                f"the structural hypothesis has formula {struct_formula.canonical_repr}, but the decompile artifact "
                f"analysed {decompile_ir.target.canonical_repr}; the inverse must reconstitute the SAME species "
                f"(section 5.4: a formula does not fix a structure, but the target's formula must equal the "
                f"decompiled formula)"
            ),
        )

    recompile_ir = recompile_to_ir(
        structure,
        reagents=reagents,
        available=available,
        commodities=commodities,
        max_depth=max_depth,
        max_results=max_results,
        cut_budget=cut_budget,
        mode=mode,
        tool_version=tool_version,
    )

    # classify from STRUCTURED facts, never by string-matching a diagnostic.  target-in-stock is decided the same
    # way the search decides it: the target's structure identity lies in the union of the declared terminals.
    terminal_idents = frozenset(_structure_ident(m) for m in (*available, *reagents, *commodities))
    target_terminal = _structure_ident(structure) in terminal_idents

    if target_terminal:
        return InverseResult(decompile_ir, recompile_ir, InverseStatus.TARGET_ALREADY_TERMINAL, None)
    if recompile_ir.candidate_count > 0:
        return InverseResult(decompile_ir, recompile_ir, InverseStatus.ROUTES_FOUND, None)
    if recompile_ir.complete_within_bounds:
        return InverseResult(
            decompile_ir,
            recompile_ir,
            InverseStatus.NO_ROUTE_IN_GRAMMAR,
            (
                f"no route reconstitutes {decompile_ir.target.canonical_repr} from the declared terminals within "
                f"the '{mode}' grammar at the declared bounds (max_depth={max_depth}); the search was exhaustive "
                f"there (no limit fired), but exhaustion is of THIS grammar/mode at THESE bounds -- NOT a proof "
                f"that no route exists under a different mode or higher bounds. No bridge reaction is invented "
                f"(W3, section 8.3, no-route: exhaustive-within-bounds)."
            ),
        )
    return InverseResult(
        decompile_ir,
        recompile_ir,
        InverseStatus.INCONCLUSIVE_BOUNDS_HIT,
        (
            f"the recompile search for {decompile_ir.target.canonical_repr} was TRUNCATED "
            f"({recompile_ir.search_status.value}) before finding any route or exhausting the grammar; no-route "
            f"cannot be concluded -- raise the bounds to decide (section 8.2)"
        ),
    )
