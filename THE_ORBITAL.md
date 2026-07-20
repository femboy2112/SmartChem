# THE ORBITAL

*Specification of SmartChem's categorical core.*

Every claim in this document names the test that backs it. A claim without a test does not
belong here — that rule is what separates this version from the one it replaces, which
described a system considerably more capable than the one that shipped.

> **Thesis.** A chemical reaction is a morphism in a category of conserving sequential
> histories whose objects carry bond topology. Conservation is enforced at construction,
> so it holds for every sequential composite by theorem rather than by vigilance. Objects
> have a commutative product; morphisms do not yet have a true parallel tensor. The
> environment is represented by Store-style utilities, so one explicitly
> condition-dependent function can be sampled across chosen positions. Mechanism search is
> Writer-over-List-style composition, so route transitions and supplied tally provenance are
> appended together. Energy is supplied by explicit, measured oracle protocols.

---

## I. THE CATEGORY — objects

**Objects are configurations: multisets of molecules, each with explicit bond topology.**
→ `smartchem/category.py`, `tests/test_laws.py::TestObjectStructure`

```
Bond      = (i, j, order)              positions within one molecule
Molecule  = (atoms, bonds, charge, state)  one connected species/state label
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

Canonicalisation has a 50,000-candidate permutation budget. Highly symmetric graphs can
exceed it regardless of raw atom count; refusal is explicit.
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
```

→ `::test_composition_inherits_conservation`, verified against hypothesis-generated chains.

A violating reaction is therefore **unconstructible**, not merely absent.
→ `::test_violating_reaction_is_unconstructible`, `::test_charge_violation_is_unconstructible`

Morphisms carry their **path** — the sequence of elementary steps traversed. Stable,
explicit `generator_id` values let two mechanisms with identical endpoints remain distinct;
without IDs, same-endpoint generators still alias. Path concatenation makes associativity
and identity laws hold for the right reason: the empty tuple is the unit.
→ `::TestCategoryLaws`

Composition is defined only when `cod(f) == dom(g)`; a mismatch raises.
→ `::test_composition_rejects_mismatch`

## III. OBJECT PRODUCT AND SCHEDULED MORPHISMS

`A + B` is multiset union of configurations; the unit `I` is the empty configuration.
→ `::TestObjectProductAndScheduledProduct`

Object commutativity holds on the nose. ``Reaction.scheduled_product`` serializes the left
history before the right. It preserves certificates but fails interchange and symmetry, so
it is not a categorical tensor. The strict-xfail interchange test records the exact debt;
ports/string diagrams are required for the real repair.
→ `::test_symmetry`, `::test_scheduled_product_is_associative_and_unital`,
`::test_true_parallel_interchange_is_architecture_debt`

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
single environment it was handed, so it computes one answer. Store can re-focus a supplied
function at any requested position; `survey` explicitly evaluates a finite solvent series,
phase grid, or pressure sweep. No surface is produced for free, and bundled energy oracles
currently ignore these coordinates.

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
a swept axis. That may be legitimate physics or a branch ignoring the variable; it is a
diagnostic, not a verdict. It catches the historical case where NaCl returned byte-identical
energies across dielectric 1.0 → 109.0.
→ `::TestResponsiveness`

## V. MECHANISM SEARCH — Writer/List-style accumulation

→ `smartchem/pathway.py`, `tests/test_pathway.py`

The exact algebraic model that motivated the implementation is a Writer transformer over
list branching:

```
Pathway a ~ WriterT Tally []
```

The **list** enumerates competing mechanisms; the Writer-style accumulator carries a `Tally`
(energy, uncertainty and provenance) along each branch. Tuple concatenation and method-set
union have exact identities and associative operations. The energy and quadrature fields are
IEEE-754 floats, however, so reassociation can change rounding and sufficiently large values
can leave the validated finite domain. The concrete Python type is therefore not claimed to
be an exact monoid or a lawful Writer monad over all values.

The predecessor's `bind` rebuilt its result without carrying `metadata`, so its claimed
certificate was destroyed by the first composition. The current tests verify representative
branch values, step labels, method sets and energy totals; separate examples cover quadrature
and route history. Comparisons are restricted to finite samples and use float tolerances. The
test-class names retain the earlier algebraic vocabulary for historical continuity; they are
not machine proofs of exact laws.
→ `::TestTallyMonoid`, `::TestCertificateSurvivesBind`

