# Ranker chemical selectivity — scope v0.1 (R47, frontier 2)

**Mandate (the user, verbatim intent):** "full blast on ... 2 (ranker chemical selectivity)" — the named frontier
R45 opened: *"the capped-scission engine OVER-GENERATES valence-valid-but-dubious candidates — a C–C homologation
outranks the sound methylation; teach the ranker to prefer chemically-sensible disconnections."* Under the standing
constraint that governs this whole arc: **do not hard-code chemical reactions — hard-code reality, derive the
chemistry.**

## The gap, ground-truthed

`compile_synthesis(caffeine, available=[theophylline, ethanol])` returns three routes; on `main` the ranked order is:

```
[0] C2H6O + C7H8N4O2 -> C8H10N4O2 + CH4O      (ethanol + theophylline -> caffeine + methanol; a C-C homologation)
[1] C7H8N4O2 + CH4O -> C8H10N4O2 + H2O        (theophylline + methanol -> caffeine + water; the SOUND N-methylation)
[2] ...two-step...
```

The dubious homologation ranks **above** the sound methylation. Their `_score_tuple` values are **byte-identical** —
`(0, 1, 1, 1, 0, 0.0, 2, 0, 0, 2)` — because caffeine/theophylline are not in the sourced thermo table, so every
sourced tier (selectivity, feasibility, equilibrium, kinetics) is UNKNOWN, and the ranker falls through to the
stable-sort's arbitrary **discovery order**. There is no chemical signal separating them.

## The fix — a DERIVED bond-additivity tier, not a reaction table

The missing signal is the disconnection's thermodynamic drive. It is **derived**, not looked up:

- **Reality (hard-coded):** mean bond enthalpies — measured physical constants, transferable averages, like atomic
  masses (`smartchem/experiment/bond_enthalpy.py`, `MEAN_BOND_ENTHALPY_KJ`, 44 bond types, sourced to a standard
  tabulation). These are *not* reactions.
- **Chemistry (derived):** the reaction enthalpy by **Hess's law over the net bond change**,
  `ΔH ≈ Σ BDE(broken) − Σ BDE(formed)`, consulting only the bonds that actually change (the multiset difference of
  reactant vs product bond inventories — the unchanged skeleton cancels, so a purine's ring never needs an accurate
  ring BDE).

Why it discriminates the caffeine case — **physics, not a rule.** The sound methylation forms the very strong O–H
bond of water (463 kJ), a thermodynamic sink; the C–C homologation breaks a strong C–C bond (347 kJ) and forms only a
weaker C–H (414 kJ), with no comparable sink. ΔH(sound) = **−19 kJ** (exergonic), ΔH(dubious) = **+19 kJ**
(endergonic). Nothing in the table says "methylation good"; Hess's law says water is stable. It is genuine
*derivation*, not a lookup — **proven by generalization**: the ΔH is computed for caffeine's methylation, which is in
no reaction/conditions table (the R45 untabulated fact). (The reverse-reaction sign-flip is a *corroborating*
property, **not** the proof — every signed quantity, a lookup included, is antisymmetric; dalembert R47.)

**What this ranks — a proxy, named plainly (birdperson R47).** The frontier asked to prefer "chemically-sensible
disconnections"; what this delivers is thermodynamic **drive** (a reaction-ΔH sign), a *proxy* for sensibility. They
coincide for the caffeine case and can part ways in general (a thermodynamically-favorable disconnection can still be
mechanistically absurd). Every route stays `FORMAL_CANDIDATE`; the tier orders drive, it does not certify mechanism.

### The domain, and the domain guard (evil-morty / dalembert R47 — the load-bearing fold)

Bond additivity is a sum of **localized** per-bond terms, so it is **blind to non-local stabilization** — ring strain
and aromatic/ring delocalization — and **inverts the sign** there. Verified counterexamples: cyclopropane → propene
(estimate **+80**, true **−33**; ring-strain release invisible) and 1,3-cyclohexadiene → benzene + H₂ (estimate
**+125**, true **−22**; aromatic stabilization invisible). Since the purine ring is aromatic, an unguarded tier could
confidently **bury** a truly-favorable ring/aromatization disconnection at the worst rank.

