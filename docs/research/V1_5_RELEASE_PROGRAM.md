# SmartChem — the post-1.0 release program (1.1 → 1.5, with 2.0 prerequisites)

**One authoritative map of what is done, what the 1.x ladder commits to, and what is deliberately a 2.0
obligation.** Supersedes nothing: `V1_0_RELEASE_GATE.md` and the `v1.0.0` tag remain the frozen 1.0 record.

## 0. Baselines (verified against the live repo, not a prompt)

| ref | SHA | note |
|---|---|---|
| `v1.0.0` (published release) | `8345bbb` | the stable 1.0 record; `git diff v1.0.0 -- smartchem/` vs `origin/main` is empty |
| `origin/main` | `99fce34` | 5 commits past the tag, all docs/launch — semantically ≡ `v1.0.0` |
| `feat/chemical-graph-projections` (PR #101, draft) | `3a37d46` (+#114) | this program's development branch (P0 + Waves A/B/C + CI OOM-fix; this commit adds Wave D #114); `__version__ = 1.1.0a1` |

## 1. Scientific authority model (invariant across the whole 1.x series — never relaxed)

These distinctions are load-bearing and every rung below preserves them:

1. Formula equality ≠ constitutional identity.
2. A formally conserving transformation ≠ an established chemical reaction.
3. A recognized structural reaction family ≠ laboratory feasibility.
4. Sourced conditions ≠ a complete procedure.
5. A complete procedure ≠ a particular bench's capability fit.
6. Bench capability ≠ safety certification.
7. A complete *bounded* search ≠ universal chemical completeness.

Readiness vocabulary (cumulative, weakest-link): `FORMAL_CANDIDATE < REACTION_VOUCHED < CONDITIONS_SUPPORTED
< PROCESS_SPECIFIED`. **A new validator is an instrument with a declared scope and identifiable failures. A
displayed diagram may EXPLAIN an existing claim; it may never MINT one.** The reaction-type oracle and the
graph re-derivation recognizers rerun the generator's OWN scission/retro machinery — a useful *internal
consistency* witness, explicitly **not an independent external-chemistry witness**; every claim that leans on
them says so.

## 2. What is actually implemented on the branch (the 1.1 candidate)

* **P0 — the version boundary is repaired.** `__version__ 1.0.0 → 1.1.0a1`; the version-independent
  fingerprint golden was re-frozen under that declared MINOR, with a field-by-field proof
  (`V1_1_COVERAGE_EXPANSION_110.md`) that the ONLY semantic move is #110's paracetamol promotion, under an
  unchanged `semantic_digest`. `Verified`.
* **#110 activated acyl transfer** — the 18th recognized class (anhydride/acyl-halide onto O/N/S). Flips the
  real industrial paracetamol route (4-aminophenol + Ac₂O → paracetamol + AcOH) to `PROCESS_SPECIFIED`.
  The **paracetamol litmus north-star firing for the first time.**
* **#111 alkyl sulfonate-ester transfer** — the 19th recognized class (a sulfonyl halide sulfonylating an sp3
  alkyl alcohol: mesylate/tosylate/triflate activation). The cheap Wave-C recognition win. A first adversarial
  pass broke the initial cut with three false-vouches (carboxylic-acid mixed anhydride / masked-carbonyl gem-diol/
  hemiacetal/enol / latent sulfate miscount); closed by an sp3-alkyl-carbinol + sulfonate-S census, with aryl-O
  (phenol) deferred to #105. A second, independent adversarial pass found no false-vouch. `Verified` (bench 15/15,
  false-vouch 0; the three kills retained as permanent controls; CI required jobs green on `22ea54e`).
