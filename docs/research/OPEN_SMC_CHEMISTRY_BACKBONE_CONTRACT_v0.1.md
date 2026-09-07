# SmartChem: Open-Diagram SMC as the Chemistry Morphism Backbone — Move-1 Keystone Contract v0.1

**Status:** proposed research contract (design gate; no code change in this document)
**Date:** 2026-09-07
**Research branch:** move1-open-smc-keystone-2026-09-07
**Baseline:** main at 0e6bba04f797a7ad66ca4c3b290a08fe1e848904 (Round 23 merged)
**Review status:** hardened after two independent adversarial reviews (evil-morty, birdperson) that both converged on a central defect in the first draft's acceptance gate. Those findings and the design changes they forced are recorded in the final section; this document is the folded result, not the draft they read.
**v0.2 revision (2026-09-07):** folded the free-energy-landscape framing (`FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md`). Two changes, both **sharpening not rescoping**: (a) the Level-2 decoration mechanism is respecified as a **general monoidal-decoration slot** (§"the keystone"), of which Rung B still instantiates *only* conservation + provenance, so the already-built ΔG (`feasibility.py`) and survival (R23) functors and later observability ride the *same* slot rather than forcing a second refactor; (b) the precedent is upgraded to the on-point Baez–Pollard *open reaction networks* + black-boxing-to-steady-states (§"precedent"). No obligation (P1–P4), no gate (§6), and no boundary (§"boundaries") changed.
**Scope:** morphism-representation semantics and a phased migration contract only. No laboratory procedure, execution authority, or claim that any route is safe, practical, legal, or bench-ready. This is the review gate that must clear **before** the Lane-A-touching core modules (`smartchem/category.py`, `smartchem/experiment/step.py`, `smartchem/experiment/dag.py`) are altered.

This is the **keystone** (Move 1) of the categorical reorientation the user opened on 2026-09-07. Its Move-2 rung 1 — the duration-survival functor — already shipped in Round 23 (`smartchem/experiment/composability.py`). This is the higher-care structural move the rest of the plan (Moves 3–6) sits on top of.

---

## Decision

**Give chemistry morphisms an open symmetric-monoidal backbone, and demote conservation from a construction-time gate to a closure predicate — reusing the *composition core* the repository already proves lawful (`smartchem/open_diagram.py`) and generalizing its electrical *construction layer* to a chemistry hypergraph layer.**

Concretely:

1. A chemistry process becomes an **open diagram**: a morphism whose domain and codomain are ordered, typed **boundary interfaces** (ports), with the reaction content on an apex. Each reaction step is a **multi-terminal hyperedge** (N reactants → M products), not the two-terminal edge the current electrical layer models.
2. **Morphism identity is taken under a structural quotient** (mirroring `open_diagram.canonicalize`): two diagrams that differ only in the schedule order of *independent* steps are equal. This is what makes the interchange law hold — and it quotients away only a *linearization artifact*, never the causal trail (see "the central knot" below).
3. **Conservation of mass and charge stops being a prerequisite for a morphism to exist.** It becomes a predicate — `is_closed_and_conserving` — decided on the apex/boundary decoration *once the boundary is saturated* (Baez–Fong / decorated-cospan discipline).
4. The conservation-at-construction theorem is **preserved exactly as the closed-diagram special case** (P1–P4 below). Every existing closed route keeps its byte-identical digest; `tests/test_laws.py::TestConservationTheorem` and `ExperimentStep`'s certificate keep passing unchanged.
5. Chemistry rides the shared core as a **decoration** (a `Config` apex + a conservation certificate + a partial-order provenance record), **not** as a competing definition of what a morphism *is*. Circuits ride the same core with their own decoration. This is the *direction* toward one base category of which both are functor images — a **destination the keystone opens, not a property Rung B delivers** (the functor requires extending `PortKind` and *proving* the decoration lawful, which is Move-6 work; `PortKind` has a single member, `ELECTRICAL`, today at `open_diagram.py:56-59`).

