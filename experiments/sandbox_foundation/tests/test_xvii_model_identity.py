"""OPERATION XVII Wave B (P0.1 continued) -- MODEL IDENTITY must bind chemical substance.

XVI-P0.1 gave Species a phase-independent ``substance`` key: the constitutional discriminator that elemental formula
cannot supply (ethanol vs dimethyl ether are both C2H6O).  It is chemically OPERATIVE -- the coupled world uses it to
decide which passive transfers are legitimate.  But ``general_chemistry_demo._species_payload`` serialized every other
identity field (name, composition, charge, phase, data_status) and OMITTED ``substance``, so two models differing only
in a species' substance identity produced the SAME model/run digest -- a chemically-operative distinction the engine
executes, invisible to the identity the digest claims to bind.

RED on the pre-XVII serialization; GREEN once substance is bound.
"""
from __future__ import annotations

from experiments.sandbox_foundation.general_chemistry_demo import (
    model_identity,
    model_identity_digest,
    run_identity_digest,
)
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, Species


def _iso_system(substance):
    """A one-species system whose sole species is an ambiguous-formula isomer (C2H6O, q0) tagged with ``substance``.
    Everything EXCEPT substance (name, composition, charge, phase, data_status) is held identical across calls."""
    sp = Species.of("iso", {"C": 2, "H": 6, "O": 1}, 0, Phase.AQUEOUS, substance=substance)
    return ChemicalSystem([sp], [], volume_L=1.0), {sp: 1.0}


def test_model_payload_includes_substance():
    """The serialized model identity must carry the substance key (so the digest can depend on it)."""
    system, _n0 = _iso_system("ethanol")
    payload = model_identity(system)
    assert any("ethanol" in str(entry) for entry in payload["species"]), \
        "model_identity does not serialize the species' substance identity"


def test_model_digest_binds_substance():
    """Two models identical in every field BUT substance (ethanol vs dimethyl ether) must have DIFFERENT model
    digests -- a chemically operative identity change the engine executes cannot be invisible to the model identity."""
    sys_eth, _ = _iso_system("ethanol")
    sys_dme, _ = _iso_system("dimethyl_ether")
    assert model_identity_digest(sys_eth) != model_identity_digest(sys_dme)


def test_run_digest_binds_substance():
    """The run digest embeds the model, so it too must distinguish the two substances."""
    sys_eth, n0_eth = _iso_system("ethanol")
    sys_dme, n0_dme = _iso_system("dimethyl_ether")
    assert run_identity_digest(sys_eth, n0_eth, 1.0) != run_identity_digest(sys_dme, n0_dme, 1.0)


def test_identical_models_have_identical_digest():
    """Determinism control: two independently built models with the SAME substance hash identically (the digest binds
    substance without becoming unstable)."""
    a, _ = _iso_system("ethanol")
    b, _ = _iso_system("ethanol")
    assert model_identity_digest(a) == model_identity_digest(b)


def test_name_change_still_detected():
    """Regression guard: the pre-existing bindings still work -- changing the species NAME (default substance) still
    changes the digest, so adding substance did not displace any field."""
    s1 = Species.of("alpha", {"C": 1}, 0, Phase.AQUEOUS)
    s2 = Species.of("beta", {"C": 1}, 0, Phase.AQUEOUS)
    sys1 = ChemicalSystem([s1], [], volume_L=1.0)
    sys2 = ChemicalSystem([s2], [], volume_L=1.0)
    assert model_identity_digest(sys1) != model_identity_digest(sys2)
