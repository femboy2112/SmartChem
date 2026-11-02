# Physicalization Round III — 2026-10-20

Proof-carrying dynamics: chemical identity → admitted mechanisms → conservative, dissipative worlds.

Scope: advance BOTH fronts — (1) the experimental two-cell/N-cell physical foundation
(`experiments/sandbox_foundation/`) toward a conservative, dissipative, compositional engine, and (2) the 1.5
chemical-compiler release program — WITHOUT changing published 1.0 semantics, the 1.1 boundary, the 19-class
recognition baseline, or merging/tagging/releasing. All work is on `feat/chemical-graph-projections` (PR #101),
a research branch. **Everything in the sandbox is SYNTHETIC / idealized; a finite numerical check is not a
universal proof.**

## 0. Repository state

- Branch `feat/chemical-graph-projections`; Round III sits on top of `c1b8e36` (Round II).
- Production compiler `smartchem/` is UNTOUCHED this round: `git diff c1b8e36 --stat -- smartchem/` is empty. The
  1.0 fingerprint, the 1.1 MINOR boundary, and the 19-class baseline cannot have drifted — by construction.
- All changes are under `experiments/sandbox_foundation/` plus `docs/research/`.
- Round III commits: `b724c41` (B1/B3), `1790f33` (D), `3f08834` (E1 plan), `33ac8e9` (B2), `c998fda` (C),
  `72abfe8` (A), `a55310c` (G), and this record.

## 1. What landed, production vs experimental

| wave | module(s) (all under `experiments/sandbox_foundation/`) | tests | status |
|---|---|---|---|
| **B1** complex validation hardening | `twocell.py` (finite/unique/exact-integer/bounded; zero-reaction & zero-net cases) | `test_probe_e_complexes.py` | verified |
| **B2** rate-law units + standard invariance | `rate_units.py` | `test_rate_units.py` (7) | verified |
| **B3** exact Wegscheider kernel | `detailed_balance.py` | `test_detailed_balance.py` (+8) | verified, red-first by **dalembert** |
| **C** free-energy Lyapunov dissipation | `lyapunov.py` | `test_lyapunov.py` (11) | verified, red-first by **evil-morty** |
| **D** oriented-face three-cell mesh | `mesh.py` | `test_mesh.py` (18) | verified (expm reference) |
| **A** SmartChem→mechanism adapter + typed authority | `mechanism_adapter.py`, `mechanism_types.py` | `test_mechanism_adapter.py` (29) + `test_mechanism_types.py` (21) | verified, red-first by **evil-morty** |
| **G** LibGibson snapshot boundary | `snapshot.py` | `test_snapshot.py` (7) | verified |
| **E1** PR #101 split plan | `docs/research/V1_5_PR101_INTEGRATION_PLAN.md` | — | delivered |
| **E3** 1.5 hard gates | (verification only) | scoped production tests | re-verified GREEN at `c1b8e36` |

Production (1.5) front: E1 (a git-grounded split/stacked integration plan: `main..34e1891` production vs
`34e1891..c1b8e36` experimental, pointer-only units) + E3 (gates re-verified: recognizer count 19 from the live
module; #110/#111 false-vouch controls 22+15; #114 opt-in profile 32; version-independent fingerprint NO DRIFT;
readiness laws 47). No production code changed.

## 2. Theorems / invariants proved this round (hypotheses explicit)

- **B2 standard-state invariance.** For every stoichiometric cycle `γ ∈ ker(N)`, `γ·Δν = γᵀNᵀ1 = 1ᵀ(Nγ) = 0`
  (`Δν = net mole change = 1ᵀN`). ⟹ the Wegscheider cycle sum `Σ γ_j log K°_j` is invariant under a change of
  reference concentration `c°`. Distinguished from the FALSE claim that `k_f/k_r` is itself dimensionless: `Kc =
  k_f/k_r` carries dimension `(mol/m³)^Δν`; only `K° = (k_f/k_r)/(c°)^Δν` is dimensionless. Checked exactly on the
  integer kernel (residual 0).
- **C2 diffusion dissipation (continuous).** Closed passive Fickian transport: `dΦ/dt = −Σ_i g_i (c_{i,A}−c_{i,B})
  (log c_{i,A}−log c_{i,B}) ≤ 0` since `(a−b)(log a−log b) ≥ 0`; the equilibrium reference `c*` cancels.
- **C1 reaction dissipation (continuous).** For reversible **elementary** mass action at a detailed-balanced `c*`:
  `dΦ/dt = −Σ_j (v_{f,j}−v_{r,j}) log(v_{f,j}/v_{r,j}) ≤ 0`, via `Σ_i N_ij log(c_i/c*_i) = −log(v_f/v_r)` using the
  detailed-balance identity `Σ_i N_ij log c*_i = log K_j`. **Requires a Wegscheider-consistent `K`** (ties to B3)
  and elementary kinetics (enforced by refusal — see §3 KILL 1).
- **C3 discrete monotonicity (Jensen).** The explicit-Euler two-cell diffusion update is, per species, a convex
  combination `c_A' = (1−α)c_A + αc_B`, `c_B' = (1−β)c_B + βc_A` with `α = hg/V_A, β = hg/V_B ∈ [0,1]` under
  `dt ≤ dt_max`. Jensen on the convex `h` plus the exact weight identity `V_Aα = V_Bβ = hg` cancels the
  cross-terms, giving `V_A h(c_A') + V_B h(c_B') ≤ V_A h(c_A) + V_B h(c_B)`. A discrete statement over the
  supported dt range, not an observation about one solver trajectory.
- **D spatial-incidence conservation.** For the oriented-face incidence matrix `B_space` (+1 head, −1 tail),
  `1ᵀ B_space = 0` exactly ⟹ a closed system conserves every species total (discrete divergence theorem),
  independent of the constitutive model.
- **A central acceptance law.** A caller-supplied/forged/omitted/invented element-charge inventory `E` can never
  certify a non-conserving transformation: `E` is DERIVED from the molecules' own `formula`+`charge`; a supplied
  `E` is only compared (fail-closed on disagreement), never used.
- **G renderer-disabled identity.** A frozen snapshot with read-only arrays + pure rendering ⟹ rendering 0/1/N
  times leaves the canonical state and the `model_digest` bit-identical; cosmetics (`display_hints`) are excluded
  from `model_digest`; model identity ⊥ evidence identity.

## 3. Red-first counterexamples and the corrected implementations

| # | adversary | defect (reproduced RED first) | fix | pinning test |
|---|---|---|---|---|
| B3 | **dalembert** | `check_detailed_balance` decided ker(N) by a floating SVD threshold cross-checked with floating lstsq; BOTH share the SVD rank cutoff (NOT independent). The unimodular full-rank integer matrix `[[1,0],[9e15,1]]` (ker={0}, every `K` admissible) was reported `consistent=False` with `residual == residual_image` to the last digit — one SVD decision read twice. | verdict driven by an EXACT integer kernel (rational Gauss-Jordan, bounded); SVD rank + lstsq kept only as diagnostics; non-integer/over-large `N` refused | `test_detailed_balance.py::test_C5_...` |
| C (KILL 1, HIGH) | **evil-morty** | `reaction_dissipation_rate` guarded the detailed-balance hypothesis but left the ELEMENTARY hypothesis fail-OPEN. On a first-class empirical mechanism with a detailed-balanced `c*` it reported `dΦ/dt = −0.575` (dissipating) while Φ genuinely ROSE at `+0.811`; the self-consistency identity broke silently. | refuse a non-elementary mechanism in `reaction_dissipation_rate` (the C1 closed form is derived from orders = complexes) | `test_lyapunov.py::test_empirical_kinetics_are_refused...` |
| A (KILL 2, MEDIUM) | **evil-morty** | `smiles_claims` re-derived local-charge detection as `charged_atoms > |net|`, weaker than the codebase's own `SmilesFeatures.has_local_charge_structure`; it MISSED same-sign multi-site charge (`[NH3+]CC[NH3+]`, net +2, two +1 sites) — a per-atom distribution the single global `Molecule.charge` cannot hold. | call the codebase's own sound predicate; plain monovalent ions still pass | `test_mechanism_adapter.py::test_same_sign_multisite_charge...` |

Also fixed red-first in B1 this round's lineage (Round II carried the complex/clamp/vacuous-E repairs). evil-morty's
central-law attacks on A (forged/omitted/invented E, 20k random states) all FAILED to break it — earned clean bill.

## 4. Independent verification methods — and whether they share assumptions

- **B3 exact kernel** vs the floating SVD/lstsq diagnostics: the exact rational kernel shares NO assumption with the
  floating routes; the module explicitly records that the two floating routes are NOT independent of each other
  (common SVD cutoff) and are advisory only. dalembert's kill ran the COMMITTED code and quoted the output; the fix
  was then checked against dalembert's own 11-control battery.
- **C dissipation**: the analytical `dPhi_dt_chain_rule = ∇Φ·(dc/dt)` is computed from the full RHS, independent of
  the simplified closed forms; their agreement is the proof's algebra (checked to ~5.7e-14 over 20k random states by
  evil-morty). A refined finite difference of Φ along a trajectory corroborates the rate but is NOT the authority.
