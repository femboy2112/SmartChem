# SmartChem roadmap

> **The single source of truth for what is done, what is queued, and what is deliberately not being built.**
> `verified @ f6e887a` · suite **4510 passed / 14 skipped / 1 xfailed** (PySCF-present dev venv; unchanged since R23 — PR #16 merged the R23 code, PR #17 the Move-1 keystone design contract, docs-only) · updated **2026-09-07 UTC**
>
> This file is canonical. `MEMORY.md` and `UPTAKE_MANIFEST_v0.5.0a1.md §N` point *here* rather than duplicating the
> queue — one list, not three that drift. Full per-round build history lives in the manifest (through `§22`); this file is
> the forward-looking plan plus a compact done-ledger. Sizes and first-steps were ground-truthed against the source and
> the load-bearing claims independently re-verified at their file:line anchors; earlier rounds used independent evil-morty passes;
> ROUND 22 records its separate source, implementation and adversarial-review bearings explicitly.

## Governance — the 3-lane projection (authoritative)

Every item is tagged with the lane it advances. **Progress in one lane never implies another.** (Audit:
`AUDIT_GENERIC_CHEMICAL_COMPILER_REORIENTATION_2026-09-03.md`.)

- **Lane A — Alpha-conformance.** Does it conform to the v0.5.0a1 alpha contract / laws?
- **Lane B — Chemical genericity.** The transform algebra (capped / bond-order / heterolytic / redox IR-COMMUTE
  families) driven through the **unchanged** bounded SEARCH core.
- **Lane C — Bench-readiness.** Section-11 bench fit (composability[E1] + physical box + process) and section-10.4
  pricing (dated **and** sourced, never invented).

**Poor-man ethos (the bench is a kitchen).** "The kitchen" and "my lab and equipment" mean the same thing: the
whole-path capability model satisfies-or-BLOCKS against **household + outdoors** equipment by default, never assumed
lab infrastructure. "Poor man's fume hood = experiment done outside" — outdoors is a valid *ventilation* control, but
ventilation ≠ hazard clearance (a toxic/corrosive vapour like Br₂/Cl₂ is still surfaced). Affordability is a whole-path
capability claim (material identity, controllable operations, measurement, containment, separation, verification,
closure), not a cheap-reagent list — a route cheap in reagents but needing a control the kitchen can't provide is
`CAPABILITY_BLOCKED`, surfaced, never papered over. See `docs/research/PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md`.
**Cheap epistemology counts too:** the ethos prefers chemistry that *tells you what it is doing* — a route whose
success/failure is legible from cheap, redundant, chemistry-supplied signals (colour change, precipitate, gas evolution,
pH/temperature excursion) beats one that fails silently and needs a $20k instrument to notice. That is a *ranking*
objective (the Observability Score, shipped ROUND 18), kept honest by the rule that a visible checkpoint is **not** chemical
proof (process-indicator / identity / purity stay separate axes — invariants 5 & 7).

## North-star litmus tests (the acceptance gates that keep the lanes honest)

- **Paracetamol litmus (Lane C):** *could a real chemist use our paracetamol decompilation to pick real steps?* Tests
  step-level usefulness.
- **DOW bromine litmus (Lanes B + C + EM) — NEW:** *can we predict Br₂'s decomposition and synthesis, enumerate the
  synthesis paths, rank them **quantitatively on cost**, and reproduce why Herbert Dow's brine-bromine process undercut
  the German bromine cartel?* It forces the WHOLE stack at once — the **redox** IR-COMMUTE family (Cl₂ + 2Br⁻ → Br₂ +
  2Cl⁻), the **electromagnetic** scope (electrolytic oxidation of bromide — electrons at an anode; the one litmus that
  bridges the chemistry core and the electron/circuit layer), **thermodynamics/feasibility**, and the **cost/affordability
  buckets** (`cash_floor`, `affordability_frontier`, `material_quantity`) — down to the humble "poor-man's" evidence
  buckets. A pass quantitatively shows the cheap-brine route beats the mineral route. **Sourcing is favorable:** bromine
  is a USGS-priced inorganic (same pattern as NaCl/Na₂CO₃), so unlike the organic-price wall this litmus's cost axis is
  genuinely achievable. Spawns the queue items marked *(DOW)* below.
  **The litmus is now two-thirds standing:** **✅ Phase 1 — pricing (ROUND 16, DOW-BROMINE-01):** elemental bromine is a
  first-class SOURCED, USGS-priced commodity ($2.70/kg 2024, MCS 2026), INDUSTRIAL-tier (the DOW insight encoded), costed
  end-to-end through the buckets. **✅ Phase 2 — mechanism (ROUND 17, REDOX-DISPLACE-01):** the coupled half-reaction
  combiner enumerates `Cl₂ + 2 Br⁻ → Br₂ + 2 Cl⁻`, the reaction no prior mechanism could reach. **✅ Phase 3 —
  electrochemistry (ROUND 18, ELECTROCHEM-01):** sourced standard potentials prove that displacement is SPONTANEOUS
  (E°cell = +0.271 V, ΔG° = −52.3 kJ/mol) and reproduce why chlorine displaces bromide but not the reverse; the
  electrolytic anode leg is modelled (minimum decomposition voltage + Faraday charge). **Remaining — the cost ranking:**
  the brine-vs-mined *quantitative cost ranking* still needs pricing integration + a NaBr feedstock. ROUND 22 recovered
  an approved municipal Cl₂ offer, with packaging/rental terms; it is not an industrial spot or historical Dow price.
  See DEFERRED and `docs/research/SOURCING_RECON_2026-09-07.md`.

---

## ✅ DONE — current shipped capability

**Categorical reorientation — Move-1 keystone (design contract, no code)** (merged **PR #17 → `main@f6e887a`**; contract
commit `d6c61cd`, `docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md`) — the **keystone** of the categorical
reorientation, spec'd as a design gate. Proposes an open-SMC chemistry morphism backbone (reuse `open_diagram.py`'s
already-lawful composition core; conservation as a **closure predicate** not a construction gate; the
conservation-at-construction theorem preserved exactly as the closed-diagram special case — obligations P1–P4). Hardened
pre-commit by two adversarial reviews (evil-morty + birdperson) that **converged on an unsound acceptance gate**; resolved
via the **"central knot"** — two kinds of order (genuine causal DAG, preserved / spurious linearization of independent
steps, quotiented) at two levels (coarse **structural ports** carry the SMC/interchange laws; an interchange-invariant
**`Config` apex decoration** carries conservation-closure; a **partial-order record** carries provenance). Re-specified
gate = interchange under the honest `canonicalize` quotient + a **real non-test consumer** (`ExperimentStep.open/.close`
round-trip) + a P4 demonstration; the legacy `Reaction` xfail preserved-and-annotated, not flipped. **This is the build
gate for Rung B (queued below).**

