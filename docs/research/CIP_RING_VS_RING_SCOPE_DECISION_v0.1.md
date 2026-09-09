# CIP ring-vs-ring + isotope-on-ring — corrected scope decision (ROUND 34 item 5)

**Verdict: Rule-1a-distinct ring pairs NAME; Rule-1a-tied isotope pairs still DEFER.** The first item-5 analysis
classified every released-ring pair as a verified defer. Adversarial review falsified that explanation and found a
general comparator defect instead. The repaired implementation and evidence are pinned by
`experiments/cip_ring_vs_ring_probe.py` and `tests/test_cip_ring_vs_ring.py`.

## What was wrong

The previous `_cip_compare` established the order of sibling pairs correctly, then recursively exhausted the
highest pair before considering the next pair. RDKit's
[source-pinned Hanson/Mayfield implementation](https://github.com/rdkit/rdkit/blob/613d0906052edb65b8f7e3f8efa1225b17a967c3/Code/GraphMol/CIPLabeler/rules/SequenceRule.cpp)
instead enqueues all paired children and visits those pairs FIFO. A lower-ranked sibling's shallow difference must
therefore be examined before a higher-ranked sibling's deeper descendants.

This was not ring-specific. The old traversal produced concrete disagreements in acyclic, saturated heteroring,
localized-ring, and mixed polyene/ring examples. It also made the temporary `_CIP_RING_VS_RING_GUARD` appear
load-bearing: disabling the guard exposed the comparator's errors, but did not establish that ring representation
or Rule 1b caused them.

## Correction and evidence

`_cip_compare`, `_cip_compare_rule2`, and `_cip_compare_rule3` now traverse paired nodes FIFO. The ceremonial
released-ring guard and its `released` bookkeeping were removed. Evidence includes:

- seven adversarial examples that previously disagreed with RDKit and now match;
- a fresh seeded 25,250-comparison holdout with 0 wrong labels;
- a 264-comparison saturated-ring sweep with 0 wrong labels; and
- a 2,586-comparison all-kind ring-pair sweep with 0 wrong labels.

These finite differential results support the bounded implementation; they are not a proof of complete CIP
correctness on arbitrary molecular graphs.

## Remaining boundary

`[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl` ties under Rule 1a and would require Rule 2 to pass a ring closure where Rule
1b may intervene. The existing Rule-1b gate therefore continues to defer this isotope-on-ring case. The unlock is
a sound ring Rule-1b implementation or a narrower proof that the tied constitutions make Rule 1b inert.
