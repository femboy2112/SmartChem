# MANIFEST — what is in this repository and why

A map of the code, written so someone (including a future session) can find the load-bearing
parts without reading the whole tree. For *what the system claims and what was measured*, read
`README.md`; for the argument, `THE_DIFFERENCE.md`; for the categorical structure,
`THE_ORBITAL.md`.

## The one-paragraph version

SmartChem is a **compositional layer above quantum chemistry**, not a replacement for it.
Chemical configurations form a commutative multiset of structured species, and reactions
are validated sequential histories that cannot violate atom or net-charge conservation.
They form a path category under sequential composition. The object product does **not**
currently extend to a symmetric monoidal product of reaction histories:
``scheduled_product`` means a deterministic left-first schedule; the deprecated
``tensor`` compatibility name warns because it is not a parallel tensor. Energy comes from
a pluggable oracle whose coverage and measured
accuracy depend on method, species and conditions.

## Layers

```
Layer 3  Search & verification    pathway.py · store.py · bench.py
Layer 3½ Compiled vertical seam   contracts.py · program.py · typed ledger bindings
                                  water_wave_domain.py · water_wave.py
                                  water_wave_continuous_domain.py · water_wave_continuous.py
                                  water_wave_continuous_verifier.py
                                  human_isotope_domain.py · human_isotope.py
                                  human_survival_domain.py · human_survival.py
Layer 2¾ Open structure           open_diagram.py        (syntax/coherence only)
Layer 2⅝ Electrical model         resistive_dc_schema.py · circuit.py
                                  resistive_dc_verifier.py · resistive_dc.py
                                  rlc_ac_schema.py · rlc_ac_circuit.py
                                  rlc_ac_verifier.py · rlc_ac.py
                                  (finite ideal DC and fixed-frequency passive RLC)
Layer 2½ Domain instances          cell.py                (chemistry meets circuit)
Layer 2  Sequential core          category.py · thermo.py
Layer 1  Energy oracle            oracle/base.py + heuristic.py + pyscf_oracle.py
                                  oracle/caching.py    (wraps any oracle tier)
                                  oracle/persistent.py (and outlives the process)
Layer 1' Structure                geometry.py            (seed → relax → curvature check)
Layer 0  Data                     atoms.py · data/reference.py · data/basis_tight_d.py
```

Nothing in Layer 2 or 3 knows which oracle it is talking to. That is the whole design.

## Modules, in dependency order

