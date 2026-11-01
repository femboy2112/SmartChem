# Operation SmartChem XIV — the lactonization recognizer + event-search wiring (Track E, production 1.5 line)

**Date:** 2026-10-31. **Branch:** `feat/lactonization-exhaustiveness` (off `integration/v1.5-candidate` #149, PR #151).
**Scope:** the production chemical-event-algebra track ONLY — the 25th reaction-type recognizer and the wiring of the
intramolecular-lactonization generator into `search_event_routes`. The 2.0 physicalization general-kernel work
(Operation XIV Tracks A–D) is a SEPARATE research branch and is NOT in this PR. Nothing is merged, tagged, or
published; this remains the unreleased 1.5 candidate line.

This finishes the "digest-delicate deferred follow-on" that Operations XII and XIII named: XII P2 shipped the
standalone lactonization *generator* (a reachability producer the oracle honestly DEMOTED); XIII §9 made its
enumeration report exhaustiveness. Track E adds the two pieces that make the type-3 event fully live: a
generator-independent *recognizer* (so the oracle VOUCHES the step) and the *wiring* into the bounded event search
(so the search EMITS the step), under a termination proof that admits the rank-increasing retro step.

---

## A. What changed (files + the reviewed transitions)

| file | change |
|---|---|
| `smartchem/experiment/reaction_type_oracle.py` | new recognizer `_intramolecular_lactonization`; registered as the **25th** `_RECOGNIZERS` entry under the generator's canonical `LACTONIZATION_CLASS` name; docstring class count 24→25 + a (25) entry |
| `smartchem/experiment/activator_ledger.py` | reseal: `_REVIEWED_CLASS_COUNT` 24→**25**, `_REVIEWED_REGISTRY_DIGEST` `0dfb95140ad927ef`→**`d9f7e867e8f1a1d2`**, with the recorded base-rate review (lactonization adds NO activator entry) |
| `smartchem/experiment/event_search.py` | wired the lactonization provider as the first `INTRAMOLECULAR_COPRODUCT` producer; receipt/result schema v1→**v2**; new `max_coproduct_events` + `coproduct_match_budget` params and the three-component termination measure |
| `tests/test_lactonization_recognizer_xiv.py` | **new** — the 22-test adversary-gated acceptance battery |
| 6 existing test files | reviewed-transition updates (P2 recognition flip; 5 class-count 24→25; event-search "no producer" rename + pure-scission parity tightened) |

**Reviewed semantic transitions (explicit, not silent):**
- The oracle now recognizes a 25th class. Per the standing invariant, a recognizer moves **count/readiness** but NOT
  the frozen `semantic_digest` (it is a demoter→voucher, not a wire-contract change) — the version-independent golden
  is UNMOVED (no corpus case is a lactonization).
- The activator-ledger registry digest moved, which the import-time guard forces to be an explicit re-decision. The
  recorded decision: intramolecular lactonization is a proton-CATALYSED dehydrative esterification (like its
  intermolecular sibling, which carries no ledger entry) — it forms no enolate and needs no metal, so it adds NO
  `REQUIRED_ACTIVATORS` entry.
- The opt-in event-route schema went v1→v2 (the grammar gained a third producer + budget). This is NOT the frozen
  1.0 `RouteSearchReceipt` replay surface, which is untouched.

## B. The recognizer — content-deterministic, generator-independent, shape-classifier-independent

`_intramolecular_lactonization(step)` reads ONLY the step's conserved molecules. Shape gate: exactly ONE principal
precursor, strictly LARGER than the target (rank-increasing), the target itself, and EXACTLY ONE water coproduct;
both principal species closed-shell neutral. Then the **structural witness**: the single connected precursor's OWN
carboxyl + hydroxyl groups must intramolecularly esterify to EXACTLY this target (`_lactonizes_to`, canonical-identity
compared). It never trusts provenance, never reads a carried `reaction_center`, and never leans on `classify_event`'s
SHAPE verdict. Intramolecularity is proven by the model that has the atom-map (a bond formed WITHIN one connected
molecule), never proxied by a local shape count.

**Why reusing `_lactonizes_to` is not a common-mode cheat.** The generator's edge certificate and the recognizer
share the forward re-derivation, so a bug there could in principle fool both. The adversarial corpus defuses that:
the recognizer is attacked with HAND-BUILT, non-generator steps that share shape — a diacid→anhydride (same type-3
shape, same water coproduct, one connected precursor), a fabricated same-formula isomer, a retro-Diels-Alder — and
refuses every one. A rubber stamp could not; the witness is doing load-bearing discrimination.

## C. The wiring + the termination proof (the rank-increasing step)

The retro lactonization step is **rank-INCREASING**: the hydroxy-acid precursor carries the expelled water's atoms,
so it is 3 atoms LARGER than the lactone target. The pre-existing lexicographic measure `(atom_count, hops_left)`
could not admit it. Track E extends it to the three-component lexicographic measure on ℕ³:

> **M(t, cop_left, hops_left) = (coproduct_events_left, atom_count, hops_left)**

- SCISSION: 1st unchanged, 2nd strictly drops (W1).
- CONNECTED_LATERAL: 1st, 2nd unchanged, 3rd drops.
- INTRAMOLECULAR_COPRODUCT: 1st (most-significant) strictly drops — so M decreases **regardless** of the 2nd
  component (atom count) increasing. The coproduct budget MUST be the most-significant component; it is the only
  thing that dominates the atom-count growth a rank-increasing step causes.

ℕ³ under the lexicographic order is well-founded → the search terminates even with `max_depth` unbounded. The
OPERATIVE halting guard remains `max_depth − depth` (every edge recurses at depth+1); the triple is the independent
chemical certificate (d'Alembert discipline: name the measure the code enforces, not only the prettiest one).

**Inverse cycles** are doubly refused: the ISSUE-124 ancestor guard, and — for coproduct events specifically —
`cop_left` strictly decreases and never resets, so no state can recur across a type-3 step.

**Honest receipts.** `complete` is False whenever any budget, depth, hop, or coproduct bound truncated the search.
A coproduct-site scan that hit `coproduct_match_budget` flags `coproduct_match_truncated`; a node that still had a
type-3 successor after its coproduct budget was spent flags `coproduct_events_truncated` — the exact analogues of the
lateral counters.

## D. Verification (this is NUMERICAL/STRUCTURAL verification, not measured validation)

- Recognizer: vouches a GENERATED and a HAND-BUILT lactonization; refuses retro-DA (non-water coproduct),
  diacid→anhydride (no forward lactonization), a same-formula isomer, an intermolecular esterification, a scission, a
  lateral, and a charged species — all fail-closed.
- Wiring: a lactone target (γ-butyrolactone) is **end-to-end reachable** from a declared hydroxy-acid precursor via
  one type-3 event, which is oracle-VOUCHED, with a COMPLETE receipt; `max_coproduct_events=0` disables the producer
  (reproduces the pre-XIV grammar); hostile budgets (cop=4, hops=3, depth=6, no stock) terminate with ≤8 nodes.
- Reseal: the ledger import guard forced the digest re-decision; `test_activator_ledger_107` recomputes the digest
  from the live 25-name registry and agrees.
- `tests/test_lactonization_recognizer_xiv.py`: 22/22 pass. The directly-affected set (9 files, 471 tests after the
  transitions) is green; ruff clean on every changed file. Full OOM-safe suite: recorded in the PR once green.

## E. Boundaries held
Structural type-validity ONLY (Problem A): a vouched lactonization route is conservation-valid and
oracle-recognized; it is NEVER a claim of feasibility, rate, ring-strain penalty, or kinetic accessibility. The
`semantic_digest` / frozen replay surface is untouched. Nothing merged, tagged, or published.
