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
from .heuristic import HeuristicOracle

__all__ = ["BaseOracle", "EnergyOracle", "Estimate", "HeuristicOracle", "available_oracles"]


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
        registry["ccsdt-tz"] = PySCFOracle(method="CCSD(T)", basis="cc-pVTZ")
        registry["ccsdt-qz"] = PySCFOracle(method="CCSD(T)", basis="cc-pVQZ")
        registry["ccsdt-cbs"] = PySCFOracle(method="CCSD(T)", basis="cbs(TZ,QZ)")

    try:
        from .xtb_oracle import XTBOracle
    except ImportError:
        pass
    else:
        registry["gfn2-xtb"] = XTBOracle()

    return registry
