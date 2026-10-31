# SmartChem 1.5 consolidation — the 20→24 coverage integration (evidence dossier)

**Date:** 2026-10-30 · **Branch:** `integration/v1.5-candidate` (off `origin/main` `9e8fa5f` = tag `v1.1.0`) ·
**Declared version:** `1.5.0` (MINOR) · **Status: release candidate — NOT merged, NOT tagged, NOT published.**

This is the Phase-V consolidation record for the post-1.1 coverage campaign: it reconciles the four divergent
1.5-candidate forks into one coherent candidate, discharges the activator-ledger re-review forced by the registry
growth, declares the version boundary, and records the §4 acceptance-gate evidence. The exhaustive per-fork
findings remain in the committed `docs/research/` records cited below; this dossier is the *differential* and the
gate ledger, not a restatement of them.

## 1. The input state — four forks, all off released `9e8fa5f`, none previously integrated

| PR | branch | tip | adds | own count |
|---|---|---|---|---|
| #145 (DRAFT) | `integration/mega-round-xi` | `93197e5` | #114 hydrogenation + #111 oxoacid ester; activator ledger (#135/#107); DAG-ADMIT-02 (#144) | 22 |
| #146 (OPEN) | `feat/sn2-recognizer-112` | `ade0f28` | #112 SN2-at-sp3 + #106 `radius1_environment.py` | 21 |
| #147 (OPEN) | `feat/reaction-algebra-1.3` | `be5f8a1` (**stacked on #146**) | #119 imine condensation (opt-in C=N generator) | 22 |
| #148 (OPEN) | `feat/bounded-event-search-123` | `466e0e3` | #123 bounded typed-event search (capability, **no recognizer**) | 20 |

All four share merge-base **exactly** `9e8fa5f` (verified: `git merge-base <tip> 9e8fa5f == 9e8fa5f` for each).
The four new recognizer function tags — `_hydrogenation`, `_oxoacid_ester`, `_sn2_substitution`,
`_imine_condensation` — are **distinct**, so the union is collision-free: **20 base + 4 = 24 classes.**

## 2. The integration — merge topology

Cut `integration/v1.5-candidate` off the **verified** release base (`origin/main` `9e8fa5f`; local `main` is a
stale pre-release ancestor `99fce34` and was **not** used). Because #147 is stacked on #146, merging #147 directly
carries #146's SN2 commits as ancestors — one union resolution for SN2+imine instead of two.

| commit | step |
|---|---|
| `25a5665` | merge #145 (fast-forwardable descendant → explicit `--no-ff`; zero conflicts) |
| `663d5e4` | merge #147 (carries #146 `ade0f28`); resolved the recognizer-tuple + count-test conflict surface to the 24-union |
| `40d1e7f` | activator-ledger re-review at the 20→24 tripwire + registry-digest reseal |
| `d2d9965` | merge #148 (clean auto-merge; disjoint from the recognizer surface) |
| `98e04b2` | version boundary `1.1.0 → 1.5.0`; regenerate version-bound CLI-JSON goldens; reconcile the numbered-derivation docstring |

**Conflict surface (as predicted, and only this):** the `_RECOGNIZERS` tuple + the recognizer-count assertions in
`test_transform_algebra_expansion.py`, `test_claisen_condensation_115.py`, `test_sulfonate_ester_transfer_111.py`,
`test_v0_7_production_algebra.py`. Resolved to the 24-union. Two **non-conflicting** stale count pins (each fork
added its own count-named test) were caught by a full sweep and fixed: `test_imine_condensation_119.py` and
`test_sn2_recognizer_112.py` (22 → 24).

## 3. The activator-ledger re-review (the 20→24 tripwire)

The ledger (`smartchem/experiment/activator_ledger.py`) carries an **import-time guard** that fails LOUD when the
recognizer registry changes since its base-rate scope was last reviewed. The growth 22→24 fired it:

```
reviewed 22 classes @ 2a3bc34443129ff2; now 24 @ 0dfb95140ad927ef. RE-REVIEW REQUIRED_ACTIVATORS: ...
```

Re-reviewed the two new-since-seal classes against the guard's question ("does any new class require a
stoichiometric activator / catalyst that would otherwise read as kitchen-runnable with nothing declared?"). Both
given **NO** `REQUIRED_ACTIVATORS` entry, reasoning recorded in the ledger:

