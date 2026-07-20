"""
Where the categorical layer meets the energy oracle.

A ``Reaction`` from ``smartchem.category`` is a structurally valid morphism -- it conserves
matter and charge by construction. That says nothing about whether it is energetically
favourable. This module answers that second question, for any oracle, without the
categorical layer having to know which oracle it is talking to.

    reaction_energy(rxn, oracle) -> Estimate | None

The accounting is deliberately simple and stated out loud, because a hidden energy model
is exactly how the legacy engine accumulated fitted constants nobody could see:

    E(config)  = -sum of the dissociation energies of every bond present
    dH(A -> B) = E(cod) - E(dom)

so forming a bond releases energy (negative dH) and breaking one costs it.

Two rules inherited from the oracle layer:

* **Partial pricing is refused.** If any single bond in either configuration cannot be
  priced, the whole reaction is declined. Quietly skipping the bond that the oracle could
  not handle would silently understate the energy, which is the failure mode where a
  wrong number looks like a right one.
* **Uncertainty propagates.** Independent bond estimates add in quadrature, so the caller
  always sees how much the answer is worth.

Bond order and what it does *not* do
------------------------------------
An oracle prices an atom **pair**, and what it returns is the dissociation energy of that
pair's ground-state diatomic -- for ``("C", "O")`` that is the full 11.16 eV triple bond,
not a C-O single bond. So bond order is deliberately **not** used as a multiplier here.
Scaling by order would triple-count CO.

The honest consequence: this module cannot currently distinguish a C-C single bond from a
C=C double bond, because the oracle interface has no way to be told which was meant. That
is exact for diatomics (the whole reference set) and an approximation for polyatomics.
Fixing it means extending the oracle protocol to accept a bond order, not inventing a
scaling factor at this layer -- which is precisely the kind of unlabelled fudge that put
a hand-fitted 0.1 into the legacy engine.
"""
from __future__ import annotations

import math

from .category import Config, Molecule, Reaction
from .oracle.base import Estimate


def _bond_estimates(config: Config, oracle) -> list[Estimate] | None:
    """
    Price every bond in a configuration. None if any bond cannot be priced.

    Returns an empty list for a configuration of unbonded atoms, which is correct:
    free atoms have no bonding energy, not an unknown one.
    """
    out: list[Estimate] = []
    for mol in config.species:
        for bond in sorted(mol.bonds):
            pair = (mol.atoms[bond.i], mol.atoms[bond.j])
            est = oracle.estimate(pair)
            if est is None:
                return None
            if bond.order != 1:
                # NOT scaled by order -- see the module docstring. The oracle already
                # returns the ground-state diatomic's full dissociation energy, so the
                # multiple-bond character is priced in. Recorded so the caller knows the
                # order was observed and deliberately not used as a multiplier.
                est = Estimate(
                    value_ev=est.value_ev,
                    uncertainty_ev=est.uncertainty_ev,
                    method=est.method,
                    seconds=est.seconds,
                    notes=f"{est.notes}; declared order {bond.order}, priced as the "
                          f"ground-state diatomic (order not used as a multiplier)",
                )
            out.append(est)
    return out


def bonding_energy(config: Config, oracle) -> Estimate | None:
    """
    Total bonding energy of a configuration, in eV. Negative = bound.

    None if any bond cannot be priced by this oracle.
    """
    ests = _bond_estimates(config, oracle)
    if ests is None:
        return None
    if not ests:
        return Estimate(0.0, 0.0, getattr(oracle, "name", "?"), 0.0, "no bonds")
    total = -sum(e.value_ev for e in ests)
    unc = math.sqrt(sum(e.uncertainty_ev ** 2 for e in ests))
    seconds = sum(e.seconds for e in ests)
    multiple = any("declared order" in e.notes for e in ests)
    return Estimate(
        value_ev=total,
        uncertainty_ev=unc,
        method=getattr(oracle, "name", "?"),
        seconds=seconds,
        notes=f"{len(ests)} bond(s)"
              + ("; multiple bonds priced as ground-state diatomics" if multiple else ""),
    )


def reaction_energy(reaction: Reaction, oracle) -> Estimate | None:
    """
    Enthalpy change of a reaction, in eV. Negative = exothermic.

    None if either side cannot be fully priced. The categorical layer has already
    guaranteed the reaction conserves matter and charge; this adds only the energetics.
    """
    dom = bonding_energy(reaction.dom, oracle)
    cod = bonding_energy(reaction.cod, oracle)
    if dom is None or cod is None:
        return None
    return Estimate(
        value_ev=cod.value_ev - dom.value_ev,
        uncertainty_ev=math.sqrt(dom.uncertainty_ev ** 2 + cod.uncertainty_ev ** 2),
        method=getattr(oracle, "name", "?"),
        seconds=dom.seconds + cod.seconds,
        notes=f"{reaction.dom} -> {reaction.cod}",
    )


def is_exothermic(reaction: Reaction, oracle) -> bool | None:
    """
    True / False / None-if-unknown.

    None is a real answer here and must not be collapsed to False: "the oracle cannot
    price this" and "this reaction is uphill" are different facts, and conflating them is
    how an unpriceable reaction gets silently reported as unfavourable.
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
