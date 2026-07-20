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

| tier | MAE (eV) | MAE (kcal/mol) | n |
|---|---|---|---|
| legacy heuristic | 4.5455 | 104.83 | 4 of 7 (3 refused) |
| HF/cc-pVQZ | 2.5814 | 59.53 | 7 |
| CCSD(T)/cc-pVTZ | 0.2186 | 5.04 | 7 |
| CCSD(T)/cc-pVQZ | 0.0763 | 1.76 | 7 |
| **CCSD(T)/cbs(TZ,QZ)** | **0.0562** | **1.30** | 7 |
| CCSD(T)/aug-cbs(TZ,QZ)+d | 0.1277 | 2.94 | 7 |

The recommended tier costs **57.7 s/species** on 8 cores; the augmented tier costs
294.7 s/species. (Those two were measured with nothing else running. The intermediate
tiers' MAE values are exact — they are deterministic — but their wall-clock was measured
while other jobs shared the machine, so it is not quoted here.)

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

- **No molecular geometry.** Bond lengths are supplied as input, not predicted.
  `optimize_geometry=True` removes that input at ~6× cost.
- **No polyatomic quantitative work — but no longer for a structural reason.** The oracle
  primitive is now the energy of a *species*, so the interface expresses polyatomics fine.
  What is missing is a geometry source: `PySCFOracle` resolves coordinates from a table of
  diatomics and declines anything it cannot place. That is a gap to fill, not a wall.
- **Bond order reaches the oracle, but not every backend uses it.** The object carries its
  topology and the oracle receives the whole species, so a bond-additive oracle prices
  C–C and C=C differently. `PySCFOracle` still keys geometry on formula, so it does not yet
  distinguish them — now a backend limitation rather than an interface one.
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
