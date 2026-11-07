# OPERATION XXIV: handoff (the honest universe × source transport × physical crystallization)

These are three different achievements, and nothing in this file counts one as another:
- a correct equation;
- a certified execution;
- an empirically validated physical prediction.

Everything here is **research-only** (`experiments/`, `docs/research/`, `ROADMAP.md`). The installed `smartchem` package is untouched: `git diff v1.6.0 HEAD -- smartchem pyproject.toml MANIFEST.in` is empty.

## 1. Coordinates

**Start:** `main` = `7314e2a44157b27e27a528a0c4bd4efbcb7fb84c`. Main CI run `42347710187` was 9/9 green. `v1.6.0` (annotated) points to `ac8bdde`.

**Branch:** `research/operation-xxiv`, cut from `7314e2a`. Commits:

| commit | content |
|---|---|
| `5e77b98` | preregistered probes + RED receipt, committed before any repair |
| `07292b0` | xxiv-1: five P0 repairs |
| `781b6a2` | xxiv-2/4: the general API and standard-state transport |
| `e718462` | xxiv-5: spatial grid |
| `1cf5a94` | xxiv-3: source grounding |
| (docs commit) | this handoff + ROADMAP |

**Merge:** through a protected-main PR. The merge SHA and CI run are recorded in the PR and in the post-merge report.

**Toolchain:** CPython 3.12.3, numpy 2.5.1, scipy 1.18.0. phreeqpython 1.6.2 is in the dev venv only. The CI-equivalent venv runs `pip install -e '.[dev]'` and has no phreeqpython.

