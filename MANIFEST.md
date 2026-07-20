# MANIFEST — what is in this repository and why

A map of the code, written so someone (including a future session) can find the load-bearing
parts without reading 8,900 lines. For *what the system claims and what was measured*, read
`README.md`; for the argument, `THE_DIFFERENCE.md`; for the categorical structure,
`THE_ORBITAL.md`.

## The one-paragraph version

SmartChem is a **compositional layer above quantum chemistry**, not a replacement for it.
Chemical configurations are objects in a symmetric monoidal category, reactions are
morphisms that *cannot* violate conservation, and the energy model is a pluggable oracle.
The categorical structure is not decoration: it is what makes a mass-violating reaction
unconstructible rather than merely undetected, and what lets the same reasoning run on a
microsecond heuristic or on CCSD(T)/CBS. Accuracy is a dial, not a property.

## Layers

```
Layer 3  Search & verification    pathway.py · store.py · bench.py
Layer 2½ Domain instances          cell.py                (chemistry meets circuit)
Layer 2  Categorical core         category.py · thermo.py
Layer 1  Energy oracle            oracle/base.py + heuristic.py + pyscf_oracle.py
                                  oracle/caching.py    (wraps any tier of the dial)
                                  oracle/persistent.py (and outlives the process)
Layer 1' Structure                geometry.py            (seed → relax → certify)
Layer 0  Data                     atoms.py · data/reference.py · data/basis_tight_d.py
```

Nothing in Layer 2 or 3 knows which oracle it is talking to. That is the whole design.

## Modules, in dependency order

| File | Lines | What it is |
|---|---:|---|
| `smartchem/atoms.py` | 149 | Periodic-table data. Ionization energies, affinities, radii. Kept from the original build; the data was always good. |
| `smartchem/data/reference.py` | 438 | **Experimental ground truth.** Diatomic D₀, band gaps, diatomic geometries, and polyatomic enthalpies of formation at 0 K (16 species; the C3 entries from ATcT, the rest CCCBDB). Every accuracy claim is measured against this file. |
| `smartchem/data/basis_tight_d.py` | 1111 | Tight-d basis augmentation for second-row elements. Generated data, not hand-written. |
| `smartchem/category.py` | 915 | **The load-bearing layer.** `Molecule` (atoms + bond topology + charge + opaque internal state), `Config` (multiset of molecules), `Reaction` (morphism with conservation enforced in the smart constructor). Composition, tensor, braiding, identity. Canonicalisation by symbol class, refined by Weisfeiler-Leman colour when that is not enough. Plus the structural predicates `is_bond_order_conserving`, `is_isodesmic`, `is_catalytic`. |
| `smartchem/geometry.py` | 545 | **Seed → relax → certify.** VSEPR-based coordinate seeding from the bond graph, Cartesian L-BFGS relaxation, Eckart-projected harmonic analysis. Deliberately PySCF-free so two of its three stages test without quantum chemistry. |
| `smartchem/oracle/base.py` | 257 | The `EnergyOracle` protocol and `Estimate` — a value with an uncertainty *and* a signed systematic channel. Plus the guard that makes oracles decline what they cannot value. |
| `smartchem/oracle/heuristic.py` | 117 | The original algebraic model, preserved unchanged as the baseline every later oracle must beat. |
| `smartchem/oracle/caching.py` | 109 | Prices each distinct species once per search. Measured 33.5× on a 45-reaction network; the saving rests entirely on canonicalising the cache key. |
| `smartchem/oracle/persistent.py` | 232 | The same functor law applied across *time*: species energies survive the process that paid for them. The caching is trivial; the key is the whole problem, and it carries the full tier provenance so a cheap number can never be served to an expensive question. |
| `smartchem/oracle/pyscf_oracle.py` | 707 | Real quantum chemistry. HF / MP2 / CCSD(T), basis-set extrapolation, geometry optimisation, polyatomic support. |
| `smartchem/cell.py` | 243 | **The AA battery litmus.** An electrochemical cell as two half-reactions that compose. Voltage from the *factorisation* (`n` lives in the path, not the endpoints), operating point under load, capacity from stoichiometry. Where the chemistry and the circuit turn out to be one object. |
| `smartchem/thermo.py` | 169 | The **strong monoidal functor** from the category to the additive reals. Where structure meets energy. |
| `smartchem/store.py` | 226 | The **actual** Store comonad, `(Env, Env → a)`. One local definition yields a whole response surface. |
| `smartchem/pathway.py` | 282 | Multi-step mechanism search through genuine monadic `bind`, with the certificate as a monoid so it survives composition. |
| `smartchem/bench.py` | 196 | `python -m smartchem.bench` — held-out MAE per oracle, printed with error bars. |
| `smartchem/legacy.py` | 342 | **Frozen.** The original engine, reduced to the path needed to reproduce its defects. Do not build on it; it exists so the regression tests have something to fail against. |

## The three ideas worth knowing

**1. Objects carry bond topology, not just atom counts.**
If an object were a bag of atoms, every mass-conserving reaction would be an endomorphism —
`Na + Cl` and `NaCl` would be *the same object*, so the reaction between them could not be a
morphism at all. Giving objects structure is what makes `Na + Cl → NaCl` a genuine arrow.
It also turned out to be the geometry source: a bond graph is exactly what a coordinate
seeder consumes.

