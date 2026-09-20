# Rule-calculus family #1: the Diels-Alder [4+2] retro-disconnection (v0.1)

**Base:** `main` after PR #81 (rule-calculus course correction). **Branch:**
`rule-calculus-diels-alder-family-2026-09-19`. **Status:** design + build in progress; NOT a production-gate
replacement. **Direction:** the first NEW structural reaction family compiled onto the `rule_calculus` kernel and
plugged through the UNCHANGED transform-provider seam as an OPT-IN provider (absent from the default registry, the
`RedoxHalfReactionProvider` precedent). Structural type-validity only (Problem A); feasibility (Problem B) deferred.

## 1. Why Diels-Alder, and what "the current grammar misses" means precisely

The production disconnection grammar is the single-cut capped-scission engine (`max_reactant_cuts = 1`): it breaks ONE
bond and caps the ends. A retro-Diels-Alder is a **concerted TWO-sigma-bond** cleavage that turns one ring into two
fragments (diene + dienophile) while shifting the pi system. A single-cut engine cannot express it: no sequence of
one-bond cuts is the concerted 2-bond pericyclic event, and the intermediate "one bond cut" state is a diradical the
engine does not model. So DA is genuinely outside the current transform algebra, not merely unranked within it.

DA is the right FIRST family because it is (a) **benign / poor-man**: thermal, catalyst-free for many substrate pairs
(cyclopentadiene + maleic anhydride runs at room temperature), so it is admissible under the kitchen-is-the-lab model
for Problem A; (b) **pericyclic**, hence **valence-conserving at every atom**, so it lives NATIVELY in the
fixed-vertex, per-atom-degree-preserving `rule_calculus` fragment with no extension; (c) a clean **2->1 cycloaddition
/ 1->2 retro** shape that exercises transport the condensation grammar never did.

## 2. The fixed-vertex rule (proven degree-preserving)

Six ring carbons, minimal all-carbon model. Forward (synthesis) rule L -> R:

    L (diene C0=C1-C2=C3  +  dienophile C4=C5, disconnected):
        edges {(0,1,2), (1,2,1), (2,3,2), (4,5,2)}
    R (cyclohexene ring C0-C1=C2-C3-C4-C5-C0):
        edges {(0,1,1), (1,2,2), (2,3,1), (3,4,1), (4,5,1), (0,5,1)}

Per-atom bond-order sums: `L.degrees = R.degrees = (2,3,3,2,2,2)` -- so `BondRule.__post_init__`'s degree lock accepts
it (verified in the feasibility spike). Forward `apply` lands exactly on R; the RETRO rule (`rule.reverse()`, R -> L)
is the disconnection direction and round-trips back to L. Both directions pass the kernel's independent `verify()`.

The **retro-DA target pattern** is therefore: a 6-membered carbocycle carrying EXACTLY one ring C=C (the C1=C2 double
bond), whose two allylic ring carbons (C0 attached to C1, C3 attached to C2) are joined through two ring sigma bonds
(C0-C5 and C3-C4) to the two remaining ring carbons (C4=C5, the dienophile-derived pair). Cleaving C0-C5 and C3-C4 and
restoring C0=C1, C2=C3, C4=C5 yields diene + dienophile.

## 3. Application guards (the soundness surface -- what the adversary gate will attack)

A raw kernel match is NOT sufficient: `apply` only requires the rule's left edges to be a SUBSET of the host edges, so
an extra bond among the six matched vertices (a substituent bridge, a fused ring, a second ring unsaturation) could let
a non-DA ring forge a DA disconnection. The provider therefore admits a match ONLY when every guard below holds; a
match failing any guard is DROPPED (coverage loss), never coerced. Failing closed here is the same discipline as the
oracle's centre check.

1. **All-carbon scope (v0.1).** All six matched vertices are carbon. Hetero-Diels-Alder (C=O / C=N dienophile,
   aza-dienes) is a real family but DEFERRED to a later version -- admitting it now would widen the pattern before its
   own guards are proven. The kernel's label-preserving match already enforces C at each position (rule labels are C).
