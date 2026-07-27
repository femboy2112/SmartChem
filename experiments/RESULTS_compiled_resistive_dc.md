# Exact resistor relation and sparse-MNA bridge — open-semantics receipt

**Run date:** 2026-07-27
**Lifecycle status:** `COMPLETE`
**Claim/evidence/lane:** `LITERAL / VALIDATED_WITHIN_REGIME / CERTIFIED`

This is literal only for the declared finite ideal mathematical circuit and its retained
binary64 numerical witness. It is not evidence about a physical device, resistor
tolerances, wiring practice, safety, AC/RLC behavior, transients, resonance, thermal
effects, radiation, active/nonlinear components, or arbitrary networks.

## Scientist-confirmed problem

The retained asymmetric bridge has ordered edges:

| edge | resistance |
|---|---:|
| P–L | 100 Ω |
| L–N | 200 Ω |
| P–R | 300 Ω |
| R–N | 400 Ω |
| L–R | 500 Ω |

The input boundary P is held at `+10 V` relative to output/reference N. Resistances and
drive voltage are exact rationals. The topology has four retained nodes and five retained
branches. The exact canonical observer used a declared candidate budget of `100000`.

## Exact boundary semantics

Boundary variables are ordered

```text
(V_input, V_output, I_inward_input, I_inward_output).
```

The exact rational RREF is:

```text
V_input - V_output + (7750/37) I_inward_output = 0
I_inward_input + I_inward_output = 0
```

Thus the exact two-terminal resistance of this particular bridge is `7750/37 Ω`; under
the declared drive the passive network current is `37/775 A` inward at P and outward at N.
This scalar is a derived observation of the full boundary relation, not the semantic
replacement for arbitrary open diagrams.

## Sparse-MNA witness

| node | voltage |
|---|---:|
| P | 10.000000000000000 V |
| L | 6.580645161290322 V (`204/31` exactly in the rational control) |
| R | 5.935483870967741 V (`184/31` exactly in the rational control) |
| N | 0 V |

| branch | current in declared edge direction |
|---|---:|
| P→L | 0.03419354838709678 A |
| L→N | 0.03290322580645161 A |
| P→R | 0.01354838709677420 A |
| R→N | 0.01483870967741935 A |
| L→R | 0.001290322580645162 A (`1/775` exactly) |

The ideal source current entering its positive terminal is
`-0.047741935483870984 A` (`-37/775 A` in the exact control). Its absorbed power is
`-0.47741935483870984 W`; total resistor dissipation is the opposite value to floating
precision.

The retained diagnostics were:

| gate | raw residual | scaled residual |
|---|---:|---:|
| KCL | `6.938893903907228e-18 A` | `1.453416966358946e-16` |
| source constraint | `0 V` | `0` |
| source-inclusive power | `1.6653345369377348e-16 W` | `3.4882007192614703e-16` |
| exact boundary relation | `3.552713678800501e-15` | `1.77635683940025e-16` |

Every resistor retained nonnegative absorbed power. All six required obligations passed:
exact subject/model binding, narrow literal scope, canonical-observer budget, separate
deterministic recomputation, residual/passivity gates, and exact three-output inventory.

## Compositional and hostile controls

The maintained tests establish, on named and finite generated controls:

- total presentation `then`/`tensor` even when exact canonical observation later refuses
  its resource budget;
- identity, associativity, tensor/interchange, braid naturality/involution, and both
  symmetric hexagons after successful exact observation;
- alpha/declaration-order invariance, parallel multiplicity, and self-loop retention;
- exact relation composition by shared potential and cancelling inward currents;
- the bridge as an explicit `1→2→1` composition;
- parallel wiring as splitter → resistor tensor → merger rather than scalar tensor;
- one stamping path for single, series, parallel, cycle, and bridge networks;
- exact-rational/signed-voltage grids checked against sparse numerical points;
- floating exact relations remaining valid while a grounded unique solve refuses;
- rank, non-finite, underflow/overflow, solver mutation, result mutation, output mutation,
  model misbinding, direct-runner bypass, and resource-cap failures closing safely.

