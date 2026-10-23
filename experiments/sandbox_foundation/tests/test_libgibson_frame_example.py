"""Wave G -- the frozen LibGibson frame example: a renderer-neutral observation the other repo can consume."""
import copy
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.sandbox_foundation import libgibson_frame_example as lge
from experiments.sandbox_foundation.libgibson_frame_example import (
    FrameContractError, HeadlessPresenter, ModelRun, example_snapshot, headless_replay, measurements,
    membrane_world, run_demo, to_frame, validate_frame)


def test_frame_has_the_required_schema_fields():
    snap, interfaces = example_snapshot()
    frame = to_frame(snap, interfaces)
    for key in ("schema_version", "model_digest", "evidence_digest", "model_tick", "physical_time_s",
                "geometry", "species", "fields", "invalid_mask", "units", "conservation_diagnostics",
                "display_hints"):
        assert key in frame, key
    g = frame["geometry"]
    assert g["n_cells"] == 3 and len(g["interfaces"]) == 2                 # three cells, two interfaces
    assert g["interfaces"] == [[0, 1], [1, 2]]                             # oriented (tail, head) pairs
    assert len(g["boundary_material"]) == 2                               # boundary identity present
    assert set(frame["fields"]) == set(frame["species"])
    for fld in frame["fields"].values():
        assert "amount_mol" in fld and "concentration_mol_per_m3" in fld
    assert frame["units"]["concentration"] == "mol/m^3"


def test_missing_data_is_null_not_a_fabricated_zero():
    snap, interfaces = example_snapshot()
    frame = to_frame(snap, interfaces)
    # cell 1, species 'tracer' was marked MISSING
    s = frame["species"].index("tracer")
    assert frame["invalid_mask"][1][s] is True
    assert frame["fields"]["tracer"]["concentration_mol_per_m3"][1] is None   # NaN -> JSON null, never 0.0
    assert frame["fields"]["tracer"]["amount_mol"][1] is None
    # a valid cell is a real float
    assert isinstance(frame["fields"]["acetate"]["concentration_mol_per_m3"][0], float)


def test_model_and_evidence_digests_are_independent():
    snap, _ = example_snapshot()
    # cosmetics never move the model identity ...
    styled = snap.with_display_hints(colormap="magma")
    assert styled.model_digest == snap.model_digest and styled.evidence_digest == snap.evidence_digest
    # ... and the two digests are distinct objects (model != evidence content)
    assert snap.model_digest != snap.evidence_digest


def test_frame_is_json_serialisable_and_renderer_neutral():
    snap, interfaces = example_snapshot()
    frame = to_frame(snap, interfaces)
    text = json.dumps(frame)                                             # survives the process boundary, no numpy
    assert json.loads(text)["schema_version"] == snap.schema_version
    # no numpy types leaked into the frame (would break a non-Python consumer)
    assert not any(isinstance(v, np.generic) for v in frame["geometry"]["cell_volumes_m3"])


def test_headless_replay_is_invariant():
    snap, _ = example_snapshot()
    d0 = snap.model_digest
    for n in (0, 1, 50):
        rep = headless_replay(snap, n)
        assert rep["model_digest_unchanged"] is True and rep["amounts_unchanged"] is True
    assert snap.model_digest == d0                                       # rendering never moved the model identity


# ======================================================================================================
# Wave F -- F1 receipt in the frame, F2 four-way typing, F3 end-to-end membrane demo, F4 runtime invariants.
# ======================================================================================================

# ---- F2: the four-way typing in the frame ----------------------------------------------------------------------
def test_RF_F2_example_frame_types_every_quantity_and_validates():
    snap, ifc = example_snapshot()
    frame = to_frame(snap, ifc)
    assert validate_frame(frame) == []
    assert frame["quantity_kinds"]["amount_mol"] == "CANONICAL"
    assert frame["quantity_kinds"]["concentration_mol_per_m3"] == "MODEL_DERIVED"
    t = frame["fields"]["tracer"]
    assert t["kinds"]["amount_mol"] == ["CANONICAL", "UNSUPPORTED", "CANONICAL"]            # the masked cell
    assert t["kinds"]["concentration_mol_per_m3"] == ["MODEL_DERIVED", "UNSUPPORTED", "MODEL_DERIVED"]
    assert t["amount_mol"][1] is None and t["concentration_mol_per_m3"][1] is None            # null, never 0
    # a legitimately-zero CANONICAL amount stays a real 0.0 (distinct from a missing one)
    assert frame["fields"]["acetate"]["amount_mol"][2] == 0.0
    assert frame["fields"]["acetate"]["kinds"]["amount_mol"][2] == "CANONICAL"


