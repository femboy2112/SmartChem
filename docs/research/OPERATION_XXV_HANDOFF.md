# OPERATION XXV: handoff (the general chemical universe)

Three achievements are kept apart throughout; nothing here counts one as another:
- a correct equation or rule;
- a certified execution;
- an empirically validated physical prediction.

Claim labels: CORROBORATED (two independent routes agree), OBSERVED (one clean run), CONJECTURED, UNVERIFIED,
DISCLOSED (stated limitation), DARK (not examined), REFUTED.

## 1. Coordinates

| | value |
|---|---|
| start `main` | `11d05bb7b17fd3546b45c329e08dadbfb2dcb79b`, CI run `42453785359` 9/9 |
| production release at start | `v1.6.0` → `ac8bdde03893da8522efba04929da3fe29aa62a1` (unchanged by this operation) |
| PR #164 (post-3.0 explorer milestone, docs only) | merged as `39f1479c80d2a0ea5be5e2d651ff93d0fb6d0641` at 2026-11-08T10:40:56Z; merge tree `a0e4ac7` equals the tested head tree; PR CI 9/9 on `7eae7b4`; main CI run `42472451045` 9/9 |
| research branch | `research/operation-xxv`: PR #167, merged as `3a1c46f62d1f1d925ebb82ac02e72ea5f67ce141` at 2026-11-08T19:58:56Z (`--match-head-commit 0717085`). The merge tree `727031ce…` equals the tested head tree. PR CI run `42481486695`: 9/9 on `0717085`. First `science.yml` run `42481486906`: success. Main CI run `42517734963`: 9/9 on `3a1c46f` |
| issue filed | #168: the SMILES parser and `resonance_identity` merge cyclooctatetraene bond-shift isomers (pre-existing, repo-wide) |
| production branch | `feat/1.7-dehydration-116-r2` (pushed, unmerged): **1.7.0 DEFERRED**. See §5, §13 and [`V1_7_DEHYDRATION_DEFER.md`](V1_7_DEHYDRATION_DEFER.md) |

Research commits (linear, in order):

| commit | content |
|---|---|
| `1502250` | preregistration rules frozen (pushed before the model existed) + Phase I-A coverage gap map |
| `284eac7` | #130 identity-carrier design and characterization controls |
| `85c406d` | reactive spatial grid, exact solid/grain ledger, measured numerics |
| `e91711b` | #165 typed standard-state verdict + #166 science-reproduction workflow |
| `135d294` | renderer-neutral `ExplorationSpec` / `ExplorationReceipt` prototype |
| `b5ea153` | P&B 1982 temperature law, generic Henry boundary, open-air calcite world |
| `5523561`, `775ae10` | red-team repairs: grid and particles |
| `7a7ecdb` | red-team repairs: science receipt, junit checker, calcite ladder |
| `297b7f1` | open-calcite live PHREEQC verification designated as a science test |
| `7522711` | red-team repairs: holdout instrument (controls first, INVALID, typed C3/C4, pinned runner) |
| `312fb0a` | §9 pin addendum (pushed before the run) |
| `0168bf3` | holdout result |
| `ee24b10` | verification result regenerated under the pinned model digest |

Toolchain: CPython 3.12.3, numpy 2.5.1, scipy 1.18.0, phreeqpython 1.6.2 (dev venv only).

## 2. Defects found by adversarial review, and their status

Four independent attackers were used, each with a separate responsibility (Phase VII):
- numerical physics: grid, particles, ladder, science receipt;
- scientific provenance: the holdout model and runner, before the pin;
- chemical algebra: the 26th class. There were five attacks; four reported and one report was lost (§5,
  `V1_7_DEHYDRATION_DEFER.md`);
- integration: **no dedicated release-gate reviewer ran**, because the candidate failed the chemistry gate first
  (§13). Attacks 4 and 5 did check default-grammar byte-identity against 1.6.0 and digest determinism under
  PYTHONHASHSEED.

