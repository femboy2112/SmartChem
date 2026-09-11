"""DISCONN-SEL-01: the ranker prefers a chemically-sensible disconnection, DERIVED from bond energies (not hard-coded).

Pins the R47 fix for the R45 over-generation finding: among routes that tie on every SOURCED tier, the one whose
bond-additivity net ΔH is favorable floats above the endergonic one -- so the sound N-methylation now outranks the
dubious C-C homologation to caffeine.  The signal is DERIVED by Hess's law from mean bond enthalpies (physical
constants), strictly subordinate to sourced data, and neutral on ignorance.
"""
from __future__ import annotations

import pytest

from experiments import ranker_disconnection_selectivity_probe as probe
from smartchem.experiment.bond_enthalpy import (
    CALIBRATION,
    DERIVED_BORDERLINE_KJ,
    MEAN_BOND_ENTHALPY_KJ,
    disconnection_favorability_rank,
    reaction_delta_h_kj,
    route_delta_h_kj,
)
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.drafter import ConstraintBox, RouteFitStatus, _score_tuple
from smartchem.smiles import parse_smiles as M


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


@pytest.mark.parametrize("name,rs,ps,lit", CALIBRATION)
def test_instrument_recovers_known_reaction_sign(name, rs, ps, lit):
    # the instrument rule: bond additivity must recover the SIGN of every known-sign reaction before it is trusted.
    dh = reaction_delta_h_kj(tuple(M(s) for s in rs), tuple(M(s) for s in ps))
    assert dh is not None, name
    assert (dh < 0) == (lit < 0), (name, dh, lit)


def test_sound_methylation_now_outranks_the_dubious_homologation():
    # THE fix: the sound N-methylation ranks ABOVE the C-C homologation to caffeine (previously the reverse).
    caf, theo = M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C"), M("N1C=NC2=C1C(=O)N(C)C(=O)N2C")
    compiled = compile_synthesis(caf, reagents=(M("CO"), M("O")), available=(theo, M("CCO")),
                                 max_depth=2, max_routes=12, cut_budget=40000, commodities=(), box=ConstraintBox())
    eqs = [probe._route_eq(r.route) for r in compiled.ranked]
    assert eqs.index(probe._SOUND) < eqs.index(probe._DUBIOUS), eqs


def test_derived_delta_h_signs_and_reverse_flips():
    caf, theo, meoh, water, etoh = (M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C"), M("N1C=NC2=C1C(=O)N(C)C(=O)N2C"),
                                    M("CO"), M("O"), M("CCO"))
    sound = reaction_delta_h_kj((theo, meoh), (caf, water))
    dubious = reaction_delta_h_kj((etoh, theo), (caf, meoh))
    assert sound < 0 < dubious, (sound, dubious)
    # a derivation, not a static per-reaction label: the reverse reaction flips the sign exactly.
    assert reaction_delta_h_kj((caf, water), (theo, meoh)) == -sound


def test_neutral_on_ignorance_untabulated_bond_is_none():
    # a net bond change touching an untabulated bond type (C-P) yields None -> the BORDERLINE middle, never fabricated.
    assert ("C", "P", 1) not in MEAN_BOND_ENTHALPY_KJ
    assert reaction_delta_h_kj((M("P"), M("C=C")), (M("CCP"),)) is None


def test_favorability_rank_is_neutral_on_ignorance():
    class _Step:
        def __init__(self, r, p):
            self.reactants, self.products = r, p

    class _Route:
        def __init__(self, steps):
            self.steps = steps

    untab = _Route([_Step((M("P"), M("C=C")), (M("CCP"),))])
    assert disconnection_favorability_rank(untab) == 1        # None -> BORDERLINE, never 0 or 2
    assert route_delta_h_kj(untab) is None


def test_derived_tier_is_strictly_subordinate_to_every_sourced_tier():
    # DEAD-LAST: a route sourced-FAVORED but derived-UNFAVORABLE must beat one sourced-DISFAVORED but derived-FAVORABLE.
    favored_sourced = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "FAVORED", "UNKNOWN", "UNKNOWN", "UNKNOWN",
                                   0, 0, derived_rank=2)
    favored_derived = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "DISFAVORED", "UNKNOWN", "UNKNOWN", "UNKNOWN",
                                   0, 0, derived_rank=0)
    assert favored_sourced < favored_derived