- **SN2 (#112) → CONDITIONAL requirement (revised after adversarial re-review).** An initial "no entry" was
  **killed** by the consolidated hostile sweep (evil-morty): the recognizer vouches both a salt nucleophile
  (`R-Nu-M`) *and* a NEUTRAL protonated one (`R-Nu-H`, coproduct H-X), and a neutral **oxygen** nucleophile (an
  alcohol `R-O-H`) is not a competent SN2 nucleophile — `EtOH + EtBr` bare gives no ether; the Williamson synthesis
  forms the alkoxide *in situ* with a stoichiometric base. That cleared as kitchen-runnable = a capability
  over-claim (a cross-fork interaction: SN2 #112 × the ledger #107, new at the merge). **Fixed** (feasibility layer
  only; recognition/type-validity untouched): `_conditional_required_roles` demotes a neutral-oxygen-nucleophile
  SN2 with no declared base to `REAL_BUT_HARD`, recoverable by declaring the base — keyed on the step's nucleophile,
  not a blanket class entry. Conscious boundaries (adversary-set): a metal-salt oxy-nucleophile (already
  deprotonated), a neutral **amine** (competent base-free), and a neutral **thiol** (reacts base-free — demoting
  would false-EXCLUDE) get no requirement. A re-attack of the fix confirmed no over-claim remains, no recognition
  regression, and no false-EXCLUDE of the salt/amine/thiol cases.
  - *pKa-regime-aware base strength (refinement implemented, not deferred).* The required base STRENGTH now depends
    on the oxygen's pKa, read from the **hydroxyl carbon's own radius-1 environment** by `sn2_oxygen_base_regime`:
    an **alcohol** (`O-H` on an sp3 carbon, pKa ~16) needs a **strong** base → `DEPROTONATING_BASE` (cleared by the
    alkoxide/hydride/amide set only); an **acidic** oxygen — a **carboxylic acid** (`C=O`, pKa ~5) or a
    **phenol/enol** (`C=C`, pKa ~10) — needs only a **mild** base → the new `ACIDIC_PROTON_BASE` (cleared by
    carbonate/hydroxide/strong-amine, or any strong base a fortiori). This closes the former safe under-claim
    (carboxylate/phenoxide O-alkylation with K₂CO₃/NaOH/Et₃N is the textbook reagent and now clears) while the pKa
    **asymmetry is load-bearing**: mild-base names are absent from the strong (`_ENOLIZING_BASE_NAMES`) set, so a
    mild base can never clear the alcohol case — an alcohol is never mis-cleared (the unsafe direction is closed by
    construction, since an sp3 carbon carries no order≥2 bond).
  - *Adversarial re-attack of the refinement (evil-morty).* The headline unsafe-direction claim held under attack
    (no sp3 alcohol, however decorated — benzylic / allylic / β-carbonyl / fluorinated — ever reads `mild`;
    nucleophile-identification cannot be gamed; no role leak into the Claisen enolizing or the alcohol strong
    requirement). It proved **one** real over-claim: a hydroxyl on a **`C=N`** carbon (an amide's **iminol**
    tautomer, an **isourea/amidine** O-form) is *amidate*-level (pKa ~17–22, O-imidate alkylation needs a strong
    base / Meerwein salt, not carbonate), yet the first cut's blanket "any sp2 ⇒ mild" cleared it with K₂CO₃.
    **Fixed**: `mild` now fires only when the hydroxyl carbon's order≥2 partner is **C or O** (phenol/enol or
    carboxyl); a **`C=N`** partner is excluded → `strong` (fail-closed). Regression locked.
  - *Residual conservative boundaries (all safe direction, documented).* A poly-ol (ambiguous nucleophile), a
    halogen-bearing nucleophile (the alkyl-halide reactant cannot be told apart), and a `C=N` hydroxyl all
    fail-closed to `strong`; **bicarbonate** and weak amines (pyridine/DABCO) are omitted from the mild set (too
    weak for a phenol — carboxylate-only clearing with bicarbonate is lost). Each is a capability *under*-claim
    (recoverable with a strong base), never a false-VOUCH. The whole gate remains latent on the default route
    search (SN2 has no default generator), so neither direction is reachable there.
