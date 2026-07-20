# SmartChem

A compositional layer above quantum chemistry: a reaction algebra where conservation is
enforced by construction, catalysis is a decidable property, and accuracy is a dial you
set rather than a property you inherit.

```python
from smartchem import Config, Molecule, Reaction, favourability
from smartchem.oracle.pyscf_oracle import PySCFOracle

rxn = Reaction(Config.atoms("C", "O"),
               Config.of(Molecule.diatomic("C", "O", order=3)))

favourability(rxn, PySCFOracle("CCSD(T)", "aug-cbs(TZ,QZ)"))
# 'exothermic (-11.13 +/- 0.04 eV)'        experiment: -11.157 eV
```

---

## Measured accuracy

Measured on **one declared species set**, 2026-07-20: `NaCl, CS, HCl, Cl₂, CO, HF, N₂` —
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

Every MAE above is exact and reproducible — the calculations are deterministic, and repeated
re-runs reproduced all five values to the digit.

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

**Exact — spectators, and this one is policy.** For `f : S ⊗ A → S ⊗ B`, the monoidal law
gives `ΔE = (E(S) + E(B)) − (E(S) + E(A)) = E(B) − E(A)`. A species present unchanged on both
sides cannot influence the answer, and the multiset difference of `dom` and `cod` finds it
with no oracle call. So it is never priced.

The saving is the smaller half. The larger half is rigor: uncertainties combine in quadrature,
which is valid only for **independent** errors. A spectator's energy is not two independent
samples — it is one number appearing twice, minus itself. Summing both sides and subtracting
afterwards adds `2·u(S)²` of variance that physically cancels to zero.

Measured on `2 N → N₂` with an Fe spectator carrying ±5.0 eV:

| | catalyst priced | reported uncertainty |
|---|---|---|
| before | 2× | 7.0711 eV |
| after | 0× | **0.0866 eV** |

The value is bit-identical; the error bar was **82× too wide**, and the width was fiction. It
is also a capability increase: a reaction whose spectator the oracle *cannot* price is now
answerable, because the answer never depended on it. Species that actually change still block.
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

**Extended to polyatomics — where a control changed the answer by 6.6×.** Same experiment on
four bond-creating and four bond-order-conserving polyatomic reactions, HF/cc-pVDZ against
CCSD(T)/cc-pVDZ with basis, geometry and ZPE shared so only correlation differs:

| statistic | bond-creating | bond-order-conserving | ratio |
|---|---|---|---|
| mean absolute error | 2.4951 eV | 0.1531 eV | 16.30 |
| **relative to \|ΔE\|** | **0.2602** | **0.1049** | **2.48** |
| per bond changed | 1.0322 eV | 0.0383 eV | 26.97 |

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

**Measured, opt-in — separating geometry from energy.** With `optimize_geometry=True` the
oracle pays *six* calculations per diatomic: five to scan the bond length, one at the fitted
minimum. That mode is not a luxury — it is the only way to price a species whose geometry is
not in the vendored table, so it decides whether the system generalises past 28 tabulated
diatomics.

Those five scan points are answering a **different question** from the sixth. The scan needs
the *position* of a minimum; the single point needs the *value* of an energy. A method's error
is nearly constant across the 0.12 Å window scanned, and a constant shift moves a parabola's
vertex not at all — only its height. So the scan should tolerate a much cheaper method.

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
there, and the binding SCF/CCSD convergence tolerances (~2.7×10⁻⁸ eV) sit six orders of
magnitude below the 0.043 eV target. The arbitrary-zero contract is numerically safe, and the
reason is the convergence thresholds, not luck.

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
smooth X⁻³ tail by TZ, fails for an ionic species. This is no longer reported with false
confidence: the extrapolation correction rides on every `Estimate` and widens the error bar
by however much survives cancellation, so NaCl reports ±0.13 eV while fully-converged H₂
keeps ±0.041.

## Polyatomic species: the geometry comes from the bond graph

Anything with three or more atoms used to be declined for want of coordinates. That was
never an interface limit — `energy(molecule)` has always taken full structure — it was a
missing input, and a lookup table of experimental geometries only ever covers species
somebody already tabulated.

