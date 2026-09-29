"""V0.9-NONINTERFERENCE-01 (Round V X-high, Part IX): capability selection never perturbs the chemistry search.

**Listen, Morty: the capability layer is a PROJECTION. It reads the search; it never writes it.** For one chemistry
request under four capability contexts -- no profile, research-lab, poor-man, and a fully-declared Custom bench -- this
harness compiles the real request through the real service and requires EXACT equality of everything the search
produced (normalized target, semantic digest, transform registry digest, search receipt digest incl. its telemetry,
IR digest, candidate digests in order, structural candidates, completeness, search-space status, outcome, ranked
routes), while the capability-specific identities (request digest, capability-question digest, result digest,
per-route assessments) differ BY DESIGN. Exit 0 iff every must-equal field is equal.

Run:  .venv/bin/python experiments/v0_9_search_noninterference.py "isopentyl acetate"
      .venv/bin/python experiments/v0_9_search_noninterference.py "smiles:CC(=O)OC"
"""
import sys
import time

from smartchem.capability.presets import isopentyl_capability_fit_bench, poor_man, research_lab
from smartchem.service import build_recompile_request, response_to_payload, run_compilation

target = sys.argv[1]
kw = {}
if target == "isopentyl acetate":
    kw = dict(helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",))
else:
    kw = dict(max_depth=2)
contexts = {
    "none": None,
    "research-lab": research_lab(),
    "poor-man": poor_man(),
    "custom(fit-bench)": isopentyl_capability_fit_bench(),
}
rows = {}
for name, prof in contexts.items():
    t = time.time()
    req = build_recompile_request(target, capability_profile=prof, **kw)
    resp = run_compilation(req)
    ir = resp.compilation_ir
    telemetry = None
    if ir is not None:
        rec = ir.search_receipt
        telemetry = {k: getattr(rec, k) for k in ("expanded_nodes", "generated_nodes", "max_depth_reached",
                                                   "candidate_count", "complete_within_bounds")
                     if hasattr(rec, k)}
    rows[name] = dict(
        normalized_target=str(req.normalized_identity),
        semantic_digest=req.semantic_digest,
        request_digest=req.digest,
        transform_registry_digest=None if ir is None else ir.transform_registry_digest,
        search_receipt_digest=resp.search_receipt_digest,
        candidate_digests=None if ir is None else tuple(c.candidate_digest for c in ir.candidates),
        structural_candidates=None if ir is None else len(ir.structural_candidates),
        ir_digest=None if ir is None else ir.digest,
        complete=None if ir is None else ir.complete_within_bounds,
        search_space_status=resp.search_space_status,
        outcome=resp.outcome.value,
        ranked=tuple(d.route_digest for d in resp.ranked_route_dossiers),
        telemetry=telemetry,
        capability_question_digest=resp.capability_question_digest,
        result_digest=resp.result_digest,
        overall=tuple((d.capability_assessment.overall.value if d.capability_assessment else None)
                      for d in resp.ranked_route_dossiers),
        wire_result_digest=response_to_payload(resp)["result_digest"],
    )
    print(f"{name}: compiled in {time.time() - t:.1f}s", flush=True)

base = rows["none"]
must_equal = ("normalized_target", "semantic_digest", "transform_registry_digest", "search_receipt_digest",
              "candidate_digests", "structural_candidates", "ir_digest", "complete", "search_space_status", "outcome",
              "ranked", "telemetry")
expected_differ = ("request_digest", "capability_question_digest", "result_digest", "overall", "wire_result_digest")
print(f"\nTARGET {target!r}")
for key in must_equal:
    vals = {n: r[key] for n, r in rows.items()}
    same = all(v == base[key] for v in vals.values())
    shown = base[key]
    if key == "candidate_digests" and shown is not None:
        shown = f"{len(shown)} digests, first {shown[0][:16]}.. last {shown[-1][:16]}.."
    elif key == "ranked":
        shown = f"{len(shown)} ranked"
    elif isinstance(shown, str) and len(shown) > 40:
        shown = shown[:16] + ".."
    print(f"  [{'EQUAL' if same else 'DIFFER!!'}] {key}: {shown}")
for key in expected_differ:
    print(f"  [by design] {key}: " + " | ".join(
        f"{n}={(str(r[key])[:16] if not isinstance(r[key], tuple) else sorted(set(map(str, r[key]))))}"
        for n, r in rows.items()))

failed = [key for key in must_equal if any(r[key] != base[key] for r in rows.values())]
print("\nNONINTERFERENCE " + ("HOLDS" if not failed else f"VIOLATED on {failed}"))
sys.exit(1 if failed else 0)
