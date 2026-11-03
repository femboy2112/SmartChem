# Activator ledger (#107) -- the typed stoichiometric-activation requirement, as a pure feasibility demoter

*Problem B, the long-deferred other half of reaction-TYPE recognition. Source: the reaction-algebra coverage audit's
W0.4. Branch-only, NOT merged. Adversarially hardened (a real chemistry kill found + fixed). Every claim labelled.*

| field | value |
|---|---|
| status | **research. A new feasibility-layer module + a 4-line symmetric wiring into the affordability frontier. Branch-only, NOT merged.** |
| branch | `research/activator-ledger` (off the released 1.1.0 `main` `9e8fa5f`) |
| new code | `smartchem/experiment/activator_ledger.py` (+ `tests/test_activator_ledger_107.py`); wiring in `smartchem/service.py` (producer + loader) |
| scope | ONE ledger entry: the Claisen condensation requires an ENOLIZING_BASE. The mechanism generalizes; the DATA stays base-rate-safe at the one unambiguous case. NO oracle recognizer added (20-class count unmoved). |

## 1. The gap (W0.4, "Problem B")

Reaction-TYPE recognition (`reaction_type_oracle.py`) answers **Problem A** -- "is this a valid instance of class
T?" -- as a pure function of the conserved molecules. It deliberately says nothing about the NON-conserved
activation a class needs to run. The #115 Claisen recognizer vouches the ester+ester -> 1,3-dicarbonyl skeleton
while its own docstring defers the stoichiometric enolizing base to "Problem B / #107". So a recognized Claisen step
whose conditions name no base ends REACTION_VOUCHED / disposition CLEAN and reads as poor-man-reachable on the
affordability frontier -- a **capability over-claim**: a reaction that cannot proceed without a strong base is
presented as kitchen-runnable with nothing in the pot but the two esters. #107 closes exactly that.

## 2. The design (orthogonal, pure demoter, base-rate-safe)

- A new module `activator_ledger.py`, a **sibling** of `catalyst_availability.py` (CATALYST-OBTAIN-01). The two are
  orthogonal: obtainability asks "can the kitchen GET a declared catalyst?" (silence = neutral); the activator
  ledger asks "does the recognized CLASS REQUIRE an activator the conditions do not supply?" (silence about a
  known-necessary base = unmet -> demote, because the requirement is a positive type-level fact, not a caller
  string).
