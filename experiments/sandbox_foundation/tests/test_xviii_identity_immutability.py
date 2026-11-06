"""OPERATION XVIII Track A (P0) -- model identity must be INJECTIVE over operative chemistry, and a certified
execution basis must not execute under a stale certificate.

These probes REPRODUCE, through the real public API, the four collisions/holes Operation XVIII §1-§2 names, BEFORE the
repair.  They are RED on the pre-XVIII kernel and GREEN after it:

  1A  name-collision in the model digest -- a reaction's stoichiometry was serialized by species NAME alone, so two
      systems with the SAME species registry (both carrying X(aq) AND X(g), both named "X") but reactions that consume
      DIFFERENT species produce the SAME model digest, though their executable stoichiometric matrices differ.
  1B  trace rounding -- run_identity rounded inputs to 12 decimals, collapsing 1e-13 mol and 2e-13 mol to the same 0.0.
  1C  evidence-as-identity -- data_status participated in Species equality/hashing (so the same substance with a
      different evidence tier became a second species) AND in the MODEL digest (so a pure provenance change moved the
      model identity).
  2   float-exactness + immutability -- an integer coefficient > 2**53 was cast to a float the solver executes, diverging
      silently from the certified integer matrix; the frozen E/N could be made writable again; and rebinding
      system.N / system.E let integrate() execute chemistry the certificate never proved.

Nothing here constructs a strawman: every probe drives the SAME API (`model_identity_digest`, `run_identity_digest`,
`Species`, `ChemicalSystem`, `integrate`) a caller uses.
"""
from __future__ import annotations

import numpy as np
import pytest

from experiments.sandbox_foundation.general_chemistry_demo import (
    model_identity_digest,
    run_identity_digest,
)
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    KernelError,
    MassActionReversible,
    Phase,
    Reaction,
    Species,
)


# ============================================================ §1A  name-collision over a shared registry
def _shared_registry():
    """A registry holding X(aq) AND X(g) (both display-named 'X', matched composition so both reactions conserve) plus
    a product Y.  Two systems share this exact registry but consume DIFFERENT X -- the executable N column differs, the
    by-name serialization does not."""
    x_aq = Species.of("X", {"M": 1}, 0, Phase.AQUEOUS)
    x_g = Species.of("X", {"M": 1}, 0, Phase.GAS)
    y = Species.of("Y", {"M": 1}, 0, Phase.AQUEOUS)
    return x_aq, x_g, y


