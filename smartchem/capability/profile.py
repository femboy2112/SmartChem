"""smartchem/capability/profile.py -- the ONE CapabilityProfile type (FREEZE decision 1).

**Hi, I'm the Bench-in-a-Box Meeseeks!** I hold everything one operator's declared bench can DO: what's
in the cupboard (``material_inventory``), what's on the shelf (``equipment``), how hot/how pressured it
can go (``physical_bounds``/``process_bounds``), whether it has a hood (``containment``)/open air
(``ventilation``), what it can measure, where waste goes, what tiers of shop it can buy from, and its
budget. ONE frozen type -- never a second "evaluator" hiding a competing model of the same bench.

Name-collision note (FREEZE decision 1 asks for this explicitly, so nobody confuses three similarly-named
things): this is ``CapabilityProfile``, never a "Bucket". It is NOT
:class:`~smartchem.experiment.bucket.Bucket` (an evidence-strength tag for a datum), NOT
:class:`~smartchem.experiment.handling.HazardFlag` (a sourced per-species hazard record), and the closed
enums it is built from live in :mod:`smartchem.capability.enums` under their own names
(``EquipmentCapability``, ``ContainmentCapability``, ...) -- never "Bucket" either.

This module deliberately carries NO ``@classmethod`` presets (``research_lab()``/``poor_man()``/
``custom()``): those are FREEZE decision 6's job, a SEPARATE Wave-B file ("v09-profile-presets",
decision 8 item 2) that consumes this frozen core. Building them here would be scope creep this Meeseeks
was not summoned for.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..constraints import PhysicalBounds
from ..contracts import Digestible
from ..data.reagents import Availability
from ..experiment.affordability import CostVector
from ..experiment.stock import StockMaterial
from ..process_constraints import ProcessBounds
from .enums import ContainmentCapability, EquipmentCapability, MeasurementCapability, VentilationCapability, WasteCapability

__all__ = ["CAPABILITY_PROFILE_SCHEMA", "CapabilityProfile"]

CAPABILITY_PROFILE_SCHEMA = "smartchem.capability/capability-profile-v1alpha1"


@dataclass(frozen=True)
class CapabilityProfile(Digestible):
    """A declared bench: what it has, on every independent capability axis (FREEZE decision 1).

    ``material_inventory=()`` (the default a preset like a no-stock ``ResearchLab`` would use) honestly
    means "no declared stock" -- :mod:`smartchem.capability.assess` reads that as material-axis UNKNOWN,
    never a silent pass. Every frozenset field is a CLOSED-vocabulary set (see :mod:`.enums`); an empty
    frozenset means "declares nothing on this axis", not "unconstrained" -- ``physical_bounds``/
    ``process_bounds``/``budget`` carry their OWN honest "unconstrained" (all-``None``) state instead of
    reusing the empty-set idiom, because they are REUSED typed leaves with that exact convention already.
    """

    schema_version: str
    profile_id: str
    material_inventory: "tuple[StockMaterial, ...]"
    equipment: "frozenset[EquipmentCapability]"
    physical_bounds: PhysicalBounds
    process_bounds: ProcessBounds
    containment: "frozenset[ContainmentCapability]"
    ventilation: "frozenset[VentilationCapability]"
    measurement: "frozenset[MeasurementCapability]"
    waste_handling: "frozenset[WasteCapability]"
    procurement: "frozenset[Availability]"
    budget: "CostVector | None"
    provenance: str

    def __post_init__(self) -> None:
        if self.schema_version != CAPABILITY_PROFILE_SCHEMA:
            raise ValueError(f"schema_version must be exactly {CAPABILITY_PROFILE_SCHEMA!r}")
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("profile_id must be a non-empty string")
        object.__setattr__(self, "profile_id", self.profile_id.strip())
        if type(self.material_inventory) is not tuple or any(
            type(m) is not StockMaterial for m in self.material_inventory
        ):
            raise TypeError("material_inventory must be a tuple of StockMaterial values")
        for name, enum in (
            ("equipment", EquipmentCapability),
            ("containment", ContainmentCapability),
            ("ventilation", VentilationCapability),
            ("measurement", MeasurementCapability),
            ("waste_handling", WasteCapability),
            ("procurement", Availability),
        ):
            value = getattr(self, name)
            if type(value) is not frozenset or any(type(item) is not enum for item in value):
                raise TypeError(f"{name} must be a frozenset of {enum.__name__} values")
        if type(self.physical_bounds) is not PhysicalBounds:
            raise TypeError("physical_bounds must be a smartchem.constraints.PhysicalBounds")
        if type(self.process_bounds) is not ProcessBounds:
            raise TypeError("process_bounds must be a smartchem.process_constraints.ProcessBounds")
        if self.budget is not None and type(self.budget) is not CostVector:
            raise TypeError("budget must be a CostVector or None (no declared ceiling)")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("provenance must be a non-empty string (the declaration's origin)")
        object.__setattr__(self, "provenance", self.provenance.strip())

    @property
    def profile_digest(self) -> str:
        """The canonical content digest of this whole declared bench -- the pin
        ``CapabilityAssessment.profile_digest`` carries, and the load-time ``CAPABILITY-REBIND-ON-LOAD``
        re-derivation (FREEZE decision 7, a later Wave-B item) will refuse a mismatch against."""
        return self.digest
