"""COST-VEC-01 (live wiring): route.leaf_inputs -> basket_cost_vector -> AffordabilityFrontierEntry -> the response.

Pins: (1) ExperimentRoute.leaf_inputs is exactly the EXTERNAL (bought) reactants, never a produced intermediate;
(2) the frontier keeps the cheaper PRICED basket over real 2a USGS prices (NaCl 52.95 vs Na2CO3 169.35 $/t) -- the
engine chain is non-vacuous on real data, not mocks; (3) the service populates affordability_frontier with typed
entries that link back to the ranked routes and form a valid Pareto set (or an HONEST empty when no route carries
signal); (4) the frontier is EXCLUDED from result_digest (prices are dated data, not search identity), so it never
splits two responses that share a search; (5) a populated frontier round-trips through the JSON payload exactly.
"""
from __future__ import annotations

import dataclasses

from smartchem.data.reagents import COMMODITY_REAGENTS, commodity_inventory
from smartchem.experiment.affordability import (
    AffordabilityFrontierEntry,
    CostVector,
    basket_cost_vector,
    pareto_frontier,
)
from smartchem.experiment.routes import search_routes
from smartchem.experiment.step import ExperimentRoute
from smartchem.service import (
    build_recompile_request,
    response_from_payload,
    response_to_payload,
    run_compilation,
)
from smartchem.smiles import parse_smiles

_BY_NAME = {c.name: c for c in COMMODITY_REAGENTS}


def _commodities() -> tuple:
    return tuple(m.canonical() for m in commodity_inventory())


def _a_real_route() -> ExperimentRoute:
    # methyl acetate at depth 2 with commodities on is the golden routes-found target -- it yields real routes.
    result = search_routes(
        parse_smiles("CC(=O)OC"), reagents=(parse_smiles("O"),), commodities=_commodities(), max_depth=2,
    )
    assert result.routes, "expected the routes-found target to yield at least one route"
    return result.routes[0]


def test_leaf_inputs_are_the_external_reactants_never_a_produced_species():
    route = _a_real_route()
    from smartchem.experiment.step import _ident
    leaf_keys = {_ident(m) for m in route.leaf_inputs}
    assert route.leaf_inputs, "a real multi-input route must have at least one purchased leaf (non-vacuous)"
    # no leaf is a species the route itself makes -- checked against ALL PRODUCTS (targets AND byproducts), not just
    # step targets, so a re-consumed byproduct can never be mis-billed as a buy (red-team Finding 2 guard).
    produced_all = {_ident(p) for s in route.steps for p in s.products}
    assert leaf_keys.isdisjoint(produced_all)
    # every leaf is a reactant of SOME step
    all_reactants = {_ident(r) for s in route.steps for r in s.reactants}
    assert leaf_keys <= all_reactants
    # and deduplicated: no repeat by canonical identity
    assert len(route.leaf_inputs) == len(leaf_keys)


def test_a_re_consumed_byproduct_is_not_billed_as_a_purchased_leaf():
    # red-team Finding 2, pinned: a species a step LIBERATES and a later step RE-CONSUMES is made internally, never a
    # bought leaf.  Build CCO -> CH3CHO + H2, then CH3CHO + H2 -> CCO: H2 is a byproduct of step 1, re-consumed by
    # step 2.  It must NOT appear in leaf_inputs (it was not purchased), even though it is a reactant of step 2.
    from smartchem.experiment.step import ExperimentStep, _ident
    cco, ch3cho, h2 = parse_smiles("CCO"), parse_smiles("CC=O"), parse_smiles("[H][H]")
    s1 = ExperimentStep.assembling(ch3cho, (cco,), (ch3cho, h2))
    s2 = ExperimentStep.assembling(cco, (ch3cho, h2), (cco,))
    route = ExperimentRoute.of(s1, s2)
    leaf_keys = {_ident(m) for m in route.leaf_inputs}
    assert _ident(h2) not in leaf_keys  # made in step 1, not bought -- would fail before the all-products fix