2. **Induced-subgraph exactness.** The subgraph the host INDUCES on the six matched vertices must equal the rule's
   left pattern exactly -- no extra edge among the six. This is the locality lock: it forbids a fused/bridged/extra-
   unsaturated ring from masquerading as a clean cyclohexene DA adduct. (A bridged norbornene-type retro-DA is a real
   reaction but has an extra bridge bond among the six, so v0.1 declines it -- honest coverage loss, deferred.)
3. **Aromatic exclusion, by construction.** The pattern requires exactly ONE ring double bond among the six with the
   other five ring bonds single. A benzene ring (three ring double bonds, or an aromatic bond type) cannot match, so
   the ranker-round's aromatization sign-inversion hazard (1,3-CHD -> benzene) never arises here: benzene is not a
   retro-DA adduct and never matches. Guard 2 also excludes cyclohexadiene (two ring double bonds).
4. **Neutral, empty-state species only** (the `rule_calculus_bridge` transport domain): charged / stateful species are
   refused, not silently transported.
5. **Two genuine fragments.** The retro must yield exactly two connected components (diene, dienophile); a match whose
   cleavage does not disconnect (e.g. an additional un-matched ring bond re-connects them -- excluded by guard 2, but
   re-checked on the reconstructed products) is dropped.

## 4. Class witness DERIVED FROM THE MATCH (not a self-declared name)

The class label is not a string the provider asserts; it is COMPUTED from the actual matched rule's structural
signature: the multiset of (deleted-bond orders, added-bond orders) over the matched centre, plus the induced-pattern
identity. Two independent checks must agree before the witness `"diels-alder-[4+2]-carbocyclic"` is emitted: (i) the
kernel `apply`/`verify` round-trip on the match, and (ii) the independent verifier of section 5 recomputing the same
net bond change from the reconstructed endpoints. A mismatch emits NO witness (fail-closed).

## 5. The independent verifier (separate representation from the enumerator)

The enumerator uses the kernel's edge-set `apply`. The verifier is a SEPARATE implementation that, given the two
reconstructed fragments and the target, recomputes: (a) each fragment is a valid neutral molecule; (b) recombining the
diene termini and the dienophile across the two cleaved bonds reproduces the target's bond multiset EXACTLY (an
adjacency-multiset check, not a call to `apply`); (c) the per-atom degree is conserved. This is the DA analogue of the
kernel's table-replay `verify` vs `apply` split, and it is what the adversary gate must not be able to fool.

## 6. Boundaries (carried honestly)

- **Problem A only.** A DA witness asserts "this disconnection is a structurally valid [4+2] retro-DA," NOT that the
  forward reaction is feasible, selective, endo/exo-resolved, or regiochemically preferred. Feasibility stays with the
  existing `feasibility` machinery; the provider adds no drive/rate claim.
- **No stereochemistry / regiochemistry.** v0.1 is connectivity only; endo/exo and ortho/para selectivity are not
  modeled. A downstream consumer must not read selectivity from a DA witness.
- **Opt-in.** The provider is NOT added to the default registry; production search and ranking are byte-unchanged
  unless a caller explicitly composes a registry containing it. It replaces no production gate.
- **Deferred sub-families** (each behind its own future gate + guards): hetero-Diels-Alder, bridged/fused retro-DA
  (guard 2), and forward DA generation (this round ships the retro/disconnection direction as the search consumes
  disconnections).

## 7. Acceptance + adversary gate

Acceptance: DA positives (cyclohexene and substituted carbocyclic adducts disconnect correctly); the THREE existing
oracle classes (acyl / ether / N-alkylation targets) and their substrates are NOT emitted as DA; fresh holdouts.
Adversary gate, run SEPARATELY from acceptance (the 4-round meta-lesson): evil-morty + dalembert attack the guards --
aromatic/cyclohexadiene false positives, fused/bridged forgeries, non-degree-preserving near-misses, extra-bond
masquerades, and the class-witness derivation. Every kill is closed before merge; a clean gate is a precondition, not
a formality.
