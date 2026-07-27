# THE COMPILER

*Design note for a meta-compiler over physical specifications. **Nothing here is built.***

`THE_ORBITAL.md` opens with the rule that a claim without a test does not belong in it.
This document is design, not specification, so it obeys a stricter version of that rule:
**every claim about what the code does today carries a `file:line`; everything else is
marked UNBUILT and carries no test because it has no code.** Read the two documents
differently. That one describes a system that exists. This one argues for one that does
not.

---

## I. THE ASK

A scientist writes something underdetermined on purpose:

```
testParticle  : mass: <value or range> ; spin: observe ; position: constrain
testParticle2 : mass: <other value>    ; spin: observe ; position: constrain
```

and the compiler does not run it. It reads it back:

> Two objects with specified masses. Spin dynamics as the observable. Positions
> constrained — but you have not said *to what*. Under this system's declared rules there
> are exactly **X** admissible relations between `testParticle.position` and
> `testParticle2.position`. Here they are. Choose one, or write one and I will check it
> against the same rules.

…and iterates until the spec is *verifiably* realisable, or until it can prove that it
is not.

---

## II. THESIS — this is the decline rule, lifted one level

SmartChem's governing rule at the **value** layer is already exactly this shape: an oracle
returns `None` for what it cannot price, because a plausible wrong number is worse than no
number.

* `smartchem/oracle/base.py:327` — `carries_unmodelled_physics`, a predicate whose whole
  job is to catch objects the category can *express* and no model here can *value*.
* `smartchem/oracle/photon.py:122-139` — one `energy()` method that declines on three
  separate grounds, each with the reason written down. Matter; charge; an opaque label it
  did not issue. Nothing else, and nothing implicit.

  *(This said "four" until 2026-07-26, with the three-item list sitting directly beneath
  the count. Recorded rather than quietly corrected, because a document arguing that
  derived beats plausible has no business carrying a miscount of the very refusals it
  cites as its evidence.)*

The meta-compiler is that same rule at the **specification** layer:

> **A compiler declines a spec it cannot coherently realise, and the declination names the
> invariant it collided with.**

This is not an analogy. The germ is in the tree with the cross-scale case already worked
as its example — `base.py:343-346` gives `Na(excited) -> Na + photon`: the category can
express the morphism, no single oracle can price it, and today the honest answer is a
boolean decline. The meta-compiler's entire job is to turn that boolean into a
**diagnosis**: which properties, which models could cover each, and whether their domains
of validity intersect.

---

## III. THE LAW THAT SEPARATES THIS FROM A CHATBOT

There is one failure mode here and it is fatal, because it is this repository's own
pathology wearing a new hat. An LLM asked "what are the possible position constraints?"
will happily produce five fluent, plausible, physically-unmotivated options. The scientist
picks one. The simulation runs. The number is wrong and confident, and now the wrongness
entered at the *specification* layer where no oracle's `None` can catch it.

So:

> **THE DERIVED-MENU LAW.** Every option offered to the scientist is the image of a
> declared invariant under a declared operation. If the compiler cannot generate the option
> set, it says *"I cannot enumerate the admissible constraints here"* and hands back the
> reason. **It never offers a plausible menu.**

The dialogue is a user interface onto a derivation. It is never a substitute for one. A
menu that is complete-by-theorem is worth everything; a menu that is merely helpful is the
`0.0 ± 0.0 eV` of `base.py:339` with more words.

The law has a second half, equally load-bearing: **do not ask what you can derive.** A
question whose answer is forced is not a clarification, it is theatre.

---

## IV. THE LAW, WORKED — the stoichiometry menu

The cheapest complete instance of §III already has all its ingredients in the tree, which
is why it is the first brick.

`conserves` at `category.py:1076` is the *checker*: it verifies that a `Reaction`'s atom
counts and net charge balance. The enumerator is its **inverse**, and the inverse is linear
algebra over the integers, not judgement.

Given species with composition vectors `a_i` (one row per element, plus a charge row), a
balanced reaction is an integer vector `ν` with `Σ ν_i a_i = 0`. The admissible completions
are exactly `ker A ∩ Z^n` — a lattice of rank `n − rank(A)`. Three ranks, three behaviours,
and the entire UX of §I falls out of which one you are in:

| `dim ker A` | Meaning | Compiler's move |
|---|---|---|
| **0** | No non-trivial balance exists | **Refuse — and the refusal is a theorem.** `H2 + He` admits only `ν = 0`. |
| **1** | Forced up to sign and scale | **Fill it in and say so.** `{H2, O2, H2O}` → `2 H2 + O2 → 2 H2O`, uniquely. Asking would be theatre. |
| **≥ 2** | A genuine choice | **Enumerate a lattice basis.** `{C, O2, CO, CO2}` has rank 2: `C + O2 → CO2` and `2 C + O2 → 2 CO`. *That* is the "here are X configurations, pick one" moment — finite, complete, derived. |

Rank 0 is worth staring at. It is the smallest possible instance of the user's own closing
insight: **a spec that verifiably cannot compile, where the impossibility is the output.**
Not "I failed to find a reaction." *No reaction exists*, proved, in two lines of rank
arithmetic.

