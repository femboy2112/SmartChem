# SmartChem 0.9 — Capability Compiler RELEASE RECORD (Round III, 2026-09-28)

**Branch** `feat/v0.9-capability-compiler` off `main@df1b38d`. This record is the whole-path account of the 0.9
Capability Compiler as it earns `0.9.0a1`. It supersedes nothing; it *closes* the Round-III barrier
(`V0_9_CAPABILITY_COMPILER_ROUND_III_FREEZE_2026-09-28.md`) and reports the built, verified result.

The one-line thesis Round III set out to prove: **the machine means what it says.** Capability is a projection
over an UNCHANGED chemistry search; a `CAPABILITY_FIT` verdict is never a false pass; every axis fails closed;
and the frozen forcing matrix is a *faithful consequence of the code*, not a coincidence of the corpus. Below is
the evidence.

## Commit chain (7 ahead of `14311a9`)
`c135ad8` barrier freeze · `9fc438b` Wave-B batch 1 (ProcedureMaterialUse + material fixture + H2SO4 hazard) ·
`bc8f294` Wave 2a (MeasurementMethod vocab + resolver) · `b00cb05` Wave 2b (capability fold) ·
`b79f4dc` Wave 3 (service/transport, D10-D12a) · `6ca3849` Wave-C hardening (F1/F2 fix + M1-M40 gate).

---

## Pure capability closure

- **Material requirement source law (D1).** The universal reaction-class `0.98` esterification assay floor is
  RETIRED (killed M23). Assay/formulation is source-scoped per input: the acetic-acid leaf earns `Phase.LIQUID`
  + a `DERIVED_WITH_ERROR` ≥0.99 assay ONLY when *this* route's sourced procedure says "glacial"; the alcohol
  earns a neat `Phase.LIQUID` requirement (compatibility by phase, no fabricated assay); everything else stays an
  honest `required_assay=None`. Vinegar (a few-% aqueous solution) BLOCKS the acetic requirement on BOTH phase
  (`AQUEOUS_SOLUTION` ≠ neat `LIQUID`) AND assay — gate-#18 discrimination preserved without the retired floor.
- **Procedure-only material representation (D2).** New SOURCE-evidence type `ProcedureMaterialUse` on
  `ProcedureOperation.material_uses`, with `identity: Molecule | None` — honestly optional, because the ionic
  auxiliaries (NaHCO3/NaCl/MgSO4) cannot resolve to a `Molecule` (the SMILES parser refuses disconnected species)
  and petroleum ether / charcoal are not pure compounds at all. Projected into the ONE material axis (killed M24);
  a procedure material NEVER silently drops.
- **Quantity + formulation (D3/D4).** `MaterialRequirement.quantity`/`.phase` now gate: unit-aware quantity
  (same-unit numeric; any unit mismatch or unknown stock amount → UNKNOWN, NO conversion engine; killed M25); phase
  equality with `Phase.UNKNOWN` never clearing a known phase requirement (killed M26).
- **Measurement identity (D5).** New specific `MeasurementMethod{MASS, MELTING_POINT, INFRARED_SPECTROSCOPY}`
  compared member-against-member, never the coarse tier (killed M27/M28 — an NMR does not clear an IR requirement).
  The FeCl3 spot test (reagent + eyeball) and percent yield (arithmetic over MASS) are deliberately excluded.
  `INFRARED_SPECTROSCOPY` is the discriminator: poor-man lacks it → isopentyl BLOCKS on measurement.
- **UNCONSTRAINED semantics (D6 + Wave-C F1).** A real route demand on a dimension the profile leaves unbounded is
  UNKNOWN, never a free ride to FIT — and (the Wave-C fix) this now holds PER DIMENSION, not just for an all-`None`
  ceiling. Presets declare real finite bounds, including the honest atmospheric floor `min_pressure_atm=1.0`.
- **Budget semantics (D7 + Wave-C F2).** The monetary axis enforces the same `(currency, unit)` law
  `affordability.dominates` holds; a mismatched OR undeclared (empty) denominator is UNKNOWN, fail-closed — never a
  raw-number compare (killed M30/M31; the empty-denominator wildcard is closed). No production-quantity bridge is
  built. Budget stays optional (no budget → outside the question).
- **Ventilation (D8).** An EXPLICIT reserved axis, surfaced in every assessment (`NOT_APPLICABLE` + a "RESERVED"
  note), never a silent green check (killed M32). OUTDOOR NEVER substitutes for a containment requirement (M6 held).
