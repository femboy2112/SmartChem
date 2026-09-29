# SmartChem 0.9.5 -- RC funnel corpus + BLIND expected-outcome oracle

**Status:** FROZEN 2026-09-29 on `feat/v0.9.5-adversarial-rc` @ `115dd71`, **before** the S7-S10 feature-closure writers land.
Machine artifact: [`V0_9_5_RC_FUNNEL_ORACLE.json`](V0_9_5_RC_FUNNEL_ORACLE.json) -- sha256 `30fbfdf7d0b3ba7997450688a87654737b269b6ea6f9a95384ad086caa9f076e` (the driver `experiments/v0_9_5_rc_funnel.py` pins it; a changed oracle is refused unless the revision is logged in §6).
**63 members**, 13 stages each. Driver: [`experiments/v0_9_5_rc_funnel.py`](../../experiments/v0_9_5_rc_funnel.py).

## 1. What 'blind' means here

* Every expected value is written from the parent barrier (`V0_9_5_ARCHITECTURE_FREEZE.md` §1/§6/§7), the baseline freeze (`V0_9_5_BASELINE_BEHAVIOR_FREEZE.json`), code reading, or a read-only probe of the BASE tree -- never from the output of a tree that contains S7-S10. The base-tree probes are tagged `PROBED@115dd71`; the freeze citations are `FREEZE:<key>`; 0.9.5 predictions are `BARRIER:Sn`.
* The oracle has no access to any 0.9.5 code (the feature writers had not started). Where today's behaviour IS the prediction, the freeze key is cited per member (`provenance`).
* A member's expected value at a 0.9.5 change carries `s` (the barrier id) and `before` (today's value). Driver verdicts: observed == expected -> the change has landed (PASS); observed == `before` -> `PENDING(<S>)` (never a pass); neither -> MISMATCH.
* Every drop carries a TYPED reason (`status: DROP, reason: ...`); a later stage of a dropped member is `NOT_REACHED` and cites the drop; `NA` is a stage that does not apply to the member's question, with a stated reason. Nothing is silently absent.

## 2. Stages

`raw_input` -> `normalized_syntax` -> `composition` -> `identity` (layer, ambiguity set, disclosed losses) -> `structure` -> `search` (outcome, exit, search_space_status, candidate count) -> `search_receipt` (bounds, completeness) -> `reaction_vouch` (routes whose every step the reaction-type oracle vouches) -> `route_readiness` (tier counts) -> `capability_requirements` (question asked / routes projected) -> `profile_projection` (per-profile overall + the distinct axis vectors, incl. the axis a member exists to test) -> `final_dossier` (transport mode, counts, zero-FIT) -> `deserialize_verify` (plain / pinned+verified-admission / thin / canonical-policy loads; refusals carry the refusal CLASS).

## 3. Members

### front_door (12)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| FD-01 | `CuSO4·5H2O` | structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED; ROUTES_FOUND (exit 0) | - |
| FD-02 | `SO4^2-` | search: DROP IDENTITY_ONLY_CHARGED_NO_NEUTRAL_DESCENT; structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED | - |
| FD-03 | `C8H10N4O2` | structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED; ROUTES_FOUND (exit 0) | - |
| FD-04 | `NH4+` | search: DROP IDENTITY_ONLY_CHARGED_NO_NEUTRAL_DESCENT; structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED | - |
| FD-06 | `C2H6O` | structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED; ROUTES_FOUND (exit 0) | - |
| FD-12 | `H₂O` | structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED; ROUTES_FOUND (exit 0) | - |
| FD-05 | `[NH4+]` | search: DROP REFUSED_CHARGED_SPECIES_CHEMISTRY_MODEL_BOUNDARY | - |
| FD-07 | `CCO` | identity: DROP INPUT_KIND_AMBIGUOUS | - |
| FD-08 | `CuSO4.5H2O` | typed refusal of the common ASCII-dot hydrate spelling: safe (never a mis-parse) but user-hostile | - |
| FD-09 | `SO4 2-` |  | - |
| FD-10 | `C2H((` |  | - |
| FD-11 | `[Na+].[Cl-]` | ionic boundary: a salt is not one Molecule | - |

