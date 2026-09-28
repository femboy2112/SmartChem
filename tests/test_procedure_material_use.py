"""v0.9 Round III -- ProcedureMaterialUse type + the authored procedure-material census (D2).

These pin the SOURCE-evidence contract for procedure-only auxiliaries (catalysts, washes, driers, solvents,
rinses, pH agents): the new ``ProcedureMaterialUse`` frozen record, the ``ProcedureMaterialRole`` closed enum,
their attachment to ``ProcedureOperation.material_uses``, and the hand-authored census on the three real
LibreTexts procedures. The load-bearing honesty here is ``identity: Molecule | None`` -- the ionic salts and
mixtures CANNOT resolve to one connected species, and a fabricated covalent spelling of a lattice is banned; so
these tests prove both the resolved and the None case, and that a bad role is refused.

Scope note (the surgeon's chart): the VERIFY-op ``apparatus`` MECHANISM is exercised here (a VERIFY op can carry
an apparatus tuple), but the three real procedures do NOT yet carry the D5 measurement strings -- that population
is blocked on the capability-core sibling scoping ``requirements.py::_equipment_requirement`` to skip VERIFY ops
(today it unions every op's apparatus into the equipment axis, so an un-scoped measurement string double-counts as
unrecognized equipment). This file asserts the field is ready, not that it is populated.
"""
from __future__ import annotations

import pytest

from smartchem.decompiler_conditions import (
    _ASPIRIN_PROCEDURE,
    _ISOPENTYL_PROCEDURE,
    _PARACETAMOL_PROCEDURE,
)
from smartchem.experiment.stock import Phase, StockQuantity
from smartchem.material_spec import EvidenceKind, PhaseClaim
from smartchem.procedure_evidence import (
    OperationKind,
    OperationRole,
    ProcedureMaterialRole,
    ProcedureMaterialUse,
    ProcedureOperation,
)
from smartchem.smiles import parse_smiles

_LOC = "https://chem.libretexts.org/example"


def _uses_by_name(procedure) -> dict[str, ProcedureMaterialUse]:
    """Flatten every operation's material_uses into a name-keyed map (names are unique per procedure here)."""
    out: dict[str, ProcedureMaterialUse] = {}
    for op in procedure.operations:
        for use in op.material_uses:
            out[use.name] = use
    return out


# -- the type itself -------------------------------------------------------------------------------------------

def test_material_use_constructs_with_none_identity() -> None:
    """An ionic/mixture species is carried with identity=None -- the honest carrier, never skipped."""
    use = ProcedureMaterialUse(
        name="sodium bicarbonate", role=ProcedureMaterialRole.WASH, identity=None,
        formulation="5% aqueous", phase=PhaseClaim(Phase.AQUEOUS_SOLUTION, EvidenceKind.SOURCE_QUOTED),
        quantity=StockQuantity.of("25", "mL"), evidence_source=_LOC)
    assert use.identity is None
    assert use.role is ProcedureMaterialRole.WASH
    assert use.formulation == "5% aqueous"
    assert use.phase == PhaseClaim(Phase.AQUEOUS_SOLUTION, EvidenceKind.SOURCE_QUOTED)
    assert use.quantity == StockQuantity.of("25", "mL")


def test_material_use_constructs_with_a_resolved_molecule() -> None:
    """A single connected species resolves through parse_smiles and rides as a real Molecule identity."""
    h2so4 = parse_smiles("OS(=O)(=O)O")
    use = ProcedureMaterialUse(
        name="sulfuric acid", role=ProcedureMaterialRole.CATALYST, identity=h2so4,
        formulation="conc.", phase=PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED),
        quantity=StockQuantity.of("4", "mL"), evidence_source=_LOC)
    assert use.identity is not None
    assert use.identity.formula == {"H": 2, "O": 4, "S": 1}


def test_material_use_is_digestible_and_stable() -> None:
    """It is a frozen Digestible: equal content -> equal digest, and the Molecule identity digests cleanly."""
    make = lambda: ProcedureMaterialUse(  # noqa: E731 -- terse on purpose; two identical births, one identity
        name="sulfuric acid", role=ProcedureMaterialRole.CATALYST, identity=parse_smiles("OS(=O)(=O)O"),
        formulation="conc.", phase=PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED), evidence_source=_LOC)
    assert make().digest == make().digest


def test_specification_defaults_none_and_is_type_checked() -> None:
    """Round V D3: ``specification`` is the load-bearing typed record; it defaults to None, only a real
    MaterialSpecification is accepted, and it enters the use's digest (formulation text alone is display)."""
    from smartchem.material_spec import MaterialSpecification

    bare = ProcedureMaterialUse(name="x", role=ProcedureMaterialRole.WASH, evidence_source=_LOC)
    assert bare.specification is None
    with pytest.raises(TypeError):
        ProcedureMaterialUse(name="x", role=ProcedureMaterialRole.WASH, evidence_source=_LOC,
                             specification={"unresolved_terms": ("conc.",)})  # type: ignore[arg-type]
    typed = ProcedureMaterialUse(name="x", role=ProcedureMaterialRole.WASH, evidence_source=_LOC,
                                 specification=MaterialSpecification(unresolved_terms=("conc.",)))
    assert typed.digest != bare.digest


