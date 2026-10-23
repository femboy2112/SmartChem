# Physicalization Round V -- Operation Chemical Reality (2026-10-22)

Branch `feat/chemical-graph-projections` (PR #101, draft). Baseline for this round: `1d67401` (end of
Round IV). Round V commits land on top; `main` = `99fce34` (`v1.0.0`) is UNTOUCHED. **No merge, tag,
release, publish, force-push, or default-algebra change was performed.** Production `smartchem/` changed
in ZERO files this round (the only production-tree edit is a comment correction in a `poor_man_*` probe,
hash-neutral); everything else is `experiments/sandbox_foundation/` + `docs/`.

Theme: **model validity is an executable precondition, not metadata.** This round repaired the first
source-backed chemistry (aqueous pH), made source verification a verifier-OWNED procedure that reaches
into execution, refuted a mis-diagnosed "nondeterminism," benchmarked the aqueous model against an
independent instrument, turned a boundary into a derived physical interface law, and gave the
simulator -> LibGibson frame an un-forgeable scientific-status receipt.

## 1. Commit stack (Round V, on 1d67401; repo identity, bare messages, no trailers)

| SHA | wave | what |
|---|---|---|
| `bcb2868` | C2 | reconcile `V1_5_RELEASE_PROGRAM` to the 20-class branch state |
| `8d11ae8` | B | verifier-owned admission receipts + parameter/source binding + admission into execution |
| `22ef517` | A | activity-based pH + temperature-domain enforcement + convergence admission gate + honest ledger |
| `e3681b2` | C1 | record the Round V refutation of the section-8 determinism cause (doc) |
| `74cc1be` | E | passive-interface dissipation law (J = -L.grad mu, log-mean mobility) + valve/membrane apparatus |
| `953f012` | D | commit the acetate/water independent PHREEQC benchmark |
| `4168bcb` | B-fu | enforce admission on the diagnostic/analysis rate paths (close the reaction_cell-only gate) |
| `3d2e089` | C1 | correct the poor-man probe comment to the determinism refutation (code) |
| `f25dc78` | A-fu | honest Davies molal/molar labelling + units allowlist + benchmark-agreement domain |
| `1b227bf` | F | ModelRunReceipt + 4-way frame quantity typing + neutral-tracer membrane demo |
| `6d5a823` | F-fu | bind frame trust/digests to the receipt + typed refusal + un-forgeable receipt stamp (evil-morty F-1..F-4) |
| `60b51a8` | E-fu | NaN-safe passivity certificate (signed -inf limit) + charge as a transport-time invariant (dalembert KILL 1/2) |

Plus branch `pr101/production-1-1-rc` (C3, local): the 20-class 1.1 release candidate =
`main..34e1891` + two clean-replayed #115 commits.

## 2. Wave A -- the aqueous model made honest (P0)

The Round IV model reported `pH = -log10([H+])` even in the Davies activity model, reused 25 C constants
outside the sourced domain in ideal mode, and could average two disagreeing solver roots into an
unqualified success. All three reproduced RED first (I re-reproduced the headline on the live module:
γ=0.82149, 4.58662 -> **4.67201**; ideal@350 K admitted).

- **A1 activity pH** -- `SpeciationResult` now carries `pH_activity = -log10(gamma_H.[H+]/C_REF)` AND
  `pH_concentration`; in Davies mode the primary `pH` IS the activity value, in ideal mode they coincide.
  `C_REF` declared EXACT at 1.0 mol/L; the molarity/standard-state approximation is stated, not dressed as
  exact thermodynamic authority.
- **A2 temperature domain in ALL modes** -- `SOURCE_T_K`/`SOURCE_T_TOL_K` enforced for ideal AND davies;
  out-of-domain raises `OutOfSourceDomainError` (`OUT_OF_SOURCE_DOMAIN`).
