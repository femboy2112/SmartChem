# SmartChem positive-frequency passive-RLC research round

**Date:** 2026-07-28
**Branch:** `main`
**Round base:** `4e1350e13ced6605244759023158b37106fea1bc`
**Selected midterm:** E2, finite positive-frequency passive ideal-RLC phasors
**Outcome:** implemented and verified within the declared mathematical regime
**Primary receipt:** `experiments/RESULTS_compiled_rlc_ac.md`

## Decision

The inherited short-term list was already complete. No calculation was in progress: the
previously recorded cold benchmark process `151446` was absent, had no journal or durable
stdout, and remains terminal-unclassified. The best-shot midterm was therefore E2 because
S0 topology and E1 resistive DC had already established its two principal prerequisites.

The implementation is additive. It does not change S0 structural identity or reinterpret
E1 records. A ninth closed executor owns a new exact RLC subject, exact output inventory,
runtime model, lifecycle, and verifier.

## Falsifying controls selected before acceptance

E2 could be accepted only if all of the following held:

1. one topology-generic path handled resistor, inductor, and capacitor edges without
   series/parallel special cases;
2. exact `Q(i)` elimination and exact driven-MNA rank were checked before a numerical solve;
3. the convention was fixed to RMS phasors with `exp(j omega t)`, absorbed
   `S = V conjugate(I)`, and source current entering the positive terminal;
4. analytic RC signs, damped resonance, nonidentity model-edge binding, KCL, source
   constraint, complex-power balance, and passive real-power gates passed;
5. an exact lossless series-LC resonance was refused before any engine call and without
   hidden regularization;
6. a verifier that imports neither the production circuit interpreter nor the E2 executor
   re-derived the relation, rank, graph content, values, powers, residuals, and output
   inventory;
7. mutation, quarantine, approval-identity, registry, and P0 admission controls remained
   fail-closed.

All seven controls passed for the shipped finite fixtures. They are not a proof for every
finite network or a physical-device validation.

## Calculation ledger

| Calculation | State | Durable evidence | Interpretation |
|---|---|---|---|
| inherited cold all-oracle benchmark, PID `151446` | terminal-unclassified | no journal or durable stdout | not timing, accuracy, or completion evidence |
| accidental unqualified local benchmark | interrupted, exit `130` | no journal/result | optional PySCF was discovered and CCSD work was stopped; not evidence |
| explicit heuristic benchmark smoke | complete | terminal command output | 19 required elements available, 28/28 bonds attemptable, 6 evaluated and 5 refused; conditional MAE `3.495 eV` / `80.60 kcal/mol`; incomplete coverage, no accuracy tier |
| first E2 damped control | complete but superseded | run `36b74989a16d4869917c33ee4eaa840e` | exposed no numerical error, but belonged to the pre-message-fix compiler |
| first E2 singular control | refused but superseded | run `0f3ae215b1a842e2a39f945bbb1f3ba3` | correctly refused, but its refusal detail was too generic |
| final E2 damped control | `COMPLETE` | run `1f1a11fc7cd34608b24e8298d990eaa9`; journal SHA-256 `2dd4bc5f446f1462ebcad99424c012e1164874d904c1a7866ae9105ee564f0e4` | authoritative finite E2 positive control |
| final exact series-LC resonance | `REFUSED` | run `da8dc8d51c394c90ba02eef1fcadfe5b`; journal SHA-256 `92896e7ee3b49c30950b4e4418650c564a9eb30abab3db0962e4fd7fdb0d7743` | authoritative zero-engine-call singular refusal |

The final write-once journals are
`/tmp/smartchem-e2-release.ZNIK1h/run.json` and
`/tmp/smartchem-e2-release.ZNIK1h/run.singular-refusal.json`. They are local raw
artifacts; the committed receipt retains their identities and complete interpretation.

## Result

For the exact parallel `R=L=C=1`, `omega=1`, `V=1` RMS control, model order `(C,R,L)`
is explicitly bound to structural edge order `(R,L,C)`. The retained currents are
`I_R=1`, `I_L=-j`, and `I_C=+j`. Absorbed powers are `S_R=1`, `S_L=+j`, `S_C=-j`,
and `S_source=-1`. KCL, the source constraint, source-inclusive complex-power balance,
the exact relation residual, and the normalized MNA backward residual are zero for this
fixture. The declared condition number is `2.6180339887498953`.

The exact boundary relation, in variable order
`(V_input,V_output,I_inward_input,I_inward_output)`, has rows

```text
V_input - V_output + I_inward_output = 0
I_inward_input + I_inward_output = 0
```

The final singular control refused with:

```text
direct subject preflight refused: exact driven MNA is rank deficient;
singular resonance is refused without regularization
```

It made zero engine calls, wrote no checkpoint, and admitted no observable.

## Evidence independence audit

- **Contact (`kappa`):** the positive and negative outcomes are live journaled executions,
  not inferred from source inspection.
- **Toolkit-relative distinguishability (`phi`):** exact `Q(i)` rank/relation derivation
  and normalized binary64 sparse MNA agree on the accepted fixture; exact rank separates
  the singular control before numerical solving.
- **Source correctness (`sigma`):** the mathematical convention and component laws are
  explicit. No empirical component source, tolerance model, or device dataset is present,
  so no empirical correctness claim is licensed.
