# Class-A reaction-residue transform — Cycle 4 receipt

**Run date:** 2026-07-27
**Transformed lifecycle status:** `COMPLETE`
**Reference lifecycle status:** `COMPLETE`

This cycle makes an existing exact execution shortcut plan-visible, runtime-model-bound,
independently verified, and certificate-bound. It does **not** claim a newly achieved
three-to-two call reduction or a measured timing speedup: `reaction_energy` already executed
on the residue before this cycle.

The exact scope is the runtime-owned closed separable endpoint model:

`E(configuration) = sum(count_i * E(species_i))`.

For a shared multiset `S`,

`E(S + products) - E(S + reactants) = E(products) - E(reactants)`.

That identity does not apply automatically to interacting vessels, solvation, fields,
context-dependent binding, open systems, or another replacement model.

## What changed

- `ReactionResidueTransform` retains the original reaction digest, exact residual
  configurations, eliminated multiplicities, unique residual workset, unchanged model
  digest, applicability/evidence, verifier identity, and empty casualty list.
- The compiler performs oracle-domain admission on the residual rather than falsely refusing
  because of a spectator that cannot affect this declared model.
- The runtime requires the exact shipped separable `ModelSpec`, independently recomputes the
  transform before any oracle call, and rejects forged or replacement-model transforms.
- The run journal retains a complete typed transform artifact. The unchanged certificate
  schema binds it transitively through the certified plan digest.
- The equivalence contract freezes every `reaction_energy` `ObservableValue` field while
  explicitly allowing only added transform/diagnostic/run provenance.

## Structural probe

The raw request was:

`Fe + H + H -> Fe + H2`.

The probe oracle declared coverage only for neutral ground-state H/H2 species. Diagnosing the
raw reaction therefore produced:

`[UNPRICED / removable] Fe: ... declares no coverage for Fe`.

After verifying the Class-A transform:

- raw distinct species: `3`;
- retained residual workset: `H`, `H2`;
- actual oracle calls: `H`, `H2`;
- Fe calls: `0`;
- output inventory: exactly `reaction_energy`;
- transformed value: `-4.5 eV`;
- transformed reported uncertainty scale: `0.223606797749979 eV`;
- exact spectator-free reference: `-4.5 eV`, `0.223606797749979 eV`;
- output-contract digest was identical in both arms:
  `ee888fdb1a634ca57d8d3c459baa0d80a42660a401b1294dff2811851b77ecd5`.

The bare reference has different reaction text in its notes, as it should. A separate
same-raw-reaction test compares transformed execution with the existing direct residual
implementation and requires exact equality of every observable field: value, uncertainty,
method, seconds, notes, systematic scale/terms, method set, unit, and support.

All four obligations passed. The oracle-domain obligation names only `H, H2`, demonstrating
that admission used the verified residual rather than the raw three-species inventory.

## Durable identities

| Artifact | SHA-256 / ID |
|---|---|
| transformed run | `7274dfa779564cb99dd8aa8d6b589941` |
| spectator-free reference run | `242ae7c5ab8345939cd1d7877620ebbf` |
| source | `572d47ae843dfe4eb65a2f670be0bac165d7d6758a9d2a25d38182f495ced6be` |
| resolved program | `f93078a290bd92c9429f324bed18c1c256df20942264f79c354d947fa18dea70` |
| Physical IR | `ded98325915b36deee01f825c1a76932c72044225008f06bc8d60e725169ae32` |
| request | `5ee4c9dc4ec9e6b5b67d66b86b767e948d184ee57ad6ab028efb9ea3205f5f95` |
| transformed plan | `6ec058a9b29f45cfd0888d5026116b7c1372a6fbd3f895408376acbfea6c16d5` |
| reference plan | `98253d7420fe001fd875a0fdc341befc36273a63dcd6e531f179e40d2978b060` |
| transformed approval | `9be4facb700f30e6815bf4c4d919339835718b3edb2564ec4ea5579bb17459f7` |
| calculation | `b48e55dc84a59b6b7bbffccfd0672d2aaaf7e7fa6b0d567a5dc673fb3479cd05` |
| probe implementation | `21ea45e11492c11e98a1fdc102a4982f70345e885c7bb510b46c974285f3e28c` |
| compiler/runtime implementation | `77ebd3296c1eafb58f10fda6c80721f16f9e6f0bbc5d2ee59890ecec6077d26a` |
| transform and retained transform artifact | `a9059283fae98baa2d05698301cedead039eb0c47041e7449fd2104c18e89bb7` |
| reaction-energy observable | `19b0c89801c62b0e0e6939fb2fe2571a91a52a627b04bc29fc44213d7f492bfd` |
| transformed certificate | `4632b8f9545193345422f1019e586c323339a46fdc787d122e79bc721d21176f` |
| reference certificate | `bb27807ce2061148cb46b490e35769972be7f095b7eeaeb6262291df6df60ea0` |

The write-once local journals were created under
`/tmp/smartchem-cycle4-final-pUQmjY`. The transformed run spanned
`2026-07-27T12:13:40.831548+00:00` to
`2026-07-27T12:13:40.889865+00:00`. Local JSON journals are intentionally not committed;
this receipt and the deterministic harness are.

## What this establishes

- an already-shipped exact spectator shortcut is now a typed reviewable plan transform;
- the runtime, not an arbitrary approved replacement model, owns the exact separability
  semantics that license cancellation;
- false oracle-domain over-refusal from an unpriceable regenerated spectator is removed;
- multiplicity, residuals, workset, reaction/model identity, and verifier identity are all
  independently checked before calls;
- no requested reaction-energy observable field is reduced or changed.

## What this does not establish

It does not establish a new performance improvement, wall-clock speedup, general optimizer,
persistent cache, shared quantum intermediates, parallel scheduler, exact cancellation in an
interacting model, or authority for any Class B/C fidelity change.

## Verification

- focused optimizer/program/registry suite: `78 passed`;
- full maintained suite: `1251 passed, 14 skipped, 1 xfailed`;
- independent algebra/science review: implementation `SHIP`;
- independent runtime/release review: `SHIP`;
- replacement interacting-model attack: `INVALID`, zero oracle calls;
- expanded residual/multiplicity/workset/model/reaction/verifier forgery attacks:
  `INVALID`, zero oracle calls;
- `python -m compileall -q smartchem experiments tests`: passed;
- `git diff --check`: passed.
