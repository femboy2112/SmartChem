# Closed runtime-registry migration — 2026-07-27

## Verdict

`PASS`. The three previously approved verticals were re-planned, re-approved, and executed
through the new closed executor registry. All returned `COMPLETE` with their exact default
output inventories. This is a runtime-regression receipt, not new chemistry, fluid, or
biological evidence.

The migration also closes two lifecycle defects:

- approval now binds every shipped `smartchem/**/*.py` source file plus `pyproject.toml`,
  rather than a hand-selected subset that omitted transitive chemistry semantics;
- a journal path is claimed with exclusive creation and remains owned by one run ID, so a
  second run cannot erase it.

The registry contains immutable lazy descriptors for exactly three executors. Unknown
executors, wrong resolved-container or subject types, modified output contracts, and changed
runner references fail closed. There is no runtime registration API.

## Regression calculations

| Vertical | Run ID | Plan digest | Certificate digest | Result |
|---|---|---|---|---|
| H2 endpoint energy | `b8a56f19cd7741c8ac4547ec029d9c40` | `dd519f0c8b1eac9f70f55f1c8b6cfad60bafb2b816b0aa2959b0c7b2ed85e6cb` | `e0adcbaf7813802dc21f8b2560c4c8faa5318ec44713e5efd919a90c9278c2b2` | `COMPLETE`, `-4.427005898711 ± 0.2186 eV` |
| Water-wave structural toy | `df1703521e6343108af72eaa85934655` | `2c4f7fa32616f7d124dc730863f997164e948ffa03aa37debdbff063f1ac4e15` | `438e2ea11ec75ecb46181dbe9757d24ca6c2ac3a7c706b168337f5297c9df55c` | `COMPLETE`, one sample-bracketed crossing |
| Human-isotope identifiability | `29be06a5f0cc46f7a0d4d66520721910` | `11299dae54664527d3e8521545368cc6df6d1f5e66fcc429b36f83b039cc980d` | `47605232d838e04f07d72faa523a8fe1cbcb9cc7a48d7c292283139857096687` | `COMPLETE`, `UNDERIDENTIFIED_DYNAMIC_MODEL` |

All three plans bind compiler implementation digest
`2fad91a924cd36759565e29ec7e7909649c217d28f43d8b0efeae1183c8e559d`.
Their journals were written to distinct ignored paths under `/tmp`.

## Scope

The source manifest is an integrity identity, not a signature or hostile-process security
boundary. It does not yet bind native-library builds, undeclared environment state, or a
multi-user authorization system. The registry is closed-world infrastructure for reviewed
local executors, not a plugin framework.

The water result still means only a bracketed crossing in supplied samples under the declared
toy model. Cycle 2 must correct the old wording that could be read as proving absence of a
continuous-profile crossing and add a stationary/regime/uncertainty preflight.