- **Identity coupling (`rho`):** production and direct-verifier code are separately
  implemented and the verifier does not import production circuit/executor code, but both
  share the repository, declared convention, and fixtures. This reduces implementation
  common mode; it is not independent experimental validation.

The exact and numerical bearings are therefore concordant inside one declared model class.
They do not identify that model with a real circuit.

## Claim ledger

| Claim | Status | Evidence and boundary |
|---|---|---|
| Ninth executor is closed-registry reachable and owns its subject/model/output contract | supported | registry, dispatch, payload, admission, and lifecycle tests |
| Exact passive RLC boundary relation is retained for the declared finite network | supported | exact `Q(i)` relation plus independent re-derivation |
| Damped resonance obeys declared branch, KCL, power, and passivity laws | supported for the fixture | complete run plus direct verification |
| Exact lossless singular resonance is fail-closed without regularization | supported for the fixture | exact rank preflight and zero-engine-call refusal |
| E2 is a general AC simulator, device model, or all-network correctness theorem | rejected | outside implementation and evidence |
| E2 establishes transients, nonlinear/active behavior, harmonics, tolerances, safety, distributed EM, or port-Hamiltonian semantics | rejected | explicitly omitted |
| Heuristic chemistry benchmark meets an accuracy tier | rejected | five refusals and `INCOMPLETE COVERAGE` |

## Verification ledger

- Focused E2 circuit/lifecycle/verifier/registry/P0 selection: `78 passed`.
- Full module-entry suite: `1467 passed, 14 skipped, 1 xfailed`.
- Full console-entrypoint suite: `1467 passed, 14 skipped, 1 xfailed`.
- The expected failure remains expected; skipped tests were not counted as passed.
- Ruff lint and format checks pass on the 12 E2-touched Python files. The wider historical
  Python scope is not Ruff-clean under local Ruff `0.15.17`; those pre-existing findings
  are outside this slice and no full-repository lint claim is made.
- Bytecode compilation and `git diff --check` must pass immediately before commit.

## Roadmap after E2

### Short term

1. Freeze the E2 receipt, roadmap state, and exact refusal language.
2. Keep all nine executor regressions green and preserve current plan/output digests.
3. Treat every raw journal as write-once; never overwrite or promote superseded runs.

These are completion/maintenance gates, not a new scientific vertical.

### Best next midterm: deliberate `StructureIR` adapter

This is now the best-shot dependency cut because S0, E1, and E2 provide three concrete
topology/semantics cases while the change can remain code-local.

1. Specify an adapter from existing S0 canonical structure into a typed `StructureIR`
   value without modifying S0 identity or the nine existing subjects.
2. Bind adapter identity into plan and compiler digests; a topology spelling change must
   not become a model change.
3. Preserve every existing output contract and observable digest under an explicitly
   approved migration.
4. Add round-trip, alpha-renaming, declaration-order, model-edge-binding, and forged
   adapter controls.
5. Regress all nine executors and refuse any generalized physics claim. The adapter is
   architecture, not evidence that one structure language already covers all domains.

### Following midterms

1. **W2 dispersive water:** declare equations, boundary conditions, wavelength support,
   and `N/2N/4N` convergence; retain branch and scattering observables; verify through
   independent code. Remain `STRUCTURAL_TOY` until measured regime-matched evidence exists.
2. **Traffic kinematic-wave vertical:** specify conserved density/flux, weak/shock
   semantics, initial/boundary data, entropy/refusal conditions, and calibration casualties
   before treating it as a regime-valid analogue.
3. **Empirical D2b:** first obtain data authority. Then define censoring, cohort
   applicability, bootstrap/profile uncertainty, external locked validation, and competing
   risks. No actual-human or experimentation authority is implied.
4. **Remaining optimizer:** admit one Class-A transform at a time only with exact
   output/provenance equivalence; measure cold and warm timing separately. Class B requires
   evidence, and every fidelity/output trade remains Class C approval.
5. **Chemistry expansion:** keep xTB, broader polyatomic validation, state/conformer
   coverage, and backend bond-order policy separate from compiler plumbing.

### Long term, decomposed

1. Domain-extensible `StructureIR` with typed open ports and explicit state identity.
2. Separate domain `ModelIR`, claim-bearing `EvidenceIR`, and feedback-preserving
   `ExecutionDAG`; do not flatten physical feedback into task order.
3. Verified structure/model adapters and a model-chain planner with frozen outputs.
4. General validity, refinement, checkpoint, and evidence-transition runtime.
5. Port-Hamiltonian semantics only after dynamic state and an operational effort/flow power
   pairing are explicit and verified.
6. Distributed/full-wave, electrothermal, mechanics, kinetics, particle/radiation, and
   relativistic extensions, each behind its own applicability and validation gates.
7. Conversational surface last, exposing rather than impersonating plan, approval, evidence,
   result, and refusal transitions.

## Compact-resume cut

After this round is committed, resume from the pushed `main` commit, not from a raw
`/tmp` journal. Read, in order:

1. `RESEARCH_ROUND_RLC_AC_2026-07-28.md`;
2. `experiments/RESULTS_compiled_rlc_ac.md`;
3. `ROADMAP_2026-07-27.md`;
4. `CATEGORY_BACKBONE_ROADMAP_2026-07-27.md`;
5. live `git status`, branch, remote, and current test state.

The next implementation target is the bounded `StructureIR` adapter. W2 is the next
scientific-model vertical after that architectural cut. No calculation remains in progress.
