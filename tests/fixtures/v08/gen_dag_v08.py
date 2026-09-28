"""Real v0.8 DAG-mode producer run (X-high D22): run ONLY against a `git archive df1b38d` tree (see README.md)."""
import sys

import smartchem

assert "v08src" in smartchem.__file__ and smartchem.__version__ == "0.8.0a1", (smartchem.__file__, smartchem.__version__)
from smartchem.process_constraints import ProcessBounds  # noqa: E402 -- only after the v0.8-tree assertion
from smartchem.service import (  # noqa: E402
    TransformGrammar,
    build_recompile_request,
    run_compilation,
    serialize_response,
)

req = build_recompile_request("isopentyl acetate",
                              grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, process=ProcessBounds.quick())
sys.stdout.write(serialize_response(run_compilation(req), include_replay=True) + "\n")
