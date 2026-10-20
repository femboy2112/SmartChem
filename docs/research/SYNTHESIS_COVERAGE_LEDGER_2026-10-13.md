# Synthesis-Coverage Campaign Ledger (2026-10-13)

**The durable record of OPERATION SMARTCHEM — the generative-synthesis-algebra campaign.**
Companion to `REACTION_ALGEBRA_COVERAGE_AUDIT_2026-10-12.md` (the family-by-family obstruction audit that
opened epic #103 + issues #104–#123); this ledger tracks what was *repaired and verified*, issue by issue,
with reproducer, root-cause class, fix, commit, and evidence.

- **Base (campaign fork point):** `main` @ `99fce34` (SmartChem 1.0.0).
- **Working branch:** `feat/chemical-graph-projections` (draft PR #101), campaign commits on top of `af66ef3`.
- **Governing contract:** `COMPATIBILITY.md` 1.0. New behaviour rides versioned providers/fields; the frozen
  verbs/schemas/digests do not move. Every `compare=False` field added here is outside identity + every digest.

## The scientific contract (held throughout)

A conserved equation is not a reaction; a valid rewrite is not a recognized class; a recognized class is not
feasible; a feasible reaction is not safe/affordable/sourced. The four statuses — `FORMAL_CANDIDATE`,
`REACTION_VOUCHED`, `CONDITIONS_SUPPORTED`, `PROCESS_SPECIFIED` — are not reinterpreted. **No false-VOUCH** is the
cardinal invariant: coverage loss (a real reaction demoted-as-unrecognized) is acceptable; a fabricated pass is not.

## Obstruction taxonomy (every "no route" is classified as exactly one)

`generated-but-demoted` · `not-generated` · `unrepresentable` · `not-recognizable` · `not-feasible` ·
`budget-truncated` · `internal-error`. The campaign refuses to report all seven as "no synthesis route".

---

## Phase 1 — foundational soundness / truthfulness (P0 + graph P1)

This phase closes holes where the engine could **assert more than it can defend** — false-VOUCH, over-claimed
naming, over-claimed completeness, phantom self-supply. These are truthfulness repairs; they add **no** new
coverage (that is Phase 2: the infra walls + recognizers). The objective is to keep every later expansion honest.

### #126 — forged `ReactionCenter` trusted as recognition evidence  ·  `generated-but-demoted` (false-VOUCH) ·  FIXED `eacc086`

- **Reproducer:** `scratchpad/probe_126.py` (committed as `tests/test_issue_126_forged_center.py`). A bundled
  double condensation `2 lactic acid -> lactide + 2 H₂O` passes the whole-molecule acyl census but is NOT an
  elementary single condensation. Honest/absent centre → demoted; a **forged elementary centre** → VOUCHED
  "acyl condensation". The vouch tracked the *supplied* centre while the molecules were held fixed.
- **Root cause:** the acyl/ether/N-alkylation recognizers read `step.reaction_center` as their locality witness,
  and `ReactionCenter.is_elementary_condensation` inspects only the centre's own declared bonds. `ExperimentStep`
  type-checked the centre but never verified it against the molecules. ([[a-verifier-that-cannot-verify-must-fail-closed]])
- **Fix:** a centre is vouch evidence ONLY when the engine derived/authenticated it. `ExperimentStep.center_trusted`
  (compare=False; set by `from_transform` and the replay deserialization seam) gates it; the oracle reads the centre
  through one `_vouchable_center` helper that fails closed on an untrusted-or-absent centre. Closes the DIRECT
  public-API hole; the verified-replay path (which already authenticates centres `in centres`) is unchanged.
- **Evidence:** 7 new tests; 89 passed across the poor-man oracle / span-local / etherification / N-methylation /
  tamper-hardening (incl. the thick-replay round-trip no-false-reject) / DA-oracle suites. ruff clean.
- **Compatibility:** no wire/digest change (compare=False field; bare-load advisory contract preserved).

### #128 — graph named a family from reaction-centre equality, not re-derivation  ·  `not-recognizable` (mislabel) ·  FIXED `246fbd2`

- **Reproducer:** a synthetic `H + H -> H2` step carrying a verbatim copy of `_DA_CENTER` (reaction_center ==
  `_DA_CENTER`) was named "Diels–Alder" by the scheme; the oracle, which re-derives [4+2]-ness from the molecules
  (Layer A), correctly abstains. (`tests/test_synthesis_scheme.py::test_family_naming_is_rederived_by_the_oracle_never_centre_equality`.)
- **Root cause:** `_reaction_family_for_step` matched a `(formed, broken) -> name` table *before* the oracle.
- **Fix:** the oracle is the sole naming authority; the centre-equality table is deleted. Genuine provider DA is
  still named (verified on the cyclohexene litmus); an unmatched step shows its neutral bond-change description.
- **Evidence:** scheme suite 14 passed / 3 RDKit-skipped; graph_projection suite green. ruff clean.

### #129 — scheme green-lit `UNATTESTED` completeness  ·  (presentation over-claim) ·  FIXED `246fbd2`

- **Reproducer:** `render_scheme_html(route, search_result=None)` → `UNATTESTED`; the banner predicate put
  `UNATTESTED` in its `COMPLETE` set, rendering it green/"ok" and suppressing the incompleteness notice.
- **Root cause:** `const COMPLETE = {COMPLETE, COMPLETE_WITHIN_BOUNDS, UNATTESTED}` in the scheme template.
- **Fix:** three distinct states — complete (ok) / UNATTESTED (amber "completeness UNKNOWN", an explicit
  disclosure, *not* a failed search) / partial (warn). New `--unknown` token + class; aligns with the ordinary
  renderer. Tested via the generated display predicate over its own emitted `COMPLETE` object, not string presence.

### #124 — ancestor precursor silently treated as stocked leaf (phantom self-supply)  ·  `not-generated` (latent soundness) ·  FIXED `474e018`

- **Reproducer:** `tests/test_issue_124_cyclic_refusal.py` — a minimal rank-flat reciprocal provider (ethanol ⇌
  dimethyl ether). An UNSTOCKED search over it reached the ancestor-exclusion branch and yielded a self-supplying
  route (A←B←A with no external feed), which then crashed the linearity invariant with an uncaught `StepError`.
- **Root cause:** `missing = [m for k,m in distinct if k not in on_hand and k not in ancestors]` (routes.py L543
  linear, L787 DAG) dropped an ancestor precursor from the still-needed set, treating it as available.
- **Reachability:** **unreachable under the W1 strict-rank capped-scission grammar** (an ancestor can never
  reappear as a lower-rank precursor), so the clause was dead *today*; it becomes a phantom the moment a rank-flat
  / reversible provider exists (#104/#123). Proven reachable only with the fake reversible provider.
- **Fix:** an ancestor precursor that is not external stock is a cyclic dependency → the branch is refused
  (`continue`), never folded into "available". Provably a no-op under W1 (identical `missing` when no
  ancestor-precursor exists); the safety net #104/#123 require. Both searchers (linear + DAG) guarded.
- **Evidence:** 3 new tests (unstocked → 0 routes/DAGs, no crash; stocked positive control → 1 route; W1
  capped-scission unaffected). Core route/DAG regression: **144 passed / 0 failed** (test_routes, test_dag,
  test_graph_projection incl. the 9-route + 47-DAG ensembles, test_v0_7_production_algebra, test_dag_flow,
  test_reagents) — the guard is a confirmed no-op on every W1 search.

### #131 — oracle exceptions masked as NOT_A_REACTION  ·  `internal-error` (observability) ·  FIXED `d8adf19`

- **Reproducer:** `tests/test_issue_131_typed_outcomes.py` — a deterministically-poisoned recognizer; the old
  `recognize_reaction_type` returned `None` for both a genuine non-match and an internal fault, indistinguishably.
- **Root cause:** `recognize_reaction_type` caught every `Exception` and `continue`d; `route_reaction_type_blockers`
  then labelled a faulted step with the same "unrecognized reaction type" demotion as a clean non-match.
- **Fix (additive, contract-stable):** `RecognitionOutcome` + `recognize_reaction_type_outcome` expose typed
  `MATCH` / `ABSTAIN` / `INTERNAL_RECOGNIZER_ERROR(faults)`; `recognize_reaction_type` delegates (identical
  `str|None`, both abstain and error → `None`, fail-closed preserved — an exception NEVER becomes a MATCH);
  `route_reaction_type_diagnostics` surfaces the per-step distinction. `route_reaction_type_blockers` byte-unchanged.
- **Evidence:** 4 new tests; 51 passed across the poor-man recognizer suites (the delegate refactor preserved the
  exact `str|None` output). No wire/verdict-string change. ruff clean.

### Benchmark corpus — SYNTHESIS-COVERAGE-CORPUS-01 (`experiments/synthesis_coverage_corpus.py`)

The campaign's baseline instrument: POSITIVE / NEGATIVE / NULL / MUTATION cases through the oracle, measuring
recall and the must-be-zero false-vouch rate. **Baseline (post Phase 1): recall 3/3, FALSE-VOUCH 0/3, null 1/1,
mutation 1/1 — PASS.** Pinned by `tests/test_synthesis_coverage_corpus.py`.

### #109 — latent capped-scission over-generation as permanent adversarial controls  ·  `generated-but-demoted` ·  CONTROLS LOCKED (partial)

- The corpus is the permanent home for the known over-generation fictions #109 requires. Locked so far: the **R55
  reachable glue-fiction** — the generator EMITS `isopropanol + ethyl acetate -> isopentyl acetate + water` (an
  engine-derived step with a *trusted* centre; 24 of the 28 isopentyl-acetate scissions are such fictions), and
  the oracle's census + span correctly demote it — plus the **forged-centre k=2 bundle** (the lactide double
  condensation) from the #126 negatives. Both must stay demoted PERMANENTLY; coverage is never "solved" by
  certifying graph surgery.
- **Open remainder:** enumerate and lock further documented over-generation classes as the grammar widens; the
  corpus's NEGATIVE channel is the mechanism.

---

## Round II (the Phase II directive, 2026-10-13) — independent-witness hardening (#126 re-attack)

A follow-up hostile audit (issue #126 comment, `feat/chemical-graph-projections@bb11c48`) proved the Phase-1
`center_trusted` fix **still forgeable**: `dataclasses.replace(step, center_trusted=True)` runs the public
constructor, and `ExperimentStep.from_transform` trusts any duck-typed object's `reaction_center()`. A stored bit
is not an authentication boundary. This round replaces self-asserted trust with an **independent re-derivation**.

### #126 (re-attack) — a stored trust field is forgeable; recognition must re-derive from the molecules · `generated-but-demoted` (false-VOUCH) · FIXED (this round)

- **Reproducers (executed):** the auditor's `replace(untrusted_lactide, center_trusted=True)` and a fake
  `from_transform` transform, both minting a trusted elementary centre on the `2 lactic acid -> lactide + 2 water`
  double-condensation fiction. `tests/test_issue_126_forged_center.py` (rewritten) + `scratchpad/probe_126_phase2.py`.
- **Root cause:** ANY stored field (`center_trusted` bool, `reaction_center` object, or any new token) is settable
  by a data-only attacker through the public constructor / `replace` / a fake transform, and liftable onto forged
  molecules. The trust decision cannot live in a stored field. ([[a-verifier-that-cannot-verify-must-fail-closed]])
- **Fix:** `center_trusted` is **removed entirely** (not renamed). The condensation recognizers (acyl/ether/
  N-alkylation) now call `_condensation_rederives`, which reruns the generator's OWN single-cut scission
  (`structure_descent.single_cut_capped_scissions(target, (water,))`, restricted to the target's order-1 C–X bonds)
  and vouches only if the target disconnects into EXACTLY the two declared precursors with an elementary-condensation
  centre it computes itself. A bundled fiction needs ≥2 cuts → never re-derivable → demoted, regardless of any
  attached centre. `reaction_center` is retained as ADVISORY metadata (graph/scheme/replay display) only.
- **The invariant (the strongest new one this round):** *no caller-settable field can MINT a vouch, for any of the
  17 recognizers* — soundness is determined by the molecules alone (condensation: single-cut re-derivation;
  pericyclic: Layer-A retro). The **condensation families are fully CONTENT-DETERMINISTIC** (verdict is a pure
  function of the reactants/products multisets; `reaction_center` ignored).
- **Independent adversarial audit (evil-morty, fresh cases):** (B) no-false-vouch **held everywhere** — forged
  `_DA_CENTER` on a non-DA step, the lactide, and the R55 glue-fiction all demote. It **refuted the over-broad claim
  (A)** that recognition is content-deterministic for *all* recognizers: the 14 pericyclic recognizers still READ
  the declared centre (Layer B/C), so a genuine Claisen/DA built with no readable centre is demoted. This is
  fail-closed-SAFE (the centre can only DEMOTE a genuine step, never mint a false vouch — Layer A gates first), a
  COVERAGE-only residual. The docstrings were corrected to state the two-tier invariant truthfully (no over-claim).
- **Follow-up (filed as residual):** make the pericyclic recognizers content-deterministic by relying on their
  Layer-A re-derivation alone (drop the Layer-B/-C centre read), gated on fuzzing Layer A
  (`experiments/chem_differential_fuzzer.py`) — evil-morty's residual #1.
- **Cost (#127 hot-path):** re-derivation is cheap in production — an isopentyl-acetate compile spends 0.04s in 6
  re-derive calls (focused C–X-bond cutter + content-keyed `_REDERIVE_CACHE`); ~10–30ms cold / <1ms cached per step.
- **New generator primitive:** `structure_descent.single_cut_capped_scissions(reactant, reagents, candidate_bonds)`
  — a focused slice of `capped_scissions` (k=1, restricted bonds) reusing the certified `_cap_a_cut`; sound by the
  same CappedScission certificate, a pure cost pre-filter.
- **Corpus rebuilt** to the content-determinism model: POSITIVE ×4 (incl. a hand-built centre-less esterification now
  recovered by re-derivation), NEGATIVE ×4 (lactide forged via the bare ctor / `replace` / fake transform + R55),
  NULL (census-fires-but-non-elementary bundle abstains), MUTATION (ester target swapped to the isomeric ethyl
  formate — census fires, re-derivation flips off). **recall 4/4, FALSE-VOUCH 0/4 — PASS.**
- **Retired mechanism:** the "centre-absent → demote" PIECE-2 / TAMPER-HARDENING-01 behaviour is superseded by
  re-derivation; recognizer + tamper tests and their committed probes (n-alkylation, n-methylation, tamper-hardening)
  were updated to content-determinism and their FROZEN_HASHes re-frozen with documented reasons.

### #127 (§4) — raw result-cap starvation: QUANTIFIED, no meaningful failure observed · `budget-truncated` (measured null) · MEASURED

- **Instrument:** `experiments/candidate_starvation_127.py` (CANDIDATE-STARVATION-127), pinned by
  `tests/test_candidate_starvation_127.py`. Sweeps `max_routes` 1→1000 on 5 benign targets that return BOTH a
  recognized route and generated fictions under the production poor-man pool, measuring RECOGNIZED-RECALL
  (recognized-in-returned / recognized-at-high-cap), each recognized route's digest-order index, the receipt
  truncation counts, and order-invariance.
- **Finding (poor-man pool, capped-scission grammar):** recognized-recall is **1.0 at every cap ≥ 1** for every
  target (ethyl/methyl acetate, di/dimethyl ether, trimethylamine). The recognized single condensation is a 1-STEP
  route to commodity precursors and enumerates FIRST (index 0, digest order); the fictions are MULTI-step
  homologation chains occupying later slots. So the hypothesised starvation is **NOT observed** — the raw cap is not
  the bottleneck, and (per the directive) **no scheduling fix is warranted yet**. The search is also order-INVARIANT
  (sets keyed by `_ident` + digest-sorted enumeration) — a shuffled reagent/commodity order returns an identical set.
- **Boundary (honest):** this is a measurement over the natural condensation corpus in the CURRENT grammar, not a
  theorem. It holds because fictions' glue-fragments are rarely all commodities, forcing fictions multi-step/deeper.
  When the grammar widens (new providers, 2-cut) a 1-step fiction could sort before a recognized route; the harness
  is the GUARD — recognized-recall < 1.0 turns the test red, the trigger to build #127's type-gated candidate
  scheduling. A separate *not-reachable* obstruction surfaced en passant: isopentyl acetate returns 10 routes at
  cap 1000, ALL fiction, because its one real route's precursor (isopentanol) is neither a commodity nor
  depth-3-reachable — that is `not-generated`/`budget-truncated`, NOT cap-starvation.

---

## Round III — §3 held-out benchmark + #132 pericyclic content-determinism (+ closed-shell hardening)

**§3 — a second, INDEPENDENT recognition instrument** (`experiments/independent_recognition_corpus_s3.py`,
`tests/test_independent_recognition_corpus_s3.py`). Unlike the baseline corpus (whose positives are the generator's
own capped scissions), every case is HAND-AUTHORED from named-reaction chemistry and labelled REAL/FICTION/OUTSIDE
*before* the oracle runs — a generated reaction cannot be its own ground truth. 24 cases across the full outcome
taxonomy (recognized / correctly-demoted / false-vouch / coverage-gap / pericyclic-residual / mutation-off /
unrepresentable), positive/negative/null/mutation/holdout per family. **Measured: recall 10/10 on in-whitelist
positives, FALSE-VOUCH 0** (the #126 content-determinism holds under independent hand-built forge/replace/
fake-transform attack + both isomer mutations + the R55 reachable glue fiction). Honest FINDINGS (not failures): 4
coverage gaps surfaced — aldol, hydrogenation (#114), Friedel-Crafts acylation (#110), charged SN2.

**#132 — the 14 pericyclic recognizers are now CONTENT-DETERMINISTIC** (the last forgeable-field dependency retired,
extending #126 from the 3 condensation families to all 17). Each pericyclic recognizer (8 Diels-Alder + 4 [3,3]
sigmatropic + 2 electrocyclic) previously vouched on `Layer A` (the family's own guarded re-derivation from the
molecules) **AND** `Layer B/C` (an exact-equality read of the caller-settable, forgeable `reaction_center`). Layer
B/C are dropped; the recognizers now rely on the re-derivation ALONE.
- *Safety argument:* Layer B was an added AND-condition, so dropping it can only turn an ABSTAIN into a MATCH, and
  only for a step that already passes Layer A — safe iff Layer A is a sound SOLE gate + a clean SEPARATOR.
- *Evidence* (`experiments/pericyclic_layer_a_fuzz_132.py`, `tests/test_pericyclic_layer_a_fuzz_132.py`): a committed
  seeded differential fuzz establishes a **14×14 identity matrix** (each genuine centre-less member passes ONLY its
  own family's Layer A — 0 cross-poach, including the three diene-position families that share a centre with their
  dienophile siblings and so are separable by Layer A alone), a curated fiction battery (0 of 14 near-misses fire),
  and a seeded random differential (every Layer-A firing conserves mass+charge). Net: a genuine Diels-Alder/
  sigmatropic/electrocyclic step hand-built WITHOUT a centre is now recognized (the §3 pericyclic residual is CLOSED).
- *Adversarial hardening (evil-morty, independent fixtures):* the adversary BROKE the first-cut "Layer A is sound"
  claim with a **charge-separated / radical false-vouch** — a net-neutral zwitterion adduct (`C1=C[CH-][CH+]CC1`) or
  an odd-electron radical passed Layer A as a genuine [4+2]/[3,3] (a true false-vouch; re-adding Layer B would NOT
  have caught it, since a radical graph's centre still equals the family centre). Root cause: guard 2c is one-sided
  (`degree > neutral_valence`, so it drops over-coordination but not an under-coordinated radical/ion), and the net
  `charge==0` check misses internal charge separation. **Fix:** a representation-aware `is_closed_shell_neutral`
  guard (`smartchem/diels_alder.py`) now gates every pericyclic re-derivation AND the condensation re-derivation
  (`_condensation_rederives`) — a radical/ion/ylide partner is not a reactant of any of these thermal classes. The
  5 kills are frozen as regression cases; genuine recall is unchanged (identity matrix + §3 10/10 + baseline 4/4).
  Separation survived the adversary untouched (0 cross-poach across 66+ molecules).
- *No wire change:* the contract-freeze / xhigh wire suite is green (`reaction_center` is `compare=False`, never
  serialized; the default compile path emits no pericyclic step, so default semantics are unchanged).

## Round IV — §5 first new-chemistry win (#110) + §6 moonshot (lateral reachability)

**§5(A) — #110 ACTIVATED ACYL TRANSFER recognized** (`experiments/activated_acyl_transfer_110.py` + test). The 18th
attested class: an anhydride / acyl halide acylating an O/N/S nucleophile (coproduct a carboxylic acid / H-X, NOT
water) — the free-acid condensation's pre-activated sibling. Recon established this is GENERATED-BUT-DEMOTED: the
capped-scission search already emits `Ac2O + 4-aminophenol -> paracetamol + AcOH`, `AcCl + MeNH2 -> NMA + HCl`, etc.
under a declared leaving-group helper + donor stock, but the free-acid census demotes them for lacking a water
coproduct. The new recognizer (`_activated_acyl_transfer`) re-derives content-deterministically by a single-cut
scission capped with the LEAVING-GROUP acid (not water) reconstructing exactly {donor, Nu-H} — the same discipline
as the condensation recognizers, generalised past water. Conservation-locked; closed-shell guard (#132) applies.
- *Measured:* recognizer matrix 11/11, 6/6 activated positives (incl. the PARACETAMOL litmus route) recognized, 0
  false-vouch, no poach (free-acid esterification stays "acyl condensation"; Friedel-Crafts C-acylation ABSTAINS —
  out of scope, deferred to #107). Reachability (actual search): the genuine 1-step `ethanol + Ac2O -> ethyl acetate
  + AcOH` route is now VOUCHED (empty blockers), while 6 isomer/glue C4H6O3 routes stay DEMOTED — the win recognizes
  the genuine route WITHOUT lifting a fiction (content-determinism distinguishes the ethyl-acetate isomer-fictions).
- *Boundaries:* O/N/S only (C-acylation wants #107 + arene guards); small targets via a large donor (acetamide /
  methyl acetate via Ac2O) are blocked UPSTREAM by the #104 W1 atom-count wall (donor larger than target), so the
  search never emits them — a generation boundary, not a recognizer gap. evil-morty adversarial review (independent).

**§6 — moonshot: ONE lateral family reachable via opt-in state-aware search, now CENTRE-FREE** (`experiments/
lateral_reachability_s6.py` + test). `smartchem.lateral_search.lateral_route_to` already reconstructs an opt-in,
bounded, state-aware lateral route (BFS over isomer states, terminating on its own visited-set + budgets, outside
the W1 descent). Demonstrated end-to-end for Cope, Claisen and 6-pi electrocyclic: each route is oracle-vouched
step-by-step BOTH with a carried centre and — the #132 payoff — CENTRE-LESS (a hand-assembled route with no
`reaction_center`, which the retired Layer-C gate demoted). **No hard blocking theorem (recorded, NOT acted on):**
an independent recon refuted the stale "fusing a rank-flat provider into `search_routes` breaks termination" claim —
`search_routes` terminates on `max_depth` (not W1), and #124 refuses a non-stock ancestor (blocking phantom
self-supply, naming "a future rank-flat provider" as the intended customer), so a bounded lateral provider CAN ride
the route lane (a working adapter was prototyped). The real cost is a factorial simple-path blow-up a lexicographic
(rank, lateral-budget) measure would cap. That FUSION alters a default-adjacent shared path and needs its own
soundness + cost regression gate — the NEXT falsifiable step, deferred.

## OPERATION SMARTCHEM 1.5 mega-round — Wave C (#111), 2026-10-20

**#111 — ALKYL SULFONATE-ESTER TRANSFER recognized** (`experiments/sulfonate_ester_transfer_111.py` + test;
commit `22ea54e`). The 19th attested class: a sulfonyl halide sulfonylating an sp3 ALKYL alcohol O —
`R-OH + R'-SO2-X -> R-O-SO2-R' + H-X` (methyl/ethyl/isopropyl/benzyl mesylate, triflate). Structurally #110's
activated-transfer shape with a SULFONYL electrophile (S(=O)2) rather than an ACYL one (C=O); the donor gates are
mutually exclusive (sulfonyl S vs acyl carbonyl C), so the full 19× no-cross-poach matrix holds.
- *Root-cause class (two-pass adversary):* the FIRST evil-morty pass BROKE the initial cut with three VERIFIED
  false-vouches from a `not-recognizable`→false-VOUCH regression — a loose census counting any O on any carbon +
  any two-=O sulfur (a NON-LOCAL signature, the R48 lesson one alphabet over): (F1) a carboxylic-acid O gave a mixed
  carboxylic-sulfonic ANHYDRIDE vouched as a sulfonate ester; (F2) masked-carbonyl O-nucleophiles (gem-diol /
  hemiacetal / enol — hydrates/tautomers of a carbonyl) vouched; (F3 latent) a dialkyl sulfate / chlorosulfate
  miscounted.
- *Fix:* `_sulfonate_ester_bond_count` now counts only a GENUINE alkyl sulfonate-ester linkage — an sp3
  non-aromatic ALKYL-carbinol carbon (every bond order-1; only heteroatom neighbour the ester O) bonded through O to
  a SULFONATE S (two =O AND its own S-C). This is N-alkylation's proven `_alkyl_carbinol_alcohol_count` lock
  (dalembert KILL 1) applied at the formed O-S locus — representation-robust (reads bond orders, no aromaticity
  model). Soundness lock = census → single O-S cut capped with H-X re-derivation (`resonance_identity` canonicalizes
  resonance NOT tautomers → no enol→keto laundering) → ExperimentStep conservation cert; content-deterministic
  (a forged reaction centre buys nothing).
- *Boundaries:* ARYL-O (a PHENOL sulfonate) is honest `unrepresentable`-class COVERAGE LOSS deferred to the 2.0
  aromaticity model (#105) — a Kekulized aryl carbinol carbon is indistinguishable from an acyclic enol in this
  aromaticity-free graph. N (sulfonamide) / S (thiosulfonate) nucleophiles and the sulfonic-anhydride donor are
  likewise out-of-scope, each a later #111 widening behind its own gate.
- *Measured:* recognizer matrix 15/15, 4/4 alkyl positives recognized, **0 false-vouch**, no poach. The three kills
  + aryl-O retained as PERMANENT regression controls. A SECOND, independent evil-morty pass found no false-vouch
  across the full named attack surface (allyl/propargyl/benzyl/strained/bridgehead carbinols, orthoester/acetal
  clean-carbon tricks, tautomer masks, bundled multi-bond steps, donor-gate & sulfonate-S census slips,
  charge/radical/kekulé representation tricks, cross-poach both directions). Full OOM-safe suite green (7623/0).

## Coverage impact so far

**Floor hardened first (Rounds I–III):** no forged-centre false-VOUCH (#126), no centre-equality mislabel (#128), no
green UNATTESTED (#129), no phantom self-supply when rank-flat providers land (#124), ALL 17→18→19 recognizers
content-deterministic + closed-shell-sound (#132). **Coverage now moving (Round IV + 1.5 Wave C):**
- **Newly RECOGNIZABLE:** activated acyl transfer (#110) — the 18th class — flips the already-generated anhydride/
  acyl-halide O/N/S acylation routes (incl. the paracetamol-via-Ac2O litmus) from demoted-as-fiction to VOUCHED;
  and ALKYL sulfonate-ester transfer (#111) — the 19th class — the cheap recognition win (mesylate/tosylate/triflate
  activation of alkyl alcohols), adversary-hardened against three false-vouches.
- **Newly SEARCHABLE (opt-in, demonstrated):** the lateral [3,3]/electrocyclic families via
  `lateral_search.lateral_route_to` (Cope/Claisen/6-pi), oracle-vouched end-to-end and now centre-free (#132).
The remaining coverage expansion lives in Phase 2 (the Tier-0 infra walls #104–#109/#125 and the recognizer/grammar
tiers #111–#123), characterised in `REACTION_ALGEBRA_COVERAGE_AUDIT_2026-10-12.md`.

## Remaining (by directive priority)

- **P0 soundness/infra (open):** #104 (W1 rank redesign), #105 (per-atom charge rail), #106 (radius-1 centre
  context), #107 (catalyst/activator ledger), #108 (organometallic elements), #109 (latent-fiction audit),
  #125 (scission arity vs intramolecular).
- **P1 (open):** #127 (result-cap starvation — a measurement task), #131 (typed oracle outcomes vs
  internal-error conflation — observability).
- **P2 (open):** #130 (stereo-aware route identity).
- **Chemistry tiers (gated on the infra):** #110–#123.

## Next most discriminating step

`#131` (typed recognition outcomes) is the cheapest remaining truthfulness win and extends the oracle work
directly. The highest *coverage*-unlocking step is `#106` (radius-1 centre context) or `#105` (charge rail),
each of which gates whole families; both are architectural and will be scoped with their own soundness gates.