- **A3 convergence admission gate (fails CLOSED)** -- both routes must converge AND agree within
  `AGREEMENT_RTOL=1e-7`, charge + acetate balance close, species >= 0, Davies fixed point converged,
  ionic strength within `DAVIES_I_MAX=0.5`. Tolerances probed from live numerics, NOT widened to pass;
  the two independent algorithms preserved as the cross-check. A solver failure returns
  `NUMERICALLY_UNVERIFIED`, never a number.
- **A4 uncertainty controls** split to single-cause (zero error bar on a MEASURED constant banned even with
  a source; empty-source / UNKNOWN-value / wrong-T / mismatched-units / exact-by-definition each isolated).
- **A5 verdict ledger** -- `VERDICTS` = {SOLVED_WITHIN_IDEAL_MODEL, SOLVED_WITHIN_ADMITTED_ACTIVITY_MODEL,
  NUMERICALLY_UNVERIFIED, OUT_OF_SOURCE_DOMAIN, EXTERNAL_VALIDATION_UNAVAILABLE}. Textbook anchors relabelled
  as equation/implementation VERIFICATION, not independent validation.

**Follow-up (`f25dc78`, from the adversary + benchmark):** the module header now honestly DISCLOSES the
molal-A / molar-I Davies approximation (it had claimed to have removed it); the `"molar" in units` substring
guard is replaced by an explicit molar allowlist + molal blocklist; a `caveats` field +
`BENCHMARK_AGREEMENT_I_MAX=0.1` (strictly inside `DAVIES_I_MAX=0.5`) flags any result above the demonstrated
independent-agreement domain with the NaAc ion-pair-omission caveat -- still SOLVES, no fabricated ion pair.
Verified: 39 sandbox tests.

## 3. Wave B -- source verification made operational (P0)

Round IV's admission types ACCEPTED a VERIFIED-looking receipt assembled from caller statements (an
"Imaginary Handbook" minted `scientific_claim=True`). Now:

- **B1 trusted authority** -- `SourceRecord` / public `AdmissionReceipt(...)` are inert declarations; a new
  `SourceStore` is the verifier (opens `<id>@<ver>.json`, recomputes the content digest, checks the law,
  mints a `SourceBinding` with no public constructor). `AdmissionReceipt.binding` is `init=False`, set only
  by the store. `DEFAULT_POLICY` trusts only `verified_sources/`, which does NOT exist -- so by default
  nothing is a scientific claim (fail-closed, confirmed).
- **B2 parameter/source binding** -- a params digest refuses a citation-kept rate swap; `to_executable`
  stamps `structure_bound` only on a Molecule-identity match; a revised rate moves both model and evidence
  identity, a re-edition with the same numbers moves only evidence (orthogonal).
- **B3 admission into execution** -- an `Applicability` rides WITH the `Mechanism`; `reaction_cell` checks T
  every step; out-of-window / over-cap / stale-or-untrusted / windowed-without-T all refuse
  (`AdmissionDomainError`).