> **Correction, 2026-07-26 — and note which half was wrong.** The paragraph above says
> `ker A ∩ Z^n`, and that specification was correct. The first implementation of it was
> not. It solved the kernel over the *rationals* and then cleared each basis vector's
> denominators one at a time, which generates a proper sublattice of the integer kernel —
> so balanced reactions existed that the menu could neither list nor reconstruct, while
> printing "every other one is an integer combination of these". On `{O2, H2O, H2O2, H2}`
> the omitted reaction was `H2 + O2 → H2O2`; it is `(b₀+b₁)/2`, and every integer
> combination of the returned basis has an even third component. Worse, *which* reactions
> vanished depended on the caller's argument order: 4 of the 24 orderings of those four
> species lost one. Fixed by unimodular column reduction, which returns the saturated
> lattice by construction. The document did not need changing here; the code did. **A
> design stated correctly is not a design implemented correctly, and only the executable
> one gets audited** — which is the entire argument for §VII's build order.

---

## V. CROSS-SCALE — why "extreme conditions" is computable and not mystical

Every physical model carries a **domain of validity**: a region of parameter space stated
as inequalities in dimensionless groups.

| Model | Its domain, as a group |
|---|---|
| Non-relativistic mechanics | `β = v/c ≪ 1` |
| Classical (vs quantum) | `S/ħ ≫ 1`, or `λ_dB / d ≪ 1` |
| Born–Oppenheimer | `(m_e/M)^{1/4} ≪ 1` |
| Continuum | `Kn = λ_mfp / L ≪ 1` |
| Non-relativistic *chemistry* | `Zα ≪ 1` |
| Single-reference CCSD(T) | `T1 < 0.02` — **but see §VI.1** |

An object carrying properties from several scales **compiles iff the intersection of the
validity domains of the models needed to evaluate its properties is non-empty at its
parameter values.** That is a feasibility question over a semialgebraic set. It has three
outcomes and all three are useful:

1. **Empty intersection** → hard refusal, with the two colliding domains named. There is no
   single theory whose validity region contains this object.
2. **Generous intersection** → compile, silently. This is the ordinary case and the
   scientist should never hear about it.
3. **Non-empty but narrow, or bounded away from ordinary parameter values** → **this is the
   research output.** The compiler does not merely refuse; it reports *the region itself*,
   as the inequalities that bound it. "Your object exists only where `β > 0.1` **and**
   `S/ħ ~ 1`" is a sentence a scientist can act on. It is a discovery shaped like a
   compiler error.

**This repository already has an untracked instance of row 5.** Iodine, `Z = 53`, sits in
the roster at `atoms.py:167` and in the reference spin table at `data/reference.py:259`.
`Zα ≈ 0.39`, which is not small. And a grep of `smartchem/` for `x2c`, `DKH`, `ECP` and
`relativis` returns **nothing** — there is no relativistic Hamiltonian anywhere in the
package. That is a real validity boundary, live in the shipped roster, that no code
currently tracks and no `Estimate` currently widens for. Under §V it would be a declared
domain and iodine would trip it.

---

## VI. THREE THINGS THAT ARE GENUINELY HARD

Stated here so nobody rediscovers them at implementation time and quietly papers over one.

**1. Some validity domains are *a posteriori*.** `β ≪ 1` can be checked from the spec.
`T1 < 0.02` cannot — the T1 diagnostic is an output of the very calculation whose validity
it governs. So the domain algebra needs two kinds of predicate, checkable-before and
checkable-after, and the compiler must label which kind gated a decision. A spec that
compiles subject to an a-posteriori condition is not the same object as one that compiles
outright, and conflating them would be exactly the sort of silent upgrade this repo has
already caught itself making elsewhere.

**2. "Meaningful output" is not a formal property.** The compiler can certify *coherent* —
it typechecks, it conserves, the domains intersect, the free parameters are all bound. It
cannot certify *meaningful*; that is the scientist's, permanently. Do not let the doc drift
into claiming otherwise. `THE_DIFFERENCE.md` exists because this project already published
a document that claimed more than shipped once.

**3. Termination of the dialogue is not free.** A compiler that keeps asking is a compiler
that never compiles. The loop needs a fixed-point criterion with teeth: **every round must
strictly reduce the number of unbound free parameters, or the compiler halts and says which
parameter it cannot reduce.** No round that merely rephrases.

> **AMENDED 2026-07-26 — the criterion is right and the measure was wrong.** The sentence
> above is kept verbatim because Brick 3 was built to it and its failure is what produced
> the replacement. *Reduce* is the correct demand; *the number of unbound free parameters*
> is the wrong quantity to reduce, because a round that answers one abstract question and
> opens two concrete ones beneath it is refinement — it is precisely what §IX's shepherd
> does when it supplies vocabulary — and it raises the count. **The measure is now the
> multiset of the holes' *ranks*, ordered by the Dershowitz–Manna multiset extension of `<`
> on ℕ**, which is well-founded, so termination is still a theorem. Binding a hole descends;
> replacing one hole of rank *r* by any finite number of holes of rank `< r` descends *while
> the count rises*; rephrasing descends nowhere. A spec that declares no ranks is entirely
> rank 0, nothing sits below rank 0, and the rule is then bit-for-bit the cardinality rule
> above — so this amendment strictly adds cases rather than changing any.
>
> **What it cost, because it was not free either.** Cardinality was doing two jobs and only
> one survives: it was the termination argument *and* an a-priori bound on the round count.
> A rule that lets one hole open unboundedly many simpler holes lets the dialogue run
> unboundedly many rounds — a fact about descending sequences below `ω^ω`, not a gap in the
> implementation. So the round budget is now conditional on a *declared* fan-out, and
> overrunning it is `EXHAUSTED` (a resource limit reached) rather than `LedgerContradiction`
> (a theorem violated). The unconditional case is kept and still raises. See
> `smartchem/ledger.py` and §VII's Brick 3 bullet.

