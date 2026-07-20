"""
Store comonad laws, and the response-surface machinery they enable.

Function equality is undecidable, so the comonad laws are checked **extensionally**: two
Stores are treated as equal when they agree at every sampled position. That is the honest
formulation -- asserting object identity would pass trivially and prove nothing.

``TestResponseSurface`` is where the comonad stops being decoration: ``survey`` is
implemented through ``extend``, so if ``extend`` were removed these tests would fail. In
the legacy code ``extend`` had zero call sites and every test still passed.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from smartchem.store import (
    Conditions,
    SOLVENTS,
    Store,
    argmin_position,
    grid,
    is_responsive,
    response_surface,
    survey,
)

POSITIONS = [0.0, 1.0, 2.5, 10.0, -3.0]


def test_illustrative_solvent_table_is_read_only():
    with pytest.raises(TypeError):
        SOLVENTS["water"] = 1.0


def agree(a: Store, b: Store, positions=POSITIONS) -> bool:
    """Extensional equality: same focus, and same observations everywhere sampled."""
    return a.focus == b.focus and all(a.peek(p) == b.peek(p) for p in positions)


# ==================================================================================
# Comonad laws
# ==================================================================================
class TestComonadLaws:
    @settings(max_examples=100, deadline=None)
    @given(st.floats(min_value=-50, max_value=50, allow_nan=False))
    def test_left_identity(self, x: float):
        """``extract . extend(f) == f``"""
        w = Store(lambda s: s * 2.0, x)
        f = lambda store: store.extract() + 1.0
        assert w.extend(f).extract() == pytest.approx(f(w))

    @settings(max_examples=100, deadline=None)
    @given(st.floats(min_value=-50, max_value=50, allow_nan=False))
    def test_right_identity(self, x: float):
        """``extend(extract) == id``"""
        w = Store(lambda s: s * 3.0 - 1.0, x)
        assert agree(w.extend(lambda store: store.extract()), w)

    @settings(max_examples=100, deadline=None)
    @given(st.floats(min_value=-20, max_value=20, allow_nan=False))
    def test_associativity(self, x: float):
        """``extend(f) . extend(g) == extend(f . extend(g))``"""
        w = Store(lambda s: s + 0.5, x)
        f = lambda store: store.extract() * 2.0
        g = lambda store: store.extract() + 10.0
        left = w.extend(g).extend(f)
        right = w.extend(lambda store: f(store.extend(g)))
        assert agree(left, right)

    def test_duplicate_agrees_with_extend_identity(self):
        w = Store(lambda s: s * 7.0, 2.0)
        dup = w.duplicate()
        ext = w.extend(lambda store: store)
        assert dup.focus == ext.focus
        for p in POSITIONS:
            assert dup.peek(p).extract() == ext.peek(p).extract()

    def test_functor_identity(self):
        w = Store(lambda s: s + 1.0, 3.0)
        assert agree(w.map(lambda a: a), w)

    def test_functor_composition(self):
        w = Store(lambda s: s + 1.0, 3.0)
        f = lambda a: a * 2.0
        g = lambda a: a - 5.0
        assert agree(w.map(g).map(f), w.map(lambda a: f(g(a))))


# ==================================================================================
# Navigation
# ==================================================================================
class TestNavigation:
    def test_seek_moves_focus_without_changing_observation(self):
        w = Store(lambda s: s ** 2, 2.0)
        assert w.extract() == 4.0
        assert w.seek(3.0).extract() == 9.0
        assert w.extract() == 4.0, "seek must not mutate the original"

    def test_experiment_looks_without_moving(self):
        w = Store(lambda s: s * 10.0, 1.0)
        assert w.experiment(lambda s: s + 1.0) == 20.0
        assert w.focus == 1.0


# ==================================================================================
# The payoff: one local definition, an entire surface
# ==================================================================================
class TestResponseSurface:
    """
    These are the tests that make the comonad load-bearing. ``survey`` goes through
    ``extend``; delete ``extend`` and this class fails.
    """

    def test_survey_covers_every_position(self):
        w = Store(lambda s: s * 2.0, 0.0)
        surface = survey(w, [1.0, 2.0, 3.0])
        assert surface == {1.0: 2.0, 2.0: 4.0, 3.0: 6.0}

    def test_survey_matches_pointwise_evaluation(self):
        """The comonadic route must agree with naive evaluation -- it just does more."""
        f = lambda s: s ** 2 - 3 * s
        w = Store(f, 0.0)
        positions = [-2.0, 0.0, 1.5, 4.0]
        assert survey(w, positions) == {p: f(p) for p in positions}

    def test_solvent_series_from_one_definition(self):
        """
        A whole solvent series from a single local rule. This is the shape of computation
        the legacy Coreader comonad structurally could not express.
        """
        def born_like(c: Conditions) -> float:
            return -7.2 * (1.0 - 1.0 / c.dielectric)

        positions = [Conditions(dielectric=e) for e in SOLVENTS.values()]
        surface = response_surface(born_like, positions)
        assert len(surface) == len(SOLVENTS)
        assert surface[Conditions(dielectric=1.0)] == pytest.approx(0.0)
        assert surface[Conditions(dielectric=80.1)] < -7.0

    def test_argmin_finds_the_most_stabilising_condition(self):
        def energy(c: Conditions) -> float:
            return -7.2 * (1.0 - 1.0 / c.dielectric)

        positions = [Conditions(dielectric=e) for e in SOLVENTS.values()]
        best = argmin_position(Store(energy, positions[0]), positions)
        assert best is not None
        assert best.dielectric == max(SOLVENTS.values())

    def test_grid_is_the_cartesian_product(self):
        g = grid(temperatures=(200.0, 300.0), dielectrics=(1.0, 80.1))
        assert len(g) == 4
        assert len({c.temperature_k for c in g}) == 2
        assert len({c.dielectric for c in g}) == 2

    def test_two_dimensional_sweep(self):
        def phase(c: Conditions) -> str:
            return "melt" if c.temperature_k > 500 and c.pressure_atm < 100 else "solid"

        positions = grid(temperatures=(300.0, 800.0), pressures=(1.0, 1000.0))
        surface = response_surface(phase, positions)
        assert len(surface) == 4
        assert sorted(set(surface.values())) == ["melt", "solid"]


class TestConditionValidation:
    @pytest.mark.parametrize("changes", [
        {"temperature_k": -1.0},
        {"pressure_atm": -1.0},
        {"dielectric": 0.0},
        {"dielectric": -1.0},
        {"photon_ev": -1.0},
    ])
    def test_negative_or_zero_invalid_ranges_are_rejected(self, changes):
        with pytest.raises(ValueError, match=next(iter(changes))):
            Conditions(**changes)

    @pytest.mark.parametrize("field", [
        "temperature_k", "pressure_atm", "dielectric", "photon_ev",
    ])
    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_nonfinite_coordinates_are_rejected(self, field, bad):
        with pytest.raises(ValueError, match=field):
            Conditions(**{field: bad})

    @pytest.mark.parametrize("bad", [True, None, "298"])
    def test_non_numeric_coordinates_are_rejected(self, bad):
        with pytest.raises(TypeError):
            Conditions(temperature_k=bad)

    def test_physical_boundary_values_are_allowed(self):
        assert Conditions(0.0, 0.0, 1e-12, 0.0).temperature_k == 0.0

    def test_copy_and_grid_share_the_constructor_gate(self):
        with pytest.raises(ValueError, match="temperature_k"):
            Conditions().with_(temperature_k=-1.0)
        with pytest.raises(ValueError, match="pressure_atm"):
            grid(pressures=(-1.0,))

    def test_misspelled_coordinate_is_not_silently_ignored(self):
        with pytest.raises(TypeError, match="temprature_k"):
            Conditions().with_(temprature_k=999.0)


# ==================================================================================
# The F2 detector
# ==================================================================================
class TestResponsiveness:
    """
    Finding F2: NaCl returned byte-identical energies across dielectric 1.0 to 109.0,
    because ``min(ionic, covalent)`` chose a branch with no solvation term.

    A flat response surface is the visible signature of that class of bug, and
    ``is_responsive`` is the check for it.
    """

    def test_flat_surface_is_detected(self):
        constant = Store(lambda c: -12.14162534017432, Conditions())
        positions = [Conditions(dielectric=e) for e in (1.0, 10.0, 40.0, 80.1, 109.0)]
        assert not is_responsive(constant, positions), (
            "a constant energy across a 100-fold dielectric change must be flagged"
        )

    def test_genuine_solvation_is_responsive(self):
        def born_like(c: Conditions) -> float:
            return -7.2 * (1.0 - 1.0 / c.dielectric)

        positions = [Conditions(dielectric=e) for e in (1.0, 10.0, 40.0, 80.1, 109.0)]
        assert is_responsive(Store(born_like, positions[0]), positions)

    def test_solvation_is_monotone_in_dielectric(self):
        """
        Physical law, testable: Born stabilisation of a charged species increases
        monotonically with dielectric and saturates. A model violating this is wrong
        regardless of how well it fits any single number.
        """
        def born_like(c: Conditions) -> float:
            return -7.2 * (1.0 - 1.0 / c.dielectric)

        eps = [1.0, 2.0, 5.0, 20.0, 80.1, 109.0]
        energies = [born_like(Conditions(dielectric=e)) for e in eps]
        assert all(b <= a for a, b in zip(energies, energies[1:])), energies
