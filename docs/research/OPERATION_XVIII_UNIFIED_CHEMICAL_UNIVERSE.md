# OPERATION SMARTCHEM XVIII — The Unified Chemical Universe (research 2.0)

Research-track engineering dossier. **Nothing here is merged, tagged, or published.** All work lands on the
research branch `research/unified-world-xviii`, stacked on the Operation XVII head `59c3143`. Every claim
carries its weakest supporting premise.

> **Scope honesty, up front.** This round closed the P0 correctness and identity obligations of the general
> kernel, built the headline unified physical simulator, executed the mixed PHREEQC benchmark, and audited the
> production compiler's 25th class. It did **not** reach a defensible 2.0 release candidate — see §J. A
> successful numerical run here is **not** an experimentally-verified prediction; a reference-solver comparison
> is **not** measured validation.

---

## A. Repository coordinates

| Reference | SHA | Meaning |
|---|---|---|
| `main` | `9e8fa5f` | published v1.1.0 (untouched) |
| XVII head (branch base) | `59c3143` | PR #153 tip; last completed CI on it was `success` (run 41355012439), with newer runs still in-progress at inspection — **not** declared green on the stale run |
| **XVIII branch** | **`research/unified-world-xviii`** | this round, 6 commits off `59c3143` |

**Commits on the branch (dependency order):**

1. `a35d3b8` — Track A P0: injective model identity (§1A/1B/1C/1D) + deep-immutable kernel execution basis (§2)
2. `d42bb0f` — Track B P0: signed external-flux ledger (§3) + scale-aware tolerances (§4A)
3. `93db9cb` — mixed acetate+carbonate equilibrium operator (§5 prerequisite)
4. `c5a889b` — **the unified vinegar/bicarbonate world** (§5, the headline)
5. `5672013` — the mixed acetate/carbonate PHREEQC benchmark executed (§6)
6. `dfc541a` — unified-world timestep/splitting characterization (§5)
7. `f557446` — ammonia equilibrium solver hardening (§8: temperature guard, circular cross-check, scale-floor tol)
8. _(this dossier)_

