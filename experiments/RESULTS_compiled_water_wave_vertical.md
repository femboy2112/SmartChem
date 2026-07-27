# Compiled water-wave structural acceptance result — 2026-07-27

## Verdict

`COMPLETE` as an approved source-to-certificate compiler/runtime calculation.

The numerical result is:

```text
KINEMATIC_CROSSING_IN_DECLARED_MODEL
x = 0.47613610288287683 m
orientation = BLACK
```

This is the linearly interpolated zero of the counter-current nondispersive characteristic
`U - sqrt(g h)` in a four-point **synthetic prescribed profile**. It is a
`ClaimScope = ANALOGUE` and `EvidenceStatus = STRUCTURAL_TOY` result. It is not a measured
flume horizon, a continuum free-surface simulation, a scattering calculation, a Hawking
temperature, quantum radiation, backreaction, literal gravity, or an astrophysical black
hole.

## Frozen request

The original underidentified phrase was:

> Simulate a black hole in water.

The typed scientist choice narrowed it to:

- target: `KINEMATIC_HORIZON`;
- regime: `NONDISPERSIVE_SHALLOW_WATER`;
- branch: `COUNTER_CURRENT`;
- requested orientation: `BLACK`;
- flow direction: positive x;
- gravity: `9.81 m/s^2`;
- a fixed four-point SI profile;
- explicit declarations of stationary, inviscid, irrotational, gravity-only, shallow,
  linear, one-dimensional, prescribed-background behavior with no retained wave forcing or
  reflections.

Those flags are declared model inputs, not evidence that the synthetic profile realizes a
physical flume. That distinction is why the result remains `STRUCTURAL_TOY`.

## Complete retained calculation

For every point the executor retained `x`, `h`, `U`, `c = sqrt(g h)`, the selected
characteristic, and `Fr = |U|/c`:

| x (m) | h (m) | U (m/s) | c (m/s) | U - c (m/s) | Fr |
|---:|---:|---:|---:|---:|---:|
| -1.0 | 0.1 | 0.4 | 0.9904544411531507 | -0.5904544411531507 | 0.4038550218769218 |
| 0.0 | 0.1 | 0.8 | 0.9904544411531507 | -0.1904544411531507 | 0.8077100437538436 |
| 1.0 | 0.1 | 1.2 | 0.9904544411531507 | +0.20954555884684922 | 1.2115650656307653 |
| 2.0 | 0.1 | 1.6 | 0.9904544411531507 | +0.6095455588468494 | 1.6154200875076872 |

The strict sign change lies between samples 1 and 2. Linear interpolation gives:

```text
c = sqrt(9.81 * 0.1) = 0.9904544411531507 m/s
x = 0 + (c - 0.8) / (1.2 - 0.8)
  = 0.47613610288287683 m
```

An independent receipt check reproduced that binary64 value exactly and confirmed that the
journal retained all 4/4 samples. This checks the declared algebra and implementation; it
does not quantify interpolation discrepancy or physical-model error.

## Exact output contract

Both requested observables were emitted; neither was downsampled or replaced:

1. `water_wave_horizon` — the typed full diagnostic, status, every crossing, orientation,
   and bracketing indices;
2. `water_wave_characteristic_profile` — every input and derived point in source order.

The current narrow executor refuses any change to observable membership, support, resolution,
precision, coverage, diagnostics, or retention until a different executor is implemented and
validated. A supported-looking observable ID cannot promise scattering or another semantic
payload that this executor does not produce.

## Certificate omissions

The certificate carries all six known missing-evidence items:

1. profile measurement and provenance are not represented or validated by this executor;
2. no wavelength or laboratory frequency establishes `kh << 1`;
3. capillarity and the gravity-dominance condition are not quantified;
4. stationary continuity and momentum balances are not checked;
5. measurement and spatial-resolution uncertainty are not available;
6. linear-interpolation discrepancy is not quantified.

These omissions prevent promotion beyond `STRUCTURAL_TOY`, regardless of convergence or a
successful crossing calculation.

## Certificate casualties

The result explicitly excludes:

- an astrophysical or literal black hole;
- Einstein dynamics or literal spacetime curvature;
- a singularity or event horizon for matter;
- spontaneous quantum Hawking radiation;
- a Hawking temperature or thermal spectrum;
- scattering coefficients or mode-conversion amplitudes;
- dispersive gravity-capillary branch horizons;
- black-hole-laser gain or instability;
- wave/mean-flow backreaction.