def test_RF_F1_a_frame_with_no_receipt_says_so_loudly():
    snap, ifc = example_snapshot()
    frame = to_frame(snap, ifc)
    assert frame["receipt"]["present"] is False
    assert frame["trust"]["admitted"] is False and frame["trust"]["scientific_measurement"] is False
    assert "NO-RECEIPT" in frame["trust"]["label"]


@pytest.mark.parametrize("corrupt", [
    lambda f: f["fields"]["tracer"]["amount_mol"].__setitem__(1, 0.0),                    # missing data forged to 0
    lambda f: f["fields"]["tracer"]["kinds"]["amount_mol"].__setitem__(0, "ILLUSTRATION"),  # decoration in a measurement slot
    lambda f: f["fields"]["acetate"]["amount_mol"].__setitem__(0, None),                  # CANONICAL silently null
    lambda f: f["fields"]["acetate"]["kinds"]["amount_mol"].__setitem__(0, "MADE_UP"),    # fifth kind
    lambda f: f["trust"].update(scientific_measurement=True),                             # forged trust
    lambda f: f.pop("receipt"),                                                           # receipt stripped
    lambda f: f["illustration"].update(glow={"kind": "ILLUSTRATION", "measurement": True, "values": [1]}),
    lambda f: f["unsupported"].update(T={"kind": "UNSUPPORTED", "unit": "K", "values": [0.0, 0.0, 0.0]}),
])
def test_RF_F2_a_frame_that_breaks_the_typing_contract_is_refused_not_drawn(corrupt):
    snap, ifc = example_snapshot()
    frame = to_frame(snap, ifc)
    corrupt(frame)
    assert validate_frame(frame) != []
    with pytest.raises(FrameContractError):
        HeadlessPresenter().render(json.dumps(frame))
    with pytest.raises(FrameContractError):
        measurements(frame)


def test_RF_F2_measurements_never_include_illustration_or_unsupported():
    run = ModelRun(*membrane_world(), 20.0)
    frame = to_frame(run.snapshot(), run.interfaces)
    assert set(frame["illustration"]) == {"glow"} and set(frame["unsupported"]) == {
        "temperature_field_K", "electric_potential_V"}
    m = measurements(frame)
    assert all(q in ("amount_mol", "concentration_mol_per_m3") for (_, q) in m)           # glow / temperature absent
    assert frame["unsupported"]["temperature_field_K"]["values"] == [None, None, None]
    assert frame["illustration"]["glow"]["measurement"] is False


# ---- F1 + F3: the end-to-end membrane demo --------------------------------------------------------------------
def _states(result):
    return [np.frombuffer(bytes.fromhex(r["n_hex"])).reshape(3, 2) for r in result["trajectory"]]


def test_RF_F3_neutral_tracer_crosses_a_configurable_membrane_over_real_ticks():
    res = run_demo(12, 1)
    n = _states(res)
    assert len(n) == 13
    # real TRANSITIONS: all 13 states and model digests are distinct
    assert len({r["model_digest"] for r in res["trajectory"]}) == 13
    X, Y = 0, 1
    for k in range(13):                                                     # conservation of each species, every tick
        assert n[k][:, X].sum() == pytest.approx(2.0e-3, abs=1e-15) and n[k][:, Y].sum() == pytest.approx(2.0e-3, abs=1e-15)
    # the RIGHT valve is shut for ticks 0..6 (opens before step index 6): nothing reaches cell 2
    for k in range(7):
        assert n[k][2].tolist() == [0.0, 0.0]
    assert n[12][2][X] > 0.0                                                # X crossed once the valve opened...
    assert n[12][2][Y] == 0.0                                               # ...Y never did: the right membrane is a wall for Y
    assert n[3][1][X] > 0.0 and n[3][1][Y] > 0.0                            # the LEFT membrane passes both
    assert [r["valves"] for r in res["trajectory"]][5] == (1.0, 0.0)
    assert [r["valves"] for r in res["trajectory"]][7] == (1.0, 1.0)


