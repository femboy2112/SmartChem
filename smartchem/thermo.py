"""
Endpoint energy differences: where the sequential category meets an oracle.

For the current *ideal noninteracting-species model* this module defines an object potential

    E(A) = sum of isolated species energies

and the exact endpoint difference ``dE(f : A -> B) = E(B) - E(A)``. It telescopes under
sequential composition and vanishes on identities. A precise categorical codomain is the
translation category of real energies, not an unspecified ``(R,+)``.

Additivity across ``tensor_obj`` is an assumption of this oracle adapter, not a universal
law for species placed in one vessel. Solvation, intermolecular forces, binding, finite-size
effects and long-range fields require explicit interaction terms. Likewise,
``Reaction.scheduled_product`` is not a parallel categorical tensor, so no morphism-level
strong-monoidal claim is made here.

Reference-shift invariance
--------------------------
Conservation makes ``E(B) - E(A)`` invariant under the reference shifts permitted by the
oracle contract.

Total energy has an arbitrary zero fixed by the atom content: PySCF reports CO at about
-3074 eV, the legacy heuristic at about -11 eV, and both are valid on their own
references. Without a shared reference or explicit reservoirs, subtracting configurations
with different inventories would be reference-dependent. Such differences can still have
physical meaning when chemical potentials, reservoirs and boundary flows are specified; the
current closed ``Reaction`` type simply does not represent those data.

``Reaction.__post_init__`` guarantees ``formula(dom) == formula(cod)``. That is exactly the
condition under which the per-atom offsets appear identically on both sides and cancel.

So the conservation theorem is not a safety check bolted onto a chemistry model. It is the
precondition under which the oracle's permitted per-element reference shifts cancel. It
does not forbid open-system comparisons with different inventories; those require explicit
reservoirs and boundary flows.
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

from collections import Counter

from .category import Config, Reaction, reaction_residue
from .oracle.base import Estimate


def configuration_energy(config: Config, oracle) -> Estimate | None:
    """
    ``E(A)``: total energy of a configuration, in eV, on the oracle's own zero.

    This sum defines the current isolated-species/ideal-mixture adapter. It omits interaction
    energy between distinct species; callers must not treat its additivity as exact physics
    for an interacting vessel.

    The empty configuration has energy exactly zero -- ``E(I) = 0``, the unit law. That is
    a real value, not a refusal.

    None if any species cannot be priced.
    """
    total = Estimate.zero(getattr(oracle, "name", "?"))
    for molecule, count in Counter(config.species).items():
        part = oracle.energy(molecule)
        if part is None:
            return None
        total = total + part.scaled(count)
    return total


def reaction_energy(reaction: Reaction, oracle) -> Estimate | None:
    """
    ``dE(f)``: the difference reported by the chosen energy oracle, in eV.

    For the bundled quantum oracle this is approximately a 0 K electronic-plus-ZPE
    internal-energy difference. It is not automatically enthalpy ``dH`` or Gibbs free
    energy ``dG``; phases, thermal populations, pressure and activities are absent.

    Invariant under the oracle contract's permitted per-element reference shifts because
    ``reaction`` conserves matter and charge. Open-system differences can also be meaningful,
    but require shared conventions plus explicit reservoirs absent from this closed type.

    None if either side cannot be fully priced.
    """
    # Cancel spectators FIRST, within this isolated-species model. Its separability
    # assumption makes an unchanged species contribute exactly nothing to
    # the difference, so pricing it would buy a number that provably cannot move the
    # answer -- and would then leak its uncertainty into the result as if it were an
    # independent random error, which it is not. See ``category.reaction_residue``.
    left, right = reaction_residue(reaction)
    dom = configuration_energy(left, oracle)
    cod = configuration_energy(right, oracle)
    if dom is None or cod is None:
        return None
    # The subtraction is where the arbitrary energy zero cancels exactly and named model
    # correction displacements propagate algebraically. Surviving displacement magnitude
    # becomes a reporting floor, not a calibrated bound on unknown residual error.
    delta = (cod - dom).with_sensitivity_floor()
    return Estimate(
        value_ev=delta.value_ev,
        uncertainty_ev=delta.uncertainty_ev,
        method=getattr(oracle, "name", "?"),
        seconds=delta.seconds,
        notes="; ".join(
            note for note in (delta.notes, f"{reaction.dom} -> {reaction.cod}") if note
        ),
        systematic_ev=delta.systematic_ev,
        methods=delta.methods or frozenset({getattr(oracle, "name", "?")}),
        systematic_terms=delta.systematic_terms,
    )


def bonding_energy(config: Config, oracle) -> Estimate | None:
    """
    Energy of a configuration relative to its own free atoms. Negative = bound.

    Derived from two endpoint energies rather than primitive: it is ``dE`` from free atoms
    to this configuration, and equal element inventories make it invariant under permitted
    per-element reference shifts.
    Kept because "how bound is this?" is the question a chemist actually asks, whereas
    ``configuration_energy`` returns a number on an arbitrary scale.

    None if either the configuration or its free atoms cannot be priced.
    """
    if config.charge != 0:
        # The neutral-free-atom reference below would change total charge and make the
        # difference depend on the oracle's charge reference. Ionic binding needs explicit
        # charge-balanced fragments or a reservoir, neither represented by this helper.
        return None
    whole = configuration_energy(config, oracle)
    if whole is None:
        return None
    free = configuration_energy(Config.atoms(*_all_atoms(config)), oracle)
    if free is None:
        return None
    return (whole - free).with_sensitivity_floor()


def _all_atoms(config: Config) -> tuple[str, ...]:
    """Every atom in the configuration, as free-atom symbols."""
    return tuple(symbol for molecule in config.species for symbol in molecule.atoms)


def is_exothermic(reaction: Reaction, oracle) -> bool | None:
    """
    Compatibility predicate: negative endpoint ``dE`` / nonnegative / unknown.

    None is a real answer and must not be collapsed to False: "the oracle cannot price
    this" and "this reaction has a nonnegative endpoint energy difference" are different
    facts. A negative electronic/internal endpoint energy is not by itself a calorimetric
    heat or enthalpy, so the historical name is narrower than the implementation.
    """
    est = reaction_energy(reaction, oracle)
    return None if est is None else est.value_ev < 0.0


def favourability(reaction: Reaction, oracle) -> str:
    """
    Legacy name for a human-readable *energy-direction* verdict.

    This does not decide thermodynamic favourability or spontaneity unless the supplied
    oracle actually returns Gibbs free energies at the relevant conditions. The bundled
    oracles do not. The text therefore reports only exothermic/endothermic direction.

    ``uncertainty_ev`` has no coverage-kind field yet: it may be a validation MAE, numerical
    scale, standard deviation, or bound. This formatter therefore reports point-estimate
    direction and the scale separately; it does not turn that scale into a confidence test.
    """
    est = reaction_energy(reaction, oracle)
    if est is None:
        return "UNKNOWN (oracle declined)"
    if est.value_ev < 0:
        direction = "energy-lowering"
    elif est.value_ev > 0:
        direction = "energy-raising"
    else:
        direction = "energy-neutral"
    return (f"estimated {direction} ({est.value_ev:+.3f} eV; reported uncertainty scale "
            f"{est.uncertainty_ev:.3f} eV, coverage unspecified)")
