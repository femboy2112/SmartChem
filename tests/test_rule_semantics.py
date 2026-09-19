from fractions import Fraction
from itertools import combinations, product

import pytest

from smartchem.rule_semantics import (
    FiniteRelation, QuantityInterval, sum_known, robustly_dominates,
    AxisVerdict, CAPABILITY_AXES, capability_verdict, fibre_collisions,
)


def subsets(values):
    return tuple(frozenset(c) for n in range(len(values) + 1) for c in combinations(values, n))


def all_relations():
    states = frozenset((0, 1))
    return tuple(FiniteRelation(states, states, p) for p in subsets(tuple(product(states, states))))


def test_all_4096_composition_associativity_cases():
    relations = all_relations()
    for a, b, c in product(relations, repeat=3):
        assert a.then(b).then(c) == a.then(b.then(c))
    for r in relations:
        identity = FiniteRelation.identity(r.domain)
        assert identity.then(r) == r == r.then(identity)


def test_context_join_requires_a_common_intermediate_witness():
    middle = frozenset(("wet", "dry"))
    a = FiniteRelation(frozenset(("feed",)), middle, frozenset((("feed", "wet"),)))
    b = FiniteRelation(middle, frozenset(("product",)), frozenset((("dry", "product"),)))
    assert a.pairs and b.pairs and not a.then(b).pairs
    with pytest.raises(ValueError):
        a.then(FiniteRelation.identity(frozenset(("undeclared-transport",))))


def test_preimage_laws_and_galois_connection_exhaustively():
    relations = all_relations()
    sets = subsets((0, 1))
    for r, a, b in product(relations, sets, sets):
        assert (r.image(a) <= b) == (a <= r.must_preimage(b))
    for r, s, target in product(relations, relations, sets):
        assert r.then(s).may_preimage(target) == r.may_preimage(s.may_preimage(target))
        assert r.then(s).must_preimage(target) == r.must_preimage(s.must_preimage(target))
    empty = FiniteRelation(frozenset((0,)), frozenset((1,)), frozenset())
    assert empty.must_preimage(frozenset()) == frozenset((0,))
    assert empty.may_preimage(frozenset((1,))) == frozenset()


def test_relational_tensor_interchange_all_65536_cases():
    relations = all_relations()
    for a, b, c, d in product(relations, repeat=4):
        assert a.tensor(b).then(c.tensor(d)) == a.then(c).tensor(b.then(d))


def test_fibre_obstruction_is_relative_to_the_supplied_observation_and_labels():
    rows = (("one", "local", "real"), ("two", "local", "unrecognized"))
    collisions = fibre_collisions(rows)
    assert len(collisions) == 1
    assert collisions[0].left_case == "one"
    assert not fibre_collisions((("one", "local+context1", "real"), ("two", "local+context2", "unrecognized")))
    assert not fibre_collisions((("one", "same", "class"), ("two", "same", "class")))


def test_exact_intervals_unknowns_and_units():
    a = QuantityInterval("USD@declared-date", 1, 2)
    b = QuantityInterval("USD@declared-date", Fraction(1, 2), 1)
    assert a + b == QuantityInterval(a.unit, Fraction(3, 2), 3)
    assert sum_known((a, None, b), unit=a.unit) is None
    assert sum_known((), unit=a.unit) == QuantityInterval(a.unit, 0, 0)
    with pytest.raises(ValueError):
        a + QuantityInterval("minutes", 1, 2)
    with pytest.raises(ValueError):
        QuantityInterval("USD", 0.1, 0.2)
    with pytest.raises(ValueError):
        QuantityInterval("USD", 2, 1)
    with pytest.raises(ValueError):
        QuantityInterval("USD", True, 2)


