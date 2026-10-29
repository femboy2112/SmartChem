"""Read-only projections from certified SmartChem search objects to typed graph data.

This is a PRESENTATION seam, not a reaction engine.  It neither searches nor ranks,
and it does not promote a formal candidate into a sourced or executable synthesis.

The bipartite incidence graph preserves AND/OR alternatives, occurrence identity and
stoichiometric multiplicity; it is not a claim about lot allocation or material flow.
No additional rendering dependency is required.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import html
import json

GRAPH_PROJECTION_SCHEMA = "smartchem/graph-projection-v0a1"


class GraphProjectionError(ValueError):
    """A graph would misrepresent its source object or exceed an explicit limit."""


def _id(prefix: str, value: str) -> str:
    return prefix + ":" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _attrs(**items: object) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(value)) for key, value in items.items()))


def _check_attrs(attrs: tuple[tuple[str, str], ...]) -> None:
    if type(attrs) is not tuple or any(
        type(item) is not tuple or len(item) != 2
        or any(type(value) is not str for value in item)
        for item in attrs
    ):
        raise GraphProjectionError("attributes must be tuple[str, str] pairs")
    keys = [key for key, _ in attrs]
    if keys != sorted(set(keys)):
        raise GraphProjectionError("attribute keys must be distinct and sorted")


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str  # species | reaction
    label: str
    attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.id or self.kind not in ("species", "reaction") or type(self.label) is not str:
            raise GraphProjectionError("invalid graph node id/kind/label")
        _check_attrs(self.attributes)

    def to_payload(self) -> dict:
        return dict(id=self.id, kind=self.kind, label=self.label,
                    attributes=dict(self.attributes))


@dataclass(frozen=True)
class GraphArc:
    source: str
    target: str
    role: str  # consumes (species->reaction) | produces (reaction->species)
    multiplicity: int
    attributes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.source or not self.target or self.role not in ("consumes", "produces"):
            raise GraphProjectionError("invalid graph arc endpoints/role")
        if type(self.multiplicity) is not int or self.multiplicity < 1:
            raise GraphProjectionError("arc multiplicity must be an integer >= 1")
        _check_attrs(self.attributes)

    def key(self) -> tuple:
        return (self.source, self.target, self.role, self.multiplicity, self.attributes)

    def to_payload(self) -> dict:
        return dict(source=self.source, target=self.target, role=self.role,
                    multiplicity=self.multiplicity, attributes=dict(self.attributes))


@dataclass(frozen=True)
class ChemicalGraphProjection:
    source_kind: str
    source_digest: str
    target_id: str
    search_status: str
    receipt_digest: str | None
    nodes: tuple[GraphNode, ...]
    arcs: tuple[GraphArc, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = GRAPH_PROJECTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != GRAPH_PROJECTION_SCHEMA:
            raise GraphProjectionError("unsupported graph projection schema")
        if self.source_kind not in ("FORMULA_DECOMPOSITION", "SYNTHESIS_ROUTE", "SYNTHESIS_DAG",
                                     "SYNTHESIS_ROUTE_ENSEMBLE", "SYNTHESIS_DAG_ENSEMBLE"):
            raise GraphProjectionError("unknown graph source kind")
        if not self.source_digest or not self.search_status:
            raise GraphProjectionError("source digest/status must be present")
        if self.receipt_digest is not None and not self.receipt_digest:
            raise GraphProjectionError("receipt digest must be nonempty or None")
        if type(self.nodes) is not tuple or type(self.arcs) is not tuple:
            raise GraphProjectionError("nodes/arcs must be immutable tuples")
        ids = [node.id for node in self.nodes]
        if ids != sorted(set(ids)):
            raise GraphProjectionError("nodes must have unique sorted ids")
        lookup = {node.id: node for node in self.nodes}
        if self.target_id not in lookup or lookup[self.target_id].kind != "species":
            raise GraphProjectionError("target must name a species node")
        keys = [arc.key() for arc in self.arcs]
        if keys != sorted(set(keys)):
            raise GraphProjectionError("arcs must be distinct and canonically ordered")
        # One incidence per (source, target, role): multiplicity belongs on that
        # incidence, not in duplicate parallel records that double-count it.
        incidence_keys = [(a.source, a.target, a.role) for a in self.arcs]
        if len(incidence_keys) != len(set(incidence_keys)):
            raise GraphProjectionError("duplicate incidence between the same ports")
        incidence: dict[str, set[str]] = {
            node.id: set() for node in self.nodes if node.kind == "reaction"
        }
        for arc in self.arcs:
            if arc.source not in lookup or arc.target not in lookup:
                raise GraphProjectionError("arc endpoint not in node set")
            source, target = lookup[arc.source], lookup[arc.target]
            if arc.role == "consumes":
                if source.kind != "species" or target.kind != "reaction":
                    raise GraphProjectionError("consumes must be species -> reaction")
                incidence[target.id].add("consumes")
            else:
                if source.kind != "reaction" or target.kind != "species":
                    raise GraphProjectionError("produces must be reaction -> species")
                incidence[source.id].add("produces")
        if any(roles != {"consumes", "produces"} for roles in incidence.values()):
            raise GraphProjectionError("each reaction needs input and output incidence")
        if type(self.notes) is not tuple or any(type(s) is not str for s in self.notes):
            raise GraphProjectionError("notes must be a tuple of strings")

    def to_payload(self) -> dict:
        return dict(
            schema_version=self.schema_version,
            source_kind=self.source_kind,
            source_digest=self.source_digest,
            target_id=self.target_id,
            search_status=self.search_status,
            receipt_digest=self.receipt_digest,
            nodes=[node.to_payload() for node in self.nodes],
            arcs=[arc.to_payload() for arc in self.arcs],
            notes=list(self.notes),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))

    @property
    def digest(self) -> str:
        """Identity of this VIEW only, never a chemistry or evidence certificate."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _finish(source_kind: str, source_digest: str, target_id: str,
            search_status: str, receipt_digest: str | None,
            nodes: dict[str, GraphNode], arcs: list[GraphArc],
            notes: tuple[str, ...], max_nodes: int, max_arcs: int) -> ChemicalGraphProjection:
    if type(max_nodes) is not int or type(max_arcs) is not int or min(max_nodes, max_arcs) < 1:
        raise GraphProjectionError("max_nodes/max_arcs must be positive integers")
    if len(nodes) > max_nodes or len(arcs) > max_arcs:
        raise GraphProjectionError(
            f"projection limit exceeded (nodes={len(nodes)}/{max_nodes}, "
            f"arcs={len(arcs)}/{max_arcs}); no partial diagram was presented as complete"
        )
    return ChemicalGraphProjection(
        source_kind, source_digest, target_id, search_status, receipt_digest,
        tuple(sorted(nodes.values(), key=lambda n: n.id)),
        tuple(sorted(arcs, key=lambda a: a.key())), notes,
    )


# --- Legibility helpers: human names, conditions, reaction family (all read-only, sound-or-silent) ---
# A diagram must COMMUNICATE the chemistry without INVENTING it: every helper below either reports a
# fact the engine already holds (a registered name, a declared condition, a family whose OWN canonical
# reaction centre matches exactly) or degrades honestly (the bare formula, "unknown", a neutral
# bond-change description).  None of them promotes a formal candidate into a named/sourced reaction.

