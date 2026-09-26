"""PLAN-01 / FORMULA-EXPR-01 integration -- the v0.6 human front door end to end, plus the mutation gate.

Proves the front door behaves at the identity/service/plan level, and pins the eight calibrated mutants the
v0.6 plan requires to DIE.  Each ``test_mutant_N_*`` asserts the exact behaviour the corresponding mutation
would break; ``experiments/v0_6_mutation_calibration.py`` (committed) injects each mutation and shows the
matching test goes red, so this gate is not vacuous.
"""
from __future__ import annotations

import pytest

from smartchem.compilation_ir import CompilationOperation
from smartchem.identity_parse import IdentityParseError, InputKind, resolve_identity
from smartchem.plan import PlanResult, plan, plan_result_to_payload
from smartchem.service import (
    build_recompile_request,
    deserialize_response,
    run_compilation,
    serialize_response,
)


# -- resolve_identity integration ----------------------------------------------------------------------------
def test_auto_resolves_a_bare_formula():
    r = resolve_identity("H2O")
    assert r.receipt.resolved_kind is InputKind.FORMULA
    assert r.molecule is None
    assert r.formula_expr is not None
    assert dict(r.formula.counts) == {"H": 2, "O": 1}


def test_auto_resolves_a_unicode_hydrate():
    r = resolve_identity("CuSO₄·5H₂O")
    assert r.receipt.resolved_kind is InputKind.FORMULA
    assert dict(r.formula.counts) == {"Cu": 1, "H": 10, "O": 9, "S": 1}
    assert r.formula_expr.is_multi_component


def test_explicit_forms_stay_authoritative():
    assert resolve_identity("paracetamol", InputKind.NAME).receipt.resolved_kind is InputKind.NAME
    assert resolve_identity("CC(=O)Nc1ccc(O)cc1", InputKind.SMILES).receipt.resolved_kind is InputKind.SMILES
    assert resolve_identity("H2O", InputKind.FORMULA).receipt.resolved_kind is InputKind.FORMULA


def test_explicit_smiles_failure_does_not_fall_through_to_formula():
    # an explicit smiles: input that fails to parse stays a SMILES failure -- formula is an AUTO-only fallback.
    with pytest.raises(IdentityParseError) as exc:
        resolve_identity("H2O", InputKind.SMILES)
    assert "SMILES" in str(exc.value)
    assert "formula" not in str(exc.value).split(";")[0].lower()  # not offered a formula reading


# -- MUTANT 1: strip Unicode subscripts instead of translating them ------------------------------------------
def test_mutant_1_unicode_subscripts_are_translated_not_dropped():
    # dropping subscripts would give C1H1N1O1; translating gives the true C8H10N4O2.
    assert dict(resolve_identity("C₈H₁₀N₄O₂").formula.counts) == {
        "C": 8, "H": 10, "N": 4, "O": 2
    }


# -- MUTANT 2: drop the hydrate leading multiplier -----------------------------------------------------------
def test_mutant_2_hydrate_multiplier_is_applied():
    # dropping the 5 in .5H2O yields H4O5 (1x water); applying it yields H10 O9.
    assert dict(resolve_identity("CuSO4·5H2O").formula.counts) == {"Cu": 1, "H": 10, "O": 9, "S": 1}


# -- MUTANT 3: flatten component boundaries before the syntax receipt ----------------------------------------
def test_mutant_3_component_boundary_is_retained_and_reported():
    r = resolve_identity("CuSO4·5H2O")
    assert len(r.formula_expr.components) == 2  # a flatten-mutant collapses to 1
    assert any("component" in n.lower() or "hydrate" in n.lower() for n in r.receipt.notes)


# -- MUTANT 4: infer a registered structure merely because its formula matches -------------------------------
def test_mutant_4_formula_match_never_selects_a_structure():
    r = resolve_identity("C2H6O")  # ethanol AND dimethyl ether are registered with this formula
    assert r.molecule is None, "a formula must not be promoted to a selected structure"
    assert not r.constitution_established
    names = {getattr(c, "name", None) for c in r.registry_candidates}
    assert {"ethanol", "dimethyl ether"} <= names  # exposed as an ambiguity SET, not a choice


