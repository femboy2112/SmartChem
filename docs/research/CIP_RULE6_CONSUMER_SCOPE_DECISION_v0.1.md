# CIP Rule 6 — a VERIFIED DEFER (queue item 1)

Status: **verified defer, committed evidence.** Lane B. `[[an-oracle-driven-existence-check-can-prove-a-defer]]`
`[[a-sound-extension-guards-its-new-cross-comparisons]]`

The queue's gate on CIP Rule 6 is explicit: *"Build only with a real Rule-6 consumer + source-exact
discriminator (4b/4c is a verified-defer with a phased plan)."* There is no real Rule-6 consumer, and building
the machinery would be dead, mislabel-prone code sitting downstream of an unbuilt, proven-empty rule. So the
correct outcome this round is a **verified defer** with committed oracle evidence — the R32 (Rule 1b) / R36
(Rules 4b/4c) precedent. Doing the existence proof honestly **is** doing the task.

## What Rule 6 is, and why it is downstream of 4b/4c

Rule 6 is the reference-dependent **like/unlike** sequence-rule tail: it discriminates two ligands that have
already tied through Rules 1a, 1b, 2, 3, 4a, revised 5, **and** the target-relative Rules 4b/4c, by the relative
(*like* vs *unlike*) pairing of their auxiliary stereodescriptors. By construction it fires only AFTER 4b/4c.

Rules 4b/4c are a **VERIFIED DEFER** (ROUND 36, `CIP_TARGET_RELATIVE_RULES_SCOPE_v0.1.md`): no north-star or
real-chiral consumer forces them, and the repo has no genuine Rule 4b (its `_cip_compare_rules45` is a faithful
port of RDKit's Rule5New two-fixed-reference trick, not the per-branch nearest-sphere majority-vote reference a
real 4b needs). A Rule-6 consumer would therefore have to be a 4b/4c consumer first — and there is none.

## The structure theorem — Rule 6 has no reachable trigger

The implemented CIP spine (`smartchem/smiles.py`) is Rules **{1a, 1b, 2, 3, 4a, revised 5}**; there is no Rule-6
branch and no code path can call one (`_cip_ranks_with_aux` terminates a Rule-5 tie at `return None`,
`smiles.py:1843-1844`).