---

## VII. BUILD ORDER

Each brick is chosen so that its *failure* is informative — if a brick cannot be built, the
thing that blocks it is a fact about the design, not about the effort.

* **Brick 0 — the stoichiometry menu (§IV). BUILT, 2026-07-26,
  `smartchem/stoichiometry.py`.** Enumerates `ker A ∩ Z^n` over real `Molecule` values,
  returns the three-way verdict, and proves completeness by test (29 of them). All three
  §IV regimes reproduce over the shipped types.

  **AND IT SHIPPED THE EXACT DEFECT IT EXISTS TO PREVENT — corrected the same day, by
  adversarial review rather than by its own tests.** The kernel was computed over the
  rationals and denominators cleared per vector, which returns a proper *sublattice* of
  `ker A ∩ Z^n`; see the correction box in §IV for the counterexample and the fix. Two
  things about that are worth more than the bug:

  * **The test suite had a class named `TestCompleteness` that asserted no completeness.**
    Its two tests were `len(completions) == freedom`, which the constructor already raises
    on — so the assertion restated two implementation lines and could error but never fail
    — and `A @ ν == 0`, which is *soundness*. Soundness was never the hard part. A mutant
    returning an index-2 sublattice passed **28 of the 29 tests**, and the one that caught
    it did so by hard-coded string comparison on a single species set. The guard was named
    after the property it did not test.
  * **A module cannot audit itself into completeness.** Every check it ran — rank-nullity,
    `A @ ν == 0`, the `Reaction` constructor — was a *soundness* check, and all of them
    passed on an incomplete menu, because an incomplete menu is a menu of correct answers.
    The property that mattered needed an *external* enumeration: every integer kernel point
    in a box, each required to be reachable. That is now `TestCompleteness`, and it kills
    the mutant.

  **One plan in this bullet was wrong and the build found it.** It said the menu "reuses
  `conserves` as an independent checker of its own output". `conserves` is
  *tautologically* `True` for any `Reaction` that exists, because
  `Reaction.__post_init__` already raises `ConservationError` otherwise — its own
  docstring says exactly that. Calling it on a reaction the menu just built checks
  nothing.

  The real independent check is the **constructor**. Every derived `ν` is turned into
  `Config` objects and pushed through `Reaction(...)`, which re-derives balance by
  accumulating `Molecule.formula` dictionaries and never touches a `Fraction`. Different
  number type, different code path, same claim; disagreement raises rather than being
  swallowed. Worth stating plainly: a document whose thesis is *derived, never plausible*
  had shipped a plausible-sounding verification plan, and only writing it exposed that.

  **And the build produced a corollary the design did not anticipate — the derived-menu
  law's own boundary, which it reports rather than hides.** A menu is complete with
  respect to the **declared** invariants and not one inch further. A species with no atoms
  and no charge — how this package spells a photon — has an all-zero column, so it lies in
  the kernel *by itself*, and the enumeration dutifully offers `(photon@589nm) →
  (nothing)` as a balanced reaction. Measured, not argued: that is the literal output.

  Under mass and charge conservation alone it **is** balanced. Those invariants cannot see
  energy. The completion is not wrong; the invariant list is short, and the menu is the
  first thing in this repository able to *say* so. Such species are named in
  `StoichiometryMenu.unconstrained` and every completion touching one is flagged, so
  "balanced under the declared invariants" can never be read as "physical".

  **THE SENTENCE ABOVE WAS MEASURED WITH A LABELLED PHOTON, AND THAT IS THE ONLY REASON IT
  HELD — a second defect, found 2026-07-26.** `Molecule.__repr__` returned the **empty
  string** for the one species with no atoms, no charge and no state, and every renderer in
  the package joins species reprs and then decides emptiness from the joined *text*. So a
  bare `Molecule.quantum()` vanished from any statement it was part of while the statement
  stayed fluent. The kernel vector with coefficient 1 on the quantum printed as
  `(nothing) -> (nothing)` — the trivial reaction, a confident false claim about a true
  basis vector — and `quantum -> Na` printed as `(nothing) -> Na`, a module whose entire
  subject is conservation announcing that matter came from nowhere. `Config((quantum,))`
  printed as `""` and a photon-only `Reaction` as `" -> "`.

  It survived because every boundary fixture used `state="photon@589nm"`, which renders as
  `(photon@589nm)`; **the one species that triggers the defect was the one species no test
  had ever rendered.** Fixed by giving the bare quantum a name (`quantum` — lower case so
  no formula can collide, unbracketed so no state can) and by deciding `(nothing)` from the
  *coefficients* rather than from the rendered text. A mutant restoring both defects
  survives **239 of 239** pre-existing tests across six files and dies on all 8 of the new
  ones. Same disease as the sublattice bug: a fact derived from a rendering of itself.

  This is the shepherd posture of §IX arriving a layer earlier than expected. The compiler
  does not refuse the photon and does not price it — it hands back the completion together
  with the exact reason the completion means less than it looks like it means. It is also
  the precondition for Brick 2: `Na(excited) → Na + photon` fails *this* way, and now the
  failure has a name.
