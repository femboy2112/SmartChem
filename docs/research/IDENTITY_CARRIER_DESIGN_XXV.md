# Configuration-aware identity carrier (issue #130): design, measured gaps, controls

**Status:** DESIGN + CHARACTERIZATION CONTROLS ONLY (OPERATION XXV). No production behaviour changes. The frozen 1.x
machine contract keys route terminals and stock on constitution; that does not change in 1.x without an explicit,
versioned decision (see §5).

## 1. Measured behaviour at main `11d05bb` (2026-11-08)

Route search matches terminals by `routes._ident` and stock by `stock.structure_key`. Both are constitution-only
(`resonance_identity`). The perception layer is richer: `LayeredIdentity.of_molecule(molecule, features)` refines
CONSTITUTION → CONFIGURATION → ISOTOPIC, fail-closed on `SmilesFeatures.configuration_complete`.

`same_identity_at(a, b, layer)` for control pairs (probe in this session; pinned in
`experiments/sandbox_foundation/tests/test_xxv_identity_controls.py`):

| pair | FORMULA | CONSTITUTION | CONFIGURATION | ISOTOPIC |
|---|---|---|---|---|
| (S)- vs (R)-alanine | = | = | ≠ | ≠ |
| (S)-alanine vs unmarked alanine | = | = | ≠ | ≠ |
| (E)- vs (Z)-2-butene | = | = | unknown | unknown |
| CD₄ vs CH₄ | = | = | = | ≠ |
| ¹³C-ethane vs ethane | = | = | = | ≠ |
| ethanol vs dimethyl ether | = | ≠ | ≠ | ≠ |
| nitromethane, two charge-separated resonance spellings | = | = | = | = |
| benzoate, aromatic vs Kekulé spelling | = | = | = | = |

So the perception layer already separates enantiomers and isotopologues, keeps resonance forms together, and refuses
(unknown) on marked E/Z. The constitution-only search discards all of that.

## 2. A gap in perception that a #130 implementation must not inherit

`configuration_complete` is **True** for molecules with an *unmarked* stereogenic element:

| SMILES | real stereo status | `configuration_complete` | `configuration_digest` |
|---|---|---|---|
| `NC(C)C(=O)O` (alanine, unmarked) | chiral, unspecified | True | None |
| `CC(O)CC` (2-butanol, unmarked) | chiral, unspecified | True | None |
| `CC=CC` (2-butene, unmarked) | E/Z, unspecified | True | None |
| `CCO` (ethanol) | achiral | True | None |
| `OCC(O)CO` (glycerol) | achiral | True | None |

"Unspecified" and "achiral" therefore have the same identity class. `known_layer` reads ISOTOPIC (configuration
"fully perceived") for every unmarked stereogenic molecule. The flag goes False only when stereo is *marked* but cannot
be perceived (e.g. `C/C=C/C`).

- **Live impact today: none found.** Search ignores CONFIGURATION and the service refuses a declared CONFIGURATION or
  ISOTOPIC match layer (`service._check_identity_layer`).
- **Latent impact:** a configuration-aware matcher that trusts `configuration_complete` would treat an unspecified
  stock as configuration-known, and would let a stereo claim about a product rest on a molecule whose configuration
  nobody stated.
- **Required before any #130 promotion:** perceive stereogenic elements independently of the marks (tetrahedral centres
  with four constitutionally distinct branches; double bonds with two distinct substituents at each end), calibrated
  against an independent oracle (RDKit `FindMolChiralCenters(includeUnassigned=True)` in a dev venv; it is not installed
  in the current dev venv), and report UNPERCEIVED rather than achiral when the detector cannot decide (ring
  pseudo-asymmetry, atropisomers, allenes).

## 3. The carrier (research schema `smartchem.research.identity_carrier/xxv-1`)

| field | values |
|---|---|
| `constitution` | the production CONSTITUTION digest (resonance-canonical; resonance spellings are one identity) |
| `configuration_status` | ACHIRAL, SPECIFIED, PARTIALLY_SPECIFIED, UNSPECIFIED, RACEMIC, UNPERCEIVED |
| `configuration` | the production CONFIGURATION digest, present only when SPECIFIED |
| `isotope_status` | NATURAL_ABUNDANCE, LABELED |
| `isotopic` | the production ISOTOPIC digest, present only when the configuration digest is present or the molecule is ACHIRAL |
| `charge` | total charge (FORMULA layer); per-atom charge localisation only through the constitution digest, so resonance-related localisations are equal and non-resonance ones (tautomers, zwitterions) are already different constitutions |

RACEMIC cannot be read from a SMILES string; it must be declared by the stock record, never inferred.

## 4. Stock-supply matching policy (demand = target, supply = stock)

| target \ stock | ACHIRAL | SPECIFIED same | SPECIFIED other | RACEMIC | UNSPECIFIED / UNPERCEIVED |
|---|---|---|---|---|---|
| ACHIRAL | MATCH | — | — | — | — |
| SPECIFIED | — | MATCH | MISMATCH | NOT_A_SUPPLY (needs a resolution step) | UNDECIDABLE (refuse) |
| RACEMIC | — | MISMATCH | MISMATCH | MATCH | UNDECIDABLE |
| UNSPECIFIED | — | MATCH_AT_CONSTITUTION + declared loss | MATCH_AT_CONSTITUTION + declared loss | MATCH_AT_CONSTITUTION + declared loss | MATCH_AT_CONSTITUTION + declared loss |

Isotopes: NATURAL vs LABELED is MISMATCH; LABELED matches only the same ISOTOPIC digest.

Rules:
- A racemate is never counted as a supply of one enantiomer. Two enantiomeric stocks are never one supply.
- A MATCH_AT_CONSTITUTION carries an explicit identity-loss record, and the route may make **no** stereochemical claim
  about its product.
- **No selectivity claims.** No current rule models the stereochemical outcome of a step. A SPECIFIED target therefore
  has product configuration UNKNOWN on any generated route, and the route is demoted, never vouched as making that
  stereoisomer.

## 5. Versioning

Changing what terminal/stock equality means changes the meaning of a stable search surface.
- Under COMPATIBILITY §1 that is a MAJOR change if made silently.
- An additive 1.x path exists only as an explicit opt-in that changes the request's semantic digest (a new search
  identity, §7). Its wire impact (a new request field, schema generation) needs its own review.
- Neither path is taken in OPERATION XXV.

## 6. Issue #105 (per-atom charge)

Not started in OPERATION XXV. The precondition recorded here: per-atom charge must enter the constitution digest
before any charge-changing rule can be recognized, which moves every charged-species digest. That makes it a
schema/digest migration, to be prototyped on its own research branch with a migration audit first.
