<!-- Thanks for contributing to SmartChem. Keep the diff scoped to one concern. -->

## What this changes

<!-- One or two sentences. What and why. -->

## Checklist

- [ ] **Scope** — the diff addresses one concern; unrelated cleanups are split out.
- [ ] **Tests** — ran `scripts/run_suite.sh` (or the targeted tests for a small change) and `ruff check` on changed files; results noted below.
- [ ] **Semantic-contract impact** — this does **not** change the meaning of any frozen 1.x verdict, schema, or API (parser/identity, search/transforms, evidence, readiness, capability/`CAPABILITY_FIT`, `StreamDisposition`, verification). If it does, I have explained the compatibility adjudication against `COMPATIBILITY.md`.
- [ ] **Evidence / sources** — any new chemistry claim is sourced or is a labeled DERIVED estimate with method + uncertainty; no unsourced practical claim; no decorative error bars.
- [ ] **Public-contract / schema impact** — no stable wire/JSON schema or result fingerprint changed, or the change is declared and justified.
- [ ] **Load-bearing semantics** — if soundness code changed, I added a test that fails without this change (holdout / mutation), and said so.
- [ ] **Docs** — README / CHANGELOG / COMPATIBILITY updated if behavior or interface changed.
- [ ] **No secrets** — no credentials, tokens, `.env`, or private data in the diff or history.

## Test output

```
<!-- paste the relevant run_suite / pytest / ruff result -->
```
