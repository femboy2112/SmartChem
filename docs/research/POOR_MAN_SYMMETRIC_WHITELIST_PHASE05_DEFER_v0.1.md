# Poor-Man Symmetric Whitelist — Phase-0.5 Decision (v0.1): DEFER #5

> **Status:** **DEFER #5** — the FIFTH verified defer of the ingenuity-reward keystone, and the one that
> **kills the escape** the four prior defers (R49/R50/R52/R53) all converged on. This round executed BOTH
> teed-up increments to their decision. Neither cleared a build; both produced sharp, verified findings that
> narrow the next target. This is the honest, *planned* outcome (the arc stays a live must-complete feature).
>
> **Mandate (user):** *"full blast on both 1. Reachability increment, and 2. The symmetric safe-set whitelist
> (Phase-0.5)."* Done — full blast, both concluded.
>
> **Provenance:** the frozen probe `experiments/poor_man_symmetric_whitelist_phase05_probe.py`
> (`FROZEN_HASH = 931976…`, `validate() → True`); a fresh full-registry reachability + consumer census
> (author's own runs); a Citadel-Rick availability sourcing recon; and a five-bearing adversarial DESIGN gate at
> HEAD `8678ad3` (dalembert / evil-morty / daniel / birdperson / butter-robot). **Every load-bearing claim below
> was independently reproduced by the author against the filesystem, never taken on a subagent's word.**

---

## 1. What the round asked, and the answers

Two increments were teed up by DEFER #4:

1. **Reachability increment** — verify the `data/reagents.py` isopentyl-alcohol commodity gap is orthogonal +
   small → give methyl salicylate a fully-sourced kitchen sibling (the one thing that turns "zero consumers"
   into one). **Answer: DEFER — the premise is refuted three ways (§2).**
2. **The symmetric positive safe-set whitelist (Phase-0.5)** — build the both-sides recognize-inert whitelist,
   gate its base-rate/vacuity question BEFORE any wiring. **Answer: DEFER #5 — over-determined (§3–§6).**

---

## 2. Increment 1 — the reachability increment is REFUTED (three ways)

The recorded census claim was "isopentyl acetate is blocked only by the isopentyl-alcohol commodity gap,
orthogonal to reactivity." A direct measurement (`compile_synthesis` over the Fischer targets) refutes it:

1. **Not blocked.** Isopentyl acetate is ALREADY fully-commodity-reachable at baseline (2 fully-sourced routes),
   with **no** isopentyl alcohol stocked. *(Verified.)*
2. **The reachable routes are chemically BOGUS.** Both baseline routes are formula-*balanced* but chemically
   *impossible* — e.g. `acetic acid + ethanol → ethyl acetate ; isopropanol + ethyl acetate → isopentyl acetate`
   and `ethanol + isopropanol → C₅H₁₂O ; acetic acid + C₅H₁₂O → isopentyl acetate`. You cannot fuse ethyl +
   isopropyl into a 3-methylbutyl skeleton. The graph-surgery grammar conserves the molecular formula but not
   chemical feasibility. The ONE real route (`acetic acid + isopentyl alcohol`) needs isopentyl alcohol as a
   leaf. *(Verified — route equations printed.)*
3. **The real precursor is INDUSTRIAL, not a kitchen commodity.** A sourcing recon (every retail channel —
   Fisher/Sigma/Lab Alley/VWR/Amazon "Industrial & Scientific") found **no** genuine consumer product for
   isoamyl/isopentyl alcohol; "banana oil" is the *acetate* (CAS 123-92-2), a different compound — the classic
   trap. Honest tag = `Availability.INDUSTRIAL`. *(SOURCED; boundary: English-web only.)*

**Therefore adding isopentyl alcohol as a kitchen commodity would be a FABRICATED availability claim**, and
adding it as INDUSTRIAL would neither be a "kitchen sibling" nor be necessary. **The deepest finding:** the
"gap" was never *orthogonal to reactivity* — the tool already "reaches" isopentyl acetate through bogus routes,
and the only thing that could tell the real Fischer route from the nonsense is a feasibility estimator: **the
deferred keystone itself.** No `reagents.py` change ships.

---

## 3. Increment 2 — the symmetric whitelist: the build + the friendly-subset positive result

The escape all four defers named: recognize the INERT set POSITIVELY on BOTH reaction centers (R51's discipline
applied symmetrically), decline everything else — `symmetric_whitelist_verdict(alcohol, acid)` → FEASIBLE iff
both `recognize_inert_carbinol` AND `recognize_inert_acyl`, else UNKNOWN. Never NOT_FEASIBLE, so — the claim —
sound *by construction*.

On the author's 25-row battery the result is genuinely better than R53:

- **`battery_sound = True`, 0 false-VOUCH.** It **closes the entire R53 kill** — β-keto, α-thioether, furfuryl,
  tert, sec-benzylic all correctly declined (verified, not luck: each hazard lands inside the bounded radius or
  trips a dedicated flag).
- **`feasible_recall = 0.875`**, `conventional_recall = 1.0`, `unconventional_recall = 0.714` — it blesses
  banana oil, benzyl acetate, allyl acetate, pentyl benzoate, ethyl levulinate. Not vacuous; not (on this
  battery) anti-telos.

**But that `sound=True` is a check-derived-from-its-own-subject** — the recognizer was designed knowing the R53
kill set, then tested on it. The gate broke it off-battery.

---

## 4. The kill — the theorem, the surviving false-VOUCHes, the un-patchability

**The theorem.** Inverting a fail-closed BLACKLIST (R53) to a POSITIVE whitelist does NOT reach zero false-VOUCH
if "recognized-inert" is an **element census over a bounded radius** (`_neighbourhood_is_pure_hydrocarbon` reads
atom identity C/H, never bond order). Reactivity lives in bond order + conjugation + remote groups the census
cannot read. The R49/R50/R52/R53 collision did not close — it **moved** from the blacklist guard into the
*definition of "recognized-inert"*, which now must enumerate reactive-but-pure-hydrocarbon motifs over an
unbounded space: the R53 theorem verbatim, one alphabet in (π-bonds instead of heteroatoms).

The surviving false-VOUCHes (whitelist returns FEASIBLE; kitchen-truth NOT feasible), frozen in the probe:

| # | Route | Axis | Finder | Why not kitchen |
|---|---|---|---|---|
| 1 | ethanol + acrylic acid | α,β-unsaturation (polymerizes) | dalembert/evil-morty | acrylate polymerizes under hot protic acid; real esterification needs a radical inhibitor (MEHQ), absent from any kitchen |
| 2 | ethanol + methacrylic acid | α,β-unsaturation | dalembert/evil-morty | methacrylate (PMMA monomer) polymerizes |
| 3 | ethanol + propiolic acid | α,β-alkyne (oxa-Michael) | dalembert/evil-morty | the alcohol oxa-Michael-adds across C≡C; product is the adduct, not the ester |
| 4 | remote-epoxide alcohol + AcOH | acid-labile past radius 2 (**R53 regression**) | evil-morty | Fischer acid opens the epoxide; R53 declined it (molecule-wide guard the radius-2 scan dropped) |
| 5 | remote-acetal alcohol + AcOH | acid-labile past radius 2 (**R53 regression**) | evil-morty | Fischer acid hydrolyzes the acetal; invisible past radius 2 |
| 6 | methanol + pyrrole-2-carboxylic | 5-ring heteroaromatic (guard vacuity) | evil-morty | pyrrole resinifies under strong acid; the ring-heteroatom decline keys on `6 in sizes`, so 5-rings bypass it |

The whole α,β-unsaturated class VOUCHes (crotonic/sorbic/maleic/fumaric/cinnamic/itaconic too).

**Not patchable within the positive frame (the R52 scissors, `run_patch_collision`).** Declining
α,β-unsaturation to close acrylic ALSO false-EXCLUDEs feasible crotonic/cinnamic/sorbic — the distinguishing
determinant (polymerization propensity) is a magnitude the bounded recognizer cannot read. `separates = False`
(3 infeasible declined, 3 feasible declined). Every leak's "fix" recurs the theorem or re-imports a blacklist
(restoring the remote-labile guard re-imports the unbounded hazard enumeration positive recognition was meant
to escape).

---

## 5. The five-bearing gate (verdicts)

- **dalembert** (structure-theorem): **DEFER** — proved the whole α,β-unsaturated class false-VOUCHes; two bugs
  (element-scan blind to bond order; a vinyl-matching "ipso" detector that routes acyclic unsaturated acids into
  a vacuously-empty benzoic branch — fixing it does *not* stop the leak, the aliphatic branch VOUCHes acrylic
  anyway); 50% false-EXCLUDE on his 22-acid set. The carbinol-side core survived his attack.
- **evil-morty** (feature-extraction break): **HAS-FALSE-VOUCH** on 3 axes (α,β-unsaturation; remote-labile
  regression; 5-ring heteroaromatic guard vacuity); confirmed the R53 kill set is genuinely declined and the
  recognizers are exception-safe (~20 hostile SMILES, no crash). Flagged a docstring/code mismatch (di-acids not
  actually declined) and a degenerate vacuous-pass (carbonic acid).
- **daniel** (instrument/base-rate): reproduced the probe's numbers exactly; on an independent 47-row deployment
  battery, **feasible_recall fell 0.875 → 0.574** (polyfunctional-only subset **0.444**) — amino/halo/hydroxy/
  polyol acids near 0% recall. The di-acid/heteroatom behavior is a **radius-window artifact**, not
  chemistry-tracking (oxalic/malonic decline; succinic/glutaric/adipic pass). My battery was measurably friendly.
- **birdperson** (architecture/telos): **DEFER** — the collision moved, not closed; *neither* wiring serves the
  telos — (A) VOUCH-as-reward rewards the conventional and launders acrylic's false-VOUCH into a rank boost; (B)
  UNKNOWN-as-blocker is the R52 base-rate inversion (mass false-EXCLUDE). A two-valued signal is telos-orthogonal
  — it cannot rank clever-above-conventional. Flagged the alcohol side shares the "pure HC = inert" blindness
  (benign only by battery luck — dalembert then found the cinnamyl/pentadienyl carbinol cases).
- **butter-robot** (YAGNI/consumer): **DEFER-NO-CONSUMER** — zero live call sites; even R51's shipped
  `route_catalyst_blockers` was "a guard ahead of its data" but justified by a near-certainty this whitelist
  lacks. Keep the probe as a committed research artifact; do NOT wire it.

---

## 6. The consumer census: ZERO, and the only wiring is destructive (verified)

Fresh full-registry sweep (all **45** targets, author's own run): **5** targets have a real (alcohol +
carboxylic acid) Fischer step in a ranked route. The whitelist VOUCHes exactly **1** (isopentyl acetate — whose
route is the bogus/industrial one from §2) and DECLINES the **4** genuinely-feasible aromatic ones (aspirin,
paracetamol, methyl salicylate, 4-aminophenyl acetate). So there is **no route where the whitelist improves a
ranking**, and the only non-trivial wiring — UNKNOWN-as-blocker — would **sink four correct targets.** Not a
consumer; a live foot-gun. *(Verified.)*

---

## 7. What is banked, and what the next escape must be

**Banked:** (i) the escape's *principle* — symmetric positive recognition — remains the right shape; (ii) the
**carbinol-side core** (degree + cation-stability score + out-of-center nucleophile, from the R53 alcohol-side
work) is the one place all five bearings agree reads a real reaction-center determinant and is sound — keep it;
(iii) a fifth independent proof, now with the failure mode of the naive version *proven*: an element census
cannot stand in for inertness.

**What the keystone actually requires (named, not built):** recognize inert **scaffolds by name** (n-alkyl,
non-benzylic sec-alkyl, bare/ortho-mono benzoic) with an explicit **saturation-state clause** (no C-multiple-bond
within radius k) AND the restored remote-acid-labile guard — i.e. a genuinely bigger, partly-enumerative model —
gated on a **proven live consumer** (still zero). And a two-valued verdict is structurally telos-orthogonal: to
*surface* cleverness the reward needs a magnitude/ranking axis, not a gate. This is the fifth proof that the
keystone needs a model beyond ANY bounded-radius reaction-center recognizer, positive or negative.

---

## 8. What ships this round, and boundaries

**Ships (this PR):** the two frozen probes' evidence — the Phase-0.5 whitelist probe (the DEFER #5 artifact) +
its 9-pin sibling test + this doc + memory/ROADMAP updates. **NOT** the whitelist wiring (proven unsound §4 +
consumer-less §6) and **NOT** an `isopentyl alcohol` commodity entry (a fabricated availability claim §2). No
production code changes; the suite is unaffected.

**Next actionable (each its own non-stacked round, all consumer-gated):**
1. The keystone now needs a *different KIND* of model (scaffold-by-name + saturation + magnitude axis, or an
   external reaction oracle), not a fifth bounded recognizer — do not re-attempt a local classifier/whitelist.
2. A live consumer must exist first (unlock #3, still unmet) — the reachability lane cannot manufacture one via
   a commodity entry (§2). A real consumer needs a target with a genuine competing Fischer route in the grammar.

**Boundaries.** Kitchen-truth labels are textbook-ASSERTED (same discipline as the probe's battery and
R50/R52/R53), not wet-lab measured. The availability recon is English-web only. The gate bearings were read-only
research passes; daniel's battery is diversity-weighted, not incidence-weighted. Anchors re-verified at HEAD
`8678ad3`; re-grep line numbers after any refactor.
