"""Calibration + structure tests for the Benson group-additivity derivation engine (rung 2).

The INSTRUMENT RULE made permanent: the estimator must recover KNOWN gas-phase molecular ΔfH°/S° before its
novel outputs (e.g. paracetamol) are believed.  The calibration anchors below are SOURCED gas-phase values
read from the NIST Chemistry WebBook (ΔfH°) and NIST CCCBDB (S°, citing the Gurvich/Veyts/Alcock 1989 and
Frenkel/Marsh/TRC 1994 critical compilations) -- an entirely SEPARATE data lineage from the RMG-database
Benson group values the engine sums.  So an agreement here is a genuine two-blind-path cross-validation
(the group values and the molecular values never saw each other), not one source nodding at itself.
"""
from __future__ import annotations

import math

import pytest

from smartchem.contracts import canonical_digest
from smartchem.data.thermo import DEFAULT_THERMO, ThermoRef
from smartchem.data.thermo_groups import (
    BENSON_GROUPS,
    R_J_PER_MOL_K,
    assign_groups,
    estimate_thermo,
)
from smartchem.experiment.feasibility import FeasibilityDirection, FeasibilityGrade, feasibility_of_step, resolve_thermo
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

# (name, SMILES, ΔfH°(g) kJ/mol, S°(g) J/mol/K) -- SOURCED anchors, see module docstring for provenance.
# ΔfH°: NIST WebBook; S°: NIST CCCBDB (Gurvich 1989 / Frenkel-Marsh TRC 1994).
CALIBRATION = [
    ("ethane", "CC", -84.0, 229.16),          # ΔfH Manion 2002; S Gurvich 1989
    ("propane", "CCC", -104.7, 270.31),        # ΔfH Pittam&Pilcher 1972; S TRC 1994
    ("n-butane", "CCCC", -125.6, 310.02),      # ΔfH Pittam&Pilcher 1972; S TRC 1994
    ("benzene", "c1ccccc1", 82.9, 269.30),     # ΔfH Roux&Temprado 2008; S TRC 1994
    ("methanol", "CO", -201.1, 239.87),        # ΔfH Green 1960; S Gurvich 1989
    ("ethanol", "CCO", -234.7, 281.62),        # ΔfH Chao&Rossini 1965; S Gurvich 1989
    ("acetone", "CC(=O)C", -217.1, 295.46),    # ΔfH Chao&Zwolinski 1976; S TRC 1994
    ("acetaldehyde", "CC=O", -170.7, 263.95),  # ΔfH Wiberg&Crocker 1991; S TRC 1997
    ("dimethyl ether", "COC", -184.1, 267.34), # ΔfH Pilcher&Pell 1964; S TRC 1994
    ("diethyl ether", "CCOCC", -252.2, 342.67),# ΔfH Pilcher&Skinner 1963; S TRC 1994
    ("propene", "CC=C", 20.41, 266.73),        # ΔfH Furuyama&Golden 1969; S TRC 1994
]

#: Tolerances: tight enough to prove the instrument is accurate (not merely honestly banded), loose enough
#: for the ~few-kJ inherent error of an additivity scheme.  Every anchor clears these with >=1.5 margin.
DHF_TOL_KJ = 6.0
S_TOL_J = 6.0


class TestTheInstrumentReadsTrue:
    """Calibration: the group sum + symmetry correction recovers each SOURCED molecular value within tol."""

    @pytest.mark.parametrize("name,smiles,dhf_known,s_known", CALIBRATION, ids=[c[0] for c in CALIBRATION])
    def test_recovers_sourced_gas_thermo(self, name, smiles, dhf_known, s_known):
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None, f"{name} should be derivable"
        assert est.phase == "gas"
        assert abs(est.dhf_kj_per_mol - dhf_known) <= DHF_TOL_KJ, (
            f"{name}: ΔfH° {est.dhf_kj_per_mol} vs sourced {dhf_known}"
        )
        assert abs(est.s_j_per_mol_k - s_known) <= S_TOL_J, (
            f"{name}: S° {est.s_j_per_mol_k} vs sourced {s_known}"
        )
        # the true value must also lie within the estimate's own reported band (honest self-consistency)
        assert abs(est.dhf_kj_per_mol - dhf_known) <= est.dhf_uncertainty_kj
        assert abs(est.s_j_per_mol_k - s_known) <= est.s_uncertainty_j_per_k