| finding | severity | status |
|---|---|---|
| a foreign `ADMITTED` receipt could ride a SYNTHETIC grid frame | HIGH | REPAIRED (`5523561`), regression test |
| continuation from a forged `final` state injected 1 mol with identity unchanged | HIGH | REPAIRED: start re-derived, start state bound into identity |
| measured-validation lane passed on ancestry alone (root SHA, `HEAD`, the run commit) | MEDIUM | REPAIRED (`7a7ecdb`): full-SHA strict ancestor, PENDING entry at the prereg commit, sha-matched evidence added after it, verified FAIL wins |
| a missing pinned-bytes report left the live lane at PASS | MEDIUM | REPAIRED |
| a legacy-basis result relabelled by `replace(spec=…)` reported formula-domain validity | MEDIUM | REPAIRED: identities bound to the spec; rung 1 re-checked from frames for closed phases |
| positivity HELD for a trace species 40× below its own inventory | MEDIUM | REPAIRED in the grid (negative feeds refused; resolution-limited segments refused). Kernel floor left as a pinned known gap: changing it breaks an XXII contract test |
| nucleation under a "dissolution" label | MEDIUM | REPAIRED: label derived from a validated law |
| holdout runner had no INVALID path and printed a verdict when a control failed | HIGH | REPAIRED before the pin (`7522711`) |
| C3/C4 controls not expressible; 25 °C Davies A unchecked by the temperature discipline | HIGH / MEDIUM | REPAIRED: typed controls; every T-dependent quantity T-tagged and checked |
| measured interval not bound to the transcription; runner code unpinned | MEDIUM | REPAIRED |
| anti-Bredt alkenes (adamantene, cubene, …) vouched by production and witness alike | HIGH | REPAIRED (`bdd2bd7`): positive safe-set |
| rearrangement-prone substrates vouched (cyclobutanol, cyclopropylcarbinols, pinacol) | MEDIUM | REPAIRED: positive safe-set |
| coproduct-producer digest bound names, not identity or order | MEDIUM-LOW | REPAIRED: closed producer set, canonical order |
| 8 further LOW findings (mutable spec containers, mixed meshes, commutator ignoring the source term, solids through boundaries, duplicate valves, tier inflation, silent Fraction rounding, junit shapes) | LOW | REPAIRED |

Still open, all DISCLOSED:
- **Kernel positivity floor.** It is absolute (1e-10 mol) and does not scale with a trace inventory. The grid now refuses such segments.
- **In-process trust boundary.** A temperature tag is checked, not believed; frames are not re-integrated, so `replace(result, frames=…)` is undetected; numpy/scipy are not bound by the running-code check.
- **Kernel continuation** carries per-segment boundary-flux state, so re-cutting a schedule with a boundary differs at 2e-13 mol.

## 3. Phase I — compiler / decompiler coverage