**ROUND 23** (branch `categorical-duration-functor-2026-09-07`, code `8e97664`, merged **PR #16 → `main@0e6bba0`**) — the **categorical
reorientation's first rung** (Move 2: physics as a functor): the duration-aware survival verdict wired into core E1, closing
the core-E1 half of queue item 3. `design → recon (2 mappers) → build → reproduce → evil-morty → fold → verify`; **additive**
(3 source files + 1 new test), **byte-stable** (the survival field is `compare=False` digest-excluded; the seed kinetics hold
only N₂O₅/cyclopropane so no existing route is assessed → no golden churn). One evil-morty MEDIUM soundness fix folded before commit.

| Item | Lane | What shipped |
|---|---|---|
| DURATION-SURVIVAL-01 (item 3, core-E1 half) | B·C | E1's `_judge_transition` now **consumes** the DAG-HOLD-01 serial hold: where an intermediate has a SOURCED first-order decomposition rate (`stability_horizon`, matched on canonical structure, never formula), a duration-aware survival reading MOVES the composability verdict (`smartchem/experiment/composability.py` `_apply_duration_gate`/`_hold_survival`/`_survival_product` + `dag.py` `_serial_hold_segments` + `tests/test_duration_survival_gate.py`). It only ever **TIGHTENS**: `DEGRADES → DEGENERATE` (even where the onset table was silent — a sourced kinetic refutation beats a missing record), `MARGINAL → UNKNOWN`, `SURVIVES` confirms without upgrading, and never touches an already-`DEGENERATE` base. The functor: `Transition.surviving_fraction` (digest-excluded) + `route_surviving_fraction` on `Composability`/`DAGComposability` = the product of per-transition fractions, the survival monoid functor `S: Process → ([0,1], ×)` (the hold survival itself composes multiplicatively over its segments). **evil-morty MEDIUM fold:** survival is read over the intervening SIBLING steps' OWN declared temperatures (the temperatures the intermediate idles at) — NOT a producer/consumer endpoint's, which could mint a false DEGENERATE *and* launder a real degradation — and **fails closed** on any undeclared hold temperature or non-finite rate (never a verdict on a temperature the model doesn't know). `survival_verdict` promoted to a shared public band-policy helper (no drift). **Still remaining on item 3:** the DOW-Br₂ collider/modified-Arrhenius half (sourcing/modeling-gated), and linear-route holds are unmodeled (only DAG serial holds carry a hold) — see QUEUE + TRACKED DEBT. |

**ROUND 22** (branch `codex/mancude-duration-sourcing-2026-09-07`, code `07651a0`, isolated from `main@043a3cd`) — neutral mancude CIP
extension, duration admission fix, and source-access corrections. Full verification and source hashes are recorded in
`experiments/validation/round22_2026_09_07.json`; the source and external-oracle reports preserve the claim boundaries.

| Item | Lane | What changed |
|---|---|---|
| CIP-MANCUDE-01 | B | Exact rational multiple-bond duplicate atomic numbers over distinct feasible partner positions in bounded neutral C/N/O/S mancude rings, including supported fused systems. Ring topology recognizes aromatic and explicit Kekulé inputs through the same path. Fixes the independently discovered uppercase pyridyl/diazinyl **wrong-label** mirror pair; names aryl/heteroaryl centres while identical ligands remain unnamed. Primary VS032/033 anchors, fractional-number controls, three fail-closed work caps, and optional accurate-RDKit panels (1,224 + 1,134 representation cases) are reproducible. Higher-rule ties and unsupported ring chemistry remain deferred. |
| DURATION-UNIT-01 | B·C | `ConditionEnvelope.duration` requires exactly `min`, through direct construction and replay. Non-minute callers must convert explicitly. Existing valid minute payloads and route digests are unchanged; 59 new unit/admission controls. Core E1 still needs an intermediate-hold interpretation and seconds conversion. |
| DOW-SOURCE-RECON-01 | B·C | Recovered Warshay's NASA Br₂ initial-dissociation primary and an approved Los Fresnos Cl₂ procurement offer. Both blanket primary-access claims are corrected. These are source receipts, not new default seeds: collider/modified-Arrhenius/hold modeling and package-aware pricing/feedstock integration remain open. |

**ROUND 21** (branch `cip-load-stability-2026-09-06`, code `6e14d51`) — 1 build, full-blast on **queue item 2** (the L
round); `design → external review (ChatGPT, folded against the tree) → recon (8-agent) → build → reproduce → evil-morty →
fold → verify`; **additive** (new codecs + a `compare=False` field + a load-time check in `service.py`, plus a new test
file), **route identity byte-stable** (no schema bump, no golden churn — the default wire is byte-identical); one VERIFIED
evil-morty finding + one LOW folded:

| Item | Lane | What shipped |
|---|---|---|
| ONLOAD-REDERIVE (item 2) | C | **On-load re-derivation of the composability + physical + ranking axes** (`smartchem/service.py` + `tests/test_onload_rederivation.py`). Closes the free-text trust boundary PROCESS-ADMIT-01 left open: a route non-FITS for a **composability** or **physical** reason (or with fabricated **ranking** verdicts) could be bare-relabeled to FITS and admitted on load. Structural close, **no key**. A thick **replay payload** (the route's complete steps: target/reactants/products/reagents + full 10-field `ConditionEnvelope`) is carried `compare=False` (digest-excluded → route identity byte-stable) and emitted opt-in (`include_replay`, default off → default wire byte-identical). `response_from_payload(require_verified_admission=True)` **reconstructs** the exact route/DAG, re-projects it through the SAME producer path (`rank_routes`+`of_fit` / `of_dag`) under the response's pinned eval-context, and requires `resummary == claimed` — ONE equality subsuming route-binding (`reconstruct.digest == route_digest`, closing the substitution hole ChatGPT found), the combined fold verdict, the composability + 4 ranking verdicts, and the process/edge projections. **Fail-CLOSED**: a FITS dossier with no payload is UNVERIFIED, refused (the **deletion door** the adversary found — closed with NO schema bump, lower blast than the reviewer proposed). Reconstruction re-runs the real `ExperimentStep`/`Route`/`DAG` constructors (conservation, linearity, acyclicity); molecule codec mirrors the digest-stable `_graph_payload` (positional, no SMILES re-parse). Edges int-coercion trap fixed (`_exact_int_pair`). **evil-morty folds:** (F1 MEDIUM, VERIFIED) keyless **eval-context relaxation** — the box is built from the response's own request, so a keyless request-relaxer could re-derive an out-of-bounds route to FITS; corrected the docstring overclaim (residuals are TWO) + added `expected_request_digest` (consumer pins its request; a signature closes it cryptographically), both directions pinned. (F2 LOW) `serial_holds` was `compare=False` → the DAG branch now re-derives + checks it. Design: `docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md` (folds the ChatGPT external review against the tree; supersedes v0.1). |

**ROUND 20** (branch `cip-load-stability-2026-09-06`) — 1 build, full-blast on **queue item 1**; `design → recon → build →
reproduce → evil-morty → fold → verify`; **additive to the engine** (new `_cip_*` in `smiles.py` + harness + test), plus a
**conscious supersession** of the ID-STEREO-01 same-element *deferral* tests (the deferral was "not built yet", now built);
byte-identical on the distinct-Z slice; one self-caught soundness bug + one evil-morty finding folded, two residuals
discharged/documented:

| Item | Lane | What shipped |
|---|---|---|
| ID-STEREO-CIP-NAMER (item 1, the namer) | B | The **general CIP R/S namer** (`smartchem/smiles.py` `_cip_ranks`/`_cip_compare`/`_cip_digraph` + `experiments/cip_namer_probe.py` + `tests/test_cip_namer.py`) — closing item 1 (the R19 oracle unblocked it). CIP **Rule 1a** priority via a hierarchical digraph, **breadth-first, branch-by-branch with need-to-know pruning** (Hanson et al. 2018) — the fix for the R13/R14 **depth-first** bug (`C[C@H](CCC)C(C)C`: DFS says S, truth **R**). Phantom atoms for multiple bonds + ring closures; reuses the shipped `_perm_parity ^ sense` emit line (byte-identical distinct-Z). Now NAMES the common same-element case (amino acids/sugars: L-alanine S, the **L-serine S / L-cysteine R flip**, glyceraldehyde R). **SOUND, not complete**: Rule 1b/2/4/5 ties and aromatic-reaching ties DEFER (a wrong R/S is worse than none). Committed harness with 5 layers (textbook absolutes, oracle cross-check, R14 differential, branch-paired-vs-pooling proof, 840-case alkyl pool), FROZEN_HASH. **Self-caught soundness fix:** a fixed Kekulé wrongly NAMED the di-2-pyridyl false centre → lazy aromatic-boundary guard (atomic number still decides, onward aromatic connectivity withheld). **evil-morty ("could not make it lie"):** folded a spurious over-defer on an aromatic ring in an already-decided branch; discharged the exocyclic-aromatic residual; documented the comparator-transitivity residual. |

**ROUND 19** (branch `cip-load-stability-2026-09-06`) — 3 builds + 1 recorded decision; each build `design → recon →
build → reproduce → evil-morty → fold → verify`; **additive** (5 new files + additive edits to `service.py`, no existing
behaviour changed); two evil-morty passes found real weaknesses, all folded or documented and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| CIP-ORACLE-01 (item 1, the oracle) | B | The committed **geometric handedness oracle** (`experiments/cip_geometry_oracle_probe.py` + test) — meeting item 1's oracle gate. Builds synthetic tetrahedron coordinates from the OpenSMILES sense bit, reads R/S off a real signed volume (lowest priority away, trace 1→2→3), takes priorities as an INPUT so it decouples geometry from priority-ranking. Green on an exhaustive 48-case {F,Cl,Br,I} battery + two textbook absolute anchors ([C@H](F)(Cl)Br = S, L-alanine = S from one derived convention). **evil-morty (MED-HIGH) right-sized the claim:** it is algebraically `perm_parity ^ sense`, so the 48-case sweep confirms ONE constant, not 48 bearings — it buys one independent bit (a global convention-flip guard) + the decoupling instrument, NOT a ranking-bug catch. Folded: docstrings corrected to that honest scope, `cip_labels` pinned into the frozen hash (so a regression in the *audited* slice reddens it too), the algebraic identity + an external-absolute pipeline check baked into the tests, the dead degeneracy-guard overclaim fixed. |
| DURATION-STABILITY-01 (item 3, the primitive) | B·C | The duration-aware **survival primitive** (`smartchem/experiment/stability_horizon.py` + harness + test) — the time axis on known physics. `f = exp(-k t)`, k = A·exp(-Ea/RT) mirroring the L1 rate engine (R pinned equal, no drift); non-vacuous on N₂O₅ (SURVIVES 60 s → MARGINAL 1 h → DEGRADES 6 h at 298 K), DERIVED/PREDICTED graded, instrument-calibrated (k(298) reproduces the measured 3.38e-5 to ~5%). Fail-closed UNKNOWN with no sourced rate; the compound→rate bridge is structure-keyed + direction-specific (cyclopropane/propene C₃H₆ collision proves no isomer or product borrows a rate). Standalone — NOT wired into core E1 (a stated boundary). **evil-morty SIGNED the anti-fabrication core** (no fail-open, no overflow/NaN reaches a verdict); folded 3 LOW: `is_sourced` docstring softened, an `isfinite` guard added (fail-closed on a non-finite injected record), the "decomposition"→"first-order consumption" naming fixed; documented the reactant-coefficient rate-convention assumption (tracked debt). |
| DAG-HOLD-MR-01 (item 2b) | C | `serial_holds` on `RankedDAGSummary` — the DAG-HOLD-01 serial-schedule hold made machine-readable as `(producer, consumer, minutes)` triples (was a human note only). **Digest-EXCLUDED** (`compare=False`): fully determined by `edges` + `process_requirements`, so it adds no identity and every existing DAG digest stays byte-stable; schema `v1alpha3→v1alpha4`, descriptor `v1alpha15→v1alpha16`, one golden (`response_schema.json`) regenerated, non-vacuous (the 40-min DAG carries `(0,2,40.0)`). |
| ONLOAD-REDERIVE (item 2, decided not built) | C | **Scope decision recorded, build-ready** (`docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.1.md`) — item 2's gate was "a scope decision". Resolved: opt-in **digest-excluded** thick per-step payload + a load-time coherence check (mirroring PROCESS-ADMIT-01), protection-equivalent to folding into `result_digest` without changing every route identity. The build (new Molecule/Envelope serializers + conservation-certified route reconstruction + 4 coherence checks) is larger than items 1+2b+3 combined and touches the module that gates every compile, so it is scheduled as its own round rather than rushed. |

**ROUND 18** (commit `5f83f6a` on branch `observability-electrochem-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; **additive** (6 new files + 1 package `__init__` re-export — new exports
only, no schema/golden/compiler-behaviour change); a 6-lens evil-morty workflow found **6 real weaknesses**, all folded
(4 code) or documented (1 boundary + 1 docstring) and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| OBSERVABILITY-01 | C·B | The **three-axis Observability Score** (`smartchem/observation/observability.py`) — cheap epistemology as a ranking objective. A SOURCED `OBSERVABLE_SIGNATURES` table keyed on **canonical structure** (Br₂ the DOW flagship: orange-red colour + phase separation; I₂ the contrast with the starch test), citations REQUIRED (§10.4). The `ObservabilityProfile` keeps **process / identity / purity as three SEPARATE axes**, never one number (invariants 5 & 7 — there is no `overall_score`); Pareto ranking (`observability_dominates`/`_frontier`) that refuses to collapse (a process-strong route does NOT dominate an identity-strong one — incomparable). Non-vacuous: Br₂ (2,1,0) dominates I₂ (1,1,0). Negation-aware bridge to ROUND-17's VERIFICATION bucket. Self-contained (NOT wired into the CostVector — that axis wire-in is a deferred schema bump). Folds: **(HIGH)** corroboration read "colourless" as corroborating COLOUR (the ROUND-17 negation fold via morphological absence) → word-boundary + extended veto; **(MED)** corroboration ignored the signature axis (process→identity leak) → axis-aware evidence; **(MED)** `sourced` was a stored forgeable flag → a computed table-provenance property. |
| ELECTROCHEM-01 | B·EM | The **electrochemical/EM bridge** (`smartchem/electrochemistry.py`) — SOURCED standard reduction potentials (CRC / Bard & Faulkner, known physics) → cell potential, ΔG° = −nFE°, spontaneity, Nernst, electrolysis voltage. Fills the documented fail-closed `open_circuit_voltage` hole in `smartchem/cell.py` for the standard-state case; reuses that module's Faraday law. **Closes the DOW loop with ROUND-17**: `Cl2 + 2 Br- -> Br2 + 2 Cl-` is not only enumerable but **SPONTANEOUS** (E°cell = +0.271 V, ΔG° = −52.3 kJ/mol), the reverse non-spontaneous — the known-answer calibration. Keyed on the couple's structural digest, fail-closed UNKNOWN, W3 (thermodynamic tendency, never rate). Folds: **(MED)** `gibbs_j_per_mol` took n as an unvalidated guess → derive n = lcm(cathode.e, anode.e), refuse a wrong one; **(MED, documented)** aqueous phase-scope boundary (F5, tracked debt); **(LOW)** citation-guarantee docstring overclaim corrected. |

**ROUND 17** (commit `6761350` on branch `process-observation-redox-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; **purely additive** (`git diff --stat main` empty — six new files, zero
edits to existing code, so no schema/golden blast radius); both evil-morty red-teams found REAL weaknesses, all folded and
pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| PROCESS-OBS-01 | C | The **read-only `ProcessObservationIR` evidence-ingress layer** (contract P1) — the poor-man ethos made computational. A new `smartchem/observation/` sibling package (like `smartchem/evidence/`: reuses `Digestible`+`ReactionDirection`, never enters the executor registry, drags zero heavy modules): an immutable source-fragment IR, the five whole-path **capability bundles** (MATERIAL/CAPABILITY/VERIFICATION/CLOSURE/SCALE → EVIDENCED/GAP/BLOCKED, fail-closed), a **no-Frankenprocedure** merge, and a read-only **projection gate**. All 7 contract invariants enforced in code (`provenance_digest` computed not stored; NO readiness field). NOT wired into the response — no schema/golden change. Folds: **(CRITICAL)** negation-blind matcher read "no containment" as containment → whole-support-text negation veto; **(HIGH)** silently-omitted calibration passed a numeric conclusion → fail-closed (positive calibration required), test corrected; **(MEDIUM)** merge spliced different reactions under one self-declared context → identity+direction agreement required. |
| REDOX-DISPLACE-01 | B | The **coupled half-reaction combiner** — the DOW enumeration wall falls. `HalfReactionCouple` (molecular redox couple) + `combine_half_reactions` (electron-balanced by LCM) → a conservation-checked `RedoxDisplacementEdge` that rides the **unchanged** search through an opt-in `RedoxDisplacementProvider` (absent from `DEFAULT_TRANSFORM_REGISTRY`, like heterolytic/redox). Enumerates `Cl₂ + 2Br⁻ → Br₂ + 2Cl⁻` — the 1:2 recon proved unreachable by `redox_edges` (single-species) or `capped_scissions` (1:1). Committed harness (`experiments/redox_displacement_probe.py`, FROZEN_HASH). Fold: **(MEDIUM)** the certificate proved conservation but not redox-ness (a hand-built edge accepted a fabricated electron count / fictitious labels / an identity `Na→Na`) → an electron-ledger verification ties `electrons_transferred` + labels to the actual charge redistribution. |

**ROUND 16** (commit `c9e0fed` on branch `dag-thermo-bromine-2026-09-06`) — 2 builds; each `design → recon →
build → reproduce → evil-morty → fold → verify`; both evil-morty findings folded and pinned by tests:

| Item | Lane | What shipped |
|---|---|---|
| DAG-THERMO-01 | C·B | A **per-node thermochemical roll-up** feeds convergent-DAG ranking, so a DAG ranking is now as rich as a linear one. `dag_thermo_rollup` aggregates the four sourced per-reaction verdicts (selectivity/feasibility/equilibrium/kinetics) worst-node-dominated — reusing the *same* per-step providers, default tables, and worst-folds the linear `fit_route` runs; `_dag_score` now mirrors `_route_score` tier-for-tier; `RankedDAGSummary` (schema v1alpha3) surfaces all five verdicts, parity with the route summary. RANKING-ONLY — never changes a section-11 status. Folds: non-vacuous selectivity/kinetics wiring test (a real FAVORED DAG, was all-UNKNOWN); reverted a `rank_dags` table-param trap that re-opened the exact ROUND-15 divergence. |
| DOW-BROMINE-01 | B·C | **Phase 1 of the DOW-bromine litmus:** elemental bromine is now a first-class **SOURCED, USGS-priced** commodity ($2.70/kg 2024, MCS 2026, bromine content), added to both the frozen provenance seed and the live copy; new `INDUSTRIAL` availability tier (not a kitchen commodity — the DOW insight, encoded); costed end-to-end through `basket_cost_vector`/`cash_floor`. Folds: the basis now discloses the figure is a compound-dominated import blend normalized to contained bromine, not an elemental-Br₂ spot price. |

**ROUND 15** (merge `978da9b`) — DAG-HOLD-01 (serial-hold disclosure), DAG-RANK-01 (best-first DAG ranking, structural).
**ROUND 14** (`574a3e2`) — DAG-BENCH-01, STEREO-DOSSIER-01, ORGANIC-PRICE-01 (methanol/Methanex) + 2 refutations.
**Prior rounds (R5–R13):** resonance-canonical identity + caps, the 4 IR-COMMUTE families, per-route/DAG process
re-derivation, cost/affordability, USGS inorganic pricing, combined-verdict HMAC, the sound distinct-Z CIP slice. Full
ledger: `UPTAKE_MANIFEST_v0.5.0a1.md §5`–`§16`.

---

## 🎯 QUEUE — what needs doing, ranked

Ranked by value ÷ cost. **Size** = build effort (S/M/L). **Horizon** = short (cheap, self-contained) / medium (needs a
scope decision or a real build) / long (blocked on a sourcing or oracle wall). *(DOW)* = advances the DOW-bromine litmus.

> **ROUND 23 CLOSED item 3's core-E1 half** — the duration-aware survival verdict is now wired into E1 (`DEGRADES →
> DEGENERATE` over a sourced serial hold, the survival monoid functor `S: Process → ([0,1], ×)`). What remains of item 3 is
> the **DOW-Br₂ collider/modified-Arrhenius kinetics** half (item 3b below), which is sourcing/modeling-gated, not
> build-gated. **ROUND 21 CLOSED item 2** — on-load re-derivation of the composability + physical + ranking axes shipped (the
> ChatGPT external review was folded against the tree first; two holes it/the adversary found were closed before code).
> **ROUND 20 CLOSED item 1** — the general CIP breadth-first **namer** (Rules 1b/2/4/5 + aromatic Kekulé-averaging
> sound-deferred, tracked below).

| # | Item | Lane | Size | Horizon | Gate / blocker |
|---|---|---|---|---|---|
| **K-B** | **Move-1 keystone Rung B** — `OpenChemDiagram` alongside `Reaction` + the 3-part gate (spec merged; build-ready) | **A·B** | **L** | **build-ready** *(on the user's go)* | design gate cleared (contract merged PR #17, sharpened v0.2 — general decoration slot); additive/byte-stable/fail-closed; the flagged design call is whether to factor `open_diagram.py` into a generic core + per-domain construction layer. **NEXT FULL-BLAST TARGET.** |
| **M2-FP** | **Move-2 functorial-physics product** — recognize `feasibility.py`'s Δ_rG as the additive functor `G: Process → (ℝ,+,≤)` (Hess = functoriality), pair it with R23's survival functor `S: Process → ([0,1],×)` in an explicit **Pareto product**, and verify/repair the DAG rollup's worst-node-vs-additive conflation | B·C | **M** | **build-ready** *(new, the user's to schedule)* | both functors already computed; the rung is the categorical recognition + product order + a property test that `net_ΔG(route)==Σ steps` (Hess); enables the DOW-Br₂ **thermo** verdict once Br/Br₂ ΔH_f°/S° are sourced (a data add). Fold: `docs/research/FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md` |
| 3b | **Model DOW-Br₂ collider / modified-Arrhenius kinetics** (the item-3 remainder; core-E1 wire-in DONE R23) | B·C | **M** | long | the recovered Warshay primary is bimolecular `kD·[Br₂][M]` with a `√T` factor at shock-tube T — needs a collider-state + modified-Arrhenius model + reverse/hold scope; NOT compatible with the concentration-free first-order seed |

### K-B · Move-1 keystone Rung B — build the open backbone's first increment — **L**, build-ready *(on the user's go)*
The Move-1 keystone contract is **merged** (design gate cleared, PR #17). Rung B is the first buildable increment:
introduce `OpenChemDiagram` — a chemistry **multi-terminal hyperedge** construction layer over a factored `open_diagram.py`
core — **alongside** `Reaction`, with a `Reaction → OpenChemDiagram` functor + a `.close()` round-trip. Land the **3-part
acceptance gate**: (1) interchange/braid/hexagon proven on the new type **under the honest `canonicalize` quotient**
(fail-closed on the budget refusal); (2) a **real non-test consumer** — `ExperimentStep.open(...)` representable + `.close()`
reproducing today's `Reaction` certificate byte-for-byte (P3); (3) a **P4 provenance round-trip** (causal DAG preserved,
only the spurious linearization quotiented). **Additive, byte-stable** (no `Reaction`/`scheduled_product` mutation → every
existing digest unchanged, P2), **fail-closed**. The legacy `Reaction` xfail (`tests/test_laws.py:330`) is
**preserved-and-annotated, not flipped**. Flagged design decision for the build: factor `open_diagram.py` into a generic
core + per-domain construction layer (recommended) vs a parallel type. **v0.2 seam refinement (free-energy fold):** the
factored core carries a **general monoidal-decoration slot** (payload + combine-under-`then`/`tensor` + interchange-invariance),
of which Rung B instantiates *only* conservation + provenance — so the already-built Δ_rG (`feasibility.py`) and survival (R23)
functors and later observability ride the same slot with no second refactor. Scope unchanged; seam sharpened. Full spec + review folds:
`docs/research/OPEN_SMC_CHEMISTRY_BACKBONE_CONTRACT_v0.1.md` (v0.2); the fold: `docs/research/FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md`.
Rungs **C** (full open-step pipeline migration: `ExperimentStep`/`Route`/`SynthesisDAG`) and **D** (meta-compiler at `service.py`,
closing = compiling) follow, each its own round.

### M2-FP · Move-2 functorial-physics product — recognize + unify the two built physics functors — **M**, build-ready
The free-energy-landscape fold (`docs/research/FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md`) found that **two of Move 2's
functors are already computed in code**, just never framed or unified as functors: the **kinetic-survival** functor
`S: Process → ([0,1],×)` (R23, `composability.py:346-363`, `surviving_fraction = exp(−kt)`) and the **thermodynamic-drive**
quantity `Δ_rG` (`feasibility.py:245-247`, Hess's law from sourced ΔH_f°/S°). The rung: (1) recognize `Δ_rG` as the additive
functor `G: Process → (ℝ,+,≤)` — **Hess's law *is* the functoriality**, `Δ_rG(g∘f)=Δ_rG(f)+Δ_rG(g)`, pinned by a property test
`net_ΔG(route)==Σ steps`; (2) put the two in an explicit **Pareto product** (no scalar collapse — "favorable ≠ fast"), and audit
whether `_route_score`/`_dag_score`'s tier-folding is a true product or a lossy scalarization; (3) **candidate finding to verify**:
DAG-THERMO-01 aggregates ΔG *worst-node-dominated*, which answers "any stuck step?" — **not** the additive net-ΔG (Hess); the two
are distinct legitimate aggregations the current code may conflate. **Litmus win:** unlocks the DOW-Br₂ *thermodynamic* verdict
(`Br₂ → 2 Br•`) the moment Br/Br₂ ΔH_f°/S° are sourced (a data add, not a build) — the walled item-3b *rate* stays walled.
Precedent (verified): Baez–Pollard open reaction networks; de Donder affinity `𝒜=−Δ_rG`; detailed-balance caveat on the
gradient-flow reading (Mielke/Maas). Data-gated only where a new species record is needed; otherwise additive/byte-stable.

### 1 · General CIP — the breadth-first namer — ✅ **DONE (ROUND 20, ID-STEREO-CIP-NAMER)**
Shipped: `smartchem/smiles.py` `_cip_ranks`/`_cip_compare`/`_cip_digraph`, wired into `_cip_labels`; validated by
`experiments/cip_namer_probe.py` (5 layers, FROZEN_HASH) + `tests/test_cip_namer.py`. CIP **Rule 1a**, breadth-first,
branch-by-branch with need-to-know pruning (the DFS-vs-BFS fix), phantom atoms for multiple bonds + ring closures,
validated `namer(mol) == geometric_handedness(true_priorities, sense)` on the textbook battery (incl. the L-serine (S) /
L-cysteine (R) flip). At R20, aromatic-reaching ties deferred. **ROUND 22 extends this with bounded neutral mancude
averaging and corrects the R20 soundness claim:** uppercase Kekulé inputs bypassed the old guard and could emit a wrong
label. The concrete mirror pair is now fixed and regression-tested. See the DONE ledger and manifest §§20/22;
higher-rule ties and unsupported ring systems remain TRACKED DEBT below.

### 2 · Composability + physical re-derivation on load — DAG **and** linear — ✅ **DONE (ROUND 21, ONLOAD-REDERIVE)**
Shipped: `smartchem/service.py` (thick `replay_payload` + `_reconstruct_route`/`_reconstruct_dag` +
`_check_verified_admission`) + `tests/test_onload_rederivation.py`. The ChatGPT external design review was folded
**against the tree** (8-agent recon+adversary pass) before any code — see `docs/research/ONLOAD_REDERIVATION_SCOPE_DECISION_v0.2.md`
(supersedes v0.1). It corrected TWO holes in the v0.1 design: (1) the load-time coherence check did **not** bind the
payload to `route_digest` (a substitution attack) — closed by `reconstruct(payload).digest == route_digest`, cheap because
`route_digest` already covers the full step content; (2) the `compare=False` payload was bypassable by **deletion** —
closed by a **fail-closed** consumer policy (verified-admission requires every FITS route to carry a matching payload),
which needed **no schema bump** (route identity byte-stable, no golden churn — lower blast than the reviewer proposed).
Plus the v0.1 HMAC conflation was corrected (a public digest recompute is free; the key-holding residual is irreducible).
See the DONE ledger and manifest §21. TRACKED DEBT below: the keyless eval-context-relaxation boundary + the
verified-admission cost lever (evil-morty F1/residual).

### 3 · Wire the duration-aware verdict into core E1 — ✅ **DONE (ROUND 23, DURATION-SURVIVAL-01)**
Shipped: `smartchem/experiment/composability.py` (`_apply_duration_gate`/`_hold_survival`/`_survival_product`) +
`dag.py` (`_serial_hold_segments`) + `tests/test_duration_survival_gate.py`. E1's `_judge_transition` consumes the
DAG-HOLD-01 serial hold: with a sourced first-order decomposition rate (R19 primitive, matched on canonical structure),
the surviving fraction over the hold's intervening-step temperatures MOVES the verdict (`DEGRADES → DEGENERATE`, even
where the onset table is silent; `MARGINAL → UNKNOWN`; `SURVIVES` confirms; only ever tightens, never touches an
already-`DEGENERATE` base). Survival is the monoid functor `S: Process → ([0,1], ×)` — `route_surviving_fraction` is the
product over duration-assessed handoffs. Fail-closed on undeclared hold temperatures or non-finite rates; the R22 unit
lock (`ConditionEnvelope.duration = min`) is the declaration side, converted explicitly to the primitive's seconds. See
the DONE ledger and manifest §23. TRACKED DEBT below: linear-route holds are unmodeled (only DAG serial holds carry a
hold), and the R19 reactant-coefficient rate-convention residual still applies.

### 3b · Model the recovered DOW-Br₂ collider / modified-Arrhenius primary — **M** *(DOW)*
**The Br₂ primary is recovered but not first-order-seed-compatible:** Warshay, NASA TN D-3502 (1966), gas-phase
shock-tube initial dissociation in Ar/Ne/Kr, `kD = A·√T·exp(-Ea/RT)`, `-d[Br₂]/dt = kD·[Br₂][M]`. It cannot enter the
concentration-free first-order seed the R23 gate consumes. The remaining gate is collider state, modified-Arrhenius
units and reverse/hold scope — a **modeling** wall, not missing primary access. Source URLs, pages and hashes:
`docs/research/SOURCING_RECON_2026-09-07.md` and `experiments/sourcing_recon_2026_09_07.json`.

### 2b (DONE R19) · machine-readable `serial_holds` on `RankedDAGSummary`
Shipped — the DAG-HOLD-01 serial hold is now a `(producer, consumer, minutes)` triple field (digest-excluded disclosure),
not just a human note. See the DONE ledger.

---

## ⏸️ DEFERRED — explicit remaining gates (not fabricated)

- **The DOW brine-vs-mined *cost ranking*** (the DOW litmus's last lane, Lane C). Pricing (R16), mechanism (R17), and
  electrochemistry (R18) all shipped; ranking the brine route against the mined/market route quantitatively needs a
  correctly scoped **Cl₂ pricing integration** and a **NaBr feedstock** price. **ROUND 22 closes the chlorine primary-access
  gap:** Los Fresnos's September 9, 2025 approved municipal offer gives $1.24/lb in a 2,000-lb cylinder ($2,480), plus
  $50 monthly cylinder rental, effective October 2025–September 2026. The attachment is unsigned and no invoice was
  recovered: an approved offer, not an observed transaction, industrial spot price or historical Dow price. It is
  recorded as reconnaissance, not silently admitted into default commodity pricing. Integration needs structure-bound
  Cl₂ registration and explicit package/rental/region/offer basis. NaBr's mass-fraction calculation would be a labelled
  DERIVED bromine-content proxy, not a sourced NaBr purchase price. **That same-benchmark proxy cannot prove an undercut:**
  its stoichiometric NaBr cost already equals the bromine benchmark before adding chlorine. A cheaper-brine claim needs
  an independent feedstock/extraction-cost basis (conditional algebra in the sourcing report). The mechanism (ROUND 17) and aqueous standard
  feasibility (ROUND 18) remain done; a quantitative whole-route or historical cost advantage is still unestablished.
- **A second sourced organic price** (was ROUND-15 item 3; Lane C). Attempted acetic acid (highest value — it ripples
  the methyl-acetate golden) and ethanol. **Wall:** organic producers post price *increases* (Celanese: +$50/MT Feb,
  +$0.10/lb Mar 2026), not absolute reference sheets; absolutes are aggregator-walled (Intratec/ChemAnalyst). Ethanol's
  only primaries are a government *projection* (EIA AEO Table 12 — a forecast, not an observed price) or a *foreign,
  regulated, denatured fuel-grade* price (IPART NSW, needing FX+density+unit conversions for a weak match). None clears
  the bar methanol set (a directly-readable, dated, observed absolute for the exact chemical), so per §10.4
  anti-fabrication this is a **DEFER, not a fabricated price** — the same call R13 made. Revisit if the bar is
  explicitly relaxed, or pivot to **bromine (USGS-priced)** via DOW litmus item 2.

---

## 🚫 NOT BUILDING — deliberately parked (with the reason, so nobody re-walks it)

- **The >64-heavy work-metered resonance escape valve.** Characterized and **refused** (RESONANCE-WORK-01). Reinforced
  YAGNI: the largest *real* target is 13 heavy (aspirin); the 24-heavy figure is a benchmark (coronene); a **72-heavy**
  fixture already proves the >64 path falls back to literal identity in ms — the door is tested-shut. Even built it
  can't separate malice from legit, and it entangles `Molecule.canonical()` (system-wide identity hot path) with an
  uncached meter that conflicts with `resonance_canonical`'s `@lru_cache`. Pinned by `tests/test_resonance_actual_work.py`.
  Re-open only when a real >64-heavy target appears — then re-measure the branch *before* touching core code.

---

## ⚠️ TRACKED DEBT — known, carried, not silently

- **Interchange-law xfail** (Lane A) — `tests/test_laws.py:330`: linear histories cannot quotient independent events by
  interchange. Orthogonal architecture debt; 1 xfail.
- **Load-time free-text trust boundary** (Lane C) — ✅ **STRUCTURALLY CLOSED (ROUND 21, item 2)** for a verified-admission
  consumer: `response_from_payload(require_verified_admission=True)` reconstructs the route/DAG from the thick
  `replay_payload` and re-derives all three axes + ranking, refusing a bare-relabel or substituted evidence with no key.
  The default (non-verified) path is unchanged (still process-axis-only, HMAC-optional), so a consumer must **opt in** to
  the close. Two residuals carried below.
- **Verified-admission keyless eval-context relaxation** (Lane C; ROUND-21, evil-morty F1 VERIFIED) — the re-derivation
  builds its bench box from the response's OWN request, so a keyless attacker who relaxes that request (and recomputes the
  free public `result_digest`) can re-derive an out-of-bounds route to FITS. The check authenticates verdict↔route
  coherence UNDER THE STATED context, not the context itself. Closed by pinning the request (`expected_request_digest`) or
  a `verification_key` (the request is folded into `result_digest`); NOT forced (the process axis trusts the request
  identically). Documented + pinned both directions.
- **Verified-admission compute cost** (perf; ROUND-21) — `_check_verified_admission` runs the full `rank_routes` fold per
  FITS dossier on load (amide-heavy targets pay the ~500 ms `Molecule.canonical()` resonance cost each). Opt-in and
  bounded by candidate count; a verified-admission consumer pays for the assurance. Reduce (if it ever matters) by
  caching the per-route fit; not worth it today.
- **DAG `dag_bench_fit` compute multiplicity** (perf, correctness-neutral) — a DAG-mode compile runs `dag_bench_fit`
  ~3×N (rank_dags key + `of_dag` + `_dag_bench_note`), and each call now ALSO computes the four-provider thermo roll-up
  per node (DAG-THERMO-01), so it is heavier. Still bounded and compile-time (real DAGs are small). Reduce by threading
  one computed fit through all three if it ever matters; not worth a refactor today.
- **Phase-specific electrode potentials** (Lane B·EM; ROUND-18 evil-morty F5) — the halogen couple is phaseless, so the
  sourced `STANDARD_REDUCTION_POTENTIALS` are the AQUEOUS standard values. This is CORRECT for the aqueous DOW displacement
  (+1.087 V) and fail-closed for an explicitly-phased couple (returns UNKNOWN, never a wrong number), but a liquid-phase
  value (Br₂(l) = +1.066 V) is unreachable until a phase-carrying couple API exists. YAGNI today; revisit if a route ever
  reasons about the liquid product.
- **Observability Score → CostVector verification axis** (Lane C; ROUND-18) — the Observability Score is a self-contained
  ranking primitive; feeding its process/identity/purity strengths into the affordability `CostVector` as a verification
  axis needs a new `_AXES` entry + a frontier-entry schema bump + golden regen (a deliberate deferral, not an oversight —
  the score is honest and usable standalone now).
- **CIP external-oracle scope** (Lane B; ROUND-22) — `experiments/cip_external_oracle_probe.py` now compares against the
  accurate RDKit `rdCIPLabeler` through an external parser/graph/labeler, including aromatic, explicit-Kekulé and reversed
  atom-order spellings. RDKit remains an optional probe dependency, absent from the runtime. Its implementation is
  separate but the CIP specification is shared; finite agreement does not prove correctness on arbitrary graphs.
- **CIP full completeness — higher rules and unsupported ring systems** (Lane B; ROUND-20/22) — the namer remains
  **Rule 1a only**. Neutral mancude averaging is built for the bounded C/N/O/S valence slice, including supported fused
  systems. Isotope/stereochemistry-dependent ties, ring stereocentres, and comparisons needing charged, exocyclic,
  incompletely conjugated, untyped or over-budget ring connectivity still DEFER. Limits: 30 atoms per ring system,
  128 complete matchings, 10,000 matching-search visits; a partial partner set is never used. The aromatic parser's
  charged-donor limitations remain separate (some aromatic inputs refuse while explicit spellings reach CIP deferral).
  See `docs/research/CIP_MANCUDE_SCOPE_2026-09-07.md`. External finite agreement does not prove full CIP soundness.
- **CIP comparator transitivity residual** (Lane B; ROUND-20, evil-morty) — `_cip_compare` is used as a `cmp_to_key` sort
  key, which assumes transitivity; a deep degenerate tie tree could in principle violate it. No counterexample found
  (fuzzer-clean) and the `sorted(ranks)==[0,1,2,3]` guard in `_cip_ranks` catches any top-level cycle (→ DEFER, sound),
  but a transitivity PROOF is not in hand — documented, not eliminated. (The exocyclic-multiple-bond-into-aromatic path IS
  discharged, by an explicit guard in `_cip_digraph`.)
- **Duration-stability reactant-coefficient rate convention** (Lane B·C; ROUND-19, evil-morty) — `surviving_fraction`
  assumes the sourced `k` is the per-species rate (`-d[A]/dt = k[A]`), which both seeded records pin in their provenance;
  a future first-order record with coefficient > 1 sourced under the *reaction-rate* convention would be off by the
  stoichiometric factor. The module can't detect the convention from the data — documented boundary, not a silent guess.
- **Duration-survival hold scope** (Lane B·C; ROUND-23) — ✅ core E1 **now consumes** the hold: `_apply_duration_gate`
  turns a DAG serial hold + a sourced first-order rate into a verdict (DURATION-SURVIVAL-01), fail-closed on undeclared
  hold temperatures or non-finite rates. Residuals carried, not silent: (1) only **DAG serial holds** carry a modeled
  hold — a **linear route's** adjacent handoff passes no hold, so its intermediates are never duration-assessed (a linear
  route has no idle-between-siblings time the model can source; a genuine bench hold would need an explicit hold
  declaration the type does not yet carry); (2) each intervening segment uses the **hi end** of its declared temperature
  range (worst-case within that step) — a policy, stated; (3) the R19 reactant-coefficient rate-convention residual
  (below) still applies. The R22 unit lock (`ConditionEnvelope.duration = min`) remains the declaration side, converted
  explicitly to the primitive's seconds.

---

## How this file stays current (so it never needs a workflow to rebuild)

Updating `ROADMAP.md` is part of the per-round ritual, the same reflex as bumping `UPTAKE_MANIFEST §N` and the README
suite count:

1. Ship a round → move each shipped item from **QUEUE** to the **DONE** ledger with its commit.
2. Re-stamp `verified @ <commit>` and the suite count at the top.
3. Add any new queue items with lane + size + gate + cheapest first step. Anything walled → **DEFERRED**; anything
   refused → **NOT BUILDING**; anything carried → **TRACKED DEBT**.

Next session: read *this file*, not a 5-agent recon.