#: Halogen + sulfur anchors -- an INDEPENDENT lineage (NIST WebBook / CCCBDB) from the RMG group values, so
#: agreement is a two-blind-path cross-validation (the sulfur groups are a Vandeputte/Gillis quantum refit,
#: the halogen groups G4-library ML fits; neither saw these molecular values).  ΔfH° recovers tightly; the S°
#: residual is up to ~6 J/mol/K on the HIGH-SYMMETRY halomethanes -- that is the KNOWN improper-mirror σ
#: factor-2 residual the code folds into the band (CCl4/CF4 have graph |Aut|=24 vs proper σ_ext=12), not error.
HALOGEN_SULFUR_CALIBRATION = [
    ("chloromethane", "CCl", -83.68, 234.36),      # ΔfH/S Chase 1998 (JANAF)
    ("dichloromethane", "ClCCl", -95.52, 270.28),  # Chase 1998
    ("chloroform", "ClC(Cl)Cl", -103.18, 295.61),  # Chase 1998
    ("carbon tetrachloride", "ClC(Cl)(Cl)Cl", -100.0, 309.65),  # avg-of-6 / Chase 1998
    ("fluoromethane", "CF", -234.30, 222.84),      # Chase 1998
    ("tetrafluoromethane", "FC(F)(F)F", -930.0, 261.41),  # avg-of-12 / Chase 1998
    ("methanethiol", "CS", -22.84, 255.14),        # ΔfH Good 1961; S webbook
    ("ethanethiol", "CCS", -46.00, 296.25),        # TRC 1994
    ("1-propanethiol", "CCCS", -68.58, 336.55),    # ΔfH webbook; S TRC
    ("dimethyl sulfide", "CSC", -37.50, 285.96),   # ΔfH webbook; S TRC
    ("dimethyl disulfide", "CSSC", -24.10, 336.80),  # ΔfH webbook; S TRC
]


