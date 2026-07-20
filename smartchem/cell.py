"""
Electrochemical-cell bookkeeping and a separate ideal load model.

This prototype represents a cell as two closed half-reaction histories containing explicit
typed negative-charge carriers. The chemical core does not yet model circuit ports, spatially
separated electrodes, potentials, current continuity or open-system composition. The
``OperatingPoint`` class below is a separate ideal-resistor calculation, not behavioral
semantics for the reaction object.

What the supplied factorisation records
---------------------------------------

    anode      Zn + 2 OH- -> ZnO + H2O + 2 e-
    cathode    2 MnO2 + H2O + 2 e- -> Mn2O3 + 2 OH-
    ---------------------------------------------------
    overall    Zn + 2 MnO2 -> ZnO + Mn2O3

This is a lumped textbook factorisation for structural tests, not a complete commercial-AA
mechanism. Real alkaline discharge descriptions commonly resolve MnOOH formation and
additional phase/transport behavior that this prototype does not represent.

The overall endpoint reaction does not retain the explicit carriers because they cancel
between the two half-reactions. In this data model ``Cell`` therefore obtains ``n`` from the
supplied anode/cathode factorisation and validates matched carrier type and elementary charge
quanta. This is useful structural bookkeeping, but it is not a general theorem that voltage
is determined by a path, and an arbitrary ``Reaction.path`` is not an electrochemical model.

The unit boundary
-----------------
The thermodynamic statement is ``dG = -n F E``. With molar Gibbs energy converted to eV
per reaction event and charge counted in electrons:

    E [volts] = -dG [eV] / n

This is the unit conversion when ``dG`` is Gibbs free energy per reaction event. The bundled
oracles return a different quantity, ``dE``. Their
``-dE/n`` is exposed only as ``energy_equivalent_voltage`` with a voltage-typed result;
``open_circuit_voltage`` fails closed until a real Gibbs/electrochemical model exists.

What this module does NOT do
----------------------------
It does not model kinetics. There is no time, no rate, no diffusion. The operating point
under a load is an algebraic consequence of a supplied source voltage and two resistances,
which is exact for that ideal lumped model and is *not* the whole story for a real cell (concentration
polarisation, double-layer charging, and everything else that makes a discharge curve
sag). Those are stated as absent rather than approximated silently.

The cross-measurand diagnostic remains useful only as an API warning: the heuristic's
``-dE/n`` proxy is 8.5 V while the illustrative cell voltage is about 1.4--1.5 V. Because
electronic endpoint energy and electrochemical Gibbs free energy are not the same
measurand, this is not a calibration or falsification of the energy oracle. It is evidence
that the proxy must not be labeled, fitted, or validated as OCV.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from numbers import Real

from .category import Config, Molecule, Reaction, identity, reaction_residue
from .oracle.base import EnergyOracle
from .thermo import reaction_energy

#: Coulombs per mole of electrons. The one physical constant in this module, and it buys
#: only the conversion from "how many electrons" to "how many amp-hours" -- never a voltage.
FARADAY_C_PER_MOL = 96485.332


def _electron_quanta(config: Config) -> int:
    """Elementary negative-charge quanta carried by zero-matter objects."""
    total = 0
    for molecule in config.species:
        if molecule.atoms or molecule.charge == 0:
            continue
        if molecule.charge > 0:
            raise ValueError(
                "Cell currently supports electron carriers, not positive holes; "
                "use a typed charge-port model for mixed carrier physics"
            )
        total += -molecule.charge
    return total


def _carrier_inventory(config: Config) -> Counter[Molecule]:
    """Typed negative carriers in a configuration, including multiplicity."""
    inventory: Counter[Molecule] = Counter()
    for molecule in config.species:
        if molecule.atoms or molecule.charge == 0:
            continue
        if molecule.charge > 0:
            raise ValueError(
                "Cell currently supports electron carriers, not positive holes; "
                "use a typed charge-port model for mixed carrier physics"
            )
        inventory[molecule] += 1
    return inventory


def _net_inventory(after: Config, before: Config) -> Counter[Molecule]:
    """Signed change in typed carrier inventory."""
    change = _carrier_inventory(after)
    change.subtract(_carrier_inventory(before))
    return +change


def _difference(a: Config, b: Config) -> Config:
    """
    Multiset difference ``a - b``: species in ``a`` beyond what ``b`` already supplies.

    Multiset, not set. A cell that consumes two MnO2 while the other half supplies one
    still needs one more, and a set difference would say it needs none.
    """
    remaining = list(b.species)
    out = []
    for m in a.species:
        if m in remaining:
            remaining.remove(m)
        else:
            out.append(m)
    return Config(tuple(out))


@dataclass(frozen=True)
class Cell:
    """
    Two half-reactions that compose into a whole cell.

    ``anode`` must produce carriers and ``cathode`` must consume the same number, or this
    is not a cell. Both conditions are checked at construction, in the same spirit as
    ``Reaction`` refusing to build a mass-violating morphism: a cell whose electrons do not
    balance is not a cell with a bug, it is not a cell.
    """
    anode: Reaction
    cathode: Reaction
    name: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.anode, Reaction) or not isinstance(self.cathode, Reaction):
            raise TypeError("anode and cathode must be Reaction values")
        if not isinstance(self.name, str):
            raise TypeError("cell name must be a string")
        anode_produced = _net_inventory(self.anode.cod, self.anode.dom)
        anode_consumed = _net_inventory(self.anode.dom, self.anode.cod)
        cathode_consumed = _net_inventory(self.cathode.dom, self.cathode.cod)
        cathode_produced = _net_inventory(self.cathode.cod, self.cathode.dom)
        produced = _electron_quanta(self.anode.cod) - _electron_quanta(self.anode.dom)
        consumed = _electron_quanta(self.cathode.dom) - _electron_quanta(self.cathode.cod)
        if produced <= 0 or anode_consumed:
            raise ValueError(
                f"anode must produce charge carriers; it nets {produced}. "
                f"Spell them with Molecule.carrier(label, charge), not Molecule.atom -- "
                f"an electron booked as matter makes the half-reaction unconstructible.")
        if consumed <= 0 or cathode_produced:
            raise ValueError("cathode must consume, not produce, typed electron carriers")
        if produced != consumed or anode_produced != cathode_consumed:
            raise ValueError(
                f"the circuit does not close: anode produces {produced} charge quanta "
                f"as {dict(anode_produced)!r}, cathode consumes {consumed} as "
                f"{dict(cathode_consumed)!r}")

    @property
    def electrons(self) -> int:
        """``n``: elementary charge quanta crossing the external circuit per reaction."""
        return _electron_quanta(self.anode.cod) - _electron_quanta(self.anode.dom)

    def overall(self) -> Reaction:
        """
        The composite, with the carriers cancelled -- the reaction a chemist would write.

        Each half is padded with an identity on whatever the other half needs, using the
        left-first ``scheduled_product`` compatibility operation, so that one codomain is
        exactly the other domain. This makes sequential composition well typed. It does not
        construct a parallel morphism tensor or prove that a physical external circuit is
        closed.

        The padding is a **multiset difference**, which is the only choice that is both
        sufficient and minimal:

            X = cathode.dom - anode.cod        what the anode side is missing
            Y = anode.cod   - cathode.dom      what the cathode side is missing

        then ``anode.cod (+) X == cathode.dom (+) Y`` by construction. For the AA cell
        that gives X = {2 MnO2} and Y = {ZnO}, while the water -- produced by the anode
        and consumed by the cathode -- is padded into neither, because it is already
        present on both sides. Adding it anyway was the first version of this method and
        it failed to compose, which is the failure mode a smart constructor is for.
        """
        pad_left = _difference(self.cathode.dom, self.anode.cod)
        pad_right = _difference(self.anode.cod, self.cathode.dom)
        left = self.anode.scheduled_product(identity(pad_left))
        right = identity(pad_right).scheduled_product(self.cathode)
        return left.then(right)

    def net_reaction(self) -> tuple[Config, Config]:
        """What is actually consumed and produced, spectators removed."""
        return reaction_residue(self.overall())

    # -- energetics ---------------------------------------------------------------
    def energy_equivalent_voltage(self, oracle: EnergyOracle) -> "VoltageEstimate | None":
        """
        Diagnostic ``-dE/n`` energy-equivalent potential, in volts.

        This is **not an electrochemical open-circuit voltage**. OCV requires ``dG`` under
        specified phases, temperature, activities, solvent and electrode state; bundled
        oracles provide none of those. This helper remains useful for diagnosing the size
        and sign of a raw energy model without mislabelling it as a measurable cell voltage.
        """
        delta_e = reaction_energy(self.overall(), oracle)
        if delta_e is None:
            return None
        n = self.electrons
        return VoltageEstimate(
            value_volts=-delta_e.value_ev / n,
            uncertainty_volts=delta_e.uncertainty_ev / n,
            method=delta_e.method,
            seconds=delta_e.seconds,
            notes=(f"{delta_e.notes}; -dE/n diagnostic, not electrochemical OCV; "
                   f"n={n}").lstrip("; "),
            systematic_volts=-delta_e.systematic_ev / n,
            systematic_terms=tuple(
                (source, -coefficient / n)
                for source, coefficient in (delta_e.systematic_terms or ())
            ),
        )

    def open_circuit_voltage(self, _oracle: EnergyOracle):
        """Fail closed until a Gibbs/electrochemical oracle and explicit context exist."""
        raise NotImplementedError(
            "open-circuit voltage requires Gibbs free energy under specified "
            "thermodynamic/electrochemical conditions"
        )


@dataclass(frozen=True)
class VoltageEstimate:
    """A voltage-typed result with source-aware systematic sensitivities."""

    value_volts: float
    uncertainty_volts: float
    method: str
    seconds: float = 0.0
    notes: str = ""
    systematic_volts: float = 0.0
    systematic_terms: tuple[tuple[str, float], ...] | None = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        for name in ("value_volts", "uncertainty_volts", "seconds", "systematic_volts"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, float(value))
        if self.uncertainty_volts < 0 or self.seconds < 0:
            raise ValueError("voltage uncertainty and seconds must be non-negative")
        if not isinstance(self.method, str) or not self.method:
            raise ValueError("method must be a non-empty provenance label")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be a string")

        raw_terms = (
            ((f"legacy-systematic:{self.method}", self.systematic_volts),)
            if self.systematic_terms is None and self.systematic_volts != 0.0
            else (() if self.systematic_terms is None else self.systematic_terms)
        )
        if not isinstance(raw_terms, tuple):
            raise TypeError("systematic_terms must be a tuple of (source, coefficient) pairs")
        combined: dict[str, float] = {}
        for item in raw_terms:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError("systematic_terms must contain (source, coefficient) pairs")
            source, coefficient = item
            if not isinstance(source, str) or not source:
                raise ValueError("systematic source IDs must be non-empty strings")
            if isinstance(coefficient, bool) or not isinstance(coefficient, Real):
                raise TypeError("systematic coefficients must be real numbers")
            coefficient = float(coefficient)
            if not math.isfinite(coefficient):
                raise ValueError("systematic coefficients must be finite")
            updated = combined.get(source, 0.0) + coefficient
            if not math.isfinite(updated):
                raise ValueError(f"combined systematic coefficient for {source!r} is not finite")
            combined[source] = updated
        terms = tuple(sorted((source, value) for source, value in combined.items() if value))
        total = sum(value for _source, value in terms)
        magnitude = sum(abs(value) for _source, value in terms)
        if not math.isfinite(total) or not math.isfinite(magnitude):
            raise ValueError("combined systematic terms must have finite total and magnitude")
        object.__setattr__(self, "systematic_terms", terms)
        object.__setattr__(self, "systematic_volts", total)

    @property
    def systematic_magnitude_volts(self) -> float:
        """Sum of surviving named sensitivity magnitudes; not a calibrated error bound."""
        return sum(abs(value) for _source, value in (self.systematic_terms or ()))


@dataclass(frozen=True)
class OperatingPoint:
    """
    A cell delivering current into a resistive load.

    Exact for a DC load given an open-circuit voltage and an internal resistance. The
    identity worth checking is the power balance:

        ocv * current == power_load + power_internal

    which holds by construction here and is asserted in the tests anyway, because an
    identity that holds by construction is exactly the kind that stops holding when
    somebody edits the construction.
    """
    ocv_volts: float
    internal_ohms: float
    load_ohms: float

    def __post_init__(self) -> None:
        for name in ("ocv_volts", "internal_ohms", "load_ohms"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a real number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.internal_ohms < 0 or self.load_ohms < 0:
            raise ValueError("resistances must be non-negative")
        if self.internal_ohms + self.load_ohms == 0:
            raise ValueError("total circuit resistance must be positive")

    @property
    def current_amps(self) -> float:
        return self.ocv_volts / (self.internal_ohms + self.load_ohms)

    @property
    def terminal_volts(self) -> float:
        """What a voltmeter across the terminals reads: OCV less the internal drop."""
        return self.ocv_volts - self.current_amps * self.internal_ohms

    @property
    def power_load_watts(self) -> float:
        return self.current_amps ** 2 * self.load_ohms

    @property
    def power_internal_watts(self) -> float:
        """Dissipated as heat inside the cell. This is why a shorted battery gets hot."""
        return self.current_amps ** 2 * self.internal_ohms

    @property
    def efficiency(self) -> float:
        """Fraction of ideal Thevenin-source power reaching the load."""
        total = self.power_load_watts + self.power_internal_watts
        return self.power_load_watts / total if total else 0.0


def matched_load_ohms(internal_ohms: float) -> float:
    """
    The load that extracts maximum instantaneous POWER in the fixed linear model, which is
    not the load that maximises delivered energy over a real discharge. ``R_load =
    R_internal`` -- the maximum power transfer theorem -- and at that operating point half
    the ideal Thevenin-source power is dissipated internally.

    Worth naming because it is a genuine and counterintuitive consequence: in this ideal
    fixed-parameter model, maximum load power dissipates the other half of the instantaneous
    source power internally. Electrical charge capacity itself is a different quantity.
    """
    if isinstance(internal_ohms, bool) or not isinstance(internal_ohms, Real):
        raise TypeError("internal_ohms must be a real number")
    if not math.isfinite(float(internal_ohms)) or internal_ohms <= 0:
        raise ValueError("internal_ohms must be finite and positive")
    return float(internal_ohms)


def theoretical_capacity_coulombs(
    moles_limiting: float,
    electrons: int,
    stoichiometric_coefficient: float = 1.0,
) -> float:
    """
    Charge available from a given amount of the limiting reagent.

    If the balanced reaction transfers ``n`` electrons per reaction event and consumes
    ``nu`` moles of the limiting reagent per mole of reaction extent, then
    ``Q = (n / nu) * moles_limiting * F``. The historical two-argument call retains
    ``nu=1``. This is a ceiling only for the specified reaction and limiting inventory;
    side reactions or different chemistry require their own bookkeeping.
    """
    if isinstance(moles_limiting, bool) or not isinstance(moles_limiting, Real):
        raise TypeError("moles_limiting must be a real number")
    if not math.isfinite(float(moles_limiting)) or moles_limiting < 0:
        raise ValueError("moles_limiting must be finite and non-negative")
    if isinstance(electrons, bool) or not isinstance(electrons, int):
        raise TypeError("electrons must be an integer")
    if electrons < 0:
        raise ValueError("electrons must be non-negative")
    if isinstance(stoichiometric_coefficient, bool) or not isinstance(
        stoichiometric_coefficient, Real
    ):
        raise TypeError("stoichiometric_coefficient must be a real number")
    if (not math.isfinite(float(stoichiometric_coefficient))
            or stoichiometric_coefficient <= 0):
        raise ValueError("stoichiometric_coefficient must be finite and positive")
    return (electrons / float(stoichiometric_coefficient)) * float(
        moles_limiting
    ) * FARADAY_C_PER_MOL


def coulombs_to_mah(coulombs: float) -> float:
    """Amp-hours are the unit batteries are actually sold in. 1 mAh = 3.6 C."""
    if isinstance(coulombs, bool) or not isinstance(coulombs, Real):
        raise TypeError("coulombs must be a real number")
    if not math.isfinite(float(coulombs)) or coulombs < 0:
        raise ValueError("coulombs must be finite and non-negative")
    return float(coulombs) / 3.6
