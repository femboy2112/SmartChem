"""smartchem.capability -- the v0.9 Capability Compiler core (FREEZE decision 8, "v09-capability-core").

**EXISTENCE IS PAIN, BUT THIS PACKAGE'S JOB IS SMALL AND EXACT: look at me, I'm a capability projection!**
The SAME ``ExperimentRoute`` the search engine already produced gets projected through a declared
``CapabilityProfile`` (what a bench HAS) and comes out the other side with an honest, per-axis
``CapabilityAssessment`` (can that bench actually RUN it). Capability is a PROJECTION, never a second
chemistry engine -- nothing in here re-derives conservation, re-runs search, or invents a threshold.

Public surface (see each module's own docstring for the reasoning):

* :mod:`.enums` -- the closed vocabularies (``CapabilityStatus``, ``EquipmentCapability``, ...).
* :mod:`.equipment_resolver` -- the closed apparatus-string -> ``EquipmentCapability`` table.
* :mod:`.requirements` -- ``compile_capability_requirements(route)``, the PURE route-only projection.
* :mod:`.profile` -- ``CapabilityProfile``, the ONE declared-bench type (no presets here; see
  :mod:`.presets` for ``research_lab()``/``poor_man()``/``custom()``).
* :mod:`.assess` -- ``assess(profile, requirements, route_readiness)``, the pure verdict fold.
* :mod:`.presets` -- the named ``CapabilityProfile`` builders + the closed
  ``resolve_capability_profile(spec)`` lookup (FREEZE decision 6).

Frozen contract: ``docs/research/V0_9_CAPABILITY_COMPILER_ROUND_II_FREEZE_2026-09-28.md``.
"""
from __future__ import annotations

from .assess import CAPABILITY_ASSESSMENT_SCHEMA, AxisResult, CapabilityAssessment, assess
from .enums import (
    CapabilityStatus,
    ContainmentCapability,
    EQUIPMENT_KIND_OF,
    EquipmentCapability,
    MeasurementCapability,
    VentilationCapability,
    WasteCapability,
)
from .equipment_resolver import resolve_apparatus, resolve_apparatus_strings
from .presets import (
    CAPABILITY_PROFILE_PRESETS,
    custom,
    poor_man,
    research_lab,
    resolve_capability_profile,
)
from .profile import CAPABILITY_PROFILE_SCHEMA, CapabilityProfile
from .quantity import QuantityDemand, QuantityKnowledge
from .requirements import (
    MaterialRequirement,
    RouteCapabilityRequirements,
    WasteRequirement,
    compile_capability_requirements,
)

__all__ = [
    "QuantityDemand",
    "QuantityKnowledge",
    "CAPABILITY_ASSESSMENT_SCHEMA",
    "AxisResult",
    "CapabilityAssessment",
    "assess",
    "CapabilityStatus",
    "ContainmentCapability",
    "EQUIPMENT_KIND_OF",
    "EquipmentCapability",
    "MeasurementCapability",
    "VentilationCapability",
    "WasteCapability",
    "resolve_apparatus",
    "resolve_apparatus_strings",
    "CAPABILITY_PROFILE_PRESETS",
    "custom",
    "poor_man",
    "research_lab",
    "resolve_capability_profile",
    "CAPABILITY_PROFILE_SCHEMA",
    "CapabilityProfile",
    "MaterialRequirement",
    "RouteCapabilityRequirements",
    "WasteRequirement",
    "compile_capability_requirements",
]
