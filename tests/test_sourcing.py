"""SHOP-LEAF-02 x STOCK-01 integration: can a StockMaterial inventory source a shopping requirement?

Pins the meeting of the two bricks: a SHOP-LEAF-02 requirement (per-species mol) judged against a STOCK-01
inventory, matched the SOUND way (canonical structure, so a same-formula isomer on the shelf never sources it), the
identity/assay axis separated from the quantity axis, sourced only when BOTH are proven, and never a vacuous green.
Also pins the CANON-KEKULE-01 payoff at this layer: a Kekule-drawn bottle sources an aromatic-drawn requirement.
"""
from fractions import Fraction

import pytest

from smartchem.experiment.dag import SynthesisDAG, dag_shopping_requirement
from smartchem.experiment.sourcing import (
    QuantityCoverage,
    SourcingPlan,
    plan_sourcing,
)
from smartchem.experiment.step import ExperimentStep
from smartchem.experiment.stock import (
    STOCK_MATERIAL_SCHEMA,
    FitnessVerdict,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
)
from smartchem.smiles import parse_smiles

ETOH = parse_smiles("CCO")
DME = parse_smiles("COC")            # dimethyl ether -- a C2H6O isomer of ethanol
O2 = parse_smiles("O=O")
ACOH = parse_smiles("CC(=O)O")
WATER = parse_smiles("O")
BENZENE = parse_smiles("c1ccccc1")
BENZENE_KEKULE = parse_smiles("C1=CC=CC=C1")
BR2 = parse_smiles("BrBr")
BROMOBENZENE = parse_smiles("Brc1ccccc1")


def _oxidation_requirement(amount=1):
    """A one-step DAG (ETOH + O2 -> ACOH + WATER); shopping requirement = ETOH + O2 (water is a co-product)."""
    step = ExperimentStep.assembling(ACOH, (ETOH, O2), (ACOH, WATER))
    return dag_shopping_requirement(SynthesisDAG.of(step), amount)


def _bromination_requirement(amount=1):
    """A one-step DAG (benzene + Br2 -> bromobenzene + HBr); requirement = benzene + Br2 (aromatic leaf)."""
    hbr = parse_smiles("[H]Br")
    step = ExperimentStep.assembling(BROMOBENZENE, (BENZENE, BR2), (BROMOBENZENE, hbr))
    return dag_shopping_requirement(SynthesisDAG.of(step), amount)


def _pure(mol, name, lo, hi, qty=None, unit="mol"):
    q = StockQuantity.of(qty, unit) if qty is not None else None
    return StockMaterial(
        STOCK_MATERIAL_SCHEMA, f"{name}-bottle", name,
        (MaterialComponent.of_molecule(mol, "active", lo, hi),), Phase.LIQUID, "reagent label", quantity=q,
    )


def _line(plan, mol):
    from smartchem.experiment.dag import _ident
    key = _ident(mol)
    return next(line for line in plan.lines if _ident(line.species) == key)


class TestFullySourced:
    def test_an_inventory_covering_every_requirement_is_fully_sourced(self):
        req = _oxidation_requirement(1)
        inv = (_pure(ETOH, "ethanol", 0.999, 1.0, qty=5), _pure(O2, "oxygen", 0.99, 1.0, qty=5))
        plan = plan_sourcing(req, inv)
        assert isinstance(plan, SourcingPlan)
        assert plan.fully_sourced
        assert not plan.gaps
        assert _line(plan, ETOH).is_sourced and _line(plan, ETOH).coverage is QuantityCoverage.COVERED


class TestIsomerSoundness:
    def test_a_same_formula_isomer_on_the_shelf_does_not_source_the_requirement(self):
        # THE integration soundness: the requirement needs ethanol; the shelf has dimethyl ether (also C2H6O).
        # Structure-keyed matching means DME can NEVER source the ethanol line -- it is IDENTITY_ABSENT, a gap.
        req = _oxidation_requirement(1)
        inv = (_pure(DME, "dimethyl ether", 0.999, 1.0, qty=5), _pure(O2, "oxygen", 0.99, 1.0, qty=5))
        plan = plan_sourcing(req, inv)
        etoh_line = _line(plan, ETOH)
        assert etoh_line.fitness is FitnessVerdict.IDENTITY_ABSENT
        assert etoh_line.material_id is None
        assert not plan.fully_sourced and etoh_line in plan.gaps


class TestKekuleInvariantSourcing:
    def test_a_kekule_drawn_bottle_sources_an_aromatic_drawn_requirement(self):
        # CANON-KEKULE-01 at the sourcing layer: the requirement's benzene is aromatic-drawn; the bottle is
        # explicit-Kekule.  They are the same molecule, so the bottle sources the requirement.
        req = _bromination_requirement(1)
        inv = (_pure(BENZENE_KEKULE, "benzene", 0.999, 1.0, qty=9), _pure(BR2, "bromine", 0.99, 1.0, qty=9))
        plan = plan_sourcing(req, inv)
        assert _line(plan, BENZENE).is_sourced           # matched across the aromatic/Kekule spelling
        assert plan.fully_sourced