def test_robust_dominance_is_strict_transitive_and_neutral_on_unknown():
    values = tuple(QuantityInterval("unit", i, j) for i in range(4) for j in range(i, 4))
    for a, b, c in product(values, repeat=3):
        assert not robustly_dominates((a,), (a,))
        if robustly_dominates((a,), (b,)) and robustly_dominates((b,), (c,)):
            assert robustly_dominates((a,), (c,))
    assert not robustly_dominates((values[0],), (None,))
    assert not robustly_dominates((None,), (values[-1],))
    assert not robustly_dominates((), ())
    with pytest.raises(ValueError):
        robustly_dominates((values[0],), ())


def test_capability_axes_are_separate_and_missing_is_not_success():
    assert capability_verdict({}) == "UNKNOWN"
    yes = {k: AxisVerdict.SUPPORTED for k in CAPABILITY_AXES}
    assert capability_verdict(yes) == "FITS_DECLARED_MODEL"
    for key in CAPABILITY_AXES:
        axes = dict(yes)
        del axes[key]
        assert capability_verdict(axes) == "UNKNOWN"
        axes[key] = AxisVerdict.BLOCKED
        assert capability_verdict(axes) == "BLOCKED"
    with pytest.raises(ValueError):
        capability_verdict({"outdoors_therefore_safe": AxisVerdict.SUPPORTED})
    with pytest.raises(ValueError):
        capability_verdict({"conditions": True})


def test_makespan_is_not_a_scalar_interchange_decoration():
    # Identical work with/without a global layer barrier: sums/maxima cannot
    # masquerade as a scalar SMC decoration for all causal diagrams.
    a, b, c, d = 10, 0, 0, 10
    assert max(a + c, b + d) == 10
    assert max(a, b) + max(c, d) == 20


def test_unknown_intermediate_cancels_before_partial_evaluation_not_after():
    from smartchem.rule_semantics import PotentialKey, PotentialBalance
    a, i, b = (PotentialKey(s, "declared-phase", "fixed-T-and-standard-state", "model-v1") for s in ("A", "I", "B"))
    first = PotentialBalance(((a, -1), (i, 1)))
    second = PotentialBalance(((i, -1), (b, 1)))
    values = {a: QuantityInterval("kJ/mol", 10, 11), b: QuantityInterval("kJ/mol", 3, 4)}
    assert first.evaluate(values, unit="kJ/mol") is None
    assert second.evaluate(values, unit="kJ/mol") is None
    # A strictly sharper NET result, with neither step promoted to known.
    assert (first + second).evaluate(values, unit="kJ/mol") == QuantityInterval("kJ/mol", -8, -6)
    assert first.evaluate(values, unit="kJ/mol") is None


def test_phase_environment_and_model_mismatch_never_cancel():
    from dataclasses import replace
    from smartchem.rule_semantics import PotentialKey, PotentialBalance
    key = PotentialKey("I", "liquid", "environment-1", "model-1")
    for other in (replace(key, phase="gas"), replace(key, environment_id="environment-2"),
                  replace(key, model_id="model-2"), replace(key, species_id="isomer-of-I")):
        balance = PotentialBalance(((key, 1), (other, -1)))
        assert len(balance.terms) == 2
        assert balance.evaluate({}, unit="kJ/mol") is None
    assert PotentialBalance(((key, 1), (key, -1))).evaluate({}, unit="kJ/mol") == QuantityInterval("kJ/mol", 0, 0)
    with pytest.raises(ValueError):
        PotentialKey("I", "", "env", "model")


def test_symbolic_balance_additivity_for_exact_known_potentials():
    from smartchem.rule_semantics import PotentialKey, PotentialBalance
    a, b = (PotentialKey(s, "phase", "environment", "model") for s in ("A", "B"))
    table = {a: QuantityInterval("kJ/mol", 7, 7), b: QuantityInterval("kJ/mol", -3, -3)}
    balances = tuple(PotentialBalance(((a, x), (b, y))) for x, y in product(range(-2, 3), repeat=2))
    for first, second in product(balances, repeat=2):
        assert (first + second).evaluate(table, unit="kJ/mol") == (
            first.evaluate(table, unit="kJ/mol") + second.evaluate(table, unit="kJ/mol")
        )
