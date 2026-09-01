"""M-4 v1 -- the chemical decompiler (elemental-descent hypergraph).

Take a compound (a molecular formula ``C8H9NO2``, or an atom-count mapping) and enumerate
**all decomposition-reaction chains through lower compounds down to the bare elements**, as
an AND-OR reaction hypergraph.  Water bottoms out in essentially one family; a denser target
over a richer intermediate inventory produces a layered graph.

The reframe that governs the whole module
-----------------------------------------
"Decompile X down to its elements" and "assemble X up from buckets of each element" are the
**same hypergraph read in opposite directions**: an edge ``X -> {A, B, C}`` (decomposition)
is the exact reverse of ``{A, B, C} -> X`` (assembly).  So one engine answers both framings.
And "how full does each element bucket need to be" is not a search result -- it is *forced by
conservation*: the leaf buckets sum to the target's own formula (see
:meth:`Formula.element_buckets`).  The only thing the search explores is the *routing* -- the
chains of intermediates connecting the buckets to the target.

The one law that makes this a SmartChem feature and not a lying cheminformatics toy
-----------------------------------------------------------------------------------
**A balanced decomposition is linear algebra over the integers -- mass conservation -- not
chemistry.**  This module CERTIFIES the algebra (exact integer conservation, and
combinatorial completeness over a *declared closed inventory*, up to a stated multiplicity
and budget) and establishes *nothing whatsoever* about thermodynamic favorability, kinetic
accessibility, reaction mechanism, or synthesizability.  It is not a retrosynthesis planner
and not a decomposition *prediction*.  This is the same discipline the finite Ising<->lattice
gas map already enforces: exact mathematics is not literal physical identity, and no amount of
suggestive-looking structure upgrades one into the other.  The tier belongs to the executor
that will wrap this (M-4 B3); this pure engine simply refuses to imply more than conservation.

The three walls (each is a real constraint, not decoration)
-----------------------------------------------------------
* **W1 Termination.**  "All the way down" is infinite without a well-founded descent measure.
  The rank of a species is its atom count; every product of an admissible edge has *strictly
  smaller* rank than the reactant, so the multiset of node ranks descends in the multiset
  order and the recursion is well-founded.  The guard has teeth: it rejects
  ``2 H2O -> H2 + H2O2`` because ``H2O2`` (rank 4) is *larger* than ``H2O`` (rank 3) -- a
  "decomposition" that grows a product is exactly the non-terminating move this forbids.
* **W2 Budget.**  Even over a closed inventory the graph explodes for dense targets.  There
  are explicit search/edge budgets and a **loud REFUSED_BUDGET status** -- never a silently
  truncated partial graph reported as complete.
* **W3 Formal != physical.**  The law above, restated as the wall an implementer is tempted to
  cross the moment the graphs look chemically suggestive.

v1 scope (decisions fixed with the owner, 2026-08-30)
-----------------------------------------------------
* **Formula-level** (atom multiset), not structure-level.  Consequence, stated loudly: *every
  structural isomer of a formula shares one decomposition graph* -- correct and honest for a
  stoichiometric decomposer.  Bond-graph-aware descent is v2.
* **Closed declared inventory**: the caller declares molecular terminal buckets; those species may appear
  in a split but are not recursively decomposed. Element buckets are always terminals. Open generative
  enumeration of intermediates is v2.
* **Terminals are element buckets counted in atoms** (``O`` and ``O2`` are the same bucket);
  the familiar molecular packaging (``O2``, ``H2``) is a *reporting* layer
  (:meth:`Formula.reference_form` / :func:`standard_state_equation`), never a separate identity.
* **Neutral species only** (charge 0).  A charged target is refused.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import reduce
from math import gcd

from .contracts import Digestible
from .data.periodic_table import ATOMIC_NUMBER
from .search import SearchStatus

__all__ = [
    "DECOMPILER_SCHEMA",
    "FORMULA_SEARCH_RECEIPT_SCHEMA",
    "DECOMPOSITION_SEARCH_RESULT_SCHEMA",
    "DecompilerError",
    "Formula",
    "DecompositionEdge",
    "DecompositionGraph",
    "FormulaSearchReceipt",
    "DecompositionSearchResult",
    "admissible_edges",
    "build_decomposition",
    "search_decomposition",
    "standard_state_equation",
    "example_inventory",
]

DECOMPILER_SCHEMA = "smartchem.decompiler/elemental-descent-v1"
FORMULA_SEARCH_RECEIPT_SCHEMA = "smartchem.decompiler/formula-search-receipt-v1alpha2"
DECOMPOSITION_SEARCH_RESULT_SCHEMA = "smartchem.decompiler/decomposition-search-result-v1alpha1"

#: Atom count at which an element's familiar molecular packaging groups.  This is *bookkeeping*
#: for repackaging atom buckets into conventional molecules (report 2 H atoms as one H2), never
#: a claim about an element's physical standard state (carbon's is graphite, not a "C1" gas).
#: Absent elements group as monatomic (1) for counting purposes.
_REFERENCE_MOLECULARITY: dict[str, int] = {
    "H": 2, "D": 2, "T": 2, "N": 2, "O": 2, "F": 2, "Cl": 2, "Br": 2, "I": 2,
}
_FORMULA_SYMBOLS = frozenset(ATOMIC_NUMBER) | {"D", "T"}  # isotope shorthand retained by the v1 API


class DecompilerError(ValueError):
    """A formula, edge, or decomposition request was not admissible for v1."""


def _multi_gcd(values: tuple[int, ...]) -> int:
    return reduce(gcd, values, 0)


# ======================================================================================
# Formula -- a formula-level species (atom multiset), the v1 node identity
# ======================================================================================
@dataclass(frozen=True)
class Formula(Digestible):
    """An atom-count multiset with charge -- one species at formula granularity.

    ``counts`` is a sorted tuple of ``(element_symbol, positive_count)`` pairs; it is the
    conserved signature.  Two structural isomers have the same ``Formula`` by construction --
    which is exactly the v1 formula-level contract.  A single-element formula is an *element
    bucket* (a terminal): ``O2`` and ``O`` are both "the oxygen bucket", differing only in how
    many atoms it holds.
    """

    counts: tuple[tuple[str, int], ...]
    charge: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.counts, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 for pair in self.counts
        ):
            raise TypeError("counts must be a tuple of (symbol, count) pairs")
        if not self.counts:
            raise ValueError("a chemical formula must contain at least one atom")
        seen: set[str] = set()
        prev: str | None = None
        for symbol, count in self.counts:
            if not isinstance(symbol, str) or not symbol:
                raise TypeError("element symbol must be a non-empty string")
            if type(count) is not int or count <= 0:
                raise ValueError(f"count for {symbol!r} must be a positive int, got {count!r}")
            if symbol not in _FORMULA_SYMBOLS:
                raise DecompilerError(
                    f"unknown element {symbol!r}; formulas validate against SmartChem's complete sourced "
                    f"periodic table and refuse rather than guess"
                )
            if symbol in seen:
                raise ValueError(f"element {symbol!r} appears twice; counts must be a multiset")
            if prev is not None and symbol < prev:
                raise ValueError("counts must be sorted by element symbol (use Formula.of)")
            seen.add(symbol)
            prev = symbol
        if type(self.charge) is not int:
            raise TypeError("charge must be an integer number of elementary charges")

    # -- construction ------------------------------------------------------------
    @classmethod
    def of(cls, mapping: "dict[str, int] | Formula", charge: int = 0) -> "Formula":
        """Build from an element->positive-integer-count mapping (unsorted), or copy a Formula."""
        if isinstance(mapping, Formula):
            return mapping
        if not isinstance(mapping, Mapping):
            raise TypeError("mapping must be a dict of element symbols to positive integer counts")
        clean: dict[str, int] = {}
        for symbol, count in mapping.items():
            if type(count) is not int:
                raise TypeError(f"count for {symbol!r} must be an int, got {type(count).__name__}")
            if count <= 0:
                raise ValueError(f"count for {symbol!r} must be positive, got {count!r}")
            clean[symbol] = count
        if not clean:
            raise ValueError("a chemical formula must contain at least one atom")
        return cls(tuple(sorted(clean.items())), charge)

    @classmethod
    def bucket(cls, symbol: str, count: int = 1) -> "Formula":
        """An element bucket holding ``count`` atoms of one element (a terminal)."""
        return cls.of({symbol: count})

    @classmethod
    def parse(cls, text: str, charge: int = 0) -> "Formula":
        """Parse a molecular formula string: multi-letter symbols, counts, nested parentheses.

        ``C8H9NO2``, ``H2O``, ``(NH4)2SO4`` all parse.  Element symbols follow the standard
        capital+optional-lowercase convention (so ``CO`` is C+O, not cobalt).  An unknown or
        untabulated element is refused by name.
        """
        if not isinstance(text, str) or not text.strip():
            raise DecompilerError("formula text must be a non-empty string")
        stack: list[dict[str, int]] = [{}]
        i, n = 0, len(text)
        while i < n:
            c = text[i]
            if c == "(":
                stack.append({})
                i += 1
            elif c == ")":
                i += 1
                j = i
                while j < n and text[j].isdigit():
                    j += 1
                mult = int(text[i:j]) if j > i else 1
                i = j
                if len(stack) == 1:
                    raise DecompilerError(f"unbalanced ')' in formula {text!r}")
                group = stack.pop()
                for sym, k in group.items():
                    stack[-1][sym] = stack[-1].get(sym, 0) + k * mult
            elif c.isupper():
                j = i + 1
                if j < n and text[j].islower():
                    j += 1
                symbol = text[i:j]
                i = j
                k = i
                while k < n and text[k].isdigit():
                    k += 1
                mult = int(text[i:k]) if k > i else 1
                i = k
                stack[-1][symbol] = stack[-1].get(symbol, 0) + mult
            elif c in " \t.·":  # allow spaces and a middle dot as separators
                i += 1
            else:
                raise DecompilerError(f"unexpected character {c!r} in formula {text!r}")
        if len(stack) != 1:
            raise DecompilerError(f"unbalanced '(' in formula {text!r}")
        if not stack[0]:
            raise DecompilerError(f"formula {text!r} names no atoms")
        return cls.of(stack[0], charge)

    # -- structure ---------------------------------------------------------------
    @property
    def as_dict(self) -> dict[str, int]:
        return dict(self.counts)

    @property
    def rank(self) -> int:
        """The well-founded descent measure: total atom count."""
        return sum(k for _, k in self.counts)

    @property
    def elements(self) -> frozenset[str]:
        return frozenset(s for s, _ in self.counts)

    @property
    def is_element(self) -> bool:
        """True iff this is a single-element bucket -- a terminal of the descent."""
        return len(self.counts) == 1 and self.charge == 0

    def element_buckets(self) -> tuple[tuple[str, int], ...]:
        """The forced per-element atom totals -- the "how full is each bucket" answer.

        For any target this is just its own composition: conservation pins the leaf buckets to
        the target's formula.  The routing is where the search lives; the buckets are not.
        """
        return self.counts

    def reference_form(self) -> tuple[int, int]:
        """``(reference_molecularity, atoms)`` for an element bucket -- the packaging layer.

        Only defined for a single-element bucket.  Bookkeeping for reporting 2 H atoms as one
        ``H2``; not a physical standard-state claim.
        """
        if not self.is_element:
            raise DecompilerError("reference_form is defined only for an element bucket")
        (symbol, atoms), = self.counts
        return _REFERENCE_MOLECULARITY.get(symbol, 1), atoms

    def __repr__(self) -> str:
        body = "".join(f"{s}{k if k > 1 else ''}" for s, k in self.counts)
        if self.charge > 0:
            body += f"^{self.charge}+"
        elif self.charge < 0:
            body += f"^{abs(self.charge)}-"
        return body or "()"


def _sort_key(formula: Formula) -> tuple:
    return (formula.counts, formula.charge)


# ======================================================================================
# DecompositionEdge -- one AND hyperedge, where W1 (termination) is enforced
# ======================================================================================
@dataclass(frozen=True)
class DecompositionEdge(Digestible):
    """One admissible decomposition step ``n . reactant -> products``.

    The constructor is where every invariant lives, so no downstream code has to remember to
    check and no built edge can violate them:

    * **conservation** -- ``reactant_multiplicity * reactant == sum(mult * product)`` for every
      element (and charge, trivially zero in v1);
    * **W1 descent** -- every product has strictly smaller :attr:`Formula.rank` than the
      reactant, so the edge cannot grow a species and the recursion terminates;
    * **non-vacuity** -- at least two product *instances* (``sum(mult) >= 2``), so a rename or
      identity is not a "decomposition";
    * **canonical element buckets** -- a single-element product is the unit bucket ``{E: 1}``
      with its quantity carried by its multiplicity, so ``2 H`` has one spelling;
    * **primitivity** -- ``gcd(reactant_multiplicity, all multiplicities) == 1``, so an edge is
      the canonical representative of its scaled family (``2 A -> 2 B`` is spelled ``A -> B``
      unless the scaling is genuinely needed to clear a fraction).
    """

    reactant: Formula
    reactant_multiplicity: int
    products: tuple[tuple[Formula, int], ...]

    def __post_init__(self) -> None:
        if type(self.reactant) is not Formula:
            raise TypeError("reactant must be a Formula")
        if type(self.reactant_multiplicity) is not int or self.reactant_multiplicity < 1:
            raise ValueError("reactant_multiplicity must be an int >= 1")
        if type(self.products) is not tuple or not self.products:
            raise TypeError("products must be a non-empty tuple of (Formula, multiplicity)")
        if self.reactant.charge != 0:
            raise DecompilerError("v1 decomposes neutral species only; reactant is charged")

        instances = 0
        for pair in self.products:
            if type(pair) is not tuple or len(pair) != 2:
                raise TypeError("each product must be a (Formula, multiplicity) pair")
            product, mult = pair
            if type(product) is not Formula:
                raise TypeError("each product must be a Formula")
            if type(mult) is not int or mult < 1:
                raise ValueError("each product multiplicity must be an int >= 1")
            if product.charge != 0:
                raise DecompilerError("v1 products are neutral; a product is charged")
            if product.rank >= self.reactant.rank:
                raise DecompilerError(
                    f"non-descending product {product!r} (rank {product.rank}) for reactant "
                    f"{self.reactant!r} (rank {self.reactant.rank}); every product must be "
                    f"strictly lower rank or the descent does not terminate (W1)"
                )
            if product.is_element and product.counts[0][1] != 1:
                raise DecompilerError(
                    f"element-bucket product {product!r} must be the unit bucket with its "
                    f"quantity in its multiplicity (canonical bucket spelling)"
                )
            instances += mult

        if instances < 2:
            raise DecompilerError(
                "a decomposition must have at least two product instances; one product of the "
                "same size is a rename, not a decomposition"
            )

        # products must be a sorted, deduplicated multiset (canonical order + no split entries)
        keys = [(_sort_key(p), m) for p, m in self.products]
        if keys != sorted(keys):
            raise ValueError("products must be sorted canonically (use admissible_edges)")
        pset = [p for p, _ in self.products]
        if len(pset) != len(set(pset)):
            raise ValueError("a product species appears twice; merge its multiplicities")

        # conservation, element by element (and no product introduces a foreign element)
        want = {s: self.reactant_multiplicity * k for s, k in self.reactant.counts}
        got: dict[str, int] = {}
        for product, mult in self.products:
            for s, k in product.counts:
                got[s] = got.get(s, 0) + mult * k
        if got != want:
            raise DecompilerError(
                f"mass not conserved: {self.reactant_multiplicity} . {self.reactant!r} carries "
                f"{want} but products carry {got}"
            )

        # primitivity -- the canonical representative of the scaled family
        scale = _multi_gcd((self.reactant_multiplicity,) + tuple(m for _, m in self.products))
        if scale != 1:
            raise DecompilerError(
                f"edge is not primitive (common factor {scale}); divide all coefficients so "
                f"the edge is the canonical representative of its family"
            )

    @property
    def is_elemental_floor(self) -> bool:
        """True iff every product is an element bucket -- the direct-to-elements step."""
        return all(p.is_element for p, _ in self.products)

    def equation(self) -> str:
        def term(mult: int, formula: Formula) -> str:
            return f"{mult} {formula!r}" if mult > 1 else repr(formula)
        lhs = term(self.reactant_multiplicity, self.reactant)
        rhs = " + ".join(term(m, p) for p, m in self.products)
        return f"{lhs} -> {rhs}"

    def __repr__(self) -> str:
        return f"DecompositionEdge({self.equation()})"


# ======================================================================================
# B1 -- the balanced-edge generator over a closed inventory
# ======================================================================================
def admissible_edges(
    reactant: Formula,
    inventory: tuple[Formula, ...] = (),
    *,
    max_multiplicity: int = 1,
    budget: int = 100_000,
) -> tuple[tuple[DecompositionEdge, ...], bool]:
    """Every primitive conserving decomposition of ``reactant`` over a closed inventory.

    The search branches only over the *molecular* candidates -- the declared intermediates of
    strictly lower rank whose elements are a subset of the reactant's.  Every sub-multiset of
    molecules that fits under ``n . reactant`` is closed by **forcing** the leftover atoms into
    unit element buckets (which is always possible in exactly one way), so element buckets are
    never search variables and the enumeration cost is the true solution count, not a cloud of
    dead partial-bucket branches.  Solutions with at least two product instances are reduced to
    their primitive representative and deduplicated; a combination that would grow a product
    (only reachable at ``n > 1``) is dropped by the edge's own descent guard.

    ``max_multiplicity`` is the largest reactant coefficient ``n`` tried.  ``n = 1`` (the
    default) already yields the atom-bucket elemental floor and every whole-number molecular
    split; ``n > 1`` adds fraction-clearing scaled edges and multiplies the search space -- an
    opt-in knob, and a stated completeness boundary either way.

    Returns ``(edges, complete)``.  ``complete`` is ``False`` iff the search hit ``budget`` --
    the edge tuple is then a *partial* result the caller must not read as complete (W2: a
    truncated search is never silently a full one).
    """
    if type(reactant) is not Formula:
        raise TypeError("reactant must be a Formula")
    if type(max_multiplicity) is not int or max_multiplicity <= 0:
        raise ValueError("max_multiplicity must be a positive integer")
    if type(budget) is not int or budget <= 0:
        raise ValueError("budget must be a positive integer")
    if reactant.charge != 0:
        raise DecompilerError("v1 decomposes neutral species only")
    if reactant.is_element:
        return (), True  # an element bucket is terminal: no decomposition

    r_rank = reactant.rank
    r_elements = reactant.elements
    molecular: list[Formula] = []
    for species in inventory:
        if type(species) is not Formula:
            raise TypeError("inventory must contain Formula values")
        if (
            species.charge == 0
            and 0 < species.rank < r_rank
            and species.elements <= r_elements
            and not species.is_element  # a single-element inventory entry is just a bucket
        ):
            molecular.append(species)
    # deterministic order (largest first prunes faster and stabilises output)
    molecular = sorted(set(molecular), key=lambda f: (-f.rank, _sort_key(f)))

    edges: dict[str, DecompositionEdge] = {}
    work = [0]  # single-cell mutable search-node counter (budget meter, W2)

    def register(n: int, target: dict[str, int], chosen: list[tuple[Formula, int]]) -> None:
        # close this molecular prefix: the leftover atoms are forced into unit buckets
        merged: dict[Formula, int] = {}
        for formula, m in chosen:
            merged[formula] = merged.get(formula, 0) + m
        for symbol, left in target.items():
            if left:
                merged[Formula.bucket(symbol)] = merged.get(Formula.bucket(symbol), 0) + left
        if sum(merged.values()) < 2:
            return  # a single product of the same size is a rename, not a decomposition
        products = tuple(sorted(merged.items(), key=lambda pm: (_sort_key(pm[0]), pm[1])))
        scale = _multi_gcd((n,) + tuple(m for _, m in products))
        try:
            edge = DecompositionEdge(
                reactant, n // scale, tuple((p, m // scale) for p, m in products)
            )
        except DecompilerError:
            return  # a non-descending combination (only reachable at n > 1) is dropped
        edges[edge.digest] = edge

    def solve(n: int, target: dict[str, int], start: int, chosen: list[tuple[Formula, int]]) -> bool:
        """Every molecular prefix in index order closes to one edge. False iff budget hit."""
        work[0] += 1
        if work[0] > budget:
            return False
        register(n, target, chosen)  # every prefix (including the empty one) is a solution
        for idx in range(start, len(molecular)):
            cand = molecular[idx]
            cap = min(target.get(s, 0) // k for s, k in cand.counts)
            if cap <= 0:
                continue
            for m in range(cap, 0, -1):
                nxt = dict(target)
                for s, k in cand.counts:
                    nxt[s] -= m * k
                chosen.append((cand, m))
                if not solve(n, nxt, idx + 1, chosen):
                    chosen.pop()
                    return False
                chosen.pop()
        return True

    complete = True
    for n in range(1, max_multiplicity + 1):
        if not solve(n, {s: n * k for s, k in reactant.counts}, 0, []):
            complete = False
            break

    ordered = tuple(sorted(edges.values(), key=_edge_key))
    return ordered, complete


# ======================================================================================
# B2 -- the AND-OR DAG builder, with a loud budget refusal (never a silent partial)
# ======================================================================================
@dataclass(frozen=True)
class DecompositionGraph(Digestible):
    """The full presentation-invariant decomposition hypergraph of one target.

    ``edges`` collects every admissible edge over every non-terminal node reached from the
    target (the AND-OR DAG: nodes are compounds, hyperedges their alternative decompositions,
    leaves are element buckets or declared inventory buckets).  ``status`` is ``COMPLETE`` only when the whole reachable
    graph was built within budget; ``REFUSED_BUDGET`` carries a partial ``edges`` and a reason,
    and must never be read as a complete enumeration (W2).
    """

    schema_version: str
    target: Formula
    inventory: tuple[Formula, ...]
    max_multiplicity: int
    budget: int
    status: str
    edges: tuple[DecompositionEdge, ...]
    refusal_reason: str = field(default="")

    _STATUSES = ("COMPLETE", "REFUSED_BUDGET")

    def __post_init__(self) -> None:
        if self.schema_version != DECOMPILER_SCHEMA:
            raise ValueError(f"schema_version must be exactly {DECOMPILER_SCHEMA!r}")
        if type(self.target) is not Formula:
            raise TypeError("target must be a Formula")
        if self.status not in self._STATUSES:
            raise ValueError(f"status must be one of {self._STATUSES}")
        if self.status == "COMPLETE" and self.refusal_reason:
            raise ValueError("a COMPLETE graph carries no refusal reason")
        if self.status == "REFUSED_BUDGET" and not self.refusal_reason:
            raise ValueError("a REFUSED_BUDGET graph must state its reason")
        if any(type(e) is not DecompositionEdge for e in self.edges):
            raise TypeError("edges must be DecompositionEdge values")
        if any(e.reactant.charge != 0 for e in self.edges):
            raise DecompilerError("graph edges must be neutral")

    @property
    def is_complete(self) -> bool:
        return self.status == "COMPLETE"

    def nodes(self) -> frozenset[Formula]:
        seen: set[Formula] = {self.target}
        for edge in self.edges:
            seen.add(edge.reactant)
            for product, _ in edge.products:
                seen.add(product)
        return frozenset(seen)

    def terminals(self) -> frozenset[Formula]:
        declared = set(self.inventory)
        return frozenset(n for n in self.nodes() if n.is_element or n in declared)

    def edges_from(self, node: Formula) -> tuple[DecompositionEdge, ...]:
        return tuple(e for e in self.edges if e.reactant == node)

    @property
    def identity(self) -> str:
        """Presentation-invariant digest of the whole graph (the ``digest`` of the value)."""
        return self.digest


@dataclass(frozen=True)
class FormulaSearchReceipt(Digestible):
    """Auditable termination facts for one formula-decomposition graph search.

    The formula sibling of :class:`~smartchem.experiment.routes.RouteSearchReceipt` /
    :class:`~smartchem.experiment.routes.DAGSearchReceipt`, over the shared :class:`~smartchem.search.SearchStatus`
    vocabulary.  The elemental descent is well-founded (W1) so it always REACHES the element/inventory buckets;
    the only ways it stops short are the two W2 budgets -- the per-node search-node ``budget`` and the whole-graph
    ``max_edges`` cap -- and this receipt names which one bit (``PARTIAL_SEARCH_BUDGET`` vs ``PARTIAL_RESULT_LIMIT``)
    so a partial graph is never read as a complete enumeration.  ``COMPLETE_WITHIN_BOUNDS`` is exhaustive only
    within the declared closed inventory and multiplicity; it is not a claim about chemistry (W3).
    """

    schema_version: str
    max_multiplicity: int
    budget: int
    max_edges: int
    edges_emitted: int
    status: SearchStatus
    stop_reason: str
    # -- section 8.1 telemetry (added v1alpha2). Formula-shaped: each admissible decomposition edge IS one
    # transform application (one candidate), and edges_emitted is the DISTINCT collected result -- so
    # transforms_considered (pre-dedup) >= edges_emitted. Every counter is a real measurement or an explicit
    # UNKNOWN (None); search_kind/cut_budget_scope are constants for the elemental descent.
    search_kind: str = "FORMULA_DECOMPOSITION"
    cut_budget_scope: str = "PER_NODE"          # the search-node `budget` is spent per decomposition node
    nodes_visited: "int | None" = None          # frontier pops (incl. terminals popped and skipped)
    transforms_considered: "int | None" = None  # admissible edges produced across all expanded nodes (pre-dedup)
    candidates_rejected_by_reason: tuple[tuple[str, int], ...] = ()  # sorted (reason, positive count): duplicate/...

    def __post_init__(self) -> None:
        if self.schema_version != FORMULA_SEARCH_RECEIPT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {FORMULA_SEARCH_RECEIPT_SCHEMA!r}")
        for name in ("max_multiplicity", "budget", "max_edges"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.edges_emitted) is not int or self.edges_emitted < 0:
            raise ValueError("edges_emitted must be a non-negative integer")
        if not isinstance(self.status, SearchStatus):
            raise TypeError("status must be a SearchStatus")
        if type(self.stop_reason) is not str:
            raise TypeError("stop_reason must be a string")
        if self.status is SearchStatus.COMPLETE_WITHIN_BOUNDS and self.stop_reason:
            raise ValueError("a complete search carries no stop reason")
        if self.status is not SearchStatus.COMPLETE_WITHIN_BOUNDS and not self.stop_reason:
            raise ValueError("a partial search must state its stop reason")
        if self.status is SearchStatus.PARTIAL_MULTIPLE_LIMITS:
            raise ValueError(
                "the formula descent stops on exactly one budget at a time; PARTIAL_MULTIPLE_LIMITS is not "
                "reachable here"
            )
        self._validate_section_8_1_telemetry()

    def _validate_section_8_1_telemetry(self) -> None:
        if not isinstance(self.search_kind, str) or not self.search_kind:
            raise ValueError("search_kind must be a non-empty string")
        if self.cut_budget_scope not in ("PER_NODE", "GLOBAL"):
            raise ValueError("cut_budget_scope must be one of ('PER_NODE', 'GLOBAL')")
        for name in ("nodes_visited", "transforms_considered"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be None (UNKNOWN) or a non-negative integer")
        if self.transforms_considered is not None and self.transforms_considered < self.edges_emitted:
            raise ValueError("transforms_considered cannot be fewer than edges_emitted (pre-dedup >= distinct)")
        if type(self.candidates_rejected_by_reason) is not tuple:
            raise TypeError("candidates_rejected_by_reason must be a tuple of (reason, count) pairs")
        seen_reasons: set[str] = set()
        prev: "str | None" = None
        for pair in self.candidates_rejected_by_reason:
            if type(pair) is not tuple or len(pair) != 2:
                raise TypeError("each candidates_rejected_by_reason entry must be a (reason, count) pair")
            reason, count = pair
            if not isinstance(reason, str) or not reason:
                raise ValueError("a rejection reason must be a non-empty string")
            if type(count) is not int or count <= 0:
                raise ValueError(f"rejection count for {reason!r} must be a positive int (drop zero-count reasons)")
            if reason in seen_reasons:
                raise ValueError(f"rejection reason {reason!r} appears twice; reasons must be distinct")
            if prev is not None and reason < prev:
                raise ValueError("candidates_rejected_by_reason must be sorted by reason (canonical order)")
            seen_reasons.add(reason)
            prev = reason

    @property
    def complete_within_bounds(self) -> bool:
        return self.status is SearchStatus.COMPLETE_WITHIN_BOUNDS

    def render(self) -> str:
        def _n(v: "int | None") -> str:
            return "UNKNOWN" if v is None else str(v)
        reason = f"{self.stop_reason} " if self.stop_reason else ""
        rejected = ", ".join(f"{r}={c}" for r, c in self.candidates_rejected_by_reason) or "none"
        return (
            f"FORMULA SEARCH RECEIPT ({self.search_kind}): {self.status.value}; edges={self.edges_emitted}; "
            f"nodes visited={_n(self.nodes_visited)}; transforms considered={_n(self.transforms_considered)}; "
            f"rejected[{rejected}]; search-node budget={self.budget} ({self.cut_budget_scope}); "
            f"edge cap={self.max_edges}; max multiplicity={self.max_multiplicity}. {reason}"
            "Scope: primitive conserving decompositions over the declared closed inventory; conservation only, "
            "not chemistry."
        )


@dataclass(frozen=True)
class DecompositionSearchResult(Digestible):
    """A decomposition graph plus its explicit completeness receipt (standard section 8.1).

    The receipt-bearing sibling of :func:`build_decomposition`: :func:`search_decomposition` returns this, while
    ``build_decomposition`` stays the graph-only compatibility wrapper.  The graph already carries a loud
    ``COMPLETE``/``REFUSED_BUDGET`` status; the receipt lifts that into the shared :class:`SearchStatus`
    vocabulary with counters, so the formula path answers the same auditable question as the route and DAG
    searches.
    """

    schema_version: str
    graph: DecompositionGraph
    receipt: FormulaSearchReceipt

    def __post_init__(self) -> None:
        if self.schema_version != DECOMPOSITION_SEARCH_RESULT_SCHEMA:
            raise ValueError(f"schema_version must be exactly {DECOMPOSITION_SEARCH_RESULT_SCHEMA!r}")
        if type(self.graph) is not DecompositionGraph:
            raise TypeError("graph must be a DecompositionGraph")
        if type(self.receipt) is not FormulaSearchReceipt:
            raise TypeError("receipt must be a FormulaSearchReceipt")
        if self.receipt.complete_within_bounds != self.graph.is_complete:
            raise ValueError("receipt completeness must agree with the graph status")
        if self.receipt.edges_emitted != len(self.graph.edges):
            raise ValueError("receipt.edges_emitted must equal the number of graph edges")


def search_decomposition(
    target: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    max_multiplicity: int = 1,
    budget: int = 100_000,
    max_edges: int = 5_000,
) -> DecompositionSearchResult:
    """Build the elemental-descent hypergraph of ``target`` and return it plus an explicit completeness receipt.

    The receipt-bearing form of :func:`build_decomposition`, exactly as
    :func:`~smartchem.experiment.routes.search_routes` is to ``enumerate_routes``.  It instruments the same graph
    descent -- adding a ``nodes_expanded`` counter and mapping the graph's own ``COMPLETE``/``REFUSED_BUDGET``
    status onto the shared :class:`~smartchem.search.SearchStatus` vocabulary -- so the formula path returns a
    first-class receipt (standard section 8.1) like the route and DAG searches do.

    ``target`` and ``inventory`` accept formula strings, atom-count mappings, or ``Formula`` values. Inventory
    species are terminal buckets: they may be products but are not expanded further.  The descent is well-founded
    (W1), so it reaches declared stock or element buckets; the only non-completion is a **loud** partial result
    when the graph exceeds ``budget`` search nodes (``PARTIAL_SEARCH_BUDGET``) or ``max_edges`` collected edges
    (``PARTIAL_RESULT_LIMIT``) (W2) -- the returned partial graph says so in its status and receipt and is never a
    silent truncation.
    """
    target_f = _coerce(target)
    inv = tuple(sorted(set(_coerce(s) for s in inventory), key=_sort_key))
    if target_f.charge != 0:
        raise DecompilerError("v1 decomposes neutral targets only")
    for name, value in (
        ("max_multiplicity", max_multiplicity), ("budget", budget), ("max_edges", max_edges)
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")

    collected: dict[str, DecompositionEdge] = {}
    expanded: set[Formula] = set()
    frontier: list[Formula] = [target_f]
    work_budget = [budget]
    # section 8.1 telemetry (read by _result via closure at each return point)
    nodes_visited = 0
    transforms_considered = 0
    rejected: dict[str, int] = {}

    def _result(status: SearchStatus, reason: str) -> DecompositionSearchResult:
        graph_status = "COMPLETE" if status is SearchStatus.COMPLETE_WITHIN_BOUNDS else "REFUSED_BUDGET"
        graph = DecompositionGraph(
            DECOMPILER_SCHEMA, target_f, inv, max_multiplicity, budget,
            graph_status, tuple(sorted(collected.values(), key=_edge_key)), reason,
        )
        receipt = FormulaSearchReceipt(
            FORMULA_SEARCH_RECEIPT_SCHEMA, max_multiplicity, budget, max_edges,
            len(graph.edges), status, reason,
            nodes_visited=nodes_visited,
            transforms_considered=transforms_considered,
            candidates_rejected_by_reason=tuple(sorted(rejected.items())),
        )
        return DecompositionSearchResult(DECOMPOSITION_SEARCH_RESULT_SCHEMA, graph, receipt)

    while frontier:
        node = frontier.pop()
        nodes_visited += 1  # this node was visited even if it is a terminal we skip
        if node in expanded or node.is_element or node in inv:
            expanded.add(node)
            continue
        node_edges, complete = admissible_edges(
            node, inv, max_multiplicity=max_multiplicity, budget=work_budget[0]
        )
        if not complete:
            return _result(
                SearchStatus.PARTIAL_SEARCH_BUDGET,
                f"search budget exhausted while decomposing {node!r}; graph is partial",
            )
        expanded.add(node)
        for edge in node_edges:
            transforms_considered += 1                       # each admissible edge is one transform application
            if edge.digest in collected:
                rejected["duplicate"] = rejected.get("duplicate", 0) + 1  # same edge reached via another node
            collected[edge.digest] = edge
            if len(collected) > max_edges:
                # the edge cap stopped enumeration; the incompleteness is carried by the status, not a per-edge
                # rejection count (we simply stop collecting -- an unknown number of future edges are dropped).
                return _result(
                    SearchStatus.PARTIAL_RESULT_LIMIT,
                    f"edge budget ({max_edges}) exceeded; graph is partial",
                )
            for product, _ in edge.products:
                if product not in expanded and not product.is_element and product not in inv:
                    frontier.append(product)

    return _result(SearchStatus.COMPLETE_WITHIN_BOUNDS, "")


def build_decomposition(
    target: "str | dict[str, int] | Formula",
    inventory: "tuple[Formula, ...] | tuple[str, ...]" = (),
    *,
    max_multiplicity: int = 1,
    budget: int = 100_000,
    max_edges: int = 5_000,
) -> DecompositionGraph:
    """Build the elemental-descent hypergraph of ``target`` over a closed ``inventory`` (graph only).

    Compatibility wrapper returning just the :class:`DecompositionGraph`; use :func:`search_decomposition` for the
    completeness receipt.  The graph still carries its own loud ``COMPLETE``/``REFUSED_BUDGET`` status and reason,
    so a graph-only caller is not deprived of the completeness truth -- only of the shared-vocabulary counters.
    """
    return search_decomposition(
        target, inventory, max_multiplicity=max_multiplicity, budget=budget, max_edges=max_edges
    ).graph


def _coerce(value: "str | dict[str, int] | Formula") -> Formula:
    if isinstance(value, Formula):
        return value
    if isinstance(value, str):
        return Formula.parse(value)
    if isinstance(value, dict):
        return Formula.of(value)
    raise TypeError(f"cannot coerce {type(value).__name__} to a Formula")


def _edge_key(edge: DecompositionEdge) -> tuple:
    return (
        _sort_key(edge.reactant),
        edge.reactant_multiplicity,
        tuple((_sort_key(p), m) for p, m in edge.products),
    )


# ======================================================================================
# Reporting layer -- the "keep the 2 coherent" bucket packaging (decision 4)
# ======================================================================================
def standard_state_equation(target: Formula, count: int = 1) -> str:
    """The target's direct-to-elements equation in conventional molecular packaging.

    Repackages the forced atom buckets into their reference molecular forms (``H2``, ``O2``,
    ...), scaling the whole equation by the minimal integer so every bucket is a whole number
    of reference molecules -- the coherent "2 part" bookkeeping.  This is a reporting
    convenience over conservation, not a physical standard-state or reaction claim.
    """
    if type(count) is not int or count <= 0:
        raise ValueError("count must be a positive integer")
    if target.is_element:
        return repr(target)
    # minimal integer scale s so every bucket is a whole number of reference molecules.
    # each element needs count*atoms*s divisible by its molecularity; the least common
    # multiple of the per-element requirements is that minimal s.
    s = 1
    for symbol, atoms in target.counts:
        mol = _REFERENCE_MOLECULARITY.get(symbol, 1)
        need = mol // gcd(mol, count * atoms)  # extra factor this element demands
        s = s * need // gcd(s, need)
    lhs_n = count * s
    lhs = f"{lhs_n} {target!r}" if lhs_n > 1 else repr(target)
    terms = []
    for symbol, atoms in target.counts:
        mol = _REFERENCE_MOLECULARITY.get(symbol, 1)
        molecules = (count * atoms * s) // mol
        form = f"{symbol}{mol}" if mol > 1 else symbol
        terms.append(f"{molecules} {form}" if molecules > 1 else form)
    return f"{lhs} -> {' + '.join(terms)}"


def example_inventory() -> tuple[Formula, ...]:
    """A small, generic inventory of common small molecules for demos and tests.

    Deliberately not a claim about which decompositions are real -- just a set of low-rank
    C/H/N/O species over which the routing becomes non-trivial.  Callers declare their own
    inventory in practice (closed-inventory v1).
    """
    return tuple(
        Formula.parse(f)
        for f in ("H2O", "CO", "CO2", "CH4", "NH3", "NO", "N2O", "C2H6", "C2H4", "HCN", "H2O2")
    )