The answer was in the type. `Molecule` carries **bond topology**, a decision made so that
`Na + Cl` and `NaCl` could be different objects and the reaction between them a genuine
arrow. A bond graph is exactly what a geometry builder needs. The structure that made
conservation enforceable makes coordinates derivable.

Getting a geometry splits into three parts with genuinely different computational
characters, and keeping them apart is the entire design:

| step | what it needs | cost |
|---|---|---|
| **seed** — graph → coordinates | pure combinatorics; VSEPR domain counts and exact solid geometry (the tetrahedral angle is `arccos(−1/3)`, not a fitted parameter) | microseconds, no wavefunction |
| **relax** — → stationary point | the real surface, but only its *gradients* | cheap tier |
| **certify** — → proven minimum | the Hessian's eigenvalues | cheap tier, same surface |

Only the middle step touches an oracle, and never the expensive one. So a
CCSD(T)/cbs single point sits on a geometry and a zero-point energy that cost a fraction
of it — which is what makes polyatomics affordable rather than merely possible.

**Step 3 turned out to be load-bearing, not decorative.** Diatomics report `D₀` by
subtracting a ZPE from tabulated `ω_e`. A polyatomic has no tabulated frequencies, so
without a Hessian the only options are reporting `D_e` while every other number in the
pipeline is `D₀`, or reporting nothing. For water that gap is **0.61 eV** — fourteen times
the chemical-accuracy threshold quoted above, and it would read as a bad method rather than
a category error. The same matrix that supplies the ZPE proves the point is a minimum and
not a saddle; a saddle is a transition state, and pricing one as a molecule is exactly the
silent wrong answer this project treats as unforgivable.

Calibrated against known answers before any of its readings were believed:

| check | against | result |
|---|---|---|
| vibrational analysis | PySCF's independently written `thermo.harmonic_analysis`, same Hessian | **0.000 cm⁻¹** |
| relaxed `r_e` | 23 tabulated experimental diatomics | MAE 0.0255 Å |
| computed ZPE | the same 23 experimental `ω_e` | MAE 0.0103 eV, **+9.1% biased** |
| imaginary modes / convergence failures | — | 0 / 0 |

The +9.1% is the known Hartree–Fock harmonic overestimate. It is **systematic**, so it rides
in `Estimate.systematic_ev` and propagates additively with sign rather than in quadrature —
the same distinction that made spectator cancellation worth doing. That gets three cases
right with no special-casing: it survives into an atomization energy (free atoms have no
vibrations, so nothing cancels it), largely cancels in a bond-conserving reaction, and never
inflates a random error bar. It is **not** applied as a scaling correction, because a factor
fitted on 23 *diatomics* and carried to polyatomics is the identical mistake already made
once here with basis augmentation.

**Two independent paths agree.** A diatomic can now be priced from tabulated experimental
`r_e` and `ω_e`, or by relaxing a graph seed and computing a Hessian — sharing only the
single-point code. Over 8 diatomics the derived path differs by **0.024 eV mean, 0.066 eV
max**, against the tier's own 0.22 eV. The geometry machinery is not the limiting error.
→ `tests/test_geometry.py`

Hartree–Fock is the only tier that can do this, for a structural reason: PySCF gives MP2
analytic gradients but no Hessian, and a Hessian cannot be taken on a different surface from
the relaxation — the point would not be stationary for it. MP2 could relax but not certify:
a geometry nobody can prove is a minimum and a ZPE nobody can compute. Declined rather than
mixed.

## What this is for

Not a faster DFT. PySCF is a *backend* here, not a rival.

What doesn't otherwise exist is the layer above: reactions as typed morphisms that cannot
violate conservation, mechanisms that compose with their energy bookkeeping guaranteed to
stay in step, catalysis decided structurally, and an entire response surface generated from
one local definition. A quantum chemistry package computes one number for one geometry. It
has nothing to say about whether your proposed mechanism conserves mass.

This is also where the speed claim becomes true, in the only way it can. You don't run one
CCSD(T) job faster — you **prune by type before any oracle call**. Candidates that violate
conservation, charge balance or valence never reach the expensive layer at all.

## What it does not do

Stated plainly, because the first version of these docs did not.

- **Polyatomic energies exist but are not yet scored.** H₂O, NH₃, CH₄ and CO₂ are priced
  (see below). What is missing is a *reference table* of polyatomic atomization energies to
  score them against — this repo vendors diatomic BDEs only, so the polyatomic MAE column is
  blank because nothing has been measured, not because something failed.
