"""THERMO-UNC-01 (Lane C): the CODATA Key Values seed -- a FROZEN, dated, cited reference dataset of standard
thermodynamic values WITH stated uncertainties, for the common small molecules a decompiler bottoms out at.

Why this exists
---------------
THERMO-UNC-01 was BLOCKED on "sourced CODATA/JANAF uncertainties (no fabrication; a hollow null churns the
ThermoRef digest)". A 2026-09-04 source hunt (fanned out per the Operator's go) established that the CODATA Key
Values for Thermodynamics carry REAL +/- uncertainties on both standard formation enthalpy and standard entropy for
exactly this set of species, and that they are independently cross-verifiable for free via the NIST Chemistry
WebBook (which reproduces the identical figures tagged "CODATA Review value"). So the block is lifted for this
closed reference set: the values below are transcribed from that source and cross-checked, DATED and SOURCED per
standard section 10.4, never fabricated.

Source (single, dated edition)
------------------------------
CODATA Key Values for Thermodynamics -- J.D. Cox, D.D. Wagman & V.A. Medvedev, Hemisphere Publishing Corp., New
York, 1989 (the NIST Chemistry WebBook, SRD 69, reproduces the same values tagged "CODATA Review value, Cox,
Wagman, et al., 1984" -- the recommendation year). Cross-verified against the free NIST WebBook
(https://webbook.nist.gov/) on the access date below. Standard state 298.15 K, 1 bar; dfH in kJ/mol, S in
J/(K.mol).

Honesty boundaries (recorded, not hidden)
-----------------------------------------
* CH4 is NOT a CODATA key species -- it is absent from this set and is NOT invented here. Widening to CH4 (or any
  non-key species) requires ATcT (version-pinned) or NIST-JANAF, a named follow-on -- do not add a row without a
  transcribed, dated source.
* The reference-state elements (O2, H2, N2, C-graphite) have dfH = 0 EXACTLY by convention -- an exact zero with
  uncertainty 0 is LEGITIMATE there (it is a definition, not a hollow value), and their S still carries a real +/-.
  The validator distinguishes this convention-zero from a hollow/absent uncertainty on a NON-reference value.
* KEYING: the CODATA key set is a closed set of UNAMBIGUOUS single-isomer reference species (no two share a
  formula), so the (formula, phase) key below cannot suffer the same-formula-isomer borrow the standing lesson
  warns of. A structure-keyed CONSUMER must nonetheless key on canonical structure identity, not formula (that
  lesson holds in general); the SMILES is stored per molecular row so a consumer can compute that canonical key.
  Graphite and the H atom have no molecular SMILES (an allotrope / a bare atom) -- their key is formula+phase.

This is a committed, frozen reference dataset (like the family-stratified holdout benchmark), NOT wired into the
compiler's thermo consumers here -- wiring the +/- into a ThermoRef.uncertainty field across the three thermo
modules (data/decompiler_thermo, data/thermo, data/thermo_groups) is the named next brick. This file is the
sourced DATA the block was waiting on, with a self-check that refuses a hollow entry.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

__all__ = ["CodataRef", "CODATA_KEY_VALUES", "SOURCE", "ACCESS_DATE", "FROZEN_HASH", "content_hash", "validate"]

SOURCE = "CODATA Key Values for Thermodynamics (Cox, Wagman & Medvedev, Hemisphere Publishing, 1989)"
SECOND_SOURCE = "NIST Chemistry WebBook, SRD 69 (reproduces the CODATA Review values), https://webbook.nist.gov/"
ACCESS_DATE = "2026-09-04"


@dataclass(frozen=True)
class CodataRef:
    """One CODATA key value: standard formation enthalpy and standard entropy at 298.15 K, each with its
    uncertainty, plus whether the species is a dfH reference state (element in its standard state)."""

    name: str
    formula: str
    phase: str                 # "gas" / "liquid" / "solid"
    smiles: str                # canonical structure witness for molecular species; "" for an allotrope / bare atom
    dfh_kj: float              # standard enthalpy of formation, kJ/mol
    dfh_unc_kj: float          # its stated uncertainty (0 EXACTLY iff is_reference_state)
    s_j_per_k: float           # standard entropy, J/(K.mol)
    s_unc_j_per_k: float       # its stated uncertainty (> 0 for every species, elements included)
    is_reference_state: bool   # an element in its standard state: dfH = 0 by convention

    def key(self) -> tuple[str, str]:
        """The record key. UNAMBIGUOUS for this closed single-isomer set; a structure-keyed consumer computes the
        canonical identity from `smiles` (see the module docstring's KEYING note)."""
        return (self.formula, self.phase)


# The FROZEN CODATA key values, transcribed VERBATIM from the 1989 recommendation and cross-checked against the
# free NIST WebBook (2026-09-04). Do NOT edit a number without re-transcribing from the dated source.
CODATA_KEY_VALUES: tuple[CodataRef, ...] = (
    CodataRef("water", "H2O", "liquid", "O", -285.830, 0.040, 69.95, 0.03, False),
    CodataRef("water", "H2O", "gas", "O", -241.826, 0.040, 188.835, 0.010, False),
    CodataRef("carbon monoxide", "CO", "gas", "[C-]#[O+]", -110.53, 0.17, 197.660, 0.004, False),
    CodataRef("carbon dioxide", "CO2", "gas", "O=C=O", -393.51, 0.13, 213.785, 0.010, False),
    CodataRef("ammonia", "NH3", "gas", "N", -45.94, 0.35, 192.77, 0.05, False),
    CodataRef("dioxygen", "O2", "gas", "O=O", 0.0, 0.0, 205.152, 0.005, True),
    CodataRef("dihydrogen", "H2", "gas", "[H][H]", 0.0, 0.0, 130.680, 0.003, True),
    CodataRef("dinitrogen", "N2", "gas", "N#N", 0.0, 0.0, 191.609, 0.004, True),
    CodataRef("carbon (graphite)", "C", "solid", "", 0.0, 0.0, 5.74, 0.10, True),
    # NOTE: atomic hydrogen H(g) is a CODATA key species (dfH = 217.998 +/- 0.006 kJ/mol) but the source hunt did
    # NOT transcribe its S, so it is DELIBERATELY omitted rather than shipped with an unsourced entropy -- add it
    # only with a transcribed S from the dated source (no-fabrication discipline).
)


def validate(rows: "tuple[CodataRef, ...]" = CODATA_KEY_VALUES) -> None:
    """The NON-VACUOUS uncertainty discipline (the source-hunt adjudicator's condition): a sourced value must carry
    a REAL +/- or be an exact reference-state convention-zero -- a hollow/absent uncertainty on a non-reference
    value is REFUSED, and the guard fires on such a record (not merely on an empty set).  Also refuses duplicate
    keys and non-finite numbers."""
    seen: set = set()
    for r in rows:
        if r.key() in seen:
            raise ValueError(f"duplicate CODATA key {r.key()}; the reference set must be single-valued per species")
        seen.add(r.key())
        for field, val in (("dfh_kj", r.dfh_kj), ("dfh_unc_kj", r.dfh_unc_kj),
                           ("s_j_per_k", r.s_j_per_k), ("s_unc_j_per_k", r.s_unc_j_per_k)):
            if val != val or val in (float("inf"), float("-inf")):
                raise ValueError(f"{r.name}: {field} must be a finite number")
        # S is a third-law entropy: strictly positive, and its uncertainty is REAL for every species (elements too).
        if r.s_j_per_k <= 0 or r.s_unc_j_per_k <= 0:
            raise ValueError(f"{r.name}: standard entropy and its uncertainty must be positive (a real +/-, never hollow)")
        if r.is_reference_state:
            # an element in its standard state: dfH == 0 EXACTLY by convention, uncertainty 0 -- legitimate, NOT hollow.
            if r.dfh_kj != 0.0 or r.dfh_unc_kj != 0.0:
                raise ValueError(f"{r.name}: a reference state has dfH = 0 +/- 0 by convention")
        else:
            # a NON-reference value is a positive claim: it MUST carry a real (positive) uncertainty -- the guard
            # that fires on the hollow-null THERMO-UNC-01 was blocked on. A dfH exactly 0 with unc 0 here would be
            # a hollow value masquerading as a reference state, and is refused.
            if r.dfh_unc_kj <= 0:
                raise ValueError(
                    f"{r.name}: a non-reference dfH is a sourced claim and MUST carry a real uncertainty (> 0); "
                    f"a hollow/zero uncertainty is refused (THERMO-UNC-01 non-vacuity)"
                )


def content_hash(rows: "tuple[CodataRef, ...]" = CODATA_KEY_VALUES) -> str:
    """A tamper-evident content hash of the frozen set -- the sorted (key, dfH, dfH_unc, S, S_unc, ref) rows."""
    canonical = sorted(
        [list(r.key()) + [r.dfh_kj, r.dfh_unc_kj, r.s_j_per_k, r.s_unc_j_per_k, r.is_reference_state]
         for r in rows]
    )
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


#: The frozen hash of the committed CODATA seed (regenerate DELIBERATELY, only after re-transcribing from the dated
#: source, by running this module as __main__).
FROZEN_HASH = "9edc41d176f7aff6462976268e6cfd941f4618a21c2fc37fac69c50f32c833aa"


def report() -> dict:
    validate()
    return {
        "source": SOURCE,
        "second_source": SECOND_SOURCE,
        "access_date": ACCESS_DATE,
        "species": len(CODATA_KEY_VALUES),
        "reference_states": sum(1 for r in CODATA_KEY_VALUES if r.is_reference_state),
        "with_real_dfh_uncertainty": sum(1 for r in CODATA_KEY_VALUES if not r.is_reference_state and r.dfh_unc_kj > 0),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    print("content_hash =", content_hash())
    print("(set FROZEN_HASH to this value to freeze)")
    for r in CODATA_KEY_VALUES:
        ref = " [reference state: dfH=0 by convention]" if r.is_reference_state else ""
        print(f"  {r.name:20s} {r.formula:4s} ({r.phase:6s}): dfH = {r.dfh_kj:+9.3f} +/- {r.dfh_unc_kj:.3f} kJ/mol; "
              f"S = {r.s_j_per_k:8.3f} +/- {r.s_unc_j_per_k:.3f} J/K/mol{ref}")
