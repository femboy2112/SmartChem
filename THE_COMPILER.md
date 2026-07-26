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
* `smartchem/oracle/photon.py:122-139` — one `energy()` method that declines on four
  separate grounds, each with the reason written down. Matter; charge; an opaque label it
  did not issue; and nothing else.

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

---

## VII. BUILD ORDER

Each brick is chosen so that its *failure* is informative — if a brick cannot be built, the
thing that blocks it is a fact about the design, not about the effort.

* **Brick 0 — the stoichiometry menu (§IV).** Enumerate `ker A ∩ Z^n` over a `Config`,
  return the three-way verdict, prove completeness by test. This is the smallest honest
  proof that the derived-menu law is implementable at all, and it reuses `conserves` as an
  independent checker of its own output. If this cannot be made complete-by-theorem, the
  whole design is unsound and better to know in a day.
* **Brick 1 — declared domains on the existing oracles.** Give `PySCFOracle` and
  `PhotonOracle` an explicit validity domain and make composition intersect them. Two
  oracles in two verticals already exist, so the first cross-scale refusal is testable
  without inventing a third.
* **Brick 2 — `Na(excited) → Na + photon`.** Turn `base.py:343-346`'s worked example from a
  boolean decline into a diagnosis. This morphism is the design's acceptance test, and it
  was written down as an open gap years before this document.
* **Brick 3 — the free-parameter ledger and the termination rule (§VI.3).** Only after a
  real spec has more than one hole.

The ordering matters. **Brick 0 before anything conversational.** The dialogue is the last
thing built, not the first, because the dialogue is the part that can fake working.