**Merge state:** none. Branches `integration/v1.5-candidate` (#149), `feat/lactonization-exhaustiveness` (#151)
and the XV→XVII research stack remain distinct and untouched. No push performed (awaits authorization).

---

## B. Bug ledger

| # | Defect (reproduced through the real API) | Status | Evidence |
|---|---|---|---|
| §1A | `model_identity` serialized a reaction's stoichiometry by species **name** only, so a shared registry with `X(aq)`+`X(g)` (both "X") gave two different executable `N` the SAME model digest | **REPAIRED** | probe RED→GREEN; reaction stoich now keyed by the full species identity (name/composition/charge/phase/substance) |
| §1B | `run_identity` rounded inputs to 12 decimals → `1e-13` and `2e-13` mol both serialized `0.0` | **REPAIRED** | probe RED→GREEN; lossless versioned `float.hex()` encoding, NaN/Inf refused |
| §1C | `data_status` participated in `Species` `__eq__`/`__hash__` (a provenance update forged a second species) AND in the model digest | **REPAIRED** | `compare=False`; separate `source_evidence_digest`; probes RED→GREEN |
| §2 float | a coefficient `>2**53` cast to float64 silently diverged from the integer-certified matrix | **REPAIRED** | symbolic model still constructs (XV-1A preserved); `integrate()` refuses it (`ExecutionBasisError`) — a symbolic certificate is not a numerically executable model |
| §2 freeze | `E`/`N` frozen on **owning** arrays whose `writeable` flag numpy lets a caller re-enable | **REPAIRED** | read-only **views over read-only bases** (re-enable raises); species/reactions are tuples; a rebind of `N`/`E` is caught by a model certificate re-checked at `integrate()` (`StaleCertificateError`) |
| §3 ledger | `CoupledWorld` exempted fixed-activity + reservoir components and reported `reservoir_exchange = E·n_final − E·n_0` — a **tautology** (internal creation/destruction absorbed silently, still STRUCTURALLY_CONSERVING) | **REPAIRED** | scout reproduced endpoint-diff == reservoir_exchange to 16 digits; now each boundary flux is accumulated independently and the balance checked; distinguishing probe (internal fabrication) breaks `material_balance_closed` |
| §4A tol | the outer ledger used `1e-6·max(1.0, scale)` — a 1-mol floor that passed a trace-scale fabrication | **REPAIRED** | scale-aware `atol + rtol·scale`, no floor |
| §1 (compiler #151) | the "generator-independent" lactonization recognizer calls the **same** `_lactonizes_to` as the generator — common-mode, not a second opinion | **CONFIRMED (fragility, not a vouch)** | Track E structural audit; no concrete false-positive found; see §I |
| §8 ammonia | no temperature-domain guard; a circular `seed=h1` fallback in the "independent" cross-check; `1e-9·max(1.0,scale)` floor | **REPAIRED** (Track E/Beth) | see §I |

**Refuted / non-issues:** the compiler #151 termination certificate and v1→v2 receipt **hold** under adversarial
structural audit (§I). No false-VOUCH was demonstrated in #151 within its declared scope.

---

## C. Mathematical contract (what is now executable)

- **Exact stoichiometric conservation:** `E N = 0` proven in **unbounded Python integers** at construction (overflow
  cannot forge a certificate). The float cast is a derived execution artifact; a coefficient `>2**53` makes the
  model non-executable and `integrate()` refuses it.
- **Signed material flux (§3):** `dn/dt = N r + B J + q_ext`, and over a run
  `Δ(E n) = E · ∫q_ext dt` for every component **not** coupled to an implicit solvent reservoir. The RHS of that
  identity is the *independently-accumulated* boundary flux (augmented ODE state), never the endpoint inventory
  diff. Reported per component: `raw_material_change`, `external_flux`, `ledger_adjusted_residual`,
  `material_balance_closed`.
- **Charge against neutral water:** neutral water supplies H/O but **cannot** source net charge. Where "charge" is
  implicit-solvent-coupled the claim is **DEMOTED** (a labeled electroneutrality approximation), never silently
  exempted — a conservation claim requires explicit counterions or a charge-carrying boundary/electrode.
- **Equilibrium projection:** admitted only through a fail-closed gate (completeness, finiteness, nonnegativity,
  an accepted solver verdict, posed-metadata match, and **two independent** conservation closures — the operator's
  own law and the kernel's exact element/charge map). Applied once per macro-step (SNIA, first order).
- **Thermodynamic consistency (Wegscheider):** `γ · log K = 0` for every `γ ∈ ker(N)`, decided on the **exact
  integer kernel** (rational Gauss elimination, not a floating SVD that hallucinates null vectors). A closed loop of
  three reversible isomerizations with K = 2,2,2 is correctly flagged inconsistent (`log 8` imbalance). Driven/open
  networks are explicitly out of scope of that check.
- **Composition / operator-split is NOT a strict functor:** the conservation decoration is a structural invariant,
  but the numerical time-evolution carries a measured operator-splitting error (first-order SNIA); this is
  characterized, never presented as an exact commuting diagram.

---

## D. Evidence receipts — numerical vs physical vs measured

| Dimension | Status in this round |
|---|---|
| Exact conservation (symbolic) | **Demonstrated** (integer `E N = 0`; material balance closes to machine zero) |
| Numerical acceptance | **Observed** (BDF solves close; residuals reported) |
| Chemical identity evidence | **Demonstrated** (species identity binds the digest; substance discriminates isomers) |
| Equilibrium source validity | **Partial** — acetate/carbonate constants sourced + temperature-guarded; ammonia now guarded (§I) |
| Kinetic parameter evidence | **ASSUMED** — `k_diss`, `kLa`, `k_export` are synthetic (CALIBRATION_REQUIRED) |
| Transport/phase parameter evidence | **ASSUMED** — Henry partition/transfer coefficients assumed |
| External reference comparison | **Done** (PHREEQC, §F) — solver corroboration, common-mode on constants |
| Experimental calibration / measured validation | **UNAVAILABLE** (no measured dataset) |

The admitted tier of the unified world is **ASSUMED_PARAMETER** — correctly capped at its weakest premise (the
assumed rate/transport coefficients), never inflated by the sourced equilibrium constants.

---

## E. Integrated flagship (§5)

**Command:** `python -m experiments.sandbox_foundation.unified_chemical_world [--scenario NAME] [--json OUT] [--csv OUT]`
(scenarios: `default`, `excess_acid`, `excess_bicarbonate`, `sealed`, `no_carbon`).

**Architecture:** ONE `CoupledWorld` (two liquid cells + a gas headspace) advanced by the **single generic
operator-split integrator** — no chemistry branch in the integrator. Chemistry lives entirely in typed
declarations: a `MixedAcetateCarbonateEquilibriumOperator` projection per liquid cell; solid dissolution as a
**kernel reaction** `NaHCO3(s) → Na+ + HCO3-` with `r = k_diss·max(0, 1−SI)` (the solid a **table-free** species
the projection never touches); a Henry `InterfaceTransfer` (`partition = K_H·R·T`, `k = kLa·V`); a **selective**
HAc/CO2(aq) membrane valve (charge-safe); and an optional §3-ledgered CO2 export boundary. Valve open/close and
seal/open are phase-level commands (integrate with/without the interface and stitch states).

**Verified default run** (acid meets bicarbonate when the valve opens, open vessel):

| Quantity | Start | End |
|---|---|---|
| cell A (vinegar) pH | 2.50 | 2.86 |
| cell B (bicarbonate) pH | 8.02 | 4.97 |
| solid NaHCO3 (mol) | 0.20 | 0.00 (fully dissolved) |
| CO2(g) (mol) / p_CO2 | 0 | 0.0050 / 0.123 atm |

- **Material balance closed every phase = True; worst checked residual 6.66e-16** (C, Na conserved to machine zero).
- **External flux total: C = −0.2776 mol, O = −0.5551 mol (= 2·C exactly)** — the fizzed-out carbon, independently
  ledgered, reconciling with the measured whole-system carbon change.
- charge **DEMOTED**; admitted tier **ASSUMED_PARAMETER**.
- Output: strict JSON frames (no NaN/Inf), CSV time series, terminal dashboard — per-cell pH/species, dissolved +
  gas CO2, p_CO2, solid remaining, external flux ledger, residuals, model/run identity, assumptions + verdicts.

**Timestep/splitting:** the material balance is a dt-independent identity and closes at every resolution
(n_steps 20/40/80); the first-order SNIA trajectory converges (the exported-C observable moves less between the
finer grids). Scenarios covered: valve closed→open, excess acid, excess bicarbonate, solid exhausted (default
dissolves fully), no carbon (no gas), sealed (no export) and open.

**Stated scientific limits:** `k_diss`/`kLa`/`k_export` are ASSUMED (a numerical simulation, **not** a fizzing-rate
predictor); `Qsp` is an empirical `S²` concentration product (dilute-regime only), not an activity-based phase
equilibrium; SNIA first-order projection + a dissolution-SI lag; **no** bubble nucleation/size/foam dynamics.

---

## F. External benchmark (§6)

The preregistered 11-case mixed acetate/carbonate benchmark was **executed** against two supported databases via
phreeqpython 1.6.2 (dev-venv only).

- **Databases + SHA256 pins (verified == upstream usgs-coupled/phreeqc3):**
  `minteq.v4.dat = 4a48bf5c…`, `llnl.dat = 1324b807…`.
- **Status:** `BENCHMARKED_AGAINST_REFERENCE_SOLVER` with a loud common-mode caveat.
- **Domain of agreement (AGREE vs BOTH DBs, code-admitted): {M1, M2, M4, M5, M7}** — 5 of 11. M11 is code-demoted
  (I > 0.5 M). The domain is **narrow, and that narrowness is the finding**, not a failure hidden.
- **Divergences (honest):** high-Na M8/M9 diverge from the omitted Na⁺ ion-pairing (confirmed in the PHREEQC
  species dump: NaHCO3/NaCO3⁻/Na-acetate populate at 1e-2–1e-1 molal); M3's minteq-only ~0.108 gap is the inherited
  carbonate gap (llnl agrees).
- **Verified:** DB SHAs == pins; abs_dpH recomputed independently for all 22 entries; pipeline reproduces
  (`run_code → compare` byte-stable); `code_results.json` regenerated from the current solver is identical.
- **This is reference-SOLVER corroboration, common-mode on the shared Ka/K1/K2/Kw lineage — NOT measured-chemistry
  validation.** External validation remains UNKNOWN.
- Reproduce: `python -I run_phreeqc.py && python -I compare.py` (DBs fetched to gitignored `db_dl/`; full cold path
  in `reproduce.sh`).

---

## G. Numerical robustness

- **Positivity:** maintained to float dust (the worst excursion observed in the flagship was `-1.6e-14` mol at
  solid exhaustion; positivity held; a real excursion would be surfaced, not clamped).
- **Stiffness:** BDF throughout; the mixed equilibrium is projected algebraically, not as a stiff kinetic relaxation.
- **Timestep convergence:** characterized (§E) — balance dt-independent, trajectory first-order convergent.
- **Precision limits:** exact-integer conservation; `>2**53` coefficients refused for execution; molar-match
  residuals in the PHREEQC harness `< 1e-9` (worst 6.06e-10, flagged as the closest-to-threshold).

---

## H. Generality — distinct chemistries on the same unchanged core

The generic `CoupledWorld` integrator ran, with **no edit to its code**, for:
- the mixed vinegar/bicarbonate world (§E);
- an acetate buffer (XV demo);
- the ammonia/ammonium base buffer + multiphase NH3(aq)⇌NH3(g) stripping (Wave D, hardened in §I);
- a synthetic A⇌B, B+C→D kinetic network and a weak-acid dissociation (XV).

Three independent equilibrium operators (acetate, ammonia, mixed acetate/carbonate) and a kinetic + a solid-
dissolution rate law all attach through the same typed interfaces. The architectural gate holds.

---

## I. Production compatibility + the compiler audit (§9)

Released (1.1.0), the 1.5 candidate (#149), the 25th-class feature (#151) and the 2.0 research track remain
**separate**. #151 was **not** merged.

**Track E adversarial structural audit of #151** (read-only, rdkit absent so structural):
- **No proven false-VOUCH** within the declared "structural type-validity only" scope.
- **MEDIUM (fragility):** the "generator-independent" recognizer and the generator's certificate both call the same
  `_lactonizes_to`/`_forward_lactonizations` — common-mode, a single point of failure dressed as two independent
  checks (our own `a-shared-assumption-cross-check-is-not-independent`). No concrete counterexample found.
- **LOW:** Kekulé-sensitive acceptance (dedup by `resonance_identity`, accept by raw `canonical()`) can demote a real
  aromatic-lactone match — **sound direction** (coverage-loss, never false-VOUCH). An enol slips the masked-carbonyl
  kill (no 2nd heteroatom on the carbinol C) — also sound-direction.
- **Holds under attack:** the termination certificate (operative bound correctly named `max_depth`; the lexicographic
  `(cop_left, atoms, hops_left)` triple well-founded; `cop_left` strictly monotone; ancestor-cycle guard) and the
  v1→v2 receipt (hard string-equality, grammar digest folds the coproduct grammar).

**Ammonia hardening (§8, commit `f557446`):** three soundness repairs, each a tightened safety net with
default-T behavior **byte-identical**: (1) a **temperature-domain guard** — off-25 °C now raises `AmmoniaError`
(before, 1.0 K returned the 25 °C pH), which propagates correctly to the ammonia operator (fail-closes off-25 °C
like acetate); (2) the **circular `seed=h1` cross-check fallback** now sets `agreement=inf` + a loud CIRCULAR
caveat and forces REFUSED — the independent polynomial root is the only thing that earns "routes agree"; (3) the
`1e-9·max(1.0, scale)` charge-balance **floor** replaced by scale-aware `atol + rtol·scale`. **Honest boundary:**
defects (2) and (3) cannot be driven through a valid `solve()` (brentq zeroes the balance; the physical cubic has
one real-positive root), so they are tested at the exact else-branch / helper — a hardened net, not a changed
answer.

**Recognized reaction type ≠ sourced kinetics ≠ demonstrated feasibility** — the compiler and the simulator stay
honest about that distinction.

---

## J. Updated roadmap to a defensible 2.0 release candidate

**Done this round:** P0 identity + immutability (§1/§2); signed flux ledger + charge demotion (§3); scale-aware
tolerances (§4A); the unified flagship world (§5) with timestep characterization; the PHREEQC benchmark (§6);
Wegscheider cycle detection (pre-existing, confirmed); the #151 audit (§9); ammonia hardening (§8).

**Partial / not done:**
- **§2 coupled-world deep immutability** — the kernel is certificate-guarded; `CoupledWorld`'s own interfaces/
  boundaries/`_Eg` are not yet frozen behind a world certificate. (Deliberately not over-invested per the directive.)
- **§4B per-operator evidence** — transport/Henry/dissolution parameter tiers are ASSUMED but not yet folded into a
  multidimensional per-operator receipt dimension-by-dimension.
- **§7 categorical bridge** — the structural laws are individually executable + tested (E·N=0, interface
  conservation, Δ(E·n)=flux, projection closure, Wegscheider); an explicit composition/gluing/idempotence contract
  tying them to `open_chem_diagram` is not assembled.
- **Hosted CI on the branch head** — requires a push (not authorized this round). The OOM-safe full suite is the
  local CI-equivalent run here (§K).

**Before a 2.0-alpha could be called defensible:** at least one *calibrated* regime (a measured dataset, not a
solver), the coupled-world immutability certificate, and the categorical composition contract.

---

## K. Verdict-changing next probes (highest value only)

1. **Calibrate one regime to measurement** — the single biggest tier lift (ASSUMED → CALIBRATED). Everything else is
   solver/structure corroboration.
2. **Resolve the Na⁺ ion-pairing gap** — add NaHCO3/NaCO3⁻/Na-acetate pairs to the mixed solver; the PHREEQC domain
   of agreement should widen from {M1,M2,M4,M5,M7} toward the high-Na cases. Decides whether the narrow domain is a
   model gap or a convention artifact.
3. **A second independent recognizer for #151's lactonization** that does **not** call `_lactonizes_to` — converts
   the MEDIUM common-mode fragility into genuine defense-in-depth.
4. **Coupled-world certificate** — lift the kernel's stale-certificate guard to `CoupledWorld` so a rebind of its
   interfaces/boundaries cannot execute.

**Local test state:** OOM-safe full sandbox suite **GREEN on the final head `f557446`: 857 passed / 0 failed /
0 errors / 0 skipped** (batched, a fresh process per batch), confirmed two ways (targeted per-increment +
whole-suite). **Hosted CI not run** — it requires a push, which was not authorized this round; this local suite
is the CI-equivalent.
