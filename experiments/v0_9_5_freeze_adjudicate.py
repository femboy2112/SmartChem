"""V0.9.5-FREEZE-02: adjudicate a sanctioned semantic step -- does it move any VERDICT, or only identities?

``v0_9_5_baseline_freeze.py --check`` reports every drifted key, and a versioned change (a schema-id bump, a new
digest-covered field) legitimately moves hundreds of digests.  This tool projects two freeze documents onto their
VERDICTS ONLY -- everything a consumer acts on -- and reports any difference; digests, payload hashes and refusal
message text are deliberately excluded (the refusal CLASS is kept).

Projected per service case: outcome, exit code, search-space status, route count and, IN ORDER, each route's fit
status, readiness tier and capability overall + all 11 axes; DAG count and each DAG's fit status; the admissible-set
size; the load outcomes (accepted? round-trip identical? refusal class).  Plus: the refusal matrix (accepted / class),
every legacy fixture's load outcome, the human renders' exit codes, the goldens' live-equals-golden flags, and the
ledgers' entry and status counts.

Run:  .venv/bin/python experiments/v0_9_5_freeze_adjudicate.py FROZEN.json LIVE.json
      (LIVE.json from ``v0_9_5_baseline_freeze.py --check --dump LIVE.json``).  Exit 0 iff no verdict moved.
"""
from __future__ import annotations

import json
import sys


def _routes(rows):
    return [(r["fit_status"], r["readiness_tier"],
             None if r["capability"] is None else (r["capability"]["overall"], tuple(sorted(r["capability"]["axes"].items()))))
            for r in rows]


def project(doc: dict) -> dict:
    out: dict = {}
    for cid, rec in doc["service"].items():
        resp = rec.get("response")
        if resp is None:
            out[f"service/{cid}"] = {"build": rec.get("build", {}).get("exc"), "run": rec.get("run", {}).get("exc")}
            continue
        out[f"service/{cid}"] = {
            "outcome": resp["outcome"], "exit_code": resp["exit_code"],
            "search_space_status": resp["search_space_status"],
            "routes": _routes(resp["routes"]), "dags": [d["fit_status"] for d in resp["dags"]],
            "admissible": len(resp["admissible_route_digests"]),
            "load": {k: (v["accepted"], v.get("round_trip_identical"), v.get("exc")) for k, v in rec["load"].items()},
        }
    out["refusals"] = {k: (v["accepted"], v.get("exc")) for k, v in doc["refusals"].items()}
    out["legacy"] = {k: (v.get("accepted"), v.get("outcome"), v.get("exc")) for k, v in doc["legacy_v08"].items()}
    out["human_exit"] = {k: v["exit_code"] for k, v in doc["cli"]["human"].items()}
    out["goldens_current"] = {k: v.get("live_equals_golden") for k, v in doc["cli"]["goldens"].items()}
    led = doc["ledgers"]
    out["ledgers"] = {"transport_entries": led["transport_ledger_entries"],
                      "transport_status_counts": led["transport_status_counts"],
                      "missing_coverage": led["missing_coverage"]}
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    frozen, live = (project(json.load(open(path))) for path in argv)
    moved = []
    for key in sorted(set(frozen) | set(live)):
        a, b = frozen.get(key), live.get(key)
        if a != b:
            moved.append(key)
            print(f"VERDICT MOVED {key}:\n  frozen={json.dumps(a, default=str)[:600]}\n  live  ={json.dumps(b, default=str)[:600]}")
    print(f"\n{'NO VERDICT MOVED' if not moved else f'{len(moved)} VERDICT GROUP(S) MOVED'} "
          f"({len(frozen)} projected groups)")
    return 0 if not moved else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
