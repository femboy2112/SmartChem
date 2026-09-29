"""v0.9 RC Round V -- Wave-C regression guards (fresh non-author hostile review, parent-integrated fixes).

Every test reproduces a break a Wave-C adversary PROVED on the real object path, then pins the fix:

* C1-K1 -- a state claim (NEAT / SATURATED / ANHYDROUS) is scoped to the COMPONENT it describes; a bottle-level claim
           can no longer certify a species present only as a trace (or pinned at exactly zero);
* C1-K2 -- "provably pure" needs a FRACTION basis + CERTIFYING evidence + an exact lower bound 1 (not a bare ``1.0``,
           not an ASSUMED [1, 1], not a MOLAR [1, 1], not a float that rounds to 1);
* C1-K3 -- a MOLAR / w-v magnitude is never squeezed to 1 (6 M is expressible; two 0.5-0.9 M parts don't read 1 M);
* C1-K4 -- coverage of a raw source material string is EXACT-name only (a second species beside a typed name stays);
* C1-K5 -- one physical package, one inventory entry;
* C1-K6 -- the exact-decimal grammar is ASCII-only;
* C1 nag -- only a SUBSTRATE/REACTANT use stands in for a leaf reactant's consumption;
* C2-1  -- a CapabilityAssessment whose ``overall`` is not the fold of its axes cannot be constructed;
* C2-4  -- a raw kernel input self-labelled DERIVED/CLAMPED needs a locator; FRACTION/PERCENT inputs can't carry MOLAR;
* C2-5  -- COMPLEMENT is ASSUMED (binary-mixture premise), never an inherited sourced strength.
"""
from __future__ import annotations

import dataclasses

import pytest

from smartchem.capability.assess import _material_axis, _species_key_in, assess
from smartchem.capability.enums import CapabilityStatus
from smartchem.capability.presets import custom
from smartchem.capability.quantity import QuantityDemand
from smartchem.capability.requirements import MaterialRequirement, _name_covers
from smartchem.data import material_library as ml
from smartchem.data.derived_evidence import DerivationKernel, InputUnit, IntervalEvidence, TypedInput
from smartchem.experiment.stock import (
    MATERIAL_COMPONENT_SCHEMA,
    STOCK_MATERIAL_SCHEMA,
    MaterialComponent,
    Phase,
    StockMaterial,
    StockQuantity,
)
from smartchem.identity_parse import InputKind, resolve_target
from smartchem.material_spec import (
    CompositionConstraint,
    ConcentrationBasis,
    DilutionState,
    EvidenceKind,
    HydrationState,
    MaterialSpecification,
    SaturationState,
    StateClaim,
    Tolerance,
    exact_fraction,
)

MF = ConcentrationBasis.MASS_FRACTION
_Q = StockQuantity.of


def _mol(name):
    return resolve_target(name, InputKind.AUTO).canonical()


def _ud(lo, hi, basis=MF):
    return IntervalEvidence.build(
        kernel=DerivationKernel.USER_DECLARED_V1, basis=basis,
        inputs=(TypedInput("low", lo, InputUnit.FRACTION, EvidenceKind.USER_DECLARED),
                TypedInput("high", hi, InputUnit.FRACTION, EvidenceKind.USER_DECLARED)),
        domain_of_validity="wave-c fixture: operator declaration")


def _bottle(mid, comps, qty="500", unit="mL", phase=Phase.LIQUID):
    return StockMaterial(STOCK_MATERIAL_SCHEMA, mid, mid, tuple(comps), phase, "wave-c fixture",
                         quantity=_Q(qty, unit))


def _req(identity=None, name=None, known=(("mL", "20"),), spec=None, phase=None):
    return MaterialRequirement(identity=identity, phase=phase, quantity=QuantityDemand(tuple(known), 0),
                               role="fixture", evidence_source="wave-c fixture", name=name,
                               specification=spec or MaterialSpecification())


_NEAT_SQ = MaterialSpecification(states=(StateClaim(DilutionState.NEAT, EvidenceKind.SOURCE_QUOTED),))
_NEAT_UD = (StateClaim(DilutionState.NEAT, EvidenceKind.USER_DECLARED),)


# -- C1-K1: component-scoped states --------------------------------------------------------------------------------

def test_k1_a_neat_solvent_bottle_never_certifies_its_trace_impurity():
    acetic = _mol("acetic acid")
    acetone = _mol("acetone")
    for trace_hi in ("0.00002", "0"):
        bottle = _bottle("acetone-acs", (
            MaterialComponent.evidenced(acetone, "active", _ud("0.99998", "1"), states=_NEAT_UD),
            MaterialComponent.evidenced(acetic, "impurity", _ud("0", trace_hi)),
        ))
        status = _material_axis((_req(identity=acetic, spec=_NEAT_SQ),), (bottle,)).status
        assert status is not CapabilityStatus.FIT, trace_hi


