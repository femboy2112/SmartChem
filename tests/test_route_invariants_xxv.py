"""OPERATION XXV route-search invariants that were behaviourally load-bearing but UNPINNED (tests only).

(a) a precursor listed in BOTH ``available`` and ``commodities`` is ONE supply: the route set, the DAG set and the
    terminal-policy identity are exactly those of listing it once (``on_hand`` is a set keyed by canonical identity);
(b) the ISSUE-124 ancestor guard's "unless it is stock" exemption (``k in ancestors and k not in on_hand``) is
    VACUOUS in all three searches: a stocked target terminates before any expansion, and a stocked precursor is never
    expanded, so no ancestor is ever stock.  Pinned by spying on every node the registry is asked to expand;
(c) ``coproduct_events_truncated`` under the DEFAULT type-3 grammar: a bis-lactone whose single coproduct event
    leaves another lactone behind reports the declared-bound truncation and an INCOMPLETE receipt.
"""
from __future__ import annotations

import pytest

from smartchem.experiment.event_search import search_event_routes
from smartchem.experiment.routes import search_dags, search_routes
from smartchem.lateral_rewrite import COPE, rewrite_edges
from smartchem.smiles import parse_smiles, resonance_identity
from smartchem.transform_provider import DEFAULT_TRANSFORM_REGISTRY, TransformProviderRegistry

P = parse_smiles
PARA = P("CC(=O)Nc1ccc(O)cc1")
AMP = P("Nc1ccc(O)cc1")
REAGENTS = (P("O"), P("CC(=O)O"), P("CC(=O)OC(=O)C"))

_EXPANDED: list[str] = []


class _SpyRegistry(TransformProviderRegistry):
    """The default algebra, recording the identity of every node the search asks it to expand."""

    def enumerate(self, reactant, reagents, *, budget):
        _EXPANDED.append(resonance_identity(reactant))
        return super().enumerate(reactant, reagents, budget=budget)


SPY = _SpyRegistry(DEFAULT_TRANSFORM_REGISTRY.providers)


# -- (a) duplicate supply collapses to one ---------------------------------------------------------------------------

def test_search_routes_collapses_a_precursor_listed_as_available_and_commodity():
    once = search_routes(PARA, reagents=REAGENTS, available=(AMP,), max_depth=1)
    twice = search_routes(PARA, reagents=REAGENTS, available=(AMP,), commodities=(AMP,), max_depth=1)
    assert once.routes and {r.digest for r in once.routes} == {r.digest for r in twice.routes}
    assert once.receipt.terminal_policy_digest == twice.receipt.terminal_policy_digest
    assert once.receipt.results_returned == twice.receipt.results_returned


def test_search_dags_collapses_a_precursor_listed_as_available_and_commodity():
    once = search_dags(PARA, reagents=REAGENTS, available=(AMP,), max_depth=1)
    twice = search_dags(PARA, reagents=REAGENTS, available=(AMP,), commodities=(AMP,), max_depth=1)
    assert once.dags and {d.digest for d in once.dags} == {d.digest for d in twice.dags}
    assert once.receipt.terminal_policy_digest == twice.receipt.terminal_policy_digest


def test_event_search_collapses_a_precursor_listed_as_available_and_commodity():
    once = search_event_routes(PARA, reagents=REAGENTS, available=(AMP,), max_depth=1)
    twice = search_event_routes(PARA, reagents=REAGENTS, available=(AMP,), commodities=(AMP,), max_depth=1)
    assert once.digest == twice.digest


# -- (b) the ancestor-is-stock exemption is vacuous ------------------------------------------------------------------

def _run_spied(search, *args, **kwargs):
    _EXPANDED.clear()
    result = search(*args, registry=SPY, **kwargs)
    return result, tuple(_EXPANDED)


@pytest.mark.parametrize("search", [search_routes, search_dags, search_event_routes],
                         ids=["search_routes", "search_dags", "search_event_routes"])
def test_a_stocked_node_is_never_expanded_so_no_ancestor_is_stock(search):
    on_hand = {resonance_identity(m) for m in (AMP, *REAGENTS)}
    _result, expanded = _run_spied(search, PARA, reagents=REAGENTS, available=(AMP,), max_depth=2)
    assert expanded, "the spy saw no expansion -- the probe is vacuous"
    assert not (set(expanded) & on_hand)


@pytest.mark.parametrize("search", [search_routes, search_dags, search_event_routes],
                         ids=["search_routes", "search_dags", "search_event_routes"])
def test_a_stocked_target_terminates_before_any_expansion(search):
    result, expanded = _run_spied(search, PARA, reagents=REAGENTS, available=(AMP, PARA))
    assert expanded == ()
    assert result.receipt.expansions_attempted == 0 and result.receipt.nodes_visited == 0


def test_the_lateral_inverse_with_the_isomer_stocked_never_expands_the_stocked_isomer():
    # the shape test_event_search_123 names for this branch: A <-> B Cope pair with B stocked.  B is a leaf, never a
    # node, so it never enters `ancestors`; the route exists because B is stock, not because of the exemption.
    a = P("C=CC(C)CC=C")
    (edge,) = rewrite_edges(COPE, a)
    b = edge.products[0]
    result, expanded = _run_spied(search_event_routes, a, reagents=(), available=(b,), lateral_hops=3, max_depth=4)
    assert len(result.routes) == 1
    assert resonance_identity(b) not in expanded


# -- (c) coproduct_events_truncated under the default grammar --------------------------------------------------------

BIS_LACTONE = P("O=C1CCC(O1)C1CCC(=O)O1")     # opening one ring leaves the other lactone behind


def test_a_spent_default_coproduct_budget_with_a_live_successor_is_reported():
    res = search_event_routes(BIS_LACTONE, reagents=())
    assert res.receipt.coproduct_events_truncated == 1
    assert not res.receipt.complete
    assert "coproduct-events=1" in res.receipt.summary()


def test_raising_the_coproduct_budget_clears_that_truncation():
    res = search_event_routes(BIS_LACTONE, reagents=(), max_coproduct_events=2, max_depth=3)
    assert res.receipt.coproduct_events_truncated == 0
    assert res.receipt.complete and res.routes == ()