- **Hazard/waste fold (D9).** Procedure-only material hazards feed containment where the identity resolves and a
  GHS record exists (H2SO4 H314 → FUME_HOOD, killed M33, made non-vacuous by the added sourced sulfuric-acid
  record). Unresolvable/unnamed species are carried as an explicit `hazard_unresolved` note, surfaced, fail-closed
  visible — never silently benign.

## Service / transport

- **Request capability representation (D10).** `CompilationRequest.capability_profile: CapabilityProfile | None`
  stores a RESOLVED immutable snapshot (a bare preset name is REFUSED — killed M34) + an optional origin name;
  default `None` = NOT_REQUESTED, no assumed bench (killed M37).
- **Search noninterference (PROVEN).** `capability_profile` enters the full `.digest` for provenance but is ABSENT
  from the hand-built `semantic_digest` tuple; `recompile_to_ir` takes only scalars, never the request. Independently
  verified: `semantic_digest` is byte-identical across {no profile, research-lab, poor-man, inline custom}; only the
  request digest, `capability_question_digest`, per-route `capability_assessment`, and `result_digest` move
  (killed M7/M8/M36).
- **Custom-profile transport (D11).** One canonical wire shape for preset AND inline custom (fail-closed whitelisted
  decoder); the resolved snapshot round-trips exactly, never re-resolved.
- **capability_question_digest (D12).** `canonical_digest((semantic_digest, profile_digest))`, additive to the
  existing consumer pin; moves under a profile-content change, never under a search-question change; the search
  identity never moves under a profile change (killed M20/M35).
- **Load-time rebind (D12).** `CAPABILITY-REBIND-ON-LOAD` re-derives the assessment per route from the replay
  payload + the request-bound profile and REFUSES structural mismatch — altered verdict, profile-A-under-B,
  assessment-on-NOT_REQUESTED, stripped stock (killed M19/M38). Thin/advisory wire never claims verified FIT.
- **Human ≡ JSON (D12a).** `--capability-profile` on `plan` + `recompile`; a `CAPABILITY[origin]` line beside
  READINESS with the scope note; unassessed/reserved axes stay visible, never a green check by omission.

## The forcing matrix (SAME real searched isopentyl-acetate route, PROCESS_SPECIFIED, as the code produces it)

| profile | overall | driving axes |
|---|---|---|
| **research-lab** (no stock) | **UNKNOWN** | material UNKNOWN (no declared stock); every other axis FIT/NA/UNCONSTRAINED |
| **poor-man** | **BLOCKED** | equipment (no reflux/fractional distillation) + measurement (no IR) + containment (no hood for H2SO4), all BLOCKED; monetary UNKNOWN (denomination) |
| **fully-declared Custom** (`isopentyl_capability_fit_bench`) | **CAPABILITY_FIT** | every axis FIT/NA/UNCONSTRAINED — material, equipment, physical, process, containment, measurement, waste, procurement all FIT |
| Custom − containment | **BLOCKED** | containment (fume hood) |
| Custom − fractional distillation | **BLOCKED** | equipment |
| Custom − IR | **BLOCKED** | measurement |
| Custom, vinegar-for-glacial | **BLOCKED** | material (phase AND assay) |
| Custom, insufficient stock quantity | **BLOCKED** | material (10 mL < 20 mL, same-unit shortfall) |
| Custom − procurement reach | **BLOCKED** | procurement |
| aspirin / paracetamol (FORMAL), methyl salicylate (CONDITIONS_SUPPORTED) | never FIT | tier HARD LAW caps below PROCESS_SPECIFIED (assessable, never overall FIT) |
| retro-Diels-Alder (REACTION_VOUCHED, null) | never FIT | hooded benches UNKNOWN; poor-man BLOCKS on 1,3-butadiene containment (honest — see matrix correction) |

**Matrix correction (truth over a prettier matrix).** The barrier called retro-DA a "null case: profiles MUST NOT
diverge." Wave C found the premise wrong: the retro-DA balanced equation carries 1,3-butadiene (IARC-1) with a real
GHS record, so its containment axis legitimately forces a hood — poor-man (no hood) BLOCKS while hooded benches are
UNKNOWN (tier-capped). This is NOT laundering: the durable law holds (below-PROCESS_SPECIFIED NEVER FITs; identical
search feeds every profile). Suppressing a real carcinogen's containment to keep a prettier null row would have been
the dishonesty the round exists to prevent.

## Evidence