**2. `Estimate` is a product of three monoids.**
`(ℝ,+) × (ℝ≥0, hypot) × (ℝ,+)`. Values add; *random* errors combine in quadrature; *systematic*
corrections add **with sign**. Quadrature is only valid for independent errors, so keeping the
systematic channel separate is what lets a basis-extrapolation correction cancel between a
molecule and its free atoms while a zero-point-energy bias correctly does *not* — with no
special-casing anywhere.

**3. The categorical layer is not about chemistry, and that is checked, not claimed.**
Objects are labelled graphs over opaque symbols with an integer charge and an opaque
internal state; conservation is over composition and charge only. So the same machinery
that makes `Fe + O + Cl → FeO` unconstructible makes a Kirchhoff-violating node
unconstructible, and a series RC differs from a parallel RC for exactly the reason `Na +
Cl` differs from `NaCl`. `tests/test_domain_neutral.py` instantiates the category on
radiation and on circuits and runs the real laws over them — because an audit that
`category.py` imports only the standard library was *true* while the structure still
could not express a radiating antenna. What foreclosed it was not an import; it was that
the conserved signature and the state label were the same field.

**4. A cell voltage lives in the factorisation, not in the reaction.**
`Zn + 2 MnO2 → ZnO + Mn2O3` does not mention electrons — they appear on both sides of the
composite and cancel as spectators. So no function of `(dom, cod)` can recover `n`, and no
function of `(dom, cod)` can return a voltage. `Reaction.path` still holds the intermediate
configuration, which is where the electrons are. That is not a limitation to route around:
a cell voltage genuinely is undetermined by the overall chemistry, depending on how the
cell splits it into half-cells. And with energy in eV and charge in electrons, `ΔG = −nFE`
collapses to `E[V] = −ΔE[eV] / n` with no physical constant at all.

**5. Getting a geometry is three problems, not one.**
Seed (combinatorics, no wavefunction) → relax (needs gradients) → certify (needs a Hessian).
Only one touches an oracle, and never the expensive one. Candidate generation never upgrades
proof status: VSEPR proposes, the frequency analysis disposes. An imaginary frequency means
the structure is a saddle, not a molecule — and the imaginary mode's eigenvector points
downhill, so the diagnosis and the repair are the same object.

## Tests — 463 fast, 10 slow

| File | Covers |
|---|---|
| `test_laws.py` | Category/SMC/monad/comonad laws; conservation under composition and tensor (hypothesis); canonicalisation exactness against brute force over all n! |
| `test_findings.py` | One named regression test per defect found in the original build |
| `test_functor.py` | Strong monoidal functor laws; spectator cancellation |
| `test_geometry.py` | Seeding, relaxation, Eckart projection, harmonic analysis, the mode-following repair |
| `test_reference.py` | The reference data itself — two-source, internal-algebra, and physical-sanity checks |
| `test_shortcuts.py` | The measured structural shortcuts and their controls |
| `test_domain_neutral.py` | The category instantiated on radiation, Kirchhoff's current law, and RC/LC networks — neutrality demonstrated rather than asserted |
| `test_caching.py` | The species cache: that it saves, that it changes nothing, and where it decays |
| `test_persistent.py` | The disk cache, tested where it can hurt — ordered by how bad the failure would be, key discipline first and "it caches" last |
| `test_cell.py` | The AA battery across coherent scenarios — structure, voltage, load sweep, power balance, capacity — plus the heuristic oracle's measured failure on it |
| `test_network.py` | A **falsified** architectural prediction, kept: the energy functor's shape does not transfer to impedance. Energy is extensive, so one monoid serves both ⊗ and ∘; impedance needs a pair, and the additive law is 31.9× wrong on a parallel RC |
| `test_thermo.py`, `test_store.py`, `test_pathway.py`, `test_basis_policy.py` | Their respective modules |

```bash
python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
pytest -q                 # fast suite
pytest -q --runslow       # includes real wavefunction calibration
python -m smartchem.bench # held-out MAE per oracle
```

**`--runslow` matters.** The slow tests were silently broken for several sessions because
the fast suite passed and nobody ran them. `tests/conftest.py` warns about exactly this.

## Working rules this repo is held to

These are not aspirations; they are why the numbers here are worth anything.

- **A claim without a passing test does not ship.** Every quantitative statement in the
  `.md` files cites the test that holds it down.
- **Pre-register predictions, and keep the falsified ones on the record.** P3 (bond
  conservation helps *more* on polyatomics) was predicted and measured false; it is still
  written down, in the docstring of the thing it was wrong about. So is the assumption
  that the energy functor's shape generalises to other physical quantities — `test_network.py`
  is the autopsy, and the 31.9× is quoted rather than softened.
- **Calibrate the instrument before believing its readings.** Code that measures physics is
  a scientific instrument. The harmonic analysis was checked to 0.000 cm⁻¹ against an
  independent implementation before any of its numbers were used.
- **Size-control a ratio before attributing it to the variable under test.** A headline of
  16.30× became 2.48× when the arms were matched for reaction magnitude. The control changed
  the answer by 6.6×.
- **Reference data is derived in code, from the measured quantity, with tests on the
  derivation** — never transcribed from memory. See the ethanol near-miss documented in
  `data/reference.py`.
- **The one unforgivable defect is a silent wrong answer.** Refusing loudly is always
  allowed; returning something plausible and unearned never is.