* **Brick 1 — declared domains on the existing oracles. BUILT, 2026-07-26,
  `smartchem/domain.py`.** `Domain` is a frozen value over four axes — atom count, element
  set, charge, internal state — with `admits`, `refusals`, `&`, `is_empty` and `witness`.
  `PySCFOracle`, `PhotonOracle` and `HeuristicOracle` each declare one; both cache wrappers
  forward it; `domain_of` supplies the unrestricted domain for anything that does not.

  **The contract points one way and that is the whole design.** `not admits(m)` implies
  `energy(m) is None`; the converse is *not* claimed, so a domain over-approximates
  coverage, and over-approximating is the safe direction — a loose domain wastes a call, a
  tight one would promise an answer that never comes. The converse fails for two reasons
  reported *separately*, because collapsing them would hide the fixable case behind the
  unfixable one: `runtime_refusals` (an SCF that will not converge — no design can
  pre-announce that) and `unexpressed_refusals` (the diatomic geometry table is keyed by
  molecular formula, which four axes cannot say — a limit of this vocabulary, removable).
  `is_exact` is true only when both are empty, and `PhotonOracle` is the only thing in the
  repository that earns it.

  **The measured payoff, and neither result was visible before writing it down.** First:
  **no `PySCFOracle` configuration prices a polyatomic.** Raising `max_atoms` past 2 does
  not open the polyatomic path, it exposes a second gate behind it — `_polyatomic_energy`
  declines on a non-finite `nominal_accuracy_ev`, and `_RELAXED_GEOMETRY_MAE` is the empty
  dict for every `geometry_tier`. Measured: `max_atoms=6` prices a free atom and a
  diatomic and returns `None` for water. Second: `optimize_geometry=True` leaves exactly
  the *free atoms* — it closes the polyatomic path and the diatomic branch, but the
  one-atom branch returns before either check, so the ceiling is 1 and not 0. The obvious
  guess was wrong and the measurement said so.

  **And the acceptance test §VII actually asked for.** `PySCFOracle.domain &
  PhotonOracle.domain` is **empty** — one requires at least one atom, the other admits only
  species with none. So there is no species both can price, and therefore no shared
  reference against which their two arbitrary zeros could be aligned. That is a real
  obstruction to a cross-vertical reaction energy, computed by construction rather than
  rediscovered once per attempt, and it is the diagnosis Brick 2 needs.
* **Brick 2 — `Na(excited) → Na + photon`. BUILT, 2026-07-26, `smartchem/diagnosis.py`.**
  `diagnose(reaction, oracles)` returns a `Diagnosis`: the per-species oracle attribution,
  and a tuple of `Obstruction`s each carrying its kind, its subject, its prose, and a
  `removable` flag. Nothing it says is invented — every obstruction is derived from
  something Brick 0 or Brick 1 already computed, which is §III's derived-menu law applied
  to refusals instead of completions. A plausible wrong *explanation* of a decline is worse
  than a bare decline, because a bare decline at least does not send anyone off to fix the
  wrong thing.

  **It is additive, and that was measured before it was decided.** Turning `Estimate |
  None` into a richer type would have broken **52 test assertions and 17 internal call
  sites**, plus every third-party `EnergyOracle` duck-type, for a gain available without
  it. `energy()` still returns `None`; the diagnosis is a separate channel. That is also
  the only way it can take a *set* of oracles — `thermo.reaction_energy` takes exactly
  one, there is no router anywhere in the package, and a reaction spanning two verticals
  has nowhere to put the second.

  **The claim §VII had been making was too strong, and building it forced the correction.**
  Brick 1 measured that `PySCFOracle.domain & PhotonOracle.domain` is empty, and that was
  being read as "so their two arbitrary zeros cannot be aligned, therefore no cross-vertical
  reaction energy". In `Na(*) → Na + photon` both sodium terms are priced by the *same*
  oracle, so its zero cancels between them and the photon's energy is absolute — the zeros
  are reconcilable for this reaction. What an empty intersection actually establishes is
  narrower and still sharp: **the offset between two oracles' zeros cannot be *measured*,
  because no species lies in both domains.** A statement about verifiability, which names
  its own remedy — one shared species.

  **And a non-empty intersection does not settle it either, so the code measures rather
  than assumes.** `PhotonOracle(589) & PhotonOracle(532)` is non-empty and even `is_exact`;
  its sole witness is the bare quantum; and the two price that witness **0.225535 eV**
  apart. A shared *token* is not a shared *reference*. That number is the thing nothing in
  this repository could compute before — the whole point of §VIII's load-bearing test.

  **What the acceptance case actually reports.** For `Na(*) → Na + photon`: `Na(excited)`
  is `UNPRICED` with *every* failing axis from *both* oracles enumerated rather than the
  first; `Na` and the photon are attributed to the oracles that do cover them; and Brick 0's
  `INVARIANT_BLIND` is carried through for the twinned Na(\*)/Na columns and the photon's
  all-zero one. The offset obstruction is deliberately **not** raised while any species is
  unpriced — that question is moot until everything has an oracle, and raising it anyway
  would be a fabricated second problem.
