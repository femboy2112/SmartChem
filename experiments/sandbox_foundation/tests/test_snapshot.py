"""Wave G -- the PhysicalWorldSnapshot contract: renderer-disabled identity + the two-digest separation.

SYNTHETIC / experimental.  The non-negotiable property: rendering a snapshot any number of times cannot alter the
canonical model state or either digest; display hints cannot move the model identity; evidence identity is
independent of model identity."""
import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from experiments.sandbox_foundation.mechanism_adapter import adapt_step
from experiments.sandbox_foundation.mechanism_types import (
    AdmissionLevel, AdmissionPolicy, DescriptiveMechanism, KineticLaw, SourceStore)
from experiments.sandbox_foundation.mesh import MeshState, MeshSystem, chain_mesh, run_mesh, transport_step_mesh
from experiments.sandbox_foundation.snapshot import (
    SCHEMA_VERSION, ModelRunReceipt, PhysicalWorldSnapshot, QuantityKind, absent_receipt_dict, ascii_render)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


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


# ======================================================================================================
# Round IV -- C3: DEEP immutability (nested dicts + unlockable arrays) and a canonical, non-str() digest.
# ======================================================================================================
def _snap():
    system = _mesh3()
    s = MeshState(np.array([[1.0, 2.0], [3.0, 0.5], [0.0, 1.0]]))
    return PhysicalWorldSnapshot.from_mesh(
        system, s, evidence={"source": "rev-1", "checks": ["conservation"]},
        numerical_uncertainty={"abs_mol": 1e-9}, display_hints={"colormap": "viridis"})


def test_RIV_C3_every_nested_mapping_is_frozen():
    snap = _snap()
    d0, e0 = snap.model_digest, snap.evidence_digest
    for name in ("units", "conservation_diagnostics", "numerical_uncertainty", "evidence", "display_hints"):
        m = getattr(snap, name)
        with pytest.raises(TypeError):
            m["x"] = "mutated"                                  # MappingProxyType -> no item assignment
    # a nested list inside conservation_diagnostics became a tuple (immutable)
    assert isinstance(snap.conservation_diagnostics["inventory_totals"], tuple)
    assert snap.model_digest == d0 and snap.evidence_digest == e0  # nothing moved


def test_RIV_C3_arrays_cannot_be_write_reenabled_even_via_base():
    snap = _snap()
    d0 = snap.model_digest
    for name in ("amounts_mol", "valid_mask", "cell_volumes_m3"):
        a = getattr(snap, name)
        assert a.flags.writeable is False
        with pytest.raises(ValueError):
            a.setflags(write=True)                              # unlockable: base is an immutable bytes buffer
        base = a.base
        if hasattr(base, "setflags"):
            with pytest.raises(ValueError):
                base.setflags(write=True)
    assert snap.model_digest == d0


def test_RIV_C3_digest_refuses_a_non_serialisable_value_not_str_hash_it():
    class Weird:
        pass
    with pytest.raises(TypeError):                              # no str() fallback -> fail closed at construction
        PhysicalWorldSnapshot(("A",), [1.0], np.array([[2.0]]), np.array([[True]]),
                              {"amount": Weird()}, 0, 0.0)


def test_RIV_C3_renderer_isolation_matrix_leaves_the_digest_invariant():
    system = _mesh3()
    s = MeshState(np.array([[3.0, 0.0], [0.0, 1.0], [1.0, 2.0]]))
    # the SAME model input, realised with every rendering regime, must give one invariant model_digest.
    digests = []
    for regime in ("none", "one_per_tick", "many_per_tick", "cosmetic", "repeated_export"):
        snap = PhysicalWorldSnapshot.from_mesh(system, s, model_tick=4)
        if regime == "one_per_tick":
            ascii_render(snap)
        elif regime == "many_per_tick":
            for _ in range(13):
                ascii_render(snap)
        elif regime == "cosmetic":
            snap = snap.with_display_hints(colormap="magma", sep=" :: ")
            for _ in range(5):
                ascii_render(snap)
        elif regime == "repeated_export":
            for _ in range(50):
                _ = (ascii_render(snap), snap.concentration_mol_per_m3(), snap.amounts_mol.copy())
        digests.append(snap.model_digest)
    assert len(set(digests)) == 1                               # rendering / cosmetics never move the model identity


def test_RIV_C3_non_string_species_is_refused_evil_morty_F2():
    # evil-morty Round IV Finding 2: a bytes-led 3-tuple species was misread by _canon as an array store and
    # could collide two different worlds' model_digest.  Non-string species are now refused at construction, and
    # the array store is a typed _ArrayStore with delimited dtype/shape/bytes (no cross-boundary byte shift).
    with pytest.raises(ValueError):
        PhysicalWorldSnapshot((b"X", "f8(1,)", ()), [1.0], np.zeros((1, 3)), np.ones((1, 3), bool), {}, 0, 0.0)


