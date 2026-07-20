"""
Monad laws, and the mechanism search they carry.

Two things are being pinned here.

First, the laws hold -- checked against hypothesis-generated chains, not examples, so a
refactor of the search strategy provably cannot change what a pathway means.

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
        if v1 != v2 or t1.steps != t2.steps or t1.methods != t2.methods:
            return False
        if t1.energy_ev != pytest.approx(t2.energy_ev, abs=1e-9):
            return False
    return True


# ==================================================================================
# The monoid, without which the Writer is not lawful
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


# ==================================================================================
# Monad laws
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

    def test_max_depth_is_enforced(self):
        free, _bound, steps = _h2_steps()
        routes = search(free, steps, max_depth=2)
        assert all(len(r.tally.steps) <= 2 for r in routes)

    def test_results_are_energy_ordered(self):
        free, _bound, steps = _h2_steps()
        routes = search(free, steps, max_depth=3)
        assert [r.energy_ev for r in routes] == sorted(r.energy_ev for r in routes)

    def test_spontaneous_only_prunes_uphill_routes(self):
        free, _bound, steps = _h2_steps()
        routes = search(free, steps, max_depth=2, spontaneous_only=True)
        assert all(r.energy_ev < 0 for r in routes)

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
