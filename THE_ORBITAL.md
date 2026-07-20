# THE ORBITAL

*Specification of SmartChem's categorical core.*

Every claim in this document names the test that backs it. A claim without a test does not
belong here — that rule is what separates this version from the one it replaces, which
described a system considerably more capable than the one that shipped.

> **Thesis.** A chemical reaction is a morphism in a symmetric monoidal category whose
> objects carry bond topology. Conservation is enforced at construction, so it holds for
> every composite by theorem rather than by vigilance. The environment is a Store comonad,
> so one local definition yields an entire response surface. Mechanism search is a
> Writer-over-List monad, so energy bookkeeping and provenance cannot drift out of step
> with the route. Energy is supplied by a pluggable oracle, so accuracy is a dial.

---

## I. THE CATEGORY — objects

**Objects are configurations: multisets of molecules, each with explicit bond topology.**
→ `smartchem/category.py`, `tests/test_laws.py::TestObjectStructure`

```
Bond      = (i, j, order)              positions within one molecule
Molecule  = (atoms, bonds, charge)     one connected species
Config    = multiset of Molecule       the contents of the vessel — the OBJECT
```

Topology is load-bearing, not ornamental. Were an object a bare bag of atoms, `Na + Cl` and
`NaCl` would be the *same object*; every conserving reaction would be an endomorphism and
there would be nothing to reason about. That was a real defect in the previous
implementation, where every computed "product" was its own reactants.
→ `::test_bonded_and_unbonded_are_distinct_objects`

`Config` canonicalises its species multiset, and `Molecule` canonicalises under relabelling,
so equality is structural and deterministic. The predecessor used a `frozenset`, whose
iteration order varies with `PYTHONHASHSEED`.
→ `::test_canonical_form_is_order_independent`

Canonicalisation is brute-force over permutations and is capped at 8 atoms. Above the cap it
raises rather than returning something non-canonical.
→ `::test_large_molecule_refuses_rather_than_lies`

## II. THE CATEGORY — morphisms and the conservation theorem

A morphism `f : A → B` is a reaction. The constructor enforces:

```
formula(dom) == formula(cod)      atoms conserved
charge(dom)  == charge(cod)       charge conserved
```

**The theorem.** Checked once on generators, inherited by every composite:

```
f : A → B, g : B → C conserve   ⟹   g∘f : A → C conserves      (transitivity)
f : A → B, g : C → D conserve   ⟹   f⊗g : A⊗C → B⊗D conserves   (additivity)
```

→ `::test_composition_inherits_conservation`, `::test_tensor_inherits_conservation`,
verified against hypothesis-generated chains rather than examples.

A violating reaction is therefore **unconstructible**, not merely absent.
→ `::test_violating_reaction_is_unconstructible`, `::test_charge_violation_is_unconstructible`

Morphisms carry their **path** — the sequence of elementary steps traversed. Two mechanisms
with identical endpoints stay distinct, which mechanism search requires. It also makes the
category laws hold for the right reason: associativity is associativity of concatenation,
and the identity laws hold because the empty tuple is its unit.
→ `::TestCategoryLaws`

Composition is defined only when `cod(f) == dom(g)`; a mismatch raises.
→ `::test_composition_rejects_mismatch`

## III. THE MONOIDAL STRUCTURE

`A ⊗ B` is both configurations in one vessel; the unit `I` is the empty vessel.
→ `::TestMonoidalLaws`

Symmetry `A ⊗ B ≅ B ⊗ A` holds **on the nose**, because `Config` canonicalises its multiset.
The braiding is therefore an identity. That is the honest statement — the previous version
claimed a symmetric monoidal structure without anything checking it.
→ `::test_symmetry`, `::test_braid_is_well_typed`

## IV. THE ENVIRONMENT — a Store comonad

→ `smartchem/store.py`, `tests/test_store.py`

The first specification claimed a Store comonad. The code implemented a **Coreader** (now
frozen in `smartchem/legacy.py` with its inert `extend` removed):

```
Coreader   W a = (a, e)         a value, and the environment it sits in
Store      W a = (e → a, e)     a way to compute the value at ANY environment,
                                plus the one currently in focus
```

Coreader is a lawful comonad and its laws did hold. But its `extend` can only ever see the
single environment it was handed, so it computes one answer. Store re-focuses everywhere, so
`extend` turns one local definition into the **entire response surface** — solvent series,
phase diagram, pressure sweep.

```
extract : W a → a                 the value here
extend  : (W a → b) → W a → W b   that value, computed everywhere
```

