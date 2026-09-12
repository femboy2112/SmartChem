# Poor-Man Reactivity Estimator — Phase-0 Decision (v0.1): DEFER #4

> **Status:** **DEFER #4** — the FOURTH verified defer of the ingenuity-reward keystone. Phase 0 of the
> completion plan ([`POOR_MAN_ARCH_COMPLETION_PLAN_v0.1.md`](POOR_MAN_ARCH_COMPLETION_PLAN_v0.1.md)) ran to its
> decision; the gate did not clear the build. This is the honest, *planned* outcome (plan §6: "a defer here is
> not a failure").
>
> **Mandate (user, 2026-09-11):** *"we must complete the poor-mans arch."* The arc stays a live must-complete
> mainline feature; this round proves what the keystone actually requires (a genuinely bigger model) and hands
> the next round a sharper, narrower target.
>
> **Provenance:** the frozen probe `experiments/poor_man_reactivity_estimator_phase0_probe.py`
> (`FROZEN_HASH = e12680fc…`, `validate() → True`); a full-registry consumer census (Citadel Rick) reproduced
> independently by the author; and a five-bearing adversarial DESIGN gate at HEAD `24afef3`
> (dalembert / evil-morty / birdperson / butter-robot / daniel). Every load-bearing claim carries an epistemic
> label and the file:line / DOI / SMILES it rests on.

---

## 1. What Phase 0 asked, and the answer

The plan narrowed the keystone to ONE unexplored fork: a **continuous DERIVED reactivity estimator** (Taft E_s /
Hammett σ, `bond_enthalpy.py`-style, domain-guarded), replacing the BOOLEAN reaction-classifiers that R49/R50/R52
each killed. Phase 0's decisive question (plan §3, §6): is the collision recurrence **bounded** (a finite set of
continuous features that terminate with a fail-closed guard → CONTINUE) or **unbounded** (→ a fourth defer)?

**Answer: DEFER #4, over-determined.** A continuous three-valued estimator with a fail-closed guard is a *real*
improvement — its alcohol-side core is sound and independently calibrated — but it does **not** reach the
zero-false-VOUCH soundness bar. Making the classifier continuous **moved** the R49/R50/R52 collision from the
classifier into the **domain guard**; it did not close it.

---

## 2. What was delivered and verified (the gains this round banks)

- **P0.1 — sourced constants: DELIVERED.** Taft E_s (methyl-referenced) + Hammett σ/σ⁺. daniel independently
  cross-checked 6/8 Taft E_s values against a *different* compilation (Anslyn & Dougherty 2006 via Wikipedia) —
  exact to the hundredths; Hammett σ from Hansch, Leo & Taft, *Chem. Rev.* **1991**, 91, 165–195,
  **DOI 10.1021/cr00002a004**. (Neopentyl −1.74 rests on a weaker secondary source — flagged, non-load-bearing.)
  The constants clear the repo's DERIVED-table bar. *(Verified.)*
- **The alcohol-side carbocation core is SOUND and CALIBRATED.** A radius-1 cation-stability score
  (`carbinol degree + adjacent-π conjugation`) **closes Bearing A's isopropanol/1-phenylethanol collision**
  (both degree-2, separated by the conjugation term degree-alone was blind to — the pair R52 said no bounded
  feature could close). daniel confirmed it *generalizes*, not overfits: it correctly separates FRESH score-3
  (benzhydrol) and score-4 (trityl alcohol) alcohols never in the battery, and dalembert **could not break the
  alcohol side**. *(Verified.)*
