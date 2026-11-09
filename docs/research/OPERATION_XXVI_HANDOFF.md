# OPERATION XXVI — handoff (prose + evidence)

**Closed 2026-11-09.** Baseline main `4d8149a` (XXV #170) → **final main `007cb36`**. Production release v1.6.0
(`ac8bdde`) **untouched**; production `__version__` unchanged. Main CI confirmed green at every merge (runs
`42569643986` on `3354d6e`, re-confirm `42609213336` on `007cb36`). Every item below was independently verified by
the integrator against the filesystem, never on an executor's word.

## Headline: a real production soundness defect, found by adversary and fixed

A directed chemical adversary (d'Alembert) broke the reaction-type oracle's **"0 false-VOUCH" cardinal**: the
etherification recognizer VOUCHED **acetalization** (`hemiacetal + alcohol → acetal + water`, e.g.
`COCO + CO → COCOC + O`) as an etherification. Dimethoxymethane is formaldehyde's dimethyl **acetal** — its central
carbon bears two C–O bonds, a MASKED CARBONYL — so this is a different reaction class, not Williamson/dehydrative
ether coupling. Reproduced by the integrator. **Root cause:** `_ether_oxygen_counts` counted an acetal O as a
"dialkyl ether"; the `("O",)` single-cut re-derivation is blind (exactly one C–O bond forms). The N-alkylation
recognizer had already closed the analogous **donor-side** hole (`_alkyl_carbinol_alcohol_count`); the ether
**product** census never got it.

**Fix (minimal, product-side):** `_carbon_bears_other_heteroatom` + an acetal-guard in `_ether_oxygen_counts`
(`smartchem/experiment/feasibility.py`). Blast radius confined — both changed censuses feed only the etherification
recognizer. **Evidence:** 3 acetal/orthoester false-vouches now DEMOTE; 3 genuine etherifications (incl. the
non-locality case) still VOUCH; **260 passed** across oracle + production-algebra + affordability-frontier +
CLI-JSON-wire + service/evidence goldens, zero drift; corpus `tests/test_etherification_acetal_false_vouch_xxvi.py`
(6 tests, RED→GREEN). The full CI suite then caught one further frozen-hash pin (R58 span-local probe) that my
intended behavior change legitimately moved; a pre/post `_payload()` diff proved the delta benign (only
`ether_k2_census_vouched`/`ether_k2_span_demoted_bundles` 368→448, equal; `false_vouch_count=0` and every soundness
invariant unchanged), so the hash was consciously re-frozen.

**Reachability:** the R58 probe's `false_vouch_count` was **0 pre-fix**, so the acetal case is **latent within the
tested reachable frontier** — a real soundness hole, not a proven shipped wrong-route. Full-frontier reachability
is a PROBE-GAP (deferred: a daniel probe over single-cut C–O scissions whose target carbon bears a 2nd O/N).

## What shipped to main `007cb36`

### WAVE 1 (PR #177 → `3354d6e`)
route-search invariant salvage (#171, 12), `smartchem doctor` + Makefile + contract re-freeze (#172, 63),
CURRENT.md + exit-code/architecture doc fixes (#173), runnable API examples (#174, 6), pluggable
coproduct-producer registry byte-identical to 1.6.0 (#175, 122), #168 COT identity pin + versioned design (#176, 5).
Merge tree == tested head tree; #171–176 auto-closed.

### WAVE 2 + 3 (PR #180 → `007cb36`)
- **#130 (#178, research-only):** route/stock identity keys (`resonance_identity`, `stock.structure_key`) are
  constitution-only and collapse configuration/isotopic distinctions the perception layer carries; the phase I-D
  hazard ((R)-stock satisfies (S)-demand) pinned in core CI. 11 tests.
- **#109 must-not-vouch (#179, research/test-only):** the oracle demotes 6 generated fictions + 2 positive controls
  vouch (one sharing reactants with a fiction, decided oppositely). 8 tests.
- **#109 acetal false-VOUCH FIX (#181, production):** the headline above. + R58 probe re-freeze.
Merge tree == tested head tree; #178/#179/#181 auto-closed.

### Probed and honestly closed as a NON-defect
- **#105 per-atom charge:** the charge-identity model is **sound within its represented scope** — the true
  nitromethane resonance pair collapses correctly (same molecule), genuine charge differences separate, and
  net-neutral local charge already fail-closes via `local_charge_loss`. #105 is a represent-more-information
  *prototype* ask, not a defect. No fabricated pin was shipped. Deferred to next round as a real prototype build.

## Disk hygiene (user directive: mind disk, lose nothing load-bearing)
Reaped 9 redundant git worktrees after confirming each was clean and its branch on origin; reclaimed the earlier
~8.6G pip-cache/throwaway-venv space in-session. Primary checkout only; ~70G free. No branch, venv, PDF, wheel, or
source lost.

## Truth-boundary ledger (nothing collapsed)
- **Formal validity:** route-invariant + coproduct pins hold; default digests byte-identical; #130/#168 identity
  collapses pinned (not silently "fixed" into the frozen 1.x contract).
- **Chemical recognition:** the oracle's 0-false-VOUCH cardinal was BROKEN, then REPAIRED and regression-pinned;
  #109 must-not-vouch pins guard it.
- **Process feasibility:** untouched (no new feasibility claim).
- **Physical prediction:** untouched; **2.0-alpha stays NOT MET** (no measured-pCO2 holdout; Guidone tier-W only).

## Release
No v1.7.0 (dehydration #116 still DEFERRED; no additive class qualified). **v1.6.1 is a real CANDIDATE** (a genuine
patch defect in shipped v1.6.0 was fixed) but was **not cut this round**: the defect is latent within the tested
frontier, the prompt says don't force a minor version, and the decision is surfaced to the user. v1.6.0 tag
untouched. No PyPI. No LibGibson main merge.