The fix turns the module's own theorem ("only the changed bonds matter, and localized changes are additive") into an
honest gate: `reaction_delta_h_kj` **fails closed** (`None` → BORDERLINE) whenever the **endocyclic-bond-type
multiset is not preserved** across the reaction — i.e. a ring bond is made, broken, or changes order (ring
formation/opening, aromatization, ring-tautomerization). This declines *exactly* the regime where additivity is
unsound and keeps the acyclic-periphery reactions it earns: the caffeine methylation preserves the purine ring, so
its endocyclic multiset is identical on both sides and its −19 kJ stands. Pinned by
`test_domain_guard_declines_ring_strain_and_aromatization` and `test_domain_guard_keeps_ring_preserving_reactions`.
Residual: *linear* (non-ring) conjugation carries a smaller (~10–20 kJ) non-additive error, bounded by the dead-band
and by this tier being dead-last + subordinate + ranking-only.

### The instrument rule (calibration) and an honest dead-band

Bond additivity's **magnitude** is unreliable — combustion errs by ~200 kJ (O₂/CO₂ resonance) — which is *why* the
tier grades only the **sign**, never magnitude. On the seven known-sign reactions the estimator recovers the sign of
every one, **including combustion**; the largest **in-domain** residual is **14 kJ** (CH₄+Cl₂). `DERIVED_BORDERLINE_KJ`
is therefore set to **15** — a conservative floor *above* that demonstrated in-domain error (so an estimate clearing
the band is unlikely to carry the wrong sign from residual error), and below the caffeine signal (±19 kJ). It is **not**
the combustion-excluded RMS (an earlier draft's overclaim, corrected per evil-morty R47) and **not** tuned to caffeine
(any band in (14, 19) works identically). Pinned by `test_dead_band_is_above_in_domain_error_and_below_the_caffeine_signal`.

### Where it sits — dead-last, strictly subordinate, neutral on ignorance

The tier is appended to the shared `_score_tuple` as the **last** element (position 11), *below* every sourced tier
and even below the sourced kinetics regime:

```
(status, composability, selectivity, feasibility, front_index, netΔG, equilibrium, gaps, exclusions, regime, DERIVED)
```

- **Strictly subordinate.** It only separates routes that tie on *every* sourced tier. A route better on any sourced
  tier but worse on the derived tier still ranks above one worse on the sourced tier but better on the derived tier
  (`test_derived_tier_is_strictly_subordinate_to_every_sourced_tier`). Where a sourced ΔG reaches a route, the sourced
  feasibility tier decides and this is inert.
- **Neutral on ignorance.** `{0 FAVORABLE (ΔH < −band), 1 BORDERLINE/UNKNOWN, 2 UNFAVORABLE (ΔH > +band)}`. An
  untabulated bond → `None` → the BORDERLINE middle (1), never rewarded or penalised
  (`test_neutral_on_ignorance_untabulated_bond_is_none`). This mirrors the "UNKNOWN sits in the middle" discipline of
  every sourced tier — not the reward-for-ignorance sentinel the R26 lesson warns against, because the sign tier's
  middle is genuinely neutral.
- **Ranking-only.** It never enters `fit.status` or any L2 grade — exactly like the kinetics regime.

## Boundaries (documented, not fabricated)

1. **Coarse, sign-only, and domain-guarded.** The tier claims only a SIGN past a 15 kJ dead-band, never a magnitude,
   and only inside its validated domain (the ring/aromatic guard above declines the strain/aromatization regime where
   the sign inverts). Within that domain a genuinely favorable route that bond additivity still mis-signs (residual
   error, or linear conjugation) would be mis-ranked *only among tied UNKNOWN routes* — a strict improvement over the
   arbitrary discovery order it replaces, not a thermochemical verdict — and is corrected the moment sourced thermo
   reaches it (the sourced tier then dominates). It is subordinate + guarded precisely so its coarseness cannot do harm.
2. **Every route stays `FORMAL_CANDIDATE`.** This ranks disconnections by derived drive; it does not certify
   mechanism. `theophylline + methanol → caffeine + water` is formally balanced but mechanistically fictional (real
   N-methylation uses dimethyl sulfate / a methyltransferase) — the readiness tier is unchanged.
3. **Both rankers fed; the DAG twin is BUILT (not deferred).** The tier is threaded as a caller-computed coordinate
   through `_physics_ranked_order` into **both** `rank_routes` (from `route.steps`) and `rank_dags` (from `dag.steps`,
   over which intermediates telescope by Hess's law), so a route and its convergent-DAG analogue rank by the identical
   discipline (the R42 no-divergence promise holds *because* both scorers stay pure extractors of the same coordinate).
   Pinned for the linear path by the caffeine flip and for the DAG path by
   `test_dag_twin_feeds_the_derived_tier_and_discriminates`. (A per-node `dag_thermo_rollup` integration, rather than
   the whole-DAG sum used here, remains a possible future refinement, not a gap.)

## Evidence

- `smartchem/experiment/bond_enthalpy.py` — the sourced table + `reaction_delta_h_kj` (with the endocyclic domain
  guard) / `route_delta_h_kj` / `disconnection_favorability_rank`, with `CALIBRATION` and `DERIVED_BORDERLINE_KJ`.
- `experiments/ranker_disconnection_selectivity_probe.py` — FROZEN_HASH
  `1fb861eda073275203ad43fb0537c09ea1f9b2fca060f2baf4cddb09f449cd88`, RDKit-free `validate()`: calibration (all signs
  incl combustion; dead-band above the in-domain residual); the caffeine flip; the derived ΔH + antisymmetry;
  neutral-on-ignorance; strict subordination; the domain guard.
- `tests/test_ranker_disconnection_selectivity.py` (23 tests): the parametrized calibration; the flip; the derived
  ranks; the reverse sign; untabulated → None; favorability-rank neutrality; strict subordination; dead-last position;
  the honest dead-band; the domain guard (declines ring-strain/aromatization, keeps ring-preserving); the DAG twin.

## Adversarial review (4 bearings)

- **mr-president — SHIP-WITH-CONDITIONS → conditions met.** All 5 mandate items verified end-to-end (sound outranks
  dubious; no hard-coded reactions — bond *energies*, ΔH computed, caffeine untabulated; honesty preserved — still
  `FORMAL_CANDIDATE`; boundaries honest; tests green). He confirmed subordination "in the wild" (a favorable-derived
  route stayed last behind an UNKNOWN-status one). Condition (a stale comment saying the DAG path was deferred) fixed;
  his residual (the DAG path untested) closed with a dedicated test.
- **birdperson — SOUND-with-folds.** Verified the physics is genuine derivation (7 bond values exact vs Atkins; the
  ring/skeleton cancellation is the honest core), placement + no-divergence correct, DAG cancellation mathematically
  sound, calibration honest. Folds applied: the scope doc + test comment falsely called the DAG twin *deferred*
  (corrected — it's built, and the doc's "per-node rollup" mechanism was wrong → now "whole-DAG sum"); the signal is
  **thermodynamic drive, a proxy for sensibility** (named plainly); "like atomic masses" softened to "transferable
  averages, model-laden".
- **evil-morty — one MEDIUM + one LOW/MEDIUM, both FIXED.** MEDIUM: the "recovers the sign every time" claim was false
  outside the calibration window — bond additivity **inverts the sign** on ring-strain/aromatization (cyclopropane,
  benzene), the caffeine target's own structural class, and (dead-last though it is) that *is* the recommendation.
  Fixed by the endocyclic **domain guard** (declines exactly that regime). LOW/MEDIUM: the dead-band was the
  combustion-excluded RMS (hid the true error scale) and was already exceeded by CH₄+Cl₂'s 14 kJ residual. Fixed:
  reframed as a conservative floor **above** the largest in-domain residual (14 → band 15), combustion included in the
  calibration honestly. His Findings 3–6 (neutral-on-ignorance, strict subordination, not-a-lookup, DAG twin) SURVIVED.
- **dalembert — SURVIVED the "lookup in disguise" charge; KILLED the "sign-reliable" claim.** Structure theorem: the
  counterexample class is exactly ring-strain-release + aromatization, both found on the first try (same as
  evil-morty) → fixed by the domain guard. He also proved the reverse-flip is a **non-sequitur** as an anti-lookup
  proof (antisymmetry holds for any signed quantity) — the valid proof is **generalization to untabulated reactions**
  (corrected in the docs). Subordination / neutral-middle / DAG cancellation all SURVIVED. His rival ("just count C–C
  disconnections") is answered: that is a hard-coded heuristic; bond additivity (domain-guarded) is derived physics
  that generalizes to any acyclic-periphery disconnection — which is what the mandate demands.
