# Compiled positive-frequency passive-RLC E2 result

**Executed:** 2026-07-28
**Final implementation state:** source tree bound by the compiler digest below; repository
publication identity is external to the calculation digest
**Primary run:** `COMPLETE`
**Exact lossless-resonance control:** `REFUSED` before an engine call
**Scientific scope:** `LITERAL/VALIDATED_WITHIN_REGIME/CERTIFIED` only for the
declared finite ideal mathematical circuits at one positive angular frequency

## Approved controls

The completed control is a two-boundary-node parallel network with exact

```text
R = 1 ohm
L = 1 H
C = 1 F
omega = 1 rad/s
V_input - V_output = 1 + 0j V RMS
phasor convention = exp(j omega t)
```

The model tuple is deliberately ordered `(C, R, L)` while the structural edges are
ordered `(R, L, C)`. The retained binding witness is

```text
model 0 -> structural edge 2
model 1 -> structural edge 0
model 2 -> structural edge 1
```

This prevents declaration order from silently becoming model authority.

The separately approved negative control is a series `L=C=1` network at the same
frequency and drive, with no resistor. Its exact driven MNA matrix is rank deficient.
The approved result is refusal; adding a hidden conductance or returning a partial
solution would be a defect.

## Complete result

At the damped parallel resonance, the retained branch currents and absorbed complex
powers are:

| branch | current, A RMS | absorbed complex power, VA |
|---|---:|---:|
| `R` | `1 + 0j` | `1 + 0j` |
| `L` | `0 - 1j` | `0 + 1j` |
| `C` | `0 + 1j` | `0 - 1j` |
| ideal source | `-1 + 0j` entering the positive terminal | `-1 + 0j` |

The inductor and capacitor currents and reactive powers cancel. The resistor retains
positive real dissipation, and the source-inclusive complex-power sum is exactly zero
at binary64 for this fixture.

The exact `Q(i)` boundary relation uses variable order

```text
(V_input, V_output, I_inward_input, I_inward_output)
```

and canonical rows

```text
V_input - V_output + I_inward_output = 0
I_inward_input + I_inward_output = 0
```

This relation—not a scalar impedance—is the semantic boundary object.

## Independent verification

`smartchem/rlc_ac_verifier.py` imports neither the production circuit interpreter nor
the compiled E2 executor. It independently derives the exact `Q(i)` relation and driven
MNA rank, checks canonical graph content without calling the production canonicalizer,
applies the explicit model-edge witness, and recomputes:

- every branch voltage, current, and `V * conjugate(I)` power;
- nodewise complex KCL and the ideal-source phasor constraint;
- source-inclusive complex-power balance;
- nonnegative resistor real power and zero ideal-L/C real power within tolerance;
- the retained normalized MNA state, condition declaration, and backward residual;
- every retained production diagnostic and output family.

The final direct decision was `pass`. The condition number was
`2.6180339887498953`; scaled KCL, source-constraint, complex-power, relation, and
MNA backward residuals were all `0`.

The singular control ended:

```text
REFUSED
engine calls = 0
checkpoints = 0
exact driven MNA is rank deficient; singular resonance is refused without regularization
```

## Frozen output inventory

The completed calculation emitted exactly:

1. `rlc_ac_analysis`;
2. `rlc_ac_boundary_relation`;
3. `rlc_ac_sparse_solution`;
4. `rlc_ac_direct_verification`.

Every source, plan, approval, checkpoint, observable, and certificate artifact in the
completed journal is non-quarantined. The three artifacts in the refused journal are
quarantined, and it contains no checkpoint or observable.

## Durable identities