The falsifiable acceptance criterion is re-specified in **§6** to survive the two objections the draft failed: it is met only when the new open representation is **consumed by a real object that is not the interchange test**, and it does **not** flip the legacy `Reaction`-level xfail in place (doing so is either the zero-call-sites trap or a byte-stability violation).

---

## The central knot and its resolution (the hard theorem of this move)

Both reviews converged here, so it leads the contract.

**The tension.** The interchange law *requires* that `(f;g) ⊗ (h;k)` equal `(f⊗h);(g⊗k)` — genuinely the same process assembled two ways. Making that equality hold *requires* quotienting away the order in which independent parallel events were scheduled. But chemistry's `Reaction` equality **deliberately** includes `path` and `generator_word` (`category.py:820-827`) precisely so that two mechanisms with the same endpoints are different morphisms (`category.py:801-816`). Naively, "quotient the schedule" and "preserve the mechanism trail" pull in opposite directions — and the current interchange xfail fails for *exactly* this reason: its two sides are equal on `dom`/`cod` and differ **only** in `path`/`generator_word` (the intermediate `H2 + N + N` vs `H2 + N2`), an artifact `scheduled_product` mints at `category.py:963-983`.

**The resolution — two kinds of order, at two levels.** The recorded trail conflates two distinct things:

- **(i) Genuine causal/dependency order** — which step's product feeds which step — is a **partial order (a DAG)**. This is real provenance; it is interchange-*invariant* (independent steps have no dependency edge between them); it **must be preserved** (P4).
- **(ii) The total-ordering of independent (commuting) steps** — the fact that the left-first schedule wrote `H2+N+N` before `H2+N2` rather than the reverse — is a **linearization artifact**. It is not a mechanism difference; it is an arbitrary choice of representative, and comparing two representatives fabricates a distinction that is not real (the same failure mode this project has hit before under resonance/Kekulé representatives). Interchange quotients away **only this**.

`Reaction.path` today is a *flat linear tuple*, which fuses (i) and (ii) and cannot tell them apart — which is why interchange is unrepresentable on it. The open backbone records provenance as a **partial order of generator steps over ports**, from which any linear presentation is one recoverable linearization. Two interchange-equivalent assemblies produce the **same** partial-order provenance and the **same** net-boundary atom/charge decoration; they differ only in a linearization the DAG never commits to.

**Consequence:** P4 (preserve the causal audit trail) and the interchange law (quotient the spurious linearization) act on *different parts of the trail* and are **both satisfiable**. This is the design's load-bearing claim, and Rung B must demonstrate it concretely (§6, §7).

---

## The non-negotiable invariant (what must survive verbatim)

The current core carries a modest, honest, *pinned* theorem — the hard-won replacement for a grand claim (`THE_DIFFERENCE.md:8-9`: "the categorical machinery it claimed as its differentiator had zero call sites") that was falsified. **The keystone preserves it, not weakens it.**

> **Conservation is enforced once, on generators, and inherited by every composite. A mass-violating reaction is unconstructible, not merely absent.**
> — `THE_DIFFERENCE.md:227-232`, checked in `tests/test_laws.py::TestConservationTheorem`.

Enforcement sites today: `Reaction.__post_init__` (`category.py:879-888`, unconditional `dom.formula==cod.formula` ∧ `dom.charge==cod.charge`); the transitivity schema (`category.py:22-33`; composition inherits conservation *by transitivity, not a re-check*, `category.py:935-936`); `_validate_path` (`category.py:891-929`, per-step conservation + continuity); the `ExperimentStep` certificate (`smartchem/experiment/step.py:113-123`, which already re-raises *both* `ConservationError` **and** the `canonicalize` refusal — see P3).

### The preservation obligations (each testable)

A **closed** diagram has zero OPEN ports (cospan legs = the empty interface): an endomorphism of the unit `I`, every atom in matched by an atom out.

