"""
Pluggable energy oracles.

The structural layer accepts multiple oracle implementations. Choosing a more expensive
tier is not a universal accuracy dial: coverage, bias and uncertainty calibration vary by
species, state and method. Every returned estimate carries a method label and uncertainty
field, but statistical meaning still requires validation in the intended domain.

Availability is discovered, never assumed. The optional PySCF oracle registers only when
its dependency imports, so the core suite runs on a bare numpy/scipy install and the
benchmark simply reports fewer rows. Planned xTB/tight-binding adapters are not advertised
as installed backends until an implementation exists.
"""
from __future__ import annotations

from .base import BaseOracle, EnergyOracle, Estimate
from .caching import CachingOracle
from .heuristic import HeuristicOracle

__all__ = ["BaseOracle", "CachingOracle", "EnergyOracle", "Estimate", "HeuristicOracle",
           "available_oracles"]


def available_oracles() -> dict[str, EnergyOracle]:
    """
    Every oracle importable in this environment, keyed by short name.

    Missing optional backends are silently absent rather than an error: a machine without
    PySCF should still be able to run the whole categorical test suite.
    """
    registry: dict[str, EnergyOracle] = {"heuristic": HeuristicOracle()}

    from .pyscf_oracle import PYSCF_AVAILABLE, PySCFOracle
    if PYSCF_AVAILABLE:
        # Distinct cost/method tiers of the same backend; accuracy remains domain-specific.
        #
        # tight_d is passed explicitly on every entry rather than left to the default.
        # These names appear in a published accuracy table, so what each one MEANS has to
        # be pinned here: flipping a default would silently redefine a tier and quietly
        # invalidate the numbers in README.md.
        registry["ccsdt-tz"] = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False)
        registry["ccsdt-qz"] = PySCFOracle("CCSD(T)", "cc-pVQZ", tight_d=False)
        registry["ccsdt-cbs"] = PySCFOracle("CCSD(T)", "cbs(TZ,QZ)", tight_d=False)
        # The augmented tier: diffuse functions for ionic character, tight d for the
        # second row. Both corrections survive extrapolation, so they must be in the
        # basis rather than recovered by it.
        registry["ccsdt-aug-cbs"] = PySCFOracle("CCSD(T)", "aug-cbs(TZ,QZ)", tight_d=True)

    return registry