class TestHalogenAndSulfurReadTrue:
    """Rung B families 4a/4c: the halogen + sulfur groups recover independent NIST/CCCBDB anchors.

    ΔfH° within 4 kJ/mol; S° within 7 J/mol/K (the extra room over the alkane calibration is the improper-
    mirror σ residual on the high-symmetry halomethanes, folded honestly into every estimate's own band)."""

    @pytest.mark.parametrize("name,smiles,dhf_known,s_known", HALOGEN_SULFUR_CALIBRATION,
                             ids=[c[0] for c in HALOGEN_SULFUR_CALIBRATION])
    def test_recovers_sourced_gas_thermo(self, name, smiles, dhf_known, s_known):
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None, f"{name} should be derivable"
        assert abs(est.dhf_kj_per_mol - dhf_known) <= 4.0, (
            f"{name}: ΔfH° {est.dhf_kj_per_mol} vs sourced {dhf_known}"
        )
        assert abs(est.s_j_per_mol_k - s_known) <= 7.0, (
            f"{name}: S° {est.s_j_per_mol_k} vs sourced {s_known}"
        )
        # the two blind paths must agree within the estimate's OWN reported band (honest self-consistency)
        assert abs(est.dhf_kj_per_mol - dhf_known) <= est.dhf_uncertainty_kj
        assert abs(est.s_j_per_mol_k - s_known) <= est.s_uncertainty_j_per_k

    @pytest.mark.parametrize("name,smiles,dhf_known,s_known", [
        ("chloroethane", "CCCl", -112.0, 275.89),          # ΔfH avg-of-6; S° TRC 1994 (CCCBDB)
        ("1,2-dichloroethane", "ClCCCl", -132.0, 305.96),  # ΔfH Manion 2002; S° TRC 1994 (CCCBDB)
    ])
    def test_flexible_halide_conformer_deficit_is_banded_not_hidden(self, name, smiles, dhf_known, s_known):
        # RED-TEAM (verified against sourced TRC S°): a FLEXIBLE halide's single-conformer G4 group entropy
        # systematically UNDER-predicts S° by the internal-rotation/gauche entropy -- one-directional, and
        # correlated across repeated halide carbons (chloroethane -8.9, 1,2-DCE -13.9 J/mol/K).  It must stay
        # INSIDE the (band-overridden) uncertainty, never a confident-wrong-answer.  Tests where the groups were
        # NOT fit (the rigid-halomethane calibration is a mirror otherwise).
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None
        assert abs(est.dhf_kj_per_mol - dhf_known) <= est.dhf_uncertainty_kj  # ΔfH within band
        s_residual = est.s_j_per_mol_k - s_known
        assert s_residual < 0.0, f"{name}: the conformer deficit is under-prediction (S° too low), not random"
        assert abs(s_residual) <= est.s_uncertainty_j_per_k, (
            f"{name}: S° deficit {s_residual:.1f} not covered by the band ±{est.s_uncertainty_j_per_k} "
            f"-- the flexible-halide band override must bracket the conformer entropy"
        )

    def test_iodine_tertiary_placeholder_zero_entropy_is_refused(self):
        # Cs-CCCI carried a bare S298=0 placeholder in RMG; it must NOT be stored (never a fabricated zero).
        # tert-butyl iodide's central carbon would need C-(C)3(I); its absence -> loud off-coverage, not a zero.
        from smartchem.data.thermo_groups import _GROUP_BY_LABEL
        assert "C-(C)3(I)" not in _GROUP_BY_LABEL
        assert estimate_thermo(parse_smiles("CC(C)(C)I")) is None  # tert-butyl iodide -> off-coverage

    def test_halogen_is_a_ligand_never_a_centre(self):
        # a halogen contributes only to its carbon's label; it emits no group of its own (like H)
        assert assign_groups(parse_smiles("CCl")) == ("C-(Cl)(H)3",)
        assert assign_groups(parse_smiles("ClC(Cl)(Cl)Cl")) == ("C-(Cl)4",)


class TestGroupAssignment:
    """The structural decomposition into canonical Benson labels (independent of the numeric values)."""

    def test_ethane_is_two_primary_methyls(self):
        assert assign_groups(parse_smiles("CC")) == ("C-(C)(H)3", "C-(C)(H)3")

    def test_benzene_is_six_aromatic_ch(self):
        assert assign_groups(parse_smiles("c1ccccc1")) == ("CB-(H)",) * 6

    def test_acetone_absorbs_the_carbonyl_oxygen(self):
        # the =O is folded into the CO group, NOT emitted as its own O group
        groups = assign_groups(parse_smiles("CC(=O)C"))
        assert sorted(groups) == ["C-(CO)(H)3", "C-(CO)(H)3", "CO-(C)2"]

    def test_paracetamol_decomposes_exactly(self):
        groups = assign_groups(parse_smiles("CC(=O)Nc1ccc(O)cc1"))
        assert sorted(groups) == sorted((
            "C-(CO)(H)3", "CO-(C)(N)", "N-(CB)(CO)(H)",
            "CB-(H)", "CB-(H)", "CB-(H)", "CB-(H)", "CB-(N)", "CB-(O)", "O-(CB)(H)",
        ))


