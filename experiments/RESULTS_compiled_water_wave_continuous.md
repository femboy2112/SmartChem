# Manufactured continuous steady-water control — 2026-07-27

**Lifecycle:** `COMPLETE`
**Claim/evidence/lane:** `ANALOGUE / STRUCTURAL_TOY / EXPERIMENTAL`

## Verdict

SmartChem completed the approved regular-transcritical manufactured control on
`32/64/128` cell-centred meshes. The runtime retained every requested field, residual,
binary64 rounding of the separately evaluated Decimal reference, refinement result,
both critical-compatibility residuals, uncertainty record, and finite-v2 comparison.
All six lifecycle obligations passed.

The implemented steady equations are

```text
q = b h U
H = z_b + h + U^2 / (2 g)
Fr^2 = U^2 / (g h)
(1 - Fr^2) h' = S0 - Sf
```

At the declared isolated critical point, the code checks both removable-regularity
conditions independently of the energy-root solver:

```text
N(x_c) = S0(x_c) - Sf(x_c) = 0
N'(x_c) = 3 h'(x_c)^2 / h_c
```

It never divides by `1 - Fr^2` at the critical point.

This compiled run is finite manufactured numerical evidence for the declared
regular-transcritical family. Directed tests separately exercise all three closed
manufactured families. Neither is a general Saint-Venant solver, a continuum convergence
theorem, measured-flume validation, or authority for dispersive, turbulent, breaking,
two-dimensional, quantum, or literal gravity claims.

## Bounded reconstruction and refinement

The engine performs a bounded, pointwise specific-energy reconstruction using
cell-edge bed averaging and a regime-aware bisection root. This is not a
finite-volume conservation solve. The branch is selected from the declared
subcritical/supercritical/regular-transcritical family, not copied from the analytic
depth. Per-cell root iterations and residuals are retained. Reference depths are
evaluated through a separate 60-digit Decimal path and retained as binary64 roundings;
the stored values are not represented as 60-digit numbers.

| Quantity | 32 cells | 64 cells | 128 cells |
|---|---:|---:|---:|
| depth L2 error | `3.4111387268610387e-4` | `1.6797496097472497e-4` | `3.819025122788959e-5` |
| maximum absolute depth error, m | `1.5475570440469655e-3` | `1.2250709094430712e-3` | `2.8032002795846944e-4` |
| momentum-residual L2 | `4.776148982585693e-5` | `2.336360179592856e-5` | `5.339013031681103e-6` |
| maximum momentum residual | `2.0317335828708648e-4` | `1.4526586649426452e-4` | `4.1946658660556483e-5` |
| maximum continuity residual | `2.220446049250313e-16` | `2.220446049250313e-16` | `2.220446049250313e-16` |
| maximum energy-root residual, m | `1.1102230246251565e-16` | `1.1102230246251565e-16` | `1.1102230246251565e-16` |
| root-iteration range | `80–80` | `80–80` | `80–80` |
| critical projections | `0` | `0` | `0` |

The conservative minimum order over **both** refinement pairs was
`1.0220072337077508` for depth reconstruction and `1.0315851382167684` for the
momentum residual. The preregistered gate was `>= 0.8` for every pair and both
quantities. Every retained mesh also passed the absolute gates:
continuity `<= 1e-12`, energy-root residual `<= 1e-10 m`, and maximum momentum
residual `<= 1e-3`.

The declared critical point was `x = 4.3 m`; its numerator residual was exactly
`0.0`, and its first-derivative compatibility residual was
`-2.5640297177109694e-14`. A mutation that preserves the numerator condition while
halving the required derivative is refused. Directed controls also reject a flipped
source sign, omitted friction, false regularity, measurement/calibration language in
manufactured provenance, wrong root branches, residual-threshold violations, and
model/result forgeries.

The input uncertainty record is retained but deliberately **not propagated** into
output bounds, regularity tolerances, or validation authority. This limitation is part
of the payload, omission inventory, direct verifier, and certificate.

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
| run | `9af118648f6c456a99390d2a77c93816` |
| source | `59da28acd223d6926ffcef62ea39dcdb7bb567f96868f5b12dac5ccd6d006fad` |
| resolved program | `e17b7d23da64e7034a2b79c02b765980dd6c837d10119e23e23f48f3af37ba8f` |
| Physical IR | `43445ca79f607bc2fb90dbf767a252f6421ee3fb224895defb33ada0e7ed7461` |
| request | `88378f86d6b1de7420adeeb2d4b147095bb284596d5286359c5fd543e137af6a` |
| plan | `fd21896268f7a1a8ee36784973eb76fcd555560f36edfb54cc5a77faade528c9` |
| approval | `a5dd6e2e1630a579d79c97cf7daf533795e8f9d4af8879021c59901793188f25` |
| calculation | `b0d9523c6035ec7b737185095bf16607f6ce7241b22e89e0c01738c7a00ddd0c` |
| compiler/runtime implementation | `d4fcf3619b64b2e4790541961f80366bfb4e26b9d7958d24e5243f523fd1c9c1` |
| continuous diagnostic/checkpoint | `c4488cc2bf03d2775ad4ed4865a1fa01b546adb8e2c656dac45b043fc34effc6` |
| retained meshes | `ac0e522ab6983a48a509470d6e124896bf073fdb27c217df8cf5b6dfeb262c7e` |
| finite-v2 comparison | `0c9c9ce32e685147ad6b0057da432f6afc51ab0abbb35776d0a560691a612f26` |
| certificate | `0e08909ff4cc31319ce606ab591b9de652ba4b90f712364d4a1b80cb2834ee28` |

The write-once local journal is
`/tmp/smartchem-continuous-authority2.FK4IFV/run.json`. It ran from
`2026-07-27T22:46:26.460250+00:00` to `2026-07-27T22:46:27.744625+00:00`.
The journal is intentionally not committed; this receipt and the deterministic harness
are.

## Verification

- both `.venv/bin/python -m pytest -q -rs` and `.venv/bin/pytest -q -rs`:
  `1329 passed, 14 skipped, 1 xfailed`;
- the 14 skips are explicitly slow and are not represented as passes;
- `python -m smartchem.bench --split test --oracle heuristic --quiet`: completed with
  honest incomplete heuristic coverage (`6` evaluated, `5` refused; conditional MAE
  `3.4950 eV`, no accuracy tier);
- `python -m compileall -q smartchem experiments tests`: passed;
- `git diff --check`: passed;
- independent continuous-equation, direct-verifier, provenance, comparison, and
  runtime review: `SHIP` after correcting the finite-volume and stored-precision claims;
- independent P0 constructor/dispatch seam review: `SHIP`.