* **#114 bond-order-edit (de/hydrogenation) family behind the opt-in `bond-order-edit-v1` profile** — a REACHABILITY
  gain, **not** a 20th recognizer (the oracle count stays 19). The already-sound `BondOrderEditProvider` (raise one
  heavy–heavy bond by one order, shed H₂; construction certificate + W1 descent) is now reachable through a NAMED,
  reviewed, selectable algebra profile (capped-scission base + bond-order-edit) instead of only a hand-built test
  registry. The synthesis-direction hydrogenation route `unsaturated + H₂ → saturated` becomes REACHABLE under the
  profile (4/4 bench cases) and is unreachable under either default. **Opt-in only:** one dict entry, no default
  constant flipped, version-independent fingerprint unmoved. **Honest demotion:** the family has no oracle
  recognizer, so its routes stay `FORMAL_CANDIDATE` ("unrecognized") — reachability (W1/W3), never a minted vouch
  (the state paracetamol-via-Ac₂O held before #110). An evil-morty pass (1,200+ steps, attribution-theft surface)
  plus an independent end-to-end sweep found 0 false-vouch, 0 internal-error leak, 0 default perturbation, 0 crash.
  `Verified` (profile test 32/32; bench reachable 4/4, false-vouch 0).
* **Typed chemical graph projection + named synthesis schemes** — DOT/Mermaid/SVG, offline HTML, optional
  RDKit depiction, route/DAG ensembles (#128/#129 family-naming + completeness honesty on the branch).
* **Soundness fixes on the branch (OPEN on main — see §6):** #124 cyclic-refusal, #126 forged-centre retired,
  #131 typed recognition outcomes, #132 pericyclic content-determinism.

## 3. Proposed 1.1 → 1.5 ladder (a PROPOSAL; each rung names its own gate)

| rung | theme | issues | owner modules | why this order |
|---|---|---|---|---|
| **1.1** (this branch) | graph workbench + first coverage wins | graph PR #101, #110, **#111**, **#114**, #124/#126/#128/#129/#131/#132 | `graph_projection`, `depiction`, `reaction_type_oracle`, `readiness`, `algebra_profiles` | highest return: a trustworthy workbench + two real recognition wins (18th/19th classes) + the first opt-in operator profile (#114) |
| **1.2** | cheap RECOGNITION wins (no new generators) | ~~#111~~ (landed early on 1.1), #112 SN2, #115 Claisen-lock | `reaction_type_oracle` | recognition is cheaper + lower-risk than generation; max coverage per rule |
| **1.3** | contained OPERATOR families w/ transformation certificates | ~~#114 hydrogenation~~ (landed early as the `bond-order-edit-v1` opt-in profile on 1.1), #116 elimination, #117 enolate C–C | `transform_provider`, `bond_order_edit` | each family ships a conservation + locality certificate, opt-in, no default-flip |
| **1.4** | bounded SEARCH + sound lateral capability | #104 W1 redesign, #124/#125 arity, #123 opt-in finite lateral | `routes`, `lateral_search`, `structure_descent` | an opt-in, finite, SOUND lateral search; fusion into `search_routes` stays deferred |
| **1.5** | evidence/capability hardening + release | #107 catalyst ledger, #109 latent-fiction audit | `catalyst_availability`, capability layer | consolidation; the 1.5 acceptance gates (§4) must all be green |

## 4. Mandatory 1.5 acceptance gates

1. **No demonstrated false-VOUCH** on the standing adversarial corpus + every new rule's hostile controls.
2. **Version-boundary discipline:** every semantic move since 1.0 is classified in a forensic record; the
   version-independent golden is green; no undeclared promotion can recur (the gate fails if it does).
3. **Workbench threat model:** hostile graph/name/status fixtures render inert; UNATTESTED never displays as
   COMPLETE; family names derive from the oracle, not caller-supplied centres; renderer is resource-bounded;
   core runs without RDKit/PySCF.
4. **Fail-closed preserved everywhere:** an unread demand stays `UNKNOWN`; a finer requested identity layer
   (stereo/config) never silently terminates on the wrong isomer — it refuses.
5. **Full OOM-safe suite green** (`scripts/run_suite.sh`) **and** clean wheel-install tests on Python
   3.10–3.13, on the FINAL branch SHA — not an ancestor. No cancelled/partial run counts as green.

## 5. Explicit 2.0 prerequisites (deferred — recorded, NOT implemented)

* **#105 per-atom formal-charge rail** — today only the molecule's one global charge is carried; blocks all
  ionic/dipolar chemistry from being represented soundly.
* **#106 radius-1 environment predicate** — `ReactionCenter` is context-free; local molecular-environment
  predicates are a 2.0 representation change.
* **#108 organometallic elements** (Li/Sn/Ni/Al/Ti/[B]).
* **#130 configuration-aware route identity** — constitution-only matching must never terminate on the wrong
  enantiomer under a finer requested identity layer (today: refuse; 2.0: honor).
* **The general reaction-event calculus** — fusing the opt-in lateral search into `search_routes` (true
  scission vs connected lateral vs intramolecular-with-coproducts as separate typed event families, with a
  correct finite-depth/state-budget termination proof and a disclosed completeness boundary). Its proof
  burden exceeds the 1.5 budget; 1.5 ships only the opt-in finite lateral capability.
* **Atom-mapped transformation witnessing** + source-subject binding of procedure evidence.

## 6. Issue reconciliation (branch vs main)

Issues #103–#132 are **OPEN on `main`** and correctly so: their fixes live on the unmerged PR #101. A fix
`Verified` on the branch is NOT resolved on `main` until the PR merges. Close-on-merge, not close-on-claim.

## 7. Governance — the 3-lane projection (unchanged from the generic-compiler reorientation)

A = Alpha-conformance, B = chemical-genericity, C = bench-readiness. **Progress in one lane never implies
another.** A generic bounded SEARCH compiler parameterized by a still-narrowing transform algebra; the oracle
is a readiness-layer demoter, not a search provider.

## 8. Reproduction (every milestone's proof command)

```sh
# P0 version boundary + forensic differential:
.venv/bin/python experiments/v1_0_version_transition.py --check-golden        # NO DRIFT
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_v1_0_version_transition.py tests/test_v1_0_public_contract.py
# recognizer count + #110:
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_transform_algebra_expansion.py tests/test_activated_acyl_transfer_110.py
# #111 alkyl sulfonate-ester transfer (adversary-hardened, 19th class):
.venv/bin/python -m experiments.sulfonate_ester_transfer_111
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sulfonate_ester_transfer_111.py
# #114 opt-in de/hydrogenation profile (reachability gain, honestly demoted, adversary-clean):
.venv/bin/python -m experiments.bond_order_edit_profile_114
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_bond_order_edit_profile_114.py
# readiness laws (graduation + non-monotonicity cap preserved):
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_v0_8_readiness_core.py tests/test_v0_9_capability_round_iii.py
# the full OOM-safe gate:
scripts/run_suite.sh
```

## 9. Known limitations / source boundaries

* `is_closed_shell_neutral` is a representation-relative heuristic — no general per-atom charge/electron
  model; its scope is bounded, not a universal closed-shell proof (2.0 #105 is the real fix).
* #111 recognizes ALKYL sulfonate esters only. Aryl-O (phenol → aryl mesylate/tosylate) is NOT recognized: a
  Kekulized aryl carbinol carbon is indistinguishable from an acyclic enol in the aromaticity-free graph, so the
  sound scope is alkyl-O (honest coverage loss, deferred to the 2.0 aromaticity model #105).
* #114's `bond-order-edit-v1` profile delivers REACHABILITY, not recognition: the de/hydrogenation family has no
  reaction-type oracle recognizer, so its routes stay `FORMAL_CANDIDATE` ("unrecognized"). Graduating them to
  `REACTION_VOUCHED` is a separate, adversary-gated recognizer task (deferred). The no-false-vouch property is
  inherited from the recognizers' re-derivation discipline (each reconstructs all declared reactants, and H₂ is
  irreducible as a retro fragment); a standing invariant test pins it, and that discipline MUST hold for every
  added class. The profile is opt-in — promoting it toward a default would first need a measured search-cost blast
  radius (its H₂-shedding edges widen branching on large saturated substrates: bounded, never a hang, not yet
  measured at scale).
* RDKit = dev-only oracle; it never changes a verdict. The committed baseline runs without it.
* Procedure-source evidence proves arithmetic/placement, not subject binding (deferred, §5).
* A complete bounded search is complete only within the declared grammar; absence of a route is never
  evidence of absence.