class TestOffCoverageIsALoudNone:
    """The engine returns None (never a fabricated / strain-blind number) outside its sourced coverage."""

    @pytest.mark.parametrize("smiles", ["C1CCCCCC1", "C1CCOCC1", "C1CCNCC1", "C1CCC2CCCCC2C1"])
    def test_rings_without_a_sourced_correction_refused(self, smiles):
        # cycloheptane (7-ring), oxane (6-ring O), piperidine (N ring), decalin (fused) have NO sourced strain
        # correction -> off-coverage, never a strain-blind estimate.  (The covered rings derive; see below.)
        assert estimate_thermo(parse_smiles(smiles)) is None
        assert assign_groups(parse_smiles(smiles)) is None

    def test_non_covered_element_refused(self):
        # thiols/sulfides + F/Cl/Br/I are NOW covered (sulfur + halogen rungs), but phosphorus has no
        # independent NIST calibration anchor so it stays a deferred, loud None -- never a fabricated number.
        assert estimate_thermo(parse_smiles("CP(C)C")) is None   # trimethylphosphine
        assert assign_groups(parse_smiles("CP")) is None          # methylphosphine

    def test_oxidised_sulfur_refused(self):
        # a divalent thiol/sulfide derives, but an OXIDISED sulfur (S=O of a sulfoxide/sulfone) is off-coverage
        # and must be refused EXPLICITLY -- its =O would otherwise be silently absorbed like a carbonyl and the
        # S mis-read as a plain sulfide (a confident wrong answer).  The _center_type "Sx" guard prevents that.
        assert estimate_thermo(parse_smiles("CS(=O)C")) is None    # dimethyl sulfoxide
        assert estimate_thermo(parse_smiles("CS(=O)(=O)C")) is None  # dimethyl sulfone

    def test_uncovered_functional_group_refused(self):
        # a nitrile's triple-bond carbon (Ct) and nitrile N have no sourced groups -> loud None (the nitrile
        # nitrogen needs second-nearest-neighbour keying the flat centre+direct-ligand scheme cannot express)
        assert estimate_thermo(parse_smiles("CC#N")) is None


class TestSymmetryNumber:
    """The σ used in S° = ΣS − R ln σ, validated where the physical value is unambiguous."""

    @pytest.mark.parametrize("smiles,sigma", [
        ("CC", 18), ("CCC", 18), ("c1ccccc1", 12), ("CO", 3), ("CC(=O)C", 18), ("COC", 18), ("CCO", 3),
    ])
    def test_symmetry_number(self, smiles, sigma):
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None and est.symmetry_number == sigma


class TestSymmetryOvercountGuard:
    """Regression (adversarial red-team, HIGH): |Aut(heavy graph)| over-counts the rotational σ without
    bound when equivalent methyl tops at DIFFERENT branch points permute independently -- a wrong (too-low)
    S°, and it was graded DERIVED with no flag. The guard: such molecules grade PREDICTED with a band that
    honestly brackets the over-count; a single multi-methyl centre (factor-2 improper only) stays DERIVED."""

    @pytest.mark.parametrize("name,smiles,true_sigma", [
        ("2,2,3,3-tetramethylbutane", "CC(C)(C)C(C)(C)C", 4374),   # was factor 12, out of band
        ("2,2,4,4-tetramethylpentane", "CC(C)(C)CC(C)(C)C", 1458),  # was factor 36, out of band
        ("2,3-dimethylbutane", "CC(C)C(C)C", 162),
    ])
    def test_multi_branch_overcount_is_predicted_and_banded(self, name, smiles, true_sigma):
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None
        assert est.grade == "PREDICTED", f"{name} must not grade DERIVED on an unreliable σ"
        # the S° band must cover the actual over-count error R*ln(codeσ/trueσ)
        s_err = R_J_PER_MOL_K * math.log(est.symmetry_number / true_sigma)
        assert abs(s_err) <= est.s_uncertainty_j_per_k, (
            f"{name}: S° error {s_err:.1f} not covered by band ±{est.s_uncertainty_j_per_k}"
        )

    def test_single_multi_methyl_centre_stays_derived(self):
        # neopentane: one quaternary C, four methyls -> only the factor-2 improper case, error = R ln 2, in band
        est = estimate_thermo(parse_smiles("CC(C)(C)C"))
        assert est is not None and est.grade == "DERIVED"
        s_err = R_J_PER_MOL_K * math.log(est.symmetry_number / 972)  # true σ(neopentane) = 12 x 3^4
        assert abs(s_err) <= est.s_uncertainty_j_per_k

    # The internal-rotor σ residual (the last open σ question), PROVEN in-band on sourced anchors.  The observed
    # bias is one-directional (S° under-predicted): the graph over-counts σ_ext by the improper-mirror factor 2
    # (isobutane |Aut|=6 vs proper C3=3), which is folded into the band; the memo's "uncounted t-butyl internal
    # rotor" would push S° the OTHER way, so it partially cancels rather than compounds.  A correct σ_ext needs
    # 3-D (a 2-D graph cannot separate a proper C2 from a mirror), so the residual stays HONESTLY BANDED, never
    # hacked with a brittle divide-by-2 that would misfire on the proper-rotation cases (propane's σ_ext=2 IS a
    # real C2 and must not be halved).  Each anchor below is under-predicted by <= R ln 2 + group variance, in band.
    @pytest.mark.parametrize("name,smiles,s_known", [
        ("isobutane", "CC(C)C", 294.6), ("neopentane", "CC(C)(C)C", 306.4),
        ("2,2-dimethylbutane", "CCC(C)(C)C", 358.1), ("2-methylbutane", "CCC(C)C", 343.6),
    ])
    def test_branched_alkane_rotor_residual_is_one_directional_and_in_band(self, name, smiles, s_known):
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None
        residual = est.s_j_per_mol_k - s_known
        assert residual < 0.0, f"{name}: the σ-overcount bias is under-prediction (S° too low), not random"
        assert abs(residual) <= est.s_uncertainty_j_per_k, f"{name}: residual {residual:.1f} not in band"


