# OPERATION XXI — scientific & engineering handoff

*The chemical universe must commute.* Built on released **v1.5.0** and the consolidated 2.0 research stack. This
dossier records the merged code and the current scientific evidence — not PR descriptions. Every "MEASURED"/"suite"
figure below is from an OOM-safe `scripts/run_suite.sh` run the author executed, not a trusted report.

## A. Exact git coordinates

| ref | SHA | note |
|---|---|---|
| Production release | tag `v1.5.0` (annotated `68f9a19`) → commit **`c3d0d01`** | 24-class oracle; `main` now `99fce34` (docs commit on top) |
| 2.0 research integration | `integration/2.0-alpha` = **`774429e`** (PR #156) | the v1.5.0 forward-merge (`476bf8a`) + Operation XX consolidated in (§1) |
| Operation XX | `research/operation-xx` = `4aef07c` | P0 trio + NIST §5 (prior round) |
| **Operation XXI work** | `research/operation-xxi` = **`e18e134`** (pushed) | §2–§5, §7, §11 (this dossier adds §14; §6 folds in on completion) |
| §7 subbranch | `research/operation-xxi-s7` = `44b25bc` | merged at `76a5fa8` |
| 1.6 lactonization witness | `candidate/1.6-lactonization-witness` = `1e5bf0f` | independent recognizer (prior round, §9) |
| Review-only 25th class | `feat/lactonization-exhaustiveness` = `38e9186` (PR #151) | held for 1.6 |

**Merge ancestry (XXI):** `476bf8a` →(§1 no-ff)→ `774429e` →(§2/§3)→ `e3f0b6d` →(§4)→ `56f6007` →(§5)→ `8c126d6`
→(§7 no-ff merge of `44b25bc`)→ `76a5fa8` →(§11)→ `e18e134`. Linear, non-destructive, no cherry-picks, no force-push.

**Outstanding permissions (NOT taken):** protected-`main` merge, release tag, package publication, force-push, and any
LibGibson change all still require separate authorization. Everything here is dev-branch integration + research under
`experiments/`. `smartchem/` is byte-identical to v1.5.0 throughout (`git diff c3d0d01 e18e134 -- smartchem/` is EMPTY);
`__version__` stays `1.5.0`.

**Suite progression (author-run, OOM-safe, junit tally):** 959 (P0 base `774429e`) → 952→959 (§2/§3+§4) → 969 (§5) →
1009 (§5+§7) → 1018 (§6). All green (0 failed / 0 errors / 0 skipped).

## B. Claim ledger

Labels: CORROBORATED (survives a real test, scope stated) · OBSERVED (measured, not yet a general claim) ·
REFUTED (a prior claim fails under a corrected comparison) · DISCLOSED (a limitation made explicit) ·
CONJECTURED · UNVERIFIED · DARK (unexamined).

- **§1 consolidation — CORROBORATED.** Operation XX is integrated into `integration/2.0-alpha` with full ancestry and
  a merged tree byte-identical to `4aef07c`; compatibility gate (smartchem byte-identical, version 1.5.0, 24-class
  oracle) holds. Scope: dev-branch integration only.
- **§2 execution identity — CORROBORATED (bug fixed).** An opaque rate law (no bindable descriptor) can no longer
  obtain false execution certification: it runs only as EXECUTABLE-UNVERIFIED (flag `execution_identity_certified=False`,
  named `uncertified_rate_laws`, kinetic tier floored to UNVERIFIED **from the descriptor, not the self-declared
  label**) or is REFUSED under `require_certified_execution=True`. DISCLOSED: a mutation of an unbindable law's hidden
  parameter remains invisible to the certificate *by construction* — the certificate cannot witness what it cannot
  bind; the honest contract is that it never *claims* to.
- **§3 component-wise conservation — CORROBORATED (bug fixed).** Each conserved component is judged against its own
  scale (`tol_i = atol + rtol·scale_i`); a physically significant trace-component defect can no longer hide under an
  unrelated bulk component's inventory. The bulk component's tolerance is unchanged, so legitimate runs are not
  refused (the full suite confirms no false positives). No numerical-adjustment term in the coupled integrator (it
  applies no phase-stitch clamp); the unified world carries that term (XX-4).
- **§4 NIST SRM 191d — REFUTED (measurement-level) + DISCLOSED (scale-contingency).** The corroboration is NOT a robust
  physical prediction: within the convention-INCLUSIVE Table 1 (U=0.010) only, thinly; REFUTED at the convention-matched
  Table A1 (U_R=0.0029, ~3× U_R); REFUTED against Table 1 itself once the molar-K scale is made self-consistent. The
  measurement-level verdict hinges on the unresolved standard-state SCALE (molar vs molal) of K1/K2. No constant tuned
  (git self-check). PARTIAL common-mode preserved (K1/K2 Harned-lineage; Davies shares the DH family with BG;
  single-ion a_H⁺ not independently derived).
- **§5 ElectroneutralBulkExchange — OBSERVED.** A bulk-liquid parcel swap produces a physically distinct trajectory
  from a selective membrane on the SAME integrator: measured, a selective HAc membrane leaves the Na⁺ gradient
  untouched (0.080/0.040 mol) while the bulk exchange relaxes it toward the well-mixed mean (0.062/0.058 → 0.06); both
  conserve C and Na globally and leave each compartment electroneutral; Q=0 recovers the closed case. Scope: a model
  demonstration on synthetic/assumed kinetics, not a calibrated mixing-rate predictor.
- **§6 Na-ion-pair ablation — CORROBORATED (model-vs-model) + REFUTED (measurement-level).** A controlled PHREEQC
  ablation (minteq.v4 with vs without the two DB-sourced Na-carbonate pairs — NaCO3- log_k 1.27, NaHCO3 log_k 10.079;
  no-pairs DB verified = exactly those 16 lines removed; no constant tuned) shows the pairs ARE the dominant cause of
  the high-Na SmartChem-vs-PHREEQC gap (SmartChem tracks PHREEQC-no-pairs to ≤0.017 pH; the SmartChem-vs-with-pairs gap
  is the pair term, up to +0.13 at C4; monotone in Na; exact null at Na=0). BUT the correction is REFUTED by the only
  measurement: adding the pairs moves PHREEQC ~0.14 pH AWAY from the NIST certified 10.014 (9.999→9.857). DISCLOSED: the
  ~0.0023 pH low-Na floor offset and the activity/molal/lineage differences are a separate, smaller, unresolved effect
  (DARK here). "Pairs explain the model-vs-model gap" CORROBORATED; "pairs improve the prediction" REFUTED.
- **§7 categorical bridge — CORROBORATED (hardened).** The structural conservation cross-checks now use exact
  unbounded-integer arithmetic (a balanced reaction with a 2⁶⁰-scale coefficient is verified exactly; the old
  float+rint path falsely reports a non-zero column — pinned), and `kernel_signature` keys species AND reaction
  participants by full identity, so two distinct same-named species cannot collapse. DISCLOSED: the bridge preserves
  STRUCTURAL (stoichiometric) composition only; NO numerical-dynamics functor is claimed. Honest scope note: different
  *mechanisms* legitimately have different signatures (intermediates are part of kernel identity).
- **§9 independent lactonization witness — CORROBORATED (prior round).** `candidate/1.6-lactonization-witness` is
  genuinely non-common-mode (it disagrees with the `38e9186` carbinol guard on a hemiacetal lactone). Not merged;
  `semantic_digest` unmoved.

## C. Reproduced bugs

**BUG-XXI-2 (opaque rate law forges execution certification).** Baseline: a custom first-order law `r = secret·c` with
no `descriptor()`. Counterexample (public `integrate` path): `secret` 0.5→5.0 changed final B 0.393469→0.993262 while
the world certificate stayed byte-identical (`f860993140097ed1`) and no `StaleCertificateError` was raised. Expected:
no false certification. Actual (pre-fix): clean receipt, no signal. Repair: §2 three-state contract. Mutation control:
the lying-tier test (an opaque law declaring BENCHMARKED is still floored to rank 1). Regression:
`test_xxi_s2_execution_identity.py` (6). Remaining risk: unbindable-law mutation is undetectable by design — mitigated
by the loud flag + strict-mode refusal, not by a (impossible) detection.

**BUG-XXI-3 (trace-component defect hidden under a bulk scale).** Baseline: components X (1 mol) and Y (1e-12 mol) under
one global tolerance. Counterexample: injecting +1e-8 mol of Y (10⁴× its pool) via the test-only observer hook left
`material_balance_closed=True` (global tol ~1e-6 from X swallowed it). Expected: caught. Actual (pre-fix): accepted.
Repair: §3 per-component tolerances. Mutation controls: trace fabrication, trace destruction, opposing errors that
cancel at the endpoint (still caught per-step), a legitimate trace component NOT falsely refused, a bulk defect still
caught. Regression: `test_xxi_s3_component_conservation.py` (6). Secondary defect found & fixed mid-work: a feed-ledger
`KeyError('O')` (fed implicit-reservoir components lacked a per-component tol key) — did not commit red.

## D. Mathematical specification (as implemented)

- **Exact stoichiometric conservation (bridge):** E·N column sums and N·1 net production computed in unbounded Python
  ints directly from integer stoich/composition — exact at any magnitude; two independent routes (component-first vs
  composition-first) cross-check.
- **Component-wise numerical residual (coupled integrator):** for each conserved component i, over EVERY accepted
  macro-step, R_i = C_i(t) − C_i(0) − Φ_i^ext(t); balance closes iff max_t|R_i| ≤ atol + rtol·max(|C_i(0)|,|Φ_i^ext|).
  (A_i^numerical = 0 here; the coupled integrator applies no phase-stitch clamp.)
- **Transport operators:** InterfaceTransfer J = k·(c_a − partition·c_b), one species (selective). ElectroneutralBulk
  Exchange J_s = Q·(c_A,s − c_B,s) for every co-advected species at shared Q (whole-solution), internal/conservative,
  charge flux Q·(ρ_q,A − ρ_q,B) = 0 for electroneutral bulk.
- **Numerical approximation:** operator-split (Lie/Strang) + SNIA fast-equilibrium projection with a fail-closed
  admission gate; the verification cadence is separated from the sampling cadence (observer-invariant, XX-3).

## E. Scientific research

- **NIST SRM 191d (§4):** three comparators + claim ledger; see §B and `benchmarks/measured_carbonate_srm191d/
  S4_THREE_COMPARATORS.md`. Key result: the measurement-level corroboration is convention-and-scale-contingent.
- **PHREEQC Na-ion-pair ablation (§6):** `benchmarks/carbonate_na_pair_s6/` — minteq.v4 with vs without the two
  Na-carbonate pairs. The pairs explain the high-Na model-vs-model gap but WORSEN the NIST measured comparison (9.999→
  9.857 vs certified 10.014). Full ledger in `S6_NA_PAIR_ABLATION_NOTES.md`. Notably SmartChem(no pairs, 10.005) is
  closer to the measured value than PHREEQC-minteq.v4 is either way — not a validation of omitting pairs, but a warning
  that pairs cannot be bolted on without re-calibrating the activity model against the measured anchor.
- **Source-family overlap:** acetate pKa and carbonate K1/K2 are Harned-lineage; agreement on K-driven quantities is
  equation/implementation verification + activity cross-check, NOT independent validation of the K's.

## F. New physics — bulk mixing vs selective membrane (§5)

| mode | pH_A | pH_B | Na⁺_A | Na⁺_B | reading |
|---|---|---|---|---|---|
| closed | 4.581 | 5.359 | 0.080 | 0.040 | nothing moves |
| selective membrane (HAc) | 4.815 | 4.581 | 0.080 | 0.040 | ions cannot cross — Na⁺ gradient PERSISTS |
| electroneutral bulk | 4.703 | 4.744 | 0.062 | 0.058 | whole solution mixes — Na⁺ gradient RELAXES to ~0.06 |

Matter and charge balance: both transport modes conserve C and Na globally (STRUCTURALLY_CONSERVING) and leave each
compartment electroneutral. Model applicability: constant-volume, well-mixed, assumed Q (not a calibrated rate).
Time-step / rendering-cadence invariance tested.

## G. Generality

One generic `CoupledWorld.integrate` runs, with no chemistry-specific branch in the engine: synthetic reaction-
diffusion, a pure-diffusion reference, the acetate buffer (fast-equilibrium projection), the selective-membrane
flagship, and the new electroneutral bulk mixer. The transport regime is a declared operator, not an engine mode.

## H. Roadmap status & the next three verdict-changing probes

DONE—RELEASED: 1.0.0, 1.1.0, 1.5.0 (24 classes). BRANCH-COMPLETE: §1–§7 (incl. §6 ablation) and §11 on
`research/operation-xxi`; the 2.0 stack on `integration/2.0-alpha`; the 1.6 independent witness on its candidate
branch. NOT STARTED: §8 (one additional bounded physical capability — precipitation/redox/non-isothermal/multi-gas),
§10 (2.0 simulation-API candidate). BLOCKED-on-authorization: any `main` merge / tag / publication.

**Next three probes (verdict-changing, not a wishlist):**
1. **Resolve the K1/K2 standard-state SCALE** (molar vs molal) from the primary Harned-cell source. This single fact
   flips the NIST measurement-level verdict (molal → survives Table 1; molar → refuted). It is the highest-leverage
   open question in the whole scientific layer.
2. **Does released v1.5.0 carry the `38e9186` hemiacetal carbinol guard?** The independent §9 witness disagrees with
   that guard on `O=C1CCC(O)O1`; whether the shipped 1.5.0 accepts or rejects that case decides the 1.6 scope.
3. **Acquire a second, chemically different MEASURED buffer** (e.g. a certified acetate standard) on a convention the
   model does not also assume — the only way to turn the carbonate agreement from implementation-verification into an
   independent predictive claim.
