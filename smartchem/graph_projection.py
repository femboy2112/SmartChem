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
    proc = subprocess.run([dot_bin, "-Tsvg"], input=render_dot(graph),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise GraphProjectionError(
            f"graphviz dot failed (exit {proc.returncode}): {proc.stderr.strip()[:200]}"
        )
    return proc.stdout


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
const complete = (G.search_status === "COMPLETE" || G.search_status === "COMPLETE_WITHIN_BOUNDS");
const banner = document.getElementById("banner");
banner.innerHTML =
  "search: <b>" + G.search_status + "</b>" + (complete ? "" : " <span class='warn'>(INCOMPLETE — candidates may be missing)</span>") +
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