These controls are not a universal mathematical proof. The canonical observer is exact
when it succeeds but resource-bounded, and the resistor model currently binds an
order-sensitive presentation digest rather than automatically transporting across an
alpha-isomorphism.

## Durable identities

| Artifact | SHA-256 / ID |
|---|---|
| run | `4ae82cdc60464cc7be231ba2015bdfa1` |
| source | `1208ff88538ed81b17b968f75ed788b152454d2338873db471ce12645c1dd668` |
| shepherd session | `2c605b2379e345608e2a56206b1979c90eaebab5bd02b0b1327100fb75a56717` |
| resolved program | `3c5252046fa561a44e4ce47ab76d4928acc05e7ca24561bfbe48fdbaf58c47de` |
| Physical IR | `50c01aee740312c78c0ccb943ec0273c6791547d20780e5bc45393278d31f514` |
| request | `d985b17408162a695d9b8a31f7330ff1026645ba2d4995ad83f0805752507554` |
| output contract | `6ddb0ab47e882c724f18ff02a4db66d6c4ad5da4489e51bb390918e23853c5cf` |
| subject | `76cdf14ab8c3fb496bb0ebe985ddcdb146f2c7fdf43df1d00f12a14643a576a8` |
| resistor model | `b9aae069b59ce6f20ff032a7d6f703ae72b654dc1f41cacfaae4fd6b63d26b0c` |
| experiment | `0cb167ac47b03555a724dbee20865195b3ce7dd7678e81dd91bc1e46b7cba2cd` |
| plan | `ab0bfbb113c894e2f8ff1ec44ebde7d12412a46ab965ec1c9bfc5ecf75dbc6c4` |
| approval | `3a1a1bb696056494b737442f6f15177b65c466445a2b0d3113c7e391ad75a85d` |
| calculation | `f126d963db2a6a088fdd9d2dfbffe17c02ee8dd7675d02d013f16fe10b13fa36` |
| compiler/runtime implementation | `e0a90f5f3e18939184176e8971f475efa89fcadf9930225d796c206016ead505` |
| structural canonical form | `7169c7094c1b32123d4bed2ec3e25e8db574c9b33b6afb806af87a2bf8087230` |
| decorated model canonical form | `d5940d77b6e0a6cece70785660457f74b6b325f19cb03bc4b6c2ee581c3c6140` |
| exact boundary relation | `962a9aabc67802e706ef338244114f83af58d826cc63a41fb6ccac0bbfef54bb` |
| sparse-MNA solution | `249bd1375c8ebc990155d48dab4d842c35b6a6555989f07f4c078e18dfd88a2a` |
| complete analysis/checkpoint | `8515ee66d51692d7ed1e948192a05e34d84e125b3bb53cff82bda5597390cee5` |
| certificate | `f164106cc8850ec285e8cbe304aacd9b4bd956cb82e86870193934d166c2cc95` |

The write-once local journal is
`/tmp/smartchem-resistive-dc-final.redHXx/run.json`. It ran from
`2026-07-27T17:13:58.954006+00:00` to
`2026-07-27T17:13:59.022606+00:00`. Local JSON journals are ignored; this receipt and the
deterministic harness are committed.

Earlier terminal development runs are recorded in
`RESEARCH_ROUND_OPEN_SEMANTICS_2026-07-27.md` and were not reused as this result.

## Verification

- focused structure/circuit/runtime/registry/P0 gate: `90 passed`;
- both maintained full-suite entrypoints:
  `1328 passed, 51 skipped, 1 xfailed`;
- skips are the existing absent-PySCF and explicit slow-test groups, not passes;
- adversarial category/semantic/runtime review: `SHIP`;
- `python -m compileall -q smartchem experiments tests`: passed;
- `git diff --check`: passed.

## Next boundary

The next electrical rung is positive-frequency passive AC/RLC with complex power,
positive-real/passivity checks, damped resonance, and explicit singular lossless-resonance
refusal. A port-Hamiltonian claim remains later: it requires explicit dynamic state,
Hamiltonian, typed effort/flow ports, and a proved power-conserving interconnection.
