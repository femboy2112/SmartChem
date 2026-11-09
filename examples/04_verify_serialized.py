"""Example 04 -- the verifiable-dossier contract: serialize a response, load it back, check it round-trips.

Shows: serialize_response ships a canonical JSON wire (with a replay payload); deserialize_response RE-VERIFIES
it on load and returns an equal response.  A tampered wire is refused rather than trusted.
"""
from smartchem.service import (
    build_recompile_request, deserialize_response, run_compilation, serialize_response,
)


def main() -> int:
    original = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=3, max_routes=50))
    wire = serialize_response(original)
    print(f"wire bytes={len(wire)}")
    loaded = deserialize_response(wire)
    assert loaded.result_digest == original.result_digest
    assert loaded.outcome is original.outcome
    assert [c.equation for c in loaded.candidates] == [c.equation for c in original.candidates]
    print(f"round-trip OK: outcome={loaded.outcome.value} result_digest={loaded.result_digest[:16]}...")
    # Control: edit one product formula inside the canonical wire; the loader must NOT hand back a trusted response.
    tampered = wire.replace("C3H6O2 + H2O", "C3H6O3 + H2O", 1)
    assert tampered != wire
    try:
        deserialize_response(tampered)
    except Exception as exc:  # noqa: BLE001 -- we only report which refusal fired
        print(f"tampered wire REFUSED: {type(exc).__name__}: {str(exc)[:90]}")
        return 0
    print("tampered wire was accepted (unexpected)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
