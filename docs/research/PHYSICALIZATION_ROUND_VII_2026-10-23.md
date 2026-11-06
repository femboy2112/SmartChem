# Physicalization Round VII — "The First Living Chamber" (2026-10-23)

*Branch `feat/chemical-graph-projections`, atop Round VI `3ffc2fd`. Production `smartchem/` is UNTOUCHED this round
(`git diff HEAD -- smartchem/` empty); all work is in `experiments/sandbox_foundation/` + `docs/research/`. `main`
(`99fce34`) and `v1.0.0` are untouched. No merge / tag / release / push is authorized by this record.*

Core objective met: **a conserved material inventory crosses a physical boundary, local chemistry re-equilibrates, a
real chemical observable (pH) changes, and the whole transition stays conservative, dimensionally valid, numerically
checked, and epistemically honest.** Failure to admit a model is recorded as a result; nothing is fabricated.

Full sandbox suite after the round: **525 passed** (Round VI left it at 469). ruff clean on every changed/added
source and test file (`compare.py` excepted — a terse, pre-existing-dirty benchmark reproduction script, and ruff is
not a CI gate here: there is no `[tool.ruff]` config and no lint step in `.github/workflows`).

---

## Wave A — soundness (P0), each red-first

### A1 — an admitted rate law cannot be integrated through its validity cap (`twocell.py::reaction_cell`)
**Red (reproduced on the real module):** with an admitted A→B law capped at 0.75 mol/m³ and a start `[A,B]=[0.6,0.4]`
(both ≤ cap), the ODE integrated to `[≈0, 0.99997]` and `reaction_cell` returned that endpoint — max conc 0.99997 >
cap, handed back as an admitted prediction. Admission had been checked only at `n0`; the solver ran
`_rate_vector_unchecked` and the endpoint was never re-checked.
**Fix:** within a single closed-cell step T is fixed, so the one trajectory-varying admitted condition is the
concentration cap. A **terminal `solve_ivp` event** on the most restrictive cap stops and refuses the moment the max
concentration rises through it (catching interior excursions, even ones that would relax back under by `dt`), and the
accepted endpoint is re-checked by the mechanism's own `require_admitted`. Crossing the cap fails CLOSED
(`AdmissionDomainError`). Boundary equality is admitted (the cap is inclusive; the solver's `assert_applicable` uses
strict `>`). A plain (unadmitted) mechanism keeps the old path. A limited-horizon *stop-and-return* was deferred (it
would break operator-splitting's fixed-`dt` advance). Tests: `test_mechanism_types.py::TestWaveA1_*` (growth→refuse,
in-domain→admit, boundary→admit, tight-cap→refuse, plain→unaffected). No regression (interface+mesh 53 passed).

### A2 — a simulated prediction is not a measurement (`snapshot.py`, `libgibson_frame_example.py`)
The receipt flag `scientific_measurement = admitted ∧ numerics_verified` named a *supported prediction* a
"measurement", inventing a physical observer. Renamed → **`supported_prediction`**; added
**`observed_measurement`** (always `False` for a model-run receipt — a simulation carries no external observation
source and can never mint one) and **`numerics_disclosure()`** (exactly which residuals were checked against a
tolerance, and which errors remain UNBOUNDED — the truncation error vs the exact solution is always disclosed as
unbounded, so a trivial caller-supplied residual dict cannot masquerade as an accuracy certificate). The frame
`measurements()` → `model_values()`; `MEASUREMENT_KINDS` → `MODEL_VALUE_KINDS`; the presenter banner can no longer
say "measurement" for a prediction. Falsifier test: a real-species, trusted-law, numerically-converged state is
classified `supported_prediction=True` **and** `observed_measurement=False`, and a converged state cannot be forged
into an observation (`validate_frame` flags it). 90 tests pass across the two files.