- **(P1) Closed composition still conserves without a re-check.** Composing two conserving closed diagrams yields a conserving closed diagram, via functoriality of the decoration under pushout. *Honest billing (fold of evil-morty F3):* for an **additive** invariant this is **equivalent** to today's transitivity theorem, the two directions mutually derivable — **not** strictly stronger. Its value is not extra strength but that the restatement **composes along pushouts of OPEN diagrams**, which the construction-time gate cannot express at all. It also does **not** dissolve exact endpoint-matching: the base `then` still demands exact interface equality (`open_diagram.py:385-386`), and the shared-foot cancellation that makes conservation compose *depends* on that match. Endpoint-matching was never the disease; see §"the one real defect."
- **(P2) Byte-stability.** Every currently-representable closed route/step/DAG keeps an unchanged `canonical_digest`. The open representation is introduced *alongside* `Reaction` (§7); no golden moves. (Both reviewers could not break this: the only live non-test caller of `scheduled_product` is `cell.py:189-193`, which flows into `electrochemistry.py` — imported by nothing and digested nowhere — so even the `scheduled_product`-replacement path touches no digested route.)
- **(P3) The closed check is byte-identical in effect.** `OpenChemDiagram.close()` on a saturated boundary reduces exactly to today's `Reaction.__post_init__` mass/charge behaviour, including re-raising the `canonicalize` refusal as `step.py:120-123` already does; a mass-violating *closed* diagram remains unconstructible as a closed value.
- **(P4) Provenance survives as a partial order.** The **causal** trail (dependency DAG of generator steps) is preserved and round-trips to/from `Reaction.path`/`generator_word` for the linear case; only the **spurious linearization** of independent steps is quotiented. P4 is a **Rung-B precondition with its own test** (§6), not a postscript — it is the hinge on which the reuse decision and the whole design turn.

**What the keystone relaxes (only this):** the construction-time totality/equality gate — `step.py:101-104` (≥1 reactant/product to exist) and `category.py:879-888` (exact balance checked before the object exists). An *open* diagram with unfilled ports may exist; its conservation is **UNDECIDED until closed**, a different state from *violated*.

---

## What current main already gets right (extend, don't replace)

- **A lawful open SMC composition core already exists** — `open_diagram.py`'s `then` (`:381`, pushout via union-find), `tensor` (`:433`, ordered-port concatenation + disjoint union), `identity` (`:454`), `braid`, and the WL+bounded-brute-force quotient `canonicalize` (`:561-609`). Interchange/braid/hexagon are proven — **under the `canonicalize` quotient** (`test_open_diagram.py:395-396,412`), not under raw `==` (fold of evil-morty F1/F6). This is the machinery the keystone extends.
- **The conservation theorem is real and pinned** (above). Kept.
- **A narrow open-boundary precedent for charge already exists.** `Molecule.carrier` (`category.py:534-562`) lets an electron cross a half-reaction boundary uncounted, but still through the closed gate — the keystone generalizes this one special case.
- **IR-COMMUTE is functorial in spirit** — the four families (`smartchem/transform_provider.py:96,133,162`; `smartchem/bond_order_edit.py:214`) with uniform `forget()`/`equation()`/`digest`, cross-checked in `tests/test_ir_commute.py`. Restated (later) as functors into the base, not rewritten.

---

## The three islands and the one real defect

Three disjoint categorical structures, no functor between any pair: **Island 1** chemistry conserving-histories (`category.py`: objects `Config` `:708` carry bond topology; morphisms `Reaction` `:792`; `then` `:931` needs whole-`Config` equality; the morphism tensor `scheduled_product` `:950` is a left-first schedule — **strict xfail** interchange `tests/test_laws.py:330-343`). **Island 2** the open circuit SMC (`open_diagram.py`: `Interface` `:84`, `OpenDiagram` `:199`; interchange **passes under the quotient**). **Island 3** the oracle `Domain` meet-lattice (`domain.py:110,206`) — a predicate lattice over objects, not a process category. Plus **`electrochemistry.py`**, imported by nothing but its own test and connected to neither island — a free-floating scalar calculator, so the electromagnetic-scope mandate is satisfied only in name.

