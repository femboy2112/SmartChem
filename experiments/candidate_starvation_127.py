"""CANDIDATE-STARVATION-127 -- does the raw ``max_routes`` cap starve a recognized route? (OPERATION SMARTCHEM §4)

Issue #127 hypothesises that ``search_routes`` applies ``max_routes`` while collecting RAW generated routes --
BEFORE reaction-TYPE recognition -- so formally-conserving FICTIONS (#109) could exhaust the result slots before a
real, recognized route is examined.  This is the committed MEASUREMENT of that hypothesis (the directive: build the
benchmark BEFORE widening generation, and add a scheduling fix ONLY IF a meaningful failure is observed).

Method.  On deterministic benign targets that return BOTH a recognized route and generated fictions under the
production poor-man pool, sweep ``max_routes`` from 1 upward and measure RECOGNIZED-RECALL = (recognized routes in
the returned set) / (recognized routes at a generous cap).  A route is "recognized" iff
``route_reaction_type_blockers(route) == ()`` (every step positively vouched by the oracle).  Also measured: the
index (digest-order position) of each recognized route in the returned set, the receipt's honest truncation counts,
and ORDER-INVARIANCE (permuting the reagent/commodity input order must not change the returned set).

MEASURED RESULT (poor-man pool, capped-scission grammar, 2026-10-13).  Recognized-recall is **1.0 at every cap >= 1**
for every target: the recognized single condensation is a 1-STEP route to commodity precursors and enumerates FIRST
(index 0) in the digest-sorted order, while the fictions are MULTI-step homologation chains occupying later slots.
The hypothesised starvation is therefore **NOT observed** in this grammar/pool -- no scheduling fix is warranted yet.
The search is also order-INVARIANT (sets keyed by ``_ident`` + digest-sorted enumeration), so shuffled reagent/
commodity order yields an identical returned set.  This harness is the regression GUARD: if a future grammar widens
to emit a 1-step fiction that sorts before a recognized route, recognized-recall drops below 1.0 and ``validate()``
turns red -- the trigger to build the type-gated / fair-provider scheduling #127 describes.

Run: ``.venv/bin/python -m experiments.candidate_starvation_127``
"""
from __future__ import annotations

from dataclasses import dataclass

from smartchem.service import (
    build_recompile_request, _canonical_helper_molecules, _canonical_commodities, resolve_algebra_profile,
)
from smartchem.identity_parse import resolve_identity
from smartchem.experiment.routes import search_routes
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers

#: benign targets that return a recognized route AND fictions under the poor-man pool at a generous cap.
TARGETS = (
    ("smiles:CCOC(C)=O", "ethyl acetate"),       # esterification (acetic + ethanol), both commodities; + 4 fictions
    ("smiles:CC(=O)OC", "methyl acetate"),        # esterification (acetic + methanol); + 1 fiction
    ("smiles:CCOCC", "diethyl ether"),            # etherification (2 ethanol); + 2 fictions
    ("smiles:COC", "dimethyl ether"),             # etherification (2 methanol); holdout
    ("smiles:CN(C)C", "trimethylamine"),          # N-alkylation; holdout
)
_HIGH_CAP = 1000
_SMALL_CAPS = (1, 2, 3, 5)


def _recognized(route) -> bool:
    return not route_reaction_type_blockers(route)


@dataclass(frozen=True)
class _Setup:
    name: str
    target: object
    reagents: tuple
    available: tuple
    commodities: tuple
    registry: object
    max_depth: int
    cut_budget: int


def _setup(target_input: str, name: str) -> _Setup:
    req = build_recompile_request(target_input, capability_profile="poor-man")
    reagents, available = _canonical_helper_molecules(req)
    commodities = _canonical_commodities(req)
    registry = resolve_algebra_profile(req.algebra_profile)
    target = resolve_identity(req.target_input, req.input_kind).molecule.canonical()
    return _Setup(name, target, reagents, available, commodities, registry,
                  req.search_bounds.value("max_depth"), req.search_bounds.value("cut_budget"))


