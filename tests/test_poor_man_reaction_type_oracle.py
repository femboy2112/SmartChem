"""POOR-MAN-REACTION-TYPE-ORACLE-01 (R56): the FIRST sound production code the ingenuity reward ships.

The committed probe (:mod:`experiments.poor_man_reaction_type_oracle_probe`) is the frozen evidence that a
positive-whitelist reaction-TYPE oracle (:mod:`smartchem.experiment.reaction_type_oracle`) DEMOTES reaction-TYPE
fictions off the affordability frontier -- SOUND (0 false-VOUCH across the production frontier), NON-VACUOUS
(genuine acyl reals still vouched), and different-in-kind from the R49-R55 escape #7 (its unbounded-ness surfaces
as coverage loss, never a false-VOUCH).  Scope: ACYL-condensation only (the one conservation-locked recognizer);
the R45 caffeine N-methylation win is demoted as honest coverage loss this round.

These are the fast regression pins over the SAME live behaviour, kept independent of the probe so a refactor
cannot silently drop coverage.  If the "consumer" pin stops firing, the pollution was fixed elsewhere (re-state
the win).  If the "soundness" pin stops firing, the oracle started false-VOUCHing a fiction (the catastrophic
regression -- STOP).  If the "escape-#7 boundary" pin stops firing, the acyl-only scope must be re-audited.
"""
from __future__ import annotations

from types import SimpleNamespace

from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.experiment.compile import compile_synthesis
from smartchem.experiment.reaction_type_oracle import route_reaction_type_blockers, recognize_reaction_type
from smartchem.service import build_recompile_request, run_compilation
import experiments.poor_man_reaction_type_oracle_probe as probe


def _routes(target_smiles, available, reagents=None):
    tgt = parse_smiles(target_smiles)
    av = tuple(probe._resolve(t) for t in available)
    kw = {"available": av, "commodities": ()}
    if reagents is not None:
        kw["reagents"] = tuple(probe._resolve(t) for t in reagents)
    return probe._routes_of(compile_synthesis(tgt, **kw))


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_consumer_is_served_isopentyl_acetate_fictions_now_blocked():
    # the transformative advance: the frontier fictions that shipped UN-blocked at R55 now all carry the blocker.
    resp = run_compilation(build_recompile_request("isopentyl acetate", max_depth=3))
    fr = resp.affordability_frontier
    assert len(fr) > 0
    for e in fr:
        hb = tuple(getattr(e.cost_vector, "hard_blockers", ()) or ())
        assert any("unrecognized reaction type" in b for b in hb), f"a fiction still ships un-blocked: {hb}"


def test_the_oracle_is_sound_zero_false_vouch_on_the_production_frontier():
    sc = probe.soundness_and_coverage()
    assert sc["total_frontier_routes"] > 0
    assert sc["false_vouch_count"] == 0     # the catastrophic error -- a fiction must NEVER be vouched


def test_the_oracle_is_non_vacuous_genuine_acyl_reals_survive():
    sc = probe.soundness_and_coverage()
    assert sc["reals_vouched"] >= 1
    # the genuine esterification/amidation targets stay vouched (their real acyl step is recognized)
    assert "aspirin" in sc["vouched_targets"]


def test_the_acyl_recognizer_vouches_a_real_fischer_ester():
    routes = _routes("CC(=O)OCCC(C)C", ["acetic acid", "isopentyl alcohol"], reagents=["water"])
    assert routes, "the Fischer ester stopped being reachable"
    assert any(not route_reaction_type_blockers(r) for r in routes)   # at least one route fully recognized
    # and the recognizer names the class on the ester step
    fires = [recognize_reaction_type(st) for r in routes for st in r.steps]
    assert any(name is not None and "acyl" in name for name in fires)


def test_both_r55_false_vouch_fakes_are_now_demoted():
    # the exact two cases that broke R55's join-element rule are DEMOTED by the type oracle.
    for tsmi, avail in (("CC(C)CCO", ["CC(C)CC", "hydrogen peroxide"]),
                        ("Nc1ccc(N)cc1", ["ammonia", "4-aminophenol"])):
        routes = _routes(tsmi, avail)
        assert routes, f"{tsmi} stopped being reachable"
        assert all(route_reaction_type_blockers(r) for r in routes)   # every route demoted (unrecognized)


def test_real_cc_condensations_are_demoted_as_honest_coverage_loss():
    # Friedel-Crafts / Claisen are real but unregistered -> demoted-as-UNRECOGNIZED (coverage loss, NOT false-vouch).
    fc = _routes("CC(=O)c1ccccc1", ["benzene", "acetic acid"], reagents=["water"])
    assert fc and all(route_reaction_type_blockers(r) for r in fc)
    claisen = _routes("CCOC(=O)CC(=O)C", ["CCOC(=O)C"], reagents=["ethanol"])
    assert claisen and all(route_reaction_type_blockers(r) for r in claisen)


def test_caffeine_is_demoted_as_coverage_loss_not_false_vouched():
    # the R45 genericity win: acyl-only cannot vouch N-methylation, so caffeine is DEMOTED as honest coverage loss
    # this round -- but it is NEVER false-vouched (the whole point of cutting the general N-alkylation recognizer).
    routes = probe._routes_of(compile_synthesis(structure_by_name("caffeine").molecule, max_depth=2))
    assert routes
    assert all(route_reaction_type_blockers(r) for r in routes)   # demoted, honestly, as unrecognized


def test_the_escape7_boundary_holds_general_nc_recognizer_collides():
    # the principled reason acyl-only is the scope: a GENERAL new-N-C recognizer fires on BOTH caffeine (real) and
    # the aromatic-amination fake (fake) -- escape #7 one alphabet over -- so it is deliberately not shipped.
    esc = probe.escape7_boundary()
    assert esc["general_nc_fires_caffeine"] is True
    assert esc["general_nc_fires_amination_fake"] is True
    assert esc["collision"] is True


def test_the_demoter_is_fail_closed_and_total():
    # a recognizer that RAISES never yields a spurious VOUCH and never crashes the frontier build.
    fc = probe.fail_closed_on_recognizer_error()
    assert fc["no_crash_on_raising_recognizer"] is True
    assert fc["fake_still_demoted"] is True


def test_a_zero_step_route_is_vacuously_vouched():
    # target already available (no steps) -> nothing to recognize -> no blocker (vacuous VOUCH), never a spurious sink.
    assert route_reaction_type_blockers(SimpleNamespace(steps=())) == ()


def test_the_disposition_is_honest_not_a_feasibility_claim():
    # the reason vocabulary must say "unrecognized reaction type" and disclaim cost/feasibility (type-validity only).
    routes = _routes("CC(C)CCO", ["CC(C)CC", "hydrogen peroxide"])
    reasons = [b for r in routes for b in route_reaction_type_blockers(r)]
    assert reasons
    assert all("unrecognized reaction type" in b for b in reasons)
    assert all("NOT a claim of cost or feasibility" in b for b in reasons)
