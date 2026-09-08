# The provider algebra as a generating set of the open SMC (categorical reorientation, Move 3)

> **Status:** formalization shipped as falsifiable laws — `tests/test_provider_category.py`. No new runtime
> machinery, no digest/golden movement. This note is the honest categorical statement the arc's Move-3 one-liner
> ("the free open-monoidal category on typed generators; IR-COMMUTE is the coherence law") pointed at, *corrected*
> against the tree by two independent pre-build design bearings.

## Why this is a formalization, not a build

Move 3 asked to formalize the transform-provider registry (`smartchem/transform_provider.py`) as a free monoidal
category. Recon + two pre-build reviews (a soundness bearing and a YAGNI bearing) converged on one uncomfortable
fact: **the categorical structure the arc wanted already exists and is already live.**

- `open_core` / `OpenChemDiagram` **is** the open symmetric monoidal category (R24/R25): real `then`/`tensor`/
  `plug_all`/`braid`/`identity`, and its coherence laws (interchange, braid, hexagon) are already proven under the
  `canonicalize` quotient (`tests/test_open_chem_diagram.py`, `tests/test_open_diagram.py`).
- The registry's providers **are** a generating set of morphisms. `TransformProviderRegistry.enumerate` is the sole
  seam of the bounded search — three live call sites (`compilation_ir.py:1680`, `routes.py:523`, `routes.py:758`),
  AST-pinned by `tests/test_provider_locality.py`. "Add a family without touching the shell" is the whole design.
- The functor's action on *words* is already live: `route.open()` / `dag.open()` compose the lifted single-step
  diagrams (via `tensor`+`plug_all` in `open_chem_diagram._assemble`), and that surface is consumed by the M2 ranker
  (`meta_compile`).

So building a new free-category runtime (a `TransformGenerator` wrapper, a `free_functor` universal-property fold)
would be **decorative parallel machinery whose only caller is its own test** — exactly the zero-call-sites failure
mode `THE_DIFFERENCE.md` was falsified for. The honest deliverable is to *name* the structure that is there and
*guard* it with falsifiable laws, and to correct three over-claims in the arc's own language.

## Three corrections to the Move-3 slogan

1. **NOT "the free category" — a semantics functor `F`.** Freeness is a universal property (any functor out is
   determined on generators, *with no relations beyond coherence*); we have not proven the absence of imposed
   relations, so "the free category" is unearned. What is provable, and what the laws pin, is a **functor `F` from
   the registry's generating morphisms into the open SMC**, whose action on one generator application (an
   `EnumeratedTransform`) is `ExperimentStep.from_transform(t).open()`.

2. **NOT "IR-COMMUTE is the coherence law" — it is a forgetful naturality square.** IR-COMMUTE
   (`tests/test_ir_commute.py`) asserts, per family, `forget(D_structure(S)) ⊆ D_formula(forget(S) | closure)` — a
   relation *between two functors* (structure-descent and formula-descent) at the **Formula layer**. It is a
   naturality/agreement datum, never an associativity/interchange law *within* the monoidal category. The genuine
   SMC coherence already lives in and is already tested on `open_core`; Move 3 does **not** re-prove it. Law 3 below
   restates IR-COMMUTE's spirit at the correct (Molecule) altitude.

3. **NOT "typed generators" (hom-restricting) — provenance-tagged generators.** A provider's
   `(witness_kind, projection_kind)` pair is a provenance tag, not a composition-gating hom-type. At the Molecule
   altitude composition is **total**: a heterolytic scission's charged products can feed a capped scission; nothing
   in the type discipline forbids a `then`. The tags decorate; they do not constrain the category. Law 1 pins that
   this provenance never enters `F`'s compared image (the R24 congruence discipline).

## The functor `F` and its on-generators action

`F: ⟨registry generators⟩ → OpenChemDiagram`, defined on a generator application by
`F(t) = ExperimentStep.from_transform(t).open()`. Two design notes:

- **Altitude.** `F` lifts through the *Molecule*-level transform interface (`transform.reactant/.products/.reagents`
  are `Molecule`s), never through `transform.forget()` — `forget()` returns a **Formula-layer** edge (bond-free,
  `structure_descent.py:674`), which has no canonical section back to a Molecule (isomers), so it is the *wrong*
  lift into a Molecule-altitude diagram. `forget` is a *parallel* functor into the Formula base, not a route into
  the SMC. (Law 3 is the agreement of these two functors on generators.)
