# SmartChem Python-API examples

Small, deterministic, benign scripts that use only the public API and the **base install** (numpy/scipy; no pyscf, no rdkit, no network). Each finishes in about a second.

Run from the repository root with SmartChem importable (`pip install -e .`, or `PYTHONPATH=.`):

```bash
python examples/01_parse_and_identify.py
python examples/02_decompile.py
python examples/03_synthesis_search.py
python examples/04_verify_serialized.py
python examples/05_reaction_type.py
```

Candidate routes here are `FORMAL_CANDIDATE`s: conservation- and structure-checked, **not** vetted lab procedures.

Note: the 'expected output' blocks below were captured from real runs (exit code 0 each); digests are truncated in the scripts' own output.

## 01_parse_and_identify.py

Parse SMILES into a graph `Molecule`, read the identity receipt, and watch `resolve_target` refuse a bare formula (a composition is not a structure).

```text
ethanol     smiles=CCO      formula={'C': 2, 'H': 6, 'O': 1} atoms=9
            identity layer=CONSTITUTION via SMILES_PARSER
acetic acid smiles=CC(=O)O  formula={'C': 2, 'H': 4, 'O': 2} atoms=8
            identity layer=CONSTITUTION via SMILES_PARSER
resolve_target('C2H6O') REFUSED: AUTO input resolved to a FORMULA-layer identity (C2H6O) with no perceived structure; a structure search needs a molecule (NAME or SMILES), not a bare formula/InChI (section 5.4)
```

## 02_decompile.py

`build_decomposition` of `C2H6O` over the small `example_inventory()`: a complete, digest-stamped set of atom-conserving formula descents (formal, not a procedure).

```text
status=COMPLETE complete=True edges=9 nodes=9
digest=88331869529441cd...
   DecompositionEdge(C2H6O -> C + CH4 + 2 H + O)
   DecompositionEdge(C2H6O -> C + CH4 + H2O)
   DecompositionEdge(C2H6O -> C + CO + 6 H)
   DecompositionEdge(C2H6O -> 2 C + 4 H + H2O)
   DecompositionEdge(C2H6O -> 2 C + 6 H + O)
   DecompositionEdge(C2H6O -> CH4 + CO + 2 H)
   DecompositionEdge(C2H6O -> C2H4 + 2 H + O)
   DecompositionEdge(C2H6O -> C2H4 + H2O)
   DecompositionEdge(C2H6O -> C2H6 + O)
```

## 03_synthesis_search.py

`build_recompile_request` + `run_compilation` for methyl acetate: outcome, exit code, standard status and the formal candidate routes.

```text
outcome=ROUTES_FOUND exit_code=0 status=COMPLETE_WITHIN_DECLARED_SPACE
routes=2
  [FORMAL_CANDIDATE] step 1: CH4O + C2H4O2 -> C3H6O2 + H2O
  [FORMAL_CANDIDATE] step 1: CH2O2 + CH4O -> C2H4O2 + H2O ; step 2: CH4O + C2H4O2 -> C3H6O2 + H2O
result_digest=8681704554c3fbfb...
```

## 04_verify_serialized.py

`serialize_response` / `deserialize_response` round-trip with re-verification on load, plus a tamper control that the loader refuses.

```text
wire bytes=11369
round-trip OK: outcome=ROUTES_FOUND result_digest=8681704554c3fbfb...
tampered wire REFUSED: ValueError: result_digest does not match the reconstructed response
```

## 05_reaction_type.py

`search_event_routes` + `recognize_reaction_type`: names the esterification class for a real step and ABSTAINs (`None`) on an unsupported one.

```text
routes=1 search_complete=True
  ExperimentStep(C2H4O2 + C2H6O -> C4H8O2 + H2O) -> acyl condensation (esterification/amidation)
unsupported step ExperimentStep(C2H6O -> C2H4 + H2O) -> None
```
