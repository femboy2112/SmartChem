"""v0.9 Round V (barrier D3) -- the SOURCE-AUTHORED MaterialSpecification census.

Pins, per use, exactly what the typed ``specification`` says for every corpus use that carries a load-bearing
formulation, and the discipline behind it: a number only where the cited page prints one (and then on basis
UNKNOWN unless the page states the basis), a state claim only where the page uses the state word, and every
"conc."/"concentrated" left as an UNRESOLVED term (-> UNKNOWN), never a guessed percentage. Also pins the two
Round-V corpus corrections: "neat" is no longer authored for isopentyl alcohol (the page never says it), and the
sourced "5 mL" of saturated NaCl is carried (F64).
"""
from __future__ import annotations

from smartchem.decompiler_conditions import (
    _ASPIRIN_PROCEDURE,
    _ISOPENTYL_PROCEDURE,
    _PARACETAMOL_PROCEDURE,
)
from smartchem.experiment.stock import Phase, StockQuantity
from smartchem.material_spec import (
    CompositionConstraint,
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    HydrationState,
    MaterialSpecification,
    SaturationState,
    SpecVerdict,
    StateClaim,
    Tolerance,
    compare_specification,
)

_SQ = EvidenceKind.SOURCE_QUOTED
_ALL = (_ISOPENTYL_PROCEDURE, _ASPIRIN_PROCEDURE, _PARACETAMOL_PROCEDURE)


def _uses(procedure):
    return [(op.ordinal, use) for op in procedure.operations for use in op.material_uses]


def _by_name(procedure, name):
    return [(o, u) for o, u in _uses(procedure) if u.name == name]


# -- isopentyl: each use's specification, exactly ------------------------------------------------------------

def test_isopentyl_glacial_acetic_acid_is_a_quoted_neat_state_with_no_number() -> None:
    [(ordinal, use)] = _by_name(_ISOPENTYL_PROCEDURE, "acetic acid")
    assert ordinal == 1
    assert use.specification == MaterialSpecification(
        # Wave C: the page never says "undiluted" -- glacial -> NEAT is the author's reading (AUTHOR_INFERRED),
        # which by D6 can never certify a FIT on its own.
        states=(StateClaim(
            DilutionState.NEAT, EvidenceKind.AUTHOR_INFERRED,
            note="'glacial' acetic acid is by definition undiluted acetic acid (species-specific term, the "
                 "author's reading of the quoted word)"),),
    )
    assert use.specification.composition is None
    assert use.phase is Phase.LIQUID


def test_isopentyl_conc_sulfuric_acid_is_unresolved_never_a_number() -> None:
    [(ordinal, use)] = _by_name(_ISOPENTYL_PROCEDURE, "sulfuric acid")
    assert ordinal == 1
    assert use.specification == MaterialSpecification(unresolved_terms=("conc.",))
    verdict, _ = compare_specification(use.specification, None)
    assert verdict is SpecVerdict.UNDETERMINED


def test_isopentyl_bicarbonate_is_a_nominal_5pct_of_unknown_basis_in_solution() -> None:
    hits = _by_name(_ISOPENTYL_PROCEDURE, "sodium bicarbonate")
    assert [o for o, _ in hits] == [5, 5]  # "25 mL ... twice": two draws, same spec
    for _, use in hits:
        spec = use.specification
        assert spec.composition == CompositionConstraint(
            "0.05", "0.05", ConcentrationBasis.UNKNOWN, Tolerance.NOMINAL_UNSTATED_TOLERANCE, _SQ,
            note=spec.composition.note)
        assert "5% sodium bicarbonate solution" in spec.composition.note
        assert [(c.state, c.evidence) for c in spec.states] == [(DilutionState.SOLUTION, _SQ)]
        assert spec.unresolved_terms == ()
        assert use.quantity == StockQuantity.of("25", "mL")
        assert use.formulation == "5% solution"  # raw source words; "aqueous" is not in the source
        assert use.phase is Phase.AQUEOUS_SOLUTION  # author inference, flagged in the source comment


def test_isopentyl_saturated_nacl_is_a_state_claim_and_carries_the_sourced_5ml() -> None:
    [(ordinal, use)] = _by_name(_ISOPENTYL_PROCEDURE, "sodium chloride")
    assert ordinal == 7
    spec = use.specification
    assert spec.composition is None
    assert [(c.state, c.evidence) for c in spec.states] == [
        (SaturationState.SATURATED, _SQ), (DilutionState.SOLUTION, _SQ)]
    assert use.quantity == StockQuantity.of("5", "mL")  # F64: "add 5 mL of saturated aqueous sodium chloride"


def test_isopentyl_anhydrous_mgso4_is_a_hydration_state_not_an_assay() -> None:
    [(ordinal, use)] = _by_name(_ISOPENTYL_PROCEDURE, "magnesium sulfate")
    assert ordinal == 8
    spec = use.specification
    assert spec.composition is None
    assert [(c.state, c.evidence) for c in spec.states] == [(HydrationState.ANHYDROUS, _SQ)]
    assert use.quantity == StockQuantity.of("2", "g")


def test_isopentyl_alcohol_is_no_longer_authored_neat() -> None:
    [(_, use)] = _by_name(_ISOPENTYL_PROCEDURE, "isopentyl alcohol")
    assert use.formulation is None
    assert use.specification is None  # no dilution claim: the source says only "15 mL"
    assert use.phase is Phase.LIQUID
    assert use.quantity == StockQuantity.of("15", "mL")


