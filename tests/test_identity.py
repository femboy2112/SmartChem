"""ID-LAYER-01 (first brick) -- the section 5 layered identity model, section 5.4 layer-relative equality, and the
section 5.3 IdentityLoss record.

The load-bearing acceptance is section 5.4's probe: *same-formula isomers must share formula balance but remain
distinct everywhere a structural claim is made* -- and, the honesty half this brick adds, a match at a layer the
model cannot perceive is UNKNOWN, never fabricated.
"""
from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from smartchem.cli import main
from smartchem.compilation_ir import ChemicalIdentity
from smartchem.decompiler import Formula
from smartchem.identity import (
    IDENTITY_LOSS_SCHEMA,
    IdentityLoss,
    LayeredIdentity,
    LossSeverity,
    MatchLayer,
    formula_reduction_loss,
    refines,
    same_identity_at,
)
from smartchem.service import (
    IdentityPolicy,
    ResponseOutcome,
    build_decompile_request,
    build_recompile_request,
    deserialize_request,
    run_compilation,
    serialize_request,
)
from smartchem.smiles import parse_smiles, parse_smiles_features


def _mol(smiles):
    return parse_smiles(smiles)


def _layered(smiles):
    """A LayeredIdentity WITH parsed features -- so CONFIGURATION/ISOTOPIC are perceived (ID-STEREO-02)."""
    molecule, features = parse_smiles_features(smiles)
    return LayeredIdentity.of_molecule(molecule, features)


class TestSection54FormulaIsNotStructure:
    """The acceptance probe: same-formula isomers agree at FORMULA and are distinct at CONSTITUTION."""

    def test_isomers_agree_at_formula_differ_at_constitution(self):
        ethanol = LayeredIdentity.of_molecule(_mol("CCO"))
        dimethyl_ether = LayeredIdentity.of_molecule(_mol("COC"))  # both C2H6O
        assert same_identity_at(ethanol, dimethyl_ether, MatchLayer.FORMULA) is True
        assert same_identity_at(ethanol, dimethyl_ether, MatchLayer.CONSTITUTION) is False

    def test_same_molecule_two_smiles_agree_at_constitution(self):
        a = LayeredIdentity.of_molecule(_mol("CCO"))
        b = LayeredIdentity.of_molecule(_mol("OCC"))
        assert same_identity_at(a, b, MatchLayer.CONSTITUTION) is True

    def test_a_formula_match_is_never_promoted_to_a_structure_match(self):
        # a FORMULA-only identity vs a molecule: they agree at FORMULA, but the structural layer is UNKNOWN (the
        # formula literally cannot see constitution) -- never silently reported equal OR unequal there.
        formula_only = LayeredIdentity.of_formula(Formula.parse("C2H6O"))
        ethanol = LayeredIdentity.of_molecule(_mol("CCO"))
        assert same_identity_at(formula_only, ethanol, MatchLayer.FORMULA) is True
        assert same_identity_at(formula_only, ethanol, MatchLayer.CONSTITUTION) is None


class TestUnperceivedLayersAreUnknownNotFabricated:
    @pytest.mark.parametrize("layer", [MatchLayer.CONFIGURATION, MatchLayer.ISOTOPIC])
    def test_finer_layers_the_model_cannot_perceive_are_unknown(self, layer):
        a = LayeredIdentity.of_molecule(_mol("CCO"))
        b = LayeredIdentity.of_molecule(_mol("CCO"))
        # even for the SAME molecule, a layer the model cannot establish must be UNKNOWN, not a fabricated True.
        assert same_identity_at(a, b, layer) is None

    def test_digest_at_returns_none_for_an_unperceived_layer(self):
        ethanol = LayeredIdentity.of_molecule(_mol("CCO"))
        assert ethanol.digest_at(MatchLayer.CONSTITUTION) is not None
        assert ethanol.digest_at(MatchLayer.CONFIGURATION) is None


