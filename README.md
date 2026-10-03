<div align="center">

# SmartChem

**A reality-respecting chemical route compiler.**

Bounded search, evidence-gated readiness and capability, and verified JSON
transport — built on the premise that a loud `UNKNOWN` beats a plausible,
unearned answer.

[![CI](https://github.com/femboy2112/SmartChem/actions/workflows/ci.yml/badge.svg)](https://github.com/femboy2112/SmartChem/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/femboy2112/SmartChem)](https://github.com/femboy2112/SmartChem/releases/latest)
[![Python](https://img.shields.io/badge/python-3.10--3.13-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

> **Current release: [v1.0.0 — Stable Chemical Compiler](https://github.com/femboy2112/SmartChem/releases/tag/v1.0.0)**
> (2026-10-03). Python 3.10–3.13, MIT. Distributed as **GitHub source + a release
> wheel/sdist** (with `SHA256SUMS` and a reproducibility manifest) — it is **not**
> published to PyPI. See the [changelog](CHANGELOG.md) and [install](#install) below.

> **Research software, not a laboratory authority.** A formally admitted route is a
> *compiler candidate, not a bench procedure*; `CAPABILITY_FIT` is a model-relative fit
> verdict, *not a safety certification*. See [safety & epistemic scope](#safety--epistemic-scope).

---

## Why SmartChem

Most tools that reason about chemistry optimize for an answer. SmartChem optimizes for an
**honest** one. Its core promise is epistemic: it must never *vouch* for something it
cannot support, because a confident wrong answer is worse than an admitted gap.

So the compiler keeps verdicts separate and earns each one:

- a bounded search tells you whether it **exhausted its declared space** or stopped at a
  budget — an incomplete search never looks complete, and an empty one never looks like a
  proof of absence;
- a route is a `FORMAL_CANDIDATE` until evidence lifts it up a **derived readiness ladder**;
  missing operations are shown, not hidden;
- a declared bench profile is **applied** to ranking — each route reads as *fitting*,
  *excluded*, or *unknown-fit*, and an unmodeled demand reads `UNKNOWN`, never a silent pass;
- chemical identity is never equated with purity, grade, phase, or price; every price is
  dated and sourced or it is `UNKNOWN`;
- derived, estimated, and unsupported claims wear distinct labels.

The standing standard is simple: **a loud refusal is acceptable; a plausible, unearned
answer is not.**

## What it does

SmartChem turns the chemistry core into a bidirectional **chemical compiler**:

- **Decompiler** — descends a target compound to its elemental buckets as an AND–OR
  hypergraph (conservation- and valence-respecting *accounting*, not a mechanism claim).
- **Recompiler** — reads that descent back into candidate synthesis routes, ranked by
  sourced evidence and terminated on real commodity buckets, not pretending every reagent
  is elemental.

Both directions share one typed `ChemicalCompilationIR` and one honesty contract. Around
that core:

- **A tolerant human front door** — paste ordinary notation (`CuSO₄·5H₂O`, `C2H6O`, a
  SMILES) and `smartchem plan` reports the strongest identity layer it can perceive, and
  exposes ambiguity instead of guessing. A formula is a *composition, not a constitution*.
- **A typed route algebra** — an ordinary request searches a certified multi-family route
  algebra (capped-scission + admitted Diels–Alder families). Widening chemistry is a typed,
  content-bound, auditable operation — a chemistry-bearing change moves the request digest;
  a prose edit does not.
- **A capability compiler** — `--capability-profile research-lab|poor-man` projects each
  ranked route through a declared bench, axis by axis (material, equipment, physical,
  process, containment, ventilation, measurement, waste, procurement, attention, monetary).
- **Verified transport** — `load_response(payload, VerificationPolicy)` re-derives or binds
  every verdict-bearing field from the carried evidence and returns an out-of-band
  `VerificationReceipt`; verification is budgeted, and exhaustion is a refusal, never a
  skipped check.
- **An evidence auditor** — `smartchem.evidence` points SmartChem's own discipline (*a check
  derived from its own subject checks nothing*) at another project's numerical probes,
  auditing the contract around them and either certifying or refusing.

Beneath the chemical compiler sits the original research seam: a rigorous compiler/runtime
boundary, a chemistry core, nine deliberately narrow executors that test the design, and a
separate finite typed open-diagram syntax with independently verified ideal-resistor DC and
positive-frequency passive-RLC interpretations.

## Install

SmartChem is not on PyPI. Install the released wheel directly from GitHub:

```bash
pip install https://github.com/femboy2112/SmartChem/releases/download/v1.0.0/smartchem-1.0.0-py3-none-any.whl
```

Or from a clone (editable, with the dev extras):

```bash
git clone https://github.com/femboy2112/SmartChem.git
cd SmartChem
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
```

The core needs only `numpy` and `scipy`. The PySCF quantum-chemistry backend is an optional
`qc` extra (`pip install -e '.[dev,qc]'`).

## Quickstart

```bash
smartchem --version                       # smartchem 1.0.0

# Resolve an identity and plan from a name / formula / SMILES:
python -m smartchem plan 'smiles:CO'

# Compile a synthesis route and emit the stable JSON response:
python -m smartchem recompile 'smiles:CC(=O)OCCC(C)C' --capability-profile poor-man --json
```

Exit codes are meaningful: `0` success · `5` a complete search with no admitted route · `4`
incomplete · `2` invalid input · `70` internal error.

```bash
# A Unicode hydrate paste → composition + retained component boundary:
python -m smartchem plan 'CuSO₄·5H₂O'

# A certified Diels–Alder route with an explicit (empty) helper-reagent pool:
python -m smartchem recompile --smiles 'C1CC=CCC1' --have 'C=CC=C' 'C=C' --no-helper-reagents
```

## Safety & epistemic scope

SmartChem is **research software**, not a laboratory authority.

- A formally admitted route is a **compiler candidate, not a bench procedure.**
- `CAPABILITY_FIT` is a model-relative fit verdict, **not a safety certification.**
- Completeness is **bounded** — over the *admitted* search space, not all of chemistry.
- `UNKNOWN` is intentional: the compiler withholds a verdict rather than fabricate one.
- There is **no universal-synthesis promise**; coverage is deliberately narrow and explicit.

See [COMPATIBILITY.md](COMPATIBILITY.md) for the full scope of what the compiler does and
does not guarantee.

## The non-negotiable contract

SmartChem follows four rules:

1. **Reality outranks completion.** Well-formed, coherent, applicable, converged,
   valid-after-run, validated, and scientifically useful are different verdicts.
2. **Output is frozen before optimization.** Observable membership, support, resolution,
   precision, coverage, uncertainty, diagnostics, provenance, and retained artifacts may not
   be reduced without explicit scientist approval.
3. **Efficiency is mandatory inside that boundary.** The compiler uses the cheapest
   identity- or contract-preserving execution it can establish; if resources are
   insufficient it checkpoints, proposes a disclosed alternative contract, or refuses — it
   does not return a smaller success.
4. **Meaning belongs to the scientist.** The compiler may derive, check, search, propose,
   and expose unknowns; it may not silently choose scientific meaning or promote a metaphor,
   finite check, or synthetic recovery into physical validation.

The full policy is in
[DIRECTION_AUDIT_2026-07-27.md](docs/history/DIRECTION_AUDIT_2026-07-27.md).

## How it works

The executable seam runs an incomplete source down to a typed outcome, binding scientist
approval to the exact plan digest:

```text
incomplete source
    → typed shepherd session
    → resolved source/target/transport/assembly meaning
    → Physical IR + frozen OutputContract
    → candidate plan + blockers + predicted resources
    → scientist approval bound to the exact plan digest
    → closed-registry execution
    → pre/post validity obligations
    → COMPLETE | INCOMPLETE | INVALID | REFUSED | FAILED
    → typed outputs + certificate
```

The runtime registry is closed and reviewed: no third-party executor inherits authority by
registration, and a pre-backend admission snapshot is rechecked after in-process callbacks
and before certification — so a callback cannot silently rewrite the approved plan, subject,
output contract, or compiler identity and still complete. `ClaimKind` and `EvidenceStatus`
stay independent: an analogue can have established algebra without becoming literal; a
literal target can remain unsupported.

### The nine executors

| Executor | What it establishes | Hard boundary |
|---|---|---|
| Reaction energy | Conserving closed endpoint-energy execution with exact output inventory and a verified spectator-residue transform under the runtime-owned separable model. | Public oracle coverage is narrow; spectator cancellation is not licensed for interacting, solvated, field-coupled, or open models. |
| Shallow-water horizon v1 | Branch-specific `U ± sqrt(g h)` characteristics and sample-bracketed crossings on a typed prescribed profile. | `ANALOGUE/STRUCTURAL_TOY`; not a continuous background solution, measured flume, scattering calculation, or literal black hole. |
| Water finite-section preflight v2 | Manufactured discharge/head, `kh`, Bond-number, sign/orientation, uncertainty, and adjacent-sample compatibility gates. | Does not establish steady regularity, a continuous transcritical solution, or experimental validation. |
| Continuous steady-water control | Manufactured sub/super/transcritical backgrounds; bounded cell-centred energy-root reconstruction on 32/64/128 meshes; binary64 roundings of a 60-digit Decimal reference; retained residuals, both refinement rates, both compatibility conditions, and an exact finite-v2 comparison. | `ANALOGUE/STRUCTURAL_TOY`; not a general stationary solver, continuum theorem, propagated-uncertainty analysis, measured flume, dispersive/scattering result, or literal gravity. |
| Human-isotope D2a | A complete typed interpretation and proof that one hypothetical median-lethality endpoint is compatible with distinct survival families. | `EXPERIMENTAL_PROXY/STRUCTURAL_TOY/UNVALIDATED`; no LD50-to-rate conversion, human prediction, toxicology calibration, or experimentation authority. |
| Synthetic survival D2b-S | TRAIN-only fixed-family conditional-binomial recovery on content-addressed synthetic cohorts, with uncertainty diagnostics and locked HOLDOUT scoring. | Same-generator implementation evidence only; no human/animal evidence, biological validation, causality, or transfer authority. |
| Finite C3 Ising↔lattice gas | All eight states, `ε=4J`, `μ=2h−4J`, `H_I=H_LG+3(h−J)`, and the formal partition identity, checked with exact integers and a separate direct verifier. | `ANALOGUE/ESTABLISHED/CERTIFIED` for that finite algebra only; no material identity, dynamics, thermodynamic limit, or arbitrary-graph transfer. |
| Finite resistive DC E1 | Exact rational passive boundary relation, one topology-generic sparse-MNA drive, explicit model-to-edge binding, complete node/branch/source output, and a production-independent verifier. | `LITERAL/VALIDATED_WITHIN_REGIME/CERTIFIED` only for finite positive ideal resistors and the declared drive/reference; no device, AC/RLC, thermal, safety, nonlinear, or distributed claim. |
| Positive-frequency passive RLC E2 | Exact `Q(i)` boundary relation, exact driven-rank preflight, one normalized sparse complex-MNA path, complete phasor/power/diagnostic output, and a production-independent verifier. | `LITERAL/VALIDATED_WITHIN_REGIME/CERTIFIED` only for declared finite ideal networks at one positive frequency; exact lossless singular resonance is refused without regularization. No device, transient, nonlinear, tolerance, safety, or distributed claim. |

The Ising/lattice-gas control is deliberately load-bearing: it proves SmartChem can carry an
exact cross-domain map without confusing exact mathematics with literal physical identity.
Every one of the eight microstates stays output; no grouped summary replaces them.

A metaphor is accepted as an **under-specified program, not as truth.** The current
portfolio deliberately spans three cases — a regime-bounded structural analogue
(water/black-hole), an underidentified cross-scale experimental proxy (human/isotope), and
an exact finite map between distinct referents (Ising/lattice-gas). For the module-by-module
map and scientific caveats, see [docs/history/MANIFEST.md](docs/history/MANIFEST.md).

## The 1.0 release program

The chemistry compiler reached 1.0 through a **finite** release program, rather than
treating each newly discovered frontier as the next release boundary:

```text
0.6 human front door            merged
0.7 production chemical algebra  merged
0.8 real route dossiers          merged
0.9 capability compiler          merged
0.9.5 coverage/adversarial RC    merged
1.0.0 stable semantics           stable release
```

The **stopping rule is explicit**: the 1.0 line freezes the public machine semantics —
identity, bounded-search completeness, the readiness ladder, capability assessment, the
evidence and `StreamDisposition` contract, and verified transport — under the stability
contract in [COMPATIBILITY.md](COMPATIBILITY.md). From 1.0, new chemistry may *widen*
coverage but may **not** silently change the meaning of an existing verdict word. A wider
reaction-family algebra is a post-1.0 MINOR, never a reason to hold the release.

The normative plan is
[CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md](docs/research/CHEMICAL_COMPILER_1_0_PROGRAM_v0.1.md);
the ranked next-steps, deliberate non-goals, and tracked debt live in
[ROADMAP.md](ROADMAP.md).

## Status & verification

The 1.0.0 production tree is **compiler-semantically and version-independent-fingerprint
identical** to the reviewed release candidate — only the declared version-bound identity
moved (the `__version__` bump and its version-bound CLI goldens). The stable release re-ran
the full hosted CI at `8345bbb`
([run `37083985662`](https://github.com/femboy2112/SmartChem/actions/runs/37083985662), all
7 jobs green):

- `test (3.10)` and `test (3.12)` run the OOM-safe suite via `scripts/run_suite.sh` with the
  optional RDKit and PySCF backends **absent**;
- four wheel-install-matrix jobs (3.10–3.13) build and install the release artifact and prove
  it byte-identical to source;
- a PySCF smoke job runs with PySCF 2.14.0 **present**.

The reviewed-RC run `37071540287` recorded the baseline counts:

```text
test (3.10), test (3.12):   7482 passed, 84 skipped, 0 xfailed   (7566 collected, 0 failed)
PySCF smoke (-m "not slow"): 7523 passed, 33 skipped, 14 deselected
```

There are **no xfails** — the last strict xfail (parallel interchange) was discharged by
PR #79. Skips are environment-honest and never reported as passed: RDKit-gated CIP checks
run only when the dev-only RDKit oracle is present, and the PySCF integration tests run only
when that stack is present. On a memory-constrained box the monolithic `pytest` run is
OOM-killed, so `scripts/run_suite.sh` (short-lived batched processes) is the maintained
full-suite runner. The official artifacts rebuild exactly via
`scripts/build_release.py --ref v1.0.0`.

Reproduce locally:

```bash
pip install -e '.[dev]'
scripts/run_suite.sh          # OOM-safe full suite
python -m smartchem.bench
pytest -q --runslow           # add real-wavefunction integration coverage
```

Every cited compiled run has a committed deterministic harness and a durable receipt under
[`experiments/`](experiments/README.md); raw journals are write-once local artifacts, and
receipts retain the identities, outcomes, scope, evidence status, omissions, and negative
claims.

## Documentation

**Start here** · this README → [COMPATIBILITY.md](COMPATIBILITY.md) (what it guarantees) →
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (the stage map).

| User-facing | Engineering / release | Research record |
|---|---|---|
| [COMPATIBILITY](COMPATIBILITY.md) | [CHANGELOG](CHANGELOG.md) | [THE_COMPILER](THE_COMPILER.md) |
| [CONTRIBUTING](CONTRIBUTING.md) | [ROADMAP](ROADMAP.md) | [THE_ORBITAL](THE_ORBITAL.md) |
| [SECURITY](SECURITY.md) | [ARCHITECTURE](docs/ARCHITECTURE.md) | [THE_DIFFERENCE](THE_DIFFERENCE.md) |
| [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) | [CHEMICAL_COMPILER_STANDARD v0.5.0a1](CHEMICAL_COMPILER_STANDARD_v0.5.0a1.md) | [experiments](experiments/README.md) |
| [CITATION](CITATION.cff) | [UPTAKE_MANIFEST v0.5.0a1](UPTAKE_MANIFEST_v0.5.0a1.md) | [docs/history](docs/history) · [docs/research](docs/research) |

The `v0.5.0a1` base standard remains the inherited normative contract; `UPTAKE_MANIFEST` is
an honest, per-requirement ledger of exactly what is implemented-and-verified versus still
open.

## Repository layout

```
smartchem/            the compiler: identity/parse, decompiler/recompiler, route algebra,
                      search, capability/, evidence/, observation/, oracle/ layers, plus the
                      chemistry core (Molecule/Config/Reaction) and the nine executors
smartchem/evidence/   decoupled probe auditor (stdlib-only; smartchem-verify-probes)
docs/                 architecture, history/ (audits, manifests), research/ (round records)
experiments/          reproducible probes, compiled harnesses, and durable receipts
tests/                the test suite (run via scripts/run_suite.sh on constrained boxes)
scripts/              build_release.py, run_suite.sh, and release tooling
```

## Contributing

Issues and PRs are welcome. Before a substantive change, read
[CONTRIBUTING.md](CONTRIBUTING.md) and [COMPATIBILITY.md](COMPATIBILITY.md): changes to
stable 1.x semantics require compatibility adjudication, new chemistry must widen coverage
without redefining a verdict word, and chemistry-bearing claims need evidence and sourcing.
Please run the [full suite](#status--verification) locally. Security and
scientific-correctness reports go through [SECURITY.md](SECURITY.md).

## Support

If SmartChem is useful to you, you can [**buy me a coffee ☕**](https://ko-fi.com/leah2112).

## License

SmartChem is released under the [MIT License](LICENSE).
