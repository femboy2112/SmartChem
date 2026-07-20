# Claude Code integration prompt

Copy everything below into a Claude Code session that has the `femboy2112/SmartChem`
repository checked out and authenticated GitHub access.

---

You are integrating a comprehensive scientific, mathematical, and code-quality audit of
`femboy2112/SmartChem`.

Audit branch: `codex/comprehensive-audit-2026-07-20`
Draft PR: `https://github.com/femboy2112/SmartChem/pull/1`
Initial published audit commit: `6fb2234bb4d1a08dfccaac59dec25fa3c4837836`

Treat the fetched branch head as authoritative because review/integration metadata may add
commits after the initial audit implementation commit.

The audit began from upstream `main` commit
`3cd098553c1140a79f013489de98b9dba72aa63b`. Do not assume `main` is still at that commit.
Fetch the remote, record the current `origin/main` SHA, inspect all commits/diffs on the
audit branch, and reconcile any concurrent mainline changes deliberately. Never discard
unrelated user work. If the audit branch or draft PR has review comments, include them in
the integration.

Your goal is to integrate the audit completely, not merely copy a few fixes. Start by
reading these files in full:

- `AUDIT_2026-07-20.md`
- `README.md`
- `THE_ORBITAL.md`
- `THE_DIFFERENCE.md`
- `MANIFEST.md`
- this prompt

Then inspect the complete diff from the pinned base and the complete diff from current
`origin/main`. Preserve the audit's implementation, regression tests, CI split, and
truthful documentation unless a newer mainline change supersedes them with stronger
evidence. Resolve conflicts semantically; do not accept either side wholesale.

The integrated state must preserve these scientific and architectural invariants:

1. The current mathematics is a path category of conserving sequential histories.
   `scheduled_product` is a deterministic left-first serialization, not a parallel tensor;
   true interchange remains an intentional strict `xfail` until an open-process IR exists.
2. Atom and net-charge conservation, graph validation, typed carrier inventory, and
   numeric finiteness are enforced. Category theory does not establish chemical
   accessibility, kinetics, environmental response, circuit behavior, or field physics.
3. `reaction_energy` is a generic endpoint `dE`, not automatically `dH`, `dG`, heat, or
   spontaneity. `energy_equivalent_voltage = -dE/n` is explicitly not OCV;
   `open_circuit_voltage` must fail closed without Gibbs/electrochemical context.
4. Charged atomization against neutral atoms is refused without balanced fragments or
   reservoirs. The tabulated `reaction_energy_ev` helper validates positive integer
   stoichiometry and elemental balance.
5. A PySCF configuration is publicly enabled only when it matches a measured fixed-neutral-
   diatomic protocol. Within an enabled configuration, supported neutral atomic reference
   energies and fixed-geometry neutral diatomic energies may be returned. Charged/stateful
   species, optimized geometries, polyatomics, and unvalidated method/basis configurations
   must decline. MP2/CCSD internals and the polyatomic seed/relax/Hessian path may exist,
   but must not inherit the seven-diatomic MAE or be advertised as validated public
   capability. Preserve the corrected Bohr/angstrom gradient chain rule, strict CBS parser,
   `max_atoms` enforcement, optional-import behavior, and model-input fingerprinting.
6. The historical train/test split and selected seven-diatomic table are not pristine
   holdouts. Benchmark MAE is conditional on returned cases; any refusal prevents an
   accuracy-tier verdict. Conventional diatomic graph bond order must reach the benchmark
   oracle. The exact 1 kcal/mol threshold is `1 / 23.0605` eV.
7. `Estimate` provenance has a true additive identity. Repeated identical species are
   priced once and scale as one perfectly reused modeled quantity. Named correction
   displacements propagate by source. Opposing unrelated terms may make the compatibility
   scalar `systematic_ev` zero, but their source records remain distinct and their absolute
   magnitudes survive in the reporting floor. A CBS displacement, ZPE displacement, or
   validation MAE is not automatically a confidence interval or residual-error bound. Do
   not reintroduce coverage assertions into tests or prose.
8. Persistent-cache schema/version, type-tagged calculation specs, source/model-data
   fingerprint, key-bound record checksum, refusal policy, locking, atomic replacement,
   corrupt/future-schema preservation, and concurrent-writer behavior all remain covered by
   regression tests. Result-driving tables are read-only, and both bundled oracle specs
   cover their transitive model/table inputs. Checksums are integrity checks, not
   authentication.
9. Through the normal `generator_id` API, pathway generator identity cannot collide with
   anonymous search-local IDs; the low-level `generator_word` field remains an advanced
   escape hatch that should eventually move behind a registry/factory. Display names are
   non-semantic; search enumerates supplied steps without ranking alternative physical
   models by endpoint energy; `best_route` refuses incomparable methods/estimates; an uphill
   prefix may still lead to an allowed completed route.
10. Circuit/radiation tests are syntax and limited algebra only. They do not implement KCL,
    MNA, antenna radiation, coupled fields, or a Wheatstone bridge. The Zn/MnO2 equation is
    a simplified structural example, not a complete AA discharge mechanism. Capacity uses
    the limiting reagent's stoichiometric coefficient.
