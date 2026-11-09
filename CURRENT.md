# SmartChem — current state

> A one-page entry point to what works **today**, what is still research, and where to look next.
> Released line: **v1.6.0**. Last reviewed for 1.6.0. For the stability contract see
> [COMPATIBILITY.md](COMPATIBILITY.md); for the stage map see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What works today (shipped in 1.6.0)

SmartChem is a bidirectional **chemical compiler** with an honest verifier:

- **Decompiler** — descends a target compound to its elemental/commodity buckets as a
  conservation- and valence-respecting AND–OR hypergraph (accounting, not a mechanism claim).
- **Recompiler** — reads that descent back into candidate synthesis routes, ranked by sourced
  evidence and terminated on real commodity buckets. `recompile` is the canonical synthesis verb.
- **Bounded search with completeness receipts** — a search tells you whether it **exhausted its
  declared space** or stopped at a budget; an incomplete search never looks complete, and an empty
  one never looks like a proof of absence.
- **A reaction-type oracle of 25 recognizer classes** — a fail-closed positive whitelist used as a
  ranking demoter (coverage loss is acceptable; a false VOUCH is not).
- **A capability compiler** — `--capability-profile research-lab|poor-man` projects each ranked
  route through a declared bench, axis by axis.
- **Verified JSON transport** — `load_response(payload, VerificationPolicy)` re-derives every
  verdict-bearing field from carried evidence; verification is budgeted and exhaustion is a refusal.

CLI verbs (`smartchem` == `python -m smartchem`): `plan`, `decompile`, `recompile` (canonical),
`compile` / `synthesize` (deprecated aliases of `recompile`), `audit`, `graph`.

## What's released

**v1.6.0** — release commit `ac8bdde03893da8522efba04929da3fe29aa62a1`, `__version__ = "1.6.0"`.
Python 3.10–3.13, MIT. Distributed as **GitHub source + a release wheel/sdist** (with `SHA256SUMS`
and a reproducibility manifest); **not** published to PyPI. Coverage line: 17 classes at 1.0.0 →
20 at 1.1.0 → 24 at 1.5.0 → 25 at 1.6.0, all under the unchanged 1.x machine contract.

## What's experimental / research-only

These live on `main` as source only — excluded from the wheel/sdist, no supported `smartchem.*`
import path, no API guarantee:

- **2.0-alpha: NOT MET.** The only measured aqueous holdout is Guidone et al. 2025 (*RSC Adv.* 15,
  38762), labelled **tier-W / CORROBORATED-weak**. Because pCO₂ is unmeasured (and replicates are
  unstated), it **does not qualify** the 2.0-alpha empirical gate. See
  [docs/research/OPERATION_XXV_HANDOFF.md](docs/research/OPERATION_XXV_HANDOFF.md).
- **Spatial 3.0** — a reactive-transport research prototype under
  [`experiments/sandbox_foundation/`](experiments/sandbox_foundation); **not accepted**.
- **Post-3.0 LibGibson synthesis explorer** — PLANNED, docs-only
  ([POST_3_0_LIBGIBSON_SYNTHESIS_EXPLORER_ROADMAP.md](docs/research/POST_3_0_LIBGIBSON_SYNTHESIS_EXPLORER_ROADMAP.md)).
- **1.7.0 dehydration (#116)** — DEFERRED, scientifically unqualified; branch unmerged. See
  [V1_7_DEHYDRATION_DEFER.md](docs/research/V1_7_DEHYDRATION_DEFER.md).

## Top blockers / open issues

- **#116** — 1.7.0 dehydration deferred (carbon-skeleton kill; branch kept unmerged).
- **#130** — configuration-aware route identity (unmarked stereocentres read as `configuration_complete`).
- **#168** — COT identity collision.
- **#165 / #166** — science provenance.
- **2.0-alpha empirical gate** — open; no qualified independent holdout yet (see tier-W above).

## Quickstart

```bash
# From a clone (editable, with dev extras):
python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
# core deps: numpy>=1.24, scipy>=1.10 · extras: dev (pytest,hypothesis), qc (pyscf), depiction (rdkit)
```

```bash
# Resolve an identity and plan from a name / formula / SMILES:
python -m smartchem plan 'smiles:CO'

# Compile a synthesis route under a bench profile and emit the stable JSON response:
python -m smartchem recompile 'smiles:CC(=O)OCCC(C)C' --capability-profile poor-man --json

# Descend a compound to its element/commodity buckets:
python -m smartchem decompile C8H9NO2
```

```bash
# OOM-safe full test suite (a bare `pytest` is OOM-killed on a small box):
scripts/run_suite.sh
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | success — routes found, or target already available |
| `2`  | invalid input (unparseable / ambiguous identity) |
| `3`  | complete search, **no** route (`NO_ROUTE_COMPLETE`) |
| `4`  | incomplete search (budget / depth truncated) |
| `5`  | refused at an identity / chemistry-model boundary (`REFUSED`) |
| `70` | internal error |
| `141`| `SIGPIPE` (e.g. output piped to `head`) — a shell condition, not a verdict |

## Architecture map

A human chemical identity goes in; a set of route candidates — each with a derived readiness ladder
and (optionally) a capability assessment against a declared bench — comes out as a versioned,
digest-bound dossier a consumer can re-verify without trusting the producer. The stages are
**front door → identity → search algebra → search + receipt → IR → capability assessment →
transport → verification**, each owning one authority, the digest it stamps, how it fails, and what
"complete" means there. Full stage-by-stage map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Extension points

- **New reaction recognizers** — add a recognizer to the reaction-type oracle
  (`smartchem/experiment/reaction_type_oracle.py`). Each must fire ONLY when the net
  functional-group change is identity-unique to its family, fail closed, and carry its own
  conservation lock; coverage may grow but a verdict word's meaning may not change (1.x freeze).
- **New domain compilers** — the categorical core (SMC backbone, functorial physics, free-category
  providers, domain functors) is built so a new domain earns its call sites; it must reach beyond
  chemistry-only (electrons, circuits, radiation — the EM bridge is `smartchem/electrochemistry.py`).

## Detailed records

- [docs/research/OPERATION_XXV_HANDOFF.md](docs/research/OPERATION_XXV_HANDOFF.md) — the current research handoff (2.0-alpha status, tier-W holdout, open controls).
- [docs/research/V1_7_DEHYDRATION_DEFER.md](docs/research/V1_7_DEHYDRATION_DEFER.md) — why 1.7.0 dehydration is deferred.
- [docs/research/POST_3_0_LIBGIBSON_SYNTHESIS_EXPLORER_ROADMAP.md](docs/research/POST_3_0_LIBGIBSON_SYNTHESIS_EXPLORER_ROADMAP.md) — the planned post-3.0 explorer.
- [ROADMAP.md](ROADMAP.md) — ranked next steps (see the **QUEUE** section).
- [CHANGELOG.md](CHANGELOG.md) · [COMPATIBILITY.md](COMPATIBILITY.md) — what changed, and what the 1.x contract guarantees.
