"""Exact finite and adversarial checks. No empirical chemical validation."""
from dataclasses import replace
from itertools import permutations, product

import pytest

from smartchem.rule_calculus import (
    BondGraph, BondRule, Edge, RewriteWitness, RuleError, apply, verify,
    enumerate_matches, bounded_closure, independent,
)


def graph(labels="XXXX", edges=((0, 1, 1), (2, 3, 1))):
    return BondGraph(tuple(labels), frozenset(Edge(*e) for e in edges))


def switch():
    return BondRule("formal-switch", graph(), graph(edges=((0, 2, 1), (1, 3, 1))))


def reference(rule, host, match):
    """Separate matrix interpreter; no production apply/verify/mapping helpers."""
    n = len(host.labels)
    if len(match) != len(rule.left.labels) or len(set(match)) != len(match):
        return None
    if any(type(v) is not int or not 0 <= v < n for v in match):
        return None
    if any(host.labels[v] != rule.left.labels[i] for i, v in enumerate(match)):
        return None
    before = [[0] * n for _ in range(n)]
    for e in host.edges:
        before[e.i][e.j] = before[e.j][e.i] = e.order
    k = len(match)
    left = [[0] * k for _ in range(k)]
    right = [[0] * k for _ in range(k)]
    for e in rule.left.edges:
        left[e.i][e.j] = left[e.j][e.i] = e.order
    for e in rule.right.edges:
        right[e.i][e.j] = right[e.j][e.i] = e.order
    after = [row[:] for row in before]
    for i in range(k):
        for j in range(i + 1, k):
            a, b = match[i], match[j]
            old, new = left[i][j], right[i][j]
            if old and before[a][b] != old:
                return None
            if old != new:
                if not old and before[a][b]:
                    return None
                after[a][b] = after[b][a] = new
    return BondGraph(host.labels, frozenset(
        Edge(i, j, after[i][j]) for i in range(n) for j in range(i + 1, n) if after[i][j]
    ))


def test_exact_differential_over_729_hosts_and_24_matches():
    pairs = tuple((i, j) for i in range(4) for j in range(i + 1, 4))
    rule = switch()
    accepted = rejected = 0
    for orders in product(range(3), repeat=6):
        host = graph(edges=tuple((i, j, o) for (i, j), o in zip(pairs, orders) if o))
        for match in permutations(range(4)):
            expected = reference(rule, host, match)
            if expected is None:
                with pytest.raises(RuleError):
                    apply(rule, host, match)
                rejected += 1
            else:
                witness = apply(rule, host, match)
                assert witness.target == expected
                assert verify(witness)
                assert witness.source.degrees == witness.target.degrees
                accepted += 1
    assert accepted > 0 and rejected > accepted
    assert accepted + rejected == 17496


def test_transport_equivariance_for_every_vertex_permutation():
    rule = switch()
    host = graph("XXXX", ((0, 1, 1), (2, 3, 1), (0, 3, 2)))
    witness = apply(rule, host, (0, 1, 2, 3))
    for permutation in permutations(range(4)):
        transported = apply(rule, host.relabel(permutation), permutation)
        assert transported.target == witness.target.relabel(permutation)
        assert verify(transported)


def test_tensor_frame_law():
    r = switch()
    frame = graph("HOH", ((0, 1, 1), (1, 2, 1)))
    small = apply(r, r.left, (0, 1, 2, 3))
    big = apply(r, r.left.tensor(frame), (0, 1, 2, 3))
    assert big.target == small.target.tensor(frame)


def test_reverse_and_interface():
    r = switch()
    w = apply(r, r.left, (0, 1, 2, 3))
    back = apply(r.reverse(), w.target, w.match)
    assert back.target == w.source and verify(back)
    assert r.reverse().reverse() == r
    assert r.interface.labels == r.left.labels
    assert r.interface.edges == frozenset()


def test_partial_bond_order_transfer_is_representable():
    left = graph(edges=((0, 1, 2), (2, 3, 2)))
    right = graph(edges=((0, 1, 1), (2, 3, 1), (0, 2, 1), (1, 3, 1)))
    r = BondRule("formal-order-transfer-not-a-reaction-attestation", left, right)
    assert verify(apply(r, left, (0, 1, 2, 3)))
    assert r.left.degrees == (2, 2, 2, 2)


def test_balanced_target_tamper_is_detected():
    r = switch()
    w = apply(r, r.left, (0, 1, 2, 3))
    # Conservation alone cannot distinguish this same-degree but wrong graph.
    fake = replace(w, target=graph(edges=((0, 3, 1), (1, 2, 1))))
    assert fake.source.degrees == fake.target.degrees
    assert not verify(fake)
    assert not verify(replace(w, target=w.source))


