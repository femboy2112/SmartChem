"""POOR-MAN-ETHERIFICATION-RECOGNIZER-01 (R57): the SECOND conservation-locked class the ingenuity reward ships.

The committed probe (:mod:`experiments.poor_man_etherification_recognizer_probe`) is the frozen evidence that a
positive-whitelist DEHYDRATIVE-ETHERIFICATION recognizer (:func:`smartchem.experiment.feasibility._is_intermolecular_etherification`,
registered in :mod:`smartchem.experiment.reaction_type_oracle`) DEMOTES reaction-TYPE fictions off the affordability
frontier -- SOUND (0 false-VOUCH across the production frontier), NON-VACUOUS (dimethyl ether now vouched), and
different-in-kind from escape #7 (its unbounded-ness surfaces as coverage loss, never a false-VOUCH).

These are the fast regression pins over the SAME live behaviour, kept independent of the probe so a refactor cannot
silently drop coverage.  If the "consumer" pin stops firing, the pollution was fixed elsewhere (re-state the win).
If the "soundness" pin stops firing, the oracle started false-VOUCHing a fiction (the catastrophic regression --
STOP).  If an "adversarial" pin stops firing, a conservation-lock clause was weakened -- re-audit it.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.conditions import ConditionEnvelope
from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.step import STEP_SCHEMA, ExperimentStep
from smartchem.experiment.feasibility import (
    _is_intermolecular_etherification, _ether_oxygen_counts, _alcohol_counts,
)
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation
import experiments.poor_man_etherification_recognizer_probe as probe


def _routes(target_smiles, available, reagents=None):
    tgt = parse_smiles(target_smiles)
    av = tuple(probe._resolve(t) for t in available)
    kw = {"available": av, "commodities": ()}
    if reagents is not None:
        kw["reagents"] = tuple(probe._resolve(t) for t in reagents)
    return probe._routes_of(compile_synthesis(tgt, **kw))


def _hand_step(reactant_smis, product_smis, target_smi):
    water = structure_by_name("water").molecule
    reactants = tuple(parse_smiles(s) for s in reactant_smis)
    products = tuple(parse_smiles(s) if s != "water" else water for s in product_smis)
    target = parse_smiles(target_smi)
    tgt = next((p for p in products if dict(p.formula) == dict(target.formula) and p.charge == target.charge), products[0])
    return ExperimentStep(STEP_SCHEMA, target=tgt, reactants=reactants, products=products,
                          reagents=(), envelope=ConditionEnvelope.unknown())


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_consumer_is_served_dimethyl_ether_now_vouched():
    resp = run_compilation(build_recompile_request("dimethyl ether", max_depth=3))
    fr = resp.affordability_frontier
    assert len(fr) > 0
    # at least one frontier route is now free of the reaction-type blocker (the etherification route).  DISPOSITION-01:
    # the fiction rides ``fiction_blockers`` now, so read both channels (else this goes vacuously true).
    assert any(
        not any("unrecognized reaction type" in b
                for b in ((getattr(e.cost_vector, "hard_blockers", ()) or ())
                          + (getattr(e.cost_vector, "fiction_blockers", ()) or ())))
        for e in fr
    )


def test_the_oracle_is_sound_zero_false_vouch_on_the_production_frontier():
    sc = probe.soundness_and_coverage()
    assert sc["total_frontier_routes"] > 0
    assert sc["false_vouch_count"] == 0     # the catastrophic error -- a fiction must NEVER be vouched


def test_the_oracle_is_non_vacuous_dimethyl_ether_is_a_vouched_real():
    sc = probe.soundness_and_coverage()
    assert sc["reals_vouched"] >= 1
    assert sc["dimethyl_ether_vouched"] is True


def test_a_real_elementary_etherification_is_recognized():
    # TAMPER-HARDENING-01: the centre-less census fallback is retired, so a POSITIVE control must carry a real
    # reaction centre (a hand-built centre-less step now fail-closes to demoted -- covered below).
    step = probe._derive_step("COC", ["CO", "CO"])   # 2 methanol -> dimethyl ether + water, centre-CARRYING
    assert step is not None and step.reaction_center is not None
    klass = recognize_reaction_type(step)
    assert klass is not None and "etherification" in klass
    assert _is_intermolecular_etherification(step) is True


def test_a_centreless_etherification_now_fails_closed():
    # TAMPER-HARDENING-01: a centre-less etherification step (e.g. a serialized replay whose centre was nulled) is
    # DEMOTED, not census-vouched -- the fail-closed polarity that shuts the fiction tamper channel.
    step = _hand_step(["CO", "CO"], ["COC", "water"], "COC")
    assert step.reaction_center is None
    assert recognize_reaction_type(step) is None


def test_the_peroxide_coupling_fake_is_demoted_no_alcohol_consumed():
    step = _hand_step(["CCOO", "CC"], ["CCOCC", "water"], "CCOCC")   # EtOOH + ethane -> Et2O + water
    assert _is_intermolecular_etherification(step) is False
    assert recognize_reaction_type(step) is None


def test_the_aryl_ether_anisole_fake_is_demoted_not_a_dialkyl_ether():
    step = _hand_step(["c1ccc(O)cc1", "CO"], ["COc1ccccc1", "water"], "COc1ccccc1")   # phenol + methanol -> anisole
    assert _is_intermolecular_etherification(step) is False
    assert recognize_reaction_type(step) is None


def test_the_bundled_glycol_dme_fake_is_demoted_reuses_a_reactant_ether():
    # dalembert's demonstrated non-local kill: the whole-molecule NET census alone would vouch it, but the
    # reactant-ether clause demotes it -- even at k >= 2 (where the bundled step becomes engine-reachable).
    step = _hand_step(["OCCO", "COC"], ["COCCOC", "water"], "COCCOC")   # glycol + DME -> dimethoxyethane + water
    assert _is_intermolecular_etherification(step) is False
    assert recognize_reaction_type(step) is None


def test_the_acyl_recognizer_and_cc_fictions_are_unregressed():
    unreg = probe.acyl_unregressed()
    assert unreg["r56_probe_validates"] is True
    assert unreg["isopentyl_fictions_all_demoted"] is True


def test_escape7_is_still_shut_the_amination_fake_stays_demoted():
    # R60 re-framing: the ETHERIFICATION recognizer never vouched N-methylation, and caffeine is now vouched by
    # R60's class-specific recognizer.  The real escape-#7 invariant -- the aromatic-amination FAKE stays demoted.
    caff = probe.caffeine_now_vouched_fake_demoted()
    assert caff["caffeine_has_vouched_route"] is True
    assert caff["amination_fake_demoted"] is True


def test_the_demoter_is_fail_closed_and_disposition_honest():
    fc = probe.fail_closed_and_disposition()
    assert fc["no_crash_on_raising_recognizer"] is True
    assert fc["fake_still_demoted"] is True
    assert fc["disposition_honest"] is True


def test_a_zero_step_route_is_vacuously_vouched():
    assert route_reaction_type_blockers(SimpleNamespace(steps=())) == ()


def test_the_census_distinguishes_dialkyl_ether_from_aryl_ether_and_ester():
    assert _ether_oxygen_counts(parse_smiles("COC")) == 1        # dimethyl ether
    assert _ether_oxygen_counts(parse_smiles("COc1ccccc1")) == 0  # anisole (aromatic neighbour -> not dialkyl)
    assert _ether_oxygen_counts(parse_smiles("CCOC(C)=O")) == 0   # ethyl acetate (ester -O-, carbonyl neighbour)
    assert _alcohol_counts(parse_smiles("CO")) == 1              # methanol
    assert _alcohol_counts(parse_smiles("c1ccc(O)cc1")) == 0      # phenol (aromatic hydroxyl -> not an alcohol)
    assert _alcohol_counts(parse_smiles("CC(=O)O")) == 0          # acetic acid (carboxyl -O-H -> not an alcohol)
