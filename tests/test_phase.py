"""The Clausius-Clapeyron phase estimator -- proven physically sane and honest about missing inputs."""
from smartchem.data.stability import StabilityRef, stability_for_named
from smartchem.conditions import Interval
from smartchem.experiment.phase import boiling_point_at_pressure, estimate_phase


class TestBoilingPointAtPressure:
    def test_lower_pressure_lowers_the_boiling_point(self):
        # water: 373 K at 1 atm; a vacuum boils it cooler, higher pressure hotter
        assert boiling_point_at_pressure(373.13, 40.66, 1.0) == 373.13
        assert boiling_point_at_pressure(373.13, 40.66, 0.1) < 373.13
        assert boiling_point_at_pressure(373.13, 40.66, 5.0) > 373.13

    def test_nonpositive_pressure_is_infinite_not_a_crash(self):
        assert boiling_point_at_pressure(373.13, 40.66, 0.0) == float("inf")


class TestEstimatePhase:
    def test_water_phase_moves_with_pressure(self):
        w = stability_for_named("H2O", "water")  # bp + dHvap sourced
        assert estimate_phase(w, 340, 5.0) == "liquid"   # below its 5-atm bp
        assert estimate_phase(w, 340, 0.1) == "gas"       # above its 0.1-atm bp
        assert estimate_phase(w, 260, 1.0) == "solid"     # below its melting point

    def test_no_boiling_or_dhvap_refuses_the_gas_boundary(self):
        # a record with only a melting point cannot place the liquid/gas boundary -> None (not a guess)
        rec = StabilityRef("X1", "mystery", Interval(300, 300, "K"), None, None, True, "test")
        assert estimate_phase(rec, 350, 1.0) is None      # above melting, but gas/liquid unknown
        assert estimate_phase(rec, 250, 1.0) == "solid"   # below melting is still confidently solid