def test_RF_F1_demo_receipt_travels_in_every_frame_unadmitted_and_numerics_verified_after_a_step():
    app, n0 = membrane_world()
    run = ModelRun(app, n0, 20.0, schedule={6: (1.0, 1.0)})
    f0 = to_frame(run.snapshot(), run.interfaces)
    assert f0["receipt"]["numerics"]["convergence_status"] == "INITIAL_CONDITION"
    assert f0["trust"]["numerically_verified"] is False                     # no step yet -> nothing verified
    run.advance()
    f1 = to_frame(run.snapshot(), run.interfaces)
    r = f1["receipt"]
    assert r["present"] and r["admission_derived"] is True and r["admitted"] is False
    assert r["admission_level"] == "SYNTHETIC" and r["law_levels"] == []
    assert r["numerically_verified"] is True
    assert set(r["numerics"]["tolerances"]) == set(r["numerics"]["residuals"]) == {
        "conservation_abs_mol", "positivity_violation_mol", "passive_witness_excess_W"}
    assert r["numerics"]["residuals"]["conservation_abs_mol"] <= r["numerics"]["tolerances"]["conservation_abs_mol"]
    assert "NEUTRAL tracers only" in " ".join(r["numerics"]["assumptions"])
    assert f1["trust"]["scientific_measurement"] is False                   # numerically fine, but NOT admitted
    assert f1["model_digest"] != f1["evidence_digest"] and r["model_identity"]
    screen = HeadlessPresenter().render(json.dumps(f1))
    assert "NOT A VALIDATED MEASUREMENT" in screen and "UNADMITTED(SYNTHETIC)+NUMERICS-VERIFIED" in screen
    assert "(illustration, not a measurement)" in screen and "temperature_field_K: n/a" in screen


def test_RF_F3_every_tick_frame_is_plain_json_and_the_presenter_imports_no_libgibson():
    res = run_demo(12, 1)
    assert len(res["screens"]) == 13 and all(s.startswith("tick ") for s in res["screens"])
    run = ModelRun(*membrane_world(), 20.0)
    for _ in range(3):
        run.advance()
        frame = to_frame(run.snapshot(), run.interfaces)
        assert json.loads(json.dumps(frame)) == frame                       # lossless across the process boundary
        def walk(o):
            assert not isinstance(o, (np.generic, np.ndarray)), type(o)
            if isinstance(o, dict):
                [walk(v) for v in o.values()]
            elif isinstance(o, list):
                [walk(v) for v in o]
            else:
                assert o is None or isinstance(o, (str, bool, int, float)), type(o)
        walk(frame)
    assert not any(m == "libgibson" or m.startswith("libgibson.") for m in sys.modules)
    src = Path(lge.__file__).read_text()
    assert not any(line.lstrip().startswith(("import libgibson", "from libgibson")) for line in src.splitlines())


def test_RF_F3_presenter_holds_no_model_reference_and_takes_only_text():
    pres = HeadlessPresenter()
    assert vars(pres) == {}                                                  # no state, no handle to anything
    run = ModelRun(*membrane_world(), 20.0)
    with pytest.raises(Exception):
        pres.render(run.snapshot())                                          # a snapshot object is not a frame
    with pytest.raises(Exception):
        pres.render({"a": 1})


# ---- F4: presentation-frequency independence -------------------------------------------------------------------
def _traj(calls_per_tick, run_factory=None):
    return run_demo(12, calls_per_tick, run_factory=run_factory)["trajectory"]


def assert_frequency_independent(run_factory=None):
    """The headline invariant, as a reusable detector: ZERO, ONE, MANY (and an irregular) presentation calls per model
    tick must give a byte-identical authoritative trajectory (state bytes + both digests + valves + commands)."""
    base = _traj(0, run_factory)
    for calls in (1, 7, lambda tick: (tick * 3) % 5):
        assert _traj(calls, run_factory) == base, f"trajectory changed with presentation frequency {calls!r}"
    return base


def test_RF_F4_presentation_frequency_never_changes_the_authoritative_trajectory():
    base = assert_frequency_independent()
    assert len(base) == 13
    # and presenting did really happen in the non-zero runs (the invariant is not vacuous)
    assert run_demo(3, 4)["screens"][2].startswith("tick 2")
    assert run_demo(3, 0)["screens"][2] == ""


class _CountingRun(ModelRun):
    """MUTANT: presentation advances hidden state -- every snapshot() call nudges the amounts."""
    def snapshot(self):
        n = np.array(self._n) * (1.0 + 1.0e-9)
        n.setflags(write=False)
        self._n = n
        return super().snapshot()


class _ClockRun(ModelRun):
    """MUTANT: presentation advances physical time."""
    def snapshot(self):
        self._t += 1.0e-6
        return super().snapshot()