→ `::TestComonadLaws` (checked extensionally — function equality is undecidable, so laws are
verified by agreement at sampled positions)

`survey` and `response_surface` are implemented **through** `extend`. Remove `extend` and they
fail. In the predecessor, `extend` had zero call sites and every test still passed.
→ `::TestResponseSurface`

**Flat surfaces are detectable.** `is_responsive` flags a property that does not vary across
a swept axis, which is nearly always a branch ignoring the variable. This is the structural
detector for the defect where NaCl returned byte-identical energies across dielectric 1.0 →
109.0.
→ `::TestResponsiveness`

## V. MECHANISM SEARCH — a Writer-over-List monad

→ `smartchem/pathway.py`, `tests/test_pathway.py`

```
Pathway a = WriterT Tally []
```

The **list** branches over competing mechanisms; the **writer** accumulates a `Tally`
(energy, uncertainty, provenance) along each branch.

`Tally` is a **monoid**, and that is load-bearing rather than pedantic: it is the
precondition for a lawful Writer, and it is what makes the certificate survive composition.
The predecessor's `bind` rebuilt its result without carrying `metadata`, so the "rigorous
mathematical certificate" was destroyed by the first compose.
→ `::TestTallyMonoid`, `::TestCertificateSurvivesBind`

Uncertainty adds in quadrature, treating step estimates as independent. Stated as an
assumption rather than buried: correlated errors would add closer to linearly, so a long
route's reported uncertainty is a lower bound.

`bind` is the only mechanism by which pathways compose.
→ `::TestMonadLaws`, `::TestSearch`

## VI. CATALYSIS — decided, not asserted

A catalytic step is a morphism `C ⊗ S → C ⊗ P`: the catalyst appears in source and target
with equal multiplicity. This is a **structural property, decided by inspection**.

`catalytic_cycles` returns the composed morphism as evidence, so the caller can re-check it
independently. The predecessor printed *"Catalytic Loop Closed mathematically"* with no
computation behind it, on a supporting edge that had silently lost its nitrogen.
→ `::TestCatalysis`, `::TestCatalyticCycles`

A structural verdict says the catalyst survives the step. It says nothing about whether the
step is kinetically or thermodynamically accessible — those are the oracle's business and
are reported separately.

## VII. ENERGY — a monoidal functor

→ `smartchem/oracle/`, `smartchem/thermo.py`, `tests/test_functor.py`

The categorical layer is oracle-agnostic. The same conservation reasoning and the same
search machinery run on a microsecond heuristic or on CCSD(T)/CBS.

Energy is a **strong monoidal functor** from the category to the additive reals:

```
E  : Ob(C) → ℝ        E(A ⊗ B) = E(A) + E(B),  E(I) = 0
ΔE : C(A,B) → ℝ       ΔE(f : A → B) = E(B) − E(A)

ΔE(g∘f)   = ΔE(f) + ΔE(g)      functoriality — energy is a path integral, by law
ΔE(f⊗g)   = ΔE(f) + ΔE(g)      monoidality
ΔE(id_A)  = 0                  identity
```

→ `::TestMonoidalFunctor`, `::TestFunctoriality`

**Conservation is what makes this well defined, and that is the load-bearing claim.**
Total energy carries an arbitrary zero fixed by atom content — PySCF puts CO near
−3074 eV, the legacy heuristic near −11 eV, and both are correct on their own reference.
`E(B) − E(A)` is physical *only* when A and B hold the same atoms, which is exactly what
`Reaction.__post_init__` enforces. The per-atom offsets then appear identically on both
sides and cancel.

So the conservation theorem is not a safety check bolted onto a chemistry model. It is the
**precondition that licenses the subtraction**. Shift every atomic reference by a million
eV and no reaction energy moves at all.
→ `::TestConservationLicensesSubtraction::test_offsets_cancel_regardless_of_their_size`

The oracle primitive is the energy of a **species**, not of an atom pair. That was
previously `estimate(symbols) -> D0`, which made bond additivity an assumption of the
architecture: polyatomic species were structurally unreachable, bond order could not be
priced, and the energy of an object was a sum over edges. A bond-additive oracle still
answers by summing over edges — see `HeuristicOracle` — but that is now a visible property
of one oracle rather than a hidden commitment of the framework.
→ `tests/test_thermo.py::TestBondOrderReachesTheOracle`

Dissociation energy is **derived**: `D₀ = E(free atoms) − E(molecule)`.

Two rules:

