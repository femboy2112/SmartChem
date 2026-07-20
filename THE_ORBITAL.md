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

The previous specification claimed a Store comonad. The code implemented a **Coreader**:

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

## VII. ENERGY — a pluggable oracle

→ `smartchem/oracle/`, `smartchem/thermo.py`, `tests/test_thermo.py`

The categorical layer is oracle-agnostic. The same conservation reasoning and the same
search machinery run on a microsecond heuristic or on CCSD(T)/CBS.

```
E(config)  = −Σ dissociation energies of the bonds present
ΔH(A → B)  = E(cod) − E(dom)
```

Two rules:

- **Declining is allowed; inventing is not.** An unpriceable species returns `None`, and
  partial pricing refuses the whole configuration — silently skipping a bond would
  understate the energy, which is the failure mode where a wrong number looks right.
  → `::test_unpriceable_bond_refuses_the_whole_configuration`
- **Every value carries provenance and uncertainty**, and a verdict never outruns its own
  error bar. → `::TestVerdictRespectsUncertainty`

Measured accuracy is in `README.md`. Chemical accuracy (1 kcal/mol) is reached by
CCSD(T)/cbs(TZ,QZ) at ~100 s per diatomic.

## VIII. WHAT THIS SPECIFICATION DOES NOT CLAIM

- **No adjunction between the environment comonad and an effect monad.** The previous
  version asserted one. Establishing it requires a distributive law `λ : T∘W ⇒ W∘T`, which
  has not been constructed or checked here. The claim is withdrawn rather than restated.
- **No lattice join/meet as frontier orbitals.** `Poset` in the legacy module computes a
  Parr–Pearson charge-transfer energy, which is identically zero for homonuclear pairs and
  so cannot describe A–A bonding at all. Making join/meet genuine bonding and antibonding
  orbitals requires an electronic-structure method at that layer. Not yet done.
- **No prediction of novel phenomena.** The system computes energetics for structures it is
  given and verifies structural properties of proposed mechanisms. It does not propose
  chemistry no one has thought of.
