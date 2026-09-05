"""Acceptance: SOURCED whole-process records drive real FIT / EXCLUDE / UNKNOWN through the search.

Every process value under test traces to an open-license bench procedure (LibreTexts CC BY-NC-SA 4.0,
cross-checked where possible; see the provenance strings in ``smartchem/decompiler_conditions.py``) --
no fabricated number. Unlike ``test_process_service`` (which monkeypatches ``_conditions_for`` to inject
synthetic metadata), these exercise the PROCESS-FIT gate on the ACTUAL ``recompile`` search hitting the
real seeded ``ProcessRequirements``. This is the audit's continuation-contract acceptance made executable:
the expected profile fits; a stricter time / apparatus / heat limit excludes; a constrained-but-undeclared
dimension yields UNKNOWN; the record does not leak to an unseeded reaction; a held-out second reaction
(isopentyl acetate) behaves as predicted.
"""
from dataclasses import replace

from smartchem.process_constraints import Agitation, Attention, ProcessBounds
from smartchem.service import build_recompile_request, run_compilation

PARA = "smiles:CC(=O)Nc1ccc(O)cc1"
PARA_KW = dict(helper_reagents=("acetic acid",),
               stock_materials=("4-aminophenol", "acetic anhydride"), max_depth=1)

# A poor-man's bench that CAN run this prep: periodic attention, hand-swirling, the sourced glassware,
# and no hard time budget. Every allowed value matches a SOURCED requirement of the record.
PARA_BENCH = ProcessBounds(
    allowed_attention=(Attention.PERIODIC,),
    allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
    available_equipment=("erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                         "fluted filter paper", "buchner funnel", "water aspirator"),
)


def _para(process=None, **kw):
    return run_compilation(build_recompile_request(PARA, process=process, **PARA_KW, **kw))


def _acetylation(resp):
    """The seeded acetylation route: acetic anhydride (C4H6O3) + 4-aminophenol (C6H7NO)."""
    return next(r for r in resp.ranked_route_dossiers
               if "C4H6O3" in r.equation and "C6H7NO" in r.equation)


def test_sourced_paracetamol_fits_a_manual_periodic_bench():
    # THE expected profile fits: the operator's declared capabilities cover every sourced requirement.
    resp = _para(process=PARA_BENCH)
    assert resp.process_selection_status == "FITS_FOUND"
    assert resp.admissible_route_digests
    assert _acetylation(resp).fit_status == "FITS"


def test_sourced_paracetamol_excluded_when_too_slow_for_quick():
    # 'quick' caps a step at 60 min; the SOURCED elapsed floor is 84 min -> proven too long -> EXCLUDED.
    # (A floor can only exclude; it never confirms a fit.)
    resp = _para(process=ProcessBounds.quick())
    assert resp.process_selection_status == "NO_FIT_FOUND"
    assert not resp.admissible_route_digests
    d = _acetylation(resp)
    assert d.fit_status == "EXCLUDED"
    assert any("minimum elapsed" in e for e in d.exclusions)


def test_sourced_paracetamol_excluded_by_missing_equipment():
    bench = replace(PARA_BENCH, available_equipment=("erlenmeyer flask", "steam bath"))
    resp = _para(process=bench)
    d = _acetylation(resp)
    assert d.fit_status == "EXCLUDED"
    assert any("equipment is unavailable" in e for e in d.exclusions)


def test_sourced_paracetamol_excluded_by_a_stricter_temperature_ceiling():
    # the SOURCED whole-process peak is 373.15 K (steam bath); an operator capped at 350 K cannot run it.
    resp = _para(process=PARA_BENCH, max_temperature_k=350.0)
    assert _acetylation(resp).fit_status == "EXCLUDED"


def test_sourced_paracetamol_unknown_when_a_constrained_dimension_is_undeclared():
    # The record does NOT declare a check interval. An operator who constrains it therefore cannot be
    # told the route fits -> UNKNOWN with a gap, never a silent pass. (Omitting a fact yields UNKNOWN.)
    bench = replace(PARA_BENCH, min_check_interval_minutes=90.0)
    resp = _para(process=bench)
    d = _acetylation(resp)
    assert d.fit_status == "UNKNOWN"
    assert any("check_interval" in g for g in d.gaps)


def test_sourced_process_does_not_leak_to_an_unseeded_reaction():
    # Scope: methyl acetate has no whole-process record. Under the same bench it can never be FITS --
    # a sourced record is licensed only for its exact reaction, never borrowed by formula/analogy.
    resp = run_compilation(build_recompile_request("smiles:CC(=O)OC", max_depth=2, process=PARA_BENCH))
    assert resp.process_selection_status != "FITS_FOUND"
    assert not resp.admissible_route_digests


def test_sourced_isopentyl_acetate_fits_a_bench():
    # Held-out second reaction: the Fischer esterification behaves as predicted on its own sourced record.
    bench = ProcessBounds(
        allowed_attention=(Attention.PERIODIC,),
        allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
        available_equipment=("round-bottom flask", "reflux condenser", "heating mantle", "boiling stones",
                             "separatory funnel", "distillation apparatus", "thermometer"),
    )
    resp = run_compilation(build_recompile_request(
        "name:isopentyl acetate", stock_materials=("isopentyl alcohol", "acetic acid"),
        max_depth=1, process=bench))
    assert resp.process_selection_status == "FITS_FOUND"
    assert resp.admissible_route_digests


# --- ROUND 11 item 4: a THIRD sourced record (methyl salicylate, LibreTexts 'Experiment 731', CC BY).
# The source is a QUALITATIVE test-tube prep: it times the heating (a floor) but describes no preparative
# workup and no reaction-step agitation, so this record HONESTLY can never FITS (workup+agitation undeclared)
# -- it exercises the gate's real-data UNKNOWN and EXCLUDED verdicts, the complement to the two FITS records.
MS = "name:methyl salicylate"
MS_KW = dict(stock_materials=("salicylic acid", "methanol"), max_depth=1)
# A bench that covers every SOURCED dimension of the record (equipment/attention). It still cannot FIT,
# because the source declares neither a preparative workup nor a reaction-step agitation.
MS_BENCH = ProcessBounds(
    allowed_attention=(Attention.PERIODIC,),
    allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
    available_equipment=("hot plate", "250 mL beaker (warm water bath)", "small (~10 mL) test tubes",
                         "test tube clamp", "test tube rack", "pipet", "watch glass"),
)


def _ms(process=None, **kw):
    return run_compilation(build_recompile_request(MS, process=process, **MS_KW, **kw))


def _esterification(resp):
    return next(r for r in resp.ranked_route_dossiers if "C7H6O3" in r.equation and "CH4O" in r.equation)


def test_sourced_methyl_salicylate_unknown_without_a_workup_or_agitation():
    # A covering bench cannot be told the route FITS: the SOURCE documents no preparative workup and no
    # reaction-step agitation, so both are honestly UNKNOWN -> the gate refuses a FITS with named gaps.
    resp = _ms(process=MS_BENCH)
    assert resp.process_selection_status == "NO_FIT_FOUND"
    assert not resp.admissible_route_digests
    d = _esterification(resp)
    assert d.fit_status == "UNKNOWN"
    assert any("workup" in g for g in d.gaps)
    assert any("agitation" in g for g in d.gaps)


def test_sourced_methyl_salicylate_excluded_by_a_stricter_temperature_ceiling():
    # SOURCED whole-process peak is 338.15 K (65 C water bath); an operator capped at 330 K cannot run it.
    d = _esterification(_ms(process=MS_BENCH, max_temperature_k=330.0))
    assert d.fit_status == "EXCLUDED"
    assert any("peak_temperature_k" in e for e in d.exclusions)


def test_sourced_methyl_salicylate_excluded_by_missing_equipment():
    d = _esterification(_ms(process=replace(MS_BENCH, available_equipment=("hot plate",))))
    assert d.fit_status == "EXCLUDED"
    assert any("equipment is unavailable" in e for e in d.exclusions)


def test_sourced_methyl_salicylate_excluded_when_too_slow_for_a_tight_step_budget():
    # The SOURCED elapsed floor is 10 min ('for 10 minutes or longer'); a 5-min step budget is proven too tight.
    d = _esterification(_ms(process=replace(MS_BENCH, max_step_minutes=5.0)))
    assert d.fit_status == "EXCLUDED"
    assert any("minimum elapsed" in e for e in d.exclusions)


# --- ROUND 12 item 3: a FOURTH sourced record -- ASPIRIN, the FLAGSHIP reaction (unblocked for compilation in
# ROUND 11 by resonance-canonical identity; its ortho-salicylate FRAGMENT now also RESOLVES to registered salicylic
# acid via the ROUND-12 resonance-identity fix in resolve_structure, which is what lets the sourced record attach).
# Unlike methyl salicylate, the source describes a genuinely PREPARATIVE workup, so workup_included=True and this
# record produces the FIRST sourced FITS on aspirin itself -- the complement to the qualitative records' UNKNOWN.
ASP = "smiles:CC(=O)Oc1ccccc1C(=O)O"
ASP_KW = dict(helper_reagents=("acetic acid",), stock_materials=("salicylic acid", "acetic anhydride"), max_depth=2)
# A bench that covers every SOURCED dimension of the aspirin record (equipment / attention / agitation).
ASP_BENCH = ProcessBounds(
    allowed_attention=(Attention.PERIODIC,),
    allowed_agitation=(Agitation.MANUAL, Agitation.NONE),
    available_equipment=("125-mL Erlenmeyer flask", "steam bath", "glass rod", "ice bath",
                         "Buchner funnel", "150 mL beaker", "dropper"),
)


def _asp(process=None, **kw):
    return run_compilation(build_recompile_request(ASP, process=process, **ASP_KW, **kw))


def _asp_acetylation(resp):
    """The seeded acetylation route: acetic anhydride (C4H6O3) + salicylic acid (C7H6O3)."""
    return next(r for r in resp.ranked_route_dossiers if "C7H6O3" in r.equation and "C4H6O3" in r.equation)


def test_sourced_aspirin_fits_a_covering_bench():
    # THE first sourced FITS on the flagship reaction: the record's PREPARATIVE workup (Buchner vacuum filtration ->
    # recrystallise -> dry -> melting point) makes a genuine FITS reachable, unlike the qualitative-prep records.
    resp = _asp(process=ASP_BENCH)
    assert resp.process_selection_status == "FITS_FOUND"
    assert resp.admissible_route_digests
    assert _asp_acetylation(resp).fit_status == "FITS"


def test_sourced_aspirin_excluded_by_missing_equipment():
    d = _asp_acetylation(_asp(process=replace(ASP_BENCH, available_equipment=("steam bath",))))
    assert d.fit_status == "EXCLUDED"
    assert any("equipment is unavailable" in e for e in d.exclusions)


def test_sourced_aspirin_excluded_by_a_stricter_temperature_ceiling():
    # The SOURCED whole-process peak is 373.15 K (steam bath); an operator capped at 350 K cannot run it.
    d = _asp_acetylation(_asp(process=ASP_BENCH, max_temperature_k=350.0))
    assert d.fit_status == "EXCLUDED"
    assert any("peak_temperature_k" in e for e in d.exclusions)


def test_sourced_aspirin_excluded_when_too_slow_for_a_tight_step_budget():
    # The SOURCED elapsed floor is 10 min ('for at least 10 minutes'); a 5-min step budget is proven too tight.
    d = _asp_acetylation(_asp(process=replace(ASP_BENCH, max_step_minutes=5.0)))
    assert d.fit_status == "EXCLUDED"
    assert any("minimum elapsed" in e for e in d.exclusions)


def test_sourced_aspirin_unknown_when_a_constrained_dimension_is_undeclared():
    # The record declares no check interval; an operator who constrains it cannot be told the route fits -> UNKNOWN.
    d = _asp_acetylation(_asp(process=replace(ASP_BENCH, min_check_interval_minutes=90.0)))
    assert d.fit_status == "UNKNOWN"
    assert any("check_interval" in g for g in d.gaps)