def test_the_frontier_keeps_the_cheaper_priced_basket_over_real_prices():
    salt, soda = _BY_NAME["sodium chloride"].molecule, _BY_NAME["sodium carbonate"].molecule
    salt_v = basket_cost_vector([salt])   # 52.95 $/t, grocery access
    soda_v = basket_cost_vector([soda])   # 169.35 $/t, grocery access
    assert salt_v.cash is not None and soda_v.cash is not None and salt_v.cash < soda_v.cash
    cheap = AffordabilityFrontierEntry.of("route-salt", salt_v)
    dear = AffordabilityFrontierEntry.of("route-soda", soda_v)
    frontier = pareto_frontier([dear, cheap])
    # the cheaper basket (same access, lower cash) strictly dominates -> only it survives on the frontier
    assert frontier == [cheap]


def test_an_all_unknown_pair_is_incomparable_so_both_stay_on_the_frontier():
    # section 10.4: UNKNOWN is incomparable -- the frontier never over-ranks on absent data.
    a = AffordabilityFrontierEntry.of("a", basket_cost_vector([parse_smiles("CCCCCCCCO")]))  # octan-1-ol: unpriced
    b = AffordabilityFrontierEntry.of("b", basket_cost_vector([parse_smiles("CCCCCCCCCO")]))  # nonan-1-ol: unpriced
    assert a.cost_vector.cash is None and b.cost_vector.cash is None
    assert pareto_frontier([a, b]) == [a, b]


def test_the_service_populates_a_valid_linked_pareto_frontier():
    # methyl acetate at depth 2 with commodities on has known-access leaves, so its frontier is NON-EMPTY -- asserted
    # directly (not behind `if frontier:`) so a mutant that returns () for the frontier or leaf_inputs is CAUGHT here
    # and not vacuously green ([[vacuous-green-over-an-empty-subject]]; red-team Finding 3).
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    frontier = resp.affordability_frontier
    assert type(frontier) is tuple and frontier, "the routes-found target must populate a non-empty frontier"
    assert all(type(e) is AffordabilityFrontierEntry for e in frontier)
    # every entry links back to a ranked route
    ranked_digests = {r.route_digest for r in resp.ranked_route_dossiers}
    assert all(e.route_digest in ranked_digests for e in frontier)
    # a valid Pareto set: no entry dominates another (pareto_frontier is idempotent on its own output)
    assert pareto_frontier(list(frontier)) == list(frontier)
    # every surviving entry carries real affordability signal (the post-dominance gate held)
    assert all(e.cost_vector.known_axes() or e.cost_vector.is_hard_blocked for e in frontier)


def test_the_signal_gate_returns_empty_when_dominance_strips_the_only_signal():
    # red-team Finding 1, pinned at the wiring boundary: one EXCLUDED route (its blocker is the only signal) among
    # all-UNKNOWN clean routes.  G6 dominates the blocked entry OFF the frontier, leaving blank vectors -- the gate
    # must then return () (no affordability info survived), NEVER a list of blank-vector entries.
    from smartchem.service import _affordability_frontier

    class _Ranked:
        def __init__(self, digest, fit_status, exclusions):
            self.route_digest, self.fit_status, self.exclusions = digest, fit_status, exclusions

    class _Route:
        def __init__(self, digest, leaves):
            self._d, self._leaves = digest, leaves
        @property
        def digest(self):
            return self._d
        @property
        def leaf_inputs(self):
            return self._leaves

    unpriced = parse_smiles("CCCCCCCCO")  # octan-1-ol: neither priced nor a known commodity -> all-UNKNOWN basket
    routes = (_Route("blk", (unpriced,)), _Route("cl1", (unpriced,)), _Route("cl2", (unpriced,)))
    ranked = (_Ranked("blk", "EXCLUDED", ("too hot",)), _Ranked("cl1", "FITS", ()), _Ranked("cl2", "FITS", ()))
    assert _affordability_frontier(routes, ranked) == ()  # blank survivors -> honest empty, not a blank-vector list


def test_the_frontier_is_excluded_from_result_digest():
    # prices are dated DATA, not search identity: a response with a populated frontier must share the result_digest
    # of the same response without one, or two aliases that ran the same search would split on price data.
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    entry = AffordabilityFrontierEntry.of("deadbeef", CostVector(cash=1.0, currency="USD", unit="kg"))
    injected = dataclasses.replace(resp, affordability_frontier=(entry,))
    assert injected.affordability_frontier == (entry,)
    assert injected.result_digest == resp.result_digest


