# CIP conjugated-carbonyl ring naming — a BUILT slice of queue item 1 (ROUND 39)

Status: **built, oracle-validated, additive-to-naming (extends the R34 boundary).** Lane B.
`[[a-sound-extension-guards-its-new-cross-comparisons]]` `[[an-oracle-driven-existence-check-can-prove-a-defer]]`

Queue item 1 is *"charged/conjugated ring representation — extend mancude past the neutral bounded C/N/O/S
slice. Sound source-pinned representation; fixed-Kekulé shortcuts forbidden."* An oracle-driven recon (RDKit
`rdCIPLabeler` + a code-boundary read + a consumer hunt) carved that item into a **buildable slice with real
forcing consumers** and two cleanly-bounded **deferred slices**. This round builds the first and documents the
second — the R33/R34 incremental discipline, not a monolithic charged-ring build.

## The recon that decided BUILD vs DEFER

An oracle existence sweep (calibrated on known-named molecules first — the instrument rule) classified every
centre of a broad battery as MATCH / MISLABEL / REPO-DEFERS-RDKIT-NAMES vs `rdCIPLabeler` (RDKit 2026.03.6,
dev-venv-only, uninstalled at baseline):

- **A real, non-empty forcing class exists.** Internally-conjugated rings bearing an exocyclic carbonyl —
  **L-ascorbic acid (VITAMIN C)**, carvone, the quinones/naphthoquinones, the cyclohexenones/cyclopentenones,
  the butenolides — DEFERRED under the shipped namer while RDKit named every one. This is not a contrived
  fixture set; vitamin C is a north-star-grade real molecule.
- **The charged slice defers by TWO distinct paths.** A charged **aromatic** spelling (`[nH+]` pyridinium,
  imidazolium) raises `SmilesError: could not assign a Kekulé structure` at the parser — upstream of the namer.
  A charged explicit-**Kekulé** spelling (e.g. the thiazolium `C[C@@H](O)C1=[N+](C)C=CS1`) parses fine and then
  declines at the namer's charge gate (`smiles.py:1193`, `if atom.charge: valid = False`), returning `{}`. Both
  fail closed; extending mancude to charge is moot until BOTH a charge-aware kekulizer and a charge-aware valence
  classifier exist, and (below) the charged AVERAGING they would feed has no real consumer.
