"""
The energy functor: where the categorical layer meets the oracle.

``smartchem.category`` gives a symmetric monoidal category of chemical configurations and
conserving reactions. This module gives a **strong monoidal functor** from it to the
additive reals:

    E   : Ob(C) -> R          E(A (x) B) = E(A) + E(B),   E(I) = 0
    dE  : C(A,B) -> R         dE(f : A -> B) = E(B) - E(A)

with the two laws that make it a functor rather than a lookup:

    dE(g . f) = dE(f) + dE(g)         functoriality  (energy is a path integral)
    dE(id_A)  = 0                     identity
    dE(f (x) g) = dE(f) + dE(g)       monoidality

checked in ``tests/test_functor.py``.

Why this is the load-bearing part
---------------------------------
``E(B) - E(A)`` is meaningful **only because every morphism conserves matter and charge.**

Total energy has an arbitrary zero fixed by the atom content: PySCF reports CO at about
-3074 eV, the legacy heuristic at about -11 eV, and both are correct on their own
reference. Subtracting across configurations with *different* atoms would compare two
different arbitrary zeros and produce a number with no physical content -- and it would
look perfectly reasonable, which is worse.

``Reaction.__post_init__`` guarantees ``formula(dom) == formula(cod)``. That is exactly the
condition under which the per-atom offsets appear identically on both sides and cancel.

So the conservation theorem is not a safety check bolted onto a chemistry model. It is the
**precondition that makes the energy functor well defined**, and functoriality is what makes
a multi-step mechanism's energy equal the sum of its steps rather than merely be reported
alongside them. That is the categorical structure doing physical work.
→ ``tests/test_functor.py::TestConservationLicensesSubtraction``

What changed, and why
---------------------
This module used to compute ``E(config) = -sum of dissociation energies of the bonds
present`` -- bond additivity, with the oracle asked about atom *pairs*. That made
bond-additivity an assumption of the architecture rather than a property of a particular
oracle, and it had three consequences that were really one defect: polyatomic species were
structurally unreachable, bond order could not be priced, and the energy of an object was
a sum over edges rather than a property of the object.

The oracle primitive is now ``energy(molecule)``. A bond-additive oracle still answers by
summing over edges (see ``HeuristicOracle``), and a correlated method answers by solving
the electronic structure -- but that is now a visible difference between oracles instead of
a hidden assumption of the framework.

Partial pricing is still refused: if any species in a configuration cannot be priced, the
whole configuration declines. Quietly skipping the species an oracle could not handle would
understate the energy, which is the failure mode where a wrong number looks like a right
one.
"""
from __future__ import annotations

from .category import Config, Reaction
from .oracle.base import Estimate


def configuration_energy(config: Config, oracle) -> Estimate | None:
    """
    ``E(A)``: total energy of a configuration, in eV, on the oracle's own zero.

    This is the object half of the functor, and the sum *is* the monoidal law:
    ``E(A (x) B) = E(A) + E(B)`` holds because a tensor of configurations is the multiset
    union of their species, and this walks that multiset.

    The empty configuration has energy exactly zero -- ``E(I) = 0``, the unit law. That is
    a real value, not a refusal.

    None if any species cannot be priced.
    """
    total = Estimate.zero(getattr(oracle, "name", "?"))
    for molecule in config.species:
        part = oracle.energy(molecule)
        if part is None:
            return None
        total = total + part
    return total


def reaction_energy(reaction: Reaction, oracle) -> Estimate | None:
    """
    ``dE(f)``: enthalpy change of a reaction, in eV. Negative = exothermic.

    Well defined precisely because ``reaction`` conserves matter and charge, so the
    oracle's arbitrary energy zero cancels between ``cod`` and ``dom``. See the module
    docstring; this single subtraction is where the conservation theorem earns its keep.

    None if either side cannot be fully priced.
    """
    dom = configuration_energy(reaction.dom, oracle)
    cod = configuration_energy(reaction.cod, oracle)
    if dom is None or cod is None:
        return None
    # The subtraction is where both the arbitrary energy zero and any systematic model
    # correction cancel. Only what survives that cancellation should widen the error bar.
    delta = (cod - dom).with_honest_uncertainty()
    return Estimate(
        value_ev=delta.value_ev,
        uncertainty_ev=delta.uncertainty_ev,
        method=getattr(oracle, "name", "?"),
        seconds=delta.seconds,
        notes=f"{reaction.dom} -> {reaction.cod}",
        extrapolation_ev=delta.extrapolation_ev,
    )


def bonding_energy(config: Config, oracle) -> Estimate | None:
    """
    Energy of a configuration relative to its own free atoms. Negative = bound.

    Derived from the functor rather than primitive: it is ``dE`` of the (conserving)
    morphism from free atoms to this configuration, so it inherits the same guarantee.
    Kept because "how bound is this?" is the question a chemist actually asks, whereas
    ``configuration_energy`` returns a number on an arbitrary scale.

    None if either the configuration or its free atoms cannot be priced.
    """
    whole = configuration_energy(config, oracle)
    if whole is None:
        return None
    free = configuration_energy(Config.atoms(*_all_atoms(config)), oracle)
    if free is None:
        return None
    return whole - free


def _all_atoms(config: Config) -> tuple[str, ...]:
    """Every atom in the configuration, as free-atom symbols."""
    return tuple(symbol for molecule in config.species for symbol in molecule.atoms)


def is_exothermic(reaction: Reaction, oracle) -> bool | None:
    """
    True / False / None-if-unknown.

    None is a real answer and must not be collapsed to False: "the oracle cannot price
    this" and "this reaction is uphill" are different facts, and conflating them is how an
    unpriceable reaction gets silently reported as unfavourable.
    """
    est = reaction_energy(reaction, oracle)
    return None if est is None else est.value_ev < 0.0


def favourability(reaction: Reaction, oracle) -> str:
    """
    A human-readable verdict that respects the error bar.

    A reaction whose predicted energy is smaller than its own uncertainty is reported as
    undecided rather than given a direction it has not earned.
    """
    est = reaction_energy(reaction, oracle)
    if est is None:
        return "UNKNOWN (oracle declined)"
    if abs(est.value_ev) <= est.uncertainty_ev:
        return (f"UNDECIDED ({est.value_ev:+.3f} +/- {est.uncertainty_ev:.3f} eV -- "
                f"within the method's own error bar)")
    direction = "exothermic" if est.value_ev < 0 else "endothermic"
    return f"{direction} ({est.value_ev:+.3f} +/- {est.uncertainty_ev:.3f} eV)"