- `ActivatorRole` enum (today: `ENOLIZING_BASE`), `REQUIRED_ACTIVATORS: {class_display_name -> {roles}}` (today:
  the Claisen condensation), `classify_activator_roles(name)` (positive whitelist, exact normalized name +
  case-fold-certify, **no substring scan** -- mirrors catalyst_availability's discipline), and
  `route_activator_blockers(route)` (mirrors `route_reaction_type_blockers`).
- **Pure DEMOTER** -> no-false-VOUCH on TYPE by construction: it only ever ADDS a `hard_blocker` (disposition
  **REAL_BUT_HARD** -- a real reaction merely out of reach), NEVER a `fiction_blocker` (NOT_A_REACTION) and NEVER an
  impossibility/feasibility claim. Type-validity is untouched; only poor-man REACHABILITY is withheld, recoverably.
- **Wiring (4 lines, symmetric):** producer `_affordability_frontier` (`service.py` ~3545) appends
  `route_activator_blockers` into `hard`; loader `_check_frontier_coherence` (~2923) re-derives it into
  `rederived_hard` from the identity-bound replay. It touches neither `_RECOGNIZERS`, `semantic_digest`, nor
  `result_digest` (the frontier is excluded from both) -- a pure MINOR feasibility-layer addition, exactly as #115
  Claisen was logged.

## 3. Claim ledger

Labels: DEMONSTRATED (independent re-derivation / adversary-proven), VERIFIED (equation/implementation),
OBSERVED (this round), REFUTED (and fixed).

| # | claim | label | basis |
|---|---|---|---|
| L1 | A baseless (or weak-based) recognized Claisen step is demoted to REAL_BUT_HARD; a Claisen declaring a recognized enolizing base is cleared | VERIFIED | `tests/test_activator_ledger_107.py` (step + route level); behavioural smoke |
| L2 | The ledger NEVER false-VOUCHes TYPE and NEVER emits a fiction/impossibility claim (pure demoter) | DEMONSTRATED | Evil Morty: ~70 hostile strings (weak bases, superbases, substring/unicode/dilution tricks) -- ZERO cleared the requirement wrongly; wiring lands in `hard_blockers`, never `fiction_blockers` |
| L3 | Among the 20 recognized classes, ONLY the Claisen condensation has an unambiguous stoichiometric activation requirement (so one ledger entry is complete, not a gap) | DEMONSTRATED | d'Alembert walked all 20: the Claisen is the only carbanion/enolate-forming class; Fischer (acid = catalyst, not stoichiometric), #110 activated-acyl & #111 sulfonate (self-activating electrophile), and the 14 pericyclics correctly need none; aldol/Michael/cross-couplings are NOT recognized today |
| L4 | The enolizing-base whitelist admits a reagent that does NOT cleanly enolize an ester/ketone | REFUTED (and fixed) | d'Alembert: the alkyllithiums (n-BuLi/s-BuLi/t-BuLi, MeLi/PhLi) are strong but NUCLEOPHILIC -- they 1,2-add to the carbonyl, not enolize it. A false-CLEAR in the module's own unsafe direction. FIXED: removed; the regression is locked (they must NOT clear); see section 4 |
| L5 | `semantic_digest` / the version-independent fingerprint is UNMOVED by the change | VERIFIED | `tests/test_v1_0_version_transition.py` green; empirically no current search target generates a Claisen retro-step -> the channel is data-dark in production today (R59's posture) |
| L6 | The wiring inherits the frontier's load-time anti-tamper guarantee (a stripped activator blocker is caught) | VERIFIED | activator blockers ride the SAME `hard_blockers`/`rederived_hard` sets as the catalyst channel; `tests/test_poor_man_tamper_hardening.py` green. BOUNDARY: on the DEFAULT thin transport (no replay) re-derivation is skipped -- the SAME inherited boundary the catalyst/fiction channels ride |

## 4. The adversarial pass, and the one real defect (RED-first, fixed)

Two orthogonal read-only adversaries on the module (authorized own-code hardening): **Evil Morty** (implementation/
exploit) and **d'Alembert** (chemistry/structure refutation).

- **No false-VOUCH exists.** Evil Morty could not clear the requirement with a single weak/non-base in ~70 attacks;
  the architecture (exact-match whitelist + case-fold-certify, no substring scan) holds. One LOW totality crack
  (`route_activator_blockers` raised on a *truthy non-iterable* `steps` -- unreachable from a real `ExperimentRoute`,
  symmetric with its siblings) was fixed anyway to honour the docstring's "total".
- **One real chemical defect, in the module's own-named UNSAFE direction:** d'Alembert proved the alkyllithiums were
  a **false-CLEAR**. I built the whitelist's conservatism against the *strength* axis and missed that the failure
  mode for carbonyl enolization is *selectivity*: n-BuLi et al. are strong enough but NUCLEOPHILIC, so with an ester
  in the pot they 1,2-add to the carbonyl rather than deprotonate the alpha-C -- which is the whole reason the
  textbook enolate bases are the hindered, non-nucleophilic amides (LDA/LiHMDS/KHMDS) and the alkoxides/hydrides,
  NEVER an alkyllithium.
- **Fix (accuracy, safe direction):** removed all alkyllithiums (and MeLi/PhLi/Grignard stay excluded); the
  resulting false-EXCLUDE of a hypothetical n-BuLi-declared Claisen is vanishingly rare and SAFE (recoverable). The
  test now asserts they must NOT clear. Added the common `t-BuOK`/`tBuOK` spellings and the hindered amides
  `LiTMP`/`KDA` to reduce an unnecessary false-EXCLUDE.
- **Future-exposure (d'Alembert) closed:** the base-rate argument is a SNAPSHOT over today's 20 classes; nothing
  forced a ledger re-decision when a NEW enolate-forming/catalysed recognizer lands (the roadmap plans aldol /
  Knoevenagel / Michael / cross-couplings). Added a **registry-fingerprint guard** (`_assert_registry_unchanged_
  since_ledger_review`): if the recognizer set changes, import fails LOUD, forcing the ledger to be re-reviewed
  rather than silently gapping into a false-VOUCH on growth. [[base-rate-dependent-fail-closed-polarity]]
  [[a-capability-reward-must-be-gated-on-the-capability-model]] [[a-label-is-not-a-binding]]

## 5. Scope and non-goals
- ONE ledger entry (Claisen -> ENOLIZING_BASE). The mechanism generalizes; the DATA is deliberately conservative.
- NO 21st recognizer (the coverage count is unmoved; this is a feasibility-layer demoter, not a type recognizer).
- Data-dark in production today: no current search target generates a Claisen retro-step, so the fingerprint is
  unmoved and the demotion fires only on a hand-built or future-reachable Claisen route. Proven correct at the
  unit + producer level; the end-to-end demotion is verified only on the thick-replay transport (the inherited
  thin-transport boundary is documented).
- Thermo's acyl-condensation UNKNOWN guard (`feasibility.py`) is a SEPARATE, complementary verdict (a DeltaG
  direction) -- not duplicated here.