### A3 — strict, portable scientific JSON (`benchmarks/acetate_phreeqc/comparison_table.json`, `compare.py`)
Four bare unquoted `NaN` in the two pure-water (`CT=0`) rows (`dAc`/`dHAc`, undefined relative errors) → `null` + a
typed `"rel_err_undefined_reason": "REFERENCE_SPECIES_ABSENT"`; the committed PHREEQC reference is otherwise
byte-identical (no PHREEQC re-run). Exporter future-proofed: `compare.py` emits `None` + the reason for `CT==0` and
dumps with `allow_nan=False` (a future nonfinite value is rejected loudly). New cross-language contract test
`test_benchmark_json_strict.py`: no `NaN`/`Infinity` token, strict parse with `parse_constant=raise`, round-trip
under `allow_nan=False`. (Done via a bounded surgical hand-off; verified on the filesystem — grep NaN = 0.)

---

## Wave B — audit of the Round VI ion-pair science (without overfitting it)

### B2 — honest uncertainty semantics (`aqueous_equilibrium.py`, `K_NAAC_ION_PAIR_25C`)
The ±0.17 on the NaAc association constant is relabelled as a **between-database / model-variation spread**
(minteq logK −0.18 vs llnl ≈ −0.079), **not** a statistical 1-σ measurement uncertainty; the two source values +
provenance are retained in the record rather than collapsed into an unearned confidence interval. Propagate it as
model-form variation, not a Gaussian σ.

### B4 — model identifiability (`identifiability.py`, new) — NUMERICALLY_VERIFIED, local
Local sensitivity Jacobian of observables `{pH, free-acetate fraction, ion-pair fraction, ionic strength}` to
`θ = (logK_NaAc, Davies A)` by central differences on `solve`, at the C5 point (C_T=Na=0.45 M):
- full 4×2 Jacobian: singular values `[0.380, 0.230]`, **rank 2**, condition **1.65** → the two parameters are
  locally identifiable TOGETHER from that observable set;
- **pH alone (1×2): rank 1** → a single scalar pH cannot separate logK_NaAc from the activity parameter (its local
  sensitivity matrix is at most rank one — as expected for one scalar and two parameters);
- free-acetate and ion-pair fractions carry opposite-sign sensitivities (near-complementary at fixed C_T), so the
  identifying move is **pH + a speciation observable**, not more pH points.
HONEST SCOPE: a LOCAL Jacobian at one operating point, NOT a global-identifiability proof, and a finite-difference
Jacobian inherits the solver's numerical noise. Tests in `test_identifiability_b4.py`.