## Run and lineage

This table is an immutable transcription of run `988b7f3dc027424998f326ab863617aa`.
The ignored JSON journal is a mutable local path that a later independent run may replace;
this receipt does not claim to mirror such a later run.

| Record | Value |
|---|---|
| status | `COMPLETE` |
| started | `2026-07-27T06:20:45.197013+00:00` |
| updated | `2026-07-27T06:20:45.253404+00:00` |
| approval timestamp | `2026-07-27T06:20:45.193849+00:00` |
| source digest | `f75e2fb05db9a21121818e210a97e74315788b81866c009c34a8d83d459b6cf0` |
| shepherd session digest | `a435e2047ecd22a16273832869d92b07827de911418a028071e03e09db322b41` |
| resolved-program digest | `9e57ff0d18cadbc47dfe5b5ca2abbd342ad4ca63f48926c20ec037a6a4a8d344` |
| Physical IR digest | `3c3a708725b6f45131f603fd580b9f7150f4ff635d70d25e8f29bf9be8ba277b` |
| request digest | `5b358fc9417d76593a59bfc447e812c29c812add11227d39650bab61bac1ccb6` |
| plan digest | `68b7d8de26777c3e99dfd7a7397e2ff3bba19046770c7cab862e3a6e9e97363d` |
| approval digest | `1b26675e27036c742065ecc41702e292cf2e3baf3c93085736a9333390ce67bb` |
| calculation digest | `e50c46d4509f8cf39db8c326e800a4b3caf0e9e63905222978e8154ff0cbdb64` |
| engine implementation digest | `de3912bf98d28169074d95e90d231a453256b593c5bcccf7092998a40e7c4372` |
| compiler implementation digest | `cb37c3350ea4e53275c7418792fdf572a782c58d76f02b4357f74034e094e8b2` |
| horizon observable content digest | `20978070799e3318f70ebfff75f473823f91597c072d6d693f17f65af874aa9b` |
| profile observable content digest | `8f302dcbd8344b2da4a7efdeaff426e20957ed4460ebbb5d92b6d31fcb43c1d2` |
| certificate artifact content digest | `93c79d34c5481bf27de4a43f961fde6016c275765560f245545d77df8c5559ac` |
| retained checkpoints | `1` |
| retained artifacts | `6` |

The certificate is represented in the RunRecord by its artifact content digest; this table
does not imply a separate top-level `certificate_digest` field in the journal.

## Obligation results

All five distinct required obligations passed:

1. typed target/regime/branch/orientation/SI subject is supported;
2. exact structural-toy analogue referent and every casualty remain intact;
3. an independent recomputation equals the retained full diagnostic;
4. computed black/white orientation matches the scientist-approved semantics;
5. the emitted output inventory exactly equals the frozen output contract.

## Verification

Before the final journal was regenerated:

```text
.venv/bin/pytest -q \
  tests/test_water_wave_domain.py tests/test_water_wave_program.py \
  tests/test_program.py tests/test_typed_ledger.py tests/test_ledger.py
157 passed in 0.93s

.venv/bin/pytest -q -rs
1133 passed, 14 skipped, 1 xfailed in 22.32s
```

The 14 skips are explicit `--runslow` real-oracle/geometry cases. The xfail is the intentional
true-parallel-interchange architecture debt. The water calculation itself has no PySCF
dependency. Adversarial probes also confirmed that semantic output expansion, forged or
omitted crossings, an astrophysical referent under an `ANALOGUE` enum, changed engine
identity, executor/subject mismatch, approval-record mutation, and partial-resource results
all fail closed through the supported local API.

## Primary scientific boundary

The source vocabulary and casualty map are grounded in:

- [Schützhold and Unruh, *Gravity wave analogs of black holes* (2002)](https://arxiv.org/abs/gr-qc/0205099);
- [Rousseaux et al., *Horizon effects with surface waves on moving water* (2010)](https://arxiv.org/abs/1004.5546);
- [Euvé et al., *Scattering of co-current surface waves on an analogue black hole* (2020)](https://arxiv.org/abs/1806.05539).

Those papers establish the relevance and limits of water-wave analogue kinematics. They do
not validate this synthetic profile or promote this receipt beyond its declared structural
compiler acceptance scope.
