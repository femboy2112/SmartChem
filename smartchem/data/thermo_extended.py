"""M3 -- thermochemistry breadth: a broader SOURCED 298 K standard-state ΔfH°/S° set for M1/M2.

M1 (ΔG feasibility) and M2 (equilibrium K) are universal ENGINES; their reach is the thermo data they are
handed.  The 8-species seed in :mod:`smartchem.data.thermo` is litmus-focused (small molecules that calibrate
the engines).  This module is the *coverage* layer: a broader set of common organics whose 298 K standard-state
formation enthalpy AND standard molar entropy are both cleanly sourced, so ΔG/K reach real bench targets --
every organic here immediately unlocks its **combustion** (CO2 / H2O / O2 are already seeded).  Not a new
capability: the same established Hess+Gibbs / van't Hoff models, on more sourced inputs.

The discipline (inherited from :mod:`smartchem.data.decompiler_thermo`)
----------------------------------------------------------------------
This repo has a documented history of *memory-recall poisoning* -- a plausible-looking thermo number recalled
from training rather than sourced, later found wrong (the ethanol near-miss, the butane/propane scrape).  So
every value here was VERIFIED against a U.S.-government standard-reference compilation -- the NIST Chemistry
WebBook for all but one, and (for HNO3, which the WebBook does not surface a condensed-phase value for) its
NBS-1982 predecessor tables via secondary thermodynamic appendices -- and carries the specific author/year of
the measurement it came from (see each record's provenance for exactly which source); never a recalled number.
Two things are refused, loudly, exactly as the seed refuses them:

* **No entropy, no record.** ΔG = ΔH - TΔS needs S°.  A compound whose ΔfH° is sourced but whose S° is NOT
  cleanly sourced does not get a fabricated S° -- it gets an entry in :data:`EXTENDED_THERMO_GAPS` naming what
  was found and what is missing.  Paracetamol is exactly this case (see the litmus note below).
* **Phase consistency.** Every value is the 298.15 K, 1 bar standard-state value in the phase named; mixing a
  gas ΔfH° into a condensed-phase balance is the silent convention error the repo warns against.

The paracetamol litmus, honestly
--------------------------------
The north-star step is ``4-aminophenol + acetic anhydride -> paracetamol + acetic acid``.  Its ΔG is still
``UNKNOWN`` after M3 -- and the reason is now *precise and sourced*, not a blanket gap:
* **acetic acid** (l): fully sourced here -> usable.
* **paracetamol** (cr): ΔfH°(cr) = -410.4 kJ/mol is real and sourced (Picciochi 2010, the same DOI the
  decompiler-thermo pass cites), but no standard molar entropy S°(cr, 298 K) is cleanly sourced (only an
  entropy of *fusion*) -> a documented gap, not a fabricated S°.
* **4-aminophenol** (s) and **acetic anhydride** (l): entropy/consistent-phase data not sourced here.
So M3 sources what genuinely exists (paracetamol's formation enthalpy skeleton) and refuses what does not
(its entropy), and the step stays honestly ``UNKNOWN`` -- the correct behaviour, loud about exactly which
species and which quantity blocks it.

R5-lite: the aromatic-intermediate skeleton toward the litmus (sourced, not fabricated)
--------------------------------------------------------------------------------------
The industrial paracetamol route descends through aromatic intermediates -- ``phenol -> (nitration) ->
4-nitrophenol -> (reduction) -> 4-aminophenol -> (acetylation) -> paracetamol`` -- and the analogous
``benzene -> nitrobenzene -> aniline`` reduction skeleton.  R5-lite sources the members of that skeleton
whose 298 K standard-state ΔfH° AND S° both genuinely exist as a same-phase pair on the NIST WebBook --
**phenol, aniline, nitrobenzene, toluene** -- so the rungs among them LIFT from L2's ``HYPOTHESIZED`` floor
to ``DERIVED`` (a real ΔG at the 298.15 K reference).  Sourcing **nitric acid** (HNO3, pure-liquid NBS-1982
pair) now extends the DERIVED reach ONE real edge FORWARD: ``benzene + HNO3 -> nitrobenzene + H2O`` grades
DERIVED and strongly favorable -- the aromatic nitration-front, the precursor skeleton of the route.
Sourcing **cumene** (isopropylbenzene, liquid pair from the raw NIST WebBook page) lifts a second real
precursor rung: ``cumene + O2 -> phenol + acetone`` (the industrial cumene process that MAKES phenol, both
products already sourced) grades DERIVED.  **Acetanilide** was fetched the same way and DELIBERATELY refused
-- its ΔfH°(cr) is real but the page carries no S°(cr), so the amidation analog of the drug-forming step
stays an honest gap (see :data:`EXTENDED_THERMO_GAPS`), never a fabricated entropy.

But do not mistake that for reaching the drug.  The TERMINAL literal descent to paracetamol does NOT lift,
and the wall is permanent and named: ``phenol -> 4-nitrophenol -> 4-aminophenol`` (nitration then reduction)
stays ``HYPOTHESIZED`` -- walled by **4-nitrophenol**'s missing S° in every phase and **4-aminophenol**'s
disagreeing ΔfH° sources -- and the final ``4-aminophenol + acetic anhydride -> paracetamol`` (acetylation)
stays ``KNOWN``-but-thermo-``UNKNOWN``, walled by **paracetamol**'s missing S°(cr).  The nitration FRONT is
derivable; the drug's own edges are not.  Every value here was fetched from a U.S.-gov standard-reference
source -- the raw NIST WebBook page, or (for HNO3) the NBS-1982 tables via a secondary thermodynamic appendix
-- and phase-checked; none is recalled.
"""
from __future__ import annotations