class TestNoFabricatedZeroEntropy:
    """The S298=0 placeholder poisoning guard: a group whose RMG entry carried a placeholder zero entropy is
    never stored as a physical zero -- the aromatic amide N (paracetamol's) is ASSIGNED a real analogue S°."""

    def test_aromatic_amide_nitrogen_has_a_real_entropy(self):
        g = {b.label: b for b in BENSON_GROUPS}["N-(CB)(CO)(H)"]
        assert g.s_j_per_mol_k > 0.0  # not the placeholder zero
        # assigned from the aliphatic amide N-(C)(CO)(H) (its RMG S298 was a 0 placeholder, refused)
        aliphatic = {b.label: b for b in BENSON_GROUPS}["N-(C)(CO)(H)"]
        assert g.s_j_per_mol_k == pytest.approx(aliphatic.s_j_per_mol_k)

    def test_every_stored_group_entropy_is_a_real_number(self):
        # no group in the table carries an exact 0.0 J/mol/K (which in RMG marks a not-yet-fitted stub)
        assert all(b.s_j_per_mol_k != 0.0 for b in BENSON_GROUPS)


class TestParacetamolResolvesAsPredicted:
    """The litmus lift: paracetamol's gas-phase thermo, once UNKNOWN, is now a PREDICTED-with-band number."""

    def test_paracetamol_gas_estimate(self):
        est = estimate_thermo(parse_smiles("CC(=O)Nc1ccc(O)cc1"))
        assert est is not None
        assert est.grade == "PREDICTED"      # the amide N is ASSIGNED by analogy
        assert est.phase == "gas"
        assert est.dhf_uncertainty_kj > 0 and est.s_uncertainty_j_per_k > 0
        # sanity: gas ΔfH° ~ crystal (-410.4, Picciochi 2010) + ΔsubH (~117) ~ -293; the estimate is in range
        assert -360.0 < est.dhf_kj_per_mol < -260.0


