"""EVENT-SEARCH-01 (#104 / #123 / #125) -- committed frozen evidence for the bounded typed-event route search.

The motivating gap (issue #123 sub-gap a): the [3,3] sigmatropic + electrocyclic families are oracle-VOUCHED
(:mod:`smartchem.lateral_rewrite`) yet UNREACHABLE from ``search_routes`` -- a rank-flat lateral hop cannot enter
the W1 strict-descent recursion (``forget()`` raises).  This round ships the opt-in bounded typed-event search
(:func:`smartchem.experiment.event_search.search_event_routes`) that interleaves rank-descending SCISSION events
with up to ``lateral_hops`` rank-flat CONNECTED_LATERAL hops, terminating on the lexicographic
``(atom_count, hops_left)`` measure.  This probe freezes the verdicts over a corpus of:

* the FORCING CONSUMER -- a target (1,3-cyclohexadiene) reachable from an on-hand isomer ONLY by one
  electrocyclization: ``search_routes`` is blind (0 routes), the event search finds the 1-hop lateral route;
* the SCISSION-PARITY control -- on a real multi-step scission target (paracetamol via amino-phenol + Ac2O),
  ``lateral_hops=0`` reproduces EXACTLY the ``search_routes`` route set (replay-integrity), and ``lateral_hops=1``
  is a superset;
* the INVERSE-PAIR / rank-flat-cycle control -- a Cope self-inverse target with no stock TERMINATES with 0 routes
  (the A->B->A inverse is cut by the ISSUE-124 ancestor guard, not an infinite loop);
* the BUDGET-TRUNCATION control -- a starved lateral match budget reports INCOMPLETE (fail-closed);
* the TAXONOMY control -- a hand-built step of each of the three typed shapes classifies to its EventType, the
  third (intramolecular-with-coproduct) being the DEFINED-but-DEFERRED category (no generator emits it here).

``content_hash()`` over ``_payload()`` is frozen so a silent behaviour change trips the paired test
(:mod:`tests.test_event_search_probe`).

Run: ``.venv/bin/python -m experiments.event_search_probe``.
"""
from __future__ import annotations

import json
from hashlib import sha256