def test_registry_candidate_set_is_not_treated_as_exhaustive():
    # a single registered candidate does NOT make the identity a constitution.
    r = resolve_identity("H2O")
    assert r.molecule is None
    assert not r.constitution_established
    assert any(getattr(c, "name", None) == "water" for c in r.registry_candidates)


# -- MUTANT 5: AUTO formula detection steals a valid registered name or SMILES -------------------------------
def test_mutant_5_auto_formula_never_steals_name_or_smiles():
    assert resolve_identity("CO").receipt.resolved_kind is InputKind.SMILES        # methanol, not formula C1O1
    assert resolve_identity("water").receipt.resolved_kind is InputKind.NAME
    assert resolve_identity("paracetamol").receipt.resolved_kind is InputKind.NAME
    assert resolve_identity("CC(=O)Nc1ccc(O)cc1").receipt.resolved_kind is InputKind.SMILES


# -- MUTANT 6: a formula-only identity enters structural recompile --------------------------------------------
def test_mutant_6_formula_only_recompile_is_refused():
    # the structural primitive must refuse a bare formula (no perceived structure), never invent one.
    resp = run_compilation(build_recompile_request("H2O", input_kind=InputKind.FORMULA))
    assert resp.outcome.value in {"INVALID_INPUT", "REFUSED"}


def test_mutant_6_plan_never_runs_recompile_on_a_formula():
    pr = plan("C8H10N4O2")
    assert not pr.structural_planning_eligible
    assert pr.operation is not CompilationOperation.RECOMPILE  # DECOMPILE or None, never RECOMPILE


# -- MUTANT 7: normalization/identity provenance disappears in transport/serialization -----------------------
def test_mutant_7_provenance_survives_plan_payload():
    payload = plan_result_to_payload(plan("CuSO4·5H2O"))
    ident = payload["identity"]
    assert ident["normalized"]  # the normalized composition is present
    assert ident["formula_syntax"]["original"] == "CuSO4·5H2O"  # the raw spelling is retained
    assert ident["formula_syntax"]["notes"]  # the normalization notes survived


def test_mutant_7_receipt_summary_survives_response_serialization():
    resp = run_compilation(build_recompile_request("paracetamol"))
    round_tripped = deserialize_response(serialize_response(resp))
    assert round_tripped.parse_receipt_summary == resp.parse_receipt_summary
    assert round_tripped.parse_receipt_summary  # and it is non-empty (provenance actually there)


# -- MUTANT 8: a parametric form is coerced into a concrete molecule ------------------------------------------
@pytest.mark.parametrize("text", ["(C2H4)n", "C6H(12±2)O6"])
def test_mutant_8_parametric_is_refused_by_the_identity_front_door(text):
    with pytest.raises(IdentityParseError):
        resolve_identity(text)


# -- plan() orchestration -----------------------------------------------------------------------------------
def test_plan_formula_routes_to_decompile():
    pr = plan("C8H10N4O2")
    assert isinstance(pr, PlanResult)
    assert pr.identity_layer == "FORMULA"
    assert pr.operation is CompilationOperation.DECOMPILE
    assert pr.exit_code == 0


def test_plan_structure_routes_to_recompile():
    pr = plan("smiles:CC(=O)OC")
    assert pr.identity_layer == "CONSTITUTION"
    assert pr.structural_planning_eligible
    assert pr.operation is CompilationOperation.RECOMPILE


def test_plan_invalid_input_is_typed_not_raised():
    pr = plan("not-a-real-name-zzz")
    assert pr.resolved is None
    assert pr.invalid_reason is not None
    assert pr.exit_code == 2


def test_plan_charged_formula_reports_identity_without_a_neutral_descent():
    pr = plan("SO4^2-")
    assert pr.identity_layer == "FORMULA"
    assert pr.operation is None            # no neutral formula descent for an ion
    assert pr.exit_code == 0               # the identity WAS delivered successfully
    assert pr.resolved.formula.charge == -2
