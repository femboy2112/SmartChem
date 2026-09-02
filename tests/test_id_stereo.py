"""ID-STEREO-01 -- stereo/isotope/local-charge loss is never silent.

The constitution-only ``Molecule`` cannot represent a stereocentre, an isotope label, or a net-neutral internal
charge separation, so an enantiomer, an isotopologue and a zwitterion all collapse to the same graph as their flat
analogue.  That collapse is CORRECT at the constitution layer -- but section 5.3 forbids it being SILENT.  These
tests prove the parse boundary DETECTS each dropped feature and records it as a typed BLOCKER
(:class:`~smartchem.identity.IdentityLoss`), so the loss-bearing input is distinguishable from the flat one.  The
ENFORCEMENT that no feature-dependent sourced claim survives (the "bite") is EVD-KEY-01, proven end-to-end in
tests/test_evd_key.py; here we prove only that the blocker is produced and ``is_blocked`` reports it.  Disconnected
salts stay a LOUD refusal (never a silent collision).  This is the standard's "record blocker" arm -- NOT faked
stereo/isotope PERCEPTION.
"""
from __future__ import annotations

import pytest

from smartchem.contracts import canonical_digest
from smartchem.identity import (
    IdentityLoss,
    LossSeverity,
    is_blocked,
    isotope_loss,
    local_charge_loss,
    representation_losses_for,
    stereo_loss,
)
from smartchem.identity_parse import InputKind
from smartchem.service import build_decompile_request, build_recompile_request, run_compilation
from smartchem.smiles import SmilesError, SmilesFeatures, parse_smiles, parse_smiles_features


class TestSmilesFeatureDetection:
    def test_isotope_label_is_captured_not_discarded(self):
        _mol, f = parse_smiles_features("[13CH4]")
        assert f.isotopes == (13,) and f.has_isotope

    def test_tetrahedral_chirality_is_captured(self):
        _mol, f = parse_smiles_features("[C@H](F)(Cl)Br")
        assert f.tetrahedral_stereo and f.has_stereo

    def test_double_bond_stereo_is_captured(self):
        _mol, f = parse_smiles_features("F/C=C/F")
        assert f.double_bond_stereo and f.has_stereo

    def test_double_bond_scan_is_conservative_by_design(self):
        # ID-STEREO-DBSTEREO-FALSEPOS (red-team, LOW): the '/'/'\' scan flags ANY directional marker -- it never
        # MISSES a declared one, but it does not perceive whether a real geometric isomer exists, so it may
        # over-flag a redundant directional bond.  That is fail-CLOSED (section 5.3) and intentional; pin it.
        assert parse_smiles_features("F\\C=C\\F")[1].double_bond_stereo   # backslash form also triggers
        # a molecule with NO directional marker is never flagged (no false stereo from a plain double bond)
        assert not parse_smiles_features("FC=CF")[1].double_bond_stereo

    def test_net_neutral_zwitterion_is_a_local_charge_structure(self):
        _mol, f = parse_smiles_features("[NH3+]CC(=O)[O-]")
        assert f.charged_atoms == 2 and f.net_charge == 0 and f.has_local_charge_structure

    def test_a_flat_neutral_unlabelled_molecule_declares_no_features(self):
        _mol, f = parse_smiles_features("FC(Cl)Br")
        assert not f.has_stereo and not f.has_isotope and not f.has_local_charge_structure

    def test_a_simple_monopole_ion_is_not_a_local_charge_structure(self):
        # a single charged atom whose charge IS the molecular total is recoverable from the scalar -- not a loss.
        _mol, f = parse_smiles_features("[OH-]")
        assert f.charged_atoms == 1 and f.net_charge == -1 and not f.has_local_charge_structure

    def test_feature_parse_and_plain_parse_agree_on_the_molecule(self):
        # parse_smiles_features must return the IDENTICAL Molecule parse_smiles does (one shared Kekulé path).
        for s in ("[C@H](F)(Cl)Br", "[13CH4]", "[NH3+]CC(=O)[O-]", "F/C=C/F", "c1ccccc1", "CC(=O)Nc1ccc(O)cc1"):
            m1 = parse_smiles(s)
            m2, _f = parse_smiles_features(s)
            assert canonical_digest(m1) == canonical_digest(m2), s

    def test_disconnected_salt_is_refused_loudly_never_silently_flattened(self):
        with pytest.raises(SmilesError):
            parse_smiles_features("[Na+].[Cl-]")


class TestRepresentationLosses:
    def test_stereo_loss_is_a_blocker_over_the_configuration_claims(self):
        loss = stereo_loss("smiles:[C@H](F)(Cl)Br")
        assert loss.severity is LossSeverity.BLOCKER
        for claim in ("selectivity", "kinetics", "conditions", "stereochemistry", "configuration-identity"):
            assert loss.blocks(claim), claim

    def test_stereo_loss_does_not_block_the_constitution_level_hazard_class(self):
        # a dropped stereocentre does not change the modeled (constitution-level) physical handling hazard;
        # blocking it would over-refuse a legitimate, gated handling claim (EVD-KEY-CLASSGAP-02 fold).
        assert not stereo_loss("smiles:[C@H](F)(Cl)Br").blocks("hazard")

    def test_isotope_loss_blocks_kinetics_but_not_selectivity(self):
        # a kinetic isotope effect is real; a 13C label does NOT change regiochemistry or bench conditions.
        loss = isotope_loss("[13CH4]", (13,))
        assert loss.blocks("kinetics") and loss.blocks("isotope-identity")
        assert not loss.blocks("selectivity") and not loss.blocks("conditions")

    def test_local_charge_loss_blocks_conditions_and_protonation_state(self):
        loss = local_charge_loss("[NH3+]CC(=O)[O-]")
        assert loss.blocks("conditions") and loss.blocks("protonation-state")

    def test_representation_losses_for_a_flat_molecule_is_empty_not_vacuous(self):
        _mol, f = parse_smiles_features("FC(Cl)Br")
        assert representation_losses_for("FC(Cl)Br", f) == ()

    def test_representation_losses_for_maps_every_present_feature(self):
        # a contrived SMILES with BOTH stereo kinds + an isotope
        _mol, f = parse_smiles_features("[13C@H](F)/C=C/Cl")
        losses = representation_losses_for("x", f)
        features = {loss.feature for loss in losses}
        assert "stereochemistry" in features and "isotope-labeling" in features
        # two distinct stereo losses (tetrahedral + double-bond) are not deduped away
        assert sum(1 for loss in losses if loss.feature == "stereochemistry") == 2

    def test_representation_losses_for_rejects_a_non_features_argument(self):
        with pytest.raises(TypeError):
            representation_losses_for("x", object())