**Follow-up (`4168bcb`, HIGH break from evil-morty, re-confirmed by principal):** admission was enforced on
`reaction_cell` ONLY -- `rate_vector` / `source_density` / the Lyapunov reaction diagnostics served
out-of-window and RETRACTED-source numbers as `SOURCE_VERIFIED`. Fixed with one
`Mechanism.require_admitted` gate those paths call (plain mechanisms unchanged; `reaction_cell` not
weakened; the diffusion path and E's reconciliation untouched). `mesh.coupled_rhs` now fail-closes on an
admitted windowed mechanism (safe; documented). Verified: 161 gate + cross-wave tests.

## 4. Wave C -- determinism + release discipline (P0)

- **C1 -- the determinism cause is REFUTED (not repaired, because there was no bug).** A read-only forensic
  instrument found `total_frontier_routes` STABLE at 29 across ~25 sweeps (fresh/warm, PYTHONHASHSEED
  0/1/2/3/unset, permuted order, caches cleared); three counterfactual interventions proved `_REDERIVE_CACHE`
  CANNOT move the count; an atom-order key fuzz (1062 relabelings) found no missing dependency. The differing
  hashes the Round IV note saw were a DETERMINISTIC code-state effect across mid-round commits (`cf3d942` ->
  `150d30cd` via the p56 sub-hash; HEAD `6d783d59` after `35928b6`), not run-to-run flakiness (Conjectured:
  no values were logged originally). The record + the live probe comment are corrected. Residual latent risk:
  a silent `except Exception: continue` in the probe could shrink the count unseen under real memory pressure
  -- attribution counters + an order-invariant digest anchor are a recorded follow-up (NOT a cache-key change
  or count deletion -- both would be motion without cause).
- **C2 -- roadmap reconciled.** `V1_5_RELEASE_PROGRAM` now states 20 classes / HEAD `1d67401` / #115 landed via
  `cf3d942` (moved from "1.2 future" to "landed early on 1.1"); `main` stays 1.0; close-on-merge-not-claim
  preserved.
- **C3 -- 1.1 release candidate prepared + proven.** Branch `pr101/production-1-1-rc` = the 39-commit
  production prefix (`main..34e1891`) + two cleanly-replayed #115 commits (`cf3d942` recognizer + `35928b6`
  E3 anchor reconcile). Zero-conflict cherry-picks, recognizer count = 20, version-transition golden UNMOVED,
  72 production #115 gates green on the candidate tip. **Recommended: Option B (20-class 1.1).** The sandbox
  2.0 work stays a separate, independently-droppable unit. The exact-SHA CI needs a push -- AUTHORIZATION-GATED.
