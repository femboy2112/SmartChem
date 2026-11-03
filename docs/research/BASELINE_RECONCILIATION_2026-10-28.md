# Baseline & Issue/PR Reconciliation — 2026-10-28

**Authoritative map of the released 1.1.0 state, the open issues #103–#136, and the live
PRs, verified against the repository (not a prompt snapshot).** Supersedes the issue-state
table in `V1_5_RELEASE_PROGRAM.md` §6, which was written **pre-#133-merge** (it records
`main = 99fce34` with the 1.1 recognizers "branch-only"). PR #133 has since merged; the 1.1
production prefix is now **on `main`**.

Claim labels: `Verified` (independently re-derived / tests re-run this round), `Observed`
(seen once, e.g. a CI run or a static read, not re-executed here), `Conjectured`, `OPEN`.

## 0. Baseline coordinates (Verified)

| ref | SHA | note |
|---|---|---|
| `v1.0.0` (published) | tag | frozen 1.0 record |
| `v1.1.0` (published) | tag | the released minor |
| `origin/main` | `9e8fa5f` | merge of PR #133 (`release/1.1.0`); `__version__ = "1.1.0"` |
| `feat/chemical-graph-projections` (PR #101, draft) | `9dab5ea` | Round VII research chamber, `__version__ = "1.1.0a1"` — **not** production |
| `research/physicalization-2x` (PR #134, draft) | — | 2.0 research track |
| `research/activator-ledger` (PR #135, draft) | `ab35f5d` | #107 feasibility gate |

Test baseline (Verified this round): with **RDKit absent** (pure committed baseline), the
targeted recognizer suite on `9e8fa5f` is green —
`Verified[.venv/bin/python -m pytest <10 reconciliation files> → 129 passed, 3 skipped]`
(the 3 skips are the `importorskip` RDKit guards). Full OOM-safe suite not re-run this
round; PR #133's release gate ran it green on `9e8fa5f` (`Observed`, from the release record).

## 1. Reaction-type oracle: 20 recognizers (Verified)

`_RECOGNIZERS` at `smartchem/experiment/reaction_type_oracle.py:1136-1165` holds exactly 20
entries: 3 dehydrative condensations · 1 activated acyl transfer (#110) · 1 sulfonate-ester
transfer (#111) · 1 Claisen condensation (#115) · 8 Diels–Alder · 4 [3,3]-sigmatropic ·
2 electrocyclic. Pinned by `test_oracle_now_has_twenty_recognizers`
(`tests/test_claisen_condensation_115.py:71`, `tests/test_sulfonate_ester_transfer_111.py:30`)
and `test_oracle_has_twenty_recognizers` (`tests/test_transform_algebra_expansion.py:45`).

## 2. Issue reconciliation #103–#136 (against `origin/main` 9e8fa5f)

**Standing rule honored:** an issue is OPEN until its resolution is *on `main`*, not when it
is claimed on a branch. The 8 SHIPPED rows below are resolved on `main` yet their GitHub
issues are still OPEN — a bookkeeping gap, not missing code.

| Issue | Verdict | Evidence (origin/main) |
|---|---|---|
| #110 activated acyl transfer | **SHIPPED** | `_activated_acyl_transfer` `reaction_type_oracle.py:497`, registered `:1140-1141`; O/N/S nucleophiles only (C-acylation → #107). Tests `tests/test_activated_acyl_transfer_110.py` (Verified green). Paracetamol-via-Ac₂O route. |
| #111 aryl/thio/oxoacid ethers & esters | **PARTIAL** | Only **alkyl sulfonate-ester** `_sulfonate_ester_transfer:667` (`:1142`). Absent: anisole/aryl ethers, thioethers, phosphate, nitrate esters, sulfonamide. Tests `tests/test_sulfonate_ester_transfer_111.py` (Verified green). |
| #112 SN2 at sp3 carbon | **OPEN** | No R–X leaving-group SN2 recognizer; `_n_alkylation:363` is dehydrative, not halide SN2. (absence-of-evidence: registry + grep) |
| #113 metal cross-coupling | **OPEN** | No Kumada/Negishi/Stille/Heck/Sonogashira/Buchwald recognizer. |
| #114 BondOrderEdit hydrogenation | **PARTIAL** | Generator SHIPPED as opt-in profile `"bond-order-edit-v1"` `algebra_profiles.py:120`; **recognizer ABSENT by design** (`algebra_profiles.py:110-116`). Tests pin the abstain-not-match contract (Verified green). |
| #115 Claisen condensation | **SHIPPED** | `_claisen_condensation:765` (`:1143`), 20th class, orientation witness rejects the butanone fiction. Not the [3,3] `_claisen_rearrangement:1061`. Tests `tests/test_claisen_condensation_115.py` (Verified green). |
| #124 ancestor-as-stocked-leaf | **SHIPPED (caveat)** | Guard `routes.py:543-549` (linear) `:787-792` (DAG). **Proven NO-OP on the current W1 strict-rank grammar** — a safety net for future rank-flat/reversible providers; its test drives a *synthetic* reciprocal provider, not the real lateral path. `tests/test_issue_124_cyclic_refusal.py` (Verified green). |
| #126 forged ReactionCenter | **SHIPPED (caveat)** | Field `step.py:115` (`compare=False`) is **advisory and never recognition evidence**; no recognizer reads it (the only `.reaction_center()` is the oracle's own re-derivation `:302`). **Neutralized, not refused:** a forged centre is still *accepted and stored* (type-checked only), displayed as "DECLARED". `tests/test_issue_126_forged_center.py` (Verified green). |
| #128 DA family from centre equality | **SHIPPED** | `_reaction_family_for_step` `graph_projection.py:268-284` calls `recognize_reaction_type` (oracle re-derives). `tests/test_synthesis_scheme.py:79` (Verified green). |
| #129 UNATTESTED completeness | **SHIPPED** | `graph_projection.py:346-365` marks missing receipt UNATTESTED (`receipt_digest=None`); `graph_cli.py:37-51` exits 3, never "complete". Tests (Verified green). |
| #131 typed oracle diagnostics | **SHIPPED (additive)** | `RecognitionOutcome` `reaction_type_oracle.py:159`, `recognize_reaction_type_outcome:184`; a raiser → `faults`, never MATCH. **Caveat:** ABSTAIN and INTERNAL_ERROR still collapse to the same demotion (observability only). `tests/test_issue_131_typed_outcomes.py` (Verified green). |
| #132 pericyclic content-determinism | **SHIPPED** | No pericyclic recognizer reads a centre; each re-derives via its guarded retro; closed-shell hardening added. `tests/test_pericyclic_layer_a_fuzz_132.py` asserts 14 distinct class names (Verified green). |
| #103 synthesis-algebra epic | OPEN (umbrella) | tracks the whole coverage campaign |
| #104/#125/#123 search/arity/lateral | OPEN | 1.4 obstruction (deep; see §5) |
| #105 per-atom charge · #106 radius-1 predicate · #108 organometallic elements | OPEN | 2.0 representation rails |
| #107 catalyst/activator ledger | **PARTIAL (on PR #135)** | see §3 |
| #109 latent-fiction audit | OPEN | permanent negative controls not yet landed |
| #116 elimination · #117 enolate C–C · #118 [2+2]/ene · #119 C=O⇄C=N · #120 Grignard | OPEN | 1.3 reaction-algebra expansion |
| #121 [3+2] · #122 oxidation/FGI | OPEN | blocked on infra (#105 / #104) |
| #130 configuration-aware identity | OPEN | 2.0; today: refuse, not honor |

**Doc drift found (both stale, both safe to fix):**
- `reaction_type_oracle.py:~96` docstring still says "EIGHTEEN ACTIVE CLASSES" — code has 20.
- `bond_order_edit.py:218-221` still says the provider is "absent from any certified profile
  this round" — contradicts `algebra_profiles.py:120` where `bond-order-edit-v1` wires it.

## 3. PR #135 activator ledger (#107) — Phase I-B review verdict: **sound, review-ready**

Tip `ab35f5d`, DRAFT. CI **green on the exact tip** (run `40067722500`, 7/7: test 3.10/3.12,
wheel-install 3.10–3.13, PySCF smoke) — `Observed`. Diff: 4 files, **+629 all additions**
(`smartchem/experiment/activator_ledger.py` +297, `service.py` +11 symmetric wiring,
`tests/test_activator_ledger_107.py` +230, one doc). **`reaction_type_oracle.py` and every
other `smartchem/` file byte-identical to `9e8fa5f`** (`Verified[git diff --stat]`).

All 6 review properties HOLD (`Verified`):
1. Positive requirement — `REQUIRED_ACTIVATORS` has exactly the Claisen→`ENOLIZING_BASE`
   entry; demotes only when the base is missing; no analogy-fabricated requirements.
2. No false-CLEAR — weak/wrong reagents (NaOH, NaHCO₃, pyridine, Et₃N, H₂SO₄) stay demoted;
   `_MUST_NOT_FILL` locks the d'Alembert kill (n-BuLi/MeLi/PhLi/EtMgBr are nucleophilic, not
   enolizing bases).
3. No "impossible" over-reach — only writes `hard_blockers` (REAL_BUT_HARD), never
   `fiction_blockers`.
4. Feasibility-only — oracle & `semantic_digest` untouched (diff proves it).
4b. Producer and verifier both call `route_activator_blockers`; replay is digest-bound; a
   round-trip probe confirmed identical blocker counts and that adding a base to the replay
   breaks the digest bind.

**The cross-phase landmine (characterize, do not trip):** the ledger carries a **registry
fingerprint guard** — `sha256("\n".join(sorted(_RECOGNIZERS display names)))[:16] ==
_REVIEWED_REGISTRY_DIGEST ("2a9ee79ec4c018a9")`, plus `_REVIEWED_CLASS_COUNT = 20`. It does
**not** reach `semantic_digest` (display names only). **Any** recognizer add/remove/rename
invalidates it. The import is **lazy** (function-local in `_affordability_frontier` /
`_check_frontier_coherence`), so a stale guard raises `AssertionError` **on the first
routes-mode frontier build — a runtime crash in a production path**, not at import. Therefore:
- **Every future recognizer PR that also carries #135 must bump both constants and re-review
  `REQUIRED_ACTIVATORS` in the same change.** On `main` today there is no `activator_ledger`,
  so a recognizer PR *off main* (e.g. #116) does not trip it — but the moment #135 and a new
  recognizer coexist, the two constants are a merge-conflict point and a required edit.
- **Hardening candidate:** make the guard eager (fail at import, not deep in a production
  path), or at least covered by a test that forces the import.

**Nags carried forward (both safe-direction):**
- A Claisen route **cannot reach CLEAN even with a base declared** — the separate
  `catalyst_availability` gate whitelists no enolizing base (NaOEt/NaH/LDA absent). The
  ledger's "declare a base and the blocker lifts" is true only of *its own* blocker. A
  false-EXCLUDE (safe), but a design question.
- **Data-dark in production** — no current search target is known to generate a Claisen
  retro-step, so the ledger is exercised by unit/producer/round-trip evidence only, not a
  live end-to-end route.

## 4. Dependency PRs — Phase I-C: all green, SHA-pinned, recommend merge

| PR | bump | tip | CI | note |
|---|---|---|---|---|
| #98 | `actions/checkout` v4.4.0→v7.0.1 | `6cb6f86` | green (run `40047882685`, 7/7) | SHA-pinned, mergeable-clean |
| #102 | `actions/upload-artifact` v4.6.2→v7.0.2 | `a9b9c25` | green (run `40047882744`, 7/7) | SHA-pinned; only used on-failure with stable params |
| #136 | `actions/setup-python` v5.6.0→v7.1.0 | `0f24032` | green (run `40125037357`, 7/7) | SHA-pinned; supersedes closed #100 |

All three use only parameters stable across the v4–v7 range. **Verdict: safe to integrate.**
Merging lands on protected `main`, which is outside autonomous authority → **operator
roll-call item**, not an unilateral merge.

## 5. Proposed issue actions

- **Propose CLOSE (resolved & Verified-green on `main`):** #110, #115, #128, #129, #132.
- **Propose CLOSE WITH NOTE (resolved on `main`, with the recorded caveat):**
  #124 (guard is a proven no-op on the production grammar; covers the real lateral path only
  by Conjecture), #126 (neutralized for recognition; a forged centre is still *stored*
  advisory, not refused at construction), #131 (ABSTAIN/ERROR still collapse to one demotion).
- **Keep OPEN, scope the remainder:** #111 (alkyl-only; aryl/thio/phosphate/nitrate remain),
  #114 (recognizer side — the 1.2/1.3 target).
- **Keep OPEN:** #112, #113, #104–#109, #116–#123, #125, #130, #103 (umbrella), #107 (PR #135).

Closures are the operator's call; this document is the evidence, not the action.

## 6. What is deferred, and why (honest walls)

- **1.4 event calculus (#104/#123/#125):** `V1_5_RELEASE_PROGRAM.md` already scopes the
  *general* reaction-event calculus as a 2.0 obligation; 1.5 ships only an **opt-in finite
  lateral capability** with a termination proof. Capped-scission arity (#125) structurally
  excludes connected intramolecular-with-coproduct events; a ranking-metric swap alone cannot
  admit them.
- **2.0 representation rails (#105 charge, #106 radius-1, #108 elements, #130 config):**
  isolated experiments only until their interaction with canonicalization, rewriting, search
  identity and the release contract is proven.
- **#117 enolate / #112 SN2 share the W0.3 wall** — the context-free `ReactionCenter` makes
  SN2≡SNAr and aldol≡benzoin; a *sound* recognizer needs a narrow radius-1 environment
  predicate (the plan's pre-authorized recognizer-local carve-out), not a representation
  rewrite.