class TestRung2FeasibilityLift:
    """resolve_thermo/feasibility now DERIVE a gas value on a sourced miss (default), the mission of rung 2."""

    def test_resolve_thermo_derives_on_miss(self):
        eth = parse_smiles("CCO")  # off-seed
        assert resolve_thermo(eth, DEFAULT_THERMO, derive=False) is None
        # condensed=False: the raw gas estimate, graded DERIVED
        gas = resolve_thermo(eth, DEFAULT_THERMO, derive=True, condensed=False)
        assert gas is not None and gas.grade == "DERIVED" and gas.phase == "gas"
        # condensed=True (default): ethanol has a sourced ΔvapH (rung C) -> corrected to its LIQUID standard
        # state, and a gas-estimate-plus-correction is a two-step estimate, so it grades PREDICTED.
        liq = resolve_thermo(eth, DEFAULT_THERMO, derive=True, condensed=True)
        assert liq is not None and liq.phase == "liquid" and liq.grade == "PREDICTED"
        assert liq.dhf_kj_per_mol < gas.dhf_kj_per_mol  # condensed is lower in enthalpy than gas

    def test_a_gas_isomerization_unknown_becomes_derived(self):
        # cyclopropane + H2 -> propane: cyclopropane is off-seed (UNKNOWN sourced-only); rung A derives it and
        # rung 2 wires it in, giving a real DERIVED ΔG -- strongly FAVORABLE as the +115 kJ ring strain is
        # released.  cyclopropane's groups + ring correction are all ESTABLISHED, propane too, H2 is seeded.
        step = ExperimentStep.assembling(
            parse_smiles("CCC"), (parse_smiles("C1CC1"), parse_smiles("[H][H]")), (parse_smiles("CCC"),)
        )
        assert feasibility_of_step(step, derive=False).direction is FeasibilityDirection.UNKNOWN
        f = feasibility_of_step(step, derive=True)
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.grade is FeasibilityGrade.DERIVED
        assert f.delta_g_kj < 0.0

    def test_phase_mix_caps_at_predicted_and_is_flagged(self):
        # ethylene hydration: C2H4 + H2O -> C2H6O.  Ethylene and ethanol are group-DERIVED (gas); seed water
        # is sourced (LIQUID).  Summing a derived-gas value with a sourced-condensed one omits the Δsub/Δvap
        # term, so the verdict must NOT grade DERIVED -- it is capped PREDICTED and the phase mix is flagged.
        step = ExperimentStep.assembling(
            parse_smiles("CCO"), (parse_smiles("C=C"), parse_smiles("O")), (parse_smiles("CCO"),)
        )
        f = feasibility_of_step(step, derive=True)
        assert f.grade is FeasibilityGrade.PREDICTED
        assert "PHASE-MIXED" in f.reason


class TestDigestStability:
    """Adding the compare=False grade field to ThermoRef must not move any fingerprint (the field trick)."""

    def test_grade_is_out_of_the_digest_and_equality(self):
        a = ThermoRef("H2O", "water", -285.83, 69.95, "liquid", "x")
        b = ThermoRef("H2O", "water", -285.83, 69.95, "liquid", "x", grade="DERIVED")
        assert canonical_digest(a) == canonical_digest(b)
        assert a == b


class TestEntropyFormula:
    """The S° correction is exactly Σ S(groups) − R ln σ (n_optical = 1)."""

    def test_methanol_entropy_is_group_sum_minus_r_ln_sigma(self):
        est = estimate_thermo(parse_smiles("CO"))
        groups = {b.label: b for b in BENSON_GROUPS}
        s_groups = groups["C-(O)(H)3"].s_j_per_mol_k + groups["O-(C)(H)"].s_j_per_mol_k
        expected = s_groups - R_J_PER_MOL_K * math.log(3)  # σ(methanol) = 3
        assert est.s_j_per_mol_k == pytest.approx(expected, abs=0.01)


# -- rung A (ring strain) + rung B (amine/acid/ester) calibration: SOURCED gas ΔfH° anchors ----------------
# (ring anchors: NIST WebBook / CCCBDB; amine/acid anchors: NIST/CCCBDB -- all CONFIRMED by the sourcing
#  workflow's independent verifier, and reconstructed by hand to the residuals in the module provenance.)
RUNG_AB = [
    ("cyclopropane", "C1CC1", 53.30), ("cyclobutane", "C1CCC1", 28.40),
    ("cyclopentane", "C1CCCC1", -76.40), ("cyclohexane", "C1CCCCC1", -123.10),
    ("oxirane", "C1CO1", -52.63), ("oxetane", "C1COC1", -80.54), ("thf", "C1CCOC1", -184.20),
    ("propylamine", "CCCN", -70.17), ("trimethylamine", "CN(C)C", -23.70), ("dimethylamine", "CNC", -19.00),
    ("acetic-acid", "CC(=O)O", -433.00), ("formic-acid", "OC=O", -378.60),
    ("methyl-acetate", "COC(=O)C", -410.00), ("ethyl-acetate", "CCOC(=O)C", -445.43),
    ("pyrrolidine", "C1CCNC1", -3.60), ("1,4-dioxane", "C1COCCO1", -315.30),  # saturated N/O hetero-rings
]


