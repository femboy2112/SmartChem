# Chemical Graphs — 2026-10-08 Claude Mega-Round Handoff

**Status:** graph-projection foundation committed on `feat/chemical-graph-projections`; NOT merged, NOT a 1.0 contract change. This note is a development handoff, not a claim of complete visualization.

**Base:** SmartChem `main@99fce3475a4b502fdaedc409954d8a1c7fb53da2` (1.0.0). EPIC `main@7c9e9b9a0db81766e47f062e12980dd747a6952c`. Verify current heads when commencing work; reconcile branch drift before changing code.

## 0. Why this exists

The user needs genuinely useful, graphical chemical decomposition and synthesis views:
1. full bounded formula decomposition **AND–OR hypergraphs**;
2. structure-aware retrosynthetic disconnection alternatives;
3. complete forward multi-step and convergent synthesis DAGs;
4. where evidence permits, expansion into physical process, reaction, workup, stream, waste and procurement views.

SmartChem's `decompiler.DecompositionGraph`, `experiment.routes.search_routes/search_dags`, `experiment.dag.SynthesisDAG`, `experiment.step.ExperimentStep`, `open_chem_diagram.OpenChemDiagram`, `compilation_ir.ChemicalCompilationIR`, the readiness and capability system, and verified replay should be reused. No forked chemistry engine or fake-route generator.

EPIC provides a **design discipline**, not a reusable renderer. See `femboy2112/EPIC/docs/DIAGRAM_STANDARD.md`, `READERS.md` and `FORMALISM.md`: typed ports, expandable nodes, multiple independent readers, provenance classes, and calibrated probes. Do not import EPIC's `src/epic/finite.py` gratuitously, nor turn route count into probability, provenance into independence, or untransported disagreement into curvature.

## 1. Initial contribution (inspect and attack)

`smartchem/graph_projection.py` is an additive standard-library-only read-only projection:
- `project_decomposition(DecompositionSearchResult|DecompositionGraph)` exports all **returned** formula graph edges; preserves exact element-bucket multiplicities and marks partial searches;
- `project_synthesis(ExperimentRoute|SynthesisDAG, search_result=optional)` projects one existing candidate preserving molecule constitution identities, stoichiometry, distinct step occurrences, input reagent counts and target product counts;
- `ChemicalGraphProjection.to_payload()/to_json()`, `render_dot`, `render_mermaid` are deterministic and have explicit graph resource ceilings;
- bipartite incidence nodes distinguish species types and reaction occurrences; no readiness or empirical synthesis claim is invented.

`tests/test_graph_projection.py` probes basic formula completeness, partial search, terminal stock, linear and convergent synthesis, multipliers, endpoint forgery, renderer escaping and limits.

**Hostile audit is required before trusting this initial patch**: the complete SmartChem test suite was not run by the creating assistant when this handoff was authored. Inspect graph identity collisions, source receipts, search membership, intrinsic validators, false model equivalence, renderer escapes, sort invariance, and type-vs-lot boundaries; fix deficiencies rather than preserving premature code.

Known intentional constraints:
- `project_synthesis` draws ONE returned route/DAG, not the complete alternative solution ensemble. `search_status=UNATTESTED` unless the source search result containing that candidate is passed.
- Species identity nodes are *not allocated physical material lots*; sharing a node does not license arbitrary quantity flow or make a visual loop a material-flow cycle.
- Formula split edges assert only compositional conservation; route transformations assert only the certified transformation grammar. No evidence state promoted.
- No `smartchem graph` CLI integration or SVG/HTML viewer yet.
- 1.0 public wire and `COMPATIBILITY.md` semantics must remain untouched.

## 2. Architectural target

Build a typed **view/projection** layer beneath a front-end, never a second authoritative compiler:

```
user input → existing identity + search service → certified search / verified replay
                 ├→ existing CompilationIR + SearchReceipt + RankedDossiers
                 └→ GraphProjection (structural source identity, receipt, topology)
                           ├→ ChemReader (formula/structure/stoichiometry)
                           ├→ EvidenceReader (readiness/source/unknown)
                           ├→ CapabilityReader (existing assessment ONLY)
                           ├→ ProvenanceReader (source ancestry/duplicates)
                           ├→ ProcessReader (source-backed operations/streams ONLY)
                           └→ exporters (JSON/DOT/Mermaid/SVG/HTML)
```

A reaction is a **typed hyperedge**, never a fictional molecule; an OR group holds alternative transforms, each transform's inputs are AND prerequisites. Model occurrences separately from identity classes and quantity-bearing material lots. Source and graph identity are content-bound; layout, colors, folded state and zoom cannot change chemical identity. Full vs partial SEARCH and full vs partial DISPLAY are independent statuses.

The `CandidateSummary` wire is deliberately thin (digest/equation, NOT entire step material topology). Never parse its equation text to invent molecules. For route visualization obtain authoritative search objects or validated replay under the existing loader/verification policy. Consider an *additive* versioned visualization schema rather than mutating frozen 1.0 wire semantics.

## 3. Build program (ordered milestones)

### A — Close the reference adapter

- Check baseline HEAD/worktree and read `docs/ARCHITECTURE.md`, `COMPATIBILITY.md`, `docs/research/V1_0_RELEASE_GATE.md`.
- Run targeted `pytest -q tests/test_graph_projection.py`; determine positive/negative/mutation controls and repair any failure; do not call CI tests if only locally reasoned.
- Unit/fuzz checks for multiplicity, simultaneous reactant/product species, source digest matching, tampered result membership, duplicate steps, capping, Unicode escaping, swapped isomers and source provenance.
- Keep the reference adapter self-contained, typed and optional-dependency-free. No changes to 1.0 result digests.

