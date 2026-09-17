# Poor-man ingenuity — the reaction-TYPE oracle grows a 3rd conservation-locked class (N-methylation)

**Round:** R60 · **Status:** SHIP · **Date:** 2026-09-17

**Verdict.** The positive-whitelist reaction-TYPE oracle
(`smartchem/experiment/reaction_type_oracle.py`) grows from two conservation-locked recognizers
(R56 acyl condensation, R57/R58 dehydrative etherification) to **three**: a **class-specific
dehydrative N-methylation** recognizer (`_n_methylation`). This recovers the R45 caffeine
genericity win — demoted as honest coverage loss for four rounds — the way the R56 record
prescribed: not a general recognizer, not a bounded-radius patch, but a class whose net
functional-group change is identity-unique within a tight elementary shape, so formula
conservation *forces* a fired step onto a genuine N-methylation.

The scalpel note for the record: the two shipped recognizers each cured a fiction the *span*
could see. This one cures a fiction the span cannot — the wound is one layer deeper, and the
census is the suture that holds it.

---

## The class

Dehydrative N-methylation: `R2N-H + CH3-OH -> R2N-CH3 + water`. The canonical live consumer is the
R45 caffeine ladder rung — `theophylline + methanol -> caffeine + water` — a reaction the engine
DERIVES (it is absent from `SEED_CONDITIONS`), not a lookup.

## The conservation-lock proof

### The collision to beat (why the R58 span alone does not lock)

Real caffeine N-methylation and the FAKE aromatic amination
(`phenol + ammonia -> aniline + water`) carry a **byte-identical reaction centre**:

```
formed      = (('C','N',1), ('H','O',1))
broken      = (('C','O',1), ('H','N',1))
n_components = 1
```

so `ReactionCenter.is_elementary_condensation(("N",))` returns `True` for **both**. The R58
span-local check — which was sufficient for acyl and ether — is here *necessary but not
sufficient*. (Verified live: both derived centres are equal element-pair-for-element-pair; the
regression is pinned in `test_the_byte_identical_centre_collision_is_split_by_the_census`.)

### The census supplies the lock

The whole-molecule predicate
(`feasibility._methylation_shape_and_net_change`), within the elementary intermolecular shape
(2 non-water reactants → 1 non-water product, water net-produced), additionally requires:

1. **A methanol-specific alcohol net-CONSUMED** (`_methanol_specific_alcohol_count`): an alcohol-O
   whose sp3 carbinol carbon bears NO other heavy neighbour — literally `CH3-OH`. This
   structurally excludes:
   - the **aromatic phenol-O** of the aryl-amination fake (aromatic carbon, not sp3); and
   - **every longer alcohol** (ethanol's/propanol's carbinol carbon carries a second heavy
     neighbour) — so *general N-alkylation is not admitted*, only methylation.
2. **An N-methyl amine net-FORMED** (`_n_methyl_amine_count`): an N with all-single bonds
   (excludes sp2 imine N and Kekulized aromatic N), bearing a methyl carbon (a terminal `CH3`),
   and NOT adjacent to a carbonyl carbon. This excludes:
   - the aryl-amination fake (aniline's N is an unmethylated aryl N); and
   - the acyl/amidation class (an amide N sits beside a `C=O`) — keeping the classes disjoint.

Within the elementary shape these two net facts, together, are the signature of a genuine
N-methylation and cannot be shared by a formula-conserving fake. For centre-carrying steps the
recognizer *also* requires the R58 span to be a single elementary condensation onto N; a
centre-absent step (hand-built / non-scission) falls back to the census alone, sound at the
production k=1 config — semantics identical to `_etherification`.

Worked census on the caffeine rung: caffeine has exactly **one** free N-methyl amine (N7); N1 and
N3 are carbonyl-flanked, so they are excluded and do not inflate the count. Theophylline has
**zero** (its two methyls are on the carbonyl-flanked N1/N3). Net formed = 1 − 0 = 1 > 0. The fake
forms zero. Methanol net-consumed = 1 for the real reaction, 0 for the fake.

## The measurements (frozen in the probe)

`experiments/poor_man_n_methylation_recognizer_probe.py`, `FROZEN_HASH` embedded.

- **Consumer served (A):** caffeine's real N-methylation step now returns the N-methylation class
  (was `None`); the caffeine production frontier carries a vouched route.
- **Soundness, production frontier (D-ii, the R56 bar):** **29** frontier routes swept across the
  registry, **0 false-VOUCH**. Non-vacuous: `caffeine` and `methylamine` join the vouched reals.
- **Adversarial k=2 bundled sweep (D-i):** over an N-methyl-bearing target library, **8**
  whole-molecule-census-vouched steps at k=2, **0 false-VOUCH** (no step recognized as
  N-methylation forms a C-C bond; every recognized step is a single elementary C-N condensation
  by its span). The census-vouched k=2 steps are all genuine single condensations (also reachable
  at k=1) — the class is not forgeable by the reachable bundles.
- **Adversarial demotes (B):** the byte-identical-centre aryl-amination fake, general N-ethylation
  by ethanol, and O-methylation to anisole are all NOT vouched as N-methylation.
- **Existing recognizers unbroken (C):** acyl and etherification classes still vouch their own
  reactions; R56/R57/R58 probes stay frozen.

## Boundaries carried as documented debt

- **The whitelist grows to THREE classes.** Other real condensations (Friedel-Crafts,
  Kolbe-Schmitt, Claisen) and **N-alkylation beyond methylation** (any longer alcohol — the
  methanol clause admits only `CH3-OH`) remain demoted-as-unrecognized: honest coverage loss, NOT
  false-VOUCH. Each is a future round behind its own conservation-lock gate.
- **Escape #7 is re-framed, not reopened.** R56/R57/R58 pinned "caffeine stays demoted" as their
  escape-#7 invariant, because with only acyl+ether no recognizer could vouch N-methylation. R60
  makes caffeine legitimately vouched, so the invariant is restated to its correct form: **escape
  #7 is shut iff the aromatic-amination FAKE stays demoted** (it does). The *general* N-C
  recognizer still collides and is still not shipped; only the class-specific one is. The three
  upstream probes and their tests were updated to this re-framing and their FROZEN_HASHes
  re-frozen — a downstream consequence of the sanctioned change, not a scope change to their own
  claims.
- **A VOUCH is type-validity, not feasibility (unchanged).** A VOUCH says only "a mechanism of
  this reaction TYPE exists" (Problem A). It is NOT a feasibility claim (Problem B): caffeine
  N-methylation needs a real methylating agent and conditions the feasibility layer still guards.
  The demoter only ever ADDS a blocker; it never lifts the feasibility guard.
- **Carried forgery debt (NOT touched this round).** The R58/R59 note that a serialized response
  can be tampered to forge a reaction centre is orthogonal and unchanged here.
