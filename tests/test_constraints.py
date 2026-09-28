"""CLI-CAN-02 brick 1: the shared section-11 PhysicalBounds leaf, and the typed request expressing it.

PhysicalBounds is the ONE T/P constraint model: ConstraintBox delegates its validation to it (no duplicate rules),
and the service's ConstraintPolicy carries it (so the request declares a real section-11 constraint that rides the
semantic_digest).  HONESTY under test: the constraint is DECLARED and identity-bearing, but routes are NOT yet
filtered by it -- the human render must say so and never imply otherwise.
"""
from __future__ import annotations

import io
import json
import math
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import main
from smartchem.constraints import PhysicalBounds
from smartchem.experiment.drafter import ConstraintBox
from smartchem.service import (
    ConstraintPolicy,
    build_recompile_request,
    deserialize_request,
    run_compilation,
    serialize_request,
)


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestPhysicalBounds:
    def test_valid_bounds_construct(self):
        b = PhysicalBounds.of(max_temperature_k=400.0, min_pressure_atm=1.0, max_pressure_atm=5.0)
        assert b.constrains_anything and "T<=400 K" in b.describe()

    def test_unconstrained_constrains_nothing(self):
        assert PhysicalBounds.unconstrained().constrains_anything is False
        assert PhysicalBounds.unconstrained().describe() == "unconstrained"

    @pytest.mark.parametrize("kw", [
        dict(max_temperature_k=-1.0),
        dict(max_temperature_k=0.0),
        dict(max_pressure_atm=math.inf),
        dict(min_pressure_atm=math.nan),
    ])
    def test_nonpositive_or_nonfinite_is_refused(self, kw):
        with pytest.raises(ValueError):
            PhysicalBounds.of(**kw)

    def test_a_bool_is_not_a_number(self):
        with pytest.raises(TypeError):
            PhysicalBounds.of(max_temperature_k=True)

    def test_inverted_pressure_window_is_refused(self):
        with pytest.raises(ValueError, match="min_pressure_atm cannot exceed"):
            PhysicalBounds.of(min_pressure_atm=5.0, max_pressure_atm=2.0)

    def test_bad_schema_version_refused(self):
        with pytest.raises(ValueError, match="schema_version"):
            PhysicalBounds("wrong", 400.0, None, None)

    def test_digest_is_bound_sensitive(self):
        assert PhysicalBounds.of(max_temperature_k=400.0).digest != PhysicalBounds.of(max_temperature_k=401.0).digest
        assert PhysicalBounds.of(max_temperature_k=400.0).digest == PhysicalBounds.of(max_temperature_k=400.0).digest


class TestConstraintBoxDelegatesToTheOneAuthority:
    @pytest.mark.parametrize("kw", [
        dict(max_temperature_k=400.0),                       # ok
        dict(max_temperature_k=-1.0),                        # nonpositive
        dict(max_pressure_atm=math.inf),                     # nonfinite
        dict(min_pressure_atm=5.0, max_pressure_atm=2.0),    # inverted
        dict(max_temperature_k=True),                        # bool
    ])
    def test_constraintbox_raises_iff_physicalbounds_raises(self, kw):
        def _err(f):
            try:
                f()
                return None
            except (TypeError, ValueError) as exc:
                return type(exc)
        assert _err(lambda: ConstraintBox(**kw)) == _err(lambda: PhysicalBounds.of(**kw))

    def test_constraintbox_exposes_its_physical_bounds(self):
        box = ConstraintBox(max_temperature_k=400.0, max_pressure_atm=5.0)
        assert box.physical_bounds == PhysicalBounds.of(max_temperature_k=400.0, max_pressure_atm=5.0)


class TestConstraintRidesTheRequestIdentity:
    def test_a_declared_constraint_moves_the_semantic_digest(self):
        base = build_recompile_request("water")
        hot = build_recompile_request("water", max_temperature_k=400.0)
        assert base.semantic_digest != hot.semantic_digest        # the constraint is part of the search identity
        assert base.constraints.bounds.constrains_anything is False

    def test_same_bounds_share_the_digest(self):
        assert (
            build_recompile_request("water", max_temperature_k=400.0).semantic_digest
            == build_recompile_request("water", max_temperature_k=400.0).semantic_digest
        )

    def test_different_bounds_split(self):
        assert (
            build_recompile_request("water", max_pressure_atm=2.0).semantic_digest
            != build_recompile_request("water", max_pressure_atm=3.0).semantic_digest
        )

    def test_the_constraint_origin_tracks_explicitness(self):
        assert dict(build_recompile_request("water").origins)["constraints"].value == "DEFAULT"
        assert dict(build_recompile_request("water", max_temperature_k=400.0).origins)["constraints"].value == "EXPLICIT"

    def test_passing_both_a_policy_and_a_bound_kwarg_is_refused(self):
        with pytest.raises(ValueError, match="either constraints or the T/P bound"):
            build_recompile_request(
                "water",
                constraints=ConstraintPolicy(PhysicalBounds.of(max_temperature_k=300.0)),
                max_temperature_k=400.0,
            )

    def test_round_trip_preserves_the_bounds_and_digest(self):
        req = build_recompile_request("water", max_temperature_k=400.0, max_pressure_atm=5.0)
        back = deserialize_request(serialize_request(req))
        assert back.constraints.bounds == req.constraints.bounds
        assert back.semantic_digest == req.semantic_digest

    def test_result_digest_reflects_the_constraint(self):
        # equal semantic_digest => equal result_digest still holds WITH the constraint in the identity.
        a = run_compilation(build_recompile_request("water", max_temperature_k=400.0))
        b = run_compilation(build_recompile_request("water", max_temperature_k=400.0))
        assert a.result_digest == b.result_digest


