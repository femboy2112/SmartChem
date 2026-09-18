"""POOR-MAN-N-ALKYLATION-RECOGNIZER-01 (R63): the FOURTH conservation-locked class, generalising R60 N-methylation
to dehydrative N-alkylation by any ALKYL alcohol onto ANY non-carbonyl N nucleophile.

The committed probe (:mod:`experiments.poor_man_n_alkylation_recognizer_probe`) is the frozen evidence that the
general recognizer (:func:`smartchem.experiment.reaction_type_oracle._n_alkylation`) is SOUND -- hardened against
TWO adversary kills the review gate caught (KILL 1 dalembert: masked-carbonyl donors; KILL 2 evil-morty: the false
"aromatic N carries an order-2 bond" premise) -- and NON-VACUOUS (a general longer-alcohol alkylation now vouched;
caffeine kept).  These fast regression pins run over the SAME live behaviour, independent of the probe, so a
refactor cannot silently drop coverage or re-open a kill.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.smiles import parse_smiles
from smartchem.experiment.feasibility import _alkyl_carbinol_alcohol_count, _n_alkyl_amine_bond_count
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers
import experiments.poor_man_n_alkylation_recognizer_probe as probe


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_consumer_is_served_general_longer_alcohol_alkylation_now_vouched():
    # the R63 advance: a longer-alcohol N-alkylation the R60 methanol clamp DEMOTED is now VOUCHED.
    c = probe.consumer_served()
    assert c["n_ethylaniline_centre"] is True
    assert c["n_ethylaniline_vouched"] is True   # aniline + ethanol -> N-ethylaniline
    assert c["ethylamine_vouched"] is True        # ammonia + ethanol -> ethylamine
    assert c["served"] is True


def test_the_oracle_is_sound_zero_cc_false_vouch_and_caffeine_kept():
    sc = probe.soundness_and_coverage()
    assert sc["total_frontier_routes"] > 0
    assert sc["cc_false_vouch_count"] == 0      # no C-C fiction vouched (the frontier proxy stays clean)
    assert sc["caffeine_vouched"] is True       # the R45 win preserved through the general recognizer


def test_kill1_masked_carbonyl_donors_are_demoted():
    # dalembert's kill: an aminal/hemiaminal condensation must NOT be vouched as N-alkylation (masked carbonyl donor).
    k1 = probe.kill1_masked_carbonyl_donors_demoted()
    assert k1["all_demoted"] is True
    assert k1["aminal_methylenediamine"]["demoted"] is True
    assert k1["aminal_bis_dimethylaminomethane"]["demoted"] is True


def test_kill2_azole_admitted_and_aryl_amination_fake_demoted():
    # evil-morty's finding, resolved by scope: azole N-alkylation is a real class, ADMITTED (vouches); the
    # aryl-amination fake stays demoted (escape #7 shut), and O-alkylation is not mistaken for N-alkylation.
    k2 = probe.kill2_azole_admitted_aryl_fake_demoted()
    assert k2["all_azoles_vouched"] is True
    assert k2["aryl_amination_fake_vouched"] is False
    assert k2["o_alkylation_vouched"] is False


def test_broad_scope_exotic_n_vouched_amide_stays_disjoint():
    scope = probe.broad_scope()
    assert scope["all_exotic_vouched"] is True     # sulfonamide / hydrazine / hydroxylamine N-alkylation vouch
    assert scope["all_amide_demoted"] is True       # amide/lactam/tautomerizable-amide N stays disjoint (demoted)


def test_the_donor_census_unit_separates_alkyl_alcohols_from_masked_carbonyls():
    # methanol / ethanol / benzyl alcohol / ethanolamine's beta-OH are ALKYL carbinols (kept)
    assert _alkyl_carbinol_alcohol_count(parse_smiles("CO")) == 1
    assert _alkyl_carbinol_alcohol_count(parse_smiles("CCO")) == 1
    assert _alkyl_carbinol_alcohol_count(parse_smiles("OCc1ccccc1")) == 1
    assert _alkyl_carbinol_alcohol_count(parse_smiles("NCCO")) == 1
    # masked carbonyls (hemiaminal / gem-diol / hemiacetal) and aromatic phenol are EXCLUDED
    assert _alkyl_carbinol_alcohol_count(parse_smiles("NCO")) == 0
    assert _alkyl_carbinol_alcohol_count(parse_smiles("OCO")) == 0
    assert _alkyl_carbinol_alcohol_count(parse_smiles("COCO")) == 0
    assert _alkyl_carbinol_alcohol_count(parse_smiles("Oc1ccccc1")) == 0
    # the amine-side census counts sp3-C--to--non-carbonyl-N BONDS (rises +1 per alkylation)
    assert _n_alkyl_amine_bond_count(parse_smiles("CCN")) == 1              # ethylamine
    assert _n_alkyl_amine_bond_count(parse_smiles("CN(C)C")) == 3           # trimethylamine
    assert _n_alkyl_amine_bond_count(parse_smiles("CC(=O)NC")) == 0         # N-methylacetamide (amide N excluded)
    assert _n_alkyl_amine_bond_count(parse_smiles("Nc1ccccc1")) == 0        # aniline (aryl C, not sp3)


def test_a_real_n_alkylation_is_positively_recognized():
    pc = probe.positive_control()
    assert pc["all_recognized"] is True
    assert pc["aniline_ethanol"]["centre"] is True
    assert pc["dimethylamine_methanol"]["recognized"] is True  # secondary -> tertiary (bond count +1)


def test_centre_absent_step_fails_closed():
    caf = probe.centre_absent_fails_closed()
    assert caf["reaction_center_is_none"] is True
    assert caf["census_would_pass"] is True     # the non-local census WOULD vouch -- but the centre is required
    assert caf["demoted"] is True
    assert caf["route_blocked"] is True


def test_upstream_recognizers_and_probes_unbroken():
    ups = probe.upstream_probes()
    assert ups["acyl_class_recognized"] is True
    assert ups["ether_class_recognized"] is True
    assert ups["r56_probe_frozen"] and ups["r57_probe_frozen"] and ups["r58_probe_frozen"] and ups["r60_probe_frozen"]


def test_a_zero_step_route_is_vacuously_vouched():
    assert route_reaction_type_blockers(SimpleNamespace(steps=())) == ()


def test_the_demoter_is_fail_closed_and_disposition_honest():
    fc = probe.fail_closed_and_disposition()
    assert fc["no_crash_on_raising_recognizer"] is True
    assert fc["fake_still_demoted"] is True
    assert fc["disposition_honest"] is True
