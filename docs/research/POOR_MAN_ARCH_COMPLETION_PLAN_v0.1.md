# Poor-Man Arch — Completion Plan (v0.1)

> **⚠️ PHASE 0 EXECUTED (R53, 2026-09-12) → outcome: DEFER #4.** The decisive kill-or-continue probe ran, and a
> five-bearing design gate broke the continuous estimator's FEASIBLE set on determinant axes the bounded feature
> set + fail-closed guard can neither read nor decline (acid-side β-keto decarboxylation; α-thioether thionium;
> heteroaryl cation magnitude). The alcohol-side core proved SOUND; the escape is now named (a symmetric positive
> safe-set whitelist on both reaction centers, gated on the R52 base-rate/vacuity question). Zero consumers
> confirmed. **Canonical outcome → [`POOR_MAN_REACTIVITY_ESTIMATOR_PHASE0_DEFER_v0.1.md`](POOR_MAN_REACTIVITY_ESTIMATOR_PHASE0_DEFER_v0.1.md).**
> The sections below are the plan as written BEFORE Phase 0; read them together with that decision doc.
>
> **⚠️ PHASE 0.5 EXECUTED (R54, 2026-09-12) → outcome: DEFER #5 — the escape itself is killed.** Both DEFER-#4
> next increments ran to decision. (1) The **reachability increment is REFUTED**: isopentyl acetate is already
> "reachable" via chemically-BOGUS formula-balanced routes, its one real route needs sourced-INDUSTRIAL isopentyl
> alcohol, and the "gap" is the reactivity wall, not orthogonal to it — no `reagents.py` change. (2) The
> **symmetric positive whitelist was built and gated → DEFER #5**: a five-bearing gate broke its FEASIBLE set on
> ≥3 axes an element-census-over-bounded-radius cannot read (α,β-unsaturation polymerization; remote acid-labile
> past the scan radius, a regression vs R53; 5-ring heteroaromatic guard vacuity); the leak is un-patchable (the
> α,β-unsat patch false-EXCLUDEs feasible crotonic/cinnamic/sorbic — the R52 scissors); base-rate recall
> 0.875→0.574; zero consumers, and UNKNOWN-as-blocker would sink 4 correct targets. Inverting the R53 blacklist
> to a positive whitelist MOVED the collision into the definition of "recognized-inert"; it did not close it.
> **Canonical outcome → [`POOR_MAN_SYMMETRIC_WHITELIST_PHASE05_DEFER_v0.1.md`](POOR_MAN_SYMMETRIC_WHITELIST_PHASE05_DEFER_v0.1.md).**
> The keystone now needs a model beyond ANY bounded-radius reaction-center recognizer (scaffold-by-name +
> saturation clause + a magnitude/ranking axis, or an external oracle), gated on a proven live consumer (still 0).
>
> **Status (original):** TEED UP, not started. The build waits for the user's explicit "go" ("make sure the next
> round is planned and tee'd up for us to start blasting on my go"). This document is the canonical R53 plan; the
> memory index and `ROADMAP.md` point here rather than duplicating it.
>
> **Mandate (user, 2026-09-11, verbatim):** *"we must complete the poor-mans arch, that functionality is a
> mainline feature."* This reopens the poor-man ingenuity arc as a LIVE, must-complete front (it had been a
> verified-defer with "no live front unless the user reopens it" — the user reopened it).
>
> **Provenance:** written after a 4-bearing read-only research pass (2026-09-11, four Citadel-Rick agents at
> HEAD `ddf7190`). Every load-bearing claim below carries an epistemic label (Verified / Observed /
> Conjectured) and the file:line or DOI it rests on. Nothing here is a build decision — the build decision is
> Phase 0's gate.

---

## 1. What "the poor-man arch" is, and where it stands

The poor-man arch is the HUNTING objective ([[poor-man-ingenuity-cursed-but-sound-routes]]): SmartChem should
actively **surface reality-respecting-but-unconventional kitchen routes** — the SmartASM "wtf how — OK it
actually works" analogue — ranked above the boring buy-the-reagent route, gated hard on real chemistry
(conservation + a feasibility signal that actually *measures* reachability), never fabricated, ranking-only.

Component ledger:

