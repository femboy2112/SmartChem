"""E2 -- the stoichiometric ceiling: the 100%-efficiency maximum outcome, by limiting reagent.

This is the ``CONSERVATION`` bucket in full: an EXACT, formal, free consequence of mass bookkeeping, and an
idealised UPPER BOUND -- never a predicted yield.  Given a certified :class:`~smartchem.experiment.step.ExperimentStep`
(already balanced) and the molar amounts of the reactants a chemist actually charges, the ceiling is the
limiting-reagent calculation::

    max mol(target) = min over specified reactants of ( available_mol / stoich_coefficient )
                      * stoich_coefficient(target)

carried out over :class:`fractions.Fraction`, so it is exact.  The stoichiometric coefficients are the
multiplicities in the step's own multiset (the multiset IS the balanced equation), and they are
CROSS-CHECKED against :mod:`smartchem.stoichiometry`'s exact integer kernel -- the step's signed
coefficient vector is fed to :meth:`~smartchem.stoichiometry.StoichiometryMenu.check`, an independent
balance derivation (dictionary accumulation, no shared code) -- so the ceiling rests on two agreeing
derivations, not on the step's own say-so (open decision #3, honoured).

Universal: pure arithmetic over the step's multiset, so it works for any chemical.  Amounts are EXACT
rationals (``int`` or :class:`~fractions.Fraction`, in mol); a ``float`` is refused rather than silently
importing binary imprecision into a bucket whose whole claim is exactness -- convert grams->mol to a
Fraction at the boundary.

This is a CONSERVATION bound at 100% efficiency, labelled as one.  It never claims the reaction *reaches*
this -- reaching it is a matter of YIELD, which this conservation number does not assert.  (A sourced
thermodynamic equilibrium extent is a tighter, DERIVED bound -- a separate, graded claim, not this one.)
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from ..category import Molecule
from ..contracts import Digestible, canonical_digest
from ..stoichiometry import stoichiometry_menu
from .bucket import Bucket, Quantity
from .step import ExperimentRoute, ExperimentStep

__all__ = [
    "CeilingError",
    "ReactantDemand",
    "StoichiometricCeiling",
    "RouteCeiling",
    "stoichiometric_ceiling",
    "route_ceiling",
]


class CeilingError(ValueError):
    """The stoichiometric ceiling could not be computed as an exact conservation fact."""


def _ident(molecule: Molecule) -> str:
    try:
        return canonical_digest(molecule.canonical())
    except NotImplementedError:
        return "asgiven:" + canonical_digest(molecule)


@dataclass(frozen=True)
class ReactantDemand(Digestible):
    """One reactant's contribution to the limiting-reagent calculation."""

    reactant: Molecule
    stoich_coefficient: int
    available_mol: Fraction | None    # None = charged in excess (not specified, not limiting)
    ratio: Fraction | None            # available / coefficient, or None if in excess

    @property
    def specified(self) -> bool:
        return self.available_mol is not None


@dataclass(frozen=True)
class StoichiometricCeiling(Digestible):
    """The exact 100%-efficiency maximum of the step's target, and the reactant that limits it."""

    step: ExperimentStep
    limiting_reactant: Molecule
    max_target_mol: Fraction
    target_coefficient: int
    demands: tuple[ReactantDemand, ...]

    @property
    def quantity(self) -> Quantity:
        """The ceiling as a bucket-labelled quantity (CONSERVATION -- an idealised upper bound)."""
        return Quantity(
            label="max target (100% efficiency)",
            value=str(self.max_target_mol),
            unit="mol",
            bucket=Bucket.CONSERVATION,
            provenance="limiting-reagent conservation; exact rational, cross-checked vs the integer kernel",
        )

    def explain(self) -> str:
        head = (
            f"stoichiometric ceiling: {self.max_target_mol} mol {self.step.target!r} at 100% efficiency "
            f"[CONSERVATION -- an idealised upper bound, not a predicted yield]"
        )
        lines = [head, f"  limiting reagent: {self.limiting_reactant!r}"]
        for d in self.demands:
            if d.specified:
                lines.append(
                    f"    {d.reactant!r}: {d.available_mol} mol / coeff {d.stoich_coefficient} "
                    f"= {d.ratio}"
                )
            else:
                lines.append(f"    {d.reactant!r}: coeff {d.stoich_coefficient}, charged in excess")
        return "\n".join(lines)


