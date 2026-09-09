# Localized unsaturated-ring substituents in the CIP namer (ROUND 33)

> **Status:** SHIPPED — the R32-surfaced "unsaturated-ring-substituent" gap is closed for **localized** rings (a
> single forced Kekulé structure). This is a bounded Rule-1a/Rule-2 extension over the UNCHANGED breadth-first
> comparator, oracle-verified against RDKit `rdCIPLabeler`; it names the localized-ring class and cleanly, soundly
> defers the two mechanisms that remain (exocyclic double bonds; aromatic-fused-to-saturated systems), plus a
> narrow isotope-on-a-ring corner the Rule-1b gate closes.

## The gap (from R32)

R32 (`CIP_RULE1B_CONSUMER_SCOPE_DECISION_v0.1.md`) proved Rule 1b has no in-scope consumer and, in doing so,
surfaced the *real* next CIP gap: an off-ring stereocentre bearing a substituent ring that carries a double bond
DEFERRED even where Rule 1a trivially decides. Isolation: `[C@](C1CC1)(C)(F)Cl` (saturated cyclopropyl) NAMED,
but `[C@](C1=CC1)(C)(F)Cl` (the same ring with one double bond) DEFERRED. The trigger was a ring-digraph
limitation, distinct from Rule 1b and from the `_on_cycle` ring-centre filter.

## Root cause (one line)

`_cip_mancude` classified *every* atom of an unsaturated ring, and any atom that fit no pi-acceptor/donor pattern
— e.g. an ordinary sp³ CH₂ in cyclopropene — hit `else: valid=False`, blocking the WHOLE ring component as a
Kekulé-dependent `_CIP_AROMATIC` boundary. A comparison that had to descend into the ring then raised
`_CipAromatic` → the centre deferred, even though the contested ligands were Rule-1a-distinct and the ring's
Kekulé structure was *unique* (nothing to be Kekulé-dependent about).

## The fix

A **localized** unsaturated ring — one whose double-bond positions are FORCED (its pi-acceptor set admits a
**unique perfect matching**, i.e. a single valid Kekulé structure: cyclopropene, cyclohexene, cyclopentadiene, a
cyclic enol ether, a localized fused bicyclic like norbornene) — is not a superposition. It is released to the
ordinary `_cip_digraph` with **real atomic number and real mass**, exactly the treatment an *acyclic* double bond
already receives soundly. Two small additions to `_cip_mancude`, over the unchanged comparator:

1. **Spectator admission.** A saturated sp³ ring carbon (`element == "C"`, `orders == [1,1,1,1]` — all bonds order
   1, which guarantees no ring *and* no exocyclic double) is accepted as a pass-through spectator instead of
   invalidating its component, so a partially-unsaturated ring reaches the perfect-matching enumeration.
2. **Three-way release** at the matching hand-off (birdperson's soundness split):
   - `matching_count == 1` → **release** to the ordinary digraph (real Z, real mass; atoms left OUT of both
     `blocked` and the mancude-average dict). Localized rings name.
   - `matching_count ≥ 2` with **no** admitted spectator → the clean fully-conjugated mancude system (benzene,
     pyridine, di-2-pyridyl): today's exact partner-Z averaging, **BYTE-IDENTICAL**.
   - `matching_count ≥ 2` **with** a spectator → a mixed partially-saturated fused system (indene, tetralin):
     extending the *averaging* claim there is unvalidated → **DEFER** (leave blocked). A characterised next gap.

## Soundness — the structure theorem (dalembert) and the Rule-1b gate

**Theorem (dalembert, sent to break it, SURVIVED with a proof):** fix a constitution. Per-atom π-demand
`need[a] = Σ(order − 1)` is preserved across all Kekulé placements, so the set of π-participating atoms (need ≥ 1)
and hence the acceptor set is Kekulé-INVARIANT, and — *provided every double bond in every Kekulé is a ring edge*
(exactly what the `ring_doubles == 1` / no-charge / no-exocyclic gate enforces) — the acceptor set's ring-edge
perfect-matching count **equals the true number of Kekulé structures**. Therefore `matching_count == 1 ⟺ unique
Kekulé structure`, `_kekulize_in_place` lands on that one placement deterministically, and the ordinary digraph
(which reads the graph, never the spelling) is spelling/Kekulé-INVARIANT and equal to the textbook duplicate-atom
construction. A counterexample can only live outside the gate (exocyclic/cumulene/charged π — all correctly
`valid=False`) or in the Rule-ordering, which is the one reinforcement below. Verified independently: benzene/
pyridine (2), naphthalene (3), anthracene (5), azulene (2) correctly stay unreleased; cyclohexene / cyclopropene /
cyclopentadiene / pyrrole / furan / thiophene are count-1.

**The Rule-1b gate (the one latent unsoundness, closed).** `_cip_rank_compare` applies Rule 1a then Rule 2,
skipping the unbuilt Rule 1b. R32 proved Rule 1b is inert on **trees** — which is what licensed that skip for
acyclic ligands. But releasing **ring** ligands enters the regime where Rule 1b *bites* (ring closures): two
ring ligands can tie under Rule 1a while being constitutionally distinct, where Rule 1b would decide and an
isotope asymmetry could let Rule 2 decide the *other* way → a mislabel. So Rule 2 may break a Rule-1a tie **only
when both tied ligands are trees**; if either contains a ring closure (`_ligand_has_ring`), a Rule-1a tie DEFERS
into Rule-1b territory. This preserves acyclic naming untouched and costs only the exotic isotope-on-a-ring
corner (e.g. `[C@]([13CH]1CCCCC1)(C1CCCCC1)(F)Cl`, which now defers rather than lean on Rule 2 past Rule 1b).

## Scope boundary (what still defers, soundly, and why)

- **Exocyclic double bonds on a ring atom** (methylenecyclohexane, a ring ketone, fulvene): the strict all-single
  spectator pattern rejects the exocyclic-double atom → the component stays blocked → DEFER. This also keeps the
  exocyclic-multiple-into-aromatic guard's teeth. A distinct next gap (the double bond is not a ring edge, so the
  ring-edge matching argument does not cover it).
