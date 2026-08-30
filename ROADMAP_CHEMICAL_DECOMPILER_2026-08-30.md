# Roadmap proposal — the chemical decompiler (elemental descent graph)

**Status:** proposal + execution + forward vision, 2026-08-30. Parts 0–6 are the original
proposal; the four owner decisions (Part 6) were fixed and **B0–B2 (the formal structural
skeleton) were built** (Part 7, superseding "nothing built" for B0–B2). **Part 8 factors the
owner's next direction — M-4b, the conditions-aware (comonadic) decompiler** ("under what
conditions is this reaction possible?", things-in-solution, byproducts, feasibility trade-offs,
transient-stability); its **C0 (the Env comonad) is built** (Part 9), C1–C4 remain vision.
**Part 9** also records the **paracetamol litmus** — the standing acceptance gate, pinned to
literature. This is a **provenance-honest** record, not a
retroactive ratification. It slots a new chemistry-core research vertical into
`ROADMAP_2026-08-06.md` as **M-4** (skeleton) + **M-4b** (conditions), parallel to the
circuit-`ModelIR` line (M-1), and does not displace it, the consumption arc, or the long-term
category backbone — indeed M-4b is a concrete driver for the long-term ModelIR/EvidenceIR split.

**Baseline:** `03ae86a` (`main == origin/main`, clean; fast suite `1624 passed, 14 skipped,
1 xfailed`, re-run and verified 2026-08-30).

---

## Part 0 — The ask, recovered

Given a chemical description — a molecular formula (`C8H9NO2`) or a name
(N-acetyl-para-aminophenol / 4-hydroxyacetanilide, i.e. paracetamol) — produce **all
possible chains of decomposition reactions through lower compounds, all the way down to the
bare elements**. Water bottoms out in essentially one family; acetone / acetaminophen
produce a dense, layered graph.

The output is not a list — it is an **AND–OR decomposition DAG** (a reaction hypergraph):

- **OR nodes** are compounds — a compound may be decomposed several alternative ways.
- **AND hyperedges** are reactions — one compound → a *multiset* of products, all of which
  are needed, and every hyperedge conserves each element exactly.
- **Leaves** are terminal elemental forms.
- **A "chain"** is a proof tree: one hyperedge chosen per compound node, complete down to
  elements. The density the user wants *is* the branching of this hypergraph.

This is structurally identical to grammar derivation / proof search, and SmartChem already
owns the pieces to do it exactly.

---

## Part 1 — The governing frame: this is FORMAL, and the tier says so

This is the load-bearing decision and the entire reason the feature belongs in *this* repo
rather than being one more cheminformatics toy that lies.

**A balanced decomposition equation is a statement in linear algebra over ℤ — mass
conservation — not a claim about chemistry.** The decompiler **CERTIFIES the algebra** (exact
integer conservation, combinatorial completeness over a declared inventory) and **REFUSES the
chemistry** (thermodynamic favorability, kinetic accessibility, mechanism, synthesizability,
any claim that a given edge *occurs*). This is the same discipline the finite Ising↔lattice-gas
map already enforces: exact mathematics is not literal physical identity, and the type must
never let one imply the other.

- **Candidate tier:** an honest `FORMAL/EXACT/CERTIFIED`-for-conservation status built from the
  **existing** `contracts.py` `ClaimKind` ⊥ `EvidenceStatus` split — *not* a freshly invented
  vocabulary (the label-borrowing constraint from `ROADMAP_2026-08-06.md` Part 2 applies:
  never let a reused label imply governance it lacks). Exact token is a B0 design item.
- **Mandatory casualty list on every certificate:** no ΔG/ΔH ranking (until M-4's optional
  thermo rung), no kinetics *ever*, no mechanism, no synthesizability, no claim any edge is
  physically realized. Explicitly: *not* a retrosynthesis planner and *not* a decomposition
  *prediction*.

If this framing is not held, the feature is a machine that emits chemically-plausible-looking
falsehoods at scale. Held, it is an exact enumerator of the conservation lattice with an honest
boundary — which is the SmartChem shape.

---

## Part 2 — The three walls (these ARE the research content)

Named as gaps, per the Lab Notebook discipline. Each transplants an existing repo doctrine.

- **W1 — Termination / well-foundedness.** "All possible chains … all the way down" is
  **infinite** without (a) a closed inventory and (b) a well-founded descent measure. Every
  hyperedge must *strictly decrease* a measure `M` (natural choice: a multiset order on species
  ranked by complexity — direct transplant of `[[well-founded-measure-is-the-multiset-order]]`).
  The descent measure **is** the termination proof. The recurring failure mode to guard against
  is a descent check that is itself blind to a missing sort — so the guard must be proven
  non-vacuous (catch a *planted* non-descending edge), not merely present.

- **W2 — Combinatorial explosion / budget.** Even over a closed inventory the AND–OR DAG
  explodes for dense targets. There must be explicit depth/candidate budgets and a **loud refusal
  above budget** — a direct transplant of the open-diagram observer's "refuses explicitly above
  its candidate budget." The disease this pre-empts is the repo's signature one: *silent
  truncation read as "covered everything"* (the arc-III vacuity bug). A partial DAG must never
  certify as complete. Water is trivially shallow; acetone/acetaminophen are exactly the cases
  that exercise the budget — the "density" the user wants is this explosion, made legible.

- **W3 — Formal ≠ physical.** Part 1. The killer boundary; restated here as a wall because it is
  the one an implementer will be tempted to cross the moment the graphs look chemically suggestive.

---

## Part 3 — Two scoping decisions (v1 boundaries, stated loudly)

- **Formula-level v1 (atom multiset), not structure-level.** `Config` already *is* an atom
  multiset; the exact stoichiometry engine already operates there. Consequence, stated up front:
  **all structural isomers of `C8H9NO2` share one decomposition tree** — correct and honest for a
  *stoichiometric* decomposer, and the boundary must say so. Structure-aware descent (bond-graph
  transformations constraining which edges are even admissible, using `Molecule.bonds` + the
  WL-canonical machinery already in `category.py`) is a **v2** rung: richer, and much harder.
  Note: the user's intuition that acetone is denser than water holds *at formula level too* (more
  atoms, more elements → more intermediate routes), so v1 already captures the core ask.

- **Closed declared inventory first, generative intermediates later.** "All possible" is only
  well-defined relative to a declared intermediate species set `S` and terminal set `E` — the
  closed-registry pattern this repo already lives by. An *open* mode that generates candidate
  intermediates (every balanced sub-formula within budget) is strictly more explosive and is a
  later, separately-gated mode.

---

## Part 4 — What already exists (portal-gun map; ~70% is reuse)

| Need | Reuse |
|---|---|
| Exact integer mass balance / all balanced relations over a species set | `stoichiometry.composition_matrix`, `integer_kernel_basis`, `stoichiometry_menu`, `Completion` |
| Conservation predicate on a candidate reaction | `category.conserves`, `category.reaction_residue` |
| Types: compound, multiset state, reaction | `category.Molecule` (optional bonds), `Config`, `Reaction`; `formula_of` |
| Element table + standard atoms | `atoms.PT` |
| Search scaffolding (the downward/retro dual of forward mechanism search) | `pathway.Pathway` monad, `pathway.search` (new descent search, same monad) |
| Termination measure + descent guard | multiset-order doctrine, transplanted |
| Budget + loud refusal-above-candidate-budget | the `open_diagram` budgeted observer pattern |
| Presentation-invariant identity for the DAG (two orderings → one digest) | `canonical_digest` (the same primitive `CircuitModelIR` uses) — the DAG becomes a frozen `Digestible` |

The genuinely *new* code is the descent search, the AND–OR DAG value, the budget policy, and
the executor+verifier+certificate wiring. The math engine is bought, not built.

---

## Part 5 — Where it slots + the build ladder (M-4, B0–B4)

**Slot:** a candidate **10th executor** (`DecompositionExecutor`) — which makes it the *first
real test* of the claim S-1 (registry-completeness guard, `9210a04`) made: that adding an
executor is now safe by construction. It therefore MUST land with the S-1 guard green, a
`_observable_payload_error` branch, a `structure_attachment_for_subject` decision, and a
production-independent verifier. The DAG output is also an early concrete instance of the
long-term `ExecutionDAG` face (a decomposition DAG is a feedback-free execution graph), noted
as a seed, not committed.

House style: each rung carries *Accept / Dep / Risk / Verdict-changing test.*

- **B0 — the object + the termination proof.** A frozen `Digestible` `DecompositionGraph`
  (nodes = species, hyperedges = conserving `Reaction`s, leaves ⊆ declared `E`). Define `M`
  (multiset complexity order) and prove every admissible hyperedge strictly decreases it.
  *Accept:* `M` well-founded; a non-descending edge is refused at construction, and the guard is
  proven non-vacuous. *Dep:* `[[well-founded-measure-is-the-multiset-order]]`. *Risk:* a descent
  guard blind to a missing sort. *Verdict-changing test:* water → the single elemental hyperedge;
  a planted ascending/cyclic edge → REFUSED.

- **B1 — balanced-edge generator over a closed inventory.** Given target + `(S, E)`, enumerate
  all conserving hyperedges `X → lower products` via the integer-kernel engine, filtered by `M`.
  *Accept:* every emitted edge passes `conserves`; enumeration complete over `(S,E)` up to budget,
  checked against a hand-enumerated small case. *Dep:* B0, `integer_kernel_basis`. *Risk:* the
  kernel admits ascending/non-elementary combinations → the `M` filter is load-bearing.
  *Verdict-changing test:* CH₄ or H₂O₂ over a small inventory → the exact hand-computed edge set;
  a non-conserving candidate → excluded.