11. The frozen heuristic may be measured in `Env.standard()` only and declines other
    environments. Do not claim that a Store sweep creates environmental physics.
12. Keep the moonshot roadmap grounded: typed ports/open processes first, then sparse MNA
    and coupled lossy resonators, then RLGC/PEEC, then full-wave Maxwell, materials/thermal,
    and only then high-voltage/plasma escalation. Resonance can magnify voltage/reactive
    energy but never creates net energy; all passive/source-free models need energy and
    passivity checks.
13. Do not weaken chemistry's atom-symbol conservation to add nuclear physics. Introduce a
    separate typed nuclide/particle domain with the applicable conservation laws, Q values,
    four-momentum, and rest-mass/binding-energy accounting. Preserve the audit's classical-
    mechanics, radiation-regime, quantum-response/material, and relativistic frame/time
    contracts as roadmap requirements rather than pretending they already exist.

Integration workflow:

1. Create a fresh integration branch from current `origin/main` (or rebase the audit branch
   if that is cleaner). Record the old main SHA, audit head SHA, and integration head SHA.
2. Bring in every intentional audit change. Review `git diff --stat`, `git diff --check`,
   untracked files, renamed/deleted files, dependency metadata, and CI YAML. Do not omit
   `AUDIT_2026-07-20.md`, the new benchmark tests, optional-backend tests, or this prompt.
3. Inspect every conflict in context. Preserve newer user changes when compatible and add
   regression tests for any nontrivial reconciliation.
4. Search for stale claims such as “symmetric monoidal,” “KCL,” “Wheatstone,” “held-out,”
   “error bar,” “chemical accuracy,” “polyatomic support,” “OCV,” and “environment
   response.” Historical claims may remain only when clearly labeled falsified/withdrawn.
5. Run formatting/static checks available in the repository without introducing a noisy
   whole-tree rewrite. At minimum run `python -m compileall -q smartchem tests`,
   `git diff --check`, and parse `.github/workflows/ci.yml` with a YAML parser.
6. Run the dependency-light suite in an environment that does not have PySCF importable.
   Then run the complete fast suite with PySCF installed. Prefer clean environments; for
   example, from the repository root:

   ```bash
   python3.12 -m venv /tmp/smartchem-core-verify
   /tmp/smartchem-core-verify/bin/pip install -e '.[dev]'
   /tmp/smartchem-core-verify/bin/python -m pytest -q -rs

   python3.12 -m venv /tmp/smartchem-qc-verify
   /tmp/smartchem-qc-verify/bin/pip install -e '.[dev,qc]'
   /tmp/smartchem-qc-verify/bin/python -m pytest -q -rs
   ```

   Run the real HF/cc-pVDZ hydrogen smoke calculation. Run selected slow gradient/Hessian
   cases when resources permit or leave them to the manual CI job. Also run, or explicitly
   defer with a reason, the real correlated-energy regression:

   ```bash
   /tmp/smartchem-qc-verify/bin/python -m pytest -q --runslow \
     tests/test_findings.py::TestF5EnergiesAreMeasured::test_ccsdt_cbs_reaches_chemical_accuracy_on_co
   ```

   Never report skipped or deferred slow cases as passed.
7. Run focused suites for category/pathway, uncertainty/thermo, cache, reference/benchmark,
   cell/network, geometry, and optional backend behavior. Preserve the one expected strict
   interchange `xfail`; investigate any additional xfail, skip, warning, or flaky result.
8. Update the audit's verification record with exact commands, dependency versions, pass/
   skip/xfail counts, and any cases not run. Do not hand-edit a benchmark number without a
   reproducible run on the same declared population/protocol.
9. Review the final diff as a scientific reviewer and as a maintainer. In particular check
   dimensions/units, sign conventions, state identity, balance, numerical domains,
   uncertainty semantics, cache identity, optional dependency behavior, and documentation
   claims against executable behavior.
10. Commit in reviewable units or one well-described squash, push, update/open the PR, and
    wait for CI. Fix all in-scope failures. This prompt authorizes reconciliation, commits,
    pushes, and PR updates. Do not merge into `main` unless I explicitly authorize merging
    in this Claude session; otherwise leave a merge-ready PR and tell me the exact remaining
    action.

Do not expand this integration into implementing the entire future Maxwell/quantum/
relativistic roadmap. The audit intentionally establishes honest interfaces and failure
boundaries. New solvers belong in follow-up PRs with their own validation domains.

At the end, report:

- current-main, audit-head, and final-integration SHAs;
- PR URL and CI status;
- exact test commands and counts;
- any intentional behavior/API changes and migration notes;
- every unresolved scientific limitation or skipped validation;
- whether the branch is merged, merge-ready, or blocked, with the precise blocker.

Do not say “fully accurate,” “universal simulator,” “chemical accuracy,” or “validated
antenna/circuit simulator” unless a named independent benchmark and explicit domain actually
support that exact statement.

---
