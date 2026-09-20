# Problem-B fragment feasibility gate — VERIFIED-DEFER (re-affirmed, 2026-09-20)

**Item D of the A–F transform-algebra round.** Re-affirms `POOR_MAN_DEFER_LEDGER_2026-09-17.md` entry #5 on this
round's fresh evidence, and records that this round built **zero** feasibility gate — deliberately.

## Verdict

**VERIFIED-DEFER.** `smartchem/experiment/feasibility.py`'s ΔG model (M1) stays out of `hard_blockers` /
`Disposition`. It is not wired as a `REAL_BUT_HARD` capability source, and it must not be until a capability-measuring
model (M2) exists. Nothing to build here is *hard*; the *soundness* of the drive→capability mapping is open.

## Why — a sound MEASUREMENT is not a capability-VERDICT source

`feasibility.py` computes a genuine, sourced, Hess's-law ΔG (`ΔH by Hess's law, ΔG = ΔH − TΔS`, calibrated on known
cases — `2H2+O2→2H2O(l)` recovers ΔG°≈−474 kJ). This is **not** the R49–R55 bounded-radius trap: it does not
hand-enumerate a hazard space, it derives a physical quantity from sourced constants. It is unimpeachable *as a
measurement*.

But it measures **thermodynamic drive**, not the **capability** property a Problem-B disposition gate needs (can a
poor-man kitchen bench actually run this step). Those two properties correlate on easy cases and **diverge on hard
ones**, and the module says so in its own voice:

> `UNFAVORABLE` — ΔG > 0: … a sourced *disfavour*, NOT a claim of impossibility — coupling to another reaction,
> non-standard concentrations, or removing a product (Le Chatelier) can still drive it; the equilibrium extent
> quantifies how far (roadmap **M2**). We say "disfavored", never "cannot happen".
> — `smartchem/experiment/feasibility.py`

Wiring the ΔG *sign* into a hard gate would (a) reverse the standing ranking-only-never-a-gate architecture, and
(b) silently equate a *measurement of drive* with a *capability verdict* — exactly the mapping the module disclaims.
An endergonic step is not an infeasible one. The lesson: **a sound measurement is not automatically a sound
capability-verdict source; the measurement→verdict mapping carries its own soundness burden, every time — especially
when the measurement itself is unimpeachable.**

## What would unblock it

The **M2** equilibrium/coupling model that `feasibility.py` names in its own roadmap — a model that maps
thermodynamic drive onto bench capability via equilibrium extent, coupling, concentration, and product removal. That
model does not exist yet (UNVERIFIED / not attempted), so a capability gate built on M1's ΔG sign would be a
fabricated verdict. Until M2 exists, the gate stays a VERIFIED-DEFER.

## This round's posture (why D belongs next to A–C, E, F)

The A–F round invested entirely in **Problem A (reaction-TYPE validity)**: five new conservation-locked classes were
added to the reaction-type oracle — thia-DA, the two 1-hetero-diene (inverse-demand) DA classes, and the two [3,3]
sigmatropic classes (Cope, Claisen) — each fail-closed, each vouching only "a mechanism of this TYPE exists," none
claiming feasibility. Every one repeats the disposition law verbatim: a VOUCH is Problem A, **not** a claim of cost,
rate, thermal-allowedness, or feasibility. Problem B (feasibility) is the orthogonal axis, and it remains deferred on
the same sound grounds it was deferred on 2026-09-17. Proving the defer still holds — with the transform algebra now
much wider and the temptation to "just rank by ΔG" correspondingly stronger — **is** item D's deliverable (the R32
pattern: a verified defer against a temptation is a real result, not an omission).
