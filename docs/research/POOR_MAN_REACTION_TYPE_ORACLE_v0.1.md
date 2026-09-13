# Poor-man ingenuity reward — reaction-TYPE oracle, R56 → SHIP (the first sound production code)

> **Canonical record for ROUND 56.** After six verified defers (R49–R55), the ingenuity reward ships its FIRST
> sound production code: a reaction-TYPE oracle that DEMOTES reaction-TYPE fictions off the affordability frontier.
> Code: `smartchem/experiment/reaction_type_oracle.py` + one wire-in line in `smartchem/service._affordability_frontier`.
> Evidence: `experiments/poor_man_reaction_type_oracle_probe.py` (FROZEN_HASH
> `fc8fea1eaa7b6c110775580e5a20f9b02ef610fd067f84903c86a7f1fb4f88e3`, re-frozen from `98cceeeb` at R57 when the
> etherification recognizer added `dimethyl ether` to the vouched reals — the whole-oracle measurement grew by one
> real, `false_vouch_count` stayed 0) + `tests/test_poor_man_reaction_type_oracle.py`
> (12 pins). RDKit-free (committed baseline). Prior round: `POOR_MAN_STEP_VALIDITY_DEMOTER_DEFER_v0.1.md` (R55);
> next round: `POOR_MAN_ETHERIFICATION_RECOGNIZER_v0.1.md` (R57).

## 1. What shipped, and why it is not a seventh defer

R55 proved the CONSUMER (the production affordability frontier ships ~72% reaction-TYPE FICTIONS — steps that are
*no real reaction at all*, Problem A — with empty `hard_blockers`) but DEFERRED the demoter, because the natural
bounded-radius join-element rule collided the R49–R55 way. R56 ships the **escape the prior defers named**: an
EXTERNAL reaction-TYPE oracle. It is a **POSITIVE WHITELIST** of attested reaction-class recognizers — a step is
VOUCHED iff it POSITIVELY matches a known reaction class; otherwise it is fail-closed demoted as *"unrecognized
reaction type"* (honest non-recognition, NOT the claim "proven fake").

**Why this is genuinely different-in-kind from escape #7** (the R49–R55 collision, and the standing operator
warning "the oracle, or nothing"). Escape #7 tried to CARRY an unbounded property with a bounded feature via a
decision function `valid = g(f(step))` that claims to discriminate ALL real from ALL fake — and every version
collided, because a bounded feature is shared by some real and some fake step. The oracle makes a strictly WEAKER,
different claim: it vouches only a FINITE positive set of classes and demotes the rest fail-closed. The
unbounded-ness therefore surfaces as **COVERAGE LOSS** (a real-but-unregistered reaction is demoted-as-unrecognized)
— NEVER as a false-VOUCH. This is the R53/R54 "invert to a positive safe-set whitelist" prescription, now over
reaction-TYPE TRANSFORMATIONS (Problem A) rather than the substrate ELEMENT census R54 deferred (Problem B).

## 2. The design gate (5 bearings, unanimous), and the author's own reproduction