def _coefficient_vector(step: ExperimentStep) -> tuple[tuple[Molecule, ...], tuple[int, ...]]:
    """The distinct species of the step and its signed net coefficient vector (reactant +, product -)."""
    react = Counter(_ident(m) for m in step.reactants)
    prod = Counter(_ident(m) for m in step.products)
    by_ident: dict[str, Molecule] = {}
    for m in (*step.reactants, *step.products):
        by_ident.setdefault(_ident(m), m)
    species: list[Molecule] = []
    nu: list[int] = []
    for key, m in by_ident.items():
        net = react.get(key, 0) - prod.get(key, 0)
        if net == 0:
            continue  # a pure spectator/catalyst (equal on both sides) is not in the balance vector
        species.append(m)
        nu.append(net)
    return tuple(species), tuple(nu)


def _verify_balances(step: ExperimentStep) -> None:
    """Cross-check the step's coefficients against the exact integer kernel (an independent path).

    The step already passed :class:`~smartchem.category.Reaction`'s conservation check, so this is a
    second, redundant derivation.  It is kept because the ceiling's exactness claim is only as strong as
    the coefficients it divides by, and a menu-vs-Reaction contradiction here would mean one of the two
    exact derivations is wrong -- which the caller is entitled to find out about, not to silently divide by.
    """
    species, nu = _coefficient_vector(step)
    if not species:
        raise CeilingError("the step has no net species (every species cancels); no ceiling to compute")
    # stoichiometry_menu refuses repeated species; _coefficient_vector already returns distinct ones.
    menu = stoichiometry_menu(species)
    written = menu.check(list(nu))
    if written.violations:
        raise CeilingError(
            f"the step's coefficient vector does not balance under the exact integer kernel "
            f"({written.explain()}); Reaction and the kernel disagree, which must not be divided through"
        )


def stoichiometric_ceiling(
    step: ExperimentStep, feed: Mapping[Molecule, "int | Fraction"]
) -> StoichiometricCeiling:
    """The exact 100%-efficiency maximum of ``step``'s target for the charged ``feed`` (mol per reactant).

    ``feed`` maps reactant molecules to EXACT molar amounts (``int`` or :class:`~fractions.Fraction`).  A
    reactant absent from ``feed`` is treated as charged in EXCESS (never limiting); at least one reactant
    must be specified, or there is nothing to limit against.  A ``float`` amount is refused (exactness).
    """
    if type(step) is not ExperimentStep:
        raise TypeError("step must be an ExperimentStep")
    _verify_balances(step)

    coeff: Counter = Counter(_ident(m) for m in step.reactants)
    by_ident: dict[str, Molecule] = {}
    for m in step.reactants:
        by_ident.setdefault(_ident(m), m)
    target_coeff = Counter(_ident(m) for m in step.products)[_ident(step.target)]
    if target_coeff < 1:
        raise CeilingError("the target does not appear among the products with a positive coefficient")

    feed_by_ident: dict[str, Fraction] = {}
    for molecule, amount in feed.items():
        if type(molecule) is not Molecule:
            raise TypeError("feed keys must be Molecule values")
        if isinstance(amount, bool) or not isinstance(amount, (int, Fraction)):
            raise CeilingError(
                f"feed amount for {molecule!r} must be an exact int or Fraction (mol), got "
                f"{type(amount).__name__}; convert grams->mol to a Fraction at the boundary so the "
                f"CONSERVATION ceiling stays exact"
            )
        if amount < 0:
            raise CeilingError(f"feed amount for {molecule!r} must be non-negative")
        key = _ident(molecule)
        if key not in coeff:
            raise CeilingError(f"{molecule!r} is not a reactant of this step; it cannot be a feed entry")
        feed_by_ident[key] = feed_by_ident.get(key, Fraction(0)) + Fraction(amount)

    demands: list[ReactantDemand] = []
    best_ratio: Fraction | None = None
    limiting_key: str | None = None
    for key, m in by_ident.items():
        c = coeff[key]
        if key in feed_by_ident:
            ratio = Fraction(feed_by_ident[key], c)
            demands.append(ReactantDemand(m, c, feed_by_ident[key], ratio))
            if best_ratio is None or ratio < best_ratio:
                best_ratio = ratio
                limiting_key = key
        else:
            demands.append(ReactantDemand(m, c, None, None))

    if best_ratio is None or limiting_key is None:
        raise CeilingError(
            "no reactant amount was specified; the ceiling has nothing to limit against. Charge at "
            "least one reactant with an exact molar amount"
        )

    max_target = best_ratio * target_coeff
    return StoichiometricCeiling(
        step=step,
        limiting_reactant=by_ident[limiting_key],
        max_target_mol=max_target,
        target_coefficient=target_coeff,
        demands=tuple(demands),
    )


