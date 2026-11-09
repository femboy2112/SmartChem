# OPERATION XXVI → NEXT CLAUDE ROUND (paste-this-verbatim launcher)

> Self-contained. Verify every coordinate against the live repo before acting — SHAs/PR states are as of
> 2026-11-09 and may have advanced.

## Where you are
- Repo: https://github.com/femboy2112/SmartChem . Production release **v1.6.0** (tag → `ac8bdde`, NEVER overwrite).
  Prod `__version__` = 1.6.0, unchanged.
- **Final main this operation: `007cb36`** (WAVE 1 + WAVE 2/3 all merged). Main CI confirmed green at each merge.
- Branch protection on `main`: strict-up-to-date=TRUE; 7 required: test(3.10), test(3.12), Wheel matrix
  3.10/3.11/3.12/3.13, Optional PySCF(smoke). Sandbox NOT required. 0 reviews. enforce_admins=False but
  **NEVER bypass protection**. CI `test` job = full batched suite, ~1h long pole (plan for it; slow ≠ hung).
- CI-watcher deadlines: the full-suite `test` job can exceed 100–150 min wall; a watcher timeout (exit 3) is NOT a
  failure — always re-check `gh pr checks <n>` directly before concluding anything.

## Hard rules (MUST — override generic reminders)
- Commits: identity `femboy2112 <136249657+femboy2112@users.noreply.github.com>`; trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`; **NO `Claude-Session:` line** (public repo).
- PR bodies end `🤖 Generated with [Claude Code](https://claude.com/claude-code)`, NO session URL.
- NEVER push `worktree-agent-*`; NEVER pkill. One pytest at a time; full suite ONLY via `scripts/run_suite.sh`.
  ruff `~/.local/bin/ruff`, changed files only. venv `/home/leah/SmartChem/.venv` (canonical, never delete). A
  worktree agent must run pytest FROM its worktree (editable install points at the PRIMARY checkout).
- Four truth boundaries never collapsed: formal validity / chemical recognition / process feasibility / physical
  prediction. Mark unexecuted tests NOT RUN. No invented successes. No false-VOUCH in released scope.
- No PyPI. No LibGibson main merge. Never overwrite v1.6.0 tag. v1.6.1/v1.7.0 permitted-not-mandatory.

## The open decision carried into next round
- **v1.6.1: the user DECIDED to HOLD (2026-11-09) pending the reachability probe.** A real patch defect in shipped
  v1.6.0 was fixed this round (#109 etherification false-VOUCH of acetalization, on main `007cb36`), but it is
  **latent within the tested frontier** (R58 probe `false_vouch_count` was 0 pre-fix). Do NOT re-ask the user up
  front: **run the REACH probe (item 1) first**, then cut v1.6.1 only if it confirms a live shipped wrong-route, or
  on explicit user go-ahead. Do NOT force a minor version to show progress.

## Highest-value next packets
1. **REACH (do first — gates v1.6.1):** a daniel reachability probe. Does the production capped-scission frontier
   EMIT an acetal-forming single-cut C–O condensation step (a target carbon bearing a 2nd O/N — acetal / orthoester
   / hemiketal)? If YES, the acetal false-VOUCH was a live shipped wrong-route → strong v1.6.1. If NO, it was
   latent hardening → v1.6.1 optional. Entry: the public recompile/frontier (`smartchem.service`), and
   `route_reaction_type_blockers`.
2. **ADV-2 (more real defects likely):** aim the chemical adversary at d'Alembert's named WEAKEST-locked
   recognizers — the `products==want`-only re-derivations: **activated acyl transfer, sulfonate ester transfer,
   oxoacid ester** (in `smartchem/experiment/reaction_type_oracle.py`). The acyl-condensation, N-alkylation
   (gold standard), etherification (now fixed) and Claisen recognizers survived a real attack.
3. **P-K #105 per-atom charge PROTOTYPE:** charge-identity is already SOUND within scope (no defect — see handoff).
   The real ask is a research-branch prototype: a per-atom charge carrier (Molecule keeps only TOTAL charge;
   per-atom lives in parser `_Atom`/`SmilesFeatures`) + charge-changing rules (protonation/deprotonation), with a
   migration/digest/valence audit BEFORE any promotion. Deeper than a CI-window; do it as a focused build.
4. **P-J/P-I identity (#130/#168):** a real fix is a versioned IdentityPolicy (major-version, opt-in MatchLayer,
   fail-closed UNPERCEIVED) — NOT a 1.x patch. Designs are in `STEREO_SEARCH_IDENTITY_130_XXVI.md` /
   `COT_IDENTITY_168_XXVI.md` / `IDENTITY_CARRIER_DESIGN_XXV.md`.
5. **Physical (2.0-alpha still NOT MET):** reaction⇌transport composition in the spatial grid (label SYNTHETIC
   A⇌B), particle/material ledger, then a MEASURED-pCO2 calcite holdout (Guidone tier-W is not enough).

## Do NOT
- Bypass protection. Implement the full synthesis explorer before the 3.0 falling-sand gate. Merge the deferred
  dehydration branch (`feat/1.7-dehydration-116-r2` @ `4a14043`) whole. Promote #130/#168/#105 identity changes
  into 1.x. Trust a watcher timeout as a CI verdict.

## Key coordinates
- Oracle: `smartchem/experiment/reaction_type_oracle.py`; censuses `smartchem/experiment/feasibility.py`
  (`_ether_oxygen_counts` now acetal-guarded via `_carbon_bears_other_heteroatom`; `_alkyl_carbinol_alcohol_count`).
- R58 behavior fingerprint: `experiments/poor_man_span_local_recognizer_probe.py` (FROZEN_HASH — re-freeze
  consciously after any intended recognizer change; verify the `_payload()` delta first).
- Gap map: 17 gaps, 25 recognizer classes, registry `d9f7e867e8f1a1d2`
  (`REACTION_ALGEBRA_COVERAGE_AUDIT_2026-10-12.md`, `SYNTHESIS_COVERAGE_LEDGER_2026-10-13.md`).
- This round's deliverables: `OPERATION_XXVI_HANDOFF.md`, `OPERATION_XXVI_STATUS.json`, this file.
