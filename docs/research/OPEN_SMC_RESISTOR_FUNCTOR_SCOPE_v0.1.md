# Open-resistor semantics — a non-additive decoration on the open SMC (item 6, EM scope)

Status: **built, sound, bounded.** Lane B. `[[electromagnetic-scope]]`

Ideal DC resistors and their **series/juxtaposition compositions** are now functor images of the SAME generic
open SMC (`smartchem/open_core.py`) that the chemistry layer rides — the compositional (`then`/`tensor`)
subcategory of resistor networks. This is concrete evidence toward Move 5's generality claim: `open_core`
demonstrably hosts a second, physically different domain, not chemistry wearing a coat.

## What is built

- **`ResistorDecoration(open_core.Decoration)`** — a resistor network's apex is its exact boundary linear
  relation (`resistive_dc_schema.BoundaryLinearRelation`, exact `Fraction`). `then_combine` is series composition
  (`.then`, a Schur elimination of the shared interface); `tensor_combine` is disjoint juxtaposition (`.tensor`).
  Both are the production-tested exact operations; the class only adapts them to `open_core.Decoration`, with an
  `isinstance` guard that rejects a mixed-domain apex loudly.
- **`resistor_edge(ohms)`** — one ideal resistor as a 1→1 `open_core.OpenDiagram` (two electrical nodes, one
  `resistor` hyperedge, the `ResistorDecoration` apex), mirroring `OpenChemDiagram.single_step`. `open_core`'s
  `then`/`tensor` then compose resistor networks and its `canonicalize` quotient applies.
- **`resistor_relation`/`for_resistor`** — the generator, `V_dom − V_cod = R·I_dom`, `I_dom + I_cod = 0`,
  calibrated to be identical to the production `blackbox_resistive_dc` single-resistor relation (and `R=0` is
  exactly the boundary-relation identity — a wire). Resistances are exact rationals only; a float is refused.

## The prize — a non-additive decoration

The chemistry apex (`ConservationDecoration`) is an ADDITIVE monoid. A resistor apex is not: series adds
resistance, but the relation composes by elimination, and the parallel law is `1/(1/R₁+1/R₂)`. The committed
**interchange-law property test** (with a non-vacuity control) proves `ResistorDecoration` satisfies
`open_core.Decoration`'s interchange-invariance obligation anyway — the FIRST non-additive apex proven to satisfy
it, so `open_core` demonstrably hosts a second, physically different domain. (The law is a theorem of the linear-
relation SMC ground; the property test is a regression tripwire on that, not evidence the apex is special — it
holds for free for any correct SMC-valued decoration, so the prize rests on `BoundaryLinearRelation`'s
production-tested SMC correctness.) This is the *demonstration* whose absence made `open_core`'s genericity
conjectural; a full Move 5 lift still wants a circuit *pipeline* consumer (see below).

## Soundness — non-circular cross-check

Every relation is checked against `resistive_dc_verifier._expected_relation` — an independently-written
Kirchhoff/Laplacian re-derivation that imports NEITHER the schema nor the solver this bridge adapts — never
against the thing it mirrors (the trusted-green-mirror trap). Confirmed: `open_core`'s `then` composition equals
the independent verifier's re-derivation on a two-resistor series network, and the closed-form `R₁‖R₂` equals the
independent re-derivation on a genuine parallel junction. The oracle is in-repo, so the probe runs in the
committed baseline (no dev-only install, unlike the CIP rdkit oracle).

## Boundary (bounded scope, honestly stated)

- **The functor is built on the series/juxtaposition subcategory** (`then`/`tensor`) — the reachable networks are
  exactly series chains and disjoint juxtapositions. **Electrical parallel is NOT constructible** via `then`/`tensor`
  (it needs a merge/plug `open_core` does not offer in the sanctioned set): only its boundary relation (`R₁‖R₂`) is
  validated against the independent oracle, **not its construction**. A general non-series-parallel **bridge** is
  deferred the same way. Reconstructing an arbitrary network's full `open_core` node/edge topology — a
  `from_circuit` over the old-core `Junction`/`ComponentSlot` spec, plus a parallel-merge primitive — is the
  **named next brick**; the old core (`open_diagram.py`) exposes only `node_for` publicly, so it needs a small
  topology-extraction API first.
- **`plug_all` is an UNENFORCED CONVENTION, not a runtime guard.** `open_core.OpenDiagram.plug_all` passes the apex
  through UNCHANGED — correct only for a gluing-invariant (additive) decoration. A boundary relation is NOT
  gluing-invariant (gluing eliminates internal variables), so `plug_all` leaves a stale, wrong-width relation with
  **no error** (proven by a guard test: a 1→1 plugged diagram whose apex is still the 2→2 juxtaposition).
  `plug_all` is a method on the shared frozen `OpenDiagram` this module cannot override, so the functor never calls
  it, and `apex_matches_boundary(diagram)` lets a caller fail closed on a stale apex. The **proper enforcement** — a
  gluing-invariance flag on the `Decoration` contract plus a core `plug_all` check — is future work in the shared
  `open_core`. Resistor networks compose via `then`/`tensor` (which DO combine the apex).
- **DC ideal resistors only** — no RLC/AC migration; the `rlc_ac` stack stays on its own core.
- **The closed PR-#3 branch was NOT salvaged.** Its `resistive_dc_schema` predecessor does not exist there;
  mainline's schema/verifier split is strictly more mature. Nothing to rebase.
- The interchange-invariance obligation is proven for the tested compositions; a general algebraic proof over ALL
  reachable `then`/`tensor` gluings rests on the Baez–Fong compositional-networks theorem (the relation category is
  symmetric monoidal) and is stated as its ground, not re-proven here — the property test is a regression tripwire
  on that ground, not an independent proof (the law holds for free for any correct SMC-valued decoration).

## Why this matters (the arc)

`open_core` was written domain-neutral (Move-1 keystone Rung B) but had ONE consumer: chemistry. Item 6 gives it a
second, structurally different decoration, **demonstrating** that the genericity is real — a non-additive apex that
satisfies the interchange obligation exists. **Judgment, not measurement:** this is a *demonstration* consumer
(`resistor_edge` is called only from the probe and tests), so it proves genericity is *possible*; it is NOT yet a
production circuit *pipeline* (route/step/DAG) that would *drive* a domain-neutral lift. It strengthens the case
for revisiting Move 5 but does not by itself clear Move 5's stated bar (a genuine multi-step non-chemistry pipeline
consumer) — that wants the `from_circuit` + circuit-route next brick first (the zero-call-sites lesson). See
`docs/research/MOVE5_DOMAIN_NEUTRAL_PARAMETERIZATION_SCOPE_DECISION_v0.1.md`.

Evidence: `smartchem/open_resistor_diagram.py`, `experiments/open_resistor_functor_probe.py`,
`tests/test_open_resistor_diagram.py`.
