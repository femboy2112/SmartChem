"""SHOP-LEAF-02 x STOCK-01: can a real StockMaterial INVENTORY source a shopping requirement?

SHOP-LEAF-02 answers "to make this much target, what pure species must I acquire, and how much" (a
:class:`~smartchem.experiment.dag.DAGShoppingRequirement`).  STOCK-01 answers "does this real bottle actually
contain that species, at a provable assay" (:meth:`~smartchem.experiment.stock.StockMaterial.satisfies`, keyed on
canonical STRUCTURE).  This brick meets them: given a shopping requirement and an inventory of ``StockMaterial``,
it reports, per required species, whether the inventory can SOURCE it -- matched the SOUND way (by structure, so a
same-formula isomer on the shelf never sources a requirement it does not satisfy), separating the IDENTITY/ASSAY
question (:class:`~smartchem.experiment.stock.FitnessVerdict`) from the QUANTITY question
(:class:`QuantityCoverage`), exactly as the standard separates a chemical identity from a material claim.

Honesty rules carried through: a species no inventory material contains is ``IDENTITY_ABSENT`` (never a silent
source); a dilute/unproven material is ``INSUFFICIENT_ASSAY``/``UNKNOWN_ASSAY`` (never assumed pure); quantity
coverage is ``UNKNOWN`` whenever the amount is undeclared OR its unit is not mol (unit conversion -- grams/volume
to mol via molar mass/density -- is a named follow-on, never faked); and a requirement is SOURCED only when the
assay is PROVEN to satisfy AND the amount is PROVEN to cover, so an empty or silent inventory can never read green.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from ..category import Molecule
from ..contracts import Digestible
from .dag import DAGShoppingRequirement
from .stock import FitnessVerdict, StockMaterial

__all__ = [
    "QuantityCoverage",
    "RequirementSourcing",
    "SourcingPlan",
    "plan_sourcing",
]

# a synthesis reactant is a PURE species by default; the caller may relax this per call.
_DEFAULT_MIN_ASSAY = 0.99

# fitness preference when several materials contain a required species (best first).
_FITNESS_RANK = {
    FitnessVerdict.SATISFIES: 0,
    FitnessVerdict.UNKNOWN_ASSAY: 1,
    FitnessVerdict.INSUFFICIENT_ASSAY: 2,
    FitnessVerdict.IDENTITY_ABSENT: 3,
}


class QuantityCoverage(str, Enum):
    """Whether an inventory material's declared amount covers the required mol -- never assumed."""

    COVERED = "COVERED"        # the worst-case available mol of the species already meets the requirement
    SHORT = "SHORT"            # even the best-case available mol falls short -> buy more / a bigger bottle
    UNKNOWN = "UNKNOWN"        # amount undeclared, unit not mol, or assay unknown -> cannot check coverage


@dataclass(frozen=True)
class RequirementSourcing(Digestible):
    """One required species judged against the inventory: the SOUND identity/assay verdict plus quantity coverage.

    ``fitness`` is :meth:`StockMaterial.satisfies` for ``species`` against the best-matching material (matched by
    canonical STRUCTURE), or ``IDENTITY_ABSENT`` when no material contains it.  ``coverage`` is a SEPARATE axis:
    even a material that satisfies the assay may not carry enough, and coverage is ``UNKNOWN`` unless the amount is
    declared in mol.  ``available_mol`` is the worst-case mol of the species the chosen material provides (amount x
    worst-case fraction), or ``None`` when it cannot be computed exactly.
    """

    species: Molecule
    required_mol: Fraction
    fitness: FitnessVerdict
    coverage: QuantityCoverage
    material_id: "str | None"
    available_mol: "Fraction | None"

    @property
    def is_sourced(self) -> bool:
        """Sourced only when the assay is PROVEN to satisfy AND the amount is PROVEN to cover -- never assumed."""
        return self.fitness is FitnessVerdict.SATISFIES and self.coverage is QuantityCoverage.COVERED

    def explain(self) -> str:
        where = f" from {self.material_id!r}" if self.material_id else ""
        have = f"; have >= {self.available_mol} mol" if self.available_mol is not None else ""
        return (
            f"{self.required_mol} mol {self.species!r}: {self.fitness.value} / {self.coverage.value}{where}{have}"
        )


@dataclass(frozen=True)
class SourcingPlan(Digestible):
    """Whether an inventory can source a whole shopping requirement -- one :class:`RequirementSourcing` per species.

    ``fully_sourced`` is true only when EVERY line :attr:`RequirementSourcing.is_sourced`; over a non-empty
    requirement (SHOP-LEAF-02 guarantees one), an empty inventory makes every line ``IDENTITY_ABSENT`` and this
    false -- never a vacuous green.  ``gaps`` names the species that are not sourced and why.
    """

    requirement: DAGShoppingRequirement
    lines: tuple[RequirementSourcing, ...]
    min_assay: float

    @property
    def fully_sourced(self) -> bool:
        return bool(self.lines) and all(line.is_sourced for line in self.lines)

    @property
    def gaps(self) -> tuple[RequirementSourcing, ...]:
        return tuple(line for line in self.lines if not line.is_sourced)

    def explain(self) -> str:
        head = (
            f"sourcing plan: {self.requirement.final_target_mol} mol "
            f"{self.requirement.dag.final_target!r} (min assay {self.min_assay:.0%}) -- "
            f"{'FULLY SOURCED' if self.fully_sourced else f'{len(self.gaps)} gap(s)'}"
        )
        return "\n".join([head, *(f"  {line.explain()}" for line in self.lines)])