### B — Make ALL returned synthesis alternatives visible

- Add an ensemble projection over `RouteSearchResult`/`DAGSearchResult` that preserves OR-alternatives, routes with convergent AND branches, exact candidate membership and search receipts.
- Decide shared chemical identity vs distinct candidate step occurrence vs physical lots explicitly; do not collapse distinct route events because a structure/digest matches.
- Support focused subgraph exploration and vertex expansion, preserving ports and exterior stoichiometry.
- Include source ids, candidate digests, reaction-family and evidence keys without forcing an empirical readiness verdict at this layer.

### C — Actual diagrams, not a JSON-only product

- Implement `smartchem graph` or `smartchem visualize` as a THIN CLI over canonical request/service. Options: `--view formula|retro|synthesis|process`, `--format json|dot|mermaid|svg|html`, `--output`, `--max-visible-nodes`, and separate explicit search budgets.
- Optional Graphviz for directed layered SVG. Optional RDKit to draw 2D structure depictions from actual molecular graphs; absence must fall back gracefully, NEVER drop chemistry.
- An offline, self-contained HTML explorer if feasible: zoom/pan, select/expand reaction, OR branch toggles, forward/backward orientation, target focus, identity/evidence overlays, full vs clipped counts, and sober contextual warning labels. No network dependency necessary.
- Tests should parse exported DOT/Mermaid/JSON for structure; where SVG exists, inspect XML and node/edge correspondences, not only snapshots.

### D — EPIC readers applied to chemistry

Readers must be separate, typed projections:
- chemistry: identity layer, balance, transform family, AND/OR connectivity;
- evidence: procedure/source provenance and readiness ladder, never derived from graph beauty;
- capability: material/physical/process/waste/equipment axes; `UNKNOWN` not FIT;
- provenance: source ancestry and report-family collapsing, never evidence-count-as-independence;
- probes: missing discriminating measurements/sources, *proposed* distinct from executed;
- process: documented operations/streams, with absent isolation/yield/hold-time visible.

Do NOT silently unlock `CAPABILITY_FIT` for convergent-DAG profiles: `service._run_recompile` explicitly refuses that combination until a topology-aware implementation is validated.

### E — Evidence-backed chemical synthesis breadth

Only after the visual vertical slice is real, examine sourcing reaction records with exact provenance (e.g. ORDB compatible imports) and expanding the transform grammar. Strictly separate formal generation from reaction vouched, conditions supported, and sourced process specified. Validate on fresh holdouts and negative controls. No inference of real procedure from composition alone.

### F — Perf, adversarial review, docs, merge

- Test worst-case AND–OR branching, multi-precursor Cartesian product in `search_dags`, deep nesting and renderer budgets. Use lazy expansion/chunking where needed, preserving FULL SEARCH vs partial DISPLAY.
- Rebuild only affected modules, run OOM-safe `scripts/run_suite.sh`, plus existing 1.0 contract/digest/transport gates; no silent skipped checks.
- Produce two real SmartChem graphs: a complete/partial formula decomposition, and a structural forward/DAG synthesis example from documented stable chemistry.
- Document commands and limitations in README; store reproducible input/expected digests, generated diagrams and metrics.
- Commit coherent checkpoints; keep scope localized; open a PR and request hostile review. Merge to main only after tests and explicit code review, with current branch/release reconciliation.

## 4. Scientific/visual acceptance contract

1. **Actual compiler output:** no diagram created from a hand-written toy graph can substitute for rendering the real source result.
2. **No false completeness:** an incomplete search always reads incomplete; a clipped viewport never silently hides alternatives.
3. **No formula→structure promotion:** constitutional isomers remain distinct where structures exist; pure formula descent never asserts one isomer or mechanism.
4. **No fake chemistry:** source-backed process ≠ formal conservation and source documents ≠ independent experiments automatically.
5. **No fake quantities:** multiset multiplicity survives projection, exports, joins and expansion; shared species nodes do not mint material.
6. **No fake bench pass:** process/waste gaps remain UNKNOWN, including convergent capability boundary.
7. **No frozen-contract drift:** 1.0 semantics, exit codes, default CLI verbs, public wire and verifier remain invariant.
8. **Reproducible artifact:** exact input, declared search bounds, registry and terminal-policy digests, receipt status, displayed slice, renderer version and output digest are discoverable.

Suggested demonstration inputs (non-hazardous): `H2O` or `C3H6O` formula decomposition; cyclohexene with supplied butadiene/ethene (the repository's documented Diels–Alder example); a directly constructed certified H/H→H2 + Cl/Cl→Cl2 → 2 HCl convergent fixture as a structural graph test. Use real existing SmartChem objects, not invented source-backed experimental conditions.

## 5. Deliverables to bring back

- PR URL and HEAD SHA, changed-files inventory.
- Exact tests/CI actually run and failures/skip reasons, including memory conditions.
- Gallery or links to actual generated DOT/SVG/HTML examples, with visible source/receipt labels.
- Audit of 1.0 compatibility, remaining gaps, and first next falsifying probe.
- Concise claim ledger: implemented and tested / implemented but unverified / explicitly deferred.

No user confirmation is needed for ordinary scoped implementation. Do not claim that EPIC mathematical novelty or route visualization constitutes validated chemical synthesis.
