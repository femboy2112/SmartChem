"""OPERATION XX §2B/§2C -- the world certificate must bind a reaction rate law's OPERATIVE
physics, not merely the container holding it.

A post-construction mutation of a rate constant, equilibrium quotient, or a species the rate
law reads must MOVE the world certificate and be caught at integrate() as StaleCertificateError.
A law that cannot supply a descriptor is marked UNVERIFIABLE (fail-closed), never forged.

RED-first: before this fix, mutating BicarbonateDissolutionRate.k_diss after construction left
the world certificate unchanged while the dissolution RHS changed 30x (certificate blind to the
rate law).  See the proof probe archived with the OPERATION XX dossier.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_coupled import (
    StaleCertificateError,
    _rate_law_descriptor,
)
from experiments.sandbox_foundation.general_kernel import (
    RATE_UNKNOWN,
    MassActionIrreversible,
    MassActionReversible,
    RateLaw,
)
from experiments.sandbox_foundation.unified_chemical_world import (
    BicarbonateDissolutionRate,
    UnifiedParams,
    _build_species,
    build_unified_world,
)


def _world():
    sp = _build_species()
    return build_unified_world(UnifiedParams(), sp, valve_open=True, sealed=False).world, sp


def _dissolution_rate_law(world):
    # cell B holds the single dissolution reaction (NaHCO3(s) -> Na+ + HCO3-)
    return world._comp["B"].system.reactions[0].rate_law


# -------------------------------------------------- §2A: the named counterexample, now detected
def test_k_diss_mutation_after_construction_is_caught():
    world, _ = _world()
    world._verify_world_certificate()                       # clean at construction
    rl = _dissolution_rate_law(world)
    assert isinstance(rl, BicarbonateDissolutionRate)
    rl.k_diss = rl.k_diss * 10.0 + 1.0                      # change the dissolution physics
    assert world._compute_world_certificate() != world._world_certificate
    with pytest.raises(StaleCertificateError):
        world._verify_world_certificate()


def test_qsp_mutation_after_construction_is_caught():
    world, _ = _world()
    _dissolution_rate_law(world).Qsp *= 2.0
    with pytest.raises(StaleCertificateError):
        world._verify_world_certificate()


def test_rate_law_species_reference_mutation_is_caught():
    world, sp = _world()
    _dissolution_rate_law(world).na = sp.HCO3               # swap the Na+ reference the rate law reads
    with pytest.raises(StaleCertificateError):
        world._verify_world_certificate()


# -------------------------------------------------- §2C: completeness (distinct->distinct, equal->equal)
def test_distinct_k_diss_gives_distinct_world_certificate():
    sp = _build_species()
    w1 = build_unified_world(UnifiedParams(k_diss_molpLps=0.05), sp, valve_open=True, sealed=False).world
    w2 = build_unified_world(UnifiedParams(k_diss_molpLps=0.07), sp, valve_open=True, sealed=False).world
    # the ONLY difference is k_diss; before the fix these collided on one certificate
    assert w1._world_certificate != w2._world_certificate


def test_identical_worlds_give_equal_world_certificate():
    sp = _build_species()
    w1 = build_unified_world(UnifiedParams(), sp, valve_open=True, sealed=False).world
    w2 = build_unified_world(UnifiedParams(), sp, valve_open=True, sealed=False).world
    assert w1._world_certificate == w2._world_certificate


# -------------------------------------------------- descriptor-level binding (unit)
def test_mass_action_descriptors_bind_their_constants():
    assert MassActionIrreversible(k=1.0).descriptor() != MassActionIrreversible(k=2.0).descriptor()
    assert MassActionIrreversible(k=1.0).descriptor() == MassActionIrreversible(k=1.0).descriptor()
    assert MassActionReversible(kf=1.0, kr=2.0).descriptor() != MassActionReversible(kf=1.0, kr=3.0).descriptor()


def test_bicarbonate_descriptor_binds_params_and_species():
    sp = _build_species()
    a = BicarbonateDissolutionRate(k_diss=0.05, Qsp=1.0, solid=sp.solid, na=sp.Nap, hco3=sp.HCO3)
    assert a.descriptor() != BicarbonateDissolutionRate(
        k_diss=0.06, Qsp=1.0, solid=sp.solid, na=sp.Nap, hco3=sp.HCO3).descriptor()
    assert a.descriptor() != BicarbonateDissolutionRate(
        k_diss=0.05, Qsp=2.0, solid=sp.solid, na=sp.Nap, hco3=sp.HCO3).descriptor()
    assert a.descriptor() != BicarbonateDissolutionRate(
        k_diss=0.05, Qsp=1.0, solid=sp.solid, na=sp.HCO3, hco3=sp.HCO3).descriptor()  # species bound


# -------------------------------------------------- §2B: opaque law fails closed, not forged
def test_opaque_rate_law_is_marked_unverifiable_not_forged():
    class _OpaqueLaw(RateLaw):
        def __init__(self, secret):
            self.secret = secret

        def evaluate(self, reaction, concentrations):
            return self.secret

    d = _rate_law_descriptor(_OpaqueLaw(1.0))
    assert d[0] == "UNVERIFIABLE_RATE_LAW"                   # not a forged stable identity
    assert _rate_law_descriptor(RATE_UNKNOWN) == "RATE_UNKNOWN"
    assert _rate_law_descriptor(MassActionIrreversible(k=1.0))[0] == "MassActionIrreversible"
