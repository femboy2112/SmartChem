# CIP ring-on-centre + Rules 4/5 — scope decision (ROUND 34 item 3)

**Verdict: VERIFIED DEFER.** A stereocentre that lies **on a ring** is scoped out by `_on_cycle` and deferred; the
current behaviour is sound over the committed battery. This records why the remaining work cannot be folded into
this round. Evidence is pinned by `experiments/cip_ring_centre_probe.py` and `tests/test_cip_ring_centre.py`.

## The consumer

RDKit `rdCIPLabeler` labels seven battery examples, including pseudoasymmetric `r`/`s`
(`O[C@H]1CC[C@@H](C)CC1` → `('s','s')`) and three-centre menthol (`('R','R','S')`). The feature is therefore real,
but two distinct capabilities remain unbuilt.

## Two remaining walls

1. **Written-neighbour order for tetrahedral parity.** A ring-closure bond is appended to `bonds` at the closing
   digit, not at the opening digit's written position. SMILES chirality is defined by the order in which neighbours,
   branches, and closure digits occur at the chiral atom. The acyclic `incoming`/`outgoing` reconstruction can
   therefore assign the wrong parity at a ring centre. `_on_cycle` fails closed at this boundary. The unlock is
   per-atom written-order capture in the parser; `_parse_skeleton_dirs` provides a nearby implementation pattern.

2. **Rules 4/5: auxiliary descriptors and pseudoasymmetry.** Cis/trans-disubstituted rings and meso systems need
   recursively assigned auxiliary R/S descriptors for Rule 4. Pseudoasymmetric centres need Rule 5 and lowercase
   `r`/`s`. Neither hierarchy is implemented.

The apparent third wall in the first item-3 analysis was removed by item 5's correction: the old Rule-1a comparator
recursively exhausted its highest child rather than traversing paired nodes FIFO. The corrected comparator passes
the fresh ring-pair differential sweep. That repair does not provide either missing ring-centre capability above.

## Recommended order

Build and independently validate (1) written-order capture, then (2) Rule 4 auxiliary descriptors, then (3) Rule 5
pseudoasymmetry. Until then, `_on_cycle` remains the correct fail-closed boundary.
