"""Wave G -- the frozen LibGibson frame example: a renderer-neutral observation the other repo can consume."""
import json

import numpy as np

from experiments.sandbox_foundation.libgibson_frame_example import example_snapshot, headless_replay, to_frame


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