def _species_name(mol) -> str:
    """The registered chemical name of ``mol`` when known, else its bare formula.

    Uses the SAME resolver the route dossier uses (:func:`smartchem.structure.resolve_structure`); an
    unknown structure degrades to its formula -- a name is never conjured from a formula.
    """
    from .decompiler import Formula
    formula = repr(Formula.of(mol.formula, mol.charge))
    try:
        from .structure import resolve_structure
        named = resolve_structure(mol)
    except Exception:
        named = None
    return named.name if named is not None and getattr(named, "name", "") else formula


def _species_detail(mol) -> dict[str, str]:
    """Extra identity attributes for the inspector: resolved name / IUPAC / CAS where known."""
    try:
        from .structure import resolve_structure
        named = resolve_structure(mol)
    except Exception:
        named = None
    out: dict[str, str] = {}
    if named is not None:
        if getattr(named, "name", ""):
            out["chemical_name"] = named.name
        if getattr(named, "iupac", ""):
            out["iupac_name"] = named.iupac
        if getattr(named, "cas", ""):
            out["cas_number"] = named.cas
    return out


def _conditions_summary(envelope) -> str:
    """One-line human conditions, or ``'unknown'`` for an undeclared envelope.

    Honest by construction: an undeclared envelope reports UNKNOWN; it is NEVER rendered as ambient or
    default conditions (filling that gap with a default is exactly what the brief forbids).
    """
    if not getattr(envelope, "is_declared", False):
        return "unknown"
    parts = []
    for attr, prefix in (("temperature", "T="), ("pressure", "P="), ("medium", "medium="),
                         ("applied_field", "field=")):
        value = getattr(envelope, attr, None)
        if value:
            parts.append(f"{prefix}{value}")
    catalysts = getattr(envelope, "catalysts", ())
    if catalysts:
        parts.append("cat=" + ",".join(str(c) for c in catalysts))
    return ", ".join(parts) or "declared"


def _bond_change_text(center) -> str:
    """A neutral rendering of a DECLARED reaction centre (which bonds it says form/break).

    ADVISORY ONLY: ``center`` is caller-settable, forgeable metadata (ISSUE-126: ``dataclasses.replace``, a
    fake ``from_transform``, the bare constructor) and is NEVER reconstructed from the step's checked
    molecular topology. So this text describes what the centre CLAIMS, not proven chemistry -- callers must
    surface it as DECLARED/advisory and must not use it as a step's authoritative identity (that is
    :meth:`step.equation`, derived from the conserved multisets). A carbon-free ``H + H -> H2`` step wearing
    a borrowed Diels-Alder centre renders carbon bond-changes here; that is the centre lying, not the step.
    """
    if center is None:
        return ""
    glyph = {1: "-", 2: "=", 3: "#"}

    def fmt(changes) -> str:
        counts = Counter((a, b, o) for a, b, o in changes)
        parts = [f"{n}×{a}{glyph.get(o, '?')}{b}" if n > 1 else f"{a}{glyph.get(o, '?')}{b}"
                 for (a, b, o), n in sorted(counts.items())]
        return ", ".join(parts) or "—"

    return f"forms {fmt(center.formed)}; breaks {fmt(center.broken)}"


def _reaction_family_for_step(step) -> str | None:
    """The named reaction family of a whole STEP, from the reaction-type oracle's INDEPENDENT
    re-derivation -- NEVER from reaction-centre equality alone (ISSUE-128).

    The oracle names a class ONLY after re-deriving it from the step's own molecules: for the pericyclic
    families (the Diels-Alder zoo, [3,3]-sigmatropics, electrocyclizations) a guarded retro-disconnection
    of the adduct back into exactly these reactants (Layer A); for the dehydrative condensations (acyl,
    etherification, N-alkylation) a conservation-locked whole-molecule census.  Post ISSUE-126/132 the reaction
    centre is NOT read at all -- recognition is a pure function of the step's conserved molecules.
    A balanced step that merely CARRIES a copy of a family's canonical centre (e.g. a synthetic
    H + H -> H2 wearing a borrowed Diels-Alder centre) is NOT named, because the oracle's Layer-A
    re-derivation abstains.  The previous centre-equality table named such a step from the centre alone;
    that path is removed, so the graph now agrees with the oracle on every step and never names chemistry
    it cannot defend.  An unnamed step shows its neutral :func:`_bond_change_text` instead.
    """
    try:
        from .experiment.reaction_type_oracle import recognize_reaction_type
        return recognize_reaction_type(step) or None
    except Exception:
        return None


def project_decomposition(value, *, max_nodes: int = 20_000,
                          max_arcs: int = 40_000) -> ChemicalGraphProjection:
    """Project ALL returned formula edges (or a loudly partial graph), including OR alternatives.

    Accepts DecompositionSearchResult (preferred: preserves section-8.1 receipt)
    or DecompositionGraph. Formula transformations are accounting identities ONLY.
    """
    from .decompiler import DecompositionGraph, DecompositionSearchResult

    if type(value) is DecompositionSearchResult:
        graph, receipt = value.graph, value.receipt
        search_status, receipt_digest = receipt.status.value, receipt.digest
    elif type(value) is DecompositionGraph:
        graph, receipt = value, None
        search_status, receipt_digest = graph.status, None
    else:
        raise TypeError("expected DecompositionSearchResult or DecompositionGraph")

    expanded = {edge.reactant for edge in graph.edges}
    terminal = graph.terminals()
    nodes: dict[str, GraphNode] = {}
    arcs: list[GraphArc] = []
    for formula in graph.nodes():
        fid = "f:" + formula.digest
        boundary = (
            "terminal" if formula in terminal
            else "unexpanded" if formula not in expanded
            else "expanded"
        )
        nodes[fid] = GraphNode(fid, "species", repr(formula),
                               _attrs(identity_layer="FORMULA", boundary=boundary,
                                      formula_digest=formula.digest))
    for edge in graph.edges:
        reaction_id = "r:" + edge.digest
        nodes[reaction_id] = GraphNode(
            reaction_id, "reaction", edge.equation(),
            _attrs(reaction_semantics="ACCOUNTING_ONLY", edge_digest=edge.digest),
        )
        arcs.append(GraphArc("f:" + edge.reactant.digest, reaction_id,
                             "consumes", edge.reactant_multiplicity))
        for product, count in edge.products:
            arcs.append(GraphArc(reaction_id, "f:" + product.digest, "produces", count))
    return _finish(
        "FORMULA_DECOMPOSITION", graph.digest, "f:" + graph.target.digest,
        search_status, receipt_digest, nodes, arcs,
        ("Every alternative decomposition is included if the source search completed.",
         "These are atom-balanced formula partitions, NOT verified chemical reactions.",
         "A source search stopped by a budget remains incomplete in this visualization."),
        max_nodes, max_arcs,
    )


