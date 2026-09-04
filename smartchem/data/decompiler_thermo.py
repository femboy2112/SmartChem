"""Decompiler-support thermochemistry -- broad coverage with honest tiers, SEPARATE from the benchmark.

Why a separate table from :mod:`smartchem.data.reference`
--------------------------------------------------------
``reference.POLYATOMIC_REFS`` is the *oracle benchmark's* ground truth: a small, pristine, verified
set with a locked train/test split and a documented history of memory-recall poisoning (the ethanol
near-miss, the butane/propane scrape). Its rule is that a value is not usable until a second
independent source agrees. Dumping provisional decompiler-support species into it would corrupt the
MAE it exists to compute. So decompiler thermochemistry lives here, tier-labelled, and the benchmark
set is untouched. This module *reads* nothing from reference and writes nothing to it.

What the sourcing pass actually established (and did not)
--------------------------------------------------------
* **ketene** (C2H2O) and **acetic acid** (C2H4O2): real 0 K gas-phase formation enthalpies, two
  independent literature sources agreeing -> stored, ``ESTABLISHED``, usable in a 0 K balance.
* **paracetamol** (C8H9NO2): a single-source *298 K* gas value. Stored for a chemist to see, but at
  ``EXPERIMENTAL`` and tagged 298 K -- and the 0 K accessor filters it OUT, because mixing a 298 K
  value into the repo's 0 K balances is exactly the silent convention error reference.py warns
  against. Its edges therefore stay ENERGETICS_UNKNOWN, honestly.
* **4-aminophenol** (C6H7NO): two real sources that DISAGREE by 9 kJ/mol at the gas phase, and
  **acetic anhydride** (C4H6O3): only a liquid value exists. Neither yields a certifiable gas 0 K
  number, so neither is stored as usable -- both are recorded in :data:`THERMO_GAPS` with the reason,
  so the gap is documented, not silent (inform-never-neuter applied to data).

All values are gas-phase enthalpy of formation in kJ/mol. ``temperature_k`` is the convention the
value is on; only ``0`` is usable in the 0 K assembly balance the review layer computes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Digestible, EvidenceStatus

__all__ = [
    "DECOMPILER_THERMO_SCHEMA",
    "ThermoRef",
    "DECOMPILER_THERMO",
    "THERMO_GAPS",
    "records_for",
    "records_for_named",
    "zero_k_records",
]

DECOMPILER_THERMO_SCHEMA = "smartchem.data.decompiler_thermo/tiered-v2"  # v2: ThermoRef gains a typed uncertainty_kj


@dataclass(frozen=True)
class ThermoRef(Digestible):
    """One sourced gas-phase formation enthalpy, with its temperature convention and evidence tier."""

    formula: str
    name: str
    dfh_kj: float
    temperature_k: int          # 0 or 298; only 0 is usable in the 0 K assembly balance
    status: EvidenceStatus
    provenance: str
    second_source: str = ""     # the independent corroborating source, "" if single-source
    uncertainty_kj: float | None = None  # THERMO-UNC-01: the SOURCED +/- on dfh_kj (kJ/mol); None = not sourced

    def __post_init__(self) -> None:
        if not isinstance(self.formula, str) or not self.formula:
            raise ValueError("formula must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("name must be a non-empty string")
        if type(self.dfh_kj) not in (int, float):
            raise TypeError("dfh_kj must be a number (kJ/mol)")
        if self.temperature_k not in (0, 298):
            raise ValueError("temperature_k must be 0 or 298 (the two stored conventions)")
        if not isinstance(self.status, EvidenceStatus):
            raise TypeError("status must be an EvidenceStatus")
        if self.status is EvidenceStatus.UNSUPPORTED:
            raise ValueError(
                "a stored thermo value is a positive claim; an unsupported/disagreeing value belongs "
                "in THERMO_GAPS, not here"
            )
        if not self.provenance:
            raise ValueError("every thermo value must name its source")
        # ESTABLISHED asserts corroboration -- it must carry the second independent source.
        if self.status is EvidenceStatus.ESTABLISHED and not self.second_source:
            raise ValueError(
                "ESTABLISHED status claims two independent sources agree; name the second source"
            )
        # THERMO-UNC-01: a stored uncertainty is a SOURCED +/- (a positive kJ/mol magnitude); None means the +/-
        # was genuinely not sourced (honest absence, not a hollow value). A zero/negative "uncertainty" is a hollow
        # claim and is REFUSED -- so the field is non-vacuous: it carries a real magnitude or is explicitly absent,
        # never a fake 0 that would churn the digest while asserting a precision the source did not give.
        if self.uncertainty_kj is not None:
            if type(self.uncertainty_kj) not in (int, float):
                raise TypeError("uncertainty_kj must be a number (kJ/mol) or None")
            if self.uncertainty_kj <= 0:
                raise ValueError("a stored uncertainty_kj is a sourced +/- and must be > 0; use None for not-sourced")

    @property
    def usable_at_0k(self) -> bool:
        return self.temperature_k == 0


DECOMPILER_THERMO: tuple[ThermoRef, ...] = (
    ThermoRef(
        formula="C2H2O",
        name="ketene",
        dfh_kj=-44.51,
        temperature_k=0,
        status=EvidenceStatus.ESTABLISHED,
        provenance="CCCBDB experimental (ATcT / Ruscic et al. 2005), CAS 463-51-4; 0 K = -44.51 +- 1.60",
        second_source="NIST WebBook (Nuttall, Laufer et al. 1971), -48 +- 2 kJ/mol at 298 K (agrees)",
        uncertainty_kj=1.60,   # the +/- already cited in the 0 K provenance (ATcT / Ruscic et al. 2005)
    ),
    ThermoRef(
        formula="C2H4O2",
        name="acetic acid",
        dfh_kj=-418.10,
        temperature_k=0,
        status=EvidenceStatus.ESTABLISHED,
        provenance="CCCBDB / TRC 1994 (Frenkel et al.), CAS 64-19-7; 0 K = -418.10 (298 K = -432.30)",
        second_source="NIST WebBook average of 8 values, -433 +- 3 kJ/mol at 298 K (agrees to 0.7)",
    ),
    ThermoRef(
        formula="C8H9NO2",
        name="paracetamol",
        dfh_kj=-280.5,
        temperature_k=298,
        status=EvidenceStatus.EXPERIMENTAL,
        provenance=(
            "Picciochi, Diogo & Minas da Piedade, J. Therm. Anal. Calorim. 100(2):391 (2010), "
            "DOI 10.1007/s10973-009-0634-y; gas 298 K = -280.5 +- 1.9 (crystal -410.4 + sublimation)"
        ),
        second_source="",  # single source; no independent gas-phase replicate found -> EXPERIMENTAL
        uncertainty_kj=1.9,   # the +/- already cited in the 298 K provenance (Picciochi et al. 2010)
    ),
    # -- the C2H6O isomer pair: SAME composition, DIFFERENT 0 K value. Structure-resolved thermo
    # returns the exact per-isomer number where formula-level can only offer the [-217.1, -166.6]
    # interval (ISOMER_AMBIGUOUS). Values REUSED from the benchmark set (reference.POLYATOMIC_REFS,
    # which stores 0 K), not re-sourced -- so they inherit the benchmark's own validation.
    ThermoRef(
        formula="C2H6O",
        name="ethanol",
        dfh_kj=-217.1,
        temperature_k=0,
        status=EvidenceStatus.ESTABLISHED,
        provenance="reference.POLYATOMIC_REFS 'C2H5OH' (CCCBDB R22, 0 K), benchmark-validated",
        second_source="the benchmark's own second-source gate; CCCBDB R22 experimental 0 K",
    ),
    ThermoRef(
        formula="C2H6O",
        name="dimethyl ether",
        dfh_kj=-166.6,
        temperature_k=0,
        status=EvidenceStatus.ESTABLISHED,
        provenance="reference.POLYATOMIC_REFS 'CH3OCH3' (CCCBDB R22, 0 K), benchmark-validated",
        second_source="the benchmark's own second-source gate; CCCBDB R22 experimental 0 K",
    ),
)


#: Composition -> why no certifiable gas-phase value is stored. Documented, not silent: a chemist
#: sees that a value was sought and why it is UNKNOWN, rather than an empty absence.
THERMO_GAPS: dict[str, str] = {
    "C6H7NO": (
        "4-aminophenol: two real gas-phase sources DISAGREE by 9 kJ/mol (Sabbah & Gouali 1996 "
        "-90.5; Nunez, Barral, Largo & Pilcher 1986 -81.5), exceeding tolerance at the "
        "solid->gas sublimation step; no single value is certifiable -> UNKNOWN"
    ),
    "C4H6O3": (
        "acetic anhydride: only a liquid-phase value exists (-625.0 +- 3.4, Guthrie 1974 / Pedley "
        "1986, one primary experiment); no 298 K vaporisation enthalpy to derive the gas value -> "
        "gas UNKNOWN (refused rather than extrapolated)"
    ),
}


def records_for(formula: str) -> tuple[ThermoRef, ...]:
    """Every stored thermo record for a composition, ANY convention (for display, not for a balance)."""
    return tuple(r for r in DECOMPILER_THERMO if r.formula == formula)


def records_for_named(name: str) -> tuple[ThermoRef, ...]:
    """Every stored thermo record for a specific NAMED compound -- the isomer-resolved lookup.

    A structure resolution supplies the name (ethanol vs dimethyl ether), and this returns that
    isomer's records only, so a 0 K balance can use the EXACT value rather than the formula-level
    interval over both isomers.
    """
    return tuple(r for r in DECOMPILER_THERMO if r.name == name)


def zero_k_records(formula: str) -> tuple[ThermoRef, ...]:
    """Only the 0 K-convention records for a composition -- the ones usable in a 0 K assembly balance.

    A 298 K value (e.g. paracetamol) is deliberately excluded: mixing conventions in a 0 K balance is
    the silent error this module refuses to make, so such edges stay ENERGETICS_UNKNOWN.
    """
    return tuple(r for r in DECOMPILER_THERMO if r.formula == formula and r.usable_at_0k)
