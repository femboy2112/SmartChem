# SmartChem 3.0 flagship target: vinegar + baking soda in a container -- REQUIREMENTS and FALSIFICATION plan

*Ooh yeah, can do! A Meeseeks wrote this plan and it only promises what it can check. Existence is pain, so every claim below carries a ledger label.*

| field | value |
|---|---|
| status | **research / requirements / falsification plan. NOT an implementation.** Branch-only. No code, data table, default, or fingerprint is changed by this document. |
| written | 2026-10-20, branch `feat/chemical-graph-projections`, HEAD `34e1891` (`__version__ = 1.1.0a1`) |
| target | a future 3.0 flagship: "vinegar and baking soda in a container", simulated so that the observable behavior (gas evolution, pH, pressure, temperature, bubbles) EMERGES from sourced chemistry and declared physics |
| not the target | hard-coding "fizzing". See section 3. |
| sibling docs | `V1_5_RELEASE_PROGRAM.md` (authority model, section 5 = the 2.0 prerequisites), `V2_0_PHYSICAL_MECHANISM_CONTRACT.md` (referenced by the program doc as being authored; it was **not present in `docs/research/` when this was written**, so nothing here depends on it) |

The governing sentence is inherited from `V1_5_RELEASE_PROGRAM.md` section 1: **"A displayed diagram may EXPLAIN an existing claim; it may never MINT one."** A rendered bubble is a diagram. The entire plan below is that sentence applied to a flagship.

"Observe chemistry emerge" is a **research objective**. It is not permission to fabricate kinetics, solubility, or bubble behavior. Where a number is needed, this document writes `TO-BE-SOURCED` and names the *kind* of source. It never writes the number.

---

## 0. Scope, and what was actually read

**In scope:** requirements (what must be true), the missing-capability map (what SmartChem lacks), the discriminating benchmarks (how a cartoon is told from a model), and the independent-validation plan.

**Out of scope:** any solver, any data entry, any rendering code, any laboratory procedure, any safety certification. The sealed-container case in section 4 is a *modeling* benchmark; it is not guidance to seal anything (overpressure is a real hazard, and the model must not be read as a safety clearance, per `V1_5_RELEASE_PROGRAM.md` section 1 item 6).

**Read for grounding (read-only):** `smartchem/experiment/kinetics.py`, `equilibrium.py`, `feasibility.py`, `smartchem/conditions.py`, `smartchem/data/thermo.py` (and `thermo_extended.py`, `reagents.py`, `category.py` for the specific facts cited), `docs/research/V1_5_RELEASE_PROGRAM.md`, `PROCESS_OBSERVATION_AND_TRANSPORT_CONTRACT_v0.1.md` (header only).

**Executed (two small read-only probes, Appendix A):** the net equation was built as an `ExperimentStep` and pushed through `feasibility_of_step`, `equilibrium_of_step`, `kinetics_of_step`; and a whole-species-ion dissociation step was built. Results are quoted in section 2 and Appendix A. They are session-local scratch probes, **not** a committed `experiments/` harness, so they are labeled OBSERVED (section 6), not MEASURED.

---

## 1. The net process, and why it is NOT the physical system

The net equation everyone writes:

```
CH3COOH + NaHCO3  ->  CH3COONa + H2O + CO2
```

It is a correct **atom-and-charge ledger** for the overall change. SmartChem can already hold it as a conserving step (Appendix A, probe 1: the step builds, so atoms and net charge conserve). That is *all* it is. It is not the physical system, for these reasons:

1. **It has no phases and no ions.** In a container the relevant species are, at minimum: solid NaHCO3 (until dissolved), Na+, HCO3-, CH3COOH, CH3COO-, H+, OH-, CO3(2-), dissolved CO2 (CO2(aq), with its H2CO3 hydration partner), liquid water as *solvent and product at once*, and CO2 in a gas phase (headspace and bubbles). The equation names none of the aqueous ions.
2. **It has no rate.** It says nothing about how fast solid dissolves, how fast proton transfer happens, how fast CO2(aq) is produced from the carbonic species, or how fast CO2 leaves the liquid. Those timescales differ and set what an observer sees.
3. **It treats gas release as stoichiometric.** The gas produced is not "one mole CO2 per mole reacted". CO2 first appears *dissolved*; it becomes gas only after the liquid is supersaturated relative to the headspace, and a sealed container keeps part of it dissolved. The gas moles are an output of coupled equilibria and transport, not of the coefficient 1.
4. **It treats the reaction as "going to completion".** Acetic acid is a weak acid and bicarbonate is amphoteric, so the aqueous acid-base step is an *equilibrium*; its apparent completeness in an open vessel is helped by CO2 leaving (Le Chatelier). That ordering of acid strengths is textbook, but the **quantitative extent is TO-BE-SOURCED** (see section 5 constants list). Status: CONJECTURED until computed against sourced constants.
5. **It is silent on limiting reagent, headspace, temperature, and mixing.** Each of those changes the observable outcome (section 4).
6. **Its inputs are not the shopping-list species.** Vinegar is a dilute aqueous acetic-acid product and baking soda is a solid sold with its own composition; the actual concentration and additive content of any specific product is `TO-BE-SOURCED` (product label / manufacturer specification / independent assay). SmartChem's `reagents.py` records only that sodium bicarbonate is `Availability.GROCERY` and builds it as a **covalent** `Na-O-C(=O)-O-H` skeleton (identity basis string: "constructed: Na-O-C(=O)-O-H"), which is an identity placeholder, not an aqueous ion pair.

