# Aromatic conjugated-carbonyl kekulizer — scope v0.1 (R46, frontier 1)

**Mandate (the user, verbatim intent):** "full blast on ... 1 (the aromatic-purine kekulizer)" — the named
frontier R45 opened: *"a generic fused-ring aromaticity gap — every purine; RDKit's DEFAULT caffeine SMILES fails
to parse; the R39 conjugated-carbonyl class."* Acceptance bar: RDKit's default aromatic caffeine SMILES parses to
the correct structure, and the fix is **generic** (the whole conjugated-carbonyl class), never a caffeine
special-case.

## The gap, ground-truthed

`smartchem/smiles.py::_aromatic_matchings` performs Kekulé perception by splitting the aromatic atoms into
pi-**acceptors** (each needs exactly one ring double bond) and pi-**donors** (they sit out; a lone pair supplies
the aromatic electron), then enumerating the perfect matchings over the acceptor subgraph (one matching = one Kekulé
structure; the resonance-canonical / min-digest one fixes the identity). The classifier treated **every aromatic
carbon as an acceptor**.

A ring **carbonyl** `c(=O)` breaks that: its pi-demand is met by the *exocyclic* C=O, and 2 ring σ + 1 exocyclic
double already reaches valence 4. Forced into the matching anyway, a carbonyl carbon either found **no acceptor
neighbour** (in caffeine the C2 carbonyl sits between two methylated donor nitrogens → an isolated acceptor → no
perfect matching → `SmilesError: could not assign a Kekulé structure`) or, where it did take a ring double,
**over-saturated to valence 5** (`_fill_hydrogens` then raises "bond order 5 exceeding normal valence" — observed on
benzoquinone). Ground-truthed on the filesystem before the fix: *every* purine, *every* pyrimidinone nucleobase
(uracil/cytosine/thymine), guanine, hypoxanthine, quinones and tropone failed closed. **RDKit's default aromatic
output for caffeine — `Cn1c(=O)c2c(ncn2C)n(C)c1=O` — did not parse.** Adenine, pyridine and benzene (no exocyclic
π) parsed fine, and stay untouched.

## The fix — one valence-forced rule, restricted to neutral carbon

A **neutral carbon** bearing an **exocyclic multiple bond** (a non-aromatic incident bond of order ≥ 2) is a
pi-**donor**: it sits out the ring matching, exactly like a lone-pair heteroatom. Its pi electron is spoken for
outside the ring, so it can take no ring double.

This is **valence-forced, not a heuristic.** For a neutral carbon, 2 ring σ + 1 exocyclic double = valence 4 is a
hard wall; a ring double on top would be valence-5, which `_fill_hydrogens` refuses. Therefore **no molecule that
parses today has such a carbon as an acceptor**, and the branch can only ever reclassify atoms on inputs that
currently fail closed. The change is **additive**: it makes previously-refused carbonyl spellings parse, and touches
nothing that already parsed — pinned byte-for-byte (`test_preexisting_spellings_are_unchanged` against the `main`
digests) and by the valence argument (`test_exocyclic_pi_rule_is_valence_forced_not_a_heuristic`, benzoquinone).

**Restricted to neutral carbon — the adversarial fold (evil-morty).** The first cut was *element-blind*, and the
valence-4 wall only holds for carbon. A heteroatom reaches higher valences (N 3/5, S 2/4/6, P 3/5), so
`_fill_hydrogens` does *not* block its hypervalence, and a carbonyl carbon's reclassification could unblock the ring
parity and expose a latent hypervalent-N-oxide bug — turning a `main` fail-closed REFUSE into a *silent wrong or
invalid parse* (`O=c1[nH]c(=O)n(=O)cc1`, `n1(=O)n(=O)c(=O)nc1`). The rule is therefore gated to a **neutral carbon**,
and **every non-carbon / charged committed-π atom fails closed** — checked *before* the R41 charge branch, so the
pre-existing charged valence-5 hole (`O=[n+]1ccccc1`) is closed too. The R41 charge whitelist (charge-separated
pyridine N-oxide `[O-][n+]`, pyridinium) is otherwise untouched and still parses.

## What kekulizes now — the conjugated-carbonyl class, verified against RDKit

For each compound, RDKit's own canonical (aromatic) SMILES now parses to the **same structural identity** as an
independent explicit-Kekulé drawing, and — the external reality anchor — RDKit's InChIKey for that SMILES equals the
PubChem anchor (dev-venv oracle):

