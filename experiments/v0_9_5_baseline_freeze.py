"""V0.9.5-FREEZE-01: the behavioural fingerprint of merged 0.9 -- the yardstick every 0.9.5 incision is judged by.

A refactor that cannot prove intended equality is not a refactor; it is a semantic change needing its own
adjudication.  This harness records, for a FROZEN corpus, every externally observable fact the 0.9.5 consolidation
promises not to move -- and, in ``--check`` mode, recomputes them and prints every drifted key.

Recorded (all as canonical sha256 fingerprints plus the compact semantic projection they hash):

* request payloads + semantic digests for every corpus request;
* service responses: outcome, exit code, search-space status, result / capability-question / search-receipt digests,
  the standard-14.3 ``response_semantic_fields``, ranked route digests IN ORDER with fit status, readiness tier and
  every capability axis, DAG dossiers, admissible set, and the canonical THICK and THIN wire payload hashes;
* load behaviour: plain / pinned + verified-admission / thin loads of every canonical payload (accepted? round-trip
  byte-identical?);
* the refusal matrix: a fixed tamper set (schema id, key deletion/insertion, digest flip, transport relabel, verdict
  relabel, dossier deletion, pin mismatches, signature policy) -> accepted or (exception class, message head);
* legacy v0.8: every real fixture under tests/fixtures/v08 (requests, responses, tamper) -> load outcome;
* CLI: the committed CLI-JSON goldens (file hashes + live-regeneration equality) and HUMAN renders (stdout hash + exit
  code) for the front-door / recompile / decompile / plan / refusal surfaces;
* both machine-checked ledgers (transport ledger, capability field coverage) + the response schema descriptor.

Wall-clock timings are recorded under ``timings`` and are NEVER compared (non-deterministic by nature).

Run:  .venv/bin/python experiments/v0_9_5_baseline_freeze.py --write   # (re)freeze -- only on a sanctioned tree
      .venv/bin/python experiments/v0_9_5_baseline_freeze.py --check   # recompute everything, diff, exit 1 on drift
      .venv/bin/python experiments/v0_9_5_baseline_freeze.py --check --quick   # skip the slow isopentyl family
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FREEZE_JSON = REPO / "docs" / "research" / "V0_9_5_BASELINE_BEHAVIOR_FREEZE.json"
SLOW = "slow"


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha(obj) -> str:
    data = obj if isinstance(obj, (bytes, str)) else canon(obj)
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def _val(x):
    return getattr(x, "value", x)


# --------------------------------------------------------------------------------------------------------------------
# the frozen corpus (the exact requests the 0.9 gates already drive; nothing invented)
# --------------------------------------------------------------------------------------------------------------------
def _corpus():
    from smartchem.capability.presets import isopentyl_capability_fit_bench
    from smartchem.identity_parse import InputKind
    from smartchem.process_constraints import ProcessBounds
    from smartchem.service import TransformGrammar

    iso = dict(helper_reagents=("water", "acetic acid"), stock_materials=("isopentyl alcohol",))
    aspirin = dict(max_depth=1, helper_reagents=("acetic acid", "water"),
                   stock_materials=("salicylic acid", "acetic anhydride"), max_temperature_k=350.0)
    paracetamol = dict(max_depth=1, helper_reagents=("acetic acid", "water"),
                       stock_materials=("4-aminophenol", "acetic anhydride"))
    return [
        # (case id, cost class, builder, target, kwargs)
        ("methyl_acetate", "fast", "recompile", "smiles:CC(=O)OC", dict(max_depth=2)),
        ("methyl_acetate@poor-man", "fast", "recompile", "smiles:CC(=O)OC", dict(max_depth=2, capability_profile="poor-man")),
        ("methyl_acetate@research-lab", "fast", "recompile", "smiles:CC(=O)OC",
         dict(max_depth=2, capability_profile="research-lab")),
        ("aspirin", "fast", "recompile", "smiles:CC(=O)Oc1ccccc1C(=O)O", aspirin),
        ("aspirin@poor-man", "fast", "recompile", "smiles:CC(=O)Oc1ccccc1C(=O)O",
         dict(aspirin, capability_profile="poor-man")),
        ("paracetamol", "fast", "recompile", "smiles:CC(=O)Nc1ccc(O)cc1", paracetamol),
        ("paracetamol@research-lab", "fast", "recompile", "smiles:CC(=O)Nc1ccc(O)cc1",
         dict(paracetamol, capability_profile="research-lab")),
        ("paracetamol_incomplete", "fast", "recompile", "paracetamol", dict(max_depth=1, cut_budget=1)),
        ("methyl_salicylate", "fast", "recompile", "methyl salicylate",
         dict(max_depth=1, helper_reagents=("water",), stock_materials=("salicylic acid", "methanol"))),
        ("diels_alder_control", "fast", "recompile", "C1CC=CCC1",
         dict(input_kind=InputKind.SMILES, helper_reagents=(), stock_materials=("C=CC=C", "C=C"),
              algebra_profile="certified-route-v07")),
        ("bromine", "fast", "recompile", "bromine", dict(max_depth=1)),
        ("bromine_smiles", "fast", "recompile", "smiles:BrBr", dict(max_depth=1)),
        ("invalid_name", "fast", "recompile", "not-a-real-name-zzz", {}),
        ("decompile_paracetamol", "fast", "decompile", "C8H9NO2", {}),
        ("isopentyl", SLOW, "recompile", "isopentyl acetate", iso),
        ("isopentyl@research-lab", SLOW, "recompile", "isopentyl acetate", dict(iso, capability_profile="research-lab")),
        ("isopentyl@poor-man", SLOW, "recompile", "isopentyl acetate", dict(iso, capability_profile="poor-man")),
        ("isopentyl@custom-fit-bench", SLOW, "recompile", "isopentyl acetate",
         dict(iso, capability_profile=isopentyl_capability_fit_bench())),
        ("methyl_acetate_dag", "fast", "recompile", "smiles:CC(=O)OC",
         dict(max_depth=2, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, helper_reagents=("water", "acetic acid"),
              process=ProcessBounds.of(max_total_minutes=30.0))),
        ("isopentyl_dag_quick", SLOW, "recompile", "isopentyl acetate",
         dict(grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, process=ProcessBounds.quick())),
        ("isopentyl_dag", SLOW, "recompile", "isopentyl acetate",
         dict(iso, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT)),
        ("isopentyl_dag@poor-man", SLOW, "recompile", "isopentyl acetate",
         dict(iso, grammar=TransformGrammar.CAPPED_SCISSION_CONVERGENT, capability_profile="poor-man")),
    ]


def _outcome_of(fn):
    """Run ``fn``; return ('ok', value) or ('refused', {exc, msg}) -- the refusal CLASS and message head are frozen."""
    try:
        return "ok", fn()
    except Exception as exc:  # noqa: BLE001 -- the class IS the recorded fact
        return "refused", {"exc": type(exc).__name__, "msg": str(exc)[:240]}


def _response_record(resp) -> dict:
    from smartchem.service import response_semantic_fields, response_to_payload

    thick = response_to_payload(resp)
    thin = response_to_payload(resp, include_replay=False)
    routes = []
    for d, dp in zip(resp.ranked_route_dossiers, thick["ranked_route_dossiers"]):
        ca = d.capability_assessment
        routes.append({
            "route_digest": d.route_digest,
            "fit_status": _val(d.fit_status),
            "readiness_tier": dp.get("readiness_tier"),
            "capability": None if ca is None else {
                "overall": _val(ca.overall),
                "axes": {ax: _val(getattr(ca, ax).status) for ax in (
                    "material", "equipment", "physical", "process", "containment", "ventilation", "measurement",
                    "waste", "procurement", "attention_care", "monetary")},
                "digest": ca.digest if hasattr(ca, "digest") else None,
            },
            "dossier_sha": sha(dp),
        })
    dags = [{"fit_status": dp.get("fit_status"), "dossier_sha": sha(dp)} for dp in thick["ranked_dag_dossiers"]]
    return {
        "outcome": _val(resp.outcome),
        "exit_code": resp.exit_code,
        "search_space_status": _val(thick.get("search_space_status")),
        "result_digest": resp.result_digest,
        "wire_result_digest": thick["result_digest"],
        "thin_wire_result_digest": thin["result_digest"],
        "capability_question_digest": thick.get("capability_question_digest"),
        "semantic_fields_sha": sha(response_semantic_fields(resp)),
        "admissible_route_digests": list(thick["admissible_route_digests"]),
        "routes": routes,
        "dags": dags,
        "frontier_sha": sha(thick["affordability_frontier"]),
        "ir_sha": sha(thick["compilation_ir"]),
        "thick_payload_sha": sha(thick),
        "thin_payload_sha": sha(thin),
    }, thick, thin


def _load_records(resp, thick, thin) -> dict:
    from smartchem.service import response_from_payload, response_to_payload

    req = resp.request
    # the consumer pins exactly as the tests' own `_pins` helper does: the request's SEMANTIC digest plus the question
    # digest (None is itself a pin -- to NOT_REQUESTED -- distinct from the unpinned sentinel)
    pins = {"expected_request_digest": req.semantic_digest,
            "expected_capability_question_digest": req.capability_question_digest}
    out = {}
    for name, payload, kw in (
        ("plain_thick", thick, {}),
        ("pinned_va_thick", thick, dict(require_verified_admission=True, **pins)),
        ("plain_thin", thin, {}),
    ):
        status, val = _outcome_of(lambda p=payload, k=kw: response_from_payload(copy.deepcopy(p), **k))
        if status == "ok":
            reemit = response_to_payload(val, include_replay=(payload is thick))
            out[name] = {"accepted": True, "round_trip_identical": sha(reemit) == sha(payload)}
        else:
            out[name] = {"accepted": False, **val}
    return out


def service_section(quick: bool, timings: dict) -> dict:
    from smartchem.service import (build_decompile_request, build_recompile_request, request_to_payload,
                                   run_compilation)

    out = {}
    for cid, cost, builder, target, kw in _corpus():
        if quick and cost == SLOW:
            continue
        t0 = time.time()
        build = build_recompile_request if builder == "recompile" else build_decompile_request
        status, req = _outcome_of(lambda: build(target, **kw))
        rec: dict = {"builder": builder, "target": target}
        if status != "ok":
            rec["build"] = req
            out[cid] = rec
            continue
        rec["request_payload_sha"] = sha(request_to_payload(req))
        rec["request_semantic_digest"] = req.semantic_digest
        rec["request_capability_question_digest"] = req.capability_question_digest
        status, resp = _outcome_of(lambda: run_compilation(req))
        if status != "ok":
            rec["run"] = resp
            out[cid] = rec
            continue
        rec["response"], thick, thin = _response_record(resp)
        t1 = time.time()
        rec["load"] = _load_records(resp, thick, thin)
        timings[cid] = {"compile_s": round(t1 - t0, 2), "load_s": round(time.time() - t1, 2)}
        out[cid] = rec
        print(f"  [service] {cid}: {rec['response']['outcome']} ({timings[cid]})", flush=True)
    return out


def refusal_section() -> dict:
    """A fixed tamper matrix on the cheap methyl acetate canonical payload (the refusal CLASS + message head)."""
    from smartchem.service import (build_recompile_request, response_from_payload, response_to_payload,
                                   run_compilation)

    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, capability_profile="poor-man"))
    base = response_to_payload(resp)
    thin = response_to_payload(resp, include_replay=False)

    def mut(fn, src=None):
        p = copy.deepcopy(base if src is None else src)
        fn(p)
        return p

    def flip(h: str) -> str:
        return h[:-1] + ("0" if h[-1] != "0" else "1")

    def set_fit(p):
        p["ranked_route_dossiers"][0]["fit_status"] = "FITS"

    cases = {
        "T01_unknown_schema_id": (mut(lambda p: p.__setitem__("schema_version", "smartchem.service/compilation-response-v0")), {}),
        "T02_delete_transport_mode": (mut(lambda p: p.pop("transport_mode")), {}),
        "T03_insert_unknown_key": (mut(lambda p: p.__setitem__("zzz", 1)), {}),
        "T04_flip_result_digest": (mut(lambda p: p.__setitem__("result_digest", flip(p["result_digest"]))), {}),
        "T05_relabel_transport_thin": (mut(lambda p: p.__setitem__("transport_mode", "THIN_ADVISORY")), {}),
        "T06_relabel_fit_status": (mut(set_fit), {}),
        "T07_request_pin_mismatch": (base, {"expected_request_digest": "0" * 64}),
        "T08_capability_pin_mismatch": (base, {"expected_capability_question_digest": "0" * 64}),
        "T09_require_signature_without_key": (base, {"require_signature": True}),
        "T10_unsigned_under_required_signature": (base, {"require_signature": True, "verification_key": b"k" * 32}),
        "T11_thin_under_verified_admission": (thin, {"require_verified_admission": True}),
        "T12_thin_plain_is_advisory": (thin, {}),
        "T13_delete_first_dossier": (mut(lambda p: p["ranked_route_dossiers"].pop(0)), {}),
        "T14_not_a_dict": ([base], {}),
        "T15_thin_relabel_fit_status": (mut(set_fit, thin), {}),
    }
    out = {}
    for name, (payload, kw) in cases.items():
        status, val = _outcome_of(lambda p=payload, k=kw: response_from_payload(copy.deepcopy(p), **k))
        out[name] = {"accepted": True} if status == "ok" else {"accepted": False, **val}
    return out


def legacy_section() -> dict:
    from smartchem.service import request_from_payload, response_from_payload

    root = REPO / "tests" / "fixtures" / "v08"
    out = {}
    for path in sorted(root.rglob("*.json")):
        rel = str(path.relative_to(root))
        data = json.loads(path.read_text())
        rec = {"file_sha": sha(path.read_bytes())}
        if "schema_descriptor" in path.name:  # a frozen descriptor document, not a loadable payload
            out[rel] = rec
            continue
        if rel.startswith("plan_"):
            data = data.get("compilation", data)
        kind = "request" if "request_" in path.name and "response" not in path.name else "response"
        loader = request_from_payload if kind == "request" else response_from_payload
        status, val = _outcome_of(lambda d=data: loader(copy.deepcopy(d)))
        if status == "ok":
            rec["accepted"] = True
            if kind == "response":
                rec["outcome"] = _val(val.outcome)
                rec["result_digest"] = val.result_digest
                rec["is_legacy_v08"] = bool(getattr(val, "is_legacy_v08", False))
            else:
                rec["semantic_digest"] = val.semantic_digest
        else:
            rec.update({"accepted": False, **val})
        out[rel] = rec
    return out


_CLI_HUMAN = {
    "recompile_methyl_acetate": ["recompile", "smiles:CC(=O)OC", "--max-depth", "2"],
    "recompile_methyl_acetate_poor_man": ["recompile", "smiles:CC(=O)OC", "--max-depth", "2",
                                          "--capability-profile", "poor-man"],
    "recompile_no_route": ["recompile", "acetic anhydride", "--elements", "--max-depth", "2"],
    "recompile_invalid": ["recompile", "not-a-real-name-zzz"],
    "decompile_paracetamol": ["decompile", "C8H9NO2"],
    "plan_hydrate_unicode": ["plan", "CuSO4·5H2O"],
    "plan_charged_ion": ["plan", "SO4^2-"],
    "plan_ambiguous_formula": ["plan", "C2H6O"],
    "plan_unknown_flag_refused": ["plan", "methyl acetate", "--max-depth", "2"],
    "plan_name": ["plan", "methyl acetate"],
    "plan_malformed": ["plan", "C2H(("],
    "plan_diels_alder_json": ["plan", "--algebra", "certified-route-v07", "--no-helper-reagents", "--smiles",
                              "C1CC=CCC1", "--json"],
}


def _cli(argv):
    from smartchem.cli import main

    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = main(list(argv))
    except SystemExit as exc:  # argparse refusals
        rc = exc.code
    return rc, out.getvalue(), err.getvalue()


def cli_section() -> dict:
    sys.path.insert(0, str(REPO / "tests"))
    import regen_cli_json as regen  # the committed golden table (kept in lock-step with tests/test_cli_json.py)
    from smartchem.service import response_schema

    gold_dir = REPO / "tests" / "fixtures" / "cli_json"
    goldens = {}
    for name, argv in regen._CASES.items():
        rc, out, _err = _cli(argv)
        live = json.loads(out.strip())
        committed = json.loads((gold_dir / name).read_text())
        goldens[name] = {"file_sha": sha((gold_dir / name).read_bytes()), "exit_code": rc,
                         "live_equals_golden": live == committed, "live_sha": sha(live)}
    schema_committed = json.loads((gold_dir / "response_schema.json").read_text())
    goldens["response_schema.json"] = {"file_sha": sha((gold_dir / "response_schema.json").read_bytes()),
                                       "live_equals_golden": response_schema() == schema_committed}
    human = {}
    for name, argv in _CLI_HUMAN.items():
        rc, out, err = _cli(argv)
        human[name] = {"exit_code": rc, "stdout_sha": sha(out), "stderr_sha": sha(err), "stdout_lines": out.count("\n")}
    return {"goldens": goldens, "human": human}


def ledger_section() -> dict:
    from smartchem.capability.coverage import FIELD_COVERAGE, missing_coverage
    from smartchem.service import COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR, response_schema
    from smartchem.transport_ledger import TRANSPORT_LEDGER, status_counts

    ledger = {container: {f: {"status": _val(e.status), "checks": list(e.checks), "thin": _val(e.thin),
                              "advisory_when": e.advisory_when}
                          for f, e in sorted(fields.items())}
              for container, fields in sorted(TRANSPORT_LEDGER.items())}
    coverage = {f"{t}.{f}": {"primary": _val(c.primary), "also": sorted(_val(a) for a in c.also)}
                for (t, f), c in sorted(FIELD_COVERAGE.items())}
    return {
        "transport_ledger_sha": sha(ledger),
        "transport_ledger_entries": sum(len(v) for v in ledger.values()),
        "transport_status_counts": {_val(k): v for k, v in sorted(status_counts().items(), key=lambda kv: _val(kv[0]))},
        "field_coverage_sha": sha(coverage),
        "field_coverage_entries": len(coverage),
        "missing_coverage": list(missing_coverage()),
        "response_schema_sha": sha(response_schema()),
        "response_schema_descriptor_id": COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR,
    }


def schema_ids() -> dict:
    import smartchem
    from smartchem import service as s

    return {"package": smartchem.__version__, "request": s.COMPILATION_REQUEST_SCHEMA,
            "response": s.COMPILATION_RESPONSE_SCHEMA, "route_summary": s.RANKED_ROUTE_SUMMARY_SCHEMA,
            "dag_summary": s.RANKED_DAG_SUMMARY_SCHEMA, "descriptor": s.COMPILATION_RESPONSE_SCHEMA_DESCRIPTOR}


# Receipts measured by the 0.9 gates (Round V §7.16) and re-confirmed by the pre-merge smoke on 2026-09-29.  They are
# RECORDED facts (not recomputed here -- each has its own committed harness); --check never compares them.
RECEIPTS = {
    "mutation": "ACTIVE 217/217 killed, 0 survived | RETIRED 4 (0 void) | DEFERRED 0 (Round V, code tip d6c7edc); "
                "pre-merge live subset 14/14 killed incl. D29 M212-M217 + all retirement replacements",
    "full_suite": "6529 collected / 6483 passed / 0 failed / 0 errors / 46 skipped, 35 batches (d6c7edc)",
    "held_out": "12 PASS / 1 lawful DIVERGE / 0 FAIL (experiments/v0_9_heldout_saponification_probe.py, re-run 2026-09-29)",
    "noninterference": "HOLDS on isopentyl acetate: 27 candidates, search receipt ea1c8afaaa1b9053.., IR 17c1c09cf357589a.. "
                       "(experiments/v0_9_search_noninterference.py, re-run 2026-09-29)",
    "funnel": "34/34 properties; 7/7 profile divergence; zero CAPABILITY_FIT",
}


def build(quick: bool) -> dict:
    timings: dict = {}
    print("[freeze] ledgers + schema ids", flush=True)
    doc = {"schema_ids": schema_ids(), "ledgers": ledger_section()}
    print("[freeze] CLI goldens + human renders", flush=True)
    doc["cli"] = cli_section()
    print("[freeze] legacy v0.8 fixtures", flush=True)
    doc["legacy_v08"] = legacy_section()
    print("[freeze] refusal matrix", flush=True)
    doc["refusals"] = refusal_section()
    print("[freeze] service corpus" + (" (quick)" if quick else ""), flush=True)
    doc["service"] = service_section(quick, timings)
    doc["receipts"] = RECEIPTS
    doc["timings"] = timings
    return doc


def _diff(frozen, live, path=""):
    if isinstance(frozen, dict) and isinstance(live, dict):
        for k in sorted(set(frozen) | set(live)):
            if k in ("timings", "receipts"):
                continue
            if k not in live:
                yield f"{path}/{k}: MISSING in live"
            elif k not in frozen:
                yield f"{path}/{k}: NEW in live"
            else:
                yield from _diff(frozen[k], live[k], f"{path}/{k}")
    elif frozen != live:
        yield f"{path}: frozen={canon(frozen)[:200]} live={canon(live)[:200]}"


def main(argv: list[str]) -> int:
    quick = "--quick" in argv
    if "--write" in argv:
        if quick:
            print("refusing --write --quick: the freeze must be complete")
            return 2
        doc = build(quick=False)
        FREEZE_JSON.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        print(f"wrote {FREEZE_JSON.relative_to(REPO)} (sha256 {sha(FREEZE_JSON.read_bytes())[:16]}..)")
        return 0
    if "--check" in argv:
        frozen = json.loads(FREEZE_JSON.read_text())
        live = build(quick=quick)
        if quick:  # compare only the cases the quick run computed
            frozen["service"] = {k: v for k, v in frozen["service"].items() if k in live["service"]}
        drift = list(_diff(frozen, live))
        for line in drift:
            print("DRIFT", line)
        print(f"\n{'NO DRIFT' if not drift else f'{len(drift)} DRIFTED KEY(S)'} "
              f"({len(live['service'])} service cases, {len(live['refusals'])} refusals, "
              f"{len(live['legacy_v08'])} legacy fixtures, {len(live['cli']['human'])} human renders)")
        return 0 if not drift else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
