# Real v0.8 producer fixtures (SmartChem main @ df1b38d, version 0.8.0a1)

Produced by the v0.8 producer's own public path. No hand edits. Regeneration is deterministic (the sha256 values below were reproduced on a second run for the two routes-mode responses).

## Source extraction (clean copy, not a worktree)
    S=<any scratch dir>; mkdir -p $S/v08src
    git -C <repo> archive df1b38d | tar -x -C $S/v08src
    PYTHONPATH=$S/v08src <repo>/.venv/bin/python -c "import smartchem;print(smartchem.__file__, smartchem.__version__)"
    #  -> $S/v08src/smartchem/__init__.py 0.8.0a1     (RDKit NOT installed in the venv)
    # v08src/smartchem/service.py sha256 240caa453b04f76f03dac21934b0bce1eb27c5bf88c9d5e254eea75b1fd21c82

## Commands (cwd = fixtures_v08, env PYTHONPATH=$S/v08src, P=<repo>/.venv/bin/python)
| file | command | exit |
|---|---|---|
| request_isopentyl_acetate.json | `$P -m smartchem recompile "isopentyl acetate" --emit-request` | 0 |
| response_isopentyl_acetate.json | `$P -m smartchem recompile "isopentyl acetate" --json` | 4 (INCOMPLETE, PARTIAL_CANDIDATE_SET, 10 ranked routes, CANONICAL_VERIFIED, 3 routes carry a sourced ProcedureEvidence) |
| request_ethyl_acetate_smiles.json | `$P -m smartchem recompile --smiles "CCOC(C)=O" --emit-request` | 0 |
| response_ethyl_acetate_smiles.json | `$P -m smartchem recompile --smiles "CCOC(C)=O" --json` | 0 (ROUTES_FOUND, 5 ranked routes, no procedure evidence, CANONICAL_VERIFIED) |
| response_ethyl_acetate_smiles_thin.json | `$P gen_thin_v08.py` (build_recompile_request + run_compilation + serialize_response(include_replay=False)) | 0 (THIN_ADVISORY) |
| request_invalid_input_ethyl_acetate_name.json | `$P -m smartchem recompile "ethyl acetate" --emit-request` | 0 |
| response_invalid_input_ethyl_acetate_name.json | `$P -m smartchem recompile "ethyl acetate" --json` | 2 (INVALID_INPUT, zero dossiers: the name is not in the offline table) |
| request_sulfuric_acid_name.json | `$P -m smartchem recompile "sulfuric acid" --emit-request` | 0 (Wave-C2 P2: v0.8 did NOT register this name -> normalized_identity "", today's resolver does) |
| response_sulfuric_acid_name.json | `$P -m smartchem recompile "sulfuric acid" --json` | 2 (INVALID_INPUT, zero dossiers; deterministic, sha reproduced on a second run) |
| plan_isopentyl_acetate.json | `$P -m smartchem plan "isopentyl acetate" --json` | 4 (schema smartchem.plan/plan-result-v0.6; `.compilation` = a full response payload) |
| response_isopentyl_acetate_dag.json | `$P gen_dag_v08.py` (build_recompile_request(CAPPED_SCISSION_CONVERGENT, process=quick) + run_compilation + serialize_response(include_replay=True)); added in the 0.9 X-high continuation (D22) -- the only fixture with ranked_dag_dossiers | 0 (INCOMPLETE, 16 DAG dossiers, 3 replay steps carry a sourced ProcedureEvidence, CANONICAL_VERIFIED; sha reproduced on three runs) |
| response_schema_descriptor.json | `$P -c "import json;from smartchem.service import response_schema;print(json.dumps(response_schema(),sort_keys=True,indent=1))"` | 0 |

## sha256
    0ddcb73db66884b0e2fa8e0feb99441b1152811eaff39dccc592069a2b1ad384  plan_isopentyl_acetate.json
    ec3fb3d8e0ecb3fbb9c7d8243c8b50567bf27569a31d7f906e4d2d4eff33c575  request_ethyl_acetate_smiles.json
    5b3787fb55598c76d07938ecb5c15d8cbee623a98dc848ee3d63ae0da4b42481  request_invalid_input_ethyl_acetate_name.json
    4cba7f31cdabed41993740611dfeb56d18fc09348b8819db4b48da55f7de92bb  request_isopentyl_acetate.json
    d0ec6b1cc3f14e04d2ead84880aba2ae97324f5b23cb7d90022e4c17f2bb39d4  response_ethyl_acetate_smiles.json
    abf28f6c75783a3e180deb1450b16783fbee44b2a84451d2fd758aea73aa4cd5  response_ethyl_acetate_smiles_thin.json
    1eb4f4beb1e833d413e1221676c6d571944c9e0572fd1a8be327dece59d8209d  response_invalid_input_ethyl_acetate_name.json
    214036447e18e83288062a6eef1111e621e6816c9bf17cd9728abb9fa59831c3  response_isopentyl_acetate.json
    0b2acad46d1969594c76dc9a867302fc22dcd004d1bae57849f047fdc7f1f4c0  request_sulfuric_acid_name.json
    1a8f5d8a916f3da6204d21e227a8f67aecf31d003acda8e335f7d5bda24a9814  response_sulfuric_acid_name.json
    25f54817e2d32ee0aec680b7aa47afe9229494540153674d131b127d2265af8a  response_schema_descriptor.json
    7f3fa7e7daac943e428b09ecac1fa6f523e81805eab8670a3f3ae695ee2717c9  gen_thin_v08.py
    0098ba9422ff8e2db70cf994ccbf87e800c9a4c723c7f0ecd65e2bca4db02f7d  response_isopentyl_acetate_dag.json
    424e3478dffafeb4a9ce180d0deef7a3e329fef262c9a5b124703e0fad7cec2b  gen_dag_v08.py

(X-high continuation: `gen_thin_v08.py` changed only its import order for lint; re-running it under the
df1b38d tree reproduces `response_ethyl_acetate_smiles_thin.json` byte-identically, sha `abf28f6c…`.)

## Tamper fixtures (tamper/, built from these + a 0.9.0a1 (tip 4b8f8c2) payload)
* T1 = request_isopentyl_acetate.json (v0.8 id kept) + the 0.9.0a1 poor-man `capability_profile` and
  `capability_profile_origin="poor-man"` injected. Pre-Round-V it was ACCEPTED as a native request (F81).
* T4b = response_invalid_input_ethyl_acetate_name.json (v0.8 id kept) + the same injected request profile + a
  RECOMPUTED `capability_question_digest` pin (result_digest untouched: the zero-dossier result does not fold the
  profile). Pre-Round-V it was ACCEPTED, also under verified admission (F81).
Both must be REFUSED (D11); tests/test_v0_9_round_v_schema_migration.py pins it.
    b8d8a184ef2a6e3138d1598ceecd50f0d77ef48f164d95659901f265f1673b37  T1_request_v08id_injected_capability.json
    431a9e3579ee61d4febf3f4d4b99e099b10faaae3628359d476aecf2642bb205  T4b_response_v08id_injected_profile_and_pin.json