A framing precision (dalembert): in the *code* there is no literal 4b / 4c / 6 dispatch — the reference-dependent
discrimination is folded into `_cip_compare_rules45` (RDKit's Rule5New two-fixed-reference trick), so "downstream
of 4b/4c" is a statement about the *spec* hierarchy, not the executed path. The OPERATIVE code-level gate on
reachability is the auxiliary-pool ADMISSION CAP, which the probe verifies **behaviourally** (the aux pass is
never entered with `|pool| > 2` across the battery, checked by wrapping `_cip_ranks_with_aux` — not by grepping
the gate's source). The auxiliary-descriptor pass Rule 6 would extend has a precise bottleneck:

1. **The auxiliary pool is the pass-1 named centres** — `auxiliary = dict(labels_by_atom)`
   (`smartchem/smiles.py:1957`). Rule 6 reads the SAME pool (it compares like/unlike pairings drawn from it).
2. **The pool is admitted only at size 1 or a single R,S pair** —
   `len(auxiliary) == 1 or (len(auxiliary) == 2 and set(auxiliary.values()) == {"R","S"})`
   (`smartchem/smiles.py:1961-1962`). A larger auxiliary system — the first place a like/unlike **pair**
   distinction can even exist, since comparing *like* vs *unlike* needs ≥ two descriptor pairs — is REFUSED
   admission and defers before any auxiliary comparison.
3. **Within the admitted ≤2 pool, every pair either resolves or has an empty effective pool.** Revised Rule 5
   (`_cip_compare_rules45`, `smiles.py:1649-1662`) returns an ordinary ±1 Rule-4a distinction or a ±2
   pseudoasymmetry when the pool discriminates, and `0` (→ `return None`, defer) when it does not. Neither branch
   leaves a like/unlike residual: the resolved branch is already ordered; the empty-pool branch has nothing to
   compare.

**Therefore Rule 6 has no reachable trigger in the admitted representation.** A trigger requires (a) admitting a
larger auxiliary system, AND (b) building target-relative Rules 4b/4c to populate and order it — both the
deferred 4b/4c round. Rule 6 unparks strictly after 4b/4c.

## Empirical confirmation (RDKit `rdCIPLabeler`, dev-venv-only oracle)

`experiments/cip_rule6_consumer_probe.py` (FROZEN_HASH `7be84bc8…`, RDKit-free `validate()` + gated
`_rdkit_cross_check()`), battery: the shared empty-pool forcing class, non-empty-pool controls, and the existence
set (north-star achiral targets + real chiral drugs). Results, blessed against RDKit 2026.03.6:

- **0 mislabels** across 16 per-atom comparisons — the shipped namer never disagrees with RDKit on a centre both
  name (the permanent differential-validation value, as in R32/R36).
- The **forcing class** (`4-methylcyclohexan-1-ol`, `1,4-dimethylcyclohexane`) is DECLINED by the repo (empty
  pool → `()`), and RDKit names it a **pseudoasymmetric `s,s`** — a 4b/4c-class recursion assignment, NOT a
  like/unlike Rule-6 tie. `forcing_confirmed = 2`.
- The **non-empty-pool controls** (ring pseudoasymmetry `→ r`, trihydroxyglutaric `→ s`) are RESOLVED by revised
  Rule 5 with no residual — the admitted-pool case never reaches a Rule-6 tie.
- The **existence set** — north-star targets (paracetamol, aspirin) are stereocenter-free; real chiral drugs
  (menthol, tartaric, glucopyranose) are fully named by the shipped rules. None needs Rule 6.

## Why a hack would be UNSOUND (not merely incomplete)

The repo has no auxiliary-pool machinery beyond the bounded ≤2 admission and no genuine 4b/4c. A special case that
named a like/unlike tie without the real 4b/4c recursion + a larger-pool representation would silently diverge
from RDKit wherever the reference or the pairing actually matters — a **mislabel**, worse than an honest decline
(`a-sound-extension-guards-its-new-cross-comparisons`). A wrong R/S is worse than none.

## The build boundary and the next consumer

Rule 6 is not buildable soundly until: (1) the charged/conjugated ring representation admits a larger auxiliary
system (queue item 2), and (2) target-relative Rules 4b/4c are built (the R36 phased plan). Only then can a
like/unlike PAIR distinction exist and be ordered. A source-exact Rule-6 discriminator would be a synthetic
molecule tying through Rules 1a–5 and 4b/4c with a non-empty ordered pool differing solely in like/unlike
pairing, plus an RDKit oracle bearing — none exists in-scope. **Unpark when 4b/4c is built and such a forcing
fixture appears.**

## Files

- `experiments/cip_rule6_consumer_probe.py` — the FROZEN_HASH evidence harness (RDKit-free `validate()` +
  structure-theorem assertion + gated `_rdkit_cross_check()`).
- `tests/test_cip_rule6_consumer.py` — pins the defer, the structure theorem, and (gated) 0 mislabels vs RDKit.

## Adversarial review — two orthogonal bearings before merge

**The defer is sound and the no-consumer claim survived a real attack.** No bearing found a mislabel or a
reachable Rule-6 consumer.

- **dalembert (structure-theorem refutation):** SURVIVED. He drove **173 distinct molecules** through the engine
  (77 reflection-pairs + 96 shape-scan: rings, chains, mixed heteroatoms, 3–5 stereocentres), instrumented
  `_cip_compare_rules45` / `_cip_ranks_with_aux`, and found: when the aux pass is entered it named 12/12 with
  **zero non-empty-pool deferrals** (no admitted-pool tie a like/unlike Rule 6 would break); the ≤2 admission cap
  is code-guaranteed structural, not coincidence (4- and 5-stereocentre molecules never enter the aux naming
  path); reflection invariance 77/77, keyset consistency 0 violations, meso self-consistency correct, two
  hand-verified sign anchors match. **Two folds applied:** (1) he flagged that `_assert_structure_theorem` used a
  source-string grep (`inspect.getsource` + substring) as a stand-in for a semantic invariant — the
  `checks-derived-from-their-own-subject` hazard — so it is now a **behavioural** check (wrap `_cip_ranks_with_aux`,
  assert the aux pass is never admitted `|pool| > 2`; a gate weakening trips it, a spelling refactor does not);
  (2) the "downstream of 4b/4c" premise is sharpened to a spec-hierarchy statement with the admission cap named
  as the operative code-level gate (above). **The honest boundary he named:** he could not run the RDKit
  absolute-sign sweep (rdkit is dev-venv-only, intentionally uninstalled), and reflection invariance alone cannot
  catch a *systematically swapped* r↔s / R↔S sign convention. That leg is closed here by the committed gated
  `_rdkit_cross_check` — **0 mislabels across 16 per-atom comparisons vs `rdCIPLabeler`, r/s sign included** (run
  at authoring time against RDKit 2026.03.6) — plus his two hand anchors and meso-consistency. Epistemic status:
  **Conjectured-sound with a triangulated adversarial line**; the upgrade path to Demonstrated is the gated RDKit
  cross-check, which passed.
- **mr-president (acceptance):** SHIP. The VERIFIED DEFER legitimately discharges the conditional-build mandate
  ("build only with a real consumer + source-exact discriminator") on the R32/R36 precedent: the existence proof
  is real and source-grounded, the boundary + unpark trigger are named checkably, and nothing load-bearing is
  over-claimed (the finite battery is positioned as differential corroboration, the structural admission-cap
  argument as the load-bearing proof). Condition raised — fill this review section (done) — and a note that the
  RDKit leg is corroboration, not the load-bearing proof (which stands RDKit-free); both honoured above.
