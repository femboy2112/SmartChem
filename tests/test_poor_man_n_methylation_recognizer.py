"""POOR-MAN-N-METHYLATION-RECOGNIZER-01 (R60): the THIRD conservation-locked class the ingenuity reward ships.

The committed probe (:mod:`experiments.poor_man_n_methylation_recognizer_probe`) is the frozen evidence that a
positive-whitelist, CLASS-SPECIFIC N-methylation recognizer (:func:`smartchem.experiment.reaction_type_oracle._n_methylation`)
recovers the R45 caffeine genericity win the honest way -- SOUND (0 false-VOUCH across the production frontier AND
on an adversarial k=2 bundled sweep), NON-VACUOUS (caffeine and methylamine now vouched), and different-in-kind
from escape #7 (the general N-C recognizer collides; this one does not, because the census locks the
byte-identical reaction centre the span alone cannot separate).

These are the fast regression pins over the SAME live behaviour, kept independent of the probe so a refactor
cannot silently drop coverage.  If the "consumer" pin stops firing, the caffeine win regressed.  If a "soundness"
pin stops firing, the oracle started false-VOUCHing a fiction (the catastrophic regression -- STOP).  If the
byte-identical-centre pin stops firing, the census clause that locks the collision was weakened -- re-audit it.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.structure_descent import capped_scissions
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.feasibility import _methanol_specific_alcohol_count, _n_methyl_amine_count
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation
import experiments.poor_man_n_methylation_recognizer_probe as probe

# R63 SUPERSESSION: the N-methylation recognizer was replaced by a general N-alkylation recognizer that subsumes it
# (methanol is an alkyl alcohol; a methyl bond is an sp3 C-N bond).  These pins remain valid as the METHYL SUB-CASE
# anchor -- caffeine/methylamine still lock via the methanol-specific census, now vouched under the "N-alkylation"
# label.  The match token tracks the live label.
_NM = "N-alkylation"


def _derive_step(product_smiles, want_products):
    """The centre-carrying synthesis step whose k=1 decomposition splits ``product_smiles`` (+ water) into
    exactly ``want_products`` -- carries a real :class:`ReactionCenter` built ``from_transform``."""
    r = parse_smiles(product_smiles)
    want = sorted(parse_smiles(s).canonical().__repr__() for s in want_products)
    for cs in capped_scissions(r, (parse_smiles("O"),), max_reactant_cuts=1)[0]:
        if sorted(p.canonical().__repr__() for p in cs.products) == want:
            return ExperimentStep.from_transform(cs)
    return None


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_byte_identical_centre_collision_is_split_by_the_census():
    # THE load-bearing proof: real caffeine N-methylation and the FAKE aryl amination carry a BYTE-IDENTICAL
    # reaction centre, so the R58 span check passes both; only the census separates them.
    caffeine = compile_synthesis(structure_by_name("caffeine").molecule, max_depth=2)
    caff_steps = [st for f in caffeine.ranked for st in f.route.steps if recognize_reaction_type(st) is not None
                  and _NM in (recognize_reaction_type(st) or "")]
    assert caff_steps, "the caffeine N-methylation step is no longer derived/recognized"
    caff_center = caff_steps[0].reaction_center
    fake = _derive_step("Nc1ccccc1", ["c1ccc(O)cc1", "N"])   # phenol + ammonia -> aniline + water
    assert fake is not None and fake.reaction_center is not None
    # byte-identical centres, both passing the span-local elementary-condensation check
    assert caff_center.formed == fake.reaction_center.formed
    assert caff_center.broken == fake.reaction_center.broken
    assert caff_center.n_components == fake.reaction_center.n_components
    assert caff_center.is_elementary_condensation(("N",)) is True
    assert fake.reaction_center.is_elementary_condensation(("N",)) is True
    # yet the census splits them: caffeine VOUCHED, the fake UNRECOGNIZED
    assert _NM in (recognize_reaction_type(caff_steps[0]) or "")
    assert recognize_reaction_type(fake) is None


def test_a_real_n_methylation_is_positively_recognized():
    pc = probe.positive_control()
    # POST-GATE-FIX: a VOUCH requires a readable reaction centre, so the positive controls must carry one.
    assert pc["n_methylaniline_carries_centre"] is True
    assert pc["methylamine_carries_centre"] is True
    assert pc["n_methylaniline_recognized"] is True
    assert pc["methylamine_recognized"] is True


def test_the_centre_absent_homologation_fails_closed():
    # THE GATE FINDING: N-methylformamide + methanol -> CNCC=O + water is NOT a methylation -- methanol's carbon
    # inserts as a CH2 and the carbonyl migrates off the N, unmasking the pre-existing methyl (whole-set-count
    # non-locality).  With no readable centre the census cannot see it, so the recognizer must FAIL CLOSED.
    from smartchem.conditions import ConditionEnvelope
    from smartchem.experiment.step import STEP_SCHEMA
    water = structure_by_name("water").molecule
    step = ExperimentStep(STEP_SCHEMA, target=parse_smiles("CNCC=O"),
                          reactants=(parse_smiles("CNC=O"), parse_smiles("CO")),
                          products=(parse_smiles("CNCC=O"), water),
                          reagents=(), envelope=ConditionEnvelope.unknown())
    assert step.reaction_center is None
    assert recognize_reaction_type(step) is None                       # demoted, not vouched
    assert route_reaction_type_blockers(SimpleNamespace(steps=(step,)))  # route carries the blocker


def test_the_aryl_amination_fake_is_demoted():
    # B (done-bar): phenol + ammonia -> aniline + water must NOT be vouched as N-methylation.
    adv = probe.adversarial_must_demote()["aryl_amination_aniline"]
    assert adv["not_vouched_as_n_methylation"] is True
    assert adv["recognized_class"] is None


def test_centre_less_general_alkylation_fails_closed_and_o_alkylation_is_not_n():
    # R63 SUPERSESSION: general N-alkylation by a longer alcohol IS now admitted (see the R63 probe) -- but only for
    # a CENTRE-CARRYING step.  This hand-built (centre-LESS) ethanol case still demotes, because a VOUCH requires a
    # readable reaction centre (TAMPER-HARDENING-01), not because ethanol is forbidden.
    adv = probe.adversarial_must_demote()["general_n_ethylation"]
    assert adv["not_vouched_as_n_methylation"] is True
    # and O-alkylation to anisole is genuinely a different class (O, not N) -- must stay demoted regardless.
    assert probe.adversarial_must_demote()["o_methylation_anisole"]["not_vouched_as_n_methylation"] is True


def test_existing_acyl_and_ether_recognizers_unbroken():
    # C (done-bar): the acyl and etherification classes still VOUCH their own reactions.
    ups = probe.upstream_probes()
    assert ups["acyl_class_recognized"] is True
    assert ups["ether_class_recognized"] is True
    assert ups["r56_probe_frozen"] and ups["r57_probe_frozen"] and ups["r58_probe_frozen"]


def test_the_consumer_is_served_caffeine_now_vouched():
    resp = run_compilation(build_recompile_request("caffeine", max_depth=3))
    fr = resp.affordability_frontier
    assert len(fr) > 0
    # at least one frontier route is now free of the reaction-type blocker (the N-methylation route)
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
    assert sc["caffeine_vouched"] is True   # non-vacuity: the R45 win recovered


def test_the_adversarial_k2_bundled_sweep_has_zero_false_vouch():
    k2 = probe.k2_adversarial()
    assert k2["k2_census_vouched"] > 0          # the sweep is non-vacuous
    assert k2["k2_false_vouch_count"] == 0      # no k=2 bundle is false-vouched as N-methylation


def test_the_census_unit_separates_methanol_and_the_n_methyl_amine():
    assert _methanol_specific_alcohol_count(parse_smiles("CO")) == 1        # methanol
    assert _methanol_specific_alcohol_count(parse_smiles("CCO")) == 0       # ethanol (carbinol C has a 2nd neighbour)
    assert _methanol_specific_alcohol_count(parse_smiles("c1ccc(O)cc1")) == 0  # phenol (aromatic carbon)
    assert _n_methyl_amine_count(parse_smiles("CN")) == 1                   # methylamine
    assert _n_methyl_amine_count(parse_smiles("Nc1ccccc1")) == 0            # aniline (aryl N, unmethylated)
    assert _n_methyl_amine_count(parse_smiles("CC(=O)NC")) == 0             # N-methyl acetamide (carbonyl-adjacent)
    assert _n_methyl_amine_count(structure_by_name("caffeine").molecule) == 1  # only N7 (N1/N3 carbonyl-flanked)


def test_a_zero_step_route_is_vacuously_vouched():
    assert route_reaction_type_blockers(SimpleNamespace(steps=())) == ()


def test_the_demoter_is_fail_closed_and_disposition_honest():
    fc = probe.fail_closed_and_disposition()
    assert fc["no_crash_on_raising_recognizer"] is True
    assert fc["fake_still_demoted"] is True
    assert fc["disposition_honest"] is True
