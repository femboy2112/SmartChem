"""Real-repository integration gates; explicitly skipped in a sparse workspace."""
from importlib.util import find_spec

import pytest

if find_spec("smartchem.category") is None:
    pytest.skip("full SmartChem checkout required; no stand-in modules", allow_module_level=True)
# A present but broken original module must FAIL import/collection, not skip.
from smartchem.smiles import parse_smiles
from smartchem.structure_descent import capped_scissions, ScissionError
from smartchem.experiment.step import ExperimentStep
from smartchem.transform_provider import CappedScissionProvider, TransformProviderRegistry, DEFAULT_TRANSFORM_REGISTRY
from smartchem.rule_calculus import verify
from smartchem.rule_calculus_bridge import audit_scission, AuditedCappedScissionProvider


@pytest.mark.parametrize("smiles,expected", [
    ("CC(=O)OC", "acyl condensation"),
    ("CCOCC", "etherification"),
    ("CCN", "N-alkylation"),
])
def test_existing_three_classes_replay_and_keep_the_same_open_projection(smiles, expected):
    molecule, water = parse_smiles(smiles), parse_smiles("O")
    transforms, complete = capped_scissions(molecule, (water,), budget=50000)
    assert complete and transforms
    classes = []
    for t in transforms:
        audit = audit_scission(t)
        assert verify(audit.decomposition) and verify(audit.synthesis)
        assert audit.open().close() == ExperimentStep.from_transform(t).open().close()
        assert audit.readiness == "FORMAL_CANDIDATE"
        classes.append(audit.recognized_class or "")
    assert any(expected in name for name in classes)


@pytest.mark.parametrize("smiles", ["CC(=O)OC", "CCOCC", "CCN"])
def test_opt_in_provider_reaches_the_existing_registry_without_changing_outputs(smiles):
    molecule, water = parse_smiles(smiles), parse_smiles("O")
    baseline, base_complete = CappedScissionProvider().enumerate_transforms(molecule, (water,), budget=50000)
    registry = TransformProviderRegistry((AuditedCappedScissionProvider(),))
    tagged, complete = registry.enumerate(molecule, (water,), budget=50000)
    assert {t.digest for t in baseline} == {t.transform.digest for t in tagged}
    assert complete == base_complete
    assert registry.digest != DEFAULT_TRANSFORM_REGISTRY.digest
    assert DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",)


def test_audited_partial_provider_never_fabricates_completeness():
    molecule, water = parse_smiles("CC(=O)OC"), parse_smiles("O")
    _, complete = AuditedCappedScissionProvider().enumerate_transforms(molecule, (water,), budget=1)
    assert not complete


def test_unknown_state_is_refused_not_erased():
    from dataclasses import replace
    molecule = replace(parse_smiles("CC(=O)OC"), state="UNTRANSPORTED")
    with pytest.raises(ScissionError):
        AuditedCappedScissionProvider().enumerate_transforms(molecule, (parse_smiles("O"),), budget=1)


def test_charged_input_declines_without_crashing_a_mixed_registry():
    from smartchem.category import Molecule
    transforms, complete = AuditedCappedScissionProvider().enumerate_transforms(
        Molecule.atom("N", charge=1), (), budget=1
    )
    assert transforms == () and complete