def _search(s: _Setup, cap: int, reagents=None, commodities=None):
    return search_routes(
        s.target, reagents=s.reagents if reagents is None else reagents,
        available=s.available, commodities=s.commodities if commodities is None else commodities,
        max_depth=s.max_depth, max_routes=cap, cut_budget=s.cut_budget, registry=s.registry,
    )


def measure_target(target_input: str, name: str) -> dict:
    s = _setup(target_input, name)
    base = _search(s, _HIGH_CAP)
    rec_idx = [i for i, r in enumerate(base.routes) if _recognized(r)]
    total_rec = len(rec_idx)
    # cap sweep: recognized-recall at each small cap
    sweep = {}
    for cap in _SMALL_CAPS:
        res = _search(s, cap)
        surv = sum(1 for r in res.routes if _recognized(r))
        sweep[cap] = {
            "returned": len(res.routes),
            "recognized_survived": surv,
            "recall": (surv / total_rec) if total_rec else None,
            "saturated": res.receipt.result_limit_saturated,
        }
    # order-invariance: a duplicated/permuted reagent pool and a reversed commodity order give the SAME returned set
    perm = _search(s, _HIGH_CAP, reagents=s.reagents + s.reagents,
                   commodities=tuple(reversed(s.commodities)))
    order_invariant = {r.digest for r in perm.routes} == {r.digest for r in base.routes}
    return {
        "name": name,
        "high_cap_returned": len(base.routes),
        "recognized_total": total_rec,
        "fiction_total": len(base.routes) - total_rec,
        "recognized_indices": rec_idx,                 # digest-order positions of recognized routes
        "min_cap_full_recall": next((c for c in _SMALL_CAPS if sweep[c]["recall"] == 1.0), None),
        "recall_at_cap1": sweep[_SMALL_CAPS[0]]["recall"],
        "candidates_emitted": base.receipt.candidates_emitted,
        "order_invariant": order_invariant,
        "sweep": sweep,
    }


def measure() -> dict:
    rows = [measure_target(tin, name) for tin, name in TARGETS]
    starved = [r for r in rows if r["recognized_total"] and r["recall_at_cap1"] != 1.0]
    return {
        "rows": rows,
        "any_starvation_observed": bool(starved),
        "starved_targets": [r["name"] for r in starved],
        "all_order_invariant": all(r["order_invariant"] for r in rows),
        "targets_with_recognized_route": sum(1 for r in rows if r["recognized_total"]),
    }


def validate() -> bool:
    """Non-regression: every target that has a recognized route keeps FULL recognized-recall even at cap=1 (the
    recognized route is never starved by the raw cap), and the search is order-invariant.  Red here = a starvation
    regression (#127 became real) -- the trigger to build type-gated candidate scheduling."""
    m = measure()
    assert m["targets_with_recognized_route"] >= 3, f"benchmark went vacuous (no recognized routes): {m}"
    assert not m["any_starvation_observed"], f"CAP STARVATION observed on {m['starved_targets']} -- build the fix"
    assert m["all_order_invariant"], "search is not order-invariant -- a reagent/commodity reorder changed the result"
    return True


def main() -> None:
    m = measure()
    print("CANDIDATE-STARVATION-127 -- recognized-route recall under the raw max_routes cap\n")
    for r in m["rows"]:
        print(f"  {r['name']:18s} returned@{_HIGH_CAP}={r['high_cap_returned']:3d}  recognized={r['recognized_total']}"
              f"  fiction={r['fiction_total']:3d}  rec_indices={r['recognized_indices']}"
              f"  recall@cap1={r['recall_at_cap1']}  order_invariant={r['order_invariant']}")
        for cap, c in r["sweep"].items():
            print(f"       cap={cap}: returned={c['returned']:3d} recognized_survived={c['recognized_survived']}"
                  f"/{r['recognized_total']} recall={c['recall']} saturated={c['saturated']}")
    print(f"\n  any_starvation_observed : {m['any_starvation_observed']}  (starved: {m['starved_targets']})")
    print(f"  all_order_invariant     : {m['all_order_invariant']}")
    print(f"\n  VERDICT: {'PASS (no starvation; cap is not the bottleneck)' if validate() else 'FAIL'}")


if __name__ == "__main__":
    main()