| compound | true InChIKey (PubChem) | class |
|---|---|---|
| caffeine / theophylline / theobromine / xanthine | RYYVLZVUVIJVGH / ZFXYFBGIUFBOJW / YAPQBXQYLJRXSA / LRFVTYWOQMYALW | purine-diones |
| guanine | UYTPUPDQBNUYGX | amino-oxo purine |
| hypoxanthine | FDGQSTZJBFJUBT | oxo purine |
| uracil / cytosine / thymine | ISAKRJDGNUQOIC / OPTASPLRGRRNAP / RWQNBRDOKXIBIV | pyrimidinones |
| tropone | QVWDCTQRORVHHT | non-benzenoid aromatic ketone |
| p-benzoquinone | (Kekulé; RDKit doesn't aromatise it) | quinone (valence-5 path) |

Identity still **discriminates isomers**: theobromine's aromatic spelling (3,7-dimethyl) does *not* match
theophylline's Kekulé (1,3-dimethyl) — same formula C7H8N4O2, distinct compounds (`test_identity_still_discriminates_isomers`).

## Boundaries (documented, not fabricated)

1. **Still fails closed on genuinely un-kekulisable aromatic systems** — an odd, isolated acceptor (`c1cc1`) still
   raises, never a silently-wrong order (`test_unkekulisable_aromatic_still_fails_closed`). The fix widened the
   accepted set; it did not defeat the guard.
2. **v1 aromatic-heteroatom gaps unchanged** — an aromatic `p` (and other non-{C,N,O,S} aromatic heteroatoms) still
   refuses loudly. Out of scope here.
3. **Non-carbon / charged committed-π atoms fail closed** — a heteroatom or charged atom bearing an exocyclic
   multiple bond is refused loudly (no valence-4 wall to make it sound). This is the honest v1 boundary the
   element-blind first cut lacked; extending sound kekulization to hypervalent/charged N-oxide systems is a named
   future brick (the R41 charged-kekulizer frontier), not this one.
4. **The non-terminal-exocyclic-π SEAM (dalembert)** — `_min_constitution_placement` pins the exocyclic double onto
   a terminal carbonyl O by that O's `need=1`; a *non-terminal* exocyclic π-system on a neutral ring carbon
   (amidinate/hydrazone-on-ring) could in principle let the double migrate off the atom the rule declared a donor.
   It does **not** crack on any reachable input — every seam case parses byte-consistent with RDKit's independent
   kekulizer (`test_nonterminal_exocyclic_pi_seam_is_consistent_with_rdkit`) — but the safety there is held by an
   incidental fact, not the design. Named as the next probe (assert the seed donor-set equals the argmin placement's
   set-of-atoms-carrying-no-ring-double).
5. **Default no-route depth is a SEPARATE frontier** — this is a *parser* fix (spelling → structure). It does not
   touch the Lane-B transform-grammar frontier that makes `recompile caffeine` no-route at commodity depth (shared
   with paracetamol). Kekulizing a SMILES and routing a target are orthogonal.

## Evidence

- `experiments/aromatic_carbonyl_kekulizer_probe.py` — FROZEN_HASH
  `39dc4c84851094df54ea75f3f8fbdf032c35fbf8a36edbb8daf544cbf7e57421`; rdkit-free `validate()` (the RDKit-generated
  aromatic spellings pinned as fixtures, so the freeze needs no rdkit); gated `_rdkit_cross_check` (InChIKey anchors,
  aromatic≡Kekulé agreement). Four demonstrations: family kekulizes; identity discriminates; additive/no-regression;
  still-fails-closed.
- `tests/test_aromatic_carbonyl_kekulizer.py` (32 tests): the headline (RDKit's default caffeine output parses);
  parametrized family identity-match; isomer discrimination; per-spelling no-regression; fail-closed preserved; the
  valence-forced safety claim (benzoquinone); parametrized InChIKey anchors on BOTH spellings (`importorskip`).
- `experiments/caffeine_derivation_probe.py` — demonstration #7 flipped from "gap present" to "kekulizes" (the
  deliberate, reviewed flip the R45 boundary anticipated); FROZEN_HASH re-frozen to
  `7290064f8a2b7b7b0c9763a084cde94555b53026ae493bcfa8e0ca105e78b5d3`.
- `tests/test_caffeine_registered.py` — `test_aromatic_purine_spelling_now_kekulizes_to_the_same_identity` replaces
  the former documented-gap test.

## Adversarial review (4 bearings)

- **mr-president — SHIP.** All four mandate items verified by his own hand: `parse_smiles("Cn1c(=O)c2c(ncn2C)n(C)c1=O")`
  (RDKit's *default* caffeine output) parses to the correct compound (`RYYVLZVUVIJVGH`); generic across all ten family
  members (true InChIKeys); the demo path goes INVALID_INPUT→parse before/after on clean `main`; boundaries honest.
  One fold applied: the probe's no-regression claim is now a **byte-equality** to the `main` digests, not a count.
- **birdperson — SOUND-with-folds.** Confirmed the rule is in the right place (`_aromatic_matchings` is the only
  function that sees the aromatic flag; the self-healing `_min_constitution_placement` re-derivation makes it robust
  even where the classifier is loose), and the evidence is honestly split (consistency rdkit-free, correctness under
  the oracle). Fold applied: the safety comment/docstring **overclaimed universality** — narrowed to *neutral carbon*
  and the border stated; the predicate renamed `committed_pi` (it matches any non-aromatic double, not only exocyclic).
- **evil-morty — two HIGH breaks, FIXED.** The element-blind rule broke soundness and fail-closed on
  hypervalent-heteroatom decoys (`O=c1[nH]c(=O)n(=O)cc1`, `n1(=O)n(=O)c(=O)nc1`): a carbonyl reclassification
  unblocked the ring parity and exposed a latent N-oxide bug, silently emitting a wrong/invalid structure. Fixed by
  restricting the donor to **neutral carbon** and failing closed otherwise, checked before the charge branch — which
  also closed the pre-existing charged `O=[n+]` valence-5 hole (his MEDIUM item 4). His 20k-fuzz found **zero** carbon
  breaks and zero regressions. Decoys pinned (`test_hypervalent_heteroatom_decoys_fail_closed`).
- **dalembert — SURVIVED.** Structure theorem: the matching only *seeds* per-atom π-demand, so a bad seed can only
  fail *closed*, never silent-wrong; the only silent-wrong regime (spare valence after the exocyclic double) is
  charged/expanded-octet, now all fail-closed. **24,000+ exhaustive aromatizable monocyclic inputs + 60 named/exotic
  compounds → 0 kills** against RDKit's independent kekulizer. He killed his own cytosine false-alarm (a tautomer
  confound). Named the non-terminal-exocyclic-π seam (boundary 4), verified robust and pinned.
- RDKit is a **dev-venv-only** oracle, uninstalled before the committed baseline.
