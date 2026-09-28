import sys

import smartchem

assert "v08src" in smartchem.__file__ and smartchem.__version__ == "0.8.0a1", (smartchem.__file__, smartchem.__version__)
from smartchem.identity_parse import InputKind  # noqa: E402 -- only after the v0.8-tree assertion
from smartchem.service import build_recompile_request, run_compilation, serialize_response  # noqa: E402
req = build_recompile_request("CCOC(C)=O", input_kind=InputKind.SMILES)
resp = run_compilation(req)
sys.stdout.write(serialize_response(resp, include_replay=False) + "\n")
