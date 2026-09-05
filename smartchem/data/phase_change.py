"""Rung C -- the gas->condensed bridge: sourced sublimation/vaporization corrections.

The group-additivity estimator (:mod:`smartchem.data.thermo_groups`) yields IDEAL-GAS ΔfH°/S°.  A great many
bench targets are CONDENSED (a crystalline drug, a liquid reagent), and a gas value summed into a
condensed-phase reaction omits the phase-change terms -- the "phase trap" the feasibility engine flags.  This
module closes it where the phase-change data is SOURCED:

    ΔfH°(condensed) = ΔfH°(gas) − ΔsubH   (sublimation, solid);  − ΔvapH  (vaporization, liquid)
    S°(condensed)   = S°(gas)   − ΔsubS   (sublimation, solid);  − ΔvapS  (vaporization, liquid)

(ΔsubH/ΔsubS and ΔvapH/ΔvapS are the enthalpy/entropy DIFFERENCE gas−condensed, both positive.)

This is the LAST MILE of the paracetamol litmus.  The documented wall was paracetamol's missing standard
molar entropy S°(cr): only an entropy of *fusion* was ever measured.  Here it is DERIVED --
S°(cr) = S°(gas, group-additivity) − ΔsubS(paracetamol, sourced) -- so the acetylation finally has a
condensed-phase ΔG (graded PREDICTED-with-band, never UNKNOWN).  And the enthalpy leg is a genuine
THREE-way cross-validation: the Benson gas estimate (−311 kJ/mol) minus the sourced ΔsubH (~118 kJ/mol)
reconstructs paracetamol's independently-sourced crystal ΔfH° (−410.4, Picciochi 2010) to within the
combined band -- three unrelated sources (RMG group values, Chickos-Acree sublimation, Picciochi calorimetry)
agreeing on one number.

Provenance discipline: every ΔsubH/ΔsubS is FETCHED and independently cross-checked (Chickos & Acree
compilations / NIST), never recalled; injectable and additive, degrading to a loud absence (no correction ->
the value stays GAS, honestly phase-flagged) rather than a fabricated one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..contracts import Digestible

__all__ = [
    "PhaseTransition",
    "PhaseChangeRef",
    "PhaseChangeTable",
    "DEFAULT_PHASE_CHANGE",
    "to_condensed",
]


class PhaseTransition(str, Enum):
    """The condensed<->gas transition a record describes; its ``condensed_phase`` is the target standard state."""

    SUBLIMATION = "sublimation"    # crystalline solid <-> gas
    VAPORIZATION = "vaporization"  # liquid <-> gas

    @property
    def condensed_phase(self) -> str:
        return "solid" if self is PhaseTransition.SUBLIMATION else "liquid"


@dataclass(frozen=True)
class PhaseChangeRef(Digestible):
    """One compound's SOURCED phase-change: the enthalpy AND entropy DIFFERENCE gas−condensed (both > 0)."""

    formula: str
    name: str
    transition: PhaseTransition
    dh_kj_per_mol: float
    ds_j_per_mol_k: float
    provenance: str
    #: PHASE-CHANGE-SIGMA: the SOURCED uncertainty on ΔsubH/ΔvapH (kJ/mol) and ΔsubS/ΔvapS (J/mol/K) -- the source's
    #: stated ± where one exists, else a between-study DISPERSION band (e.g. a NIST WebBook "average of N values"
    #: spread; NOT necessarily a single-measurement 1σ, and the band's central value must be close to the stored value
    #: for it to be honestly attributable).  ``None`` is an HONEST absence (never a hollow 0).  Like
    #: :class:`~smartchem.data.thermo.ThermoRef`'s ± these are ``compare=False`` metadata (a ± is provenance, not
    #: identity), so adding one moves no digest and no golden.  ``resolve_thermo`` propagates a condensed-phase σ in
    #: quadrature PER LEG (ΔfH° from ΔH, S° from ΔS) and lifts the lower-bound caveat ONLY when BOTH legs are sourced;
    #: a ``None`` leg keeps that leg's correction σ-less, so the condensed σ there stays an honest LOWER BOUND.
    #:
    #: Honest scope (red-team folds): free sources reliably state ΔH ± but rarely ΔS ± (the named
    #: THERMO-PHASE-ENTROPY-SIGMA follow-on), so ΔS ± is usually ``None`` today and the caveat correctly stands.  And
    #: the sourced ΔH ± is typically MUCH smaller than the group-additivity gas band it quadratures with (ethanol:
    #: ±0.4 vs a ~9.8 kJ/mol band, ~25x), so the enthalpy-leg narrowing is small in absolute terms -- the mechanism's
    #: real payoff is the LIFT once a sourced ΔS ± also lands, not the enthalpy narrowing on today's seed.  The
    #: quadrature assumes the gas-band model error and the phase-change measurement error are INDEPENDENT; where a
    #: compound's Benson gas reference was itself back-computed from its own sublimation enthalpy the two could share
    #: provenance and the quadrature would slightly UNDER-estimate (never over) -- immaterial while σ_gas dominates.
    uncertainty_dh_kj_per_mol: "float | None" = field(default=None, compare=False)
    uncertainty_ds_j_per_mol_k: "float | None" = field(default=None, compare=False)

    def __post_init__(self) -> None:
        for f in ("formula", "name", "provenance"):
            v = getattr(self, f)
            if not isinstance(v, str) or not v:
                raise ValueError(f"{f} must be a non-empty string")
        if not isinstance(self.transition, PhaseTransition):
            raise TypeError("transition must be a PhaseTransition")
        for f in ("dh_kj_per_mol", "ds_j_per_mol_k"):
            v = getattr(self, f)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"{f} must be a real number")
        if self.dh_kj_per_mol < 0 or self.ds_j_per_mol_k < 0:
            raise ValueError("a gas−condensed enthalpy/entropy difference is >= 0 by definition")
        # a sourced phase-change ± is never a convention-zero (unlike a reference-state ΔfH°): > 0 or an honest None.
        for f in ("uncertainty_dh_kj_per_mol", "uncertainty_ds_j_per_mol_k"):
            v = getattr(self, f)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0):
                raise ValueError(f"{f} must be a real sourced ± (> 0) or None; a hollow/zero/negative ± is refused")