**The one real defect (corrected from the draft — fold of evil-morty F5).** The draft blamed "whole-state equality vs partial boundary-gluing." That is wrong: `open_diagram.then` *also* demands exact endpoint equality (`open_diagram.py:385-386`), identical in kind to `Reaction.then`'s `cod==dom` (`category.py:938`). Endpoint-matching is not the disease. Island 1 fails interchange for two other reasons:

1. **No real parallel product on morphisms.** `scheduled_product` linearizes independent events left-first (`category.py:963-983`) instead of taking a genuine tensor; the arbitrary order it commits to is what makes the two interchange sides differ.
2. **Identity is raw structural equality over a linear path**, so the linearization artifact is *visible* to `==`. Island 2 passes because it has (a) an ordered-port disjoint-union tensor and (b) equality **under a quotient** that erases internal presentation.

The keystone supplies both: a real tensor and a structural quotient — while keeping the causal DAG and the boundary decoration (which the quotient leaves invariant).

---

## The keystone: open morphisms, conservation as closure, at two levels

Adopt the decorated / structured-cospan pattern on a **shared, generalized core**:

- **Level 1 — structural (the SMC laws).** A morphism is an open diagram `X → N ← Y` with ordered typed boundary ports and an apex of **multi-terminal hyperedges** (generator steps). `then` = pushout along the shared interface; `tensor` = ordered-port concatenation + disjoint union; **identity is the structural quotient** (`canonicalize`). Interchange/braid/hexagon hold here — the same laws already proven for circuits. **The ports are coarse/structural**, so the quotient can act.
- **Level 2 — decorations (the chemistry content), on a *general monoidal slot* (v0.2).** The decoration mechanism is **one general slot**, not a hardcoded field: a decoration is a payload with (i) a declared **combine law under `then`/`tensor`** (a monoid/functor into an ordered target) and (ii) an **interchange-invariance obligation** so it survives the Level-1 quotient. Recon confirmed the core has *no* such slot today (`open_diagram.py` is topology-only; only transient per-edge opaque `str` labels at `canonicalize`; the R23 survival monoid lives in a *different* subsystem, `composability.py:346-363`), so the factored core **adds** this slot and threads it through `then`/`tensor`/`canonicalize`. **Rung B instantiates exactly two decorations** (below); the rest are declared future instances of the *same* slot, so they need no second refactor. This is the fold of `FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md` §2.3 — it changes the *seam*, not Rung B's scope.
  - **Conservation** (Rung B) — the net-boundary `Config` (species/atom/charge multiset). `is_closed_and_conserving` counts atoms/charge on the saturated EXTERNAL boundary; it does **not** require fine per-atom "flow" ports. Net boundary counts do not depend on schedule order ⇒ interchange-invariant ⇒ compatible with Level 1. (This resolves the draft's Open Q2 / evil-morty's "unexploded ordnance": conservation lives at Level 2 as an apex decoration, **not** as a Level-1 port granularity — so the two requirements never compete for one port model.)
  - **Provenance** (Rung B) — the causal DAG of generator steps (P4). Interchange-invariant; the linear tuple is one recoverable linearization.
  - **(later, same slot — declared instances, not built here):** the **thermodynamic-drive functor** `Δ_rG: Process → (ℝ,+,≤)` — *already computed* per step by `feasibility.py:245-247` (Hess's law from sourced ΔH_f°/S°); **Hess's law *is* its combine law** (`Δ_rG(g∘f)=Δ_rG(f)+Δ_rG(g)`, additive, hence interchange-invariant); the **kinetic-survival functor** `S: Process → ([0,1],×)` — *already built* (R23, `composability.py`), multiplicative combine, interchange-invariant; **observability** and **EM certificates** (Move 5). These form the product-of-ordered-semirings of Move 2 ("favorable ≠ fast" = the product order forbids collapse). Wiring them onto the backbone is a *later* rung; Rung B only guarantees the slot admits them.

### The three port states (makes the meta-compiler reading literal)

| State | Meaning | Closure effect |
|---|---|---|
| **INTERNAL** | glued to a partner | counted inside |
| **EXTERNAL** | declared net input/output (reactant supplied / product or byproduct emitted) | **counted** by `is_closed_and_conserving` |
| **OPEN / UNRESOLVED** | an unfilled slot — unknown byproduct, unresolved reagent, spec hole | any OPEN port ⇒ **cannot close** ⇒ conservation **UNDECIDED**, never reported conserved or violated |

An OPEN port *is* an underdetermined spec hole; closing the diagram *is* compilation.

### Reuse — honestly scoped (fold of evil-morty F4)

The **composition algebra** (`then`/`tensor`/`identity`/`braid`, `open_diagram.py:381-475`) and the **quotient** (`canonicalize`, `:561-609`) are domain-neutral and genuinely reusable. But the **construction/validation layer is electrical-specific and two-terminal**: `_Edge` (`:162-173`) and `ElementPortRef` (`:124-134`, terminal exactly `'a'`/`'b'`) model a two-terminal component; `__post_init__` rejects non-`ELECTRICAL` node kinds (`:277-280`) and enforces a Kirchhoff-shaped ≥2-incidence rule (`:287-288`); `build` hardcodes `expected_kind=ELECTRICAL` (`:339`). A reaction step is a **multi-terminal hyperedge** the two-terminal `_Edge` cannot hold — the hypergraph/prop machinery the module does **not** implement. So "reuse" means **factor `open_diagram.py` into (a) a generic core + quotient and (b) a per-domain construction/validation layer**, then add a *chemistry* construction layer (hyperedges, species-typed ports, mass/charge incidence) beside the electrical one. This is materially more than "add a `PortKind`" and is **the single largest design decision — flagged for the reviewer to rule on explicitly.** The alternative (a standalone chemistry open-diagram type) is rejected because it would recreate the island-disjointness the keystone exists to dissolve.

---

## Falsifiable call sites — re-specified (the anti-zero-call-sites discipline)

The draft's gate ("flip `test_laws.py:330` to a real pass") was unsound: in one reading it edits the falsifiable target itself (the zero-call-sites trap), in the other it mutates `Reaction` identity and breaks P2. Re-specified gate for Rung B, **all three required**:

1. **Interchange proven on the new representation, under its own (honestly labeled) quotient.** A **new** test asserts interchange/braid/hexagon on `OpenChemDiagram` under its structural equality (the `canonicalize`-style quotient — *not* raw `==`, and the quotient's budget refusal is handled **fail-closed** as UNKNOWN, never as a pass, consistent with `step.py:120-123`). Chemistry apices are more symmetric than resistors, so the refusal path is load-bearing and must be tested.
2. **A real non-test consumer.** `ExperimentStep.open(...)` (impossible today) must be *representable*, and `.close()` on a saturated one must reproduce today's `Reaction` certificate **byte-for-byte** (P3). This is the consumer that keeps the structure from being lawful-but-unused — a real object cross-checks it, not its own test.
3. **P4 demonstrated.** A test shows the causal DAG round-trips to/from `Reaction.path`/`generator_word` for the linear case, and that two interchange-equivalent assemblies yield **equal** provenance (proving the quotient erased only the linearization artifact, not the trail).

**The legacy xfail (`test_laws.py:330`) is preserved and re-annotated, not flipped in place** — it stays true as "the *legacy linear `Reaction`* representation cannot interchange under raw structural equality," now noting the open backbone supersedes it for parallel events. This avoids both the trap and the P2 violation.

**Preservation regression:** `TestConservationTheorem` + a representative set of existing closed-route digests pass unchanged (P1, P2, P4).

Follow-on call sites (later rungs): observability as a `Transition` decoration (copy of R23's `surviving_fraction` pattern, `composability.py:232`); the meta-compiler at `smartchem/service.py:1995/2028/2185` (closing = compiling; report *which ports remain open*); the EM bridge as a certificate on a real arrow (`electrochemistry.py` + `redox_displacement.py:248`).

> **Roadmap tension noted (fold of evil-morty's residual unease):** the meta-compiler and observability rungs pull *toward* order-sensitive content on morphisms, the same direction as P4 and the opposite of the interchange quotient. The two-level split above is precisely what keeps them from colliding — order-sensitive content is a Level-2 decoration; interchange acts on Level 1. If a future rung cannot phrase its content as an interchange-invariant Level-2 decoration, that rung — not the keystone — is where the tension must be re-litigated.

---

## Boundaries — what this contract deliberately does NOT do

- **Does not fix the DOW cost undercut.** Supplies the representational fix (typed feedstock/byproduct ports vs the undifferentiated bag at `smartchem/experiment/affordability.py:290`), not the epistemic one: the NaBr-from-Br-content proxy self-cancels (`SOURCING_RECON_2026-09-07.md:101-109`) and NaBr is unpriced (`smartchem/experiment/commodity_pricing.py:74-78`). **The keystone must not be accepted against a DOW-undercut test.**
- **Does not model Br₂ collider kinetics (item 3b)** — a modeling wall, orthogonal.
- **Does not wire observability or the EM bridge** — named follow-on rungs.
- **Does not touch Domain** — orthogonal; a fibration over the base, later.
- **Adds no execution authority or safety claim.** UNKNOWN is not safe; untouched.

---

## Migration phasing

- **Rung A — this document.** Design gate; external review recommended (Lane-A-touching).
- **Rung B — additive, byte-stable, falsifiable (first buildable increment).** Factor the core; add `OpenChemDiagram` (hyperedge construction layer) *alongside* `Reaction`, with a `Reaction → OpenChemDiagram` functor and a `.close()` round-trip. Land **all three §6 gates**: interchange under the quotient, the `ExperimentStep.open/.close` non-test consumer, and the P4 provenance demonstration. Every existing digest untouched (P2). No mutation of `Reaction`/`scheduled_product`.
- **Rung C — full open-step migration (higher care; separate contract).** Migrate `ExperimentStep`/`Route`/`SynthesisDAG` to carry open diagrams so partial/underdetermined steps become first-class throughout the pipeline. (Rung B only lands the *minimal* `open/close` consumer; the invasive pipeline migration is Rung C — resolving the draft's §5/§7 inconsistency.)
- **Rung D — meta-compiler unification at `service.py` (highest care).** Closing = compiling.
- **Follow-ons (Move 5):** observability decoration; EM certificate on an arrow; Domain as a fibration.

Each rung clears the R23 bar: additive first, byte-stable, fail-closed, a real call site + a falsifiable test before it lands.

---

## Open questions for review (the resolved ones removed)

1. **Core factoring.** Is factoring `open_diagram.py` into a generic core + per-domain construction layers acceptable, or is a cleaner seam available? (Supersedes the draft's "just add a `PortKind`.")
2. **Provenance round-trip fidelity.** Can `generator_word`'s per-step witness be reconstructed from the partial-order DAG for *every* case E1/DAG replay and R21 verified-admission depend on, or only the linear case (gating how much of Rung C is safe)?
3. **Quotient budget on chemistry apices.** How large must the `canonicalize` budget be, and where is the honest UNKNOWN boundary, given chemistry apices are more symmetric than circuits (`open_diagram.py:549-558`)?
4. **`Molecule.carrier` unification** (`category.py:534-562`) — fold the charge-open precedent into the new port mechanism, or keep mass and charge as distinct certificates?

---

## Precedent & references

- **In-repo:** `smartchem/open_diagram.py` (the lawful open SMC core + `canonicalize` quotient; the two-terminal electrical construction layer to generalize); `tests/test_open_diagram.py:350-412` (laws proven **under the quotient**); `THE_DIFFERENCE.md:8-9,227-232` (the zero-call-sites cautionary tale + the theorem to preserve); `smartchem/category.py:22-37,801-827,879-999` (the current chemistry category, its deliberate mechanism-distinctness, and the interchange gap); `tests/test_laws.py:330-343` (the legacy xfail — preserved, not flipped); `smartchem/cell.py:189-193` (the only live non-test `scheduled_product` caller — evidence for P2).
- **External (framing, not imported as fact):** **the on-point precedent is Baez & Pollard, *A Compositional Framework for Reaction Networks* (Rev. Math. Phys. 29, 2017, 1750028; arXiv:1704.02051)** — open reaction networks as morphisms of a symmetric monoidal category, with a **black-boxing functor to the *steady-state* input/output relation**. That black-box is the natural semantics target of `OpenChemDiagram.close()` (a later rung; Rung B's `.close()` only reproduces today's conservation certificate, P3). Lineage/related: Baez–Fong–Pollard, *Markov Processes* (JMP 57, 2016); Baez & Fong, *A Compositional Framework for Passive Linear Networks* (TAC 33, 2018 — decorated cospans, the electrical precedent already in-repo); Baez & Courser, *Structured Cospans* (TAC 35, 2020); Baez & **Master**, *Open Petri Nets* (MSCS 30(3), 2020); the hypergraph-category / prop literature (multi-terminal generators — the machinery the electrical layer lacks). Verified citations + the detailed-balance caveat on the gradient-flow reading live in `FREE_ENERGY_FUNCTORIAL_PHYSICS_FOLD_2026-09-07.md` §3. No claim rests on these beyond what the in-repo tests establish.

---

## Adversarial review folds (pre-commit, v0.1)

The first draft was reviewed by two independent read-only adversaries before any commit. Both **converged on the same central defect**, which reshaped the contract:

- **[HIGH, both] Unsound acceptance gate + P4 contradiction.** The oracle `test_open_diagram.py:412` passes only under the `canonicalize` **quotient**, not raw `==` (evil-morty ran it: raw False, canon True); the chemistry xfail uses raw `==` over a linear `path`. Flipping it in place either edits the falsifiable target (the trap) or mutates `Reaction` identity (breaks P2), and the failing field (`path`/`generator_word`) is exactly what P4 preserves. → **Re-specified the gate** (§6: quotient-honest interchange test + a real non-test consumer + a P4 demonstration; legacy xfail preserved-and-annotated) and **added "the central knot"** section resolving quotient-vs-provenance via the two-kinds-of-order / two-level split.
- **[MED, evil-morty F3] "Strictly stronger" overstated** → P1 rebilled as **equivalent** for an additive invariant, valued for composing along *open* pushouts.
- **[MED, evil-morty F4] "Just add a `PortKind`" understated a rewrite** (two-terminal `_Edge` can't hold a multi-terminal reaction hyperedge) → **reuse honestly re-scoped** to "factor the core + add a chemistry hyperedge construction layer."
- **[MED, evil-morty F5] Wrong defect diagnosis** ("partial vs whole-state gluing"; both demand exact endpoint equality) → **§"the one real defect"** rewritten: the causes are the missing real tensor + raw-equality-over-a-linear-path, not gluing partiality.
- **[LOW, evil-morty F6] Citation prefixes** (`smartchem/experiment/…`) and the "pass on real `OpenDiagram` values" slip → corrected throughout.
- **[birdperson] Rung B/C inconsistency** (open steps as call-site #2 vs Rung C) → **reconciled**: Rung B lands only the minimal `open/close` consumer; Rung C does the pipeline migration.
- **Upheld, could not break:** P2 byte-stability and P3 closed-check-reduction both survived scrutiny (the additive "alongside" discipline; `step.py:113-123` already re-raises both refusals). The core functoriality math is sound (only its billing was fixed). All four scope exclusions verified honest.

*This is a proposed design contract. It commits to no code until Rung B is separately reviewed and authorized. Its acceptance test is chosen so the keystone cannot claim victory without a real, falsifiable, non-test call site — and cannot flip the interchange law by quietly deleting the audit trail to do it.*