Uncertainty adds in quadrature, treating step estimates as independent. Stated as an
assumption rather than buried: correlated errors can make that result too small or too
large, so it is neither a general bound nor a calibrated coverage interval.

`bind` is the mechanism used by pathway search to extend branches.
→ `::TestMonadLaws`, `::TestSearch`

## VI. STOICHIOMETRIC REGENERATION — decided, not catalysis

``is_regenerated`` decides that a species appears at both endpoints with equal positive
multiplicity. An inert spectator also passes, so this is not evidence of catalysis or rate
enhancement.

`catalytic_cycles` returns the composed morphism as evidence, so the caller can re-check it
independently. The predecessor printed *"Catalytic Loop Closed mathematically"* with no
computation behind it, on a supporting edge that had silently lost its nitrogen.
→ `::TestCatalysis`, `::TestCatalyticCycles`

A structural verdict says only that the candidate species survives. Kinetic catalysis needs
transition states/rates and comparison against an uncatalysed mechanism; neither exists yet.

## VII. ENERGY — an endpoint potential under a separability model

→ `smartchem/oracle/`, `smartchem/thermo.py`, `tests/test_functor.py`

The categorical layer is oracle-agnostic. The same conservation reasoning and the same
search machinery run on a microsecond heuristic or on CCSD(T)/CBS.

The current adapter sums isolated species energies and maps a reaction to its endpoint
difference. A precise codomain is the translation category of real energies:

```
E  : Ob(C) → ℝ        E(A + B) = E(A) + E(B),  E(I) = 0
ΔE : C(A,B) → ℝ       ΔE(f : A → B) = E(B) − E(A)

ΔE(g∘f)   = ΔE(f) + ΔE(g)      endpoint differences telescope
ΔE(id_A)  = 0                  identity
```

→ `::TestSeparableEnergyAdditivity`, `::TestFunctoriality`

**Conservation is what makes this well defined, and that is the load-bearing claim.**
Total energy carries an arbitrary zero fixed by atom content — PySCF puts CO near
−3074 eV, the legacy heuristic near −11 eV, and both are correct on their own reference.
Conservation ensures invariance under permitted per-element reference shifts: the offsets
appear identically and cancel. Open-system inventory changes remain meaningful when
reservoirs and boundary flows are modeled explicitly.

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

Atomization/dissociation energy is **derived** as
`E(free atoms) − E(molecule)` under the oracle's state convention. It is `Dₑ` for
electronic-only energies and approximates `D₀` only when ground-vibrational ZPE is included
consistently; finite-temperature dissociation enthalpy is another quantity.

Two rules:

- **Declining is allowed; inventing is not.** An unpriceable species returns `None`, and
  partial pricing refuses the whole configuration — silently skipping a bond would
  understate the energy, which is the failure mode where a wrong number looks right.
  → `::test_unpriceable_bond_refuses_the_whole_configuration`
- **Every value carries provenance and a nonnegative reported scale.** The type does not
  turn that scale into confidence. Energy-direction formatting reports it separately and
  labels coverage unspecified. → `tests/test_thermo.py::TestEnergyDirectionReporting`

**Systematic and random error are tracked separately**, because they combine differently.
`uncertainty_ev` currently adds in quadrature under an explicit independence assumption.
Named ``systematic_terms`` propagate algebraically only within the same source ID. Opposing
unrelated terms can make the compatibility scalar ``systematic_ev`` zero, but the source
records stay distinct and their absolute magnitudes survive in the reporting floor.
Cancellation of equal correction displacements does not prove cancellation of unknown
residual errors. A calibrated coefficient/covariance model remains roadmap work.
→ `tests/test_functor.py::TestSystematicVsRandomError`

This was measured into existence rather than designed in. An earlier table labeled
`cbs(TZ,QZ)` NaCl as 4.3806 ± 0.041 eV against an experimental 4.234 and treated an MAE like
a calibrated standard deviation. Both the stale aggregate and that confidence reading were
wrong: a flat tier-average MAE says little about *that* species. Plain `cc-pVQZ`
without extrapolation lands at +0.39 kcal/mol where the extrapolated value lands at +3.38:
the extrapolation degraded a good answer, since its premise (smooth X⁻³ convergence by TZ)
was inadequate for this NaCl row. The correction displacement is now a named sensitivity —
not a fitted constant or residual-error bound — so the displayed scalar floor is 0.13 eV
for NaCl while H₂ retains the declared tier MAE of 0.0562.

