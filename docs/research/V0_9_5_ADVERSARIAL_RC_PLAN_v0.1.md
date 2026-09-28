# SmartChem 0.9.5 — Adversarial Release Candidate PLAN (v0.1)

**Status:** PLAN only. Do NOT implement until 0.9 merges and external review clears it. 0.9.5's job is **not new
features** — it is to FREEZE the complete product and systematically attack it end to end, until the whole pipeline
demonstrably means what it says. No new reaction classes. No new chemistry family. No capability-fit by omission.

The finite ladder: `0.6 ✅ → 0.7 ✅ → 0.8 ✅ → 0.9 ✅ (Round III + Round IV external audit) → 0.9.5 Adversarial RC → 1.0 Stable`.

Round III proved the *capability projection* is sound under a fresh hostile review (two adversaries converged on
F1/F2, both fixed; everything else held). 0.9.5 widens that discipline to the ENTIRE pipeline, from raw human input
to the final dossier, with denominator accounting at every stage — nothing graded on the pretty cases.

---

## Round IV audit — the findings 0.9.5 must keep dead (folded in 2026-09-28)

0.9's external audit (Round IV) found and closed a NEW class of composition / whole-path overclaim beyond Round
III's F1/F2 (F41–F56). 0.9.5 re-attacks the FROZEN product against every one; each already has a calibrated mutant
(M41–M61) that must stay dead, and the attack surfaces below are enriched accordingly:

- **Resource conservation (F41/F42/F50)** — repeated procedure materials must SUM (25 mL ×2 = 50 mL; 55+10+25 = 90);
  finite stock is a POOL a bottle cannot be spent twice from (a small max-flow allocation); distinct-spec uses of
  one species never collapse. Attack the allocation with knife-edge inventories + multi-bottle aggregation.
- **Material semantics / identity (F43/F44)** — a formulated wash needs a TWO-SIDED composition band (100% bicarbonate
  ⊬ "5% wash"); a structure-known requirement matches ONLY structure-keyed stock (a bare name never stands in).
  Re-attack every substitution (hydrated⊬anhydrous, unsaturated⊬saturated, wrong-%⊬5%, name⊬structure).
- **Typed derived data (F46/F55/M57/M58)** — every interval flows through `DerivedIntervalEvidence`, whose
  construction REFUSES a value its own `derivation_fn(inputs)` does not reproduce; `unit` distinguishes
  mass-fraction-of-solution from mass-per-100g-solvent (the NaCl bug). Attack a decorative/unsupported band.
- **Unknownness (F47/F48/F49) + the FOLD CONTRACT (F56/Decision 11)** — the per-dimension fail-closed law (*a real
  demand on an unmodeled or exhausted capacity → UNKNOWN, never FIT*) must hold on EVERY axis, not one: process time
  (F56), material capacity (F42), hazard→containment (F47), spent-stream→waste (F48/F49). Re-attack for any axis that
  still launders an omission into a pass.
- **Topology / CLI / transport (F51/F52/F54)** — a capability request under convergent DAG is typed-REFUSED, not
  silently unassessed; `compile` human ≡ `--json` ≡ `recompile` on every capability field; a legacy v0.8 RESPONSE
  loads additive-optional (profile/assessment None, no crash, no fabricated FIT) — 0.9.5 must land a real
  v0.8-producer-emitted RESPONSE fixture (not only the request fixture already committed).
- **Held-out genericity (F45)** — a benign held-out `ProcedureEvidence` with typed reactant/auxiliary
  `ProcedureMaterialUse`s must project correctly WITHOUT adding its identity to `requirements.py`.
- **Source substitution (M60)** — a swapped `ProcedureMaterialUse` (species/quantity/formulation) must move the
  digest and be refused on rebind.

**The vanished FIT positive is a 0.9.5 target.** 0.9 ships with `CAPABILITY_FIT` rigorously defined but UNREACHED on
the current corpus: the one PROCESS_SPECIFIED route (isopentyl) reads UNKNOWN because its sourced procedure
under-specifies whole-process DURATION (only the 1-hr reflux floor is timed), the ionic auxiliaries' HAZARDS, and the
spent-stream DISPOSAL. 0.9.5 must determine whether ANY corpus member can HONESTLY reach FIT once those three are
sourced (a fully-timed, disposal-declared, benign-auxiliary procedure), or confirm the ceiling and carry it to 1.0.
Fabricating a duration/hazard/disposal remains banned.

---

## The frozen end-to-end corpus (the spine of 0.9.5)

Freeze one corpus and drive it through EVERY stage, counting the denominator at each:

```
raw human input  →  identity (parse/resolve)  →  search  →  real route  →  procedure readiness
                 →  capability projection  →  final dossier (canonical transport)
```