class _MemoRun(ModelRun):
    """MUTANT: the first presentation 'caches' the frame and the model then reads the cache back (a lazy-render
    optimisation gone wrong): trajectory depends on whether anything was ever rendered."""
    def snapshot(self):
        s = super().snapshot()
        seen = getattr(self, "_seen", {})
        seen[self._tick] = seen.get(self._tick, 0) + 1
        self._seen = seen
        if seen[self._tick] == 2:        # trajectory_record() is call #1; any PRESENTATION call is #2+
            self._commands.append((self._tick, -1, 0.0))     # presentation leaves a footprint in the model record
        return s


@pytest.mark.parametrize("mutant", [_CountingRun, _ClockRun, _MemoRun])
def test_RF_F4_RED_a_presentation_coupled_model_turns_the_invariant_red(mutant):
    with pytest.raises(AssertionError):
        assert_frequency_independent(mutant)


# ---- F4: no write-back (red-team #15) --------------------------------------------------------------------------
def _scribble(obj, hits, path="obj", depth=0, seen=None):
    """Try EVERY in-place mutation a hostile frame consumer could attempt on `obj` and everything reachable from it.
    `hits` collects the paths where a mutation actually SUCCEEDED."""
    seen = set() if seen is None else seen
    if id(obj) in seen or depth > 8:
        return
    seen.add(id(obj))
    if isinstance(obj, np.ndarray):
        for attempt in (lambda: obj.__setitem__(Ellipsis, 123.0),
                        lambda: (obj.setflags(write=True), obj.__setitem__(Ellipsis, 123.0)),
                        lambda: obj.base.__setitem__(Ellipsis, 123.0)):
            try:
                attempt()
                hits.append(path)
            except (ValueError, TypeError, AttributeError, IndexError):
                pass
        if isinstance(obj.base, np.ndarray):
            _scribble(obj.base, hits, path + ".base", depth + 1, seen)
    elif isinstance(obj, dict):
        for k in list(obj):
            _scribble(obj[k], hits, f"{path}[{k!r}]", depth + 1, seen)
        try:
            obj["__injected__"] = 1
            hits.append(path + "+key")
        except TypeError:
            pass
    elif isinstance(obj, Mapping):
        try:
            obj["__injected__"] = 1
            hits.append(path + "+key")
        except TypeError:
            pass
        for k in list(obj):
            _scribble(obj[k], hits, f"{path}[{k!r}]", depth + 1, seen)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            _scribble(obj[i], hits, f"{path}[{i}]", depth + 1, seen)
        try:
            obj.append("__injected__")
            hits.append(path + ".append")
        except (TypeError, AttributeError):
            pass
    elif hasattr(obj, "__dict__") or hasattr(type(obj), "__slots__"):
        for name in [n for n in dir(obj) if not n.startswith("__")]:
            try:
                val = getattr(obj, name)
            except Exception:
                continue
            if callable(val):
                continue
            try:
                setattr(obj, name, "HACKED")
                hits.append(f"{path}.{name}=")
            except (AttributeError, TypeError):
                pass
            try:
                delattr(obj, name)
                hits.append(f"{path}.{name} del")
            except (AttributeError, TypeError):
                pass
            _scribble(val, hits, f"{path}.{name}", depth + 1, seen)


def assert_no_write_back(run_factory=None):
    """Run the model; at EVERY tick hand a hostile consumer the snapshot AND the frame; let it scribble on everything.
    The authoritative trajectory must equal a pristine run's, and the snapshot (the object that crosses the boundary)
    must have accepted ZERO mutations.  Returns the number of mutations the snapshot accepted (must be 0)."""
    pristine = run_demo(12, 0, run_factory=run_factory)["trajectory"]
    app, n0 = membrane_world()
    run = (run_factory or ModelRun)(app, n0, 20.0, schedule={6: (1.0, 1.0)})
    traj, snap_hits = [run.trajectory_record()], []
    for _ in range(13):
        snap = run.snapshot()
        frame = to_frame(snap, run.interfaces)
        before = copy.deepcopy(frame)
        _scribble(snap, snap_hits, "snapshot")
        _scribble(frame, [], "frame")                       # the frame is a plain dict COPY: scribbling it is allowed...
        assert snap.verify_integrity()                      # ...but the snapshot must be untouched
        assert to_frame(run.snapshot(), run.interfaces) == before    # and a fresh frame ignores the scribbles
        if len(traj) <= 12:
            run.advance()
            traj.append(run.trajectory_record())
    assert traj == pristine, "a frame consumer's writes reached the authoritative model"
    return snap_hits


