# Compiled H2 vertical — first approved source-to-certificate execution

## Scope and authority

This is the completed narrow instance of Direction Audit Milestones A and B and Milestone C's
first chemistry vertical. The direction audit's milestone order was originally a proposal; on
2026-07-27 the user explicitly directed this execution. That directive authorizes this exact
slice. It does not assert that the larger roadmap had been previously ratified, and it does not
promote the slice into a general simulation language.

The source was the closed reaction `2 H -> H2`, requested as a 0 K endpoint `delta-E` under the
existing fixed-geometry `CCSD(T)/cc-pVTZ` protocol. It ran through the immutable source,
request, candidate plan, approval, approved-plan capability, tracked execution, obligations,
result, and certificate path.

## Durable run receipt

The raw RunRecord journal was `experiments/compiled_h2_run.json` at execution time. It is an
ignored, atomically updated run artifact. The values below are a durable transcription of the
final `COMPLETE` run against the exact compiler/runtime source prepared for this change, so the
result remains auditable if a later local run replaces the ignored journal.

| Field | Value |
|---|---|
| Status | `COMPLETE` |
| Run ID | `d3f775f8f4ae41f993e1d5619761ead1` |
| Started/updated | `2026-07-27T05:33:49.091426+00:00` / `2026-07-27T05:33:49.435209+00:00` |
| Backend | `CCSD(T)/cc-pVTZ` |
| Source digest | `cf521bb5ed5abdd024394a323083a4ce5bd449c029dfe894200540e16d915eaf` |
| Shepherd-session digest | `6c10a0f62fae2f5bfce4b797424f77271a721f84414458c0ca5b717542124d34` |
| Request digest | `cd75ee1d2dfb4f1563bbf0943aaf189bdcc85daac649a86a3d37469c1ad4d540` |
| Plan digest | `970a12b132be61d309d04082befefe7a4c5c369afd97c1aa923a33e932a1f9fb` |
| Approval digest | `84e1efdf625e833d833934bb0f5b8224a0f9dc12c3a759de752cd27491057024` |
| Calculation digest | `c17412a3c7e9391b2a046e1c98d6f05e834241a37a796978083b0a6d245dd9a0` |
| Oracle implementation digest | `e4a560ee1b6320debdf8b994003b2af17861c67353f92d79458196e0270dd94e` |
| Compiler/runtime implementation digest | `328ece62866984f28df0f787f662cf24ed6acdb8dfd25eae7846e36e9e7cea8b` |
| Certificate artifact content digest | `859612ad6d6f7119847627c1b6a28859200c86a84b31989441231cabd9ec9b3f` |
| Cache state | `in-memory canonical cache: hits=2, misses=2, distinct_species=2` |
| Diagnostics/failures | none / none |

The journal records four distinct passing obligations: reaction conservation,
domain/reference diagnosis, an `Estimate` returned by the oracle, and exact
output-inventory coverage (`reaction_energy`). The approved executor can emit only that named
observable; unsupported additions are blocked before an oracle call.

## Result and comparison

The completed observable was:

```text
reaction_energy = -4.427005898711 eV
reported scale  =  0.2186 eV
```

The repository's H2 reference is a positive dissociation energy, `D0 = 4.478 eV`
(`smartchem/data/reference.py`, `BondRef("H2", ...)`). Comparing magnitudes only,
`abs(abs(delta-E) - D0) = 0.050994 eV`.

That is a one-run diagnostic comparison. It is **not** a new calibration, a mean absolute
error, an uncertainty bound, a statement that the reported 0.2186 eV scale covers this
difference, or a replacement for the repository's named benchmark population. It also does
not turn endpoint `delta-E` into Gibbs free energy, spontaneity, kinetics, mechanism evidence,
or expanded chemistry coverage.

## Artifact digests

| Artifact | Content digest | Detail |
|---|---|---|
| H intermediate | `9170211fdfd5cccaf5ba0ace1c14ea0032cbbc63599b8c529ad50d97d1515455` | `-13.6005178249 eV`, reported scale `0 eV` |
| H2 intermediate | `c4629f41abd1f49c8fc3d03722a5f117a204f313f59248a591ec5711954604af` | `-31.6280415484 eV`, reported scale `0.2186 eV` |
| `reaction_energy` observable | `0dfcf43fee15d9b9cd710538df51c85ddee18a3f98444229ae1783c9dfc9a842` | `-4.42700589871 eV`, reported scale `0.2186 eV` |
| Certificate artifact | `859612ad6d6f7119847627c1b6a28859200c86a84b31989441231cabd9ec9b3f` | complete |

The two intermediate content digests also appear as complete, non-quarantined checkpoints in
the journal. The journal serializes the complete source, candidate-plan (including the request
and calculation specification), approval, `Estimate` payloads, and certificate. The request
digest is taken from that serialized certificate, which binds it to the source, plan,
approval, calculation, compiler implementation, run, validity outcomes, output inventory, and
casualty list.

## Verification

```text
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python experiments/compiled_h2_vertical.py \
  --journal experiments/compiled_h2_run.json
COMPLETE

.venv/bin/python -m pytest -q -rs
1089 passed, 14 skipped, 1 xfailed in 22.23s

.venv/bin/python -m compileall -q smartchem tests experiments
git diff --check
passed
```

The 14 skips require `--runslow` real-oracle geometry/finding work and are not reported as
passed. The xfail is the already-declared true-parallel-interchange architecture debt. The
real H2 run above is the scoped backend smoke for this vertical; the fast full suite does not
turn the unbuilt general compiler into a validated capability.

## What completed, and what remains

Completed: the narrow contract seam, typed binding/obligation path, explicit approval, exact
output inventory, durable run state, in-progress/failure quarantine, and one existing-domain
chemistry execution. The recorded run is terminal; no H2 calculation remains in progress.

Still unbuilt: the canonical cross-domain pair, a general model-chain planner and optimizer,
the conversational surface, general state evolution/open-system semantics, and all broader
chemistry and multiphysics validation. See `ROADMAP_2026-07-27.md`.
