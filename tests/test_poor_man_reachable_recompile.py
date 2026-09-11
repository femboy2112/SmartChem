"""POOR-MAN-REACHABLE-RECOMPILE-01 (R48, PR-1): reachability + the aqueous free-acid dehydrative-acylation
DOMAIN GUARD.

The committed probe (:mod:`experiments.poor_man_reachable_recompile_probe`) is the comprehensive evidence --
18 recognizer cases, the north-star honesty flip, the reachability flip, and the anti-overfit generalization
checks, all against the REAL production predicate.  These are the fast, readable regression pins over the same
production functions, kept independent of the probe so a probe refactor cannot silently drop coverage.
"""
from __future__ import annotations

from experiments import poor_man_reachable_recompile_probe as probe

from smartchem.conditions import ConditionEnvelope
from smartchem.experiment.equilibrium import EquilibriumExtent, equilibrium_of_step
from smartchem.experiment.feasibility import (
    FeasibilityDirection,
    _acyl_group_counts,
    _is_intermolecular_acyl_condensation,
    feasibility_of_step,
)
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.smiles import parse_smiles as M
from smartchem.structure import structure_by_name


def _named(name):
    return structure_by_name(name).canonical_molecule


def _step(target, reactants, products):
    return ExperimentStep(
        STEP_SCHEMA, target=target, reactants=tuple(reactants), products=tuple(products),
        reagents=(), envelope=ConditionEnvelope.unknown(),
    )


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_guard_fires_on_the_paracetamol_fischer_route_both_layers_unknown():
    # THE flagship lie: aqueous acetic acid + 4-aminophenol reads FAVORABLE (ΔG -98) / ESSENTIALLY_COMPLETE
    # today, but gives the ammonium salt, not the amide.  The guard fails BOTH layers closed to UNKNOWN.
    step = _step(_named("paracetamol"), (_named("acetic acid"), _named("4-aminophenol")),
                 (_named("paracetamol"), _named("water")))
    assert _is_intermolecular_acyl_condensation(step) is True
    f = feasibility_of_step(step)
    assert f.direction is FeasibilityDirection.UNKNOWN and f.delta_g_kj is None
    assert "domain guard" in f.reason
    assert equilibrium_of_step(step).extent is EquilibriumExtent.UNKNOWN   # equilibrium inherits the guard


def test_guard_is_silent_on_the_legit_anhydride_acylation():
    # the acetic-anhydride route to paracetamol is the REAL synthesis (byproduct = acetic acid, NOT water, and
    # the donor is not a free acid); the guard must NOT fire (a 2nd product excludes the dehydrative shape).
    step = _step(_named("paracetamol"), (M("CC(=O)OC(=O)C"), _named("4-aminophenol")),
                 (_named("paracetamol"), _named("acetic acid")))
    assert _is_intermolecular_acyl_condensation(step) is False


def test_guard_is_target_independent():
    # a free-acid amidation built from molecules UNRELATED to the north stars fires just the same -- the
    # predicate is pure graph surgery, never a name lookup (dalembert: target-independence SURVIVED).
    step = _step(M("CCC(=O)NCC"), (M("CCC(=O)O"), M("CCN")), (M("CCC(=O)NCC"), M("O")))
    assert _is_intermolecular_acyl_condensation(step) is True


def test_guard_is_silent_on_intramolecular_lactonization():
    # evil-morty Finding 1: 4-hydroxybutanoic acid -> gamma-butyrolactone + water is INTRAMOLECULAR ring
    # closure (1 non-water reactant) -- entropically favored, the ΔG IS competent, so the guard must NOT fire.
    step = _step(M("O=C1CCCO1"), (M("OCCCC(=O)O"),), (M("O=C1CCCO1"), M("O")))
    assert _is_intermolecular_acyl_condensation(step) is False


def test_guard_is_silent_on_a_bundled_multispecies_step():
    # dalembert KILL 3: a real amidation lie bundled with a transesterification (3 non-water reactants) fails
    # OPEN -- the shape restriction refuses to let a composite step's independent sub-reactions cancel the count.
    step = _step(M("CC(=O)NC"), (M("CC(=O)O"), M("CN"), M("CCOC=O")),
                 (M("CC(=O)NC"), M("OC=O"), M("CCO")))
    assert _is_intermolecular_acyl_condensation(step) is False


def test_caffeine_route_is_honest_unknown_via_the_data_gap_not_the_guard():
    # caffeine <- theophylline + methanol is an N-methylation, NOT a free-acid acylation: the guard does NOT
    # fire, and the route is honestly UNKNOWN via the missing sourced thermo instead.
    step = _step(_named("caffeine"), (_named("theophylline"), _named("methanol")),
                 (_named("caffeine"), _named("water")))
    assert _is_intermolecular_acyl_condensation(step) is False
    f = feasibility_of_step(step)
    assert f.direction is FeasibilityDirection.UNKNOWN and f.missing   # a DATA gap, not the domain guard


def test_acid_detector_is_representation_robust():
    # dalembert KILL 1 + the salt-sink point: a carboxyl O with no heavy neighbour is a free acid whether its H
    # is explicit or implicit, and the carboxylate ANION is in-scope too; an anhydride/peroxy-acid is neither.
    assert _acyl_group_counts(M("CC(=O)O"))[0] >= 1           # acetic acid
    assert _acyl_group_counts(M("CC(=O)[O-]"))[0] >= 1        # acetate anion (the salt sink)
    assert _acyl_group_counts(M("CC(=O)OC(=O)C")) == (0, 0, 0, 0)   # anhydride: no free acid, no ester
    assert _acyl_group_counts(M("CC(=O)OO"))[0] == 0         # peroxyacetic acid is not a free carboxylic acid
