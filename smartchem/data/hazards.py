"""Sourced, qualitative safety hazards for the decomposition review layer -- inform, never neuter.

The v1 review screen (:mod:`smartchem.decompiler_review`) knew only *energetics*: forming a molecule
from atoms is exothermic. That misses the hazards a working chemist most needs -- that ketene is
fatal if inhaled and polymerizes explosively, that 4-aminophenol is a regulated nephrotoxic
degradant, that acetic anhydride reacts violently with water. This module is the sourced, tiered
reference that supplies them, so the screen can *attach* real hazards rather than only compute a heat
of formation.

Doctrine (unchanged, and load-bearing)
--------------------------------------
* **Inform, never neuter.** These records are attached, never used to hide or refuse a
  decomposition. The chemist owns the safety decision; the tool's job is to give them the known
  facts to make it.
* **UNKNOWN is not safe.** An absent record means *unassessed*, never *cleared*. A lookup miss
  returns ``None``, which the caller must render as a loud gap, not a green light.
* **Isomer-specific.** Hazards belong to a *compound*, not a bare formula: the ``C6H7NO`` hazards
  here are 4-aminophenol's specifically. Each record names the compound it describes; the structure
  registry (:mod:`smartchem.structure`) is what licenses attaching them to a formula-level node.

Sources are named per record. GHS classes are the well-populated ECHA/PubChem aggregate profiles
(authoritative, though self-classification aggregates carry notifier variance); reactivity and
exposure limits are from CAMEO Chemicals (NOAA) and the NJ DOH Right-to-Know fact sheets
(OSHA/NIOSH/ACGIH). Where a specific figure rests on secondary sources it is flagged inline.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Digestible, EvidenceStatus

__all__ = [
    "HAZARDS_SCHEMA",
    "HazardRef",
    "HAZARD_REFS",
    "hazards_for",
]

HAZARDS_SCHEMA = "smartchem.data.hazards/qualitative-v1"


@dataclass(frozen=True)
class HazardRef(Digestible):
    """Well-established qualitative hazards for one named compound.

    ``formula`` is the composition key (formula-level, matching the decompiler's node identity);
    ``name`` pins the specific isomer these hazards describe. ``ghs_codes`` are the core, widely
    notified H-statements; ``reactivity`` and ``exposure`` carry the process hazards a heat-of-
    formation number cannot; ``regulatory`` carries tox/regulatory context.
    """

    formula: str
    name: str
    ghs_codes: tuple[str, ...]
    summary: str
    reactivity: tuple[str, ...]
    exposure: str
    regulatory: str
    provenance: str
    status: EvidenceStatus = EvidenceStatus.EXPERIMENTAL

    def __post_init__(self) -> None:
        if not isinstance(self.formula, str) or not self.formula:
            raise ValueError("formula must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if type(self.ghs_codes) is not tuple or any(
            not isinstance(c, str) or not c for c in self.ghs_codes
        ):
            raise TypeError("ghs_codes must be a tuple of non-empty strings")
        if type(self.reactivity) is not tuple:
            raise TypeError("reactivity must be a tuple of strings")
        if not isinstance(self.status, EvidenceStatus):
            raise TypeError("status must be an EvidenceStatus")
        if self.status is EvidenceStatus.UNSUPPORTED:
            raise ValueError(
                "a stored hazard record is a positive claim and cannot be UNSUPPORTED; "
                "absence of a record is how UNKNOWN is represented"
            )
        if not self.provenance:
            raise ValueError("every hazard record must name its source")


HAZARD_REFS: tuple[HazardRef, ...] = (
    HazardRef(
        formula="C8H9NO2",
        name="paracetamol",
        ghs_codes=("H302", "H315", "H319", "H412"),
        summary="harmful if swallowed; skin/eye irritant; hepatotoxic in overdose",
        reactivity=(),  # no oxidiser/water-reactive/pyrophoric/explosive flags in a 432-report aggregate
        exposure="",
        regulatory=(
            "overdose causes dose-dependent hepatotoxicity via the NAPQI metabolite (textbook "
            "toxicology); a minority of notifiers report H370/H372 (liver) and H341"
        ),
        provenance="PubChem GHS (ECHA C&L aggregate, CID 1983); hepatotoxicity is established clinical tox",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="C6H7NO",
        name="4-aminophenol",
        ghs_codes=("H302", "H332", "H341", "H400", "H410", "H317"),
        summary=(
            "harmful if swallowed/inhaled; suspected mutagen (Cat 2); very toxic to aquatic life; "
            "skin sensitiser; the REGULATED nephrotoxic hydrolytic degradant of paracetamol"
        ),
        reactivity=(),
        exposure="",
        regulatory=(
            "USP General Chapter <227> controls 4-aminophenol as the acetaminophen hydrolysis "
            "impurity, limit ~NMT 0.005% (50 ppm) in the drug substance [ppm figure: secondary "
            "sources, MEDIUM confidence; the control and its nephrotoxicity/teratogenicity rationale "
            "are HIGH]"
        ),
        provenance="PubChem GHS (ECHA harmonized block, CID 403); USP <227>",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="C2H4O2",
        name="acetic acid",
        ghs_codes=("H226", "H314"),
        summary="flammable liquid and vapour; causes severe skin burns and eye damage (corrosive)",
        reactivity=("corrosive at concentration", "incompatible with strong oxidisers and strong bases"),
        exposure="glacial acetic acid flash point ~39 C",
        regulatory="",
        provenance="PubChem GHS (ECHA harmonized block, CID 176, >99.9% notifier agreement)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="C4H6O3",
        name="acetic anhydride",
        ghs_codes=("H226", "H302", "H314", "H332"),
        summary=(
            "flammable; harmful if swallowed/inhaled; severe skin burns and eye damage (corrosive); "
            "REACTS VIOLENTLY WITH WATER to give acetic acid"
        ),
        reactivity=(
            "reacts violently with water (CAMEO); heightened by mineral acids (nitric, perchloric, "
            "sulfuric)",
            "dangerous with alcohols, glycerol, boric acid, and oxidisers",
        ),
        exposure="flash point ~121 F; explosive limits 2.9-10.3%",
        regulatory=(
            "US DEA List II precursor chemical [secondary-source convergence, MEDIUM confidence; "
            "not confirmed against the primary DEA regulation in sourcing]"
        ),
        provenance="PubChem GHS (CID 7918); CAMEO Chemicals (NOAA), chemical 2276",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="C2H2O",
        name="ketene",
        ghs_codes=("H220", "H330", "H335", "H315", "H318"),
        summary=(
            "extremely flammable gas; FATAL IF INHALED; a highly toxic reactive gas that cannot be "
            "stored -- generated and consumed in situ"
        ),
        reactivity=(
            "reacts violently with water to form acetic acid",
            "polymerises, sometimes explosively, on warming or acid/base contact",
            "forms explosive diacetyl peroxide with hydrogen peroxide",
        ),
        exposure="OSHA PEL 0.5 ppm (8-h TWA); NIOSH REL 0.5 ppm / 1.5 ppm STEL; IDLH 5 ppm",
        regulatory=(
            "NJ RTK health hazard 3/4; delayed pulmonary edema possible, medical observation "
            "advised 24-48 h post-exposure"
        ),
        provenance=(
            "PubChem GHS (CID 10038); NJ DOH Right-to-Know fact sheet (OSHA/NIOSH/ACGIH), Sept 2016; "
            "CAMEO Chemicals (NOAA), chemical 25037"
        ),
        status=EvidenceStatus.ESTABLISHED,
    ),
)


def _index() -> dict[str, HazardRef]:
    index: dict[str, HazardRef] = {}
    for ref in HAZARD_REFS:
        if ref.formula in index:
            raise ValueError(
                f"two hazard records share formula {ref.formula!r}; hazards are isomer-specific and "
                f"this formula-keyed table admits one named compound per formula (extend the key)"
            )
        index[ref.formula] = ref
    return index


_BY_FORMULA = _index()


def hazards_for(formula: str) -> HazardRef | None:
    """The hazard record for a composition, or ``None`` (UNKNOWN, which is NOT safe).

    ``formula`` is a canonical formula string as produced by ``repr`` of a decompiler ``Formula``
    (e.g. ``"C2H2O"``). A miss is a loud gap for the caller to surface, never a clearance.
    """
    return _BY_FORMULA.get(formula)