- **imine (#119) → no entry.** A dehydrative carbonyl+amine condensation (coproduct water). A Brønsted acid
  *accelerates* dehydration but is not a feasibility gate (the reaction reaches equilibrium uncatalysed, driven by
  water removal) — the same self-acidic condensation population as the acyl / ether / oxoacid classes that get no
  entry. A `BRONSTED_ACID` requirement here is the banned base-rate trap.

The #145 decisions (hydrogenation → `TRANSITION_METAL_CATALYST`; oxoacid ester → none) stand. `REQUIRED_ACTIVATORS`
is therefore unchanged (Claisen condensation + hydrogenation); only the snapshot constants moved:
`_REVIEWED_CLASS_COUNT = 24`, `_REVIEWED_REGISTRY_DIGEST = "0dfb95140ad927ef"` (recomputed independently from the
24 sorted display names, not trusted from the error message). The feasibility-negatives fold into the hostile-control
sweep before the gate.

## 4. Fingerprint discipline — two distinct identities, one moves, one must not

- **Recognizer registry digest** (the ledger's `_REVIEWED_REGISTRY_DIGEST`): a function of the display-name set, so
  it **moves** with coverage. Resealed `2a3bc34443129ff2` (22) → `0dfb95140ad927ef` (24). This is the only
  "fingerprint" the campaign ever re-sealed.
- **Version-independent payload golden** (`experiments/v1_0_version_transition.py`): the compiled-output fingerprint
  over the standing corpus. By the demoter invariant — *a recognizer changes readiness, never `semantic_digest`* —
  it **must not move**. Verified: `--check-golden` → **NO DRIFT**. The golden was **not** re-frozen.

## 5. The version boundary — `1.1.0 → 1.5.0`

`smartchem.__version__` bumped to `1.5.0`. Per the compatibility law a package bump moves **exactly** the
tool-version-bound fields; the regenerated `tests/fixtures/cli_json/*.json` diff is precisely `tool_version` +
`result_digest` across 5 fixtures and **nothing semantic** (audited line-by-line). No stable wire schema id,
verdict word, route digest or readiness/capability semantic moved.

## 6. §4 acceptance-gate ledger (status at `98e04b2` + docs)

| # | gate | status |
|---|---|---|
| 1 | No demonstrated false-VOUCH on the standing corpus + every new rule's hostile controls | **MET** — per-fork adversarial corpora retained; the consolidated hostile sweep found ONE cross-fork capability over-claim (neutral-alcohol SN2 reading kitchen-runnable), **fixed** and re-attack-confirmed. The prior safe-direction under-claim (acidic-O mild-base recovery) is now **implemented** as a pKa-regime-aware base-strength gate (§3); a second evil-morty re-attack held the unsafe direction and found+**fixed** one further over-claim (a `C=N` iminol hydroxyl reading mild — now excluded → strong). Remaining residuals are all SAFE-direction under-claims (bicarbonate/poly-ol/halo-nucleophile/`C=N` → conservative strong, §3), documented. No false-VOUCH remains. |
| 2 | Version-boundary discipline: every semantic move since 1.0 classified; version-independent golden green; no undeclared promotion | **MET** — §4/§5 above; golden NO DRIFT; cli-json diff version-bound-only |
| 3 | Workbench threat model (UNATTESTED≠COMPLETE; names from oracle not caller; bounded renderer; runs without RDKit/PySCF) | inherited from 1.1; unchanged by this integration |
| 4 | Fail-closed everywhere (unread demand→UNKNOWN; finer identity refuses, never wrong-isomer) | inherited; the ledger + oracle are pure demoters by construction |
| 5 | Full OOM-safe suite green AND clean wheel-install Py 3.10–3.13 on the FINAL SHA, no cancelled/partial counts | **in progress** — OOM suite + wheel matrix + hosted CI per-job on the final SHA |

**Boundaries.** No merge into protected `main`, no tag, no publish without separate explicit authorization. The
2.0 track (PHREEQC physicalization, PR #134; per-atom formal charge #105; general reaction-event calculus /
type-3 INTRAMOLECULAR_COPRODUCT) remains deferred.

## 7. Provenance of the per-fork evidence (unchanged, committed)

- #145: `docs/research/MEGA_ROUND_IX_EXECUTION_REPORT_2026-10-28.md`, `DAG_ADMISSION_BYPASS_FINDING_2026-10-29.md`,
  `ACTIVATOR_LEDGER_107_2026-10-24.md`, `BASELINE_RECONCILIATION_2026-10-28.md`.
- #147: `docs/research/REACTION_ALGEBRA_1_3_P3_FINDINGS_2026-10-30.md`.
- #148: `docs/research/BOUNDED_EVENT_SEARCH_1_4_P4_FINDINGS_2026-10-30.md`.
