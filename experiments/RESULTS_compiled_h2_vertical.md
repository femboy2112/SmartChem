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
| Run ID | `538d32e77f634e1ba5f7d836cca7ee81` |
| Started/updated | `2026-07-27T05:41:48.016479+00:00` / `2026-07-27T05:41:48.448440+00:00` |
| Backend | `CCSD(T)/cc-pVTZ` |
| Source digest | `cf521bb5ed5abdd024394a323083a4ce5bd449c029dfe894200540e16d915eaf` |
| Shepherd-session digest | `6c10a0f62fae2f5bfce4b797424f77271a721f84414458c0ca5b717542124d34` |
| Request digest | `cd75ee1d2dfb4f1563bbf0943aaf189bdcc85daac649a86a3d37469c1ad4d540` |
| Plan digest | `5b57ec5e1d89e972db6f496293559a0ea720d96c2f607e26f8571fb2e6302f87` |
| Approval digest | `14b84e670975394591430a6520ced413cebdf9dcc922e64544ed4e26db7ad9e3` |
| Calculation digest | `c17412a3c7e9391b2a046e1c98d6f05e834241a37a796978083b0a6d245dd9a0` |
| Oracle implementation digest | `e4a560ee1b6320debdf8b994003b2af17861c67353f92d79458196e0270dd94e` |
| Compiler/runtime implementation digest | `dfb849a140cf3e98291b3acdc1a2d174c94d4b3f43ac5c2e108638f38bd07c19` |
| Certificate artifact content digest | `9d1359d42b2644dbc7be802376049d421770207b11f2c4664dea40573b83b4b0` |
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
| H intermediate | `c6682a67e0424fd87e56c6765922747b8d498c1886bbb3924685afa128d190a3` | `-13.6005178249 eV`, reported scale `0 eV` |
| H2 intermediate | `0f5c1e5727c31b1f3fc2931d9a9115a59604897ca90ebecaeae978f91c67d7ea` | `-31.6280415484 eV`, reported scale `0.2186 eV` |
| `reaction_energy` observable | `7c97f46f81a42d8f77d58320535f15fd5f3eea7a88dc8b64ac81cf4d3c64cf0c` | `-4.42700589871 eV`, reported scale `0.2186 eV` |
| Certificate artifact | `9d1359d42b2644dbc7be802376049d421770207b11f2c4664dea40573b83b4b0` | complete |

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
1089 passed, 14 skipped, 1 xfailed in 21.09s

uv run --isolated --python 3.10 --extra dev python -m pytest -q -rs
1048 passed, 51 skipped, 1 xfailed in 21.16s

uv run --isolated --python 3.12 --extra dev python -m pytest -q -rs
1048 passed, 51 skipped, 1 xfailed in 17.93s

.venv/bin/python -m compileall -q smartchem tests experiments
git diff --check
passed
```

The local environment includes PySCF; its 14 skips require `--runslow` real-oracle
geometry/finding work and are not reported as passed. The Python 3.10/3.12 core matrix
deliberately lacks PySCF, so 37 additional backend-dependent tests skip there and remain
covered by the dedicated PySCF run. The xfail is the already-declared
true-parallel-interchange architecture debt. The real H2 run above is the scoped backend
smoke for this vertical; the fast full suite does not turn the unbuilt general compiler into
a validated capability.

## What completed, and what remains

Completed: the narrow contract seam, typed binding/obligation path, explicit approval, exact
output inventory, durable run state, in-progress/failure quarantine, and one existing-domain
chemistry execution. The recorded run is terminal; no H2 calculation remains in progress.

Still unbuilt: the canonical cross-domain pair, a general model-chain planner and optimizer,
the conversational surface, general state evolution/open-system semantics, and all broader
chemistry and multiphysics validation. See `ROADMAP_2026-07-27.md`.
