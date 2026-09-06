"""ELECTROCHEM-01 / the EM bridge (queue item 5, DOW): sourced standard electrode potentials ->
cell potential, Gibbs free energy, a spontaneity verdict, and the Nernst equation.

Prior art relocated onto (portal-gun, not reinvention): :mod:`smartchem.cell` already models an
electrochemical :class:`~smartchem.cell.Cell` (electron balancing at construction), Faraday's law
(:func:`~smartchem.cell.theoretical_capacity_coulombs`) and a voltage-typed result
(:class:`~smartchem.cell.VoltageEstimate`) -- but :meth:`~smartchem.cell.Cell.open_circuit_voltage`
FAILS CLOSED: it raises "open-circuit voltage requires Gibbs free energy under specified
thermodynamic/electrochemical conditions".  This module supplies exactly that missing piece for the
STANDARD-state case: a SOURCED table of standard reduction potentials E deg (KNOWN physics -- CRC /
Bard & Faulkner reference data, never invented; section 10.4 anti-fabrication), from which E deg_cell,
Delta-G deg = -nFE deg, a spontaneity verdict, and the Nernst potential follow by textbook
electrochemistry.

It closes the DOW-bromine litmus loop with ROUND-17's REDOX-DISPLACE-01.  That round proved
``Cl2 + 2 Br- -> Br2 + 2 Cl-`` is ENUMERABLE (the coupled half-reaction combiner); this module proves
it is SPONTANEOUS at standard state and reproduces WHY chlorine displaces bromide but not the reverse:

    E deg_cell = E deg(Cl2/Cl-) - E deg(Br2/Br-) = 1.358 - 1.087 = +0.271 V > 0  (spontaneous)
    Delta-G deg = -n F E deg_cell = -2 * 96485.332 * 0.271 = -52.3 kJ/mol         (< 0, spontaneous)

and the reverse ``Br2 + 2 Cl- -> Cl2 + 2 Br-`` comes back at -0.271 V (NON-spontaneous) -- the
known-answer calibration this module is pinned against.  For the ELECTROLYTIC leg of Dow's real
process (bromide/chloride oxidised at an anode -- electrons crossing a circuit, the electromagnetic
scope the litmus demands), :func:`minimum_electrolysis_voltage` gives the reversible decomposition
voltage a forced oxidation needs, and the Faraday charge per mole is
:func:`~smartchem.cell.theoretical_capacity_coulombs` (relocated, not reinvented).

W3 (unchanged, the same refusal as :mod:`smartchem.redox_displacement` and
:class:`~smartchem.structure_descent.RedoxHalfReaction`): a standard potential certifies a
THERMODYNAMIC TENDENCY at standard state; it is NEVER a claim that the reaction occurs, at what RATE,
with what overpotential, or under non-standard activities the caller has not supplied.  Fabrication is
refused -- an unsourced couple returns ``None`` (UNKNOWN), never a made-up potential -- and the table
is keyed on the couple's structural :attr:`~smartchem.contracts.Digestible.digest` (canonical
structure), so a species can never borrow another's potential by a shared formula string
(the fail-open lesson).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .contracts import Digestible
from .redox_displacement import HalfReactionCouple, halogen_couple
from .structure_descent import ScissionError

__all__ = [
    "ELECTROCHEM_SCHEMA",
    "FARADAY_C_PER_MOL",
    "GAS_CONSTANT_J_PER_MOL_K",
    "STANDARD_TEMPERATURE_K",
    "SpontaneityVerdict",
    "StandardReductionPotential",
    "CellPotential",
    "STANDARD_REDUCTION_POTENTIALS",
    "couple_potential",
    "standard_cell_potential",
    "displacement_cell_potential",
    "gibbs_free_energy_j_per_mol",
    "spontaneity",
    "nernst_potential",
    "minimum_electrolysis_voltage",
]

ELECTROCHEM_SCHEMA = "smartchem.electrochemistry/standard-potential-v1"

#: Faraday constant, C/mol e-.  A NIST fundamental constant (CODATA 2018: 96485.33212 C/mol).  Restated
#: here (rather than imported from :mod:`smartchem.cell`) so this module stays import-light -- the single
#: source of physical truth is NIST, and ``test_electrochemistry`` pins this equal to ``cell.FARADAY_C_PER_MOL``
#: so the two copies can never drift.
FARADAY_C_PER_MOL = 96485.332
#: Molar gas constant, J/(mol K).  NIST CODATA 2018: 8.314462618 J/(mol K).
GAS_CONSTANT_J_PER_MOL_K = 8.314462618
#: Standard temperature, K (25 deg C) -- the state the tabulated potentials are referenced to.
STANDARD_TEMPERATURE_K = 298.15


class SpontaneityVerdict(str, Enum):
    """The sign of the standard-state driving force -- a THERMODYNAMIC tendency, never a rate.

    ``SPONTANEOUS`` means E deg_cell > 0 (Delta-G deg < 0): the reaction is thermodynamically
    favoured as written at standard state.  It does NOT say the reaction proceeds at a useful rate,
    at what overpotential, or under the caller's actual (non-standard) activities -- W3.
    """

    SPONTANEOUS = "SPONTANEOUS"
    NON_SPONTANEOUS = "NON_SPONTANEOUS"
    AT_EQUILIBRIUM = "AT_EQUILIBRIUM"


def _couple_key(couple: HalfReactionCouple) -> str:
    """The structural key a potential attaches to: the couple's canonical digest (NOT a formula
    string), so a same-formula species can never borrow another couple's potential (fail-open lesson).
    """
    if type(couple) is not HalfReactionCouple:
        raise ScissionError("a standard potential attaches to a HalfReactionCouple")
    return couple.digest


@dataclass(frozen=True)
class StandardReductionPotential(Digestible):
    """A SOURCED standard reduction potential E deg for a :class:`HalfReactionCouple`, written (like the
    couple) in the reduction direction ``oxidized + n e- <-> reduced``.

    ``potential_volts`` is the standard electrode potential vs the standard hydrogen electrode (SHE) at
    ``conditions`` (aqueous, 25 deg C, unit activity by default).  ``citation`` is REQUIRED and must be a
    non-empty provenance string, but its CONTENT is NOT machine-verified (code cannot check a reference is
    real -- evil-morty fold: the docstring used to overclaim "refused at construction").  The trustworthy
    sourced path is :func:`couple_potential`, which returns ONLY the curated
    :data:`STANDARD_REDUCTION_POTENTIALS` entries; a directly-constructed
    :class:`StandardReductionPotential` carries only the provenance the CALLER asserts, exactly as a
    hand-built value would -- so treat the curated table, not arbitrary construction, as the sourced
    authority (section 10.4).  The couple is stored so a lookup can verify the structure it matched.

    PHASE SCOPE (evil-morty fold F5): the couple is phaseless by construction (``halogen_couple`` builds
    ``state=""``) and the tabulated values are the AQUEOUS standard potentials -- the phase the DOW
    displacement actually runs in, so +1.087 V is the CORRECT Br2(aq)/Br- value for the litmus.  A
    phase-specific value (Br2(l) = +1.066 V) is out of scope until a phase-carrying couple API exists; an
    explicitly-phased couple simply misses the table and returns UNKNOWN (fail-closed, never a wrong number).
    """

    schema_version: str
    couple: HalfReactionCouple
    potential_volts: float
    citation: str
    conditions: str = "aqueous, 25 C, unit activity, vs SHE"

    def __post_init__(self) -> None:
        if self.schema_version != ELECTROCHEM_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {ELECTROCHEM_SCHEMA!r}")
        if type(self.couple) is not HalfReactionCouple:
            raise ScissionError("couple must be a HalfReactionCouple")
        if isinstance(self.potential_volts, bool) or not isinstance(self.potential_volts, (int, float)):
            raise ScissionError("potential_volts must be a real number of volts")
        if not math.isfinite(float(self.potential_volts)):
            raise ScissionError("potential_volts must be finite")
        object.__setattr__(self, "potential_volts", float(self.potential_volts))
        for name in ("citation", "conditions"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScissionError(f"a standard potential needs a non-empty {name} (section 10.4: sourced, not invented)")
            object.__setattr__(self, name, value.strip())

    @property
    def electrons(self) -> int:
        """The electron count of the couple this potential is for."""
        return self.couple.electrons

    @property
    def key(self) -> str:
        return _couple_key(self.couple)

    @classmethod
    def of(cls, couple: HalfReactionCouple, potential_volts: float, citation: str,
           conditions: str = "aqueous, 25 C, unit activity, vs SHE") -> "StandardReductionPotential":
        return cls(ELECTROCHEM_SCHEMA, couple, potential_volts, citation, conditions)


#: The SOURCED standard reduction potentials (KNOWN physics; the halogen couples the DOW displacement
#: pairs).  Values from the CRC Handbook of Chemistry and Physics, 97th ed. (2016-2017), "Standard
#: Reduction Potentials" table, cross-checked against Bard & Faulkner, *Electrochemical Methods* 2nd
#: ed., Appendix C.  Aqueous values at 25 C vs SHE.  Br2(aq) is used (not Br2(l), +1.066 V) because the
#: DOW displacement is an aqueous-phase reaction; the citation states the phase.  UNKNOWN for any couple
#: not listed here -- never extrapolated, never invented.
_CRC = "CRC Handbook of Chemistry and Physics, 97th ed. (2016-2017), Standard Reduction Potentials"
_BF = "Bard & Faulkner, Electrochemical Methods 2nd ed., Appendix C"
STANDARD_REDUCTION_POTENTIALS: tuple[StandardReductionPotential, ...] = (
    StandardReductionPotential.of(halogen_couple("F"), 2.866, f"{_CRC}; {_BF}",
                                  "F2(g) + 2 e- <-> 2 F-, aqueous, 25 C vs SHE"),
    StandardReductionPotential.of(halogen_couple("Cl"), 1.358, f"{_CRC}; {_BF}",
                                  "Cl2(g) + 2 e- <-> 2 Cl-, aqueous, 25 C vs SHE"),
    StandardReductionPotential.of(halogen_couple("Br"), 1.087, f"{_CRC}; {_BF}",
                                  "Br2(aq) + 2 e- <-> 2 Br-, aqueous, 25 C vs SHE (Br2(l): +1.066 V)"),
    StandardReductionPotential.of(halogen_couple("I"), 0.536, f"{_CRC}; {_BF}",
                                  "I2(s) + 2 e- <-> 2 I-, aqueous, 25 C vs SHE"),
)

#: keyed on the couple's structural digest (fail-open lesson: never a formula string).
_POTENTIAL_TABLE: dict[str, StandardReductionPotential] = {p.key: p for p in STANDARD_REDUCTION_POTENTIALS}
assert len(_POTENTIAL_TABLE) == len(STANDARD_REDUCTION_POTENTIALS), "duplicate couple in the sourced table"


def couple_potential(couple: HalfReactionCouple) -> "StandardReductionPotential | None":
    """The sourced standard reduction potential for ``couple``, or ``None`` (UNKNOWN) if not tabulated.

    Fail-closed: a couple absent from the sourced table returns ``None`` -- never a fabricated or
    extrapolated potential (section 10.4).  Matched on the couple's structural digest.
    """
    return _POTENTIAL_TABLE.get(_couple_key(couple))


@dataclass(frozen=True)
class CellPotential(Digestible):
    """The standard cell potential of a full redox reaction assembled from a cathode (reduction) couple
    and an anode (oxidation) couple, ``E deg_cell = E deg(cathode) - E deg(anode)``.

    E deg_cell is INTENSIVE -- it does NOT depend on how the reaction is scaled (the electron count is a
    separate, EXTENSIVE quantity that enters :func:`gibbs_free_energy_j_per_mol`).  Both members are
    looked up as REDUCTION potentials; the anode couple is the one physically run in reverse (oxidation).
    Carries the two sourced potentials so a consumer can audit the provenance of the verdict.
    """

    schema_version: str
    cathode: StandardReductionPotential
    anode: StandardReductionPotential
    e_cell_volts: float

    def __post_init__(self) -> None:
        if self.schema_version != ELECTROCHEM_SCHEMA:
            raise ScissionError(f"schema_version must be exactly {ELECTROCHEM_SCHEMA!r}")
        for name in ("cathode", "anode"):
            if type(getattr(self, name)) is not StandardReductionPotential:
                raise ScissionError(f"{name} must be a StandardReductionPotential")
        if isinstance(self.e_cell_volts, bool) or not isinstance(self.e_cell_volts, (int, float)):
            raise ScissionError("e_cell_volts must be a real number")
        if not math.isfinite(float(self.e_cell_volts)):
            raise ScissionError("e_cell_volts must be finite")
        object.__setattr__(self, "e_cell_volts", float(self.e_cell_volts))
        # the invariant the value must satisfy: E_cell = E(cathode) - E(anode) (guards a hand-built edge
        # from carrying an e_cell inconsistent with its own two potentials -- an identity/coherence check).
        expected = self.cathode.potential_volts - self.anode.potential_volts
        if not math.isclose(self.e_cell_volts, expected, abs_tol=1e-9):
            raise ScissionError(
                f"e_cell_volts {self.e_cell_volts} != E(cathode) - E(anode) = {expected} "
                "(a cell potential must equal the difference of its own two electrode potentials)"
            )

    @property
    def verdict(self) -> SpontaneityVerdict:
        return spontaneity(self.e_cell_volts)

    @property
    def balanced_electrons(self) -> int:
        """``n`` for the balanced reaction: the LCM of the two couples' electron counts (the same LCM
        :func:`~smartchem.redox_displacement.combine_half_reactions` computes).  The object HOLDS both
        counts, so n is derived, never guessed (evil-morty fold: ``gibbs`` used to accept an unchecked n)."""
        return math.lcm(self.cathode.electrons, self.anode.electrons)

    def gibbs_j_per_mol(self, electrons: "int | None" = None) -> float:
        """Delta-G deg = -n F E deg_cell for the balanced reaction.

        ``electrons`` DEFAULTS to :attr:`balanced_electrons` (n derived from the two couples the object
        already carries, so a caller cannot silently pass a wrong n and corrupt the quantitative ΔG --
        an evil-morty fold).  A supplied ``electrons`` is VALIDATED against the derived n and a mismatch
        is refused, so the only way to get a ΔG is with the reaction's actual electron balance.
        """
        n = self.balanced_electrons
        if electrons is not None:
            if isinstance(electrons, bool) or not isinstance(electrons, int) or electrons != n:
                raise ScissionError(
                    f"electrons {electrons!r} != the balanced reaction's n = lcm("
                    f"{self.cathode.electrons}, {self.anode.electrons}) = {n}; ΔG needs the actual "
                    "electron balance, not a guess (pass None to derive it)"
                )
        return gibbs_free_energy_j_per_mol(self.e_cell_volts, n)


def standard_cell_potential(*, cathode: HalfReactionCouple, anode: HalfReactionCouple) -> "CellPotential | None":
    """The standard cell potential of the reaction whose ``cathode`` couple is reduced and whose ``anode``
    couple is oxidised, or ``None`` if EITHER couple is unsourced.

    ``E deg_cell = E deg(cathode) - E deg(anode)`` with both looked up as reduction potentials.  A
    positive result means the forward reaction (cathode reduced, anode oxidised) is spontaneous at
    standard state.  Fail-closed: if either potential is UNKNOWN the cell potential is UNKNOWN (``None``),
    never computed from a fabricated half.
    """
    if cathode.element == anode.element:
        raise ScissionError("a cell needs two DIFFERENT redox couples (an electrode cannot be its own counter-electrode)")
    e_cathode = couple_potential(cathode)
    e_anode = couple_potential(anode)
    if e_cathode is None or e_anode is None:
        return None
    return CellPotential(
        ELECTROCHEM_SCHEMA, e_cathode, e_anode,
        e_cathode.potential_volts - e_anode.potential_volts,
    )


def displacement_cell_potential(*, reduction: HalfReactionCouple, oxidation: HalfReactionCouple) -> "CellPotential | None":
    """The standard cell potential of the displacement :func:`~smartchem.redox_displacement.combine_half_reactions`
    builds from the SAME two couples, closing the ROUND-17 loop.

    ``combine_half_reactions`` names its arguments by role: ``reduction`` is the oxidant (its oxidised
    form is REDUCED -> the cathode) and ``oxidation`` is the reductant (its reduced form is OXIDISED ->
    the anode).  So the DOW displacement ``combine_half_reactions(reduction=Cl2/Cl-, oxidation=Br2/Br-)``
    has ``E deg_cell = E deg(Cl2/Cl-) - E deg(Br2/Br-) = +0.271 V`` -- the enumerated reaction is
    spontaneous, and the reverse pairing is -0.271 V (non-spontaneous).  ``None`` if either is unsourced.
    """
    return standard_cell_potential(cathode=reduction, anode=oxidation)


def gibbs_free_energy_j_per_mol(e_cell_volts: float, electrons: int) -> float:
    """Delta-G deg = -n F E deg_cell, in J per mole of reaction extent.

    ``electrons`` is ``n``, the electrons transferred per mole of reaction (for the DOW displacement,
    n = 2, the LCM :func:`~smartchem.redox_displacement.combine_half_reactions` computes).  A positive
    E deg_cell gives a negative Delta-G deg (spontaneous).  This is the exact unit boundary
    :mod:`smartchem.cell` names in its docstring but leaves unbuilt.
    """
    if isinstance(e_cell_volts, bool) or not isinstance(e_cell_volts, (int, float)) or not math.isfinite(float(e_cell_volts)):
        raise ScissionError("e_cell_volts must be a finite real number")
    if isinstance(electrons, bool) or not isinstance(electrons, int) or electrons < 1:
        raise ScissionError("electrons (n) must be a positive integer")
    return -electrons * FARADAY_C_PER_MOL * float(e_cell_volts)


def spontaneity(e_cell_volts: float) -> SpontaneityVerdict:
    """The standard-state spontaneity verdict from the sign of ``e_cell_volts`` (E > 0 -> Delta-G < 0 ->
    spontaneous).  W3: a THERMODYNAMIC tendency, never a rate."""
    if isinstance(e_cell_volts, bool) or not isinstance(e_cell_volts, (int, float)) or not math.isfinite(float(e_cell_volts)):
        raise ScissionError("e_cell_volts must be a finite real number")
    v = float(e_cell_volts)
    if math.isclose(v, 0.0, abs_tol=1e-12):
        return SpontaneityVerdict.AT_EQUILIBRIUM
    return SpontaneityVerdict.SPONTANEOUS if v > 0 else SpontaneityVerdict.NON_SPONTANEOUS


def nernst_potential(standard_volts: float, electrons: int, reaction_quotient: float,
                     temperature_k: float = STANDARD_TEMPERATURE_K) -> float:
    """The Nernst potential ``E = E deg - (R T / n F) ln Q`` under non-standard activities.

    At 25 C this is the textbook 59.2/n mV per decade of ``Q`` (``R T / F = 0.025693 V``; times ln 10 =
    0.05916 V).  ``reaction_quotient`` (Q) must be a positive real; ``temperature_k`` a positive real.
    This is the ONLY concession to non-standard state, and it still assumes the caller supplies a real Q
    -- it does not measure activities itself (W3).
    """
    if isinstance(standard_volts, bool) or not isinstance(standard_volts, (int, float)) or not math.isfinite(float(standard_volts)):
        raise ScissionError("standard_volts must be a finite real number")
    if isinstance(electrons, bool) or not isinstance(electrons, int) or electrons < 1:
        raise ScissionError("electrons (n) must be a positive integer")
    if isinstance(reaction_quotient, bool) or not isinstance(reaction_quotient, (int, float)) or reaction_quotient <= 0 or not math.isfinite(float(reaction_quotient)):
        raise ScissionError("reaction_quotient (Q) must be a finite positive real number")
    if isinstance(temperature_k, bool) or not isinstance(temperature_k, (int, float)) or temperature_k <= 0 or not math.isfinite(float(temperature_k)):
        raise ScissionError("temperature_k must be a finite positive real number")
    rt_over_nf = GAS_CONSTANT_J_PER_MOL_K * float(temperature_k) / (electrons * FARADAY_C_PER_MOL)
    return float(standard_volts) - rt_over_nf * math.log(float(reaction_quotient))


def minimum_electrolysis_voltage(cell_potential: CellPotential) -> float:
    """The reversible (thermodynamic minimum) applied voltage to DRIVE a non-spontaneous reaction by
    electrolysis -- the electron/circuit leg of Dow's process (bromide/chloride oxidised at an anode).

    For a spontaneous cell (E deg_cell > 0) this is 0 -- no external voltage is needed to drive it (it is
    a galvanic source, not an electrolytic load).  For a non-spontaneous one it is ``-E deg_cell = |E deg_cell|``,
    the decomposition voltage.  This is the REVERSIBLE minimum only: real electrolysis needs this PLUS an
    overpotential (activation + concentration + iR) this module deliberately does NOT model (W3 / the same
    "stated absent, not approximated" discipline as :mod:`smartchem.cell`).  Faraday's law for the charge
    a given amount of product costs is :func:`smartchem.cell.theoretical_capacity_coulombs` (reused, not
    reinvented).
    """
    if type(cell_potential) is not CellPotential:
        raise ScissionError("minimum_electrolysis_voltage takes a CellPotential")
    return max(0.0, -cell_potential.e_cell_volts)
