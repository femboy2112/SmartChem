# Contributing to SmartChem

Thanks for your interest. SmartChem is a reality-respecting chemical route compiler, and
its central value is *epistemic honesty*: it must not claim more than its evidence
supports. Contributions are very welcome, but they are held to that same bar. Please read
this before opening a pull request.

## Supported Python

SmartChem supports **Python 3.10–3.13**. Changes must keep all four working.

## Development install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'          # core + pytest + hypothesis
# pip install -e '.[dev,qc]'     # add the optional PySCF quantum-chemistry backend
```

The package has a tiny runtime footprint (`numpy`, `scipy`); the quantum-chemistry
oracle (`pyscf`) is an *optional* extra and is never required for the core compiler.

## Running the tests

The suite is large and accumulates memory across its ~290 files, so a monolithic
`pytest` run is OOM-killed on a small (~7 GB) box. **Use the OOM-safe batched runner:**

```bash
scripts/run_suite.sh
```

It runs heavy files solo, uses a fresh pytest process per batch, and exits non-zero iff
any batch failed. While developing, run the **targeted** tests for the area you touched
first — they are fast and specific:

```bash
pytest -q tests/test_identity.py
pytest -q tests/test_<the_module_you_changed>.py
```

Lint only the files you changed:

```bash
ruff check <your changed files>
```

## The public-contract freeze (read this before changing behavior)

SmartChem 1.x has a **frozen public contract**. The following are stable and must not
change meaning within the 1.x line:

- the parser / identity semantics,
- the route-search behavior and transform algebra,
- evidence strength, readiness, and capability (`CAPABILITY_FIT`) semantics,
- `StreamDisposition` and the verification semantics,
- the stable wire/JSON schemas and the public API surface,
- the meaning of every verdict word (VOUCH, FIT, complete, ready, `UNKNOWN`, …).

**New chemistry is welcome and expands *coverage* — it must never *redefine a verdict
word*.** Adding a reaction family, an oracle row, or a capability declaration so that the
compiler can *say something true about more inputs* is in scope. Changing what "VOUCH" or
"complete" or "FIT" *means* is not, within 1.x.

Any change that touches the frozen contract — including a change that would alter a
stable schema, a verdict, or a result fingerprint — requires **compatibility
adjudication**: it must be justified against [COMPATIBILITY.md](COMPATIBILITY.md), and a
breaking change is a 2.0 conversation, not a 1.x patch.

## Evidence and sourcing requirements for chemistry

- **No unsourced practical claim.** A rate, cost, temperature, or feasibility assertion
  must carry a source, or be a clearly labeled **DERIVED** estimate that states its method
  *and* a real uncertainty.
- A fabricated or decorative error bar is **banned** — it is worse than `UNKNOWN`, because
  it launders a guess into a measurement. If you cannot defend a number, emit `UNKNOWN`.
- A capability/readiness verdict must be gated on a model that actually *measures* the
  property it rewards. A topological or thermodynamic proxy that does not encode the
  capability is not evidence for it.

## Mutation / holdout expectation for load-bearing semantics

If you touch load-bearing soundness code (identity, conservation, evidence gating,
capability, search completeness), a green suite is not sufficient on its own — a
self-consistent menu can be incomplete and still pass every self-check. Demonstrate that
your change is actually exercised: add a test that *fails without your change* (a holdout
case or a mutation it must catch), and say so in the PR.

## Opening a pull request

1. Branch off the latest `main`.
2. Make the change; keep the diff scoped to one concern.
3. Run `scripts/run_suite.sh` (or the targeted tests for a small change) and `ruff check`
   on your changed files.
4. Fill out the pull-request template, including the semantic-contract and
   evidence/source sections.
5. Open the PR against `main`.

## Reporting bugs and correctness issues

- A **software security vulnerability** → private report, see [SECURITY.md](SECURITY.md).
- A **scientific-correctness / overclaim** issue (false vouch, false FIT, identity
  hallucination, provenance mismatch, …) → the **Scientific correctness** issue form.
- An ordinary **bug** or **feature** → the corresponding issue form.

By contributing, you agree your contributions are licensed under the project's
[MIT License](LICENSE), and you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md).
