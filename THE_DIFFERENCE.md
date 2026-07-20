# THE DIFFERENCE

*Where SmartChem sits relative to neighbouring tools — including where they beat it.*

The previous version of this document claimed SmartChem was better than cheminformatics,
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
`Atom.valence_cap` is a hardcoded group/period rule including an explicit octet check —
precisely the thing RDKit was criticised for. It takes no environment argument and so
cannot respond to one. Swept across four extreme environments including 5 MK and 10⁹ atm,
carbon never exceeded 4 bonds.

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
interpreted is a curve fit.

## 3. vs. Quantum chemistry (PySCF, ORCA, Gaussian)

**They do better:** the actual physics, comprehensively. Correlated methods, open-shell
systems, excited states, relativistic treatments, periodic boundary conditions, analytic
gradients, solvation models, and molecules with more than two atoms.

**SmartChem adds:** composition. It calls PySCF and wraps the result in structure that
tracks provenance, enforces conservation across multi-step routes, and generates response
surfaces.

**Previously claimed, withdrawn:** *"The Oracle Gate resolves in milliseconds what takes
DFT hours, achieving chemical accuracy through structural entailment."* No. Chemical
accuracy is reached by running CCSD(T) with basis-set extrapolation, at ~100 s per
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

---

## The claim that replaced the killer feature

The previous document's headline was the *Multi-Electron Fixpoint Search*, which claimed
the engine discovered iron's +2/+3 preference in water and refused Na²⁺ on the strength of
its +47 eV second ionization energy.

Both were tested. Neither held:

- Sweeping FeO₁ through FeO₄ showed ΔG decreasing monotonically — the model preferred
  *maximum* oxidation, not +2/+3, and returned identical values in vacuum and in water.
- The Na²⁺ refusal came from the hardcoded `valence_cap` of 1 at `engine.py:74`, which
  skips the loop iteration *before* the ionization arithmetic at line 80 ever runs. Proof:
  Mg, with `valence_cap` 2, is permitted to double-ionize at 22.68 eV. The advertised
  energy wall never fired.

The replacement claim is smaller and true:

> **Conservation is enforced once, on generators, and inherited by every composite.**
> A mass-violating reaction is unconstructible, not merely absent. Checked against
> hypothesis-generated composition and tensor chains in
> `tests/test_laws.py::TestConservationTheorem`.

That is a modest theorem. It is also the thing here that actually works, and it does a job
no neighbouring tool does.
