"""POOR-MAN-SYMMETRIC-WHITELIST-PHASE05-DEFER-01 (R54, Phase 0.5): the FIFTH verified defer of the ingenuity
reward -- the one that kills the escape the four prior defers (R49/R50/R52/R53) all named.

The committed probe (:mod:`experiments.poor_man_symmetric_whitelist_phase05_probe`) is the frozen evidence that a
SYMMETRIC POSITIVE safe-set whitelist -- confidently FEASIBLE only when BOTH reaction centers are positively
recognized-inert -- does NOT reach zero false-VOUCH when "recognized-inert" is an ELEMENT census over a bounded
radius.  A five-bearing adversarial design gate broke the FEASIBLE set on multiple determinant axes the census
can neither read nor decline (alpha,beta-unsaturation polymerization; remote acid-labile groups past the scan
radius -- a regression vs R53; 5-membered heteroaromatic ring vacuity), and proved the leak is not patchable
within the positive frame (the acrylic patch also false-EXCLUDEs feasible crotonic/cinnamic/sorbic) at a base
rate that declines the polyfunctional-feasible population (recall 0.875 friendly -> 0.574 deployment).  The
theorem: inverting the R53 blacklist to a positive whitelist MOVED the collision into the definition of
"recognized-inert"; it did not close it.

These are the fast regression pins over the SAME live behavior, kept independent of the probe so a refactor
cannot silently drop coverage.  If a "positive result" pin fires, the carbinol-side core regressed; if a "kill"
pin stops firing, someone quietly patched a leak (which only proves the unbounded-hazard theorem again one step
out) and the defer's evidence must be re-stated, not silently dropped.
"""
from __future__ import annotations

from smartchem.smiles import parse_smiles
from experiments import poor_man_symmetric_whitelist_phase05_probe as probe


def _v(alc: str, acid: str) -> str:
    return probe.symmetric_whitelist_verdict(parse_smiles(alc), parse_smiles(acid))


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_positive_result_friendly_battery_is_clean_and_closes_the_r53_kill():
    # The genuine gain: on the friendly-subset battery the whitelist is clean (0 false-VOUCH) and non-vacuous,
    # and it CLOSES the entire R53 kill the continuous estimator could not.
    p = probe._payload()
    assert p["counts"]["battery_false_vouch"] == 0
    assert p["battery_sound"] is True
    assert p["counts"]["true_vouch"] > 0
    # the R53 leaks are now declined
    assert _v("CCO", "CC(=O)CC(=O)O") == probe.UNKNOWN      # beta-keto acetoacetic
    assert _v("OC(C)SCC", "CC(=O)O") == probe.UNKNOWN       # alpha-thioether
    assert _v("OCc1ccco1", "CC(=O)O") == probe.UNKNOWN      # furfuryl


def test_the_carbinol_side_core_is_the_banked_sound_part():
    # The one part all five bearings agree reads a real reaction-center determinant.
    assert probe.recognize_inert_carbinol(parse_smiles("CCCCCO")) is True       # plain primary
    assert probe.recognize_inert_carbinol(parse_smiles("CC(C)(C)O")) is False   # tertiary -> E1
    assert probe.recognize_inert_carbinol(parse_smiles("CC(O)c1ccccc1")) is False  # sec-benzylic -> SN1


def test_kill_alpha_beta_unsaturated_acid_class_false_vouches():
    # dalembert/evil-morty: the whole alpha,beta-unsaturated acid class VOUCHes and polymerizes/Michael-adds.
    assert _v("CCO", "C=CC(=O)O") == probe.FEASIBLE     # acrylic -> FALSE-VOUCH
    assert _v("CCO", "CC(=C)C(=O)O") == probe.FEASIBLE  # methacrylic
    assert _v("CCO", "C#CC(=O)O") == probe.FEASIBLE     # propiolic


def test_kill_remote_acid_labile_regression_vs_r53():
    # evil-morty: a labile group past radius 2 is invisible to the positive scan (R53 declined these).
    assert _v("OCCCC1CO1", "CC(=O)O") == probe.FEASIBLE      # remote epoxide -> FALSE-VOUCH
    assert _v("OCCCC(OC)OC", "CC(=O)O") == probe.FEASIBLE    # remote acetal -> FALSE-VOUCH


def test_kill_five_membered_heteroaromatic_guard_vacuity():
    # evil-morty: the ring-heteroatom decline keys on 6-rings, so a 5-ring heteroaromatic bypasses it.
    assert _v("CO", "OC(=O)c1ccc[nH]1") == probe.FEASIBLE    # pyrrole-2-carboxylic -> FALSE-VOUCH (resinifies)


def test_kill_spans_multiple_independent_axes():
    p = probe._payload()
    assert p["counts"]["adversarial_false_vouches"] >= 1
    assert p["counts"]["adversarial_axes"] >= 2
    assert all(r["is_false_vouch"] for r in p["adversarial_false_vouches"])
    assert p["defer_verdict"] is True


def test_the_acrylic_patch_cannot_separate_the_r52_scissors():
    # Closing the acrylic false-VOUCH by declining alpha,beta-unsaturation ALSO false-EXCLUDEs feasible
    # crotonic/cinnamic/sorbic -- the leak is not patchable within the positive frame.
    pc = probe.run_patch_collision()
    assert pc["separates"] is False
    assert pc["declined_feasible"] >= 1 and pc["declined_infeasible"] >= 1


def test_the_base_rate_cost_declines_real_feasible_esters():
    # The polyfunctional-feasible workhorses (malonate, wintergreen, parabens, lactate, glycolate, pyruvate)
    # are declined -- the soundness attempt is bought by a high false-EXCLUDE rate.
    dfe = probe.run_deployment_false_excludes()
    assert all(r["is_false_exclude"] for r in dfe)