- **Architecture: no carrier needed (Bearing B premise reduced).** The estimator reads functional groups off the
  reactant molecule graphs, which survive intact in `step.reactants` (`from_transform` sets
  `synth_reactants = tuple(transform.products)`, `step.py:237`) — exactly as `bond_enthalpy.route_delta_h_kj`
  reads `route.steps`. Wiring would be R51-scale: one `route_fischer_infeasibility_blockers(route)` mirroring
  `route_catalyst_blockers`, one line at `service.py:2020`. *(Verified premise; birdperson's caveat below.)*
- **The probe is FROZEN as the defer artifact** (core battery clean + the surviving kill), with a sibling test
  `tests/test_poor_man_reactivity_estimator_phase0_defer.py` (8 pins).

---

## 3. The kill — the theorem, and the surviving false-VOUCHes

**The theorem.** The estimator's confident FEASIBLE region is guarded by a **hand-enumerated blacklist** of
hazard triggers (element whitelist; epoxide/acetal; sp2-phenol; α-O/α-N heteroatom; adjacent 3-ring; ortho-aryl
steric). The hazard space for "does this Fischer esterification run cleanly in a kitchen" is **unbounded**, so
every guard patch is met by a new leak one heteroatom / position / functional-group out. The P0.3 census found +
this round patched the **phenol** hole — and patching it was immediately met by the sulfur / β-keto / furfuryl
leaks below. This is the R49/R50/R52 collision recurring **through the guard**.

The surviving false-VOUCHes (estimator returns FEASIBLE; kitchen-truth is NOT feasible), frozen in the probe:

| # | Route | Axis | Finder | Why not kitchen |
|---|---|---|---|---|
| 1 | ethanol + acetoacetic acid | acid-side β-keto decarboxylation | dalembert | β-keto acids decarboxylate (acetone + CO₂) under Fischer acid/heat; ethyl acetoacetate is made from diketene/Claisen, never Fischer |
| 2 | ethanol + 3-oxoglutaric acid | acid-side β-keto decarboxylation | dalembert | doubly-β-keto acid decarboxylates readily |
| 3 | 1-(ethylthio)ethanol + AcOH | α-thioether thionium (S guard gap) | evil-morty | S is in `_SAFE_ELEMENTS` but omitted from `_carbinol_alpha_heteroatom` (O/N only) and the thiol detector → thionium SN1 vouched while byte-identical α-O/α-N are declined |
| 4 | furfuryl alcohol + AcOH | heteroaryl cation magnitude | evil-morty/daniel | ring-O-stabilized cation → acid resinification; the binary conjugation flag gives it benzyl's exact FEASIBLE vector |

**The acid-side structure theorem (dalembert):** the acid side is a *single* flag (ortho-aryl steric). Any acid
that fails Fischer for a **non-steric** reason is invisible. The keto-position sweep is the proof: α-keto
(pyruvic, real) works, **β-keto (acetoacetic) fails**, γ-keto (levulinic, real) works — separating β requires the
**keto-to-carboxyl distance**, a radius-2 determinant the feature set has *zero* acid-side features for. It can
neither read it nor decline it, so it is forced to a confident wrong call. This is exactly the plan's own §6 kill
criterion.

---

## 4. The five-bearing gate (verdicts)

- **dalembert** (structure-theorem refutation): **DEFER** — proven β-keto false-VOUCH + the unbounded acid-side
  regress theorem. The alcohol side survived his attack; the acid side is a blacklist of one.
- **evil-morty** (feature-extraction break): **HAS-FALSE-VOUCH** — α-thioether (the S gap), furfuryl magnitude,
  trityl-ether lability. Confirmed the earned parts hold (role assignment, element whitelist, epoxide/acetal/THP,
  the E1/SN1 core, N-nucleophiles, no crashes).
- **birdperson** (architecture): **SOUND-WITH-CONDITIONS**, but the conditions bite — (i) the no-carrier path
  *rediscovers by heuristic* the role/reaction-type the atom-map made exact (the phenol bug is proof of that
  class), so it must fail closed on any polyfunctional/ambiguous reactant; (ii) wired as a **demotion**, the
  consequential error is a false NOT_FEASIBLE (a *false-EXCLUDE*, never asserted zero on a deployment battery),
  which *defeats the arch's telos* — it sinks the very clever route the keystone exists to surface; (iii)
  building past an empty consumer census steps over the plan's own red P0.3 gate. His doubt — a FROZEN "continue"
  validated by the battery it was shaped against is a check-derived-from-its-own-subject — was **proven correct**
  by dalembert.
- **butter-robot** (YAGNI/scope): **DEFER (c)** — the R51 "guard ahead of its data" analogy is not decisive
  (R51 guards a near-certainty; this guards a door no one walks toward). Investigate the reachability increment
  (d) as the real next step.
- **daniel** (instrument verification): constants **PASS** (6/8 exact vs an independent source), hash reproduces
  byte-for-byte, threshold **calibrated not tuned** (generalizes to fresh score-3/4), phenol fix holds on 8
  geometries — and independently re-found the furfuryl gap.

---

## 5. P0.3 — the consumer census: ZERO (verified by the author's own sweep)

Independently re-run at HEAD `24afef3` (not on the Citadel Rick's word): `compile_synthesis` over **all 45**
registered targets, prototyping `route_fischer_infeasibility_blockers` over every ranked route. **5 targets**
touch a Fischer step (4-aminophenyl acetate, aspirin, isopentyl acetate, methyl salicylate, paracetamol);
**NONE** would receive a hard blocker (every one resolves to FEASIBLE-unchanged or UNKNOWN). The one apparent
consumer, **aspirin**, was the **phenol domain-guard bug** — now patched to UNKNOWN — and demoting it would have
been *destructive* (no competing anhydride route exists in the capped-scission grammar: a Lane-B genericity gap,
not mediator widening). So even a *sound* estimator has **zero live call sites** today. *(Verified.)*

---

## 6. The escape (named, not built) — what the keystone actually requires

All four defers now point at the same bigger model: a **symmetric POSITIVE safe-set whitelist on BOTH reaction
centers** (R51's "recognize the SAFE set only", applied to substrates) — confidently FEASIBLE *only* when both
the carbinol *and* the acyl neighborhood are recognized-inert scaffolds, decline everything else. This converts
every §3 false-VOUCH to an honest UNKNOWN. But it **re-raises the R52 base-rate/vacuity question**
([[base-rate-dependent-fail-closed-polarity]]): does the FEASIBLE set survive being restricted to a
positively-recognized-inert scaffold, or does the whitelist swallow the population (a vacuous reward)? That is
unresolved and needs its own calibration + gate round. This is the fourth independent proof that the keystone
needs a genuinely bigger model than any reaction-center classifier — now with the *shape* of that model named.

---

## 7. What ships this round, and the next actionable increments

**Ships (this PR):** the frozen probe (the defer artifact) + its sibling test + this doc + memory/ROADMAP
updates. **NOT** the estimator wiring — it is proven unsound (§3) and consumer-less (§5); shipping it would be a
false-VOUCHing guard on zero routes.

**Next actionable, in priority order (each its own non-stacked round):**
1. **Reachability increment (butter-robot's (d) — the one thing that turns zero consumers into one):** the
   census flagged isopentyl acetate is blocked only by a `data/reagents.py` commodity-catalog gap (isopentyl
   alcohol not stocked), orthogonal to reactivity. Verify the gap is commodity-only (not a rabbit hole) and, if
   so, it gives methyl salicylate a fully-sourced kitchen sibling. *(A PR-1 reachability lane item.)*
2. **The symmetric safe-set whitelist (§6) as a Phase-0.5**, IF the user wants to keep pushing the reward: build
   the both-sides positive-inert whitelist and gate its base-rate/vacuity question BEFORE any wiring.
3. The acid-side / S / furfuryl leaks are **left unpatched on purpose** — patching them is just more blacklist
   entries proving the theorem; they are evidence, not a to-do.

---

## 8. Boundaries

- Kitchen-truth labels are textbook-ASSERTED (the same discipline as the probe's own battery and R50/R52), not
  wet-lab measured.
- The gate bearings were read-only research passes; malonic acid's decarboxylation label is the "more arguable"
  of dalembert's set (excluded from the frozen kill; acetoacetic + 3-oxoglutaric are the clean ones).
- Anchors re-verified at HEAD `24afef3`; re-grep line numbers after any refactor. Memory's `bond_enthalpy.py`
  anchor was corrected this round to `smartchem/experiment/bond_enthalpy.py` (not `smartchem/data/`), and
  `_affordability_frontier` to `smartchem/service.py:1984-2028` (not `smartchem/experiment/service.py`).