def test_derived_tier_is_the_last_element_and_defaults_neutral():
    # the tier is DEAD-LAST (position 11); its default is the neutral BORDERLINE (1), used when a scorer is called
    # directly without the caller coordinate.  BOTH rank_routes and rank_dags feed it identically (a caller-computed
    # coordinate threaded through _physics_ranked_order), so the two scorers stay pure extractors and cannot diverge.
    t = _score_tuple(RouteFitStatus.FITS, "COMPOSABLE", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", 0, 0)
    assert t[-1] == 1 and len(t) == 11


def test_dead_band_is_above_in_domain_error_and_below_the_caffeine_signal():
    # honesty (evil-morty R47): the dead-band is NOT the (much larger, magnitude) accuracy -- it is a conservative
    # floor set above the largest IN-DOMAIN residual (14 kJ, CH4+Cl2) and below the caffeine signal (19 kJ), so it is
    # not a magic constant tuned to caffeine (any band in (14, 19) works identically) and not the combustion-excluded
    # RMS overclaim.  All signs (incl combustion) are still recovered.
    c = probe.calibration()
    assert c["all_signs_recovered"] is True
    assert c["max_in_domain_residual_kj"] < DERIVED_BORDERLINE_KJ < 19
    assert c["max_residual_kj"] >= 100     # combustion's magnitude error is large and honestly reported


@pytest.mark.parametrize("reactants,products", [
    (("C1CC1",), ("CC=C",)),                        # cyclopropane -> propene: ring strain release (est +80, true -33)
    (("C1=CCCC=C1",), ("c1ccccc1", "[H][H]")),      # 1,3-cyclohexadiene -> benzene + H2: aromatization (est +125)
    (("c1ccccc1", "[H][H]"), ("C1=CCCC=C1",)),      # the reverse: de-aromatization
])
def test_domain_guard_declines_ring_strain_and_aromatization(reactants, products):
    # evil-morty / dalembert R47: bond additivity inverts the sign on non-local (ring/aromatic) stabilization; the
    # endocyclic-bond-type guard fails closed there rather than confidently mis-tiering a route.
    assert reaction_delta_h_kj(tuple(M(s) for s in reactants), tuple(M(s) for s in products)) is None


def test_domain_guard_keeps_ring_preserving_reactions():
    # the caffeine N-methylation preserves the purine ring (endocyclic multiset identical on both sides), so it is
    # IN DOMAIN and its ΔH stands -- the guard declines the unsound cases WITHOUT killing the reaction it earns.
    caf, theo, meoh, water = (M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C"), M("N1C=NC2=C1C(=O)N(C)C(=O)N2C"), M("CO"), M("O"))
    assert reaction_delta_h_kj((theo, meoh), (caf, water)) == -19.0


def test_dag_twin_feeds_the_derived_tier_and_discriminates():
    # mr-president fold: pin the DAG twin's derived tier as tightly as the linear one.  rank_dags feeds
    # disconnection_favorability_rank(dag) identically; the function reads a SynthesisDAG's .steps (intermediates
    # cancel), so a sound-methylation DAG grades FAVORABLE and a C-C-homologation DAG grades UNFAVORABLE.
    from smartchem.conditions import ConditionEnvelope, Interval
    from smartchem.contracts import EvidenceStatus
    from smartchem.experiment.dag import SynthesisDAG
    from smartchem.experiment.step import ExperimentStep
    caf, theo, meoh, water, etoh = (M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C"), M("N1C=NC2=C1C(=O)N(C)C(=O)N2C"),
                                    M("CO"), M("O"), M("CCO"))
    env = ConditionEnvelope(temperature=Interval(300, 300, "K"), status=EvidenceStatus.EXPERIMENTAL,
                            provenance="synthetic test; no experimental claim")
    sound_dag = SynthesisDAG.of(ExperimentStep.assembling(caf, (theo, meoh), (caf, water), envelope=env))
    homolog_dag = SynthesisDAG.of(ExperimentStep.assembling(caf, (etoh, theo), (caf, meoh), envelope=env))
    assert disconnection_favorability_rank(sound_dag) == 0        # FAVORABLE (ΔH = -19 kJ), read off the DAG's steps
    assert disconnection_favorability_rank(homolog_dag) == 2      # UNFAVORABLE (ΔH = +19 kJ)


def test_caffeine_derived_ranks_are_favorable_and_unfavorable():
    caf, theo = M("CN1C=NC2=C1C(=O)N(C)C(=O)N2C"), M("N1C=NC2=C1C(=O)N(C)C(=O)N2C")
    compiled = compile_synthesis(caf, reagents=(M("CO"), M("O")), available=(theo, M("CCO")),
                                 max_depth=2, max_routes=12, cut_budget=40000, commodities=(), box=ConstraintBox())
    # read the derived tier directly (rank_routes applies it as a caller coordinate; _route_score defaults it neutral)
    by_eq = {probe._route_eq(r.route): disconnection_favorability_rank(r.route) for r in compiled.ranked}
    assert by_eq[probe._SOUND] == 0        # FAVORABLE
    assert by_eq[probe._DUBIOUS] == 2      # UNFAVORABLE
