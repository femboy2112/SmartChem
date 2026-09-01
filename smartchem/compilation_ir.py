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
    "decompile_to_ir",
    "recompile_to_ir",
    "ir_to_payload",
    "ir_from_payload",
    "serialize_ir",
    "deserialize_ir",
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
    the terminal policy, a search bound (carried in :attr:`request_digest`), the search status, the candidate set,
    or the diagnostics -- and NEVER for a display-only or ordering difference.  ``request_digest`` identifies the
    REQUEST (target + terminal policy + bounds) and is stable across re-runs; the full value digest additionally
    covers the result (candidates, status, diagnostics).
    """

    schema_version: str
    tool_version: str
    operation: CompilationOperation
    target: ChemicalIdentity
    request_digest: str
    identity_losses: tuple[str, ...]
    terminal_policy_digest: str
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
        for name in ("request_digest", "terminal_policy_digest", "search_receipt_digest"):
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
    # the request digest covers exactly the semantic REQUEST inputs, so changing a bound changes the IR digest
    # even when the returned candidate set happens to be identical.
    request_digest = canonical_digest(
        (
            "decompile-request",
            target_id.identity_digest,
            terminal_digest,
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
    # request_digest identifies the REQUEST: target + terminal set + the reagent HELPER pool (distinct from
    # plain stock) + mode + bounds -- so a bound change (or a reagent-vs-available move) changes the IR digest
    # even when the candidate set is identical.
    reagent_pool = frozenset(_structure_ident(m) for m in reagents)
    request_digest = canonical_digest(
        (
            "recompile-request",
            target_id.identity_digest,
            terminal_digest,
            ("reagent-pool", reagent_pool),
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
