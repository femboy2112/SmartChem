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
        formulation="5% aqueous", phase=Phase.AQUEOUS_SOLUTION, quantity=StockQuantity.of("25", "mL"),
        evidence_source=_LOC)
    assert use.identity is None
    assert use.role is ProcedureMaterialRole.WASH
    assert use.formulation == "5% aqueous"
    assert use.phase is Phase.AQUEOUS_SOLUTION
    assert use.quantity == StockQuantity.of("25", "mL")


def test_material_use_constructs_with_a_resolved_molecule() -> None:
    """A single connected species resolves through parse_smiles and rides as a real Molecule identity."""
    h2so4 = parse_smiles("OS(=O)(=O)O")
    use = ProcedureMaterialUse(
        name="sulfuric acid", role=ProcedureMaterialRole.CATALYST, identity=h2so4,
        formulation="conc.", phase=Phase.LIQUID, quantity=StockQuantity.of("4", "mL"), evidence_source=_LOC)
    assert use.identity is not None
    assert use.identity.formula == {"H": 2, "O": 4, "S": 1}


def test_material_use_is_digestible_and_stable() -> None:
    """It is a frozen Digestible: equal content -> equal digest, and the Molecule identity digests cleanly."""
    make = lambda: ProcedureMaterialUse(  # noqa: E731 -- terse on purpose; two identical births, one identity
        name="sulfuric acid", role=ProcedureMaterialRole.CATALYST, identity=parse_smiles("OS(=O)(=O)O"),
        formulation="conc.", phase=Phase.LIQUID, evidence_source=_LOC)
    assert make().digest == make().digest


def test_enum_has_exactly_the_frozen_six_roles() -> None:
    assert {r.value for r in ProcedureMaterialRole} == {
        "CATALYST", "WASH", "DRY", "SOLVENT", "RINSE", "NEUTRALIZE"}


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
        "sulfuric acid", "cold water", "sodium bicarbonate", "water", "sodium chloride", "magnesium sulfate"}
    assert uses["sulfuric acid"].role is ProcedureMaterialRole.CATALYST
    assert uses["sulfuric acid"].identity is not None
    assert uses["sulfuric acid"].identity.formula == {"H": 2, "O": 4, "S": 1}
    assert uses["sulfuric acid"].formulation == "conc."
    assert uses["sulfuric acid"].phase is Phase.LIQUID
    assert uses["sulfuric acid"].quantity == StockQuantity.of("4", "mL")
    # ionic washes/drier: identity=None (unresolvable), the sourced adjective survives as structured data
    assert uses["sodium bicarbonate"].identity is None
    assert uses["sodium bicarbonate"].role is ProcedureMaterialRole.WASH
    assert uses["sodium bicarbonate"].phase is Phase.AQUEOUS_SOLUTION
    assert uses["sodium chloride"].identity is None
    assert uses["magnesium sulfate"].identity is None
    assert uses["magnesium sulfate"].role is ProcedureMaterialRole.DRY
    assert uses["magnesium sulfate"].formulation == "anhydrous"
    assert uses["magnesium sulfate"].phase is Phase.SOLID
    assert uses["magnesium sulfate"].quantity == StockQuantity.of("2", "g")
    # benign resolvable waters
    assert uses["cold water"].identity is not None and uses["cold water"].role is ProcedureMaterialRole.RINSE
    assert uses["water"].identity is not None and uses["water"].role is ProcedureMaterialRole.WASH


def test_aspirin_material_census() -> None:
    uses = _uses_by_name(_ASPIRIN_PROCEDURE)
    assert set(uses) == {"sulfuric acid", "water", "ethyl acetate", "petroleum ether"}
    assert uses["sulfuric acid"].role is ProcedureMaterialRole.CATALYST
    assert uses["sulfuric acid"].identity is not None
    assert uses["ethyl acetate"].role is ProcedureMaterialRole.SOLVENT
    assert uses["ethyl acetate"].identity is not None
    assert uses["ethyl acetate"].identity.formula == {"C": 4, "H": 8, "O": 2}
    # petroleum ether is a hydrocarbon cut, not one compound -> identity=None
    assert uses["petroleum ether"].identity is None
    assert uses["petroleum ether"].role is ProcedureMaterialRole.RINSE


def test_paracetamol_material_census() -> None:
    uses = _uses_by_name(_PARACETAMOL_PROCEDURE)
    assert set(uses) == {
        "hydrochloric acid", "decolorizing charcoal (Norit)", "sodium acetate buffer", "water"}
    assert uses["hydrochloric acid"].role is ProcedureMaterialRole.NEUTRALIZE
    assert uses["hydrochloric acid"].identity is not None
    assert uses["hydrochloric acid"].identity.formula == {"Cl": 1, "H": 1}
    assert uses["hydrochloric acid"].phase is Phase.AQUEOUS_SOLUTION
    assert uses["hydrochloric acid"].quantity == StockQuantity.of("1.5", "mL")
    # amorphous carbon and a buffered mixture: both identity=None
    assert uses["decolorizing charcoal (Norit)"].identity is None
    assert uses["sodium acetate buffer"].identity is None
    assert uses["sodium acetate buffer"].role is ProcedureMaterialRole.NEUTRALIZE
    assert uses["water"].identity is not None and uses["water"].role is ProcedureMaterialRole.RINSE