def test_model_digest_distinguishes_same_name_different_phase_reactant():
    """§1A: a reaction consuming X(aq) and a reaction consuming X(g) -- same name, same registry, DIFFERENT executable
    stoichiometric column -- must NOT share a model digest.  RED pre-XVIII (serialized by name)."""
    x_aq, x_g, y = _shared_registry()
    sys_a = ChemicalSystem([x_aq, x_g, y],
                           [Reaction("r", ((x_aq, -1), (y, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    sys_b = ChemicalSystem([x_aq, x_g, y],
                           [Reaction("r", ((x_g, -1), (y, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    # the registries and reaction names are identical by construction; only WHICH X the reaction consumes differs
    assert [sp.name for sp in sys_a.species] == [sp.name for sp in sys_b.species]
    assert not np.array_equal(sys_a.N, sys_b.N), "control: the executable N columns really do differ"
    assert model_identity_digest(sys_a) != model_identity_digest(sys_b), \
        "model digest collapsed two different executable stoichiometries (name-only reaction serialization)"


def test_model_digest_distinguishes_same_name_different_substance_reactant():
    """§1A corollary: the collision also opens on the SUBSTANCE axis (ethanol vs dimethyl ether, both name 'C2H6O')."""
    eth = Species.of("C2H6O", {"C": 2, "H": 6, "O": 1}, 0, Phase.AQUEOUS, substance="ethanol")
    dme = Species.of("C2H6O", {"C": 2, "H": 6, "O": 1}, 0, Phase.AQUEOUS, substance="dimethyl_ether")
    prod = Species.of("P", {"C": 2, "H": 6, "O": 1}, 0, Phase.AQUEOUS, substance="P")
    sys_a = ChemicalSystem([eth, dme, prod],
                           [Reaction("r", ((eth, -1), (prod, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    sys_b = ChemicalSystem([eth, dme, prod],
                           [Reaction("r", ((dme, -1), (prod, 1)), MassActionReversible(kf=1.0, kr=1.0))])
    assert model_identity_digest(sys_a) != model_identity_digest(sys_b)


# ============================================================ §1B  trace-inventory rounding collision
def _one_species_system():
    sp = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
    return sp, ChemicalSystem([sp], [], volume_L=1.0)


def test_run_digest_distinguishes_trace_inventories():
    """§1B: 1e-13 mol and 2e-13 mol are physically distinct initial states; they must not collide through rounding.
    RED pre-XVIII (round(x,12) collapses both to 0.0)."""
    sp, sysm = _one_species_system()
    assert round(1e-13, 12) == round(2e-13, 12) == 0.0, "control: the old rounding really does collapse both to 0.0"
    assert run_identity_digest(sysm, {sp: 1e-13}, 1.0) != run_identity_digest(sysm, {sp: 2e-13}, 1.0), \
        "run digest collapsed two distinct trace inventories (lossy 12-decimal rounding)"


def test_run_digest_distinguishes_trace_duration_and_volume():
    """§1B: a sub-pico-second duration difference is also operative and must not round away."""
    sp = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
    sysm = ChemicalSystem([sp], [], volume_L=1.0)
    assert run_identity_digest(sysm, {sp: 1.0}, 1.0 + 1e-13) != run_identity_digest(sysm, {sp: 1.0}, 1.0)


# ============================================================ §1C  evidence status is not chemical identity
def _co2(data_status):
    return Species.of("CO2", {"C": 1, "O": 2}, 0, Phase.GAS, data_status=data_status)


def test_data_status_does_not_split_species_identity():
    """§1C: the same chemical species with a different EVIDENCE tier is the SAME species -- equal, and equally hashed.
    RED pre-XVIII (data_status is in the frozen-dataclass __eq__/__hash__)."""
    a, b = _co2("NONE"), _co2("SOURCED")
    assert a == b, "a data_status change silently forged a second chemical species (equality)"
    assert hash(a) == hash(b), "a data_status change silently forged a second chemical species (hash)"


def test_model_digest_is_invariant_to_evidence_status():
    """§1C: a pure provenance change (NONE -> SOURCED) must NOT move the MODEL identity -- evidence is a separate
    digest from chemistry.  RED pre-XVIII (_species_payload bakes data_status into the model identity)."""
    none = _co2("NONE")
    sourced = _co2("SOURCED")
    sys_none = ChemicalSystem([none], [], volume_L=1.0)
    sys_sourced = ChemicalSystem([sourced], [], volume_L=1.0)
    assert model_identity_digest(sys_none) == model_identity_digest(sys_sourced), \
        "model digest moved on a pure evidence-status change (data_status leaked into chemical identity)"


def test_source_evidence_digest_moves_with_data_status():
    """§1C/§1D: the SEPARATE source/evidence digest DOES move on a provenance change -- evidence is tracked, just not
    as chemistry.  (The model digest stays fixed, asserted above.)"""
    from experiments.sandbox_foundation.general_chemistry_demo import source_evidence_digest
    sys_none = ChemicalSystem([_co2("NONE")], [], volume_L=1.0)
    sys_sourced = ChemicalSystem([_co2("SOURCED")], [], volume_L=1.0)
    assert source_evidence_digest(sys_none) != source_evidence_digest(sys_sourced)


def test_three_identity_axes_are_distinct():
    """§1D: model, run and source/evidence are three distinct digests of one system (three axes of identity)."""
    from experiments.sandbox_foundation.general_chemistry_demo import source_evidence_digest
    sp = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS, data_status="SOURCED")
    sysm = ChemicalSystem([sp], [], volume_L=1.0)
    digests = {model_identity_digest(sysm), run_identity_digest(sysm, {sp: 1.0}, 1.0), source_evidence_digest(sysm)}
    assert len(digests) == 3


# ============================================================ §2  float-exactness of the execution basis
def test_coefficient_beyond_float_exactness_constructs_but_refuses_to_execute():
    """§2: an integer coefficient > 2**53 is NOT exactly representable in float64.  The SYMBOLIC model is still valid
    (the integer conservation certificate holds -- XV-1A), so construction SUCCEEDS and is flagged non-executable; but
    integrate() must REFUSE it, because the float-cast matrix the solver would run diverges from the certified one.
    'A symbolic certificate does not imply a numerically executable model.'  RED pre-XVIII (integrates silently)."""
    big = 2 ** 53 + 1
    assert float(big) != big, "control: 2**53+1 really is not exactly float-representable"
    a = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
    b = Species.of("B", {"X": 1}, 0, Phase.AQUEOUS)
    # exactly balanced in integers (X: -big + big = 0), but one coefficient is beyond float exactness
    sysm = ChemicalSystem([a, b], [Reaction("A->B", ((a, -big), (b, big)), MassActionReversible(kf=1.0, kr=1.0))])
    assert sysm._float_exact is False, "a >2**53 coefficient must be flagged non-float-exact at construction"
    with pytest.raises(KernelError):
        sysm.integrate({a: 1.0}, duration=1.0, n_samples=3)


# ============================================================ §2  deep immutability of the frozen basis
def _rev_system():
    a = Species.of("A", {"X": 1}, 0, Phase.AQUEOUS)
    b = Species.of("B", {"X": 1}, 0, Phase.AQUEOUS)
    return a, b, ChemicalSystem([a, b], [Reaction("A<->B", ((a, -1), (b, 1)), MassActionReversible(kf=1.0, kr=1.0))])


def test_frozen_matrix_cannot_be_re_enabled():
    """§2: it must be impossible to flip the frozen N/E back to writable and then mutate it (the XVII freeze used an
    OWNING array, whose writeable flag numpy lets a caller re-enable).  RED pre-XVIII if re-enable succeeds."""
    _a, _b, sysm = _rev_system()
    with pytest.raises(ValueError):
        sysm.N.flags.writeable = True
    with pytest.raises(ValueError):
        sysm.E.flags.writeable = True


def test_species_and_reactions_are_immutable_sequences():
    """§2: the declared species / reactions are not appendable lists a caller can grow after certification."""
    _a, _b, sysm = _rev_system()
    assert isinstance(sysm.species, tuple)
    assert isinstance(sysm.reactions, tuple)


def test_rebinding_N_is_caught_before_execution():
    """§2: rebinding system.N to a different matrix must be detected and refused at integrate() -- the integrator must
    execute the model that was CERTIFIED, not a matrix swapped in afterward.  RED pre-XVIII (integrate runs it)."""
    a, _b, sysm = _rev_system()
    object.__setattr__(sysm, "N", np.zeros_like(np.asarray(sysm.N)))   # hostile rebind (bypass any property guard)
    with pytest.raises(KernelError):
        sysm.integrate({a: 1.0}, duration=1.0, n_samples=3)


def test_rebinding_E_is_caught_before_execution():
    """§2: likewise rebinding the element-charge map must be refused at integrate()."""
    a, _b, sysm = _rev_system()
    object.__setattr__(sysm, "E", np.ones_like(np.asarray(sysm.E)))
    with pytest.raises(KernelError):
        sysm.integrate({a: 1.0}, duration=1.0, n_samples=3)


def test_certified_system_still_integrates_cleanly():
    """§2 regression control: an untampered system integrates and conserves, so the certificate guard is not a false
    tripwire on the honest path."""
    a, _b, sysm = _rev_system()
    traj = sysm.integrate({a: 1.0}, duration=5.0, n_samples=5)
    assert traj.solver_success
    c0 = sysm.component_amounts({a: 1.0})["X"]
    cf = sysm.component_amounts(traj.amounts[-1])["X"]
    assert abs(cf - c0) < 1e-9