| Component | State | Where |
|---|---|---|
| Reachability (tiered stock catalog + reachable recompile) | ✅ SHIPPED R48 (PR #59) | `data/reagents.py`, `feasibility.py` domain guard |
| Catalyst obtainability (kitchen model's catalysis blindness fixed) | ✅ SHIPPED R51 (PR #62) | `experiment/catalyst_availability.py` |
| **The ingenuity REWARD** (the positive signal that surfaces clever routes) | ❌ **VERIFIED-DEFER ×3** (R49/R50/R52) — the missing keystone | — |
| Poor-man ranking / affordability frontier | ◐ partial (Pareto axis live; reward not yet on it) | `service._affordability_frontier`, `affordability.py` |

**"Complete the arch" = build the missing keystone: a SOUND positive feasibility/ingenuity reward, wired to
the affordability Pareto axis, with a proven reachable consumer.** Everything else is in place.

Why the keystone keeps deferring (the three kills, all the same shape): every attempt built the gate by
**classifying a reaction by lookup** — a bounded-radius atom-mapped class key (R50), or an inventory of
out-of-center functional groups (R52). A bounded-radius key cannot carry an unbounded-radius feasibility
envelope, so the class key **collides across the kitchen-reachable boundary** and the reward fires on
unreachable routes (a fabricated capability claim, the exact rubber stamp forbidden
[[a-capability-reward-must-be-gated-on-the-capability-model]]). The escape all three defers named:
**a substrate-reactivity model that MEASURES the determinants**, not a classifier that looks them up.

---

## 2. The 4-bearing research synthesis (2026-09-11)

### Bearing A — soundness of a measuring model → **STILL-UNSOUND as a boolean recognizer (4th collision found)**

- The minimal graph-computable feature set that closes the two *documented* collisions — `{carbinol
  substitution degree, out-of-center competing-nucleophile flag}` — is already prototyped in
  `experiments/poor_man_out_of_center_recognizer_defer_probe.py:106-146` and **has zero production call sites**
  (grep-Verified). It does separate pentyl (1°) / tert-butyl (3°) and pentyl / 5-aminopentyl. *(Verified.)*
- **It re-collides one bond-radius further out.** A **benzylic/allylic secondary** carbinol
  (1-phenylethanol, `_carbinol_degree = 2`, identical to isopropanol which IS a clean kitchen Fischer
  substrate) has a resonance-stabilized cation that makes E1/SN1 side-chemistry compete under Fischer's own
  acid — the tert-butyl failure reappearing at a degree the feature set calls safe, because degree counts
  carbon-neighbor *count*, not *character* (sp²/aromatic). And **acid-side sterics** (pivalic acid) is an
  entire axis no recon round (R48–R52) ever varied — every probe only varied the alcohol. *(Conjectured —
  standard phys-org, not re-computed against the engine; must be a Phase-0 probe before it enters a design.)*
- **The general theorem:** adding functional-group inventory entries does not help — the SAME failure mode
  recurs one bond-radius out (conjugation/aromaticity/acid-side) no matter how many discrete types you
  enumerate. A sound "measure" must read **bond character / hybridization / carbocation stability**, not a
  bigger table. *(This is the R52 lesson [[base-rate-dependent-fail-closed-polarity]] generalized.)*
- **The open fork (decisive for the whole plan):** is the recurrence **unbounded** (infinite regress → a
  boolean recognizer is flatly impossible for Fischer esterification as a class) or **bounded-but-large** (a
  real physical-organic continuous estimator — Taft steric E_s / Hammett σ — that terminates with its own
  domain guard, the `bond_enthalpy.py` [[a-derived-estimate-must-guard-its-domain-of-validity]] pattern)? The
  bearing could not close this; **Phase 0 exists to close it.**
- Bonus finding (probe-only, low priority): the R52 defer-probe flags a second –OH (diol) with the same
  EXCLUDE polarity as an amine — wrong (a diol still gives an ester, just a mixture; a competing amine changes
  the product *class*). Lives only in a defer probe, not production.

### Bearing B — architecture / wiring → **frontier confirmed; a recognizer needs a CARRIER (bigger lift than R51)**

- The enumeration frontier premise holds at HEAD `ddf7190`: the raw transform (`CappedScission` /
  `BondOrderEdit`, carrying the atom-mapped `cut`/`caps`) is in scope as local `cs` at **`routes.py:528-529`**
  (linear) and **`routes.py:763-764`** (DAG), immediately before `ExperimentStep.from_transform` **drops**
  `cut`/`caps` (`step.py:217-245`). This is the ONLY site a substrate-reactivity recognizer can read the edit.
  *(Verified by code read; memory's old "~526" anchor was 2-3 lines stale — corrected here.)*
- **Unlike R51**, which reused an existing *surviving* structured field (`envelope.catalysts`) all the way to
  `_affordability_frontier`, a substrate recognizer's input dies at `from_transform`. So the minimal surface
  is **not** "one module + one line": it needs (1) a recognizer called at the frontier, (2) a **carrier** to
  thread the verdict forward — either (a) a new field on `ExperimentStep`/`STEP_SCHEMA` (`step.py:196-214`), or
  (b) a `route.digest`-keyed side-channel built during enumeration and read in `_affordability_frontier` — and
  only (3) then the R51-style append. *(Verified premise; carrier tradeoff Conjectured — decide at the gate.)*
- **The reward home is settled and structurally enforced:** `service._affordability_frontier` appends blocker
  strings to `hard` (`service.py:~2020`) → `basket_cost_vector(..., hard_blockers=hard)` → `pareto_frontier`
  G6 dominance (`affordability.py`). It never touches the scalar `_score_tuple`/`_physics_ranked_order` — the
  "never the scalar, always the Pareto axis" law is true **by absence of any shared path**, not just by
  convention. *(Verified.)* The recognizer's verdict must land here, ranking-only, fail-closed.
- No Taft/Hammett substituent-constant table exists in `smartchem/data/`; `bond_enthalpy.py`
  (`MEAN_BOND_ENTHALPY_KJ` + provenance + `CALIBRATION` + endocyclic domain guard) is the exact DERIVED-table
  precedent a new one would follow. *(Verified.)*

### Bearing C — reachable-consumer census → **NO consumer for a derived model; ONE shovel-ready consumer for a sourced fact**

- Freshly ran `compile_synthesis(target, reagents=(water,))` over **all 45** registered targets (`structure.py`),
  not just the 3 the committed census probe hard-codes. Confirmed: exactly **1 of 45** has a fully-sourced +
  all-kitchen route (methyl salicylate, 1 step). *(Verified — new evidence, full-registry sweep.)*
- **No registered target has an engine-derived route where a substrate-reactivity measuring model would flip a
  verdict that is *wrong today*.** The carbinol-degree collision family (pentyl/tert-butyl/aminopentyl) exists
  ONLY as `parse_smiles` literals in a probe — never a registered target the engine ranks. *(Verified.)* This
  is the zero-call-sites wall [[an-oracle-driven-existence-check-can-prove-a-defer]]: a derived model built now
  would have no live call site.
- **The one shovel-ready consumer** is `paracetamol` vs `4-aminophenyl acetate` (C₈H₉NO₂ isomers, both
  registered `structure.py`): both derive a 1-step route from `4-aminophenol + acetic acid`, and the engine
  *already recognizes they compete* (returns `selectivity=UNKNOWN`, "2 registered isomers... compete, but no
  sourced selectivity"). It fails to resolve **only for want of a SOURCED fact** — a `SelectivityRecord`, not
  a derived model. Zero new engine plumbing to wire it. *(Verified by live re-derivation.)*
- Aside: isopentyl acetate's census miss is a `reagents.py` stock-catalog coverage gap (isopentyl alcohol not
  a commodity), **not** a reactivity gap — a reachability (PR-1) increment, orthogonal to the keystone.

### Bearing D — sourced-data path → **SOURCING-WALL, and the premise may be INVERTED**

- The enforced `SelectivityRecord` bar (`selectivity.py:105-151`, `provenance.py:36-55`): a syntactically valid
  DOI or HTTP(S) URL + `SourceReview.ACCEPTED`. A numeric ratio is a **curatorial** preference, not a code gate.
  *(Verified.)* So the patent wall is a judgment call (patents self-report, aren't peer-reviewed), consistent
  with R52.
- **Free-acid 4-aminophenol N-vs-O: no peer-reviewed source exists.** Two patents only (WO2017154024A1 from
  R52; CN101250131B — 1:6 aminophenol:AcOH, *zinc* catalyst, 150 °C, reports only 90% yield / 98% purity, **no
  N:O ratio**). Structural reason it's unfindable: **nobody runs plain glacial acetic acid on 4-aminophenol** —
  industrial and teaching preps both use acetic *anhydride* precisely *because* free AcOH is too weak an
  acylating agent to characterize at this regime. *(Verified: two patents + zero journal hits after ACS/RSC/
  Beilstein/PMC/Org.Synth. search.)*
- **THE NAG (load-bearing, changes the R52 premise):** Kristensen, *Beilstein J. Org. Chem.* 2015, 11, 511
  (**DOI `10.3762/bjoc.11.51`**, peer-reviewed, OA, full-text read) states the field mantra: *"acidity favors
  O-acylation, while alkalinity favors N-acylation."* Glacial acetic acid *as the medium* is arguably the
  acidic condition — so the free-acid route to 4-aminophenol may favor the **O-product (4-aminophenyl
  acetate)**, the OPPOSITE of R52's stated assumption that a sourced fact would flip the O-route to DISFAVORED.
  The direction is unresolved for this exact substrate (no one published it). **Do not accept a future citation
  just because it flips the route the convenient way.** *(Verified quote; Conjectured that free-AcOH medium
  counts as "acidic conditions" strongly enough to flip 4-aminophenol specifically.)*
- One genuine bar-clearing source surfaced — Habibi et al., *J. Chem.* 2013, **DOI `10.1155/2013/268654`**
  (peer-reviewed, OA): selective N-acetylation of p-aminophenol with Ac₂O. But it is the **anhydride** case =
  redundant with the existing anhydride SEED record; it does not touch the free-acid case. *(Verified.)*
- Schema note: `SelectivityRecord` (same product_formula, different isomer) **cannot hold** a
  tertiary-alcohol-E1-vs-esterification fact — E1 gives a different molecular formula (alkene + water), not a
  competing isomer. That determinant needs a different container. *(Verified — architecture debt.)*

---

## 3. The honest verdict

**The ingenuity REWARD is not shovel-ready via any of the three sound paths today:**

1. **Derived boolean recognizer** — a likely 4th defer (collision recurs unboundedly at benzylic/acid-side
   sterics) AND has no registered consumer. Do not build this form.
2. **Sourced `SelectivityRecord`** — sourcing-wall for the free-acid case, and the premise may be inverted.
   The one bar-clearing source is redundant.
3. **The consumer** exists (paracetamol / 4-aminophenyl acetate) but is gated on path 2.

**But the research narrowed the problem to ONE unexplored fork with a decisive early test:** a **continuous
DERIVED reactivity estimator** (Taft E_s / Hammett σ), which — unlike a boolean recognizer — (a) has an
architectural precedent (`bond_enthalpy.py`), (b) has **sourceable data** (Taft/Hammett constants are standard
textbook physical constants; the sourcing wall is on the specific *ratio*, not the *constants*), and (c) faces
exactly two gates the plan attacks head-on: the bounded-vs-unbounded fork (Bearing A) and the consumer problem
(Bearing C).

This is the difference between "defer #4" and "drive at completion honestly": we do not promise a build the
evidence says may fail, but we run the ONE experiment that decides it, with the kill criteria stated up front.

---

## 4. The R53 plan (phased, gated)

### Phase 0 — the decisive kill-or-continue probe *(no production code; a probe + a design gate)*

- **P0.1 — source a minimal Taft E_s / Hammett σ table.** A committed `smartchem/data/` module on the
  `bond_enthalpy.py` pattern (constants keyed by substituent, provenance = a standard compilation, a
  calibration tuple). Taft/Hammett constants are textbook-tier; expected SOURCEABLE (unlike the 4-aminophenol
  ratio). If they somehow don't clear the bar → data-sourcing defer (unlikely).
- **P0.2 — the recurrence probe.** A committed probe testing whether `{carbinol degree, Taft E_s at the
  carbinol, Taft/σ at the acyl carbon, competing-nucleophile flag}` (with a domain guard) separates **all**
  collision pairs — the two documented ones AND Bearing A's new ones (isopropanol/1-phenylethanol,
  acetic/pivalic acid) — then a STRESS battery of further engine-derivable substrate pairs. **Kill:** if the
  collision recurs at a determinant the continuous feature set structurally cannot read → **defer #4, with the
  theorem written down** (the honest deliverable, matching R49/R50/R52). **Continue:** if it holds within a
  stated domain guard, and the guard's fail-closed UNKNOWN set is non-vacuous but not everything (avoid the
  base-rate-inversion trap [[base-rate-dependent-fail-closed-polarity]]).
- **P0.3 — resolve the consumer.** Is there an engine-derivable route (possibly via the deferred P1.2 mediator
  widening) that the estimator would demote/exclude — a real call site? If none, and there is no **principled,
  non-overfit** way to surface one (registering targets *to make the feature fire* is forbidden by the
  poor-man anti-overfit rule [[a-control-must-discriminate-the-hypotheses-it-separates]]) → the arc stays
  consumer-gated (defer with the exact unlock named). The paracetamol/4-aminophenyl-acetate pair is NOT a
  consumer for this path (it needs a sourced fact, not a measuring model).
- **GATE:** a 4/5-bearing adversarial DESIGN gate on the Phase-0 findings (the R49/R50/R51/R52 discipline —
  dalembert/evil-morty/birdperson/butter-robot/daniel) BEFORE any Phase-1 wiring.

### Phase 1 — build *(only if P0.2 continues AND the gate approves)*

The estimator at the frontier (`routes.py:528-529`/`763-764`) + the carrier (Bearing B option (a) schema field
or (b) digest side-channel — decided at the gate) + wire to `_affordability_frontier` `hard_blockers` / the
Pareto axis, ranking-only, fail-closed, never the scalar `_score_tuple`. One PR: probe (FROZEN_HASH pattern) +
`tests/` regression pins + a v0.1 scope doc.

### Phase 2 — the ingenuity reward proper (R50 unlock #4)

Once a sound feasibility signal exists, the positive "ingenuity" surfacing (demote the boring
buy-the-reagent route below the clever kitchen one) rides on it, on the affordability Pareto axis. This is the
keystone; it is meaningless before Phase 1's signal is sound.

---

## 5. Parallel sound increments (independent of the keystone; bank cheaply, any round)

1. **Premise correction (DONE this round in memory; TODO in the R52 scope doc):** the free-acid 4-aminophenol
   route may favor the O-product, not N — record Bearing D's Kristensen finding so no future citation is
   accepted on the convenient-direction vibe.
2. **SelectivityRecord schema gap:** it cannot hold E1-vs-ester (different product formula) — note as
   architecture debt; a tertiary-alcohol dehydration signal needs a different container.
3. **reagents.py stock-catalog gap (PR-1 lane):** isopentyl alcohol is not a commodity, so isopentyl acetate
   has no fully-sourced route despite a sourced Fischer step — a reachability increment, orthogonal to the
   reward, that would give methyl salicylate a sibling.
4. **(Low value)** fix the R52 defer-probe's diol-EXCLUDE polarity — probe-only, cosmetic.

---

## 6. Kill criteria (stated up front, so the gate is honest)

- **Unbounded regress (P0.2):** collision recurs at a determinant the continuous feature set can't read →
  defer #4 with the theorem.
- **No consumer (P0.3):** no engine-derivable call site and no non-overfit way to create one → consumer-gated
  defer.
- **Data wall (P0.1):** Taft/Hammett constants can't be sourced to the repo's bar → data defer (unlikely —
  textbook constants).

A defer here is not a failure — it is the same verified-defer deliverable that R49/R50/R52 produced, and it
would be the FOURTH independent proof that this keystone needs a genuinely bigger model than any classifier.
The point of Phase 0 is to find that out in one cheap, decisive round instead of a bad PR.

---

## 7. Boundaries of this plan

- The four bearings were read-only research passes, not builds; the Conjectured claims (benzylic/acid-side
  recurrence, carrier tradeoff, free-acid selectivity direction) are exactly what Phase 0 must *measure*
  before they enter a design.
- Anchors re-verified at HEAD `ddf7190`; re-grep before trusting any line number after the next refactor.
- This plan does not touch the other open frontiers (ranker ring/aromatization thermochem; aromatic-heteroatom
  kekulizer) — all scout-verified consumer-gated defers, unchanged.