class TestRingAndFunctionalGroupRungs:
    """Rungs A + B: strained/aliphatic rings and amines/acids/esters now DERIVE within band of sourced data."""

    @pytest.mark.parametrize("name,smiles,dhf_known", RUNG_AB, ids=[c[0] for c in RUNG_AB])
    def test_derives_within_band(self, name, smiles, dhf_known):
        est = estimate_thermo(parse_smiles(smiles))
        assert est is not None, f"{name} should now be derivable"
        assert est.phase == "gas"
        assert abs(est.dhf_kj_per_mol - dhf_known) <= 8.0, f"{name}: {est.dhf_kj_per_mol} vs {dhf_known}"
        assert abs(est.dhf_kj_per_mol - dhf_known) <= est.dhf_uncertainty_kj  # within its own band

    def test_ring_strain_actually_moves_the_estimate(self):
        # cyclohexane's strain (~0) vs cyclopropane's (+115 kJ): without the correction cyclopropane would be
        # ~-62 (a bare propyl chain); the strain is what makes it correctly +53.
        cp = estimate_thermo(parse_smiles("C1CC1"))
        assert cp.dhf_kj_per_mol > 40.0  # strain-corrected, not the ~-62 chain estimate

    def test_saturated_hetero_rings_reproduce_their_anchor(self):
        # pyrrolidine + 1,4-dioxane derive from their gas anchors (both ΔfH° AND S° sourced), reproducing them
        # exactly by construction; pyrrolidine is PREDICTED (its N-(C)2(H) is ASSIGNED), dioxane DERIVED.
        pyr = estimate_thermo(parse_smiles("C1CCNC1"))
        assert abs(pyr.s_j_per_mol_k - 309.60) < 1.0 and pyr.grade == "PREDICTED"
        diox = estimate_thermo(parse_smiles("C1COCCO1"))
        assert abs(diox.dhf_kj_per_mol - (-315.30)) < 1.0 and abs(diox.s_j_per_mol_k - 299.91) < 1.0

    @pytest.mark.parametrize("name,smiles", [
        ("1,2-dioxane", "C1CCOOC1"), ("1,3-dioxane", "C1COCOC1"), ("1,3-dioxolane", "C1OCOC1"),
    ])
    def test_ring_isomer_does_not_borrow_a_different_arrangements_strain(self, name, smiles):
        # the necklace-signature key distinguishes ARRANGEMENT, not just the element multiset: 1,2-/1,3-dioxane
        # (same CCCCOO multiset as 1,4-dioxane, different O placement, different real strain) must stay a loud
        # None -- never borrow 1,4-dioxane's correction ([[a-reaction-key-by-formula-borrows-a-rate]] at the ring).
        assert estimate_thermo(parse_smiles(smiles)) is None


