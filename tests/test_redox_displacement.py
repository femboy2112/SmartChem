"""ROUND-17 item 2 (REDOX-DISPLACE-01): the coupled half-reaction combiner (two-species displacement).

The DOW-bromine litmus's enumeration wall: ``Cl2 + 2 Br- -> Br2 + 2 Cl-`` is a 1:2 displacement that
recon PROVED no prior mechanism can produce -- single-species ``redox_edges`` is charge-only on
IDENTICAL atoms (it can never form the Br-Br bond), and ``capped_scissions`` ties reactant-cuts 1:1 and
refuses charged input.  This battery pins that the new combiner reaches it, balances electrons by the
LCM (NOT a 1:1 assumption), conserves mass AND charge, enumerates through the UNCHANGED registry seam,
and stays OPT-IN (absent from the DEFAULT algebra).  Non-vacuity: the stoichiometry tests assert the
exact species multiset, and a differential test shows the old families genuinely cannot.
"""
from __future__ import annotations

from collections import Counter

import pytest

from experiments.redox_displacement_probe import FROZEN_HASH, content_hash
from experiments.redox_displacement_probe import validate as validate_probe
from smartchem.category import Molecule
from smartchem.experiment.step import ExperimentStep
from smartchem.redox_displacement import (
    DISPLACEMENT_SCHEMA,
    HalfReactionCouple,
    RedoxDisplacementEdge,
    RedoxDisplacementProvider,
    combine_half_reactions,
    halogen_couple,
)
from smartchem.structure_descent import ScissionError, capped_scissions, redox_couples
from smartchem.transform_provider import (
    DEFAULT_TRANSFORM_REGISTRY,
    TransformProviderRegistry,
    search_algebra_digest,
)

_CL2 = Molecule.diatomic("Cl", "Cl")
_BR2 = Molecule.diatomic("Br", "Br")
_BRM = Molecule.atom("Br", charge=-1)


def _multiset(molecules):
    return Counter((tuple(sorted(m.formula.items())), m.charge) for m in molecules)