* **Brick 3 — the free-parameter ledger and the termination rule (§VI.3). BUILT,
  2026-07-26, `smartchem/ledger.py`.** `Spec` is named slots, bound or not; `shepherd`
  interrogates until the spec closes or §VI.3's rule stops it. **The gate this bullet
  carried — "only after a real spec has more than one hole" — was met twice over and it was
  never arbitrary.** §I's own example is a four-hole spec as written (two masses, two
  positions "constrained, but you have not said to what"), and Brick 2 returns more than one
  obstruction on a real reaction. On a *one*-hole spec "strictly reduced" and "finished" are
  the same event, so the rule has no teeth and testing it proves nothing.

  **The whole design hangs off one decision: the measure is re-derived, never reported.**
  `Spec.measure()` counts `binding is None` over the slots of the object the responder
  actually returned, every round. Write `remaining -= len(bound)` instead and "strictly
  reduced" becomes a tautology no responder can fail — the loop would certify progress it
  never made. That is not fastidiousness, it is the correction box two bullets up applied
  before the fact rather than after: a check whose input comes from the thing it checks. The
  load-bearing test hands `shepherd` a responder that *reports* binding every hole it was
  shown and returns the spec untouched; the session must come back `STALLED` with all four
  parameters still free. Relaxing the strict `<` to `<=` kills **4 tests**, one of them by
  driving the loop past its own termination bound into `LedgerContradiction`.

  **§III is enforced by the constructor, not by review.** A `Slot` carrying options and no
  `derivation` raises `UnderivedMenu`. The compiler may invent a *question* — falsifiable by
  whoever answers it — and may not invent an *answer*. `reaction_slot` is the worked case:
  its options are Brick 0's `equations()` verbatim, which is §I's "there are exactly X
  admissible relations, here they are" made literal instead of illustrative.

  **And the first version collapsed a distinction that is the entire point, caught by its
  own test.** An empty menu was reported as §IX's *"nothing here can enumerate this — a
  statement about the available language"*. But Brick 0's `REFUSE` verdict also produces an
  empty menu, and that is the opposite claim: **enumerated, and the answer is zero.** The
  first says find better words; the second says the question has been answered by theorem.
  Told the wrong one, a scientist goes looking for vocabulary they do not need. The two are
  now separated by whether a `derivation` exists, and a mutant restoring the collapse dies
  on exactly one test — the one written for it.

  **§VI.1 is honoured rather than absorbed.** A spec whose holes all close but one of whose
  bindings is only checkable *after* the run returns `COMPILED_SUBJECT_TO`, never `COMPILED`.
  Both are truthy; `bool` answers "did this close" and `outcome` answers "closed how", so no
  caller has to infer the second from the first. §VI.2 is honoured by omission: nothing here
  emits the word *meaningful*, and a test asserts that along with five other overclaims.
  §X's casualty list prints on every successful refinement, and prints *"nothing was
  recorded as discarded"* when it is empty, because silently omitting it is a different
  claim from reporting that it is empty.

  **THE BRICK'S FAILURE WAS THE INTERESTING PART, AND §VII PROMISED IT WOULD BE.** Applied
  literally, §VI.3 halts on a round that *widens* the spec — one hole closed and two opened
  beneath it. That is ordinary refinement; it is exactly what §IX's shepherd does when it
  supplies vocabulary. The rule was written against rounds that **rephrase** and its measure
  cannot tell those from rounds that **deepen**, because both fail "strictly reduce". So
  `WIDENED` was made a separate outcome carrying the slots that opened, rather than being
  reported as a stall — the same split that keeps `runtime_refusals` apart from
  `unexpressed_refusals` in Brick 1, and for the same reason: collapsing them would hide the
  informative case behind the failure case. **A cardinality measure is the wrong measure for
  a shepherding loop, and §VI.3 will need a well-founded one — depth-weighted, or ordinal —
  before the loop of §I can run more than one round of genuine refinement.** That is a fact
  about the design, which is what this build order is for. *(Both halves of that sentence
  are now discharged and dated: the ordinal measure two paragraphs down, and the §I loop it
  was gating in Brick 4 below — where the widening round runs as the middle of a four-round
  dialogue instead of halting it.)*

  **AND IT IS NOW FIXED, 2026-07-26 — the ordinal one, and it is the multiset order.** A
  `Slot` carries a `rank`: how abstract the question is, and therefore how far it may still
  be unfolded. `Spec.ordinal()` is the multiset of the *holes'* ranks, returned as a
  descending-sorted tuple, and the loop continues exactly when that strictly descends under
  ordinary tuple comparison — which on descending-sorted tuples is precisely the
  Dershowitz–Manna multiset extension of `<` on ℕ, equivalently the ordinal `Σ ω^rank` in
  Cantor normal form. Well-founded, so termination is a theorem rather than a hope. **The
  round that used to halt the loop now advances it**, and the disagreement is legible on the
  `Round` object itself: `reduced` is False and `descended` is True on the same round, which
  is the entire content of the repair. `WIDENED` survives with a sharper meaning — *these
  opened holes are not strictly simpler than what was closed* — and a rank-0 spec, which is
  every spec that declares nothing, behaves bit-for-bit as it did before.

  **THE SORT IS THE TERMINATION ARGUMENT, NOT PRESENTATION, AND THAT IS THE SUBTLE PART.**
  Lexicographic order on *arbitrary* tuples of naturals is **not** well-founded —
  `(1,) > (0,1) > (0,0,1) > …` descends forever — and that chain is realisable here by a
  responder that closes its rank-1 hole and opens a rank-0 *and* a rank-1 hole every round.
  Sorted descending that round reads `(1,) → (1,0)`, an increase, and halts. Drop
  `reverse=True` and it reads `(1,) → (0,1)`, a "descent", and the loop never stops. The test
  written for it asserts `WIDENED` specifically, because a budget would otherwise mask the
  non-termination as `EXHAUSTED`.

  **And measuring that guard caught a second, subtler one — in the check itself.**
  `experiments/ledger_mutation_probe.py` is a committed harness that writes eight plausible
  wrong implementations of this module and counts survivors. It reports **8 mutants, 0
  survivors**, but the interesting run was the intermediate one. `TestTheOrderIsTheOneItClaimsToBe`
  decides the multiset-order identity by exhaustive search against the textbook
  Dershowitz–Manna definition — and as first written it built its specs from *already
  descending* tuples, so it could not tell a correct sort from **no sort at all**: the mutant
  that deletes `sorted()` entirely survived every assertion in the class, killed by only 1 of
  53 tests. Building the slots in *ascending* order fixed it and both sort mutants now die 4
  ways. Same disease as the correction boxes above — a check handed input derived from the
  thing it checks — this time inside the test written to protect a theorem.

  **WHAT THE REPAIR COST, KEPT AS A DISTINCTION RATHER THAN ABSORBED.** Cardinality was
  doing two jobs — the termination argument and an a-priori round count — and only the first
  survives unconditionally, because permitting unbounded fan-out on a deepening permits
  unboundedly many rounds. `Spec.round_bound(fan_out)` is `Σ (fan_out+1)^rank`, which
  strictly decreases on every round that respects the declared fan-out, and
  `Spec.bound_is_theorem()` answers whether that declaration was needed at all rather than
  leaving a caller to assume. Overrunning an unconditional bound is still
  `LedgerContradiction`; overrunning a conditional one is `EXHAUSTED`, because calling a
  reached resource limit a contradiction would be asserting a theorem this module does not
  have. And the boundary, which is easy to overread: the rank order certifies **termination**
  and nothing else. No parentage is recorded and none is checked, so a responder may close a
  rank-3 hole and open two rank-2 holes about something else entirely and be accepted.
  Semantic descent is not decidable here; that the dialogue ends is.