- **Aromatic-fused-to-saturated systems** (indane, tetralin, dihydronaphthalene): matching_count ≥ 2 with an sp³
  spectator → DEFER. Extending the mancude *averaging* into a mixed saturated/unsaturated fused topology is
  unvalidated; a wrong average is a mislabel. The next round after this one.
- **Isotope-labelled ring ligands tied under Rule 1a**: deferred by the Rule-1b gate above.
- **Ring-on-centre stereocentres**: still filtered by `_on_cycle` (the deferred Rule-4/5 auxiliary-descriptor
  territory), unchanged.

Every deferral is a NAMED deferral: a wrong R/S is worse than none.

## Verification boundary (evil-morty, SURVIVED)

The adversarial review threw ~1,200 random ring-substituent stereocentres, a spelling-invariance attack (15 named
molecules × 25 RDKit-random respellings each — the direct test that `matching_count==1 ⟹ unique Kekulé`, all labels
constant), fused/bridged polycyclics, deep Rule-1a ties forcing descent through ring-closure duplicates,
heteroaromatic azoles/diazines, and multi-stereocentre multiset checks at the shipped fix — **0 mislabels**. Honest
residuals it could not turn into a kill: (1) **common-mode oracle risk** — every "match" is against RDKit
`rdCIPLabeler`; a case where this fix and RDKit are wrong the *same* way is invisible to this validation, so the bill
is truth-relative to that single oracle, not absolute; (2) the unique-Kekulé exclusion argument leans on
`_kekulize_in_place` never placing a double on a donor O/S or an sp³ spectator (valence-forced, observed, but the
kekulizer was not itself adversary-tested under exotic bracket-declared valences feeding a released ring); (3) the
`_CIP_MANCUDE_MAX_ATOMS`/budget seam fails **closed** (a released component over budget stays blocked → defer), so an
off-by-one there costs a name, never a mislabel. All three are either inherent to oracle-relative validation or
fail-closed — none is a soundness defect.

## Evidence (committed, per "experiments are committed")

- **`experiments/cip_localized_ring_probe.py`** (FROZEN_HASH) — an oracle-verified battery (each label baked +
  verified against `rdCIPLabeler`) plus reproducible sweep generators showing the localized class NAMES and
  matches RDKit, the exocyclic / aromatic-fused / isotope-on-ring cases DEFER, and the furan/pyrrole/thiophene
  reroute (unique-matching aromatic heterocycles now carry real mass; Rule 1a byte-identical). RDKit-free
  `validate()`; a gated live cross-check re-runs the sweeps when rdkit is present (dev/probe only, absent from the
  committed suite).
- **`tests/test_cip_localized_ring.py`** — `validate()`, the hash pin, the isolation, the guard, the reroute, the
  boundary deferrals.
- **`experiments/cip_rule1b_consumer_probe.py`** (R32) updated: its ring-substituent frags — all localized — now
  NAME (its in-scope-deferral count goes 24 → 0), a "R33 closed this" note; the Rule-1b finding, the 992-case
  acyclic sweep, and the `duplicate_never_collides_with_real` crux are UNCHANGED.
