# Poor-man reachable recompile — scope v0.1 (R48, PR-1)

Make `recompile <molecule>` produce a usable synthesis from stock **by default** (reachability), with every
emitted route an honest `FORMAL_CANDIDATE` whose feasibility fails **closed** to UNKNOWN wherever the ΔG
estimator cannot vouch (honesty). Both halves hard-code STRUCTURE (reality — buyable-stock identities) and
DERIVE the chemistry (generic graph surgery), never a reaction lookup table.

This is PR-1 of the de-bundled Lane-B poor-man arc. PR-2 (separate) is the poor-man *ingenuity hunter* — the
general DERIVED reaction-class recognizer and the affordability-frontier reachability signal.

## The gap, ground-truthed

Recon (4 blind bearings) proved the Lane-B wall is **reachability, not a weak transform algebra**: the engine
already derives the one-step north-star routes (`caffeine <- theophylline + methanol`;
`paracetamol <- acetic acid + 4-aminophenol`), but the default linear retrosynthesis reached no buyable leaf —
a 16-item kitchen catalog with zero aromatic/hetero scaffolds. Depth was a spurious limiter (raising it
exhausts the finite tree → COMPLETE_WITHIN_BOUNDS, 0 routes).

A design review then killed the naïve honesty gate: once the routes are emitted, the EXISTING feasibility layer
over-claims the flagship `acetic acid + 4-aminophenol -> paracetamol + water` as **FAVORABLE (ΔG = -98.3 kJ) /
ESSENTIALLY_COMPLETE (K = 1.66e17, "~100% conversion")** — a fabrication. Aqueous free acid + amine gives the
ammonium **carboxylate salt** (an acid-base proton transfer), not the amide; direct (Fischer) amidation needs
activation (heat with water removal, or an activated acyl donor). **Thermodynamic DRIVE ≠ mechanistic
FEASIBILITY**; the ΔG estimator is blind to the acid-base salt sink and the activation barrier.

## The fix — two parts

### P1.1 Tiered buyable-leaf catalog (reachability; reality, anti-overfit)
`smartchem/data/reagents.py` gains three registry-grounded purchasable scaffolds, each with its real
`Availability` tier and a procurement note: **theophylline** (PHARMACY), **4-aminophenol** (HARDWARE — photo
developer), and the NON-precursor witness **salicylic acid** (PHARMACY). Membership is a target-independent rule
(registered purchasable scaffolds), not "the precursors of caffeine + paracetamol": the generalization test pins
that the catalog admits ≥1 non-precursor scaffold (salicylic acid is not a precursor of either north star) and
does not depend on the two north stars. Aspirin is deliberately NOT admitted — it is itself a registered
synthesis target with existing producibility/bench-fit coverage, and making it buyable stock would short-circuit
that coverage (the poor man can just buy aspirin, but the bench still needs to synthesise it). Pricing stays
fail-safe (unpriced → None, never fabricated). The north stars flip from NO route to a one-step synthesis from
stock.

### P1.3 The aqueous free-acid dehydrative-acylation DOMAIN GUARD (honesty; the R47 pattern, on the feasibility layer)
`feasibility.py::_is_intermolecular_acyl_condensation` recognizes the guarded class by DERIVED bond-topology
surgery and makes `feasibility_of_step` FAIL CLOSED to UNKNOWN. Because `equilibrium_of_step` reuses the ΔG and
returns UNKNOWN when it is None, **one guard makes both the feasibility and equilibrium layers honest** (and it
propagates to `verify_feasibility`, `verify_equilibrium`, and the net-ΔG drive `route_net_delta_g`, which all
route through `feasibility_of_step`). The route is still FOUND; feasibility just stops vouching for a class it
cannot.

The guarded class: an **intermolecular** dehydrative acylation of a **free carboxylic acid** onto a heteroatom
nucleophile (N→amide, O→ester, S→thioester), expelling water. Recognized by:

* the **shape**: exactly 2 non-water reactants → exactly 1 non-water product, with water net-produced; and
* the **net functional-group change**: a free acid/carboxylate net-consumed, an amide/ester/thioester net-formed.

## The shape restriction is load-bearing (evil-morty + dalembert, with run evidence)

The first design was three global functional-group counts (Δacid<0 ∧ Δacyl>0 ∧ Δwater>0). Both adversaries
converged on its one structural flaw: nothing ties the consumed acid, the formed acyl, and the expelled water
to the SAME reaction center, so the counts are foolable/cancellable across independent sub-reactions. The
**elementary-shape** restriction (2 non-water reactants → 1 non-water product + water) structurally repairs it:

* **Intramolecular ring closure** (lactone/lactam: 1 reactant) — entropically favored, the ΔG IS competent, so
  it must NOT be guarded. Excluded by "2 non-water reactants." (evil-morty Finding 1.)
* **Activated-donor acylation** (anhydride / acid chloride) — legitimate; emits a 2nd product (the leaving
  group). Excluded by "1 non-water product." (Also caught by "water net-produced" / "free acid consumed.")
