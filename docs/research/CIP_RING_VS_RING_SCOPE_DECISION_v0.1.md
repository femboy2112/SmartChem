# CIP ring-vs-ring + isotope-on-ring — scope decision (ROUND 34 item 5)

**Verdict: VERIFIED DEFER.** An off-ring stereocentre bearing **two rings** is not soundly nameable yet; the
`_CIP_RING_VS_RING_GUARD` fails it closed. This records *why*, with the oracle evidence, and names the unlock.

## The question

R33 released localized rings and R34 items 2/4 released exocyclic and mixed aromatic-fused rings — each NAMES as
the **only** ring on a centre. Item 5 asked: can a centre bearing **two** rings be named?

## The finding (RDKit `rdCIPLabeler` oracle, dev-venv-only, 2026-09-08)

A ring-vs-ring comparison forces the CIP hierarchical digraph to **descend into two competing ring-closure /
double-bond duplicate structures**. A category sweep (guard disabled) shows the disagreement is **structured**:

| pair kind | oracle mismatches (guard off) |
|---|---|
| saturated vs *anything* | 0 (sound) |
| localized vs {exocyclic, aromatic, fused, saturated} | 0 (sound) |
| exocyclic vs {aromatic, fused} | 0 (sound) |
| pure mancude vs pure mancude (benzene/pyridyl, R22) | 0 (sound) |
| **localized vs localized** | **12 (mislabel)** |
| **exocyclic vs exocyclic** | **2 (mislabel)** |
| **fused vs fused** | **2 (mislabel)** |

The mislabels concentrate in **same-kind unsaturated ring pairs** (cyclohexenyl vs cyclopentenyl; a ring ketone vs
another ring ketone; indane vs tetralin), where Rule 1a cannot decide at a shallow sphere and the comparison
descends into the competing ring structures. This is **Rule-1b territory** (R32: Rule 1b bites with ring closures —
two rings can tie under Rule 1a while being constitutionally distinct), and Rule 1b is UNBUILT. Whether our
divergence is a latent Rule-1a ring-closure-representation bug or genuine Rule-1b is not resolved here; either way
**naming would mislabel**, so we DEFER (a wrong R/S is worse than none).

## The guard is load-bearing AND targeted

- **Load-bearing:** with the guard ON, 0 ring-vs-ring mislabels over the sweep; flip it OFF (the
  `guard_off_mislabels()` seam) and the mislabels return (8 in the committed battery-fragment sweep). Pinned live
  in `experiments/cip_ring_vs_ring_probe.py` + `tests/test_cip_ring_vs_ring.py`.
- **Targeted, not a blanket veto:** two **saturated** rings still NAME (never released, guard doesn't fire); a
  **single** released/fused ring + acyclic co-ligands NAMES (item 2/4); **pure mancude-vs-mancude** (benzene/pyridyl,
  no sp³ spectator, not `released`) ranks soundly via the R22 averaging (0 oracle mismatches). Item 4's mixed fused
  rings ARE recorded in `released` precisely so the guard catches fused-vs-fused without touching the R22 path.

## Isotope-on-a-ring

`[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl` (two constitutionally-identical rings differing only by isotope) defers via
the R33 Rule-1b gate (`both_acyclic=False` when rings are present). RDKit names it (R) by Rule 2. A *sound* narrow
win exists — if the two Rule-1a-tied ring ligands are proven **constitutionally identical**, Rule 1b is inert and
Rule 2 may decide — but it is an exotic, low-value consumer and is deferred with the rest of ring-vs-ring, not
built (butter-robot/YAGNI).

## Unlock (the real next consumer)

Either **a Rule-1b constitutional comparator** (rank two Rule-1a-tied ring ligands by constitution — the same
machinery that would name the isotope case), **or a verified ring-closure/double-bond digraph representation** that
matches the oracle on deep ring-descent. Either lets ring-vs-ring NAME; neither is this round's build.
