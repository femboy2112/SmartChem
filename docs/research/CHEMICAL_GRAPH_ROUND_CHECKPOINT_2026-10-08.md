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

---

## Checkpoint G/H — the drawn, named synthesis SCHEME (2026-10-12, `83bee16`)

Addresses the reviewer's core complaint that the diagrams were *"technically correct information blasted out in
graph form with no intuitive meaning"* rather than *"diagrammatic steps of actually synthesizing something."* Two
distinct gaps were found and both closed:

1. **Rendering gap (fixed).** Every `ExperimentStep` already carries the *verbs* of a synthesis — `reagents`
   (the acetylating agent / solvent), `envelope` (conditions), direction, byproducts — and the generic projection
   dropped them, keying species by resonance hash + bare formula and merging candidates into one blob.
2. **Content gap (fixed).** The default `graph synthesis` ran `search_routes` on the legacy **capped-scission**
   registry, which produces formula-level *fragments*, not named bench steps. The named reaction families live in
   `certified-route-v07`.

### Verified (committed tests in `tests/test_synthesis_scheme.py`; 13, 3 RDKit-only via `importorskip`)

- **Named algebra, proven on the Diels–Alder litmus.** `--algebra` routes the synthesis search through
  `resolve_algebra_profile` (default `certified-route-v07`). Cyclohexene retro surfaces **butadiene + ethene** as
  ONE reaction consuming BOTH precursors (an **AND-dependency**), named **"Diels–Alder [4+2] cycloaddition"**,
  `COMPLETE_WITHIN_BOUNDS`. This is the previously-deferred falsifiable step, now delivered. (The retro fragments
  must be supplied as terminal stock — `--available "C=CC=C" "C=C"` — or the search returns 0 routes.)
- **Family naming is sound-or-silent.** A family is named ONLY on an exact match of the step's `reaction_center`
  to that family's OWN canonical centre (carbocyclic DA via `diels_alder._DA_CENTER`; hetero `[4+2]` via each
  provider's `family.center`). A foreign centre, a one-bond-off tamper, and a `None` centre all return no name and
  degrade to a neutral bond-change description — a family is never guessed from a formula.
- **The scheme inherits attestation.** `render_scheme_html(route, search_result=…)` validates membership and the
  receipt↔target binding via `project_synthesis` and never re-searches; search completeness stays the receipt's.
- **Optional depiction is faithful and degrades.** `smartchem/depiction.py` builds an RDKit `RWMol` directly from a
  Molecule's atoms+bonds (no SMILES writer) and draws a 2D skeletal SVG (and a static reaction-scheme SVG). It
  round-trips constitution exactly (paracetamol → `CC(=O)Nc1ccc(O)cc1`), so two constitutional isomers (ethanol /
  dimethyl ether) are never drawn or labelled the same. With RDKit absent (the committed baseline) the scheme
  degrades to name/formula boxes and the chemistry stays legible — the DA family is still named without any drawing.
- **Injection-safe.** The scheme embeds its data as a neutralised JSON island (inherits `_embed_json`); a scripted
  SVG is never inlined (`<script`-guarded server-side).

### Observed (ran clean on the real path; not a committed regression)

- Flagship drawn artifacts render from real compiler output: ethene + butadiene → cyclohexene, and ethene +
  2,3-dimethylbutadiene → 1,2-dimethylcyclohexene, both as drawn Diels–Alder reaction schemes (RDKit Cairo PNG/SVG).

### Deferred / honest boundaries

- **The compiler's named algebra is capped-scission + the Diels–Alder family ONLY.** There is no acylation /
  esterification / amide-formation transform, so **paracetamol and ethyl acetate yield 0 named routes** through
  `certified-route-v07` (they only ever produced capped-scission *fragments*). A paracetamol "acylation" scheme is
  correct chemistry but is **not something this compiler's algebra can produce** — the honest named demos are
  Diels–Alder syntheses. Bridged-bicyclic DA (cyclopentadiene + ethene → norbornene) also yields 0 routes: the
  registry's `[4+2]` forms monocyclic adducts.
- The scheme renders ONE candidate per HTML; client-side route switching across the full ensemble is not built.
- The HTML scheme's structural correctness is validated (data island parses, no script breakout); its interactive
  rendering is not browser-E2E-tested here.