### B5 — numeric hardening of `_ion_pair_acetate_root` — NUMERICALLY_VERIFIED, fixed red-first
The shipped positive root `(-b1+√disc)/(2 a2)` subtracts near-equal large numbers when `b1>0` (dilute acetate,
`4 a2 C_T ≪ b1²`): measured relative error climbs from 9.5e-14 (C_T=1e-2) to **3.0e-8 (C_T=1e-7)**, within ~30× of
the `AGREEMENT_RTOL=1e-7` route-agreement gate and growing as C_T→0. It does not break an admitted solve *today*
(routes still agree ~1e-17 at C_T≥1e-5) but is a latent fragility. Pinned to the algebraically identical
cancellation-free conjugate form `2 C_T/(b1+√disc)` for `b1>0` (the `b1≤0` branch already adds like-signed terms).
This is a DIFFERENT cancellation from the Round VI `h_of_a` fix (that was route 2's charge quadratic; this is route
1's inner acetate elimination). Red-first regression (`test_ion_pair_numerics.py`): the root must satisfy its own
quadratic to machine level across C_T ∈ [1e-2, 1e-8] — the naive subtraction fails this at small C_T.

### B1 / B3 — deferred to a recorded obligation (PHREEQC absent)
`phreeqpython` + the thermodynamic databases are not installable in this environment, so the ABLATIONS (B1:
MINTEQ-vs-LLNL activity model / Ka / Kw / extra-complex isolation) and the PHREEQC columns of the held-out set (B3)
are preserved as an explicit UNKNOWN obligation (alongside the existing `reaktoro_benchmark_obligation`), never
faked. **B3 pre-registration (declared BEFORE any run, separate from the A7 post-hoc set):**
- held-out conditions (new, not in C1–C5): C_T ∈ {0.03, 0.07, 0.2, 0.3} M at Na/C_T ∈ {0.25, 0.5, 0.9, 1.0},
  emphasizing intermediate sodium fractions and the upper admitted ionic-strength range (I up to ≈0.45 M);
- predeclared metric: |ΔpH| vs each reference, plus free-acetate fraction, ion-pair fraction, ionic strength, and
  charge + analytical-component residuals; thresholds AGREE ≤0.02, MARGINAL ≤0.05, DIVERGE >0.05;
- compared predictions: no-pair Davies, pair Davies (both our own solver — computable now and to be frozen as the
  pre-registered code-side predictions), PHREEQC minteq.v4, PHREEQC llnl (deferred to the obligation);
- cross-database disagreement is classified as model-form variation (B2), not statistical uncertainty;
- **no retuning** of K_assoc or thresholds on the held-out set; exact DB sha256 + reference inputs preserved.

---

## Wave C — the first living chamber (`living_chamber.py`, new) — the centerpiece

State is the **conserved component inventory** per cell — `(n_acetate, n_sodium, volume, T)` — never six free
species. The concentrations are a pure function `E(b)` of the totals via `AcetateWaterSystem.solve`. The membrane
passes **only neutral acetic acid**: `J_HAc = g_HAc·(c_HAc[tail] − c_HAc[head])` (mol/s), `g = D·A/dist·valve`
(m³/s), with the mol/L↔mol/m³ hinge explicit (`LITRES_PER_M3 = 1000`). A face moves TOTAL ACETATE by ±(J·dt) on its
two incident cells and moves nothing else — no sodium, no ion, no charge, no energy, no hydrogen-ion transport law.

**Proved / verified (checkable residuals, `test_living_chamber.py` — 21 tests):**
- `A·E(b) = b` (the component inventory survives the local speciation): residual **0.0** (#8);
- global total acetate invariant under internal transport, global/per-cell sodium invariant (sodium immobile),
  per-face transfer exactly equal-and-opposite (#9, #10); `conservation_report` drift 0.0 over long runs;
- local charge balance closes after every accepted step (per-cell residual ~1e-18, #11);
- zero permeability (shut valve or g=0) ⇒ no transport, even at huge dt (#12);
- the mol/L↔mol/m³ conversion is exact and 1000× (#13);
- a step exporting more neutral acid than the donor holds is REFUSED (`policy='raise'`) or SUBSTEPPED
  (`policy='substep'`, conservative, re-equilibrated between) — never silently truncated (#14);
- the pH trajectory is byte-identical for 0, 1, or many presenter calls (rendering is a pure read, #15).

**The algebra (C3), stated honestly, not over-claimed.** With `A` the component map (acetate = HAc+Ac⁻+NaAc,
sodium = Na⁺+NaAc) and `E` the equilibrium speciation, `A∘E = id` on the totals space (within the solver's own mass
tolerance), hence the projection identity `E∘A∘E = E` holds by construction — a verified numerical identity, **not**
claimed as an exact categorical functor (its object/morphism laws were not established). Global conservation is the
statement that the internal-face incidence `B_space` has columns summing to zero, so `Σ_cells b` is invariant under
`db/dt = (B_space ⊗ a_HAc) J_HAc` with the neutral-HAc transfer vector `a_HAc = (1, 0)`.

**Free energy — a weaker true theorem over a stronger false one (C3).** PROVED: the neutral-HAc transport step alone
is down the HAc chemical-potential gradient — under the model's own ideal-dilute neutral-solute assumption
`a_HAc ≈ c_HAc`, `sign(J_HAc) = sign(μ_HAc[tail]−μ_HAc[head])` with `μ_HAc = μ0 + RT ln(c_HAc/c_ref)`, so
`transport_dissipation_margin ≥ 0` for every face (#16). NOT claimed: a global Lyapunov / free-energy certificate for
the FULL coupled system (transport + re-speciation + the nonideal Davies activity model + the optional ion pair) —
the equilibrium projection redistributes acetate across HAc/Ac⁻/NaAc and the activity coefficients couple the charged
species, and no single global functional with a proven monotone discrete decrease was established. That obstruction
is named in code (`FREE_ENERGY_OBSTRUCTION`), not papered over.

**Flagship scenarios (C4), each with positive + negative + mutation tests:** (1) impermeable membrane — every pH and
inventory frozen; opening it DOES move pH (negative control). (2) pure acid vs water — HAc redistributes acid→water,
water drops 7.0→~3.8 over 20 steps, conservative. (3) acid vs sodium-acetate buffer — neutral HAc moves, the buffer
acidifies LESS than plain water would (buffer capacity), and every sodium ion stays home. (4) ion-pair on/off —
both admitted + conservative; the pair's influence on this membrane scenario is small (|ΔpH| < 0.1, weak pair) and
disclosed; it is active (NaAc > 0) only where sodium is present. (5) renderer disabled — trajectory bit-identical
for 0/1/5 renders while the presenter demonstrably ran.

**Numerical references (C5):** two independent equilibrium root solvers PER compartment (the solver's own route
agreement, gated at `AGREEMENT_RTOL`); a dt-halving self-consistency check (labelled numerical, explicitly NOT
validation and NOT a convergence-order claim); frozen conservation + per-step charge controls. The time-dependent
permeability/diffusivity are NOT physically calibrated — the equations are implemented, not validated.

---

## Wave D — the observation boundary (`chamber_frame.py`, new) — 8 tests

A strict-JSON, renderer-neutral frame + a tiny headless `ChamberPresenter`, reusing the Wave A2 honesty contract.
The composed model's admission is **SYNTHETIC** (transport conductances are CALLER-DECLARED, even though the per-cell
equilibrium is source-backed), so `supported_prediction=False` and `observed_measurement=False`; each cell still
carries its own aqueous verdict + caveats as evidence. The frame carries: conserved totals (CANONICAL), derived
species concentrations + activity pH (MODEL_DERIVED), per-cell charge residual + verdict/caveats, membrane state +
transfer ledger, the receipt + `numerics_disclosure`, and unsupported quantities (temperature field, electric
potential) as explicit `null` (never 0). `validate_chamber_frame` enforces strict JSON (no NaN/Infinity), the
field set, and the A2 non-negotiable (`observed_measurement` must be False). The presenter shows two chambers, their
pH, and the transfer ledger, and NEVER presents a prediction as a physical measurement. Field set documented for the
LibGibson interactive-instrument epic **#125** (`LIBGIBSON_FRAME_FIELDS`). No LibGibson source change required.

---

## Wave E — the 1.1 production candidate / post-1.1

- **E1:** exact-SHA review dossier for `pr101/production-1-1-rc @ 0dde33a` → `V1_1_PRODUCTION_CANDIDATE_REVIEW_0dde33a.md`.
  Verified: 20 recognizers (vs main's 1.0 oracle), `1.1.0a1`, sandbox absent, CI run `39897599474` green (7 jobs).
  Stale PR #101 body claims ("78 tests", "numpy/scipy only", `34e1891`/7655) confirmed stale on the live body; a
  corrected body is DRAFTED in that dossier for the owner to approve posting (not posted here). The candidate is not
  merged/tagged/released.
- **E2 (#107 catalyst/activator ledger):** explicitly a SEPARATE post-1.1 branch; deliberately NOT started this
  round so as not to disturb the prepared release candidate, and never to add an unsound 21st recognizer for a
  milestone. Deferred with that constraint recorded.

---

## Wave F — adversarial review (evil-morty, read-only; every finding re-verified on the filesystem)

A targeted adversarial pass found ONE real defect, failing CLOSED, in a module whose load-bearing claims otherwise
held under genuine assault. Falsifier #18 (a red-team gate shown to catch a real error) is discharged: the pass
caught Finding 1, reproduced here, then fixed red-first.

**Finding 1 (LOW, fails closed) — substep's contract gap, FIXED.** `policy='substep'` sized its chunk count ONCE from
`transport_dt_max()` on the INITIAL speciation. On a heterogeneous multi-cell world a cell that starts empty of HAc
does not enter that bound, then fills and over-exports in a later substep → `_one_substep` raised `ChamberError`,
defeating substep's "completes" promise. Reproduced on the filesystem — and not only for the extreme-conductance
case: a MODERATE g-ratio (g_BC = 2e-9 vs g_AB = 1e-9) also wrongly raised. No soundness impact (the per-substep guard
re-checks current HAc, so the failure is a raise, never a leak or over-advance). **Fixed** by making substep ADAPTIVE:
it consumes dt in chunks, re-evaluating `transport_dt_max` on the current re-equilibrated world each chunk
(h = min(remaining, dt_max)), completing for any non-stiff world and failing CLOSED (early budget check,
`MAX_SUBSTEPS = 10000`) for a genuinely stiff one. Red-first regression: `TestWaveF_AdaptiveSubstep` (moderate world
now completes + conserves; stiff world fails closed).

**Held under attack (the earned boundary — each genuinely exercised):** conservation (3-cell cycle, asymmetric
volumes/sodium, ion pair on, 20 steps: global acetate drift ~1.1e-19, sodium exactly 0, faces equal/opposite); the
A1 cap guard against a REAL non-monotone interior excursion (an amplifying A→2B→C chain whose intermediate overshoots
then relaxes below the cap by dt — every genuine crossing refused by the terminal event, backed by the endpoint
re-check); the A2 contract (`observed_measurement` a hardcoded False with no path to flip it; forged trust/receipt and
NaN pH all rejected); the dissipation margin (≥ 0 over 4506 randomized configs, worst 4.3e-22; not vacuous — a real
finite 4.15e-7; the ln(0) corner returns +inf or 0, never negative); the units hinge (no factor-1000 error); the B5
fix (conjugate strictly better than the naive form vs a 60-digit Decimal reference, continuous at b1=0); the
fail-closed gates (off-temperature, out-of-Davies-domain all refuse).

**Residual unease, disposed:** (A) the substep bound was the weakest spot — the adaptive fix removes the single-state
sizing; the only fail-OPEN path (an over-export within `AVAILABILITY_RTOL` clipping ≤1e-15 mol) stays bounded to
irrelevance. (B) `validate_chamber_frame` was asymmetrically weaker than `libgibson_frame_example.validate_frame`
(checked only the two trust booleans) — **hardened** to recompute the trust verdict from the receipt's numerics +
admission, catching an edited-receipt forgery (`test_chamber_frame` still green). (C) a strong-base near-zero-HAc
chamber (C_T=0, Na=0.1 M) is REFUSED on the base aqueous solver's charge-balance tolerance at the high-pH limit —
fail-closed and safe, a usability cliff of the aqueous gate (not this round's chamber), recorded, not fixed.
(D) PHREEQC not exercised — the recorded obligation (B1/B3).

---

## Claim ledger (round vocabulary)

| claim | status |
|---|---|
| A1 cap-crossing fails closed over the trajectory | **IMPLEMENTATION_CROSS_CHECKED** (red-first + 5 tests) |
| A2 prediction ≠ measurement; a sim invents no observer | **IMPLEMENTATION_CROSS_CHECKED** (falsifier test) |
| A3 benchmark JSON is strict / portable | **IMPLEMENTATION_CROSS_CHECKED** (cross-language parse test) |
| B2 K_NaAc ±0.17 is model-form spread, not 1-σ | **SOURCE_INSPECTED** |
| B4 pH alone is rank-1; full set rank-2 (local) | **NUMERICALLY_VERIFIED** (local Jacobian only) |
| B5 ion-pair acetate root is cancellation-free | **NUMERICALLY_VERIFIED** (quadratic residual at machine level) |
| C conservation: acetate/sodium invariant, faces equal/opposite | **PROVED** (algebra) + **NUMERICALLY_VERIFIED** (residual 0) |
| C local electroneutrality re-established each step | **NUMERICALLY_VERIFIED** (~1e-18) |
| C neutral transport is down-gradient (dissipative) | **PROVED** (ideal-dilute neutral solute) |
| C global free-energy Lyapunov for the coupled system | **REFUSED** (obstruction named, not claimed) |
| C `E∘A∘E = E` projection identity | **NUMERICALLY_VERIFIED** (not an asserted functor) |
| D frame is strict JSON; never an observed measurement | **IMPLEMENTATION_CROSS_CHECKED** |
| aqueous model vs a MEASURED acetate-buffer pH | **UNKNOWN** / **EXTERNAL_VALIDATION_UNAVAILABLE** (unchanged) |
| PHREEQC ablations (B1) + held-out columns (B3) | **UNKNOWN** (engine absent; obligation + pre-registration recorded) |
| the whole living chamber as a physically CALIBRATED model | **SYNTHETIC** (conductances caller-declared) |
| F adversarial pass: 1 LOW defect (substep contract) found + FIXED red-first; soundness held | **IMPLEMENTATION_CROSS_CHECKED** (falsifier #18 discharged) |

No claim is labelled EMPIRICALLY_VALIDATED: nothing here was checked against an independent MEASURED datum.

---

## Roadmap (branch-only / verified / released / unverified distinguished)

- **1.0** — RELEASED (`main` `99fce34`, tag `v1.0.0`). Untouched.
- **1.1 (production)** — branch-only candidate `pr101/production-1-1-rc @ 0dde33a`, CI-green, 20 classes. NOT merged
  / tagged / released. Review dossier ready.
- **1.5 program** — on `feat/chemical-graph-projections` (head now this round's tip); #107 is the next post-1.1
  chemistry slice (separate branch, unstarted).
- **2.0 physical-mechanism engine** — the sandbox foundation: this round adds the FIRST living chamber (verified
  conservative reactive transport) on top of the verified pieces (aqueous equilibrium, interface discipline,
  admission model). All sandbox, all SYNTHETIC/experimental, none validated against measured data.
- **3.0 LibGibson falling-sand lab** — unbuilt; the renderer is explicitly NOT built this round. The observation
  boundary (#125 fields) is specified.

## One next best falsifying physical experiment

Measure, for a real acetate solution at the **upper ionic-strength range (I ≈ 0.4 M, C_T ≈ Na ≈ 0.45 M)**, BOTH the
pH (calibrated electrode) AND a **speciation observable that resolves free vs ion-paired acetate** (e.g. a
Na⁺-ion-selective electrode for free [Na⁺], or conductometric/potentiometric determination of the NaAc association).
Per Wave B4, pH alone is rank-1 and cannot separate the ion-pair constant from the activity model, so the Round VI
attribution of the residual ~0.023 pH at C5 to "activity model, not the pair" is currently UN-falsified rather than
confirmed. pH + the speciation observable lifts the Jacobian to rank 2 and would, for the first time, (a) provide the
independent MEASURED datum this program has only ever recorded as UNKNOWN, and (b) decide whether the C5 residual is
the activity model or the pair — a genuine falsification test of the model, not another same-database cross-check.
