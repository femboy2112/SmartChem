"""Sourced standard thermodynamic data (ΔfH°, S°) -- the inputs M1 feasibility DERIVES ΔG from.

A tiny, sourced seed of standard formation enthalpies and standard molar entropies at 298.15 K, 1 bar, in
each species' standard-state phase.  From these, an ESTABLISHED model (Hess's law for ΔH, the Gibbs
relation ΔG = ΔH - TΔS) computes a reaction's ΔG -- a value we do NOT store but *derive*, exactly as the
PySCF oracle computes an atomization energy rather than looking one up.  That is reproducing known
chemistry, not inventing new physics.

The universality contract (identical to :mod:`smartchem.data.stability`)
----------------------------------------------------------------------
* The compiler holds a :class:`ThermoTable`, not this module's tuple, so a chemist EXTENDS coverage for any
  compound with :meth:`ThermoTable.with_records` and passes the result in -- the universality lever.
* A lookup miss returns ``None`` -> feasibility renders a LOUD ``UNKNOWN`` (never a fabricated ΔG).  Absence
  is never a guess; the seed is deliberately small and every value carries its source.
* Values are the internationally-agreed reference set where one exists (CODATA Key Values for
  Thermodynamics) and NIST/CRC otherwise; each record cites which.

What this does NOT do: it never invents a formation enthalpy or entropy for a compound it has no source
for, and it makes no claim about a reaction's RATE -- ΔG says *whether* a reaction is thermodynamically
favorable, never *how fast* (kinetics is a separate, unbuilt model; see the roadmap).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import Digestible

__all__ = [
    "ThermoRef",
    "ThermoTable",
    "SEED_THERMO_REFS",
    "DEFAULT_THERMO",
    "REFERENCE_TEMPERATURE_K",
]

#: The temperature the seed's ΔfH° / S° are referenced to (standard state, 1 bar).
REFERENCE_TEMPERATURE_K = 298.15


@dataclass(frozen=True)
class ThermoRef(Digestible):
    """One species' SOURCED standard thermodynamic data: ΔfH° (kJ/mol) and S° (J/mol/K) at 298.15 K.

    ``phase`` is the standard-state phase the values are for (the ΔfH°/S° of liquid water differ from
    steam); it is carried for honesty and appears in provenance.  Formation enthalpy of an element in its
    reference state is 0 by definition.
    """

    formula: str
    name: str
    dhf_kj_per_mol: float
    s_j_per_mol_k: float
    phase: str
    provenance: str
    #: How the ΔfH°/S° were obtained: ``"SOURCED"`` (a measured/tabulated value, the default), or a
    #: derivation grade (``"DERIVED"`` / ``"PREDICTED"``) when the record was ESTIMATED by group additivity
    #: (:mod:`smartchem.data.thermo_groups`).  ``compare=False`` keeps it OUT of the semantic digest and out
    #: of equality (``contracts.canonical_payload`` skips ``field.compare is False`` fields), so tagging a
    #: record's provenance-grade never moves any fingerprint -- it is metadata, not identity.
    grade: str = field(default="SOURCED", compare=False)

    def __post_init__(self) -> None:
        for field_name in ("formula", "name", "phase", "provenance", "grade"):
            v = getattr(self, field_name)
            if not isinstance(v, str) or not v:
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("dhf_kj_per_mol", "s_j_per_mol_k"):
            v = getattr(self, field_name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
        if self.s_j_per_mol_k < 0:
            raise ValueError("standard molar entropy S° cannot be negative (third law)")


@dataclass(frozen=True)
class ThermoTable(Digestible):
    """An immutable set of sourced thermodynamic records, resolvable by ``(formula, name)`` or by formula.

    Mirrors :class:`~smartchem.data.stability.StabilityTable`: the compiler holds a table, a caller extends
    it with :meth:`with_records`, records are deduplicated by ``(formula, name)`` (a later record wins).
    """

    records: tuple[ThermoRef, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(type(r) is not ThermoRef for r in self.records):
            raise TypeError("records must be a tuple of ThermoRef values")

    def with_records(self, *records: ThermoRef) -> "ThermoTable":
        by_key: dict[tuple[str, str], ThermoRef] = {(r.formula, r.name): r for r in self.records}
        for r in records:
            if type(r) is not ThermoRef:
                raise TypeError("with_records takes ThermoRef values")
            by_key[(r.formula, r.name)] = r
        return ThermoTable(tuple(sorted(by_key.values(), key=lambda r: (r.formula, r.name))))

    def for_named(self, formula: str, name: str) -> ThermoRef | None:
        for r in self.records:
            if r.formula == formula and r.name == name:
                return r
        return None

    def for_formula(self, formula: str) -> ThermoRef | None:
        """The record for a formula IFF exactly one is tabulated (else ``None``) -- the same isomer-ambiguity
        honesty as stability: attaching one isomer's thermo to a formula naming several would be wrong."""
        hits = [r for r in self.records if r.formula == formula]
        return hits[0] if len(hits) == 1 else None


#: The SEED -- sourced standard thermodynamic data, litmus-focused (small molecules whose ΔG we can DERIVE
#: and calibrate against known values: the 2H2+O2 water reaction recovers ΔG°=-474 kJ, Haber recovers
#: -33 kJ and its ~465 K sign-flip).  Tiny by design; injectable per call for any chemical, NOT a whitelist.
_CODATA = "CODATA Key Values for Thermodynamics (Cox, Wagman & Medvedev 1989)"
_NIST = "NIST Chemistry WebBook / CRC Handbook 97th ed."

SEED_THERMO_REFS: tuple[ThermoRef, ...] = (
    ThermoRef("H2", "hydrogen", 0.0, 130.68, "gas", f"element reference state; S° {_CODATA}"),
    ThermoRef("O2", "oxygen", 0.0, 205.15, "gas", f"element reference state; S° {_CODATA}"),
    ThermoRef("N2", "nitrogen", 0.0, 191.61, "gas", f"element reference state; S° {_NIST}"),
    ThermoRef("H2O", "water", -285.83, 69.95, "liquid", f"ΔfH° and S° (liquid, 298.15 K) {_CODATA}"),
    ThermoRef("H3N", "ammonia", -45.9, 192.8, "gas", f"ΔfH° and S° (gas, 298.15 K) {_NIST}"),
    ThermoRef("CO2", "carbon dioxide", -393.51, 213.79, "gas", f"ΔfH° and S° (gas, 298.15 K) {_CODATA}"),
    ThermoRef("CO", "carbon monoxide", -110.53, 197.66, "gas", f"ΔfH° and S° (gas, 298.15 K) {_CODATA}"),
    ThermoRef("CH4", "methane", -74.6, 186.3, "gas", f"ΔfH° and S° (gas, 298.15 K) {_NIST}"),
)

#: A convenience default seed; extended per call for any other chemical, NOT a whitelist.
DEFAULT_THERMO = ThermoTable(SEED_THERMO_REFS)
