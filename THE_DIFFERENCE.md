# THE DIFFERENCE

*Where SmartChem sits relative to neighbouring tools — including where they beat it.*

The first version of this document claimed SmartChem was better than cheminformatics,
better than neural potentials, better than DFT, and better than applied category theory,
on every axis. Adversarial testing on 2026-07-20 falsified the central claims: measured
accuracy was 76× worse than stated, CO was predicted not to bond at all, and the
categorical machinery it claimed as its differentiator had zero call sites.

This version states what is actually true, including the parts that are unflattering.

---

## The honest position

SmartChem is **not** a faster quantum chemistry package. PySCF is a backend here, not a
rival, and on any question of "what is the energy of this molecule" PySCF *is* SmartChem's
answer.

What SmartChem currently adds is a small compositional layer: **closed reactions enforce
atom and net-charge conservation at construction**, sequential histories retain generator
provenance, and route search carries a caller-supplied energy tally alongside each branch.
It can also evaluate an explicitly condition-dependent function over a finite grid. The
structural predicate called `is_catalytic` is a compatibility alias for stoichiometric
regeneration; kinetics and catalytic effect are not decided.

Quantum-chemistry packages do much more than one number for one geometry, but they do not
usually impose this repository's reaction-history type. SmartChem's useful separation is
between structural validation, route bookkeeping and the energy backend. Environmental
sweeps are meaningful only when the supplied computation actually models those conditions.

---

## 1. vs. Cheminformatics (RDKit, Open Babel)

**They do better:** essentially everything about real molecules. SMILES/InChI parsing, ring
perception, stereochemistry, substructure search, conformer generation, fingerprints,
reaction templates, and broad periodic-table support. RDKit handles drug-sized molecules;
SmartChem's validated oracle domain is currently small and method-dependent.

**SmartChem adds:** conservation as a type-level guarantee. RDKit will happily let a
reaction template drop an atom; SmartChem raises `ConservationError` at construction.

**Previously claimed, now withdrawn:** *"We do not hardcode valency."* The legacy
`Atom.valence_cap` was a hardcoded group/period rule including an explicit octet check —
precisely the thing RDKit was criticised for. It took no environment argument and so could
not respond to one. That module was retired on 2026-07-20; the current system models no
valency at all, so the claim is not merely withdrawn but inapplicable.

## 2. vs. Neural potentials (ANI, MACE, AlphaFold3)

**They do better:** speed at scale and domain coverage. A trained potential can evaluate
large systems rapidly and may reach low errors on the observables and chemical domain it
was trained and validated for. That does not transfer automatically out of domain.

**SmartChem adds:** structural guarantees that an unconstrained learned model does not give.
Learned architectures can also encode conservation, so this is an implementation property,
not a limitation of neural methods. A `Tally` records the energy, uncertainty and method
labels supplied for each step; it does not verify that those labels came from an oracle or
that the uncertainties are calibrated.

**Previously claimed, softened:** the "white box" framing was fair, but it was attached to
an engine whose central covalent term was a constant fitted on two data points, with a
comment in the source saying so. Being interpretable is worth little when what is being
interpreted is a curve fit. That engine is now frozen in `smartchem/legacy.py` and used
only as the baseline the accurate tiers are measured against.

## 3. vs. Quantum chemistry (PySCF, ORCA, Gaussian)

**They do better:** much broader electronic-structure physics and tooling. Correlated methods, open-shell
systems, excited states, relativistic treatments, periodic boundary conditions, analytic
gradients, solvation models, and molecules with more than two atoms.

**SmartChem adds:** composition. It can call PySCF and wrap results in structures that track
provenance and enforce conservation across sequential routes. Its Store utilities sample a
user-supplied condition function; they do not make a condition-independent oracle respond
to temperature, pressure or solvent. It also contains an experimental basis-selection
policy keyed by the elements involved — see §5.

**Previously claimed, withdrawn:** *"The Oracle Gate resolves in milliseconds what takes
DFT hours, achieving chemical accuracy through structural entailment."* No. The best
declared in-repository diatomic benchmark row uses CCSD(T) with basis-set extrapolation,
at substantial cost per species, and remains above the conventional 1 kcal/mol threshold.
The algebra contributed none of that electronic-structure accuracy, and benchmark
performance does not guarantee accuracy out of domain. MP2, CCSD, optimized geometries,
and polyatomic computation paths may exist internally, but public estimates fail closed
when the selected protocol lacks a validation scale.

