"""
Pluggable energy oracles.

Accuracy is a dial, not a fixed property of the system. The categorical layer above does
not care which oracle answers; it cares that the answer arrives with a method and an error
bar attached.

Availability is discovered, never assumed. Oracles with optional heavy dependencies
(PySCF, tblite) register only if their dependency imports, so the core suite runs on a
bare numpy/scipy install and the benchmark simply reports fewer rows.
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

    try:
        from .tightbinding import TightBindingOracle
    except ImportError:
        pass
    else:
        registry["tightbinding"] = TightBindingOracle()

    try:
        from .pyscf_oracle import PySCFOracle
    except ImportError:
        pass
    else:
        # Distinct tiers of the same backend: the accuracy/cost dial made explicit.
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

    try:
        from .xtb_oracle import XTBOracle
    except ImportError:
        pass
    else:
        registry["gfn2-xtb"] = XTBOracle()

    return registry
