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
