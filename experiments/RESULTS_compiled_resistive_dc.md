# Independently verified finite resistive-DC bridge receipt

**Run date:** 2026-07-28 (America/New_York)
**Lifecycle status:** `COMPLETE`
**Claim/evidence/lane:** `LITERAL / VALIDATED_WITHIN_REGIME / CERTIFIED`

This claim is literal only for the declared finite ideal-resistor equations and the
retained binary64 sparse-MNA witness. It is not evidence about a physical device,
component tolerances, layout, grounding, safety, AC/RLC behaviour, transients, resonance,
thermal effects, radiation, active/nonlinear elements, or arbitrary networks.

## Scientist-confirmed problem

The retained asymmetric bridge has ordered structural edges

| structural edge | resistance |
|---|---:|
| P-L | 100 ohm |
| L-N | 200 ohm |
| P-R | 300 ohm |
| R-N | 400 ohm |
| L-R | 500 ohm |

The model retains the explicit identity witness `model_index -> structural_edge_index`
for indices `0..4`. A separate finite control also exercises a non-identity witness; model
tuple order is therefore not silently treated as topology identity.

Boundary P is held at exact `+10 V` relative to output/reference N. Resistances and drive
voltage are exact rationals. The topology has four retained nodes and five retained
branches. The exact canonical observer and its direct content check used budget `100000`.

## Complete retained outputs

The frozen output contract emitted exactly four typed payloads:

1. the structural/decorated canonical forms, explicit edge-binding witness, exact
   relation, and sparse result in one `ResistiveDCAnalysis`;
2. the complete exact `BoundaryLinearRelation`;
3. every node, branch, source, and production diagnostic in the `DCSolveResult`;
4. the complete production-independent `DirectVerificationReport`.

No scalar equivalent resistance replaced these outputs.

Boundary variables are ordered

```text
(V_input, V_output, I_inward_input, I_inward_output).
```

The exact rational RREF is

```text
V_input - V_output + (7750/37) I_inward_output = 0
I_inward_input + I_inward_output = 0
```

Thus this particular bridge has the derived two-terminal resistance `7750/37 ohm`, and
the declared drive produces passive-network current `37/775 A`. This scalar consequence
is not the semantic object of a general open diagram.

## Sparse-MNA witness

| node | voltage |
|---|---:|
| P | 10 V |
| L | 6.580645161290322 V |
| R | 5.935483870967741 V |
| N | 0 V |

| branch | current in declared structural-edge direction |
|---|---:|
| P to L | 0.03419354838709678 A |
| L to N | 0.03290322580645161 A |
| P to R | 0.013548387096774197 A |
| R to N | 0.014838709677419354 A |
| L to R | 0.001290322580645162 A |

The ideal source current entering its positive terminal is
`-0.047741935483870984 A`; its absorbed power is
`-0.47741935483870984 W`. Every retained positive resistor has nonnegative absorbed
power, and their total dissipation balances the source to the residual below.

## Independent verification

`smartchem/resistive_dc_verifier.py` imports neither the production circuit module nor
the compiled executor. It independently:

- applies the explicit model-to-structural-edge witness;
- checks the presentation digest and every retained inventory;
- validates exact structural and decorated canonical output content;
- performs verifier-local exact `Fraction` elimination for the boundary relation;
- recomputes every branch voltage, current, and power;
- recomputes nodewise KCL, source voltage/power, passivity, and global power;
- recomputes all eight dimension-separated diagnostics and requires the retained
  production diagnostics to match exactly.

The retained decision was `pass`, with all named gates true:

| direct gate | result |
|---|---|
| canonical forms | pass |
| inventory and edge binding | pass |
| exact relation | pass |
| branch law | pass |
| KCL | pass |
| source constraint | pass |
| power balance | pass |
| passivity | pass |

The direct residuals were:

| gate | raw residual | scaled residual |
|---|---:|---:|
| KCL | `2.0816681711721685e-17 A` | `4.360250899076838e-16` |
| source constraint | `0 V` | `0` |
| source-inclusive power | `1.6653345369377348e-16 W` | `3.4882007192614703e-16` |
| exact boundary relation | `3.552713678800501e-15` | `1.77635683940025e-16` |

All are far below the approved `1e-9` scaled tolerance and its stricter verifier
certification margin.

## Hostile and holdout controls

The maintained controls include single, series, parallel, cycle, and asymmetric
five-edge bridge networks through the same sparse stamping path; exact analytic values;
floating/reference, singular/rank, underflow/overflow, non-finite, and residual refusal;
and 64 deterministic connected multigraph holdouts at seed `20260727`.

