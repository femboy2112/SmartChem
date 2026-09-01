"""E5 depth -- isomer-keyed regiochemical selectivity, proven on the paracetamol N-/O-acetylation fork.

The formal engine and the composability check are blind to *which isomer* an assembly makes -- paracetamol
(N-acetyl amide) and 4-aminophenyl acetate (O-acetyl ester) share the formula C8H9NO2.  These tests pin
that the sourced selectivity table resolves the fork structurally: the amide is the sourced-FAVORED major
product of acetylating 4-aminophenol, the ester is DISFAVORED, an unsourced reactant set is a loud UNKNOWN,
a single-isomer product is NOT_APPLICABLE (never a manufactured preference), and the ranking floats the
favored route above the disfavored one.  The universality lever (inject a record -> resolve a gap) is proven.
"""
import pytest

from smartchem.contracts import EvidenceStatus
from smartchem.decompiler import Formula
from smartchem.experiment.bucket import Bucket
from smartchem.experiment.drafter import draft_procedure, rank_routes
from smartchem.experiment.selectivity import (
    DEFAULT_SELECTIVITY,
    SelectivityRecord,
    SelectivityStatus,
    SelectivityTable,
    _formulas_key,
    selectivity_of_step,
    verify_selectivity,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
from smartchem.provenance import SourceCitation, SourceReview
from smartchem.smiles import parse_smiles

PARA = parse_smiles("CC(=O)Nc1ccc(O)cc1")      # paracetamol, the N-acetyl amide
AMP = parse_smiles("Nc1ccc(O)cc1")             # 4-aminophenol
ANH = parse_smiles("CC(=O)OC(=O)C")            # acetic anhydride
ACOH = parse_smiles("CC(=O)O")                 # acetic acid
KETENE = parse_smiles("C=C=O")                 # ketene
ESTER = parse_smiles("CC(=O)Oc1ccc(N)cc1")     # 4-aminophenyl acetate, the O-acetyl ester
BENZENE = parse_smiles("c1ccccc1")             # single registered isomer of C6H6
ACETYLENE = parse_smiles("C#C")
ETHANOL = parse_smiles("CCO")                  # competes with dimethyl ether (C2H6O)
ETHYLENE = parse_smiles("C=C")
WATER = parse_smiles("O")


def _para_via_anhydride():
    return ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH))


def _ester_via_anhydride():
    return ExperimentStep.assembling(ESTER, (AMP, ANH), (ESTER, ACOH))