- **D mesh**: validated against `scipy.linalg.expm(−L t)` (the graph-Laplacian reference is independent of the
  stepper; first-order Euler convergence confirmed, error halving with dt). The ledger (per-side events) and the
  accepted state (one-sided flux through `B_space`) are DIFFERENT code paths, so `transition_residual` is a real
  cross-check. Boundary: `B_space` in the expm reference is the mesh's own (cross-checked against a hand-written
  matrix, but the incidence convention is shared).
- **A adapter**: E derived from `Molecule.formula`/`charge` is independent of any supplied E. evil-morty attacked the
  central law directly and could not break it.

## 5. Test results (local, `.venv`, this box)

- Full sandbox suite: **211 passed** (`experiments/sandbox_foundation/tests`); `run_probes` → `OVERALL: OK`.
- `ruff check` on all changed/new files: clean.
- Production core suite (`scripts/run_suite.sh`): **not run this round** — production `smartchem/` is unchanged
  (`git diff c1b8e36 -- smartchem/` empty), so no new risk; the last recorded figure is 7655/0/50skip at `34e1891`.
  The `sandbox-foundation` CI job + the core/PySCF jobs run on the pushed SHA (see §8).

## 6. Model representations and their identity/authority rules

- **Mechanism** (`twocell.py`): complex-primary; `N = product − reactant` is a lossy projection; kinetic orders are
  the complexes (elementary) or explicit (empirical), never the net column; conservation `E·N=0` lives on the net;
  structural complexes are exact non-negative integers (fractional orders live only in empirical kinetics).