class TestConfigurationLayerWiring:
    """ID-STEREO-02: with parsed features, of_molecule perceives CONFIGURATION and ISOTOPIC -- fail-closed on
    incomplete perception, so enantiomers get DISTINCT identities while unperceived stereo stays honest UNKNOWN."""

    def test_enantiomers_share_constitution_but_differ_at_configuration(self):
        d, l_form = _layered("N[C@@H](C)C(=O)O"), _layered("N[C@H](C)C(=O)O")   # D- vs L-alanine
        assert same_identity_at(d, l_form, MatchLayer.CONSTITUTION) is True       # same graph
        assert same_identity_at(d, l_form, MatchLayer.CONFIGURATION) is False     # different handedness -- the refinement

    def test_configuration_is_spelling_invariant_for_one_enantiomer(self):
        a, b = _layered("N[C@@H](C)C(=O)O"), _layered("OC(=O)[C@H](C)N")          # same enantiomer, two spellings
        assert same_identity_at(a, b, MatchLayer.CONFIGURATION) is True

    def test_achiral_configuration_reduces_to_constitution_never_unknown(self):
        a, b = _layered("CCO"), _layered("OCC")                                   # achiral: configuration is known
        assert same_identity_at(a, b, MatchLayer.CONFIGURATION) is True           # perceived (not None), and equal
        assert same_identity_at(_layered("CCO"), _layered("COC"), MatchLayer.CONFIGURATION) is False  # still separates isomers

    def test_parser_preserved_ring_stereo_separates_enantiomers(self):
        # ROUND 35 preserves the ring digit's written neighbour position, so CONFIGURATION can distinguish this pair.
        r1, r2 = _layered("N[C@]1(F)CCCCO1"), _layered("N[C@@]1(F)CCCCO1")
        assert r1.digest_at(MatchLayer.CONFIGURATION) is not None
        assert same_identity_at(r1, r2, MatchLayer.CONFIGURATION) is False

    def test_double_bond_stereo_makes_configuration_unknown(self):
        # E/Z is unperceived (a named deferral), so a molecule declaring '/' or '\\' has UNKNOWN configuration -- never
        # a spuriously-confident reduction to constitution.
        ez = _layered("F/C=C/F")
        assert ez.digest_at(MatchLayer.CONFIGURATION) is None

    def test_enantiomeric_isotopologues_are_distinct_at_isotopic(self):
        # the trap the combined key closes: the bare isotopic_digest is chirality-blind, so two enantiomers with the
        # SAME isotope labels would share it -- but folding it OVER the configuration digest keeps them distinct.
        di = _layered("N[C@@H]([13CH3])C(=O)O")
        li = _layered("N[C@H]([13CH3])C(=O)O")
        assert same_identity_at(di, li, MatchLayer.CONSTITUTION) is True          # same graph
        assert same_identity_at(di, li, MatchLayer.ISOTOPIC) is False             # distinct isotopologue stereoisomers

    def test_isotopic_refines_configuration_refines_constitution(self):
        labeled = _layered("N[C@@H]([13CH3])C(=O)O")
        unlabeled = _layered("N[C@@H](C)C(=O)O")
        assert same_identity_at(labeled, unlabeled, MatchLayer.CONFIGURATION) is True   # same stereochemistry
        assert same_identity_at(labeled, unlabeled, MatchLayer.ISOTOPIC) is False       # isotopes differ
        assert labeled.known_layer is MatchLayer.ISOTOPIC                               # all four layers perceived

    def test_bare_of_molecule_still_perceives_only_formula_and_constitution(self):
        # WITHOUT features the historical behaviour is unchanged: no fabricated finer layer.
        bare = LayeredIdentity.of_molecule(_mol("N[C@@H](C)C(=O)O"))
        assert bare.known_layer is MatchLayer.CONSTITUTION
        assert bare.digest_at(MatchLayer.CONFIGURATION) is None


class TestDigestCongruence:
    """The layered identity must not fork a new notion of identity: its per-layer digests equal the pipeline's."""

    def test_constitution_digest_equals_of_molecule(self):
        ethanol = _mol("CCO")
        li = LayeredIdentity.of_molecule(ethanol)
        assert li.digest_at(MatchLayer.CONSTITUTION) == ChemicalIdentity.of_molecule(ethanol).identity_digest

    def test_formula_digest_equals_of_formula(self):
        li = LayeredIdentity.of_molecule(_mol("CCO"))
        assert li.digest_at(MatchLayer.FORMULA) == ChemicalIdentity.of_formula(Formula.parse("C2H6O")).identity_digest

    def test_layered_identity_digest_is_deterministic(self):
        a = LayeredIdentity.of_molecule(_mol("CC(=O)OC")).digest
        b = LayeredIdentity.of_molecule(_mol("CC(=O)OC")).digest
        assert a == b