def test_enum_has_exactly_the_frozen_eight_roles() -> None:
    # Round IV F45: SUBSTRATE + REACTANT added so the SOURCE carries reaction inputs as typed uses -- the
    # generic capability compiler reads reactant semantics off material_uses, with no leaf-identity whitelist.
    assert {r.value for r in ProcedureMaterialRole} == {
        "SUBSTRATE", "REACTANT", "CATALYST", "WASH", "DRY", "SOLVENT", "RINSE", "NEUTRALIZE"}


def test_role_rejects_a_bare_string() -> None:
    with pytest.raises(TypeError):
        ProcedureMaterialUse(name="x", role="CATALYST", evidence_source=_LOC)  # type: ignore[arg-type]


def test_identity_rejects_a_non_molecule() -> None:
    with pytest.raises(TypeError):
        ProcedureMaterialUse(
            name="x", role=ProcedureMaterialRole.WASH, identity="O", evidence_source=_LOC)  # type: ignore[arg-type]


def test_phase_and_quantity_reject_wrong_types() -> None:
    with pytest.raises(TypeError):
        ProcedureMaterialUse(
            name="x", role=ProcedureMaterialRole.WASH, phase="AQUEOUS_SOLUTION", evidence_source=_LOC)  # type: ignore[arg-type]
    # D18 (Part III): a BARE Phase is an ungraded claim and is refused -- the phase must carry its evidence kind.
    with pytest.raises(TypeError, match="PhaseClaim"):
        ProcedureMaterialUse(
            name="x", role=ProcedureMaterialRole.WASH, phase=Phase.AQUEOUS_SOLUTION, evidence_source=_LOC)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ProcedureMaterialUse(
            name="x", role=ProcedureMaterialRole.WASH, quantity="25 mL", evidence_source=_LOC)  # type: ignore[arg-type]


def test_name_and_source_must_be_non_empty() -> None:
    with pytest.raises(ValueError):
        ProcedureMaterialUse(name="  ", role=ProcedureMaterialRole.WASH, evidence_source=_LOC)
    with pytest.raises(ValueError):
        ProcedureMaterialUse(name="water", role=ProcedureMaterialRole.RINSE, evidence_source="   ")


# -- ProcedureOperation.material_uses attachment ---------------------------------------------------------------

def test_operation_material_uses_defaults_empty_and_validates_membership() -> None:
    op = ProcedureOperation(ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION, locator=_LOC)
    assert op.material_uses == ()
    with pytest.raises(TypeError):
        ProcedureOperation(
            ordinal=1, kind=OperationKind.ADD, role=OperationRole.REACTION,
            material_uses=("not a use",), locator=_LOC)  # type: ignore[arg-type]


def test_verify_op_apparatus_mechanism_is_ready() -> None:
    """The VERIFY-op apparatus channel exists and accepts strings; population on the real procedures is held
    (see module docstring). This asserts the field, not the (blocked) data."""
    verify = ProcedureOperation(
        ordinal=1, kind=OperationKind.VERIFY, role=OperationRole.OTHER,
        apparatus=("analytical balance", "infrared spectrometer"), locator=_LOC)
    assert verify.kind is OperationKind.VERIFY
    assert verify.apparatus == ("analytical balance", "infrared spectrometer")


# -- the authored census on the three real procedures ----------------------------------------------------------

