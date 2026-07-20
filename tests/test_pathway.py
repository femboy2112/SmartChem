"""
Writer/List-style laws, and the mechanism search they carry.

Two things are being pinned here.

First, the structural laws hold up to the explicitly tolerated floating-point arithmetic
used by the comparison helper. Generated examples are regression evidence, not a proof over
all Python values.

Second, and more to the point: ``bind`` is the *only* way pathways compose. In the legacy
code ``bind`` had zero call sites and every test still passed, which is precisely how a
monad ends up decorative. Delete ``Pathway.bind`` and ``TestSearch`` and
``TestCatalyticCycles`` both collapse.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from smartchem.category import Bond, Config, Molecule, Reaction, is_catalytic
from smartchem.pathway import (
    Mechanism,
    Pathway,
    Step,
    Tally,
    best_route,
    catalytic_cycles,
    search,
)


# ==================================================================================
# strategies
# ==================================================================================
tallies = st.builds(
    Tally,
    energy_ev=st.floats(min_value=-20, max_value=20, allow_nan=False),
    uncertainty_ev=st.floats(min_value=0, max_value=2, allow_nan=False),
    steps=st.lists(st.text(min_size=1, max_size=4), max_size=3).map(tuple),
    methods=st.lists(st.sampled_from(["a", "b", "c"]), max_size=2).map(frozenset),
)

pathways = st.lists(
    st.tuples(st.integers(min_value=-20, max_value=20), tallies), max_size=4
).map(lambda bs: Pathway(tuple(bs)))


def same(p: Pathway, q: Pathway) -> bool:
    """Branch-wise comparison with a float tolerance on the accumulated energy."""
    if len(p.branches) != len(q.branches):
        return False
    for (v1, t1), (v2, t2) in zip(p.branches, q.branches):
        if (
            v1 != v2
            or t1.steps != t2.steps
            or t1.methods != t2.methods
            or t1.transitions != t2.transitions
            or t1.generator_word != t2.generator_word
        ):
            return False
        if t1.energy_ev != pytest.approx(t2.energy_ev, abs=1e-9):
            return False
        if t1.uncertainty_ev != pytest.approx(t2.uncertainty_ev, abs=1e-9):
            return False
    return True


# ==================================================================================
# Approximate accumulator laws over IEEE-754 values
# ==================================================================================
class TestTallyMonoid:
    @settings(max_examples=200, deadline=None)
    @given(tallies)
    def test_identity(self, t: Tally):
        assert (Tally.empty() + t).steps == t.steps
        assert (t + Tally.empty()).energy_ev == pytest.approx(t.energy_ev)

    @settings(max_examples=200, deadline=None)
    @given(tallies, tallies, tallies)
    def test_associativity(self, a: Tally, b: Tally, c: Tally):
        left, right = (a + b) + c, a + (b + c)
        assert left.steps == right.steps
        assert left.methods == right.methods
        assert left.energy_ev == pytest.approx(right.energy_ev)

    def test_energy_accumulates(self):
        total = Tally(-1.5) + Tally(-2.0) + Tally(+0.5)
        assert total.energy_ev == pytest.approx(-3.0)

    def test_uncertainty_adds_in_quadrature(self):
        total = Tally(0.0, 0.3) + Tally(0.0, 0.4)
        assert total.uncertainty_ev == pytest.approx(0.5)

    def test_hypot_avoids_spurious_intermediate_overflow(self):
        total = Tally(0.0, 1e200) + Tally(0.0, 1e200)
        assert total.uncertainty_ev == pytest.approx(2 ** 0.5 * 1e200)

    @pytest.mark.parametrize("kwargs", [
        {"steps": "ab"},
        {"methods": "HF"},
    ])
    def test_sequence_fields_reject_bare_strings(self, kwargs):
        with pytest.raises(TypeError):
            Tally(**kwargs)

    @pytest.mark.parametrize("args", [
        (float("nan"), 0.0),
        (0.0, float("inf")),
        (0.0, -0.1),
        (True, 0.0),
    ])
    def test_invalid_numeric_tallies_are_rejected(self, args):
        with pytest.raises((TypeError, ValueError)):
            Tally(*args)

    def test_generator_word_rejects_an_empty_semantic_id(self):
        state = Config.atoms("H")
        with pytest.raises(ValueError, match="non-empty"):
            Tally(
                transitions=((state, state),),
                generator_word=((state, state, ""),),
            )


# ==================================================================================
# Writer/List-style bind laws on the tested finite floating-point domain
# ==================================================================================
class TestMonadLaws:
    @settings(max_examples=200, deadline=None)
    @given(st.integers(min_value=-20, max_value=20))
    def test_left_identity(self, x: int):
        f = lambda n: Pathway(((n * 2, Tally(1.0, 0.1, ("f",))),))
        assert same(Pathway.pure(x).bind(f), f(x))

    @settings(max_examples=200, deadline=None)
    @given(pathways)
    def test_right_identity(self, p: Pathway):
        assert same(p.bind(Pathway.pure), p)

    @settings(max_examples=200, deadline=None)
    @given(pathways)
    def test_associativity(self, p: Pathway):
        f = lambda n: Pathway(((n + 1, Tally(0.5, 0.1, ("f",), frozenset({"o1"}))),))
        g = lambda n: Pathway(((n * 3, Tally(-2.0, 0.2, ("g",), frozenset({"o2"}))),))
        assert same(p.bind(f).bind(g), p.bind(lambda n: f(n).bind(g)))

    def test_empty_pathway_is_absorbing(self):
        assert len(Pathway.none().bind(lambda n: Pathway.pure(n))) == 0

    def test_branching_multiplies(self):
        two = Pathway(((1, Tally.empty()), (2, Tally.empty())))
        assert len(two.bind(lambda n: Pathway(((n, Tally.empty()), (-n, Tally.empty()))))) == 4


# ==================================================================================
# The F4 fix
# ==================================================================================
class TestCertificateSurvivesBind:
    """
    Finding F4: the legacy ``Reaction.bind`` built ``Reaction(new_outcomes)`` without
    carrying ``metadata``, so the "rigorous mathematical certificate" was destroyed by
    the first composition.
    """

    def test_provenance_survives_a_single_bind(self):
        start = Pathway(((1, Tally(-1.0, 0.1, ("bind Mo",), frozenset({"ccsd(t)"}))),))
        out = start.bind(lambda n: Pathway(((n, Tally(-2.0, 0.1, ("insert H2",),
                                                     frozenset({"ccsd(t)"}))),)))
        _, tally = out.branches[0]
        assert tally.steps == ("bind Mo", "insert H2")
        assert tally.methods == frozenset({"ccsd(t)"})
        assert tally.energy_ev == pytest.approx(-3.0)

    def test_provenance_survives_a_long_chain(self):
        p = Pathway.pure(0)
        for i in range(6):
            p = p.bind(
                lambda n, i=i: Pathway(((n + 1, Tally(-0.5, 0.1, (f"s{i}",),
                                                      frozenset({"m"}))),))
            )
        _, tally = p.branches[0]
        assert len(tally.steps) == 6
        assert tally.energy_ev == pytest.approx(-3.0)
        assert "s0" in tally.certificate and "s5" in tally.certificate

    def test_certificate_is_human_readable(self):
        t = Tally(-3.0, 0.2, ("a", "b"), frozenset({"ccsd(t)/cbs"}))
        cert = t.certificate
        assert "a -> b" in cert
        assert "-3.000" in cert
        assert "ccsd(t)/cbs" in cert


# ==================================================================================
# Mechanism search
# ==================================================================================
def _h2_steps():
    """A tiny reaction set: H + H <-> H2."""
    free = Config.atoms("H", "H")
    bound = Config.of(Molecule.diatomic("H", "H"))
    return free, bound, [
        Step(Reaction(free, bound, "associate"), -4.478, 0.04, "ccsd(t)/cbs"),
        Step(Reaction(bound, free, "dissociate"), +4.478, 0.04, "ccsd(t)/cbs"),
    ]


class TestSearch:
    @pytest.mark.parametrize("kwargs", [
        {"energy_ev": float("nan")},
        {"energy_ev": 0.0, "uncertainty_ev": -0.1},
        {"energy_ev": True},
    ])
    def test_invalid_step_numbers_are_rejected(self, kwargs):
        free = Config.atoms("H", "H")
        bound = Config.of(Molecule.diatomic("H", "H"))
        with pytest.raises((TypeError, ValueError)):
            Step(Reaction(free, bound), **kwargs)

    def test_finds_a_one_step_route(self):
        free, bound, steps = _h2_steps()
        routes = search(free, steps, target=bound, max_depth=1)
        assert routes
        assert routes[0].energy_ev == pytest.approx(-4.478)
        assert routes[0].tally.steps == ("associate",)

    def test_accumulates_over_multiple_steps(self):
        free, bound, steps = _h2_steps()
        routes = search(free, steps, target=bound, max_depth=3)
        # depth 3 also finds associate -> dissociate -> associate
        lengths = {len(r.tally.steps) for r in routes}
        assert 1 in lengths and 3 in lengths
        three = next(r for r in routes if len(r.tally.steps) == 3)
        assert three.energy_ev == pytest.approx(-4.478)
        assert three.route.steps == 3
        assert len(three.intermediates) == 2

    def test_a_cycle_keeps_its_two_step_history(self):
        free, _bound, steps = _h2_steps()
        cycle = next(
            route for route in search(free, steps, target=free, max_depth=2)
            if len(route.tally.steps) == 2
        )
        assert cycle.route.steps == 2
        assert cycle.route != Reaction(free, free, path=())

    def test_max_depth_is_enforced(self):
        free, _bound, steps = _h2_steps()
        routes = search(free, steps, max_depth=2)
        assert all(len(r.tally.steps) <= 2 for r in routes)

    def test_search_does_not_implicitly_rank_model_numbers(self):
        free, _bound, steps = _h2_steps()
        routes = search(free, steps, max_depth=3)
        energies = [route.energy_ev for route in routes]
        assert energies != sorted(energies), (
            "search ordering must remain enumeration, not an implicit scientific verdict"
        )

    def test_same_display_label_generators_remain_distinct(self):
        free, bound, _steps = _h2_steps()
        routes = search(
            free,
            [
                Step(Reaction(free, bound, "same", generator_id="channel-a"), -1.0),
                Step(Reaction(free, bound, "same", generator_id="channel-b"), -2.0),
            ],
            target=bound,
            max_depth=1,
        )
        assert len(routes) == 2
        assert {route.energy_ev for route in routes} == {-1.0, -2.0}
        assert len({route.route.generator_word for route in routes}) == 2

    def test_duplicate_generator_preserves_alternative_estimates(self):
        free, bound, _steps = _h2_steps()
        routes = search(
            free,
            [
                Step(Reaction(free, bound, "old", generator_id="same"), -1.0),
                Step(Reaction(free, bound, "new", generator_id="same"), -2.0),
            ],
            target=bound,
            max_depth=1,
        )
        assert len(routes) == 2
        assert {route.energy_ev for route in routes} == {-1.0, -2.0}

    def test_renaming_an_identical_generator_does_not_duplicate_a_route(self):
        free, bound, _steps = _h2_steps()
        routes = search(
            free,
            [
                Step(Reaction(free, bound, "old", generator_id="same"), -1.0),
                Step(Reaction(free, bound, "renamed", generator_id="same"), -1.0),
            ],
            target=bound,
            max_depth=1,
        )
        assert len(routes) == 1

    def test_anonymous_ids_cannot_collide_with_public_generator_ids(self):
        free, bound, _steps = _h2_steps()
        with pytest.raises(ValueError, match="NUL"):
            Reaction(free, bound, generator_id="\x00smartchem-local-step:0")

    def test_anonymous_same_endpoint_channels_do_not_alias(self):
        free, bound, _steps = _h2_steps()
        routes = search(
            free,
            [
                Step(Reaction(free, bound, "channel-a"), -1.0),
                Step(Reaction(free, bound, "channel-b"), -2.0),
            ],
            target=bound,
            max_depth=1,
        )
        assert len(routes) == 2
        assert len({route.route.generator_word for route in routes}) == 2

    def test_spontaneous_only_filters_returned_uphill_routes(self):
        free, _bound, steps = _h2_steps()
        routes = search(free, steps, max_depth=2, spontaneous_only=True)
        assert all(r.energy_ev < 0 for r in routes)

    def test_spontaneous_only_does_not_prune_an_uphill_prefix(self):
        a = Config.atoms("H", "H")
        b = Config.of(Molecule.diatomic("H", "H"))
        c = Config.of(Molecule(
            ("H", "H"), frozenset({Bond(0, 1)}), state="relaxed"
        ))
        routes = search(
            a,
            [
                Step(Reaction(a, b, generator_id="up"), +1.0),
                Step(Reaction(b, c, generator_id="down"), -3.0),
            ],
            target=c,
            max_depth=2,
            spontaneous_only=True,
        )
        assert len(routes) == 1
        assert routes[0].energy_ev == pytest.approx(-2.0)

    @pytest.mark.parametrize("bad", [-1, 1.5, True])
    def test_invalid_depth_is_rejected(self, bad):
        free, _bound, steps = _h2_steps()
        with pytest.raises((TypeError, ValueError)):
            search(free, steps, max_depth=bad)

    def test_unreachable_target_returns_nothing(self):
        free, _bound, steps = _h2_steps()
        unrelated = Config.of(Molecule.diatomic("O", "O"))
        assert search(free, steps, target=unrelated, max_depth=3) == []

    def test_best_route_picks_the_minimum(self):
        free, bound, steps = _h2_steps()
        routes = search(free, steps, target=bound, max_depth=3)
        best = best_route(routes)
        assert best is not None
        assert best.energy_ev == min(r.energy_ev for r in routes)

    def test_best_route_of_nothing_is_none(self):
        assert best_route([]) is None

    def test_best_route_refuses_alternative_estimates_of_one_route(self):
        free, bound, _steps = _h2_steps()
        routes = search(
            free,
            [
                Step(Reaction(free, bound, "a", generator_id="same"), -1.0),
                Step(Reaction(free, bound, "b", generator_id="same"), -2.0),
            ],
            target=bound,
            max_depth=1,
        )
        with pytest.raises(ValueError, match="alternative estimates"):
            best_route(routes)

    def test_best_route_refuses_mixed_estimators(self):
        free, bound, _steps = _h2_steps()
        routes = search(
            free,
            [
                Step(Reaction(free, bound, "a", generator_id="a"), -1.0, method="A"),
                Step(Reaction(free, bound, "b", generator_id="b"), -2.0, method="B"),
            ],
            target=bound,
            max_depth=1,
        )
        with pytest.raises(ValueError, match="common estimator"):
            best_route(routes)


# ==================================================================================
# Catalysis, decided and evidenced
# ==================================================================================
class TestCatalyticCycles:
    """Finding F3, from the other side: the search must produce checkable evidence."""

    def test_finds_a_cycle_that_regenerates_the_catalyst(self):
        mo = Molecule.atom("Mo")
        n2 = Molecule.diatomic("N", "N", order=3)
        bound = Molecule(("Mo", "N", "N"), frozenset({Bond(0, 1), Bond(1, 2)}))

        free = Config.of(mo, n2)
        complexed = Config.of(bound)
        steps = [
            Step(Reaction(free, complexed, "coordinate"), -1.2, 0.05, "ccsd(t)"),
            Step(Reaction(complexed, free, "release"), +1.0, 0.05, "ccsd(t)"),
        ]

        cycles = catalytic_cycles(free, steps, mo, max_depth=3)
        assert cycles, "the Mo should be regenerated by coordinate -> release"
        cycle = cycles[0]
        assert isinstance(cycle, Mechanism)
        assert is_catalytic(cycle.route, mo), "evidence must survive independent re-checking"
        assert cycle.tally.steps, "a zero-step route regenerates everything trivially"

    def test_consumed_catalyst_yields_no_cycle(self):
        mo = Molecule.atom("Mo")
        free = Config.of(mo, Molecule.atom("N"))
        consumed = Config.of(Molecule.diatomic("Mo", "N"))
        steps = [Step(Reaction(free, consumed, "bind"), -3.0, 0.1, "ccsd(t)")]
        assert catalytic_cycles(free, steps, mo, max_depth=3) == []

    def test_cycle_carries_its_certificate(self):
        mo = Molecule.atom("Mo")
        n2 = Molecule.diatomic("N", "N", order=3)
        bound = Molecule(("Mo", "N", "N"), frozenset({Bond(0, 1), Bond(1, 2)}))
        free, complexed = Config.of(mo, n2), Config.of(bound)
        steps = [
            Step(Reaction(free, complexed, "coordinate"), -1.2, 0.05, "ccsd(t)/cbs"),
            Step(Reaction(complexed, free, "release"), +1.0, 0.05, "ccsd(t)/cbs"),
        ]
        cycle = catalytic_cycles(free, steps, mo, max_depth=2)[0]
        assert "coordinate" in cycle.certificate
        assert "ccsd(t)/cbs" in cycle.certificate
