"""PLAN-01 / FORMULA-EXPR-01 integration -- the v0.6 human front door end to end, plus the mutation gate.

Proves the front door behaves at the identity/service/plan level, and pins the eight calibrated mutants the
v0.6 plan requires to DIE.  Each ``test_mutant_N_*`` asserts the exact behaviour the corresponding mutation
would break; ``experiments/v0_6_mutation_calibration.py`` (committed) injects each mutation and shows the
matching test goes red, so this gate is not vacuous.
"""
from __future__ import annotations

import pytest

from smartchem.compilation_ir import CompilationOperation
from smartchem.identity_parse import (
    IdentityParseError,
    InputKind,
    InputKindAmbiguity,
    detect_auto_ambiguity,
    resolve_identity,
)
from smartchem.plan import PlanResult, PlanStatus, plan, plan_result_to_payload
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


# == v0.6 hostile merge-readiness fixes (P0-A / P0-E / P0-F) + typed PlanStatus (P1) =========================

# -- P1: the explicit PlanStatus outcome, not an overloaded (operation, exit_code) triple --------------------
def test_plan_status_reflects_the_route():
    assert plan("C8H10N4O2").status is PlanStatus.FORMULA_DECOMPOSITION
    assert plan("smiles:CC(=O)OC").status is PlanStatus.STRUCTURAL_PLANNING
    assert plan("SO4^2-").status is PlanStatus.IDENTITY_ONLY          # charged: identity answered, no descent
    assert plan("not-a-real-name-zzz").status is PlanStatus.INVALID_INPUT
    assert plan("CO").status is PlanStatus.INPUT_KIND_AMBIGUOUS


# -- P0-A: the human front door refuses to silently pick between materially-distinct input-kind readings -----
def test_P0A_detect_auto_ambiguity_flags_cross_kind_strings():
    amb = detect_auto_ambiguity("CO")
    assert isinstance(amb, InputKindAmbiguity)
    assert set(amb.kinds) == {InputKind.SMILES, InputKind.FORMULA}


@pytest.mark.parametrize("text", ["CO", "CC", "CN", "NO", "Cl", "Br"])
def test_P0A_plan_reports_input_kind_ambiguity_instead_of_launching_structure(text):
    pr = plan(text)
    assert pr.status is PlanStatus.INPUT_KIND_AMBIGUOUS
    assert not pr.structural_planning_eligible          # NO silent structural launch
    assert pr.operation is None
    assert pr.exit_code == 2                             # a non-zero "supply an explicit kind" outcome
    assert pr.ambiguity is not None and len(pr.ambiguity.interpretations) >= 2


def test_P0A_explicit_kind_is_a_decision_and_resolves_unambiguously():
    # both escape hatches: an inline prefix and the --input-kind flag pin one reading, no ambiguity.
    assert plan("smiles:CO").status is PlanStatus.STRUCTURAL_PLANNING       # methanol
    assert plan("formula:CO").status is PlanStatus.FORMULA_DECOMPOSITION    # carbon monoxide
    assert plan("CO", InputKind.FORMULA).status is PlanStatus.FORMULA_DECOMPOSITION
    # detect_auto_ambiguity itself returns None once a kind is declared inline.
    assert detect_auto_ambiguity("smiles:CO") is None
    assert detect_auto_ambiguity("formula:CO") is None


def test_P0A_an_unambiguous_bare_formula_is_not_flagged():
    # C8H10N4O2 is a valid formula but NOT a valid SMILES -> only one reading -> not ambiguous.
    assert detect_auto_ambiguity("C8H10N4O2") is None
    assert plan("C8H10N4O2").status is PlanStatus.FORMULA_DECOMPOSITION
    # a registered name that is not also a formula is likewise single-reading.
    assert detect_auto_ambiguity("paracetamol") is None


def test_P0A_legacy_resolve_identity_precedence_is_unchanged():
    # the ambiguity lives on the PLAN surface; the expert identity authority keeps its AUTO precedence
    # (anti-Mutant-5 ordering), so CO still resolves to the SMILES reading there.
    assert resolve_identity("CO").receipt.resolved_kind is InputKind.SMILES


