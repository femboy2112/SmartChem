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
        if self.source_kind not in ("FORMULA_DECOMPOSITION", "SYNTHESIS_ROUTE", "SYNTHESIS_DAG"):
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
        nodes[ident] = GraphNode(
            ident, "species", f"{formula} [{ident[-8:]}]",
            _attrs(identity_layer="CONSTITUTION", structure_identity=mol_key,
                   formula=formula, boundary=boundary),
        )

    for index, step in enumerate(route.steps):
        rid = _id("r", f"{index}:{step.digest}")
        nodes[rid] = GraphNode(
            rid, "reaction", f"Step {index + 1}: {step.equation()}",
            _attrs(step_index=index, step_digest=step.digest,
                   evidence_status="NOT_ASSESSED",
                   condition_envelope_declared=step.envelope.is_declared),
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


def render_dot(graph: ChemicalGraphProjection) -> str:
    """Deterministic Graphviz DOT; safe quoting even for unusual chemical labels."""
    if type(graph) is not ChemicalGraphProjection:
        raise TypeError("graph must be a ChemicalGraphProjection")

    def quote(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    lines = ["digraph SmartChem {", "  rankdir=LR;"]
    for node in graph.nodes:
        shape = "box" if node.kind == "species" else "ellipse"
        lines.append(f"  {quote(node.id)} [shape={shape},label={quote(node.label)}];")
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

    lines = ["flowchart LR"]
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
    return "\n".join(lines) + "\n"
