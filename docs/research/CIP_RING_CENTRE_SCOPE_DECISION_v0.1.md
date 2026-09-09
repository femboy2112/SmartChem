# CIP ring-on-centre + Rules 4/5 — scope decision (ROUND 34 item 3)

**Verdict: VERIFIED DEFER.** A stereocentre that lies **on a ring** is scoped out by `_on_cycle` and deferred; the
current behaviour is sound (0 mislabels over the battery). This records *why* a sound namer cannot be built this
round, with the oracle evidence and the precise unlock. Pinned by `experiments/cip_ring_centre_probe.py` +
`tests/test_cip_ring_centre.py`.

## The question

Can a ring stereocentre — menthol, a cis/trans-disubstituted cyclohexane, a pseudo-asymmetric centre — be named?
The consumer is real: RDKit `rdCIPLabeler` labels a population of them (7 in the battery), including
pseudo-asymmetric `r`/`s` (`O[C@H]1CC[C@@H](C)CC1` → `('s','s')`) and multi-centre (menthol → `('R','R','S')`).

## Three compounding walls (each a genuine build)

1. **Written neighbour order for the tetrahedral parity.** A ring-closure bond is appended to `bonds` at the
   *closing* digit, not at the *opening* digit's written position — but SMILES chirality is defined by the order
   the neighbours (branches **and** ring-closure digits) appear *at* the chiral atom. The acyclic
   `incoming`/`outgoing` reconstruction in `_cip_labels` therefore mis-orders a ring centre's neighbours → a wrong
   parity → a wrong R/S. `_on_cycle` fails closed exactly here. **Unlock:** per-atom written-order capture in the
   parser (the same shape as the R34-item-1 direction capture; `_parse_skeleton_dirs` is the precedent).

2. **Reliable ring-vs-ring ranking.** A ring stereocentre's two ring-path ligands *are* a ring-vs-ring comparison —
   the deep-ring-descent ROUND 34 item 5 proved our Rule-1a digraph resolves differently from the oracle for
   same-kind pairs (`_CIP_RING_VS_RING_GUARD`). A diagnostic bypass of `_on_cycle` finds cases that *rank* (8 of 15
   in the recon) but would **mislabel**. **Unlock:** item 5's — a Rule-1b constitutional comparator, or a verified
   ring-closure/double-bond digraph representation.

3. **Rules 4/5 (auxiliary descriptors + pseudo-asymmetry).** cis/trans-disubstituted rings and meso systems need
   **Rule 4** (like/unlike auxiliary R/S descriptors, assigned recursively to the branches, then compared);
   pseudo-asymmetric centres need **Rule 5** (lowercase `r`/`s`, R > S). Neither is built — they sit above Rules
   1a/2/3 in the hierarchy. This is the largest of the three: a recursive auxiliary-descriptor subsystem.

Building ring-centre naming now would mislabel on all three counts. The R32 discipline applies: a feature proven
not soundly buildable yet is a **verified defer**, with committed evidence and the named unlock — not a guess.

## Recommended order for the future round

(1) the written-order parser capture (unblocks parity and is self-contained) → (2) item 5's ring-vs-ring unlock
(shared prerequisite) → (3) Rule 4 auxiliary descriptors → (4) Rule 5 pseudo-asymmetry. Each is its own reviewed,
oracle-swept increment; (3)+(4) together are a major round on their own.