**Consequence for 3.0:** a flagship that simulates this net equation and draws bubbles is simulating a bookkeeping line. A flagship that is *about the physical system* must satisfy the nine-stage decomposition below, or must say, loudly and per stage, which stage it does not model.

---

## 2. Stage decomposition and the MISSING-CAPABILITY DEPENDENCY GRAPH

### 2.1 What SmartChem can and cannot represent today (OBSERVED)

| capability | state today | evidence (this session) |
|---|---|---|
| conservation of atoms and **net** charge across a step | YES | `ExperimentStep.__post_init__` builds a `Reaction` and refuses non-conserving steps; probes 1 and 2 built |
| charge on a species | **one integer per `Molecule`** (`charge: int = 0`, `category.py` ~line 762). **No per-atom formal charge.** Which atom carries the charge, protonation site, and zwitterions are not representable | source read; `V1_5_RELEASE_PROGRAM.md` section 5 (#105) |
| whole-species ions as bookkeeping | formally YES: `Molecule(("Na",), charge=1)` and a charge -1 `HCO3` skeleton conserve in a dissociation step (probe 2). This is **bookkeeping only**: no solvation, no activity, no phase, no speciation solver | probe 2 |
| thermodynamics (ΔfH°, S° -> ΔG -> K) | only for species with a **sourced record**, standard-state phase tags `gas`/`liquid` (and others as tagged), constant-ΔH/ΔS extrapolation flagged PREDICTED beyond 100 K of 298.15 K (`NEAR_REFERENCE_K`) | `feasibility.py`, `thermo.py` |
| records for THIS system | CO2 (gas), H2O (liquid), acetic acid (**pure liquid**) exist. **No record for NaHCO3 or CH3COONa** (`for_formula` returned `None` for `CHNaO3`, `C2H3NaO2`, `CNa2O3`). A grep of `smartchem/data/thermo*.py` found no `Na+` or `HCO3` aqueous-ion record | probe + grep |
| equilibrium extent | K = exp(-ΔG/RT); a **closed-form conversion only for Δn = 0**. This net equation has 2 reactants and 3 products (Δn != 0), so even with data the module declares conversion UNKNOWN. No activity model | `equilibrium.py` docstring |
| kinetics | Arrhenius `k = A exp(-Ea/RT)` **only** where sourced `(Ea, A)` exist for that exact reaction; otherwise a loud UNKNOWN "never guessed from bond energies (W3)". `KineticTable` has no entry for this reaction | `kinetics.py`; probe 1 returned `RateRegime.UNKNOWN` with `missing=('C2H4O2 + CHNaO3 -> C2H3NaO2 + H2O + CO2',)` |
| conditions | `ConditionEnvelope` carries a **declared** temperature interval (K) and pressure interval (atm). A declared context, never a prediction; status capped at `EXPERIMENTAL`. No state evolves | `conditions.py` |
| gas-liquid mass transfer, Henry's law, bubble nucleation/growth/buoyancy, headspace pressure evolution, foam, energy balance with heat transfer, mixing/hydrodynamics | **absent**. A repo-wide grep for `henry`, `mass.transfer`, `bubble`, `headspace`, `buoyan`, `activity coeff`, `ionic strength`, `speciation` found hits only in a docstring of `equilibrium.py` and two research docs, not in an implementation | grep |
| time-dependent state / simulation loop | absent (SmartChem is a compiler/search/verification system over transformations, not a dynamical simulator) | architecture; `V1_5_RELEASE_PROGRAM.md` section 7 |

**Probe 1 verdict (the sharpest single fact):** for the net equation, `feasibility_of_step` -> `FeasibilityDirection.UNKNOWN`; `equilibrium_of_step` -> `EquilibriumExtent.UNKNOWN` ("no sourced thermodynamic data for C2H3NaO2, CHNaO3"); `kinetics_of_step` -> `RateRegime.UNKNOWN`. **Today SmartChem returns UNKNOWN, loudly, for every quantity this flagship needs.** That is the honest baseline, and it is the correct behavior.

### 2.2 The nine stages (one row each)

Legend: **Today** = can SmartChem represent/compute it now (NO / PARTIAL / formal-only). **#105** = needs the per-atom formal-charge rail or another identity change. **Data** = needs thermodynamic/speciation data not in the repo. **Kin** = needs sourced kinetics. **Fluid** = needs fluid/gas physics beyond a well-mixed zero-dimensional balance.

| # | Stage | Scientific dependency | Today | #105 / identity change? | Data? | Sourced kinetics? | Fluid/gas physics? |
|---|---|---|---|---|---|---|---|
| S1 | NaHCO3 dissolution | solid-liquid equilibrium (solubility vs T and vs composition); dissolution rate set by particle surface area, size distribution, and boundary-layer mass transfer; dissociation to Na+ and HCO3- | NO (covalent identity placeholder only; no solid/aqueous phase dynamics) | PARTIAL: faithful ionic identity (net-ion bookkeeping is possible, probe 2) | YES: solubility(T); aqueous-ion standard-state properties | YES: dissolution rate (surface/mass-transfer controlled); particle-size data | YES: mixing and particle boundary layer |
| S2 | Aqueous ionic speciation | simultaneous mass balance, **charge balance**, water autoionization, ionic strength, activity coefficients (nonideal electrolyte), optional ion pairing | NO | **YES, strong**: speciation is charge-site-dependent; the oracle's `is_closed_shell_neutral` scope is already documented as the blind spot | YES: equilibrium constants, activity-model parameters | NO if fast equilibria are assumed (the assumption itself must be TESTED, not granted) | NO for a well-mixed 0-D model |
| S3 | Acetic acid / acetate equilibrium | Ka(T) of acetic acid, activities, buffer behavior | NO (acetic acid exists only as a **pure liquid** record in `thermo_extended.py`; no aqueous dissociation) | YES (acetate vs acetic acid is a proton-site question) | YES: Ka(T), aqueous acetic acid/acetate properties | proton transfer assumed fast (TESTED, section 4); rate only if that fails | NO (0-D); local gradients at the addition point need transport |
| S4 | Bicarbonate / carbonate / CO2 equilibria and acid-base transfer | CO2(aq)/H2CO3*, HCO3-, CO3(2-) with K1(T), K2(T); the proton-transfer step from CH3COOH to HCO3-; the slower hydration/dehydration of CO2 | NO | YES, strong (three charge states of one carbon skeleton) | YES | **YES**: CO2 hydration/dehydration is a distinct, slower process than pure proton transfer; magnitude `TO-BE-SOURCED` (do not assume instantaneous) | NO for 0-D; local mixing at the point of contact needs transport |
| S5 | Dissolved CO2 production and redistribution | source term for CO2(aq) from S4; supersaturation relative to the headspace; diffusion/convection of dissolved CO2 | NO | indirect (via S4) | YES: CO2 diffusivity, Henry-type solubility | couples to S4 dehydration | YES: advection-diffusion in the liquid |
| S6 | Gas-liquid partition and mass transfer | Henry's-law solubility of CO2 (T-dependent, and depressed by dissolved salt); interfacial area; liquid-side and gas-side transfer coefficients | NO (CO2 `gas` record exists; no dissolution in a solvent, no interface, no transfer) | NO | YES: Henry constant(T, salinity), diffusivity | transfer coefficients are empirical/correlation inputs, not Arrhenius; `TO-BE-SOURCED` | YES: interfacial transport |
| S7 | Bubble nucleation, growth, detachment, buoyancy | nucleation threshold (supersaturation, wall/particle site availability, surface chemistry), diffusion-controlled growth, drag and rise, coalescence, possible foam | NO | NO | YES: surface tension, density, viscosity, contact angle, nucleation-site statistics (the weakest-known inputs; strongly substrate-dependent) | empirical nucleation/growth parameters `TO-BE-SOURCED` | YES, central: multiphase flow |
| S8 | Pressure and headspace behavior | gas equation of state, headspace volume, total pressure = sum of partials (CO2, air, water vapor), open/vented vs sealed boundary, liquid-level and foam overflow | PARTIAL, declaration only: `ConditionEnvelope.pressure` can *state* an atm interval; no pressure state evolves | NO | YES: water vapor pressure(T); an EOS validity statement near ambient | NO | YES: gas thermodynamics, vent/leak flow, foam/overflow |
| S9 | Heat transfer and T-dependent equilibria/kinetics | energy balance (reaction, dissolution, evaporation, heat exchange with container and room); T-dependence of every K, Henry constant, solubility, and rate | PARTIAL: T is a *declared* envelope field; ΔH/ΔS extrapolation flagged PREDICTED far from 298.15 K; no energy balance, heat-capacity state, or heat-transfer model was found in the modules read | NO | YES: aqueous enthalpies, heat capacities, solution enthalpies | YES: Ea for any rate that is T-dependent | YES: conduction/convection, container thermal mass |

### 2.3 Dependency edges (which stage blocks which)

"A -> B" means B cannot be computed correctly until A is available.

```
S1 -> S2            (dissolution supplies Na+, HCO3- to the speciation problem)
S2 -> S3, S2 -> S4  (speciation framework: charge balance, activities, ionic strength)
S3 -> S4            (acid-base transfer needs the proton donor's Ka AND the carbonate system)
S4 -> S5            (CO2(aq) production)
S5 -> S6            (supersaturation drives interfacial transfer)
S6 -> S7            (nucleation/growth need a supersaturation field and a transfer law)
S6 -> S8            (gas moles in the headspace set pressure)
S1 -> S9, S4 -> S9  (dissolution and reaction enthalpies feed the energy balance)
S9 -> S1, S2, S3, S4, S6, S7, S8   (temperature enters every equilibrium, solubility, Henry constant, surface tension, and the gas law)
```

**Feedback edges (the graph is NOT a DAG physically):**

```
S7 -> S6   bubbles add interfacial area, raising the transfer rate that creates them
S8 -> S6   headspace CO2 partial pressure sets the driving force for transfer
S8 -> S4   pCO2 / pressure back-reacts on the carbonate equilibria
S9 <-> all temperature changes the equilibria that produced the heat
```

So the dependency order above is an **implementation and data-availability order**, not a causal order. The physics is a coupled system. A sequential "S1 then S2 then ..." code path would reproduce the DAG but not the feedbacks; it must be rejected as a model of S5-S9 (the loops are what make open and sealed behave differently, benchmark B6).

**Cross-cutting prerequisites that are NOT among the nine but gate benchmarks:**

| id | prerequisite | gates |
|---|---|---|
| X1 | mixing / hydrodynamics (stirring, pouring, powder wetting) | S1, S5, S7; benchmark B7 |
| X2 | product composition and impurities (commercial vinegar and baking-soda composition, additives, surface-active species that affect nucleation and foaming) -- `TO-BE-SOURCED` per product | S1, S7; every quantitative benchmark |
| X3 | units, uncertainty propagation, and a ledger that can say UNKNOWN (SmartChem already has `Quantity`/`Bucket.UNKNOWN`; a dynamical state would need the same discipline) | all |
| X4 | a verified stiff coupled ODE/PDE solver with a convergence study (benchmark B9) | S2-S9 |

### 2.4 Stage -> missing-capability summary

* **Blocked on #105 (per-atom formal charge / ionic identity):** S2, S3, S4 (strong); S1 (partial); S5 (indirect). #105 is **necessary for faithful ionic identity but not sufficient**: it does not supply a speciation solver, aqueous standard states, or an activity model.
* **Blocked on sourced thermodynamic/speciation data:** S1, S2, S3, S4, S5 (diffusivity, solubility), S6 (Henry), S7 (surface properties), S8 (vapor pressure), S9 (enthalpies, heat capacities). **No stage is data-free.**
* **Blocked on sourced kinetics:** S1 (dissolution rate), S4 (CO2 hydration/dehydration), S7 (nucleation/growth parameters), S9 (T-dependence of rates). S3's proton transfer is *assumed* fast; that assumption is a test target, not a given.
* **Blocked on fluid/gas physics:** S5, S6, S7, S8, S9, plus X1 for S1. A well-mixed 0-D model removes the *spatial* part but still needs S6 (as an equilibrium partition) and S8.
* **Smallest checkable slice (MFS):** a well-mixed, isothermal, **equilibrium end-state** model of S1-S4 + equilibrium S6 + closed or open S8. It cannot show time-dependent fizzing. It *can* predict final pH, the carbon partition among HCO3-/CO3(2-)/CO2(aq)/CO2(g), and equilibrium headspace pressure, and each of those is checkable against independent solvers and measurements (section 5). Build and falsify this slice before any rate, transport, or bubble model.

---

## 3. BANNED ANTI-PATTERN

> **FORBIDDEN: a single global rule of the form `if vinegar touches baking soda: spawn bubbles`.**
>
> That is a **game mechanic, not chemistry.** It is not allowed anywhere in the 3.0 flagship, in any default, in any "demo mode", in any renderer hook, or in any test fixture presented as a prediction.
>
> **No artificial bubble may be presented as a scientifically derived prediction.** A bubble that appears on screen must be traceable to a canonical-state quantity (a validated stage-7 bubble population, or a stage-6 supersaturation/transfer flux) through a documented function, or it must be labeled **`ILLUSTRATION ONLY -- not a model output`** in the artifact itself.

Why the rule is not merely distasteful but **wrong as a function** (this is a proof sketch, not an experiment, so its ledger label in section 6 is by-argument):

1. A rule whose trigger is *contact* is independent of amounts. The physical gas output depends on limiting reagent (B5): it must scale with the smaller of the acid and bicarbonate amounts. A contact-only trigger cannot satisfy that, so it fails B5 by construction.
2. It is independent of headspace. The physical outcome depends on whether the container is open or sealed (B6). Fails B6 by construction.
3. It is independent of temperature (B8) and of mixing/dissolution conditions (B7) in the way the physics requires.
4. It fires identically with the renderer on or off only if the bubbles are not state -- if they are state, it fails B10 (section 4); if they are not state, they are an illustration and must be labeled as such.

Allowed: a *visualization layer* that reads canonical state read-only (B10 enforces that it cannot write back). Forbidden: any bubble source that is not a function of canonical chemical/physical state.

---

## 4. DISCRIMINATING BENCHMARKS

Each benchmark is designed so that a **correct model** and a **cartoon** give different answers. All quantitative reference values are `TO-BE-SOURCED`; the expected outcomes below are *directional/qualitative predictions of the physics* (ledger label CONJECTURED until a model run and an independent measurement exist). Tolerances must be **pre-registered before the model is run** (`TO-BE-SET-BEFORE-RUN`), to prevent tuning to the answer.

### 4.0 Always-on invariants (checked at every output step of every benchmark)

These are not benchmarks; they are the floor. A violation is an implementation failure regardless of how good the picture looks.

* atom conservation per element, with exported (vented) matter counted explicitly;
* **carbon balance:** total carbon = acetate/acetic-acid carbon + (HCO3- + CO3(2-) + CO2(aq) + solid NaHCO3) + CO2(g) in headspace and bubbles + CO2(g) exported through a vent;
* sodium balance; total acetate+acetic acid balance;
* **solution charge neutrality** (to numerical tolerance);
* closed-system total mass exactly conserved; open-system mass change equals exported mass;
* energy balance closes within the stated heat-transfer model;
* no negative amounts; no quantity reported without a unit and an uncertainty or an explicit UNKNOWN.

### 4.1 The benchmark table

| id | setup | what it discriminates | EXPECTED discriminating outcome | quantitative reference |
|---|---|---|---|---|
| B1 | **Water only** (no acid, no bicarbonate), same container, same headspace | a model that fizzes whenever liquid is present or on "any addition event" | no net reaction; no net CO2 evolution beyond equilibration of dissolved atmospheric gases; the speciation is just water's own. **Any spawned bubble here FAILS the model.** | pure-water pH and dissolved-gas equilibrium at (T, P): `TO-BE-SOURCED` (NIST/IUPAC reference data) |
| B2 | **Bicarbonate, no added acid** (dissolve NaHCO3 in water) | a model that equates "bicarbonate present" with "gas evolves" | dissolution up to a finite solubility; a weakly basic, buffered solution; **no sustained vigorous gas evolution at the starting temperature**. Slow CO2 loss and thermal decomposition at elevated T are real physics and must appear only where the temperature perturbation (B8) puts them. | solubility(T), solution pH vs concentration: `TO-BE-SOURCED` |
| B3 | **Acid, no bicarbonate** (vinegar alone) | a model that equates "acid present" with "gas evolves" | no CO2 evolution (there is no carbonate carbon); partial dissociation only; acidic pH. | acetic-acid Ka(T), pH vs concentration: `TO-BE-SOURCED` |
| B4 | **Mixed solution, sufficient reactants** | the core claim: gas arises *from the coupled equilibria and transfer*, not from a switch | CO2 evolves; solution pH rises toward the buffered acetate/bicarbonate region; the gas amount is **bounded by the carbon and proton budget** (4.0 invariants) and is **less than the naive stoichiometric CO2** whenever a fraction remains dissolved or the headspace is closed | end-state pH, gas moles, pressure: `TO-BE-SOURCED` independent measurement + Reaktoro/Cantera cross-check (section 5) |
| B5 | **Limiting acid vs limiting bicarbonate** (two runs, otherwise equal) | contact-only triggers (section 3), and any model that ignores stoichiometric limits | gas moles track the *limiting* reagent (never exceed the carbon/proton budget). **Acid-limiting:** residual bicarbonate remains, final solution is at the *higher-pH* end. **Bicarbonate-limiting:** residual acetic acid remains, the solution is an acetic acid/acetate buffer at the *lower-pH* end. The two final pH values must be **ordered**, and the ordering is a falsifiable prediction. | pH and gas moles for each case: `TO-BE-SOURCED` |
| B6 | **Open (vented) vs sealed headspace** (equal contents) | models without a pressure/partition feedback (S8 -> S6 -> S4) | open: CO2 leaves, mass of the contents decreases by exported CO2, reaction proceeds further. Sealed: pressure rises, **more CO2 stays dissolved**, the extent of reaction is lower than the open case, closed-system mass is exactly conserved. A model that gives identical results for open and sealed has no S8 feedback and FAILS. *This is a modeling benchmark only; the model is never a safety assessment, and burst/rupture/leak behavior is out of scope and must be reported UNMODELED, not predicted.* | equilibrium pressure and dissolved/gas CO2 partition: `TO-BE-SOURCED` (Henry constant, vessel and headspace volumes, T, P) |
| B7 | **Mixing and dissolution conditions:** powder vs coarse grains vs pre-dissolved solution; stirred vs unstirred; addition order | cartoons with one hard-coded rate and equilibrium models that wrongly depend on path | the **time course** changes strongly with surface area and mixing; the **final equilibrium state depends only on the total contents, T, and P** (a state function), except where a metastable supersaturated or undissolved-solid state is *explicitly* modeled and flagged. A model whose end state depends on the mixing path without a declared metastable mechanism FAILS; a model whose rate ignores particle size and mixing FAILS. | dissolution-rate vs particle-size data: `TO-BE-SOURCED` |
| B8 | **Temperature perturbation** (same contents, changed T within the data's validity window) | models with temperature-independent behavior | every T-dependent quantity moves in its known direction: gas solubility falls as T rises (more CO2 to the headspace at equal contents), acid-base constants shift per their sourced enthalpies, and the sign of the thermal effect of mixing is a prediction derived from sourced aqueous enthalpies. **The commonly reported cooling on mixing is a hypothesis to be checked against sourced calorimetry; this plan does not assert its magnitude.** If the model's sign of ΔT disagrees with calorimetric measurement beyond the combined uncertainty, the energy model is REFUTED. | heat of mixing, ΔT: `TO-BE-SOURCED` (calorimetry). Beyond the data's window the model must return `UNKNOWN`/`PREDICTED`, never a confident number (matches `NEAR_REFERENCE_K` discipline). |
| B9 | **Grid-resolution (and time-step) change** | numerical artifacts presented as physics | the canonical outputs (final pH, gas moles, pressure, and, if modeled, bubble-size statistics) **converge** under refinement at a documented order, with a reported discretization-error estimate. A behavior that appears or vanishes when the grid changes is a numerical artifact and must not be reported. Convergence evidence is required *before* any claim for S5-S7. | convergence order and tolerance: `TO-BE-SET-BEFORE-RUN` |
| B10 | **Renderer disabled (NON-NEGOTIABLE)** | any coupling from visualization back into chemistry | see 4.2 | none: this is a bit-level or tolerance-level identity test |

### 4.2 B10 -- the renderer-disabled test (NON-NEGOTIABLE)

**Requirement:** removing the visual bubbles (or the entire renderer) must have **ZERO influence on the canonical chemical evolution.** The canonical state is the sole source of truth; the renderer is a pure, read-only function of it.

**Architecture rule that makes the test meaningful:**

* *Canonical state* `C(t)`: species amounts by phase, temperature, pressure, volumes, and (only if a validated stage-7 model exists) the physical bubble population. It is serialized by one deterministic function.
* *Renderer* `R(C(t)) -> pixels/scene`: no write path into `C`; no shared mutable object with the solver; **its own pseudo-random stream** (the solver's stream must not be consumed by rendering); no timing feedback (frame rate must not set the solver's time step).
* A physical bubble population in `C` is a *chemistry/physics* object (stage 7). Whether it is *drawn* is a renderer decision. The renderer toggle must never delete, create, or alter bubbles in `C`.

**Test procedure (run in CI for every release that contains the flagship):**

1. Fix inputs, seeds, grid, and platform. Run the simulation with `render=ON`, recording the canonical-state serialization `S_on(t_k)` at a pre-declared checkpoint set `{t_k}` (including `t_0` and the final time).
2. Run again with `render=OFF` (renderer not constructed at all, not merely hidden), recording `S_off(t_k)`.
3. **Primary criterion (if the solver is deterministic): `S_on(t_k) == S_off(t_k)` byte-for-byte at every checkpoint**, compared by canonical digest (SmartChem's `Digestible` / `canonical_digest` machinery exists for exactly this kind of content-identity check).
4. **Fallback criterion (if parallel/GPU nondeterminism is unavoidable):** first measure the solver's *intrinsic* run-to-run spread by running `render=ON` twice (`D_on_on`). Then require the on-vs-off canonical-state difference `D_on_off` to be **no larger than `D_on_on`** at every checkpoint and every canonical variable, with the tolerance pre-registered. The tolerance is never loosened after seeing a failure.
5. **Variation controls:** repeat with the renderer at extreme settings (zero visual bubbles; 100x visual bubble count; a different frame rate; a different resolution). Canonical digests must be identical across all of them.
6. **Mutation test (the test must be able to FAIL):** deliberately inject a leak -- for example, let the renderer write a "visible bubble count" into a solver input, or consume a draw from the solver's random stream. The B10 test **must detect** this. A B10 test that passes with a known-injected leak is vacuous and is itself a defect. (This is the "a check derived from its own subject passes the mutant it should catch" lesson.)
7. **Artifact labeling test:** every rendered frame/export must carry a provenance tag saying whether bubbles are `DERIVED FROM CANONICAL STATE (validated stage-7 model)` or `ILLUSTRATION ONLY`. A frame with neither tag is a defect.

---

## 5. INDEPENDENT VALIDATION INSTRUMENTS

### 5.1 The epistemic distinction (load-bearing)

* **Verification** answers "did we solve our equations right?" A benchmark generated from the **same equations and the same data** (even by a different code) is **implementation verification**. It can catch coding errors. It cannot show the equations describe nature.
* **Validation** answers "do the equations describe the physical system?" That requires **independent measurements** of the real system. A match with an independent measurement is the **stronger physical-validation claim**.
* **Shared-provenance warning:** two independent *codes* that read the **same thermodynamic database** share their data errors. Their agreement counts once for the data. For every cross-check, record which database and which activity model each instrument used before counting agreement as independent. Agreement of two tools on a common database is verification of the solver, not corroboration of the constants.

The ladder, weakest to strongest: (V0) SmartChem's own invariants (4.0) -> (V1) code-to-code agreement with an independent solver on the *same* declared constants and model (verification) -> (V2) code-to-code with an independent database/model (partial corroboration of the data) -> (V3) agreement with **independent experimental measurements** (validation).

### 5.2 Named independent instruments

I did **not** fetch either project's documentation in this session; the scope statements below are what is to be *confirmed against the official docs* before reliance. Mark: UNVERIFIED against docs.

| instrument | what it would validate | what it would NOT validate | pre-use checks |
|---|---|---|---|
| **Cantera** (official documentation) | 0-D reactor thermochemistry and kinetics: reactor energy and mass balances, ideal-gas thermodynamics for the headspace (S8, equilibrium S6 gas side), and kinetics integration *where a reaction mechanism with sourced rate parameters is supplied* (S9, S4 rate if sourced) | it does not by itself supply the missing aqueous data; whether its electrolyte-solution phase models adequately cover the acetic acid/bicarbonate/CO2 system is `TO-BE-CHECKED` in its docs; it does not model bubbles or dissolution transport | record version, phase model, and database; state which solved equations are identical to SmartChem's (-> verification) and which are not (-> partial corroboration) |
| **Reaktoro** (official documentation) | aqueous speciation and chemical equilibrium including gas-aqueous partition with nonideal activity models (S2, S3, S4, equilibrium S6, closed/open S8): the MFS of section 2.4 | not rates (S4 kinetics, S1 dissolution, S7), not transport, not bubble physics, not heat transfer | record version, activity model, and thermodynamic database (and that database's own sources) so shared provenance with Cantera or with SmartChem's data can be detected |

Neither tool is an experiment. Both are *calculators over somebody's constants*. They earn the V1/V2 rungs, not V3.

### 5.3 External experimental datasets to source (ALL `TO-BE-SOURCED`)

Nothing below is filled in. Each dataset is accepted only with the **required metadata**: temperature `T`, concentrations (with basis: mol/L vs mol/kg vs % w/w vs % w/v), total and partial pressures, units, headspace/vessel volumes, material composition and purity (manufacturer lot or assay), method, and stated **uncertainty with its type** (one sigma / expanded / range).

| dataset kind | feeds | kind of source to look for | required metadata |
|---|---|---|---|
| NaHCO3 solubility vs T (and vs added salts) | S1, B2 | critical evaluation in IUPAC-NIST solubility compilations; CRC-class handbook with primary citations | T, g or mol per kg solvent, solid form, equilibration method, uncertainty |
| Acetic acid Ka vs T and ionic strength | S3, B3 | NIST critically selected stability constants; IUPAC pKa compilations | T, ionic strength and medium, method, uncertainty |
| Carbonic-system K1, K2 vs T and salinity; CO2 hydration/dehydration rate constants | S4 | NIST/IUPAC critical compilations; oceanographic carbonate-system literature; kinetics literature for CO2 hydration | T, ionic strength, scale/convention (concentration vs activity constants), uncertainty |
| CO2 solubility (Henry constant) vs T and salting-out | S6, B6, B8 | IUPAC-NIST Solubility Data Series for CO2 in water; a critical Henry's-law compilation | T, P, salt content, uncertainty |
| CO2 diffusivity in water vs T | S5, S7 | critical evaluations / careful experiments | T, method, uncertainty |
| Aqueous standard-state ΔfH, S, ΔG, Cp of the ions and neutrals | S1-S4, S9 | CODATA Key Values, NIST WebBook, NBS/NIST tables | species and standard-state convention (this is where aqueous vs pure-liquid records must not be confused), uncertainty |
| Calorimetry of the mixture (heat of mixing / ΔT) | S9, B8 | peer-reviewed calorimetry or teaching-lab measurements with stated uncertainty | T0, amounts, concentrations, heat-capacity of the calorimeter, uncertainty |
| End-state pH of defined mixtures | B4, B5 | peer-reviewed measurements with calibrated pH meters | calibration buffers, T, ionic strength, electrode type, uncertainty |
| Pressure-vs-time in a sealed vessel (and mass-loss-vs-time in an open vessel) | B4, B6 | instrumented-vessel experiments in peer-reviewed or institutional reports | vessel and headspace volume, T, amounts, particle size, mixing, sensor accuracy, uncertainty |
| Dissolution rate vs particle size and stirring | S1, B7 | pharmaceutical/chemical-engineering dissolution studies of NaHCO3 | particle-size distribution, stirring rate, T, uncertainty |
| Bubble nucleation/growth/rise in CO2-supersaturated aqueous liquids | S7 | carbonated-beverage bubble-nucleation and growth literature (nucleation-site statistics); fluid-mechanics measurements | liquid composition, surface treatment and substrate, supersaturation, T, optical resolution, uncertainty |
| Composition of the actual products used (vinegar acetic-acid content; baking-soda purity and additives) | X2, every quantitative benchmark | manufacturer specification plus an independent titration assay | lot, method, uncertainty |

---

## 6. CLAIM LEDGER

Labels: **DISCLOSED** = stated by the repository or an established textbook relation, cited here but not re-derived. **CORROBORATED** = confirmed by two or more *independent* routes. **OBSERVED** = seen directly in this session by reading source or running a probe (single route, session-local). **CONJECTURED** = reasoned, not yet tested. **UNVERIFIED** = asserted from memory or a source not inspected, to be checked before reliance. **REFUTED** = shown false (by test or by proof).

| # | claim | label | basis / boundary |
|---|---|---|---|
| L1 | The net equation conserves atoms and net charge as a SmartChem `ExperimentStep` | OBSERVED | probe 1 built the step (covalent placeholder skeletons for NaHCO3 and CH3COONa) |
| L2 | SmartChem returns UNKNOWN for feasibility, equilibrium extent, and kinetics of the net equation | OBSERVED | probe 1 output; the reasons are missing records (`C2H3NaO2`, `CHNaO3`) and no sourced `(Ea, A)` |
| L3 | `Molecule` carries one integer charge, no per-atom formal charge | OBSERVED + DISCLOSED | `category.py` ~line 762; `V1_5_RELEASE_PROGRAM.md` section 5 (#105). Same repo and author, so this is **not** two independent routes; it stays OBSERVED, not CORROBORATED |
| L4 | Whole-species ions (Na+, HCO3-) can be held as net-charge bookkeeping in a conserving step | OBSERVED | probe 2. Bookkeeping only; no solvation, activity, or speciation |
| L5 | No record for NaHCO3 / CH3COONa / aqueous ions exists in the seed or extended thermo tables | OBSERVED | `for_formula` -> `None`; grep found no `Na+`/`HCO3` record |
| L6 | M2 would still decline a conversion for this net reaction even with data (Δn != 0) | DISCLOSED (docstring) | `equilibrium.py` module docstring; **not exercised with injected data** -> UNVERIFIED by run |
| L7 | No Henry's-law, mass-transfer, bubble, headspace, activity, or speciation implementation exists in `smartchem/` | OBSERVED | grep for the keywords (hits only in one docstring and research docs). A negative search is evidence, not proof |
| L8 | No energy-balance or heat-transfer model exists in `smartchem/` | UNVERIFIED | not seen in the modules read; a full-repo search for energy-balance code was **not** done |
| L9 | A contact-triggered "spawn bubbles" rule cannot satisfy B5 (amount scaling) or B6 (open/sealed) | REFUTED (the hypothesis that such a rule can pass the suite) | by argument: its output is independent of amounts and headspace. A proof sketch, not an experiment |
| L10 | The physical system is a coupled, feedback-bearing system (S7 -> S6, S8 -> S6, S8 -> S4, S9 <-> all) | DISCLOSED | standard physical chemistry; the specific coupling strengths are UNKNOWN until modeled |
| L11 | Acetic acid is a stronger acid than the CO2(aq)/H2CO3 pair, so the aqueous step is net-favorable but not by itself "complete" | CONJECTURED | textbook ordering; the numerical K and the extent are `TO-BE-SOURCED` and must come from the sourced constants, not from this document |
| L12 | Gas actually released is less than the naive stoichiometric CO2 when headspace is closed or CO2 stays dissolved | CONJECTURED | follows from L10/Henry partition; to be tested by B4/B6 against measurements |
| L13 | CO2 hydration/dehydration is slower than pure proton transfer and must not be assumed instantaneous | CONJECTURED | qualitative textbook expectation; the timescale is `TO-BE-SOURCED` |
| L14 | The commonly reported cooling on mixing is real and derivable from sourced aqueous enthalpies | UNVERIFIED | reported observation; derivation and magnitude `TO-BE-SOURCED` (B8) |
| L15 | Cantera and Reaktoro cover the scopes named in 5.2 | UNVERIFIED | docs not fetched this session; confirm before relying |
| L16 | Agreement between two codes using the same database corroborates the constants | REFUTED (as a general claim) | shared provenance: agreement counts once for the data (section 5.1) |
| L17 | A well-mixed isothermal equilibrium end-state slice (S1-S4 + equilibrium S6 + S8) is the smallest independently checkable slice | CONJECTURED | design judgment; the probe below is designed to attack it |
| L18 | The renderer-disabled test (B10) can actually fail | UNVERIFIED | requires the injected-leak mutation (4.2 step 6) to be demonstrated when the harness exists |

### 6.1 The single next best FALSIFYING probe

**Probe P1 -- the equilibrium end-state slice, against an independent solver AND one independent measurement, pre-registered.**

*Claim under attack:* L17 (and by extension the design in section 2.4) -- that a well-mixed isothermal equilibrium model of S1-S4 + equilibrium S6 + S8, run on sourced constants, predicts the end state of B5 (both limiting cases) and B6 (open vs sealed), independent of any rate or bubble model.

*Why this one:* it is the cheapest check that can kill the plan *before* anything is built. If equilibrium alone (with sourced constants) cannot reproduce a measured end state, then missing ion pairing, activity effects, or an omitted species is a first-order problem and the entire staged plan is mis-ordered. If it can, S1-S4/S6/S8 are de-risked and the remaining risk is concentrated in rates, transport, and bubbles.

*Procedure (not run; Reaktoro is not installed and nothing was installed for this document):*

1. Pre-register, before computing: the exact amounts and vessel/headspace volumes for B5-acid-limiting, B5-bicarbonate-limiting, B6-open, B6-sealed; T and P; the activity model; the database; and the pass tolerance (combined solver + measurement uncertainty). All `TO-BE-SET-BEFORE-RUN`.
2. Compute the four end states with Reaktoro (verification rung V1/V2). Record database provenance (section 5.1).
3. Predict, in writing, the *ordering* claims of B5 (final pH ordered across the two limiting cases) and B6 (sealed has more dissolved CO2 and lower extent than open).
4. Compare with one independent measured end-state (pH and either gas moles or pressure) from the datasets in 5.3, with its uncertainty.
5. **Falsified if:** the ordering predicted in step 3 is violated by the measurement; **or** the model-minus-measurement difference exceeds the pre-registered combined uncertainty. In either case the SmartChem plan's slice S1-S4/S6/S8 must be revised (add species, ion pairs, or an activity model) before any dynamic stage is attempted.

*Dependency of P1 on the orchestrator:* an installed Reaktoro (separate environment, not the committed baseline; the repo's rule is that optional dev-only oracles never change a verdict) and a sourced measurement. Neither is available inside this task.

---

## Appendix A -- the two probes that were actually run (OBSERVED, session-local)

Run with `.venv/bin/python` from the repo root, read-only. Scripts were scratch files, **not committed**; if a future round wants these as MEASURED claims they must be promoted to a committed `experiments/` harness (repo rule).

**Probe 1 -- the net equation through the M1/M2/L1 instruments.** Species: acetic acid and sodium bicarbonate from `smartchem.data.reagents.COMMODITY_REAGENTS`; sodium acetate built as the covalent skeleton `CH3-C(=O)-O-Na`; CO2 and H2O built from explicit skeletons; `ExperimentStep(schema_version=STEP_SCHEMA, target=co2, reactants=(acetic_acid, sodium_bicarbonate), products=(sodium_acetate, h2o, co2), reagents=(), envelope=ConditionEnvelope.unknown())`.

Observed: step built (conserves). `feasibility_of_step` -> `FeasibilityDirection.UNKNOWN`. `equilibrium_of_step` -> `EquilibriumExtent.UNKNOWN`, `reason`: "no sourced thermodynamic data for C2H3NaO2, CHNaO3; ΔG cannot be computed". `kinetics_of_step` -> `RateRegime.UNKNOWN`, `reason`: "no sourced Arrhenius (Ea, A) for this reaction ... a rate is NEVER guessed from bond energies (W3)", `missing=('C2H4O2 + CHNaO3 -> C2H3NaO2 + H2O + CO2',)`, `temperature_k=298.15`.

Thermo-table lookup (`smartchem.data.thermo_extended.extended_thermo().for_formula`): `C2H4O2` -> acetic acid, **liquid**; `CO2` -> gas; `H2O` -> liquid; `CHNaO3`, `C2H3NaO2`, `CNa2O3` -> `None`.

**Probe 2 -- whole-species ions as net-charge bookkeeping.** `Molecule(atoms=("Na",), charge=1)` and `Molecule(atoms=("O","C","O","O","H"), bonds=frozenset({Bond(0,1), Bond(1,2,2), Bond(1,3), Bond(3,4)}), charge=-1)`; step `NaHCO3 -> Na+ + HCO3-` **built** (atoms and net charge conserve). Interpretation boundary: this proves only that the conservation ledger accepts net-charged species. It does not show the charge site is represented (it is not), and it is not speciation.

## Appendix B -- everything marked TO-BE-SOURCED / TO-BE-SET / TO-BE-CHECKED (index)

* **Product composition:** vinegar acetic-acid content; baking-soda purity and additives (X2, 5.3).
* **Thermodynamic and speciation constants:** NaHCO3 solubility(T); acetic acid Ka(T); carbonic K1(T), K2(T); aqueous standard-state ΔfH/S/ΔG/Cp of ions and neutrals; Henry constant(T, salinity); CO2 diffusivity; vapor pressure of water; surface tension, density, viscosity.
* **Kinetics and transport parameters:** CO2 hydration/dehydration rates; dissolution rate vs particle size and stirring; nucleation/growth parameters; gas-liquid transfer coefficients.
* **Measurements:** calorimetry/heat of mixing; end-state pH; sealed-vessel pressure-vs-time and open-vessel mass-loss-vs-time; bubble nucleation/growth/rise data.
* **Tolerances and registrations:** every pass/fail tolerance in B1-B10 and P1 is `TO-BE-SET-BEFORE-RUN`.
* **Tool facts:** Cantera and Reaktoro scope, versions, activity models, and databases are `TO-BE-CHECKED` against their official documentation.