**Outward action:** filed [femboy2112/libgibson#290](https://github.com/femboy2112/libgibson/issues/290) (§10). LibGibson was not modified.

## 2. P0 regressions reproduced and repaired

Each was reproduced RED by `experiments/sandbox_foundation/xxiv_p0_probes.py`, whose PASS/FAIL/AMBIGUOUS rules were fixed before the first run (`docs/research/OPERATION_XXIV_PREREGISTRATION.md`). The receipts are `benchmarks/p0_xxiv/RED_receipt_7314e2a.json` (5 × FAIL) and `GREEN_receipt_xxiv.json` (5 × PASS).

| probe | RED on 7314e2a | repair |
|---|---|---|
| P1 F2-gap | A user operator whose own `descriptor()` omitted its partition fraction got `AUDITED_BUILTIN`/certified, ran strict, and shared one certificate with a physically different world (final X1 0.2 vs 0.8). A post-construction mutation also ran certified. Same result on 1- and 2-compartment worlds. | Operators get the rate-law authority tiers. The closed `_AUDITED_OPERATOR_PINS` covers the 3 in-tree operators; everything else is `register_attested_equilibrium_operator` (bound, never certified, strict needs explicit opt-in) or UNVERIFIABLE. Authority is by exact type; method-swap and instance-override checks apply. |
| P2 p6b | At `atol=1e-2` (coupled) or `1e-1` (kernel), an inventory of −0.5 mol of a 2 mol species came back `positivity_held=True`, `STRUCTURALLY_CONSERVING`. | `admissibility.positivity_audit`. The physical floor is caller-independent: abs (1e-10 coupled / 1e-12 kernel) + 1e-9 × the species' own peak. `atol` only bounds `UNRESOLVED_AT_REQUESTED_TOLERANCE`, never a pass. Raw negative minima are preserved in `negative_minima`. |
| P3 charge | Kernel path, bare Na⁺ feed: `STRUCTURALLY_CONSERVING` with no charge field at all. The coupled path refused it but mislabelled it as transport separation. | One typed `ChargeValidity` on both paths with three separate claims: E_qN = 0 (exact), external-charge accounting (ledger), and bulk electroneutrality. An unsupported external net charge floors the admitted tier to REFUSED while the structural tier keeps its mathematical meaning. Transport separation is judged net of boundary-supplied charge and stays a structural refusal (F3). A declared non-neutral input is reported, not floored. |
| P4 closure | Editing the module helper `_constant_key` so it dropped Ksp's value left `ActivitySolubilityRate` SEALED. Worlds with Ksp 1e-6 and 4e-6 then shared one certificate while final [M⁺] differed by 2×. | Pins hash the **in-tree dependency closure**: the class, its in-tree bases, and module-level functions and constants it references, transitively and across in-tree imports. For operators the closure includes the wrapped `solve()` and its helpers. All pins re-audited. Declared outside the closure: type dependencies (bound per system by the model certificate), stdlib/numpy/scipy, and runtime monkeypatching (the in-process trust boundary, unchanged, not cryptographic). |
| P5 temperature | A 350 K world ran a 25 °C Ksp certified, with a trajectory identical to the 298.15 K one, on both paths. | A sourced constant executed more than 0.01 K off its `T_K` is REFUSED (`SourceDomainError`) on both paths and at API spec time. No temperature law is validated, so none is applied. |

## 3. Tests executed (raw outcomes)

| what | command / venv | result |
|---|---|---|
| Baseline probes on 7314e2a | `PYTHONPATH=. python -m experiments.sandbox_foundation.run_probes` (dev) | 22 PASS / 0 FAIL, OVERALL OK |
| Baseline sandbox on 7314e2a | `python -m pytest experiments/sandbox_foundation/tests -q -p no:cacheprovider` (dev) | 1225 passed, 389.9 s |
| P0 probes, pre-fix | `python -m experiments.sandbox_foundation.xxiv_p0_probes` | 5 × FAIL (receipt committed) |
| P0 probes, post-fix | same | 5 × PASS (receipt committed) |
| Full sandbox, first post-fix run | dev venv | 1289 passed, **3 failed**: XXIII pin-anchor tests still hashing class source, which is the expected consequence of the re-pin. Updated to closure digests; that file then 41 passed. An earlier `-x` run had stopped on the s2 anchor of the same kind. |
| Probes after repairs | `run_probes` (dev) | 22 PASS / 0 FAIL |
| XXIV test files | CI-equivalent venv | 74 passed, 1 skipped (live PHREEQC cell: no phreeqpython) |
| Full sandbox on the committed tree | CI-equivalent venv | posted as a PR comment (it was still running when this file was committed) |
| Production suite | `smartchem/` and `tests/` unchanged vs `main` | evidence = hosted `test (3.10)` / `test (3.12)` on the PR head. `scripts/run_suite.sh` was **not** re-run locally in XXIV (the production tree is byte-identical to the 1.6.0 tag apart from the #160 test record already on main) |

Two harness or test errors of mine were caught and fixed, not hidden:
- **P4 control:** the child crashed on the (correct) strict refusal before reporting. Disclosed in the preregistration.
- **Spatial-grid claim:** I first claimed "1ᵀL = 0 bit-exactly". In floating point a multi-face column sums to about 1e-17; only the per-face pair cancels exactly. The claim and the test were corrected.

## 4. Source, temperature and standard state (`OPERATION_XXIV_SOURCE_GROUNDING.md`)

**Temperature.** Off-domain is refused (above). A validated temperature law is OPEN.

**Standard state.** log K^(c) = log K^(m) + Σ_aq ν · log10(ρ_w* m°/c°).
- The whole activity product is transported; tested against an independent dimensional / ideal-dilute check.
- The calcite world vs PHREEQC Ca goes from **+0.298% → −0.0071%** once constants are transported.
- **CORROBORATED:** the XXIII 0.30% was the basis mismatch.
- Both sides use the same database, so this is verification only.

**Domain.** `ionic_strength_max` is an executability limit, not accuracy. Every API result carries a four-rung `validation_ladder`. The empirical rung is False everywhere.

## 5. Pitzer and phosphate

**Pitzer (EXPLAINED).**
- C2 = −0.07406745913108281 is reproduced bit-for-bit from vendored, pinned `pitzer.dat` bytes.
- Zeroing the single 2015 β2(Na⁺,HCO₃⁻) = 8.22 line gives C2 = +0.0051 (attribution +0.0792).
- The MacInnes toggle shifts C2 by 6e-12, confirming the acidity function is convention-free.
- It is a reference-database artifact, not a model-class limit. +0.0051 is still above U_R 0.0029.

**Phosphate (NOT RUN).**
- The sourced Pitzer binary fits disagree by up to 0.0055 in log γ± at I = 0.1, comparable to the 0.0078 effect.
- Key mixing terms were not found.
- So no fail-capable preregistration (with a sign) was possible. OPEN.

## 6. Empirical holdout

- **NIST provenance corrected** (appended, dated):
  - SRM 186g **expired 2023-04-30**;
  - 191d Table A1 is the same measurement (U_R printed 0.0029);
  - the 2025 date is an editorial reissue;
  - lot variation is unbudgeted.
- **Best independent calcite candidate:** Kline / Frear & Johnston 1929 (via Linke 1958). Its analytical method is unread and **no uncertainty is stated**, and a delegated exploratory comparison preceded registration. **Not qualified.**
- **2.0-alpha independent-measurement gate: NOT MET.**

## 7. General simulation API: acceptance matrix (`test_xxiv_sim_api_general.py`)

| requirement | how it is met |
|---|---|
| Typed species and phases | phase mismatch refused |
| Exact stoichiometry | `structural_conservation.holds` |
| Explicit inventories | `SpeciesInventory` only |
| Bound sources | tiered provenance; `Ksp_calcite` SOURCED, rate scales ASSUMED |
| Boundary schedules | multi-phase |
| Solver settings | bound in the run identity |
| Source-domain refusals | vented/open phase, 320 K, I > I_max |
| Per-component receipts | `VERIFIED_WITHIN_RESOLUTION` for Ca, C, charge, … |
| Identities | model / run / evidence / observation separation; distinct across worlds |
| Determinism | frames bit-identical across runs |
| Composition laws | continuation is **exact** at equal macro-step (two phases = one = `continue_from`). A **different macro-step does not compose exactly**: it differs at solver-tolerance level (non-zero, < 1e-6 relative). |
| No chemistry in the shared run path | asserted on `inspect.getsource(run)` |

Calcite equilibrium Ca = 1.23009e-4 mol, matching the XXIII harness. The vinegar world's XXIII identities are unchanged (XXIII API tests green).

## 8. Spatial prototype (3.0 research, `spatial_grid_xxiv.py`)

**Model.**
- A ≤9×9 grid of compartments.
- One `InterfaceTransfer` per open face per neutral species: F_{i→j} = k(c_i − c_j) = −F_{j→i}.
- Walls are absent faces; valves follow a segment schedule; one feed source and one first-order sink.
- **Conservation identity:** d(1ᵀn)/dt = 1ᵀq + 1ᵀb(n), proved per face and checked by the per-step coupled ledger.

**Verified:**
- an **independent `expm` reference discretization** on a 5×5 walled grid with a scheduled valve: relative error < 1e-6;
- zero-flux and uniform-state fixed points (exact);
- single interface vs the analytic relaxation (1e-8);
- exact flux antisymmetry and sign reversal;
- mirror symmetry (orientation-independence);
- source-only closure;
- sealed pocket constant while its valve is closed, draining after it opens;
- over-drain refused with the raw minimum reported;
- charged species refused.

**Projection.** Frames go through the existing typed `PhysicalWorldSnapshot`/`to_frame` contract, with deterministic digests. Writes to a frame cannot reach the run, which is itself read-only. `render_html` is a labelled self-contained view: "not a measurement".

## 9. Roadmap through 3.0

See the XXIV block in `ROADMAP.md`. The lanes:
- **Production 1.x** frozen.
- **Research 2.0:** P0 repairs done; source transport done (temperature refusal, standard-state); a second consumer done; independent measurement OPEN.
- **Research 3.0:** conservative spatial composition prototype done; renderer-neutral projection done; the LibGibson wire gap is filed (#290).

## 10. LibGibson

Wire v1 `FIELD` carries `{cols, rows, origin, cell_w, cell_h, model_tick, data, mask}` only. It has no quantity identity, unit or kind, no trust label or digests, and no face-centred data. The reproducer is in the issue. SmartChem renders through its own typed contract meanwhile, and LibGibson was not changed to paper over anything.

## 11. Strongest verified result

The trust boundary now has one shape for both operator kinds:
- a closed, closure-pinned audit table;
- labelled attestation;
- everything else unverifiable.

Five predeclared attacks that each produced a false admission on `7314e2a` are refused with typed reasons on both execution paths. **(Certification, not validation.)**

Strongest *scientific* result: two "unexplained" residuals were attributed by single-factor ablation on pinned sources:
- the calcite 0.30% is the molal/molar basis;
- the pitzer.dat −0.074 is one β2 parameter.

## 12. Strongest surviving conjecture

With a source-faithful specific-interaction model (pre-2015 Na–HCO₃ parameters, or a primary-read phosphate set), the Harned-lineage buffers sit within U_R. That would make the Davies refutations an activity-model limit, not a constant error. It is UNTESTED as a preregistered claim, and common-mode with Harned metrology anyway.

## 13. Most important refuted hypothesis

"pitzer.dat's carbonate miss is a Pitzer-model-class limit": refuted. One 2015 parameter accounts for +0.079 of the −0.074. Also refuted: "XXIII's calcite 0.30% gap is chemistry". It is the standard-state basis.

## 14. Next three verdict-changing experiments

1. **Read Frear & Johnston 1929** (or IUPAC-NIST SDS 95 Part 2, JPCRD 41:023105) for Kline's analytical method and uncertainty. Then preregister a calcite–CO₂ holdout with a sourced Henry boundary, before running. This is the only path to the 2.0-alpha gate in view.
2. **Phosphate:** fix one primary-read Pitzer parameter set and a predicted sign and magnitude, and preregister. It passes only if it explains **both** 186g formulations.
3. **Re-run the 191d C2 comparison with the pre-2015 Pitzer Na–HCO₃ set as a preregistered prediction**, and decide whether it is independent of the constants' Harned fits. If the parameters were fitted to Harned EMFs, it is common-mode and cannot count.

## 15. Status

- **Production 1.6.0:** RELEASED, unchanged, tag immutable; nothing in `smartchem/` changed.
- **Research 2.0-alpha:** **NOT MET.** P0 acceptance matrix PASS; independent-measurement gate OPEN.
- **2.0 stable:** not started; gated on 2.0-alpha.
- **Spatial 3.0:** research prototype only; no release.
