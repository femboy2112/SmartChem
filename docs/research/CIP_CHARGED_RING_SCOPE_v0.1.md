# CIP charged conjugated/aromatic ring representation — scope decision (v0.1)

**Round 40 · queue item q1 · Lane B (chemical genericity) · 2026-09-10**

> **Verdict: BUILD the cationic-ring-N slice (explicit-Kekulé); DEFER the cationic chalcogen, the
> charged-aromatic spelling, and anionic/exotic rings — all fail-closed.** Queue item q1 ("CHARGED ring
> representation") was carried *verified-defer-leaning*. A full oracle-driven recon + a 4-bearing adversarial
> gate **refuted the defer lean for cationic ring N** (real consumers, 0 mislabels vs RDKit across a
> ring-vs-heteroaromatic-ring sweep) while **proving the cationic chalcogen must stay deferred** (an
> RDKit-divergent mislabel class).

## 1. The question and why the prior lean was half-wrong

The old queue note read q1 as verified-defer-leaning because the mancude **averaging sub-capability** has only
synthetic consumers ("pyridinium C2 duplicate = 6.5 = pyridine's"). That is true but it is the wrong test: a
stereocentre on a charged ring does not need a distinction *from pyridine*; it needs **its own centre named**,
which requires the ring to release/average at all. The oracle sweep found the consumers directly. But the lean
was *half* right — the adversarial gate proved one charged sub-class (chalcogen cations) genuinely must stay
deferred.

## 2. What was built

`smartchem/smiles.py`, `_cip_mancude`: the blanket charge gate `if atom.charge: valid = False` is replaced by a
**fail-closed whitelist**. One new branch, placed *before* a residual `elif atom.charge: valid = False`, admits
exactly the cationic **acceptor** pattern the oracle validated:

- **cationic ring N** — `atom.element == "N" and atom.charge > 0 and orders == [1, 1, 2] and ring_doubles == 1`
  (pyridinium, pyridine N-oxide, imidazolium / thiazolium N⁺). A valence-4 pattern that **arises only when
  charged**.

Every **other** charged ring atom — including a cationic **chalcogen** (pyrylium O⁺ / thiopyrylium S⁺) — hits the
residual `elif atom.charge: valid = False` and declines. Every **neutral** atom skips the branch (`charge > 0`
false; and a neutral ring N is `[1,2]`/`[1,1,1]`, a parser-permissive neutral overvalent N fills to `[1,1,1,2]` —
never the admitted `[1,1,2]`), so every neutral ring stays byte-identical. Source delta: `smartchem/smiles.py`
+2/−1 net over `f4cd27a` (one branch + a tightened residual comment).

## 3. The soundness argument — and why N⁺ is in but chalcogen is out

CIP priority is by **atomic number**; formal charge changes **no atomic number**. The matching/averaging machinery
in `_cip_mancude` is **charge-blind by construction** (the perfect-matching enumeration iterates pure `ring_adj`
topology; the partner-Z average is keyed on the element string only; `_cip_mass` on element+isotope, never charge).
So once a charged atom is *correctly classified* as an acceptor, its `matching_count` and averaged Z are byte-
identical to its **neutral isoelectronic analogue**.

The load-bearing distinction is **whether that neutral analogue exists and is what the oracle computes**:

- **Cationic ring N — admitted.** It has a neutral isoelectronic acceptor analogue: **pyridine's N**, which RDKit
  `rdCIPLabeler` averages identically. Its averaged ipso duplicate is `(C:6 + N:7)/2 = 6.5`, which stays **below
  any real heteroatom Z ≥ 7**, so it never crosses a competitor's genuine value even in a ring-vs-ring
  comparison. Verified 0 mislabels across a ring-vs-heteroaromatic-ring oracle sweep.
- **Cationic ring chalcogen — deferred.** It has **no** neutral acceptor analogue (a neutral ring O/S is the
  `[1,1]` ether/thioether *donor*, never a π-acceptor). Its charge-blind average — `(C:6+O:8)/2 = 7`,
  `(C:6+S:16)/2 = 11` — **crosses** a real heteroatom, and RDKit does **not** fold the cationic chalcogen into the
  ipso average. This is a **proven ring-vs-ring mislabel class** (§7, dalembert): e.g.
  `O[C@H](C1=CC=CC=[S+]1)C1=NC=CS1` — the charge-blind average would say **S**, RDKit says **R**. A wrong R/S is
  worse than an honest decline, so it stays fail-closed (its pre-R40 state).

## 4. Consumers (previously deferred at the charge gate, now name — 0 mislabels vs RDKit)

Chiral centres bearing a cationic-ring-N heterocycle — the protonated (physiological) or N-alkylated / N-oxide
forms:

- **pyridinium** (→ S), **N-methylpyridinium** (→ S), **pyridine N-oxide** zwitterion (→ S), **imidazolium**
  (→ S), **thiazolium** (thiamine-family motif, → R)
- **ring-vs-ring where the averaged fractions decide** (the load-bearing regime): phenyl-vs-pyridinium (→ R),
  pyridyl-vs-pyridinium (→ R), **pyridinium-vs-thiazole** (→ R), **N-oxide-vs-thiazole** (→ R),
  **pyridinium-vs-thiadiazole** (→ R)

Sweeps: 5 hand consumers + a **106-case ring-vs-heteroaromatic-ring** sweep (N⁺ ring vs benzene / pyridine /
pyrimidine / thiazole / thiadiazole / pyrrole / furan / thiophene / another N⁺ ring, both spellings, both
enantiomers) → **0 mislabels, 0 enantiomer-flip failures**; every one RDKit also names.

## 5. Deferred, fail-closed (documented — 0 silent mislabels)

Each deferred class **raises or returns `{}`, never a silent label** (proven in `_assert_structure_theorem` and
across the adversarial sweeps):

1. **Cationic chalcogen rings** (pyrylium O⁺ / thiopyrylium S⁺) — the RDKit-divergent averaging class above.
2. **Charged AROMATIC spellings** (`c1cccc[n+]1C`) → parser kekulization wall (`SmilesError`). Fix: a charge-aware
   `_aromatic_matchings` (treat a cationic ring N as an acceptor regardless of its third σ-bond) — a **different
   function, upstream of the namer**, its own round. **Latent risk flagged for that round:** an even-acceptor-count
   charged aromatic could, after that fix, find a *wrong* matching silently rather than refuse loudly.
3. **Anionic rings** (ring carbanion) — no validated donor branch.
4. **Exotic / over-charged valences** (`[NH2+]` in a ring), and **parser-permissive neutral overvalent** N/S — the
   `charge > 0` guard keeps the neutral cases byte-stable (they decline exactly as pre-R40).

## 6. Evidence

- `experiments/cip_charged_ring_probe.py` — `FROZEN_HASH`, RDKit-free `validate()` + `_assert_structure_theorem()`
  (consumers name incl. the ring-vs-heteroaromatic regime; deferred classes fail closed; enantiomer consistency
  @↔@@ flips every R↔S) + gated `_rdkit_cross_check()` (**22 compared, 0 mislabels, 14 consumers named, 5 defers
  confirmed, 4 respelling-invariant**).
- `tests/test_cip_charged_ring.py` — pins the build RDKit-free (incl. explicit chalcogen-defer and
  neutral-overvalent byte-stability tests).
- **Capability extension, not purely additive** (the R39/R34 precedent): the R39 `cip_conjugated_carbonyl_probe.py`
  and R34 `cip_exocyclic_ring_probe.py` probes' `FROZEN_HASH` + their charged pins re-anchored (the charged
  *pyridinium/thiazolium* they listed as a defer now names) — recorded, not silently moved.