def test_isopentyl_waters_carry_no_specification() -> None:
    waters = _by_name(_ISOPENTYL_PROCEDURE, "cold water") + _by_name(_ISOPENTYL_PROCEDURE, "water")
    assert sorted(u.quantity.value for _, u in waters) == ["10", "25", "55"]
    assert all(u.specification is None and u.formulation is None for _, u in waters)


# -- corpus-wide discipline ------------------------------------------------------------------------------------

def test_no_use_anywhere_is_authored_neat() -> None:
    for proc in _ALL:
        for _, use in _uses(proc):
            assert (use.formulation or "").lower() != "neat"


def test_every_formulation_has_a_typed_specification() -> None:
    """D3/F69: a non-empty raw formulation with no typed spec would project UNKNOWN by law -- but the corpus
    author types every one explicitly (a spec or explicit unresolved_terms), so none relies on the fallback."""
    for proc in _ALL:
        for _, use in _uses(proc):
            if use.formulation is not None:
                assert type(use.specification) is MaterialSpecification, use.name


def test_every_conc_use_carries_unresolved_terms_and_no_number() -> None:
    conc = [(p, u) for p in _ALL for _, u in _uses(p)
            if u.formulation is not None and u.formulation.lower().startswith("conc")]
    # isopentyl H2SO4, aspirin H2SO4, aspirin reprecipitation HCl, paracetamol HCl (1.5 mL + "a few more drops")
    assert sorted((p.reaction_scope.split(":")[0], u.name) for p, u in conc) == sorted([
        ("Fischer esterification", "sulfuric acid"), ("acetylation", "sulfuric acid"),
        ("acetylation", "hydrochloric acid"), ("acetylation", "hydrochloric acid"),
        ("acetylation", "hydrochloric acid")])
    for _, use in conc:
        assert use.specification.unresolved_terms == (use.formulation,)
        assert use.specification.composition is None
        assert use.specification.states == ()


def test_no_numeric_composition_claims_a_basis_the_source_never_stated() -> None:
    """The only number in the corpus is the isopentyl 5% bicarbonate, and its basis stays UNKNOWN."""
    comps = [(u.name, u.specification.composition) for p in _ALL for _, u in _uses(p)
             if u.specification is not None and u.specification.composition is not None]
    assert [n for n, _ in comps] == ["sodium bicarbonate", "sodium bicarbonate"]
    assert all(c.basis is ConcentrationBasis.UNKNOWN for _, c in comps)


def test_every_requirement_claim_is_source_quoted() -> None:
    for proc in _ALL:
        for _, use in _uses(proc):
            spec = use.specification
            if spec is None:
                continue
            # the ONE author inference (glacial -> NEAT) is labelled as such; everything else is quoted
            assert all(c.evidence is _SQ or (use.name == "acetic acid" and c.evidence is EvidenceKind.AUTHOR_INFERRED)
                       for c in spec.states)
            assert spec.composition is None or spec.composition.evidence is _SQ


def test_paracetamol_hcl_is_an_exact_draw_plus_an_unquantified_draw() -> None:
    """"add 1.5 mL of concentrated hydrochloric acid" + "Add a few more drops of concentrated acid if necessary"
    -> two uses on op1, the second with quantity=None, so the demand can never project EXACT 1.5 mL."""
    hits = _by_name(_PARACETAMOL_PROCEDURE, "hydrochloric acid")
    assert [o for o, _ in hits] == [1, 1]
    assert [u.quantity for _, u in hits] == [StockQuantity.of("1.5", "mL"), None]
    for _, use in hits:
        assert use.formulation == "concentrated"
        assert use.specification == MaterialSpecification(unresolved_terms=("concentrated",))


def test_paracetamol_filter_paper_rinse_is_carried_and_conditional_norit_is_not() -> None:
    op3 = _PARACETAMOL_PROCEDURE.operations[2]
    assert op3.ordinal == 3 and op3.kind.value == "FILTER"
    assert [(u.name, u.quantity) for u in op3.material_uses] == [("water", StockQuantity.of("1", "mL"))]
    norit = _by_name(_PARACETAMOL_PROCEDURE, "decolorizing charcoal (Norit)")
    assert len(norit) == 1 and norit[0][1].quantity is None  # the conditional 0.1 g is not a demand


def test_aspirin_reprecipitation_auxiliaries_are_typed_from_the_source() -> None:
    [(o_b, bicarb)] = _by_name(_ASPIRIN_PROCEDURE, "sodium bicarbonate")
    assert o_b == 6
    assert bicarb.quantity == StockQuantity.of("25", "mL")
    assert bicarb.specification.composition is None
    assert [(c.state, c.evidence) for c in bicarb.specification.states] == [
        (SaturationState.SATURATED, _SQ), (DilutionState.SOLUTION, _SQ)]
    [(o_h, hcl)] = _by_name(_ASPIRIN_PROCEDURE, "hydrochloric acid")
    assert o_h == 8
    assert hcl.quantity is None  # "ca 3.5 mL" is approximate -> never an exact demand
    assert hcl.specification == MaterialSpecification(unresolved_terms=("conc.",))
    waters = [(o, u.quantity) for o, u in _by_name(_ASPIRIN_PROCEDURE, "water")]
    assert (8, StockQuantity.of("10", "mL")) in waters
    rinses = [(o, u.quantity) for o, u in _by_name(_ASPIRIN_PROCEDURE, "cold water")]
    assert [q for o, q in rinses if o == 9] == [StockQuantity.of("5", "mL")] * 3


def test_added_ops_leave_readiness_completeness_unchanged() -> None:
    from smartchem.experiment.readiness import procedure_representation_is_complete

    for proc in _ALL:
        assert procedure_representation_is_complete(proc) and proc.is_sourced