from .thermo import DEFAULT_THERMO, ThermoRef, ThermoTable

__all__ = [
    "EXTENDED_THERMO_REFS",
    "EXTENDED_THERMO_GAPS",
    "extended_thermo",
]

_NIST = "NIST Chemistry WebBook (webbook.nist.gov), U.S.-gov public domain"

#: Broader sourced 298.15 K, 1 bar standard-state records -- each VERIFIED against the NIST WebBook (HNO3
#: via its NBS-1982 predecessor tables; see its provenance), each
#: naming the specific measurement (author, year) its ΔfH° and S° came from.  Every one unlocks its combustion
#: (CO2/H2O/O2 seeded).  Injectable and additive to the seed; NOT a whitelist and NOT re-sourced from memory.
EXTENDED_THERMO_REFS: tuple[ThermoRef, ...] = (
    ThermoRef(
        "CH4O", "methanol", -239.5, 127.19, "liquid",
        f"ΔfH° -239.5±0.2 (Chao & Rossini 1965); S° 127.19 (Carlson & Westrum 1971); {_NIST}",
    ),
    ThermoRef(
        "C2H6O", "ethanol", -277.0, 159.86, "liquid",
        f"ΔfH° NIST avg of 6 exptl -276±2 (CRC/CODATA -277.0, agrees); S° 159.86 "
        f"(Haida & Suga 1977, adiabatic calorimetry); {_NIST}",
    ),
    ThermoRef(
        "CH2O2", "formic acid", -425.09, 131.84, "liquid",
        f"ΔfH° -425.09 (Guthrie 1974); S° 131.84 (Stout & Fisher 1941); {_NIST}",
    ),
    ThermoRef(
        "C2H4O2", "acetic acid", -483.52, 158.0, "liquid",
        f"ΔfH° -483.52±0.36 (Steele, Chirico et al. 1997, combustion cal.); S° 158.0 "
        f"(Martin & Andon 1982); {_NIST}",
    ),
    ThermoRef(
        "C3H6O", "acetone", -249.4, 200.4, "liquid",
        f"ΔfH° -249.4±0.63 (Wiberg, Crocker et al. 1991); S° 200.4 (Kelley 1929); {_NIST}",
    ),
    ThermoRef(
        "C6H6", "benzene", 49.0, 173.26, "liquid",
        f"ΔfH° +49.0±0.9 (Roux, Temprado et al. 2008); S° 173.26 (Oliver, Eaton et al. 1948); {_NIST}",
    ),
    # -- R5-lite: the aromatic-intermediate skeleton toward the paracetamol litmus (same-phase ΔfH°+S°
    #    pairs fetched from the raw NIST WebBook page and phase-checked; NOT recalled) ------------------
    ThermoRef(
        "C6H6O", "phenol", -165.1, 144.01, "solid",
        f"ΔfH° -165.1±1.3 (Andon, Biddiscombe et al. 1960, combustion cal.); S° 144.01 "
        f"(Andon, Counsell et al. 1963); {_NIST}",
    ),
    ThermoRef(
        "C6H7N", "aniline", 31.3, 191.30, "liquid",
        f"ΔfH° 31.3±0.84 (Hatton, Hildenbrand et al. 1962, combustion cal.); S° 191.30 "
        f"(Hatton, Hildenbrand et al. 1962, same paper); {_NIST}",
    ),
    ThermoRef(
        "C6H5NO2", "nitrobenzene", 12.5, 224.3, "liquid",
        f"ΔfH° 12.5±0.54 (Lebedeva, Katin et al. 1971, reanalyzed by Pedley, Naylor et al. 1986); "
        f"S° 224.3 (Parks, Todd et al. 1936); {_NIST}",
    ),
    ThermoRef(
        "C7H8", "toluene", 12.0, 220.96, "liquid",
        f"ΔfH° 12.0±1.1 (Roux, Temprado et al. 2008, review); S° 220.96 "
        f"(Scott, Guthrie et al. 1962); {_NIST}",
    ),
    ThermoRef(
        "HNO3", "nitric acid", -174.1, 155.6, "liquid",
        "ΔfH°(l) -174.1 and S°(l) 155.6 (298.15 K, pure liquid, standard state) from the NBS Tables "
        "(Wagman et al., J. Phys. Chem. Ref. Data 11 Suppl.2, 1982) via the OpenStax/LibreTexts "
        "thermodynamic appendix; crosschecked to the digit against Penn State Chem 310 / Inorganic "
        "Chemistry Wikibook. Pure-LIQUID row (distinct from the aqueous -207.4/146.4 and gas -134.3 "
        "values — the correct phase); NBS-1982 lineage, not a CODATA Key Values species.",
    ),
    ThermoRef(
        "C9H12", "cumene", -41.2, 277.57, "liquid",
        f"ΔfH°(l) -41.2 (Prosen, Gilmont et al. 1945, combustion cal.); S°(l) 277.57 "
        f"(Kishimoto, Suga et al. 1973, calorimetry); {_NIST}. FETCHED from the raw cbook.cgi Mask=2 page "
        f"(ID C98828) this pass and phase-checked (liquid ΔfH° paired with liquid S°); lifts "
        f"'cumene + O2 -> phenol + acetone' (the cumene process that industrially MAKES phenol) to DERIVED, "
        f"both products already sourced.",
    ),
)