class TestEveryRingCorrectionIsReachable:
    """Guard against the dead-ring-correction class (red-team): a RING_STRAIN entry that no molecule can ever
    trigger is hollow coverage.  The cyclobutene/cyclopentene/cyclohexene corrections were removed because an
    in-ring alkene's allylic carbon needs a Cd-ligand group the table lacks -- assign_groups returns None first.
    Every surviving RING_STRAIN key must (a) have a live necklace pattern, and (b) actually fire on a real ring."""

    def test_ring_strain_and_patterns_are_a_bijection(self):
        from smartchem.data.thermo_groups import RING_STRAIN, _RING_SIG_TO_NAME
        assert set(_RING_SIG_TO_NAME.values()) == {r.key for r in RING_STRAIN}, (
            "a RING_STRAIN key with no pattern (or a pattern with no strain entry) is a dead/unreachable entry"
        )

    @pytest.mark.parametrize("key,smiles", [
        ("Cyclopropane", "C1CC1"), ("Cyclobutane", "C1CCC1"), ("Cyclopentane", "C1CCCC1"),
        ("Cyclohexane", "C1CCCCC1"), ("Ethylene_oxide", "C1CO1"), ("Oxetane", "C1COC1"),
        ("Tetrahydrofuran", "C1CCOC1"), ("Pyrrolidine", "C1CCNC1"), ("1,4-Dioxane", "C1COCCO1"),
    ])
    def test_each_ring_correction_actually_fires(self, key, smiles):
        # every parent ring must derive (proving its correction is reachable), and there must be a
        # representative SMILES for every RING_STRAIN key (the parametrize list is complete)
        from smartchem.data.thermo_groups import RING_STRAIN
        assert key in {r.key for r in RING_STRAIN}
        assert estimate_thermo(parse_smiles(smiles)) is not None, f"{key} correction is unreachable"


class TestLabelsAreCanonical:
    """Guard against the ester-oxygen bug class: every table key must be in canonical ligand order, else the
    label assign_groups PRODUCES will never match it and the group is silently unreachable (a dead entry)."""

    def test_every_group_label_is_canonically_ordered(self):
        import re
        from smartchem.data.thermo_groups import _LIGAND_PRIORITY
        for b in BENSON_GROUPS:
            m = re.match(r"^[A-Za-z]+-((?:\([A-Za-z]+\)\d*)+)$", b.label)
            assert m, f"unparseable group label {b.label!r}"
            heavy = [t for t in re.findall(r"\(([A-Za-z]+)\)(\d*)", m.group(1)) if t[0] != "H"]
            types = [t for t, _n in heavy]
            assert types == sorted(types, key=lambda t: (_LIGAND_PRIORITY[t], t)), (
                f"group label {b.label!r} has non-canonical ligand order -- assign_groups can never reach it"
            )


class TestRedTeamRegressions:
    """Four CONFIRMED defects from the adversarial red-team of the ring/group/phase rungs -- each now guarded."""

    def test_thf_ring_entropy_consistent_with_group_basis(self):
        # RMG's THF ring-S (fit to RMG's groups) gave S° 26 J too low with this engine's basis; the ring
        # corrections are now DERIVED from sourced molecular S° minus THIS engine's group sum -> exact anchor.
        est = estimate_thermo(parse_smiles("C1CCOC1"))
        assert abs(est.s_j_per_mol_k - 301.70) <= est.s_uncertainty_j_per_k
        assert abs(est.s_j_per_mol_k - 301.70) < 3.0  # reproduces the anchor

    @pytest.mark.parametrize("smiles", ["O=C1CC1", "O=C1CCC1", "O=C1CCCC1", "O=C1CCCCC1", "O=C1CCCO1"])
    def test_in_ring_carbonyl_is_off_coverage(self, smiles):
        # a ring with an in-ring carbonyl (ketone-ring / lactone) has a strain the parent-carbocycle
        # correction does not capture -- cyclopropanone was off by 76 kJ, sign-flipped, graded DERIVED.
        assert estimate_thermo(parse_smiles(smiles)) is None

    def test_tertiary_amine_is_predicted_with_a_covering_band(self):
        # triethylamine: the methyl-armed N-(C)3 fit is ~19 kJ off for ethyl arms; now PREDICTED with a band
        # (widened via the N group's per-group override) that covers the transfer error.
        est = estimate_thermo(parse_smiles("CCN(CC)CC"))
        assert est.grade == "PREDICTED"
        assert abs(est.dhf_kj_per_mol - (-92.9)) <= est.dhf_uncertainty_kj

    def test_primary_amine_still_derives_tightly(self):
        # the fix must not degrade primary amines (no N-(C)2/N-(C)3): propylamine stays DERIVED and tight
        est = estimate_thermo(parse_smiles("CCCN"))
        assert est.grade == "DERIVED" and abs(est.dhf_kj_per_mol - (-70.17)) < 3.0
