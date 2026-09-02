"""Regenerate the CLI-JSON-01 golden fixtures (tests/fixtures/cli_json/).

Run ONLY after an INTENTIONAL change to the response schema or to a command's output:

    .venv/bin/python tests/regen_cli_json.py

It rewrites every golden from the live CLI/service output.  A golden diff on an UNINTENTIONAL change is the
guard in tests/test_cli_json.py doing its job -- do not regen to silence it; fix the regression instead.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from smartchem.cli import main
from smartchem.service import response_schema

_FIXTURES = Path(__file__).parent / "fixtures" / "cli_json"

# keep in lock-step with _GOLDEN_CASES in tests/test_cli_json.py
_CASES = {
    "recompile_routes_found.json": ["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--json"],
    "recompile_no_route.json": ["recompile", "acetic anhydride", "--elements", "--max-depth", "2", "--json"],
    "recompile_invalid.json": ["recompile", "not-a-real-name-zzz", "--json"],
    "decompile_paracetamol.json": ["decompile", "C8H9NO2", "--json"],
    "decompile_smiles_paracetamol.json": ["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles", "--json"],
}


def _cli_json(argv: list[str]) -> dict:
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        main(argv)
    return json.loads(out.getvalue().strip())


def _dump(name: str, obj: object) -> None:
    (_FIXTURES / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"wrote {name}")


def main_regen() -> None:
    _FIXTURES.mkdir(parents=True, exist_ok=True)
    _dump("response_schema.json", response_schema())
    for name, argv in _CASES.items():
        _dump(name, _cli_json(argv))


if __name__ == "__main__":
    main_regen()
