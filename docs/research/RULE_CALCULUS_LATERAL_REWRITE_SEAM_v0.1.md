# Rule-calculus lateral-rewrite seam: [3,3] sigmatropic isomerizations (Cope + Claisen) — v0.1

**Item C of the A–F transform-algebra round.** This builds the *lateral-rewrite seam* the alkyne-DA round
(`RULE_CALCULUS_ALKYNE_DIELS_ALDER_FAMILY_v0.1.md` §5) named as the missing integration path when it
VERIFIED-DEFERRED Cope/Claisen. It ships the seam's **sound core** and reproduces, end-to-end, the **W1 structure
theorem** that keeps the recursive-search *auto-discovery* of isomerization routes deferred.

## 1. The two reaction kinds, and why one fit the existing seam and one did not

| | Diels–Alder retro (families #1–#10) | [3,3] sigmatropic (this seam) |
|---|---|---|
| shape | 1 adduct → 2 fragments | 1 molecule → 1 isomer |
| rank | **strictly descends** (adduct rank > each fragment) | **rank-flat** (product formula == reactant formula) |
| `forget()` image | a valid `DecompositionEdge` | **none exists** (see §2) |
| kernel | degree-preserving, accepted | degree-preserving `(2,3,2,2,3,2)`, accepted |

A retro-DA is a *decomposition*; a Cope/Claisen is an *isomerization*. The kernel (`smartchem.rule_calculus`) accepts
both — a [3,3] shift breaks one σ, forms one σ, and migrates two π, preserving every atom's bond-order sum — but the
*decompiler / route-search consumer seam* only carries strict rank-descent.

## 2. The W1 structure theorem (reproduced end-to-end this round)

`DecompositionEdge` (`smartchem.decompiler`) enforces invariant **W1**: *"every product has strictly smaller
`Formula.rank` than the reactant."* That is what makes the recursive `search_routes` descent **terminate**. A
rank-flat rewrite has product rank == reactant rank, so it has **no** admissible `DecompositionEdge` image.

This round confirmed the collision is on the *search* path, not merely the decompiler:

```
search_routes → _conditions_for → assembly_conditions → capped.forget()   # sourced-conditions lookup
forget() → DecompositionEdge(rank-flat product)  → DecompilerError (W1)    # and assembly_conditions does not catch it
```

So a lateral edge **cannot** ride `search_routes`. Forcing it in would either crash (an uncaught W1 error) or, if the
guarantee were relaxed, break termination — **unsound**. This is a theorem about the seam, not a bug.

## 3. What is BUILT (the sound core) — `smartchem/lateral_rewrite.py`

* **The [3,3] rules**, kernel-verified and round-tripping: `COPE` (all-carbon 1,5-diene) and `CLAISEN` (array atom 2
  = O; allyl vinyl ether → γ,δ-unsaturated carbonyl). A generic `_SigmatropicFamily` descriptor derives each rule's
  `retro` / `signature` / `center`, so Cope, Claisen and any future family (electrocyclization, aza-Cope, …) ride one
  factory.
* **A guarded standalone enumeration** `sigmatropic_rewrites(family, molecule)` — the lateral analogue of
  `retro_da_disconnections`. Guards (each a fail-closed drop): locality (the six matched atoms induce exactly the
  array), no exocyclic multiple bond on a matched atom, **neutral-valence** on every matched atom (the DA guard-2c
  bound, reused so a Claisen O never appears over-valent), class-witness + kernel-verify + independent
  reconstruction, **single molecule** (an isomerization, never a fragmentation), and **canonical non-degeneracy** —
  a self-map is dropped. NB the drop uses *canonical molecular identity* (`resonance_identity`), not the raw
  `BondGraph.digest`, which is a presentation hash: the parent 1,5-hexadiene Cope maps to a renumbered copy of
  itself, whose raw digest differs but whose canonical identity does not.
* **A rank-flat `LateralRewriteEdge`** carrying the same double certificate the DA edges carry — (1) mass/charge
  conservation via a real `Reaction`, (2) [3,3]-ness re-derived from the reactant. Conservation alone proves nothing
  here (every isomer balances mass), so certificate (2) is the load-bearing one. Its **`forget()` RAISES**
  `LateralRewriteError` — the honest W1 boundary made executable, so a lateral edge can never be dropped into a
  `search_routes` registry. A step is built with `ExperimentStep.from_transform`, which reads
  `reactant`/`products`/`reaction_center` and never calls `forget`.
* **Two oracle recognizers** `_cope_rearrangement` / `_claisen_rearrangement` (the 11th and 12th active reaction-type
  classes, and the first **1→1** recognizers). Same three-layer discipline as the DA recognizers: Layer A re-derives
  the guarded [3,3] from the step's own molecule, Layer B pins the exact family centre, Layer C fail-closes on an
  absent centre. A cheap `len(reactants)==1 and len(products)==1` early-out keeps them a no-op on the common (2→1 /
  2→2) production step.

## 4. The REACHABLE consumer (why this is not a fabricated feature)

Per the R32 pattern, a soundness-critical feature needs a reachable consumer. The consumer here is the production
reaction-type oracle itself: **a route containing a [3,3] step is now VOUCHED instead of demoted as "unrecognized
reaction type."** `ExperimentRoute.of` accepts a hand-assembled or literature step, so a Claisen route is a real,
buildable input to `route_reaction_type_blockers` today — `test_a_hand_built_sigmatropic_route_is_vouched_not_demoted`
demonstrates it. What is *deferred* is only the automatic *discovery* of such routes by the recursive search.

## 5. What is DEFERRED (the epic), and what would unblock it

**Auto-discovery of isomerization routes by `search_routes`.** It needs a lateral conditions/search path that does
NOT route through the strict-descent decompiler (`assembly_conditions` → `forget()` → W1). Options for a future round:
a lateral-aware `_conditions_for` that recognises a rank-flat edge and looks up conditions by a non-decomposition
signature; or a separate depth-bounded isomerization sweep with an explicit cycle guard (an isomer graph can loop
A→B→A, so it needs canonical-state dedup — the kernel's `bounded_closure` already dedups by full graph value and
declares state-preserving cycles legal, which is the natural substrate). Neither is built here; both are scoped as
future work. The seam's core (rules + enumeration + edge + recognizers + a reachable consumer) is what this round
ships.

## 6. Scope honesty

Structural type-validity only (Problem A): a witness means "this is a structurally valid [3,3] sigmatropic
isomerization," never that it is feasible, thermally allowed at a given temperature, or selective. Cope's parent
(1,5-hexadiene) is degenerate and correctly yields nothing; a substituted Cope (e.g. 3-methylhexa-1,5-diene) and the
Claisen (allyl vinyl ether → pent-4-enal) are the non-degenerate demonstrators. Electrocyclizations and other
sigmatropic families (aza-Cope, oxy-Cope, [2,3]) are trivial future adds on the same `_SigmatropicFamily` factory.
