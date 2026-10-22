"""Wave A4: evidence identity survives the whole conversion pipeline
    ExperimentStep -> InventoryDerivation -> DescriptiveMechanism -> ExecutableMechanism -> twocell.Mechanism
                   -> PhysicalWorldSnapshot
and the two identities stay orthogonal: the AUTHORITATIVE model identity moves with chemistry / kinetics, the
EVIDENCE/ADMISSION identity moves with the source, a display relabel moves neither, and a downgrade from verified
to synthetic cannot silently disappear.  SYNTHETIC / experimental sandbox."""
import numpy as np

from experiments.sandbox_foundation.mechanism_adapter import adapt_step
from experiments.sandbox_foundation.mechanism_types import (
    AdmissionLevel, AdmissionReceipt, DescriptiveMechanism, KineticLaw, SourceRecord, VerificationStatus)
from experiments.sandbox_foundation.mesh import MeshState, MeshSystem, chain_mesh
from experiments.sandbox_foundation.snapshot import PhysicalWorldSnapshot
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

A, B, W = parse_smiles("CCO"), parse_smiles("COC"), parse_smiles("O")
OMIT = ("competing chemistry omitted for the test",)
ISO_STEP = ExperimentStep.assembling(B, (A,), (B,))                     # A <-> B isomerization (both C2H6O)
EST_STEP = ExperimentStep.assembling(parse_smiles("CCOC(C)=O"), (parse_smiles("CCO"), parse_smiles("CC(=O)O")),
                                     (parse_smiles("CCOC(C)=O"), W))     # esterification (different chemistry)


def _record(version="3rd ed"):
    return SourceRecord("Imaginary Handbook", version, ("ethanol", "DME"), "s^-1", "298 K ideal",
                        "elementary unimolecular", "280-320 K")


def _verified_uni(k_f=2.0e-3, receipt=None):
    return KineticLaw(k_f, 1.0e-3, True, AdmissionLevel.SOURCE_VERIFIED, "s^-1", "s^-1",
                      receipt=receipt or AdmissionReceipt(_record(), VerificationStatus.VERIFIED))


def _synthetic_uni():
    return KineticLaw(2.0e-3, 1.0e-3, True, AdmissionLevel.SYNTHETIC, "s^-1", "s^-1",
                      assumption="hypothetical first-order constants")


def _verified_bimol():
    return KineticLaw(2.0e-3, 1.0e-3, True, AdmissionLevel.SOURCE_VERIFIED, "m^3 mol^-1 s^-1", "m^3 mol^-1 s^-1",
                      receipt=AdmissionReceipt(_record(), VerificationStatus.VERIFIED))


def _ex(step, law):
    return DescriptiveMechanism.from_derivations([adapt_step(step)]).to_executable([law], omissions=OMIT)


def _snapshot(ex, *, evidence=None, display_hints=None):
    """Full pipeline tail: executable -> twocell -> a 2-cell mesh state -> PhysicalWorldSnapshot."""
    mech = ex.to_twocell()
    S = len(mech.species)
    sysm = MeshSystem(mech.species, (0.0,) * S, chain_mesh([1.0, 1.0], [1.0], [1.0]), mechanism=mech)
    n0 = np.zeros((2, S))
    n0[:, 0] = 1.0                                                      # one unit of the first species in each cell
    st = MeshState(n0)
    return PhysicalWorldSnapshot.from_mesh(sysm, st, evidence=evidence or {}, display_hints=display_hints or {})


# (1) a changed chemical identity changes the model identity
def test_A4_chemical_identity_change_moves_model_identity():
    iso = _ex(ISO_STEP, _verified_uni())
    est = _ex(EST_STEP, _verified_bimol())
    assert iso.model_identity != est.model_identity


# (2) a changed kinetic parameter changes the model identity (and NOT the evidence identity, same receipt)
def test_A4_kinetic_parameter_change_moves_model_identity_only():
    slow = _ex(ISO_STEP, _verified_uni(k_f=2.0e-3))
    fast = _ex(ISO_STEP, _verified_uni(k_f=8.0e-3))
    assert slow.model_identity != fast.model_identity
    assert slow.admission_identities == fast.admission_identities      # same source receipt -> same evidence id


# (3) a changed verified source revision changes the evidence identity, NOT the model content
def test_A4_source_revision_moves_evidence_not_model():
    r1 = _ex(ISO_STEP, _verified_uni(receipt=AdmissionReceipt(_record("3rd ed"), VerificationStatus.VERIFIED)))
    r2 = _ex(ISO_STEP, _verified_uni(receipt=AdmissionReceipt(_record("4th ed"), VerificationStatus.VERIFIED)))
    assert r1.model_identity == r2.model_identity
    assert r1.admission_identities != r2.admission_identities
    m1, m2 = r1.to_twocell(), r2.to_twocell()
    assert np.array_equal(m1.N, m2.N) and np.array_equal(m1.E, m2.E)


# (4) a changed display label does not change the physical model digest
def test_A4_display_label_does_not_change_the_model_digest():
    ex = _ex(ISO_STEP, _verified_uni())
    snap = _snapshot(ex, evidence={"admission": ex.admission_identities})
    styled = snap.with_display_hints(colormap="magma", sep=" :: ")
    assert styled.model_digest == snap.model_digest
    assert styled.evidence_digest == snap.evidence_digest


# (5) a downgrade from verified to synthetic cannot silently disappear during conversion
def test_A4_downgrade_to_synthetic_survives_to_the_twocell_and_snapshot():
    exv = _ex(ISO_STEP, _verified_uni())
    exs = _ex(ISO_STEP, _synthetic_uni())
    assert exv.to_twocell().label == "SOURCE_VERIFIED"
    assert exs.to_twocell().label == "SYNTHETIC"                       # the downgrade is carried, not relabelled
    sv = _snapshot(exv, evidence={"admission": exv.admission_identities})
    ss = _snapshot(exs, evidence={"admission": exs.admission_identities})
    assert sv.model_digest == ss.model_digest                          # identical physical state...
    assert sv.evidence_digest != ss.evidence_digest                    # ...distinct admission identity (not lost)


# evil-morty Finding 3: a law's temperature-validity window is authoritative kinetic content -> moves model identity
def test_A4_validity_window_moves_model_identity():
    a = _ex(ISO_STEP, KineticLaw(2.0e-3, 1.0e-3, True, AdmissionLevel.SYNTHETIC, "s^-1", "s^-1",
                                 assumption="x", validity_T_K=(200.0, 300.0)))
    b = _ex(ISO_STEP, KineticLaw(2.0e-3, 1.0e-3, True, AdmissionLevel.SYNTHETIC, "s^-1", "s^-1",
                                 assumption="x", validity_T_K=(1000.0, 2000.0)))
    assert a.model_identity != b.model_identity


# the snapshot's evidence digest is independent of the model digest (the two-digest discipline, end to end)
def test_A4_snapshot_evidence_is_independent_of_model():
    ex = _ex(ISO_STEP, _verified_uni())
    s_a = _snapshot(ex, evidence={"admission": ex.admission_identities, "src": "revA"})
    s_b = _snapshot(ex, evidence={"admission": ex.admission_identities, "src": "revB"})
    assert s_a.model_digest == s_b.model_digest
    assert s_a.evidence_digest != s_b.evidence_digest
