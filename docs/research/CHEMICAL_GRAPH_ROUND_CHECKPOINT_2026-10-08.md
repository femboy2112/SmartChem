# Chemical Graph Round — Checkpoint A–C (2026-10-08)

**Branch:** `feat/chemical-graph-projections` · **base:** `main@99fce34` (SmartChem 1.0.0) · **PR:** #101 (draft).
Companion to `CHEMICAL_GRAPH_MEGA_ROUND_HANDOFF_2026-10-08.md` (the originating ChatGPT handoff) — that
document is preserved; this one records what was audited, repaired, built and verified on top of it.

This is a visualization/projection round. Every claim below is labelled by how it was established:
**Verified** (committed test, named), **Observed** (ran clean once on the real path, not a committed regression),
**Deferred** (scoped, not built). No readiness, evidence, capability, yield or hazard verdict is produced by any
code in this round — the graph communicates the chemistry, it does not invent it.

## Audit of the initial contribution (hostile)

`smartchem/graph_projection.py` as contributed was **found sound** and was NOT rewritten. The two test failures it
shipped with were a false *chemistry* premise, not a module bug:

- **Finding (repaired):** every formula decomposes to elemental buckets in exactly ONE edge under the default
  element-only terminal policy, so no edge budget can ever truncate an element-only search — it is always
  `COMPLETE_WITHIN_BOUNDS`. A partial result requires a **molecular inventory** to widen the OR-alternative fan.
  The two partial-search tests asserted an impossible partiality (and a `"unexpanded"` frontier node that cannot
  exist under edge-cap truncation). Repaired to use `inventory=(H2O,CO2,CH4)` + a tiny edge cap → genuine
  `PARTIAL_RESULT_LIMIT`. The module was correctly refusing to launder a completeness that was real.
- **Finding (architectural, reported):** the decomposition grammar is **single-level**: every edge partitions the
  target directly into elements ∪ inventory buckets. There are **no multi-level intermediates / reused intermediate
  composition nodes** in the current engine. Mode A's AND–OR hypergraph is genuine but always depth-1. We do not
  fake depth the engine does not produce.
- **Finding (downgraded, then Verified):** `project_synthesis(search_result=...)` was entirely untested; its
  receipt binding compares `receipt.target_identity_digest` against `resonance_identity(final_target)`. Verified
  empirically these share a hash space (`_ident` in `experiment/routes.py` *is* `resonance_identity`), so the path
  is correct — but it now has a committed test (it did not before).
- **Finding (dead):** the duplicate-edge crash hazard is **structurally unreachable** — `search_decomposition`
  dedups edges by `edge.digest` in a dict; distinct reactions get distinct reaction-node ids.

## Claim ledger

### Verified (committed tests in `tests/test_graph_projection.py`)

- **A — repairs + anchors.** Partial formula search surfaces `PARTIAL_RESULT_LIMIT` and is never laundered into
  completeness; the attested route AND convergent-DAG paths bind a real receipt and fail closed on kind-mismatch
  and non-membership; each reaction's stoichiometric multiset reconstructs from graph incidence and a single forged
  multiplicity breaks the match (negative control); two constitutional isomers of one formula (ethanol/dimethyl
  ether, C2H6O) stay distinct species nodes keyed on resonance constitution, never the printed formula.
- **B — ensemble projection.** `project_synthesis_ensemble` renders ALL returned candidates as one content-merged
  AND–OR hypergraph: species merge by resonance identity (9 paracetamol routes → 52 per-route species collapse to
  7 shared nodes); reactions merge by content digest and carry candidate membership; **every** candidate boundary
  is exactly recoverable from the `candidates` attribute (verified for all 9 paracetamol routes and all 47
  ethyl-acetate convergent DAGs); OR-alternative producers are surfaced; a partial search (`PARTIAL_DEPTH_LIMIT`)
  carries its incompleteness onto the ensemble, never upgraded; an empty search shows the lone target and invents
  no reaction.
- **C — renderers + CLI.** Deterministic layered layout places every node (cycle-tolerant); `render_svg` is
  well-formed XML via optional Graphviz and fails closed when `dot` is absent; `render_html` is offline/CDN-free,
  its JSON data island cannot be broken out of (an adversarial `</script>` label is neutralized), and it discloses
  display completeness exactly (a viewport limit states how many nodes were omitted — no silent clip); the
  `smartchem graph` CLI returns 0/complete, 4/partial, 5/refused across formula and synthesis views.

### Observed (ran clean on the real path; not a committed regression)

- 7-graph artifact gallery renders from real compiler output in all of json/dot/mermaid/svg/html; all SVGs parse as
  XML. Digests recorded in the gallery manifest.
- The HTML explorer's **interactive** behaviour (pan/zoom, click-inspect, candidate highlight, SVG export) is
  structurally correct (valid markup, safe data, vanilla JS, no network) but is **not** browser-E2E-tested here —
  boundary stated honestly.

### Deferred (scoped, not built this checkpoint)

- **D — EPIC-style multiple readers** (chemistry / evidence / capability / provenance / probe / process) as separate
  typed projections. Not started.
- **E — source-backed process/sourcing breadth.** Not started.
- **F — perf at adversarial scale.** Basic ceilings (`max_nodes`/`max_arcs`) are tested; Cartesian-explosion stress
  and lazy/chunked disclosure are not.
- **Reagents-not-reactants are invisible** in `project_synthesis` (a reagent that is not also a reactant gets no node).
  A representational gap, not a correctness bug; deferred because fixing it changes node/arc counts and belongs with
  the reader work.
- **Diels–Alder (and the full certified multi-family algebra) are NOT surfaced by `graph synthesis`.** It reuses the
  low-level `search_routes(registry=DEFAULT_TRANSFORM_REGISTRY)`, but DA families live behind the service's
  `--algebra certified-route-v07` selection. Next step: route the synthesis view through the service/algebra layer
  (an `--algebra` option) like `recompile` does. (Verified: cyclohexene + butadiene/ethene yields 0 routes under the
  default registry.)
- **Convergent-DAG capability profile** remains refused by `service._run_recompile`; untouched by design — no
  visualization code bypasses it.

## Next most valuable falsifiable step

Wire the `graph synthesis` view through the service's algebra selection so the certified multi-family route algebra
(Diels–Alder etc.) is visible, then prove — with a committed test — that the cyclohexene retro surfaces butadiene +
ethene as an AND-dependency with its reaction family named, and that the richer ensemble still recovers every
candidate boundary. This is the single change that moves the synthesis explorer from "the toy linear/capped grammar"
to "what the 1.0 compiler actually knows."
