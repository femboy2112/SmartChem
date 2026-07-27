# SmartChem

A conserving sequential-history layer above quantum chemistry. It enforces atom and charge
balance, retains mechanism provenance, and lets benchmarked oracles decline unsupported work.
It does **not** yet implement a symmetric-monoidal/open-system physics core; parallel
composition, catalysis, Gibbs thermodynamics, circuits and radiation remain explicit roadmap
items. See [the 2026-07-20 multiphysics audit](AUDIT_2026-07-20.md).
The [2026-07-27 direction audit](DIRECTION_AUDIT_2026-07-27.md) proposes the acceptance
contract for the simulation language/compiler: maximize efficiency without silently reducing
the scientist-approved output, while treating cross-domain and cross-scale experimental
language as a first-class shepherding problem.

On 2026-07-27, by explicit user directive rather than presumed earlier roadmap ratification,
the first contract/typed-binding slice, its H2 chemistry vertical, a typed structural-toy
water-wave analogue-kinematics slice, and a typed human–isotope structural-identifiability
slice were executed. Their strict scopes are recorded in
[the compiled H2 receipt](experiments/RESULTS_compiled_h2_vertical.md) and
[the compiled water-wave receipt](experiments/RESULTS_compiled_water_wave_vertical.md), plus
[the human-identifiability receipt](experiments/RESULTS_compiled_human_isotope_vertical.md).
The latter two are synthetic compiler acceptance calculations: neither is a validated
physical/biological model, and the human slice emits no mortality prediction.

The approved runtime now uses a closed three-executor registry, binds plans to the complete
shipped source manifest, and gives each journal path exclusive run ownership. The
[migration receipt](experiments/RESULTS_runtime_registry_migration.md) records fresh
regressions of all three verticals; it is infrastructure evidence, not new scientific
validation.

```python
from smartchem import Config, Molecule, Reaction, favourability
from smartchem.oracle.pyscf_oracle import PySCFOracle

rxn = Reaction(Config.atoms("C", "O"),
               Config.of(Molecule.diatomic("C", "O", order=3)))

favourability(rxn, PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", tight_d=False))
# reports an oracle ΔE direction, not Gibbs spontaneity; benchmark MAE is 0.0562 eV
```

---

## Measured accuracy

Measured on **one selected species set**, 2026-07-20: `NaCl, CS, HCl, Cl₂, CO, HF, N₂` —
spanning ionic, second-row and first-row covalent, with N₂ as a hard-correlation control.
Iodine species are excluded because `aug-cc-pVQZ` on iodine would dominate the cost without
testing anything; that exclusion is stated rather than silent.

| tier | MAE (eV) | MAE (kcal/mol) | n | CPU s/species † | wall s/species † |
|---|---|---|---|---|---|
| legacy heuristic | 4.5455 | 104.83 | 4 of 7 (3 refused) | 0.00 | 0.00 |
| HF/cc-pVQZ | 2.5814 | 59.53 | 7 | 19.1 | 3.1 |
| CCSD(T)/cc-pVTZ | 0.2186 | 5.04 | 7 | 106 | 17.1 |
| CCSD(T)/cc-pVQZ | 0.0763 | 1.76 | 7 | 356 | 58.6 |
| **CCSD(T)/cbs(TZ,QZ)** | **0.0562** | **1.30** | 7 | 432 | 71.4 |
| CCSD(T)/aug-cbs(TZ,QZ)+d | 0.1277 | 2.94 | 7 | not re-measured | not re-measured |

This set and the historical `test` partition were inspected during protocol/model-policy
work; neither is an independent holdout. The table is regression/model-selection evidence,
not an estimate of broad generalization. A new locked external validation population is
required before a coverage claim.

The tabulated MAEs are pinned outputs of the declared data set and protocol. Re-runs in the
recorded environment reproduced the displayed digits; backend/library versions, numerical
settings and hardware still belong in provenance, so these are not timeless constants.

† **The cost column is much weaker than the accuracy column, and the difference is stated
rather than hidden. Treat it as ±10%, and as an ordering rather than a set of constants.**

