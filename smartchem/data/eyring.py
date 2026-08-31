"""Sourced transition-state (Eyring) activation parameters -- the inputs the L1 Eyring provider reproduces
``k`` from.  The SECOND, INDEPENDENT rate provider, sibling to the Arrhenius ``(Ea, A)`` table.

Where :mod:`smartchem.data.kinetics` sources the Arrhenius pair ``(Ea, A)`` and the engine computes
``k = A*exp(-Ea/RT)``, this module sources the transition-state activation parameters ``(ΔH‡, ΔS‡)`` and the
engine (:mod:`smartchem.experiment.eyring`) computes ``k = (kB*T/h)*exp(-ΔG‡/RT)`` with ``ΔG‡ = ΔH‡ - T*ΔS‡``
(the Eyring equation, established transition-state theory).  The two providers are INDEPENDENT bearings on
the SAME observable ``k``: where both cover a reaction, the two computed ``k``'s cross-validate (the repo's
"two blind paths to one number" discipline), and neither is derived from the other.

Why ΔH‡/ΔS‡ and not a single ΔG‡
-------------------------------
A single ``ΔG‡`` is pinned to one temperature; storing the enthalpy/entropy pair (the usual Eyring-plot
outputs) makes ``ΔG‡`` correctly ``T``-dependent -- exactly as the Arrhenius ``(Ea, A)`` pair makes ``k``
temperature-dependent -- and lets a large negative ``ΔS‡`` (an ordered, associative transition state) carry
its mechanistic sign honestly.

Same disciplines as :mod:`smartchem.data.kinetics`
--------------------------------------------------
* Records name their reactants/products by **SMILES**; the engine matches on the CANONICAL STRUCTURE of each
  (``canonical_digest(m.canonical())``), NOT the molecular formula -- so a same-formula isomer never inherits
  another's barrier, and the match is DIRECTION-SPECIFIC.
* A lookup miss returns ``None`` -> a LOUD ``UNKNOWN`` rate, never a fabricated ``k``.  The seed is tiny
  (calibration only) and injectable; a caller extends coverage with :meth:`EyringTable.with_records`.
* Every value is FETCHED with author + year (never recalled), and a barrier is NEVER back-computed from an
  Arrhenius ``Ea/A`` (circular) nor from ground-state formation data (a transition state has no formation
  enthalpy) -- only an independently measured/tabulated activation parameter, or a documented gap.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Digestible
from .kinetics import SpeciesSpec, _is_species_spec

__all__ = [
    "EyringRef",
    "EyringTable",
    "SEED_EYRING_REFS",
    "DEFAULT_EYRING",
    "EYRING_GAPS",
]


@dataclass(frozen=True)
class EyringRef(Digestible):
    """One elementary reaction's SOURCED transition-state activation parameters, reactants/products by SMILES.

    ``reactant_smiles`` / ``product_smiles`` are tuples of ``(smiles, coefficient)`` -- the engine matches on
    the CANONICAL STRUCTURE of each (never the formula).  ``dh_dagger_kj_per_mol`` is the activation enthalpy
    ``ΔH‡`` (kJ/mol, a barrier so ``>= 0``); ``ds_dagger_j_per_mol_k`` is the activation entropy ``ΔS‡``
    (J/mol/K, ANY sign -- an associative transition state has ``ΔS‡ < 0``); ``a_units`` is the order-dependent
    unit of the resulting rate constant (``"s^-1"`` unimolecular, ``"M^-1 s^-1"`` bimolecular -- carried for
    honesty since ``k``'s units and half-life interpretation depend on the reaction order);
    ``temperature_range_k`` is the ``(lo, hi)`` window the activation parameters are stated valid over (inside
    it a rate is DERIVED, outside it a flagged PREDICTED extrapolation).  ``provenance`` (author + year) is
    REQUIRED.
    """

    reactant_smiles: SpeciesSpec
    product_smiles: SpeciesSpec
    name: str
    dh_dagger_kj_per_mol: float
    ds_dagger_j_per_mol_k: float
    a_units: str
    temperature_range_k: tuple[float, float]
    provenance: str

    def __post_init__(self) -> None:
        for field_name in ("name", "a_units", "provenance"):
            v = getattr(self, field_name)
            if not isinstance(v, str) or not v:
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("dh_dagger_kj_per_mol", "ds_dagger_j_per_mol_k"):
            v = getattr(self, field_name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
        if self.dh_dagger_kj_per_mol < 0:
            raise ValueError("activation enthalpy ΔH‡ cannot be negative (it is a barrier)")
        if not _is_species_spec(self.reactant_smiles):
            raise ValueError("reactant_smiles must be a non-empty tuple of (smiles, +int) pairs")
        if not _is_species_spec(self.product_smiles):
            raise ValueError("product_smiles must be a non-empty tuple of (smiles, +int) pairs")
        rng = self.temperature_range_k
        if type(rng) is not tuple or len(rng) != 2:
            raise TypeError("temperature_range_k must be a (lo, hi) tuple")
        lo, hi = rng
        for v in rng:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError("temperature_range_k bounds must be real numbers")
        if not (0 < lo <= hi):
            raise ValueError("temperature_range_k must satisfy 0 < lo <= hi (kelvin)")

    @property
    def is_first_order(self) -> bool:
        """True iff the rate constant carries first-order units (``s^-1``) -- concentration-free half-life."""
        return self.a_units.replace(" ", "") == "s^-1"


@dataclass(frozen=True)
class EyringTable(Digestible):
    """An immutable set of sourced :class:`EyringRef` records, mirroring
    :class:`~smartchem.data.kinetics.KineticTable`: the compiler holds a table, a caller extends it with
    :meth:`with_records`, records are deduplicated by their ``(reactant_smiles, product_smiles)`` source form
    (a later record wins)."""

    records: tuple[EyringRef, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(type(r) is not EyringRef for r in self.records):
            raise TypeError("records must be a tuple of EyringRef values")

    def with_records(self, *records: EyringRef) -> "EyringTable":
        by_key: dict[tuple[SpeciesSpec, SpeciesSpec], EyringRef] = {
            (r.reactant_smiles, r.product_smiles): r for r in self.records
        }
        for r in records:
            if type(r) is not EyringRef:
                raise TypeError("with_records takes EyringRef values")
            by_key[(r.reactant_smiles, r.product_smiles)] = r
        return EyringTable(tuple(sorted(by_key.values(), key=lambda r: (r.reactant_smiles, r.product_smiles))))


#: The SEED -- sourced transition-state activation parameters for CALIBRATION reaction(s) whose rate constant
#: is measured, so the engine's computed k can be checked against a known value (the instrument rule).  Tiny
#: by design and injectable per call, NOT a whitelist.  Filled from FETCHED, cited values -- never recalled,
#: and NEVER back-computed from an Arrhenius Ea/A (that would be circular).  The instrument reads true: with
#: these parameters, k = (kB*T/h)*exp(-ΔG‡/RT) reproduces an INDEPENDENTLY measured k within 0.14 decades.
SEED_EYRING_REFS: tuple[EyringRef, ...] = (
    # Alkaline hydrolysis (saponification) of ethyl acetate: a bimolecular SN2-at-carbonyl reaction whose
    # transition-state activation parameters are INDEPENDENTLY tabulated (Eyring/TST, NOT an Arrhenius
    # back-calc) -- the calibration reaction for the Eyring provider.
    EyringRef(
        reactant_smiles=(("CCOC(C)=O", 1), ("[OH-]", 1)),
        product_smiles=(("CC(=O)[O-]", 1), ("CCO", 1)),
        name="ethyl acetate saponification",
        dh_dagger_kj_per_mol=38.6,
        ds_dagger_j_per_mol_k=-131.0,
        a_units="M^-1 s^-1",
        temperature_range_k=(298.0, 323.0),
        provenance=(
            "CH3COOC2H5 + OH- -> CH3COO- + C2H5OH (bimolecular, rate = k[ester][OH-]). ΔH‡ = 38.6±0.5 kJ/mol, "
            "ΔS‡ = -131.0±1.4 J/mol/K (=> ΔG‡(298 K) = 77.7 kJ/mol), obtained by transition-state theory "
            "SEPARATELY from the Arrhenius fit (NOT an Ea/A back-calc -- the non-circularity requirement), "
            "Petek & Krajnc, Int. J. Chem. Kinet. 44(10):692-698 (2012); the TST methodology confirmed "
            "verbatim from the Crossref abstract, the numeric table via a secondary channel because the Wiley "
            "primary is paywalled (403) -- a provenance caveat answered by calibration. CALIBRATED against an "
            "INDEPENDENT measured rate constant: the engine reproduces k(298 K) = 0.154 M^-1 s^-1 vs the "
            "measured 0.112 M^-1 s^-1 (Tsujikawa & Inoue, Bull. Chem. Soc. Jpn. 39(9):1837 (1966)) -- 0.14 "
            "decades / a factor of 1.4, across two independent studies 46 years apart. The large negative "
            "ΔS‡ is physically correct for an associative transition state. Fit window 298-323 K."
        ),
    ),
)

#: A convenience default seed; extended per call for any other reaction, NOT a whitelist.
DEFAULT_EYRING = EyringTable(SEED_EYRING_REFS)


#: Reaction -> why no sourced activation parameters are stored (documented, never a silent absence), exactly
#: as :data:`~smartchem.data.kinetics.KINETIC_GAPS` documents missing Arrhenius data.
EYRING_GAPS: dict[str, str] = {
    "furan-maleimide retro-Diels-Alder": (
        "the only fully-open-access, cleanly-verbatim Eyring ΔH‡/ΔS‡ table found this pass (Widstrom & Lear, "
        "PMC6892874, 2019, retro-Diels-Alder of furan-maleimide adducts) was REJECTED as a seed on PHYSICAL "
        "grounds: its ΔS‡ = +178..+215 (source header omits the K^-1) for a unimolecular retro-DA implies an "
        "Arrhenius A-factor far larger than physically sensible, so the printed values could not be trusted -> "
        "not seeded, rather than ship an anomalous barrier. A clean open-access primary Eyring table for a "
        "physically-sound reaction remains a gap; the saponification seed came via a paywalled primary."
    ),
}
