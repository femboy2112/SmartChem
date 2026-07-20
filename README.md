# SmartChem

A compositional layer above quantum chemistry: a reaction algebra where conservation is
enforced by construction, catalysis is a decidable property, and accuracy is a dial you
set rather than a property you inherit.

```python
from smartchem.category import Config, Molecule, Reaction
from smartchem.thermo import favourability
from smartchem.oracle.pyscf_oracle import PySCFOracle

rxn = Reaction(Config.atoms("C", "O"),
               Config.of(Molecule.diatomic("C", "O", order=3)))

favourability(rxn, PySCFOracle("CCSD(T)", "cbs(TZ,QZ)"))
# 'exothermic (-11.120 +/- 0.041 eV)'      experiment: -11.157 eV
```

---

## Measured accuracy

Every number below was produced by `python -m smartchem.bench` on this repository, against
experimental dissociation energies from NIST/CRC. None of them is a vendor claim.

| oracle | MAE (eV) | MAE (kcal/mol) | sec/species | n |
|---|---|---|---|---|
| legacy heuristic | 3.4950 | 80.60 | 0.000 | 6 of 11 (5 refused) |
| HF/cc-pVDZ | 2.4402 | 56.27 | 0.14 | 3 |
| CCSD(T)/cc-pVDZ | 0.5745 | 13.25 | 1.31 | 3 |
| CCSD(T)/cc-pVTZ | 0.1912 | 4.41 | 5.59 | 5 |
| CCSD(T)/cc-pVQZ | 0.0790 | 1.82 | 23.57 | 5 |
| **CCSD(T)/cbs(TZ,QZ)** | **0.0411** | **0.95** | 99.60 | 10 |

Chemical accuracy (1 kcal/mol) is reached, at roughly a minute and a half per diatomic.

Where CBS still misses is systematic and understood, not noise. Three of ten fall outside
1 kcal/mol: **NaCl** +3.38 (ionic — wants diffuse functions, `aug-cc-pVXZ`), **CS** −1.53
(second-row sulfur — wants tight *d* functions, `cc-pV(X+d)Z`), **N₂** −1.19 (a hard
correlation case). First-row covalent species land between 0.01 and 0.86 kcal/mol.

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

Stated plainly, because the previous version of these docs did not.

- **No molecular geometry.** Bond lengths are supplied as input, not predicted.
  `optimize_geometry=True` removes that input at ~6× cost.
- **No polyatomic quantitative work.** The oracle interface covers diatomics.
- **Bond order is not priced.** An oracle returns the ground-state diatomic energy for an
  atom pair, so a C–C single bond and a C=C double bond are currently indistinguishable.
  Fixing that means extending the oracle protocol, not adding a scaling factor.
- **No kinetics.** Everything here is thermodynamic. A favourable reaction may still be
  impossibly slow.
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

## Architecture

```
Search & verification    pathway.py · store.py    mechanisms, catalysis, response surfaces
Categorical core         category.py              SMC — conservation enforced here
Oracle interface         oracle/                  pluggable, provenance + error bar
  ├─ heuristic           legacy, kept as a measurable baseline    ~3.5 eV
  ├─ pyscf_oracle        HF / MP2 / CCSD / CCSD(T), any cc-pVXZ, CBS   0.04–2.4 eV
  └─ (xtb, tight-binding)                                          not yet implemented
Data                     data/reference.py        experiment + declared train/test split
```

An oracle may **decline** but may not **invent**. Refusals are counted separately in the
benchmark, so ducking the hard cases cannot improve a score.

## Install and run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # core + tests
pip install -e '.[dev,qc]'       # + PySCF for the accurate tiers

pytest -q                        # 88 passed, 28 xfailed
pytest -q -rx                    # ...with every known defect and its reason
python -m smartchem.bench --split test
```

### The xfail ratchet

28 tests are marked `xfail(strict=True)`. Each pins one defect from the 2026-07-20
adversarial review of the original implementation. This is deliberate:

- **today** — the test xfails; `pytest -rx` lists exactly what is broken, and why.
- **when fixed** — it xpasses, and `strict=True` turns that into a *failure*, forcing the
  marker to be removed in the same commit as the fix.

A defect cannot be quietly fixed, and cannot be quietly left broken. See
`tests/test_findings.py`.

## Status

Stages 1–5 complete. The legacy engine (`engine.py`, `comonad.py`, `lattice.py`,
`network.py`) is retained as the measurable baseline and still carries its original
defects — that is what the 28 xfails track. New work should build on `category.py`,
`store.py`, `pathway.py` and `thermo.py`.

Remaining: a tight-binding oracle for the fast tier, `aug-` and `+d` basis sets to close
the ionic and second-row gaps, and retirement of the legacy modules once nothing depends
on them.

## Origin

The first implementation was generated by Antigravity and reviewed adversarially on
2026-07-20. The review found the categorical machinery had zero call sites — `bind`,
`extend`, `map`, `Poset.leq`, `is_favorable` were all dead — while the documentation
claimed chemical accuracy the code missed by 76×.

The atomic data was genuinely good (36 NIST values, zero errors > 0.06 eV) and the textbook
formulas were correctly transcribed. Those were kept. See `THE_ORBITAL.md` for the current
specification and `THE_DIFFERENCE.md` for an honest comparison against neighbouring tools.
