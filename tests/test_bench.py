"""Benchmark decision semantics: conditional accuracy never hides missing coverage."""
from __future__ import annotations

import pytest

from smartchem.bench import Result, Row, evaluate, report, verdict
from smartchem.data import CHEMICAL_ACCURACY_EV, KCAL_PER_EV, bonds
from smartchem.oracle.base import Estimate


def _row(formula: str, predicted: float | None) -> Row:
    return Row(
        formula=formula,
        reference_ev=1.0,
        predicted_ev=predicted,
        seconds=0.0,
        kind="test",
    )


def test_a_perfect_single_prediction_plus_a_refusal_earns_no_accuracy_tier():
    result = Result("selective", [_row("easy", 1.0), _row("hard", None)])
    assert result.mae_ev == 0.0, "the displayed arithmetic mean is explicitly conditional"
    decision = verdict(result.mae_ev, refused=len(result.refused))
    assert "INCOMPLETE COVERAGE" in decision
    assert "CHEMICAL ACCURACY" not in decision


def test_report_labels_the_mean_conditional_and_the_verdict_incomplete(capsys):
    result = Result("selective", [_row("easy", 1.0), _row("hard", None)])
    report([result], frozenset(), split=None)
    output = capsys.readouterr().out
    assert "cond MAE" in output
    assert "INCOMPLETE COVERAGE" in output
    assert "conditional MAE excludes them" in output
    assert "reference uncertainty fields" in output


def test_full_coverage_can_still_earn_a_numeric_tier():
    result = Result("complete", [_row("a", 1.0), _row("b", 1.0)])
    assert not result.refused
    assert "CHEMICAL ACCURACY" in verdict(result.mae_ev, refused=0)


def test_evaluate_passes_the_reference_bond_graph_to_the_oracle():
    class RecordingOracle:
        name = "recording"

        def __init__(self):
            self.molecules = []

        def atomization_energy(self, molecule):
            self.molecules.append(molecule)
            return Estimate(0.0, 0.0, self.name)

        def bond_energy(self, _symbols):  # pragma: no cover - must not be called
            raise AssertionError("benchmark discarded the molecular graph")

    oracle = RecordingOracle()
    result = evaluate(oracle, verbose=False)

    references = bonds()
    assert len(result.rows) == len(oracle.molecules) == len(references)
    for molecule, reference in zip(oracle.molecules, references):
        assert molecule.formula == {
            symbol: reference.atoms.count(symbol) for symbol in set(reference.atoms)
        }
        assert {bond.order for bond in molecule.bonds} == {reference.bond_order}
    assert [row.reference_scale_ev for row in result.rows] == [
        reference.uncertainty_ev for reference in references
    ]


def test_chemical_accuracy_threshold_uses_the_shared_exact_conversion():
    assert CHEMICAL_ACCURACY_EV * KCAL_PER_EV == pytest.approx(1.0)
    assert "CHEMICAL ACCURACY" in verdict(CHEMICAL_ACCURACY_EV - 1e-12)
    assert "CHEMICAL ACCURACY" not in verdict(CHEMICAL_ACCURACY_EV)