- **Inventory (introspected live, `experiments/coverage_gap_map_xxv.py`).** 25 classes @ `d9f7e867e8f1a1d2` at start, and four algebra profiles. 14 issues from the 2026-10 audits were already solved and are not gaps. 17 gaps remain, classified into the seven categories (machine-readable: `experiments/coverage_gap_map_xxv.json`).
- **New family (#116, dehydration slice).** See §5.
- **Route invariants (pinned on the DEFERRED branch only; not on `main`).** Three invariants that had no test are
  pinned in `tests/test_route_invariants_xxv.py` on `feat/1.7-dehydration-116-r2`:
  - the same precursor listed in both `available` and `commodities` is one supply;
  - "an ancestor that is also stock" is unreachable in all three searches, because a stocked node is never expanded (the
    ISSUE-124 guard's second half never changes an outcome);
  - default-grammar `coproduct_events_truncated` reports INCOMPLETE.

  They are production-agnostic, and porting them to `main` alone is a cheap follow-up.
- **Multi-step route through the public API (deferred branch).** `search_event_routes` with dehydration enabled finds a
  2-step route in both orders, COMPLETE, while the default grammar finds 0. The demo target changed twice, and both
  changes are recorded:
  1. allyl acetate from 1,3-propanediol left the safe set at attack 3;
  2. but-3-enyl acetate from butane-1,4-diol was itself a false VOUCH at attack 4, because acid gives THF;
  3. the current demo is ethyl crotonate from 3-hydroxybutanoic acid + ethanol.

  Hostile counterparts: no stock gives no route; dehydration plus its inverse cannot manufacture stock (the coproduct
  budget never resets); under (M) dehydration cannot chain down one lineage. None of this is on `main`, because the
  class is deferred (§5).
- **#130 identity (design + controls, `IDENTITY_CARRIER_DESIGN_XXV.md`).** Route terminals and stock are constitution-only (enantiomers and isotopologues merge). **New finding (CORROBORATED, two readings):** an *unmarked* stereogenic element reads `configuration_complete=True`, the same identity class as an achiral molecule. This is latent today, but a #130 implementation must not trust that flag. No 1.x semantics changed.
- **#105 (per-atom charge).** Not started. Recorded as a digest-migration prerequisite.

## 4. Phase II — provenance and certification

- **#165.** A typed `StandardStateVerdict` is derived from params; it cannot be supplied by a caller.
  - The API default for new scenarios is now `converted_to_molar`. Legacy replay passes `as_tabulated_molal` explicitly and keeps its frozen numbers.
  - The four-rung ladder is computed. A legacy result reports `WITHIN_DECLARED_FORMULA_DOMAIN` False with reason `LEGACY_REPLAY_BASIS_MISMATCH`.
  - Live PHREEQC (dev venv): molar basis −0.0070%, legacy +0.298% (model-vs-model).
- **#166.** `.github/workflows/science.yml` is a separate workflow:
  - full history, Python 3.12, a hash-locked phreeqpython 1.6.2 install;
  - vendored and installed database bytes verified before and after the tests;
  - designated science tests that may not skip (72), and a sandbox floor (1539);
  - expected-red mutation controls, and a manifest guard against quietly lowering counts;
  - a four-lane receipt: production compatibility, sandbox numerical, live reference solver, measured validation. A skip yields UNVERIFIED, never PASS.
  - **It has not run on GitHub before this branch's pull request.** Its first hosted result is recorded in §12.

## 5. The 26th class: alcohol dehydration (#116) — DEFERRED

Full record: [`V1_7_DEHYDRATION_DEFER.md`](V1_7_DEHYDRATION_DEFER.md). In brief:
- **Representation (kept; reusable).** Dehydration is rank-INCREASING, so W1 bars it from every TransformProvider.
  It lives in the type-3 lane of `search_event_routes` behind a closed, identity-matched `coproduct_producers` set.
  The default grammar, receipt and result digests stay byte-identical to 1.6.0; this was pinned and re-verified by two
  adversaries.
- **Recognition (not shippable).** There were four successive implementations. The last one has three parts: a
  molecule-wide heteroatom whitelist (M), radius-1 ring saturation (R), and no sp neighbour (S). It is backed by an
  independent witness whose (M)/(R)/(S) a separate author wrote from the spec alone.
- **Attacks.** Four blind attacks reported; a fifth report was lost and is not counted. Every reported attack found
  false VOUCHes that production and the witness agreed on (common-mode).
  - The heteroatom census leaked one bond further out each time, until (M) went molecule-wide.
  - The last attack then found **carbon-skeleton** hazards inside the declared domain, and the ledger cleared every one
    under conc. H2SO4: Friedel–Crafts cyclialkylation, Nazarov / indanone cyclisation, intramolecular
    hydroalkoxylation, aromatic-tautomer rings at radius 2, and acid-labile esters.
- **Decision.** By the stopping rule written before that attack, 1.7.0 is deferred rather than repaired again.
- **Lesson.** Acid-dehydration outcomes are carbocation chemistry over the whole skeleton, so no bounded-neighbourhood
  recognizer can certify them (the R49–R55 theorem, now shown in a production candidate). The successor options
  (scaffold whitelist by name; type-only re-scope with the ledger never clearing; a carbocation-fate model) are the
  maintainer's decision.

## 6. Phase III — the measured holdout

- **Source.** Guidone et al. 2025, *RSC Adv.* 15, 38762, Table 1. [Ca]tot = (5.79 ± 0.27) × 10⁻⁴ M (2σ),
  22 ± 2 °C, under air. Read by two independent readers who agree on every value. pCO₂ was **not measured**; the
  replicate count is not stated.
- **Physics built for it.**
  - The Plummer & Busenberg (1982) temperature laws (Kc, K_H, K₁, K₂, CaHCO₃⁺, CaCO₃°), checked coefficient by
    coefficient against the vendored databases.
  - A generic, ledgered gas–liquid boundary, shown on CO₂ and O₂.
  - An open-air calcite world.
  - Every T-dependent quantity is T-tagged and checked.
  - Allowed-grid PHREEQC agreement: 0.07–1.7% in Ca, growing with ionic strength (Davies vs Debye–Hückel;
    model-vs-model).
  - The Kell density was checked against tabulated values (≤ 3e-6).
- **Preregistration** (`OPERATION_XXV_PREREGISTRATION.md`).
  - The rules were pushed (`1502250`) before the model existed; the model and runner pins were pushed (`312fb0a`)
    before the run.
  - A PHREEQC proxy computed before registration is disclosed.
  - Five instrument defects found by the pre-pin review were repaired before the pin.
- **Result (`0168bf3`): PASS.**
  - Controls: C1 FAIL_HIGH, C2 FAIL_LOW, C3 REFUSED (seven slots), C4 REFUSED, all as predicted.
  - P = [5.328, 6.005] × 10⁻⁴ M against M = [5.52, 6.06] × 10⁻⁴ M.
  - The nominal point is 5.716 × 10⁻⁴ M (−1.28%).
  - d ln Ca/dT = −1.63 %/K; pCO₂ exponent 0.339.
  - Secondary comparisons carry no verdict weight. Model [HCO₃⁻]+[CO₃²⁻] = 1.116e-3 against measured
    1.21 ± 0.10e-3. Model pH 8.198 against measured 8.3 ± 0.1, i.e. 0.002 below the band.
- **Why it passed.**
  - Not a shared fit: no constant was fitted to these data.
  - Partly a broad band: T ± 2 °C dominates; only a model about 15% high or about 40% low could fail.
  - The point prediction agrees to 1.3%, *conditional on an assumed outdoor pCO₂*.
- **Meaning, fixed before the run.** CORROBORATED (weak, tier W). It **cannot** satisfy the 2.0-alpha gate. The
  registry records qualified false.
- **Other candidates.**
  - Kline / Frear & Johnston 1929: ACCESS-GAP on its method and precision, and already contaminated by XXIV's
    exploratory comparison.
  - P&B's own data: DISQUALIFIED (common-mode).
- **Phosphate / Pitzer (III-D).** UNVERIFIED.
  - pitzer.dat's Na–HCO₃ entries (β₂ = 8.22) are Appelo (2015) refits coupled to the calcite analytic, fitted with
    Ellis 1959 and P&B 1982 data (read in the file header). They are not HMW-1984 values.
  - No source-complete phosphate model could be built, so no interaction was improvised.

## 7. Phase IV — the reactive falling-sand world

- **Engine.** `reactive_grid_xxv.py` is one chemistry-independent reaction–transport engine on the general kernel.
  - It has per-species typed conductance: SYNTHETIC, or DERIVED as k = D·A/dx from a stated D with an input tier.
  - It supports synthetic reversible mass-action reactions, always labelled SYNTHETIC, with exact E·N = 0 at
    construction.
  - Walls, valves, sources and sinks are ledgered.
- **Verified against an independent reference.**
  - It matches an independent `expm` reference, which has its own face enumeration, to 1.4e-10.
  - Splitting orders on a non-commuting grid: Lie 1.08, Strang 1.97. The commuting control is exact, so the test is
    calibrated.
  - Spatial convergence of the finite-volume diffusion decay rate is O(dx²): measured order 2.000 at N = 64. This is a
    property of the discretization, not validation.
  - Fixed points, analytic one-face transfer, antisymmetry, mirror symmetry, walls, valves, deterministic replay and
    exact continuation are all checked.
- **Particles (`particles_xxv.py`).**
  - Grains are an exact `Fraction` projection of per-cell solid inventory.
  - An `ILLUSTRATIVE_GRANULAR_AUTOMATON` (not calibrated granular physics) moves whole quanta as ledgered transfers.
  - A grain without inventory is refused.
  - Dissolution is SYNTHETIC first order; no nucleation or precipitation is invented.
  - Fuzzing (400 grids × 6 sweeps) found 0 violations.
- **Not yet.**
  - Sourced reactive chemistry inside the grid: the sourced calcite law produces charged ions, and grid transport of
    charged species is refused.
  - Calibrated granular dynamics.
  - A gas boundary in the grid.
  - A non-linear independent reference.

## 8. Phase V — LibGibson and the explorer

- **Wire.** LibGibson wire v1 FIELD is unchanged (checked at `a0a36d17`). SmartChem's producer-side frame
  (`xxv-reactive-grid-frame-v1`) carries per-quantity unit/identity/kind, face-centred valve state and flux,
  receipts and digests. The concrete loss list was posted to libgibson#290
  (issuecomment-6721525886). **No integration is claimed.**
- **Explorer.** The post-3.0 milestone is merged on `main` (#164). The P1 renderer-neutral `ExplorationSpec` /
  `ExplorationReceipt` prototype binds production digests and keeps seven separate verdict axes, with no aggregate.
  INCOMPLETE is never IMPOSSIBLE. Configuration and isotope identity layers are refused, citing #130.

## 9–11. Theorem, surviving hypothesis, refuted hypothesis

- **Strongest verified invariant.** The measured-validation lane cannot report PASS unless all of these hold:
  - a full-SHA preregistration is a strict ancestor of both the run and the evidence;
  - the registry *at* that commit already held the id as a qualified PENDING entry;
  - the evidence bytes match;
  - the tier is not W.

  This was verified against real temporary git repositories, with calibrated tests. On the physics side, the grain
  ledger's Σgrains·q + Σresidual = Σn holds exactly in rational arithmetic at every frame.
- **Best surviving hypothesis (CONJECTURED, with its truth debt).** The P&B-constant open-system calcite model with
  Davies activity predicts calcite solubility in air within about 2% at 20–25 °C. The debt to pay:
  - a holdout with **measured** pCO₂ and replicates;
  - an ionic-strength regime above 0.01, where Davies and Debye–Hückel diverge;
  - an independent temperature series.
- **Most consequential refuted hypothesis.** "A conserving, witness-agreed dehydration is a real reaction." It was
  refuted by adamantene and cubene, which were vouched by production and witness together. A shared class definition
  makes the witness blind exactly where the definition is. Its successor was also refuted, by attack 5: "a
  molecule-wide heteroatom whitelist makes acid dehydration certifiable". The carbon skeleton decides the
  carbocation's fate (cyclialkylation, Nazarov, hydroalkoxylation).

## 12. CI / test matrix

Hosted (recorded after the merge):
- **PR #167 head `0717085`.** `ci.yml` run `42481486695`: 9/9 success. This covers `test (3.10)`, `test (3.12)`, the
  wheel matrix on 3.10–3.13, the PySCF smoke and both sandbox jobs.
- **First `science.yml` run `42481486906`: success.** Every step succeeded, including the pinned database bytes before
  and after the tests, the expected-red one-flipped-byte control and the four-lane receipt. The lane-level verdicts
  were not read back for this record. Whether the XXII-6b cross-machine byte check ran inside it is UNVERIFIED.
- **Merged `main` `3a1c46f`.** `ci.yml` run `42517734963`: 9/9 success.

Local runs (dev venv; a superset of the CI venv, so these are not CI results):
- **Integrated sandbox suite.**
  - At `135d294`: 1444 passed, 0 failed, 0 skipped. This predates the red-team repairs; every repaired file's tests
    were rerun by the registrant after each hand-back.
  - At the merged head `0717085`: 1562 passed, 0 skipped.
- **Full OOM-safe production suite (`scripts/run_suite.sh`) on the dehydration branch.**

  | commit | collected | passed | failed | skipped |
  |---|---|---|---|---|
  | `cee2ab3` | 8417 | 8367 | 0 | 50 |
  | `00c6a64` (version bump + goldens) | 8572 | 8522 | 0 | 50 |
  | `8796ee3` (fourth implementation) | 8645 | 8595 | 0 | 50 |

  The branch is code-green; the deferral is about chemistry (§5).
- The holdout receipt records its own environment: a fresh interpreter, an empty bytecode cache, and the running code
  bound to the pinned digests.

## 13. Release status (updated after the merge, 2026-11-08)

- **Production 1.6.0.** RELEASED, unchanged. The tag never moves. This branch changes nothing under `smartchem/`,
  `pyproject.toml` or `MANIFEST.in`.
- **Production 1.7 candidate.** DEFERRED. Nothing was tagged, built for release or published. The candidate
  (`feat/1.7-dehydration-116-r2`, fourth implementation `8796ee3`) failed the no-false-VOUCH gate on the fifth blind
  attack. That triggered the stopping rule declared before the attack (§5,
  [`V1_7_DEHYDRATION_DEFER.md`](V1_7_DEHYDRATION_DEFER.md)). The branch carries an unreleased 1.7.0 version bump and is
  kept for the record and for a successor design.
- **Research 2.0-alpha.** NOT MET. The only measured holdout is tier W (pCO₂ unmeasured, replicates unstated); this
  was declared before the run. The API is also not installable (research source only).
- **2.0 stable.** Not started.
- **Spatial 3.0.** A research prototype, advanced: it reacts (SYNTHETIC kinetics), has an exact particle ledger, and
  verified numerics. Not accepted: no sourced reactive chemistry in the grid, an illustrative granular automaton, and
  the LibGibson wire gap.
- **Post-3.0 LibGibson synthesis explorer.** PLANNED. The milestone is on `main` (#164). A P1 renderer-neutral schema
  prototype exists, but no explorer.

## 14. Next three verdict-changing probes

1. **A calcite holdout with measured pCO₂** (a controlled-atmosphere series, or the authors' raw pCO₂ and replicate
   data). It is the only visible path to a qualifying 2.0-alpha measurement.
2. **Stereogenic-element perception independent of SMILES marks**, calibrated against an independent oracle. It
   blocks any honest #130 implementation.
3. **The dehydration successor design** (maintainer decision; §5 options). Whichever option is chosen, its first
   probe is the same: replay all five attack corpora against it before any new adversary runs.