- **No shipped combinator.** `F`'s on-generators action is *not* a new public function. There is no live consumer
  that wants an `EnumeratedTransform`→diagram lift which `ExperimentStep.open()` does not already serve, and shipping
  a combinator whose only caller is a test would re-open the zero-call-sites trap. The laws express `F(t)` inline as
  `ExperimentStep.from_transform(t).open()`; the framing names it, the code stays where the callers are.

## The three laws (all in `tests/test_provider_category.py`, all with non-vacuity controls)

1. **Provenance is out of the categorical identity** — a *forward change-detector* for the R24 congruence hazard
   (`a-quotient-must-be-a-congruence`), not a proof of a congruence theorem. Two registries emitting the *same*
   transform under *different* provider identities (`provider_id` "capped-A" vs "capped-B") lift to the *same*
   canonical diagram. Honestly: provenance is *structurally absent* from `F`'s domain — `from_transform` receives
   only the bare transform, never the `EnumeratedTransform` wrapper that carries `provider_id` — so the congruence
   question does not arise while nothing threads provenance in. This law reddens the day someone does thread it in,
   which is exactly the edit that *would* create the R24 hazard (equal-now, diverge-after-one-compose).

2. **`F` quotients symmetric cuts, and is faithful on distinct reactions.** The four symmetric ways to cut ethane
   are four distinct transforms (distinct `transform.digest`) but ONE reaction — and `F` maps all four to a single
   canonical diagram. This is `comparing-fixed-representatives-fabricates-a-distinction` as a *theorem*: `F` sees the
   reaction, not the bond-cut choice, so it fabricates no distinction between equivalent cuts. Faithfulness holds
   where the chemistry genuinely differs: a capped scission and a bond-order edit of the same target are different
   reactions and lift to distinct diagrams.

3. **`forget`/`open` naturality — the two projection functors agree per generator** (IR-COMMUTE at the SMC
   altitude). For every generator `t`, the net reaction of `F(t)` is the exact *reverse* of `t.forget()`
   (`from_transform` reads a decomposition backwards into a synthesis); species agree as multisets. Honest scope:
   both functors read the *same* `transform` fields, so the check is **common-mode on the product multiset itself**
   (a wrong product molecule cancels on both sides) — what it genuinely catches is the dom↔cod *reversal
   orientation* and a Molecule↔Formula altitude divergence, not the correctness of the products (which the
   conservation certificate owns). A consistency/orientation datum tying the two functors on the shared generating
   set, not an independent oracle.

## What was considered and DROPPED (the honest boundary)

A fourth "law" was proposed — *branch-order interchange*: reorder a convergent DAG's two independent branches and
assert the projected diagrams are canonicalize-equal. **It is false as stated, and grounding caught it before it
shipped.** The open diagram's external boundary is *ordered* (`open_core` Interface: position is identity), so
`branch_acid, branch_alcohol, esterify` and `branch_alcohol, branch_acid, esterify` project to genuinely *different*
morphisms — same structure, different domain object — reconcilable only *up to a boundary braid*. Proving that
reconciliation is exactly `open_core`'s already-tested braid-naturality. So the branch-order statement is either
false (naive form) or a re-proof of coherence that already lives one layer down (a mirror). We keep the honest
scope: **SMC coherence lives in `open_core`; the search's assemblies inherit it; Move 3 asserts the functor lands
there, not that it re-establishes coherence.**

## What is deliberately NOT claimed

- No claim of freeness (universal property), only of a semantics functor.
- No new runtime object, no change to `DEFAULT_TRANSFORM_REGISTRY` (its `digest` feeds `search_algebra_digest` →
  route/DAG receipts; a provider-set/order/version/manifest change would churn those digests — out of scope here).
- No re-proof of SMC coherence; that is `open_core`'s, and stays there.
- Cross-family composition is *total* at the Molecule altitude; the laws do not restrict hom-sets by provenance.

The result: the transform algebra is now categorically legible (a generating set + a semantics functor into the
proven open SMC) and law-guarded, with every over-claim in the original slogan corrected against the tree.
