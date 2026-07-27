# Exact finite C3 Ising/lattice-gas map — Cycle 5 receipt

**Run date:** 2026-07-27
**Lifecycle status:** `COMPLETE`
**Claim/evidence/lane:** `ANALOGUE / ESTABLISHED / CERTIFIED`

This run is the exact-map control for SmartChem's cross-domain language. It establishes a
finite algebraic equivalence on one fixed graph while retaining distinct physical referents
and every requested state. It is not a material simulation, a dynamics calculation, a
thermodynamic-limit result, or authority to transfer the map to another graph.

## Scientist-confirmed problem

The graph is the three-site undirected cycle with vertices `(0,1,2)` and edges
`((0,1),(1,2),(0,2))`, each counted exactly once. The confirmed source parameters were
`J=2`, `h=1` exact abstract energy ticks. Beta remained a formal symbol.

The declared Hamiltonians and map are:

```text
H_I  = -J sum_edges(s_i s_j) - h sum_i(s_i)
n_i  = (s_i + 1)/2
H_LG = -epsilon sum_edges(n_i n_j) - mu sum_i(n_i)

epsilon = 4J
mu      = 2h - 4J
C       = 3(h - J)
H_I     = H_LG + C
Z_I(beta) = exp(-beta C) Xi_LG(beta)
```

For this run, `(epsilon, mu, C) = (8, -6, -3)` ticks.

## Complete state inventory

| occupancy | spins | N | Q | M | edge-spin sum | H Ising | H lattice |
|---|---|---:|---:|---:|---:|---:|---:|
| `000` | `(-1,-1,-1)` | 0 | 0 | -3 | 3 | -3 | 0 |
| `001` | `(-1,-1,+1)` | 1 | 0 | -1 | -1 | 3 | 6 |
| `010` | `(-1,+1,-1)` | 1 | 0 | -1 | -1 | 3 | 6 |
| `011` | `(-1,+1,+1)` | 2 | 1 | 1 | -1 | 1 | 4 |
| `100` | `(+1,-1,-1)` | 1 | 0 | -1 | -1 | 3 | 6 |
| `101` | `(+1,-1,+1)` | 2 | 1 | 1 | -1 | 1 | 4 |
| `110` | `(+1,+1,-1)` | 2 | 1 | 1 | -1 | 1 | 4 |
| `111` | `(+1,+1,+1)` | 3 | 3 | 3 | 3 | -9 | -6 |

All eight identities were retained in lexicographic order. The four occupancy-class
degeneracies were `1,3,3,1` and sum to eight. No sampling, grouping-only replacement, or
other output reduction was applied.

The lattice-gas formal terms `(degeneracy, coefficient of beta in the exponent)` were
`(1,0), (3,-6), (3,-4), (1,6)`. The paired Ising terms were
`(1,3), (3,-3), (3,-1), (1,9)`. Each Ising exponent is the corresponding lattice exponent
minus `C`, which is exactly the factor `exp(-beta*C)`.

## Verification boundary

The engine derives the map by lexicographically enumerating all `2^3` occupancy states. A
separately implemented direct verifier does not call that derivation routine. It recomputes
from the approved `J`, `h`, graph, and Hamiltonians:

- `epsilon`, `mu`, and `C`;
- every occupancy/spin pair, `N`, `Q`, `M`, and edge-spin sum;
- both state energies and both formal exponent coefficients;
- all four class memberships, degeneracies, and energies;
- both formal partition inventories and relation metadata;
- all completeness and zero-output-reduction fields.

The exact map constructor, executor postconditions, and final journal payload validator all
apply that binding. A self-consistent forged row with `H_I=999`, `H_LG=1002`, and the correct
constant difference was rejected because neither energy follows from the approved `J`, `h`,
and C3 Hamiltonian. A constructor-bypass attack with forced passing postconditions was still
rejected by the final payload validator; its checkpoint and artifacts were quarantined.

All five required obligations passed in the retained run:

1. exact subject and runtime-owned model;
2. established finite analogue and full casualty boundary;
3. complete exact eight-state map;
4. exact formal partition identity;
5. exact three-observable output inventory.

## Durable identities

| Artifact | SHA-256 / ID |
|---|---|
| run | `6fb05d2ed3dd4324a8bc7d75383fd402` |
| source | `43f03dc78c6630056a7f83535942a2c2518a7b03f2db5e85a7e785a60cbe9943` |
| resolved program | `6216f0dd7a49b3a51773bd544c42ab58d5f4f748511c7c5031c39fc9105b3fba` |
| Physical IR | `0831d8db85c31595a89e0f611b5f90a9c105cab94bfaf4c03571dba27cb892ec` |
| output contract | `8b517a3cc9899d81a70589cb414f0dbc99a2706fcbe249f48e7515556982ebd7` |
| plan | `9babc698cd1af1ffac0071026f0e2f7ebe3c1aef3e1d558498a7242b165c4b56` |
| approval | `c4fbbae557a6d10daf056175e190ecac86a2d935fb9890bbfde1933f083bd853` |
| calculation | `d350324a8361db3db0a9cc9167be48154afe3f7590bcdc670718d591c718069c` |
| compiler/runtime implementation | `0e8b5250518852f50adf30cfe0825f10d9de049bc576802a8424cf4e56dc6f8c` |
| complete state map/checkpoint | `7c2981cdaf58fd27adfb2ab14122c7e945e7d2bea3c7e9cdf94ee4691e2bffe3` |
| partition identity | `8d457862dab65410f501f7dd5f2c94e8b2bc5bb78bad26cfed388d3799090efa` |
| completeness inventory | `83ed0ee24364f96589ecab6c6fcb875a71ad036dbbf89c8b6be6598be7a3b6af` |
| certificate | `73aa2051bcb18cae41c7f8ad51b32f8a07b1a37f9fa45555bec35be85a9571ab` |

The write-once local journal was created at
`/tmp/smartchem-cycle5-final-ydxe5S/run.json`. The run spanned
`2026-07-27T12:34:05.081740+00:00` to
`2026-07-27T12:34:05.163857+00:00`. Local JSON journals are intentionally not committed;
this receipt and the deterministic harness are.

## What this establishes

- the shipped language/runtime can carry an exact cross-domain analogue whose evidence is
  established without promoting its physical referents to literal identity;
- every finite microstate, derived class, formal partition term, diagnostic, casualty, and
  provenance field survives the shepherd/plan/approval/run/certificate chain;
- exactness is bound to the approved model and independently defended after engine execution;
- no simulation output was reduced.

## What this does not establish

It does not establish literal particle identity, a material equation of state, calibrated
temperature-dependent numbers, dynamics or kinetics, diffusion or particle-number
conservation, Glauber or Kawasaki behavior, a thermodynamic limit, phase transition,
critical exponent, quantum or measurement semantics, or validity on any other graph,
boundary, dimension, or Hamiltonian.

## Verification

- focused finite-map/domain/registry suite: `34 passed`;
- full maintained suite: `1266 passed, 14 skipped, 1 xfailed`;
- independent algebra/science review: `SHIP`;
- independent runtime/release review: `SHIP`;
- exact-subject, contract-mutation, zero-engine-call, calculation-identity,
  replacement-model, forged-result, constructor-bypass, and payload-quarantine attacks:
  passed;
- `python -m compileall -q smartchem experiments tests`: passed;
- `git diff --check`: passed.