# -- P0-E: a TARGET_FILE perceives the SAME identity as resolving its contents directly ----------------------
def test_P0E_target_file_transports_the_v0_6_syntax_and_candidate_set(tmp_path):
    # a Unicode hydrate file must keep the syntax layer (formula_expr + component boundary).
    hyd = tmp_path / "hydrate.txt"
    hyd.write_text("CuSO₄·5H₂O", encoding="utf-8")
    direct = resolve_identity("CuSO₄·5H₂O", InputKind.AUTO)
    via_file = resolve_identity(str(hyd), InputKind.TARGET_FILE)
    assert via_file.formula_expr is not None, "formula_expr was dropped in transport"
    assert via_file.formula_expr.is_multi_component
    assert dict(via_file.formula.counts) == dict(direct.formula.counts)

    # a same-formula ambiguity file must transport the (non-exhaustive) registry candidate set.
    iso = tmp_path / "iso.txt"
    iso.write_text("C2H6O", encoding="utf-8")
    via_iso = resolve_identity(str(iso), InputKind.TARGET_FILE)
    direct_iso = resolve_identity("C2H6O", InputKind.AUTO)
    assert via_iso.registry_candidates, "candidate set was dropped in transport"
    assert {getattr(c, "name", None) for c in via_iso.registry_candidates} == {
        getattr(c, "name", None) for c in direct_iso.registry_candidates
    }
    # the plan JSON for a formula target file must retain the formula syntax.
    payload = plan_result_to_payload(plan(str(iso), InputKind.TARGET_FILE))
    assert payload["identity"]["formula_syntax"] is not None


# -- P0-F: a registry lookup FAILURE must not masquerade as "zero candidates" --------------------------------
def test_P0F_registry_programming_error_propagates_not_laundered(monkeypatch):
    import smartchem.structure as structure

    def boom(formula):
        raise RuntimeError("registry index corrupt")

    monkeypatch.setattr(structure, "known_compounds", boom)
    # the old `except Exception: return ()` turned this into a silent "no candidates"; it must now PROPAGATE.
    with pytest.raises(RuntimeError):
        resolve_identity("H2O", InputKind.FORMULA)


def test_P0F_available_registry_reports_lookup_ok_even_for_zero_candidates():
    # an empty candidate set with lookup_ok True is "queried, none known" -- distinct from "unavailable".
    r = resolve_identity("Cr2O7^2-", InputKind.FORMULA)
    assert r.registry_lookup_ok is True


# == the extended adversarial gate: mutants 9-14 (v0.6 hostile-review defects) ================================
# Each asserts the exact behaviour the corresponding mutation breaks; experiments/v0_6_mutation_calibration.py
# injects each and shows this check goes red, so the extended gate is non-vacuous.

# -- MUTANT 9: plan silently picks the SMILES reading for a cross-kind-ambiguous input (P0-A) -----------------
def test_mutant_9_plan_does_not_silently_resolve_a_cross_kind_ambiguity():
    pr = plan("CO")
    assert pr.status is PlanStatus.INPUT_KIND_AMBIGUOUS   # a mutant that skips detection -> STRUCTURAL_PLANNING
    assert pr.operation is not CompilationOperation.RECOMPILE


# -- MUTANT 10: an ambiguous bare-sign ion's digit is misread (single-element OR >=2-digit run) (P0-B) -------
@pytest.mark.parametrize("text", ["Fe3+", "Ca2+", "O2-", "SO42-", "PO43-"])
def test_mutant_10_ambiguous_bare_charge_is_refused_at_the_front_door(text):
    with pytest.raises(IdentityParseError):
        resolve_identity(text, InputKind.FORMULA)


# -- MUTANT 11: a compact ASCII decimal is coerced into an adduct composition (P0-C) -------------------------
def test_mutant_11_decimal_is_refused_never_becomes_an_adduct():
    with pytest.raises(IdentityParseError):
        resolve_identity("C1.5H2", InputKind.FORMULA)   # a mutant makes this C1H10 (C + 5x H2)


# -- MUTANT 12: a leading whole-expression coefficient is folded into composition (P0-D) ---------------------
def test_mutant_12_leading_coefficient_is_refused():
    with pytest.raises(IdentityParseError):
        resolve_identity("5H2O", InputKind.FORMULA)     # a mutant makes this H10O5


# -- MUTANT 13: a TARGET_FILE drops the v0.6 syntax/candidate fields in transport (P0-E) ---------------------
def test_mutant_13_target_file_does_not_drop_the_syntax_layer(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("CuSO₄·5H₂O", encoding="utf-8")
    r = resolve_identity(str(f), InputKind.TARGET_FILE)
    assert r.formula_expr is not None                    # a drop-mutant reconstructs without it -> None


# -- MUTANT 14: a registry failure is laundered into an empty candidate set (P0-F) ---------------------------
def test_mutant_14_registry_failure_is_not_swallowed(monkeypatch):
    import smartchem.structure as structure

    monkeypatch.setattr(structure, "known_compounds", lambda formula: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):                     # a laundering-mutant returns () and does NOT raise
        resolve_identity("H2O", InputKind.FORMULA)