* **Brick 4 — §I's loop, end to end, and §I's second clause. BUILT, 2026-07-26,
  `experiments/section_i_end_to_end.py` and `tests/test_section_i.py`.** This is the brick
  the paragraph above was gating, and the prediction it made is discharged: the loop now
  runs **four rounds on a real spec, one of which is a genuine refinement.** Round 2 closes
  `geometry` — §I's own *"constrained, but you have not said to what"* — and opens
  `geometry.bond_lengths` and `geometry.frame` beneath it. The count of free parameters goes
  `1 → 2` and the measure goes `[1] → [0,0]`: `reduced` False and `descended` True on one
  `Round` object. **That is the round the cardinality rule halted the compiler on**, running
  as the middle of a dialogue instead of the end of one.

  **Every menu in it is derived, and that is the part that took the work.** The reaction
  options are Brick 0's `stoichiometry_menu`; the bond-length options are
  `geometry.seed_bond_length` over the distinct bond types actually present in the candidate
  species; the frame options come from calling `is_linear` on `seed_coordinates`' own output.
  Nothing is written by hand, and `Slot.__post_init__` would refuse it if it were.

  **§I'S SECOND CLAUSE EXISTED ONLY AS PROSE UNTIL NOW, AND THAT IS THE REAL DELIVERABLE.**
  §I promises *"Choose one, **or write one and I will check it against the same rules.**"*
  Brick 0 implemented the first clause in July and the second was never built — which makes
  a derived menu a multiple-choice question wearing the costume of a dialogue.
  `StoichiometryMenu.check` is the second clause, and *the same rules* is enforced literally
  rather than rhetorically: the verdict is `A @ ν` against the menu's **own `matrix`**, the
  identical object that produced `completions`, not a second checker written to agree with
  the first. A test asserts the two clauses agree — every option the menu *offers* passes the
  check the menu *applies* — because if they ever disagreed, one of them would be lying about
  which rules it used.

  **Three things a naive residual test gets wrong, kept apart deliberately.** The all-zero
  vector satisfies `A @ ν == 0` exactly, on every row, in every menu that has ever existed,
  and is not a reaction — reporting it admissible would be a confident yes about the empty
  statement. `admissible` (it balances) and `verified` (…and the invariants could see every
  species it touches) are two claims, and `Na(*) → Na` is the case that separates them: the
  columns are identical because `state` is deliberately outside the conserved signature, so
  `A @ ν` is unchanged by either column and a zero residual is *silence* about de-excitation
  rather than evidence of it. Same distinction as `COMPILED` against `COMPILED_SUBJECT_TO`,
  and `bool(Written)` follows the stronger claim. And a malformed input — wrong length,
  a float, a coefficient weight past the allocation bound — **raises** instead of returning
  `False`, because answering a malformed question with `False` tells a scientist their
  chemistry is wrong when their typing was.

  **And the refusal is informative, which is §IX applied to arithmetic.** `CH4 + O2 → CO2 +
  2 H2O` comes back not as *no* but as **`O off by -2`** — the row label is
  `composition_matrix`'s, so even the diagnosis is derived. What makes realisation a
  *verification* rather than a flag: `Reaction`'s constructor re-derives conservation by
  accumulating formula dictionaries and **raises** rather than returning something wrong, so
  the existence of the object is the evidence. `COMPILED` is the loop's opinion of its own
  dialogue; the constructed `Reaction` is the category's.

  **One defect found on the way, in code that predates this brick.** `Completion.equation()`
  took a caller-supplied species tuple and `zip`ped it against the coefficients — and `zip`
  truncates in silence, so a short tuple rendered a **shorter balance that reads as
  complete**. A plausible wrong equation, reachable from a public method, in the module whose
  entire purpose is refusing plausible wrong answers. It raises now.

The ordering matters. **Brick 0 before anything conversational.** The dialogue is the last
thing built, not the first, because the dialogue is the part that can fake working.