| artifact | SHA-256 / ID |
|---|---|
| completed run | `1f1a11fc7cd34608b24e8298d990eaa9` |
| refused run | `da8dc8d51c394c90ba02eef1fcadfe5b` |
| source | `4d37ab055a25b4947d98ede17847e133917a8ca301729ec9f805191bcd28919a` |
| shepherd session | `e8c3f8e10c567157e71945b7ff2d68c897485181357963531f5940785cb1cdb5` |
| resolved program | `27616ca837e67ae37fd79306e1cad4f182626ce245aa36613d1667bc3c9591fa` |
| Physical IR | `b24bef16d3821b385089155b3d86ba5d5c2f0e41ffda66c0d24663b60241cd56` |
| request | `7c0f618da838d4fc81fdc9c3822800d74cb3523854f9517ef92a431266df3637` |
| output contract | `0a752fc2945e6a715ef42531eb2f9e1d325abe363517a07de80e5693e5619be0` |
| subject | `33bad6b923d602eacfc79eb1b954fe68b991d81c2e6740d91daa248e81f3fe18` |
| runtime-owned model | `c424d5a7273ecf0dba9fb1febe2cebcba37f034c41ba3480db95cd9ff15edbab` |
| completed plan | `66323ff747ccfb2bde8c5f50bf151a3456adb5fc537e854d31aecea14b13cca8` |
| refused plan | `a5606247b4826ef0f60c1d472f909f9ec61fce9abcf0bf0ac52188219431dfa2` |
| completed approval | `e5948f47ef74cb58a6005cba07b7b72f6ab16e7b5af3a01e5cbb947febc53ab8` |
| refused approval | `ca6bfb42e88832d5e59f52ab54f595a84067a469f0cf9bec79dd19e919394436` |
| calculation | `3f2e81d40b6e84d6a111a0507d40ecfe06b127d35d78aba78ad491c65ff0165b` |
| compiler/runtime implementation | `1304c52cc492eef1a758274fb83bbdf55ad7ae3bfe3e0dc894c2138af08a9709` |
| runtime registry | `a9b8b4f8e0dd698cd018dec31517a3c0c25de4f8569b098bbac15c3e0246359a` |
| analysis | `1c19e334a16186855fcb02d68711ae265b8f1f0a552a82ffae25b3a72f432fb0` |
| exact boundary relation | `26362603a0a7d14516b136d5cfba5bd8c838b5354f65bad2a831de8a2fc8c4f2` |
| sparse complex-MNA result | `d2400c07c24571dbef63ca741ebce2751fbdebb95b6b22955d8daeeb31bbff09` |
| direct verification | `3754d752c84e1589816cc316065b336d4dbaa0a6aefea72193e979ea701d7f07` |
| certificate | `08e2a09fa94c68b02cb32951af47b2637373b57a350fab21ceae9fb391e0e016` |

The write-once raw journals are:

```text
/tmp/smartchem-e2-release.ZNIK1h/run.json
/tmp/smartchem-e2-release.ZNIK1h/run.singular-refusal.json
```

Their SHA-256 digests are respectively
`2dd4bc5f446f1462ebcad99424c012e1164874d904c1a7866ae9105ee564f0e4`
and
`92896e7ee3b49c30950b4e4418650c564a9eb30abab3db0962e4fd7fdb0d7743`.
The completed run lasted from `2026-07-28T05:25:16.973483+00:00` through
`2026-07-28T05:25:17.220263+00:00`; the refusal ran from
`2026-07-28T05:25:17.272668+00:00` through
`2026-07-28T05:25:17.342754+00:00`.

## Verification

- E2 circuit/lifecycle/verifier/registry/P0 selection: `78 passed`.
- Full suite through `python -m pytest -q -rs`:
  `1467 passed, 14 skipped, 1 xfailed`.
- Full suite through the console `pytest` entrypoint:
  `1467 passed, 14 skipped, 1 xfailed`.
- Ruff lint and format checks passed on the 12 E2-touched Python files. The repository's
  wider historical Python scope is not Ruff-clean under local Ruff `0.15.17`, so no
  full-repository lint claim is made.
- `python -m compileall -q smartchem experiments tests` and `git diff --check`
  passed.
- The explicit heuristic benchmark smoke completed with all 19 required elements
  available and all 28 reference bonds attemptable. It declined 5 of 11 test rows,
  so its conditional MAE is not an accuracy tier.

An earlier unqualified local benchmark command discovered installed PySCF backends and
was interrupted with exit `130` during CCSD work. It had no journal or durable result and
is not timing or accuracy evidence. The intended CI-equivalent smoke was rerun explicitly
with `--oracle heuristic`.

The first E2 journal pair under compiler digest
`ca78b4f86b874c4e3a9705a5974449edc50109191c9d40d2eb47524969735c17`
was terminal (`COMPLETE`/`REFUSED`) but exposed a generic refusal-detail message. It is
superseded by the final pair above; no result was overwritten.

## Boundary

This result establishes a finite fixed-frequency ideal passive-RLC interpreter and one
independently verified damped-resonance control, plus an explicit exact singular-refusal
path. It does **not** establish:

- a physical device, component tolerance, thermal/noise/failure, grounding, or safety result;
- transient state, switching, harmonics, nonlinear/active behavior, or multi-frequency response;
- a general AC/RLC simulator or a positive-real transfer-function theorem;
- distributed electromagnetics, radiation, or electrothermal coupling;
- port-Hamiltonian semantics, dynamic effort/flow composition, or a general
  multiphysics category;
- a theorem about conditioning or correctness for every finite network.