# ======================================================================================================
# Wave F -- ModelRunReceipt (F1) and the 4-way quantity typing support (F2).
# ======================================================================================================
_OK = {"solver": "test", "convergence_status": "NOT_ITERATIVE",
       "tolerances": {"cons": 1e-12, "pos": 0.0}, "residuals": {"cons": 1e-16, "pos": 0.0}}


def _num(**over):
    d = json.loads(json.dumps(_OK))
    d.update(over)
    return d


def _snap_with(receipt, **kw):
    return PhysicalWorldSnapshot(("A",), [1.0], np.array([[2.0]]), np.array([[True]]), {"amount": "mol"}, 3, 0.5,
                                 receipt=receipt, **kw)


def _verified_executable():
    root = Path(tempfile.mkdtemp(prefix="sc_rcpt_src_"))
    art = {"record_id": "iso", "version": "3rd ed", "title": "Imaginary Handbook", "status": "current",
           "entries": {"iso": {
               "reactants": [{"smiles": "CCO", "count": 1}], "products": [{"smiles": "COC", "count": 1}],
               "kinetics": "elementary", "reversible": True,
               "k_f": {"value": 2.0e-3, "units": "s^-1"}, "k_r": {"value": 1.0e-3, "units": "s^-1"},
               "conditions": {"T_K": [280.0, 320.0], "phase": "liquid", "standard_state": "pure liquid, 1 bar"},
               "assumptions": ["ideal"]}}}
    (root / "iso@3rd ed.json").write_text(json.dumps(art))
    store = SourceStore(root)
    step = ExperimentStep.assembling(parse_smiles("COC"), (parse_smiles("CCO"),), (parse_smiles("COC"),))
    desc = DescriptiveMechanism.from_derivations([adapt_step(step)])
    omit = ("competing chemistry omitted for the test",)
    verified = desc.to_executable([store.law_from_source("iso", "3rd ed", "iso")], omissions=omit)
    synthetic = desc.to_executable([KineticLaw(2.0e-3, 1.0e-3, True, AdmissionLevel.SYNTHETIC, "s^-1", "s^-1",
                                               assumption="hypothetical")], omissions=omit)
    return verified, synthetic, AdmissionPolicy((store,))


def test_RF_F1_absent_receipt_reads_unadmitted_and_unverified():
    snap = _snap_with(None)
    assert snap.receipt is None
    d = absent_receipt_dict()
    assert d["present"] is False and d["admitted"] is False and d["scientific_measurement"] is False


def test_RF_F1_public_constructor_cannot_claim_admission_a_label_is_not_a_binding():
    r = ModelRunReceipt("m" * 8, _num(), admission_level="BENCHMARK_VALIDATED", law_levels=["BENCHMARK_VALIDATED"])
    assert r.admission_level == "BENCHMARK_VALIDATED"          # the DECLARATION is recorded...
    assert r.admitted is False and r.admission_derived is False   # ...but it is no authority
    assert r.scientific_measurement is False
    assert "UNADMITTED" in r.label
    with pytest.raises(ValueError):
        ModelRunReceipt("m", _num(), admission_level="TOTALLY_VERIFIED")   # not a real level


def test_RF_F1_admission_is_derived_from_the_executable_mechanism_under_a_policy():
    verified, synthetic, policy = _verified_executable()
    nm = _num()
    good = ModelRunReceipt.from_executable(verified, policy, nm)
    assert good.admitted is True and good.admission_derived is True
    assert good.admission_level == AdmissionLevel.SOURCE_VERIFIED.value
    assert good.model_identity == verified.model_identity
    assert tuple(tuple(x) for x in good.admission_identities) == tuple(verified.admission_identities)
    assert good.scientific_measurement is True                  # admitted AND numerically verified
    syn = ModelRunReceipt.from_executable(synthetic, policy, nm)
    assert syn.admitted is False and syn.admission_level == "SYNTHETIC"
    untrusted = ModelRunReceipt.from_executable(verified, AdmissionPolicy(()), nm)   # a store the policy doesn't trust
    assert untrusted.admitted is False                          # capped: a receipt from an untrusted store is not authority


@pytest.mark.parametrize("numerics, why", [
    (_num(residuals={"cons": 1e-16}), "pos residual missing -> fail closed"),
    (_num(residuals={"cons": 1e-16, "pos": None}), "None residual -> fail closed"),
    (_num(residuals={"cons": 1e-3, "pos": 0.0}), "residual above tolerance"),
    (_num(convergence_status="DIVERGED"), "non-converged status"),
    (_num(convergence_status="INITIAL_CONDITION"), "no step taken -> nothing verified"),
    (_num(tolerances={}), "no tolerance declared -> nothing to certify"),
    (_num(residuals={"cons": True, "pos": 0.0}), "a bool is not a residual"),
])
def test_RF_F1_numerically_verified_is_computed_and_fails_closed(numerics, why):
    assert ModelRunReceipt("m", numerics).numerically_verified is False, why
    assert ModelRunReceipt("m", _num()).numerically_verified is True