The machine is shared with unrelated workloads, so wall-clock is not reproducible; CPU-seconds
(across all of PySCF's ~6 threads) is quoted because it measures work done rather than elapsed
time. Even that is imperfect: OpenMP barriers spin-wait, so a contended run burns CPU without
doing work.

The honest state of this column is a coherence check that **fails, mildly, and is not fully
explained.** `cbs(TZ,QZ)` computes both TZ and QZ, so it should cost their sum — and a call
counter confirms it does exactly that (16 calls vs 8 + 8). Yet it *times* 6.4% below
`106 + 356 = 462`. An earlier, independent wall-clock attempt came in 6.8% below its own
contemporaneous sum. Same deficit, two instruments.

An earlier version of this file called the first such figure *"impossible on its face"* and
used that to declare it contaminated. **That was an overclaim and is withdrawn**: a ~7%
shortfall sits inside this instrument's demonstrated variance, so it never established
contamination. The work counts are exact; the timings carry noise of about this size, and the
residual is an open question rather than a settled one.

**Why one declared set.** The previously published table was not comparable across its own
rows: it reported `n = 3, 3, 5, 5, 10`, and since CBS requires *both* TZ and QZ,
`n(cbs)=10` against `n(qz)=5` is impossible from a single run. Its rows came from different
species sets. The per-species values in it were real — NaCl +3.38, CS −1.53 and N₂ −1.19 all
reproduced exactly on re-measurement — but the aggregate was meaningless.

**A claim that was measured and failed.** Augmenting the basis (`aug-` for ionic character,
tight *d* for the second row) was expected to close the ionic and second-row gaps. It is
**2.3× worse at 5.1× the cost**. It helped CS (−1.53 → −1.25) and HCl marginally, and hurt
NaCl (+3.38 → +12.42), Cl₂, CO and HF. The motivating probe was run at *fixed cardinal*,
where augmentation genuinely does help; that conclusion was carried to the extrapolated tier
without being tested there. Extrapolation weights the larger basis by 64/37 and the smaller
by −27/37, so it amplifies non-smoothness rather than averaging it out. The machinery is
kept and tested but not recommended — a negative result you can still run beats one you have
to take on trust.

---

## What the category lets us *not* compute

The oracle is the expensive layer, and no algebra makes CCSD(T) faster. But the algebra can
prove that particular oracle calls are unnecessary *before any of them run* — which is the
same "prune by type, ahead of the expensive layer" move the candidate search already makes,
turned on the energy itself. Two shortcuts exist, at deliberately different levels of proof.

**Exact inside the current separable-species model.** For `f : S + A → S + B`, the adapter's
additivity assumption
gives `ΔE = (E(S) + E(B)) − (E(S) + E(A)) = E(B) − E(A)`. A species present unchanged on both
sides cannot influence the answer, and the multiset difference of `dom` and `cod` finds it
with no oracle call. Interactions with a nominal spectator can invalidate this shortcut in a
real vessel; the future compiler must require a separability proof/guard.

The saving is the smaller half. The larger half is consistent reuse: quadrature is valid
only for **independent** terms. A spectator's modeled energy is not two independent samples —
it is one quantity appearing twice, minus itself. Summing both sides and subtracting
afterwards invents `2·u(S)²` under that independence model.

Measured on `2 N → N₂` with an Fe spectator carrying ±5.0 eV:

| | spectator priced | reported uncertainty |
|---|---|---|
| before | 2× | 7.0711 eV |
| after | 0× | **0.0866 eV** |

The value is bit-identical; the scalar reporting scale was **82× wider** under the incorrect
independence assumption. Neither number is automatically a calibrated confidence interval.
It is also a capability increase: a reaction whose spectator the oracle *cannot* price is
now answerable, because the answer never depended on it. Species that actually change still block.
→ `tests/test_functor.py::TestSpectatorsAreCancelledStructurally`

**Approximate — bond-order conservation, and this one is deliberately *not* policy.** Method
error is roughly a property of the bonds present, so a morphism that breaks and makes the same
bond content should cancel much of it. Our objects carry bond topology, so `is_bond_order_conserving`
decides this with no oracle call. Pre-registered prediction: the ratio of mean |error|
(bond-creating ÷ bond-conserving) would exceed 3.

| tier | bond-creating | bond-order-conserving | ratio |
|---|---|---|---|
| HF/cc-pVTZ | 1.8847 eV | 0.7475 eV | 2.52 |
| CCSD(T)/cc-pVTZ | 0.1265 eV | 0.0592 eV | 2.14 |

**The prediction failed at both tiers.** The effect is real and stable across tiers differing
~15× in absolute error, but it is worth a factor of two, not three. So the predicate decides
and reports the property; nothing selects a cheaper tier on the strength of it. Nine diatomic
reactions in one basis family do not license an automatic accuracy policy — and the last policy
proposed here on that kind of evidence, basis augmentation, lost outright when finally measured
at the tier that mattered.

**Tested on an internal polyatomic research path — where a control changed the answer by
6.6×.** Same controlled experiment on
four bond-creating and four bond-order-conserving polyatomic reactions, HF/cc-pVDZ against
CCSD(T)/cc-pVDZ with basis, geometry and ZPE shared so only correlation differs:

| statistic | bond-creating | bond-order-conserving | ratio |
|---|---|---|---|
| mean absolute error | 2.4951 eV | 0.1531 eV | 16.30 |
| **relative to \|ΔE\|** | **0.2602** | **0.1049** | **2.48** |
| per bond changed | 1.0322 eV | 0.0383 eV | 26.97 |

These numbers do not validate public polyatomic estimates; the bundled oracle currently
declines that protocol because conformer/spin coverage and a validation scale are absent.
The raw 16.30 is **mostly artifact**. The creating arm is atomizations at 4–16 eV; the
conserving arm rearranges one or two bonds at 1–3 eV. An error that merely scaled with reaction
size would produce a large ratio with no help from the predicate at all. Size-controlled, the
answer is **2.48** — sitting right on the diatomic 2.14–2.52. The effect **transfers unchanged
rather than growing**, which falsifies the third pre-registered prediction (that more conserved
bonds would mean more cancellation).

And the spreads *touch*. `C₂H₆ + H₂ → 2 CH₄` has relative error 0.206, above the weakest
creating reaction (`C + 4H → CH₄`, 0.199). That one reaction breaks a C–C bond and makes C–H
bonds: bond *order* is conserved, all single throughout, but the bond *types* change about as
much as they can. It is the least isodesmic-like member of a set chosen only for order
conservation — so the single case that spoils the separation is exactly the one
`is_isodesmic` would exclude. That is the strongest argument yet for measuring the stronger
predicate, and the reason it stays on the task list rather than being quietly dropped.
→ `tests/test_geometry.py::TestThePolyatomicConservationMeasurement`

**Measured, then retired — local geometry refinement versus energy.** With
`optimize_geometry=True` the oracle now pays *zero* calculations per diatomic: `energy()`
declines before buying anything. It used to pay six — five to scan around the tabulated
`r_e`, one at the bracketed fitted minimum — but the scan was truth-centered on that same
tabulated `r_e` and the mode still took its spin and frequency from the tables, so it never
priced an unlisted species or proved geometry prediction from structure, and no benchmark
ever measured it. A protocol with no validation scale of its own does not ship a number
here. Listed or unlisted, the diatomic answer is a decline until a computed
frequency/state protocol exists. The scanner is kept and still unit-tested, so the numbers
below remain reproducible.

Those five scan points are answering a **different question** from the sixth. The scan needs
the *position* of a local minimum; the single point needs the *value* of an energy. A method's
error may be nearly constant across this truth-centered 0.12 Å window, and a constant shift
moves a parabola's vertex not at all—only its height. Whether a cheaper scan tier preserves
that local vertex is measured below, not assumed globally.

Energy tier held fixed at CCSD(T)/cc-pVTZ; only the scan tier varies:

| scan tier | max Δr_e vs full scan | MAE (kcal/mol) | s/species | speedup |
|---|---|---|---|---|
| CCSD(T)/cc-pVTZ (full) | — | 4.99 | 45.6 | 1× |
| MP2/cc-pVDZ | 0.0289 Å | 5.26 | 12.5 | 3.64× |
| HF/cc-pVDZ | 0.0236 Å | 5.27 | 14.8 | 3.08× |

**About 3× cheaper for about 0.3 kcal/mol.** Two honesty notes. The pre-registered bar was
0.30 kcal/mol and both arms landed at 0.27–0.28 on n=7 — a pass, but with almost no margin,
which is exactly why this is `geometry_tier=` and not the default. And the 3.64-vs-3.08
ordering **is not a result**: HF/cc-pVDZ measured *slower* than MP2/cc-pVDZ, which cannot
reflect work done since MP2 is HF plus a correction. Per-species wall-clock swung ~3.4× on
identical final calculations, so the honest claim is "about 3×".

One prediction was falsified: MP2 was expected to give geometries closer to the full tier than
HF, and within 0.015 Å. It did neither — 0.0289 Å, and worse than HF's 0.0236.
→ `tests/test_shortcuts.py::TestGeometryTierWasMeasured`

**A candidate shortcut examined and rejected as unnecessary**, recorded so nobody optimises it
later. Reaction energies come from subtracting two total energies near −3000 eV, which looks
like catastrophic cancellation. It isn't: float64 carries ~6.8×10⁻¹³ eV of absolute precision
there, so the floating-point subtraction itself loses negligible precision at the quoted
target. SCF/CC iteration tolerances are separate convergence controls, not rigorous bounds on
the final electronic energy; solver residual/refinement and model error still need their own
checks.

Writing the tests also caught an error in the framing: `HCl + F → HF + Cl` preserves bond
*orders* but not bond *types* (`H–Cl` became `H–F`), so the measured set is **not** isodesmic in
the strict sense. Attaching the ratio to an isodesmic predicate would have claimed a number for
a property the experiment never varied. Hence two predicates — `is_bond_order_conserving`
(measured) and `is_isodesmic` (strictly stronger, labelled unmeasured) — with parametrized
tests asserting every scored reaction falls on the side of the predicate it was scored as.
→ `tests/test_shortcuts.py`

---

**And something worth knowing about the recommended tier.** For NaCl, extrapolation makes a
good answer worse:

| basis | error (kcal/mol) |
|---|---|
| cc-pVTZ | −4.10 |
| **cc-pVQZ** | **+0.39** |
| cbs(TZ,QZ) | +3.38 |

Plain QZ is nearly at chemical accuracy; extrapolating makes it 8× worse. The Helgaker
formula behaves exactly as written — its *premise*, that correlation is already in the
smooth X⁻³ tail by TZ, was inadequate for this NaCl row. The extrapolation displacement rides
on every `Estimate` as a named sensitivity and raises the reported scalar floor when it
survives algebraically, so NaCl reports 0.13 eV while H₂ retains the declared tier MAE of
0.0562 eV. Neither is a species-level confidence interval.

## Polyatomic research path: the geometry seed comes from the bond graph

Anything with three or more atoms used to be blocked even internally for want of coordinates. That was
never an interface limit — `energy(molecule)` has always taken full structure — it was a
missing input, and a lookup table of experimental geometries only ever covers species
somebody already tabulated.

Part of the answer was in the type. `Molecule` carries **bond topology**, a decision made so that
`Na + Cl` and `NaCl` could be different objects and the reaction between them a genuine
arrow. A bond graph can seed a geometry builder, but does not determine stereochemistry,
conformation, electronic state, or the global minimum. The structure that made conservation
enforceable therefore makes candidate coordinates constructible, not uniquely derivable.
The public oracle still declines polyatomic energy estimates until this complete protocol
has a domain-specific validation profile.

Getting a geometry splits into three parts with genuinely different computational
characters, and keeping them apart is the entire design:

| step | what it needs | cost |
|---|---|---|
| **seed** — graph → coordinates | pure combinatorics; VSEPR domain counts and exact solid geometry (the tetrahedral angle is `arccos(−1/3)`, not a fitted parameter) | microseconds, no wavefunction |
| **relax** — → stationary point | a chosen approximate surface and its *gradients* | cheap tier |
| **check** — → local-curvature evidence | the Hessian's eigenvalues | cheap tier, same surface |

Relaxation and certification both evaluate a cheap electronic-structure surface; the final
single point can use a more expensive tier. So a CCSD(T)/CBS single point can sit on a
geometry and zero-point estimate obtained at a cheaper, explicitly recorded tier. Whether
that separation is accurate enough is a protocol-specific validation question.

**Step 3 turned out to be load-bearing, not decorative.** Diatomics report `D₀` by
subtracting a ZPE from tabulated `ω_e`. A polyatomic has no tabulated frequencies, so
without a Hessian the only options are reporting `D_e` while every other number in the
pipeline is `D₀`, or reporting nothing. For water that gap is **0.61 eV** — fourteen times
the chemical-accuracy threshold quoted above, and it would read as a bad method rather than
a category error. The same matrix that supplies the ZPE detects negative local curvature
and can reject a saddle on the modeled surface. The implementation currently counts every
negative projected mode; it has no calibrated noise cutoff. No detected imaginary mode is
not a proof of the global structure or finite-temperature stability.

Cross-checked against known answers before treating the mechanics as usable:

| check | against | result |
|---|---|---|
| vibrational algebra cross-check | PySCF's independently written `thermo.harmonic_analysis`, same Hessian | **0.000 cm⁻¹ difference** on tested cases |
| relaxed `r_e` | 23 tabulated experimental diatomics | MAE 0.0255 Å |
| computed ZPE | the same 23 experimental `ω_e` | MAE 0.0103 eV, **+9.1% biased** |
| imaginary modes / convergence failures | — | 0 / 0 |

The +9.1% is the aggregate displacement of a Hartree–Fock harmonic protocol on this
23-diatomic sample; the experiment does not separate electronic-method, anharmonic, and
reference-convention contributions. It rides in a
named signed systematic-sensitivity channel rather than being treated as an independent
random draw. It survives into atomization against free atoms and can cancel algebraically in
a related difference, but that does not establish cancellation of unknown residual error;
coefficient uncertainty, species scatter, and transfer to polyatomics are not yet validated.
The reporting policy may widen the displayed scalar uncertainty scale when a
named sensitivity survives; it does not turn that scale into a confidence bound. The factor
is not applied as a correction.

**Two independent paths agree.** A diatomic can now be priced from tabulated experimental
`r_e` and `ω_e`, or by relaxing a graph seed and computing a Hessian — sharing only the
single-point code. Over 8 diatomics the derived path differs by **0.024 eV mean, 0.066 eV
max**, against the tier's own 0.22 eV. The geometry machinery is not the limiting error.
→ `tests/test_geometry.py`

Hartree–Fock is the only tier that can do this, for a structural reason: PySCF gives MP2
analytic gradients but no Hessian, and a Hessian cannot be taken on a different surface from
the relaxation — the point would not be stationary for it. MP2 could relax but not perform
the same-tier local-curvature/ZPE check. Declined rather than
mixed.

## What this is for

Not a faster DFT. PySCF is a *backend* here, not a rival.

The useful layer above is narrower: reactions whose endpoints cannot violate composition or
charge conservation, sequential mechanisms whose structural history stays aligned with their
tally, and environment-response utilities. ``is_regenerated`` decides unchanged
stoichiometric presence; it does not prove catalysis.

This is also where the speed claim becomes true, in the only way it can. You don't run one
CCSD(T) job faster — you **prune by type before any oracle call**. Candidates that violate
composition or charge balance never reach the expensive layer at all. Chemical valence is
not currently validated.

## What it does not do

Stated plainly, because the first version of these docs did not.

- **Public polyatomic energy coverage is refused.** A small 0 K reference table and several
  controlled internal comparisons exercise the research mechanics, but they do not validate
  conformer search, spin-state choice, solution chemistry, finite-temperature free energies,
  or broad chemical space. The oracle returns no public estimate for that protocol.
- **Strict isodesmicity is decided and measured, but the result is confounded.** The current
  sample has seven isodesmic reactions; five contain carbonyl species, versus three of the
  47 order-only reactions. Stratification flips the apparent ordering, so the evidence is
  explicitly recorded as undecided rather than promoted to solver policy.
- **The internal polyatomic path guesses PySCF spin from electron parity.** This is not safe
  for production chemistry and is one reason the public path declines; explicit electronic
  state/multiplicity identity and spin-state ensembles are required.
- **The interface carries bond order, but both shipped backends have limitations.** The
  frozen heuristic ignores order; PySCF treats it as topology/geometry guidance rather than
  a quantum input. Backend conformance is roadmap work.
- **No Gibbs thermodynamics or kinetics.** Bundled results are energy differences, not
  spontaneity, equilibrium constants, rates, transition states or discharge curves.
- **No valency model, no solid state, no photochemistry.** These existed in the legacy
  engine, did not work, and were removed rather than repaired. See
  `tests/test_findings.py::RETIRED`.
- **Graph canonicalisation has a 50,000-candidate budget**, which can refuse highly symmetric
  systems such as benzene regardless of raw atom count.

## The categorical structure, and why it is load-bearing

The claim is not that chemistry can be *described* with category theory. It is that the
structure **prevents defects that description would only document**.

| Property | Enforced by | Test |
|---|---|---|
| Mass and charge conserved | `Reaction.__post_init__` | `test_laws.py::TestConservationTheorem` |
| Conservation survives composition | transitivity of `∘` | `::test_composition_inherits_conservation` |
| Category laws | `path` concatenation | `::TestCategoryLaws` |
| Object product is commutative | `Config` canonicalisation | `::TestObjectProductAndScheduledProduct` |
| True morphism interchange | not implemented; strict xfail | `::test_true_parallel_interchange_is_architecture_debt` |
| Stoichiometric regeneration | `is_regenerated` | `::TestCatalysis` |
| Comonad laws | `Store` | `test_store.py::TestComonadLaws` |
| Response surfaces via `extend` | `survey` | `test_store.py::TestResponseSurface` |
| Writer/List-style `bind` behavior on sampled finite values | `Pathway` | `test_pathway.py::TestMonadLaws` |
| Step labels, method provenance and energy survive `bind` | structured accumulation | `test_pathway.py::TestCertificateSurvivesBind` |
| Isolated-species energy is additive | `thermo` model assumption | `test_functor.py::TestSeparableEnergyAdditivity` |
| **ΔE is additive along a path** | `∘` → `+` | `test_functor.py::TestFunctoriality` |
| **Conservation licenses the subtraction** | `Reaction` + `ΔE` | `test_functor.py::TestConservationLicensesSubtraction` |
| Named correction displacements propagate by source | `Estimate` | `test_functor.py::TestSystematicVsRandomError` |
| Basis choice follows the elements | `resolve_basis` | `test_basis_policy.py::TestResolution` |

**The theorem.** Conservation is checked once, on generators, in the `Reaction`
constructor. Every composite inherits it:

```
f : A → B conserves,  g : B → C conserves   ⟹   g∘f : A → C conserves    (transitivity)
```

So a mass-violating reaction is not merely absent — it is **unconstructible**:

```python
>>> Reaction(Config.atoms("Fe", "O", "Cl"), Config.of(Molecule.diatomic("Fe", "O")))
ConservationError: mass not conserved: Cl + Fe + O -> FeO;
                   {'Cl': 1, 'Fe': 1, 'O': 1} != {'Fe': 1, 'O': 1}
```

**Objects carry bond topology, and that is load-bearing.** If an object were a bare bag of
atoms, `Na + Cl` and `NaCl` would be the *same object*, every conserving reaction would be
an endomorphism, and there would be no arrows to reason about at all.

### Conservation is what licenses the physics

The honest categorical statement is an endpoint potential into the real translation
category, under an isolated-species additivity model:

```
E(A + B) = E(A) + E(B)          ΔE(f: A→B) = E(B) − E(A)
ΔE(g∘f)  = ΔE(f) + ΔE(g)
```

Total energy has an **arbitrary zero** set by atom content — PySCF puts CO near −3074 eV and
the legacy heuristic near −11 eV, with each internally consistent on its own reference.
`E(B) − E(A)` is invariant under the permitted per-element reference shifts when A and B hold
the same atoms. Open-system differences require shared conventions plus explicit reservoirs;
the closed `Reaction` type enforces the invariant case at construction.

```python
>>> o.energy(Molecule.diatomic("C","O", order=3))   # -3082.5872 eV   arbitrary zero
>>> o.energy(Molecule.atom("C"))                    # -1029.3330 eV   arbitrary zero
>>> reaction_energy(Reaction(Config.atoms("C","O"), Config.of(co)), o)
-11.1199 +/- 0.0562 eV        # experiment: -11.157; MAE label, not a confidence interval
```

An 11 eV answer extracted as the difference of two ~3000 eV numbers, correct to five
significant figures, because the arbitrary parts cancel. Shift every atomic reference by a
million eV and no reaction energy moves at all
(`test_functor.py::test_offsets_cancel_regardless_of_their_size`).

**So conservation is not a safety check bolted onto a chemistry model — it is the
precondition that makes endpoint differences invariant under permitted per-element reference
shifts.** Telescoping then makes a multi-step history's endpoint ΔE equal the sum of its step
differences. Open systems need explicit reservoirs rather than pretending inventories match.

## Architecture

```
Specification layer      stoichiometry.py         derive every balanced reaction; check a written one
                         rigidity.py              the same law against a quadratic invariant
                         domain.py                what an oracle can be asked, before asking
                         diagnosis.py             why a refusal happened, and whether it is removable
                         ledger.py                interrogate an underdetermined spec to a fixed point
Compiled verticals       contracts.py · program.py
                         water_wave_domain.py     typed branch/profile diagnostic, structural toy
                         water_wave.py            analogue-only plan/approval/journal/certificate path
                         human_isotope_domain.py  typed endpoint/assembly identifiability
                         human_isotope.py         proxy-only plan/approval/journal/certificate path
Search & verification    pathway.py · store.py    mechanisms, regeneration, response surfaces
Sequential core          category.py              conservation + validated histories
Oracle interface         oracle/                  pluggable, provenance + untyped scale/sensitivities
  ├─ heuristic           the frozen baseline, kept measurable
  ├─ pyscf_oracle        HF / MP2 / CCSD / CCSD(T), cc-pVXZ ± aug ± tight d, CBS
  └─ (xtb, tight-binding)                                          not yet implemented
Data                     atoms.py                 NIST ionization / affinity data
                         data/reference.py        curated references + inspected historical split
                         data/basis_tight_d.py    vendored (X+d) sets for Al–Ar
Frozen baseline          legacy.py                the original engine. Do not build on it.
```

An oracle may **decline** but may not **invent**. Refusals are counted separately in the
benchmark and prevent any accuracy-tier verdict; the numerical MAE is labeled conditional
on the cases actually returned.

## The specification layer, and the one negative result it has produced

`THE_COMPILER.md` argues for a layer above the oracles: a scientist writes a deliberately
underdetermined specification, and the system interrogates it — naming what is
underdetermined, offering the admissible completions, iterating — rather than either
running it or rejecting it. The governing rule is the **derived-menu law**: every option
offered must be the image of a *declared invariant* under a *declared operation*, and a
system that cannot enumerate the options must **say so** rather than improvise a plausible
list. An LLM asked "what are the possible configurations here?" will always produce a
fluent answer, and a wrong specification is unreachable by any oracle's refusal.

Two instances are built, and the interesting part is that they do not behave the same way.

**Linear invariant — `stoichiometry.py`.** Declare per-element atom counts and net charge;
the operation is the saturated integer kernel of the composition matrix. The admissible
balances are `ker(A) ∩ Zⁿ`, a lattice, so a basis is a *complete* menu and every balanced
reaction is an integer combination of it. Three ranks give three behaviours: `freedom == 0`
refuses and the refusal is a theorem; `1` is forced; `≥ 2` is a genuine choice. It also
implements the second half of the ask — hand it a balance you wrote and it checks it
against the same matrix that derived the menu, naming which conserved quantity fails and by
how much (`O off by -2`), not merely *no*.

**Non-linear invariant — `rigidity.py`.** Declare pairwise distances, `|pᵢ − pⱼ|² = d²`.
This is the case the stoichiometry module named as its own open question and could not
answer. Measured by `experiments/nonlinear_menu_rank.py`:

| | linear (atom counts) | non-linear (distances) |
|---|---|---|
| admissible set | a lattice | a real algebraic variety |
| closed under addition | yes | no |
| REFUSE is a theorem | always | only on a **complete** constraint set |
| FILL_IN is a theorem | always | only on a complete constraint set |
| ENUMERATE | a finite basis generating everything | **no analogue exists** |
| check a written answer | decidable | decidable |

**The law does not survive, and it fails in a specific way rather than collapsing.** A
complete distance matrix is decided exactly, in rational arithmetic with no tolerance, by
the rank and definiteness of its Gram matrix — but a complete distance matrix also fixes
the configuration up to isometry, so it can never present a choice. *The non-linear
invariant is derivable exactly where it is doing no work.* The row where the linear menu
earned its keep is the row where derivability dies. Deciding a *partial* distance matrix in
a fixed dimension is NP-hard (Saxe 1979), and a real bond graph is always partial — the
undeclared H–H distance in water **is** the bond angle.

Both standard repairs are linearisations, and both give confident wrong answers in
*opposite* directions:

- the **Maxwell count** says the double banana (8 points, 18 constraints, 3D) is rigid; it
  hinges. Counted 0, true internal freedom 1.
- the **rigidity-matrix rank** says a triangle with lengths 1, 1, 2 is flexible; it is
  rigid, because the triangle inequality is tight and exactly one configuration exists.

The rank proxy is salvageable only in one direction, and adversarial review is what forced
that admission. Zero linearised freedom **implies** rigidity and is a theorem; a nonzero
one implies nothing, and the module's first attempt to flag *when* it could be trusted was
a global test that a locally collinear sub-framework walks straight past. There is no cheap
local repair, so the claim was weakened to the one-directional statement rather than
patched — `Placement.conclusive` is now the only certificate offered.

Two further honesty notes on the `FORCED` row, because it hands back less than it looks
like it does. "Unique **up to isometry**" is exact, and `O(d)` contains reflections — so a
chiral configuration and its mirror image satisfy the same complete distance matrix and are
not interconvertible by any rigid motion. In chemistry that pair is a pair of enantiomers,
different substances, and lacking a mirror symmetry is the generic case. A declared
distance invariant cannot see the distinction, exactly as identical composition columns
leave `Na(*) → Na` unseen in the linear module.

This repository has already paid for that second sentence once, two layers down:
`geometry.py:604` records **0.0476 eV** of zero-point energy lost when a physically linear
molecule carrying a ten-millionth of an Ångström of noise was assigned six external modes
instead of five, and a real vibration vanished with no warning. The external modes are the
trivial infinitesimal motions of a framework; the degenerate configurations are the
collinear geometries. Same phenomenon, two storeys apart.

What survives intact is the *checking* clause. Evaluating a written answer is decidable for
any computable invariant, while deriving the menu needed the invariant to be linear. **The
two halves of the ask have different computability, and stoichiometry made them look like a
matched pair.** A compiler generalised from the friendly case would have inherited that
assumption silently.

The ground truth for the two counterexamples was derived independently and blind, by a
separate agent working from standard definitions and never reading this repository; it
agrees with everything above. Run `.venv/bin/python experiments/nonlinear_menu_rank.py`
(exit 0 = all claims verified) and `experiments/ledger_mutation_probe.py`, which restores
each of these modules' known defects verbatim and confirms the tests kill them.

## Install and run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # core + tests
pip install -e '.[dev,qc]'       # + PySCF for the accurate tiers

pytest -q                        # fast suite
pytest -q --runslow              # + selected real oracle integration calls (needs PySCF)
python -m smartchem.bench --split test
```

`--split test` selects a reproducible historical partition; it does not restore holdout
status. Quoting which population produced a number still matters because the first version
of this table mixed populations across rows.

## Status

The closed sequential core, Store utilities, mechanism search, oracle interface and basis
policy are tested but not complete for the stated multiphysics goal. The strict interchange
xfail and audit roadmap make that boundary executable rather than implicit.

**Compiled vertical status (2026-07-27).** The narrow source-to-certificate seam is now
implemented and was executed once for `2 H -> H2` at existing fixed-geometry
CCSD(T)/cc-pVTZ coverage: `delta-E = -4.427005898711 eV`. Its magnitude differs from the
repository H2 D0 (`4.478 eV`) by `0.050994 eV`. This comparison is a single-run diagnostic,
not a calibration, MAE, error bound, Gibbs/spontaneity result, or expanded chemistry claim;
the original public-domain and validation limits still apply. See
`experiments/RESULTS_compiled_h2_vertical.md`.

**The legacy engine was retired on 2026-07-20.** Seven modules (`engine`, `comonad`,
`lattice`, `monad`, `network`, `molecule`, `electrochem`) and twelve demo scripts were
removed; the code path needed to reproduce the baseline was consolidated into
`smartchem/legacy.py` and is byte-identical to the original `propose_bond`.

That distinction is the point. **Deleting the module that fails a test is not the same as
fixing it** — a capability that disappears during a cleanup is indistinguishable from one
that never existed. So each of the 28 findings from the original review carries an explicit
verdict, and both kinds are pinned by tests in `tests/test_findings.py`:

- **13 discharged** — F1 conservation, F2 environment response, F3 stoichiometric
  regeneration evidence (not proof of catalysis),
  F4 certificate survival, F5 measured energies, F11 bond topology. Each now asserted
  against the live system, unmarked, passing.
- **9 dropped** — F6 valency, F7 ionization search, F8 the lattice gate, F9 photolysis,
  F10 band gaps. Recorded in `RETIRED` and asserted *absent*, so none can creep back
  unmeasured.
- **6 dissolved** — F12's crash surface lived in the demo scripts that were removed.

The frozen baseline's exact MAE on every split is pinned, because the headline claim is a
*comparison*, and a comparison is only checkable while both sides still run.

Both structural halves of the canonical cross-domain pair now run. The human half correctly
returns incompatible mathematical probability witnesses rather than an empirically calibrated
or actual-human/population mortality prediction; an empirically fitted D2b model requires
multi-dose/time evidence, uncertainty, held-out validation, competing-risk semantics where
applicable, and data-governance authority. The no-loss optimizer precedes the
conversational surface. Physical water-wave validation remains separate:
continuity/momentum-admissible backgrounds, wavelength/capillarity gates, uncertainty, and a
full dispersive branch solver. The broader metaphor portfolio begins with traffic kinematic
waves, Ising/lattice-gas as an exact-map control, and port-Hamiltonian networks as the
cross-substrate composition control.
Chemistry expansion remains separate: a tight-binding/xTB fast tier, broader polyatomic
backend validation, explicit electronic states/conformers, and a documented bond-order policy
per backend.

On the specification layer, the derived-menu law is now implemented for a linear invariant
and measured against a quadratic one, with the negative result above. What is **not**
settled is whether any useful middle ground exists — an invariant non-linear enough to be
worth declaring, structured enough to enumerate. Multiplicative laws linearise under a log
and are not a real test of that; a genuine one has not been found. Until it is, the honest
reading is that the enumerating half of the law is a property of linear invariants and not
of the law.

## Origin

The first implementation was generated by Antigravity and reviewed adversarially on
2026-07-20. The review found the categorical machinery had zero call sites — `bind`,
`extend`, `map`, `Poset.leq`, `is_favorable` were all dead — while the documentation
claimed chemical accuracy the code missed by 76×.

The atomic data was genuinely good (36 NIST values, zero errors > 0.06 eV) and the textbook
formulas were correctly transcribed. Those were kept. See `THE_ORBITAL.md` for the current
specification, `THE_DIFFERENCE.md` for an honest comparison against neighbouring tools, and
`THE_COMPILER.md` for the specification layer's design and its running record of what each
brick's failure taught — which is most of what it is for.

Every module in the specification layer has shipped at least one defect invisible to its own
tests, and every one was found by pointing an adversary at it rather than by the suite: an
index-2 sublattice that made the menu quietly incomplete, a domain ceiling welded shut by
dead arithmetic while its docstring promised it would rise, a length check standing in where
identity was needed, an `isinstance` that admitted a subclass which then lied about its own
magnitude, and a rigid-motion count that went negative above seven points. That is a
budgeting fact, not a confession — the tests are written knowing it, and
`experiments/ledger_mutation_probe.py` restores each of those defects verbatim and checks
that the suite now kills it.
