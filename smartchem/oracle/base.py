"""
The energy oracle interface.

The whole point of this layer: the categorical machinery above it is oracle-agnostic.
The same conservation reasoning, pathway search and response-surface machinery runs on a
microsecond heuristic or on CCSD(T)/CBS. Accuracy becomes a dial, not a fixed property of
the system, and the dial setting is always attached to the answer.

Two rules every oracle obeys:

1. **Declining is allowed; lying is not.** An oracle that cannot cover a species returns
   None. It must never return a fabricated number to look complete. The benchmark counts
   refusals separately so ducking the hard cases cannot improve a score.

2. **Every value carries its provenance and its uncertainty.** A number without a stated
   method and error bar is not a result. This is what the original design called a
   "certificate" and never actually produced.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Estimate:
    """A single energy prediction with everything needed to judge it."""
    value_ev: float
    uncertainty_ev: float
    method: str
    seconds: float = 0.0
    notes: str = ""

    def __repr__(self) -> str:
        return (f"{self.value_ev:.4f} +/- {self.uncertainty_ev:.4f} eV "
                f"[{self.method}]")


@runtime_checkable
class EnergyOracle(Protocol):
    """Anything that can price a bond."""

    name: str
    #: Honest self-assessment: expected MAE in eV. Measured, not asserted -- see
    #: ``python -m smartchem.bench``. Used to pick a tier, never to replace measurement.
    nominal_accuracy_ev: float

    def bond_energy(self, symbols: tuple[str, ...]) -> float | None:
        """
        Dissociation energy in eV for the given atoms, positive = bound.

        Returns None if this oracle does not cover the species. Raise only on a genuine
        internal failure, never to signal "not supported".
        """
        ...

    def estimate(self, symbols: tuple[str, ...]) -> Estimate | None:
        """Same as bond_energy but carrying provenance and an error bar."""
        ...


class BaseOracle:
    """Convenience base: implement ``estimate``, get ``bond_energy`` for free."""

    name: str = "unnamed"
    nominal_accuracy_ev: float = float("inf")

    def estimate(self, symbols: tuple[str, ...]) -> Estimate | None:  # pragma: no cover
        raise NotImplementedError

    def bond_energy(self, symbols: tuple[str, ...]) -> float | None:
        est = self.estimate(symbols)
        return None if est is None else est.value_ev