---

## VIII. WHY ANY OF THIS TRANSPORTS — the general form of §V

§V is a special case of something larger, and this section states the larger thing because
it is the actual load-bearing claim of the whole design.

**When a structural pattern recurs across scales, the recurrence induces a vocabulary that is
about the STRUCTURE rather than about any one scale's substrate — and that vocabulary can
then be validly carried across scales.** The scientist's spec in §I is written in exactly
such a vocabulary: `observe`, `constrain`, `range` are structural roles, not physics. That is
*why* the compiler can be scale-free at all. If the spec language were chemical, there would
be no compiler here, only a chemistry front-end.

The question that makes this rigorous instead of poetic is: **when is such a transport
valid?** The answer is standard mathematics wearing an operational hat — a transport is valid
on exactly the sub-theory preserved by the map, i.e. where the map is a homomorphism for the
operations the conclusion actually uses. Nothing new. What is proposed here is that the
compiler be made to *do* it, as a required and checkable step:

> **NAME THE ASSEMBLY.** A cross-scale transport is valid on exactly the sub-theory that the
> assembly operation preserves. Identify the operation that builds the whole from the parts,
> determine which axioms it preserves, and you have named — not guessed — the exact set of
> conclusions that survive the crossing.

### The evidence, and it is already in this repository

**Case 1 — the `EnergyOracle` protocol, chemistry → radiation. Transport valid, whole.**
`smartchem/oracle/photon.py` prices a photon and satisfies the oracle contract **with no
interface change**. Its own docstring states the finding: the contract "was in fact
domain-neutral all along." The assembly here is *"an oracle prices an object"*, which uses
nothing about atoms — so it preserves everything, and the transport is total.

**Case 2 — the interchange law, chemistry → electrical networks. The strongest case, because
what transported was a NEGATIVE result.**

* `tests/test_laws.py::TestObjectProductAndScheduledProduct::test_true_parallel_interchange_is_architecture_debt`
  — a **strict xfail**. Chemical reactions do not satisfy interchange.
* `tests/test_network.py::TestSeriesParallelScalarInterchangeCounterexample` — the same
  law, asked of series/parallel impedance. It fails there too, and the counterexample is
  exactly rational: for resistors 1, 2, 3, 4,

      parallel(series(1,2), series(3,4)) = 21/10 = 2.1000
      series(parallel(1,3), parallel(2,4)) = 25/12 = 2.0833

  Not approximately unequal. Unequal.

The *question* transported perfectly and so did the *answer*. A vocabulary that were secretly
chemical could not have produced a true statement about resistors; that it did is the best
evidence available that the language is genuinely about structure. Note also what this closes:
the standing requirement that the categorical layer reach circuits and radiation is, at the
level of *structure*, already met by these two cases.

**Case 3 — memoryless decay, nuclear → biological. Valid on a sub-theory only, and the
assembly said which one.** `experiments/decay_analogy_probe.py`. The assembly is redundancy
plus a quorum rule; it does not preserve memorylessness; therefore no organism-scale survival
conclusion transports, while part-scale rate conclusions do. Naming the assembly converted
"the metaphor is imperfect" into a decomposition with edges.

### What this section does NOT claim

* **It is not new mathematics.** Structure-preserving maps are old. The proposal is the
  discipline — that "name the assembly" become a step the compiler *refuses to skip* — not
  the concept.
* **n = 3, and one is not independent.** Case 3 was constructed for this document, so it
  demonstrates the method rather than testing it. The real evidence is Cases 1 and 2, which
  predate it and were not built to support it.
* **The open problem is identifying the assembly at all.** In chemistry it is `tensor_obj`
  (`category.py:610`, whose docstring already declares what it does *not* assert). In the
  survival model it is redundancy-plus-quorum. For an arbitrary spec **nobody has said what
  the assembly is**, and until that is answerable the §III derived-menu law binds here too:
  a compiler that cannot identify the assembly must say so, and must not transport anyway.

That last bullet is the genuine research problem underneath this whole document. Everything
else is engineering.

---

## IX. THE COMPILER IS A SHEPHERD, NOT A GATE

**This section corrects the emphasis of the eight above it.** Read back, §II is titled "the
decline rule", §III forbids offering anything, and §IV's headline outcome is a refusal that is
"a theorem". That describes a gatekeeper. It is the wrong primary posture, and the reason is
not stylistic:

> **The specs that fail hardest are the ones closest to new science.** A compiler whose main
> verb is *reject* will reject exactly the inputs most worth having.

The scientist arrives in one of two states, and neither is an error:

* **The truth they are pointing at has no precise language yet.** They are not wrong; the
  vocabulary is missing. Rejecting them for imprecision punishes the frontier.
* **The language exists and they do not know it.** Innocent ignorance. Rejecting them for it
  is a failure of the tool, not of the scientist.

In both cases the job is to **shepherd them toward reality as we currently understand it** —
supplying the words, locating the intuition inside existing structure, and handing back
something sharper than what came in that they still recognise as their own idea.

### This does not weaken §III. It says what §III governs.

The derived-menu law constrains what the compiler **asserts**, never what it **asks**:

| | May the compiler invent it? |
|---|---|
| **The physics** — an admissible constraint, a value, a claim about the world | **No.** Derived or declined. §III stands unchanged. |
| **The language** — a name, a translation, a candidate framing, a question | **Yes, and it must.** Naming costs no invented physics. |

