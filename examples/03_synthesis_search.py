"""Example 03 -- bounded retrosynthesis of methyl acetate through the service seam.

Shows: build_recompile_request -> run_compilation.  Reads outcome, exit code, standard status and the candidate
routes.  Candidates are FORMAL_CANDIDATEs (conservation + structure checked), not vetted lab procedures.
"""
from smartchem.service import build_recompile_request, run_compilation


def main() -> int:
    request = build_recompile_request("smiles:CC(=O)OC", max_depth=3, max_routes=50)
    response = run_compilation(request)
    print(f"outcome={response.outcome.value} exit_code={response.exit_code} status={response.standard_status}")
    print(f"routes={len(response.candidates)}")
    for cand in response.candidates:
        print(f"  [{cand.readiness_tier}] {cand.equation}")
    print(f"result_digest={response.result_digest[:16]}...")
    return response.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