#: Composition -> why no usable 298 K standard-state record is stored (documented, never a silent absence).
#: A chemist sees that a value was sought and exactly what is missing, rather than an empty gap.
EXTENDED_THERMO_GAPS: dict[str, str] = {
    "C8H9NO2": (
        "paracetamol: ΔfH°(cr, 298 K) = -410.4±1.3 kJ/mol IS sourced (Picciochi, Diogo & Minas da Piedade, "
        "J. Therm. Anal. Calorim. 2010, DOI 10.1007/s10973-009-0634-y), but no standard molar entropy "
        "S°(cr, 298 K) is cleanly sourced (only an entropy of fusion, 59.8 J/K/mol) -> ΔG cannot be formed "
        "without fabricating S°; refused. The acetylation step therefore stays UNKNOWN on the entropy gap"
    ),
    "C6H7NO": (
        "4-aminophenol: two gas-phase ΔfH° sources disagree by 9 kJ/mol (per the decompiler-thermo pass), "
        "and no consistent-phase 298 K ΔfH°+S° pair is sourced here -> UNKNOWN, not extrapolated"
    ),
    "C4H6O3": (
        "acetic anhydride: a liquid ΔfH° exists (~-624.4 kJ/mol, Guthrie 1974 / Pedley 1986) but the only "
        "sourced standard molar entropy is GAS-phase (S°gas 389.95 J/mol/K, Stull 1969) -- the WRONG phase "
        "to pair with the liquid ΔfH°. No same-phase 298 K liquid ΔfH°+S° pair exists here, so mixing them "
        "would be the silent phase-convention error the repo warns against -> stays UNKNOWN until a liquid "
        "S° is sourced"
    ),
    "C6H5NO3": (
        "4-nitrophenol: ΔfH° IS sourced (solid -207.1±1.1, gas -114.7±1.2 kJ/mol, Sabbah & Gouali 1994) "
        "but NO standard molar entropy S°(298 K) exists in any phase on the NIST WebBook (only a 283 K Cp "
        "point, Campbell & Campbell 1941) -> ΔG cannot be formed without fabricating S°; refused. A fourth "
        "instance of the same 'no entropy, no record' gap as paracetamol / 4-aminophenol / acetic anhydride"
    ),
    "C8H9NO": (
        "acetanilide (N-phenylacetamide): ΔfH°(cr) IS sourced (-209.5±1.5 Sato-Toshima, Kamagughi et al. "
        "1983; -209.4±1.0 Johnson 1975, both combustion cal.), FETCHED from the raw NIST WebBook cbook.cgi "
        "Mask=2 page (ID C103844) this pass, but that page carries NO standard molar entropy S°(cr) row -> "
        "ΔG cannot be formed without fabricating S°; refused. The N-acetylation analog "
        "'aniline + acetic acid -> acetanilide + water' -- the SAME amidation class as the paracetamol "
        "acetylation -- therefore stays HYPOTHESIZED on the entropy gap. A fifth instance of the same "
        "'no entropy, no record' gap; the ΔfH° is real, the entropy is genuinely absent, not recalled"
    ),
}


def extended_thermo(base: ThermoTable = DEFAULT_THERMO) -> ThermoTable:
    """The seed extended with the broader sourced 298 K set -- the download-and-go thermo table for M1/M2.

    Additive to ``base`` (the litmus seed by default): pass a caller's own table to layer these on top of it.
    A composition in :data:`EXTENDED_THERMO_GAPS` deliberately gets NO record (its ΔG stays a loud UNKNOWN).
    """
    return base.with_records(*EXTENDED_THERMO_REFS)
