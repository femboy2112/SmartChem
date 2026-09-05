"""THERMO-UNC-01 organic widen (Lane C): the FROZEN, dated Burcat/ATcT seed for the organic bench species -- and the
committed record that the BOTH-sigma organic thermo gate is CONFIRMED CLOSED.

The gate finding (the primary item-2 result -- CONFIRMED, verified by a live fetch on the access date)
-------------------------------------------------------------------------------------------------------
The goal was a FETCHABLE source giving BOTH standard formation enthalpy (dfH) AND standard entropy (S) *each with a
stated uncertainty* for organic bench targets (methanol / ethanol / acetic acid), which is what an INFORMATIVE
sigma(dG) needs (sigma_dG^2 = sigma_dH^2 + T^2 sigma_dS^2; a missing sigma_dS leaves sigma(dG) UNKNOWN).  Four walls,
each verified this round -- the gate is closed, do not re-dig:

  1. ATcT (Active Thermochemical Tables, atct.anl.gov) HAS both uncertainties, but its per-species pages sit behind a
     Cloudflare *managed JS challenge* (curl returns a "Just a moment..." interstitial, not the data) -- unreachable
     by any headless fetch, and the DOI -> OSTI -> ANL bulk-download chain terminates at a publication landing page,
     not a flat file.
  2. NIST Chemistry WebBook gives organic S BARE -- a value with no stated +/-.
  3. Burcat & Ruscic's Third Millennium database (the one source that IS fetchable, below) carries dfH WITH an
     uncertainty (quoted from ATcT) but NEVER states an S uncertainty for any species -- asymmetric the opposite way
     to NIST.
  4. The NIST-JANAF "Ten Organic Molecules" paper DOES report both sigmas, but for ten OTHER species (bromoacetic
     acid, oxalic acid, ...), none of them our bench targets.

So sigma(dG) for these organics stays UNKNOWN and is NOT faked (section 10.4).  What IS achievable and delivered here:
the ENTHALPY half -- a real, sourced dfH uncertainty from ATcT -- plus a DERIVED entropy (see below), so the organics
enter the thermo table (dH/dG become computable for them) with sigma(dG) honestly UNKNOWN.

Source (single, dated, fetchable edition)
-----------------------------------------
A. Burcat & Ruscic, "Third Millennium Ideal Gas and Condensed Phase Thermochemical Database", the respecth.elte.hu
   mirror -- BURCAT.THR.txt, https://respecth.elte.hu/burcat/BURCAT.THR.txt (fetched 2026-09-04, HTTP 200, 2,315,627
   bytes).  ``dfh_kj``/``dfh_unc_kj`` are the ATcT value+uncertainty quoted VERBATIM in each species' comment block
   ({HF298=... +/- ... kJ REF=ATcT ...}); ``atct_ref`` records which ATcT determination (A/C).  The parsing hazard is
   real (each block lists several competing HF298 values -- a Chao/Zwolinski fit, a G3B3 calc, the ATcT value); the
   ATcT one is the deliberately-chosen sourced value, NOT "the first number".
B. The standard entropy ``s_j_per_k`` is DERIVED, not sourced with a +/- (there is no both-sigma source; wall 3): it
   is the NASA-7 polynomial standard entropy S(298.15 K) evaluated from the LOW-T coefficients of the SAME Burcat
   record (``nasa7_low``), the fit Burcat built WITH the hindered-internal-rotor corrections these molecules need (a
   naive rigid-rotor/harmonic S would be wrong for them).  It is cross-checked against an approximate NIST WebBook
   standard entropy (``s_crosscheck_nist``, a recalled literature value used ONLY as a GROSS sanity gate -- see the
   validate() note on what that gate does and does NOT catch).  There is NO entropy-uncertainty FIELD at all (the
   record simply cannot hold an S ±) -- the strongest possible form of the honest asymmetry the CH4 thermo entry
   carries (dfH ±, S none): the gate above is data-unreachable, so a derived S carries no stated uncertainty.

Honesty boundaries (recorded, not hidden)
-----------------------------------------
* This is the ENTHALPY-sigma widen only; it does NOT lift sigma(dG) for these organics (the entropy sigma is
  data-unreachable -- the gate above).  Deriving a sigma_S (from the Burcat spectroscopic constants + a hindered-rotor
  uncertainty model, or a reachable both-sigma source appearing) is the named next brick.
* Gas phase, 298.15 K, 1 bar; dfH in kJ/mol, S in J/(K.mol).
* Like ``thermo_codata_seed`` and ``usgs_commodity_seed``, the package cannot import from ``experiments/``; the
  load-bearing numbers are transcribed into ``smartchem/data/thermo.py`` and pinned to this seed by a test, so the
  two copies cannot drift.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

__all__ = [
    "BurcatAtctRef", "BURCAT_ATCT_REFS", "SOURCE", "SECOND_SOURCE", "ACCESS_DATE", "GATE_STATUS",
    "FROZEN_HASH", "R_J_PER_MOL_K", "nasa7_s298", "content_hash", "validate", "report",
]

SOURCE = (
    "Burcat & Ruscic, Third Millennium Ideal Gas and Condensed Phase Thermochemical Database "
    "(respecth.elte.hu mirror, BURCAT.THR.txt), fetched 2026-09-04; dfH from the ATcT value quoted in each record"
)
SECOND_SOURCE = "NIST Chemistry WebBook, SRD 69 (bare organic S, used only as a cross-check of the derived entropy)"
ACCESS_DATE = "2026-09-04"
#: The primary item-2 finding, recorded as data: a fetchable BOTH-sigma organic thermo source does NOT exist.
GATE_STATUS = "BOTH_SIGMA_ORGANIC_GATE_CONFIRMED_CLOSED"

#: CODATA molar gas constant (J/mol/K) -- the same constant the NASA-7 entropy is defined against.
R_J_PER_MOL_K = 8.314462618


@dataclass(frozen=True)
class BurcatAtctRef:
    """One organic bench species: an ATcT-sourced dfH (with uncertainty) and a Burcat-NASA-7-DERIVED S (no stated
    uncertainty), plus the NASA-7 low-T coefficients the S is derived from so the derivation is reproducible from the
    seed itself, and the NIST cross-check value that sanity-gates it."""

    name: str
    formula: str               # Hill-order formula string, matching smartchem.data.thermo
    phase: str                 # "gas" for all here
    smiles: str                # canonical structure witness
    dfh_kj: float              # ATcT standard enthalpy of formation, kJ/mol (quoted in the Burcat record)
    dfh_unc_kj: float          # its ATcT stated uncertainty (> 0; sourced)
    atct_ref: str              # which ATcT determination the value is from ("ATcT A" / "ATcT C")
    s_j_per_k: float           # DERIVED standard entropy S(298.15 K), J/(K.mol) -- from nasa7_low
    nasa7_low: tuple           # (a1..a7) NASA-7 low-T (200-1000 K) coefficients of the same Burcat record
    s_crosscheck_nist: float   # approximate NIST WebBook S, used ONLY as a < 1% sanity gate on the derivation

    def key(self) -> tuple[str, str]:
        return (self.formula, self.phase)

    def derived_s298(self) -> float:
        """S(298.15 K) recomputed from ``nasa7_low`` -- the reproducible derivation behind ``s_j_per_k``."""
        return nasa7_s298(self.nasa7_low)


def nasa7_s298(coeffs: tuple, temperature_k: float = 298.15) -> float:
    """Standard molar entropy S(T) from NASA-7 coefficients: S/R = a1 lnT + a2 T + a3 T^2/2 + a4 T^3/3 + a5 T^4/4 + a7."""
    a1, a2, a3, a4, a5, _a6, a7 = coeffs
    t = temperature_k
    return R_J_PER_MOL_K * (a1 * math.log(t) + a2 * t + a3 * t ** 2 / 2 + a4 * t ** 3 / 3 + a5 * t ** 4 / 4 + a7)


# The FROZEN organic seed. dfH+/- transcribed VERBATIM from the ATcT comment in each Burcat record; the NASA-7 low-T
# coefficients transcribed from the same record (lines 3-4 of its two-range block); S DERIVED from them (validated
# below).  Do NOT edit a number without re-fetching the dated source.
BURCAT_ATCT_REFS: tuple[BurcatAtctRef, ...] = (
    BurcatAtctRef(
        "methanol", "CH4O", "gas", "CO", -200.70, 0.17, "ATcT C", 240.65,
        (5.65851051e+00, -1.62983419e-02, 6.91938156e-05, -7.58372926e-08, 2.80427550e-11, -2.56119736e+04,
         -8.97330508e-01), 239.9,
    ),
    BurcatAtctRef(
        "ethanol", "C2H6O", "gas", "CCO", -234.56, 0.2, "ATcT A", 280.59,
        (4.8586957e+00, -3.7401726e-03, 6.9555378e-05, -8.8654796e-08, 3.5168835e-11, -2.9996132e+04,
         4.8018545e+00), 281.6,
    ),
    BurcatAtctRef(
        "acetic acid", "C2H4O2", "gas", "CC(=O)O", -432.216, 1.5, "ATcT A", 283.47,
        (2.78950201e+00, 9.99941719e-03, 3.42572245e-05, -5.09031329e-08, 2.06222185e-11, -5.34752488e+04,
         1.41053123e+01), 283.5,
    ),
)


def validate(rows: "tuple[BurcatAtctRef, ...]" = BURCAT_ATCT_REFS) -> None:
    """The NON-VACUOUS discipline for a sourced-dfH / derived-S seed:

    * dfH carries a REAL sourced uncertainty (> 0) -- these are non-reference organic species, so a hollow/zero dfH
      uncertainty is refused (the same THERMO-UNC-01 non-vacuity the CODATA seed enforces);
    * S is a real third-law entropy (> 0);
    * the S is genuinely DERIVED from the committed NASA-7 coefficients: the stored ``s_j_per_k`` must equal
      ``nasa7_s298(nasa7_low)`` to 0.02 J/K/mol -- so the seed cannot ship an S that is NOT reproducible from its own
      polynomial (the derivation is auditable, never a smuggled hand number).  This is the guard that catches the
      COMMON transcription slip: a wrong coefficient copied while the human-known ``s_j_per_k`` stays put no longer
      reproduces, and validate() refuses it; and
    * the derivation passes a GROSS sanity gate against the recalled NIST value: derived S within 1% of
      ``s_crosscheck_nist``.  Honest bound on this gate (red-team fold, reproduced): it catches order-of-magnitude /
      wrong-species errors, NOT a subtle single-digit coefficient slip -- a +5% error on a2..a5/a7 shifts S by <1% and
      passes.  So ``validate()`` is a sanity gate, NOT a proof of transcription: the real guarantee on the shipped
      numbers is the commit-time line-by-line audit against the source file plus the ``FROZEN_HASH`` (which guards
      against DRIFT from that audited state, not against an error made AT commit time).
    """
    seen: set = set()
    for r in rows:
        if r.key() in seen:
            raise ValueError(f"duplicate key {r.key()}; the seed must be single-valued per species")
        seen.add(r.key())
        for field, val in (("dfh_kj", r.dfh_kj), ("dfh_unc_kj", r.dfh_unc_kj), ("s_j_per_k", r.s_j_per_k)):
            if val != val or val in (float("inf"), float("-inf")):
                raise ValueError(f"{r.name}: {field} must be a finite number")
        if r.dfh_unc_kj <= 0:
            raise ValueError(
                f"{r.name}: a non-reference dfH is a sourced claim and MUST carry a real uncertainty (> 0); "
                f"a hollow/zero uncertainty is refused (THERMO-UNC-01 non-vacuity)"
            )
        if r.s_j_per_k <= 0:
            raise ValueError(f"{r.name}: standard entropy must be positive")
        if len(r.nasa7_low) != 7:
            raise ValueError(f"{r.name}: nasa7_low must be the 7 NASA-7 coefficients (a1..a7)")
        derived = r.derived_s298()
        if abs(derived - r.s_j_per_k) > 0.02:
            raise ValueError(
                f"{r.name}: stored S {r.s_j_per_k} is not reproducible from its NASA-7 coefficients "
                f"(recomputed {derived:.3f}); the derived entropy must match its own polynomial"
            )
        if abs(derived - r.s_crosscheck_nist) / r.s_crosscheck_nist > 0.01:
            raise ValueError(
                f"{r.name}: derived S {derived:.2f} disagrees with the NIST cross-check {r.s_crosscheck_nist} by "
                f">1% -- a GROSS error (wrong species / wrong coefficient set); a subtle single-digit slip can still "
                f"pass this coarse gate (see validate()'s docstring)"
            )


def content_hash(rows: "tuple[BurcatAtctRef, ...]" = BURCAT_ATCT_REFS) -> str:
    """A tamper-evident content hash: the sorted (key, dfH, dfH_unc, atct_ref, S, nasa7_low) rows."""
    canonical = sorted(
        [list(r.key()) + [r.dfh_kj, r.dfh_unc_kj, r.atct_ref, r.s_j_per_k, list(r.nasa7_low)] for r in rows]
    )
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


#: The frozen hash of the committed seed (regenerate DELIBERATELY, only after re-fetching, by running as __main__).
FROZEN_HASH = "12a65a9c161dcd1a30441ea833d0259921de579563b35c91075c8797c665c9a6"  # methanol/ethanol/acetic (fetched 2026-09-04)


def report() -> dict:
    validate()
    return {
        "source": SOURCE,
        "second_source": SECOND_SOURCE,
        "access_date": ACCESS_DATE,
        "gate_status": GATE_STATUS,
        "species": len(BURCAT_ATCT_REFS),
        "with_real_dfh_uncertainty": sum(1 for r in BURCAT_ATCT_REFS if r.dfh_unc_kj > 0),
        # the gate, computed (NOT a hardcoded 0 -- red-team fold): the record has NO s-uncertainty field, so this
        # getattr sum is structurally 0 and would only rise if someone ADDED a sourced S ± -- the strongest gate is
        # that BurcatAtctRef cannot even hold an S uncertainty (data-unreachable; wall 3).
        "with_stated_s_uncertainty": sum(
            1 for r in BURCAT_ATCT_REFS if getattr(r, "s_unc_j_per_k", None) is not None
        ),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    print("content_hash =", content_hash())
    print("(set FROZEN_HASH to this value to freeze)")
    for r in BURCAT_ATCT_REFS:
        print(f"  {r.name:12s} {r.formula:7s} ({r.phase}): dfH = {r.dfh_kj:+9.3f} +/- {r.dfh_unc_kj:.3f} kJ/mol "
              f"({r.atct_ref}); S = {r.s_j_per_k:.2f} J/K/mol [DERIVED, NASA-7 -> {r.derived_s298():.3f}, "
              f"NIST xcheck {r.s_crosscheck_nist}]")