- **Descriptive vs Executable** (`mechanism_types.py`): structure+facets (inspection) vs a selected finite reaction
  set with complete admitted kinetics+provenance+declared omissions (execution). Conversion needs sourced or
  explicitly-SYNTHETIC rate laws; a missing law is `KINETICS_UNAVAILABLE`, never a silent zero. `E` is re-derived,
  not injectable.
- **PhysicalWorldSnapshot** (`snapshot.py`): two content-bound digests — `model_digest` (authoritative scientific
  content only) and `evidence_digest` (admission sources/checks) — with renderer-neutral `display_hints` excluded
  from both. This is also Wave A3 (model identity ⊥ evidence identity ⊥ display).

## 7. New data sources & unsupported regimes

- **No new sourced thermodynamic/kinetic data admitted this round.** All mechanisms remain SYNTHETIC. No rate
  constant or equilibrium constant was invented.
- Standing walls, unchanged: the `#105` single-global-`int` `Molecule.charge` (per-atom/local charge unrepresentable
  — the adapter REFUSES such species, it does not solve #105); isotope/stereo/material/phase refused.

## 8. CI

The push of the Round III commits triggers a CI run on the new HEAD; the `sandbox-foundation` job (py3.10/3.12)
exercises the full 211-test sandbox suite on a real runner, and the core/wheel jobs exercise the unchanged
production package. **The complete-SHA verdict must be read off that run, not claimed here.** (The prior `c1b8e36`
run `39472998934` had both sandbox jobs + all wheel jobs green; its core/PySCF jobs are to be confirmed.)

## 9. Claim ledger

- **OBSERVED** — all three red-first defects (B3 SVD false-inconsistency, C KILL 1 sign inversion, A KILL 2
  local-charge miss) reproduced RED and made GREEN; sandbox suite 211-green; `run_probes` OK.
- **DISCLOSED (within scope)** — the C theorems hold under their stated closed/ideal/isothermal/fixed-volume/
  elementary/detailed-balance hypotheses, enforced by refusal; D's expm agreement is first-order Euler (measured,
  not machine-precision); the coupled reaction-diffusion mesh term is linear-only and its split error is measured,
  not proved.