## 7. Adversarial review (4-bearing gate)

- **dalembert — KILLED, then repaired.** Derived the structure theorem for a counterexample (ring-vs-ring, a
  **high-Z cation** whose averaged ipso duplicate crosses the competitor) and hit it: 7511 generated ring-vs-ring
  stereocentres → **30 mislabels, every one on an O⁺/S⁺ chalcogen ring**; the **N⁺ branch survived** 200
  ring-vs-ring cases with 0 kills. He proved my original probe was **blind** (it pitted charged rings only against
  phenyl/alkyl, where the averaged fraction never decides). Rival "pre-existing neutral bug" **rejected** (0/14
  neutral ring-vs-ring disagreements; every kill was `{}` on `f4cd27a`). **Repair:** dropped the chalcogen branch
  (fail-closed), kept the oracle-survived N⁺ branch, and added the ring-vs-heteroaromatic regime to the probe.
- **evil-morty — CLEAN.** 1063 charged atoms cross-checked (0 mislabels), index mapping element-verified across
  3057 molecules (0 sequence mismatches), 1649-molecule neutral before/after diff main-vs-branch (**0 labels
  changed**, mechanism traced: neutral tetravalent N fills to `[1,1,1,2]`), 1063 enantiomer pairs (0 inversion
  failures), 260 declines all `SmilesError` (0 crashes). Residual (inherent): an RDKit-derived sweep can't police a
  ring smartchem parses+names but RDKit can't — probed directly, found nothing living there.
- **birdperson — SOUND-BUT-HEED, folded.** Independently found the neutral-overvalent leak (a neutral N/S reaching
  the cationic branch); his remedy — add `atom.charge > 0` to the new branch — matches the fold already applied.
  Confirmed the charged direction structurally fail-closed and the re-anchoring honest.
- **mr-president — SHIP-WITH-CONDITIONS, discharged.** Verified the gated cross-check, FROZEN_HASH stability, and
  neutral no-regression himself. All four conditions were round-close documents (this doc, the ROADMAP flip, the
  deferred-kekulizer brick, the "aromatic spelling still fails closed" caveat).

## 8. Boundary / next

q1 is **partly built** (cationic-ring-N, explicit-Kekulé) + **partly deferred** (cationic chalcogen; charged
aromatic spelling; anionic/exotic). The deferred **aromatic slice's** next step is a charge-aware kekulizer in
`_aromatic_matchings`. The deferred **chalcogen slice** would need a representation RDKit agrees with (an open
question — the mean-of-Kekulé-partners average is defensible under IUPAC P-92.1.4.4, but it diverges from the
oracle, so by the project's RDKit-is-oracle discipline it stays deferred). Charged-ring admission also remains the
prerequisite that would let a future CIP Rule 4b/4c/6 admit a larger auxiliary pool — still gated behind those
rules' own missing consumers. **Honest caveat:** the natural aromatic pyridinium spelling `c1cccc[n+]1C` still
fails closed at the parser; only the explicit-Kekulé spelling names.