@dataclass(frozen=True)
class PhaseChangeTable(Digestible):
    """An immutable, injectable set of sourced phase-change records (mirrors :class:`~smartchem.data.thermo.ThermoTable`)."""

    records: tuple[PhaseChangeRef, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(type(r) is not PhaseChangeRef for r in self.records):
            raise TypeError("records must be a tuple of PhaseChangeRef values")

    def with_records(self, *records: PhaseChangeRef) -> "PhaseChangeTable":
        by_key: dict[tuple[str, str], PhaseChangeRef] = {(r.formula, r.name): r for r in self.records}
        for r in records:
            if type(r) is not PhaseChangeRef:
                raise TypeError("with_records takes PhaseChangeRef values")
            by_key[(r.formula, r.name)] = r
        return PhaseChangeTable(tuple(sorted(by_key.values(), key=lambda r: (r.formula, r.name))))

    def for_named(self, formula: str, name: str) -> PhaseChangeRef | None:
        for r in self.records:
            if r.formula == formula and r.name == name:
                return r
        return None

    def for_formula(self, formula: str) -> PhaseChangeRef | None:
        hits = [r for r in self.records if r.formula == formula]
        return hits[0] if len(hits) == 1 else None


_S = PhaseTransition.SUBLIMATION
_V = PhaseTransition.VAPORIZATION
_CA = "Chickos & Acree, Enthalpies of Sublimation (J. Phys. Chem. Ref. Data 31, 2002) / NIST; FETCHED + cross-checked"
_VAP = "NIST/CRC standard enthalpy & entropy of vaporization (298 K); FETCHED + cross-checked"

#: SOURCED phase-change data.  Sublimation targets a crystalline standard state; vaporization a liquid one.
#: Each ΔsubH/ΔsubS (or ΔvapH/ΔvapS) was independently verified (Source->Verify workflow, all CONFIRMED).
#: Paracetamol: ΔsubH 117.9 is the bedrock value; its ΔsubS (190) is lower-confidence (the literature
#: ΔsubH/ΔsubS/ΔGsub trio is mildly inconsistent) -- carried, but the estimate it feeds is banded accordingly.
_SUBLIMATION_REFS: tuple[PhaseChangeRef, ...] = (
    PhaseChangeRef("C8H9NO2", "paracetamol", _S, 117.9, 190.0, f"ΔsubH 117.9 kJ/mol, ΔsubS ~190 J/mol/K; {_CA}; ΔsubS lower-confidence"),
    PhaseChangeRef("C7H6O2", "benzoic acid", _S, 89.2, 184.0, f"ΔsubH 89.2 kJ/mol, ΔsubS ~184 J/mol/K; {_CA}; ΔsubS lower-confidence"),
    # naphthalene carries NO ΔsubH ± (red-team fold): NIST's ±5 belongs to its AVG central value 71, not the stored
    # 72.6 (Kruif 1980) -- attaching it would splice a band onto a value it is not centered on; and resolve_thermo has
    # no group-additivity gas estimate for the fused aromatic, so the ± would be dead metadata that never propagates.
    PhaseChangeRef("C10H8", "naphthalene", _S, 72.6, 166.0, f"ΔsubH 72.6 kJ/mol, ΔsubS 166 J/mol/K; {_CA}"),
    PhaseChangeRef("C14H10", "anthracene", _S, 100.4, 189.0, f"ΔsubH 100.4 (Cp-corrected extrapolation to 298 K), ΔsubS 189; {_CA}"),
    PhaseChangeRef("I2", "iodine", _S, 62.42, 144.55, f"ΔsubH 62.42 kJ/mol, ΔsubS 144.55 J/mol/K; {_CA}"),
)
_VAPORIZATION_REFS: tuple[PhaseChangeRef, ...] = (
    PhaseChangeRef("H2O", "water", _V, 44.0, 118.89, f"ΔvapH 44.0 kJ/mol, ΔvapS 118.89 J/mol/K; {_VAP}"),
    PhaseChangeRef("C2H6O", "ethanol", _V, 42.3, 120.70,
                   f"ΔvapH 42.3 ± 0.4 kJ/mol (NIST WebBook Δvap H°, average of 12/13 studies -- an inter-study band, "
                   f"not a single-measurement 1σ), ΔvapS 120.70 J/mol/K; {_VAP}",
                   uncertainty_dh_kj_per_mol=0.4),  # ΔvapH band sourced (NIST AVG, centered on 42.3); ΔvapS ± not reported -> None
    PhaseChangeRef("C6H6", "benzene", _V, 33.9, 96.0, f"ΔvapH 33.9 kJ/mol, ΔvapS 96.0 J/mol/K; {_VAP}"),
    PhaseChangeRef("C3H6O", "acetone", _V, 31.3, 95.1, f"ΔvapH 31.3 kJ/mol, ΔvapS 95.1 J/mol/K; {_VAP}"),
)

DEFAULT_PHASE_CHANGE = PhaseChangeTable(_SUBLIMATION_REFS + _VAPORIZATION_REFS)


def to_condensed(gas_dhf_kj: float, gas_s_j: float, ref: PhaseChangeRef) -> tuple[float, float, str]:
    """Correct a gas-phase (ΔfH°, S°) to its condensed standard state via a sourced phase-change record.

    Returns ``(dhf_condensed_kj, s_condensed_j, phase)``.  Subtracts the (positive) gas−condensed difference:
    the condensed phase is lower in both enthalpy and entropy than the gas.
    """
    return (
        round(gas_dhf_kj - ref.dh_kj_per_mol, 2),
        round(gas_s_j - ref.ds_j_per_mol_k, 2),
        ref.transition.condensed_phase,
    )
