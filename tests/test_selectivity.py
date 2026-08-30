"""E5 depth -- isomer-keyed regiochemical selectivity, proven on the paracetamol N-/O-acetylation fork.

The formal engine and the composability check are blind to *which isomer* an assembly makes -- paracetamol
(N-acetyl amide) and 4-aminophenyl acetate (O-acetyl ester) share the formula C8H9NO2.  These tests pin
that the sourced selectivity table resolves the fork structurally: the amide is the sourced-FAVORED major
product of acetylating 4-aminophenol, the ester is DISFAVORED, an unsourced reactant set is a loud UNKNOWN,
a single-isomer product is NOT_APPLICABLE (never a manufactured preference), and the ranking floats the
favored route above the disfavored one.  The universality lever (inject a record -> resolve a gap) is proven.
"""
import pytest

from smartchem.decompiler import Formula
from smartchem.experiment.drafter import draft_procedure, rank_routes
from smartchem.experiment.selectivity import (
    DEFAULT_SELECTIVITY,
    SelectivityRecord,
    SelectivityStatus,
    _formulas_key,
    selectivity_of_step,
    verify_selectivity,
)
from smartchem.experiment.step import ExperimentRoute, ExperimentStep
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