So: **generous in interrogation, strict in assertion.** A compiler may propose *"is this what
you mean by 'constrain'?"* freely, because a question is falsifiable by the person answering
it. It may not propose *"here are five admissible constraints"* unless it derived all five.

### The evidence: this document's own decay exchange

`experiments/decay_analogy_probe.py` exists because a scientist arrived with *"a human life is
an isotope with a half-life"* — informal, imprecise, and pointing at something real. The
shepherding loop ran four rounds, and the record is worth keeping because each round was a
correction *of the compiler*, not of the scientist:

1. **Take it seriously, supply the vocabulary.** Hazard function, memorylessness, Gompertz,
   Makeham. Result: the analogy fails on the founding axiom.
2. **Find where it is right.** Relocated to the element scale — a human is a Poisson-sized
   bucket of isotopes with a quorum rule. The failure at the whole is what the *assembly*
   introduces (§VIII).
3. **Push on the environment.** Nuclear λ moves by ~10⁻⁴ ordinarily and 10⁹ only under full
   ionisation — i.e. only by *destroying structure*, never by tuning a rate. Which is exactly
   how environmental insult acts on an organism: it lowers the redundancy, not the rate.
4. **Find what the intuition was actually for.** Not "humans are isotopes" but *the class of
   processes that present as memoryless and are not* — where the exponential is the **ruler,
   not the model**, and the deviation is a measurement of hidden structure. Verified by
   inversion: the redundancy count was read back off the survival curve's curvature to within
   the error inherited from its own first step, six independent ages agreeing to 0.9%.

Round 4 is the one that mattered, and no round of it was reachable by rejecting round 1.

### The guard, without which §VIII becomes a flattery machine

Relocation is powerful and therefore dangerous. **You can always find some scale at which a
metaphor holds, if you are willing to weaken it enough.** A shepherd that always discovers the
scientist was "right at some level" is a courtier. So:

> **A relocation is admissible only if it is LOAD-BEARING** — it must let you compute or
> predict something you could not compute before. If relocating buys no new prediction, the
> honest report is *"this does not survive"*, not *"it survives at some scale."*

The decay case passes its own guard: relocating memorylessness to the element scale is what
makes the inversion possible, and recovering a hidden part-count from a survival curve is a
computation that does not exist without it. Had it bought nothing, the correct output would
have been a refusal.

### And the compiler's authority is bounded

"Reality as we understand it **to the best of our ability**" — the qualifier is load-bearing
and belongs in the output. When no adequate language exists, the compiler must be able to say
so, and to say it the right way round:

> *"There is no vocabulary in what I hold that captures this. That is a statement about the
> available language, not about your idea."*

Which is the same discipline as `carries_unmodelled_physics` at `base.py:327`, one more level
up: the honest boundary is more useful than a confident wrong answer, **and it is also more
useful than a discouraging one.**

---

## X. REFINABILITY IS NOT VINDICATION

The most dangerous moment in §IX's loop is the moment it **succeeds**. A scientist brings a
metaphor, the compiler refines it into something coherent and reality-respecting, and the
obvious reading of that outcome is *"so the metaphor was right."* It is not, and the compiler
must be built so that it cannot be read that way.

> **A metaphor that refines successfully has demonstrated exactly one thing: that it carried
> enough STRUCTURE to be iteratively refined into a coherent, reality-respecting simulation.**
> It has not demonstrated that it was true. The refined artefact belongs to the refinement,
> not to the metaphor, and the metaphor does not inherit its credibility.

The worked case in this repository is unambiguous on the point. *"A human life is an isotope
with a half-life"* refined all the way to a working inversion that recovers a hidden part-count
from a survival curve. **And the metaphor is still false.** Humans are not memoryless. What
was demonstrated was that the metaphor committed to enough structure — a rate, a state, a
succession rule, an ensemble rule — to be *checked against*, and that its pattern of failure
was informative. Its reward for being refinable was **being disproved precisely**. That is the
entire payoff and it is a large one. It is not a promotion.

### The two axes are independent

Refinability and truth are orthogonal, and the compiler must know which cell it is reporting
from:

| | **True** | **False** |
|---|---|---|
| **Refinable** | the ordinary success | ← **the decay case**, and enormously productive anyway |
| **Not refinable** | the frontier: §IX's missing-language case | genuinely empty |

Note the bottom-left cell. **A metaphor that cannot be refined is not thereby false** — it may
be underdetermined, or the vocabulary to express it may not exist yet. So refinability implies
nothing about truth in *either* direction. Any compiler output that collapses these two axes
into one verdict is lying about which measurement it made.

### The enforcement mechanism: report the casualty list

A shepherd that refines everything and reports success will systematically flatter, which is
§IX's courtier failure arriving by a different road. The guard is concrete and cheap:

> **On every successful refinement, the compiler reports what was DISCARDED.**

For the decay case that list is five axioms of the source theory, all of them load-bearing
there and none of them surviving here:

```
memorylessness              discarded -- the founding axiom of the source
half-life as a PROPERTY     discarded -- becomes a cohort statistic, not a parameter
rate invariance             discarded -- nuclear lambda moves ~1e-4; human hazard by factors
independent ensemble        discarded -- nuclei share no environment; people do
daughter inherits a rate    discarded -- decomposition is Arrhenius and environment-coupled
```

The scientist reads that and sees precisely what they no longer have. A refinement reported
without its casualty list is a refinement pretending to be a confirmation.

---

*Sections I–X are design. Nothing in this document is built. `THE_ORBITAL.md` describes what
exists; this describes what is argued for.*