@pytest.mark.parametrize("state", [SaturationState.SATURATED, HydrationState.ANHYDROUS])
def test_k1_states_on_the_principal_do_not_transfer_to_a_trace_component(state):
    principal = MaterialComponent.evidenced(
        "sodium bicarbonate", "active", _ud("0.08", "0.09"), states=(StateClaim(state, EvidenceKind.USER_DECLARED),))
    trace = MaterialComponent.evidenced("sodium chloride", "impurity", _ud("0", "0.0001"))
    bottle = _bottle("other-salt", (principal, trace), phase=Phase.AQUEOUS_SOLUTION)
    spec = MaterialSpecification(states=(StateClaim(state, EvidenceKind.SOURCE_QUOTED),))
    assert _material_axis((_req(name="sodium chloride", spec=spec),), (bottle,)).status is not CapabilityStatus.FIT


def test_k1_control_the_species_own_certified_claim_still_certifies():
    """K1's positive control: the principal's OWN certified NEAT claim still certifies the NEAT state. Since D24.5
    (Wave-C' B1) a state word alone never makes the draw commensurable, so the quantity is carried by a certified
    composition floor on the SAME requirement -- the state question and the quantity question stay separate."""
    acetic = _mol("acetic acid")
    bottle = _bottle("glacial", (MaterialComponent.evidenced(acetic, "active", _ud("0.995", "1"), states=_NEAT_UD),))
    state_only = _material_axis((_req(identity=acetic, spec=_NEAT_SQ),), (bottle,))
    assert state_only.status is CapabilityStatus.UNKNOWN  # NEAT certifies the state, never the 20 mL draw (D24.5)
    assert "specification SATISFIES" in " ".join(state_only.reasons)
    floor = CompositionConstraint("0.995", "1", MF, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED)
    spec = MaterialSpecification(composition=floor, states=_NEAT_SQ.states)
    assert _material_axis((_req(identity=acetic, spec=spec),), (bottle,)).status is CapabilityStatus.FIT


# -- C1-K2: the pure-bottle rule ---------------------------------------------------------------------------------------

def test_k2_no_uncertified_or_non_fraction_one_is_a_proven_pure_draw():
    alcohol = _mol("isopentyl alcohol")
    req = _req(identity=alcohol, known=(("mL", "15"),))
    candidates = {
        "bare 1.0 (UNKNOWN evidence, UNKNOWN basis)": MaterialComponent.of_molecule(alcohol, "active", 1.0, 1.0),
        "ASSUMED [1, 1]": MaterialComponent.evidenced(alcohol, "active", IntervalEvidence.build(
            kernel=DerivationKernel.ASSUMED_BAND_V1, basis=MF,
            inputs=(TypedInput("low", "1", InputUnit.FRACTION, EvidenceKind.ASSUMED),
                    TypedInput("high", "1", InputUnit.FRACTION, EvidenceKind.ASSUMED)),
            domain_of_validity="assumed")),
        "MOLAR [1, 1] declared": dataclasses.replace(
            MaterialComponent.of_molecule(alcohol, "active", 1.0, 1.0), basis=ConcentrationBasis.MOLAR),
    }
    for label, comp in candidates.items():
        assert _material_axis((req,), (_bottle("b", (comp,)),)).status is not CapabilityStatus.FIT, label


def test_k2_a_float_that_rounds_to_one_is_not_evidence_of_one():
    alcohol = _mol("isopentyl alcohol")
    near = _ud("0.99999999999999999", "1")
    with pytest.raises(ValueError, match="does not equal"):
        # the float slot would read 1.0; the exact record says < 1 -- the two may not disagree
        MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "x", "active", 1.0, 1.0, MF, near)
    comp = MaterialComponent.evidenced(alcohol, "active", near)
    view = _bottle("n", (comp,)).spec_view(alcohol)
    assert view.interval[0] < 1


def test_k2_control_a_certified_fraction_one_bottle_is_a_proven_draw():
    alcohol = _mol("isopentyl alcohol")
    bottle = _bottle("pure", (MaterialComponent.evidenced(alcohol, "active", _ud("1", "1")),))
    assert _material_axis((_req(identity=alcohol, known=(("mL", "15"),)),), (bottle,)).status is CapabilityStatus.FIT


# -- C1-K3: non-fraction magnitudes ---------------------------------------------------------------------------------------

def test_k3_molar_components_are_not_capped_at_one_and_six_molar_is_expressible():
    six = MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "sodium hydroxide", "active", 6.0, 6.0,
                            ConcentrationBasis.MOLAR)
    assert six.max_fraction == 6.0
    with pytest.raises(ValueError):
        MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "x", "active", 6.0, 6.0, MF)  # a mass fraction can't exceed 1
    part = MaterialComponent(MATERIAL_COMPONENT_SCHEMA, "hydrochloric acid", "active", 0.5, 0.9,
                             ConcentrationBasis.MOLAR)
    bottle = _bottle("hcl", (part, part), phase=Phase.AQUEOUS_SOLUTION)
    view = bottle.spec_view("hydrochloric acid")
    assert view.interval == (exact_fraction("1"), exact_fraction("1.8"))
    assert bottle.active_fraction_interval("hydrochloric acid")[1] == pytest.approx(1.8)