A 5-bearing adversarial design gate (dalembert structure-theorem, daniel instrument/coverage, birdperson
architecture, butter-robot YAGNI, evil-morty break-the-wiring) returned **unanimous GO_WITH_FOLDS**. The
load-bearing findings, each **reproduced by the author against live code** (never trusted on a bearing's word):

- **The escape is real** (dalembert + birdperson): the positive whitelist NEUTRALIZES the false-EXCLUDE axis
  (unrecognized reals become honest coverage loss, not a soundness bug) and, for a **conservation-locked**
  recognizer, does not false-VOUCH. The shipped acyl-condensation recognizer is conservation-locked: within the
  elementary intermolecular shape (2 non-water reactants → 1 non-water product, water expelled) a new
  ester/amide carbonyl cannot be minted de novo (that needs an oxidation product the shape excludes), so a fired
  step is FORCED by formula conservation onto a real acyl transfer (R48-hardened).
- **The escape-#7 boundary is sharp** (dalembert + butter-robot + evil-morty, author-reproduced): a GENERAL
  "new C-N bond" recognizer — the one that would keep the R45 caffeine N-methylation genericity win — **COLLIDES**:
  it fires on BOTH `theobromine + methanol → caffeine + water` (real, must-vouch) AND
  `ammonia + 4-aminophenol → p-phenylenediamine + water` (fake, must-not-vouch). It is the R55 theorem one
  alphabet over. It is **deliberately NOT shipped**; caffeine is demoted as honest coverage loss this round.
- **Type-validity ≠ feasibility** (evil-morty, load-bearing): a VOUCH means ONLY "a mechanism of this reaction
  TYPE exists" (Problem A), NOT "feasible" (Problem B, still deferred). The oracle only ADDS blockers; it never
  removes one and must not be read as lifting the feasibility domain guard.
- **Fail-closed totality** (evil-morty, author-reproduced): `_affordability_frontier` is OUTSIDE the compile
  path's `ScissionError`/`IdentityParseError` guards, so a raising recognizer would crash compilation — every
  recognizer call is guarded so an exception ⇒ "did not fire" ⇒ the step stays demoted, never a spurious VOUCH.

## 3. The measurement (author-reproduced, HEAD baseline, rdkit absent)

Acyl-condensation-only oracle, route rule = *VOUCH iff every step recognized*, over the whole production frontier:

| Metric | Value |
|---|---|
| Total affordability-frontier routes | 29 |
| **FALSE-VOUCH (a fiction vouched) — the catastrophic error** | **0** |
| Raw-C-C reaction-type fictions demoted | 21 |
| Genuine acyl reals VOUCHED (non-vacuous) | 4 — paracetamol, 4-aminophenyl acetate, aspirin, methyl salicylate |
| Reals demoted as honest coverage loss | 4 (non-acyl condensations) |
| Flagship consumer (isopentyl acetate) | **10/10 frontier fictions now blocked** (was 0) |
| Both R55 false-VOUCH fakes (H2O2 hydroxylation; aromatic amination) | DEMOTED |
| R55 false-EXCLUDE reals (Friedel-Crafts, Claisen) | demoted-as-unrecognized (honest coverage loss) |
| General N-C recognizer collision (why acyl-only) | reproduced True |

`SOUND` (0 false-VOUCH) and `NON-VACUOUS` (4 genuine reals survive) for the stated scope. The
`test_the_frontier_populates_and_ranks_by_material_quantity` interaction confirmed a deeper point: the multi-route
material-quantity "diversity" on the frontier was itself an artifact of fiction pollution — once the fictions are
demoted, methyl acetate's honest clean frontier is the single genuine Fischer ester (the pre-R56 "second route"
was `formic acid + methanol → acetic acid`, a C-C-fusion fiction).

## 4. What ships, and the folds honored

- `smartchem/experiment/reaction_type_oracle.py`: `recognize_reaction_type(step)` (positive-whitelist union,
  total + fail-closed) and `route_reaction_type_blockers(route)` (a sibling to `route_catalyst_blockers`; one
  honest reason string per unrecognized step; VOUCH iff every step recognized; 0-step route vacuously vouched).
- `smartchem/service._affordability_frontier`: one wire-in line, `hard = hard + route_reaction_type_blockers(route)`,
  next to the catalyst demoter. A G6 hard blocker; it never touches `_score_tuple`.
- **FOLD honored — per-recognizer conservation-lock admission gate:** acyl-only this round; a recognizer without a
  conservation-lock proof (e.g. general N-alkylation) is NOT admitted. Documented in the module.
- **FOLD honored — disposition honesty:** the reason vocabulary says "unrecognized reaction type … NOT a claim of
  cost or feasibility"; a type-VOUCH is never a feasibility claim.
- **FOLD honored — fail-closed totality:** exceptions in a recognizer are treated as abstention (demote), never a
  crash or a silent vouch.

## 5. Scope and boundaries (documented debt)

- **ACYL-ONLY** — the one conservation-locked recognizer. Non-acyl real condensations (Friedel-Crafts,
  Kolbe-Schmitt, Claisen, Williamson etherification, N-alkylation/caffeine) are demoted-as-unrecognized: honest
  coverage loss, NOT false-VOUCH. Each is a future round behind its OWN conservation-lock admission gate.
- **The R45 caffeine genericity win is DEMOTED as coverage loss this round** — it cannot be recovered by a
  bounded-radius N-alkylation recognizer (that collides, §2); only a class-specific conservation-locked recognizer
  can, which is future work.
- **Disposition flattening (debt):** the fiction blocker shares the `hard_blockers` tuple with catalyst/section-11
  blockers, so "real reaction, needs industrial catalyst" and "not a reaction at all" both G6-sink equally (the
  partial order "real-but-hard strictly outranks not-a-reaction" is lost). A distinct disposition channel is a
  named follow-up; the honest reason vocabulary is the minimal correct thing this round.
- **Problem B (substrate feasibility) stays deferred** — the oracle answers Problem A (does a mechanism of this
  type exist), not Problem B (does it proceed with this substrate under these conditions). The acyl recognizer
  vouches the direct free-acid esterification/amidation TYPE that `feasibility.py` itself fails closed on; both are
  correct at their own scope.

## 6. Next (R57 candidates, each gated)

1. **Grow the whitelist under the admission gate** — add the next conservation-locked recognizer (candidate:
   etherification, if it passes a conservation-lock proof) to reduce coverage loss without a false-VOUCH.
2. **A class-specific conservation-locked recognizer to recover the caffeine N-methylation win** (never a
   bounded-radius patch).
3. **A distinct disposition channel** so "not a reaction" is ordered below "real but hard", instead of the
   flattening debt above.
