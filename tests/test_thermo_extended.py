"""M3 -- thermochemistry breadth: the extended sourced table unlocks M1/M2 beyond the seed.

The Instrument rule (E41 discipline): the extended data must recover a KNOWN reaction's ΔG before its novel
reach is believed. Ethanol combustion must recover the textbook ΔG° ~ -1325 kJ. These tests pin that, the
core "unlock" claim (a reaction UNKNOWN with the seed becomes DERIVED with the extended table), that every
value is genuinely sourced (NIST-cited, not recalled), formula uniqueness, and -- the honesty that matters
most -- that the paracetamol litmus gap is DOCUMENTED, not papered over with a fabricated entropy.
"""
from smartchem.data.thermo import DEFAULT_THERMO
from smartchem.data.thermo_extended import (
    EXTENDED_THERMO_GAPS,
    EXTENDED_THERMO_REFS,
    extended_thermo,
)
from smartchem.experiment.equilibrium import EquilibriumExtent, equilibrium_of_step
from smartchem.experiment.feasibility import (
    FeasibilityDirection,
    FeasibilityGrade,
    feasibility_of_step,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.smiles import parse_smiles

O2 = parse_smiles("O=O")
CO2 = parse_smiles("O=C=O")
H2O = parse_smiles("O")
H2 = parse_smiles("[H][H]")
ETHANOL = parse_smiles("CCO")
METHANOL = parse_smiles("CO")
ACETIC = parse_smiles("CC(=O)O")

EXT = extended_thermo()


def ethanol_combustion():   # C2H6O + 3 O2 -> 2 CO2 + 3 H2O
    return ExperimentStep.assembling(CO2, (ETHANOL, O2, O2, O2), (CO2, CO2, H2O, H2O, H2O))


def methanol_combustion():  # 2 CH4O + 3 O2 -> 2 CO2 + 4 H2O
    return ExperimentStep.assembling(
        CO2, (METHANOL, METHANOL, O2, O2, O2), (CO2, CO2, H2O, H2O, H2O, H2O)
    )


class TestInstrumentCalibration:
    """Recover a known combustion ΔG before believing the extended table's novel reach."""

    def test_ethanol_combustion_recovers_the_textbook_delta_g(self):
        f = feasibility_of_step(ethanol_combustion(), thermo=EXT)
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.grade is FeasibilityGrade.DERIVED
        assert abs(f.delta_g_kj - (-1325.0)) < 15.0     # textbook ethanol combustion ΔG° ~ -1325 kJ

    def test_methanol_combustion_is_strongly_favorable(self):
        f = feasibility_of_step(methanol_combustion(), thermo=EXT)
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.delta_g_kj < -1200.0                    # 2 mol methanol combustion, strongly exergonic


class TestTheUnlock:
    """The core M3 claim: a reaction UNKNOWN on the seed becomes DERIVED on the extended table."""

    def test_a_seed_unknown_reaction_becomes_derived(self):
        step = ethanol_combustion()
        # derive=False isolates the SOURCED coverage layer: rung-2 group additivity would otherwise DERIVE
        # ethanol's gas thermo by default (that lift is exercised in tests/test_thermo_groups.py).
        assert feasibility_of_step(step, derive=False).direction is FeasibilityDirection.UNKNOWN  # seed: no ethanol
        assert feasibility_of_step(step, thermo=EXT).direction is FeasibilityDirection.FAVORABLE

    def test_the_unlock_reaches_M2_equilibrium_too(self):
        e = equilibrium_of_step(ethanol_combustion(), thermo=EXT)
        assert e.extent is EquilibriumExtent.ESSENTIALLY_COMPLETE
        assert e.log10_k > 100.0                          # combustion K is astronomical

    def test_extended_table_still_covers_the_seed(self):
        # the extended table is ADDITIVE: methane (seed) is still resolvable through it
        CH4 = parse_smiles("C")
        burn = ExperimentStep.assembling(CO2, (CH4, O2, O2), (CO2, H2O, H2O))   # CH4 + 2O2 -> CO2 + 2H2O
        assert feasibility_of_step(burn, thermo=EXT).direction is FeasibilityDirection.FAVORABLE


class TestSourcingDiscipline:
    """Every value is genuinely sourced (NIST-cited, a named measurement), not recalled from memory."""

    def test_every_extended_record_names_a_real_source(self):
        for r in EXTENDED_THERMO_REFS:
            # a named U.S.-gov standard-reference lineage: NIST WebBook, or its NBS predecessor (the HNO3
            # pair is Wagman-1982/NBS via JPCRD -- the same body, an earlier compilation, not memory-recall)
            assert "NIST" in r.provenance or "NBS" in r.provenance
            assert any(ch.isdigit() for ch in r.provenance)   # carries a measurement year
            assert r.s_j_per_mol_k > 0                          # third law (also enforced at construction)

    def test_formulas_are_unique_so_formula_resolution_is_unambiguous(self):
        formulas = [r.formula for r in EXTENDED_THERMO_REFS]
        assert len(formulas) == len(set(formulas))
        # each resolves by formula alone through the extended table
        assert EXT.for_formula("C2H6O") is not None            # ethanol, the only C2H6O here
        assert EXT.for_formula("C6H6") is not None             # benzene

    def test_a_pinned_value_matches_what_was_verified(self):
        # locks the sourced value against silent drift: NIST methanol ΔfH°(l) and benzene ΔfH°(l)
        methanol = EXT.for_formula("CH4O")
        benzene = EXT.for_formula("C6H6")
        assert methanol.dhf_kj_per_mol == -239.5
        assert benzene.dhf_kj_per_mol == 49.0


class TestParacetamolLitmusGapIsDocumented:
    """The honesty that matters: paracetamol's ΔG stays UNKNOWN on a DOCUMENTED entropy gap, never faked."""

    def test_no_fabricated_paracetamol_record_exists(self):
        assert all(r.formula != "C8H9NO2" for r in EXTENDED_THERMO_REFS)
        assert EXT.for_formula("C8H9NO2") is None              # no record -> no fabricated ΔG

    def test_the_gap_is_documented_with_the_missing_quantity_named(self):
        assert "C8H9NO2" in EXTENDED_THERMO_GAPS
        reason = EXTENDED_THERMO_GAPS["C8H9NO2"]
        assert "-410.4" in reason                              # the ΔfH° that IS sourced
        assert ("S°" in reason or "entropy" in reason)    # names entropy as the missing piece

    def test_the_paracetamol_step_stays_unknown_under_the_extended_table(self):
        PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")
        AMP = parse_smiles("Nc1ccc(O)cc1")
        ANH = parse_smiles("CC(=O)OC(=O)C")
        step = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACETIC))
        f = feasibility_of_step(step, thermo=EXT)
        assert f.direction is FeasibilityDirection.UNKNOWN    # entropy gap holds; no fabrication
        assert f.missing