The direct verifier remains functional after production analysis, relation, row-reduction,
assembly, and solver helpers are replaced with functions that raise. It rejects forged
node, branch, source, power, resistance, relation, canonical-form, diagnostic, inventory,
edge-binding, and presentation-binding records, including dynamically created same-module/
same-name dataclass impostors. A pre-backend admission snapshot also rejects mutation of
the approved plan, resolved subject, output contract, calculation identity, or compiler
identity after every backend callback and before certification—even when a callback mutates
then raises. Runtime attacks require `INVALID`, no result or certificate, and quarantined
artifacts/checkpoints. A coherent production forgery uses an 11 V result plus a false
relation against the approved 10 V subject; the untouched direct verifier rejects it.

These are finite controls, not a universal proof or a conditioning guarantee for arbitrary
networks.

## Durable identities

| Artifact | SHA-256 / ID |
|---|---|
| run | `253854ae0cb443f4abab86d0d009e90a` |
| source | `1208ff88538ed81b17b968f75ed788b152454d2338873db471ce12645c1dd668` |
| shepherd session | `907c570e6136649da7bf38a16c4aca2a74d742c592ad9526d300ea6bdc12a995` |
| resolved program | `5133abb8f1a934fc9a649a97c6ebc0b1743bc596ba216ec7659657a4b08d4553` |
| Physical IR | `e1c7858fc412c02312b3777fabd3ab01ea76c052482ddccddeeb53f426fd335c` |
| request | `1d3386a69235763c61e00688a35fa91fccea6e78b7c600b209bfe3fe9bff72b6` |
| output contract | `fb7a609d2b494373afc2d3565ed4605439b3c8c9a7d2c04563b4fee55e81f6f1` |
| subject | `af51f2d9d2c2f8062bf6db6f1988d76edef98f38140f1163456265328ce8a2dc` |
| resistor model | `7685865e2bb2de9f32c8a6d5f78e3755d2a2eca7fcf5c6629fa53e0f7f6573c0` |
| experiment | `4e2a4a02b642fad02bf08b5b9ed691e4e650bc730fb00e2b5cc94e1c232c272f` |
| plan | `7c2fa026878041ed197e70fadcc0f2a7965177b563ea2d8e9048ae2dd05ff90a` |
| approval | `90d93f55cbb47142f1e5d0682e059572f3ea033513365bc00a38b3c6a6bc3d22` |
| calculation | `c0ca129aa149869d244e1af08e8e39c101674514c29b8ab2920b4da84deb64d2` |
| compiler/runtime implementation | `9b265acd7051d1e174f5b41c05c85fd0602bc71cf2f3fc457367eb7c9f0c1512` |
| structural canonical form | `7169c7094c1b32123d4bed2ec3e25e8db574c9b33b6afb806af87a2bf8087230` |
| decorated model canonical form | `d5940d77b6e0a6cece70785660457f74b6b325f19cb03bc4b6c2ee581c3c6140` |
| exact boundary relation | `5498701fcf6fbc359550dde4a83100e8ca4d7e59a56152d8d7b1334bc73eaa02` |
| sparse-MNA solution | `e6194b516618090b1901b93cd385c8a18abe026db617a39b429dc00f27b1a708` |
| direct-verification report | `e2636d5ebfdd33e1f75ab88261c344fdaca0fdc117af220dd085e0b1925307d1` |
| complete analysis/checkpoint | `1d21c7dc0f2bb5325e02ff8a9fd707914e0ee433e4136cdbeb6c0bc444c28854` |
| certificate | `c81048bc1ee52fa5b78eba5f9494b12ff99a2e10ee9c1be288c5aea7c8cd5e75` |

The write-once local journal is
`/tmp/smartchem-e1-release.EidAwH/run.json`. It ran from
`2026-07-28T04:46:12.553364+00:00` to
`2026-07-28T04:46:12.655526+00:00`. The ignored journal is the local raw record; this
receipt and `compiled_resistive_dc.py` are the durable reproducible artifacts.

The older remote `fdb906f` receipt is not authority: that attempt reused production
analysis in its completion check. This run was planned and executed anew after the
separate direct verifier and forced common-mode gates existed.

## Verification boundary

Focused, full-suite, compiler-digest, registry-digest, and local release gates are
recorded in `RESEARCH_ROUND_RESISTIVE_DC_2026-07-27.md`. This receipt establishes only
the scoped run above. E2 positive-frequency AC/RLC remains unbuilt, and port-Hamiltonian
semantics require an explicit dynamic state and proved effort/flow power pairing.