class TestRefinementOrder:
    def test_finer_refines_coarser_not_the_reverse(self):
        assert refines(MatchLayer.CONSTITUTION, MatchLayer.FORMULA) is True
        assert refines(MatchLayer.ISOTOPIC, MatchLayer.FORMULA) is True
        assert refines(MatchLayer.FORMULA, MatchLayer.CONSTITUTION) is False

    def test_a_layer_refines_itself(self):
        assert refines(MatchLayer.CONSTITUTION, MatchLayer.CONSTITUTION) is True


class TestIdentityLoss:
    """Section 5.3: the typed loss record and its blocker semantics."""

    def test_formula_reduction_is_a_blocker_for_every_structure_dependent_claim(self):
        loss = formula_reduction_loss("smiles:CC(=O)Nc1ccc(O)cc1", "C8H9NO2")
        assert loss.severity is LossSeverity.BLOCKER
        # the four evidence classes section 5.3 names explicitly MUST NOT survive this blocker:
        for claim in ("conditions", "selectivity", "kinetics", "hazard"):
            assert loss.blocks(claim), claim
        # ... nor the structure-level claims section 5.4 forbids a formula from making:
        for claim in ("structure-identity", "stereochemistry", "product-identity"):
            assert loss.blocks(claim), claim

    def test_a_non_affected_claim_is_not_blocked(self):
        loss = formula_reduction_loss("smiles:CCO", "C2H6O")
        assert not loss.blocks("atom-balance")  # formula balance survives a formula reduction

    def test_loss_record_validates_its_fields(self):
        with pytest.raises((ValueError, TypeError)):
            IdentityLoss(IDENTITY_LOSS_SCHEMA, "", "in", "out", "why", (), LossSeverity.WARNING)
        with pytest.raises(ValueError):
            # affected_claims must be canonically sorted
            IdentityLoss(IDENTITY_LOSS_SCHEMA, "f", "in", "out", "why", ("b", "a"), LossSeverity.BLOCKER)

    def test_loss_digest_is_stable(self):
        a = formula_reduction_loss("smiles:CCO", "C2H6O").digest
        b = formula_reduction_loss("smiles:CCO", "C2H6O").digest
        assert a == b


class TestLayeredIdentityValidation:
    def test_cannot_claim_a_layer_finer_than_known(self):
        with pytest.raises(ValueError):
            LayeredIdentity(
                "smartchem.identity/layered-identity-v1alpha1",
                MatchLayer.FORMULA,  # claims to only know FORMULA ...
                "x",
                ((MatchLayer.CONSTITUTION.value, "d"),),  # ... but carries a CONSTITUTION digest
            )

    def test_known_layer_must_be_present(self):
        with pytest.raises(ValueError):
            LayeredIdentity(
                "smartchem.identity/layered-identity-v1alpha1",
                MatchLayer.CONSTITUTION,
                "x",
                ((MatchLayer.FORMULA.value, "d"),),  # known_layer CONSTITUTION absent
            )


