"""
Electrochemical cells: where the chemistry becomes a circuit.

A battery is the place the two halves of this project meet. The categorical layer already
hosts both -- reactions as conserving morphisms, circuits as the same conservation law over
charge carriers -- and a cell is the object that is *simultaneously* both: a chemical
reaction whose electrons are made to take the long way round, through a load.

The structural claim, and it is not decoration
----------------------------------------------
A cell voltage is **a property of the factorisation, not of the overall reaction**.

    anode      Zn + 2 OH- -> ZnO + H2O + 2 e-
    cathode    2 MnO2 + H2O + 2 e- -> Mn2O3 + 2 OH-
    ---------------------------------------------------
    overall    Zn + 2 MnO2 -> ZnO + Mn2O3

The overall reaction does not mention electrons: they appear on both sides of the
composite and cancel as spectators. So no function of ``(dom, cod)`` can recover ``n``,
and no function of ``(dom, cod)`` can therefore return a voltage. ``Reaction.path``
remembers the intermediate configuration, which is where the electrons still are.

That is not a limitation to work around; it is physically exact. A cell voltage genuinely
is undetermined by the overall chemistry -- it depends on how the cell splits it into
half-cells, which is a design choice about the cell and not a fact about the reaction.
The category enforces the distinction for free, and enforces that the electrons balance:
``tests/test_domain_neutral.py::TestAnElectrodeIsAMorphism``.

The unit choice pays for itself here
------------------------------------
The thermodynamic statement is ``dG = -n F E``. With energy in eV and charge counted in
electrons, ``F / N_A`` is exactly the elementary charge, so dividing both sides by it:

    E [volts] = -dE [eV] / n

with **no physical constant anywhere**. A volt is an electron-volt per electron; that is
what the unit means. The only place a constant appears in this module is converting a
count of electrons into coulombs for capacity, and it is named there.

What this module does NOT do
----------------------------
It does not model kinetics. There is no time, no rate, no diffusion. The operating point
under a load is an algebraic consequence of the open-circuit voltage and two resistances,
which is exact for a DC load and is *not* the whole story for a real cell (concentration
polarisation, double-layer charging, and everything else that makes a discharge curve
sag). Those are stated as absent rather than approximated silently.

It also does not, at present, have an oracle that can price the species involved. That is
measured rather than assumed -- see ``tests/test_cell.py::TestTheHeuristicOracleFailsThisLitmus``,
which records the heuristic oracle predicting **8.5 V for a 1.5 V cell**, with an error bar
that excludes the true answer. The structure reaches further than the energy models, again,
and the honest thing is to report the gap with a number on it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .category import Config, Molecule, Reaction, identity, reaction_residue
from .oracle.base import Estimate, EnergyOracle
from .thermo import reaction_energy

#: Coulombs per mole of electrons. The one physical constant in this module, and it buys
#: only the conversion from "how many electrons" to "how many amp-hours" -- never a voltage.
FARADAY_C_PER_MOL = 96485.332


def _carriers(config: Config) -> int:
    """How many charge carriers (zero-atom charged objects) this configuration holds."""
    return sum(1 for m in config.species if not m.atoms and m.charge != 0)


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
        produced = _carriers(self.anode.cod) - _carriers(self.anode.dom)
        consumed = _carriers(self.cathode.dom) - _carriers(self.cathode.cod)
        if produced <= 0:
            raise ValueError(
                f"anode must produce charge carriers; it nets {produced}. "
                f"Spell them with Molecule.carrier(label, charge), not Molecule.atom -- "
                f"an electron booked as matter makes the half-reaction unconstructible.")
        if produced != consumed:
            raise ValueError(
                f"the circuit does not close: anode produces {produced} carriers, "
                f"cathode consumes {consumed}")

    @property
    def electrons(self) -> int:
        """``n``: carriers crossing the external circuit per turn of the cell reaction."""
        return _carriers(self.anode.cod) - _carriers(self.anode.dom)

    def overall(self) -> Reaction:
        """
        The composite, with the carriers cancelled -- the reaction a chemist would write.

        Each half is tensored with the identity on whatever the other half needs, so that
        one codomain IS the other domain. Composition requires exact equality, and making
        it hold is precisely what "the circuit is closed" means categorically.

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
        left = self.anode.tensor(identity(pad_left))
        right = identity(pad_right).tensor(self.cathode)
        return left.then(right)

    def net_reaction(self) -> tuple[Config, Config]:
        """What is actually consumed and produced, spectators removed."""
        return reaction_residue(self.overall())

    # -- energetics ---------------------------------------------------------------
    def open_circuit_voltage(self, oracle: EnergyOracle) -> Estimate | None:
        """
        ``E = -dE / n``, in volts, or None if the oracle cannot price the cell.

        The returned ``Estimate`` is in VOLTS, not eV: value, uncertainty and the
        systematic channel are all divided by ``n``, which is exact because ``n`` is an
        integer count and carries no error of its own.
        """
        de = reaction_energy(self.overall(), oracle)
        if de is None:
            return None
        n = self.electrons
        return Estimate(
            value_ev=-de.value_ev / n,
            uncertainty_ev=de.uncertainty_ev / n,
            method=de.method,
            seconds=de.seconds,
            notes=(f"{de.notes}; volts, n={n}").lstrip("; "),
            systematic_ev=-de.systematic_ev / n,
        )


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
        """Fraction of chemical power reaching the load. Maximised as load -> infinity."""
        total = self.power_load_watts + self.power_internal_watts
        return self.power_load_watts / total if total else 0.0


def matched_load_ohms(internal_ohms: float) -> float:
    """
    The load that extracts maximum POWER, which is not the load that extracts maximum
    energy. ``R_load = R_internal`` -- the maximum power transfer theorem -- and at that
    point efficiency is exactly 50%: half the chemical energy is heating the battery.

    Worth naming because it is a genuine and counterintuitive consequence, and because a
    cell designed for maximum power is designed to waste half its capacity.
    """
    return internal_ohms


def theoretical_capacity_coulombs(moles_limiting: float, electrons: int) -> float:
    """
    Charge available from a given amount of the limiting reagent.

    ``Q = n * moles * F``. This is the ceiling a real cell is measured against and can
    never exceed -- a rated capacity above this number would mean the chemistry produced
    more electrons than its stoichiometry allows, which is the electrical analogue of a
    mass-violating reaction.
    """
    return electrons * moles_limiting * FARADAY_C_PER_MOL


def coulombs_to_mah(coulombs: float) -> float:
    """Amp-hours are the unit batteries are actually sold in. 1 mAh = 3.6 C."""
    return coulombs / 3.6