def test_RF_F1_a_nan_residual_is_refused_at_construction_not_hashed():
    nan = _num(residuals={"cons": float("nan"), "pos": 0.0})
    with pytest.raises(ValueError):                              # allow_nan=False in the canonical JSON
        _snap_with(ModelRunReceipt("m", nan))


def test_RF_F1_receipt_is_immutable():
    r = ModelRunReceipt("m", _num())
    with pytest.raises(AttributeError):
        r.admitted = True
    with pytest.raises(TypeError):
        r.numerics["residuals"]["cons"] = 0.0
    with pytest.raises(TypeError):
        _snap_with(r).receipt.numerics["solver"] = "x"


def test_RF_F1_receipt_sides_move_the_right_digest_only():
    base = _snap_with(ModelRunReceipt("m", _num()))
    # a different DECLARED admission level moves the EVIDENCE digest, never the model digest
    adm = _snap_with(ModelRunReceipt("m", _num(), admission_level="SOURCE_DECLARED"))
    assert adm.model_digest == base.model_digest and adm.evidence_digest != base.evidence_digest
    # different numerical assumptions / model identity move the MODEL digest, never the evidence digest
    num = _snap_with(ModelRunReceipt("m", _num(solver="other")))
    assert num.model_digest != base.model_digest and num.evidence_digest == base.evidence_digest
    ident = _snap_with(ModelRunReceipt("m2", _num()))
    assert ident.model_digest != base.model_digest and ident.evidence_digest == base.evidence_digest
    # having NO receipt is itself distinguishable from having one
    assert _snap_with(None).model_digest != base.model_digest


def test_RF_F1_receipt_must_be_a_receipt():
    with pytest.raises(TypeError):
        _snap_with({"admitted": True})                           # a dict claiming admission is not a receipt


def test_RF_F1_with_display_hints_preserves_the_receipt():
    snap = _snap_with(ModelRunReceipt("m", _num()), illustration={"glow": {"values": [0.5]}})
    styled = snap.with_display_hints(colormap="magma")
    assert styled.receipt is snap.receipt and styled.model_digest == snap.model_digest
    assert styled.evidence_digest == snap.evidence_digest and dict(styled.illustration) == dict(snap.illustration)


def test_RF_F2_illustration_is_excluded_from_both_digests_unsupported_is_authoritative():
    a = _snap_with(None, illustration={"glow": {"values": [0.1]}})
    b = _snap_with(None, illustration={"glow": {"values": [0.9]}, "sparkle": {"values": [1]}})
    assert a.model_digest == b.model_digest and a.evidence_digest == b.evidence_digest   # decoration moves nothing
    u = _snap_with(None, unsupported_quantities={"temperature_field_K": "K"})
    assert u.model_digest != a.model_digest        # declaring what the model does NOT supply is authoritative content
    assert dict(u.unsupported_quantities) == {"temperature_field_K": "K"}


def test_RF_F2_quantity_names_cannot_clash_across_kinds():
    for kw in ({"illustration": {"A": {"values": [1]}}},                      # collides with a species
               {"illustration": {"amount_mol": {"values": [1]}}},              # collides with a canonical field
               {"unsupported_quantities": {"concentration_mol_per_m3": "x"}},
               {"illustration": {"q": {}}, "unsupported_quantities": {"q": "K"}}):
        with pytest.raises(ValueError):
            _snap_with(None, **kw)


def test_RF_F2_four_kinds_exist_and_only_two_are_measurements():
    from experiments.sandbox_foundation.snapshot import MEASUREMENT_KINDS
    assert {k.value for k in QuantityKind} == {"CANONICAL", "MODEL_DERIVED", "UNSUPPORTED", "ILLUSTRATION"}
    assert MEASUREMENT_KINDS == {QuantityKind.CANONICAL, QuantityKind.MODEL_DERIVED}


def test_RF_F4_verify_integrity_detects_an_object_level_tamper():
    snap = _snap_with(ModelRunReceipt("m", _num()))
    assert snap.verify_integrity() is True
    from experiments.sandbox_foundation.snapshot import _store_array
    object.__setattr__(snap, "_amt", _store_array(np.array([[999.0]]), float))   # bypasses __setattr__ on purpose
    assert snap.verify_integrity() is False                       # python cannot forbid it; a consumer CAN detect it