@dataclass(frozen=True)
class RouteCeiling(Digestible):
    """The propagated 100%-efficiency ceiling of a whole route: chain each step's limiting-reagent max.

    The intermediate a step produces (its ``max_target_mol``) becomes an input amount to the next step, so
    the final number answers the operator's *"if every reaction runs at 100% efficiency, this is the max
    possible outcome."*  It is ``CONSERVATION`` -- an idealised UPPER BOUND, never a predicted yield.

    Stated assumption (a documented idealisation, not a hidden one): each step's EXTERNAL reagents are taken
    to be charged fresh in the amount given, and only the carried INTERMEDIATE is propagated.  A reagent
    shared across steps is not decremented between them -- which only ever keeps the number an upper bound.
    """

    route: ExperimentRoute
    per_step: tuple[StoichiometricCeiling, ...]
    final_target_mol: Fraction

    def explain(self) -> str:
        lines = [
            f"route ceiling: {self.final_target_mol} mol {self.route.final_target!r} at 100% efficiency "
            f"[CONSERVATION -- an idealised upper bound over the whole route, not a predicted yield]"
        ]
        for k, c in enumerate(self.per_step):
            lines.append(f"  step {k + 1}: <= {c.max_target_mol} mol {c.step.target!r} "
                         f"(limited by {c.limiting_reactant!r})")
        return "\n".join(lines)


def route_ceiling(
    route: ExperimentRoute, feed: Mapping[Molecule, "int | Fraction"]
) -> RouteCeiling:
    """The propagated exact ceiling of a route for external ``feed`` amounts (mol per external reactant).

    Each step is limited by whichever is scarcer -- an external reagent from ``feed`` or the intermediate
    the previous step could make -- and the intermediate amount is threaded forward.  The final step's max
    is the route's ceiling.  ``feed`` must cover at least one reactant of the first step (nothing to limit
    against otherwise); intermediates are supplied automatically.
    """
    if type(route) is not ExperimentRoute:
        raise TypeError("route must be an ExperimentRoute")
    available: dict[str, tuple[Molecule, Fraction]] = {}
    for molecule, amount in feed.items():
        if isinstance(amount, bool) or not isinstance(amount, (int, Fraction)):
            raise CeilingError("feed amounts must be exact int or Fraction (mol)")
        available[_ident(molecule)] = (molecule, Fraction(amount))

    per: list[StoichiometricCeiling] = []
    for step in route.steps:
        step_feed: dict[Molecule, Fraction] = {}
        for r in step.reactants:
            key = _ident(r)
            if key in available:
                step_feed[available[key][0]] = available[key][1]
        ceiling = stoichiometric_ceiling(step, step_feed)
        per.append(ceiling)
        # the intermediate/product this step makes is now available to the next step
        available[_ident(step.target)] = (step.target, ceiling.max_target_mol)

    return RouteCeiling(route, tuple(per), per[-1].max_target_mol)