- **CORROBORATED** — B3 (exact kernel + dalembert's independent battery); C (analytical identity + 20k-state
  evil-morty sweep + finite-difference); D (expm reference + 2-cell reduction).
- **UNVERIFIED** — the complete-SHA CI verdict on the pushed HEAD; the adapter's `resonance_identity` species-key
  as a faithful proxy across ALL exotic resonance/tautomer pairs (evil-morty's residual unease — no counterexample
  found; next probe in §10).

## 10. Remaining obligations & next falsifying experiments (measured defers)

Each is DEFERRED, not half-built.

- **B4 thermodynamics → equilibrium.** `ΔrG° = Nᵀμ°`, `ln K° = −ΔrG°/RT` as a SECOND, independent route to the
  equilibrium constants. *Blocked on:* independently sourced standard-state `μ°` data (none admitted this round).
  *Next:* source + audit `μ°` for a specific small set and cross-check its `K°` against the detailed-balance check;
  keep optional/UNKNOWN when data is unavailable.
- **E2 one substantive 1.5 chemistry improvement.** NOT attempted this round (a soundness-critical production
  recognizer deserves its own red-first adversarial gate + full OOM-safe suite run, not a tail-of-round addition).
  *Next:* #115 Claisen CONDENSATION recognition (distinct from the [3,3] Claisen rearrangement) — the 1,3-dicarbonyl
  product + residual α-H + base/alkoxide constraints; the falsifying probe is a butanone-type FICTION that must NOT
  be vouched. Or #107 catalyst/activator ledger (a negative/control corpus first). Ship one verified, or a
  documented obstruction — never a fabricated vouch.
- **F aqueous-chemistry foothold.** NOT built this round. *Next:* ONE curated 0-D electrolyte-equilibrium subsystem
  (acetic acid / acetate / water, then bicarbonate/carbonate/CO₂) from explicitly selected, SOURCED species —
  `Ka(AcOH)` pKa 4.76 is tertiary-sourceable with an uncertainty, but NO thermo numbers are to be invented; validate
  against an independent solver (Reaktoro). Challenge any universal "sealed always means lower conversion" claim with
  a discriminating, measurable range. If data can't be sourced, deliver the data-requirement contract only.
- **Mesh general topology / coupled nonlinear reaction-diffusion.** D ships a chain + a linear coupled term.
  *Next:* a non-chain graph trajectory vs expm; a nonlinear coupled reaction-diffusion split-error study.
- **Adapter species-key soundness.** *Next:* hunt a `resonance_identity` collision across distinct
  composition/charge (the one path that could break the central law from the inside); if found, key on
  `(resonance_identity, composition, charge)` instead.

## 11. 2.0 → 3.0 dependencies (revised)

The conservative, dissipative, compositional spine now exists in the sandbox: complex-primary admitted mechanisms
(B1) with dimensioned kinetics (B2) and an exact detailed-balance certificate (B3) drive a free-energy-dissipating
(C) evolution on an oriented-face conservative geometry (D), observed through an immutable, content-bound,
renderer-disabled snapshot (G), fed by a SmartChem→mechanism adapter whose conservation cannot be forged (A). The
remaining 3.0 path runs through B4 (sourced thermodynamics) → F (a real aqueous subsystem) → #105 (per-atom charge,
the ionic-chemistry prerequisite) → the mechanism-pack loader → LibGibson's own renderer (its repo, epic #125).
