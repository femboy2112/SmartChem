# Physicalization Round II — 2026-10-20

Scope of this round: audit and strengthen the experimental two-cell physical foundation
(`experiments/sandbox_foundation/`) so an admitted reaction mechanism drives local physical state with
correctly represented reaction complexes, kinetic dependencies, and accountable numerical conservation — while
leaving the published 1.x chemical compiler untouched. All work is on branch
`feat/chemical-graph-projections` (PR #101), a research branch. No `main` merge, tag, or release.

**Everything here is SYNTHETIC / idealized.** Finite numerical checks are not universal proofs.

## 0. Repository state

- Branch `feat/chemical-graph-projections`; this round's work sits on top of `8d327c9`.
- Production compiler `smartchem/` is UNTOUCHED this round: `git diff --stat -- smartchem/` is empty. The frozen
  1.x wire and the 1.0 fingerprint cannot have drifted; 1.5 authority is preserved by construction.
- All changes are under `experiments/sandbox_foundation/` plus `.github/workflows/ci.yml`.

## 1. New / changed models and their assumptions

### 1a. `Mechanism` is now COMPLEX-primary (`twocell.py`)
The authoritative data are the **reactant complex** and **product complex** (`reactant`, `product`: S×R
non-negative multiplicity matrices). The net stoichiometric matrix `N = product − reactant` is a DERIVED,
lossy projection. Element/charge conservation lives on the net: `E · N = 0`.

- Mass-action orders are the complex multiplicities for an **elementary** reaction (default), or **explicit**
  `forward_orders`/`reverse_orders` for an `kinetics="empirical"` law (with a `rate_law_note` recording the
  validity regime). Orders are **never** read off the net column.
- `Mechanism.from_net(...)` is a convenience for reactions with **no species shared across the two sides** (then
  `reactant = max(−N,0)`, `product = max(N,0)` recovers the complexes exactly). Its precondition is documented
  and — by the lossy-projection theorem — **unenforceable from the net alone** (a hostile review confirmed a
  runtime guard is impossible here; the honest contract is the docstring precondition).
- Assumptions: idealized mass-action; closed-shell/charge bookkeeping via the caller-supplied `E`; synthetic
  species.

### 1b. Detailed-balance / Wegscheider instrument (`detailed_balance.py`, standalone, additive)
`check_detailed_balance(N, K)` decides, for a CLOSED reversible network, whether equilibrium constants `K` admit
a detailed-balanced equilibrium: **`log K ∈ im(Nᵀ)` ⇔ `γ · log K = 0` for every `γ ∈ ker(N)`** (the Wegscheider
condition). Computed by two independent routes — `ker(N)` cycle dot (SVD null space) and `im(Nᵀ)` least-squares
membership — which must agree, else it FAILS CLOSED (`consistent=False`, `method_agreement=False`).

- Assumptions: closed system. Driven/open systems (chemostats, work, light, reservoirs) legitimately sustain
  nonequilibrium cycles and are OUT OF SCOPE — a failed check must not be read as forbidding them.
- Source: M. Feinberg, *Foundations of Chemical Reaction Network Theory* (Springer, 2019); historical origin
  Wegscheider (1901). **Citation is from memory, not page-verified**; the module's proof sketch is self-contained
  and does not depend on it.
- Known limitation: `tol` is absolute in log-K space; for `K` spanning many decades a per-reaction *relative*
  imbalance maps non-uniformly. A hostile review could not produce a false-*consistent* exploiting this (the
  dangerous direction); it fails closed on a near-rank-deficient `N`.

## 2. Red-first reproductions and the fixes

| # | Defect (reproduced RED first) | Fix | Pinning test |
|---|---|---|---|
| 1 | `rate_vector` read mass-action orders off the **net** column, so `A+B→2B` at `[B]=0` gave rate `k[A]` (manufactured product from a seedless state) and a catalyst `A+C→B+C` dropped `[C]` (net 0). | Complex-primary orders (1a). | `test_probe_e_complexes.py` T1/T2 |
| 2 | The reaction positivity fixup was a componentwise `np.clip`, which leaves `im(N)` and silently breaks `E·n` conservation; the ledger logged the uncorrected `N·xi` candidate, not the accepted state. | Conservative **extent** clamp (R==1) that stays in `n0+im(N)`; ledger records the **actual** transition `n1−n0`; bounded clip displacement surfaced as `StepReport.clamp_residual`; fail-closed if it exceeds `pos_tol`. | `test_probe_c_reaction.py` (7) |
| 3 | *(hostile review)* The R==1 extent clamp could leave the limiting reactant a few ulp **negative** when its net coefficient is not a power of two (e.g. `96.73 − 3·(96.73/3) < 0`), crashing `State` with `NegativeAmountError` on a legitimate exhaustion step. | Roundoff clip after the extent clamp; displacement surfaced; fail-closed past `pos_tol`. | `test_probe_c_reaction.py::test_extent_clamp_survives_a_non_power_of_two_limiting_coefficient` |
| 4 | *(hostile review)* An empty / all-zero `E` made `E·N = 0` **vacuous** (`max(…, initial=0.0)` reads 0), so a matter-creator `A→2A` passed constitution validation and `audit` was blind. | Refuse a vacuous inventory when `validate=True` (`not np.any(E)`); `validate=False` stays the explicit, declared opt-out. | `test_probe_c_reaction.py::test_vacuous_element_inventory_cannot_certify_conservation` |

### CI gate (`.github/workflows/ci.yml`)
The sandbox lived outside `testpaths = ["tests"]` and `scripts/run_suite.sh` (which collects only
`tests/test_*.py`), so CI never ran it. A new **separate** `sandbox-foundation` job runs
`pytest experiments/sandbox_foundation/tests` + `run_probes` on py3.10/3.12, bounded, without touching the
OOM-safe core runner or the released package. Gate proven: a deliberately broken sandbox test turned it
**red (exit 1)**; revert → green.

## 3. Independent witnesses (not self-consistency)

- `references.py` is an independent closed-form / `expm` / `solve_ivp` oracle importing nothing from `twocell.py`.
- The detailed-balance verdict was re-derived from scratch (build `ker(N) ∋ (1,1,1)`, dot with `log K`): the
  3-cycle residual equals `log(K₁K₂K₃)` exactly — `0` for `[2,3,⅙]`, `log 8 = 2.0794` for `[2,2,2]` — matching
  both the instrument's routes.
- A directed hostile-review pass (authorized own-code adversary) attacked the full diff; it found items 3 and 4
  above (both now fixed + pinned) and could not break rate_vector, the orders gate, the ledger invariant, or
  produce a false-consistent Wegscheider verdict.

## 4. Test results (local, `.venv`, this box)

- Sandbox suite: **102 passed** (`experiments/sandbox_foundation/tests`, no:cacheprovider). `run_probes` → `OVERALL: OK`.
- `ruff check` on all changed files: clean.
- Production core suite (`scripts/run_suite.sh`): **not run this round** (OOM-safe runner; production `smartchem/`
  unchanged, so no new risk). The `sandbox-foundation` CI job's py3.10/3.12 matrix is **unexercised locally** —
  it needs a real runner on the pushed SHA.

## 5. Claim ledger

- **OBSERVED** — autocatalysis/catalyst rate bug, clamp-crash, and vacuous-`E` hole each reproduced RED and then
  made GREEN; sandbox suite 102-green; CI gate caught a mutation.
- **DISCLOSED (within scope)** — conservation is exact to roundoff for the R==1 extent clamp; the R>1 clip's
  conservation displacement is bounded by `pos_tol` (fail-closed past it) and surfaced in `clamp_residual`.
- **CORROBORATED** — the detailed-balance verdict (two internal routes + an external hand re-derivation).
- **UNVERIFIED** — the Feinberg page-level citation; the `sandbox-foundation` job on the CI matrix.

## 6. Remaining unknowns & measured defers (next falsifying experiment named)

Each is DEFERRED, not half-built. These are the honest 2.0 obligations.

- **§5 General N-cell mesh / face contract.** The two-cell interface already proves `J_A→B + J_B→A = 0` per side.
  *Next:* a 3-cell chain where one oriented transfer event updates both adjacent cells; assert per-face residual
  0, global conservation, and the structural condition `onesᵀ · B_space = 0`.
- **§6 SmartChem→mechanism adapter + Descriptive/Executable split.** The V2_0 contract still carries the
  ambiguity "valid pack with unavailable kinetics" vs "refuse on missing kinetics". *Resolution to implement:*
  `DescriptiveMechanism` (structure + optional, possibly-UNKNOWN facets) vs `ExecutableMechanism` (admitted
  subset, complete params, verified conservation, declared regime). *Next:* `compile_physical_mechanism(step)`
  that RE-DERIVES `E` and `N` from a real `ExperimentStep`/`OpenChemDiagram`, returns a typed
  `KINETICS_UNAVAILABLE` descriptive result, and refuses to emit an executable mechanism without a sourced rate
  law (never a silent zero).
- **§7 Production 1.5 chemistry.** Untouched this round. *Next:* targeted (scoped, not full-suite) rerun of the
  #110/#111 false-vouch gates to confirm no drift; investigate #115 Claisen condensation, explicitly
  distinguished from the already-explored Claisen [3,3] rearrangement.
- **§8 Aqueous equilibrium.** The `#105` single-global-int `Molecule.charge` wall blocks general ionic chemistry.
  A curated 0-D electrolyte-equilibrium model (acetic acid/acetate/water, then bicarbonate/carbonate/CO₂) MAY be
  admissible from explicitly selected, sourced species — but **no thermodynamic numbers are to be invented**.
  *Next:* source + audit the species set and validate against an independent solver (Reaktoro); if the data
  cannot be sourced this round, deliver only the missing-data contract. (This round delivers the defer, not a
  manufactured result.)
- **§9 LibGibson `PhysicalWorldSnapshot → Presentation`.** *Next:* an immutable, schema-versioned snapshot
  dataclass + a property test that different presentation framerates yield identical authoritative trajectories
  (the non-negotiable renderer-disabled identity test).
