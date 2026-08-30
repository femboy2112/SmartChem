# Structure decompiler — reality-respecting ladder

**Question.** Can the structure decompiler recompile chemicals of increasing difficulty into their
constituent fragments and byproducts, and is every emitted output *reality-respecting* — in the
W3-bounded sense the repo means (conservation, valence-validity, structural fidelity, honest
labelling, honest termination), never a physical prediction of which reaction occurs?

**Harness.** `experiments/structure_decompiler_ladder.py` — a self-reporting gate (exit non-zero on
any hard violation). 36 entries across 8 difficulty tiers: trivial hydrides → small chains →
unsaturation/heteroatoms → single rings → substituted aromatics → drug-sized targets → fused /
heteroaromatic-as-Kekulé → ionic/redox. Each is parsed through the SMILES front door (parser formula
checked against the declared Hill formula), decomposed, and every edge audited against an
**independent** recompute — not the edge's own certificate (avoiding a check derived from its own
subject).

## Result (2026-08-30)

```
audited: 2888 scission edges, 2888 independent valence recomputes, 2888 forget() projections,
         5821 species labels, 14 charge/mass conservations.
VERDICT: PASS
```

Every one of the 2 888 emitted scission edges: conserves every atom, passes the independent
`verify_valence_integrity` recompute, projects via `forget()` to a valid formula-level v1 edge whose
products re-sum to the reactant composition, and labels every open-valence fragment RADICAL / every
ionic product ION (never a reactive fragment dressed as an isolable compound). Every decomposable
target produced edges (hard **non-vacuity** — a green run cannot be green over an empty subject). All
14 ionic/redox checks conserve charge and mass, with the electron massless (`ELECTRON.atoms == ()`).

## The one defect the ladder caught — and the fix

`StructureDecompositionGraph.is_complete` (status `COMPLETE`) documented itself as "a full descent to
**single atoms**", and the class prose said the descent "bottoms out at single atoms." That is an
**over-claim** on any molecule with a ring: at `max_cut_bonds=1` no single cut can open a ring (a ring
bond is not a bridge), so benzene / cyclohexane / cyclopropane / phenol / aniline / naphthalene /
pyridine each finish `COMPLETE` yet bottom out at an irreducible **carbon-ring core** (C3, C6, C10,
C5N), not at single atoms. A caller trusting `is_complete` + `terminals()` would silently believe a
benzene ring came apart into six carbons.

Not a conservation break — a **labelling** over-claim, the exact class of defect this repo guards
against hardest, and a W3 concern (the engine must never claim more than it did). The surgical fix
(commit alongside this receipt):

* corrected the over-claiming docstrings (`is_complete`, the class prose, `terminals()`);
* added `StructureDecompositionGraph.irreducible_cores()` — the non-atomic leaves no admissible cut
  can open — so the boundary is **auditable**, not silently claimed;
* added `reaches_single_atoms` — the precise "did it actually atomise?" predicate `is_complete` was
  mistaken for (a `COMPLETE` graph with no cores).

After the fix the ladder re-runs the audit through the engine's **own** accessors and cross-checks
`reaches_single_atoms` against a fully independent from-scratch recompute; a disagreement is now a hard
failure. All 7 ring targets report `reaches_single_atoms=False` with their core surfaced, verified.
Pinned by `tests/test_structure_descent.py::TestIrreducibleCoreHonesty`.

## What this does NOT establish

* **W3 unchanged.** Not one edge is a claim that a cleavage *occurs*, at what rate, or which is
  favoured. The ladder certifies structure (conservation, valence, fidelity, honest labels), never
  physics. "Reality-respecting" here means the graph facts hold on real molecules — not that the
  decomposition is a reaction that happens.
* **Symmetric aromatics only.** Every registered ring is benzene / mono- / para-substituted, whose two
  Kekulé forms are isomorphic so the canonical washes the choice out. An **asymmetric** aromatic has
  Kekulé-form-specific identity (the documented resonance/constitutional boundary); the ladder does
  not yet exercise it, and it remains the top open reality-respecting boundary.
* **Single ionic level.** Heterolysis splits neutrals only; recursive ionic descent of an
  already-charged ion is a documented next rung.
* **Runtime is shape, not a benchmark** — full atomic descent of a substituted aromatic is several
  seconds of aromatic H-stripping, so the three heaviest tier-4/5 targets run depth-bounded
  (`COMPLETE_TO_DEPTH`); every invariant is still audited on their real edges.
