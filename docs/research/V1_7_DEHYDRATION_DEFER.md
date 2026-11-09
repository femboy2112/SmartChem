# SmartChem 1.7.0 (alcohol dehydration, #116) — DEFERRED

*Decision: 2026-11-08, OPERATION XXV Phase I-E. Production 1.6.0 stays the release; nothing was tagged or published.
The work is kept on `feat/1.7-dehydration-116-r2`; it is not on `main`.*

## 1. The decision and the rule that made it

The OPERATION XXV release gate required **no false VOUCH**: a step that is not real chemistry under its declared
conditions must never be certified. Blind adversaries attacked four successive implementations. Every attack whose
report came back (four of five) found false VOUCHes.

Before the fifth attack was launched, the stopping rule was written down. If it found a false VOUCH inside what the
fourth implementation's rules claim to cover, 1.7.0 would be deferred rather than repaired a fifth time. It did, so 1.7.0 is
deferred. The rule exists so that the standard of proof cannot be lowered after the results are in.

## 2. Coordinates

| | value |
|---|---|
| candidate branch | `feat/1.7-dehydration-116-r2` (unmerged); head `4a14043` |
| implementations 1–4 | `cee2ab3` / `bdd2bd7` / `081837c` / `8796ee3` (commit messages label the repairs r2, r3 and r5) |
| attack-5 corpus pin | `4a14043` (test only, added after this record first merged): `tests/test_dehydration_attack5_corpus_116.py`, targeted run 24 passed |
| version bump + goldens (unreleased) | `00c6a64`: `__version__` 1.7.0; five CLI goldens, where only `tool_version` and `result_digest` moved |
| full OOM-safe suite | `cee2ab3`: 8417 collected / 8367 passed / 0 failed / 50 skipped. `00c6a64`: 8572 / 8522 / 0 / 50. `8796ee3`: 8645 / 8595 / 0 / 50 |
| default grammar | byte-identical to 1.6.0 on every candidate (pinned digests; re-verified by attacks 4 and 5) |
| registry | 26 @ `370164278ebb3bf8` on the branch; 25 @ `d9f7e867e8f1a1d2` on `main` |

The branch is **code-green**. The deferral is about **chemistry**, not about failing tests.

## 3. The attacks

Production and the witness agreed on every case below: they fail common-mode.

| # | attacker, SHA | what broke | repair |
|---|---|---|---|
| 1 | blind adversary, `cee2ab3` | anti-Bredt products (adamantene, cubene) | `bdd2bd7`: named exclusions (bridgeheads, small rings, quaternary C, vicinal OH, sp3-CH aromatisation) |
| 2 | amber, `bdd2bd7` | **report lost** (duplicate hand-back refused); the attack was stopped and is not counted | — |
| 3 | blind adversary, `bdd2bd7` | each named exclusion leaked one step sideways: the H-free aromatisation sibling (dienone–phenol, semibenzene); β-halo / amino / alkoxy / silyl / boryl alcohols; unbounded wall time; isotopes | `081837c`: (e′) carbon-only radius-2 neighbourhood; (f′) ≤ 1 non-π ring atom; (g) unlabelled closed-shell species; positional producer |
| 4 | dalembert, `081837c` | a latent leaving group at radius 3 aromatises the product one step later (cyclohexenediols, 4-halo / 4-acyloxy cyclohexenols, 3,5-dihydroxycyclohexanone → phenol); far-side 1,3-diols; propargylic alcohols (Meyer–Schuster); the shipped BDO → but-3-en-1-ol demo (acid gives THF); a 120 s oracle call; alumina cleared at 298 K | `8796ee3`: (M) **molecule-wide** heteroatom whitelist; (R) radius-1 ring saturation; (S) no sp neighbour; WL-prefiltered certificate; alumina dropped |
| 5 | amber, `8796ee3` | **carbon-skeleton** hazards inside the declared domain, all cleared by the ledger under conc. H2SO4 and all reproduced independently: Friedel–Crafts cyclialkylation onto a pendant arene (2-methyl-4-phenylbutan-2-ol → prenylbenzene; acid gives 1,1-dimethylindan); Nazarov / indanone cyclisation of the vouched divinyl or aryl vinyl ketones; intramolecular hydroalkoxylation of unsaturated alcohols (4-methylpent-4-en-1-ol; acid gives 2,2-dimethyl-THF); aromatic-tautomer rings at radius 2 (isotoluene, semibenzene); acid-labile t-butyl and vinyl esters | none: deferred |