| File | Lines | What it is |
|---|---:|---|
| `smartchem/atoms.py` | 168 | A limited, read-only periodic-data table (ionization energies, affinities and radii) retained from the original build. Coverage, units and provenance must be checked before extending it. |
| `smartchem/data/reference.py` | 526 | Curated comparison data: intended diatomic D₀ rows, band gaps and geometries, plus selected 0 K formation enthalpies used to derive polyatomic references. Compact source labels do not prove every D₀/D₂₉₈ convention, and uncertainty fields are curation scales rather than one calibrated coverage model. Balanced reaction helpers validate stoichiometry; these rows are not universal ground truth. |
| `smartchem/data/basis_tight_d.py` | 1114 | Read-only tight-d basis augmentation for second-row elements. Generated data, not hand-written. |
| `smartchem/category.py` | 1092 | **The load-bearing layer.** `Molecule` (atoms + bond topology + charge + opaque internal state), `Config` (multiset of molecules), and `Reaction` (validated sequential morphism history). It provides category composition and identities, a commutative object product, and a left-first `scheduled_product`; the latter is not a parallel tensor. Canonicalisation is by symbol class, refined by Weisfeiler-Leman colour when that is not enough. Structural predicates include `is_bond_order_conserving`, `is_isodesmic`, and stoichiometric `is_regenerated` (`is_catalytic` is a compatibility alias, not a proof of catalysis). |
| `smartchem/open_diagram.py` | current | A separate finite topology-only kernel with ordered electrical interfaces, two-terminal component slots, exact terminal/junction ownership, a public ID-free structural-edge view, total boundary gluing and disjoint-union tensor, identity/braid, and an exact alpha-invariant observer with named candidate-budget refusal. It contains no resistance, equation, solver, evidence, execution authority, or general multiphysics semantics. |
| `smartchem/structure_ir.py` | current | A versioned representation of successful S0 quotient observations, resource-bounded composition/tensor/identity/braid, and a separate presentation-specific adapter witness. Every plan records `OBSERVED`, `REFUSED`, or `NOT_APPLICABLE`, and execution rederives the attachment before dispatch. The quotient value does not own model parameters or infer declaration-index transport; it is not a universal SmartChem category, semantic functor, or physics claim. |
| `smartchem/resistive_dc_schema.py`, `smartchem/circuit.py`, `smartchem/resistive_dc.py`, `smartchem/resistive_dc_verifier.py` | finite ideal-resistor E1 | Shared immutable nominal records, exact rational passive boundary relations, explicit model-index to structural-edge binding, one topology-generic sparse DC MNA path, complete node/branch/source/diagnostic records, and a compiled runtime whose direct verifier imports neither production circuit nor executor code. The verifier independently eliminates the exact relation and recomputes canonical content, inventory, Ohm law, KCL, source constraint, power, passivity, and every retained diagnostic. Recursive class-identity and post-engine approval-identity gates refuse forged records and approved-input substitution. Scope is finite positive ideal resistors under one declared drive/reference only—not a device, AC/RLC, thermal, nonlinear, distributed, safety, or port-Hamiltonian model. |
| `smartchem/rlc_ac_schema.py`, `smartchem/rlc_ac_circuit.py`, `smartchem/rlc_ac.py`, `smartchem/rlc_ac_verifier.py` | positive-frequency passive-RLC E2 | Immutable exact-`Q(i)` and phasor records, explicit model-index to structural-edge binding, exact driven-rank preflight, one topology-generic normalized sparse complex-MNA path, complete node/branch/source/power/diagnostic records, and a compiled runtime whose direct verifier imports neither production circuit nor executor code. The verifier independently derives graph content, exact relation/rank, component laws, KCL, source constraint, source-inclusive complex power, passivity, retained MNA state, and output inventory. Exact lossless singular resonance refuses before an engine call and without regularization. Scope is finite ideal R/L/C networks at one declared positive frequency—not a device, transient, nonlinear/active, harmonics, tolerance, thermal, distributed, safety, or port-Hamiltonian model. |
| `smartchem/contracts.py`, `smartchem/program.py`, `smartchem/runtime_registry.py`, `smartchem/ledger.py` | current compiler seam | Immutable source/request/plan/approval/run/certificate records; a closed exact-subject/output/preflight/runner registry; exact `PhysicalIR` member, ID, graph, evidence, source/target, model, transform, contract, and StructureIR-attachment ownership; dispatch-capability-guarded runners; full shipped-source approval identity; a pre-backend execution-admission snapshot rechecked after successful and exceptional callbacks and before certification; write-once run-owned journals; typed observable payload schemas; typed shepherd bindings/validity obligations; and the first plan-visible/runtime-model-bound Class-A `reaction-residue-v1` transform. It is not yet a general language, optimizer, planner, hostile-process security boundary, or multiphysics runtime. |
| `smartchem/evidence/*` | decoupled probe-evidence auditor | A standalone sibling of the compiler that reuses `contracts.py` primitives to audit the epistemic contract around an *external* project's numerical probes — teeth, provenance independence, source locks, scope, and tier boundary — certifying or refusing without ever entering the closed executor registry or raising a declared evidence status. Every certificate prints a hygiene-not-physics banner. The integration contract is the versioned JSON manifest schema (`manifest.schema.json`, shipped in the wheel); a consumer emits a conformant manifest and runs `smartchem-verify-probes` (or `python -m smartchem.evidence verify-probes`), importing nothing else from SmartChem. The subpackage imports only the standard library, so the auditor never pulls in the numeric stack. Scope is epistemic hygiene, not physics: it never certifies that a probe's science is correct. See `smartchem/evidence/README.md`. |
| `smartchem/water_wave_domain.py`, `smartchem/water_wave.py` | current structural cross-domain slice | Pure typed SI prescribed-profile characteristic diagnostics plus the analogue-only compiler/runtime bridge. It retains all profile points/crossings and refuses unsupported regimes/claims. Its bundled run is `STRUCTURAL_TOY`, not a measured flume, free-surface evolution, scattering calculation, or literal-gravity result. |
| `smartchem/water_wave_validation_domain.py`, `smartchem/water_wave_validation.py` | manufactured water preflight v2 | Finite-section nominal discharge/Bernoulli compatibility, wavelength/depth and gravity/capillarity screens, typed sign-aware branch/orientation, and uncertainty-resolved adjacent-sample brackets. It deliberately does not establish steady momentum/regularity, a continuous stationary background, measured validation, or a physical horizon. |
| `smartchem/water_wave_continuous_domain.py`, `smartchem/water_wave_continuous.py`, `smartchem/water_wave_continuous_verifier.py` | manufactured continuous steady-water control | Typed constant-width subcritical, supercritical, and isolated regular-transcritical backgrounds; mandatory manufactured friction/source provenance; bounded branch-aware cell-centred energy-root reconstruction; complete 32/64/128-mesh fields; binary64 roundings of a separate 60-digit Decimal reference evaluation; continuity/momentum residuals; numerator and first-derivative critical compatibility; metadata-only uncertainty retention; all-mesh magnitude gates; conservative convergence over both refinement pairs; a solver-independent direct payload verifier; and an exact attached finite-v2 comparison. The default mismatch is quantitatively friction-dominated, while non-dominant cases are explicitly unattributed. This remains `ANALOGUE/STRUCTURAL_TOY`: it is not a finite-volume/general Saint-Venant solver, continuum theorem, propagated uncertainty analysis, measured validation, scattering calculation, or literal gravity. |
| `smartchem/human_isotope_domain.py`, `smartchem/human_isotope.py` | current structural cross-scale slice | Pure typed target/population/granularity/assembly/exposure/toxicokinetic/LD50-LC50/calibration records plus the proxy-only identifiability runtime. Its two normalized family witnesses establish that one median endpoint does not identify dynamics. The run is `EXPERIMENTAL_PROXY/STRUCTURAL_TOY/UNVALIDATED`, not a human mortality, clinical, toxicological, causal, or regulatory model. |
| `smartchem/human_survival_domain.py`, `smartchem/human_survival.py` | synthetic D2b-S recovery slice | Content-addressed seeded-binomial independent synthetic interval cohorts, fixed TRAIN/HOLDOUT authority, a preselected Weibull proportional-hazards conditional-binomial likelihood, deterministic multistart/gradient diagnostics, conditional likelihood-curvature intervals, heldout binomial scores, and post-fit generator recovery. The intervals are not calibrated confidence coverage; the run is not empirical human calibration, biological validation, toxicology, LD50/LC50 evidence, causality, or transfer authority. |
| `smartchem/ising_lattice_gas_domain.py`, `smartchem/ising_lattice_gas.py` | exact finite cross-domain control | Exact-integer enumeration of all eight states on the fixed undirected three-cycle, the affine spin/occupancy and Hamiltonian map, both formal partition inventories, explicit zero-output-loss evidence, and a separately implemented direct runtime verifier. Its finite algebra is `ESTABLISHED`; its physical claim remains `ANALOGUE`, with no material, dynamics, thermodynamic-limit, or arbitrary-graph transfer. |
| `smartchem/geometry.py` | 650 | **Seed → relax → check local curvature.** VSEPR-based candidate coordinates from the bond graph, Cartesian L-BFGS relaxation on a supplied surface, and Eckart-projected harmonic analysis. The module imports no quantum backend, but relaxation and Hessian construction still require backend data in real use. |
| `smartchem/oracle/base.py` | 440 | The `EnergyOracle` protocol and `Estimate` — a value with an untyped reported scale and named signed correction sensitivities. Plus the guard that makes oracles decline what they cannot value. |
| `smartchem/oracle/heuristic.py` | 184 | A guarded wrapper around the frozen original algebraic model with transitive table/source fingerprinting. It remains measurable only in its selected standard/vacuum environment and declines nonstandard environments rather than exporting that calibration. |
| `smartchem/oracle/caching.py` | 122 | Prices each distinct species once per search. Measured 33.5× on a 45-reaction network; the saving rests entirely on canonicalising the cache key. |
| `smartchem/oracle/persistent.py` | 490 | A schema-versioned persistent species-energy cache with type-tagged calculation specs, model/code fingerprints, key-bound record checksums, optional refusal caching, locking/atomic replacement, and fail-safe handling of corrupt or future schemas. Integrity checks are not authentication. |
| `smartchem/oracle/pyscf_oracle.py` | 980 | HF / MP2 / CCSD(T), basis-set extrapolation and geometry research workflows. Public estimates currently cover enabled neutral atomic references and fixed neutral diatomic protocol rows with finite selected-set validation metadata. MP2/CCSD, optimized-geometry and polyatomic mechanics remain implemented-but-unvalidated paths and fail closed rather than inheriting another protocol's scale. |
| `smartchem/cell.py` | 414 | A structural two-half-reaction prototype. It validates matched typed negative-charge carrier inventories, obtains `n` from transferred charge quanta in that supplied factorisation, exposes `-dE/n` only as an energy-equivalent diagnostic, and fails closed for OCV until Gibbs/electrochemical context exists. The load and capacity helpers are algebraic models, not a coupled electrochemical dynamics model. |
| `smartchem/thermo.py` | 196 | Endpoint energy differences for an ideal, noninteracting-species adapter. Object energies add by model assumption and differences telescope under sequential composition; no morphism-level strong-monoidal claim is made. |
| `smartchem/store.py` | 257 | A lawful Store comonad, `(Env, Env → a)`, plus utilities that explicitly evaluate a supplied function at a finite set of positions. It provides no interpolation, caching, or free response surface. |
| `smartchem/pathway.py` | 427 | List-branching multi-step search with `bind` and a structured `Tally` carried alongside each route. It follows a Writer/List pattern, but float accumulation is not an exact monoid or monad over all Python values. |
| `smartchem/bench.py` | 227 | `python -m smartchem.bench` — per-species errors, conditional MAE, refusal counts, reference curation scales, and timing on a declared reference set or historical split. The historical test split was inspected during model selection, so it is not a pristine holdout; the report does not produce calibrated error bars. |
| `smartchem/legacy.py` | 343 | **Frozen.** The original engine, reduced to the path needed to reproduce its defects. Do not build on it; it exists so the regression tests have something to fail against. |