class TestDoNotCollideWithSimplifiedAnalogues:
    """The acceptance: an enantiomer / isotopologue / zwitterion must NOT silently collide with its flat analogue."""

    def test_enantiomers_share_constitution_but_carry_a_distinguishing_blocker(self):
        left = parse_smiles("[C@H](F)(Cl)Br")
        right = parse_smiles("[C@@H](F)(Cl)Br")
        flat = parse_smiles("FC(Cl)Br")
        # correct AT constitution: all three ARE the same constitution
        assert canonical_digest(left) == canonical_digest(right) == canonical_digest(flat)
        # but the chiral inputs carry a stereo BLOCKER the flat one does not -- so they are NOT silently identical
        _m, chiral_f = parse_smiles_features("[C@H](F)(Cl)Br")
        _m2, flat_f = parse_smiles_features("FC(Cl)Br")
        chiral_losses = representation_losses_for("chiral", chiral_f)
        assert chiral_losses and is_blocked(chiral_losses, "stereochemistry")
        assert representation_losses_for("flat", flat_f) == ()

    def test_isotopologue_carries_an_isotope_blocker_the_unlabelled_form_lacks(self):
        _m, labelled = parse_smiles_features("[13CH4]")
        _m2, plain = parse_smiles_features("C")
        assert is_blocked(representation_losses_for("13C", labelled), "kinetics")
        assert representation_losses_for("C", plain) == ()

    def test_no_configuration_claim_survives_a_stereo_blocker(self):
        _m, f = parse_smiles_features("[C@H](F)(Cl)Br")
        losses = representation_losses_for("chiral", f)
        # every configuration-dependent claim is blocked -- section 5.3 fail-closed
        for claim in ("selectivity", "conditions", "kinetics", "configuration-identity"):
            assert is_blocked(losses, claim), claim


class TestServiceWiring:
    def test_recompile_chiral_target_carries_the_stereo_blocker_in_the_ir(self):
        resp = run_compilation(build_recompile_request("smiles:[C@H](F)(Cl)Br", helper_reagents=("water",)))
        features = {loss.feature for loss in resp.identity_losses}
        assert "stereochemistry" in features
        assert is_blocked(resp.identity_losses, "selectivity")

    def test_recompile_flat_target_carries_no_finer_loss(self):
        resp = run_compilation(build_recompile_request("smiles:FC(Cl)Br", helper_reagents=("water",)))
        assert resp.identity_losses == ()

    def test_recompile_chiral_and_flat_have_distinct_ir_digests(self):
        chiral = run_compilation(build_recompile_request("smiles:[C@H](F)(Cl)Br", helper_reagents=("water",)))
        flat = run_compilation(build_recompile_request("smiles:FC(Cl)Br", helper_reagents=("water",)))
        # same constitution target, but the loss rides the IR digest, so the two IRs are distinct values
        assert chiral.compilation_ir is not None and flat.compilation_ir is not None
        assert chiral.compilation_ir.digest != flat.compilation_ir.digest

    def test_decompile_isotope_smiles_carries_isotope_and_formula_blockers(self):
        resp = run_compilation(build_decompile_request("[13CH4]", input_kind=InputKind.SMILES))
        features = {loss.feature for loss in resp.identity_losses}
        assert "isotope-labeling" in features and "molecular-constitution" in features

    def test_decompile_zwitterion_smiles_carries_the_local_charge_blocker(self):
        resp = run_compilation(build_decompile_request("[NH3+]CC(=O)[O-]", input_kind=InputKind.SMILES))
        features = {loss.feature for loss in resp.identity_losses}
        assert "local-charge" in features
        assert is_blocked(resp.identity_losses, "protonation-state")

    def test_decompile_plain_formula_target_carries_no_loss(self):
        resp = run_compilation(build_decompile_request("CH4"))
        assert resp.identity_losses == ()

    def test_recompile_losses_round_trip_through_serialization(self):
        from smartchem.service import deserialize_response, serialize_response
        resp = run_compilation(build_recompile_request("smiles:[C@H](F)(Cl)Br", helper_reagents=("water",)))
        back = deserialize_response(serialize_response(resp))
        assert {loss.feature for loss in back.identity_losses} == {loss.feature for loss in resp.identity_losses}
        assert all(type(loss) is IdentityLoss for loss in back.identity_losses)


class TestSmilesFeaturesValue:
    def test_features_is_a_frozen_value(self):
        f = SmilesFeatures((13,), True, False, 0, 0)
        with pytest.raises(Exception):
            f.isotopes = (14,)  # frozen
