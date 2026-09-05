"""A formula-only inventory match is insufficient to certify reagent identity.

The conserving isomerization steps are formal audit fixtures, not experimental
reaction claims. Fits below concern only the explicitly declared inventory.
"""
import pytest

from smartchem.experiment.drafter import ConstraintBox, RouteFitStatus, fit_route
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.smiles import parse_smiles


def _route(source_smiles, target_smiles):
    source, target = map(parse_smiles, (source_smiles, target_smiles))
    return ExperimentRoute.of(ExperimentStep.assembling(target, (source,), (target,)))


@pytest.mark.parametrize("source,target,formula", [
    ("CC(=O)C", "CCC=O", "C3H6O"),  # only acetone is registered for this formula
    ("CCC=O", "CC(=O)C", "C3H6O"),  # propanal is absent from the registry
    ("CCCC", "CC(C)C", "C4H10"),     # neither isomer is registered
])
def test_formula_only_inventory_keeps_identity_unknown(source, target, formula):
    fit = fit_route(_route(source, target), ConstraintBox(available_reagents=frozenset({formula})))
    assert fit.status is RouteFitStatus.UNKNOWN
    assert not fit.exclusions
    assert any("matches only formula" in gap and "structural identity is unresolved" in gap for gap in fit.gaps)


@pytest.mark.parametrize("inventory", [
    frozenset({"acetone"}),
    frozenset({"propan-2-one"}),
    frozenset({"C3H6O", "acetone"}),
])
def test_exact_registered_name_or_alias_resolves_the_inventory_match(inventory):
    fit = fit_route(_route("CC(=O)C", "CCC=O"), ConstraintBox(available_reagents=inventory))
    assert fit.status is RouteFitStatus.FITS
    assert not fit.gaps and not fit.exclusions


def test_name_of_wrong_same_formula_isomer_cannot_supply_reactant():
    fit = fit_route(
        _route("CCC=O", "CC(=O)C"), ConstraintBox(available_reagents=frozenset({"acetone"})),
    )
    assert fit.status is RouteFitStatus.EXCLUDED
    assert any("not in the available-reagent inventory" in reason for reason in fit.exclusions)


def test_absent_inventory_still_excludes():
    fit = fit_route(_route("CC(=O)C", "CCC=O"), ConstraintBox(available_reagents=frozenset()))
    assert fit.status is RouteFitStatus.EXCLUDED
