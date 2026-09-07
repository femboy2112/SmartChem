# CIP external implementation check

Baseline: `043a3cd87acdc33d1df9a3b8ad4b2215d93e8890`. Work isolated in
`codex/mancude-duration-sourcing-2026-09-07`; the original main checkout was not edited.

## Instrument and independence

[`experiments/cip_external_oracle_probe.py`](../../experiments/cip_external_oracle_probe.py)
uses RDKit **2026.03.6** and its accurate
[`rdCIPLabeler.AssignCIPLabels`](https://www.rdkit.org/docs/source/rdkit.Chem.rdCIPLabeler.html),
with a 100,000-iteration limit. Legacy `_CIPCode` properties are cleared first.
The optional wheel is installed only in a scratch target; SmartChem gains no runtime dependency.
Wheel SHA-256: `9f97b58f1962df73bdacf44347bfa013f4fcb9896e049f98af2183e70e7aab46`.

The external parser, graph construction and C++ labeler are separate from SmartChem's Python
implementation. Both use the CIP specification and Hanson/Mayfield algorithm family, so agreement
is implementation evidence with shared conceptual provenance, not two independent chemical laws.
The existing geometric oracle also shares the parser/convention; it cannot independently certify
priority ranking. Four absolute/false-centre controls calibrate the external instrument.

The panel was selected before running the new implementation: 17 ligands, all unordered pairs
including duplicates, both `@` and `@@` senses, and four representations per base structure.
The configurations are the written input, canonical aromatic spelling, canonical explicit Kekulé
spelling, and reversed atom numbering. RDKit canonical isomeric identity and reference label equality
are required for every transform. Equal-ligand controls must have zero reference labels and unequal
ligands exactly one; a review found no lost valid stereo tags across the panel.

This is the operational representation transport: preserve the same stereoisomer while changing its
spelling and atom order. No arbitrary phase, probability or physical-quantum interpretation is used.
κ is executable external contact; φ is finite agreement/refutation; σ records the shared specification
and distinct implementations; ρ is the pressure to call broader naming complete. The falsifier is any
emitted label differing from the calibrated reference, including a label on a false centre.

## Result and discovered release defect

| Outcome | Baseline | Mancude extension |
|---|---:|---:|
| Correct emitted labels | 354 | 1088 |
| True constitutional ties, no label | 136 | 136 |
| Deferred named reference cases | 732 | 0 |
| Parser refusals | 0 | 0 |
| Wrong emitted labels | 2 | 0 |

These are **1,224 representation cases for 306 base inputs**, not 1,224 independent molecules.
The two baseline errors are a mirror pair:

```text
O[C@H](C1=CC=CC=N1)C1=NC=CN=C1     baseline S, accurate reference R
O[C@@H](C1=CC=CC=N1)C1=NC=CN=C1    baseline R, accurate reference S
```

The original guard only recognized lowercase aromatic flags; explicit Kekulé spellings bypassed it.
The new topology-based ring treatment fixes both errors. This is a demonstrated release correction
as well as a completeness extension. The mirror pair is retained in the regression tests and compact
receipt. All 136 identical-ligand controls remain unnamed, including the di-2-pyridyl false centre.

The original test suite did not expose this bypass. Repeating it alone would not have validated
the original soundness claim. The revised claim is bounded neutral-mancude Rule-1a naming, with
unsupported ring systems and unresolved higher-rule priorities deferred.

## Reproduction and receipts

From a checkout of the requested revision, with the separately installed RDKit wheel on `PYTHONPATH`:

```sh
PYTHONPATH=/tmp/smartchem-cip-rdkit-2026.3.6 python -m experiments.cip_external_oracle_probe --output /tmp/cip-external.json
```

The baseline was run with this same probe script importing SmartChem from the untouched original
checkout; the after run imports the isolated checkout. A read-only reviewer independently reproduced
the baseline row hash. Instrument hardening then replaced optimizable assertions with explicit
calibration/transport failures and added molecular-identity and centre-count checks; the corpus did
not change.

Compact before/after counts, exact mismatches and full-row hashes are retained in
[`experiments/validation/cip_external_oracle_2026_09_07.json`](../../experiments/validation/cip_external_oracle_2026_09_07.json).
The CLI regenerates all per-case results; scratch JSON persistence is not required. A separate fresh
adversarial panel and its scope are retained in `experiments/cip_mancude_adversarial_probe.py` and its
validation receipt. Neither panel proves the comparator's general transitivity or full CIP completeness.