@pytest.mark.parametrize("match", [(0, 0, 2, 3), (True, 1, 2, 3), (0, 1, 2), (0, 1, 2, 4), [0, 1, 2, 3]])
def test_bad_match_refuses_in_both_implementations(match):
    r = switch()
    with pytest.raises(RuleError):
        apply(r, r.left, match)
    assert not verify(RewriteWitness(r, r.left, match, r.right))


def test_wrong_labels_and_surviving_bond_collision():
    r = switch()
    with pytest.raises(RuleError):
        apply(r, graph("HXXX"), (0, 1, 2, 3))
    collision = graph(edges=((0, 1, 1), (2, 3, 1), (0, 2, 2)))
    with pytest.raises(RuleError):
        apply(r, collision, (0, 1, 2, 3))
    assert not verify(RewriteWitness(r, collision, (0, 1, 2, 3), r.right))


def test_required_unchanged_context_is_checked():
    r = BondRule("with-context", graph(edges=((0, 1, 1), (2, 3, 1), (0, 3, 2))),
                 graph(edges=((0, 2, 1), (1, 3, 1), (0, 3, 2))))
    with pytest.raises(RuleError):
        apply(r, switch().left, (0, 1, 2, 3))


def test_bad_graphs_rules_and_budgets():
    with pytest.raises(RuleError):
        Edge(0, 0)
    with pytest.raises(RuleError):
        graph(edges=((0, 1, 1), (0, 1, 2)))
    with pytest.raises(RuleError):
        graph(edges=((0, 4, 1),))
    with pytest.raises(RuleError):
        BondRule("bad", graph(), graph("YXXX"))
    with pytest.raises(RuleError):
        BondRule("unbalanced-degree", graph(), graph(edges=((0, 1, 1),)))
    with pytest.raises(RuleError):
        enumerate_matches(switch(), graph(), budget=True)
    with pytest.raises(RuleError):
        bounded_closure(graph(), (switch(), switch()), depth=1)
    with pytest.raises(RuleError):
        bounded_closure(graph(), (), depth=-1)


def test_matching_receipt_matches_independent_exhaustion():
    r = switch()
    expected = tuple(m for m in permutations(range(4)) if reference(r, r.left, m) is not None)
    full = enumerate_matches(r, r.left, budget=1000)
    assert full.complete and tuple(w.match for w in full.witnesses) == expected
    assert len(expected) == 8
    for budget in range(full.attempts + 1):
        part = enumerate_matches(r, r.left, budget=budget)
        assert part.attempts <= budget
        assert part.complete == (budget == full.attempts)
        assert set(part.witnesses) <= set(full.witnesses)


def test_certified_empty_and_zero_vertex_identity():
    r = BondRule("no-labelled-match", graph("YYYY"), BondGraph(tuple("YYYY"), switch().right.edges))
    assert enumerate_matches(r, graph(), budget=0).complete
    assert enumerate_matches(r, graph(), budget=0).witnesses == ()
    empty = BondGraph(())
    identity = BondRule("identity-unit", empty, empty)
    receipt = enumerate_matches(identity, graph(), budget=0)
    assert receipt.complete and len(receipt.witnesses) == 1
    assert receipt.witnesses[0].target == graph()


def test_bounded_closure_is_complete_for_raw_states_not_all_paths():
    r = switch()
    full = bounded_closure(r.left, (r,), depth=3)
    assert full.complete and len(full.states) == 3
    assert all(verify(w) for w in full.transitions)
    assert set(full.states) == {graph(), r.right, graph(edges=((0, 3, 1), (1, 2, 1)))}
    assert bounded_closure(r.left, (r,), depth=0, match_budget=0).complete
    assert bounded_closure(r.left, (), depth=5, match_budget=0).complete
    assert not bounded_closure(r.left, (r,), depth=1, match_budget=0).complete
    assert bounded_closure(r.left, (r,), depth=1, state_budget=1).status == "INCOMPLETE_STATE_BUDGET"
    assert full.grammar_digest != bounded_closure(r.left, (replace(r, rule_id="other"),), depth=3).grammar_digest


def test_independent_events_commute_and_conflicts_do_not_pass():
    r = switch()
    host = r.left.tensor(r.left)
    a = apply(r, host, (0, 1, 2, 3))
    b = apply(r, host, (4, 5, 6, 7))
    assert independent(a, b)
    assert apply(r, a.target, b.match).target == apply(r, b.target, a.match).target
    assert not independent(a, a)
    assert not independent(a, replace(b, target=host))
    assert not independent(a, apply(r, r.left, (0, 1, 2, 3)))


def test_verifier_does_not_call_generator(monkeypatch):
    import smartchem.rule_calculus as module
    r = switch()
    witness = apply(r, r.left, (0, 1, 2, 3))
    monkeypatch.setattr(module, "apply", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("mutant")))
    assert module.verify(witness)