- **Mutation gate:** `experiments/v0_9_mutation_calibration.py`, **M1-M40, 40/40 killed, 0 vacuous, 0 survived**
  (`.venv/bin/python experiments/v0_9_mutation_calibration.py`, exit 0). M39 (partial-bounds physical) + M40
  (empty-denominator monetary) are the discriminators the original M29/M30 were too weak to be — the reason the gate
  first missed F1, and the reason it never will again.
- **Funnel/census:** `experiments/v0_9_capability_funnel.py` + `V0_9_CAPABILITY_FUNNEL_RESULTS.md`,
  **75/75 properties hold**; 7 searched routes, profile-blind; only the fully-declared Custom bench reaches
  `CAPABILITY_FIT` (research-lab 0, poor-man 0, Custom 1); per-axis census with the denominator never narrowed.
- **Wave C (fresh non-author hostile review, evil-morty directed + dalembert structure-theorem):** two independent
  adversaries CONVERGED on **F1** (P0 physical per-dimension false-FIT) and **F2** (monetary empty-denominator
  fail-open) — both **FIXED** (`6ca3849`), reproduced-then-re-verified on the real path, guarded by
  `tests/test_v0_9_wavec_fixes.py` (10 passed) + M39/M40. Everything else they attacked — the rebind, the generic
  canonical decoder, search noninterference, the tier firewall, the material interval logic, the source-scoped
  assay direction — **HELD under genuine attack** (documented survival boundaries, not unearned clean bills).
- **Targeted v0.9 tests:** 159 passed (core + fit-positive + presets + round-III + procurement + stock +
  procedure-evidence + measurement + material + procedure-material) + 14 transport + 10 Wave-C regression.
- **Full OOM-safe suite (`scripts/run_suite.sh`):** **GREEN** — **5757 passed, 0 failed, 0 errors, 46 skipped**
  (rdkit `importorskip`-skips; 5803 collected across 33 batches, fresh process per batch, exit 0). No 0.7/0.8
  regression: the 0.8 baseline was 5628 passed / 0 / 46 skipped, so +129 passing tests from the v0.9 core, the
  service/transport wiring, the Wave-C regression suite, and the two batch-1 regression fixes — and the same 0
  failures/errors. **Gate closed.**
- **Hosted CI:** none on this branch (no workflow evidence) — preserved distinction.

## VERIFIED DEFERs (with exact release boundaries)

1. **D9 hazard coverage is name/resolution-dependent.** A resolvable, *named* hazardous procedure material (H2SO4)
   forces containment; an ionic or unnamed hazardous species (identity `None`, no GHS-name match) lands in
   `hazard_unresolved` and raises NO containment requirement, so containment can read FIT and ride to overall FIT.
   This is a freeze-declared boundary: **CAPABILITY_FIT is explicitly NOT a safety certification.** The
   covalent-and-named-forces-a-hood / ionic-or-unnamed-escapes asymmetry is stated here loudly. Boundary: closed
   when the SMILES→name resolver (in the off-limits `decompiler_review.py`) can name small inorganics, or a
   name-keyed hazard table lands.
2. **Process-time omission = "unlimited patience."** A bench declaring attention/agitation but no time ceiling does
   not gate a route's time demand. Defensible (time is not a hard physical ceiling like T/P — one can always wait);
   NOT a false-FIT. Boundary: if a future round makes time a hard capability, the same per-dimension rule as F1
   applies to the process delegate.
3. **FeCl3 spot test + percent yield** excluded from `MeasurementMethod` (reagent/arithmetic, not instruments);
   a later round may model reagent-confirmation as a MATERIAL possession requirement.
4. **Per-material reactant quantity** is source-authored per route in `requirements.py` (the isopentyl volumes),
   gated on the sourced procedure + "glacial"; generalizing it to arbitrary quantity-bearing routes is a later
   round's structured-quantity work.

## Release

- **Version:** `0.9.0a1` — bumped iff the full suite closes green (see above).
- **PR:** merge-ready `feat/v0.9-capability-compiler → main`, opened for EXTERNAL release review. **NOT MERGED** —
  external review has the final say.
- **Blockers:** none outstanding on the pure/transport/evidence layers; the only open gate item is the full-suite
  green (running).

## 1.0 runway

After 0.9 merges: **0.9.5 Adversarial Release Candidate** (freeze the complete product and attack it end-to-end —
plan in `V0_9_5_ADVERSARIAL_RC_PLAN_v0.1.md`), then **1.0 Stable Chemical Compiler**. No new reaction classes, no
new chemistry family, no capability-fit by omission. The remaining game is proving the whole machine means what it
says — Round III proved the capability projection does.