class TestCliConstraintFlags:
    def test_emit_request_records_the_constraint(self):
        code, out, _ = _cli(["recompile", "water", "--max-temp", "400", "--emit-request"])
        assert code == 0
        req = json.loads(out)
        assert req["constraints"]["max_temperature_k"] == 400.0

    def test_compile_and_recompile_stay_byte_identical(self):
        # CLI-CAN-01 must SURVIVE: the same --max-temp yields byte-identical requests across the two aliases.
        _, rc, _ = _cli(["recompile", "water", "--max-temp", "400", "--emit-request"])
        _, cc, _ = _cli(["compile", "water", "--max-temp", "400", "--emit-request"])
        assert rc == cc

    def test_human_render_shows_the_constraint_is_applied(self):
        # CLI-CAN-02 brick 2: the constraint is now APPLIED -- the routes are ranked against the bench box.  The
        # methyl-acetate search finds routes, so the note reports the real fit tally and the ranked block is shown.
        code, out, _ = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--max-temp", "500"])
        assert "constraint APPLIED" in out and "T<=500 K" in out
        assert "ranked routes (best first" in out    # the per-route fit disposition is surfaced, not just declared

    def test_the_caveat_appears_in_BOTH_human_and_json(self):
        # the disclosure lives in the RESPONSE diagnostics, so --json carries it too (CLI-JSON-01 agreement): human
        # and machine read the SAME applied-constraint note; neither view can drift from the other.
        _, human, _ = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--max-temp", "500"])
        _, jout, _ = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2", "--max-temp", "500", "--json"])
        payload = json.loads(jout)
        note = next(d for d in payload["diagnostics"] if "constraint APPLIED" in d)
        assert note in human    # the exact same caveat string in both views
        assert payload["ranked_route_dossiers"], "the machine payload must carry the ranked fit dispositions"

    def test_no_constraint_note_when_unconstrained(self):
        _, out, _ = _cli(["recompile", "smiles:CC(=O)OC", "--max-depth", "2"])
        assert "constraint DECLARED" not in out

    @pytest.mark.parametrize("bad", ["-5", "inf", "0"])
    def test_a_bad_bound_is_a_loud_exit_2_not_a_traceback(self, bad):
        code, out, err = _cli(["recompile", "water", "--max-temp", bad])
        assert code == 2
        assert "Traceback" not in err and "Traceback" not in out

    def test_min_pressure_flag_rides_the_request(self):
        _, out, _ = _cli(["recompile", "water", "--min-pressure", "0.5", "--emit-request"])
        req = json.loads(out)
        assert req["constraints"]["min_pressure_atm"] == 0.5

    def test_inverted_pressure_window_via_cli_is_a_loud_exit_2(self):
        # min > max is a physically empty window -- PhysicalBounds refuses it -> exit 2, no traceback (CLI-ERR-01).
        code, out, err = _cli(["recompile", "water", "--min-pressure", "5", "--max-pressure", "2"])
        assert code == 2
        assert "Traceback" not in err and "Traceback" not in out

    def test_compile_human_dossier_also_applies_and_discloses_the_constraint(self):
        # CLI-CAN-02 brick 2: `compile`'s human path renders a compile_synthesis dossier that now APPLIES the same
        # section-11 box (ConstraintBox.of_bounds) the recompile service uses -- alias coherence.  Its note comes from
        # its OWN applied ranking via the ONE constraint_note authority, so it can never drift from recompile's.
        _, out, _ = _cli(["compile", "acetic anhydride", "--max-depth", "2", "--max-temp", "500"])
        assert "constraint APPLIED" in out and "T<=500 K" in out
        # and it must NEVER read as constraint-fitted beyond what was checked: an undeclared-dimension route is UNKNOWN
        assert "never a silent pass" in out