**Also open from attack 5, not repaired:**
- β-acyl acids prone to decarboxylation (a β-keto acid or a malonic acid on C_beta). The vouch is confirmed; whether the chemistry beats decarboxylation is suspected and depends on temperature.
- Hot conc. H2SO4 hydrating a β-hydroxy nitrile. Suspected.
- Producer wall time grows roughly cubically on long polyenes: 32 s at 840 atoms.

## 4. Why the rule kind, not its radius, is the problem

Every bounded rule leaked one bond further out:
- heteroatoms at radius 1 (attack 3); then, once the census had been widened to radius 2, at radius 3 (attack 4);
- carbon at radius 2 (attack 5), once (M) had closed the heteroatom side molecule-wide.

The outcome of an acid-catalysed dehydration is decided by **carbocation chemistry over the whole carbon skeleton**:
- whether a tethered nucleophile (an arene, an alkene, the OH itself) traps the cation;
- whether the cation shifts, expands or contracts;
- whether the product alkene itself survives the acid (cyclialkylation, Nazarov, oligomerisation).

A recognizer that reads a bounded neighbourhood cannot certify that, at any polarity or radius. This is the
R49–R55 theorem again ([`POOR_MAN_STEP_VALIDITY_DEMOTER_DEFER_v0.1.md`](POOR_MAN_STEP_VALIDITY_DEMOTER_DEFER_v0.1.md),
[`POOR_MAN_SYMMETRIC_WHITELIST_PHASE05_DEFER_v0.1.md`](POOR_MAN_SYMMETRIC_WHITELIST_PHASE05_DEFER_v0.1.md)). This time
it was shown in a production candidate across four reported attacks.

**The standard of proof, stated explicitly.** The module docstring scopes the class as structural type-validity only
("an edge never means feasible, favourable or selective"). Under that weaker reading, most attack-4/5 kills are real
dehydrations whose selectivity is poor, not graph fictions.

But the system as shipped makes a stronger claim. A dehydration step with a declared conc. H2SO4 **clears** the
activator ledger, so the route reads as runnable. A route reported runnable must be runnable, so the feasibility
standard the adversaries applied is the right one for this release. Lowering it now would change what the gate
means after the gate failed.

## 5. What a shippable successor needs (maintainer decision)

Any one of these would be a new design, needing its own gate and a fresh adversary.

1. **Scaffold whitelist by name** (the R54 prescription). For example:
   - saturated C5–C8 cycloalkanols and saturated acyclic alkanols with **no other unsaturation or arene anywhere**;
   - β-hydroxy ketones / esters / acids whose acyl partner is saturated alkyl and whose ester alkoxy is a primary or
     secondary alkyl group.

   Even this leaves carbocation shifts, ring expansion and cationic oligomerisation of the product. It needs either
   an explicit "first elementary product, not the isolated product" semantics, or (3).
2. **Re-scope the claim to type validity**, *and* stop the ledger clearing acid dehydration. The step would always
   stay REAL_BUT_HARD with a "conditions not modelled" demotion, so nothing reads as runnable. Coverage stays wide;
   the claim becomes honest.
3. **A measuring model of carbocation fate** (the "model of a different kind"): rank the competing channels by
   computed or sourced cation and product stabilities, and fail closed when a competitor wins or cannot be ruled out.

## 6. What is kept

- The **closed `coproduct_producers` set** in `event_search`. It has a default byte-identical to 1.6.0, identity-matched
  producers and an order-invariant digest, and it is reusable for any future type-3 producer.
- The **positional producer and bounded certificate** pattern: build at the target's indices; certify the built site
  first; canonicalise only on a connectivity-key match.
- The **independent witness**: retro direction, its own ring algorithms; the fourth implementation's conditions were
  written from the spec by a separate author.
- The **adversarial corpora** of every reported attack, as tests on the branch. Any successor must pass them all.
  - The chemistry cases of attacks 1, 3 and 4 are in the recognizer, witness and search tests (spot-checked case
    by case). Attack 4's 120 s oracle call is not pinned as a timing test; only the producer's wall time is.
  - Attack 5's reproductions first lived only in a session scratchpad. They were committed after this record
    was first merged, as `tests/test_dehydration_attack5_corpus_116.py` (`4a14043`). That file pins the defect:
    17 false VOUCHes, 3 suspected-open cases, 1 control, and the false VOUCH reaching the public route search.
    A successor must flip those assertions.
- **#168** (filed from attack 4): the parser and `resonance_identity` merge cyclooctatetraene bond-shift isomers. This
  is a pre-existing, repo-wide identity defect.
- The branch carries an **unreleased** `__version__ = "1.7.0"` and regenerated goldens. A real 1.7.x must redo the bump
  from `main`.
