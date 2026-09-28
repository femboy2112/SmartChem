"""v0.8 Round II -- source migration (Writer 2): the 4 forcing routes' typed procedure evidence.

Pins that the accepted primary sources were migrated into ConditionEnvelope.procedure via the STRUCTURALLY
guarded assembly path only (never the isomer-blind decomposition path), that each attached procedure is
sourced+well-formed, and that the control route (methyl salicylate) honestly carries no procedure. Tier outcomes
live in the readiness suite; this file asserts attachment + source scope, not the tier.
"""
from __future__ import annotations

import smartchem.decompiler_conditions as dc
from smartchem.algebra_profiles import DEFAULT_ROUTE_ALGEBRA_PROFILE, resolve_algebra_profile
from smartchem.decompiler import Formula
from smartchem.decompiler_conditions import ReactionDirection, reaction_conditions
from smartchem.experiment import routes as rt
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.procedure_evidence import ProcedureEvidence

_CERTIFIED = resolve_algebra_profile(DEFAULT_ROUTE_ALGEBRA_PROFILE)


def _search(target_name, reagents, have, max_depth):
    target = resolve_target(target_name, InputKind.NAME).canonical()
    reag = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in reagents)
    hv = tuple(resolve_target(s, InputKind.AUTO).canonical() for s in have)
    return rt.search_routes(target, reagents=reag, available=hv, max_depth=max_depth, registry=_CERTIFIED)


def _find_step_with_procedure(result):
    for route in result.routes:
        for step in route.steps:
            if step.envelope.procedure is not None:
                return step
    return None


def test_the_three_preparative_routes_carry_a_sourced_procedure_the_control_does_not():
    attached = {rec.assembly_target_name: rec.envelope.procedure
                for rec in dc.SEED_CONDITIONS.values() if rec.assembly_target_name}
    for target in ("isopentyl acetate", "aspirin", "paracetamol"):
        ev = attached[target]
        assert isinstance(ev, ProcedureEvidence) and ev.is_sourced
        assert len(ev.operations) >= 2
    # methyl salicylate's source is a qualitative smell-test, not a preparative procedure -> no procedure
    assert attached["methyl salicylate"] is None


def test_paracetamol_procedure_carries_its_own_source_not_the_conditions_citation():
    rec = next(r for r in dc.SEED_CONDITIONS.values()
               if r.assembly_target_name == "paracetamol" and r.envelope.procedure is not None)
    # The envelope's CONDITIONS source is the ACS DOI; the PROCEDURE's own source is the LibreTexts page.
    assert "10.1021" in (rec.envelope.source.locator if rec.envelope.source else "")
    assert "Acetaminophen" in rec.envelope.procedure.source_locator
    assert rec.envelope.procedure.source_locator != rec.envelope.source.locator


def test_isopentyl_search_step_carries_the_migrated_procedure_via_the_assembly_path():
    result = _search("isopentyl acetate", ("water", "acetic acid"), ("isopentyl alcohol",), 3)
    step = _find_step_with_procedure(result)
    assert step is not None, "expected a searched isopentyl-acetate step to carry procedure evidence"
    assert step.envelope.procedure.source_locator == dc._ISOPENTYL_URL
    assert step.envelope.procedure.is_sourced


def test_decomposition_path_never_exposes_a_procedure_isomer_blind_leak_stays_closed():
    # reaction_conditions is formula-keyed (isomer-blind); it must NOT serve a procedure. The one seed record
    # it can return (paracetamol hydrolysis, DECOMPOSITION) carries no procedure, and ASSEMBLY is refused here.
    edge = type("E", (), {})()
    edge.reactant = Formula.parse("C8H9NO2")
    edge.reactant_multiplicity = 1
    edge.reagents = ((Formula.parse("H2O"), 1),)
    edge.products = ((Formula.parse("C6H7NO"), 1), (Formula.parse("C2H4O2"), 1))
    env = reaction_conditions(edge, direction=ReactionDirection.DECOMPOSITION)
    assert env.procedure is None
    # and the anhydride ASSEMBLY signature is refused through the formula-only decomposition API
    assert reaction_conditions(edge, direction=ReactionDirection.ASSEMBLY).procedure is None