- **C4 (#107 activator ledger)** -- deferred this round (scope); recorded as the next production-chemistry gap.

## 5. Wave D -- first real chemistry, independently benchmarked (P1)

An isolated-venv PHREEQC cross-check (`phreeqpython`, USGS `minteq.v4` + `llnl` databases -- different
constants and a NaAc ion pair the model lacks) of the corrected `AcetateWaterSystem.solve`. Committed under
`experiments/sandbox_foundation/benchmarks/acetate_phreeqc/` (pre-registration, harness, 12 `.pqi` inputs,
comparison tables; DBs excluded, provenance by sha256 + URL).

- **VERIFICATION-grade:** reproduces PHREEQC acetate speciation to **|dpH| <= 0.015 for I <= 0.10 M** vs both
  databases (code C3 buffer pH 4.6720 = the module reference 4.67201).
- **DIVERGE** to |dpH| ~ 0.052 at I ~ 0.45 -- caused by the model's OMISSION of the NaAc(aq) ion pair, NOT
  Davies invalidity. This is why the admitted domain (`DAVIES_I_MAX=0.5`) is wider than the demonstrated
  independent-agreement domain -- fixed in A-fu with the `caveats` field.
- **Independence is thin** (shared Ka lineage; minteq's Davies is the same functional form); only llnl is a
  different activity model. **External validation against a measured datum: UNKNOWN** (IUPAC primary tables
  Cloudflare-blocked) -- no value fabricated.
- **Stopping rule honored:** no carbonate/CO2 chemistry on the back of this.

## 6. Wave E -- the boundary as a derived physical law (P1)

A wall / valve / membrane is now a PHYSICAL INTERFACE LAW, derived from `B_space`, not an equipment event.

- **Theorem (DERIVED, not asserted):** for a face oriented tail->head, `Delta(mu)_f = R T ln(c_head/c_tail)`
  (the species-uniform `mu^0` and `c_ref` cancel because each `B_space` column sums to zero). The existing
  Fick flux `J = g_f(c_tail - c_head)` is `J = -L_f.Delta(mu)_f` with `L_f = g_f.c_lm/(R T)`,
  `c_lm = (c_tail - c_head)/(ln c_tail - ln c_head)` the LOG-MEAN concentration; `c_lm > 0` so `L_f >= 0`
  (PSD) and the per-face witness `Delta(mu)_f.J_f = -L_f (Delta(mu)_f)^2 <= 0`. Limiting cases derived:
  equal c -> witness 0, L finite (l'Hopital); c -> 0 -> signed -inf ideal-dilute limit, NOT NaN (the naive
  factored form made 0*inf=NaN and a c->0 test caught it RED). Per-face <-> global reconciliation PROVEN:
  `sum_f Delta(mu).J = R T . dPhi/dt|diff`, checked against `lyapunov.diffusion_dissipation_rate` to 1e-13.
- **Apparatus** (`interface.py`): Mesh + conductance + reversible valve; `two_chamber_valve`,
  `three_chamber_membrane`; all boundary physics in the conductance/valve (one law). Conservation, impermeable
  = no flux, downhill transport, valve-creates-no-matter, independent closed compartments -- all pinned.
- **E3 charged species: DEFERRED, fail-closed.** Independent Fick fluxes do not enforce LOCAL
  electroneutrality; the correct law is Nernst-Planck with an electrical-potential closure the mesh has no DOF
  for. A charged tracer raises `ChargedTransportNotAdmitted`; the prototype is neutral-only. No ion dynamics
  fabricated.
- **E follow-up (`60b51a8`, dalembert):** the passivity certificate is now NaN-safe -- the empty-cell underflow
  yields a signed -inf (dissipation, never injection; dmu and J provably carry opposite signs) and
  `assert_passive` refuses a NaN witness instead of failing open -- and `charge==0` is enforced as a
  TRANSPORT-TIME invariant (a post-construction charge flip or a duck-typed species is refused at every
  `transport`), not only at construction.

## 7. Wave F -- a trustworthy simulator -> LibGibson contract (P1)

- **ModelRunReceipt** on the snapshot: `admitted` is DERIVED (only `from_executable` stamps it; the public
  constructor cannot), `numerically_verified` is computed (CONVERGED + every tolerance has a finite residual
  within it; NaN refused at construction), `scientific_measurement = admitted AND numerically_verified`. Model
  identity + numerics feed `model_digest`; the admission side feeds `evidence_digest` (orthogonal).
- **4-way quantity typing** -- CANONICAL | MODEL_DERIVED | UNSUPPORTED | ILLUSTRATION; only the first two are
  measurements; a masked cell is explicit null (never 0); `FrameContractError` on any violation.
- **Demo** -- a neutral tracer crossing a configurable 3-chamber membrane (Wave E), 12 ticks, rendered through
  a stateless `HeadlessPresenter` that imports NO LibGibson. Receipt reads UNADMITTED(SYNTHETIC) + "NOT A
  VALIDATED MEASUREMENT" (conductances are caller-declared).
- **Invariants** -- presentation-frequency independence (0/1/7/irregular calls -> byte-identical trajectory)
  and no write-back (#15: a hostile consumer handed snapshot + frame achieves zero mutations; `verify_integrity`
  re-derives both digests). Honest boundary: in-process isolation is NOT cryptographic; the real guarantee is
  the JSON/text process boundary.
- **F follow-up (`6d5a823`, evil-morty):** the frame no longer trusts its own `trust` block or digests --
  `validate_frame` RECOMPUTES the verdict and both digests from the receipt and flags any mismatch (a forged
  trust block is caught; the presenter banners from the receipt-derived verdict), a malformed frame is a typed
  `FrameContractError` not a `KeyError`, and the receipt stamp is un-forgeable via a private `_mint` (the public
  stamp kwargs + the sentinel are gone). Residual: the digests are UNKEYED -- a full re-forger who rewrites the
  receipt and recomputes both digests needs a MAC/signature (deferred, documented).

## 8. Adversarial pass (independent, red-before-green on the SHIPPED code)

- **evil-morty on A + B** -- found ONE HIGH break (the diagnostic-path admission bypass, Wave B-fu above),
  FIXED + regressed; confirmed the forgery surface, convergence gate, temperature guard, and mesh-fail-closed
  as sound; two LOW/MED claim-honesty defects in the aqueous units/Davies labelling, FIXED in A-fu.
- **dalembert on E** -- TWO Verified KILLs, both excised red-first (`60b51a8`): KILL 1 (HIGH) `assert_passive`
  failed OPEN on a NaN witness (empty-cell flux underflow `(+inf)*(-0.0)`), now NaN-aware with
  `face_dissipation` pinning the genuine empty-cell limit to signed -inf; KILL 2 (MED-HIGH) the charged-species
  guard was construction-only, now a transport-time invariant (`object.__setattr__` charge flip + duck-typed
  species both refused). Survivals SIGNED: witness <= 0 in the positive regime (5e5 samples), conservation,
  the per-face<->global reconciliation (20000 configs, worst 5.5e-16 vs the 1e-13 claim), the T_K refusals.
  Both kills principal-re-confirmed CLOSED (dissipation -inf not NaN + transport refuses; charged transport
  refuses).
- **evil-morty on F** -- ONE HIGH + three lower, all fixed red-first (`6d5a823`): F-1 (HIGH) the frame `trust`
  block + carried digests were unmoored from the receipt (a forged trust block printed as VALIDATED), now
  `validate_frame` RECOMPUTES the verdict + digests from the receipt and flags any mismatch; F-2 a raw KeyError
  made a typed refusal; F-3 the receipt stamp made un-forgeable via a private `_mint` (sentinel deleted); F-4
  the tolerance guard made symmetric + the NaN docstring corrected. Earned parts SIGNED: no-write-back (#15),
  frequency independence, read-only views, digest orthogonality, verify_integrity. Honest residual: the frame
  digests are UNKEYED -- a full re-forger (rewrite receipt + recompute both digests) needs a MAC/signature,
  out of scope (documented in validate_frame).

**The adversarial pass found FOUR real breaks (BREAK 1, F-1, KILL 1, KILL 2), every one the same shape -- a
guarantee enforced on the primary path but leaking at a side door -- and all were fixed red-first with the
adversary's own repro frozen as a regression. That is the round's own admission lesson turned on itself.**

## 9. The three contracts

- **Conservation:** matter and charge are not fabricated by internal transitions -- `B_space` columns sum to
  zero (transport), `im(N)` backtracking (reaction, Round IV), charged transport refused until its law exists.
- **Dissipation:** a genuinely passive system cannot secretly create free energy -- the per-face witness
  `Delta(mu).J <= 0`, reconciled to the global `dPhi/dt`.
- **Admission:** no physical prediction is more certain than the evidence + model assumptions -- verifier-owned
  receipts, admission enforced on EVERY prediction path (not just the time-stepper), the receipt carried into
  the presentation frame, benchmark-agreement vs admitted-domain distinguished.

## 10. Red-team checklist (15 items)

1. Davies pH uses activity -- PASS (A1). 2. ideal mode can't bypass temp bounds -- PASS (A2). 3. two solvers
can't disagree + succeed -- PASS (A3; adversary swept 50, 0 spurious). 4. Davies non-convergence can't verify
-- PASS (A3). 5. bad-units/mismatched constants can't acquire authority -- PASS (A4 + A-fu allowlist).
6. fabricated receipt can't establish science -- PASS (B1; falsifier). 7. domain enforceable after conversion,
INCLUDING diagnostic + mesh paths -- PASS after B-fu (was the HIGH break). 8. source/model revision invalidates
obsolete receipts -- PASS (B2). 9. cache/ordering can't change consumer-visible chemistry -- PASS (C1: count is
deterministic; cache can't move it). 10. #115 Claisen negative corpus unvouched + 20-class versioned -- PASS
(C2/C3; 72 gates green). 11. no source-free/out-of-domain aqueous prediction -- PASS (A2/A3/A-fu). 12. passive
interfaces dissipate, don't inject -- PASS (E + `60b51a8`; dalembert KILL 1 fixed: assert_passive is NaN-aware,
witness never injects). 13. closed compartments conserve independently -- PASS (E; dalembert survival). 14.
charged transport never claims electroneutrality without its law -- PASS (E3 defers + `60b51a8`; dalembert
KILL 2 fixed: charge is a transport-time invariant). 15. presentation has no write path into physical
evolution -- PASS (F #15, evil-morty SIGNED) and F-1 fixed (`6d5a823`: frame trust/digests bound to the
receipt).

## 11. Verification state

- Sandbox suite at `60b51a8` (all waves + all adversary fixes): **460 passed** (up from the 279 Round IV
  baseline; +admission-diagnostics, +interface, +snapshot/frame, +aqueous, + the follow-up regressions).
- Production touch-points (the comment-only probe + #115 gates): **51 passed**.
- Core production suite: UNCHANGED from `1d67401` (zero production code changed); hosted CI at the exact final
  SHA is the authoritative gate -- AUTHORIZATION-GATED (needs a push).

## 12. Boundaries / deferred / UNVERIFIED (not papered over)

- No real sourced artifact ships (`verified_sources/` is empty) -- sigma/source-correctness is uncheckable in
  code; the system enforces the STRUCTURE of admission and fails closed.
- External validation of the aqueous model against a MEASURED datum: UNKNOWN. The sourced Ka/Kw are tertiary.
- In-process isolation is realistic, not cryptographic (the process/JSON boundary is the real guarantee).
- `numerically_verified` covers conservation/positivity/passivity residuals, not a truncation-error bound.
- mesh `run_mesh` reaction path + `coupled_rhs` fail CLOSED on admitted windowed mechanisms (not yet threaded).
- Charged/ionic transport deferred (needs Nernst-Planck + electroneutral closure). #105/#130 stay 2.0 prereqs.
- C1 attribution counters + order-invariant anchor: recorded follow-up.
- C4 (#107) activator ledger: deferred.

## 13. The next single best falsifying experiment

Unchanged in spirit from Round IV and now sharper: obtain a genuinely INDEPENDENT MEASURED acetate-buffer pH
(an IUPAC primary table or a cited electrochemical measurement, not a value back-computed from the same Ka),
and add the NaAc(aq) ion pair to the model, then re-run the committed PHREEQC benchmark across the I <= 0.5
sweep. That single datum + species would move the aqueous model from "internally consistent + implementation-
verified + textbook-anchored" to "validated against an independent measurement," and would turn the C5
(I ~ 0.45) divergence from a documented scope gap into a closed one.

## 14. Release disposition

#115 (Claisen, 20th class) is dispositioned: branch-only, documented, the Option B 1.1 candidate is prepared
and green on its tip. NOTHING is merged, tagged, released, or pushed. The one outward step this round reaches
is an exact-SHA CI re-run on a pushed branch, which is held for explicit authorization.

## 15. Final SHA + CI

Pushed 2026-10-23 under explicit user authorization — the single outward step of this round. Merge, tag, and release remain unauthorized.

**A — feature branch.** `feat/chemical-graph-projections` advanced `1d67401 → 7ddb404` as a pure fast-forward (no force). Hosted CI run `39897481870` (event `pull_request`, head SHA `7ddb404`) concluded **success** — all 9 jobs green: `test (3.10)`, `test (3.12)`, `Sandbox foundation (experimental) (3.10)`, `Sandbox foundation (experimental) (3.12)`, `Wheel install matrix (3.10 / 3.11 / 3.12 / 3.13)`, `Optional PySCF backend (smoke)`.

**B — production candidate.** `pr101/production-1-1-rc` @ `0dde33a` pushed as a new branch (no force). CI run `39897599474` (event `workflow_dispatch` — `ci.yml` auto-triggers only on push-to-`main` / any PR / dispatch, so a bare branch push needs the manual dispatch) concluded **success** — 7 jobs green: `test (3.10)`, `test (3.12)`, `Wheel install matrix (3.10 / 3.11 / 3.12 / 3.13)`, `Optional PySCF backend (smoke)`. The candidate carries no "Sandbox foundation" jobs: it is built from the production prefix that predates `experiments/sandbox_foundation/`, so its `ci.yml` never defined them. The 2-job difference from A is expected, not a gap.

Prior pushed CI-green baseline: Round IV `1d67401`, run `39740729751`.
