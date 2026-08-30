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
    # --- common small molecules (decomposition products / inventory) ------------------------
    HazardRef(
        formula="CO",
        name="carbon monoxide",
        ghs_codes=("H220", "H331", "H360D", "H372"),
        summary=(
            "extremely flammable gas; TOXIC IF INHALED -- binds haemoglobin as carboxyhaemoglobin, "
            "a chemical asphyxiant that is colourless and odourless; reproductive toxicant"
        ),
        reactivity=(
            "forms explosive mixtures with air (12.5-74%)",
            "forms metal carbonyls (Ni, Fe) under pressure in steel systems; some detonate on heating",
        ),
        exposure="OSHA PEL 50 ppm (8-h TWA); NIOSH REL 35 ppm / 200 ppm ceiling; IDLH 1200 ppm",
        regulatory="ECHA harmonised: Repr. 1A (H360D), STOT RE 1 (H372, cardiovascular)",
        provenance="PubChem GHS / ECHA harmonised (CID 281); NIOSH Pocket Guide; CAMEO (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="CO2",
        name="carbon dioxide",
        ghs_codes=("H280",),
        summary=(
            "not flammable; a SIMPLE ASPHYXIANT -- displaces oxygen, high concentrations cause rapid "
            "CNS depression and unconsciousness; solid/liquid cause cryogenic burns"
        ),
        reactivity=("asphyxiation hazard in confined/low spaces (denser than air)",),
        exposure=(
            "OSHA PEL 5000 ppm (8-h TWA); NIOSH REL 5000 ppm / 30000 ppm STEL "
            "[IDLH figure not corroborated across sources in verification -- omitted rather than guessed]"
        ),
        regulatory="",
        provenance="PubChem GHS (CID 280, ~82% notifier H280); NIOSH Pocket Guide; CAMEO Chemicals (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="CH4",
        name="methane",
        ghs_codes=("H220",),
        summary=(
            "extremely flammable gas; a simple asphyxiant that displaces oxygen; not otherwise toxic"
        ),
        reactivity=("forms explosive mixtures with air (5-15%); violent with strong oxidisers",),
        exposure="no specific PEL (simple asphyxiant); explosive limits 5-15%; IDLH 50000 ppm (LEL-based, not health-based)",
        regulatory="",
        provenance="PubChem GHS / ECHA harmonised (CID 297); NIOSH Pocket Guide; CAMEO (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="H3N",  # canonical Formula repr (alphabetical: H before N) -- NOT "NH3"
        name="ammonia",
        ghs_codes=("H221", "H280", "H314", "H331", "H400"),
        summary=(
            "flammable gas; TOXIC IF INHALED; corrosive -- severe skin/eye burns; very toxic to "
            "aquatic life"
        ),
        reactivity=(
            "reacts violently with strong acids and oxidisers",
            "forms explosive/shock-sensitive compounds with halogens, gold, silver, mercury",
        ),
        exposure="OSHA PEL 50 ppm (8-h TWA); NIOSH REL 25 ppm / 35 ppm STEL; IDLH 300 ppm",
        regulatory="",
        provenance="PubChem GHS / ECHA harmonised (CID 222); NIOSH Pocket Guide; CAMEO (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="H2O2",
        name="hydrogen peroxide",
        ghs_codes=("H271", "H302", "H314", "H332"),
        summary=(
            "STRONG OXIDISER (concentrated may cause fire/explosion); corrosive -- severe burns; "
            "harmful if swallowed/inhaled; decomposes to water + oxygen. This profile is for the "
            "CONCENTRATED grade (>=70%); severity is concentration-graded and much lower when dilute"
        ),
        reactivity=(
            "powerful oxidiser; decomposes exothermically, accelerated by heat, metals, catalysts and "
            "contamination (can rupture sealed containers)",
            "incompatible with organics, reductants, many metals and their salts",
        ),
        exposure="OSHA PEL 1 ppm (8-h TWA); NIOSH REL 1 ppm; IDLH 75 ppm",
        regulatory=(
            "ECHA CLP Annex VI concentration bands: Ox. Liq. 1 / H271 and Skin Corr. 1A / H314 apply "
            "at >=70%; Skin Corr. 1B at 50-70%; mere irritation (H315) at 35-50%; eye damage (H318) "
            "from ~8%. A minority H351 self-notification is not corroborated by IARC/NTP and is omitted"
        ),
        provenance="PubChem GHS / ECHA C&L (CID 784, H271 ~90%/H314 ~99.6% notifier); NIOSH Pocket Guide; CAMEO (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="CH4O",
        name="methanol",
        ghs_codes=("H225", "H301", "H311", "H331", "H370"),
        summary=(
            "highly flammable liquid and vapour; TOXIC by all routes (oral/dermal/inhalation); "
            "H370 -- damages organs: metabolised to formic acid, causing optic-nerve damage and "
            "blindness"
        ),
        reactivity=("flammable; incompatible with strong oxidisers",),
        exposure="OSHA PEL 200 ppm (8-h TWA); NIOSH REL 200 ppm / 250 ppm STEL [skin]; IDLH 6000 ppm",
        regulatory="ECHA harmonised: Acute Tox. 3 (oral/dermal/inhalation), STOT SE 1 (H370); [skin] = significant dermal absorption",
        provenance="PubChem GHS / ECHA harmonised (CID 887); NIOSH Pocket Guide; CAMEO (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="CH2O",
        name="formaldehyde",
        ghs_codes=("H301", "H311", "H331", "H314", "H317", "H341", "H350"),
        summary=(
            "TOXIC by all routes; corrosive -- severe burns; skin sensitiser; CARCINOGEN (IARC "
            "Group 1, ECHA Carc. 1B) and suspected mutagen"
        ),
        reactivity=(
            "polymerises to paraformaldehyde on standing/cooling",
            "incompatible with strong oxidisers, strong bases, and amines",
        ),
        exposure="OSHA PEL 0.75 ppm (8-h TWA) / 2 ppm STEL; NIOSH REL 0.016 ppm (carcinogen); IDLH 20 ppm",
        regulatory=(
            "carcinogen classification disagrees across sources, resolved toward the STRONGER call: "
            "IARC Group 1 (human carcinogen) and ECHA harmonised Carc. 1B / H350 (legally binding) -- "
            "even though a majority of individual self-notifiers under-classify to only H351 (Carc. 2); "
            "codes here follow the harmonised/IARC classification. Also Muta. 2 (H341)"
        ),
        provenance="PubChem GHS / ECHA harmonised Annex VI (CID 712); IARC Monograph 100F; NIOSH Pocket Guide",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="CH2O2",
        name="formic acid",
        ghs_codes=("H314", "H302", "H331"),
        summary=(
            "CORROSIVE -- severe skin/eye burns (the one near-universal call, ~99.7% of notifiers); "
            "harmful if swallowed and toxic if inhaled at concentration (minority-notified, ~18-21%). "
            "Combustible (flash point ~50-69 C) but below the H226 flammable-liquid threshold in most "
            "classifications, so H226 is not asserted here"
        ),
        reactivity=(
            "decomposes on heating/catalysis to CO + water (dehydration) or CO2 + H2 "
            "(dehydrogenation); the CO route is the hazard with hot conc. sulfuric acid",
            "corrodes active metals releasing hydrogen; exothermic with all bases",
            "incompatible with strong oxidisers, strong bases, and concentrated sulfuric acid",
        ),
        exposure="OSHA PEL 5 ppm (8-h TWA); NIOSH REL 5 ppm; IDLH 30 ppm",
        regulatory="",
        provenance="PubChem GHS / ECHA C&L (CID 284, H314 ~99.7% notifier); NIOSH Pocket Guide; CAMEO (NOAA)",
        status=EvidenceStatus.ESTABLISHED,
    ),
    HazardRef(
        formula="H2O",
        name="water",
        ghs_codes=(),  # deliberately empty: water carries no GHS classification
        summary=(
            "no significant hazard -- the reference benign substance. This is a positive ASSESSED "
            "record (assessed and benign), NOT an absence: a decomposition touching water reads "
            "documented, not the loud HAZARDS_UNASSESSED that an unknown species gets"
        ),
        reactivity=("violent with a few reactive species (alkali metals, acid anhydrides), by their reactivity not water's",),
        exposure="",
        regulatory="a ~0.5% minority self-notification (H315/H319/H335) exists and is uninterpreted (likely a mislabelled mixture or data artefact); not asserted here",
        provenance="assessed-benign at scale: PubChem CID 962 records 'does not meet GHS hazard criteria' for 99.5% (1866/1876) of reports; recorded so absence-of-record stays meaningful",
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
