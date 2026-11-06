# sandbox_foundation -- the "two-cell universe" (SmartChem 2.0 simulation-foundation prototype)

Ooh yeah, can do!  This is the smallest falsifiable proof-of-shape that an admitted (here: SYNTHETIC) mechanism
can drive a local evolving physical state with conservation that survives deliberate counterexamples.
It is **not** a game, **not** a PDE engine, **not** a LibGibson dependency, **not** a SmartChem release, and it
touches nothing under `smartchem/`.  Only `numpy` + `scipy`; headless; deterministic (no RNG, `seed=None`).

## Repro

```
.venv/bin/python -m experiments.sandbox_foundation.run_probes                       # prints residuals, exit 0 iff OK
.venv/bin/python -m pytest experiments/sandbox_foundation/tests -q -p no:cacheprovider   # ~20 s, tiny arrays
```
(`run_probes.validate()` returns `(ok, summary)`.)

**`pytest` is the AUTHORITATIVE gate.**  `run_probes.py`'s `OVERALL: OK` is a coarser residual-threshold gate over a few
fixed configurations; it is NOT a substitute for the test suite.  Several real bugs (e.g. a wrong dt bound for
asymmetric volumes, dropped area/distance factors, a dropped reservoir term) fail pytest while leaving the harness OK,
because the harness never visits those configurations.  Never cite the harness alone as evidence the module is correct.

**Mutation-testing hazard:** `min`->`max` (and similar same-length edits) made and reverted within one second can leave a
stale `.pyc` (pyc validation is by integer-second mtime + size).  Run mutation experiments with
`PYTHONDONTWRITEBYTECODE=1` and delete `__pycache__` afterwards.  Do NOT run the repo-wide suite for this module's sake.

## Domain and units (SI)

Two control volumes A (cell 0) and B (cell 1) joined by ONE explicit interface (`area_m2`, `distance_m`).
volume m^3, amount mol, concentration mol/m^3, time s, T K (absolute, > 0), energy J, power W, heat capacity J/K,
diffusivity m^2/s, conductivity W/(m K), rate mol/(m^3 s).

## Constitutive models (all IDEALIZED, all declared)