## The ideas worth knowing

**1. Objects carry bond topology, not just atom counts.**
If an object were a bag of atoms, every mass-conserving reaction would be an endomorphism —
`Na + Cl` and `NaCl` would be *the same object*, so the reaction between them could not be a
morphism at all. Giving objects structure is what makes `Na + Cl → NaCl` a genuine arrow.
It also turned out to be the geometry source: a bond graph is exactly what a coordinate
seeder consumes.

**2. `Estimate` is a source-aware numerical accumulator, not an exact algebra over floats.**
Values add, stated random uncertainties combine in quadrature under an independence
assumption, provenance combines as a set, and named systematic sensitivities add with sign.
Stable source IDs allow the same systematic term to cancel while unrelated terms cannot
cancel merely because their scalar totals happen to oppose. IEEE-754 addition and `hypot`
are not exactly associative, and no covariance model or calibration guarantee is implied.

**3. The core syntax is domain-neutral; its physical semantics are not automatic.**
Objects use labelled graphs over opaque symbols, an integer charge and opaque internal
state, while `Reaction` conserves symbol counts and total charge. That syntax can spell
toy radiation and circuit examples, but it has no typed boundary ports, Kirchhoff node
semantics, rates, fields or open-system composition. The separate `open_diagram` module now
supplies typed open wiring syntax and genuine structural gluing/tensor, without
reinterpreting `Reaction`. It still has no Kirchhoff or constitutive semantics: a future
domain layer and direct verifier must establish those rather than infer them from topology.