* **Multi-transformation bundled steps** whose independent sub-reactions would forge (false positive) or cancel
  (false negative) a whole-molecule count — excluded by the shape. Bundled steps fail OPEN (keep the estimate);
  the capped-scission engine emits elementary steps, and the general recognizer over arbitrary steps is PR-2.
  (dalembert KILL 2 / KILL 3.)

Within the elementary shape, conservation forces the net change to reflect the real acyl transfer, so the
counts are sound. The acid detector is **representation-robust** — a carbonyl O with no heavy neighbour is a
carboxyl whether its H is explicit or implicit, and the carboxylate ANION (the salt sink itself) is in-scope —
so the fail-closed guarantee never rests on an explicit-H precondition the graph may not carry (dalembert
KILL 1). Carbonyls are scored per-substituent (no first-match ordering), so a carbamate reads amide+ester and a
carbamic acid amide+acid.

Verified on 18 cases (`experiments/poor_man_reachable_recompile_probe.py`): the flagship lies fire (paracetamol
Fischer, esterification, thioesterification, peptide bond, carbamate), target-independent witnesses fire
(propanoic + ethylamine, benzoic + methanol), and every legitimate control and adversary counterexample stays
silent (anhydride, acid chloride, neutralization, N-methylation, homologation, both lactonizations, both
bundles). The paracetamol route flips FAVORABLE/ESSENTIALLY_COMPLETE → UNKNOWN/UNKNOWN; caffeine stays honestly
UNKNOWN via the data gap (the guard does not fire — no free acid).

## Boundaries (documented, not fabricated)

* **Scoped to ONE class.** The general DERIVED reaction-class recognizer (that would also fail-close other
  fabrications — methanol→ethanol homologation, peroxide oxidations, etc.) is PR-2. Out-of-class steps keep
  their estimate (the guard never claims to catch them).
* **Bundled (non-elementary) steps fail OPEN.** Not reachable from the capped-scission engine (elementary
  steps only); a bundled lie reaching `feasibility_of_step` directly would keep its estimate. PR-2 territory.
* **Carbamic acids** are unstable and not emitted; the guard recognizes them correctly (amide+acid) but they
  are not a practical route.
* **Ether/other dehydrations** (2 ROH → ROR + water) are NOT guarded (no free acid) — a different class, PR-2.
* **Condition-blind BY DESIGN (birdperson).** The guard fires on bond topology regardless of the step's declared
  envelope, so a step declaring high temperature with water removal (Dean–Stark, where Fischer esterification
  genuinely proceeds) is still failed closed to UNKNOWN. This is correct fail-closed behaviour for PR-1 — the ΔG
  estimator is blind to the acid-base salt sink even at high T — but the item-5 phase field already flows through
  `feasibility_of_step`'s `phases=` kwarg, so a later author might expect the guard to relax under declared
  water-removal conditions. It does not. Revisit when conditions gate feasibility; named here so it is not
  mistaken for an oversight.
* **UNKNOWN now carries two meanings (birdperson).** A domain-guard UNKNOWN (`missing == ()`, reason contains
  "domain guard") and a data-gap UNKNOWN (`missing` non-empty, reason "no sourced …") are both
  `FeasibilityDirection.UNKNOWN`, distinguishable today only by the `reason` substring / the empty `missing`. Fine
  for PR-1 (both are honest fail-closed sentinels with defined lattice precedence), but a structured guard tag on
  `StepFeasibility` would pay for itself the first time a ranker or auditor must tell the two apart — a PR-2
  refinement, flagged so no consumer leans on string-matching the reason.

## Evidence

* `experiments/poor_man_reachable_recompile_probe.py` (FROZEN_HASH `208b1373…`, rdkit-free `validate()`): the
  18-case recognizer, the north-star honesty flip, the reachability flip, and the anti-overfit generalization
  checks — all against the REAL production predicate.
* `tests/test_poor_man_reachable_recompile.py`: probe self-check + fast regression pins over the production
  functions (flagship both-layers-UNKNOWN, anhydride silent, target-independent, intramolecular silent, bundled
  silent, caffeine honest-via-data-gap, representation-robust detector).
* Test churn from the guard de-certifying the esterification example (all corrections, not regressions): the
  `recompile_routes_found.json` golden (methyl-acetate esterification → UNKNOWN), the `_convergent_40min_dag`
  fixture (swapped ethyl-acetate esterification join → a non-guarded ethyl-chloride synthesis), the sigma
  test (esterification → ester hydrolysis), and the dag-rank M2b subject (ethyl acetate → methyl propyl ether,
  since every ester route is now thermo-UNKNOWN).

## Invariants (the line)

* **J1** no hard-coded reactions — every emitted route is derived by the generic engine; only stock IDENTITIES
  and the reaction-CLASS taxonomy (reality) are declared.
* **J2** no dossier over-claim — the guarded class fails closed; every route stays `FORMAL_CANDIDATE`.
* **J3** the catalog generalizes — target-independent predicate + the generalization test.
* **J4** default cost bounded — no mediator widening in PR-1 (that was a measured depth-exponential cost bomb,
  deferred to PR-2 where the recognizer can prune the flood).
