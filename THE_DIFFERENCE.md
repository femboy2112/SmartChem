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

What SmartChem adds is the layer above, which does not otherwise exist: a reaction algebra
where **conservation is enforced by construction**, **catalysis is a decidable property**,
**mechanism search carries its own energy bookkeeping and provenance by law**, and an
**entire response surface follows from one local definition**.

A quantum chemistry package computes one number for one geometry. It has nothing to say
about whether your proposed mechanism conserves mass, whether your catalyst is actually
regenerated, or what the answer looks like across twelve solvents.

---

## 1. vs. Cheminformatics (RDKit, Open Babel)

**They do better:** essentially everything about real molecules. SMILES/InChI parsing, ring
perception, stereochemistry, substructure search, conformer generation, fingerprints,
reaction templates, and a periodic table covering the whole periodic table. RDKit handles
drug-sized molecules; SmartChem's oracle interface handles diatomics.

**SmartChem adds:** conservation as a type-level guarantee. RDKit will happily let a
reaction template drop an atom; SmartChem raises `ConservationError` at construction.

**Previously claimed, now withdrawn:** *"We do not hardcode valency."* The legacy
`Atom.valence_cap` was a hardcoded group/period rule including an explicit octet check —
precisely the thing RDKit was criticised for. It took no environment argument and so could
not respond to one. That module was retired on 2026-07-20; the current system models no
valency at all, so the claim is not merely withdrawn but inapplicable.

## 2. vs. Neural potentials (ANI, MACE, AlphaFold3)

**They do better:** speed at scale and coverage. A trained potential evaluates in
milliseconds on systems of thousands of atoms, and modern ones reach ~1 kcal/mol on the
chemistry they were trained for. That is faster than SmartChem's accurate tier by four
orders of magnitude.

**SmartChem adds:** structural guarantees a learned model cannot give. A network can
predict a reaction that violates conservation because nothing in it forbids that. And a
`Tally` certificate records exactly which oracle produced which step at what stated
uncertainty.

**Previously claimed, softened:** the "white box" framing was fair, but it was attached to
an engine whose central covalent term was a constant fitted on two data points, with a
comment in the source saying so. Being interpretable is worth little when what is being
interpreted is a curve fit. That engine is now frozen in `smartchem/legacy.py` and used
only as the baseline the accurate tiers are measured against.

## 3. vs. Quantum chemistry (PySCF, ORCA, Gaussian)

**They do better:** the actual physics, comprehensively. Correlated methods, open-shell
systems, excited states, relativistic treatments, periodic boundary conditions, analytic
gradients, solvation models, and molecules with more than two atoms.

**SmartChem adds:** composition. It calls PySCF and wraps the result in structure that
tracks provenance, enforces conservation across multi-step routes, and generates response
surfaces. It also makes basis choice a function of the *elements involved* rather than a
global setting — see §5.

**Previously claimed, withdrawn:** *"The Oracle Gate resolves in milliseconds what takes
DFT hours, achieving chemical accuracy through structural entailment."* No. Chemical
accuracy is reached by running CCSD(T) with basis-set extrapolation, at minutes per
diatomic. The algebra contributed none of that accuracy.

**What survived, in a different form:** there *is* a real speed argument, just not the one
claimed. Pruning happens **by type, before any oracle call** — candidates violating
conservation, charge balance or valence never reach the expensive layer. That makes an
expensive oracle affordable over a large candidate space. It does not make one calculation
faster.

## 4. vs. Applied category theory in chemistry (Baez, CRNs, Petri nets)

**They do better:** rigour, generality, and priority. Baez and collaborators have a
developed theory of reaction networks as symmetric monoidal categories, with published
semantics for rates, stochastic dynamics and open systems. SmartChem's core is a small,
concrete instance of ideas that literature already covers more generally.

**SmartChem adds:** an executable implementation wired to a real energy oracle, with the
laws machine-checked against generated chains rather than proved on paper. That is an
engineering contribution, not a mathematical one.

**Previously claimed, withdrawn:** *"They are modelling macroscopic topology; we model
microscopic quantum state transitions and prove whether the arrow should exist at all."*
The legacy engine proved nothing of the kind — it compared hand-fitted algebraic
expressions. Whether an arrow should exist is now answered by an oracle, and the oracle is
PySCF.

## 5. Where the typed framing pays off in the physics — and where it didn't

**It pays off in the energy functor.** `E` is a monoidal functor from the reaction category
to `(ℝ, +)`, and `ΔE(f : A → B) = E(B) − E(A)` is well defined *only because* every morphism
conserves matter. Total energy has an arbitrary zero fixed by atom content; conservation is
what makes the offsets cancel. Shift every atomic reference by a million eV and no reaction
energy moves. That is category theory doing load-bearing physical work rather than
describing chemistry that was already there.
→ `tests/test_functor.py::TestConservationLicensesSubtraction`

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
- *"NaCl needs diffuse functions"* survives at fixed cardinal but is beside the point: plain
  `cc-pVQZ` gives +0.39 kcal/mol and the extrapolation to `cbs(TZ,QZ)` makes it +3.38.
  **For ionic species the extrapolation is the problem, not the basis.**

The machinery is kept and tested but not recommended, for the same reason the legacy engine
is kept: a negative result you can still run beats one you have to take on trust.

The honest summary is that the typed framing bought a real theorem in the energy functor
and bought nothing in basis selection, and only measurement could tell those apart.

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
> hypothesis-generated composition and tensor chains in
> `tests/test_laws.py::TestConservationTheorem`.

That is a modest theorem. It is also the thing here that actually works, and it does a job
no neighbouring tool does.