- **Declining is allowed; inventing is not.** An unpriceable species returns `None`, and
  partial pricing refuses the whole configuration — silently skipping a bond would
  understate the energy, which is the failure mode where a wrong number looks right.
  → `::test_unpriceable_bond_refuses_the_whole_configuration`
- **Every value carries provenance and uncertainty**, and a verdict never outruns its own
  error bar. → `tests/test_thermo.py::TestVerdictRespectsUncertainty`

**Systematic and random error are tracked separately**, because they combine differently.
`uncertainty_ev` is random and adds in quadrature; `extrapolation_ev` is a signed
systematic model correction that adds with sign and *cancels* in a conserving difference,
exactly as the energy zero does. Whatever survives that cancellation widens the error bar.
→ `tests/test_functor.py::TestSystematicVsRandomError`

This was measured into existence rather than designed in. `cbs(TZ,QZ)` reported NaCl at
4.3806 ± 0.041 eV against an experimental 4.234 — 3.6σ wrong, with full confidence —
because the flat tier-average bar said nothing about *that* species. Plain `cc-pVQZ`
without extrapolation lands at +0.39 kcal/mol where the extrapolated value lands at +3.38:
the extrapolation degraded a good answer, since its premise (smooth X⁻³ convergence by TZ)
fails for an ionic species. The correction is now its own error bar — no fitted constant —
so NaCl reports ±0.13 eV and H₂, which is fully converged, keeps ±0.041.

**Basis choice is a function of the elements, not a global setting.** Extrapolation removes
only the error the basis family is converging toward; diffuse-function and tight-*d*
deficiencies are present at *every* cardinal and survive it. Both are properties of the
elements involved, so `resolve_basis` computes the basis per element — the same move the
category makes elsewhere: let the type of the object decide.
→ `tests/test_basis_policy.py`

The policy declines rather than guesses: at a cardinal with no vendored (X+d) set it
returns the standard basis instead of substituting a different one.
→ `::test_declines_when_no_variant_is_vendored`

Measured accuracy is in `README.md`.

## VIII. WHAT WAS RETIRED, AND WHAT THAT COST

On 2026-07-20 the legacy engine was retired: seven modules (`engine`, `comonad`, `lattice`,
`monad`, `network`, `molecule`, `electrochem`) and twelve demo scripts were removed, and the
code path needed to reproduce the baseline was consolidated into `smartchem/legacy.py`.

Retirement is **not** a fix. Deleting the module that fails a test removes the failure, not
the defect, and a capability that disappears during a cleanup is indistinguishable from one
that never existed. So every finding carries an explicit verdict, and both kinds are pinned
by tests.
→ `tests/test_findings.py`

**Discharged** — the capability exists now, and the test asserts it against the live system:
F1 (conservation, unconstructible), F2 (`Store.extend` + `is_responsive`), F3
(`catalytic_cycles` returns re-checkable evidence), F4 (`Tally` monoid), F5 (measured
oracle), F11 (bond topology).

**Dropped** — the capability is gone and the claim is withdrawn: F6 (environment-responsive
valency), F7 (multi-electron ionization search), F8 (the frontier-orbital lattice gate),
F9 (photolysis and allotropes), F10 (solid-state band gaps), F12 (the crash surface, which
lived in the demo scripts). Recorded in `test_findings.py::RETIRED` and asserted absent by
`::TestRetiredCapabilitiesAreGone`, so none can creep back unmeasured.

The frozen baseline is byte-identical to the original `propose_bond`, and its exact MAE on
each split is pinned — because the headline claim is a *comparison*, and a comparison is
only checkable while both sides still run.
→ `::TestBaselineIsPreserved`

## IX. WHAT THIS SPECIFICATION DOES NOT CLAIM

- **No adjunction between the environment comonad and an effect monad.** The first version
  asserted one. Establishing it requires a distributive law `λ : T∘W ⇒ W∘T`, which has not
  been constructed or checked here. The claim is withdrawn rather than restated.
- **No lattice join/meet as frontier orbitals.** `Poset` computes a Parr–Pearson
  charge-transfer energy, which is identically zero for homonuclear pairs and so cannot
  describe A–A bonding at all. Making join/meet genuine bonding and antibonding orbitals
  requires an electronic-structure method at that layer. `is_favorable` and `leq` were
  removed outright in the retirement; only the two statics the baseline calls remain.
- **No prediction of novel phenomena.** The system computes energetics for structures it is
  given and verifies structural properties of proposed mechanisms. It does not propose
  chemistry no one has thought of.
