"""OPERATION XXIII S4 -- an ACTIVITY-based solid dissolution / precipitation law for the 2.0 research kernel.

WHAT THIS ADDS.  ``unified_chemical_world.BicarbonateDissolutionRate`` saturates on an EMPIRICAL concentration product
Qsp = S^2 (the sourced bulk solubility squared).  That proxy is dilute-only and NaHCO3-specific.  This module adds the
generic thermodynamic form for a solid  M_a X_b(s) <=> a M^zm + b X^zx :

    r_vol = k * (1 - Omega),   Omega = IAP / Ksp,   IAP = prod_i (gamma_i * c_i)^nu_i

with Davies activity coefficients at the ionic strength of the concentration map the law is handed
(I = 1/2 sum_i c_i z_i^2 over EVERY charged species in the map -- the compartment's own I, not a global).
Dissolution (r > 0) needs the solid present; precipitation (r < 0) needs ``allow_precipitation=True`` AND the solid
present (no nucleation -- deliberately the simplest sound choice).

``ActivityReversibleRate`` is the companion law for the FAST aqueous speciation that a dissolving solid feeds
(CO3^2- + H+ <=> HCO3-, ion pairs, ...):  r = kf * (prod a_react - prod a_prod / K) in ACTIVITIES, with declared
unit-activity species (the solvent) excluded from the products.  Both laws share ONE activity model and ONE domain.

THE DOMAIN, AND WHY IT FAILS CLOSED.  Davies carries no specific-ion terms.  The Phase III convention verdict
(benchmarks/measured_buffers_xxiii/CONVENTION_BRIDGE_VERDICT.md) measured it at only ~0.01 pH even at I ~ 0.1 (3 of 3
NIST buffers REFUTED at the convention-free level).  So the default declared domain is ionic_strength_max = 0.1, and
``evaluate`` RAISES ``OutOfDomainError`` (a KernelError, verdict OUT_OF_DOMAIN) when I exceeds it: a world can never
integrate these laws silently outside the regime where the activity model has been checked.  Raising the limit is a
declared, descriptor-bound parameter (so it moves the world certificate), never a silent default.

AUDIT.  Both classes are sealed through general_kernel's CLOSED audit table (``_AUDITED_BUILTIN_PINS``), so they run as
AUDITED_BUILTIN.  Each class is SELF-CONTAINED on purpose (the pin hashes the class source only, so any logic a class
executes lives inside it; the two Davies implementations are duplicated and a test cross-checks them).  Honest limits:
the pin does not cover the module-level imports/``OutOfDomainError``; the activity model is Davies on MOLARITY (not
molality); neutral species have gamma = 1; 25 C only (the rate law is not handed the world temperature, so the Ksp's
T_K provenance is the only temperature statement); k and kf are ASSUMED kinetic scales -- they set how fast, never
where, the steady state sits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from experiments.sandbox_foundation.aqueous_equilibrium import DAVIES_A_25C, SourcedConstant
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER, OUT_OF_DOMAIN
from experiments.sandbox_foundation.general_coupled import _canon_num, _species_key
from experiments.sandbox_foundation.general_kernel import KernelError, Phase, RateLaw, Species, _seal_audited_builtin

#: Default declared activity-model domain (mol/L): the Phase III verdict's I ~ 0.1 regime, where Davies is ~0.01 pH.
DEFAULT_IONIC_STRENGTH_MAX = 0.1


class OutOfDomainError(KernelError):
    """The concentration map's ionic strength lies outside the activity model's declared domain.  Carries the
    OUT_OF_DOMAIN verdict plus the offending/declared ionic strengths, so a caller reads the claim status off the
    exception.  Raised from ``evaluate`` -- an integration that wanders out of domain ABORTS, it does not continue."""

    def __init__(self, message: str, ionic_strength: float = float("nan"), ionic_strength_max: float = float("nan")):
        super().__init__(message)
        self.verdict = OUT_OF_DOMAIN
        self.ionic_strength = ionic_strength
        self.ionic_strength_max = ionic_strength_max


def _constant_key(c: SourcedConstant) -> tuple:
    """Lossless identity of a sourced constant (every field a reader could be misled by)."""
    return (c.name, _canon_num(c.value), _canon_num(c.uncertainty), c.units, _canon_num(c.T_K), c.source, c.status,
            c.note)


def _check_common(k, A, ionic_strength_max, tier, what):
    for nm, v in ((what, k), ("davies_A", A), ("ionic_strength_max", ionic_strength_max)):
        if isinstance(v, bool) or not (isinstance(v, (int, float)) and math.isfinite(v)):
            raise KernelError(f"{nm} must be a finite number")
    if k < 0:
        raise KernelError(f"{what} must be >= 0")
    if A <= 0 or ionic_strength_max <= 0:
        raise KernelError("davies_A and ionic_strength_max must be > 0")
    if not isinstance(tier, str):
        raise KernelError("tier must be a string")


def _check_stoich(stoich):
    if type(stoich) is not tuple or len(stoich) < 2 or not all(
            type(p) is tuple and len(p) == 2 and type(p[0]) is Species and type(p[1]) is int
            and not isinstance(p[1], bool) and p[1] != 0 for p in stoich):
        raise KernelError("stoich must be a tuple of >= 2 (Species, nonzero int) pairs")
    if len({sp for sp, _ in stoich}) != len(stoich):
        raise KernelError("a species appears twice in the law's stoichiometry")
    if sum(c * sp.charge for sp, c in stoich) != 0:
        raise KernelError("the law's declared stoichiometry does not conserve charge")


@dataclass(frozen=True)
class ActivitySolubilityRate(RateLaw):
    """r_vol = k (1 - Omega) for M_a X_b(s) <=> a M + b X, Omega = IAP/Ksp in Davies ACTIVITIES (see module docstring).

    ``stoich`` is the declared reaction as ((Species, coeff), ...): exactly one SOLID reactant (coeff -1) and the
    aqueous ion products (coeff = nu_i > 0).  evaluate() refuses a Reaction whose stoichiometry differs from it.
    ``ksp`` is a SourcedConstant (dimensionless activity product, 1 mol/L standard state).  Units of k: mol L^-1 s^-1."""
    k: float
    ksp: SourcedConstant
    stoich: tuple
    allow_precipitation: bool = False
    davies_A: float = DAVIES_A_25C.value
    ionic_strength_max: float = DEFAULT_IONIC_STRENGTH_MAX
    tier: str = ASSUMED_PARAMETER
    source: str = "ActivitySolubilityRate (XXIII-S4): Davies activities, domain-guarded"

    def __post_init__(self):
        _check_common(self.k, self.davies_A, self.ionic_strength_max, self.tier, "k")
        if type(self.ksp) is not SourcedConstant or self.ksp.status == "UNKNOWN":
            raise KernelError("ksp must be a SourcedConstant with a value (an UNKNOWN Ksp cannot drive a law)")
        if type(self.allow_precipitation) is not bool:
            raise KernelError("allow_precipitation must be a bool")
        _check_stoich(self.stoich)
        solids = [(sp, c) for sp, c in self.stoich if sp.phase is Phase.SOLID]
        if len(solids) != 1 or solids[0][1] != -1:
            raise KernelError("exactly one SOLID reactant with coefficient -1 is required")
        ions = [(sp, c) for sp, c in self.stoich if sp.phase is not Phase.SOLID]
        if not ions or any(sp.phase is not Phase.AQUEOUS or c <= 0 for sp, c in ions):
            raise KernelError("every non-solid species must be an AQUEOUS product with a positive coefficient")

    def evaluate(self, reaction, concentrations):
        if dict(reaction.stoich) != dict(self.stoich):
            raise KernelError("the Reaction's stoichiometry differs from the law's declared stoichiometry")
        ionic = 0.0
        for sp, c in concentrations.items():
            if sp.charge:
                ionic += 0.5 * max(float(c), 0.0) * sp.charge * sp.charge
        if not math.isfinite(ionic):
            raise KernelError("non-finite ionic strength")
        if ionic > self.ionic_strength_max:
            raise OutOfDomainError(
                f"ionic strength {ionic:.6g} mol/L exceeds the declared Davies-activity domain "
                f"{self.ionic_strength_max:.6g} mol/L: refusing to evaluate the solid-equilibrium law out of domain",
                ionic, self.ionic_strength_max)
        s = math.sqrt(ionic)
        log_g1 = -self.davies_A * (s / (1.0 + s) - 0.3 * ionic)          # Davies log10 gamma of a |z| = 1 ion
        solid = None
        iap = 1.0
        for sp, nu in self.stoich:
            if sp.phase is Phase.SOLID:
                solid = sp
            else:
                iap *= (10.0 ** (log_g1 * sp.charge * sp.charge) * max(float(concentrations[sp]), 0.0)) ** nu
        omega = iap / self.ksp.value
        present = float(concentrations[solid]) > 0.0
        if not present:
            return 0.0                                  # no solid: nothing to dissolve and nothing to grow on
        if omega >= 1.0 and not self.allow_precipitation:
            return 0.0                                  # supersaturated: dissolution only, never precipitates
        return self.k * (1.0 - omega)

    def descriptor(self):
        # Binds EVERY operative parameter: k, the full Ksp provenance, the declared stoichiometry (species identities +
        # coefficients), Davies A, the domain limit, the precipitation switch, tier and source.
        return ("ActivitySolubilityRate", _canon_num(self.k), _constant_key(self.ksp),
                tuple((_species_key(sp), int(c)) for sp, c in self.stoich),
                self.allow_precipitation, _canon_num(self.davies_A), _canon_num(self.ionic_strength_max),
                self.tier, self.source)


_seal_audited_builtin(ActivitySolubilityRate)


@dataclass(frozen=True)
class ActivityReversibleRate(RateLaw):
    """r_vol = kf (prod a_react^nu - prod a_prod^nu / K) in Davies ACTIVITIES, for a fast aqueous speciation step.

    ``K`` is the activity equilibrium quotient of the reaction AS WRITTEN (products over reactants).  ``unit_activity``
    names species held at activity 1 and left out of both products (the solvent, a pure liquid).  ``stoich`` is the
    declared reaction; evaluate() refuses a Reaction that differs.  Same I-domain guard as ActivitySolubilityRate."""
    kf: float
    K: SourcedConstant
    stoich: tuple
    unit_activity: tuple = ()
    davies_A: float = DAVIES_A_25C.value
    ionic_strength_max: float = DEFAULT_IONIC_STRENGTH_MAX
    tier: str = ASSUMED_PARAMETER
    source: str = "ActivityReversibleRate (XXIII-S4): Davies activities, domain-guarded"

    def __post_init__(self):
        _check_common(self.kf, self.davies_A, self.ionic_strength_max, self.tier, "kf")
        if type(self.K) is not SourcedConstant or self.K.status == "UNKNOWN":
            raise KernelError("K must be a SourcedConstant with a value")
        _check_stoich(self.stoich)
        declared = {sp for sp, _ in self.stoich}
        if type(self.unit_activity) is not tuple or any(sp not in declared for sp in self.unit_activity):
            raise KernelError("unit_activity must be a tuple of species that appear in the stoichiometry")
        if any(sp.charge for sp in self.unit_activity):
            raise KernelError("a unit-activity (solvent/pure-phase) species must be uncharged")

    def evaluate(self, reaction, concentrations):
        if dict(reaction.stoich) != dict(self.stoich):
            raise KernelError("the Reaction's stoichiometry differs from the law's declared stoichiometry")
        ionic = 0.0
        for sp, c in concentrations.items():
            if sp.charge:
                ionic += 0.5 * max(float(c), 0.0) * sp.charge * sp.charge
        if not math.isfinite(ionic):
            raise KernelError("non-finite ionic strength")
        if ionic > self.ionic_strength_max:
            raise OutOfDomainError(
                f"ionic strength {ionic:.6g} mol/L exceeds the declared Davies-activity domain "
                f"{self.ionic_strength_max:.6g} mol/L: refusing to evaluate the speciation law out of domain",
                ionic, self.ionic_strength_max)
        s = math.sqrt(ionic)
        log_g1 = -self.davies_A * (s / (1.0 + s) - 0.3 * ionic)
        fwd = 1.0
        rev = 1.0
        for sp, nu in self.stoich:
            if sp in self.unit_activity:
                continue
            a = 10.0 ** (log_g1 * sp.charge * sp.charge) * max(float(concentrations[sp]), 0.0)
            if nu < 0:
                fwd *= a ** (-nu)
            else:
                rev *= a ** nu
        return self.kf * (fwd - rev / self.K.value)

    def descriptor(self):
        return ("ActivityReversibleRate", _canon_num(self.kf), _constant_key(self.K),
                tuple((_species_key(sp), int(c)) for sp, c in self.stoich),
                tuple(_species_key(sp) for sp in self.unit_activity),
                _canon_num(self.davies_A), _canon_num(self.ionic_strength_max), self.tier, self.source)


_seal_audited_builtin(ActivityReversibleRate)