**Basis choice is a function of the elements, not a global setting.** Extrapolation removes
only the error the basis family is converging toward; diffuse-function and tight-*d*
deficiencies are present at *every* cardinal and survive it. Both are properties of the
elements involved, so `resolve_basis` computes the basis per element — the same move the
category makes elsewhere: let the type of the object decide.
→ `tests/test_basis_policy.py`

The basis resolver avoids inventing a nonexistent (X+d) set: at a cardinal with no vendored
variant it explicitly returns the requested standard basis rather than substituting a
different cardinal. Provenance must retain that policy.
→ `::test_declines_when_no_variant_is_vendored`

Measured accuracy is in `README.md`.

**The endpoint-potential model also decides what not to compute.** No algebra makes a single quantum-chemical
calculation faster. What the laws do is prove, ahead of the expensive layer, that particular
calls cannot affect the answer — the same prune-by-type move the candidate search makes,
turned on the energy itself. Four results, at different levels of proof, and the
distinction between them is the point:

| shortcut | status | evidence |
|---|---|---|
| spectator cancellation | **exact only in separable adapter** | explicit model assumption; shared-quantity scale no longer duplicated |
| geometry/energy separation | **measured — opt-in** | `geometry_tier=`, see §VII table |
| bond-order conservation | **measured, ~2× — decided, not policy** | prediction of >3× falsified |
| geometry seed *from the bond graph* | **internal research path** | `smartchem/geometry.py`; tested vibrational algebra agrees on selected cases, public energies decline |

The fourth is the one where the object's structure pays a debt nobody expected it to. Objects
were given bond topology so that `Na + Cl` and `NaCl` could be distinct and the reaction between
them a genuine arrow — a purely categorical motive. But a bond graph is also exactly what a
geometry builder needs, so the same decision that made conservation enforceable made
candidate coordinates constructible, and an internal polyatomic research path became
reachable. Public polyatomic estimates still decline because the complete protocol lacks
state/conformer coverage and a validation scale. The three sub-steps have
different characters and are kept apart deliberately: the seed is pure combinatorics, the
relaxation needs gradients, and certification needs a Hessian from the same cheap surface.
Both latter steps touch an electronic-structure backend; the final high-level single point
is a separate, explicitly recorded tier.

For `f : S + A → S + B` the shared part cancels in the current separable model, so `E(S)`
is never priced. Interaction energies can invalidate this in a real vessel.
`reaction_residue` finds it from the multiset difference of `dom` and `cod` with no oracle
call. The saving is the smaller half: quadrature is valid only for **independent** terms,
and a spectator's modeled energy is one quantity appearing twice minus itself, not two
samples. Summing both sides before subtracting invented `2·u(S)²` under that independence
assumption. The remaining scalar scale is not automatically a coverage interval.
→ `tests/test_functor.py::TestSpectatorsAreCancelledStructurally`, `tests/test_shortcuts.py`

Two further things are already exploited by construction rather than by code. Telescoping
means the net `ΔE` of an n-step mechanism needs only its **endpoints**, never its
intermediates — `ΔE(g∘f) = ΔE(f) + ΔE(g)` guarantees the two agree. Per-step endpoint
energies can describe energetic changes but cannot identify a rate-limiting step without
barriers and kinetics. And `Config` canonicalises its multiset, so isolated-species
``E(A + B)`` and ``E(B + A)`` use the same structural representation.

One candidate shortcut was examined and **rejected as unnecessary**, recorded so nobody
optimises it later. Reaction energies are extracted as the difference of two total energies
near −3000 eV, which looks like catastrophic cancellation. It is not: float64 carries
~6.8×10⁻¹³ eV of absolute precision at that magnitude, and the binding SCF/CCSD convergence
tolerances (1×10⁻¹⁰ and 1×10⁻⁹ Hartree, i.e. ~2.7×10⁻⁸ eV) are far below the conventional
1 kcal/mol scale. Float64 subtraction loses negligible precision at this magnitude;
iteration tolerances are not rigorous bounds on final electronic energy, so solver residual,
refinement, and model error remain separate checks.

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
(`catalytic_cycles` returns re-checkable regeneration evidence, not proof of catalysis),
F4 (step labels, method provenance and energy survive `bind`; the historical exact-monoid
claim is withdrawn), F5 (measured
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
