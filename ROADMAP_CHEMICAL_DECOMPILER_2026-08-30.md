# Roadmap proposal — the chemical decompiler (elemental descent graph)

**Status:** proposal + execution, 2026-08-30. The design in Parts 0–6 is the original
proposal; the four owner decisions (Part 6) were then fixed and **B0–B2 were authorized
("go full blast") and built** — see the execution addendum in Part 7, which supersedes the
"nothing built" framing for B0–B2. This is a **provenance-honest** record, not a retroactive
ratification. It slots a new chemistry-core research vertical into `ROADMAP_2026-08-06.md` as
**M-4**, parallel to the circuit-`ModelIR` line (M-1), and does not displace it, the
consumption arc, or the long-term category backbone.

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
