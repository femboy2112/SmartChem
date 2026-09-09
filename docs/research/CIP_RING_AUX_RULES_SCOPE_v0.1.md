# CIP ring order and Rules 1b/4a/5 — bounded admission (ROUND 35)

Status: **built for the validated slice; recursive auxiliary-descriptor systems still defer.**

## What is admitted

1. The parser preserves each atom's written neighbour order. An opening ring digit reserves its position until its matching digit identifies the neighbour. The official OpenSMILES-equivalent pair `FC1C[C@](Br)(Cl)CCC1` and `[C@]1(Br)(Cl)CCCC(F)C1` therefore gives S by both spellings; their configuration keys also agree.
2. Revised CIP Rule 1b is a separate breadth-first pass between Rules 1a and 2. Ring-closure duplicate nodes outrank non-ring duplicates of equal Rule-1a rank; between ring duplicates, the nearer corresponding real atom wins.
3. The IUPAC Blue Book P-9 example `(1S)-1-(bicyclo[2.2.2]octan-1-yl)-4-cyclopropyl-2,2-bis(2-cyclopropylethyl)butan-1-ol` is the decisive consumer. The committed SMILES isolates a Rule-1a tie and a nonzero Rule-1b comparison, then yields S; its mirror yields R.
4. A two-pass auxiliary-descriptor path admits Rule 4a when exactly one descriptor-free uppercase R/S centre is available, and revised Rule 5 when exactly one opposed R/S pair is available. One enantiomorphic comparison produces lowercase r/s.

## What is not claimed

- The auxiliary pass is not iterated. Mutually dependent pseudo-asymmetric centres such as `O[C@H]1CC[C@@H](C)CC1` still defer.
- Same-handed or larger auxiliary systems can need target-relative Rules 4b/4c and Rule 6. They remain outside the admission gate.
- The RDKit 2026.3.6 comparison is finite validation, not a proof of complete CIP conformance. The committed fixed battery and 320 deterministic randomized equivalent spellings had zero disagreements.
- Charged and unsupported mancude systems retain their existing fail-closed boundaries.

Primary algorithm sources used for the implementation boundary are the [OpenSMILES specification](https://opensmiles.org/opensmiles.html), [IUPAC Blue Book P-9](https://iupac.qmul.ac.uk/BlueBook/P9.html), and RDKit's source-pinned CIPLabeler implementation. Evidence is executable in `experiments/cip_ring_aux_rules_probe.py` and `tests/test_cip_ring_aux_rules.py`.