def test_RF_F4_15_a_hostile_frame_consumer_cannot_write_back_into_the_model():
    assert assert_no_write_back() == []        # zero mutations accepted by the snapshot; model trajectory pristine


class _LiveArrayRun(ModelRun):
    """MUTANT: snapshot() leaks the LIVE writable state array (and a mutable dict view) instead of a private copy."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._n = np.array(self._n)                              # writable, and handed out below

    def advance(self):
        super().advance()
        self._n = np.array(self._n)                              # keep the live array writable after each step

    def snapshot(self):
        real = super().snapshot()
        return SimpleNamespace(amounts_mol=self._n, model_digest=real.model_digest,
                               verify_integrity=lambda: True, **{
                                   k: getattr(real, k) for k in ("species", "cell_volumes_m3", "valid_mask", "units",
                                                                 "model_tick", "physical_time_s", "receipt",
                                                                 "conservation_diagnostics", "numerical_uncertainty",
                                                                 "boundary_material", "evidence", "display_hints",
                                                                 "illustration", "unsupported_quantities",
                                                                 "schema_version", "evidence_digest",
                                                                 "concentration_mol_per_m3")})


def test_RF_F4_15_RED_a_leaky_snapshot_that_exposes_live_state_turns_the_write_back_probe_red():
    with pytest.raises(AssertionError):
        assert_no_write_back(_LiveArrayRun)


def test_RF_F4_15_an_object_level_tamper_cannot_reach_the_model_and_is_detectable():
    run = ModelRun(*membrane_world(), 20.0)
    pristine = run.trajectory_record()
    snap = run.snapshot()
    from experiments.sandbox_foundation.snapshot import _store_array
    object.__setattr__(snap, "_amt", _store_array(np.zeros((3, 2)), float))   # forge the consumer's private copy
    assert snap.verify_integrity() is False                                  # the forged snapshot is detectable...
    assert run.trajectory_record() == pristine                               # ...and the model never saw it (private copy)
    run.advance()
    assert run.snapshot().verify_integrity() is True                         # a fresh snapshot is unaffected


def test_RF_F4_15_control_enters_only_through_the_model_command_api_and_is_recorded():
    run = ModelRun(*membrane_world(), 20.0)
    run.set_valve(1, 1.0)                                                    # the SmartChem-owned control path
    rec = run.trajectory_record()
    assert rec["valves"] == (1.0, 1.0) and rec["commands"] == ((0, 1, 1.0),)  # a valve change is visible in the record
    # nothing in the presentation surface offers a way to do it: no frame/snapshot attribute refers to the run
    snap, frame = run.snapshot(), to_frame(run.snapshot(), run.interfaces)
    assert not any(isinstance(v, ModelRun) for v in vars(HeadlessPresenter()).values())
    assert "run" not in frame and not hasattr(snap, "run")
    ok, _ = membrane_world()
    assert tuple(ok.valves) == (1.0, 0.0)                                    # the world factory is not mutated by running


# ======================================================================================================
# Wave F follow-up -- F-1 (trust/digests bound to the receipt), F-2 (typed refusal, never KeyError).
# ======================================================================================================
def _demo_frame(ticks=2):
    run = ModelRun(*membrane_world(), 20.0)
    for _ in range(ticks):
        run.advance()
    return to_frame(run.snapshot(), run.interfaces)


def _admitted_frame():
    """A genuinely ADMITTED+verified frame: the receipt minted by from_executable, spliced onto a real snapshot."""
    from experiments.sandbox_foundation.snapshot import ModelRunReceipt, PhysicalWorldSnapshot
    from experiments.sandbox_foundation.tests.test_snapshot import _verified_executable
    verified, _, policy = _verified_executable()
    run = ModelRun(*membrane_world(), 20.0)
    run.advance()
    base = run.snapshot()
    rec = ModelRunReceipt.from_executable(verified, policy, base.receipt.numerics)
    snap = PhysicalWorldSnapshot(
        base.species, base.cell_volumes_m3, base.amounts_mol, base.valid_mask, base.units, base.model_tick,
        base.physical_time_s, base.conservation_diagnostics, base.numerical_uncertainty, base.boundary_material,
        base.evidence, base.display_hints, receipt=rec, illustration=base.illustration,
        unsupported_quantities=base.unsupported_quantities)
    return to_frame(snap, run.interfaces)


def test_RF_F1_genuine_frames_validate_clean_including_a_really_admitted_one():
    assert validate_frame(_demo_frame()) == []
    f = _admitted_frame()
    assert f["trust"]["scientific_measurement"] is True and validate_frame(f) == []
    screen = HeadlessPresenter().render(json.dumps(f))
    assert "NOT A VALIDATED MEASUREMENT" not in screen and "ADMITTED+NUMERICS-VERIFIED" in screen


def test_RF_F1_RED_a_forged_trust_block_on_an_unadmitted_receipt_is_caught_and_never_shown_as_validated():
    f = _demo_frame()
    assert f["receipt"]["admitted"] is False
    f["trust"] = {"label": "ADMITTED+NUMERICS-VERIFIED", "admitted": True, "numerically_verified": True,
                  "scientific_measurement": True}                  # overwrite ONLY the trust block
    probs = validate_frame(f)
    assert any("trust" in p for p in probs)                        # the binding is enforced
    with pytest.raises(FrameContractError):
        HeadlessPresenter().render(json.dumps(f))                  # strict presenter refuses
    screen = HeadlessPresenter().render(json.dumps(f), strict=False)
    assert "NOT A VALIDATED MEASUREMENT" in screen                 # verdict from the RECEIPT, not the forged block
    assert "CONTRACT VIOLATIONS" in screen


@pytest.mark.parametrize("forge", [
    lambda f: f["receipt"].update(numerically_verified=True, scientific_measurement=True),   # receipt flags vs numerics
    lambda f: f["receipt"]["numerics"]["residuals"].update(conservation_abs_mol=5.0),        # verdict vs residuals
    lambda f: f["receipt"].update(admitted=True),                                           # admitted w/o derivation/level
    lambda f: f["receipt"].update(admitted=True, admission_derived=True),                   # ... w/o a verified level
    lambda f: f["receipt"].update(label="ADMITTED+NUMERICS-VERIFIED"),
    lambda f: f.update(model_digest="0" * 64),
    lambda f: f.update(evidence_digest="f" * 64),
    lambda f: f["fields"]["X"]["amount_mol"].__setitem__(0, 1.0),                           # state edited, digest stale
    lambda f: f["geometry"]["boundary_material"].__setitem__(0, "inert wall"),
    lambda f: f["receipt"].update(model_identity="other"),
    lambda f: f["evidence"].update(admission="SOURCE_VERIFIED"),
])
def test_RF_F1_every_unmoored_claim_is_flagged_digest_and_verdict_are_recomputed(forge):
    f = _demo_frame()
    forge(f)
    assert validate_frame(f) != []
    with pytest.raises(FrameContractError):
        HeadlessPresenter().render(json.dumps(f))


def test_RF_F1_a_forged_trust_on_a_no_receipt_frame_is_caught_too():
    snap, ifc = example_snapshot()
    f = to_frame(snap, ifc)
    assert validate_frame(f) == []
    f["trust"].update(admitted=True, scientific_measurement=True, numerically_verified=True)
    assert any("trust" in p for p in validate_frame(f))


def test_RF_F1_digest_recompute_covers_masked_cells_and_round_trips_through_json():
    snap, ifc = example_snapshot()                                   # has a MASKED cell (null in the frame)
    f = json.loads(json.dumps(to_frame(snap, ifc)))
    assert validate_frame(f) == []


@pytest.mark.parametrize("damage", [
    lambda f: f["fields"]["X"].pop("kinds"),
    lambda f: f["fields"]["X"]["kinds"].pop("amount_mol"),
    lambda f: f["fields"]["X"].pop("amount_mol"),
    lambda f: f["fields"]["X"]["kinds"].update(concentration_mol_per_m3=[]),
    lambda f: f.pop("fields"),
    lambda f: f.pop("geometry"),
    lambda f: f["receipt"].pop("numerics"),
    lambda f: f.update(receipt=None),
    lambda f: f.update(fields={"X": None}),
    lambda f: f.update(species=None),
    lambda f: f.pop("invalid_mask"),
])
def test_RF_F2_a_malformed_frame_is_a_typed_refusal_never_a_bare_keyerror(damage):
    f = _demo_frame()
    damage(f)
    probs = validate_frame(f)                                         # must RETURN problems, not raise KeyError
    assert probs != []
    with pytest.raises(FrameContractError):
        HeadlessPresenter().render(json.dumps(f))
    with pytest.raises(FrameContractError):
        measurements(f)
    for junk in ("[]", "3", "null"):
        with pytest.raises(FrameContractError):
            HeadlessPresenter().render(junk)
