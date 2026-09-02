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
from smartchem.smiles import (
    SmilesError,
    SmilesFeatures,
    isotope_refined_key,
    parse_smiles,
    parse_smiles_features,
)


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


class TestSoundIsotopePerception:
    """ID-STEREO-01 PERCEPTION half: a canonical, presentation-invariant isotope-refined-constitution key.

    The detection arm records the DROP as a blocker; this key perceives the isotope PLACEMENT soundly, so two
    isotopologues are distinguishable (not merely both-blocked).  It rides the proven graph canonicaliser over an
    isotope-coloured copy of the graph, so its relabel-invariance is the canonicaliser's, not a new bespoke proof.
    """

    def test_relabel_invariance_two_spellings_of_one_isotopologue_agree(self):
        # acetic-acid-2-13C written two ways -> ONE key (presentation-invariant).
        assert isotope_refined_key("[13CH3]C(=O)O") == isotope_refined_key("OC(=O)[13CH3]")

    def test_symmetric_position_invariance(self):
        # a label on EITHER of two symmetric ends (propane C1/C3) is ONE identity -- the canonicaliser minimises
        # over the symmetry, so which symmetric site was labelled cannot leak into the key.
        assert isotope_refined_key("[13CH3]CC") == isotope_refined_key("CC[13CH3]")

    def test_positional_distinction(self):
        # a label at a DIFFERENT (non-symmetric) site is a DIFFERENT isotopologue.
        assert isotope_refined_key("[13CH3]C(=O)O") != isotope_refined_key("C[13C](=O)O")
        assert isotope_refined_key("[13CH3]CC") != isotope_refined_key("C[13CH2]C")

    def test_labelled_differs_from_unlabelled_but_shares_constitution(self):
        labelled, plain = "[13CH3]C(=O)O", "CC(=O)O"
        assert isotope_refined_key(labelled) != isotope_refined_key(plain)      # finer than constitution
        # ... yet the CONSTITUTION is identical (the key strictly refines it, never forks it)
        assert canonical_digest(parse_smiles(labelled).canonical()) == canonical_digest(parse_smiles(plain).canonical())

    def test_aromatic_isotopologue_is_resonance_and_spelling_invariant(self):
        # a ring-bearing input: two spellings of unlabelled toluene collapse (resonance-canonical), and a methyl
        # label makes a distinct, stable key.
        assert isotope_refined_key("Cc1ccccc1") == isotope_refined_key("c1ccccc1C")
        assert isotope_refined_key("[13CH3]c1ccccc1") != isotope_refined_key("Cc1ccccc1")

    def test_fused_benzenoid_does_not_split_across_aromatic_vs_kekule_spelling(self):
        # ID-STEREO-01-SPLIT-KEKULE (red-team, HIGH): a fused benzenoid (naphthalene) has non-isomorphic Kekule
        # structures; the key MUST commit to the SAME resonance structure the constitution does, so an aromatic
        # spelling and an explicit-Kekule spelling of ONE species share ONE key (never split into two identities).
        aromatic, kekule = "c1ccc2ccccc2c1", "C1=CC2=C(C=C1)C=CC=C2"
        assert canonical_digest(parse_smiles(aromatic).canonical()) == canonical_digest(parse_smiles(kekule).canonical())
        assert isotope_refined_key(aromatic) == isotope_refined_key(kekule)
        # ... and a labelled aromatic ring is likewise spelling-invariant
        assert isotope_refined_key("[13CH3]c1ccccc1") == isotope_refined_key("[13CH3]C1=CC=CC=C1")

    def test_deuterium_bracket_hydrogen_is_perceived(self):
        # [2H] (deuterium) is an isotope-labelled hydrogen; heavy-water D2O differs from H2O at the isotope layer.
        assert isotope_refined_key("[2H]O[2H]") != isotope_refined_key("O")

    def test_multiple_labels_distinguish_from_single(self):
        assert isotope_refined_key("[13CH3][13CH3]") != isotope_refined_key("[13CH3]C")

    def test_features_carry_the_isotopic_digest_only_when_labelled(self):
        _m, labelled = parse_smiles_features("[13CH3]C(=O)O")
        _m2, plain = parse_smiles_features("CC(=O)O")
        assert labelled.isotopic_digest is not None and labelled.isotopic_digest == isotope_refined_key("[13CH3]C(=O)O")
        assert plain.isotopic_digest is None

    def test_honest_boundary_key_is_modulo_stereochemistry(self):
        # DOCUMENTED boundary (never faked): the key is the isotope refinement of CONSTITUTION, not the lattice
        # ISOTOPIC slot -- it does NOT encode chirality, so two enantiomeric isotopologues share it.  Filling the
        # MatchLayer ISOTOPIC slot needs sound stereo (CIP) perception, which stays the ID-STEREO-01 deferral.
        assert isotope_refined_key("[13CH3][C@H](F)Cl") == isotope_refined_key("[13CH3][C@@H](F)Cl")

    def test_malformed_smiles_is_refused_loudly(self):
        with pytest.raises(SmilesError):
            isotope_refined_key("[Na+].[Cl-]")   # disconnected -> loud, never a silent partial key


class TestSmilesFeaturesValue:
    def test_features_is_a_frozen_value(self):
        f = SmilesFeatures((13,), True, False, 0, 0)
        with pytest.raises(Exception):
            f.isotopes = (14,)  # frozen
