# POOR-MAN-OUT-OF-CENTER-RECOGNIZER — VERIFIED DEFER (R52, PR-2)

> **Status: VERIFIED DEFER.** The third verified defer of the poor-man *ingenuity reward*, this time of the
> "out-of-centre recognizer" proposed as KILL-1's ordered unlock #2. A five-bearing adversarial DESIGN gate
> deferred it 4-to-1, on a **new structure theorem**: the recognizer *moves* the kitchen-boundary collision
> (from the competing-nucleophile blade to the steric blade) rather than closing it, and it has no live consumer
> today. The reward stays deferred; R50's KILL-1 is *deepened*, not resolved. Evidence:
> `experiments/poor_man_out_of_center_recognizer_defer_probe.py` (FROZEN_HASH `2115ded5…`) +
> `tests/test_poor_man_out_of_center_recognizer_defer.py`.

## The user's ask and the reading

> "full blast on PR-2s remaining blockers, pull some fresh bricks to build, and get defered work done."

PR-2 (the poor-man ingenuity hunter) is a VERIFIED DEFER twice (R49 feasibility-layer, R50 the ingenuity
scissors). The user reopened it. R50 named the deferred reward's **ordered unlock**: (#1) catalyst obtainability
— **BUILT R51** (`catalyst_availability.py`); (#2) **a fail-closed recognizer on out-of-centre features**; (#3) a
proven reachable consumer. This round put unlock #2 before the mandated design gate.

## The proposal that was gated

An **out-of-centre interference recognizer**: EXCLUDE-only, fail-closed, R51-shaped. For a step whose atom-mapped
reaction centre is known, read the functional groups *outside* that centre and: **EXCLUDE** the "kitchen-selective
one-pot" claim on a recognized interferer (a competing free amine outcompetes the alcohol in O-acylation); stay
**NEUTRAL** only when every out-of-centre group is a recognized inert; **fail closed** (EXCLUDE) on an
unrecognized group — the R51 burden-of-proof flip applied to *substrate* features. Claimed to resolve KILL-1 by
reading a wider (whole-molecule) radius on top of the bounded-radius local-edit class key.

## The five-bearing DESIGN gate (run BEFORE any wiring)

| Bearing | Verdict | The load-bearing finding |
|---|---|---|
| **dalembert** (soundness) | **DEFER** | **The steric structure theorem.** `pentyl acetate` (kitchen) and `tert-butyl acetate` (NOT a Fischer one-pot — a tertiary carbinol dehydrates via E1 under acid catalysis) have a **byte-identical atom-mapped edit signature** AND **byte-identical out-of-centre functional groups** (both: one reacting hydroxyl on an all-carbon skeleton, zero competing nucleophiles) → both reach NEUTRAL, yet only pentyl is kitchen. The recognizer catches the amine blade (5-aminopentyl → EXCLUDE) but **re-collides pentyl with tert-butyl** on the substitution-degree blade, which lives *at* the centre and is not a functional group in any inventory. It moves the collision, it does not close it. |
| **birdperson** (architecture) | **DEFER** | **The base-rate inversion.** R51's flip is sound because an unrecognized *declared catalyst* is overwhelmingly an industrial metal (block is usually right). An unrecognized *substrate group* is overwhelmingly a **spectator** (block is usually wrong), so fail-closed-on-unrecognized false-EXCLUDEs real kitchen routes en masse. The "inert whitelist" is the *vouching* direction — a wrong inert entry is a false-NEUTRAL = false-VOUCH-equivalent. |
| **daniel** (census) | **DEFER** | 45 registered structures × `compile_synthesis` → 59 steps; the recognizer fires on **2/59, both already handled** (R48 guard on the Fischer family + a sourced record on 4-aminophenol). Non-vacuous but redundant. |
| **butter-robot** (YAGNI) | **KILL** | `smartchem/experiment/selectivity.py` **already exists** — a *sourced* (ACS J. Chem. Educ. DOI 10.1021/acs.jchemed.0c01512) `SelectivityRecord` giving paracetamol→FAVORED / 4-aminophenyl-acetate→DISFAVORED, wired into `rank_routes`. A sourced minor-isomer demerit is *better* than a blind whole-molecule EXCLUDE for the identical headline example. Zero ingenuity call sites. |
| **evil-morty** (wiring/consumer) | BUILD_w/-folds | Lone build vote: the registered `4-aminophenyl acetate` free-acid Fischer route sits on the affordability frontier with `hard_blockers=()`. **Refuted by the census:** the *ranker* carries the sourced demerit for the anhydride reactant set, and the free-acid route is honest UNKNOWN (silence, not a false-VOUCH) — no live output to change. |

**Verdict: DEFER, 4-to-1.**

## The load-bearing kill, in one line

An out-of-centre **functional-group** recognizer captures exactly the subclass of KILL-1's unbounded-radius
determinants that surface as a discrete group in a finite inventory (a competing amine). It is structurally blind
to the determinants that are **steric / substitution-degree at the centre** (tertiary carbinol → E1), remote
through-bond electronics, and ring-strain/conformation. For any such substrate every out-of-centre group is a
recognized inert → NEUTRAL → yet the route is non-kitchen: a residual **false-VOUCH-by-omission of exactly the
R51/KILL-1 shape**. Proven live: `tert-butanol`'s out-of-centre group multiset equals `pentanol`'s (both empty
beyond the reacting -OH) and their edit signatures are byte-identical, so **no** functional-group recognizer that
keeps pentyl NEUTRAL (it must, or it false-EXCLUDEs the kitchen case) can separate them.

## The three supporting refutations (verified against live code)

1. **Redundant with R48.** `feasibility_of_step` already returns UNKNOWN for *both* the pentyl and the
   5-aminopentyl free-acid Fischer condensations (the R48 domain guard fires on both), so there is no false
   "kitchen" pass at the feasibility layer to remove for the class the recognizer fires on — a feasibility-layer
   version is dead code.
2. **No live false-VOUCH to remove.** The one reachable route to the O-minor-isomer registered target
   (`4-aminophenol + acetic acid → 4-aminophenyl acetate + water`) is honest UNKNOWN on *both* selectivity and
   feasibility today. Per R49, a model's silence on a property is **not** a false-VOUCH. The sourced
   N-selectivity record covers the **anhydride** reactant set, not this free-acid one; and the anhydride route is
   architecturally unreachable (no anhydride in the commodity catalog).
3. **Base-rate inversion** (above): the flip's polarity does not transfer from catalyst to substrate.

## Architectural adjudication (why no home is right today)

- **NOT the feasibility layer.** R48 removes a *thermodynamic* lie (the acid-base salt sink) in ΔG's own
  currency. Chemoselectivity is not thermodynamics; failing the ΔG verdict closed for a chemoselectively-disfavored
  O-product is the R49 lesson in negative dress (a capability judgment on a model that does not measure the
  capability).
- **NOT a §10.4 affordability HARD BLOCKER like R51.** The substrate-feature base rate inverts R51's catalyst
  base rate, so unrecognized→block would sink real kitchen routes — and would sink the single FAVORABLE registry
  step (paracetamol's O-methylation, amide out-of-centre) unless the amide is hand-whitelisted.
- **The right home is the deferred substrate-aware SELECTIVITY model** that *measures* chemoselectivity, consumed
  by the still-deferred ingenuity reward. That consumer does not exist — which is exactly why this is a defer.

## The sound follow-up the gate surfaced (named, NOT built here)

A **DERIVED** recognizer is unsound (this kill); a **SOURCED** `SelectivityRecord` is not. Adding a sourced
free-acid 4-aminophenol N-selectivity record (`4-aminophenol + acetic acid → paracetamol` major) would flip the
O-minor-isomer route's selectivity from UNKNOWN → **DISFAVORED**, correctly telling the poor man "this reaction
makes paracetamol, not your O-ester" — consuming a *sourced fact*, dodging every kill above, with a live consumer
(the registered `4-aminophenyl acetate` target). This is **sourcing-gated**: it enters the table only when the
free-acid (or donor-general) N-selectivity is primary/textbook-sourced, dated, and readable — never fabricated
(the DOW-bromine discipline). It is the concrete unlock this defer recommends over rebuilding a derived recognizer.

**Sourcing attempted this round — DEFER, sourcing wall (recorded so nobody re-chases it).** A web recon looked
for a source clearing the bar the three existing `SEED_SELECTIVITY_RECORDS` meet (peer-reviewed/textbook, with a
quantified regiochemical ratio for the exact reactant pair) and did **not** find one:

- The existing citation `10.1021/acs.jchemed.0c01512` covers only the **acetic-anhydride** prep (confirmed via
  its abstract mirror), not the free-acid case.
- The one specific-reaction hit is a **patent**, WO2017154024A1 ("A process for synthesis of paracetamol",
  2017-09-14), Example 5: p-aminophenol + acetic acid + 1,4-dioxane, 120–150 °C → paracetamol. But it is
  **patent-tier** (below every existing record's journal tier), reports **no** O/N ratio (silence is not
  "O-isomer ruled out" — the *vacuous-green-over-an-empty-subject* trap), and carries a mass-balance red flag
  ("1.3 moles paracetamol per mole p-aminophenol", >100%). Not promoted to `ACCEPTED`.
- The **general-principle** framing (aromatic amine ≫ phenol nucleophilicity; amide thermodynamically favored
  over aryl ester; phenols are poor Fischer substrates) is chemically well-founded and *strengthens* N-selectivity
  under free-acid/thermal conditions — but no checked textbook locator (ISBN+page) was obtainable in-sandbox, only
  search-engine paraphrase, which would be fabrication to cite.
- Dead ends (don't re-chase): `pubs.acs.org` / `pubs.rsc.org` hard-403 (publisher wall); `hal.science` bot-walled;
  ACS Omega `10.1021/acsomega.8b01428` is the wrong isomer (2-aminophenol) + enzymatic; *Green Chem.*
  `10.1039/C4GC00166D` is the wrong substrate (hydroquinone + ammonium acetate, no pre-existing competing amine).

So the sound follow-up is real but **sourcing-blocked today** — the same shape as the second-organic-price and
modern-bromine sourcing walls. Unpark it if the free-acid (or a checkable donor-general) N-selectivity is
primary/textbook-sourced, or if the tier policy is explicitly relaxed to admit the patent with its caveats stated.

## Honest boundaries

- The `tert-butyl` non-kitchen fact and the `pentyl` kitchen fact are **asserted textbook chemistry** (E1
  dehydration of tertiary carbinols; Fischer esterification of primary/secondary alcohols), not computed — the
  same discipline the R50 scissors probe uses for its `_ESTER_FAMILY` flags. What is *computed* is that the
  recognizer cannot separate them (identical edit + identical out-of-centre groups + both NEUTRAL).
- The census (2/59) is over registered targets at the depths daniel sampled; a molecule a user types ad hoc could
  differ — but the structure theorem (the steric collision) is substrate-general, not census-dependent.
- This defer does **not** touch R51's catalyst gate (sound, shipped) or the ingenuity reward's other unlocks.

## Relationship to the deferred ingenuity reward (PR-2)

R50's **KILL-1 is deepened, not resolved**: the recognizer approach to unlock #2 is proven to move the collision
rather than close it. The reward remains **deferred**. The real unlock #2 is a substrate-reactivity model that
*measures* the steric/electronic (unbounded-radius) determinants — or, for a narrow but sound increment, a
sourced-fact consumer (the follow-up above). Unlock #3 (a proven reachable consumer) is untouched.