- **Strict isodesmicity is decided but still unmeasured**, and now for a reason that can be
  named exactly: over the elements covered, the smallest non-trivial strictly-isodesmic
  reaction is `C₂H₆ + CH₃OH → C₂H₅OH + CH₄`, and C₂H₅OH has 9 atoms — one past the
  canonicalisation cap. `is_bond_order_conserving`, the weaker predicate, *is* measured.
- **Open-shell polyatomics take the lowest spin consistent with electron parity.** That is
  an assumption, not a derivation — O₂ is the standard counterexample — so it is stated in
  the notes of every estimate that relies on it. Diatomics use tabulated spins instead.
- **Bond order reaches the oracle, but not every backend uses it.** The object carries its
  topology and the oracle receives the whole species, so a bond-additive oracle prices
  C–C and C=C differently. `PySCFOracle` keys *diatomic* geometry on formula, so it does not
  distinguish them there — polyatomics do use the bond orders, via the VSEPR seed.
- **No kinetics.** Everything here is thermodynamic. A favourable reaction may still be
  impossibly slow.
- **No valency model, no solid state, no photochemistry.** These existed in the legacy
  engine, did not work, and were removed rather than repaired. See
  `tests/test_findings.py::RETIRED`.
- **Graph canonicalisation is capped at 8 atoms**, and refuses loudly above that rather
  than silently returning a non-canonical form.

## The categorical structure, and why it is load-bearing

The claim is not that chemistry can be *described* with category theory. It is that the
structure **prevents defects that description would only document**.

| Property | Enforced by | Test |
|---|---|---|
| Mass and charge conserved | `Reaction.__post_init__` | `test_laws.py::TestConservationTheorem` |
| Conservation survives composition | transitivity of `∘` | `::test_composition_inherits_conservation` |
| Conservation survives tensor | additivity of `⊗` | `::test_tensor_inherits_conservation` |
| Category laws | `path` concatenation | `::TestCategoryLaws` |
| Symmetric monoidal laws | `Config` canonicalisation | `::TestMonoidalLaws` |
| Catalysis decidable | `is_catalytic` | `::TestCatalysis` |
| Comonad laws | `Store` | `test_store.py::TestComonadLaws` |
| Response surfaces via `extend` | `survey` | `test_store.py::TestResponseSurface` |
| Monad laws | `Pathway` | `test_pathway.py::TestMonadLaws` |
| Certificate survives `bind` | `Tally` monoid | `test_pathway.py::TestCertificateSurvivesBind` |
| **Energy is a monoidal functor** | `thermo` | `test_functor.py::TestMonoidalFunctor` |
| **ΔE is additive along a path** | `∘` → `+` | `test_functor.py::TestFunctoriality` |
| **Conservation licenses the subtraction** | `Reaction` + `ΔE` | `test_functor.py::TestConservationLicensesSubtraction` |
| Systematic error cancels, random doesn't | `Estimate` | `test_functor.py::TestSystematicVsRandomError` |
| Basis choice follows the elements | `resolve_basis` | `test_basis_policy.py::TestResolution` |

**The theorem.** Conservation is checked once, on generators, in the `Reaction`
constructor. Every composite inherits it:

```
f : A → B conserves,  g : B → C conserves   ⟹   g∘f : A → C conserves    (transitivity)
f : A → B, g : C → D conserve               ⟹   f⊗g : A⊗C → B⊗D conserves (additivity)
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

The strongest claim here, and the one that took longest to find. Energy is a **monoidal
functor** from the reaction category to `(ℝ, +)`:

```
E(A ⊗ B) = E(A) + E(B)          ΔE(f: A→B) = E(B) − E(A)
ΔE(g∘f)  = ΔE(f) + ΔE(g)        ΔE(f⊗g) = ΔE(f) + ΔE(g)
```

Total energy has an **arbitrary zero** set by atom content — PySCF puts CO near −3074 eV,
the legacy heuristic near −11 eV, and both are right on their own reference. So `E(B) − E(A)`
is physically meaningful *only* when A and B hold the same atoms. That is exactly what
`Reaction` enforces at construction.

```python
>>> o.energy(Molecule.diatomic("C","O", order=3))   # -3082.5872 eV   arbitrary zero
>>> o.energy(Molecule.atom("C"))                    # -1029.3330 eV   arbitrary zero
>>> reaction_energy(Reaction(Config.atoms("C","O"), Config.of(co)), o)
-11.1199 +/- 0.0410 eV        # experiment: -11.157
```

An 11 eV answer extracted as the difference of two ~3000 eV numbers, correct to five
significant figures, because the arbitrary parts cancel. Shift every atomic reference by a
million eV and no reaction energy moves at all
(`test_functor.py::test_offsets_cancel_regardless_of_their_size`).

**So conservation is not a safety check bolted onto a chemistry model — it is the
precondition that makes the energy functor well defined**, and functoriality is what makes a
multi-step mechanism's energy *equal* the sum of its steps rather than merely be reported
next to them.

## Architecture

```
Search & verification    pathway.py · store.py    mechanisms, catalysis, response surfaces
Categorical core         category.py              SMC — conservation enforced here
Oracle interface         oracle/                  pluggable, provenance + error bar
  ├─ heuristic           the frozen baseline, kept measurable
  ├─ pyscf_oracle        HF / MP2 / CCSD / CCSD(T), cc-pVXZ ± aug ± tight d, CBS
  └─ (xtb, tight-binding)                                          not yet implemented
Data                     atoms.py                 NIST ionization / affinity data
                         data/reference.py        experiment + declared train/test split
                         data/basis_tight_d.py    vendored (X+d) sets for Al–Ar
Frozen baseline          legacy.py                the original engine. Do not build on it.
```

An oracle may **decline** but may not **invent**. Refusals are counted separately in the
benchmark, so ducking the hard cases cannot improve a score.

## Install and run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # core + tests
pip install -e '.[dev,qc]'       # + PySCF for the accurate tiers

pytest -q                        # fast suite
pytest -q --runslow              # + real oracle calls (minutes, needs PySCF)
python -m smartchem.bench --split test
```

`--split test` matters: the reference set declares a train/test split, and quoting a
number without saying which set produced it is how the first version of this table became
incomparable across its own rows.

## Status

The categorical core, the Store comonad, the mechanism-search monad, the oracle interface
and the basis policy are complete and tested.

**The legacy engine was retired on 2026-07-20.** Seven modules (`engine`, `comonad`,
`lattice`, `monad`, `network`, `molecule`, `electrochem`) and twelve demo scripts were
removed; the code path needed to reproduce the baseline was consolidated into
`smartchem/legacy.py` and is byte-identical to the original `propose_bond`.

That distinction is the point. **Deleting the module that fails a test is not the same as
fixing it** — a capability that disappears during a cleanup is indistinguishable from one
that never existed. So each of the 28 findings from the original review carries an explicit
verdict, and both kinds are pinned by tests in `tests/test_findings.py`:

- **13 discharged** — F1 conservation, F2 environment response, F3 catalysis evidence,
  F4 certificate survival, F5 measured energies, F11 bond topology. Each now asserted
  against the live system, unmarked, passing.
- **9 dropped** — F6 valency, F7 ionization search, F8 the lattice gate, F9 photolysis,
  F10 band gaps. Recorded in `RETIRED` and asserted *absent*, so none can creep back
  unmeasured.
- **6 dissolved** — F12's crash surface lived in the demo scripts that were removed.

The frozen baseline's exact MAE on every split is pinned, because the headline claim is a
*comparison*, and a comparison is only checkable while both sides still run.

Remaining: a tight-binding oracle for the fast tier, an `xtb` backend, polyatomic support
in the oracle interface, and pricing bond order.

## Origin

The first implementation was generated by Antigravity and reviewed adversarially on
2026-07-20. The review found the categorical machinery had zero call sites — `bind`,
`extend`, `map`, `Poset.leq`, `is_favorable` were all dead — while the documentation
claimed chemical accuracy the code missed by 76×.

The atomic data was genuinely good (36 NIST values, zero errors > 0.06 eV) and the textbook
formulas were correctly transcribed. Those were kept. See `THE_ORBITAL.md` for the current
specification and `THE_DIFFERENCE.md` for an honest comparison against neighbouring tools.
