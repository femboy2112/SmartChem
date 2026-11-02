"""OPERATION XVI P0.1 -- close the chemical-identity laundering gap in InterfaceTransfer.

An interface is a PASSIVE physical transfer of ONE chemical substance between compartments/phases.  Validating it by
elemental composition + charge alone is insufficient: ethanol and dimethyl ether are both C2H6O, charge 0, yet are
different substances.  A passive transfer between them would be a chemical REACTION smuggled in as transport -- a
direct violation of the chemistry/transport boundary, and (worse) it is stamped STRUCTURALLY_CONSERVING because atoms
balance.  The repair: a species carries a phase-independent ``substance`` identity (an explicitly-typed, auditable
declaration, NOT the free-text display name inferred structurally), and an interface requires BOTH the existing
composition+charge match (necessary) AND a substance match (the constitutional discriminator).  CONSERVATION MUST
NEVER SUBSTITUTE FOR CHEMICAL IDENTITY.

These pins are RED on the pre-XVI code (which accepts the ethanol->DME transfer) and GREEN after the repair.
"""
from __future__ import annotations

import pytest

from experiments.sandbox_foundation.general_coupled import (
    Compartment,
    CoupledError,
    CoupledWorld,
    InterfaceTransfer,
)
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species


# ---------------------------------------------------------------- the laundering counterexample
def _ethanol():
    return Species.of("ethanol", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS)


def _dme():
    return Species.of("dimethyl ether", {"C": 2, "H": 6, "O": 1}, charge=0, phase=Phase.AQUEOUS)


def test_isomer_passive_transfer_is_refused():
    """Ethanol and dimethyl ether: identical composition/charge, DIFFERENT substance -> a passive interface is a
    reaction in disguise and MUST be refused (RED pre-XVI: the interface currently constructs)."""
    ethanol, dme = _ethanol(), _dme()
    assert ethanol.composition == dme.composition and ethanol.charge == dme.charge   # the trap: atoms match
    assert ethanol.substance != dme.substance                                        # but the substance does not
    with pytest.raises(CoupledError):
        InterfaceTransfer("launder", "A", "B", ethanol, dme, k_transfer=0.5)


def test_isomer_laundering_cannot_evolve_through_the_world():
    """The full public path: building a CoupledWorld with the isomer interface must fail (no trajectory can launder
    ethanol into dimethyl ether and be stamped STRUCTURALLY_CONSERVING)."""
    ethanol, dme = _ethanol(), _dme()
    cell_a = Compartment("A", ChemicalSystem([ethanol], [], volume_L=1.0))
    cell_b = Compartment("B", ChemicalSystem([dme], [], volume_L=1.0))
    with pytest.raises(CoupledError):
        world = CoupledWorld([cell_a, cell_b],
                             interfaces=[InterfaceTransfer("launder", "A", "B", ethanol, dme, k_transfer=0.5)])
        world.integrate({"A": {ethanol: 1.0}, "B": {dme: 0.0}}, duration=5.0, n_steps=10, scheme="lie")


# ---------------------------------------------------------------- genuine same-substance transfers still work
def test_same_substance_phase_transfer_is_supported():
    """CO2(aq) <-> CO2(g): same substance declared, differ only in phase -> a legitimate Henry transfer, supported."""
    co2aq = Species.of("CO2(aq)", {"C": 1, "O": 2}, charge=0, phase=Phase.AQUEOUS, substance="CO2")
    co2g = Species.of("CO2(g)", {"C": 1, "O": 2}, charge=0, phase=Phase.GAS, substance="CO2")
    assert co2aq.substance == co2g.substance == "CO2"
    iface = InterfaceTransfer("henry", "aq", "gas", co2aq, co2g, k_transfer=0.5, partition=1.0)
    assert iface.name == "henry"


def test_same_species_diffusion_still_works():
    """A <-> A across two cells (same Species object, so same substance): plain diffusion, must remain supported."""
    A = Species.of("A", {"R": 1}, charge=0, phase=Phase.AQUEOUS)
    iface = InterfaceTransfer("diffuse", "c0", "c1", A, A, k_transfer=0.5)
    assert iface.name == "diffuse"


# ---------------------------------------------------------------- the substance key cannot launder a composition change
def test_substance_match_still_requires_composition_match():
    """A shared substance tag must NOT override the composition/charge necessary condition: two species declared the
    same substance but with different composition is refused (the tag cannot launder a stoichiometry change)."""
    a = Species.of("X", {"C": 1}, charge=0, phase=Phase.AQUEOUS, substance="X")
    b = Species.of("X2", {"C": 2}, charge=0, phase=Phase.AQUEOUS, substance="X")   # same substance, DIFFERENT formula
    with pytest.raises(CoupledError):
        InterfaceTransfer("bad", "c0", "c1", a, b, k_transfer=0.5)


def test_default_substance_is_the_name_and_fails_closed():
    """With no explicit substance, the identity defaults to the species name (fail-closed): two differently-named
    same-formula species do NOT silently become transferable."""
    ethanol, dme = _ethanol(), _dme()
    assert ethanol.substance == "ethanol" and dme.substance == "dimethyl ether"
