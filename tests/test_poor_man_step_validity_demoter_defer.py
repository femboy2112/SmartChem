"""POOR-MAN-STEP-VALIDITY-DEMOTER-DEFER-01 (R55): the SIXTH verified defer of the ingenuity reward -- the
first with a PROVEN, SURFACED, DOMINANT live consumer.

The committed probe (:mod:`experiments.poor_man_step_validity_demoter_defer_probe`) is the frozen evidence
that the frontier-pollution consumer is REAL (fictional routes ship un-blocked on the affordability frontier
today) but the natural Problem-A demoter -- "a step whose FORMED JOIN BOND is C-C is fake; C-O/C-N/C-S joins are
sound" -- is NOT sound: it FALSE-VOUCHes reachable non-C-C fakes (H2O2 hydroxylation; aromatic amination) AND
FALSE-EXCLUDEs reachable real C-C condensations (Friedel-Crafts, Claisen).  The join-bond element is neither
necessary nor sufficient for fakeness -- the R49-R54 bounded-local-recognizer theorem one alphabet over
(reaction-TYPE validity in place of reaction feasibility).

These are the fast regression pins over the SAME live behaviour, kept independent of the probe so a refactor
cannot silently drop coverage.  If the "consumer" pin stops firing, the pollution was fixed elsewhere (re-state
the win, do not silently drop it).  If a "false-VOUCH"/"false-EXCLUDE" pin stops firing, someone patched the
join-element rule (which only proves the theorem again one step out) and the defer's evidence must be re-stated.
"""
from __future__ import annotations

from smartchem.smiles import parse_smiles
from smartchem.structure import structure_by_name
from smartchem.experiment.compile import compile_synthesis
from experiments import poor_man_step_validity_demoter_defer_probe as probe


def _routes(target_smiles, available, reagents=None):
    tgt = parse_smiles(target_smiles)
    av = tuple(probe._resolve(t) for t in available)
    kw = {"available": av, "commodities": ()}
    if reagents is not None:
        kw["reagents"] = tuple(probe._resolve(t) for t in reagents)
    cs = compile_synthesis(tgt, **kw)
    return probe._routes_of(cs)


def test_probe_validates_and_frozen_hash_stable():
    assert probe.validate() is True
    assert probe.content_hash() == probe.FROZEN_HASH


def test_the_consumer_is_proven_fictions_ship_unblocked_on_the_frontier():
    # The transformative advance: refutes the standing "zero live consumers" premise (R49-R54).
    c = probe.consumer_proof()
    assert c["frontier_entries"] >= 1
    assert c["all_frontier_unblocked"] is True        # every frontier entry carries empty hard_blockers today
    assert c["all_reconstructed_fictional"] is True   # and every one is a C-C-fusion fiction


def test_the_pollution_base_rate_is_dominant():
    r = probe.base_rate()
    assert r["total_frontier_routes"] > 0
    assert r["fictional_fraction"] >= 0.5     # the majority of the production frontier is fiction


def test_the_raw_rule_false_vouches_a_reachable_C_O_hydroxylation_fake():
    # dalembert's FATAL: a C-O-join fake is reachable and the RAW "reject C-C" rule ABSTAINS -> VOUCH.
    routes = _routes("CC(C)CCO", ["CC(C)CC", "hydrogen peroxide"])   # isopentane + H2O2 -> isopentyl alcohol
    assert routes, "the H2O2 hydroxylation fake stopped being reachable"
    assert not any(probe.raw_rule_blocks(r) for r in routes)         # VOUCHED -- but it is chemically fake


def test_the_raw_rule_false_vouches_a_reachable_C_N_amination_fake():
    # a C-N-join fake from TWO commodities: ammonia + 4-aminophenol -> p-phenylenediamine.
    routes = _routes("Nc1ccc(N)cc1", ["ammonia", "4-aminophenol"])
    assert routes, "the aromatic-amination fake stopped being reachable"
    assert not any(probe.raw_rule_blocks(r) for r in routes)         # VOUCHED -- but aromatic amination is fake


def test_the_raw_rule_false_excludes_a_reachable_friedel_crafts_acylation():
    # the dual: a REAL C-C condensation the RAW rule wrongly SINKS.
    routes = _routes("CC(=O)c1ccccc1", ["benzene", "acetic acid"])   # -> acetophenone
    assert routes, "Friedel-Crafts acylation stopped being reachable"
    assert all(probe.raw_rule_blocks(r) for r in routes)             # BLOCKED -- but it is a real reaction


def test_the_raw_rule_false_excludes_a_reachable_claisen_condensation():
    routes = _routes("CCOC(=O)CC(=O)C", ["CCOC(=O)C"], reagents=["ethanol"])  # 2 ethyl acetate -> ethyl acetoacetate
    assert routes, "Claisen condensation stopped being reachable"
    assert all(probe.raw_rule_blocks(r) for r in routes)             # BLOCKED -- but Claisen is a real reaction


def test_the_defer_verdict_holds_across_both_failure_modes():
    p = probe._payload()
    assert p["counts"]["false_vouch_classes"] >= 1     # reachable non-C-C fakes VOUCHed
    assert p["counts"]["false_exclude_classes"] >= 1   # reachable real C-C reactions SUNK
    assert p["problem_a_is_the_consumer"] is True
    assert p["defer_verdict"] is True


def test_a_sound_step_survives_the_join_instrument_genericity_intact():
    # the instrument itself is sound as a MEASUREMENT: caffeine's untabulated N-methylation (the R45 win) forms
    # a C-N bond (dCC=0) and is NOT flagged -- the demoter's failure is the FEATURE choice, not the instrument.
    caff = structure_by_name("caffeine")
    cs = compile_synthesis(caff.molecule, max_depth=2)
    routes = probe._routes_of(cs)
    assert routes
    assert not any(probe.raw_rule_blocks(r) for r in routes)   # N-methylation kept -- genericity survives