- **B2 — recursive AND–OR DAG builder + budget refusal.** Recurse to elements; bound
  depth/candidate count; refuse loudly above budget. *Accept:* water/CH₄ terminate shallow and
  complete; acetone `C3H6O` yields a multi-layer DAG *or* a clean budget-REFUSAL — never a silent
  partial. *Dep:* B1, open-diagram budget pattern. *Risk:* silent truncation certified as complete
  (the arc-III disease). *Verdict-changing test:* an over-budget target → REFUSED with the budget
  named, not a truncated DAG certified complete.

- **B3 — executor + independent verifier + honest tier.** Wire `DecompositionExecutor` into the
  closed registry with: S-1 guard green, payload-error branch, structure-attachment decision, a
  **production-independent** verifier that re-derives every hyperedge's conservation and the
  leaf-completeness by an independent path, and the `FORMAL/EXACT/CERTIFIED`-for-conservation tier
  + realizability-refusal casualty list on every certificate. *Accept:* full certificate with
  casualties; verifier disagreement → INVALID; registry guard green. *Dep:* B2, S-1 machinery.
  *Risk:* the certificate leaks an implied realizability claim → banner + tier + casualty list,
  tested that no `EvidenceStatus` is raised past the formal floor. *Verdict-changing test:* the
  acetaminophen certificate names its casualties (no ΔG, no kinetics, no mechanism); a mutant that
  drops a casualty → refused by the tier guard.

- **B4 — thermodynamic decoration (mid→long; SEPARATE go).** Optionally annotate each hyperedge
  with ΔH from `thermo.py` / `data/reference.py` *only where the reference tables cover the
  species*, as a **separate evidence layer** — still not kinetics, still not realizability, marking
  uncovered species UNKNOWN rather than guessing. This is where "which decompositions are
  real-ish" begins, honestly tiered. Deferred; earns itself only after B0–B3 land and a consumer
  wants ranking.

---

## Part 6 — Open decisions (owner's call, before B0)

These reshape the build; recorded here rather than silently chosen. Recommendation attached.

1. **Executor vs. compiler-analysis tool.** *Rec: 10th executor* — it fits the shape, inherits
   the certificate/verifier machinery, and forces the honest tier. Cost: a real registry event.
2. **Formula-level v1 vs. structure-level v1.** *Rec: formula-level v1* (matches `Config`, finite,
   clean boundary); structure-aware descent is v2.
3. **Closed inventory vs. open generative intermediates.** *Rec: closed-first*; open mode later,
   separately gated.
4. **Terminal elemental form.** *Rec: elements in declared standard states* (C graphite, H₂, N₂,
   O₂, metals as solids), so `2 C8H9NO2 → 16 C + 9 H2 + N2 + 2 O2` is the full-descent endpoint.
   Confirm "bare elements" means standard states, not monatomic gases.

---

## Continuation authority

- Governing laws / scientific boundaries: `DIRECTION_AUDIT_2026-07-27.md` (untouched).
- Current roadmap this extends: `ROADMAP_2026-08-06.md` (this is its new **M-4**).
- On authorization: start B0 (object + termination proof) after decisions 1–4 are fixed. The
  math engine is reuse; the discipline (termination, budget-refusal, formal≠physical tier,
  independent verifier) is the actual work.

---

## Part 7 — Execution addendum (2026-08-30): B0–B2 built and verified

The four decisions were fixed with the owner: **(1)** 10th executor; **(2)** formula-level v1,
structure v2; **(3)** closed inventory v1, open v2; **(4)** terminals are **element buckets
counted in atoms** (`O`/`O2` are one bucket), with the familiar molecular packaging kept as a
*reporting* layer, not a terminal identity. The owner also sharpened the framing to its dual —
"given buckets of each element, how full must each be, and by what chains do they assemble to
X" — which is the **same hypergraph read leaves-to-root**; and the bucket-fullness question is
*forced by conservation* (it is the target's own formula), so only the routing is searched.

**Landed — `smartchem/decompiler.py` + `tests/test_decompiler.py` (35 tests; full suite
1659 passed, 14 skipped, 1 xfailed — baseline 1624 + 35, zero regressions):**

- **`Formula`** — the honest formula-level species (atom multiset + charge), a `Digestible`.
  Necessary because `category.Molecule` *requires bond-connectivity* for any n>1 species, so a
  bond-free "just the formula" molecule is illegal there — and injecting fake bonds would assert
  structure that isn't there. Parses `C8H9NO2` / `(NH4)2SO4`, validates elements against
  `atoms.PT` (refuses unknowns by name), collapses isomers by construction (the v1 contract).
- **B0 — `DecompositionEdge`** — one AND hyperedge `n · reactant → products`, with every
  invariant enforced at construction: exact conservation, **W1 descent** (every product strictly
  lower rank — the termination proof; it *bites*, rejecting `2 H2O → H2 + H2O2` because H2O2 is
  larger than H2O), ≥2 product instances, canonical unit-bucket spelling, and primitivity. The
  descent guard is proven **non-vacuous** (a genuine descending edge builds).
- **B1 — `admissible_edges`** — enumerates every primitive conserving decomposition over a
  closed inventory. Key algorithmic move: branch only over *molecular* candidates and **force**
  the leftover atoms into unit element buckets (one way, deterministic) — so the cost is the true
  solution count, not a cloud of dead partial-bucket branches (the first cut exploded on acetone
  before the fix). Returns an explicit `complete` flag; a budget hit is reported, never a silent
  subset. `max_multiplicity=1` default (the atom floor + all whole-number splits); n>1 is the
  opt-in fraction-clearing knob.
- **B2 — `DecompositionGraph` + `build_decomposition`** — the AND–OR DAG, a presentation-invariant
  `Digestible`. `status` is `COMPLETE` only when the whole reachable graph fit the budget;
  `REFUSED_BUDGET` carries a partial graph **and a reason**, and can never read as complete (W2 —
  the arc-III vacuity disease, pre-empted). Measured: water → 1 edge (`H2O → 2 H + O`, the one
  family); acetone/`C3H6O` over a generic inventory → COMPLETE, 19 edges / 9 nodes; paracetamol
  → COMPLETE, 145 edges / 15 nodes — denser, as predicted. Identity is deterministic and
  representation-independent (a dict target and a string target digest equal).
- **Reporting — `standard_state_equation`** — repackages the forced atom buckets into reference
  molecules with the minimal integer scaling (`2 H2O → 2 H2 + O2`): decision 4's coherent "2
  part" bookkeeping, explicitly a conservation-reporting convenience, not a physical or reaction
  claim.

**Deliberately NOT done this cut (held for B3, its own focused pass):** the module is *not* wired
into the closed executor registry or the top-level public API, and there is no certificate/tier
or production-independent verifier yet. That is the architectural, registry-touching step — it
must land with the S-1 completeness guard green, a payload-error branch, a structure-attachment
decision, the `FORMAL/EXACT/CERTIFIED`-for-conservation tier + realizability-refusal casualty
list, and an independent verifier (the `stoichiometry.integer_kernel_basis` engine is the natural
second blind path). Also open: exposing `smartchem.decompiler` on the lazy public API (touches the
`__all__`/`_ATTR_SOURCE` lockstep), and B4 thermodynamic decoration.

**Stated v1 boundaries (honest walls, not hidden):** formula-level (all isomers of a formula
share one graph); neutral species only (a charged target is refused); completeness is over
`(declared inventory, n ≤ max_multiplicity)`; and — the load-bearing one — this certifies
*conservation*, never chemistry: no thermodynamics, kinetics, mechanism, or synthesizability.

---

## Part 8 — M-4b: the conditions-aware (comonadic) decompiler

**Direction from the owner (2026-08-30):** the decompiler must be *smart* — it must answer
"**under what conditions is this reaction possible?**", account for **things in solution** and
**reaction byproducts**, and rank pathways by a **multi-dimensional feasibility cost**, so that a
path that looks infeasible on sheer input volume may actually be *simpler* than a low-volume path
that demands extreme temperature/pressure/time. And — the deep one — a product that is stable only
for milliseconds *because of the very conditions that enabled its formation* should still be
**surfaced, not pruned**: a chemist may have no use for it, but the information is real.

This is not a field on an edge. It is the **dual** of what M-4 v1 built, and factoring it as the
dual is what keeps it honest and reusable.

### Why comonadic — precisely, not as ornament

M-4 v1 is the **structural skeleton**: the space of all conservation-valid decompositions,
*context-free*. The repo's `pathway.Pathway` is already a **monad** (`pure`/`bind`/`map`, with
`downhill`/`spontaneous` energy notions) — it models a computation that *produces* a reaction
network and accumulates effects (`Tally`). Conditions are the **comonadic** dual: an edge is not a
free-standing fact, it is a value *embedded in a condition context*, and the operations you want
are the comonad's — `extract` (the product *as actually realized in this context*), `extend`
(re-evaluate a context-dependent predicate over every sub-context of a chain), `duplicate` (expose
the whole tower of nested condition envelopes down a chain).

Two concrete comonads name the two jobs:

* **The Env (coreader) comonad** `Env C a = (C, a)` — an edge (or product) *paired with its
  condition envelope* `C`, with `extract = snd` and `extend f (c, a) = (c, f (c, a))`. This is the
  home of "under what conditions is this edge possible". Crucially, **chain feasibility is a
  co-property, not a product of edge-local feasibilities**: the conditions that enable step 3 may
  destroy the product of step 1, so you must evaluate the *whole* chain inside *one coherent
  envelope* — exactly what a comonad's context-propagation expresses, and exactly what independent
  per-edge checks miss. The **milliseconds-stability** case is precisely `extract` *failing*: the
  value does not survive extraction from the context that produced it. Comonadic, not monadic — and
  we retain the flagged value rather than dropping it, honoring "the information is still useful".
