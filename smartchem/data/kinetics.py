"""Sourced Arrhenius kinetic data (Ea, A) -- the inputs the L1 rate engine reproduces ``k`` from.

The kinetic sibling of :mod:`smartchem.data.thermo`.  A tiny, sourced seed of Arrhenius parameters for
CALIBRATION reactions -- reactions whose rate constant is measured and tabulated, so the engine's
``k = A·exp(-Ea/RT)`` can be checked against a known value before any novel output is believed (the
instrument rule).  From a :class:`KineticRef` an established model (the Arrhenius equation) computes a rate
constant; a reaction with no sourced ``(Ea, A)`` yields a LOUD ``UNKNOWN`` rate, never a fabricated ``k``.

Why this is keyed by a REACTION, and by STRUCTURE not formula
------------------------------------------------------------
Thermodynamic data (:mod:`~smartchem.data.thermo`) is per-species and summed; a rate constant is a property
of the WHOLE elementary reaction, so a :class:`KineticRef` names its reactants and products.  It names them by
**SMILES**, and the engine (:mod:`smartchem.experiment.kinetics`) matches on the CANONICAL STRUCTURE of each
species (the same ``canonical_digest(m.canonical())`` identity :mod:`smartchem.data.autoload` uses), NOT on the
molecular formula -- because two constitutional isomers share a formula but not a rate, and matching on formula
would hand one compound another's measured rate (a fabricated number in place of a loud UNKNOWN).  The match is
DIRECTION-SPECIFIC: forward and reverse rates differ, so a record for ``2 N2O5 -> 4 NO2 + O2`` does not answer
the reverse assembly's rate (that stays UNKNOWN).  Storing SMILES keeps the seed human-writable; the engine owns
the canonicalisation so the data layer stays parser-free.

The universality contract (identical to :mod:`smartchem.data.thermo`)
--------------------------------------------------------------------
* The compiler holds a :class:`KineticTable`, not this module's tuple, so a chemist EXTENDS coverage for any
  reaction with :meth:`KineticTable.with_records` and passes the result in -- the universality lever.
* A lookup miss returns ``None`` -> the rate engine renders a LOUD ``UNKNOWN`` (never a fabricated ``k``).
  Absence is never a guess; the seed is deliberately tiny (calibration only) and every value carries its
  source (author, year).
* ``log10 A`` is stored (not ``A``): the pre-exponential factor spans ``1e11 .. 1e15``, and the engine works
  in ``log10 k`` space so an enormous ``A`` never overflows a float into a fabricated ``inf`` -- the same
  overflow honesty :mod:`~smartchem.experiment.equilibrium` uses for ``K``.

What this does NOT do: it never invents an ``(Ea, A)`` for a reaction it has no source for, never guesses a
barrier from bond energies or group additivity (that would be a NOVEL, unestablished kinetics model -- the
forbidden move per :mod:`smartchem.experiment.bucket`), and never claims which cleavage Nature actually takes.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..contracts import Digestible

__all__ = [
    "SpeciesSpec",
    "KineticRef",
    "KineticTable",
    "SEED_KINETIC_REFS",
    "DEFAULT_KINETICS",
    "KINETIC_GAPS",
]

#: One side of a reaction, named by SMILES: a tuple of ``(smiles, coefficient)`` pairs, coefficients > 0.
#: The engine canonicalises each SMILES to a structural identity for matching -- the SMILES is the writable
#: source form, the canonical structure is the match key.
SpeciesSpec = tuple


def _is_species_spec(spec: object) -> bool:
    """True iff ``spec`` is a non-empty tuple of ``(non-empty-str SMILES, positive-int coefficient)`` pairs."""
    if type(spec) is not tuple or not spec:
        return False
    for item in spec:
        if type(item) is not tuple or len(item) != 2:
            return False
        smiles, coeff = item
        if not isinstance(smiles, str) or not smiles:
            return False
        if isinstance(coeff, bool) or not isinstance(coeff, int) or coeff <= 0:
            return False
    return True


@dataclass(frozen=True)
class KineticRef(Digestible):
    """One elementary reaction's SOURCED Arrhenius parameters, its reactants/products named by SMILES.

    ``reactant_smiles`` / ``product_smiles`` are tuples of ``(smiles, coefficient)`` -- the engine matches on
    the CANONICAL STRUCTURE of each (never the formula), so a same-formula isomer never inherits this rate.
    ``ea_kj_per_mol`` is the activation energy (kJ/mol); ``log10_a`` is the base-10 log of the pre-exponential
    factor ``A``; ``a_units`` is the order-dependent unit of ``A`` (``"s^-1"`` first-order, ``"M^-1 s^-1"`` /
    ``"cm^3 molecule^-1 s^-1"`` second-order -- carried for honesty, since a rate constant's units and
    interpretation depend on the reaction order); ``temperature_range_k`` is the ``(lo, hi)`` window the
    Arrhenius fit is stated valid over (inside it a rate is DERIVED, outside it a flagged PREDICTED
    extrapolation).  ``provenance`` (author + year) is REQUIRED, exactly as for a
    :class:`~smartchem.data.thermo.ThermoRef`.
    """

    reactant_smiles: SpeciesSpec
    product_smiles: SpeciesSpec
    name: str
    ea_kj_per_mol: float
    log10_a: float
    a_units: str
    temperature_range_k: tuple[float, float]
    provenance: str

    def __post_init__(self) -> None:
        for field_name in ("name", "a_units", "provenance"):
            v = getattr(self, field_name)
            if not isinstance(v, str) or not v:
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("ea_kj_per_mol", "log10_a"):
            v = getattr(self, field_name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise TypeError(f"{field_name} must be a real number")
        if self.ea_kj_per_mol < 0:
            raise ValueError("activation energy Ea cannot be negative")
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
        """True iff ``A`` carries first-order units (``s^-1``) -- the case with a concentration-free half-life."""
        return self.a_units.replace(" ", "") == "s^-1"


@dataclass(frozen=True)
class KineticTable(Digestible):
    """An immutable set of sourced :class:`KineticRef` records.  The engine resolves a step against them by
    canonical reaction structure; this container just holds and deduplicates them.

    Mirrors :class:`~smartchem.data.thermo.ThermoTable`: the compiler holds a table, a caller extends it with
    :meth:`with_records`, records are deduplicated by their ``(reactant_smiles, product_smiles)`` source form
    (a later record wins).
    """

    records: tuple[KineticRef, ...]

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(type(r) is not KineticRef for r in self.records):
            raise TypeError("records must be a tuple of KineticRef values")

    def with_records(self, *records: KineticRef) -> "KineticTable":
        by_key: dict[tuple[SpeciesSpec, SpeciesSpec], KineticRef] = {
            (r.reactant_smiles, r.product_smiles): r for r in self.records
        }
        for r in records:
            if type(r) is not KineticRef:
                raise TypeError("with_records takes KineticRef values")
            by_key[(r.reactant_smiles, r.product_smiles)] = r
        return KineticTable(tuple(sorted(by_key.values(), key=lambda r: (r.reactant_smiles, r.product_smiles))))


#: The SEED -- sourced Arrhenius parameters for CALIBRATION reaction(s) whose rate is measured and tabulated,
#: so the engine's computed k can be checked against a known value.  Tiny by design; injectable per call for
#: any reaction, NOT a whitelist.  Filled from FETCHED, cited values -- never recalled from memory.  The
#: instrument reads true: with these parameters, k = A*exp(-Ea/RT) reproduces the measured k at 298 K (3.6e-5
#: vs 3.38e-5, ~7%) and 338 K (5.0e-3 vs 4.82e-3, ~3%).
SEED_KINETIC_REFS: tuple[KineticRef, ...] = (
    # 2 N2O5 -> 4 NO2 + O2: THE canonical first-order gas-phase Arrhenius calibration reaction.
    KineticRef(
        reactant_smiles=(("O=[N+]([O-])O[N+](=O)[O-]", 2),),
        product_smiles=(("[N+](=O)[O-]", 4), ("O=O", 1)),
        name="N2O5 decomposition",
        ea_kj_per_mol=103.5,
        log10_a=13.69,
        a_units="s^-1",
        temperature_range_k=(298.0, 338.0),
        provenance=(
            "2 N2O5 -> 4 NO2 + O2, first order in N2O5 (convention: -d[N2O5]/dt = k[N2O5], the per-N2O5-"
            "consumed rate, NOT the reaction-rate convention which is half this). Ea = 103.5 kJ/mol, "
            "A = 4.9e13 s^-1 (log10 A = 13.69); Arrhenius fit valid ~298-338 K. FETCHED and corroborated "
            "across >=3 independent sources: FSU CHM1046 states Ea = 103 kJ/mol; a Numerade k(T) regression "
            "(ln k = -12447/T + 31.519, R2 = 0.9999 over 298/318/338 K) gives Ea = 103.5, log10 A = 13.69; "
            "Brown/LeMay 'Chemistry: The Central Science' gives measured k = 3.38e-5 s^-1 at 298 K and "
            "4.82e-3 s^-1 at 337 K. Textbook-compilation provenance (Daniels & Johnston 1921 lineage; the "
            "primary paper was not directly fetched). log10 A = 4.9e13 differs ~14% from the classic 4.3e13; "
            "either calibrates the engine."
        ),
    ),
    # Cyclopropane -> propene thermal isomerization: the canonical first-order UNIMOLECULAR family (single
    # reactant, single product, clean s^-1, and a 1:1 isomerization so NO stoichiometric-convention ambiguity).
    KineticRef(
        reactant_smiles=(("C1CC1", 1),),
        product_smiles=(("CC=C", 1),),
        name="cyclopropane isomerization",
        ea_kj_per_mol=272.0,
        log10_a=15.20,
        a_units="s^-1",
        temperature_range_k=(700.0, 800.0),
        provenance=(
            "cyclopropane -> propene, first order (rate = -d[c-C3H6]/dt = k[c-C3H6]; a 1:1 isomerization, so "
            "no stoichiometric-convention ambiguity). Ea = 272 kJ/mol, A = 1.58e15 s^-1 (log10 A = 15.20) "
            "from Atkins' Physical Chemistry, Data Table 22.4 (Arrhenius parameters); classic experimental "
            "lineage Chambers & Kistiakowsky 1934 / Pritchard, Sowden & Trotman-Dickenson 1953 / tabulated by "
            "Laidler. The table prints no explicit validity window; set to the classic high-pressure "
            "gas-phase experimental regime ~700-800 K, anchored by the sourced point k = 6.71e-4 s^-1 at "
            "773 K (Atkins Table 22.1), which the engine reproduces to 0.985 (6.61e-4 computed) -- the "
            "instrument reads true. FETCHED via curl+pdftotext from the Atkins data-tables PDF, quoted "
            "verbatim; not recalled. NOTE: the isomer cyclopropane and product propene share the formula "
            "C3H6, so this record is safe ONLY because the engine keys on canonical STRUCTURE, not formula."
        ),
    ),
)

#: A convenience default seed; extended per call for any other reaction, NOT a whitelist.
DEFAULT_KINETICS = KineticTable(SEED_KINETIC_REFS)


#: Reaction -> why no sourced Arrhenius fit is stored (documented, never a silent absence), exactly as
#: :data:`~smartchem.data.thermo_extended.EXTENDED_THERMO_GAPS` documents missing thermodynamic data.
KINETIC_GAPS: dict[str, str] = {
    "2 HI -> H2 + I2": (
        "HI gas-phase decomposition (the classic second-order reaction): Ea = 180-186 kJ/mol IS sourced "
        "(UCalgary fit of the classic k(T) table; primary raw data Bodenstein 1899, Z. phys. Chem. 29, "
        "295-314, over 556-781 K), but NO live source directly tabulating the pre-exponential factor A "
        "(second order, M^-1 s^-1) was fetchable this run -> the rate stays UNKNOWN rather than shipping a "
        "fitted (not-quoted) A. A ~ 1e11 M^-1 s^-1 can be derived from the fetched k(T), but a derived A is "
        "not a sourced A."
    ),
    "4-aminophenol + acetic anhydride -> paracetamol": (
        "the litmus acetylation: the reaction is KNOWN (sourced regiochemistry attests it), but its "
        "Arrhenius (Ea, A) rate parameters are not sourced -> its RATE is a loud UNKNOWN, ORTHOGONALLY to "
        "the KNOWN grade. A reaction can be attested-and-legitimate yet kinetically unquantified; L2 says so."
    ),
    "ethyl acetate saponification (Arrhenius A)": (
        "CH3COOC2H5 + OH- -> CH3COO- + C2H5OH: Ea = 43.1 kJ/mol IS sourced (Mukhtar et al., Res. J. Chem. "
        "Sci. 5(11):46 (2015)), but that paper's tabulated pre-exponential 2.314e10 has AMBIGUOUS units -- it "
        "prints k in 'min-1' for a SECOND-order reaction, and reading that A as M^-1 s^-1 gives a k ~100x the "
        "independently measured value, so the units cannot be pinned -> the ARRHENIUS rate stays UNKNOWN "
        "rather than ship a mis-conventioned A. The reaction's rate IS reproduced by the EYRING provider from "
        "independently-sourced ΔH‡/ΔS‡ (see smartchem.data.eyring) -- the two providers are complementary."
    ),
}