def project_synthesis(route, *, search_result=None, max_nodes: int = 20_000,
                      max_arcs: int = 40_000) -> ChemicalGraphProjection:
    """Project ONE existing linear route or convergent DAG without re-searching.

    Optional search_result must contain the exact route/DAG and bind the target.
    Otherwise search_status is UNATTESTED; no search-completeness claim is made.
    """
    from .decompiler import Formula
    from .experiment.dag import SynthesisDAG
    from .experiment.routes import DAGSearchResult, RouteSearchResult
    from .experiment.step import ExperimentRoute
    from .smiles import resonance_identity

    if type(route) is ExperimentRoute:
        kind, required_type, member = "SYNTHESIS_ROUTE", RouteSearchResult, "routes"
    elif type(route) is SynthesisDAG:
        kind, required_type, member = "SYNTHESIS_DAG", DAGSearchResult, "dags"
    else:
        raise TypeError("expected ExperimentRoute or SynthesisDAG")

    def key(molecule) -> str:
        return resonance_identity(molecule)

    if search_result is None:
        search_status, receipt_digest = "UNATTESTED", None
    else:
        if type(search_result) is not required_type:
            raise GraphProjectionError("route kind disagrees with search-result kind")
        if not any(candidate.digest == route.digest for candidate in getattr(search_result, member)):
            raise GraphProjectionError("route is not a member of the supplied search result")
        receipt = search_result.receipt
        if receipt.target_identity_digest != key(route.final_target):
            raise GraphProjectionError("search receipt target does not match route target")
        search_status, receipt_digest = receipt.status.value, receipt.digest

    molecules = {}
    for step in route.steps:
        for mol in (*step.reactants, *step.products, step.target):
            molecules.setdefault(key(mol), mol)

    nodes: dict[str, GraphNode] = {}
    arcs: list[GraphArc] = []
    produced = {key(m) for step in route.steps for m in step.products}
    consumed = {key(m) for step in route.steps for m in step.reactants}
    final_key = key(route.final_target)
    for mol_key, mol in molecules.items():
        ident = _id("s", mol_key)
        formula = repr(Formula.of(mol.formula, mol.charge))
        boundary = ("target" if mol_key == final_key else
                    "intermediate_species" if mol_key in produced and mol_key in consumed else
                    "external_input_species" if mol_key not in produced else
                    "output_species")
        name = _species_name(mol)
        # A known name labels the node; an unknown structure keeps formula+identity so two unnamed
        # isomers of one formula stay visually distinct (never collapsed to the same drawing/label).
        label = name if name != formula else f"{formula} [{ident[-8:]}]"
        nodes[ident] = GraphNode(
            ident, "species", label,
            _attrs(identity_layer="CONSTITUTION", structure_identity=mol_key,
                   formula=formula, boundary=boundary, **_species_detail(mol)),
        )

    for index, step in enumerate(route.steps):
        rid = _id("r", f"{index}:{step.digest}")
        center = getattr(step, "reaction_center", None)
        family = _reaction_family_for_step(step)
        bond_change = _bond_change_text(center)
        reagent_names = "; ".join(sorted(_species_name(m) for m in step.reagents)) or "none"
        byproduct_names = "; ".join(sorted(_species_name(m) for m in step.byproducts)) or "none"
        nodes[rid] = GraphNode(
            rid, "reaction", f"Step {index + 1}: {family or bond_change or step.equation()}",
            _attrs(step_index=index, step_digest=step.digest,
                   evidence_status="NOT_ASSESSED",
                   condition_envelope_declared=step.envelope.is_declared,
                   reaction_family=family or "", bond_change=bond_change,
                   equation=step.equation(), reagents=reagent_names,
                   conditions=_conditions_summary(step.envelope),
                   byproducts=byproduct_names),
        )
        input_counts = Counter(key(m) for m in step.reactants)
        reagent_counts = Counter(key(m) for m in step.reagents)
        output_counts = Counter(key(m) for m in step.products)
        for mol_key, count in input_counts.items():
            arcs.append(GraphArc(
                _id("s", mol_key), rid, "consumes", count,
                _attrs(ancillary_quantity=reagent_counts[mol_key]),
            ))
        for mol_key, count in output_counts.items():
            arcs.append(GraphArc(
                rid, _id("s", mol_key), "produces", count,
                _attrs(target_quantity=(count if mol_key == key(step.target) else 0)),
            ))

    return _finish(
        kind, route.digest, _id("s", final_key),
        search_status, receipt_digest, nodes, arcs,
        ("The graph shows one candidate route, not all alternative routes.",
         "Species nodes are identity classes, NOT allocated material lots or measured stream quantities.",
         "No readiness, yield, hazard safety, or bench-capability verdict was inferred here.",
         "Step occurrence IDs are distinct even when two steps have identical content."),
        max_nodes, max_arcs,
    )


def project_synthesis_ensemble(search_result, *, max_nodes: int = 20_000,
                               max_arcs: int = 40_000) -> ChemicalGraphProjection:
    """Project the FULL returned candidate ensemble (routes or DAGs) as ONE AND-OR hypergraph.

    Accepts a ``RouteSearchResult`` or ``DAGSearchResult``.  Species identity nodes merge by
    resonance constitution across candidates, so a shared precursor appears exactly once;
    reaction hyperedges merge by CONTENT digest and each carries the set of candidate indices
    that use it (attribute ``candidates``) plus every (candidate:position) occurrence
    (``occurrences``).  Alternative reactions producing the same species are therefore visible
    OR-branches, multi-precursor reactions are AND-dependencies, and every individual candidate
    boundary is exactly recoverable from the membership attribute -- no candidate is flattened
    into another.  This is the content-merged OR view; :func:`project_synthesis` remains the
    occurrence-distinct single-candidate view.  Search completeness is the receipt's: a partial
    search omits candidates that are simply not present here.
    """
    from .decompiler import Formula
    from .experiment.routes import DAGSearchResult, RouteSearchResult
    from .smiles import resonance_identity

    if type(search_result) is RouteSearchResult:
        kind, members = "SYNTHESIS_ROUTE_ENSEMBLE", search_result.routes
    elif type(search_result) is DAGSearchResult:
        kind, members = "SYNTHESIS_DAG_ENSEMBLE", search_result.dags
    else:
        raise TypeError("expected RouteSearchResult or DAGSearchResult")

    def key(mol) -> str:
        return resonance_identity(mol)

    receipt = search_result.receipt
    target_key = receipt.target_identity_digest
    target_id = _id("s", target_key)

    if not members:
        # An exhaustive-but-empty search is a real result, not a crash: show the lone target.
        node = GraphNode(target_id, "species", f"target [{target_id[-8:]}]",
                         _attrs(identity_layer="CONSTITUTION", structure_identity=target_key,
                                boundary="external_input_species", candidates=""))
        note = ("The search returned no candidates within its bounds; "
                f"target_in_terminal_stock={getattr(search_result, 'target_in_terminal_stock', False)}.",)
        return _finish(kind, search_result.digest, target_id, receipt.status.value,
                       receipt.digest, {target_id: node}, [], note, max_nodes, max_arcs)

    # Fail closed exactly as project_synthesis does on the single route: the receipt's target must
    # be EVERY candidate's final target.  A guard that holds on one layer and not its sibling is the
    # fallback-layer leak -- a forged/inconsistent receipt must never silently mislabel a precursor
    # as the target.
    if any(key(candidate.final_target) != target_key for candidate in members):
        raise GraphProjectionError("ensemble receipt target disagrees with a candidate's final target")

    mols: dict[str, object] = {}
    reactions: dict[str, dict] = {}  # reaction_id -> {step, members:set[int], occ:list[(int,int)]}
    for cand_index, candidate in enumerate(members):
        for step_index, step in enumerate(candidate.steps):
            for mol in (*step.reactants, *step.products, step.target):
                mols.setdefault(key(mol), mol)
            rid = _id("r", step.digest)
            entry = reactions.setdefault(rid, {"step": step, "members": set(), "occ": []})
            entry["members"].add(cand_index)
            entry["occ"].append((cand_index, step_index))

    produced = {key(m) for e in reactions.values() for m in e["step"].products}
    consumed = {key(m) for e in reactions.values() for m in e["step"].reactants}
    species_members: dict[str, set] = {k: set() for k in mols}
    for e in reactions.values():
        for m in (*e["step"].reactants, *e["step"].products):
            species_members[key(m)] |= e["members"]

    nodes: dict[str, GraphNode] = {}
    arcs_by_port: dict[tuple, GraphArc] = {}
    for mol_key, mol in mols.items():
        ident = _id("s", mol_key)
        formula = repr(Formula.of(mol.formula, mol.charge))
        boundary = ("target" if mol_key == target_key else
                    "intermediate_species" if mol_key in produced and mol_key in consumed else
                    "external_input_species" if mol_key not in produced else
                    "output_species")
        nodes[ident] = GraphNode(
            ident, "species", f"{formula} [{ident[-8:]}]",
            _attrs(identity_layer="CONSTITUTION", structure_identity=mol_key,
                   formula=formula, boundary=boundary,
                   candidates=",".join(str(i) for i in sorted(species_members[mol_key]))),
        )
    for rid, e in reactions.items():
        step = e["step"]
        nodes[rid] = GraphNode(
            # The formula-level equation collides across constitutional isomers (n- vs iso-propanol
            # esterification print identically); the content-digest suffix keeps distinct reactions
            # visually distinct in EVERY format, not just in JSON/HTML attributes.
            rid, "reaction", f"{step.equation()}  [{step.digest[:8]}]",
            _attrs(step_digest=step.digest, evidence_status="NOT_ASSESSED",
                   condition_envelope_declared=step.envelope.is_declared,
                   candidates=",".join(str(i) for i in sorted(e["members"])),
                   occurrences=",".join(f"{c}:{s}" for c, s in sorted(e["occ"])),
                   candidate_count=len(e["members"])),
        )
        for mol_key, count in Counter(key(m) for m in step.reactants).items():
            arc = GraphArc(_id("s", mol_key), rid, "consumes", count)
            arcs_by_port[(arc.source, arc.target, arc.role)] = arc
        for mol_key, count in Counter(key(m) for m in step.products).items():
            arc = GraphArc(rid, _id("s", mol_key), "produces", count)
            arcs_by_port[(arc.source, arc.target, arc.role)] = arc

    return _finish(
        kind, search_result.digest, target_id, receipt.status.value, receipt.digest,
        nodes, list(arcs_by_port.values()),
        (f"Ensemble of {len(members)} returned candidate(s): shared species are one identity node; "
         "reactions merge by content and carry candidate membership.",
         "Alternative reactions producing one species are OR-branches; multi-precursor reactions "
         "are AND-dependencies.",
         "Each candidate's exact boundary is recoverable from the per-node 'candidates' attribute; "
         "no candidate is flattened into another.",
         "Search completeness is the receipt's, NOT the display's: a partial search omits candidates "
         "that are simply absent here."),
        max_nodes, max_arcs,
    )


