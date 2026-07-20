"""
The energy oracle interface.

The categorical machinery above this layer is oracle-agnostic: the same conservation
reasoning, pathway search and response-surface machinery runs on a microsecond heuristic
or on CCSD(T)/CBS. Accuracy is a dial, not a fixed property of the system, and the dial
setting is always attached to the answer.

The primitive is the energy of a SPECIES
----------------------------------------
``energy(molecule) -> Estimate`` returns the total energy of one chemical species, given
its full structure (atoms, bond topology, charge).

It used to be ``estimate(symbols) -> D0``, the dissociation energy of an atom *pair*. That
choice quietly determined the whole design and was wrong in three ways at once:

* the energy of a configuration became a sum over *edges* -- bond additivity, which is a
  fiction for anything polyatomic;
* bond order could not be priced, since an atom pair carries no order;
* only species present in a geometry lookup table could be asked about at all, so
  polyatomic support was structurally blocked rather than merely unimplemented.

With a species as the primitive, all three dissolve. Dissociation energy becomes a derived
quantity (``E(free atoms) - E(molecule)``) rather than the thing the interface is built on.

The arbitrary-zero contract -- and why conservation is what makes it safe
------------------------------------------------------------------------
Every oracle may choose its own zero of energy. PySCF returns total electronic energies
(CO is about -3074 eV); the legacy heuristic works relative to free atoms (CO is about
-11 eV). Both are legal. The **only** requirement is that an oracle is *self-consistent*:
the same zero for every species it prices.

That is safe for exactly one reason. The quantity anyone actually asks for is

    dE(f : A -> B) = E(B) - E(A)

and ``smartchem.category`` guarantees that any morphism ``f`` has the same atoms and charge
in ``A`` and ``B``. Whatever per-atom offset an oracle's zero encodes therefore appears
identically on both sides and cancels exactly.

**Conservation is the precondition that makes the energy functor well defined.** Without
it, ``E(B) - E(A)`` would be subtracting energies of different collections of matter, which
is meaningless no matter how accurate the oracle is. That is the categorical structure
doing real physical work rather than describing it -- checked in
``tests/test_functor.py::TestConservationLicensesSubtraction``.

Two rules every oracle obeys
----------------------------
1. **Declining is allowed; inventing is not.** An oracle that cannot cover a species
   returns None. It must never return a fabricated number to look complete. The benchmark
   counts refusals separately, so ducking the hard cases cannot improve a score.

2. **Every value carries its provenance and its uncertainty.** A number without a stated
   method and error bar is not a result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..category import Molecule


@dataclass(frozen=True)
class Estimate:
    """
    A single energy prediction with everything needed to judge it.

    ``extrapolation_ev`` is a **signed** model correction carried alongside the value --
    currently the amount a basis-set extrapolation moved this number beyond its largest
    explicit basis. It is signed, and it propagates additively rather than in quadrature,
    because it is a systematic correction rather than a random error: it cancels between
    the two sides of a conserving difference in exactly the way the arbitrary energy zero
    does.

    That distinction is load-bearing and was got wrong once. Treating the per-species
    correction as an independent random error and combining it in quadrature produced
    +/-1.4 eV bars on a method whose real accuracy is 0.04 eV, because it discarded a
    cancellation of roughly 97%. Systematic and random errors do not combine the same way,
    and conflating them destroys the certificate in either direction.
    """
    value_ev: float
    uncertainty_ev: float
    method: str
    seconds: float = 0.0
    notes: str = ""
    #: signed systematic model correction; cancels in differences (see class docstring)
    extrapolation_ev: float = 0.0

    def __add__(self, other: "Estimate") -> "Estimate":
        """
        Combine independent estimates: values add, random uncertainties in quadrature,
        systematic corrections additively **with sign** so they can cancel.

        This is what makes ``E(A (x) B) = E(A) + E(B)`` hold for the *whole* Estimate and
        not merely its central value -- the monoidal functor law has to carry the error bar
        with it, or the certificate degrades silently as a configuration grows.
        """
        return Estimate(
            value_ev=self.value_ev + other.value_ev,
            uncertainty_ev=math.hypot(self.uncertainty_ev, other.uncertainty_ev),
            method=self.method if self.method == other.method
            else f"{self.method}+{other.method}",
            seconds=self.seconds + other.seconds,
            notes="; ".join(n for n in (self.notes, other.notes) if n),
            extrapolation_ev=self.extrapolation_ev + other.extrapolation_ev,
        )

    def __neg__(self) -> "Estimate":
        """Negation keeps the random uncertainty and flips the systematic correction."""
        return Estimate(-self.value_ev, self.uncertainty_ev, self.method,
                        self.seconds, self.notes, -self.extrapolation_ev)

    def __sub__(self, other: "Estimate") -> "Estimate":
        return self + (-other)

    def with_honest_uncertainty(self) -> "Estimate":
        """
        Widen the error bar to at least the size of the net systematic correction.

        A model correction that survived cancellation is a real statement about how much
        this answer depends on the model. If an extrapolation still moves the final number
        by 0.13 eV after the atomic references cancel, the answer is not known to 0.04 eV,
        whatever the tier's average accuracy says.

        Measured motivation: NaCl at cbs(TZ,QZ) lands 3.38 kcal/mol from experiment while
        plain cc-pVQZ lands 0.39 away -- the extrapolation degraded a good answer, and the
        old flat error bar reported the bad one with full confidence. That is the oracle
        inventing rather than declining.
        """
        net = abs(self.extrapolation_ev)
        if net <= self.uncertainty_ev:
            return self
        return Estimate(self.value_ev, net, self.method, self.seconds,
                        (f"{self.notes}; widened to the net extrapolation correction "
                         f"{net:.4f} eV").lstrip("; "),
                        self.extrapolation_ev)

    @staticmethod
    def zero(method: str = "exact") -> "Estimate":
        """The additive identity -- the energy of the empty configuration."""
        return Estimate(0.0, 0.0, method, 0.0, "")

    def __repr__(self) -> str:
        return f"{self.value_ev:.4f} +/- {self.uncertainty_ev:.4f} eV [{self.method}]"


@runtime_checkable
class EnergyOracle(Protocol):
    """Anything that can price a chemical species."""

    name: str
    #: Honest self-assessment: expected MAE in eV. Measured, not asserted -- see
    #: ``python -m smartchem.bench``. Used to pick a tier, never to replace measurement.
    nominal_accuracy_ev: float

    def energy(self, molecule: Molecule) -> Estimate | None:
        """
        Total energy of this species in eV, on this oracle's own consistent zero.

        Returns None if the oracle does not cover the species -- an element it lacks data
        for, a size it cannot handle, a geometry it has no way to obtain. Raise only on a
        genuine internal failure, never to signal "not supported".
        """
        ...


class BaseOracle:
    """
    Convenience base. Implement ``energy``; get the derived quantities for free.

    Subclasses must keep the arbitrary-zero contract: one consistent zero for every species
    a given instance prices.
    """

    name: str = "unnamed"
    nominal_accuracy_ev: float = float("inf")

    def energy(self, molecule: Molecule) -> Estimate | None:  # pragma: no cover
        raise NotImplementedError

    # -- derived ------------------------------------------------------------------
    def atomization_energy(self, molecule: Molecule) -> Estimate | None:
        """
        ``E(free atoms) - E(molecule)``, positive = bound.

        Derived, not primitive. For a diatomic this is the dissociation energy D_e, which
        is what the benchmark compares against experiment (after a ZPE correction applied
        by the caller).

        Note this is exactly the difference the arbitrary zero cancels in: both sides
        contain the same atoms, which is the same condition ``Reaction`` enforces.
        """
        whole = self.energy(molecule)
        if whole is None:
            return None
        total = Estimate.zero(self.name)
        for symbol in molecule.atoms:
            part = self.energy(Molecule.atom(symbol))
            if part is None:
                return None
            total = total + part
        # The subtraction is where systematic corrections cancel; widen only afterwards,
        # on whatever survived. Widening per-species instead would discard the cancellation
        # and inflate a 0.04 eV method to 1.4 eV bars.
        return (total - whole).with_honest_uncertainty()

    def bond_energy(self, symbols: tuple[str, ...]) -> float | None:
        """
        Back-compatible helper: atomization energy of the ground-state species built from
        these atoms. Used by the benchmark, which is written against experimental D0.
        """
        if len(symbols) == 1:
            return 0.0
        if len(symbols) != 2:
            return None
        est = self.atomization_energy(Molecule.diatomic(*symbols))
        return None if est is None else est.value_ev