At each arrow, record: how many inputs entered, how many survived, how many were correctly refused, and WHY each
drop happened. A stage that only ever sees the friendly inputs is not tested. The corpus MUST include:
the 0.6 human front-door phrasings; the ester/analgesic teaching corpus (isopentyl acetate, aspirin, paracetamol,
methyl salicylate); the DOW bromine + paracetamol litmus targets; ambiguous / mis-parseable names; below-tier
routes (FORMAL / CONDITIONS_SUPPORTED / REACTION_VOUCHED); the null retro-DA; and a held-out route NEVER seen during
0.6-0.9 development (the generalization probe).

---

## Attack surfaces (each gets a directed adversary + a structure-theorem adversary + a seeded fuzzer)

1. **Front-door parser** — malformed, adversarial, Unicode-confusable, and over-long human inputs; injection-shaped
   strings; the silent-mis-parse class 0.6 already closed — re-attacked for regressions.
2. **Ambiguity** — inputs with >1 plausible identity; does the compiler refuse / disambiguate / never silently pick?
3. **Identity** — same-formula constitutional isomers, stereo/isotope blindness (the declared ID-layer boundaries),
   resonance/Kekulé spellings, ionic species the SMILES parser refuses.
4. **Search completeness** — does the bounded search's completeness receipt mean what it claims? Attack the
   `search_space_status` and the transform-registry/algebra digest.
5. **Transform algebra** — the 0.7 production algebra; can a profile/algebra selection perturb search identity (it
   must not); can the certified-vs-legacy default boundaries be crossed silently?
6. **Procedure evidence** — the 0.8 ProcedureEvidence + the 0.9 ProcedureMaterialUse; source-substitution attacks
   (swap a sourced procedure/material and demand the digest/rebind refuses); the F3 hazard-scan blind spot.
7. **Material / profile evidence** — StockMaterial interval logic, name-vs-structure keying, the DERIVED_WITH_ERROR
   intervals (anti-fabrication: every interval must trace to a citable source), the capability profile snapshots.
8. **Capability projection** — re-run the full Round-III false-FIT hunt (F1/F2 regressions + the axes that held) on
   the FROZEN product; attack the D9 hazard name/resolution asymmetry the release record defers; the
   process-time-as-unlimited-patience boundary.
9. **Source substitution** — across procedure, material, hazard, and price data: any altered source must move the
   relevant digest and be refused on canonical load.
10. **Schema migration + legacy payloads** — every pre-0.9 serialized request/response must load safely (no assumed
    bench, no crash); every schema-version bump must be honored; a payload from 0.7/0.8 must not silently gain 0.9
    semantics.
11. **Canonical replay** — the thick/thin wire discipline; CAPABILITY-REBIND-ON-LOAD + ALGEBRA-REBIND + readiness
    rebind, all fail-closed under tamper; the generic canonical decoder whitelist (Round-III Wave-C flagged it sound
    only because no live Molecule is in the graph — re-attack if any new capability type embeds one).
12. **Deterministic output** — same input → byte-identical output across runs/processes; the digests are stable.
13. **Optional-backend matrix** — RDKit present (dev) vs absent (committed baseline): the committed behavior must be
    identical; rdkit-only tests importorskip-skip; NO backend may change a verdict.
14. **Performance** — the amide-heavy `Molecule.canonical()` resonance cost; the OOM-safe suite batching; search
    bounds under adversarial depth/branching; no pathological blowup on the frozen corpus.
15. **Held-out chemistry** — a route/target never seen in 0.6-0.9 dev: does identity/search/readiness/capability
    behave honestly (correct refusal or correct projection), or does it expose a corpus-coincidence?
16. **CLI / API / human / JSON equivalence** — the three CLI surfaces (plan/recompile/compile); human render ≡ JSON
    semantics on every field; no surface exposes a verdict another hides.

---

## Method (inherit Round III's, widened)

- **Parent barrier freezes the attack corpus + expected-result oracle FIRST** (an independent oracle, blind to the
  implementation, like Round-III Lane F).
- **Fan out fresh non-author adversaries** per surface (directed exploit + structure-theorem refutation + seeded
  fuzzer with minimized repros). Every finding: FIXED / REFUTED-WITH-EVIDENCE / VERIFIED-DEFER-WITH-EXACT-BOUNDARY.
- **Any false-FIT, any silent-mis-parse, any digest that fails to move under a real change, any legacy payload that
  gains new semantics — is release-blocking.**
- **Denominator accounting at every stage** — report the full funnel, not the survivors.
- **The mutation gate grows** — every 0.9.5 finding earns a calibrated mutant (M62+), and the M1-M61 gate is re-run
  on the frozen product.
- **Full OOM-safe suite green + no 0.6/0.7/0.8/0.9 regression** is the floor, not the ceiling.

## Exit criterion

0.9.5 earns its tag when the frozen corpus survives the entire adversarial battery with no unresolved
release-blocking finding, every stage's denominator is accounted for, and the end-to-end pipeline is demonstrably
deterministic, fail-closed, and honest from raw input to final dossier. Then, and only then, 1.0 is the stable
contract freeze.
