"""POOR-MAN-REACTIVITY-ESTIMATOR-PHASE0-DEFER-01 (R53, Phase 0): the FOURTH verified defer of the ingenuity reward.

The committed probe (:mod:`experiments.poor_man_reactivity_estimator_phase0_probe`) is the frozen evidence that a
CONTINUOUS three-valued Fischer-esterification estimator with a fail-closed domain guard -- the plan's one
unexplored fork -- is a REAL improvement over the boolean classifiers R49/R50/R52 killed (its alcohol-side
carbocation core is sound and independently calibration-verified), yet still does NOT reach zero false-VOUCH:
a five-bearing adversarial design gate broke the FEASIBLE set on multiple determinant axes the bounded feature
set + hand-enumerated guard can neither read nor decline (acid-side beta-keto decarboxylation; alpha-thioether
thionium; heteroaryl cation magnitude).  The theorem: making the classifier continuous MOVED the collision into
the guard; it did not close it.  These are the fast regression pins over the SAME live behavior, kept
independent of the probe so a refactor cannot silently drop coverage.  If a "positive result" pin fires, the
alcohol-side core regressed; if a "kill" pin stops firing, someone quietly patched a leak (which only proves the
unbounded-hazard theorem again one step out) and the defer's evidence must be re-stated, not silently dropped.
"""
from __future__ import annotations

from smartchem.smiles import parse_smiles
from experiments import poor_man_reactivity_estimator_phase0_probe as probe


def _est(alc: str, acid: str) -> str:
    return probe.estimate_fischer_feasibility(parse_smiles(alc), parse_smiles(acid))


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_positive_result_alcohol_side_core_is_sound_and_non_vacuous():
    # The core/calibration battery reads clean: zero false-VOUCH, a non-vacuous FEASIBLE set, and the guard
    # fires on the enumerated hazards it DOES know.  This is the genuine gain over R49/R50/R52.
    p = probe._payload()
    c = p["counts"]
    assert c["core_false_vouch"] == 0
    assert c["true_feasible"] > 0
    assert c["declined_unknown"] > 0
    assert p["core_clean"] is True


def test_bearing_a_benzylic_collision_is_closed_by_the_cation_score():
    # The degree-2 collision R52 said no bounded feature could close: isopropanol (score 2) vs 1-phenylethanol
    # (score 3), separated by the radius-1 conjugation term degree-alone was blind to.
    assert _est("CC(C)O", "CC(=O)O") == probe.FEASIBLE            # isopropanol -> works
    assert _est("CC(O)c1ccccc1", "CC(=O)O") == probe.NOT_FEASIBLE  # 1-phenylethanol -> E1/SN1


def test_the_kill_surviving_false_vouches_span_independent_axes():
    # THE defer's evidence: independent adversaries produced confident FEASIBLE on infeasible routes across
    # >=2 distinct determinant axes the guard neither reads nor declines.
    p = probe._payload()
    assert p["counts"]["adversarial_false_vouches"] >= 1
    assert p["counts"]["adversarial_axes"] >= 2
    assert all(r["is_false_vouch"] for r in p["adversarial_false_vouches"])
    assert p["defer_verdict"] is True


def test_kill_acid_side_beta_keto_decarboxylation_false_vouch():
    # dalembert: the acid side is a single ortho-aryl flag, blind to non-steric failure.  A beta-keto acid
    # decarboxylates under Fischer conditions (not a clean ester), but scores FEASIBLE -- and its alpha/gamma
    # neighbours are genuinely feasible, so separating beta needs the keto->carboxyl DISTANCE the model can't read.
    assert _est("CCO", "CC(=O)CC(=O)O") == probe.FEASIBLE   # acetoacetic (beta-keto) -> FALSE-VOUCH
    assert _est("CCO", "CC(=O)C(=O)O") == probe.FEASIBLE    # pyruvic (alpha-keto) -> genuinely feasible
    assert _est("CCO", "CC(=O)CCC(=O)O") == probe.FEASIBLE  # levulinic (gamma-keto) -> genuinely feasible


def test_kill_alpha_thioether_false_vouch_while_O_and_N_are_declined():
    # evil-morty: S is in the element whitelist but omitted from the alpha-heteroatom guard, so an alpha-thioether
    # (thionium SN1) is VOUCHED while its byte-identical alpha-O and alpha-N graphs are correctly DECLINED.
    assert _est("OC(C)SCC", "CC(=O)O") == probe.FEASIBLE    # alpha-S -> FALSE-VOUCH
    assert _est("OC(C)OCC", "CC(=O)O") == probe.UNKNOWN     # alpha-O -> declined
    assert _est("OC(C)NCC", "CC(=O)O") == probe.UNKNOWN     # alpha-N -> declined


def test_kill_heteroaryl_magnitude_blindness_furfuryl_matches_benzyl():
    # evil-morty/daniel: the binary conjugation flag is magnitude-blind, so furfuryl (ring-O-stabilized cation ->
    # acid resinification) gets benzyl's exact FEASIBLE vector.
    assert _est("OCc1ccco1", "CC(=O)O") == probe.FEASIBLE   # furfuryl -> FALSE-VOUCH
    assert _est("OCc1ccccc1", "CC(=O)O") == probe.FEASIBLE  # benzyl -> genuinely feasible (same vector)


def test_phenol_domain_fix_declines_sp2_reacting_carbons():
    # The P0.3 census's find, patched: a phenolic/enolic reacting O is out of the sp3-carbinol domain -> UNKNOWN,
    # not a wrong-physics NOT_FEASIBLE.
    assert _est("Oc1ccccc1", "CC(=O)O") == probe.UNKNOWN            # phenol
    assert _est("O=C(O)c1ccccc1O", "CC(=O)O") == probe.UNKNOWN      # salicylic acid (aspirin route)