- **The mancude AVERAGING sub-capability has synthetic-only consumers** (the recon's consumer bearing):
  formal charge changes no atomic number and, for aromatic cations, no Kekulé-averaged value
  (pyridinium C2 duplicate = 13/2 = 6.5, identical to pyridine), so a charged average equals its neutral
  parent's — no real molecule's descriptor turns on the charged-averaging capability. What has real consumers
  is ring **ADMISSION** (letting ordinary Rule 1a descend past the ring), not the averaging.

The decision follows: build the **admission** of the conjugated exocyclic-carbonyl class (real consumers,
soundly releasable); defer the **charged** slice (parser wall + synthetic-only averaging consumers) and the
**aromatic-resonance** slice (exocyclic =CH2/=NH).

## What was built

`smartchem/smiles.py` `_exocyclic_carbonyl_spectator(atoms, a, adj, ring_adj)` + one branch in the
`_cip_mancude` valence classifier. A ring **carbon** whose two ring bonds are both single (`ring_doubles == 0`)
but which bears a single **exocyclic double to a TERMINAL CHALCOGEN** (`=O` / `=S`) is admitted as a
pass-through ring **spectator**, exactly like the R34 sp3 spectator — the only difference is the exocyclic
double, which the ordinary `_cip_digraph` already handles soundly (real z/mass on the carbon, an order-1
duplicate leaf of the real partner, exactly as an acyclic `C=O`). Admitting it lets the internally-conjugated
enone / dienone / quinone / butenolide ring reach the matching enumeration, where its **unique** acceptor
matching **releases** the ring to real z/mass (`matching_count == 1`) and ordinary Rule 1a decides the centre.
No new averaging path is added; this is ring **admission via release**.

## The soundness argument (dalembert R33, generalized)

The R33 release theorem — `matching_count == 1 ⟺ unique Kekulé`, so release to a fixed structure is sound — is
proven for a ring where `need[a] = Σ(order − 1)` is Kekulé-invariant AND **every double bond is a ring edge**.
An exocyclic double is not a ring edge, so the theorem does not apply blindly (`fixed-Kekulé shortcuts
forbidden`). Two conditions restore it, and both are enforced by `_exocyclic_carbonyl_spectator`:

1. **Terminal partner ⇒ the exocyclic double is Kekulé-FIXED.** A degree-1 atom's double bond can only ever
   point back at the ring carbon, so it contributes the SAME `order − 1` duplicate leaf in every Kekulé
   structure and never perturbs `need[a]` for the ring. Therefore `matching_count` over the TRUE ring
   acceptors still equals the ring's Kekulé count, and `matching_count == 1 ⟺ unique Kekulé` holds.
2. **Neutral chalcogen (O/S) partner ⇒ the release stays NEUTRAL-KEKULÉ-COUNT-PRESERVING.** The precise
   invariant (sharpened by dalembert + birdperson — the earlier wording "no aromatic-resonance form" was too
   strong): a neutral carbonyl / thiocarbonyl does not add a second **neutral** Kekulé structure. It CAN carry
   aromatic resonance — tropone, tropolone, cyclopropenone, γ-pyranone, the pyridones are all chalcogen
   carbonyls with genuine aromaticity — but that resonance is DIPOLAR (charge-separated), not a second neutral
   Kekulé, so it does not raise `matching_count`. A monocyclic exocyclic-carbonyl ring therefore has
   `matching_count ≤ 1` **provably** (dalembert: the spectator is a vertex removed from the ring cycle, leaving
   a path, and a path has a unique perfect matching or none), and releases to its one true Kekulé — RDKit's
   delocalized average over a unique Kekulé equals that Kekulé, so they agree. Where `matching_count ≥ 2` (a
   FUSED ambiguous cycle) the ring AVERAGES rather than releases, so no fixed-Kekulé artifact can arise there
   either. An exocyclic `=CH2` (fulvene, a quinodimethane) or `=NH` (azafulvene) is still DELIBERATELY EXCLUDED
   (the helper's O/S gate) — those non-benzenoid systems can carry a genuine second neutral Kekulé; a charged
   partner (`=[O-]` enolate, `=[O+]` acylium) is EXCLUDED too (the helper's `charge == 0` gate, evil-morty R39).
   Both stay deferred fail-closed (`a wrong R/S is worse than none`).

The direct RDKit-free test of representation-invariance is **enantiomer consistency** (the `@`/`@@` mirror
flips every R↔S / r↔s with no fabricated distinction); the gated cross-check strengthens it with RDKit-generated
same-molecule respellings (labels constant).

## Evidence (RDKit `rdCIPLabeler`, dev-venv-only oracle)

- `experiments/cip_conjugated_carbonyl_probe.py` (FROZEN_HASH `b6dcb052…`, RDKit-free `validate()` +
  `_assert_structure_theorem()` + gated `_rdkit_cross_check()`): the consumer battery names with blessed
  labels; the deferred slice declines while RDKit names it; **0 mislabels** across the compared centres;
  enantiomer + respelling invariance hold.
- The R34 `experiments/cip_exocyclic_ring_probe.py` sweep (170 cases) re-runs against RDKit with **0
  mismatches**; its two former conjugated-enone boundary-defers are re-tagged as named (RDKit `("R",)`), and
  its boundary-defer anchors are re-pointed at the R39 boundary (conjugated exocyclic `=CH2`; a charged ring).
- Regression: the neutral slice is byte-stable — saturated rings, localized rings (R33), mancude averaging
  (benzene/pyridine), fused aromatics (R34), amino acids and sugars are all unchanged (0 regressions in the
  broad sweep and the full suite).

## The scope boundary (deferred, fail-closed — named for the unpark)

- **Charged conjugated / aromatic rings** (pyridinium, imidazolium, thiazolium): a parser kekulization wall
  (`could not assign a Kekulé structure`) plus the charge gate (`smiles.py:1193`); the mancude AVERAGING
  sub-capability has synthetic-only consumers. Unpark needs a charge-aware kekulizer/valence classifier AND a
  real charged-averaging consumer — neither exists in scope.
- **Exocyclic `=CH2` / `=NH` on a conjugated ring** (fulvene, quinodimethane, azafulvene): aromatic-resonance
  ambiguity; a fixed release could diverge from the oracle. Unpark needs a resonance-aware model validated
  against RDKit on that class.
- Non-C/N/O/S conjugated rings, over-budget systems: unchanged (the pre-existing `_CipTooBig` / `else:
  valid=False` fail-closed paths).

## Relationship to the auxiliary pool (the ROADMAP's "gate for 4b/4c/6")

Bearing A verified, with a precision the ROADMAP shorthand omits: admitting these rings lets a ring
stereocentre resolve in pass 1, which enlarges the **raw** auxiliary pool (`smiles.py:2022`). It does NOT
enlarge the **admitted** pool — the cap at `smiles.py:2026-2027` still refuses any pool > 2, and a pool > 2 is
already reachable from purely acyclic centres. So this round is a correct **prerequisite** step toward any
future 4b/4c/6 (it supplies ring-derived auxiliary descriptors), not the whole gate; raising the admission cap
is a separate change coupled to actually building 4b/4c/6.

## Files

- `smartchem/smiles.py` — `_exocyclic_carbonyl_spectator` + the `_cip_mancude` spectator branch.
- `experiments/cip_conjugated_carbonyl_probe.py` — the FROZEN_HASH evidence harness.
- `tests/test_cip_conjugated_carbonyl.py` — pins the build, the structure theorem, and (gated) 0 mislabels.
- `experiments/cip_exocyclic_ring_probe.py`, `tests/test_cip_exocyclic_ring.py`, `tests/test_cip_mancude.py` —
  updated to the R39 boundary (two enones re-tagged named; boundary anchors re-pointed).

## Adversarial review — four bearings before merge

**The build is sound within its declared scope; no bearing found a mislabel.** All four ran the RDKit oracle
live (2026.03.6, dev-venv-only) before it was uninstalled for the baseline.

- **dalembert (structure-theorem refutation): SURVIVED** — ~2,400 oracle comparisons, 0 mislabels, and a
  PROOF of the load-bearing monocyclic class: the carbonyl spectator is a vertex removed from the ring cycle,
  leaving a path, and a path has a unique perfect matching or none — so a monocyclic exocyclic-carbonyl ring has
  `matching_count ≤ 1` and always releases to its ONE true Kekulé (airtight, not sampled). He named the loose
  wording of condition 2 (tropone/cyclopropenone are aromatic chalcogen carbonyls) — folded to the
  neutral-Kekulé-count-preserving invariant above. **His one reinforcement, folded:** the AVERAGING path
  (`matching_count ≥ 2`) for a carbonyl-bearing FUSED NON-benzenoid ring is newly reachable and inherited the
  R34 benzenoid lineage's assurance without its own tombstone; a committed non-benzenoid-fused-carbonyl case
  (`O[C@@H](C)C1=CC2=CC=CC=CC=C2C1=O`, 0 mislabels) was added to the probe battery.
- **evil-morty (directed break): CLEAN BILL** — ~20k oracle checks (12,780-molecule randomized ring sweep +
  9,163-centre regression corpus + isotope/radical/sulfine/acylium edges) and an 11,319-molecule before/after
  diff: 0 flipped, 0 lost, 1,410 newly named (all matching RDKit), 0 crashes — strictly additive on the corpus.
  **His one LOW finding, folded:** `_exocyclic_carbonyl_spectator` checked the exocyclic partner's element but
  not its charge (an enolate `=[O-]` / acylium `=[O+]` partner was admitted — unweaponizable, since such forms
  are valence-invalid and RDKit refuses them); tightened to require `partner.charge == 0`.
- **birdperson (principled review): SOUND-BUT-HEED** — verified the code is in-idiom with the R33/R34 spectator
  framework, no double-counting, every fail-closed guard fires for the right reason, and the round is honestly
  labeled a capability extension (moves a boundary; not "purely additive"). Folded: two comment defects
  (`smiles.py` branch comment claimed "imine/methylene", stale `_exocyclic_double_terminal` name) and the
  condition-2 wording.
- **mr-president (acceptance): SHIP-WITH-CONDITIONS** — ran the oracle himself (0/19 mismatches), ruled the
  conjugated slice built and sound, the real-consumer bar met (vitamin C), "fixed-Kekulé shortcuts forbidden"
  honored (release-under-a-proven-invariant), and the aux-pool claim honestly under-stated. Conditions, all
  discharged: (1) re-anchor stale line citations (done — `1193` charge gate, `2022` raw pool, `2026-2027` cap);
  (2) reconcile the charged-defer mechanism with its Kekulé-form fixture (done — the two-path split above, and a
  committed aromatic-charged `SmilesError` pin in the tests); (3) fill this review section (done); (4) uninstall
  RDKit before the committed baseline (done).
