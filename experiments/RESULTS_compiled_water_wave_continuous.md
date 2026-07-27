# Manufactured continuous steady-water control — 2026-07-27

**Lifecycle:** `COMPLETE`
**Claim/evidence/lane:** `ANALOGUE / STRUCTURAL_TOY / EXPERIMENTAL`

## Verdict

SmartChem completed the approved regular-transcritical manufactured control on
`32/64/128` finite-volume cells. The runtime retained every requested field, residual,
refinement result, critical-compatibility result, uncertainty record, and finite-v2
comparison. All six lifecycle obligations passed.

The implemented steady equations are

```text
q = b h U
H = z_b + h + U^2 / (2 g)
Fr^2 = U^2 / (g h)
(1 - Fr^2) h' = S0 - Sf
```

At the declared isolated critical point, the code checks the removable regularity
condition `S0 = Sf` directly instead of dividing by `1 - Fr^2`.

This compiled run is finite manufactured numerical evidence for the declared
regular-transcritical family. Directed tests separately exercise all three closed
manufactured families. Neither is a general Saint-Venant solver, a continuum convergence
theorem, measured-flume validation, or authority for dispersive, turbulent, breaking,
two-dimensional, quantum, or literal gravity claims.

## Reconstruction and refinement

The engine reconstructs depth from the finite-volume energy equation with a bounded,
regime-aware bisection root. The branch is selected from the declared
subcritical/supercritical/regular-transcritical family, not copied from the analytic
depth. Per-cell root iterations and residuals are retained.

| Quantity | 32 cells | 64 cells | 128 cells |
|---|---:|---:|---:|
| depth L2 error | `3.41113872686102e-4` | `1.679749609747297e-4` | `3.8190251227890805e-5` |
| momentum-residual L2 | `4.776148982585693e-5` | `2.336360179592856e-5` | `5.339013031681103e-6` |
| maximum momentum residual | `2.0317335828708648e-4` | `1.4526586649426452e-4` | `4.1946658660556483e-5` |
| maximum continuity residual | `2.220446049250313e-16` | `2.220446049250313e-16` | `2.220446049250313e-16` |
| maximum energy-root residual, m | `1.1102230246251565e-16` | `1.1102230246251565e-16` | `1.1102230246251565e-16` |
| root-iteration range | `80–80` | `80–80` | `80–80` |
| critical projections | `0` | `0` | `0` |

The conservative minimum order over **both** refinement pairs was
`1.0220072337077022` for depth reconstruction and `1.0315851382167684` for the
momentum residual. The preregistered gate was `>= 0.8` for every pair and both
quantities.

The declared critical point was `x = 4.3 m`; its compatibility residual was exactly
`0.0`. Directed controls also reject a flipped source sign (residual `-0.02`), omitted
friction, false regularity, measurement/calibration language in manufactured provenance,
and branch/model/result forgeries.

## Finite-v2 differential control

The attached finite-v2 subject is formed from nine explicitly retained points on the
finest mesh. It is evaluated by independent diagnostic code, but it is **not independent
input data or experimental validation**.

Finite v2 passed continuity, shallow-water, gravity/capillarity, uncertainty-bracket,
position-order, and orientation gates. Its lossless constant-head gate failed:

```text
FINITE_SAMPLE_BALANCE_INCOMPATIBLE
```

The continuous model passed because it includes declared friction. The attribution is
quantitative:

| Quantity | Value |
|---|---:|
| observed head range | `0.09921965023463053 m` |
| declared friction head drop | `0.09921875000000001 m` |
| maximum reconstruction head offset | `1.801707032789146e-6 m` |

Because the friction drop exceeds both the reconstruction offset and the v2 head
tolerance by more than the preregistered `10x` threshold, the retained relation is:

```text
FRICTION_DOMINATED_CONTINUOUS_PASS_LOSSLESS_FINITE_V2_HEAD_MISMATCH
```

A tiny-friction mutation does not receive that explanation; it is reported as
`FINITE_V2_HEAD_MISMATCH_CAUSE_NOT_ISOLATED`.

## Durable identities

| Record | Digest / ID |
|---|---|
| run | `d60a232aa9d74507bbc1127f38cc6315` |
| source | `e8a2a42bb1e20a1c64a9fc6c0ac60de0bd80765ecf3b1a8312cbda957446c1e8` |
| resolved program | `11b724e85ff0b1e46b723f54bab8b6fc5339f9c1de24e42746cc567a10b1743e` |
| Physical IR | `1f4898f71ec91398afc999d33dd284c778937be7a78d76991f95459bcc8c2272` |
| request | `df6cc6085894bc1a2ecb005b92acecb3da1f7f8df5d35ea1baa15cd0c62ae6d5` |
| plan | `fdfd71e645ce5ef51da31862e122d3a5b5d6b2fe03a84c61c6806ef4f2f055` |
| approval | `6ccb6667b91aca5b0a7d5d213a1714e744768b0580ebb5e8bdcba3c1f3498cdb` |
| calculation | `684b1e460541e4945c20be76187a3dd53018a39c7af811a6d810d8aebe781da2` |
| compiler/runtime implementation | `7f2efe663186f96c0524c9ea34c1532b6799fedb9ebaca4d29c800ce24ddfa0c` |
| continuous diagnostic/checkpoint | `c57ffa066c75c42b62c7e8bd658ae6a695acad76f7c7823ef6ef756a763b0f4c` |
| retained meshes | `f406c22de0b5ed7d35328bc84cc131f5e98c8e7a7b83ed69c9f36559bebdcfbf` |
| finite-v2 comparison | `0c9c9ce32e685147ad6b0057da432f6afc51ab0abbb35776d0a560691a612f26` |
| certificate | `fb3a9f604c82e133d1c1c08cf199405c70ebaaf5967b51ba6716c3374162c3ee` |

The write-once local journal is
`/tmp/smartchem-continuous-final.ujJhon/run.json`. It ran from
`2026-07-27T14:05:09.333912+00:00` to `2026-07-27T14:05:09.855206+00:00`.
The journal is intentionally not committed; this receipt and the deterministic harness
are.

## Verification

- both `.venv/bin/python -m pytest -q -rs` and `.venv/bin/pytest -q -rs`:
  `1279 passed, 51 skipped, 1 xfailed`;
- the 51 skips are explicitly PySCF-dependent or slow and are not represented as passes;
- `python -m smartchem.bench --split test --quiet`: completed with honest incomplete
  heuristic coverage (`6` evaluated, `5` refused);
- `python -m compileall -q smartchem experiments tests`: passed;
- `git diff --check`: passed;
- independent continuous-equation, solver, provenance, comparison, and runtime review:
  `SHIP`;
- independent P0 constructor/dispatch seam review: `SHIP`.