def _dow():
    return combine_half_reactions(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"), target=_BR2)


# --- the wall falls: 1:2 stoichiometry no prior mechanism could reach --------------------------------

def test_the_combiner_reaches_the_1_to_2_stoichiometry_no_prior_mechanism_could():
    synth = ExperimentStep.from_transform(_dow())
    # NON-VACUOUS: the exact species multiset of the DOW displacement.
    assert _multiset(synth.reactants) == Counter({((("Cl", 2),), 0): 1, ((("Br", 1),), -1): 2})
    assert _multiset(synth.products) == Counter({((("Br", 2),), 0): 1, ((("Cl", 1),), -1): 2})
    assert _dow().electrons_transferred == 2


def test_the_single_species_and_capped_families_cannot_reach_the_displacement():
    # The differential (the wall): single-species redox keeps the SAME atoms -- it can never form Br2
    # from bromide (no bond can appear), so it produces only charge-raised bromine, never diatomic Br2.
    oxidations = redox_couples(_BRM, max_electrons=2)
    assert oxidations, "redox_couples must be non-empty here (else the differential is vacuous)"
    assert all(rc.oxidized.formula == {"Br": 1} for rc in oxidations)  # same atoms, never {'Br': 2}
    assert all(len(rc.oxidized.atoms) == 1 for rc in oxidations)
    # capped scission refuses charged input outright (it is a neutral valence-rewrite model), so it
    # cannot even be pointed at bromide.
    with pytest.raises(ScissionError):
        capped_scissions(_BRM, (_CL2,), max_reactant_cuts=1, budget=64)


def test_electron_balancing_uses_the_lcm_not_a_1_to_1_assumption():
    # LCM(1, 2) = 2: a 1-electron reduction couple must be scaled x2 against a 2-electron oxidation.
    fe = HalfReactionCouple(DISPLACEMENT_SCHEMA, "Fe",
                            (Molecule.atom("Fe", charge=3),), (Molecule.atom("Fe", charge=2),), 1)
    sn = HalfReactionCouple(DISPLACEMENT_SCHEMA, "Sn",
                            (Molecule.atom("Sn", charge=4),), (Molecule.atom("Sn", charge=2),), 2)
    edge = combine_half_reactions(reduction=fe, oxidation=sn, target=Molecule.atom("Sn", charge=4))
    assert edge.electrons_transferred == 2
    synth = ExperimentStep.from_transform(edge)
    counts = _multiset(synth.reactants)
    assert counts[((("Fe", 1),), 3)] == 2  # the reduction couple scaled x2 (2 Fe3+)
    assert counts[((("Sn", 1),), 2)] == 1  # the oxidation couple x1 (1 Sn2+)


# --- couple + edge conservation certificates --------------------------------------------------------

def test_a_couple_conserves_mass_and_charge_or_is_refused():
    halogen_couple("Cl")  # a valid couple constructs fine
    # mass asymmetry between the two forms is refused (this family scopes to mass-symmetric couples).
    with pytest.raises(ScissionError, match="mass not conserved"):
        HalfReactionCouple(DISPLACEMENT_SCHEMA, "Cl", (_CL2,), (Molecule.atom("Cl", charge=-1),), 2)
    # a charge that does not match oxidized - n is refused.
    with pytest.raises(ScissionError, match="charge not conserved"):
        HalfReactionCouple(DISPLACEMENT_SCHEMA, "Cl", (_CL2,),
                           (Molecule.atom("Cl", charge=-1), Molecule.atom("Cl", charge=-1)), 3)


def test_a_species_cannot_displace_itself():
    with pytest.raises(ScissionError, match="displace itself"):
        combine_half_reactions(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Cl"), target=_CL2)


def test_the_target_must_be_the_oxidation_couples_elemental_form():
    with pytest.raises(ScissionError, match="oxidised form"):
        combine_half_reactions(reduction=halogen_couple("Cl"), oxidation=halogen_couple("Br"), target=_CL2)


def test_the_displacement_edge_re_checks_conservation_independently():
    # A hand-built, mis-balanced edge (Br2 -> Cl2 conserves nothing) must be refused by the edge's own
    # Reaction certificate -- not only by combine_half_reactions upstream.
    with pytest.raises(ScissionError, match="conserve"):
        RedoxDisplacementEdge(DISPLACEMENT_SCHEMA, _BR2, (_CL2,), (), "Cl", "Br", 2)


def test_the_edge_certificate_verifies_redoxness_not_just_conservation():
    # evil-morty fold: conservation alone does not prove a REDOX displacement.  A directly-built edge must
    # not carry a fabricated electron count, fictitious element labels, or an identity/no-op reaction --
    # electrons_transferred and the element labels ride the digest, so unchecked metadata is identity rot.
    clm, brm, na = Molecule.atom("Cl", charge=-1), Molecule.atom("Br", charge=-1), Molecule.atom("Na", charge=0)
    # a genuinely conserving Br2 + 2Cl- -> Cl2 + 2Br-, but electrons_transferred LIES as 999.
    with pytest.raises(ScissionError, match="electrons_transferred"):
        RedoxDisplacementEdge(DISPLACEMENT_SCHEMA, _BR2, (_CL2, brm, brm), (clm, clm), "Cl", "Br", 999)
    # fictitious element labels on the same real reaction.
    with pytest.raises(ScissionError, match="fabricated element label"):
        RedoxDisplacementEdge(DISPLACEMENT_SCHEMA, _BR2, (_CL2, brm, brm), (clm, clm), "Xx", "Yy", 2)
    # an identity Na -> Na conserves trivially but transfers no electrons: not a displacement.
    with pytest.raises(ScissionError, match="no element changes charge"):
        RedoxDisplacementEdge(DISPLACEMENT_SCHEMA, na, (na,), (), "Na", "Cl", 1)
    # NON-VACUOUS: the correctly-built edge (via combine) still passes the strengthened certificate.
    assert _dow().electrons_transferred == 2


def test_from_transform_reverses_the_displacement_into_a_conserving_synthesis_step():
    step = ExperimentStep.from_transform(_dow())
    # ExperimentStep's own conservation certificate accepted it (it would raise on a mis-balance).
    assert step.target.canonical() == _BR2.canonical()
    assert step.equation()  # renders


def test_forget_is_a_conserving_composition_edge():
    edge = _dow()
    fe = edge.forget()
    # mass + charge conserve at the composition level too (sum over both sides).
    def atoms(terms):
        total: Counter = Counter()
        for items, _charge, coeff in terms:
            for el, n in items:
                total[el] += n * coeff
        return total
    def charge(terms):
        return sum(c * coeff for _items, c, coeff in terms)
    assert atoms(fe.reactants) == atoms(fe.products)
    assert charge(fe.reactants) == charge(fe.products)


# --- the registry seam (Lane B: new family through the UNCHANGED core) -------------------------------

def _wider():
    return TransformProviderRegistry(
        DEFAULT_TRANSFORM_REGISTRY.providers
        + (RedoxDisplacementProvider(couples=(halogen_couple("Cl"), halogen_couple("Br"))),)
    )


def test_the_family_enumerates_through_the_unchanged_registry_seam():
    transforms, complete = _wider().enumerate(_BR2, (_CL2,), budget=64)
    assert complete is True
    displacements = [et for et in transforms if et.witness_kind == "REDOX_DISPLACEMENT"]
    assert displacements, "the displacement must be enumerated through registry.enumerate (non-vacuous)"
    # and it reverses into exactly the DOW synthesis.
    step = ExperimentStep.from_transform(displacements[0].transform)
    assert _multiset(step.products) == Counter({((("Br", 2),), 0): 1, ((("Cl", 1),), -1): 2})


def test_the_provider_is_fail_closed_when_the_oxidant_is_absent_and_never_raises():
    provider = RedoxDisplacementProvider(couples=(halogen_couple("Cl"), halogen_couple("Br")))
    # no reagents at all -> nothing to enumerate, and it does NOT raise (the boundary contract).
    assert provider.enumerate_transforms(_BR2, (), budget=64) == ((), True)
    # a reactant that is not any couple's elemental form -> nothing.
    assert provider.enumerate_transforms(Molecule.atom("Na", charge=0), (_CL2,), budget=64) == ((), True)
    # the required oxidant (Cl2, the reduction couple's elemental form) is absent from the pool -> no
    # pairing is offered (fail-closed): Br2 cannot be displaced by an I2-only pool via the Cl/Br couples.
    transforms, complete = provider.enumerate_transforms(_BR2, (Molecule.diatomic("I", "I"),), budget=64)
    assert complete is True
    assert transforms == ()


def test_the_family_is_opt_in_and_absent_from_the_default_registry():
    assert DEFAULT_TRANSFORM_REGISTRY.provider_ids == ("capped-scission-mediated",)


def test_the_registry_and_search_algebra_digests_move_when_the_displacement_widens_the_algebra():
    base, wider = DEFAULT_TRANSFORM_REGISTRY, _wider()
    assert wider.digest != base.digest  # the algebra widened -> the registry identity moves
    assert search_algebra_digest("route", wider) != search_algebra_digest("route", base)


# --- the committed harness --------------------------------------------------------------------------

def test_the_committed_harness_validates_and_its_hash_is_frozen():
    validate_probe()  # raises if the demonstration does not hold
    assert content_hash() == FROZEN_HASH  # tamper pin: the mechanism's output has not drifted