* **The Store comonad** `Store S a = (S -> a, S)` — a reaction *focused at one point* of the
  condition space `S` (a chosen T/P/time/medium) with the ability to **peek** at neighboring
  conditions. This is the home of the **feasibility landscape and the trade-off frontier**: peek
  the same decomposition across the T/P/time surface, and surface the **Pareto-optimal** pathways
  over the cost vector rather than collapsing to one "cheapest".

### The four asks, mapped to design

1. **Conditions of possibility.** Each `DecompositionEdge` carries zero-or-more
   `ConditionEnvelope`s (T range, P range, time scale, medium/solvent, catalysts, applied field),
   each with its own `EvidenceStatus`. **Most edges will carry NONE** — the honest default is
   `UNKNOWN`, loudly, never a guessed envelope (W-cond-1 below).
2. **Stability under the enabling conditions.** A product-in-context carries a `stability_window`
   (a lifetime/regime bound). A product stable only transiently under its enabling envelope is
   **retained and flagged** (`extract`-fails), not pruned. The chemist filters; the decompiler
   informs.
3. **Things in solution + byproducts.** Edges may be **mediated**: `n·R (+ reagents drawn from a
   declared medium) -> products (+ byproducts released to the medium)`, where the *full* system
   conserves and a **separate medium ledger** tracks reagents consumed / byproducts released /
   catalysts returned. Catalysts are the spectator-residue case (in = out) — this reuses the repo's
   already-*verified* spectator-residue transform and `category.reaction_residue` /
   `is_catalytic` / `catalytic_cycle`. The medium is a **closed declared inventory** (the registry
   pattern again), not open.