class TestDecompileSmilesLossIsTyped:
    def test_smiles_decompile_renders_the_typed_blocker_loss(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = main(["decompile", "CC(=O)Nc1ccc(O)cc1", "--smiles"])
        text = out.getvalue()
        assert code == 0
        assert "IDENTITY LOSS [BLOCKER]" in text
        assert "C8H9NO2" in text
        assert "selectivity" in text and "hazard" in text  # the affected claims are surfaced


class TestRedTeamRegressions:
    """Each pins a defect the CLI-JSON-01/ID-LAYER-01 red-team (workflow wkphhybxf) surfaced and I folded."""

    def test_F3_formula_layer_carries_total_charge(self):
        # a charged species and its neutral namesake differ at FORMULA (section 5.1: "counts + total charge"), and
        # the FORMULA digest is congruent with of_formula of the TRUE charged formula, not a charge-stripped one.
        from smartchem.category import Molecule
        nh4_plus = parse_smiles("[NH4+]")
        nh4_neutral = Molecule(nh4_plus.atoms, nh4_plus.bonds, 0)
        a = LayeredIdentity.of_molecule(nh4_plus)
        b = LayeredIdentity.of_molecule(nh4_neutral)
        assert same_identity_at(a, b, MatchLayer.FORMULA) is False
        assert a.digest_at(MatchLayer.FORMULA) == ChemicalIdentity.of_formula(
            Formula.of({"N": 1, "H": 4}, 1)
        ).identity_digest

    def test_F3_neutral_formula_congruence_preserved(self):
        li = LayeredIdentity.of_molecule(parse_smiles("CCO"))
        assert li.digest_at(MatchLayer.FORMULA) == ChemicalIdentity.of_formula(
            Formula.of({"C": 2, "H": 6, "O": 1}, 0)
        ).identity_digest

    def test_F6_a_blocker_that_blocks_nothing_is_rejected(self):
        # a BLOCKER with an empty affected_claims blocks nothing -- the vacuous-guard fail-open. Reject it.
        with pytest.raises(ValueError):
            IdentityLoss(IDENTITY_LOSS_SCHEMA, "f", "in", "out", "why", (), LossSeverity.BLOCKER)
        with pytest.raises(ValueError):
            formula_reduction_loss("smiles:CCO", "C2H6O", affected_claims=())
        # a WARNING with no claims is still constructible (it warns, it does not block).
        IdentityLoss(IDENTITY_LOSS_SCHEMA, "f", "in", "out", "why", (), LossSeverity.WARNING)

    def test_summary_is_one_line_and_names_severity_and_claims(self):
        loss = formula_reduction_loss("smiles:CCO", "C2H6O")
        s = loss.summary()
        assert "\n" not in s
        assert "[BLOCKER]" in s and "hazard" in s and "C2H6O" in s


# == ID-LAYER-02: MatchLayer wired into the service IdentityPolicy =================================================


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestIdentityPolicyCarriesAMatchLayer:
    def test_default_layers_are_the_engine_honored_ones(self):
        # recompile's structural engine matches at CONSTITUTION; a formula descent at FORMULA. The builders default
        # to exactly the layer each engine can honestly honor.
        assert build_recompile_request("water").identity_policy.match_layer is MatchLayer.CONSTITUTION
        assert build_decompile_request("H2O").identity_policy.match_layer is MatchLayer.FORMULA

    def test_match_layer_rides_the_semantic_digest(self):
        base = build_recompile_request("name:water")
        moved = build_recompile_request("name:water", match_layer=MatchLayer.CONFIGURATION)
        assert base.semantic_digest != moved.semantic_digest  # the layer is part of the SEARCH identity

    def test_policy_validates_its_layer(self):
        with pytest.raises(TypeError, match="match_layer must be a MatchLayer"):
            IdentityPolicy("DEFAULT", "CONSTITUTION")  # a string, not a MatchLayer

    def test_request_round_trip_preserves_the_layer(self):
        req = build_recompile_request("name:water", match_layer=MatchLayer.ISOTOPIC)
        back = deserialize_request(serialize_request(req))
        assert back.identity_policy.match_layer is MatchLayer.ISOTOPIC
        assert back.digest == req.digest

    def test_cannot_pass_both_identity_policy_and_match_layer(self):
        with pytest.raises(ValueError, match="either identity_policy or match_layer"):
            build_recompile_request(
                "name:water", identity_policy=IdentityPolicy(), match_layer=MatchLayer.FORMULA
            )


class TestUnhonorableLayerIsRefusedNotFaked:
    """The section-5.4 enforcement: the engine only matches at a layer it can HONESTLY honor; anything else is a
    REFUSED response (exit 5, REFUSED_IDENTITY_UNSUPPORTED), never a silent match at a coarser layer."""

    @pytest.mark.parametrize("layer", [MatchLayer.CONFIGURATION, MatchLayer.ISOTOPIC])
    def test_recompile_refuses_a_finer_layer_not_yet_honored_in_the_search(self, layer):
        # ID-STEREO-02: the identity model now PERCEIVES configuration/isotopic (of_molecule with features gives
        # enantiomers distinct identities), but the recompile SEARCH still matches terminals at CONSTITUTION, so a
        # finer match is refused -- honestly named as perceivable-but-not-wired-into-search, NEVER "unbuilt".
        resp = run_compilation(build_recompile_request("water", match_layer=layer))
        assert resp.outcome is ResponseOutcome.REFUSED
        assert resp.exit_code == 5
        assert resp.standard_status == "REFUSED_IDENTITY_UNSUPPORTED"
        reason = resp.diagnostics[0]
        assert "can perceive the finer" in reason and layer.value in reason
        assert "unbuilt" not in reason and "ID-STEREO-02" in reason      # the lie is gone; the honest wall is named

    def test_recompile_refuses_the_coarser_formula_layer_per_5_4(self):
        # a structure search must not terminate on formula-only equality (section 5.4 / gate G3).
        resp = run_compilation(build_recompile_request("water", match_layer=MatchLayer.FORMULA))
        assert resp.outcome is ResponseOutcome.REFUSED
        assert resp.exit_code == 5
        assert "5.4" in resp.diagnostics[0]

    @pytest.mark.parametrize("layer", [MatchLayer.CONSTITUTION, MatchLayer.CONFIGURATION, MatchLayer.ISOTOPIC])
    def test_decompile_refuses_any_layer_finer_than_formula(self, layer):
        resp = run_compilation(build_decompile_request("H2O", match_layer=layer))
        assert resp.outcome is ResponseOutcome.REFUSED
        assert resp.exit_code == 5

    def test_decompile_constitution_refusal_reason_is_honest_not_fabricated(self):
        # red-team IDLAYER02-01: a formula descent PERCEIVES constitution in principle (it is the recompile-honored
        # layer), so the refusal must NOT falsely blame "unbuilt stereo/isotope perception". The honest reason is
        # that a formula descent constructs no structure to match at constitution (section 5.4).
        reason = run_compilation(build_decompile_request("H2O", match_layer=MatchLayer.CONSTITUTION)).diagnostics[0]
        assert "perception is unbuilt" not in reason
        assert "constructs no" in reason and "5.4" in reason

    @pytest.mark.parametrize("layer", [MatchLayer.CONFIGURATION, MatchLayer.ISOTOPIC])
    def test_no_refusal_reason_still_claims_perception_is_unbuilt(self, layer):
        # ID-STEREO-02 built configuration/isotope perception, so NO refusal may still say "unbuilt" (that is now a
        # lie).  The honest reason differs by operation: a recompile names "perceivable but not honored in the search";
        # a decompile names "constructs no structure" (a formula descent builds nothing to match at any finer layer).
        recompile_reason = run_compilation(build_recompile_request("water", match_layer=layer)).diagnostics[0]
        assert "unbuilt" not in recompile_reason
        assert "can perceive the finer" in recompile_reason and "ID-STEREO-02" in recompile_reason
        decompile_reason = run_compilation(build_decompile_request("H2O", match_layer=layer)).diagnostics[0]
        assert "unbuilt" not in decompile_reason
        assert "constructs no" in decompile_reason and "5.4" in decompile_reason

    def test_the_honored_layer_runs(self):
        assert run_compilation(build_recompile_request("water")).outcome is not ResponseOutcome.REFUSED
        assert run_compilation(build_decompile_request("H2O")).outcome is not ResponseOutcome.REFUSED

    def test_refusal_is_alias_independent(self):
        # the refusal is a function of the SEARCH identity: two requests with equal semantic_digest refuse identically.
        a = run_compilation(build_recompile_request("water", match_layer=MatchLayer.CONFIGURATION))
        b = run_compilation(build_recompile_request("water", match_layer=MatchLayer.CONFIGURATION))
        assert a.result_digest == b.result_digest


class TestMatchLayerCLI:
    def test_flag_default_runs_at_constitution(self):
        code, out, _ = _cli(["recompile", "water", "--json"])
        assert code == 0
        assert json.loads(out)["request"]["identity_policy"]["match_layer"] == "CONSTITUTION"

    def test_flag_declares_the_layer_in_the_emitted_request(self):
        code, out, _ = _cli(["recompile", "water", "--match-layer", "configuration", "--emit-request"])
        assert code == 0  # emit does not run the search, so it does not refuse
        assert json.loads(out)["identity_policy"]["match_layer"] == "CONFIGURATION"

    def test_flag_finer_layer_refused_exit_5(self):
        # the human render (incl. the refusal outcome + diagnostics) goes to stdout; the exit code is 5.  ID-STEREO-02:
        # the reason names configuration as perceivable-but-not-honored-in-the-search, never "cannot perceive".
        code, out, _ = _cli(["recompile", "water", "--match-layer", "configuration"])
        assert code == 5
        assert "REFUSED" in out and "can perceive the finer" in out

    def test_human_render_surfaces_the_match_layer(self):
        _, out, _ = _cli(["recompile", "water"])
        assert "identity match layer: CONSTITUTION" in out
