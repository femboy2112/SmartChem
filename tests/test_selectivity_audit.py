"""Sparse registry coverage cannot certify that competing structures are absent.

The isomerization steps below are conservation-valid audit fixtures, not claims
that these reactions proceed. Exact sourced controls exercise the existing path.
"""
import pytest

from smartchem.experiment.bucket import Bucket
from smartchem.experiment.selectivity import (
    DEFAULT_SELECTIVITY, SelectivityStatus, selectivity_of_step,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles


@pytest.mark.parametrize("source_smiles,target_smiles", [
    ("CCC=O", "CC(=O)C"),       # propanal / acetone: only acetone is registered
    ("CC(C)C", "CCCC"),         # isobutane / butane: neither is registered
])
def test_unregistered_competing_structure_cannot_be_a_nonapplicability_pass(
    source_smiles, target_smiles,
):
    source, target = map(parse_smiles, (source_smiles, target_smiles))
    assert source.formula == target.formula
    assert source.canonical() != target.canonical()
    step = ExperimentStep.assembling(target, (source,), (target,))
    result = selectivity_of_step(step, table=DEFAULT_SELECTIVITY)
    assert result.status is SelectivityStatus.UNKNOWN
    assert result.finding.bucket is Bucket.UNKNOWN
    assert "registry completeness is not established" in result.finding.provenance


def test_exact_sourced_selectivity_survives_sparse_formula_index(monkeypatch):
    # Mutate only the optional formula index. Exact structure/source checks must
    # still carry the accepted control; registry cardinality is not its evidence.
    monkeypatch.setattr("smartchem.experiment.selectivity.known_compounds", lambda formula: ())
    target, precursor, reagent, byproduct = map(parse_smiles, (
        "CC(=O)Nc1ccc(O)cc1", "Nc1ccc(O)cc1", "CC(=O)OC(=O)C", "CC(=O)O",
    ))
    step = ExperimentStep.assembling(target, (precursor, reagent), (target, byproduct))
    result = selectivity_of_step(step, table=DEFAULT_SELECTIVITY)
    assert result.status is SelectivityStatus.FAVORED
    assert result.finding.bucket is Bucket.KNOWN_SOURCED
