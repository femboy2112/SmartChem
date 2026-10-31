# OPERATION SMARTCHEM XII — scientific hardening of the 1.5 candidate (2026-10-31)

A hostile scientific review of the CI-green 1.5 release candidate (PR #149), repairing claims that are not
scientifically universal. This record is **append-only** relative to the 1.5 consolidation dossier
([`V1_5_CONSOLIDATION_2026-10-30.md`](V1_5_CONSOLIDATION_2026-10-30.md)), which stays a dated record of what was known
on 2026-10-30; the corrections below revise specific conclusions and say so explicitly.

> **Reviewable work on the candidate branch `integration/v1.5-candidate` (PR #149). Nothing is merged into protected
> `main`, tagged, or published.** The release remains the production 1.1.0 (`main` `9e8fa5f`, tag `v1.1.0`).

## Coordinates

- Branch `integration/v1.5-candidate`; baseline this round began at `55a44c6` (the 1.5 candidate, all §4 gates MET).
- `9e8fa5f` (= released `v1.1.0`) is an ancestor; `main` is untouched.
- Commits this round (newest last): `75c0119` (1A), `1c46279` (1B), `5c29f70` (1C), `18469fa` + `33bfacf`
  (P0 docs + §2 DAG trust matrix), `c2331c2` (P1 event-type certificate).

## P0 — hostile scientific review (§1 of OPERATION XII)

### 1A — the universal transition-metal hydrogenation requirement was scientifically false (REPAIRED · `75c0119`)

**Claim refuted.** The activator ledger stamped EVERY recognized hydrogenation with a universal
`TRANSITION_METAL_CATALYST` requirement (its docstring asserted "a UNIVERSAL requirement"). That is false for the
nitrogen-unsaturation subdomain: metal-free frustrated-Lewis-pair (FLP) catalysts catalytically hydrogenate **imines
(C=N)** and lone-pair-sequestered **nitriles (C≡N)** — Chase, Welch, Jurca & Stephan, *Metal-Free Catalytic
Hydrogenation*, Angew. Chem. Int. Ed. **2007**, 46, 8050–8053, DOI [10.1002/anie.200702908](https://doi.org/10.1002/anie.200702908)
— and explicitly **not aldehydes** (C=O reacts only stoichiometrically). Source read and substrate domain confirmed
before any code change.

**Direction.** The ledger is a demoter; the defect was a false *reason / false universal* ("only a transition metal
can"), not a false-VOUCH. The repair stays on the feasibility axis.

**Repair.** The requirement is split by the reduced bond, keyed on the step (mirroring the existing SN2 pKa-regime
precedent), so hydrogenation moves from the class-keyed `REQUIRED_ACTIVATORS` to `_conditional_required_roles`:

| reduced bond | required role | cleared by |
|---|---|---|
| genuine imine (C=N) / nitrile (C≡N) | `HYDROGEN_ACTIVATION_CATALYST` (new) | a transition metal **or** a metal-free FLP (`B(C6F5)3` / `BCF` / tris(pentafluorophenyl)borane) |
| C=C / C=O / C≡C / indeterminate | `TRANSITION_METAL_CATALYST` | a transition metal only (fail-closed to the narrower set) |

- The metal-free whitelist is **disjoint** from the transition-metal set and case-certified (no arbitrary text label
  clears), so a C=C / C=O hydrogenation is **never** cleared by an FLP — the module's named unsafe direction
  (false-CLEAR) stays closed by construction. A transition metal clears the imine/nitrile case a fortiori.
- The recognizer is behavior-identical (the bool recognizer is now "the reduced-bond witness is not None").
- New import-time guard protects the step-conditional class anchors (SN2, hydrogenation) against a silent
  rename-disarm.

**Adversarial re-attack (evil-morty, read-only).** Five of six attack vectors held (verified). One **false-CLEAR**
found and **repaired in the same round**: keying on the reduced bond's element pair `{C,N}` was too coarse — an
**oxime** (C=N–O), **hydrazone / azine** (C=N–N), **amidine / guanidine** (the C=N carbon bearing a second N) and the
**isocyanate / carbodiimide cumulenes** (the carbon carrying a second multiple bond) all reduce through a C=N yet are
not metal-free-FLP substrates. Replaced the element predicate with a structural witness
(`hydrogenation_reduces_imine_or_nitrile`) that reads the reduced bond's *environment* and excludes all five; locked by
regression tests.

**Residual boundary (honest, Problem B).** The catalytic FLP turnover classically needs a *sterically hindered* imine
(unhindered imines run B(C6F5)3-mediated); the constitution-only graph cannot represent sterics, so the vouch stays the
existential Problem-A claim "a metal-free catalytic hydrogenation of an imine/nitrile of this constitution is
experimentally established", not a feasibility claim for a specific substrate.

### 1B — the SN2 recognizer over-claimed a mechanism constraint (REPAIRED · `1c46279`)

**Claim corrected.** A graph rewrite cannot establish a reaction *mechanism*. The `_sn2_substitution` docstring claimed
the radius-1 carbon gate "supplies the MECHANISM constraint". Corrected: the gate supplies **SN2-COMPATIBILITY** (a
necessary structural condition — sp3, non-tertiary, single-heteroatom, halide LG), excluding the structural impostors
(SNAr / vinylic / acyl / tertiary-SN1 / oxocarbenium). It does **not** resolve the SN1/SN2/E2 competition
(solvent/kinetics-dependent, unrepresented) and mints **no** stereochemical (Walden-inversion) claim (the
constitution-only `Molecule` carries no configuration; the CLI `--match-layer configuration` is refused until stereo
perception exists). IUPAC Gold Book terms `SN2` / `bimolecular`.

**Scope.** Documentary + one boundary test; no wire rename, recognizer registry digest `0dfb95140ad927ef` untouched,
golden NO DRIFT. Independently confirmed nothing downstream mints a stereochemistry or SN1-vs-SN2 claim. The vouch is
the oracle's standard existential "a mechanism of the SN2 TYPE is structurally available"; a secondary substrate (where
SN1/E2 compete) still vouches, because SN2 is a structurally available mechanism there — the vouch does not claim it
wins.

### 1C — the oxygen base-regime classifier calibrated against a preregistered corpus (VERIFIED SOUND · `5c29f70`)

**Claim corroborated (no code fix needed).** `sn2_oxygen_base_regime` keys on the **hydroxyl carbon's own** order≥2
bond, so a C=C / C=O *near but not on* it does not relax the base requirement. Verified against a preregistered
source-backed corpus + hostile holdouts, now locked as tests:

- positive: carboxylic acid (pKa 4.76), phenol (9.95), enol (~10.5) → `mild`;
- the positional discriminators a naive "any unsaturation → mild" rule would false-CLEAR:
  **enol** (C=C *on* the OH-carbon → mild) vs **allyl alcohol** (C=C *near*, pKa ~15.5 → strong) — same bond, opposite
  regime; carboxylic acid (C=O *on*) vs **β-hydroxy carbonyl** / glycolaldehyde (C=O *near* → strong); **1,2-diol**
  (poly-ol, ambiguous nucleophile → fail-closed strong); the **C=N iminol** (amidate-level pKa ~17–22 → strong, the
  prior evil-morty exclusion).
- Every `strong` holdout stays demoted under a mild base (K2CO3 / NaOH / Et3N / DBU) — the unsafe false-CLEAR direction
  is closed. The `mild` whitelist tops out at conjugate-acid pKa ~10.5 (carbonate), so only sub-11 acids clear mild.

## P0 — DAG admission trust boundary (§2 of OPERATION XII · VERIFIED + DOCUMENTED · Outcome A)

DAG-ADMIT-02 (Candidate A, PR #144) re-derives convergent-DAG reaction recognition from the thick `replay_payload` at
admission, identity-bound to `route_digest`, storing no forgeable recognition field and moving no digest / golden /
schema. `fit_status` keeps its pure physical/process/composability meaning; only ADMISSION carries the recognition
tier. The remaining thin-wire boundary is real and is now stated plainly rather than presented as strong verification
(the plan's **Outcome A** — preserve Candidate A, expose + document its trust tiers):

| transport / policy | replay | recognition | admission tier | proven by |
|---|---|---|---|---|
| in-memory / default `CANONICAL_VERIFIED` wire | present | re-derived + identity-bound | **VERIFIED_ADMISSIBLE** | `test_recognized_fits_dag_is_admitted`; `test_gate_does_not_move_result_digest_or_break_round_trip` |
| unrecognized steps (with replay) | present | fails | **WITHHELD** | `test_unrecognized_fits_dag_is_withheld_from_admission` |
| substituted / forged replay | present | identity-bind fails | **WITHHELD** | `test_substituted_replay_cannot_buy_admission` |
| explicit `THIN_ADVISORY` opt-out, plain load | absent | unverifiable | **ADVISORY_ONLY** (admitted on `fit_status`; not a false "impossible") | `test_missing_replay_is_advisory_on_plain_but_refused_under_verified_admission` |
| any no-replay FITS DAG under `require_verified_admission` | absent | unverifiable | **REFUSED** (the strong guarantee) | same; `test_onload_rederivation`; `test_v0_9_5_loader_laws` |

**Acceptance (met):** no forged or unrecognized DAG becomes VERIFIED-admissible, and the recognized positives
(paracetamol via Ac₂O) keep working across a thick round-trip (`result_digest` / `admissible_dag_digests` /
`process_selection_status` byte-identical). `admissible_dag_digests` on a *default* load is **advisory-tier** for a
no-replay DAG and must not be read as verified chemistry; a consumer needing the strong guarantee loads under
`require_verified_admission`. The new `test_trust_mode_matrix_advisory_admission_is_distinguishable_from_withheld`
restates the tiers as one legible artifact.

**Outcome A, not B.** A fully fail-closed-on-every-plain-load gate would need a versioned stored-recognition facet
(`schema_version` bump + golden re-freeze + operator sign-off) — the deferred, review-only Candidate B. The shipped
re-derivation is the weakest sound repair that closes the production / default-transport hole with no wire-identity
move; nothing here changes `fit_status` meaning.

## P1 — event-type certificates (`classify_event`; VERIFIED + REPAIRED · `c2331c2`)

The #123 bounded typed-event search (`smartchem/experiment/event_search.py`) classifies every search step into
one of three `EventType`s via `classify_event`. P1 makes that classifier a genuine **certificate** of each
class's asserted invariants — the RECOGNITION projection — independent of how the step was produced (the search
grammar, the REACHABILITY projection).

**Claim refuted (false label).** `classify_event` returned `SCISSION` on `len(step.reactants) >= 2` **alone**.
The `SCISSION` class asserts ">=2 **strictly-smaller** fragments" (the inherited W1 rank-descent), but that rank
property was checked only in a test helper (`_is_monotone_and_hop_bounded`), never in the recognizer. A real
conserving 2→2 step whose principal reactant exceeds the target — ester hydrolysis, methyl acetate (11 atoms) +
water → acetic acid target (8) + methanol — was therefore mislabeled a rank-descending assembly.

**Repair.** The `SCISSION` branch now certifies `all(len(r.atoms) < len(target.atoms) for r in reactants)`,
fail-closed (`EventClassificationError`) otherwise. Grammar-safe by construction: `structure_descent.py` W1
(every capped-scission fragment strictly smaller than the parent, lines 300 / 642–643) guarantees the predicate
holds for every step the default `CappedScission`-only registry produces, so `event_type_counts()` never raises
on real search output. **Connectedness needs no check** — a `Molecule` of >1 atom is one connected species by
construction (`category.py:790`), so the single-precursor branches (`CONNECTED_LATERAL` / `INTRAMOLECULAR_COPRODUCT`)
already guarantee "one connected precursor" from `arity == 1`; adding a connectedness predicate would be a check
the type system makes impossible to violate.

**Adversarial re-attack (evil-morty, read-only).** Both claims on trial — (1) grammar-safe / no false-exclude,
(2) no surviving mislabel — **HELD**, verified by code reading *and* a live search over 6 targets / 22 route steps
(zero raised). It surfaced one **residual** (not a break of the invariants on trial, independently reproduced):

**Residual pinned — the `INTRAMOLECULAR_COPRODUCT` certificate boundary.** The type-3 class certifies a **shape**
(one connected principal precursor, rank-larger than the target, expelling ≥1 coproduct); it does **not** certify
the *intramolecular* connectivity its name evokes. A genuine intramolecular lactonization (4-hydroxybutanoic acid
→ γ-butyrolactone + water) and an **inter**molecular 1→many fragmentation (retro-Diels-Alder: cyclohexene →
butadiene + ethylene) have the **identical shape**, and no atom-map on a constitution-only `Molecule` separates
them — both classify `INTRAMOLECULAR_COPRODUCT`. A nonlocal (atom-origin) property cannot be proven by a local
shape check. Following the 1B precedent (document the boundary, preserve wire identity — no rename, digest
untouched): the connectivity-preservation property is now stated as the **(P2) producer's proof obligation** (the
generator builds the step from a known intramolecular transform and so carries the atom-map), pinned by
`test_intramolecular_coproduct_certifies_shape_not_connectivity_preservation`. **Hard constraint on P2:** the
lactonization generator must establish intramolecularity itself; it may not lean on `classify_event` for it.

**Scope / gates.** `classify_event` / `event_type_counts` / `EventType` are confined to `event_search.py` (only
tests consume them elsewhere) — zero blast radius into any digest/serialization surface. Golden **NO DRIFT**;
ruff clean; `tests/test_event_search_123.py` 22 passed (19 prior + `test_scission_certifies_w1_rank_descent_not_arity_alone`,
`test_classify_event_recognition_does_not_trust_provenance`, the boundary test above). Full OOM-safe suite on the
P1 tip `01a2183`: **8106 passed / 0 failed / 0 errors / 50 skipped** (collected 8156 = 8152 + the `33bfacf` DAG
matrix test + the 3 P1 regressions), verified two ways (console aggregate + an independent 40-file junit tally,
zero problem batches). Hosted CI run `41187287909` (head `01a21832…`): **conclusion success, all 7 jobs green**
(`test` 3.10/3.12, `Wheel install matrix` ×4, `Optional PySCF backend (smoke)`), per-job + head-SHA verified.

### P1 claim ledger

| claim | status | evidence |
|---|---|---|
| a `SCISSION` is certified by ≥2-reactant arity alone | **REFUTED** (false label) → repaired to certify W1 rank-descent | ester-hydrolysis probe; `c2331c2` |
| the tightened `SCISSION` cert false-excludes a reachable search step | **REFUTED** (grammar-safe: W1 holds for every capped scission) | evil-morty; 6-target run; `structure_descent` W1 |
| `INTRAMOLECULAR_COPRODUCT` certifies the *intramolecular* property its name claims | **CORRECTED** to a shape certificate; connectivity is the P2 producer's obligation | retro-DA counterexample; boundary test |

## P2 — the type-3 `INTRAMOLECULAR_COPRODUCT` generator: intramolecular lactonization (BUILT · `8f2b10f`)

The headline. The `INTRAMOLECULAR_COPRODUCT` event class was DEFINED but had **zero producers** (`CappedScission`'s
≥2-component contract cannot represent a connected 1→1+coproduct event; no lateral family expels a coproduct). This
adds the first real producer, for the lactonization subfamily — a new module
`smartchem/intramolecular_condensation.py`, `retro_lactonization_edges(target)`, which given a lactone emits an edge
encoding the synthesis `hydroxy_acid → lactone + water` (a step `classify_event` classifies `INTRAMOLECULAR_COPRODUCT`).

**Intramolecularity proved AT THE GENERATOR (the P1 hard constraint discharged).** The generator opens only
**in-ring** ester linkages (a bond whose removal leaves the graph connected), so the precursor stays one connected
`Molecule` and the forward condensation closes a bond within it. It is therefore structurally **incapable** of an
intermolecular 1→many fragmentation — a retro-Diels-Alder has the identical type-3 *shape* (which `classify_event`,
shape-only, cannot distinguish) but no ester ring to open, so it yields zero edges. The nonlocal property `classify_event`
could not certify is proven here by the model that has the atom-map.

**Three certificates** (conservation alone proves nothing — every condensation balances mass): (1) conservation via an
independent `Reaction`; (2) the load-bearing forward re-derivation — the precursor is re-scanned for its own carboxyl
and hydroxyl and must lactonize to *exactly* the target + water, compared by canonical identity; (3) the
one-connected-precursor intramolecularity invariant.

**Adversarial review (evil-morty + own probes) broke the first draft; folded in.** Two of three claims were BROKEN by
one root cause — the acyl carbon was never constrained to bear exactly one heteroatom, and a docstring promised a
carboxyl-`OH` exclusion that was absent from the code:

- **Narrowed to true lactones.** Cyclic **anhydrides** (succinic/glutaric/maleic → diacids), **carbonates** (ethylene
  carbonate), and **carbamates** (oxazolidinone) were being opened and mislabeled "lactonization" (genuine condensations
  of *other* families whose precursors are not hydroxy acids). The acyl carbon must now bear exactly one heteroatom
  besides its `=O`; the look-alikes yield zero edges.
- **The missing carboxyl-`OH` exclusion is now enforced**, so a diacid is not read as alcohol+acid; a hand-built
  diacid-precursor edge is refused (the certificate now bears its claimed load).
- **Dedup bug fixed.** Dedup keyed on `repr()` — which is the **formula** string — collapsed distinct same-formula
  isomers and could discard the genuine target lactone (a polyol-lactone false negative). Re-keyed on
  `resonance_identity`; the polyol case is recovered. Claim 2 (intramolecularity / no intermolecular fragmentation)
  HELD throughout, verified.

**Scope.** STANDALONE (not wired into `search_routes` / `search_event_routes`), structural type-validity only
(Problem A). The 24-class oracle has no lactonization recognizer, so it honestly **demotes** the step as unrecognized
rather than false-vouching — the recognition-vs-reachability separation, pinned by a test. **Gates:** golden NO DRIFT
(nothing registered or digested), ruff clean, `tests/test_intramolecular_condensation_p2.py` (21) + the event suite
green; zero blast radius (the module is imported by nothing but its test). Full OOM-safe suite on tip `52596fb`:
**8127 passed / 0 failed / 0 errors / 50 skipped** (collected 8177 = 8156 + 21 P2 tests), two ways (console + 40-file
junit tally, zero problem batches); hosted CI run `41193640463` (head `52596fb`): **conclusion success, all 7 jobs
green**, per-job + head-SHA verified. **Deferred follow-on:** wiring the generator into
the bounded recursive search, with the `(coproduct_events, atoms, lateral_hops)` termination proof for the
rank-INCREASING retro step and a lactonization *recognizer* so the oracle vouches rather than demotes.

### P2 claim ledger

| claim | status | evidence |
|---|---|---|
| the type-3 class has no producer | **RESOLVED** — `retro_lactonization_edges` is the first | `8f2b10f`; `test_lactonization_generator_produces_a_type3_event` |
| every emitted edge is a genuine intramolecular lactonization (hydroxy acid → lactone + water) | **BROKEN → repaired** (anhydride/carbonate/carbamate were mislabeled) | evil-morty; lactone-guard narrowing; `test_non_lactone_acyl_rings_are_rejected` |
| the re-derivation certificate refuses a fabricated precursor | **BROKEN → repaired** (a diacid passed) | evil-morty; carboxyl-`OH` exclusion; `test_diacid_precursor_is_refused_by_rederivation` |
| the generator can emit an intermolecular fragmentation | **REFUTED** (in-ring-only; connected precursor) | evil-morty HELD; `test_generator_structurally_cannot_emit_an_intermolecular_fragmentation` |
| a polyol lactone is silently dropped | **was a `repr()`/formula dedup bug → fixed** (resonance-identity dedup) | trace; `test_polyol_lactone_is_not_dropped_by_formula_dedup` |

## Scientific claim ledger (P0 §1)

| claim | status | evidence |
|---|---|---|
| hydrogenation universally needs a transition metal | **REFUTED** → repaired | Stephan 2007 (DOI above); `75c0119` |
| a C=N element pair implies a metal-free-FLP substrate | **REFUTED** (false-CLEAR) → repaired | evil-morty; structural witness in `75c0119` |
| the SN2 gate establishes the SN2 mechanism / inversion | **CORRECTED** to SN2-compatibility, existential vouch | `1c46279` |
| the O base-regime classifier is fooled by nearby unsaturation | **REFUTED** (classifier is positional) | preregistered corpus `5c29f70` |

## Gates (P0 §1, local, on each commit)

- ruff clean (changed files); targeted suites green (activator 259, SN2 40, hydrogenation/recognizer 52, corpus 4).
- Version-independent payload golden: **NO DRIFT** on every commit (all three corrections ride the feasibility layer
  or are documentary; none moves a search/semantic identity).
- Full OOM-safe suite on code-final `5c29f70`: **8102 passed / 0 failed / 0 errors / 50 skipped** (collected 8152),
  verified two ways (console aggregate + an independent 40-file junit tally, zero problem batches). The one test added
  after it (`33bfacf`'s DAG trust-mode matrix test) verified standalone 7/7.
- Hosted CI on the P0 tip `33bfacf` (= head `33bfacf5445a322cdca804b6e22395d9c221ade9`), run `41181700389`:
  **conclusion `success`, all 7 jobs green** — `test (3.10)`, `test (3.12)`, `Wheel install matrix` ×4 (3.10/3.11/3.12/3.13),
  `Optional PySCF backend (smoke)`. Head-SHA confirmed pinned to the branch tip; per-job conclusions read from the run
  object, not the watcher exit code.

## Remaining (scoped, not yet executed this round)

- **P2 follow-on** — the generator (`8f2b10f`) is standalone; wiring it into the bounded recursive search needs the
  `(coproduct_events, atoms, lateral_hops)` lexicographic termination proof for the rank-INCREASING retro step
  (the coproduct-event budget strictly decreases per hop even as atom count rises — attribute the measure to the
  code that enforces it, not the prettiest certificate), plus a lactonization *recognizer* so the oracle vouches
  rather than demotes the step. Both deferred.
- **P3** — independent imine-condensation witness; elimination via the rank-increasing event rail; aldol scoping.
- **P4** — physicalization (separate 2.0 research branch): mixed acetate/carbonate PHREEQC benchmark; open/sealed gas
  boundaries; conservative chamber transport.