4. **Multi-dimensional feasibility cost.** A pathway's cost is a **vector** — element-volume/quantity
   *and* condition-severity (T, P, time, energy input) — and these are Pareto-incomparable. The
   decompiler exposes the **Pareto frontier** and the trade-off surface (the "less input but extreme
   conditions vs. more input at mild conditions" comparison), ranked by a **declared** cost model,
   never asserting a single physical "best".

### The boundary that keeps this from becoming a liar (W3, sharpened)

Everything in M-4b is a **separate, honestly-tiered EVIDENCE LAYER decorating the CERTIFIED formal
skeleton**. Conditions, stability, and cost are **reference-sourced** (`thermo.py`,
`data/reference.py`, or a pluggable oracle), enter the ledger as `EXPERIMENTAL` (or below), and are
`UNKNOWN` wherever the data does not cover the edge — *never computed-then-asserted as prediction*.
The conditions layer **never upgrades the skeleton's conservation status**, and a suggestive
envelope never becomes a claim that the reaction *occurs*. This is the M-4 v1 `ClaimKind` ⊥
`EvidenceStatus` split doing exactly its job, one layer up: the structure is `LITERAL`/certified for
*conservation*; the conditions are `EXPERIMENTAL_PROXY`/`EXPERIMENTAL` for *possibility*, and the two
never bleed. It is also the cleanest concrete driver yet for the long-term **ModelIR (skeleton) /
EvidenceIR (conditions) / ExecutionDAG** separation: the skeleton *is* a ModelIR/ExecutionDAG, the
comonadic conditions layer *is* an EvidenceIR.

### The walls (each real, each named)

* **W-cond-1 — data sparsity is the norm.** The overwhelming majority of formal edges have no
  reference condition data. The layer must make `UNKNOWN` the loud, first-class default and refuse to
  fabricate an envelope. A conditions decompiler that guesses is worse than the formal one that admits
  it knows only conservation.
* **W-cond-2 — chain co-validity is combinatorial.** Evaluating whole-chain feasibility under a shared
  envelope (the comonadic `extend`) over the already-dense AND–OR graph is a new blow-up; it needs its
  own budget + loud refusal, same discipline as W2.
* **W-cond-3 — mediated conservation must be formalized cleanly.** Two ledgers (target-descent +
  medium) with catalysts as spectator-residue; getting this wrong re-introduces "matter from nowhere"
  through the solvent. The verified spectator-residue transform is the anchor, not a new hand-rolled
  balance.
* **W-cond-4 — computed stability/energetics is a physics claim.** ΔG/ΔH *lookups* are decoration;
  *computing* stability windows or reaction feasibility from a model is real physics and enters the
  certified oracle lanes' rules (PySCF etc.), not a decorator's. Draw that line at C-level explicitly.

### Reuse map (portal-gun, again ~mostly-there)

| Need | Reuse |
|---|---|
| The monad to dualize; energy/spontaneity proto-notions | `pathway.Pathway` (`downhill`/`spontaneous`), `pathway.Mechanism.energy_ev`, `pathway.search` |
| Byproduct / catalyst / medium accounting | verified spectator-residue transform (reaction-energy executor), `category.reaction_residue`, `is_catalytic`, `is_regenerated`, `catalytic_cycle` |
| Condition / thermodynamic data source | `thermo.py`, `data/reference.py` (coverage-gated; `UNKNOWN` outside it) |
| Honest tiering of the evidence layer | `contracts.EvidenceStatus` ⊥ `ClaimKind`, the `EvidenceRecord` model from `smartchem.evidence` |
| The structural skeleton it decorates | M-4 v1 `DecompositionGraph` / `DecompositionEdge` (built, unchanged) |

### Build ladder (M-4b, C0–C4; supersedes and absorbs the old "B4 thermo decoration")

* **C0 — `ConditionEnvelope` + the Env-comonad structure.** The condition context type (T/P/time/
  medium/catalyst/field, all ranges) and `Conditioned[X] = Env(envelope, X)` with `extract`/`extend`.
  *Accept:* comonad laws hold (left/right identity, associativity of `extend`) as property tests; an
  envelope is a *declared context*, never a prediction. *Verdict-changing test:* the comonad laws;
  and an unsourced envelope is refused/`UNKNOWN`, not fabricated.
* **C1 — condition-annotated edges + coverage-gated evidence.** Attach envelopes to edges from
  reference data, tiered `EXPERIMENTAL`; `UNKNOWN` wherever uncovered. *Accept:* an edge outside the
  data returns `UNKNOWN` (loud), never a guess; a covered edge carries its source + status.
  *Verdict-changing test:* a fabricated/over-tiered envelope is refused; coverage boundary is exact.
* **C2 — mediated edges (solution + byproducts).** Extend to a closed medium inventory with the
  two-ledger conservation; catalysts via the spectator-residue transform. *Accept:* the full system
  conserves and the medium ledger balances (catalyst in = out); a mediated edge that leaks matter
  through the medium is refused. *Verdict-changing test:* a planted solvent-borne matter leak → refused.
* **C3 — stability-under-enabling-conditions (`extract`).** Annotate products with stability windows;
  surface (never prune) transiently-stable products. *Accept:* an `extract`-failing product is
  retained and flagged, and whole-chain co-validity under one envelope is evaluated (the `extend`),
  budgeted with a loud refusal (W-cond-2). *Verdict-changing test:* a chain whose step-1 product dies
  under step-3's conditions is flagged co-infeasible, not reported feasible.
* **C4 — Store-comonad cost landscape + Pareto frontier.** The cost vector and the trade-off surface;
  expose Pareto-optimal pathways, peeking across the condition space. *Accept:* the frontier is
  correct on a hand-built case (a low-volume/extreme path and a high-volume/mild path both surface as
  non-dominated); ranking uses a *declared* cost model. *Verdict-changing test:* neither path is
  silently dropped; changing the declared weights re-orders without hiding the frontier.

### Open decisions (owner's call, before C0)

1. **Medium model** — closed declared medium inventory (recommended, matches v1/the registry) vs. an
   open reagent generator.
2. **Condition data source** — reference tables only (recommended first) vs. a pluggable conditions
   oracle (and if so, does it enter the certified lane, W-cond-4).
3. **Stability** — reference/lookup windows only (recommended) vs. computed stability (a physics claim
   → the oracle lane, not a decorator).
4. **Cost model** — a fixed cost vector vs. user-declared weights over the condition dimensions
   (recommended: declared, so the frontier is honest and the ranking is the caller's stated policy).

**Sequencing:** M-4b sits *above* M-4 v1 (built) and is independent of B3 (the executor wiring) —
though B3's certificate/tier is the natural place the conditions `EvidenceRecord` eventually attaches.
**C0 is now built** (Part 9); C1–C4 remain the factored vision.

---

## Part 9 — Execution (C0) + the paracetamol litmus, pinned to literature

**C0 built** — `smartchem/conditions.py` + `tests/test_conditions.py` (83 tests; full suite green,
ruff clean). The **Env comonad** `Env C a = (C, a)`: `ConditionEnvelope` (temperature/pressure/
duration `Interval`s, medium, catalysts, applied field — the EM-scope hook — plus an
`EvidenceStatus` + provenance), `Conditioned[A]` with `extract`/`extend`/`duplicate`/`map`, and the
point-free `extract`/`extend`/`duplicate`. **The three comonad laws are property-tested** over
representative (envelope, value) pairs with context-*reading* functions (so `extend` is non-trivial).
The tiering gates are isolated and bite: the empty `unknown()` is the only `UNSUPPORTED` envelope; any
declared condition **requires a provenance** (no fabricated envelope); the status is **capped below
the certified lane** (no label-borrowing). Nothing computes chemistry — this is the pure context
algebra C1–C4 hang on.

**The litmus (the standing acceptance gate for the whole M-4 line):** *Could a real chemist use our
paracetamol decompilation to pick real steps that make the reaction happen?* Run it at every rung,
pinned to a known truth rather than our own say-so.

*Known truth (literature-pinned):* synthesis is `p-aminophenol (C6H7NO) + acetic anhydride (C4H6O3)
→ paracetamol (C8H9NO2) + acetic acid (C2H4O2)` (H2SO4 cat.); degradation is `paracetamol + H2O →
4-aminophenol + acetic acid` (acidic amide hydrolysis; 4-aminophenol is the regulated ≤50 ppm
degradant). Sources: ACS *J. Chem. Ed.* 10.1021/acs.jchemed.3c00549; RSC *Anal. Methods* c3ay40747k.

*What v1 actually produces* (measured, not asserted): COMPLETE, ~124 edges / 14 nodes, **80 direct
edges**. It **does contain the correct backbone** — `paracetamol → p-aminophenol + ketene`
(`C8H9NO2 = C6H7NO + C2H2O`), which is the **anhydrous skeleton of the real hydrolysis** (ketene +
H2O → acetic acid). The chemist-recognisable `p-aminophenol + acetic acid` does not balance without
water (`= C8H11NO3 = paracetamol + H2O`).

*Verdict:* **NO — a chemist could not yet pick real steps from v1 alone — but the skeleton is
under-decorated, not misdirected** (the real backbone is in there). The three gaps map exactly to the
plan:
1. the real route is **mediated** (water / anhydride from solution); v1 shows the dehydrated ketene
   skeleton → **C2**;
2. the real edge is **1 of 80**, unrankable next to `→ C + CO + C6H7NO + 2 H` → **C1 + C4**;
3. **formula-level** `C6H7NO` is not an actionable structure → **v2**.

This is the encouraging read: the formal foundation is *sound* (it holds the real pathway's skeleton),
and turning the litmus from NO to YES is precisely what C1/C2/C4 + v2 do. The litmus is recorded as a
standing benchmark; re-run it at each rung.

---

## Part 10 — Execution: the review layer (safety screen + coherence ranking)

**Built** — `smartchem/decompiler_review.py` + `tests/test_decompiler_review.py` (15 tests; full
suite 1757 passed, zero regressions; ruff clean). Two jobs, both aimed straight at the litmus, both
honest about their tier.

- **Structural coherence ranking (C4 structural half; data-free).** `coherence_score(edge)` = the
  fraction of product content that is a *declared compound* rather than an element bucket;
  `review_graph` sorts by it. Measured: for paracetamol the real backbone
  `C8H9NO2 → p-aminophenol + ketene` (score **1.00**) now ranks **#1 of 80**, above the element
  shrapnel — the litmus's "1-of-80-unrankable" gap, closed by a pure structural heuristic (labelled a
  presentation heuristic, not feasibility).
- **Safety screen (the owner's ask: inform, never neuter).** `screen_edge` **always** returns a
  `HazardProfile` — no decomposition is ever hidden or refused for being dangerous. The energetics are
  **real**: assembly reaction enthalpy at 0 K from NIST/CCCBDB formation enthalpies
  (`smartchem.data.reference`), and **Verified by a second blind path** — the assembly enthalpy equals
  `reference.atomization_energy_ev` computed by an independent route (H2O −9.5113 eV, CO2 −16.561 eV,
  agree to 1e-9). Assembling from bare atoms is strongly exothermic and is flagged with the actual
  number (`EXOTHERMIC_ASSEMBLY`). Two honesty rules: **UNKNOWN is not safe** — an uncovered edge is a
  loud `ENERGETICS_UNKNOWN`, never an absent flag read as a clearance (paracetamol itself is
  UNKNOWN — no tabulated dfH); and **formula-level ambiguity is surfaced** — a composition with several
  tabulated isomers (C2H6O = ethanol/DME) carries an enthalpy *interval* and `ISOMER_AMBIGUOUS`, not a
  false single number. A `SAFETY_BANNER` states the doctrine. It is a screening estimate (0 K, ideal,
  from atoms), never the enthalpy under real reagents/conditions; it decorates, never upgrades, the
  certified skeleton.

**Litmus movement:** the real backbone now *surfaces ranked and safety-annotated* — a real gain. Still
NO on "run the actual steps," because the runnable reaction is **mediated** (`paracetamol + H2O →
4-aminophenol + acetic acid`), which needs **C2** (mediated edges + medium ledger). C2 is the next
rung and the linchpin for the litmus flipping to YES.

---

## Part 11 — Execution: C2 mediated (solution / byproduct) edges — the litmus reaction is generated

**Built** — `smartchem/decompiler_mediated.py` + `tests/test_decompiler_mediated.py` (11 tests; full
suite 1768 passed, zero regressions; ruff clean). A `MediatedEdge` is
`n . reactant + reagents (from a declared closed medium) -> products`, with every invariant enforced:
**augmented-system conservation** (`n.reactant + reagents == products`), **descent** (every product
*and* reagent strictly lower rank than the reactant, so termination is unchanged from v1), **genuine
mediation** (≥1 reagent, and no species is both a reagent and a product — a pass-through would be a
plain decomposition with a spectator; catalytic regeneration is a C2b refinement), a real split (≥2
products), canonical bucket spelling, primitivity. The generator `mediated_edges` reuses v1's
bucket-forced solver against the augmented target `n.reactant + reagents`, enumerating reagent
multisets from the medium; v1 itself is untouched.

**The litmus reaction is now generated.** Measured:
`mediated_edges("C8H9NO2", inventory=["C6H7NO","C2H4O2"], medium=["H2O"])` produces
**`C8H9NO2 + H2O -> C2H4O2 + C6H7NO`** — paracetamol + water → acetic acid + 4-aminophenol, the exact
literature hydrolysis (Part 9), which v1's own-atoms-only model *structurally could not represent*.
With no medium there are no mediated edges (mediation genuinely requires a reagent from solution).

**Litmus status now:** the real, runnable reaction is **representable, generated, conserving, and (via
the review layer) rankable and safety-screenable** — no longer a flat NO. The remaining gaps to a full
YES for an arbitrary target from bare elements, each a named next step:
1. ~~**mediated-graph recursion**~~ — **DONE**: `MediatedDecompositionGraph` + `mediated_decompose`
   recurse the whole descent to element buckets using both plain and mediated steps (medium is a
   reservoir), terminating (every product strictly lower rank) with a loud `REFUSED_BUDGET`.
   Measured: acetic acid → COMPLETE, 15 plain + 10 mediated edges to C/H/O, no stuck node.
2. ~~**review/coherence over `MediatedEdge`**~~ — **DONE**;
3. ~~**conditions data (C1) mechanism**~~ — **DONE (seed)**: `decompiler_conditions.reaction_conditions`
   attaches sourced C0 `ConditionEnvelope`s to edges by scale-independent reaction signature, wired
   into `EdgeReview.conditions`. The paracetamol hydrolysis carries its literature conditions
   (`aqueous, acidic`, RSC provenance); every un-tabulated edge is a loud `unknown()`. **Coverage** (a
   real conditions database beyond the one-reaction seed) is the remaining *data* work;
4. **structure (v2)** — `C6H7NO` is still a formula, not the specific p-aminophenol a chemist acts on.

**Where the litmus stands after this session.** The whole M-4b *framework* is built: C0 (Env comonad),
the safety screen (source-backed, cross-verified, inform-never-neuter), coherence ranking, C2 (mediated
edges), C2b (recursive mediated graph), the unified `decompile_and_review`, and C1 (sourced-conditions
mechanism). For the paracetamol reaction specifically the litmus is effectively **YES**: one call yields
the real `C8H9NO2 + H2O → C2H4O2 + C6H7NO` ranked #1, conservation-certified, safety-screened, and
carrying its sourced conditions. What stands between here and a *general* YES for an arbitrary target is
no longer framework — it is **data** (a real conditions/hazard database; the enthalpy and conditions
tables are small) and **structure** (v2 bond graphs, so a formula resolves to the specific isomer a
chemist acts on). Both are their own efforts; the machinery to consume them is in place and honest
(UNKNOWN is loud everywhere the data runs out).

**Update — unified review landed (gap #2 closed).** `decompiler_review` now scores and safety-screens
**both** plain and mediated edges (`AnyEdge`), and `decompile_and_review(target, inventory, medium)` is
the single chemist-facing entry: it generates plain + mediated direct edges and reviews them together.
The energy balance now adds reagents to the reactant side (a hydrolysis is scored with its water),
cross-verified — for `DME + H2O → 2 MeOH` the structure-resolved `reference.reaction_energy_ev` (0.2622
eV) falls inside the formula-level interval [0.2622, 0.7856] eV. Measured: for paracetamol the real
hydrolysis `C8H9NO2 + H2O → C2H4O2 + C6H7NO` surfaces **ranked #1** (coherence 1.0) and safety-screened,
in one call. 5 new tests; full suite 1773 passed. The **direct-reaction view is now coherent**; C2b
(recursion) is what extends that coherence to the whole chain from bare elements.

## Part 12 — Execution: data + structure (v2 rung 1) — the litmus made actionable

**Built this session (four coherent commits, pushed):** the two efforts Part 11 named as "no longer
framework — data and structure" are now standing, consumed by the honest machinery already in place.

- **Structure bridge** (`smartchem/structure.py`, commit `b9b995f`). `NamedStructure(Digestible)` over
  the existing `category.Molecule` bond graph (relocate, don't reinvent — no new graph type). The
  forgetful `structure -> Formula` map is `Formula.of(molecule.formula, molecule.charge)`;
  `structure_identity` is the `canonical_digest` of `Molecule.canonical()` (1-WL), presentation-
  invariant, with an honest `asgiven:` fallback if canonicalization refuses. A hand-entered,
  guard-verified registry of the six litmus species (water, ketene, acetic acid, acetic anhydride,
  4-aminophenol, paracetamol) — each molecule's composition checked against its declared formula at
  import, so a mistyped atom list fails loudly. `C6H7NO` now resolves to **4-aminophenol** (CAS,
  synonyms, real bond graph), closing litmus gap #3 at the name/identity level. Tests are differential:
  the guard is shown to reject a wrong formula; the identity is shown both relabel-**invariant** and
  isomer-**separating** (acetic acid vs methyl formate, same formula, different id).

- **Hazard data** (`smartchem/data/hazards.py`, commit `228ce4e`). Sourced, tiered `HazardRef` records
  (GHS + reactivity + exposure limits + regulatory/tox) for the five litmus species, from PubChem GHS
  (ECHA aggregates), CAMEO Chemicals (NOAA), and NJ DOH Right-to-Know fact sheets. Ketene reads *fatal
  if inhaled, polymerises explosively*; 4-aminophenol carries its **USP <227>** regulated-degradant
  status (~50 ppm cap); acetic anhydride warns *reacts violently with water*. A record cannot be
  UNSUPPORTED or source-less; absence is UNKNOWN (a loud gap), never a clearance.

- **Thermochemistry** (`smartchem/data/decompiler_thermo.py`, commit `b90cde8`), **separate from the
  oracle benchmark** so provisional values can never corrupt its MAE. What the sourcing pass honestly
  established: ketene (0 K −44.51) and acetic acid (0 K −418.10) — two independent sources agree,
  `ESTABLISHED`, usable; paracetamol — single-source **298 K** (−280.5), stored for display but the 0 K
  accessor filters it out (mixing conventions is the silent error `reference.py` warns of), so its edges
  stay UNKNOWN; 4-aminophenol (two sources disagree by 9 kJ/mol) and acetic-anhydride gas (only a liquid
  value) — recorded in `THERMO_GAPS` with the reason. **The data pull proved the litmus hydrolysis
  energetics genuinely cannot be certified from literature** — a result, not a failure of the machine.

- **Integration** (`decompiler_review.py`, `decompiler_conditions.py`, commit `a79927a`). One
  `decompile_and_review` call on paracetamol now surfaces, for the real routes, **named** compounds
  (`C6H7NO (4-aminophenol)`), **attached** sourced hazards (`DOCUMENTED_HAZARD`), **broadened**
  energetics (ketene/acetic-acid edges get real assembly enthalpies; paracetamol/4-aminophenol stay
  honestly UNKNOWN), and **sourced synthesis conditions** for both the ketene-acetylation route (reverse
  of the coherence-1.0 backbone) and the acetic-anhydride route (the standard lab synthesis). Nothing is
  filtered — inform-never-neuter throughout. Full suite **1823 passed** (was 1782), zero regressions.

**Litmus status now.** For paracetamol a chemist reading the output gets the three real routes to/from
the compound, each named, hazard-annotated, and condition-annotated — enough to *pick real steps*
(e.g. "reverse of the acetic-anhydride edge is my synthesis; run it cooled; acetic anhydride reacts
violently with water"). The energetics are honestly UNKNOWN exactly where the literature is.

**What remains (each its own effort, none of it this session's framework):**
1. **Data coverage** — the thermo/hazard/conditions tables are the litmus set plus neighbours, not a
   database. Broaden with the same tiered, sourced, second-source discipline (ketene and acetic acid
   meet the benchmark standard and could later be *promoted* into `POLYATOMIC_REFS` as a deliberate,
   split-aware act).
2. **Structure-aware DESCENT (v2 proper)** — today structure resolves *names* on a formula-level graph;
   the deeper v2 is bond-graph-aware decomposition (break specific bonds), where N- vs O-acetylation
   selectivity becomes representable rather than a formula-level ambiguity.
3. **Public-API exposure** — `smartchem.decompiler`/`structure` are not yet on the lazy `__init__`
   surface (the `__all__`/`_ATTR_SOURCE` lockstep); a deliberate, separate act when wanted.

**Adversarial hardening (commit `7c3f5a0`).** Before the arc was called done, an adversarial pass
(evil-morty) attacked the new layer for the repo's known disease family. It broke three surfaces and
signed four as holding. Fixed, each with a regression test firing on the counterexample: **F1** the
hazard channel was silent when blind (a species with no record produced no flag, so partial coverage
read as assessed-clean) → `HAZARDS_UNASSESSED` now fires and names the gap, symmetric with
`ENERGETICS_UNKNOWN`; **F2** a single isomer was presented as identity → `ISOMER_ASSUMED` now marks
any formula-level name/hazard attachment; **F3** `ISOMER_AMBIGUOUS` under-fired (sign-crossing only,
missing its own C2H6O docstring example) → now fires on any non-degenerate interval; **F4** corrected
`structure._check`'s over-claim (composition + connectivity, not isomer identity); **F5** strengthened
the cross-coherence guard to assert each hazard/thermo formula pins exactly one registered isomer.
Held under real attack: the 298 K→0 K convention firewall, the whole-token equation annotator, the
canonical identity's separation/relabel-invariance, and the W3 forward-reaction framing.

## Part 13 — Execution: structure-aware DESCENT (v2 proper) + the capability-gap map

Part 12's own tail named "structure-aware DESCENT (v2 proper)" as the next build: *bond-graph-aware
decomposition (break specific bonds), where N- vs O-acetylation becomes representable rather than a
formula-level ambiguity.* This part records that it is **built and pushed**, and then — the second
half of the ask, "plan anything we are still structurally incapable of doing that we should be" —
maps every wall this build hit, each classified so a future session knows whether to climb it, source
it, or leave it uncrossed by law.

### 13.0 — What got built (`smartchem/structure_descent.py`, commits `d514673`, `66dbb4a`, `59361cf`)

- **Pure scission (rung 1).** A `ScissionEdge` cuts a set of bonds from a `category.Molecule` and reads
  off the connected components as `Fragment`s — specific radical sub-structures with recorded open
  valences, not bare compositions. The constructor is a full self-certificate: partition of the
  parent's atoms, fragment-graph fidelity (no fabricated bond), valence conserved atom-by-atom
  (`used + open == parent degree`), and W1 descent forced by the partition. `ScissionEdge.forget()`
  is the **soundness bridge**: every scission projects to a valid v1 `DecompositionEdge`, so
  structure-level descent is a *refinement* of formula-level descent, not a parallel engine. The
  presentation-invariant `signature` deduplicates symmetry-equivalent cuts (proven on the para ring's
  mirror-paired C–H bonds: 14 bridges → 12 scissions).
- **Capped scission (rung 2).** A `CappedScission` is a **valence-preserving bond rewrite**: break
  `cut` bonds, form `caps` bonds, read off the closed products. The object *is* the plan; products are
  derived, so there is nothing to lie about. The certificate is the structural teeth — every atom
  keeps its exact valence (order removed == order added), products connected + closed, reactant
  genuinely cleaved across ≥2 products, reagent consumed, W1 descent. `forget()` lands the existing
  `MediatedEdge`, so a structure-derived reaction flows through the whole review layer unchanged.
- **The litmus, mechanized.** `capped_scissions(paracetamol, water)` **derives**
  `C8H9NO2 + H2O → C2H4O2 + C6H7NO` and **proves by canonical graph-equality** against the sourced
  structure registry that the products *are* 4-aminophenol and acetic acid — not hand-entered, derived
  and checked. The engine honestly enumerates all seven valence-valid rewrites of that bond+water (the
  acetaldehyde variant, the phenol-cleavage variant, …); the registry match picks the real one.
  **Structure enumerates, evidence identifies** — that division of labour is the whole design.
- **N- vs O-acetylation is now a graph fact.** Paracetamol (amide) and its O-acetyl isomer
  4-aminophenyl acetate (ester) share one formula but have *different scission menus*; the acetyl-link
  cleavage opens a valence on **N** in one and on **O** in the other. Both hydrolyse to the same pair,
  but the structure says *which bond broke* — invisible to v1, gap #3 of the litmus, closed.
- **Registry widened (rung 3a).** 6 → 14 named compounds (CO, CO₂, CH₄, NH₃, H₂O₂, methanol,
  formaldehyde, formic acid), so more decomposition nodes resolve to a real name.

### 13.1 — The capability-gap map (what "complete" still needs)

Each gap is tagged **BUILD** (a structural capability we should add), **DATA** (sourcing under the
second-source discipline, not structure), or **BOUNDARY** (a physical claim W3 forbids us to make —
listed so a future session does not mistake a deliberate refusal for an unfinished feature). The line
that separates BUILD from BOUNDARY is the same one the whole package rides on: *we may represent and
attach, we may never predict.*

1. **Isomer-keyed evidence — BUILD (highest leverage).** The hazard/thermo/conditions tables are
   *formula*-keyed, but structure-aware descent produces *structure*-specific facts. The
   one-isomer-per-formula guard (`test_data_coherence`) is a band-aid over exactly this: it is why the
   O-acetyl isomer cannot be registered in the main registry without breaking the invariant. **Next
   rung:** key evidence by `NamedStructure.structure_identity` (the canonical digest), with the
   formula→structure resolution licensing attachment; the review layer attaches by *structure* where a
   node is structure-resolved, by *formula* (loudly `ISOMER_ASSUMED`) where it is not. This is the
   bridge from "structure resolves names" to "structure resolves data," and it retires `ISOMER_ASSUMED`
   from the resolved cases. Medium difficulty; touches all three data modules + the attach path.

2. **General capping — BUILD.** `capped_scissions` v2 handles the bounded common case: one order-1
   reactant bond, one reagent, two pairings. It cannot yet do multi-bond cuts, double/triple-bond
   caps, ring-forming or ring-opening rewrites, condensations (lose a small molecule), or multi-reagent
   mediation (two waters). **Next rung:** a general valence-matching capper (perfect matching between
   the reactant's and reagents' open-valence multisets), under the identical valence-preservation
   certificate and a stated budget. Medium-high difficulty (combinatorial matching).

3. **Recursive structure-level descent graph — BUILD.** Today the structure engine emits single-step
   edges; there is no structure-level analogue of `DecompositionGraph`/`MediatedDecompositionGraph`
   that recurses on fragment *structures* down to elements. **Next rung:** `structure_decompose`
   recursing over `ScissionEdge`/`CappedScission` products; per-step termination is already proven, so
   this is the graph builder + a loud budget refusal. Medium difficulty.

4. **Radical intermediates in the review layer — BUILD.** Scission fragments are radicals (open
   valences); the review layer reviews formula-level and mediated edges, not pure `ScissionEdge`s. A
   structure-descent review that surfaces the radical intermediates *labelled as radicals* (never as
   stable compounds — that would be the exact structural lie) is unwired. Small–medium.

5. **Public-API exposure — BUILD (small).** `smartchem.structure_descent` is not on the lazy
   `__init__` surface (`__all__`/`_ATTR_SOURCE` lockstep, per the evidence-bridge decoupling). A
   deliberate, separate act when wanted.

6. **Structure-resolved & broader thermochemistry — DATA.** Energetics is formula-level formation
   enthalpies (16 reference + 2 decompiler species, already folded in). Bond-specific / structure-
   resolved enthalpy is absent, and the litmus itself is genuinely *uncertifiable* today: paracetamol
   is 298 K-only (excluded from the 0 K balance by the convention firewall), 4-aminophenol's two
   gas-phase sources disagree by 9 kJ/mol. That an edge reads `ENERGETICS_UNKNOWN` is a **result**,
   not a missing feature. Grows only under the second-source discipline.

7. **Broader hazard / conditions coverage — DATA.** Hazards and conditions grow only with sourced,
   corroborated records; the point is the mechanism (real reaction → its real facts, everything else a
   loud UNKNOWN), never coverage for its own sake.

8. **Which cleavage actually happens — BOUNDARY.** The engine enumerates *all* valence-valid rewrites;
   ranking which is thermodynamically or kinetically favored is a physical prediction and is **not
   ours to make**. The permitted move, and the only one: attach sourced conditions/hazards/energetics
   so a chemist can rank, while the engine claims only conservation. Attach, never predict.

9. **Stereochemistry — BUILD-if-needed (representation) / BOUNDARY (outcome).** Bond graphs are
   constitutional (no cis/trans, no R/S). Adding a stereo layer is a legitimate representational
   extension should a use-case need it; claiming a stereochemical *outcome* is physical and stays
   uncrossed.

10. **Aromaticity / resonance / tautomers — mixed.** Aromatic rings are hand-entered in one Kekulé
    form and the canonicalizer treats the drawn graph as given; bare vertex-transitive benzene still
    refuses canonicalization (individualisation, the second nauty move, is unbuilt — tracked as
    `category.py` #25). **BUILD:** individualisation, for full canonical completeness — but it is the
    one change where a silent error corrupts every graph equality, so it earns brute-force
    verification, not a bolt-on. **BOUNDARY:** which tautomer or resonance form *dominates* is
    physical. (Substituted rings — every litmus species — already canonicalize; the gap bites only bare
    symmetric rings.)

11. **Charge / ionic / electrochemical descent — BUILD (substantial).** The decompiler is neutral-only;
    heterolytic cleavage → ions, acid/base chemistry, and redox are absent from the descent, though
    `category.Molecule` + the charge/carrier machinery already support charged species and electrons
    for the electromagnetic vertical. **Next rung:** extend scission/capping to charged fragments and
    heterolytic caps (charge conserved alongside valence) — a real rung that also ties the chemical and
    EM verticals together.

**The through-line.** Gaps 1–5 and 11 are the buildable structure work; 6–7 are honest sourcing; 8–10
carry a BOUNDARY half that is not an unfinished feature but the W3 law restated at finer resolution.
"Complete" for this feature is: **isomer-keyed evidence (1) + general capping (2) + the recursive
structure graph (3)**, at which point a chemist gets a structure-resolved, evidence-annotated
decomposition tree — with every physical judgment still theirs to make.

## Part 14 — Execution: Part 13's plan, built (BUILD ×6 + BOUNDARY + DATA)

The Part 13 map was interrogated column by column and built. Commits `1951ac8`..`084a1e2`
(pushed); suite 1863 → 1896. What landed:

**BUILD.**
1. **Isomer-keyed evidence** (`1951ac8`) — the keystone. Evidence attaches by STRUCTURE, not formula:
   `resolve_structure(molecule)` names the specific isomer; hazards/thermo key by unique name (a
   formula may carry several isomers); `hazards_for(ambiguous formula)` returns `None` not a false
   pick; the review threads a `structures` context so a resolved species gets its isomer's data and
   `ISOMER_ASSUMED`/`ISOMER_AMBIGUOUS` RETIRE. `review_capped_scission` reviews a structure-derived
   edge at structure resolution. Registered the C2H6O pair (ethanol/DME) and the C8H9NO2 O-acetyl
   isomer — the plurality the old one-isomer band-aid forbade. Ethanol (−217.1, H225 liquid, IARC 1)
   vs dimethyl ether (−166.6, H220 gas) are now fully distinguished, sourced.
2. **General capping** (`8923d76`) — `capped_scissions(max_reactant_cuts=k)`: cut k order-1 bonds,
   consume a size-k reagent multiset, bipartite-match the open valences. Derives the diester double
   hydrolysis `C4H6O4 + 2 H2O → 2 CH2O2 + C2H6O2`.
3. **Recursive structure graph** (`5ffda3e`) — `structure_decompose`: the structure analogue of B2,
   recursing scission to single atoms, W1-terminating, W2 loud `REFUSED_BUDGET`.
4. **Radical/ion intermediates** (`084a1e2`) — `species_class` / `stability_caveat`: a scission
   fragment is a RADICAL, a heterolytic product an ION; neither is presented as an isolable compound.
5. **Public API** (`5bc8c26`) — the whole vertical on the lazy `__init__` surface (45 names), lockstep
   held, root import still numpy-free.
6. **Charged/ionic descent** (`03211a3`) — `HeterolyticScission`: `HCl → H⁺ + Cl⁻`, acetic acid's
   acid dissociation derived; charge conserved, both electron directions enumerated (which ionises is
   not claimed). The chemical/EM bridge.

**BOUNDARY, made executable** (`9ea38cb`, `084a1e2`) — `smartchem/decompiler_boundary.py`.
`stereo_status`/`stereocenters`/`cis_trans_candidates` detect stereochemistry (1-WL sound lower bound,
ring bonds excluded) and report `CONSTITUTIONAL_ONLY`, never R/S or E/Z. `tautomerizable` detects the
keto-enol motif; which tautomer dominates is not claimed. `evidence_ranking` orders only by SOURCED
evidence present, `UNRANKED` (input order kept) when there is no basis — "which cleavage happens" has
no predict function, by design. Attach, never predict — enforced, not merely documented.

**DATA** (`1820f3f` earlier, `1951ac8`) — hazards 5 → 22 (common products + the 8 isomer-pair/
heteroatom species), each authored blind then reconciled against an independent PubChem/ECHA/NIOSH
bearing; real corrections caught (H2O2 ≥70% band, CO2 IDLH omitted, formic-acid H226 dropped, ammonia
`H3N` key). Thermo gained the ethanol/DME 0 K pair reused from the benchmark.

**The one BUILD item deliberately NOT taken this pass:** the canonicalizer INDIVIDUALISATION for
bare vertex-transitive rings (`category.py` #25) — Part 13 marked it the one change where a silent
error corrupts every graph equality, so it earns brute-force verification rather than a bolt-on at
the end of a long arc. It bites only bare benzene; every registered/litmus species canonicalizes.
That, and broader sourced coverage, are what remain.

## Part 15 — Capability verdict: "recompile ANY chemical into its reaction paths and byproducts?"

The owner's standing question, answered against the built system, not against optimism. The
sentence hides a **fork across W3**, and the two halves get opposite answers — conflating them is
the exact error this whole vertical exists to not commit.

### 15.0 — The fork (the load-bearing distinction)

- **Byproducts + the conservation-valid decomposition graph = FORMAL.** "What multisets of
  lower species does this structure conserve down to, and by what tree of bond-rewrites" is linear
  algebra over the bond graph. This we **certify** — for a target we can (a) represent as a
  `category.Molecule` and (b) fit in budget — and we attach sourced byproduct facts wherever the
  data covers them, a loud `UNKNOWN` everywhere else.
- **The reaction path that actually occurs = PHYSICAL.** "Which of these routes happens, in what
  order, under what conditions, at what rate" is thermodynamic/kinetic prediction. This we **never
  assert** (W3). We enumerate candidate routes and hand a chemist sourced evidence to rank; we do
  not rank by reactivity ourselves. Building *past* this is not a missing feature — it is the wall
  that keeps the tool from emitting chemically-plausible falsehoods at scale.

**Verdict, both halves.** *Formal:* **not for "any" yet** — blocked by ingestion, search budget,
and rewrite/ion coverage (15.1, all buildable). *Physical (the real reaction path, singular):*
**no, by design, permanently** — that is a BOUNDARY, not a TODO.

### 15.1 — The gaps between here and "any chemical, formal tree" (measured 2026-08-30)

Ranked by how hard each bites on the word **any**. Tags as Part 13: BUILD / DATA / BOUNDARY.

- **G1 — the front door: structure INPUT — BUILD (highest leverage, NEW; Part 13's map assumed
  the `Molecule` already in hand).** There is **no** name/SMILES/InChI → `category.Molecule`
  reader; the only parser in the repo is `Formula.parse` (formula *string* → bond-free atom
  multiset). Every bond graph is hand-entered and guard-verified — **23** compounds today
  (measured). So "any chemical" is false *at ingestion*: the decompiler can only reach what
  someone typed in. This one change — a structure reader landing in `category.Molecule`, then the
  existing certified composition guard — is what turns "23 hand-entered species" into "any
  compound a chemist can name." *Owner decision:* a hand-rolled SMILES-subset parser (bounded, no
  dependency, matches the numpy-free-root discipline) vs. an optional RDKit-backed reader behind
  the lazy surface (heavy dep, full coverage). Not silently chosen. Substantial.

- **G2 — the budget wall on real targets — BUILD.** Measured: `structure_decompose(paracetamol)`
  → **`REFUSED_BUDGET` at 5001 edges** (edge budget 5000); ethanol (9 atoms) → **COMPLETE, 131
  edges / 46 nodes**. The full recursive descent of a real drug molecule does **not** reach
  elements under default budget — it refuses *loudly and correctly* (W2), but the complete tree is
  unobtainable for dense targets. Needs: canonical memoization across the graph (fragments recur
  massively), pruning to meaningful cleavages, or an explicit bounded-depth contract as the honest
  deliverable. Medium-high. *This is the price of "all the way down" being real rather than
  silently truncated.*

- **G3 — rewrite coverage (capping) — BUILD (Part 13 #2 remainder).** `capped_scissions` is
  **order-1 only**: no double/triple-bond caps (order-2 ends), no ring-forming or ring-opening
  rewrites, no condensations that close a ring. Whole classes of real byproduct-producing
  reactions are structurally unrepresentable. Medium-high (higher-order valence matching).

- **G4 — ionic / redox descent not wired into the graph — BUILD.** `HeterolyticScission` exists
  (`HCl → H⁺ + Cl⁻`, charge-conserved, both directions enumerated) but is **not** in the recursive
  graph or the review layer, and there is no redox / electron-transfer edge. Acid-base and redox
  routes — a large fraction of real decomposition chemistry — are absent from the tree. Substantial;
  also the concrete tie to the EM vertical.

- **G5 — byproduct evidence coverage — DATA.** Even when structure enumerates and *identifies*
  correctly, the byproduct FACTS (hazard / thermo / conditions) attach only across the ~22-record
  registry; everything else is a loud `UNKNOWN`. Honest, but "any chemical's real byproducts,
  annotated" needs a real database grown under the second-source discipline — never coverage for
  its own sake.

### 15.2 — The BOUNDARY pile (absent on purpose — never mistake these for TODO)

- **Which cleavage / route actually happens** — reactivity, ΔG/ΔH ranking as *selection*, kinetics.
  The engine enumerates; the chemist ranks with the sourced evidence we attach. Attach, never predict.
- **Stereochemical / tautomer / resonance-dominance OUTCOMES** — detection is built and refuses
  (`decompiler_boundary.py`, `CONSTITUTIONAL_ONLY` / `UNRANKED`); the *outcome claim* stays uncrossed.
- **Any claim an edge is physically realized.** The casualty list on every certificate.

### 15.3 — "Complete" for the formal ask, defined

**G1 (input) + G2 (search) + G3 (capping) + G4 (ionic) + G5 (data)** — at which point a chemist
hands in any nameable compound and gets back a structure-resolved, byproduct-enumerated,
evidence-annotated decomposition graph, with every *which-one-happens* judgment still theirs. The
**physical** ask ("give me the real reaction path") is answered `no` forever, and that `no` is the
feature. **G1 is the single highest-leverage next build** — without it, every other rung only ever
serves the two-dozen compounds already typed in.

## Part 16 — Execution: Part 15's gap map built (bonds + G1–G5), the FORMAL half closed

Part 15's five buildable gaps and the "bonds working fully" prerequisite are **built, verified,
pushed** (commits `fa11f30`..`e646eca`; suite 1896 → 1971, zero regressions). The formal half of
"recompile any chemical into its byproducts + conservation-valid decomposition tree" is now
substantially closed; the physical half ("the real reaction path") remains the permanent W3 BOUNDARY.

- **B — bonds working fully (`fa11f30`), the foundation.** The canonicaliser did only refinement
  (nauty's first move) and RAISED on a vertex-transitive cell, so bare benzene / symmetric rings had
  no canonical form. **Individualisation** (the second move, category #25) closes it: proven SOUND
  (benzene's form is a genuine relabelling, brute-forced over all 518,400 labellings) and COMPLETE
  (relabel-invariant, byte-exact), purely additive (reached only where refinement was already over
  budget, so no prior form moves — the whole suite is the regression proof). **False-twin pruning**
  makes it fast: cyclododecane 12,721 ms → 24.6 ms (516×), a former 30-s refusal now 53 ms. Honest
  boundary kept: a complete graph K_n still refuses loudly. This was BOTH the "bonds" fix AND the
  "efficient" win, and the prerequisite for G1.

- **G1 — the front door (`66e7599`).** `smartchem/smiles.py`, a hand-rolled SMILES-subset parser
  (no dependency, numpy-free-root-clean — RDKit was rejected as against the ethos). All 23 registered
  species parse to their hand-entered structure CANONICAL-EQUAL. Aromatic all-carbon Kekulisation by
  perfect matching; aromatic heteroatoms / malformed input refused loudly; constitutional-only (W3).
  Ingestion is no longer the wall.

- **G2 — bounded-depth descent (`4791f82`).** `structure_decompose(max_depth=k)` → the new
  `COMPLETE_TO_DEPTH` status, a POSITIVE horizon guarantee distinct from full `COMPLETE` and from a
  `REFUSED_BUDGET` truncation. Paracetamol depth-1 in 0.06 s / depth-2 in 1.2 s where the full descent
  is ~7,750 edges / ~30 s. Proven: bounded edges are a SUBSET of the full descent (bounding never
  invents), monotone in depth.

- **G3 — general capping (`faaba2f`).** Any-order cuts + a full perfect matching over open ends
  (equal-order pairs), filtered by the unchanged valence certificate. New reach: olefin metathesis
  `2-butene + ethylene → 2 propene` (order-2 whole-bond swap) and ring-forming reactant-to-reactant
  caps. Fixed a latent `forget()` bug the general capper surfaced (an element-only product H2 now
  buckets to unit elements). Out of scope, documented: partial bond-order change (addition).

- **G4 — redox + ionic descent (`b118de0`).** `RedoxHalfReaction` (`Fe2+ → Fe3+ + e-`), the
  chemical↔EM bridge: the electron is a massless charge carrier (never `atom("e")`), charge is the
  conserved quantity. `ionic_edges` wires heterolysis + redox into one node view; every ionic product
  is labelled ION / electron, never a neutral compound. Boundary: heterolysis of an already-charged
  ion (recursive ionic descent) is the next rung.

- **G5 — widened byproduct evidence (`e646eca`), DATA.** Six common products (benzene, H2S,
  acetaldehyde, ethylene, acetylene, phenol) registered via G1's `parse_smiles` + sourced hazard
  records under the second-source discipline (multi-notifier / ECHA-harmonised GHS, minority
  over-classifications rejected, load-bearing hazards surfaced). Thermo deliberately NOT added: the
  research pass gave one 0 K value each and CCCBDB mirrors NIST WebBook for several (shared provenance,
  not two independent bearings), so none clears the two-independent-source ESTABLISHED bar — recorded
  as the honest next step, not faked. Registry 23 → 29.

**Where the capability stands now.** A chemist can hand in a SMILES (G1), get a fast structure-resolved
bounded decomposition (G2) with general rewrites (G3), ionic/redox routes (G4), and sourced byproduct
evidence where covered (G5) — every physical which-one-happens judgment still theirs (W3). Remaining:
broader sourced coverage (data, ongoing) and recursive ionic descent (a named next rung). The physical
ask stays `no`, and that `no` is the feature.

## Part 17 — Reality-respecting audit on a difficulty ladder, and the honest "truly complete" ledger

**What was asked.** "What's left to build for the decompiler to be *truly complete*? — and test the
machinery against chemicals of increasing difficulty, making sure the output is reality-respecting on
all, fixing issues that show up."

**The ladder (`experiments/structure_decompiler_ladder.py`, receipt
`RESULTS_structure_decompiler_ladder.md`, commit `1ab0bd4`).** 36 chemicals across 8 difficulty tiers
(hydrides → chains → unsaturation/heteroatoms → single rings → substituted aromatics → drug-sized →
fused/heteroaromatic-as-Kekulé → ionic/redox), each parsed through G1 and decomposed, every edge
audited against an **independent** recompute — never the edge's own certificate (the repo's
"no check derived from its own subject" discipline). **2 888 scission edges, all PASS:** every one
conserves atoms, passes the independent `verify_valence_integrity`, projects via `forget()` to a valid
formula-level edge, and labels every open-valence fragment RADICAL / every ionic product ION. Hard
non-vacuity held (every decomposable target produced edges); all 14 ionic/redox checks conserve charge
and mass with the electron massless. The FORMAL half is now *demonstrated* reality-respecting, not
merely argued.

**The one defect it caught, and fixed.** `is_complete` (status `COMPLETE`) documented itself as "a full
descent to **single atoms**", but any ring is irreducible at `max_cut_bonds=1` (a ring bond is not a
bridge), so benzene / cyclohexane / cyclopropane / phenol / aniline / naphthalene / pyridine finish
`COMPLETE` yet bottom out at a carbon-ring **core**, not single atoms. A labelling over-claim (not a
conservation break) — and W3 forbids claiming more than was done. Fixed by correcting the docstrings and
adding `irreducible_cores()` (the non-atomic leaves no cut can open — the boundary made auditable) and
`reaches_single_atoms` (the precise "did it atomise?" predicate `is_complete` was mistaken for). Pinned
by `TestIrreducibleCoreHonesty` (5 tests); full suite 1976 passed, zero regressions.

**The honest "truly complete" ledger.** The sentence forks on W3, and the fork is the answer:

- **PHYSICAL completeness is NOT a build target — it is the permanent W3 wall.** *Which* cleavage
  happens, at what rate, under what conditions, driven by what thermodynamics — the real reaction path —
  is never certified. The most a chemist gets is a structurally-honest menu they rank with their own
  knowledge plus sourced evidence (the litmus). "Truly complete" can never mean "predicts reality";
  that `no` is the ethos, not a gap.

- **FORMAL completeness is substantially built and now proven; what remains are refinements, ranked by
  leverage (R1 is the one the ladder made load-bearing):**
  - **R1 — ring-aware descent.** The ladder's finding: cyclics do not atomise without the caller
    knowing to raise `max_cut_bonds`, and even then the 2-cut powerset blows up. A ring-perception layer
    that opens each ring with its minimal cut set would let `reaches_single_atoms` become `True` for
    cyclics without the combinatorial cost. **The highest-leverage open formal rung.**
  - **R2 — resonance-aware identity (asymmetric-aromatic Kekulé).** Two Kekulé drawings of the same real
    asymmetric aromatic can canonicalise differently → different menus. Symmetric rings (all currently
    registered) wash the choice out; asymmetric ones do not. The top reality-respecting *boundary* the
    ladder does not yet cover. Research rung (delocalised-bond representation or Kekulé-orbit quotient).
  - **R3 — recursive ionic descent.** Heterolysis splits neutrals only; an already-charged ion does not
    further descend. Named next rung (Part 16).
  - **R4 — cross-level radical/open-valence ledger.** The descent certifies the *skeleton* (which bonds
    break into which sub-structures), not a threaded radical-electron count across levels. Documented
    boundary in the graph docstring.
  - **R5 — fragment evidence + naming coverage.** Enumerated byproducts are structurally exact but only
    29 species carry sourced hazard/condition evidence, and 0 K thermo stays deferred for lack of two
    independent bearings. Open-ended data curation, not a correctness gap.

**Verdict.** The decompiler produces reality-respecting FORMAL output on chemicals from H₂O to aspirin —
audited, not asserted. It is *not* "truly complete" in the sense of atomising every ring (R1) or
resolving resonance identity (R2), and it will *never* be complete in the physical sense (W3). Those are
the honest edges: R1-R5 are refinements to a sound skeleton, and the physical wall is permanent.

## Part 18 -- R1 + R2 built, and the new vertical: the Experiment Compiler (M-5)

**R1 -- ring-aware descent (`4ffb6b2`), BUILT.** `ring_aware=True` adds targeted 2-cuts of ring-bond
pairs: cutting a ring at two bonds splits it into two arcs, a genuine scission (W1 holds by atom count),
the only way a pure ring atomises. Small rings now reach single atoms (`reaches_single_atoms` True,
cyclopropane/benzene); the ring-opening move enters the menu (benzene 4, naphthalene 12); a big/fused
ring whose full atomic descent explodes REFUSES loudly. **R2 -- resonance-canonical identity (`42dfb15`),
BUILT.** A fused benzenoid had several identities across its Kekule forms (naphthalene 2, anthracene 2,
phenanthrene 4, measured); the parser now returns the canonical-minimal Kekule form -- the resonance
orbit's representative -- so one molecule has one drawing-invariant identity (three naphthalene spellings
-> one identity) without over-merging isomers (1- vs 2-naphthol stay distinct). Remaining: R3 recursive
ionic descent, R4 cross-level radical ledger, R5 evidence/thermo coverage.

### The ask, recovered

"An experimental compiler: take a reaction PATH the decompiler produced and verify it as an actually
runnable experiment; output a DRAFT sequence of synthesis steps; and simulate it to the best of our
ability -- the 100%-efficiency max outcome, the time/heat/pressure each step takes, the solvents and
freely-available chemicals assumed to aid it -- flagging paths that are physically degenerate (an
intermediate that cannot survive the transition to the next step's conditions; a pressure that cannot be
reconciled with the next step)."

### The governing frame (refined W3): reproduce KNOWN chemistry, never invent NEW physics

The operator's correction is load-bearing and it is the ethos the repo already lives by: **the wall is
NEW physics, not physics.** The PySCF oracle does not predict new physics -- it reproduces *known*
quantum chemistry (CCSD(T)) under a calibrate-on-known-cases / state-the-envelope / fail-closed
discipline. M-5 is that same pattern extended to reaction SEQUENCES. Every number M-5 emits falls in
exactly one of four buckets, and it says which:

* **CONSERVATION (formal, free).** The 100%-efficiency ceiling is the limiting-reagent calculation --
  exact stoichiometric conservation, no physics. An idealised UPPER BOUND, labelled as such, never a
  predicted yield.
* **COMPOSABILITY (constraint satisfaction, not prediction).** "Won't survive the transition to room
  temp", "pressure can't be reconciled" -- these are *incompatibilities of declared/sourced envelopes*,
  a logical refusal (`DEGENERATE`), not a claim about what chemistry does. A path is degenerate when its
  own stated constraints contradict, full stop.
* **KNOWN-MODEL / SOURCED (reproduce, with the oracle's discipline).** Per-step T/P/time/heat and
  assumed solvents/reagents come from SOURCED conditions or an ESTABLISHED, VALIDATED model (ideal gas,
  a sourced decomposition threshold, the repo's own thermochemistry) -- calibrated on known cases, its
  envelope stated, refused outside it, the model and its inputs labelled.
* **UNKNOWN (loud).** No source and no established model -> `UNKNOWN`/`UNRANKED`, never a manufactured
  number. Inventing a novel feasibility/kinetics/yield model is the forbidden "new physics".

W3 restated for M-5: it never predicts *which* path Nature takes, a real yield, a real rate, or the
feasibility of an unsourced reaction. It composes, checks, idealises, and reproduces known chemistry --
and refuses or labels everything else.

### The walls (M-5's, restated)

* **W1 (composition terminates).** A route is a finite DAG of steps over the (terminating) descent; the
  composability check is a single pass over consecutive steps -- no fixpoint.
* **W2 (loud partial).** A route with any `UNKNOWN` envelope is not "runnable" -- it is `DRAFT` with the
  gaps named, never silently sold as verified. A degenerate path is `DEGENERATE(reason)`.
* **W3 (formal/known, never new).** The frame above.

### Build ladder (E0-E4), each with its certificate and its litmus

* **E0 -- `ExperimentStep`.** A certified step: reactants + reagents (incl. assumed solvent/ancillary
  chemicals, each evidence-labelled) -> product, conserving mass and charge (reuse the scission/capped
  certificate). Carries a `ConditionEnvelope` (T-range, P-range, phase, time) that is DECLARED (sourced)
  or `UNKNOWN` -- never invented. *Reuses:* `decompiler_conditions`, `data.hazards`, the
  `structure_descent` certificates.
* **E1 -- the composability verifier.** Given an ordered step sequence, check each intermediate survives
  the transition to the next step's envelope, against its SOURCED stability threshold
  (decomposition/melting/boiling). Emit `COMPOSABLE` or `DEGENERATE(reason)`. The executable form of
  "won't survive the transition" / "pressure can't be reconciled" -- constraint satisfaction over sourced
  envelopes, the E-analogue of the W3 boundary module. *Certificate:* the reason cites the exact two
  envelopes and the sourced threshold that conflict; no source -> the pair is `UNKNOWN`, not "fine".
* **E2 -- the stoichiometric ceiling.** The 100%-efficiency maximum outcome by limiting reagent -- exact
  rational conservation, seconds, no oracle. *Litmus:* paracetamol from 4-aminophenol + acetic anhydride,
  max mol paracetamol per mol limiting reagent.
* **E3 -- the physical-accounting attach layer.** Per-step time/heat/pressure/solvent from SOURCED
  conditions or an ESTABLISHED model, under the oracle's calibrate/state-envelope/refuse discipline;
  `UNKNOWN` where unsourced. *Boundary:* never a computed rate or a yield below the ceiling (kinetics --
  new physics unless sourced).
* **E4 -- the procedure drafter.** Emit the human-readable DRAFT sequence of synthesis steps, every
  assumption (solvent, reagent, envelope, ceiling) evidence-labelled, under a banner: a composed and
  composability-checked draft over KNOWN data, NOT a predicted successful synthesis. *North-star litmus
  (extends the paracetamol litmus):* given the decompiler's paracetamol routes, rank the ones whose steps
  are COMPOSABLE and fully SOURCED above those with `UNKNOWN`/`DEGENERATE` gaps -- surfacing what is known
  and stopping, exactly as `evidence_ranking` does for single edges.

### Open decisions (owner's call, before E0)

1. **Sourcing model for stability thresholds.** E1 needs decomposition/melting/boiling data under the
   second-source discipline. Start from the registry species (29) or pull a dedicated sourced set first?
2. **Route direction.** A "synthesis path" is a decompiler descent read backwards (assembly). Confirm
   M-5 consumes an existing descent/assembly path object rather than re-deriving routes.
3. **Where E2's ceiling gets its molar arithmetic** -- reuse `stoichiometry.py`'s exact integer kernel.