def _best_source(
    species: Molecule, required_mol: Fraction, inventory: tuple[StockMaterial, ...], min_assay: float
) -> RequirementSourcing:
    """Judge ``species`` against the inventory: the best material by fitness, then coverage, then worst-case assay."""
    candidates: list[RequirementSourcing] = []
    for material in inventory:
        interval = material.active_fraction_interval(species)   # STRUCTURE-keyed match (None if absent)
        if interval is None:
            continue
        lo, hi = interval
        fitness = material.satisfies(species, min_assay=min_assay)
        coverage, available = _coverage(material, required_mol, lo, hi)
        candidates.append(RequirementSourcing(species, required_mol, fitness, coverage, material.material_id, available))
    if not candidates:
        return RequirementSourcing(
            species, required_mol, FitnessVerdict.IDENTITY_ABSENT, QuantityCoverage.UNKNOWN, None, None
        )
    # best: proven fitness first, then proven coverage, then the largest guaranteed amount on hand.
    _COVER_RANK = {QuantityCoverage.COVERED: 0, QuantityCoverage.UNKNOWN: 1, QuantityCoverage.SHORT: 2}
    return min(
        candidates,
        key=lambda c: (_FITNESS_RANK[c.fitness], _COVER_RANK[c.coverage], -(c.available_mol or Fraction(0))),
    )


def _coverage(
    material: StockMaterial, required_mol: Fraction, lo: float, hi: float
) -> "tuple[QuantityCoverage, Fraction | None]":
    """Coverage of ``required_mol`` from a material, honestly: only a mol amount with a known fraction is checkable.

    Uses the worst-case (lower-bound) active fraction for the guaranteed amount, so ``COVERED`` is a PROVEN cover;
    ``SHORT`` needs even the best case to fall short.  Any undeclared amount, a non-mol unit, or an unknown fraction
    is ``UNKNOWN`` (never assumed) -- gram/volume-to-mol conversion (molar mass/density) is a named follow-on.
    """
    quantity = material.quantity
    if quantity is None or quantity.unit.strip().casefold() != "mol":
        return QuantityCoverage.UNKNOWN, None
    try:
        amount = Fraction(quantity.value)                  # exact: StockQuantity.value is a numeric source string
    except ValueError:                                     # a non-decimal literal (e.g. scientific "1e3") -- cannot
        return QuantityCoverage.UNKNOWN, None              # convert exactly, so coverage is honestly UNKNOWN
    available_lo = amount * Fraction(lo).limit_denominator(10**9)
    available_hi = amount * Fraction(hi).limit_denominator(10**9)
    if lo <= 0.0:                                           # an unknown/zero worst-case fraction cannot prove cover
        return QuantityCoverage.UNKNOWN, None
    if available_lo >= required_mol:
        return QuantityCoverage.COVERED, available_lo
    if available_hi < required_mol:
        return QuantityCoverage.SHORT, available_lo
    return QuantityCoverage.UNKNOWN, available_lo           # the amount straddles the requirement -> measure


def plan_sourcing(
    requirement: DAGShoppingRequirement,
    inventory: "tuple[StockMaterial, ...]",
    *,
    min_assay: float = _DEFAULT_MIN_ASSAY,
) -> SourcingPlan:
    """Judge whether ``inventory`` can source ``requirement``, one required species at a time (SHOP-LEAF-02 x STOCK-01).

    Each required species is matched against the inventory by canonical STRUCTURE (so a same-formula isomer on the
    shelf never sources it), the assay judged by :meth:`StockMaterial.satisfies` at ``min_assay``, and the quantity
    coverage judged SEPARATELY and only when provable (a mol amount with a known fraction).  A species is SOURCED
    only when both are proven; everything else is a named gap, never a silent pass.
    """
    if type(requirement) is not DAGShoppingRequirement:
        raise TypeError("requirement must be a DAGShoppingRequirement")
    if type(inventory) is not tuple or any(type(m) is not StockMaterial for m in inventory):
        raise TypeError("inventory must be a tuple of StockMaterial")
    if isinstance(min_assay, bool) or not isinstance(min_assay, (int, float)) or not (0.0 < float(min_assay) <= 1.0):
        raise ValueError("min_assay must be a fraction in (0, 1]")
    lines = tuple(
        _best_source(species, required_mol, inventory, float(min_assay))
        for species, required_mol in requirement.requirements
    )
    return SourcingPlan(requirement, lines, float(min_assay))
