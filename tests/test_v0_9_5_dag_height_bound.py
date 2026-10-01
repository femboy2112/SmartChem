"""0.9.5 A17 -- the S5 DAG-height law, corrected to the bound the convergent search actually obeys.

S5 (Wave-A G F4) refused a replayed DAG taller than the request's ``max_depth``, on the premise that the convergent
search "recurses from depth 1 while depth < max_depth". The premise was never measured on a DAG whose branches share
an intermediate: ``routes._merge_branches`` keeps the FIRST producer of each target, so a later branch's consumer can be
fed by an earlier branch's deeper producer and the heights STACK. Isopentyl acetate at max_depth=3 emits honest DAGs
four steps high, and S5 refused that honest payload (found by the A16 writer on the ``c2_isopentyl_dag`` perf payload;
parent-measured: 3 of 100 DAGs, both with and without isopentyl alcohol in stock).

``service._dag_height_bound`` is the proven bound (its docstring carries the argument): H(1) <= 1 + b + ... +
b**(max_depth-1), b = the most distinct reactants any step consumes. These tests pin the false refusal, the bound's
soundness on that honest witness and the formula itself; the forgery S5 exists for (max_depth=3 DAGs under a pinned
max_depth=1 request) stays refused -- ``tests/test_v0_9_5_loader_laws.py::test_s5_*``.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem import service as svc
from smartchem.process_constraints import ProcessBounds
from smartchem.service import response_from_payload, response_to_payload, run_compilation
from smartchem.smiles import parse_smiles

_TALL: list = []


def _tall_response():
    """The cheapest honest witness found (parent probe over four targets): ~75 s, cached for the module."""
    if not _TALL:
        _TALL.append(run_compilation(svc.build_recompile_request(
            "smiles:CC(=O)OCCC(C)C", max_depth=3, helper_reagents=("water", "acetic acid"),
            grammar=svc.TransformGrammar.CAPPED_SCISSION_CONVERGENT,
            process=ProcessBounds.of(max_total_minutes=30.0))))
    return _TALL[0]


def test_honest_dags_stand_taller_than_max_depth_and_load():
    """Pre-fix FAILS: the plain thick load refused with 'the replayed DAG is 4 steps high but ... max_depth=3'."""
    resp = _tall_response()
    dags = [svc._reconstruct_dag(d.replay_payload) for d in resp.ranked_dag_dossiers]
    heights = [svc._dag_height(d) for d in dags]
    assert max(heights) > 3, "the premise: an honest DAG taller than max_depth"
    assert all(svc._dag_height(d) <= svc._dag_height_bound(d, 3) for d in dags)
    loaded = response_from_payload(response_to_payload(resp))
    assert len(loaded.ranked_dag_dossiers) == len(resp.ranked_dag_dossiers)


def _stub_dag(*reactant_lists: tuple[str, ...]):
    return SimpleNamespace(steps=tuple(
        SimpleNamespace(reactants=tuple(parse_smiles(s) for s in reactants)) for reactants in reactant_lists))


def test_bound_formula():
    # one distinct reactant per step: a chain -- the strict law, height <= max_depth
    chain = _stub_dag(("CCO",), ("CC=O", "CC=O"))
    assert [svc._dag_height_bound(chain, d) for d in (1, 2, 3)] == [1, 2, 3]
    # two distinct reactants on some step: 1 + 2 + 4 at max_depth=3
    branched = _stub_dag(("CCO", "CC(=O)O"), ("O",))
    assert [svc._dag_height_bound(branched, d) for d in (1, 2, 3)] == [1, 3, 7]
    # distinctness is the search's own key (resonance identity): two Kekule spellings of benzene are ONE reactant
    kekule = _stub_dag(("C1=CC=CC=C1", "C1C=CC=CC=1"))
    assert svc._dag_height_bound(kekule, 3) == 3
