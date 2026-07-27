# Manufactured water-background compatibility result — 2026-07-27

## Verdict

`COMPLETE` as an approved source-to-certificate **finite-section compatibility
preflight**:

```text
FINITE_SAMPLE_COMPATIBILITY_AND_UNCERTAINTY_RESOLVED_BRACKET
ClaimScope = ANALOGUE
EvidenceStatus = STRUCTURAL_TOY
```

The two supplied manufactured sections have equal nominal discharge and lossless Bernoulli
head, pass the declared shallow-water and gravity/capillarity screens, and bracket the
counter-current characteristic with separated input-uncertainty intervals. The nominal
linear locator is `3.333333333333333 m`; without a continuous background model the retained
position interval is the entire uncertain adjacent support, `[-0.01, 10.01] m`.
The two position-uncertainty intervals are strictly ordered; overlapping or touching
position intervals receive `POSITION_ORDER_AMBIGUOUS` rather than the strongest status.

This is not a continuous stationary solution, a steady momentum/regularity check, a measured
flume validation, or a physical horizon location.

## Exact manufactured screen

The approved reduced equations were:

```text
q = b h U
H = z_b + h + U^2 / (2 g)
lambda_counter = U - sign(U) sqrt(g h)
kh = 2 pi h / wavelength_min
Bo_h = rho g h^2 / sigma
```

With `g = 9.81 m/s^2`, `rho = 1000 kg/m^3`, `sigma = 0.072 N/m`,
`h = 1 m`, and declared wavelength support `[100, 200] m`, both sections give:

| Quantity | Section 0 | Section 1 | Gate |
|---|---:|---:|---|
| `q` | `6.26418390534633 m^3/s` | `6.26418390534633 m^3/s` | pass |
| `H` | `1.125 m` | `1.125 m` | pass |
| `kh` at 100 m | `0.06283185307179587` | same | `<= 0.1`, pass |
| depth Bond number | `136250` | same | `>= 1`, pass |
| counter-current characteristic | `-1.5660459763365826 m/s` | `3.132091952673165 m/s` | nominal bracket |
| characteristic interval | `[-1.583866442824181, -1.5482059341213434]` | `[3.114271486185567, 3.149931994888404]` | separated, pass |

The runtime independently recomputed the full diagnostic and retained all four requested
observables:

1. `water_background_validation`;
2. `water_background_sample_diagnostics`;
3. `water_background_crossing_brackets`;
4. `water_background_regime_inventory`.

No point, uncertainty, residual, gate, bracket, failure state, or certificate casualty was
downsampled or omitted.

## What the screen does not establish

Equal sectionwise `q` and Bernoulli head are only a nominal compatibility screen. The
certificate explicitly records that it does not check:

- the steady Saint-Venant momentum residual or a friction/energy-loss model;
- a continuous bathymetry, width, depth, velocity, or free-surface field between sections;
- hydrostatic/depth-averaged/rectangular-section applicability or a non-unit energy
  coefficient;
- hydraulic jumps or transcritical critical-control regularity;
- uncertainty propagation through the discharge and head gates;
- measured provenance, calibration, spatial convergence, or held-out validation;
- dispersive roots, scattering, quantum state, thermal spectrum, or literal gravity.

The v1 diagnostic was also corrected in this cycle: absence of an adjacent sign bracket is
now `NO_BRACKET_IN_SUPPLIED_SAMPLES`, not a continuous-profile no-horizon claim.

## Run and lineage

| Record | Value |
|---|---|
| status | `COMPLETE` |
| run ID | `fc88ab40b04341348c66d3915e4c936b` |
| started | `2026-07-27T11:29:29.224246+00:00` |
| updated | `2026-07-27T11:29:29.299853+00:00` |
| source digest | `c408c227f4a7518dba786467767ad13f5354098ce7dd856b4b163b3b99e542b2` |
| resolved-program digest | `00f650cb0d6fb7585ad9eb5d6fdd1cfb927350bda673764f0b1327f1e435031a` |
| Physical IR digest | `dff21246f9faf7d7edc6251ea90cff64ecc7fe1476016312daf4ca63e35c307d` |
| request digest | `a1ce7b05c50b339ad22c00aa3016557e4f65be3616a4543b4a58e36ba7f6219f` |
| plan digest | `67ccbb4296ee341f69a4d05fcf53d9b21a7be9b0f62d7ca157cd5be97bc7be75` |
| approval digest | `665195cc3387272d7dc0872fc4eb395408acddf25972668d8d5d96edc6ab259e` |
| calculation digest | `f937a0c8df83f1896772948f7961a6af30d40e395754ac1d01bc671e911f6821` |
| engine implementation digest | `ab5608a83bc252fc44a11a76af4729dcf580b9563482c3c999ccffd18e560fa2` |
| compiler implementation digest | `d417f4c2c4f9e3209e9f138561c10bbeaa764ea5f62d12f876b5f74bc3bf04b3` |
| diagnostic observable digest | `6bc7fd0577b856a0d21ab87c2071e20a0c3bfb7c9cd10ac38ec483c717129e63` |
| sample observable digest | `5373499321cc4f698e9fefa1f979d73065c61dfaa67f5755a2f13b34fbf8a5e1` |
| crossing observable digest | `7989848f7f26ca7cb306723df08d20a40145178b077efeccc9e759c3a459ba19` |
| regime observable digest | `77408fa8378438fb6b4ebe736a7e166036dbc868990990e4630c9225b1fe4a1f` |
| certificate artifact digest | `212ced888c5ae487d4fee4cd2f79deeb528913173847c31d2e5e41d28ad88c10` |

All four required obligations passed. One complete diagnostic checkpoint and all observable
payloads were retained in the ignored, write-once journal.

## Verification

The focused runtime/domain/registry compatibility gate passed `156` tests. The final suite
passed `1213` tests with `14` skipped and `1` expected failure. An independent arithmetic
check recomputed discharge, head, `kh`, Bond number, and the nominal bracket locator.
Directed regressions cover negative-flow sign conventions, branch and
orientation typing, uncertainty-ambiguous nominal brackets, forged nested results, exact
output inventory, resources, calculation mutation, scope tampering, and public CLI summary.