class TestInjectabilityLayering:
    def test_extended_thermo_layers_on_a_caller_base(self):
        # passing a caller's own table layers the extended set on top of it
        layered = extended_thermo(DEFAULT_THERMO)
        assert layered.for_formula("C2H6O") is not None       # ethanol from the extended set
        assert layered.for_named("H2O", "water") is not None  # water from the seed base


class TestR5LiteAromaticSkeleton:
    """R5-lite: the sourced aromatic-intermediate skeleton toward the paracetamol litmus lifts real rungs.

    ``phenol -> 4-nitrophenol -> 4-aminophenol -> paracetamol`` (and the ``benzene -> nitrobenzene ->
    aniline`` reduction analogue) is the industrial descent; R5-lite sources the members whose 298 K
    ΔfH°+S° both genuinely exist as a same-phase NIST pair, so those rungs grade DERIVED instead of sitting
    at L2's HYPOTHESIZED floor -- while the rungs that reach the drug itself stay honest, documented GAPS.
    """

    def test_the_four_aromatic_records_are_sourced_and_resolvable(self):
        for formula, dhf in (("C6H6O", -165.1), ("C6H7N", 31.3), ("C6H5NO2", 12.5), ("C7H8", 12.0)):
            rec = EXT.for_formula(formula)
            assert rec is not None
            assert rec.dhf_kj_per_mol == dhf                   # pinned against silent drift
            assert rec.s_j_per_mol_k > 0                        # a same-phase S° was sourced (third law)
            assert "NIST" in rec.provenance and any(ch.isdigit() for ch in rec.provenance)

    def test_toluene_combustion_calibrates_the_instrument(self):
        # C7H8 + 9 O2 -> 7 CO2 + 4 H2O ; textbook ΔcH° ~ -3910 kJ/mol, ΔG strongly exergonic
        TOL = parse_smiles("Cc1ccccc1")
        burn = ExperimentStep.assembling(CO2, (TOL,) + (O2,) * 9, (CO2,) * 7 + (H2O,) * 4)
        f = feasibility_of_step(burn, thermo=EXT)
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.grade is FeasibilityGrade.DERIVED
        assert f.delta_g_kj < -3700.0                          # combustion: hugely exergonic, cannot be wrong

    def test_nitrobenzene_reduction_rung_lifts_from_unknown_to_derived(self):
        # a real skeleton rung: C6H5NO2 + 3 H2 -> C6H7N + 2 H2O ; UNKNOWN on the seed, DERIVED on R5-lite
        NB = parse_smiles("O=[N+]([O-])c1ccccc1")
        ANILINE = parse_smiles("Nc1ccccc1")
        step = ExperimentStep.assembling(ANILINE, (NB, H2, H2, H2), (ANILINE, H2O, H2O))
        assert feasibility_of_step(step).direction is FeasibilityDirection.UNKNOWN   # seed lacks the aromatics
        f = feasibility_of_step(step, thermo=EXT)
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.grade is FeasibilityGrade.DERIVED

    def test_4_nitrophenol_is_a_documented_gap_not_a_fabricated_record(self):
        # ΔfH° exists but S° does not in any phase -> refused, documented, never a fabricated entropy
        assert all(r.formula != "C6H5NO3" for r in EXTENDED_THERMO_REFS)
        assert EXT.for_formula("C6H5NO3") is None
        assert "C6H5NO3" in EXTENDED_THERMO_GAPS
        reason = EXTENDED_THERMO_GAPS["C6H5NO3"]
        assert ("S°" in reason or "entropy" in reason)