class TestAssayAxis:
    def test_a_dilute_structure_keyed_material_is_insufficient_not_a_source(self):
        req = _oxidation_requirement(1)
        dilute_etoh = _pure(ETOH, "aqueous ethanol", 0.04, 0.07, qty=5)     # a few % -- structure matches, assay does not
        inv = (dilute_etoh, _pure(O2, "oxygen", 0.99, 1.0, qty=5))
        line = _line(plan_sourcing(req, inv), ETOH)
        assert line.fitness is FitnessVerdict.INSUFFICIENT_ASSAY and not line.is_sourced

    def test_an_unknown_fraction_material_is_unknown_assay_not_a_source(self):
        req = _oxidation_requirement(1)
        mystery = StockMaterial(
            STOCK_MATERIAL_SCHEMA, "mystery", "unlabelled ethanol",
            (MaterialComponent.unknown_molecule(ETOH, "active"),), Phase.LIQUID, "no assay", quantity=StockQuantity.of(5, "mol"),
        )
        line = _line(plan_sourcing(req, (mystery, _pure(O2, "oxygen", 0.99, 1.0, qty=5))), ETOH)
        assert line.fitness is FitnessVerdict.UNKNOWN_ASSAY and not line.is_sourced


class TestQuantityAxis:
    def test_a_pure_but_too_small_bottle_is_quantity_short(self):
        req = _oxidation_requirement(2)                    # need 2 mol ethanol
        inv = (_pure(ETOH, "ethanol", 0.999, 1.0, qty=1), _pure(O2, "oxygen", 0.99, 1.0, qty=5))  # only 1 mol on hand
        line = _line(plan_sourcing(req, inv), ETOH)
        assert line.fitness is FitnessVerdict.SATISFIES
        assert line.coverage is QuantityCoverage.SHORT and not line.is_sourced

    def test_a_non_mol_unit_leaves_coverage_unknown_not_assumed(self):
        req = _oxidation_requirement(1)
        grams = _pure(ETOH, "ethanol", 0.999, 1.0, qty=500, unit="g")       # grams -> mol needs molar mass (deferred)
        line = _line(plan_sourcing(req, (grams, _pure(O2, "oxygen", 0.99, 1.0, qty=5))), ETOH)
        assert line.fitness is FitnessVerdict.SATISFIES
        assert line.coverage is QuantityCoverage.UNKNOWN and line.available_mol is None
        assert not line.is_sourced                          # right stuff, unknown amount -> NOT confidently sourced

    def test_an_undeclared_quantity_leaves_coverage_unknown(self):
        req = _oxidation_requirement(1)
        no_qty = _pure(ETOH, "ethanol", 0.999, 1.0, qty=None)
        line = _line(plan_sourcing(req, (no_qty, _pure(O2, "oxygen", 0.99, 1.0, qty=5))), ETOH)
        assert line.coverage is QuantityCoverage.UNKNOWN and not line.is_sourced

    def test_worst_case_assay_is_used_for_a_proven_cover(self):
        # 3 mol of a 50-100% material provides a GUARANTEED 1.5 mol (worst case), covering a 1 mol requirement.
        req = _oxidation_requirement(1)
        wide = _pure(ETOH, "ethanol", 0.5, 1.0, qty=3)
        line = _line(plan_sourcing(req, (wide, _pure(O2, "oxygen", 0.99, 1.0, qty=5))), ETOH)
        assert line.available_mol == Fraction(3, 2) and line.coverage is QuantityCoverage.COVERED

    def test_a_worst_case_fraction_just_below_one_is_not_rounded_up_to_covered(self):
        # red-team fails-open fold: a 1 mol bottle whose declared worst-case fraction is 0.9999999999 guarantees
        # only 0.9999999999 mol -- strictly short of a 1 mol requirement.  COVERED must NOT be reported (a prior
        # limit_denominator rounded the lower bound UP to 1.0 and read a false green).
        req = _oxidation_requirement(1)
        just_under = _pure(ETOH, "ethanol", 0.9999999999, 1.0, qty=1)
        line = _line(plan_sourcing(req, (just_under, _pure(O2, "oxygen", 0.99, 1.0, qty=5))), ETOH)
        assert line.coverage is QuantityCoverage.UNKNOWN and not line.is_sourced   # straddle -> measure, not COVERED


class TestNonVacuous:
    def test_an_empty_inventory_is_never_vacuously_sourced(self):
        req = _oxidation_requirement(1)
        plan = plan_sourcing(req, ())
        assert not plan.fully_sourced
        assert all(line.fitness is FitnessVerdict.IDENTITY_ABSENT for line in plan.lines)
        assert len(plan.gaps) == len(plan.lines) and plan.lines            # every line a gap, and lines non-empty

    def test_the_plan_has_one_line_per_requirement(self):
        req = _oxidation_requirement(1)
        plan = plan_sourcing(req, ())
        assert len(plan.lines) == len(req.requirements)


class TestInputGuards:
    def test_a_non_requirement_is_refused(self):
        with pytest.raises(TypeError):
            plan_sourcing("not a requirement", ())

    def test_a_non_tuple_inventory_is_refused(self):
        req = _oxidation_requirement(1)
        with pytest.raises(TypeError):
            plan_sourcing(req, [_pure(ETOH, "ethanol", 0.999, 1.0)])       # a list, not a tuple

    @pytest.mark.parametrize("bad", [0.0, -0.1, 1.5, True])
    def test_a_bad_min_assay_is_refused(self, bad):
        req = _oxidation_requirement(1)
        with pytest.raises(ValueError):
            plan_sourcing(req, (), min_assay=bad)

    def test_min_assay_governs_the_verdict(self):
        # the SAME 0.95-1.0 material SATISFIES a relaxed 0.9 requirement but is UNKNOWN at the strict default 0.99.
        req = _oxidation_requirement(1)
        mat = (_pure(ETOH, "ethanol", 0.95, 1.0, qty=5), _pure(O2, "oxygen", 0.99, 1.0, qty=5))
        assert _line(plan_sourcing(req, mat, min_assay=0.90), ETOH).fitness is FitnessVerdict.SATISFIES
        assert _line(plan_sourcing(req, mat, min_assay=0.99), ETOH).fitness is FitnessVerdict.UNKNOWN_ASSAY
