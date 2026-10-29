# OPERATION SMARTCHEM — Mega-Round IX execution report (2026-10-28)

Autonomous engineering round off released `1.1.0`. Every item is its own branch/PR off fresh `main`; **nothing
is merged, tagged, or released** (no such authority was granted). All claims carry evidence; unverified items say so.

> ## ⚠ ERRATUM (2026-10-29, Mega-Round X)
>
> **This report's CI status was WRONG.** It implied the PRs were green, but the long full-suite jobs were still
> running when it was written, and **PR #140's full CI (run `40802775981`, tip `fcc92de`) then FAILED with four
> failures**: `test_provider_locality::test_family_enumerators_are_referenced_only_by_the_provider_layer`,
> `test_v0_7_production_algebra::test_oracle_recognises_twenty_classes_...`, and two
> `test_independent_recognition_corpus_s3` tests. Root cause: the #114 `_hydrogenation` recognizer re-derived
> through the `bond_order_edits` family enumerator from inside the oracle — a G3 provider-locality violation, and
> generator self-agreement rather than independent evidence. #141 (stacked) inherited the breakage.
>
> **Resolved in Mega-Round X.** #140 repaired with a structurally-independent witness (`c485bc8`) and #141 rebased
> onto it (`630e0ac`); **both are now CI-green on their final SHAs** (full `test (3.10/3.12)` + PySCF + wheel
> matrix 3.10–3.13 all success). The independent corpus was reconciled deliberately (hydrogenation moved from a
> coverage gap to a recognized positive; a withheld skeletal-fiction control added); live-registry count tracked
> to 22.
>
> **A second #139 item was sharpened.** The "latent DAG oracle-blindness" #139 documented is now **confirmed and
> reproduced** as a live admission bypass (a conserved fiction reaches `FITS` in DAG mode while unrecognized),
> and is **production-reachable** — see PR #144 + `docs/research/DAG_ADMISSION_BYPASS_FINDING_2026-10-29.md`. The
> #139 characterization that the containing wall was "missing process conditions" was imprecise; the real residual
> is the composability stability-data gap. The repair (DAG-ADMIT-02) is designed but staged behind a schema/golden
> sign-off.
>
> Lesson, logged: green *targeted* tests are not a green *full suite*, and a CI run still in progress is not a
> pass. Section E's status below reflects Round IX as written; this erratum supersedes its CI claims.

## A. Repository coordinates