def render_dot(graph: ChemicalGraphProjection) -> str:
    """Deterministic Graphviz DOT; safe quoting even for unusual chemical labels."""
    if type(graph) is not ChemicalGraphProjection:
        raise TypeError("graph must be a ChemicalGraphProjection")

    def quote(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    heading = f"SmartChem {graph.source_kind} | search: {graph.search_status} | source: {graph.source_digest[:12]}"
    lines = ["digraph SmartChem {", "  rankdir=LR;",
             f"  graph [label={quote(heading)},labelloc=t];"]
    for node in graph.nodes:
        shape = "box" if node.kind == "species" else "ellipse"
        # Emit the full attribute set as a hover tooltip so the SVG carries the structural identity
        # (structure_identity / step_digest / candidates) that a formula-level label cannot show --
        # DOT/SVG then carry no less than JSON, only rendered differently.
        tip = quote("; ".join(f"{key}={value}" for key, value in node.attributes) or node.kind)
        lines.append(f"  {quote(node.id)} [shape={shape},label={quote(node.label)},tooltip={tip}];")
    for arc in graph.arcs:
        label = str(arc.multiplicity) if arc.multiplicity != 1 else ""
        lines.append(f"  {quote(arc.source)} -> {quote(arc.target)} [label={quote(label)}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_mermaid(graph: ChemicalGraphProjection) -> str:
    """Deterministic Mermaid flowchart without introducing a chemistry dependency."""
    if type(graph) is not ChemicalGraphProjection:
        raise TypeError("graph must be a ChemicalGraphProjection")

    def mid(node_id: str) -> str:
        return _id("n", node_id).replace(":", "_")

    def safe(text: str) -> str:
        escaped = html.escape(text, quote=True)
        return (escaped.replace("[", "#91;").replace("]", "#93;")
                .replace("|", "#124;").replace("\n", " "))

    heading = safe(
        f"SmartChem {graph.source_kind} | search: {graph.search_status} | "
        f"source: {graph.source_digest[:12]}"
    )
    lines = ["flowchart LR", f'  subgraph graph_status["{heading}"]']
    for node in graph.nodes:
        label = safe(node.label)
        if node.kind == "reaction":
            lines.append(f'  {mid(node.id)}(["{label}"])')
        else:
            lines.append(f'  {mid(node.id)}["{label}"]')
    for arc in graph.arcs:
        if arc.multiplicity == 1:
            lines.append(f"  {mid(arc.source)} --> {mid(arc.target)}")
        else:
            lines.append(f"  {mid(arc.source)} -->|{arc.multiplicity}| {mid(arc.target)}")
    lines.append("  end")
    return "\n".join(lines) + "\n"


def _layered_layout(graph: ChemicalGraphProjection) -> dict[str, tuple[int, int]]:
    """Deterministic left-to-right layered layout (longest-path from sources, cycle-tolerant).

    No Graphviz dependency: integer (column, row) grid positions, column = longest path from a
    source node, rows assigned by the already-sorted node order.  Autocatalytic 2-cycles cannot
    strand the layout -- any node never drained to in-degree 0 is placed in a trailing column.
    """
    from collections import deque

    succ: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    indeg: dict[str, int] = {n.id: 0 for n in graph.nodes}
    for arc in graph.arcs:
        succ[arc.source].append(arc.target)
        indeg[arc.target] += 1
    layer = {nid: 0 for nid in indeg}
    remaining = dict(indeg)
    queue = deque(sorted(nid for nid, d in indeg.items() if d == 0))
    seen = set(queue)
    while queue:
        nid = queue.popleft()
        for target in sorted(succ[nid]):
            layer[target] = max(layer[target], layer[nid] + 1)
            remaining[target] -= 1
            if remaining[target] == 0 and target not in seen:
                seen.add(target)
                queue.append(target)
    trailing = max(layer.values(), default=0) + 1
    for nid in indeg:
        if nid not in seen:
            layer[nid] = trailing
    columns: dict[int, list[str]] = {}
    for node in graph.nodes:                      # graph.nodes is already id-sorted (see _finish)
        columns.setdefault(layer[node.id], []).append(node.id)
    pos: dict[str, tuple[int, int]] = {}
    for column in sorted(columns):
        for row, nid in enumerate(columns[column]):
            pos[nid] = (column, row)
    return pos


def render_svg(graph: ChemicalGraphProjection) -> str:
    """SVG via the OPTIONAL Graphviz ``dot`` backend; fails loudly (never silently) when absent.

    Graphviz is not a dependency of the chemical core: this import and process launch happen only
    when SVG is explicitly requested, and a missing ``dot`` steers the caller to the dependency-free
    dot/mermaid/html formats rather than dropping any chemistry.
    """
    import shutil
    import subprocess

    if type(graph) is not ChemicalGraphProjection:
        raise TypeError("graph must be a ChemicalGraphProjection")
    dot_bin = shutil.which("dot")
    if dot_bin is None:
        raise GraphProjectionError(
            "SVG export needs the optional Graphviz 'dot' backend (not found on PATH); the "
            "dot/mermaid/html formats need no extra dependency and carry the same topology, "
            "stoichiometry and identity tags (dot/svg expose full identity on hover)"
        )
    try:
        proc = subprocess.run([dot_bin, "-Tsvg"], input=render_dot(graph),
                              capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise GraphProjectionError(
            "graphviz dot timed out (>30s): this graph is too large/dense to lay out as SVG. The "
            "dot/mermaid/html formats need no subprocess and carry the same topology and identity."
        ) from None
    if proc.returncode != 0:
        raise GraphProjectionError(
            f"graphviz dot failed (exit {proc.returncode}): {proc.stderr.strip()[:200]}"
        )
    out = proc.stdout
    if len(out) > 32_000_000:  # ~32 MB: a pathological layout can emit unbounded SVG -- bound it
        raise GraphProjectionError(
            f"graphviz dot produced an oversized SVG ({len(out)} bytes > 32 MB cap); use the "
            "dot/mermaid/html formats for a graph this large"
        )
    return out


def _embed_json(payload: dict) -> str:
    """Serialize for a <script type=application/json> block: the ONLY sequences that can escape a
    script element are ``</`` and ``<!--``, so neutralize exactly those and nothing else."""
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return blob.replace("</", "<\\/").replace("<!--", "<\\!--")


def render_html(graph: ChemicalGraphProjection, *, max_visible_nodes: int | None = None) -> str:
    """A self-contained, offline, dependency-free HTML explorer for one projection.

    The graph is embedded as a JSON data island and parsed by the page's own vanilla JS (no markup
    interpolation, no network, no CDN).  The page offers pan/zoom, click-to-inspect, candidate-route
    highlighting, a per-node layer/attribute view, and a status banner that always states the search
    AND display completeness -- it NEVER hides nodes without saying how many were omitted, and it
    never uses color as the only carrier of scientific status (shape + text do that).
    """
    if type(graph) is not ChemicalGraphProjection:
        raise TypeError("graph must be a ChemicalGraphProjection")
    positions = _layered_layout(graph)
    total = len(graph.nodes)
    visible = total if max_visible_nodes is None else max(1, min(total, int(max_visible_nodes)))
    payload = {
        "graph": graph.to_payload(),
        "layout": {nid: list(pos) for nid, pos in positions.items()},
        "view_digest": graph.digest,
        "visible_limit": visible,
        "total_nodes": total,
    }
    data = _embed_json(payload)
    title = html.escape(f"SmartChem {graph.source_kind}")
    return _HTML_TEMPLATE.replace("__TITLE__", title).replace("__DATA__", data)


def render_scheme_html(route, *, search_result=None, depict: bool = True,
                       route_label: str | None = None) -> str:
    """Render ONE route/DAG as a drawn, step-by-step reaction SCHEME -- the chemist's reading.

    Where :func:`render_html` draws the full identity hypergraph, this lays the SAME route out as an
    ordered sequence of reaction steps read top-to-bottom: for each step the drawn precursors (plus any
    ancillary reagents) react -- under the named reaction family and its declared/UNKNOWN conditions --
    to the drawn product (plus byproducts), and a precursor made by an earlier step is cross-referenced
    to it (convergence stays convergent).  2D structures come from the OPTIONAL RDKit depiction backend;
    when it is absent (the committed baseline) every species degrades to a name/formula box and the
    scheme is still complete and readable.  It INHERITS the sound projection: search completeness is the
    receipt's (never the drawing's), membership/target binding are validated, and NO readiness, yield,
    or hazard claim is produced -- the picture communicates the chemistry, it does not invent it.
    """
    from .decompiler import Formula
    from .experiment.dag import SynthesisDAG
    from .experiment.step import ExperimentRoute
    from .smiles import resonance_identity

    if type(route) not in (ExperimentRoute, SynthesisDAG):
        raise TypeError("expected ExperimentRoute or SynthesisDAG")

    # Inherit the SOUND single-candidate projection: this validates search-result membership and the
    # receipt<->target binding, and carries the attested status / receipt / view digest.  The scheme is
    # a second RENDERING of that projection -- never a second search, never a completeness upgrade.
    projection = project_synthesis(route, search_result=search_result)

    def key(mol) -> str:
        return resonance_identity(mol)

    def cell(mol) -> dict:
        formula = repr(Formula.of(mol.formula, mol.charge))
        svg = None
        if depict:
            try:
                from .depiction import depict_svg
                svg = depict_svg(mol)
            except Exception:
                svg = None
            if svg and "<script" in svg.lower():   # defense-in-depth only; the real boundary is the
                svg = None                          # client <img> sandbox (an <img>-embedded SVG runs no
                                                    # script/event handler) -- never trust this blacklist alone
        return {"name": _species_name(mol), "formula": formula, "svg": svg}

    produced_by: dict[str, int] = {}
    for index, step in enumerate(route.steps):
        for mol in step.products:
            produced_by.setdefault(key(mol), index)

    families: set[str] = set()
    steps_payload = []
    for index, step in enumerate(route.steps):
        center = getattr(step, "reaction_center", None)
        family = _reaction_family_for_step(step)
        if family:
            families.add(family)
        precursors = []
        for mol in step.precursors:
            entry = cell(mol)
            source = produced_by.get(key(mol))
            if source is not None and source < index:
                entry["from_step"] = source + 1
            precursors.append(entry)
        steps_payload.append({
            "index": index + 1,
            "family": family or "",
            # headline is the SOUND identity: an oracle-vouched family, else the conserved-multiset equation
            # -- NEVER the forgeable centre (a borrowed centre must not become a step's headline claim, #A3).
            "headline": family or step.equation(),
            "bond_change": _bond_change_text(center),  # ADVISORY: the DECLARED centre; labelled as such at display
            "conditions": _conditions_summary(step.envelope),
            "equation": step.equation(),
            "precursors": precursors,
            "reagents": [cell(mol) for mol in step.reagents],
            "target": cell(step.target),
            "byproducts": [cell(mol) for mol in step.byproducts],
        })

    payload = {
        "target_name": _species_name(route.final_target),
        "target_formula": repr(Formula.of(route.final_target.formula, route.final_target.charge)),
        "kind": projection.source_kind,
        "search_status": projection.search_status,
        "receipt_digest": projection.receipt_digest,
        "source_digest": projection.source_digest,
        "view_digest": projection.digest,
        "n_steps": len(route.steps),
        "route_label": route_label or "",
        "families": sorted(families),
        "leaf_inputs": [cell(mol) for mol in getattr(route, "leaf_inputs", ())],
        "steps": steps_payload,
    }
    data = _embed_json(payload)
    title = html.escape(f"SmartChem synthesis scheme · {payload['target_name']}")
    return _SCHEME_TEMPLATE.replace("__TITLE__", title).replace("__DATA__", data)


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#f7f7f9; --fg:#14151a; --panel:#ffffff; --line:#9aa0ab; --muted:#5a6270;
          --species:#d7e9ff; --reaction:#ffe7c7; --edge:#55606f; --warn:#8a1f1f; --dim:0.12; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14151a; --fg:#e8eaf0; --panel:#1e2027; --line:#4a515e; --muted:#9aa2b1;
            --species:#1d3a5f; --reaction:#5a3c18; --edge:#9aa2b1; --warn:#ff8a8a; --dim:0.08; } }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--fg); }
  header { padding:10px 16px; border-bottom:1px solid var(--line); background:var(--panel); }
  header h1 { font-size:15px; margin:0 0 4px; }
  #banner { font-size:12px; color:var(--muted); }
  #banner b { color:var(--fg); }
  .warn { color:var(--warn); font-weight:600; }
  #bar { display:flex; gap:12px; flex-wrap:wrap; align-items:center; padding:8px 16px;
         border-bottom:1px solid var(--line); background:var(--panel); font-size:12px; }
  #bar label { color:var(--muted); }
  select, button { font:inherit; font-size:12px; padding:3px 6px; background:var(--bg);
                   color:var(--fg); border:1px solid var(--line); border-radius:5px; }
  button { cursor:pointer; }
  #wrap { display:flex; height:calc(100vh - 118px); }
  #canvas { flex:1; overflow:hidden; touch-action:none; cursor:grab; }
  #canvas.drag { cursor:grabbing; }
  aside { width:300px; max-width:42vw; border-left:1px solid var(--line); background:var(--panel);
          padding:12px 14px; overflow:auto; }
  aside h2 { font-size:13px; margin:0 0 8px; }
  .kv { display:grid; grid-template-columns:auto 1fr; gap:2px 10px; font-size:12px; word-break:break-word; }
  .kv dt { color:var(--muted); }
  .legend { font-size:12px; color:var(--muted); margin-top:14px; line-height:1.8; }
  .legend span.box, .legend span.ell { display:inline-block; width:22px; height:13px; margin-right:6px;
          border:1px solid var(--line); vertical-align:middle; }
  .legend span.box { background:var(--species); }
  .legend span.ell { background:var(--reaction); border-radius:50%; }
  text { font:11px system-ui,sans-serif; fill:var(--fg); }
  .node rect { fill:var(--species); stroke:var(--line); }
  .node ellipse { fill:var(--reaction); stroke:var(--line); }
  .node.sel rect, .node.sel ellipse { stroke:var(--fg); stroke-width:2.5; }
  .edge { stroke:var(--edge); fill:none; }
  .elabel { fill:var(--muted); font-size:10px; }
  .dim { opacity:var(--dim); }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <div id="banner"></div>
</header>
<div id="bar">
  <label>candidate route: <select id="cand"><option value="">all</option></select></label>
  <label><input type="checkbox" id="labels" checked> labels</label>
  <button id="fit">fit</button>
  <button id="export">export SVG</button>
  <span id="clip"></span>
</div>
<div id="wrap">
  <div id="canvas"><svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg></div>
  <aside>
    <h2>inspector</h2>
    <div id="inspect">Click a node to inspect its identity, stoichiometry and evidence status.</div>
    <div class="legend">
      <div><span class="box"></span>species (identity class)</div>
      <div><span class="ell"></span>reaction (hyperedge, occurrence)</div>
      <div>edge number = stoichiometric multiplicity</div>
      <div>status is carried by text, never color alone.</div>
    </div>
  </aside>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("data").textContent);
const G = D.graph, L = D.layout;
const svg = document.getElementById("svg");
const NS = "http://www.w3.org/2000/svg";
const COLW = 220, ROWH = 64, PAD = 40, NW = 168, NH = 34;
const nodeById = {}; G.nodes.forEach(n => nodeById[n.id] = n);

document.getElementById("title").textContent = G.source_kind + "  ·  view " + D.view_digest.slice(0,12);
// ISSUE-129 / #A1: three DISTINCT completeness states. UNATTESTED (no search receipt) is NOT complete, but
// it is ALSO NOT a failed/truncated search -- it is simply unknown, so it must read neither "complete" nor
// "INCOMPLETE — candidates missing".
const complete = (G.search_status === "COMPLETE" || G.search_status === "COMPLETE_WITHIN_BOUNDS");
const unattested = (G.search_status === "UNATTESTED");
const banner = document.getElementById("banner");
banner.innerHTML =
  "search: <b>" + G.search_status + "</b>" + (complete ? "" : unattested
    ? " <span class='warn'>(UNATTESTED — completeness not established: no search receipt, not a failed search)</span>"
    : " <span class='warn'>(INCOMPLETE — a bounded search was truncated; candidates may be missing)</span>") +
  " &nbsp;|&nbsp; source " + G.source_digest.slice(0,12) +
  " &nbsp;|&nbsp; receipt " + (G.receipt_digest ? G.receipt_digest.slice(0,12) : "UNATTESTED") +
  " &nbsp;|&nbsp; " + G.nodes.length + " nodes / " + G.arcs.length + " arcs";

// Display-completeness: never clip silently. If a viewport limit hides nodes, say how many.
const limit = D.visible_limit, hidden = D.total_nodes - limit;
const shown = new Set(G.nodes.slice(0, limit).map(n => n.id));
document.getElementById("clip").innerHTML = hidden > 0
  ? "<span class='warn'>displaying " + limit + " of " + D.total_nodes + " nodes (" + hidden + " hidden by viewport limit)</span>"
  : "displaying all " + D.total_nodes + " nodes";

// candidate dropdown (ensembles): distinct membership indices across reaction nodes
const cands = new Set();
G.nodes.forEach(n => { const c = (n.attributes||{}).candidates; if (c) c.split(",").forEach(x => x && cands.add(x)); });
const sel = document.getElementById("cand");
[...cands].sort((a,b)=>(+a)-(+b)).forEach(c => { const o=document.createElement("option"); o.value=c; o.textContent="route "+c; sel.appendChild(o); });
if (cands.size === 0) sel.parentElement.style.display = "none";

function membership(id){ const c=(nodeById[id].attributes||{}).candidates; return c? c.split(",") : null; }

function draw(){
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const showLabels = document.getElementById("labels").checked;
  const pick = sel.value;
  const arcLayer = document.createElementNS(NS,"g");
  const nodeLayer = document.createElementNS(NS,"g");
  const pos = id => { const p=L[id]||[0,0]; return [PAD + p[0]*COLW, PAD + p[1]*ROWH]; };
  const inCand = id => { if(!pick) return true; const m=membership(id); return m ? m.includes(pick) : false; };
  // edges
  G.arcs.forEach(a => {
    if (!shown.has(a.source) || !shown.has(a.target)) return;
    const [sx,sy]=pos(a.source), [tx,ty]=pos(a.target);
    const path = document.createElementNS(NS,"path");
    const x1=sx+NW, y1=sy+NH/2, x2=tx, y2=ty+NH/2, mx=(x1+x2)/2;
    path.setAttribute("d",`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`);
    path.setAttribute("class","edge");
    path.setAttribute("marker-end","url(#arrow)");
    if (!(inCand(a.source)&&inCand(a.target))) path.classList.add("dim");
    arcLayer.appendChild(path);
    if (showLabels && a.multiplicity !== 1){
      const t=document.createElementNS(NS,"text");
      t.setAttribute("x",mx); t.setAttribute("y",(y1+y2)/2-3); t.setAttribute("class","elabel");
      t.textContent=a.multiplicity; arcLayer.appendChild(t);
    }
  });
  // nodes
  let maxX=0,maxY=0;
  G.nodes.forEach(n => {
    if (!shown.has(n.id)) return;
    const [x,y]=pos(n.id); maxX=Math.max(maxX,x+NW); maxY=Math.max(maxY,y+NH);
    const g=document.createElementNS(NS,"g"); g.setAttribute("class","node"); g.dataset.id=n.id;
    const sp = n.kind==="species";
    const shape=document.createElementNS(NS, sp?"rect":"ellipse");
    if (sp){ shape.setAttribute("x",x); shape.setAttribute("y",y); shape.setAttribute("width",NW); shape.setAttribute("height",NH); shape.setAttribute("rx",5);}
    else { shape.setAttribute("cx",x+NW/2); shape.setAttribute("cy",y+NH/2); shape.setAttribute("rx",NW/2); shape.setAttribute("ry",NH/2);}
    g.appendChild(shape);
    if (showLabels){
      const t=document.createElementNS(NS,"text");
      t.setAttribute("x",x+NW/2); t.setAttribute("y",y+NH/2+4); t.setAttribute("text-anchor","middle");
      let lab=n.label; if(lab.length>26) lab=lab.slice(0,25)+"…";
      t.textContent=lab; g.appendChild(t);
    }
    if (!inCand(n.id)) g.classList.add("dim");
    g.addEventListener("click", e => { e.stopPropagation(); inspect(n.id); });
    nodeLayer.appendChild(g);
  });
  const defs=document.createElementNS(NS,"defs");
  defs.innerHTML='<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--edge)"/></marker>';
  svg.appendChild(defs); svg.appendChild(arcLayer); svg.appendChild(nodeLayer);
  svg.dataset.w = maxX+PAD; svg.dataset.h = maxY+PAD;
  fit();
}

function inspect(id){
  const n=nodeById[id];
  document.querySelectorAll(".node.sel").forEach(e=>e.classList.remove("sel"));
  const g=[...svg.querySelectorAll(".node")].find(e=>e.dataset.id===id); if(g) g.classList.add("sel");
  let h="<div class='kv'><dt>kind</dt><dd>"+esc(n.kind)+"</dd><dt>label</dt><dd>"+esc(n.label)+"</dd>";
  const a=n.attributes||{};
  Object.keys(a).sort().forEach(k => h += "<dt>"+esc(k)+"</dt><dd>"+esc(String(a[k]))+"</dd>");
  h+="<dt>id</dt><dd>"+esc(id)+"</dd></div>";
  document.getElementById("inspect").innerHTML=h;
}
function esc(s){ return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// pan + zoom via viewBox
let vb={x:0,y:0,w:1000,h:700};
function apply(){ svg.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`); }
function fit(){ const w=+svg.dataset.w||1000, h=+svg.dataset.h||700; vb={x:-20,y:-20,w:w+40,h:h+40}; apply(); }
const canvas=document.getElementById("canvas");
canvas.addEventListener("wheel", e=>{ e.preventDefault(); const k=e.deltaY<0?0.9:1.1;
  const r=svg.getBoundingClientRect(); const mx=vb.x+(e.clientX-r.left)/r.width*vb.w, my=vb.y+(e.clientY-r.top)/r.height*vb.h;
  vb.x=mx-(mx-vb.x)*k; vb.y=my-(my-vb.y)*k; vb.w*=k; vb.h*=k; apply(); }, {passive:false});
let drag=null;
canvas.addEventListener("pointerdown", e=>{ drag={x:e.clientX,y:e.clientY}; canvas.classList.add("drag"); });
window.addEventListener("pointerup", ()=>{ drag=null; canvas.classList.remove("drag"); });
window.addEventListener("pointermove", e=>{ if(!drag) return; const r=svg.getBoundingClientRect();
  vb.x-=(e.clientX-drag.x)/r.width*vb.w; vb.y-=(e.clientY-drag.y)/r.height*vb.h; drag={x:e.clientX,y:e.clientY}; apply(); });
canvas.addEventListener("click", ()=>{ document.querySelectorAll(".node.sel").forEach(e=>e.classList.remove("sel")); });

document.getElementById("fit").addEventListener("click", fit);
document.getElementById("labels").addEventListener("change", draw);
sel.addEventListener("change", draw);
document.getElementById("export").addEventListener("click", ()=>{
  const clone=svg.cloneNode(true); clone.setAttribute("xmlns",NS);
  const blob=new Blob([clone.outerHTML],{type:"image/svg+xml"}); const url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download="smartchem_"+D.view_digest.slice(0,12)+".svg"; a.click(); URL.revokeObjectURL(url);
});
draw();
</script>
</body>
</html>
"""


_SCHEME_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#f6f7f9; --fg:#14151a; --panel:#ffffff; --line:#c9ced8; --muted:#5a6270;
          --accent:#1d5fbf; --chip:#eef1f6; --species:#ffffff; --warn:#8a1f1f; --ok:#1f6a3a;
          --unknown:#8a5a1f; --arrow:#39404d; }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) { --bg:#13141a; --fg:#e8eaf0; --panel:#1c1e25; --line:#3a4150;
          --muted:#9aa2b1; --accent:#7fb0ff; --chip:#262a33; --species:#1a1c22; --warn:#ff8a8a;
          --ok:#86e0a6; --unknown:#e0c086; --arrow:#aab2c0; } }
  :root[data-theme="dark"] { --bg:#13141a; --fg:#e8eaf0; --panel:#1c1e25; --line:#3a4150;
          --muted:#9aa2b1; --accent:#7fb0ff; --chip:#262a33; --species:#1a1c22; --warn:#ff8a8a;
          --ok:#86e0a6; --unknown:#e0c086; --arrow:#aab2c0; }
  * { box-sizing:border-box; }
  body { margin:0; font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--fg); }
  header { padding:14px 16px; border-bottom:1px solid var(--line); background:var(--panel); }
  header h1 { font-size:17px; margin:0 0 6px; }
  header h1 small { color:var(--muted); font-weight:400; font-size:13px; }
  #banner { font-size:12px; color:var(--muted); }
  #banner b { color:var(--fg); } #banner .warn { color:var(--warn); font-weight:600; }
  #banner .ok { color:var(--ok); font-weight:600; }
  #banner .unknown { color:var(--unknown); font-weight:600; }
  #fams { margin-top:6px; font-size:12px; color:var(--muted); }
  #fams span { display:inline-block; background:var(--chip); border:1px solid var(--line);
         border-radius:11px; padding:1px 9px; margin:2px 4px 0 0; color:var(--fg); }
  main { max-width:1100px; margin:0 auto; padding:16px; }
  .step { background:var(--panel); border:1px solid var(--line); border-radius:12px;
          margin:0 0 16px; overflow:hidden; }
  .step > .head { display:flex; flex-wrap:wrap; align-items:baseline; gap:10px;
          padding:9px 14px; border-bottom:1px solid var(--line); }
  .step .num { font-weight:700; background:var(--accent); color:#fff; border-radius:7px;
          padding:1px 9px; font-size:12px; }
  .step .fam { font-weight:600; }
  .step .cond { color:var(--muted); font-size:12px; }
  .step .bc { color:var(--muted); font-size:11px; margin-left:auto; font-family:ui-monospace,monospace; }
  .rxn { display:flex; flex-wrap:wrap; align-items:center; gap:10px 8px; padding:14px; }
  .cell { display:flex; flex-direction:column; align-items:center; text-align:center;
          min-width:120px; max-width:200px; }
  .cell .pic { width:168px; height:132px; display:flex; align-items:center; justify-content:center;
          border:1px solid var(--line); border-radius:8px; background:var(--species); overflow:hidden; }
  .cell .pic svg { max-width:100%; max-height:100%; }
  .cell .pic.text { font:600 20px ui-monospace,monospace; color:var(--fg); letter-spacing:.3px; }
  .cell .nm { margin-top:5px; font-size:13px; font-weight:600; word-break:break-word; }
  .cell .fo { font-size:11px; color:var(--muted); font-family:ui-monospace,monospace; }
  .cell .ref { font-size:11px; color:var(--accent); }
  .plus { font-size:20px; color:var(--muted); font-weight:600; }
  .arrow { display:flex; flex-direction:column; align-items:center; min-width:150px; flex:1; }
  .arrow .over { font-size:11px; color:var(--fg); font-weight:600; margin-bottom:2px; text-align:center; }
  .arrow .line { width:100%; min-width:120px; height:0; border-top:2px solid var(--arrow); position:relative; }
  .arrow .line:after { content:""; position:absolute; right:-1px; top:-5px; border:5px solid transparent;
          border-left-color:var(--arrow); }
  .arrow .under { font-size:11px; color:var(--muted); margin-top:3px; text-align:center; }
  .arrow .with { font-size:11px; color:var(--muted); margin-bottom:2px; }
  .arrow .with b { color:var(--fg); font-weight:600; }
  .inputs { padding:10px 14px; border-top:1px dashed var(--line); font-size:12px; color:var(--muted); }
  .inputs b { color:var(--fg); }
  .notes { margin-top:10px; font-size:12px; color:var(--muted); line-height:1.7; }
  .notes li { margin:2px 0; }
  .toggle { float:right; }
  button { font:inherit; font-size:12px; padding:3px 9px; background:var(--bg); color:var(--fg);
           border:1px solid var(--line); border-radius:6px; cursor:pointer; }
  @media (max-width:560px){ .cell{min-width:46%;} .cell .pic{width:140px;height:112px;} main{padding:12px 8px;} }
</style>
</head>
<body>
<header>
  <button class="toggle" id="theme">light / dark</button>
  <h1 id="title"></h1>
  <div id="banner"></div>
  <div id="fams"></div>
</header>
<main id="scheme"></main>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("data").textContent);
// ISSUE-129: three DISTINCT completeness states.  UNATTESTED is NOT complete -- a route with no search
// receipt cannot certify that every bounded alternative was searched -- but it is also not a FAILED/partial
// search; it is simply unknown.  COMPLETE/COMPLETE_WITHIN_BOUNDS -> ok (green); a partial/limited receipt
// status -> warn (incomplete); UNATTESTED -> unknown (amber, completeness not established).
const COMPLETE = {COMPLETE:1, COMPLETE_WITHIN_BOUNDS:1};
function el(tag, cls, text){ const e=document.createElement(tag); if(cls) e.className=cls;
  if(text!=null) e.textContent=text; return e; }

document.getElementById("title").innerHTML = "";
const h1 = document.getElementById("title");
h1.appendChild(document.createTextNode(D.target_name + "  "));
h1.appendChild(el("small", null, D.target_formula + " · " + D.n_steps + " step" + (D.n_steps===1?"":"s")
  + (D.route_label ? " · " + D.route_label : "")));

const complete = !!COMPLETE[D.search_status];
const unattested = (D.search_status === "UNATTESTED");
const b = document.getElementById("banner");
b.innerHTML = "search: ";
const st = el("b", complete ? "ok" : (unattested ? "unknown" : "warn"), D.search_status); b.appendChild(st);
if(unattested) b.appendChild(el("span","unknown",
  " — completeness UNKNOWN: this route was not bound to a search receipt, so other routes/precursors may exist (no search was attested, not a failed search)"));
else if(!complete) b.appendChild(el("span","warn"," — INCOMPLETE: alternative routes/precursors may be missing"));
b.appendChild(document.createTextNode(
  "  |  source " + D.source_digest.slice(0,12) +
  "  |  receipt " + (D.receipt_digest ? D.receipt_digest.slice(0,12) : "UNATTESTED") +
  "  |  view " + D.view_digest.slice(0,12)));

const fams = document.getElementById("fams");
if(D.families.length){ fams.appendChild(document.createTextNode("reaction families: "));
  D.families.forEach(f => fams.appendChild(el("span", null, f))); }
else fams.appendChild(document.createTextNode("reaction families: no family re-derived by the oracle — steps show the sound equation; any declared bond-change centre is advisory, not proven"));

function cell(c){
  const wrap = el("div","cell");
  const pic = el("div","pic");
  if(c.svg){                                     // #A2: embed the optional RDKit SVG as a SANDBOXED <img>
    const im = el("img"); im.className = "depiction"; im.alt = c.formula;  // an <img>-referenced SVG runs
    im.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(c.svg);  // no script/event handler
    pic.appendChild(im);                          // -- so onload/onerror/foreignObject/javascript: are inert
  }
  else { pic.classList.add("text"); pic.textContent = c.formula; }
  wrap.appendChild(pic);
  const name = (c.name && c.name !== c.formula) ? c.name : c.formula;
  wrap.appendChild(el("div","nm", name));
  if(c.name && c.name !== c.formula) wrap.appendChild(el("div","fo", c.formula));
  if(c.from_step) wrap.appendChild(el("div","ref","(from step " + c.from_step + ")"));
  return wrap;
}
function plus(){ return el("div","plus","+"); }

const root = document.getElementById("scheme");
D.steps.forEach(s => {
  const card = el("div","step");
  const head = el("div","head");
  head.appendChild(el("span","num","Step " + s.index));
  head.appendChild(el("span","fam", s.headline));
  head.appendChild(el("span","cond","conditions: " + s.conditions));
  if(s.bond_change) head.appendChild(el("span","bc", "declared Δbonds (advisory): " + s.bond_change));
  card.appendChild(head);

  const rxn = el("div","rxn");
  s.precursors.forEach((p,i) => { if(i) rxn.appendChild(plus()); rxn.appendChild(cell(p)); });

  const arrow = el("div","arrow");
  if(s.reagents.length){
    const w = el("div","with"); w.appendChild(document.createTextNode("with "));
    s.reagents.forEach((r,i)=>{ if(i) w.appendChild(document.createTextNode(", "));
      w.appendChild(el("b",null, (r.name&&r.name!==r.formula)?r.name:r.formula)); });
    arrow.appendChild(w);
  }
  if(s.family) arrow.appendChild(el("div","over", s.family));
  arrow.appendChild(el("div","line"));
  arrow.appendChild(el("div","under", s.conditions === "unknown" ? "conditions unknown" : s.conditions));
  rxn.appendChild(arrow);

  rxn.appendChild(cell(s.target));
  s.byproducts.forEach(bp => { rxn.appendChild(plus()); const c=cell(bp);
    c.appendChild(el("div","fo","byproduct")); rxn.appendChild(c); });
  card.appendChild(rxn);
  root.appendChild(card);
});

if(D.leaf_inputs.length){
  const inp = el("div","inputs");
  inp.appendChild(el("b",null,"Starting materials: "));
  inp.appendChild(document.createTextNode(
    D.leaf_inputs.map(c => (c.name&&c.name!==c.formula)?c.name+" ("+c.formula+")":c.formula).join(", ")));
  root.appendChild(inp);
}
const notes = el("ul","notes");
[ "This is ONE candidate route, drawn in synthesis order; it is not a ranked recommendation and not all alternatives.",
  "Structures are drawn by the optional RDKit backend; a plain formula box means that species was not drawn (absent backend or a fragment that would not sanitise), never a missing identity.",
  "A named reaction family is shown only where the reaction-type oracle INDEPENDENTLY RE-DERIVES that family from the step's own molecules (ISSUE-128: never from a caller-supplied reaction centre); otherwise the sound conserved-multiset equation is the headline, and any declared bond-change centre is shown as a DECLARED, advisory annotation — never proven chemistry.",
  "Conditions read UNKNOWN unless the step carries a sourced envelope — no default conditions are filled in.",
  "No yield, readiness, hazard, or bench-capability verdict is asserted by this drawing."
].forEach(t => notes.appendChild(el("li", null, t)));
root.appendChild(notes);

const themeBtn = document.getElementById("theme");
themeBtn.addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  document.documentElement.setAttribute("data-theme", cur === "dark" ? "light" : "dark");
});
</script>
</body>
</html>
"""