* **Species transport:** Fick, two-point finite-volume flux: inflow into a cell `= g (c_other - c_self)`, `g = D*Area/Distance`.
* **Thermal:** constant heat capacity, `U = C*T` (U's zero is 0 K, no phase change, no composition dependence);
  Fourier two-point conduction `Q_in = G (T_other - T_self)`, `G = k*Area/Distance`.  `State` stores amounts and
  ENERGY only; temperature is derived, so there is no independent T degree of freedom.  Imposing a T requires an
  explicit `DeclaredController` whose injected energy is booked in the ledger; the state's arrays are read-only.
* **Boundaries:** species `closed` | `prescribed_flow` (mol/s, + into cell); thermal `adiabatic` | `heater` (W) |
  `reservoir` (fixed T through conductance `G_res`; the reservoir keeps its OWN ledger line `RESERVOIR_ACCOUNT`).
* **Reaction:** elementary mass-action with USER-SUPPLIED `k_f`/`k_r` (`ReactionRate`), constant volume, thermally
  neutral (dH = 0 is declared, i.e. NO reaction heat feeds the thermal model).  Mechanisms carry stoichiometric `N`
  (species x reactions) and an inventory matrix `E` (rows = elements + `charge`); the constructor demands `E.N == 0`
  (`ConstitutionError`).  **The mechanisms are SYNTHETIC test fixtures (abstract P<->Q, R+ + S- -> RS, rate
  constants made up).  They are NOT real laboratory chemistry and carry no thermodynamic or kinetic authority.**

## Numerical method and its treatment of positivity / stability / stiffness / error

| Concern | Treatment |
|---|---|
| Transport + conduction | explicit forward Euler, 1st order in dt. Each cell update is a convex combination when `dt <= dt_max = min_i(capacity_i / coupling_i)` (discrete maximum principle => no new extrema, no negative concentration, T stays > 0). |
| Positivity | Layer 1: `dt > dt_max` raises `TimestepError` (`policy="raise"`, default) or substeps with an explicit `report.substepped` flag (`policy="substep"`). Layer 2 (independent of layer 1): any negative amount raises `NegativeAmountError`, `T <= 0` raises `NonPhysicalTemperatureError`; nothing is silently clamped in transport. Tests prove layer 2 fires even with layer 1 disabled. |
| Stiffness | Reaction integrated by `scipy.integrate.solve_ivp` with implicit L-stable **Radau** (declared in `SolverSettings`: rtol 1e-10, atol 1e-13). Checked on a stiff case (k ~ 1e4 /s). Transport is explicit and therefore NOT stiff-stable beyond `dt_max` -- that is why it is bounded and refused, not hand-rolled around. |
| Reaction positivity | Solved in EXTENT space (`n = n0 + N xi`), so element/charge conservation holds by construction up to roundoff. Rates use `max(c,0)`. A result in `[-pos_tol, 0)` (pos_tol 1e-11 mol, roundoff-level overshoot at reactant exhaustion) is clamped to 0 with `report.clamped=True`; below `-pos_tol` it raises. |
| Error | Transport: first-order, error vs closed form measured. Reaction: local error ~ rtol/atol, measured vs closed forms. Composition: Lie splitting, first order; error vs an independent un-split `expm` solve measured, order estimated by log-log fit. NO a-posteriori error bound is claimed. |
| Missing parameters | `MissingKineticParameter` -- a rate is UNKNOWN, never silently zero. Invalid inputs raise `InvalidParameterError`. |

## Probes (each has positive, negative, mutation and independent-method tests)

* **A transport** -- closed conservation, exact `J_AB + J_BA == 0` at ledger level, open boundary == recorded external flow,
  equal c -> zero flux, reversed gradient -> reversed flux, oversize dt cannot make a negative.  Independent: closed form + DOP853.
* **B thermal** -- energy consistent, hot->cold, equal T -> zero, heater == recorded injection, reservoir books its own side,
  T not settable without a declared controller.  Independent: closed form + DOP853.
* **C reaction** -- source == `N r`, `E.N == 0` (elements + charge), extent capped by limiting reactant, missing rates raise,
  closed-form agreement (incl. a stiff case and an unequal-amount bimolecular case), rate change moves only dynamics.
* **D composition** -- global conservation, separable per-operator reports (a transport bug lights up only the transport
  report), disjoint operations commute, coupled ones do NOT (a test asserts the failure of a commutation claim),
  dt-refinement converges at first order to the monolithic solution.

Mutation controls are real: a one-sided flux sign bug, an uphill (anti-diffusion) flux, an unbalanced stoichiometric row
(refused at construction, and -- when smuggled in with `validate=False` -- caught by the conservation assertions), a
reversed-stoichiometry mechanism (conservation is blind to it; the closed-form check is not), a tampered ledger, a
dropped heater record, and an inconsistent splitting scheme (fails the convergence check).  Several mutants are
deliberately *invisible* to conservation and are caught only by a direction / independent-method check -- by design.

## Honesty boundaries (what this does NOT prove)

* Finite numerical checks on a handful of tiny, hand-picked parameter sets are NOT a universal proof of conservation,
  positivity, stability or convergence for all parameters, meshes, or mechanisms.
* The mechanisms are synthetic; nothing here validates SmartChem's real route/oracle outputs or any real chemistry.
* Only two cells, 1-D coupling, constant heat capacity, no reaction enthalpy (so no thermal-chemical feedback), no
  temperature-dependent (Arrhenius) kinetics, no advection/pressure/momentum, no phase change, no multi-reaction
  limiting-reactant LP (single-reaction caps only).  Spatial-partition refinement is NOT tested (only dt refinement).
* Order of accuracy (~1) is observed on one problem family, not proven.
* Commutation failures are demonstrated on instances; commutation successes are exact only because the state supports
  are disjoint (or, in one flagged special case, because the linear operators happen to share a structure).
* Exact-zero ledger cancellation relies on IEEE-754 `a-b == -(b-a)` and summation order; it is a floating-point fact,
  not a symbolic one.