### identity (5)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| ID-01 | `smiles:CCO / smiles:COC` | same-formula constitutional isomers never merge | - |
| ID-02 | `smiles:Cc1ccccc1C / smiles:Cc1cccc(C)c1 / smiles:Cc1ccc(C)cc1` | o/m/p-xylene: one composition, three identities | - |
| ID-04 | `smiles:C[C@H](O)CC / smiles:C[C@@H](O)CC` | enantiomer pair: identity collapses (declared boundary) but the collapse is DISCLOSED as a BLOCKER loss on the | - |
| ID-05 | `smiles:[2H]O[2H] / smiles:O` | isotopologue: D2O is reported TARGET_ALREADY_AVAILABLE (water bottle) -- the collapse is disclosed, not hidden | - |
| ID-06 | `smiles:CC(=O)[O-]` | search: DROP REFUSED_CHARGED_SPECIES_CHEMISTRY_MODEL_BOUNDARY | - |

### material_identity (6)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| MK-01 | `MK-01` | salicylic acid bottle (parsed spelling) vs a Kekule-flipped requirement: S7 member. Today's literal key splits | S7 |
| MK-02 | `MK-02` | REVERSE direction: the bottle is the flipped spelling, the requirement the parsed one (S7 both directions). | S7 |
| MK-03 | `MK-03` | CONTROL: identical spelling bottle x requirement is never BLOCKED in either era (the control the surgery pairs | - |
| MK-04 | `MK-04` | NEGATIVE control: o-xylene bottle vs m-xylene requirement stays a miss in both eras (S7 must not merge constit | - |
| MK-05 | `MK-05` | declared boundary: (R)/(S) share a stock key (constitution-level identity, disclosed loss) in both eras. | - |
| MK-06 | `MK-06` | S8: a name requirement spelled with internal double space / different case vs a bottle component named 'vegeta | S8 |

### route (22)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| R-01 | `smiles:CC(=O)OC` | ROUTES_FOUND (exit 0), 2 routes | - |
| R-02 | `smiles:CC(=O)OC` | ROUTES_FOUND (exit 0), 2 routes; poor-man: overall BLOCKED | - |
| R-03 | `smiles:CC(=O)OC` | ROUTES_FOUND (exit 0), 2 routes; research-lab: overall UNKNOWN | - |
| R-04 | `smiles:CC(=O)Oc1ccccc1C(=O)O` | INCOMPLETE (exit 4), 2 routes | - |
| R-05 | `smiles:CC(=O)Oc1ccccc1C(=O)O` | INCOMPLETE (exit 4), 2 routes; poor-man: overall BLOCKED | - |
| R-06 | `smiles:CC(=O)Nc1ccc(O)cc1` | INCOMPLETE (exit 4), 2 routes | - |
| R-07 | `smiles:CC(=O)Nc1ccc(O)cc1` | INCOMPLETE (exit 4), 2 routes; research-lab: overall UNKNOWN | - |
| R-08 | `paracetamol` | INCOMPLETE (exit 4) | - |
| R-09 | `methyl salicylate` | INCOMPLETE (exit 4), 1 routes | - |
| R-10 | `C1CC=CCC1` | ROUTES_FOUND (exit 0), 1 routes | - |
| R-11 | `bromine` | DOW bromine: the NAME is not in the offline table -> INVALID_INPUT (typed, closed-world names) | - |
| R-12 | `smiles:BrBr` | TARGET_ALREADY_AVAILABLE (exit 0) | - |
| R-13 | `not-a-real-name-zzz` | unresolvable name | - |
| R-14 | `C8H9NO2` | structure: DROP COMPOSITION_ONLY_NO_STRUCTURE_PERCEIVED; ROUTES_FOUND (exit 0) | - |
| R-15 | `isopentyl acetate` | INCOMPLETE (exit 4), 27 routes | - |
| R-16 | `isopentyl acetate` | INCOMPLETE (exit 4), 27 routes; poor-man: overall BLOCKED | - |
| R-17 | `isopentyl acetate` | INCOMPLETE (exit 4), 27 routes; custom: overall BLOCKED/UNKNOWN | - |
| R-18 | `smiles:CC(=O)OC` | INCOMPLETE (exit 4), 4 DAGs | - |
| R-19 | `isopentyl acetate` | search: DROP REFUSED_CONVERGENT_DAG_UNDER_CAPABILITY_PROFILE | - |
| R-20 | `smiles:O` | TARGET_ALREADY_AVAILABLE (exit 0) | - |
| R-21 | `smiles:CBr` | NO_ROUTE_COMPLETE (exit 3) | - |
| C-01 | `recompile 'acetic anhydride' --elements --max-depth 2` | no-route COMPLETE: an exhaustive-within-bounds absence, never a claim about chemistry outside the bounds | - |

### legacy (14)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| L-01 | `tests/fixtures/v08/plan_isopentyl_acetate.json` |  | S1 |
| L-02 | `tests/fixtures/v08/request_ethyl_acetate_smiles.json` |  | - |
| L-03 | `tests/fixtures/v08/request_invalid_input_ethyl_acetate_name.json` |  | - |
| L-04 | `tests/fixtures/v08/request_isopentyl_acetate.json` |  | - |
| L-05 | `tests/fixtures/v08/request_sulfuric_acid_name.json` | deserialize_verify: DROP LEGACY_PAYLOAD_REFUSED | - |
| L-06 | `tests/fixtures/v08/response_ethyl_acetate_smiles.json` |  | S1 |
| L-07 | `tests/fixtures/v08/response_ethyl_acetate_smiles_thin.json` |  | S1 |
| L-08 | `tests/fixtures/v08/response_invalid_input_ethyl_acetate_name.json` |  | S1 |
| L-09 | `tests/fixtures/v08/response_isopentyl_acetate.json` |  | S1 |
| L-10 | `tests/fixtures/v08/response_isopentyl_acetate_dag.json` |  | S1 |
| L-12 | `tests/fixtures/v08/response_stereo_isopentyl_acetate_smiles.json` |  | S1 |
| L-13 | `tests/fixtures/v08/response_sulfuric_acid_name.json` | deserialize_verify: DROP LEGACY_PAYLOAD_REFUSED | - |
| L-14 | `tests/fixtures/v08/tamper/T1_request_v08id_injected_capability.json` | deserialize_verify: DROP LEGACY_PAYLOAD_REFUSED | - |
| L-15 | `tests/fixtures/v08/tamper/T4b_response_v08id_injected_profile_and_pin.json` | deserialize_verify: DROP LEGACY_PAYLOAD_REFUSED | - |

### wire (1)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| W-01 | `methyl_acetate@poor-man canonical payload` | canonical() = require_canonical_transport + require_verified_admission: a thin advisory payload must be refuse | S1, S14 |

### heldout (1)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| H-01 | `experiments/v0_9_heldout_saponification_probe.py::run()` | the held-out benign procedure: an unsourced synthesized case can never reach PROCESS_SPECIFIED; P10 (containme | - |

### stream_disposition (1)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| SD-01 | `DME synthetic witness (2 MeOH -> DME + H2O)` | baseline half of the witness: with no dispositions FIT is unreachable (the 0.9 theorem) | S10 |

### lateral (1)

| id | raw input | headline prediction | depends on |
|---|---|---|---|
| LT-01 | `C1=CCCC=C1 (1,3-cyclohexadiene)` | search: DROP NOT_PUBLICLY_REACHABLE | - |

## 4. Predictions that move at a 0.9.5 change (the S-facets)

| id | change | expected AFTER | today (`before`) |
|---|---|---|---|
| MK-01 / MK-02 | S7 | salicylic acid bottle x Kekule-flipped requirement (both directions): stock keys equal, `active_fraction_interval` finds the component, **material axis not BLOCKED** | keys differ -> material BLOCKED (the false-BLOCKED, C7-2) |
| MK-06 | S8 | `Vegetable  Oil` matches a `vegetable oil` component (one normaliser) | no match (strip + casefold only) |
| W-01 | S1 | `VerificationPolicy.canonical()` load of a THIN payload refused at dispatch (ValueError); THICK canonical accepted | policy API absent |
| W-01 | S14 | a payload relabelled with the 0.9.0a1 response id is refused (`unsupported schema version`) | accepted (the id is still current) |
| L-* (accepted v0.8 responses) | S1 | refused under the canonical policy | accepted under the plain policy (kept; only canonical refuses) |
| SD-01 | S10 | the DME synthetic witness reaches CAPABILITY_FIT with the 3 dispositions; deleting any one -> UNKNOWN; a bench without AQUEOUS_NEUTRAL -> BLOCKED | no dispositions exist -> waste UNKNOWN, exactly 3 unresolved, overall UNKNOWN (predicted and asserted today) |

Zero production CAPABILITY_FIT is expected after S10 too (barrier §6: no cited corpus page states disposal): every route member's `capability_fit_count` is 0 in BOTH eras. Digests and schema ids move at S7/S9/S10 (adjudicated drift) -- the oracle pins behaviour, never digests.

## 5. Boundaries recorded, not papered over

* **Lateral search** (LT-01) has no CLI/service door: `smartchem.lateral_search` is a library core kept out of the W1 route search. Recorded as the typed drop `NOT_PUBLICLY_REACHABLE` at `search`, plus the library-level closure facts (complete, 2 isomers, 1-step route).
* **DOW bromine** (R-11, R-12, R-21): the name `bromine` is INVALID_INPUT; `smiles:BrBr` is TARGET_ALREADY_AVAILABLE (a commodity terminal); 12 bromide targets were probed and NONE has a supported ROUTE in the linear route algebra at depth 1 (R-21 records bromomethane: NO_ROUTE_COMPLETE). The Dow cost/kinetics litmus lives in the `dow_bromine_*` probes, not in the route search -- a bromide *route* member cannot be honestly written today.
* **Identity is constitution-level** (barrier §7): ID-04 enantiomers and ID-05 isotopologues collapse to one identity; the collapse is DISCLOSED as a BLOCKER `identity_losses` record, and ID-05 shows the sharp edge (D2O 'already available' via a water bottle).
* **User-hostile but safe refusals** (FD-08 ASCII-dot hydrate `CuSO4.5H2O`, FD-09 `SO4 2-`, FD-11 salts): typed, never mis-parsed.
* `CCO` bare AUTO is INPUT_KIND_AMBIGUOUS (ethanol's SMILES is also the formula C2O) -- FD-07.
* The held-out member (H-01) is the existing blind-oracle probe run through its public `run()`; its own oracle sha is `eb01d67c9b76..`.
* Members NOT in the corpus, on purpose: `isopentyl@research-lab`, the two default-process isopentyl DAG cases and `isopentyl_dag_quick` (each 15-70 s and adds no new stage behaviour over R-15..R-19; they stay in the baseline freeze).

## 6. Oracle revision log

1. **R-17 `profile_projection.profile`**: `custom-fit-bench` -> `custom`. The freeze-time value was a label I invented for the object-valued `isopentyl_capability_fit_bench()` profile; the public projection reports any non-preset profile as `custom` (an ORACLE LABELLING ERROR, found by the first full funnel run; frozen sha c27ad0d35d65b4aa959e8488ccd5e7cc8c2832faef5c4063a261f14c8f326c3f -> revised sha in the header; no behaviour moved, and every other R-17 stage matched as frozen).

