"""Sourced physical-stability thresholds for the composability verifier (E1) -- a SEED, not a boundary.

The Experiment Compiler's E1 rung asks a constraint-satisfaction question, not a chemistry one: *does an
intermediate survive the transition to the next step's declared conditions?*  Answering it needs SOURCED
thresholds -- a melting point, a boiling point, a decomposition onset, or the flat fact that a species is
never isolable (generated and consumed in situ).

The universality contract (read this before you assume the six records below are the whole world)
-------------------------------------------------------------------------------------------------
The Experiment Compiler is a REASONING ENGINE over whatever sourced data it is given, not an encyclopedia
of six drugs.  The formal layers (conservation, the composability *logic*, the stoichiometric ceiling,
equipment-from-conditions) run on ANY molecule the parser accepts -- no whitelist anywhere.  This module
is only the *data* under E1, and it is deliberately structured so that any chemical works:

* :data:`DEFAULT_STABILITY` is a small, litmus-focused SEED table -- every entry sourced.  It is a
  convenience default, never the set of chemicals the compiler "supports".
* :meth:`StabilityTable.with_records` returns an EXTENDED, immutable table, so a chemist throwing an
  arbitrary compound at the compiler injects its sourced thresholds at call time and they flow straight
  through.  This is the primary path for "any chemical": you bring the compound and its known facts.
* A lookup miss returns ``None`` -> E1 renders a LOUD ``UNKNOWN`` transition, never "stable".  Absence is
  never a green light, and it is never a crash: any molecule resolves (to a record or to ``None``).

What this module does NOT do, on purpose: it never *predicts* a threshold for a compound it has no source
for.  A decomposition onset for an arbitrary molecule is not known chemistry, and inventing one is the
forbidden "new physics".  Missing == UNKNOWN, always.  (Thermochemistry, which the repo genuinely sources
broadly, is E3's job via :mod:`smartchem.data.reference`; that is an established-model path, labelled as
one -- and it, too, degrades to UNKNOWN off its coverage.)

Doctrine (identical to :mod:`smartchem.data.hazards`, and load-bearing)
----------------------------------------------------------------------
* **Sourced, never invented.**  Every stored figure carries a provenance and a below-certified status.
* **UNKNOWN is not "stable".**  An absent record means *unassessed*, never *survives*.
* **Isomer-specific.**  Thresholds belong to a *compound*, not a bare formula; each record names its
  compound, and the structure registry (:mod:`smartchem.structure`) licenses attaching it to a node.

What a threshold means for E1
-----------------------------
* ``decomposition_onset`` (K): at or above its low bound the species *decomposes* rather than persists, so
  a transition that heats it there destroys it -- a ``DEGENERATE`` verdict, citing this onset.
* ``melting`` / ``boiling`` (K, at ~1 atm): the phase boundaries.  E1 uses them only at ~1 atm; it does
  NOT extrapolate a boiling point with pressure (Clausius-Clapeyron is a sourced-model gap E1 does not
  attempt), which is stated loudly rather than guessed.
* ``isolable = False``: the species cannot be stored or carried across ANY transition (ketene: generated
  and consumed in situ).  A route handing such an intermediate to a *later* step is ``DEGENERATE`` on this
  sourced fact alone.

Sources are named per record: melting/boiling/decomposition figures are CRC Handbook / NIST WebBook /
PubChem aggregate profiles; the non-isolable reactive-gas facts are CAMEO Chemicals (NOAA) and the NJ DOH
Right-to-Know fact sheets.  These are well-established physical constants, not calibrated coverage claims.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..conditions import Interval
from ..contracts import Digestible, EvidenceStatus

__all__ = [
    "STABILITY_SCHEMA",
    "StabilityRef",
    "StabilityTable",
    "SEED_STABILITY_REFS",
    "DEFAULT_STABILITY",
    "stability_for",
    "stability_for_named",
]

STABILITY_SCHEMA = "smartchem.data.stability/thresholds-v1"


@dataclass(frozen=True)
class StabilityRef(Digestible):
    """Sourced stability thresholds for one named compound (all temperatures in kelvin, at ~1 atm).

    ``formula`` is the composition key (formula-level, matching the decompiler's node identity);
    ``name`` pins the specific isomer.  Any of the three intervals may be ``None`` (that threshold is
    not tabulated for this compound), and ``isolable`` is the flat sourced fact of whether the species
    can be stored at all.  A record is a positive claim, so it is never ``UNSUPPORTED``.
    """

    formula: str
    name: str
    melting: Interval | None
    boiling: Interval | None
    decomposition_onset: Interval | None
    isolable: bool
    provenance: str
    dhvap_kj_per_mol: float | None = None
    status: EvidenceStatus = EvidenceStatus.EXPERIMENTAL

    def __post_init__(self) -> None:
        if not isinstance(self.formula, str) or not self.formula:
            raise ValueError("formula must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        for field_name in ("melting", "boiling", "decomposition_onset"):
            value = getattr(self, field_name)
            if value is not None and type(value) is not Interval:
                raise TypeError(f"{field_name} must be an Interval (kelvin) or None")
            if value is not None and value.unit != "K":
                raise ValueError(f"{field_name} must be in kelvin (unit 'K'), got {value.unit!r}")
        if type(self.isolable) is not bool:
            raise TypeError("isolable must be a bool")
        if self.dhvap_kj_per_mol is not None and (
            isinstance(self.dhvap_kj_per_mol, bool)
            or not isinstance(self.dhvap_kj_per_mol, (int, float))
            or self.dhvap_kj_per_mol <= 0
        ):
            raise ValueError("dhvap_kj_per_mol must be a positive number (kJ/mol) or None")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("a stored stability record must carry a non-empty provenance")
        if not isinstance(self.status, EvidenceStatus):
            raise TypeError("status must be an EvidenceStatus")
        if self.status is EvidenceStatus.UNSUPPORTED:
            raise ValueError(
                "a stored stability record is a positive claim and cannot be UNSUPPORTED; "
                "an unassessed species is simply absent from the table"
            )

    def survives_temperature(self, temperature: Interval) -> bool | None:
        """Does the species survive being held over ``temperature`` (K), on the sourced onset alone?

        Returns ``True`` if the whole exposed range is below the decomposition onset, ``False`` if any
        of it reaches the onset, and ``None`` if no decomposition onset is tabulated (unassessed -- the
        caller must render that as ``UNKNOWN``, never as survival).  A non-isolable species never
        survives a transition and is handled by the caller before this is consulted.
        """
        if self.decomposition_onset is None:
            return None
        # It decomposes once ANY of the exposed range reaches the onset's low bound.
        return temperature.hi < self.decomposition_onset.lo


@dataclass(frozen=True)
class StabilityTable(Digestible):
    """An immutable set of sourced stability records, resolvable by ``(formula, name)`` or by formula.

    The compiler holds a table, not the module-level dict, so a caller can EXTEND coverage for any
    chemical with :meth:`with_records` and pass the result in -- the universality lever.  Records are
    deduplicated by ``(formula, name)``; :meth:`with_records` overrides a seed record with a caller's
    when the keys collide (the caller's sourced data wins for their own compound).
    """

    records: tuple[StabilityRef, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(r) is not StabilityRef for r in self.records
        ):
            raise TypeError("records must be a tuple of StabilityRef values")

    def with_records(self, *records: StabilityRef) -> "StabilityTable":
        """A new table with ``records`` added (a later record wins on a ``(formula, name)`` collision)."""
        by_key: dict[tuple[str, str], StabilityRef] = {(r.formula, r.name): r for r in self.records}
        for r in records:
            if type(r) is not StabilityRef:
                raise TypeError("with_records takes StabilityRef values")
            by_key[(r.formula, r.name)] = r
        ordered = tuple(sorted(by_key.values(), key=lambda r: (r.formula, r.name)))
        return StabilityTable(ordered)

    def for_named(self, formula: str, name: str) -> StabilityRef | None:
        """The sourced thresholds for a specific named isomer, or ``None`` (a loud gap) on a miss."""
        for r in self.records:
            if r.formula == formula and r.name == name:
                return r
        return None

    def for_formula(self, formula: str) -> StabilityRef | None:
        """The thresholds for a formula IFF exactly one isomer is tabulated (else ``None``).

        Returns ``None`` on a miss AND when the formula is genuinely ambiguous (several isomers), because
        attaching one isomer's onset to a formula naming several would be a silently-wrong threshold --
        the isomer-ambiguity honesty the review layer already enforces.  Use :meth:`for_named` when the
        caller knows which compound it holds.
        """
        hits = [r for r in self.records if r.formula == formula]
        return hits[0] if len(hits) == 1 else None


def _k(lo: float, hi: float) -> Interval:
    return Interval(lo, hi, "K")


#: The SEED records -- sourced, litmus-focused (the paracetamol synthesis family plus common bench
#: solvents/reagents).  A convenience default, extended per call for any other chemical; NOT a whitelist.
SEED_STABILITY_REFS: tuple[StabilityRef, ...] = (
    StabilityRef(
        formula="H2O",
        name="water",
        melting=_k(273.15, 273.15),
        boiling=_k(373.12, 373.15),
        decomposition_onset=None,  # water does not thermally decompose in any bench regime
        isolable=True,
        provenance="CRC Handbook 97th ed.: water mp 0.00 C, bp 99.97-100.0 C at 1 atm; dHvap 40.66 kJ/mol",
        dhvap_kj_per_mol=40.66,
    ),
    StabilityRef(
        formula="C2H4O2",
        name="acetic acid",
        melting=_k(289.6, 289.9),
        boiling=_k(390.9, 391.2),
        decomposition_onset=None,
        isolable=True,
        provenance="CRC Handbook / PubChem CID 176: acetic acid mp 16.6 C, bp 117.9-118 C at 1 atm; "
        "dHvap 23.7 kJ/mol",
        dhvap_kj_per_mol=23.7,
    ),
    StabilityRef(
        formula="C4H6O3",
        name="acetic anhydride",
        melting=_k(199.9, 200.2),
        boiling=_k(412.7, 413.2),
        decomposition_onset=None,
        isolable=True,
        provenance=(
            "PubChem CID 7918 / CRC: acetic anhydride mp -73 C, bp 139.5-140 C at 1 atm; reacts "
            "violently with water (a reagent-handling hazard, tracked in smartchem.data.hazards, "
            "not a thermal-stability threshold)"
        ),
    ),
    StabilityRef(
        formula="C6H7NO",
        name="4-aminophenol",
        melting=_k(460.0, 463.0),
        boiling=None,  # decomposes on/around melting rather than boiling cleanly
        decomposition_onset=_k(557.0, 557.0),  # ~284 C reported decomposition
        isolable=True,
        provenance=(
            "PubChem CID 403 / NIST WebBook: 4-aminophenol mp 187-190 C (melts with decomposition), "
            "decomposition ~284 C; air-sensitive (darkens on oxidation)"
        ),
    ),
    StabilityRef(
        formula="C8H9NO2",
        name="paracetamol",
        melting=_k(441.0, 445.0),
        boiling=None,
        decomposition_onset=_k(523.0, 523.0),  # ~250 C onset of thermal decomposition
        isolable=True,
        provenance=(
            "PubChem CID 1983 / NIST: acetaminophen mp 168-172 C; thermal decomposition onset ~250 C "
            "(TGA literature) -- above melting it degrades rather than distilling"
        ),
    ),
    StabilityRef(
        formula="C2H2O",
        name="ketene",
        melting=_k(122.0, 122.0),
        boiling=_k(217.0, 217.0),
        decomposition_onset=None,
        isolable=False,  # the load-bearing fact: generated and consumed in situ, never stored
        provenance=(
            "NJ DOH RTK / CAMEO Chemicals: ketene bp -56 C; an acutely toxic reactive gas that "
            "dimerises to diketene and polymerises -- generated and consumed IN SITU, never isolated "
            "or stored. isolable=False is the sourced fact E1 turns on"
        ),
    ),
)

#: The default table the compiler consults when the caller supplies no extension.  Extend it, per call,
#: with :meth:`StabilityTable.with_records` for any chemical whose sourced thresholds you have.
DEFAULT_STABILITY = StabilityTable(SEED_STABILITY_REFS)


def stability_for_named(
    formula: str, name: str, table: StabilityTable = DEFAULT_STABILITY
) -> StabilityRef | None:
    """The sourced thresholds for a named isomer in ``table`` (default seed), or ``None`` on a miss."""
    return table.for_named(formula, name)


def stability_for(formula: str, table: StabilityTable = DEFAULT_STABILITY) -> StabilityRef | None:
    """The thresholds for a formula in ``table`` IFF exactly one isomer is tabulated, else ``None``."""
    return table.for_formula(formula)