class TestStepSelectivity:
    def test_paracetamol_from_anhydride_is_the_sourced_favored_isomer(self):
        sel = selectivity_of_step(_para_via_anhydride(), table=DEFAULT_SELECTIVITY)
        assert sel.status is SelectivityStatus.FAVORED
        assert "paracetamol" in sel.reason
        assert sel.finding.bucket.name == "KNOWN_SOURCED"

    def test_uniform_equation_scaling_preserves_selectivity_lookup(self):
        base = _para_via_anhydride()
        scaled = ExperimentStep.assembling(PARA, base.reactants * 4, base.products * 4)
        assert selectivity_of_step(scaled, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.FAVORED

    def test_the_o_acetyl_ester_from_the_same_reactants_is_disfavored(self):
        sel = selectivity_of_step(_ester_via_anhydride(), table=DEFAULT_SELECTIVITY)
        assert sel.status is SelectivityStatus.DISFAVORED
        # names both the sourced major product and the minor one this step makes
        assert "paracetamol" in sel.reason and "4-aminophenyl acetate" in sel.reason

    def test_a_competing_formula_with_no_sourced_record_is_a_loud_unknown(self):
        # the ketene acetylation reactant set {C6H7NO, C2H2O} carries no sourced N-/O-selectivity
        step = ExperimentStep.assembling(PARA, (AMP, KETENE), (PARA,))
        sel = selectivity_of_step(step, table=DEFAULT_SELECTIVITY)
        assert sel.status is SelectivityStatus.UNKNOWN
        assert sel.finding.bucket.name == "UNKNOWN"

    def test_a_single_isomer_product_has_no_selectivity_question(self):
        # benzene is the only registered C6H6 isomer: no regiochemistry to rank, never a fabricated FAVORED
        step = ExperimentStep.assembling(BENZENE, (ACETYLENE, ACETYLENE, ACETYLENE), (BENZENE,))
        sel = selectivity_of_step(step, table=DEFAULT_SELECTIVITY)
        assert sel.status is SelectivityStatus.NOT_APPLICABLE


class TestRouteVerdict:
    def test_a_favored_single_step_route_is_favored(self):
        route = ExperimentRoute.of(_para_via_anhydride())
        assert verify_selectivity(route).verdict == "FAVORED"

    def test_a_disfavored_step_dominates_the_route_verdict(self):
        route = ExperimentRoute.of(_ester_via_anhydride())
        assert verify_selectivity(route).verdict == "DISFAVORED"

    def test_verify_selectivity_requires_a_route(self):
        with pytest.raises(TypeError):
            verify_selectivity(_para_via_anhydride())


class TestRankingUsesSelectivity:
    def test_favored_floats_above_unknown_above_disfavored(self):
        r_para = ExperimentRoute.of(_para_via_anhydride())
        r_ester = ExperimentRoute.of(_ester_via_anhydride())
        r_ket = ExperimentRoute.of(ExperimentStep.assembling(PARA, (AMP, KETENE), (PARA,)))
        ranked = rank_routes([r_ester, r_ket, r_para])
        verdicts = [verify_selectivity(f.route).verdict for f in ranked]
        assert verdicts == ["FAVORED", "UNKNOWN", "DISFAVORED"]


class TestInjectabilityLever:
    """The universality lever: an off-seed reactant set is UNKNOWN until a sourced record is injected."""

    def test_unknown_until_a_sourced_record_is_injected_then_favored(self):
        # ethylene + water -> ethanol competes with dimethyl ether (C2H6O), and the seed has no record
        step = ExperimentStep.assembling(ETHANOL, (ETHYLENE, WATER), (ETHANOL,))
        assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.UNKNOWN

        injected = DEFAULT_SELECTIVITY.with_records(
            SelectivityRecord(
                reactant_key=_formulas_key("C2H4", "H2O"),
                product_formula=Formula.parse("C2H6O").counts,
                major_isomer_name="ethanol",
                provenance="test: acid-catalysed Markovnikov hydration of ethylene gives ethanol",
                source=SourceCitation(
                    "https://example.test/reviewed-ethylene-hydration", SourceReview.ACCEPTED
                ),
            )
        )
        assert selectivity_of_step(step, table=injected).status is SelectivityStatus.FAVORED


class TestDraftSurfacesSelectivity:
    def test_the_draft_renders_the_sourced_selectivity_for_a_competitive_step(self):
        route = ExperimentRoute.of(_para_via_anhydride())
        text = draft_procedure(route).render()
        assert "selectivity: FAVORED" in text
        assert "major:paracetamol" in text

    def test_the_draft_omits_selectivity_for_a_single_isomer_product(self):
        route = ExperimentRoute.of(
            ExperimentStep.assembling(BENZENE, (ACETYLENE, ACETYLENE, ACETYLENE), (BENZENE,))
        )
        text = draft_procedure(route).render()
        assert "selectivity:" not in text


class TestSourcedDiscipline:
    def test_a_selectivity_record_must_carry_a_provenance(self):
        with pytest.raises(ValueError):
            SelectivityRecord(
                reactant_key=_formulas_key("C2H4", "H2O"),
                product_formula=Formula.parse("C2H6O").counts,
                major_isomer_name="ethanol",
                provenance="",
            )

    def test_reactant_names_must_be_a_tuple_of_non_empty_strings(self):
        with pytest.raises(TypeError):
            SelectivityRecord(
                reactant_key=_formulas_key("C2H4", "H2O"),
                product_formula=Formula.parse("C2H6O").counts,
                major_isomer_name="ethanol",
                provenance="test",
                reactant_names=("",),
            )

    def test_an_unsupported_record_cannot_promote_a_reaction(self):
        with pytest.raises(ValueError, match="cannot be UNSUPPORTED"):
            SelectivityRecord(
                reactant_key=_formulas_key("C2H4", "H2O"),
                product_formula=Formula.parse("C2H6O").counts,
                major_isomer_name="ethanol",
                provenance="test negative record",
                status=EvidenceStatus.UNSUPPORTED,
            )

    def test_free_text_provenance_cannot_promote_a_reaction(self):
        step = ExperimentStep.assembling(ETHANOL, (ETHYLENE, WATER), (ETHANOL,))
        declared = SelectivityTable((SelectivityRecord(
            reactant_key=_formulas_key("C2H4", "H2O"),
            product_formula=Formula.parse("C2H6O").counts,
            major_isomer_name="ethanol",
            provenance="because I said so",
        ),))
        result = selectivity_of_step(step, table=declared)
        assert result.status is SelectivityStatus.UNKNOWN
        assert result.finding.bucket is Bucket.UNKNOWN

    def test_unreviewed_or_malformed_locator_cannot_promote(self):
        with pytest.raises(ValueError, match="source locator"):
            SourceCitation("doi:", SourceReview.ACCEPTED)
        step = ExperimentStep.assembling(ETHANOL, (ETHYLENE, WATER), (ETHANOL,))
        unreviewed = SelectivityTable((SelectivityRecord(
            reactant_key=_formulas_key("C2H4", "H2O"),
            product_formula=Formula.parse("C2H6O").counts,
            major_isomer_name="ethanol",
            provenance="citation supplied but not accepted",
            source=SourceCitation("https://example.test/pending-review"),
        ),))
        assert selectivity_of_step(step, table=unreviewed).status is SelectivityStatus.UNKNOWN


# Mid-1: two more sourced regiochemical facts beyond the paracetamol N-/O-acetylation record --
# ooh, one Markovnikov, one meta-director, so the SEED covers more than one litmus compound now.
PROPENE = parse_smiles("CC=C")
PROP1OL = parse_smiles("CCCO")          # propan-1-ol, the Markovnikov-minor product
PROP2OL = parse_smiles("CC(O)C")        # propan-2-ol, the Markovnikov-major product
NITROBENZENE = parse_smiles("[O-][N+](=O)c1ccccc1")
HNO3 = parse_smiles("O[N+](=O)[O-]")
META_DNB = parse_smiles("[O-][N+](=O)c1cccc([N+](=O)[O-])c1")   # 1,3-dinitrobenzene, sourced major
PARA_DNB = parse_smiles("[O-][N+](=O)c1ccc([N+](=O)[O-])cc1")   # 1,4-dinitrobenzene, sourced minor
DNB_WATER = parse_smiles("O")   # nitration's byproduct, needed to conserve mass (C6H5NO2+HNO3 -> DNB+H2O)


class TestMid1SourcedSelectivityBeyondParacetamol:
    def test_markovnikov_hydration_of_propene_favors_propan_2_ol(self):
        step = ExperimentStep.assembling(PROP2OL, (PROPENE, WATER), (PROP2OL,))
        assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.FAVORED

    def test_the_same_reactants_making_propan_1_ol_is_disfavored(self):
        step = ExperimentStep.assembling(PROP1OL, (PROPENE, WATER), (PROP1OL,))
        assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.DISFAVORED

    def test_meta_directed_nitration_favors_1_3_dinitrobenzene(self):
        # nitration's byproduct water is required to conserve mass: C6H5NO2+HNO3 -> DNB + H2O
        step = ExperimentStep.assembling(META_DNB, (NITROBENZENE, HNO3), (META_DNB, DNB_WATER))
        assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.FAVORED

    def test_the_same_reactants_making_1_4_dinitrobenzene_is_disfavored(self):
        step = ExperimentStep.assembling(PARA_DNB, (NITROBENZENE, HNO3), (PARA_DNB, DNB_WATER))
        assert selectivity_of_step(step, table=DEFAULT_SELECTIVITY).status is SelectivityStatus.DISFAVORED


AMINOPHENOL_3 = parse_smiles("Nc1cccc(O)c1")  # 3-aminophenol, same formula (C6H7NO) as 4-aminophenol


class TestS2ReactantSideIsomerKeying:
    """S2: a sourced record injected with ``reactant_names`` must refuse to fire for the WRONG reactant
    isomer, even though the composition matches -- 3-aminophenol is not 4-aminophenol just because both
    resolve to C6H7NO. This exercises an INJECTED table, never the seed."""

    def _injected_table(self) -> SelectivityTable:
        return DEFAULT_SELECTIVITY.with_records(
            SelectivityRecord(
                reactant_key=_formulas_key("C6H7NO", "C4H6O3"),
                product_formula=Formula.parse("C8H9NO2").counts,
                major_isomer_name="paracetamol",
                provenance="test: N-selective acetylation, keyed to the 4-aminophenol isomer specifically",
                reactant_names=("4-aminophenol",),
                source=SourceCitation(
                    "https://example.test/reviewed-paracetamol-selectivity", SourceReview.ACCEPTED
                ),
            )
        )

    def test_fires_favored_when_the_reactant_actually_resolves_to_the_keyed_isomer(self):
        # acetic acid is the anhydride acetylation's byproduct, needed to conserve mass (as in
        # _para_via_anhydride above)
        step = ExperimentStep.assembling(PARA, (AMP, ANH), (PARA, ACOH))
        sel = selectivity_of_step(step, table=self._injected_table())
        assert sel.status is SelectivityStatus.FAVORED

    def test_refuses_to_fire_for_a_same_formula_wrong_isomer_reactant(self):
        # 3-aminophenol + acetic anhydride -> paracetamol: same C6H7NO composition, WRONG isomer.
        # A fabricated FAVORED here would be exactly the vacuity this guard exists to prevent.
        step = ExperimentStep.assembling(PARA, (AMINOPHENOL_3, ANH), (PARA, ACOH))
        sel = selectivity_of_step(step, table=self._injected_table())
        assert sel.status is SelectivityStatus.UNKNOWN
        assert "4-aminophenol" in sel.reason
        assert sel.finding.bucket.name == "UNKNOWN"