def test_a_populated_frontier_round_trips_through_the_json_payload():
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    entry = AffordabilityFrontierEntry.of(
        "cafe1234", CostVector(cash=52.95, access_difficulty=0, currency="USD", unit="t", hard_blockers=()),
    )
    injected = dataclasses.replace(resp, affordability_frontier=(entry,))
    back = response_from_payload(response_to_payload(injected))
    assert back.affordability_frontier == (entry,)
    assert back.affordability_frontier[0].cost_vector == entry.cost_vector


# ---- COST-VEC-01 quantity/stoich axis: material_quantity via dag_shopping_requirement ----

def test_route_material_quantity_is_the_conserved_external_mol_per_product():
    from smartchem.experiment.step import ExperimentStep
    from smartchem.service import _route_material_quantity
    H2, O2, H2O = parse_smiles("[H][H]"), parse_smiles("O=O"), parse_smiles("O")
    route = ExperimentRoute.of(ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O)))  # 2 H2 + O2 -> 2 H2O
    # per 1 mol H2O (extent 0.5): buy 1 mol H2 + 0.5 mol O2 = 1.5 mol external -- a conserved 100%-eff lower bound.
    assert _route_material_quantity(route) == 1.5


def test_route_material_quantity_is_none_when_shopping_is_underdetermined(monkeypatch):
    # the honest UNKNOWN: a coupled multi-net-producer route makes the buy a genuine range, so dag_shopping_requirement
    # raises ShoppingUnderdeterminedError -> _route_material_quantity returns None, never a fabricated allocation.
    import smartchem.experiment.dag as dagmod
    from smartchem.experiment.step import ExperimentStep
    from smartchem.service import _route_material_quantity
    H2, O2, H2O = parse_smiles("[H][H]"), parse_smiles("O=O"), parse_smiles("O")
    route = ExperimentRoute.of(ExperimentStep.assembling(H2O, (H2, H2, O2), (H2O, H2O)))

    def _raise(*_a, **_k):
        raise dagmod.ShoppingUnderdeterminedError("coupled multi-producer (test)")

    monkeypatch.setattr(dagmod, "dag_shopping_requirement", _raise)
    assert _route_material_quantity(route) is None  # DAGError family caught -> honest None, not a crash, not a number


def test_route_material_quantity_is_none_for_a_degenerate_no_net_species_step():
    # red-team fold: a degenerate step (identity 2 H2O -> 2 H2O) is a VALID DAG but has no net species, so
    # dag_shopping_requirement raises CeilingError -- a SIBLING of DAGError, not a subclass.  _route_material_quantity
    # must catch it too (honest None), else a degenerate-but-valid route crashes the whole compilation response.
    from smartchem.experiment.step import ExperimentStep
    from smartchem.service import _route_material_quantity
    H2O = parse_smiles("O")
    route = ExperimentRoute.of(ExperimentStep.assembling(H2O, (H2O, H2O), (H2O, H2O)))  # identity, no net species
    assert _route_material_quantity(route) is None  # CeilingError caught -> None, NOT a crash


def test_the_frontier_populates_and_ranks_by_material_quantity():
    # the quantity axis is LIVE and DISCRIMINATING: methyl acetate at depth 2 yields routes with different external
    # material burdens (mol/product); the leaner route dominates the heavier on material_quantity (same access), so the
    # heavier route is dropped OFF the frontier -- a ranking the per-unit cash axis (cash UNKNOWN here) cannot make.
    from smartchem.service import _route_material_quantity
    result = search_routes(
        parse_smiles("CC(=O)OC"), reagents=(parse_smiles("O"),), commodities=_commodities(), max_depth=2,
    )
    mqs = sorted(_route_material_quantity(r) for r in result.routes)
    assert len(mqs) >= 2 and mqs[0] is not None and mqs[-1] is not None and mqs[0] < mqs[-1]  # routes differ on burden
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2))
    frontier = resp.affordability_frontier
    front_mqs = [e.cost_vector.material_quantity for e in frontier]
    assert frontier and all(m is not None for m in front_mqs)  # the axis is POPULATED on the frontier (non-vacuous)
    assert max(front_mqs) < mqs[-1]  # the heaviest-material route was dominated OFF -- the quantity axis ranked it out