from smartchem.experiment.event_search import (
    EventType,
    classify_event,
    search_event_routes,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

#: sha256 of the canonical JSON of _payload(); re-freeze ONLY on an intended behaviour change (see validate()).
FROZEN_HASH = "451242176c00a19d0da84a0996fe44b8c8f6330f5514946ac39c3976d9d6862c"

# -- reusable corpus molecules --
_RING = "C1=CCCC=C1"        # 1,3-cyclohexadiene (electrocyclization retro fires here -> opens to the triene)
_OPEN = "C=CC=CC=C"         # 1,3,5-hexatriene  (its rank-flat open isomer)
_COPE = "C=CC(C)CC=C"       # 3-methyl-1,5-hexadiene (a Cope self-inverse: A<->B)
_PARA = "CC(=O)Nc1ccc(O)cc1"
_AMP = "Nc1ccc(O)cc1"


def _para_kw() -> dict:
    # max_depth=1 (paracetamol has depth-1 routes; see tests/test_routes.py): the parity + superset facts hold at
    # depth 1 and the search is ~3s instead of ~45s, keeping the committed probe and its drift test cheap.
    return dict(
        reagents=(parse_smiles("O"), parse_smiles("CC(=O)O"), parse_smiles("CC(=O)OC(=O)C")),
        available=(parse_smiles(_AMP),),
        max_depth=1,
    )


def _forcing_consumer() -> str:
    ring, open_ = parse_smiles(_RING), parse_smiles(_OPEN)
    sr = search_routes(ring, reagents=(), available=(open_,))
    er = search_event_routes(ring, reagents=(), available=(open_,), lateral_hops=1)
    counts = er.event_type_counts()
    return (f"search_routes={len(sr.routes)};event_routes={len(er.routes)};"
            f"lateral={counts[EventType.CONNECTED_LATERAL]};scission={counts[EventType.SCISSION]};"
            f"complete={er.receipt.complete}")


def _forcing_hops0() -> str:
    ring, open_ = parse_smiles(_RING), parse_smiles(_OPEN)
    er = search_event_routes(ring, reagents=(), available=(open_,), lateral_hops=0)
    return f"routes={len(er.routes)};complete={er.receipt.complete};hops_trunc={er.receipt.lateral_hops_truncated}"


def _scission_parity() -> str:
    para = parse_smiles(_PARA)
    sr = {r.digest for r in search_routes(para, **_para_kw()).routes}
    e0 = {r.digest for r in search_event_routes(para, lateral_hops=0, **_para_kw()).routes}
    e1 = {r.digest for r in search_event_routes(para, lateral_hops=1, **_para_kw()).routes}
    return f"n={len(sr)};hops0_equals_search_routes={e0 == sr};hops1_superset={e0 <= e1}"


def _inverse_cycle() -> str:
    cope = parse_smiles(_COPE)
    er = search_event_routes(cope, reagents=(), available=(), lateral_hops=5, max_depth=6)
    return f"routes={len(er.routes)};complete={er.receipt.complete};nodes={er.receipt.nodes_visited}"


def _budget_truncation() -> str:
    # a target with a real lateral successor, searched with a starved lateral match budget -> INCOMPLETE.
    ring = parse_smiles(_RING)
    er = search_event_routes(ring, reagents=(), available=(), lateral_hops=1, lateral_match_budget=1, max_depth=2)
    return f"complete={er.receipt.complete}"


def _classify(kind: str) -> str:
    if kind == "scission":   # AcOH + AcOH -> Ac2O + H2O  (two identical fragments: arity-2 by multiplicity)
        step = ExperimentStep.assembling(
            parse_smiles("CC(=O)OC(=O)C"), (parse_smiles("CC(=O)O"), parse_smiles("CC(=O)O")),
            (parse_smiles("CC(=O)OC(=O)C"), parse_smiles("O")), reagents=())
    elif kind == "lateral":  # cyclohexadiene <- hexatriene (1->1 rank-flat)
        step = ExperimentStep.assembling(
            parse_smiles(_RING), (parse_smiles(_OPEN),), (parse_smiles(_RING),), reagents=())
    elif kind == "intramolecular_coproduct":  # 4-hydroxybutanoic acid -> gamma-butyrolactone + water (DEFERRED type)
        step = ExperimentStep.assembling(
            parse_smiles("O=C1CCCO1"), (parse_smiles("OCCCC(=O)O"),),
            (parse_smiles("O=C1CCCO1"), parse_smiles("O")), reagents=())
    else:  # pragma: no cover
        raise ValueError(kind)
    return classify_event(step).value


def _payload() -> dict:
    return {
        "forcing_consumer": _forcing_consumer(),
        "forcing_hops0_scission_only": _forcing_hops0(),
        "scission_parity_paracetamol": _scission_parity(),
        "inverse_cycle_terminates": _inverse_cycle(),
        "budget_truncation_incomplete": _budget_truncation(),
        "classify_scission": _classify("scission"),
        "classify_lateral": _classify("lateral"),
        "classify_intramolecular_coproduct": _classify("intramolecular_coproduct"),
    }


def content_hash(payload: dict | None = None) -> str:
    data = _payload() if payload is None else payload
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(payload: dict | None = None) -> None:
    """Assert the load-bearing soundness facts of the typed-event search (the no-false-reach cardinals)."""
    p = _payload() if payload is None else payload
    assert p["forcing_consumer"] == (
        "search_routes=0;event_routes=1;lateral=1;scission=0;complete=True"
    ), p["forcing_consumer"]
    assert p["forcing_hops0_scission_only"] == "routes=0;complete=True;hops_trunc=0", p["forcing_hops0_scission_only"]
    assert p["scission_parity_paracetamol"] == (
        "n=2;hops0_equals_search_routes=True;hops1_superset=True"
    ), p["scission_parity_paracetamol"]
    assert p["inverse_cycle_terminates"].startswith("routes=0;complete=True;"), p["inverse_cycle_terminates"]
    assert p["budget_truncation_incomplete"] == "complete=False", p["budget_truncation_incomplete"]
    assert p["classify_scission"] == "SCISSION"
    assert p["classify_lateral"] == "CONNECTED_LATERAL"
    assert p["classify_intramolecular_coproduct"] == "INTRAMOLECULAR_COPRODUCT"


if __name__ == "__main__":
    payload = _payload()           # computed ONCE -- validate / print / hash all reuse it (the search is the cost)
    validate(payload)
    for label, verdict in payload.items():
        print(f"  {label:34} {verdict}")
    digest = content_hash(payload)
    print(f"\ncontent_hash() = {digest}")
    print("FROZEN_HASH matches." if digest == FROZEN_HASH else "FROZEN_HASH STALE -- re-freeze if intended.")