**What survived, in a different form:** there *is* a real speed argument, just not the one
claimed. Invalid `Reaction` objects that violate atom or net-charge conservation fail at
construction, before any oracle call. The current core does not validate valence, generate
reaction candidates, or prove that a conserving reaction is chemically accessible. Search
only explores the supplied valid steps. This can avoid pricing malformed candidates; it
does not make one quantum calculation faster.

## 4. vs. Applied category theory in chemistry (Baez, CRNs, Petri nets)

**They do better:** rigour, generality, and priority. Baez and collaborators have a
developed theory of reaction networks as symmetric monoidal categories, with published
semantics for rates, stochastic dynamics and open systems. SmartChem does not yet implement
that structure: its `Reaction` values form a category of sequential histories, while the
commutative product on `Config` has no lawful parallel morphism tensor. The compatibility
method `Reaction.tensor` is a deterministic left-first schedule and fails interchange and
symmetry, so it must not be read as an SMC operation.

**SmartChem adds:** an executable sequential implementation wired to energy oracles, with
property tests over generated finite examples. Those tests are useful engineering evidence;
they are not machine proofs of general laws and do not supply CRN rates or open-system
semantics.

**Previously claimed, withdrawn:** *"They are modelling macroscopic topology; we model
microscopic quantum state transitions and prove whether the arrow should exist at all."*
The legacy engine proved nothing of the kind — it compared hand-fitted algebraic
expressions. The current constructor answers only whether atom counts and net charge match.
It accepts many physically impossible or kinetically inaccessible arrows. An energy oracle
prices supported endpoint species; it does not decide whether a reaction mechanism exists.

## 5. Where the typed framing pays off in the physics — and where it didn't

**It pays off in reference-shift invariance.** The current ideal-species adapter defines an
object potential `E(A)` by summing isolated species energies, and
`ΔE(f : A → B) = E(B) − E(A)`. Sequential differences telescope. Conservation makes that
difference invariant under permitted per-element reference shifts: add an arbitrary constant
for every occurrence of each element and the offsets cancel between equal inventories. This
is a useful gauge-invariance contract, not a strong-monoidal functor theorem and not a claim
that energy is additive for interacting species in one vessel.
→ `tests/test_functor.py::TestConservationLicensesSubtraction`

**It pays off again in deciding what not to compute.** The structure does not make any
single quantum-chemical calculation faster — nothing here does, and the retirement of the
legacy engine was the lesson that no algebra substitutes for the wavefunction. What it does
is decide, *before* the expensive layer runs, which calls cannot affect the answer.

A species present unchanged on both sides cancels identically in `ΔE` **under the adapter's
separable isolated-species assumption**, so it is not priced. Binding, solvent reorganisation
or long-range interactions can invalidate that shortcut in a real common environment. On
`2 N → N₂` with an Fe spectator at ±5.0 eV the implemented shortcut
removed two oracle calls and shrank the reported scalar scale from 7.0711 eV to 0.0866 —
because quadrature is valid only for *independent* terms, and a spectator's energy is one
modeled quantity appearing twice, minus itself, not two samples. The old scale was 82×
too wide under that model. Neither scalar is automatically a confidence interval.

That is the honest answer to "are we leaning too hard on someone else's calculation." For the
*absolute energy of a species*, we should lean on PySCF entirely and there is no shortcut. For
*which* isolated-species energies this adapter needs, and *how their stated errors compose*,
the multiset structure plus the separability assumption supports an exact cancellation.

**The same decomposition opened an experimental polyatomic geometry path.** Anything with
three or more atoms was previously blocked for want of coordinates. A bond graph is a useful
input to a seed builder, so the object representation enabled a research path without a
larger table of geometries. Public polyatomic energies still decline: the seed/relaxation/
Hessian machinery is not a conformer or spin-state search and has no validated accuracy
profile. “Computable internally” is deliberately not presented as “supported estimate.”