- **Starting SHA:** `origin/main` `9e8fa5f` (SmartChem 1.1.0, PR #133 merge). **No production merge/tag/release made.**
- **Branches + PRs created (all DRAFT):**

| PR | branch | base | content |
|---|---|---|---|
| #137 | `prod/phase1-baseline-reconcile` | main | Phase I reconciliation ledger + 4 doc-drift fixes |
| #138 | `fix/search-starvation-127` | main | #127 starvation instrument + permanent recall control (verified-negative) |
| #139 | `test/latent-fiction-109` | main | #109 cross-mode fiction controls + documented DAG-oracle-blindness hole |
| #140 | `feat/hydrogenation-recognizer-114` | main | #114 hydrogenation recognizer (21st class) — adversary SURVIVED |
| #141 | `feat/oxoacid-ester-recognizer-111` | #140 (stacked) | #111 oxoacid (nitrate/phosphate) ester recognizer (22nd class) — adversary KILLED→FIXED |
| #142 | `research/coupled-vinegar-bicarbonate` | #134 (stacked) | VI-A coupled vinegar/bicarbonate 0-D equilibrium |

- **Changed production modules:** `smartchem/experiment/reaction_type_oracle.py` (2 recognizers + valence gate),
  `smartchem/bond_order_edit.py`/`experiment/step.py`/`graph_projection.py` (doc-drift, #137 only).
  **Public JSON / `semantic_digest` / verifier contracts UNCHANGED** (recognizers are not in `semantic_digest`;
  version-transition + public-contract goldens green with 22 recognizers).
- **Research modules:** `experiments/sandbox_foundation/coupled_equilibrium.py` (+ test, + doc). No `smartchem/` impact.
- **Unresolved merge conflicts:** none. #141 stacks on #140 and #142 on #134 to avoid `_RECOGNIZERS`/count-test conflicts.

## B. Issue matrix (#103–#136)

Legend: **DONE-branch** = resolved on a branch here (not on `main`); **SHIPPED** = already on released `main`.

| Issue | Status | Evidence |
|---|---|---|
| #103 Epic (coverage algebra) | PARTIAL | +2 families this round (#114, #111-oxoacid); frontier re-measured (see §F) |
| #104 W1 rank redesign | BLOCKED → 2.0 | W0.1 confirmed empirically (§E/§F): alkene synthesis = 0 routes |
| #105 per-atom charge | UNTOUCHED (2.0 rail) | — |
| #106 radius-1 predicate | UNTOUCHED (gates sound #112) | — |
| #107 catalyst/activator ledger | PARTIAL (PR #135) | reviewed & verified sound (§C); not merged |
| #108 organometallic elements | UNTOUCHED (2.0 rail) | — |
| #109 latent-fiction audit | **DONE-branch (controls)** PR #139 | `test_latent_fiction_109.py`; cross-mode controls + documented latent DAG hole |
| #110 activated acyl transfer | SHIPPED | `reaction_type_oracle.py:497` (Verified green §C) — propose CLOSE |
| #111 aryl/thio/oxoacid esters | **PARTIAL → advanced** PR #141 | alkyl-sulfonate SHIPPED; **nitrate/phosphate added this round** (22nd class) |
| #112 SN2 at sp3 | OPEN (scoped) | needs the W0.3 radius-1 predicate (SNAr collision); not landed — see §F |
| #113 metal cross-coupling | OPEN | needs W0.3 + W0.4 (catalyst gate) |
| #114 hydrogenation | **DONE-branch** PR #140 | recognizer = 21st class; generator shipped in 1.1; adversary SURVIVED |
| #115 Claisen | SHIPPED | 20th class (Verified green) — propose CLOSE |
| #116 elimination | BLOCKED (reclassified) | **NOT "CLEAN": alkene synthesis is W0.1-blocked** (verified 0 routes); §F |
| #117 enolate C–C | OPEN | W0.3 shared-centre (aldol≡benzoin); donor-EWG whitelist needed |
| #118 [2+2]/ene | UNTOUCHED | new BondRule |
| #119 C=O⇄C=N condensation | OPEN (scoped) | needs a C=O→C=N BondRule + masked-carbonyl guard |
| #120 Grignard | UNTOUCHED | W0.1 workup + W0.5 Li |
| #121 [3+2] dipolar | UNTOUCHED | W0.2 charged rail |
| #122 oxidation/FGI | UNTOUCHED | W0.1 |
| #123 lateral-hop search | OPEN | 1.4 event calculus (2.0-scoped); W0.1 |
| #124 cyclic ancestor refusal | SHIPPED (caveat) | guard present, proven no-op on current grammar — propose CLOSE-with-note |
| #125 arity/scission | UNTOUCHED (2.0) | capped-scission arity excludes intramolecular-with-coproduct |
| #126 forged ReactionCenter | SHIPPED (caveat) | neutralized for recognition; forged centre still *stored* advisory — CLOSE-with-note |
| #127 result-cap starvation | **DONE-branch (verified-negative)** PR #138 | mechanism real, harm not reproduced; bite-able control |
| #128 DA graph attribution | SHIPPED | `graph_projection.py:268` re-derives — propose CLOSE |
| #129 UNATTESTED completeness | SHIPPED | `graph_cli.py:37` exits 3 — propose CLOSE |
| #130 config-aware identity | UNTOUCHED (2.0) | — |
| #131 typed oracle diagnostics | SHIPPED (caveat) | ABSTAIN/ERROR still collapse to one demotion — CLOSE-with-note |
| #132 pericyclic determinism | SHIPPED | 14x14 matrix green — propose CLOSE |
| #98/#102/#136 dependency bumps | VERIFIED green | SHA-pinned, full matrix green; recommend operator merge |

## C. Verification matrix

- **Phase-0 baseline** (RDKit absent, released `9e8fa5f`): targeted reconciliation suite `Verified[129 passed, 3 skipped]`.
- **#114**: `ruff` clean; `Verified[pytest → 140 passed]` targeted; dedicated suite 20 passed. Adversary **dalembert: SURVIVED**
  (structure theorem + resonance-injectivity hunt, no collision). Goldens UNMOVED.
- **#111-oxoacid**: `ruff` clean; adversary **dalembert: KILLED claim (d)** (hypervalent-carbon false-VOUCH) **→ FIXED**
  (upper-bound valence gate; claims a/b/c survived); kill retained as a permanent control; `Verified[pytest → 77 passed]`
  (oxoacid + goldens + cross-poach + forged-centre). Goldens UNMOVED.
- **#127**: `Verified[pytest → 1 passed]`; instrument green; harm NOT reproduced across 14 targets at depths 1–3.
- **#109**: `Verified[pytest → 1 passed, 18.86s]`; cross-mode controls; independent evil-morty probe corroborated no live false-VOUCH.
- **VI-A coupled model**: `Verified[pytest → 16 passed]`; full sandbox suite `Verified[577 passed]`; two-route agreement ~machine-zero;
  limiting cases reduce EXACTLY to the PHREEQC-benchmarked parents (|ΔpH| = 0.00).
- **Mutation/adversary**: #114 SURVIVED dalembert; #111 KILLED→FIXED by dalembert; #109 corroborated by evil-morty.
- **Hosted CI (final SHAs, as of this report):** every COMPLETED check SUCCESS on all six PRs; the ~1h `test (3.10/3.12)` +
  PySCF jobs are IN_PROGRESS/QUEUED. **No failures. No PR is declared fully green until those jobs finish** (do not read
  in-progress as passing).
- **Public-contract / semantic-digest differential:** zero. Two recognizers added (20→22) with the version-transition and
  public-contract goldens unmoved — recognizers are not in `semantic_digest`; a MINOR coverage add, not a semantic re-freeze.

## D. Release readiness

| version | status | why |
|---|---|---|
| 1.2 | **CANDIDATE (partial)** | #127 (verified-negative), #109 (controls), #114 recognition landed on branches; **#112 SN2 OPEN** (needs W0.3 radius-1 predicate). Not consolidated/merged. |
| 1.3 | **CANDIDATE** | the plan's ≥2 new families met: #114 hydrogenation + #111 oxoacid ester, each independently adversary-gated. #116/#117/#119 scoped with documented blockers (§F). |
| 1.4 | **NOT READY** | W0.1 confirmed as the real obstruction; the opt-in finite lateral/event-search capability + its termination proof are 2.0-scoped and not built this round. |
| 1.5 | **NOT READY** | consolidation gate not run; depends on 1.2–1.4 merging + the full acceptance matrix + full-SHA CI. |

**No version was merged, tagged, or released.** All work is reviewable DRAFT PRs.

## E. Physicalization status (VI-A)

- **Implemented:** `VinegarBicarbonateSystem` / `solve` — a coupled CLOSED 0-D equilibrium over total acetate, total
  inorganic carbon, sodium, with a shared H⁺/charge balance (`[Na⁺]+[H⁺]=[OH⁻]+[Ac⁻]+[HCO3⁻]+2[CO3²⁻]`), Davies activity
  (monovalent + divalent γ), constants/vocabulary imported from both parent solvers.
- **Supported domain:** closed liquid, I ≤ 0.5 M (Davies), T = 298.15 K. Open (fixed P_CO2) / sealed (headspace) modes:
  documented next step (carbonate parent already has the machinery).
- **Conservation / numerical residuals:** carbon, acetate, charge all close to machine zero (≤ ~1e-17); two independent
  routes (brentq + polynomial) agree to ~1e-20·h.
- **Independent-solver agreement:** limiting cases reduce EXACTLY to the already-PHREEQC-benchmarked parents
  (vinegar-only == acetate solver, bicarbonate-only == carbonate closed solver; |ΔpH| = 0.00) — those end-states inherit
  the parents' PHREEQC agreement for free.
- **External experimental validation:** **UNKNOWN.** No measured mixed-system pH compared; a future mixed-PHREEQC
  comparison would be common-mode (shared constant provenance), not independent.
- **What prevents a credible DYNAMIC vinegar/bicarbonate demo:** this is a 0-D EQUILIBRIUM solver — **no bubbles**: no
  supersaturation/nucleation/gas-liquid-transfer model (a 0-D solver is not a bubbly-fluid simulator). Dissolved-CO₂ is an
  output; any fizzing visual would be illustrative only. Chamber coupling (VI-B) and a mixed-PHREEQC benchmark are the next steps.

## F. Next frontier — the load-bearing blockers (measured, not assumed)

1. **W0.1 / #104 (search obstruction):** CONFIRMED empirically — alkene synthesis by elimination/dehydration is
   rank-INCREASING in retro (precursor bigger than the alkene), so it is unreachable via default W1 descent (`2-butene`
   from an alcohol pool = **0 routes**). #116's audit label "CLEAN" was about the BondRule *shape*, not reachability. The
   fix is the 1.4 opt-in finite lateral/event-search with a termination proof — a 2.0-scoped obligation. **Next probe:** a
   bounded lateral-hop search over the existing sigmatropic consumers with a well-founded `(state, depth, hops)` measure.
2. **The cheap-recognizer tier is exhausted.** The remaining coverage needs infrastructure: #112 SN2 / #117 aldol need the
   W0.3 radius-1 environment predicate (SNAr/benzoin collisions); #119 imine needs a C=O→C=N BondRule + masked-carbonyl
   guard; #121 dipolar needs the W0.2 charged rail. Each is its own soundness gate. **Prefer two sound families to five.**
3. **#109 latent DAG-oracle-blindness (contained, not closed):** the convergent-DAG path never consults the oracle; a
   fiction is contained today only by the unrelated undeclared-conditions wall. **Next falsifying probe:** inject a declared
   condition into a generated DAG step; if `fit_status` reaches FITS with the oracle unconsulted, that is a true false-VOUCH.
   The real fix is a DAG-mode readiness/oracle surface.
4. **Activator fingerprint-guard cross-dependency:** once PR #135 (activator ledger) and the new recognizers both land, the
   lazy registry fingerprint guard (`_REVIEWED_CLASS_COUNT`, `_REVIEWED_REGISTRY_DIGEST`) must be bumped and re-reviewed in
   the same change (it currently crashes a production path at runtime on mismatch — a hardening candidate: make it eager).

**Minimum-deliverable scorecard:** all feasible short-term soundness goals addressed (#127, #109, #114, activator review,
dependency bumps); **two new independently adversary-gated 1.3 families** (#114, #111-oxoacid); a **scientifically honest
coupled acid/carbonate 0-D model** with limiting-case validation; **substantial 1.4 is a documented, measured blocker**
(W0.1), not a speculative attempt. The one explicit miss vs the plan's letter: #112 SN2 and the 1.4 opt-in lateral search
were scoped-with-blockers rather than built, because the sound versions require infrastructure (W0.3 / the event calculus).
