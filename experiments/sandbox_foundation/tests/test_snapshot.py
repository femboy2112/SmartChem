"""Wave G -- the PhysicalWorldSnapshot contract: renderer-disabled identity + the two-digest separation.

SYNTHETIC / experimental.  The non-negotiable property: rendering a snapshot any number of times cannot alter the
canonical model state or either digest; display hints cannot move the model identity; evidence identity is
independent of model identity."""
import numpy as np
import pytest

from experiments.sandbox_foundation.mesh import MeshState, MeshSystem, chain_mesh, run_mesh, transport_step_mesh
from experiments.sandbox_foundation.snapshot import SCHEMA_VERSION, PhysicalWorldSnapshot, ascii_render


def _mesh3():
    return MeshSystem(("A", "B"), (0.1, 0.2), chain_mesh([1.0, 1.0, 1.0], [1.0, 1.0], [1.0, 1.0]))


# ---- THE non-negotiable property: rendering changes nothing ---------------------------------------------------
def test_render_count_does_not_alter_the_trajectory_or_the_digest():
    system = _mesh3()
    s0 = MeshState(np.array([[3.0, 0.0], [0.0, 1.0], [1.0, 2.0]]))
    plain = run_mesh(system, s0, 2.0, 20).state                       # a trajectory with NO rendering
    s = s0
    for k in range(20):                                               # the same trajectory, rendered every step
        s, _ = transport_step_mesh(system, s, 0.1, step=k)
        snap = PhysicalWorldSnapshot.from_mesh(system, s, model_tick=k)
        for _ in range(7):
            ascii_render(snap)
    assert np.array_equal(plain.n, s.n)                               # rendering changed NOTHING in the canonical state
    snap = PhysicalWorldSnapshot.from_mesh(system, s)
    d0, a0 = snap.model_digest, snap.amounts_mol.copy()
    for _ in range(100):
        ascii_render(snap)
    assert snap.model_digest == d0 and np.array_equal(snap.amounts_mol, a0)


# ---- display hints are cosmetic: they cannot move the model identity ------------------------------------------
def test_display_hints_do_not_change_the_model_digest_but_do_change_the_render():
    system = _mesh3()
    s = MeshState(np.array([[1.0, 2.0], [3.0, 0.5], [0.0, 1.0]]))
    base = PhysicalWorldSnapshot.from_mesh(system, s, display_hints={"colormap": "viridis"})
    styled = base.with_display_hints(colormap="magma", sep=" :: ")
    assert styled.model_digest == base.model_digest                  # cosmetics cannot move model identity (A3)
    assert styled.evidence_digest == base.evidence_digest
    assert ascii_render(styled) != ascii_render(base)                # ...but the rendering itself did change


# ---- model identity vs admission identity are independent -----------------------------------------------------
def test_evidence_digest_is_independent_of_the_model_digest():
    system = _mesh3()
    s = MeshState(np.array([[1.0, 2.0], [3.0, 0.5], [0.0, 1.0]]))
    a = PhysicalWorldSnapshot.from_mesh(system, s, evidence={"source": "rev-1", "checks": ["conservation"]})
    b = PhysicalWorldSnapshot.from_mesh(system, s, evidence={"source": "rev-2", "checks": ["conservation"]})
    assert a.model_digest == b.model_digest                          # same physical state -> same model receipt
    assert a.evidence_digest != b.evidence_digest                    # a source revision moves ONLY the evidence receipt


def test_a_changed_amount_moves_the_model_digest():
    system = _mesh3()
    a = PhysicalWorldSnapshot.from_mesh(system, MeshState(np.array([[1.0, 2.0], [3.0, 0.5], [0.0, 1.0]])))
    b = PhysicalWorldSnapshot.from_mesh(system, MeshState(np.array([[1.0, 2.0], [3.0, 0.5], [0.0, 1.5]])))
    assert a.model_digest != b.model_digest


# ---- explicit invalid/missing masks + immutability ------------------------------------------------------------
def test_invalid_mask_yields_nan_not_a_fabricated_zero():
    snap = PhysicalWorldSnapshot(("A", "B"), [1.0, 1.0], np.array([[2.0, 0.0], [0.0, 0.0]]),
                                 np.array([[True, True], [True, False]]), {"amount": "mol"}, 0, 0.0)
    c = snap.concentration_mol_per_m3()
    assert c[0, 0] == 2.0 and np.isnan(c[1, 1])                       # invalid cell -> NaN, not 0


def test_snapshot_arrays_are_read_only_and_schema_versioned():
    snap = PhysicalWorldSnapshot(("A",), [1.0], np.array([[2.0]]), np.array([[True]]), {}, 0, 0.0)
    assert snap.schema_version == SCHEMA_VERSION
    with pytest.raises(ValueError):
        snap.amounts_mol[0, 0] = 9.0                                 # read-only


def test_a_valid_cell_may_not_carry_a_nonfinite_amount():
    with pytest.raises(ValueError):
        PhysicalWorldSnapshot(("A",), [1.0], np.array([[np.nan]]), np.array([[True]]), {}, 0, 0.0)
