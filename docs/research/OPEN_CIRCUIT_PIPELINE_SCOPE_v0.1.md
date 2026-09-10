# The circuit pipeline — a second-domain step/route/cost consumer of the open SMC (item 1, EM scope)

Status: **built, sound, bounded.** Lane B. `[[electromagnetic-scope]]` `[[categorical-reorientation]]`

Item 6 proved the `open_core` decoration slot hosts a non-additive physical apex (`ResistorDecoration`), but it
was a **demonstration** consumer — `resistor_edge` was called only from tests/probes (the zero-call-sites gap the
Move-5 deferral named as its missing evidence). This round closes that gap with a real **ingest** and a
**route/step shape**: a second physical domain now flows through the SAME generic open SMC
(`smartchem/open_core.py`) that the chemistry layer rides, end to end.

## What is built (`smartchem/open_circuit_pipeline.py`)

- **`from_circuit(diagram, model)`** — lift an ARBITRARY production resistor network (a
  `smartchem.open_diagram.OpenDiagram` presentation + its `ResistiveDCModel`, the live electrical core *with a
  solver*) into an `open_core.OpenDiagram`. It reconstructs the topology **directly** — one `resistor` hyperedge
  per structural edge, the old core's own node indices carried through — and attaches the apex the production
  `blackbox_resistive_dc` computes for the whole network. Because it reconstructs directly rather than
  compositionally, it handles **series, parallel, AND genuinely non-series-parallel networks (a Wheatstone
  bridge)** that `then`/`tensor` cannot build. *(The old core already exposed everything needed —
  `structural_edges()` + `input_nodes`/`output_nodes` — so no new "junction-extraction API" was required; the
  ROADMAP's assumed prerequisite dissolved on contact with the source.)*
- **`parallel(left, right)`** — the parallel-merge primitive at the DIAGRAM level: tensor two 1→1 stages (a 2→2
  block-diagonal diagram), then merge the two input nodes into one and the two output nodes into one — the
  correct parallel topology — and carry the exact `R₁‖R₂` apex via `ResistorDecoration.parallel_combine`. This
  **closes item 6's deferred parallel CONSTRUCTION**: parallel is now constructible with an exact apex, not only
  reconstructible via the solver.
- **`equivalent_resistance(diagram)`** — the domain COST read: the two-terminal resistance off a 1→1 apex
  relation, fail-closed to `None` for an open/short-in-a-non-resistor-form/non-two-terminal apex. It extracts `R`
  off the canonical RREF **and verifies `relation == resistor_relation(R)`**, so it never fabricates a resistance
  for something that is not a pure two-terminal resistor. `R=0` (a wire) is a valid finite answer.
- **`within_spec(diagram, lo, hi)`** — a Move-5 SURVIVAL PREDICATE over that cost (finite resistance inside a
  band), the circuit-domain analogue of the chemistry survival fraction. Fail-closed: an open/short/non-two-
  terminal apex never survives.
- **`CircuitStage` / `CircuitRoute`** — the route/step SHAPE. A stage is a 1→1 lifted circuit (a resistor via
  `CircuitStage.resistor`, an ingested sub-network via `CircuitStage.ingest` → `from_circuit`, or a parallel
  block via `CircuitStage.in_parallel` → `parallel`); a route composes stages **in series through the generic
  `open_core.then`**, and the cost + survival read off the assembled apex. `from_circuit`, `parallel`, and
  `resistor_edge` all get genuine pipeline call sites here — this is a pipeline, not a demonstration.

## The parallel-merge primitive — the correct-apex counterpart to `plug_all`

Item 6 flagged `open_core.plug_all` as a hazard: it merges nodes but passes the apex through UNCHANGED, leaving a
stale, wrong-width relation on a resistor diagram (correct only for a gluing-invariant/additive decoration).
`BoundaryLinearRelation.parallel` (new, in `smartchem/resistive_dc_schema.py`, the sibling of `.then`/`.tensor`)
is the RELATION-level merge that does it **right**: it identifies each boundary potential across the two operands
(shared `V`), sums the two inward currents at each port (`I = I_self + I_other`), and existentially eliminates
the branch currents via the same verified `_project_relation` machinery `.then` uses. So the diagram-level
`parallel` merges nodes for the topology **and** installs the correctly-recomputed apex — no stale relation rides
through.

## Soundness — cross-checks of two DIFFERENT provenances (the common-mode caveat, stated)

Every apex is checked against `resistive_dc_verifier._expected_relation` — an independently-**typed**
re-derivation that imports NEITHER the schema's relation algebra NOR the `blackbox` solver the pipeline adapts.
An adversarial structure-theorem review (dalembert) named the honest limit: `_expected_relation` and `blackbox`
are the **same nodal-Laplacian elimination coded twice**, so their agreement (6000 random topologies, 0
disagreements) bounds implementation **typos**, not a shared algorithmic assumption — it is not a fully
independent bearing. So the scalar equivalent resistance is **also** checked against a **physically distinct**
oracle: `_spanning_tree_resistance`, the weighted **matrix-tree** effective resistance (a combinatorial sum over
spanning trees and 2-forests — no Laplacian, no elimination, no common-mode). The two agree on series, parallel,
and the bridge. Confirmed (`experiments/open_circuit_pipeline_probe.py`, FROZEN_HASH `33bc257c…`, RDKit-free so
it runs in the committed baseline):

- `from_circuit`'s apex equals the independent verifier on **series, parallel, and a Wheatstone bridge**;
- the FUNCTOR law: `from_circuit(A).then(from_circuit(B))` equals the solver on the old-core series `A then B`
  (and the item-6 `resistor_edge` construction) — the pipeline agrees with the algebra where they overlap;
- the parallel-merge equals the `R₁‖R₂` closed form AND the independent oracle, commutes, is associative, and is
  non-vacuous (`R₁‖R₂ ≠ R₁+R₂`);
- the cost + survival predicate read correctly and FAIL CLOSED on an open circuit;
- a mixed series/parallel `CircuitRoute` assembles through `open_core.then` and its cost equals the closed form.

## The Move-5 claim, bounded honestly

This is a second-domain **demonstration pipeline** — a self-contained route/step/cost/survival shape with a live
ingest and an independent-oracle cross-check. Its **internal consumer graph is real** (`CircuitRoute.assemble` →
`open_core.then`, `CircuitStage.ingest` → `from_circuit`, `CircuitStage.in_parallel` → `parallel`, cost/survival
read the assembled apex) — the genericity evidence Move 5's deferral named as missing, and exactly what item 6's
`resistor_edge` (zero call sites) lacked. **But** — by this project's own zero-call-sites standard, judged
honestly (birdperson) — nothing OUTSIDE this module + its test/probe yet plans, ranks, or verifies a circuit
through this shape. So it **strengthens** the Move-5 case (the genericity is now exercised end to end by a real
consumer graph); it does **not complete** Move 5. The full domain-neutral refactor making the CHEMISTRY
`ExperimentStep`/`ExperimentRoute` literally parametric over a "conserved-inventory transition + survival
predicate" remains its own large round, and **this pipeline still awaits its first non-test caller**. (Naming the
residual honestly, against the last-round over-claim lesson.)