What made it more auditable rather than merely convenient was refusing to treat "get a geometry" as
one problem. It is three, with different computational characters: a seed (combinatorics, no
wavefunction), a relaxation (needs gradients), and a local-minimum diagnostic (linear
algebra on a Hessian). Splitting them is what let each ride at an appropriate tier, and it
made the diagnostic explicit — a step that is easy to omit when "geometry" remains a
single opaque call.

That diagnostic immediately earned its place. H₂O₂'s symmetric seed relaxes to the trans-planar
form: a perfectly converged stationary point, gradient 1.7×10⁻⁵, and a *transition state*. The
gradient alone calls it done. Only the Hessian says otherwise — and then its imaginary
eigenvector says which way to go, so the diagnosis and the repair are the same object. Three of
four bond-conserving polyatomic reactions hit this; without the curvature check all three would have
returned confident numbers for the wrong species.

The engineering lesson generalises: candidate generation does not establish a minimum. The
VSEPR seed is a heuristic and stays one. A projected frequency analysis is a numerical
local-minimum check under the harmonic approximation, not a mathematical proof. Keeping the
two roles in separate functions makes assumptions and failure modes visible.

**It did not pay off in basis selection, and that was measured.** The reasoning was sound
in shape: extrapolation only removes error the family is converging toward, so diffuse
(ionic) and tight-*d* (second-row) deficiencies survive it; both are properties of the
*elements*, so let the type of the object choose the basis.

At **fixed cardinal** the probe supported it (CCSD(T)/TZ, signed error, kcal/mol):

| species | plain | +diffuse | +tight *d* | both |
|---|---|---|---|---|
| CS | −6.56 | −3.80 | −5.17 | **−2.44** |
| NaCl | −4.10 | −1.11 | −4.07 | **−1.11** |

At the **extrapolated tier** it lost outright — 2.94 kcal/mol against 1.30 for plain
`cbs(TZ,QZ)`, at 5.1× the cost. The inference failed at an identifiable step: "helps at TZ"
was assumed to imply "helps after extrapolating from TZ and QZ." Extrapolation weights the
larger basis by 64/37 and the smaller by −27/37, so it *amplifies* non-smoothness between
them instead of averaging it out. Two different claims; only one was measured.

Two corrections to the record fell out of this:

- *"CS misses because sulfur wants tight d"* was borrowed from the literature, not measured.
  Diffuse is worth +2.76 to CS and tight *d* only +1.39.
- *"NaCl needs diffuse functions"* survives at fixed cardinal in this selected calculation,
  but is beside the point here: plain
  `cc-pVQZ` gives +0.39 kcal/mol and the extrapolation to `cbs(TZ,QZ)` makes it +3.38.
  **For this NaCl protocol the tested extrapolation was the problem.** One molecule does
  not justify a conclusion about ionic species generally.

The machinery is kept and tested but not recommended, for the same reason the legacy engine
is kept: a negative result you can still run beats one you have to take on trust.

The honest summary is that the typed framing bought reference-shift invariance and reliable
sequential bookkeeping, while the tested basis-selection policy bought no accuracy at its
target tier. Measurement was needed to tell those apart.

---

## The claim that replaced the killer feature

The first document's headline was the *Multi-Electron Fixpoint Search*, which claimed the
engine discovered iron's +2/+3 preference in water and refused Na²⁺ on the strength of its
+47 eV second ionization energy.

Both were tested. Neither held:

- Sweeping FeO₁ through FeO₄ showed ΔG decreasing monotonically — the model preferred
  *maximum* oxidation, not +2/+3, and returned identical values in vacuum and in water.
- The Na²⁺ refusal came from the hardcoded `valence_cap` of 1 (`engine.py:74`, since
  retired), which skipped the loop iteration *before* the ionization arithmetic at line 80
  ever ran. Proof: Mg, with `valence_cap` 2, was permitted to double-ionize at 22.68 eV.
  The advertised energy wall never fired.

The replacement claim is smaller and true:

> **Conservation is enforced once, on generators, and inherited by every composite.**
> A mass-violating reaction is unconstructible, not merely absent. Checked against
> hypothesis-generated sequential composition chains in
> `tests/test_laws.py::TestConservationTheorem`.

That is a modest theorem and the clearest invariant the current core supports. Other
reaction-network and chemistry tools can also enforce conservation; SmartChem's contribution
is this particular executable representation and its integration with route bookkeeping.