# -- C1-K4: exact-name coverage -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw", ["dilute sodium hydroxide in water", "benzene/water", "benzene (water co-solvent)"])
def test_k4_a_second_species_beside_a_typed_name_is_not_covered(raw):
    assert not _name_covers("water", raw)
    assert _name_covers("water", "  Water ")


# -- C1-K5: one package, one entry ------------------------------------------------------------------------------------------

def test_k5_a_duplicated_package_is_refused():
    bottle = ml.glacial_acetic_acid(quantity=_Q("10", "mL"))
    with pytest.raises(ValueError, match="twice"):
        custom(profile_id="dup", material_inventory=(bottle, bottle))


# -- C1-K6: ASCII grammar ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["５", "٩٩.٥", "９９.5"])
def test_k6_non_ascii_digits_are_refused(value):
    with pytest.raises(ValueError):
        exact_fraction(value)
    with pytest.raises(ValueError):
        StockQuantity.of(value, "mL")


# -- C2-1: overall must be the fold of the axes --------------------------------------------------------------------------------

def test_c2_a_self_contradictory_assessment_cannot_be_constructed():
    from smartchem.capability.requirements import RouteCapabilityRequirements, WasteRequirement  # noqa: F401
    from tests.test_v0_9_round_v_core import _ps_readiness, _reqs

    real = assess(custom(profile_id="c2", no_limit_dimensions=frozenset({"budget"})), _reqs(), _ps_readiness())
    blocked_axis = dataclasses.replace(real.material, status=CapabilityStatus.BLOCKED)
    with pytest.raises(ValueError, match="fold of its axes"):
        dataclasses.replace(real, material=blocked_axis, overall=CapabilityStatus.FIT)
    with pytest.raises(ValueError, match="fold of its axes"):
        dataclasses.replace(real, overall=CapabilityStatus.FIT, readiness_tier="REACTION_VOUCHED")


# -- C2-4 / C2-5: evidence-input honesty ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("kind", [EvidenceKind.DERIVED, EvidenceKind.CLAMPED, EvidenceKind.SOURCE_QUOTED])
def test_c2_a_sourced_input_kind_needs_a_locator(kind):
    with pytest.raises(ValueError, match="source_locator"):
        TypedInput("floor", "99.9", InputUnit.PERCENT, kind)


def test_c2_percent_inputs_cannot_carry_a_molar_basis():
    with pytest.raises(ValueError, match="MOLAR"):
        IntervalEvidence.build(
            kernel=DerivationKernel.IDENTITY_SOURCE_QUOTED_V1, basis=ConcentrationBasis.MOLAR,
            inputs=(TypedInput("low", "6", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, "loc"),
                    TypedInput("high", "6", InputUnit.PERCENT, EvidenceKind.SOURCE_QUOTED, "loc")),
            source_locators=("loc",), domain_of_validity="x")


def test_c2_complement_of_a_sourced_assay_is_assumed():
    h2so4 = ml.INTERVAL_EVIDENCE["sulfuric-acid-concentrated-acs/acid"] if (
        "sulfuric-acid-concentrated-acs/acid" in ml.INTERVAL_EVIDENCE) else next(
        ev for key, ev in ml.INTERVAL_EVIDENCE.items() if key.startswith("sulfuric-acid"))
    water = IntervalEvidence.build(kernel=DerivationKernel.COMPLEMENT_V1, basis=MF, parent=h2so4,
                                   domain_of_validity="binary premise")
    assert water.kind is EvidenceKind.ASSUMED


# -- C1 nag: a wash never erases a leaf reactant's consumption ------------------------------------------------------------

def test_only_a_stoichiometric_use_stands_in_for_a_leaf_reactant():
    from smartchem.capability import requirements as rq
    assert rq._STOICHIOMETRIC_ROLES == frozenset({
        rq.ProcedureMaterialRole.SUBSTRATE, rq.ProcedureMaterialRole.REACTANT})


def test_species_key_helper_is_still_structure_first():
    acetic = _mol("acetic acid")
    bottle = _bottle("g", (MaterialComponent.evidenced(acetic, "active", _ud("1", "1")),))
    assert _species_key_in(_req(identity=acetic, name="acetic acid"), bottle) is acetic


def test_composition_floor_on_an_unknown_basis_stock_is_never_fit():
    acetic = _mol("acetic acid")
    spec = MaterialSpecification(composition=CompositionConstraint(
        "0.99", "1", MF, Tolerance.FLOOR, EvidenceKind.SOURCE_QUOTED))
    bottle = _bottle("u", (MaterialComponent.of_molecule(acetic, "active", 0.995, 1.0),))
    assert _material_axis((_req(identity=acetic, spec=spec),), (bottle,)).status is CapabilityStatus.UNKNOWN