def test_isopentyl_material_census() -> None:
    uses = _uses_by_name(_ISOPENTYL_PROCEDURE)
    assert set(uses) == {
        "isopentyl alcohol", "acetic acid", "sulfuric acid", "cold water", "sodium bicarbonate", "water",
        "sodium chloride", "magnesium sulfate"}
    # Round IV F45: the two reactants are now typed SUBSTRATE/REACTANT source uses (not a leaf whitelist).
    assert uses["isopentyl alcohol"].role is ProcedureMaterialRole.SUBSTRATE
    assert uses["isopentyl alcohol"].identity is not None
    assert uses["isopentyl alcohol"].quantity == StockQuantity.of("15", "mL")
    assert uses["acetic acid"].role is ProcedureMaterialRole.REACTANT
    assert uses["acetic acid"].identity is not None
    assert uses["acetic acid"].formulation == "glacial"
    assert uses["acetic acid"].specification is not None
    assert uses["isopentyl alcohol"].formulation is None  # Round V: the source never says "neat"
    assert uses["isopentyl alcohol"].specification is None
    assert uses["acetic acid"].quantity == StockQuantity.of("20", "mL")
    assert uses["sulfuric acid"].role is ProcedureMaterialRole.CATALYST
    assert uses["sulfuric acid"].identity is not None
    assert uses["sulfuric acid"].identity.formula == {"H": 2, "O": 4, "S": 1}
    assert uses["sulfuric acid"].formulation == "conc."
    assert uses["sulfuric acid"].specification.unresolved_terms == ("conc.",)
    assert uses["sulfuric acid"].phase == PhaseClaim(Phase.LIQUID, EvidenceKind.AUTHOR_INFERRED,
                                                      note=uses["sulfuric acid"].phase.note)
    assert uses["sulfuric acid"].quantity == StockQuantity.of("4", "mL")
    # ionic washes/drier: identity=None (unresolvable), the sourced adjective survives as structured data
    assert uses["sodium bicarbonate"].identity is None
    assert uses["sodium bicarbonate"].role is ProcedureMaterialRole.WASH
    # D18: the cited page itself says "5% aqueous sodium bicarbonate" -> SOURCE_QUOTED (the Round-V comment
    # calling this an author inference was wrong).
    assert (uses["sodium bicarbonate"].phase.phase, uses["sodium bicarbonate"].phase.evidence) == (
        Phase.AQUEOUS_SOLUTION, EvidenceKind.SOURCE_QUOTED)
    assert uses["sodium chloride"].identity is None
    assert uses["magnesium sulfate"].identity is None
    assert uses["magnesium sulfate"].role is ProcedureMaterialRole.DRY
    assert uses["magnesium sulfate"].formulation == "anhydrous"
    assert uses["magnesium sulfate"].specification is not None
    assert uses["sodium chloride"].quantity == StockQuantity.of("5", "mL")  # Round V F64: sourced 5 mL carried
    assert (uses["magnesium sulfate"].phase.phase, uses["magnesium sulfate"].phase.evidence) == (
        Phase.SOLID, EvidenceKind.AUTHOR_INFERRED)  # "2 g" is a mass; the page never says SOLID
    assert uses["magnesium sulfate"].quantity == StockQuantity.of("2", "g")
    # benign resolvable waters
    assert uses["cold water"].identity is not None and uses["cold water"].role is ProcedureMaterialRole.RINSE
    assert uses["water"].identity is not None and uses["water"].role is ProcedureMaterialRole.WASH


def test_aspirin_material_census() -> None:
    uses = _uses_by_name(_ASPIRIN_PROCEDURE)
    # Round V: the bicarbonate/HCl reprecipitation ops now carry their sourced auxiliaries
    # Wave-C K4: the rinse uses are named "cold water" exactly as their op.materials string says
    assert set(uses) == {"sulfuric acid", "water", "cold water", "ethyl acetate", "petroleum ether",
                         "sodium bicarbonate", "hydrochloric acid"}
    assert uses["sulfuric acid"].role is ProcedureMaterialRole.CATALYST
    assert uses["sulfuric acid"].identity is not None
    assert uses["sulfuric acid"].specification.unresolved_terms == ("conc.",)
    assert uses["ethyl acetate"].specification is None and uses["petroleum ether"].specification is None
    assert uses["ethyl acetate"].role is ProcedureMaterialRole.SOLVENT
    assert uses["ethyl acetate"].identity is not None
    assert uses["ethyl acetate"].identity.formula == {"C": 4, "H": 8, "O": 2}
    # petroleum ether is a hydrocarbon cut, not one compound -> identity=None
    assert uses["petroleum ether"].identity is None
    assert uses["petroleum ether"].role is ProcedureMaterialRole.RINSE


def test_paracetamol_material_census() -> None:
    hcl = [u for op in _PARACETAMOL_PROCEDURE.operations for u in op.material_uses if u.name == "hydrochloric acid"]
    # Round V: "1.5 mL" then "a few more drops ... if necessary" -> an exact draw + an unquantified draw
    assert [u.quantity for u in hcl] == [StockQuantity.of("1.5", "mL"), None]
    uses = {u.name: u for op in _PARACETAMOL_PROCEDURE.operations for u in op.material_uses
            if not (u.name == "hydrochloric acid" and u.quantity is None)}
    assert set(uses) == {
        "hydrochloric acid", "decolorizing charcoal (Norit)", "sodium acetate buffer", "water", "cold water"}
    assert uses["hydrochloric acid"].role is ProcedureMaterialRole.NEUTRALIZE
    assert uses["hydrochloric acid"].identity is not None
    assert uses["hydrochloric acid"].identity.formula == {"Cl": 1, "H": 1}
    assert (uses["hydrochloric acid"].phase.phase, uses["hydrochloric acid"].phase.evidence) == (
        Phase.AQUEOUS_SOLUTION, EvidenceKind.AUTHOR_INFERRED)  # a dictionary reading of "hydrochloric acid"
    assert uses["hydrochloric acid"].quantity == StockQuantity.of("1.5", "mL")
    # Round V: verbatim "concentrated hydrochloric acid", no % -> unresolved, never a number
    assert uses["hydrochloric acid"].formulation == "concentrated"
    assert uses["hydrochloric acid"].specification.unresolved_terms == ("concentrated",)
    assert uses["hydrochloric acid"].specification.composition is None
    # amorphous carbon and a buffered mixture: both identity=None
    assert uses["decolorizing charcoal (Norit)"].identity is None
    assert uses["sodium acetate buffer"].identity is None
    assert uses["sodium acetate buffer"].role is ProcedureMaterialRole.NEUTRALIZE
    assert uses["water"].identity is not None and uses["water"].role is ProcedureMaterialRole.RINSE