## Boundary (sound deferrals)

- **Ideal DC resistors only** (no RLC/AC) — the item-6 scope.
- **Compositional construction** covers series (`.then`), juxtaposition (`.tensor`), and now parallel
  (`parallel`). A general non-series-parallel COMPOSITIONAL builder (assembling e.g. a bridge from parts through
  the generic ops) stays deferred — but `from_circuit` reconstructs such networks **directly**, which subsumes
  the need for the pipeline consumer, so nothing here depends on it.
- `equivalent_resistance` is defined for **1→1** stages (a two-terminal equivalent); a multi-port equivalent
  (an n→m network's full relation is its apex, but there is no single scalar "resistance") is out of scope.

## Files

- `smartchem/open_circuit_pipeline.py` — the pipeline (from_circuit, parallel, equivalent_resistance,
  within_spec, CircuitStage, CircuitRoute).
- `smartchem/resistive_dc_schema.py` — `BoundaryLinearRelation.parallel` (the relation-level merge).
- `smartchem/open_resistor_diagram.py` — `ResistorDecoration.parallel_combine`.
- `experiments/open_circuit_pipeline_probe.py` — the FROZEN_HASH evidence harness (vs the independent verifier).
- `tests/test_open_circuit_pipeline.py` — unit coverage of every primitive + error paths.

## Adversarial review — three orthogonal bearings before merge

**The engine is sound; the folds were all guard-rails and framing.** No bearing found a wrong `R` on any
well-formed network.

- **evil-morty (directed break):** the physics survived a 2266-network + 3000-parallel-tree fuzz against the
  oracle, 0 mismatches. Folds: (1) the compositional path (`resistor_edge`/`CircuitStage.resistor`) accepted a
  **negative** resistance the ingest path refused → `for_resistor` now refuses `R<0` and `equivalent_resistance`
  fails closed on a negative candidate; (2) `within_spec` raised `OverflowError` on `float('inf')` and silently
  took the binary expansion of a finite float → now accepts `±inf` sentinels and refuses finite floats; (3)
  `apex_matches_boundary`/`_require_two_terminal_resistor` documented as width/type gates, not correctness.
- **dalembert (structure-theorem refutation):** all three claims SURVIVED. The multiport (`p,q>1`) branch of
  `BoundaryLinearRelation.parallel` was proven correct against an independent image-space oracle (4000 random
  multiport relations, 0 mismatches) → kept general, cited, and given a committed 2→1 cross-check. His main
  construction-to-reinforce — the "independent verifier" is common-mode with `blackbox` — drove the addition of
  the physically-distinct spanning-tree oracle above.
- **birdperson (principled soundness):** SOUND-BUT-HEED. Folds: the residual "not a demonstration" over-claim
  relabeled honestly (above); the "topology is decorative" doubt closed by making the topology load-bearing
  (`from_circuit` mirrors the source edges; `parallel`'s merge canonicalizes byte-identically to the direct
  reconstruction); `parallel`'s placement in the trust-boundary schema judged SOUND (homogeneous with `.then`).

All folds are committed with tests; the FROZEN_HASH is unchanged (the folds added checks, not payload).