**4. The current cell prototype gets electron count from an explicit factorisation.**
The simplified structural example `Zn + 2 MnO2 → ZnO + Mn2O3` does not mention electrons —
they appear on both sides of the
composite and cancel as spectators. The endpoint `Config` therefore does not retain the
half-cell electron-transfer count. `Cell` accepts two half-reactions and validates equal
counts of explicit elementary negative-charge carriers; that supplied factorisation provides
`n`. It is not inferred from arbitrary `Reaction.path` data. The thermodynamic relation is
`ΔG = −nFE`. Because bundled oracles return an endpoint `ΔE` rather than `ΔG` under
electrochemical conditions, the implemented `−ΔE/n` value is only an energy-equivalent
voltage proxy. `open_circuit_voltage` deliberately raises. This lumped product is not a
complete commercial-AA discharge mechanism; real descriptions commonly resolve MnOOH and
phase/transport behavior.

**5. Separability makes spectators cancel in the current adapter.**
`thermo.configuration_energy` defines `E(A + B) = E(A) + E(B)` for isolated,
noninteracting species. Under that explicit assumption an unchanged species cancels from
an endpoint difference. This is not exact for species interacting in one vessel. Separately,
the zero-point-energy data admit a useful bond-multiset regression: a 10-parameter
bond model reproduces 16 species' Hessian-derived ZPEs to RMS 0.0113 eV — and the consequence
can be compared across structural reaction classes:

| class | conserves | mean \|ΔZPE\| |
|---|---|---|
| isodesmic | bond *types* | 0.0448 eV |
| order-only | bond *orders* | 0.0948 eV |
| creating | nothing | 0.3824 eV |

Monotone, 8.5× across the ladder in this dataset. That is empirical evidence for a shortcut,
not a functor law or a universal extensivity result. **Not yet actionable — the fit is
in-sample**, with four species the sole source of information about their own
bond types, so their zero residuals are construction rather than accuracy. A newly locked,
external validation set is required before this becomes policy (#32); the existing historical
test split is not a pristine holdout. The local-minimum diagnostic that caught H2O2 is
independent of this fit and must be evaluated separately.

**6. Getting a geometry is three problems, not one.**
Seed (combinatorics, no wavefunction) → relax (needs gradients) → check (needs a Hessian).
The latter two need backend data in real calculations. Candidate generation does not
establish a minimum: VSEPR proposes, while a projected Hessian supplies a numerical
local-minimum diagnostic under the harmonic approximation. The implementation currently
flags every negative projected mode because no numerical-noise cutoff is calibrated. Its
eigenvector can seed a repair attempt but does not prove which chemical structure will result.

## Tests

| File | Covers |
|---|---|
| `test_laws.py` | Sequential category laws and conservation, object-product laws, scheduled-product compatibility boundaries, and canonicalisation checks on generated finite examples. These are tests, not a formal proof or an SMC construction. |
| `test_open_diagram.py` | Smart-constructor ownership/refusal, public structural-edge projection, alpha/declaration invariance, multiplicity/self-loops, observer-budget refusal, and finite generated identity/associativity/interchange/symmetry/coherence controls for the separate topology kernel. These finite tests are not a formal proof or circuit validation. |
| `test_structure_ir.py` | Exact S0 quotient encode/decode, alpha/declaration invariance, finite symmetric-monoidal law controls, budget refusal, presentation-witness separation, unchanged E1/E2 identities/model bindings, plan-forgery refusal, and frozen registry/all-nine output contracts. These are finite executable controls, not a formal proof or a universal cross-domain category. |
| `test_circuit.py`, `test_resistive_dc_verifier.py`, `test_resistive_dc_program.py` | Exact relation composition/tensor controls; the single generic sparse-MNA path over analytic, bridge, and cycle cases; non-identity model reindexing; 64 seeded connected multigraph holdouts; production-disabled independent verification; coherent common-mode, retained-output, nominal-impostor, and approved-input-substitution forgeries; refusal, quarantine, lifecycle, and full-output gates. These finite controls do not prove arbitrary-network conditioning or device validity. |
| `test_rlc_ac_circuit.py`, `test_rlc_ac_verifier.py`, `test_rlc_ac_program.py` | Exact `Q(i)` relation/rank controls; analytic branch signs, parallel RC, damped resonance, nonidentity model reindexing, normalized sparse complex MNA, independently recomputed branch/KCL/source/power/passivity/output diagnostics, lifecycle and admission mutation gates, and exact zero-engine-call singular-resonance refusal. These finite controls do not prove arbitrary-network conditioning or physical-device validity. |
| `test_findings.py` | One named regression test per defect found in the original build |
| `test_functor.py` | Endpoint-difference telescoping, ideal isolated-species additivity, permitted reference-shift invariance, and spectator cancellation under that adapter. |
| `test_geometry.py` | Seeding, relaxation, Eckart projection, harmonic analysis, the mode-following repair |
| `test_reference.py` | The reference data itself — two-source, internal-algebra, and physical-sanity checks |
| `test_shortcuts.py` | The measured structural shortcuts and their controls |
| `test_domain_neutral.py` | Zero-atom/state tokens, labelled-graph syntax and typed carrier-inventory conservation over opaque labels. These checks do not supply radiative energetics, port semantics, KCL, dynamics or an open-network category. |
| `test_caching.py` | The species cache: that it saves, that it changes nothing, and where it decays |
| `test_persistent.py` | The disk cache, tested where it can hurt — ordered by how bad the failure would be, key discipline first and "it caches" last |
| `test_bench.py` | Conditional-MAE/refusal decision semantics, bond-order-aware benchmark inputs, and the exact 1 kcal/mol threshold |
| `test_optional_backends.py` | Core import/registry behavior when PySCF is unavailable or broken |
| `test_cell.py` | Half-reaction structure and carrier counting, the `−ΔE/n` diagnostic, resistive-load algebra and stoichiometric capacity. Electrochemical OCV is intentionally not implemented. |
| `test_network.py` | A **falsified** architectural prediction, kept: isolated-species energy additivity does not transfer to scalar impedance. One additive rule is 31.9× wrong on the tested parallel RC. Its power identity covers only uncoupled parallel branches at one prescribed voltage; it says nothing about radiative additivity or coupled fields. |
| `test_thermo.py`, `test_store.py`, `test_pathway.py`, `test_basis_policy.py` | Their respective modules |
| `test_program.py`, `test_p0_runtime_seam.py`, `test_optimizer.py`, `test_typed_ledger.py`, `test_water_wave_domain.py`, `test_water_wave_program.py`, `test_water_wave_validation_domain.py`, `test_water_wave_validation_program.py`, `test_water_wave_continuous_domain.py`, `test_water_wave_continuous_program.py`, `test_human_isotope_domain.py`, `test_human_isotope_program.py`, `test_human_survival_domain.py`, `test_human_survival_program.py`, `test_ising_lattice_gas_domain.py`, `test_ising_lattice_gas_program.py` | Approval/integrity/lifecycle boundaries, exact IR/evidence/model/transform/dispatch ownership, typed shepherd authority, Class-A transform multiplicity/workset/forgery/output preservation, branch/orientation algebra, finite and continuous manufactured water balance/regularity/convergence/comparison gates, LD50/LC50 and underidentification semantics, synthetic interval-likelihood/split/uncertainty gates, exact finite cross-domain algebra/completeness, analogue/proxy casualties, exact output semantics, payload schemas, resource/quarantine transitions, constructor bypass, and forged-result rejection. |

```bash
python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
pytest -q                 # fast suite
pytest -q --runslow       # includes selected real-wavefunction integration cases
python -m smartchem.bench # declared-set errors, conditional MAE, refusals and timing
```

**`--runslow` matters.** The slow tests were silently broken for several sessions because
the fast suite passed and nobody ran them. `tests/conftest.py` warns about exactly this.

**Compiled-run convention.** An execution that is going to be cited must preserve its
source-to-certificate receipt. `2 H -> H2` is recorded in
`experiments/RESULTS_compiled_h2_vertical.md`; the structural water-wave compiler acceptance
run is recorded in `experiments/RESULTS_compiled_water_wave_vertical.md`; and the
manufactured continuous steady-water control is recorded in
`experiments/RESULTS_compiled_water_wave_continuous.md`; the human-identifiability run is
recorded in
`experiments/RESULTS_compiled_human_isotope_vertical.md`; the finite ideal-resistor E1
run is recorded in `experiments/RESULTS_compiled_resistive_dc.md`; and the
positive-frequency passive-RLC E2 run and exact singular refusal are recorded in
`experiments/RESULTS_compiled_rlc_ac.md`. All were executed by explicit user directive on
2026-07-27 or 2026-07-28, not because the wider roadmap was silently assumed approved. Raw
RunRecords are ignored journals; durable notes carry the relevant digests, evidence status,
omissions, casualties, and limitations.

## Working rules this repo is held to

These are not aspirations; they are why the numbers here are worth anything.

- **Quantitative claims need a reproducible check.** Tests can hold down code-level
  invariants and measured examples; they do not turn finite sampling into a mathematical
  proof or establish validity outside the tested physical domain.
- **Pre-register predictions, and keep the falsified ones on the record.** P3 (bond
  conservation helps *more* on polyatomics) was predicted and measured false; it is still
  written down, in the docstring of the thing it was wrong about. So is the assumption
  that isolated-energy additivity generalises to other physical quantities — `test_network.py`
  is the autopsy, and the 31.9× is quoted rather than softened.
- **Cross-check the instrument before believing its readings.** Code that measures physics
  is a scientific instrument. The harmonic analysis matched an independently implemented
  algorithm on selected same-Hessian cases before its numbers were used; that verifies the
  algebra on those cases, not the electronic surface or broad physical calibration.
- **Size-control a ratio before attributing it to the variable under test.** A headline of
  16.30× became 2.48× when the arms were matched for reaction magnitude. The control changed
  the answer by 6.6×.
- **Reference data is derived in code, from the measured quantity, with tests on the
  derivation** — never transcribed from memory. See the ethanol near-miss documented in
  `data/reference.py`.
- **The one unforgivable defect is a silent wrong answer.** Refusing loudly is always
  allowed; returning something plausible and unearned never is.
