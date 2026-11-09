# Issue #130 — the search/stock identity key is configuration-blind (measured gap + migration)

**Status:** CHARACTERIZATION + MIGRATION DESIGN ONLY (OPERATION XXVI, WAVE 2). No production behaviour changes.
This extends `IDENTITY_CARRIER_DESIGN_XXV.md`; it does not restate it. XXV designed the configuration-aware
*carrier* and pinned the *perception* layer's controls in the sandbox suite. This note pins the other half — the
**search/stock** layer — in the **core** (required-CI) suite, and states exactly what a #130 promotion changes.

Pinned by `tests/test_stereo_search_identity_130_xxvi.py` (11 tests, GREEN on main `4d8149a`).

## 1. The measured gap

Route search matches terminals by `resonance_identity` and stock supply by `stock.structure_key`. Both are
**constitution-only**. Measured at main `4d8149a` through the public APIs:

| pair | GROUND TRUTH | `resonance_identity` / `structure_key` | feature-aware perception |
|---|---|---|---|
| (R)- vs (S)-alanine | different substances | **SAME** | CONFIGURATION **≠** |
| (E)- vs (Z)-2-butene | different substances | **SAME** | CONFIGURATION **None** (fail-closed) |
| CD₄ vs CH₄ | different substances | **SAME** | ISOTOPIC **≠** (CONFIGURATION =) |
| ¹³C-ethane vs ethane | different substances | **SAME** | ISOTOPIC **≠** (CONFIGURATION =) |
| ethanol vs dimethyl ether (control) | different substances | **DIFF** | CONSTITUTION **≠** |

Two facts, both now regression-pinned:

1. **The search/stock key collapses every configuration and isotopic distinction** (rows 1–4 are `SAME`), while
   remaining constitution-SOUND (the control is `DIFF`). The collapse is specific, not a broken key — that is the
   anti-vacuity control `test_constitution_control_stays_distinct`.
2. **The information is not lost at the parser.** `parse_smiles_features` + `LayeredIdentity.of_molecule` either
   SEPARATES the distinct substances one layer up (enantiomers at CONFIGURATION, isotopologues at ISOTOPIC) or
   fail-closes to `None` (marked E/Z it cannot resolve). The search key *discards* information that already exists.

## 2. The synthesis hazard (phase I-D), made concrete

> "A system that knows chemical constitution but not configuration cannot silently treat two enantiomeric stocks
> as interchangeable."

`test_enantiomeric_stock_satisfies_opposite_demand` pins it: a stock set keyed by `structure_key` holding only
(R)-alanine reports an (S)-alanine **target** as in stock. The supply layer cannot distinguish the enantiomers, so
a route that consumes (S)-material would be certified "stocked" by (R)-material. This is a correctness hazard for
any stereospecific synthesis, latent today only because the search *also* ignores CONFIGURATION on the demand side
(the two blindnesses cancel into "no wrong answer surfaced yet", not "no defect").

This is the exact-same *shape* as #168 (COT bond-shift, pinned in WAVE 1): a distinction that is real, is perceived
or perceivable one layer up, and is erased by a constitution-only identity used as the matching key. #130 is the
configuration/isotopic axis; #168 is the resonance/kekulé axis.

## 3. What a #130 promotion changes, and why it is not a 1.x patch

The fix is to key route terminals and stock on a **configuration-aware identity** — but `resonance_identity` and
`structure_key` are part of the **frozen 1.x machine contract** (they are serialized/compared as the route-terminal
and stock-membership keys). Changing what they return would change every route digest and stock match across the
population: a breaking wire/identity change, exactly what phases I-D/I-E reserve for an explicit major-version
decision with migration and independent review. It is **not** a silent 1.x patch.

Versioned migration (mirrors the #168 `IdentityPolicy` V1/V2 approach):

- **V1 (current, default):** search/stock key = constitution-only. Unchanged; every existing digest is stable.
- **V2 (opt-in):** search/stock key = a layered key at a caller-declared `MatchLayer` (CONSTITUTION ⊑ CONFIGURATION
  ⊑ ISOTOPIC), built from `LayeredIdentity.digest_at(layer)`. A demand carries the layer it requires; stock matches
  only at that layer or finer.
- **Fail-closed rule (required):** when `configuration_complete` is False / the layer digest is `None`, a V2 match
  at CONFIGURATION or finer must **refuse** (UNPERCEIVED), never silently treat unspecified as achiral. This closes
  the perception gap XXV §2 already flagged (`configuration_complete == True` for *unmarked* stereocentres) before
  it can reach a matcher.

### Forward / backward controls a V2 implementation must pin

- **Forward (the flip):** under V2@CONFIGURATION, the row-1 enantiomer pair separates (`!=`); under V2@ISOTOPIC the
  isotopologue pairs separate; the WAVE 2 pins' `==` assertions become `!=`. GROUND TRUTH distinctness is unchanged.
- **Backward (stability):** under V1 / V2@CONSTITUTION, every pin in this file and every existing route/stock digest
  is byte-identical to main. A V2 build must not perturb a V1 caller.
- **Anti-vacuity:** the constitution control stays `DIFF` at every layer; a marked-but-unperceivable element
  (E/Z-2-butene) returns UNPERCEIVED at CONFIGURATION, never a guessed match.

## 4. Boundary

- No production behaviour changed this round. No digest moved. The frozen 1.x contract is intact.
- This is Problem-of-identity work (formal/representational truth boundary); it makes **no** claim about
  stereoselectivity, mechanism, or feasibility — a configuration-aware *key* does not assert a configuration-aware
  *reaction*. That separation is the standing #130 discipline.
- Prerequisite for promotion (carried from XXV §2): perceive stereogenic elements independently of the marks,
  calibrated against an independent oracle (RDKit `FindMolChiralCenters(includeUnassigned=True)` in a dev venv),
  and report UNPERCEIVED rather than achiral when the detector cannot decide.

## 5. Restart coordinates

- Pins: `tests/test_stereo_search_identity_130_xxvi.py` (11, GREEN at `4d8149a`).
- Design base: `docs/research/IDENTITY_CARRIER_DESIGN_XXV.md`; sibling defect `COT_IDENTITY_168_XXVI.md`.
- Keys to migrate: `smartchem.smiles.resonance_identity`, `smartchem.experiment.stock.structure_key`.
- Carrier: `smartchem.identity.LayeredIdentity` / `MatchLayer` / `same_identity_at` / `digest_at`.