class TestR5LiteNitrationFront:
    """HNO3 extends the DERIVED reach one real edge FORWARD: the aromatic nitration front.

    ``benzene + HNO3 -> nitrobenzene + H2O`` is the precursor skeleton of the industrial route. With the
    liquid HNO3 pair sourced (NBS-1982), all four species carry a same-phase 298 K ΔfH°+S°, so the edge
    grades DERIVED and strongly exergonic -- NOT the drug itself, which stays walled by the missing entropies.
    """

    def test_benzene_nitration_front_lifts_to_derived(self):
        # a real precursor edge: C6H6 + HNO3 -> C6H5NO2 + H2O ; DERIVED on R5-lite, ΔG ~ -138 kJ/mol
        benzene = parse_smiles("c1ccccc1")
        hno3 = parse_smiles("O[N+](=O)[O-]")
        nitrobenzene = parse_smiles("[O-][N+](=O)c1ccccc1")
        water = parse_smiles("O")
        step = ExperimentStep.assembling(nitrobenzene, (benzene, hno3), (nitrobenzene, water))
        f = feasibility_of_step(step, thermo=extended_thermo())
        assert f.direction is FeasibilityDirection.FAVORABLE
        assert f.grade is FeasibilityGrade.DERIVED
        assert f.delta_g_kj < -100                          # independently computed ΔG ~ -138 kJ/mol
