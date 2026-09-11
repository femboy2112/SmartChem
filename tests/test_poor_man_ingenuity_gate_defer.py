"""POOR-MAN-INGENUITY-GATE-DEFER-01 (R49, PR-2): the verified defer of the feasibility-layer ingenuity gate.

The committed probe (:mod:`experiments.poor_man_ingenuity_gate_defer_probe`) is the comprehensive evidence that
a topological reaction-class recognizer cannot soundly gate the poor-man ingenuity reward at the feasibility
layer (it VOUCHES catalysis-required reactions -- topology does not encode kitchen-reachability).  These are the
fast regression pins over the SAME production predicate, kept independent of the probe so a probe refactor cannot
silently drop coverage.  R48's guard -- the sound part -- stays untouched, which these also confirm.
"""
from __future__ import annotations

from experiments import poor_man_ingenuity_gate_defer_probe as probe

from smartchem.experiment.feasibility import _is_intermolecular_acyl_condensation, feasibility_of_step


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_kill_topology_vouches_catalysis_required_reactions():
    # THE fatal kill: a correctly-keyed topological VOUCHED predicate fires on reactions that only proceed under
    # transition-metal catalysis -- so it cannot gate a "poor-man-reachable" reward (topology != reachability).
    kill = probe.kill_topology_not_reachable()
    assert kill["_vouched_but_needs_catalysis"] == [
        "aniline_ethanol_n_alkylation", "caffeine_n_methylation_by_methanol",
    ]
    # the design's OWN cited non-vacuity example is itself a catalysis-required reaction it would wrongly reward
    assert kill["caffeine_n_methylation_by_methanol"]["topological_vouched"] is True


def test_r48_guard_stays_sound_and_untouched():
    # the SOUND part is unchanged: the acid class fires, the alcohol-donor cases stay silent (a negative guard).
    caffeine = probe._step(["theophylline", "methanol"], ["caffeine", "O"])
    fischer = probe._step(["acetic acid", "4-aminophenol"], ["paracetamol", "O"])
    assert _is_intermolecular_acyl_condensation(fischer) is True
    assert _is_intermolecular_acyl_condensation(caffeine) is False


def test_anhydride_leak_is_harmless_not_a_fabricated_favorable():
    # 2 acetic acid -> acetic anhydride + water is a free-acid condensation R48 does not guard, but the estimator
    # already returns UNKNOWN (not a fabricated FAVORABLE) -- so there is no lie to catch and R48's conjunction is
    # right to leave alone (verified so the completeness gap is not chased as a bug).
    anhydride = probe._step(["CC(=O)O", "CC(=O)O"], ["CC(=O)OC(=O)C", "O"])
    assert feasibility_of_step(anhydride).direction.value != "FAVORABLE"
    assert _is_intermolecular_acyl_condensation(anhydride) is False