class TestD14TemperatureRange:
    """Round V X-high D14 / F-1: temperature is a RANGE on the ONE shared leaf. v1alpha1 could say "cannot exceed
    500 K" but never "cannot get below 250 K", so a 77 K cooling step had no honest capability coordinate. The floor
    is appended LAST (positional construction unchanged); ``None`` keeps the legacy UNCONSTRAINED reading."""

    def test_the_current_schema_is_v1alpha2_and_of_emits_it(self):
        from smartchem.constraints import PHYSICAL_BOUNDS_SCHEMA, PHYSICAL_BOUNDS_SCHEMA_V1
        assert PHYSICAL_BOUNDS_SCHEMA == "smartchem.constraints/physical-bounds-v1alpha2"
        assert PHYSICAL_BOUNDS_SCHEMA_V1 == "smartchem.constraints/physical-bounds-v1alpha1"
        assert PhysicalBounds.of(min_temperature_k=273.15).schema_version == PHYSICAL_BOUNDS_SCHEMA
        assert PhysicalBounds().schema_version == PHYSICAL_BOUNDS_SCHEMA

    def test_a_floor_alone_constrains_and_describes_itself_before_the_ceiling(self):
        floor_only = PhysicalBounds.of(min_temperature_k=273.15)
        assert floor_only.constrains_anything and floor_only.describe() == "T>=273.15 K"
        both = PhysicalBounds.of(min_temperature_k=273.15, max_temperature_k=500.0)
        assert both.describe().startswith("T>=273.15 K, T<=500 K")

    def test_legacy_v1alpha1_is_accepted_only_without_a_floor(self):
        from smartchem.constraints import PHYSICAL_BOUNDS_SCHEMA_V1
        legacy = PhysicalBounds(PHYSICAL_BOUNDS_SCHEMA_V1, 400.0, 1.0, 2.0)  # a released v0.8 box, positionally
        assert legacy.min_temperature_k is None and legacy.max_temperature_k == 400.0
        with pytest.raises(ValueError, match="no temperature floor"):
            PhysicalBounds(PHYSICAL_BOUNDS_SCHEMA_V1, 400.0, None, None, 273.15)

    def test_positional_construction_is_unchanged_by_the_appended_floor(self):
        from smartchem.constraints import PHYSICAL_BOUNDS_SCHEMA
        b = PhysicalBounds(PHYSICAL_BOUNDS_SCHEMA, 400.0, 1.0, 5.0)
        assert (b.max_temperature_k, b.min_pressure_atm, b.max_pressure_atm, b.min_temperature_k) == (400.0, 1.0, 5.0,
                                                                                                        None)

    def test_an_empty_temperature_window_is_refused_but_a_point_window_is_not(self):
        with pytest.raises(ValueError, match="min_temperature_k cannot exceed max_temperature_k"):
            PhysicalBounds.of(min_temperature_k=600.0, max_temperature_k=500.0)
        point = PhysicalBounds.of(min_temperature_k=500.0, max_temperature_k=500.0)
        assert point.min_temperature_k == point.max_temperature_k == 500.0

    @pytest.mark.parametrize("value", [0, -1.0, float("inf"), float("nan")])
    def test_a_nonpositive_or_nonfinite_floor_is_refused(self, value):
        with pytest.raises(ValueError, match="min_temperature_k must be finite and positive"):
            PhysicalBounds.of(min_temperature_k=value)

    def test_a_bool_floor_is_not_a_number(self):
        with pytest.raises(TypeError, match="min_temperature_k must be a real number"):
            PhysicalBounds.of(min_temperature_k=True)

    def test_the_floor_is_identity_bearing(self):
        assert PhysicalBounds.of(min_temperature_k=273.15).digest != PhysicalBounds.of().digest
        assert PhysicalBounds.of(min_temperature_k=273.15).digest != PhysicalBounds.of(min_temperature_k=195.15).digest

    def test_constraintbox_delegates_the_floor_and_never_drops_it(self):
        # MP6's bridge: a floor declared on the shared leaf must survive into the ranking box (of_bounds) and back.
        with pytest.raises(ValueError, match="min_temperature_k cannot exceed"):
            ConstraintBox(min_temperature_k=600.0, max_temperature_k=500.0)
        bounds = PhysicalBounds.of(min_temperature_k=273.15, max_temperature_k=500.0)
        box = ConstraintBox.of_bounds(bounds)
        assert box.min_temperature_k == 273.15 and box.physical_bounds == bounds
        assert ConstraintBox(min_temperature_k=273.15).constrains_anything
        assert ConstraintBox.of_bounds(PhysicalBounds.of(max_temperature_k=500.0)).min_temperature_k is None


class TestD14ExperimentCliMinTemp:
    """``python -m smartchem.experiment --min-temp K`` -- the same validation style as the other T/P flags."""

    def _syn(self, argv):
        from smartchem.experiment.cli import main as syn_main
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = syn_main(argv)
            except SystemExit as exc:  # argparse's own type errors
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    @pytest.mark.parametrize("bad", ["0", "-5", "nan", "inf", "cold"])
    def test_a_bad_floor_is_an_argparse_exit_2(self, bad):
        code, _, _ = self._syn(["water", "--min-temp", bad, "--emit-request"])
        assert code == 2

    def test_the_floor_rides_the_emitted_request(self):
        code, out, err = self._syn(["water", "--min-temp", "250", "--emit-request"])
        assert code == 0, err
        assert json.loads(out)["constraints"]["min_temperature_k"] == 250.0

    def test_a_floor_above_the_ceiling_is_a_loud_exit_2(self):
        code, out, err = self._syn(["water", "--min-temp", "300", "--max-temp", "250", "--emit-request"])
        assert code == 2
        assert "min_temperature_k cannot exceed max_temperature_k" in err
        assert "Traceback" not in err and "Traceback" not in out
