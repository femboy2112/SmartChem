"""OPERATION XXV Phase III-B -- an OPEN-AIR calcite + water + CO2(g) world at temperature T (research code only).

    CaCO3(s) <=> Ca+2 + CO3-2                       Kc(T)         Plummer & Busenberg 1982 (P&B)
    CO3-2 + H+ <=> HCO3-                            1/K2(T)       P&B
    HCO3- + H+ <=> CO2(aq) + H2O                    1/K1(T)       P&B
    H+ + OH- <=> H2O                                1/Kw(T)       phreeqc.dat fit (not P&B)
    Ca+2 + CO3-2 <=> CaCO3(aq)                      K(T)          P&B      } include_ion_pairs=True (default)
    Ca+2 + HCO3- <=> CaHCO3+                        K(T)          P&B      }
    CO2(g, fixed pCO2) <=> CO2(aq)                  KH(T)         P&B, via gas_boundary_xxv.GasLiquidBoundary

Every constant comes from ``temperature_law_xxv`` evaluated at the world temperature T_K, transported molal -> molar by
``standard_state.molal_to_molar_logK``, and stamped with T_K, so the kernel's XXIV-2A source-domain check passes at T_K
and refuses at any other temperature.  Activities are Davies (the sandbox's ``ActivitySolubilityRate`` /
``ActivityReversibleRate``, sealed audited built-ins) with A(T) from ``temperature_law_xxv.davies_A``, in the declared
domain I <= 0.1 mol/L.  The world is integrated MONOLITHICALLY (no operator splitting, so the steady state is the exact
fixed point of the full right-hand side) until a convergence certificate holds: Omega = 1, c(CO2,aq) = c_sat, and
Q/K = 1 for every speciation reaction, each to EQ_RTOL.  Otherwise it raises (fail closed).

ION PAIRS: the existing sandbox calcite world (benchmarks/solid_equilibrium_xxiii, build_calcite_world) carries CaCO3(aq),
CaHCO3+ and CaOH+, so ``include_ion_pairs`` defaults to True.  CaOH+ is OMITTED here: no temperature law for it exists in
either vendored database (phreeqc.dat holds a bare 25 C log_k -12.78 with no enthalpy), and executing a 25 C record at T
is exactly what this work forbids.  At the pH of an open calcite system (<= ~8.4) its share of dissolved Ca is ~1e-4 or
less; the PHREEQC verification reports it per grid point.

KINETIC SCALES (k_diss, kf, kLa) are ASSUMED_PARAMETER: they set how fast the steady state is reached, never where it is.
``logKc_shift`` exists ONLY for mutation controls; a nonzero shift marks the constant and the receipt as MUTATED.

TEMPERATURE TAGS.  Every temperature-dependent quantity the builder consumes -- each log K, K_H, Kw, Davies A and the
water density -- arrives as a T-TAGGED ``SourcedConstant``.  ``require_constants_at`` checks EVERY tag against the world
temperature (``admissibility.TEMPERATURE_MATCH_TOL_K``) BEFORE any rate law, boundary or world is constructed and raises
``OffTemperatureConstantError`` otherwise.  Before this, Davies A and rho_w travelled as bare floats the kernel's
source-domain check never saw: a 25 C Davies A injected into a 313.15 K world shifted Ca by -0.53 % unrefused.
``substitute`` (mutation controls only) replaces named slots with caller-supplied SourcedConstants that pass through the
SAME check; it accepts no bare float.  A tag can be checked, not believed: a constant re-stamped with the right T_K but
the wrong value is out of reach of this check (see the holdout runner's in-process boundary note).

CLAIM LEVEL: NUMERICALLY_EXECUTABLE + WITHIN_DECLARED_FORMULA_DOMAIN.  Agreement with PHREEQC (which shares the P&B
constants) is model-vs-model verification, never validation against nature.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from experiments.sandbox_foundation.admissibility import TEMPERATURE_MATCH_TOL_K
from experiments.sandbox_foundation.aqueous_equilibrium import SourcedConstant, _is_molar_standard_state
from experiments.sandbox_foundation.claim_tiers import ASSUMED_PARAMETER
from experiments.sandbox_foundation.gas_boundary_xxv import (
    GasLiquidBoundary,
    boundary_ledger,
    build_open_world,
    verify_world_boundaries,
)
from experiments.sandbox_foundation.general_coupled import Compartment
from experiments.sandbox_foundation.general_kernel import (
    ChemicalSystem,
    KernelError,
    Phase,
    Reaction,
    SourceDomainError,
    Species,
)
from experiments.sandbox_foundation.solid_equilibrium import ActivityReversibleRate, ActivitySolubilityRate
from experiments.sandbox_foundation.standard_state import aqueous_nu
from experiments.sandbox_foundation.temperature_law_xxv import (
    PB82_CACO3,
    PB82_CAHCO3,
    PB82_K1,
    PB82_K2,
    PB82_KH_CO2,
    PB82_LOG_KC,
    PHREEQC_DAT_KW,
    davies_A,
    water_density,
)

MODEL_NAME = "open_calcite_xxv"
MODEL_VERSION = "1"

# ASSUMED kinetic / numerical scales (steady state independent of the kinetic ones; tested).
KLA_DEFAULT_PER_S = 0.05
K_DISS_DEFAULT = 1.0e-4            # mol L^-1 s^-1
KF_DEFAULT = 1.0e8
VOLUME_L = 1.0
SOLID_MOL = 0.2                    # calcite supplied; an excess at every admitted state
N_WATER_MOL = 55.34
IONIC_STRENGTH_MAX = 0.1           # mol/L, the Davies domain of solid_equilibrium (DEFAULT_IONIC_STRENGTH_MAX)
FIRST_CHUNK_S = 10.0               # geometric chunk schedule: 10, 20, 40, ... s, one macro-step each.  A fixed long
CHUNK_GROWTH = 2.0                 # macro-step through the initial transient made BDF thrash (observed at 313.15 K,
MAX_CHUNKS = 20                    # 1e-2 atm); restarting with doubling spans converges in seconds.
RTOL, ATOL = 1e-10, 1e-18
EQ_RTOL = 1e-7                     # convergence certificate tolerance on every equilibrium residual

# pCO2 domain: P&B's CO2-H2O expressions are stated for 1 atm TOTAL pressure; partial pressures above 1 atm are refused.
PCO2_MAX_ATM = 1.0
PCO2_DOMAIN_BASIS = "ASSERTED_BY_THIS_MODULE from the source's '1 atm total pressure' statement"


class OpenCalciteError(KernelError):
    """The open calcite world refused a request or could not certify its steady state."""


class SteadyStateNotCertifiedError(OpenCalciteError):
    """The integration did not reach a state satisfying every equilibrium residual to EQ_RTOL."""


class OffTemperatureConstantError(OpenCalciteError, SourceDomainError):
    """A temperature-dependent quantity is untagged (not a SourcedConstant) or was produced for another temperature."""


#: the builder's temperature-dependent slots, by the name each carries in the receipt's constants list
KC_SLOT = "Kc_calcite"
KH_SLOT = "KH_CO2"
DAVIES_A_SLOT = "davies_A"
RHO_W_SLOT = "rho_w"
SPECIATION_SLOTS = ("K HCO3- formation", "K CO2(aq) formation", "K water formation")
ION_PAIR_SLOTS = ("K CaCO3(aq) pair", "K CaHCO3+ pair")
SLOTS = (KC_SLOT,) + SPECIATION_SLOTS + ION_PAIR_SLOTS + (KH_SLOT, DAVIES_A_SLOT, RHO_W_SLOT)


# ------------------------------------------------------------------------------------------------ species
def open_calcite_species(spectator: bool) -> dict:
    A, L, S = Phase.AQUEOUS, Phase.PURE_LIQUID, Phase.SOLID
    sp = {
        "Ca": Species.of("Ca+2", {"Ca": 1}, 2, A), "CO3": Species.of("CO3-2", {"C": 1, "O": 3}, -2, A),
        "HCO3": Species.of("HCO3-", {"C": 1, "H": 1, "O": 3}, -1, A),
        "CO2": Species.of("CO2(aq)", {"C": 1, "O": 2}, 0, A, substance="CO2"),
        "H": Species.of("H+", {"H": 1}, 1, A), "OH": Species.of("OH-", {"H": 1, "O": 1}, -1, A),
        "CaCO3aq": Species.of("CaCO3(aq)", {"Ca": 1, "C": 1, "O": 3}, 0, A),
        "CaHCO3": Species.of("CaHCO3+", {"Ca": 1, "C": 1, "H": 1, "O": 3}, 1, A),
        "H2O": Species.of("H2O", {"H": 2, "O": 1}, 0, L),
        "calcite": Species.of("CaCO3(s)", {"Ca": 1, "C": 1, "O": 3}, 0, S),
    }
    if spectator:
        sp["Na"] = Species.of("Na+", {"Na": 1}, 1, A)
        sp["Cl"] = Species.of("Cl-", {"Cl": 1}, -1, A)
    return sp


# ------------------------------------------------------------------------------------------------ inputs
def _finite(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise OpenCalciteError(f"{what} must be a finite number")
    return float(v)


def _config(*, include_ion_pairs, spectator_nacl_M, kLa_per_s, k_diss, kf) -> dict:
    if type(include_ion_pairs) is not bool:
        raise OpenCalciteError("include_ion_pairs must be a bool")
    nacl = _finite(spectator_nacl_M, "spectator_nacl_M")
    if nacl < 0:
        raise OpenCalciteError("spectator_nacl_M must be >= 0")
    for v, nm in ((kLa_per_s, "kLa_per_s"), (k_diss, "k_diss"), (kf, "kf")):
        if _finite(v, nm) <= 0:
            raise OpenCalciteError(f"{nm} must be > 0")
    return {"include_ion_pairs": include_ion_pairs, "spectator_nacl_M": nacl, "kLa_per_s": float(kLa_per_s),
            "k_diss": float(k_diss), "kf": float(kf), "volume_L": VOLUME_L, "solid_mol": SOLID_MOL,
            "n_water_mol": N_WATER_MOL, "ionic_strength_max": IONIC_STRENGTH_MAX, "first_chunk_s": FIRST_CHUNK_S,
            "chunk_growth": CHUNK_GROWTH, "max_chunks": MAX_CHUNKS, "rtol": RTOL, "atol": ATOL, "eq_rtol": EQ_RTOL,
            "pco2_max_atm": PCO2_MAX_ATM, "activity_model": "Davies(A(T)), 0.3 I, neutral gamma = 1, molar basis",
            "scheme": "monolithic"}


def _law_constant(law, T_K, stoich, unit_activity, name, *, shift=0.0) -> tuple:
    """(SourcedConstant at T_K on the molar basis, provenance row).  Checks the law's nu_aq against the kernel stoich."""
    nu = aqueous_nu(stoich, unit_activity)
    if nu != law.nu_aq:
        raise OpenCalciteError(f"{law.name}: nu_aq {law.nu_aq} != kernel stoichiometry's {nu}")
    base = law.sourced_constant(T_K, basis="molar", name=name)
    u, kind = law.uncertainty_log10(T_K)
    row = {"name": name, "law": law.name, "reaction_as_written": law.reaction, "tier": law.tier, "T_K": float(T_K),
           "basis": "molar (transported from molal)", "log10K_molal": law.log10_K(T_K),
           "log10K_molar": math.log10(base.value), "uncertainty_log10": u, "uncertainty_kind": kind,
           "law_digest": law.digest(), "source": law.source, "mutated": False}
    if shift == 0.0:
        return base, row
    mutated = SourcedConstant(
        name + " [MUTATED]", base.value * 10.0 ** shift, base.uncertainty * 10.0 ** shift, base.units, base.T_K,
        base.source + f" [MUTATION CONTROL: log10 K shifted by {shift:+.6g}; not a physical claim]", "DERIVED",
        base.note + f"; MUTATION CONTROL log10 shift {shift:+.6g}")
    row.update({"log10K_molar": math.log10(mutated.value), "mutated": True, "log10_shift": shift})
    return mutated, row


@dataclass(frozen=True)
class _Assembled:
    world: object
    sp: dict
    initial: dict
    gas: GasLiquidBoundary
    rxns: tuple
    constants: tuple
    davies_A: SourcedConstant
    rho_w: SourcedConstant
    substituted: tuple = ()


def require_constants_at(T_K, tagged: dict) -> None:
    """Refuse unless every value in ``tagged`` ({slot: value}) is a SourcedConstant whose T_K is within
    TEMPERATURE_MATCH_TOL_K of the world temperature.  Called BEFORE any rate law is constructed."""
    T = _finite(T_K, "T_K")
    bad = []
    for slot, c in tagged.items():
        if type(c) is not SourcedConstant:
            bad.append((slot, f"UNTAGGED {type(c).__name__}"))
            continue
        t = c.T_K
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) \
                or abs(float(t) - T) > TEMPERATURE_MATCH_TOL_K:
            bad.append((slot, t))
    if bad:
        raise OffTemperatureConstantError(
            f"world temperature {T} K: temperature-dependent quantities {bad} (slot, produced-for T_K) are untagged or "
            f"were produced for another temperature (tol {TEMPERATURE_MATCH_TOL_K} K); refusing before any rate law "
            f"is constructed")


def _substituted_row(slot: str, c: SourcedConstant) -> dict:
    return {"name": slot, "substituted": True, "mutated": True, "T_K": c.T_K, "value": c.value, "units": c.units,
            "constant_name": c.name, "status": c.status, "source": c.source}


def assemble_open_calcite_world(T_K, pCO2_atm, *, logKc_shift=0.0, include_ion_pairs=True, spectator_nacl_M=0.0,
                                kLa_per_s=KLA_DEFAULT_PER_S, k_diss=K_DISS_DEFAULT, kf=KF_DEFAULT,
                                substitute=None) -> _Assembled:
    """The un-integrated world (for inspection / mutation tests).  Refuses out-of-domain T, pCO2, and any
    temperature-dependent quantity not tagged for T (``require_constants_at``).  ``substitute`` ({slot: SourcedConstant},
    slots in SLOTS) exists ONLY for mutation controls; every substituted constant goes through the same tag check."""
    T = _finite(T_K, "T_K")
    p = _finite(pCO2_atm, "pCO2_atm")
    shift = _finite(logKc_shift, "logKc_shift")
    if not (0.0 < p <= PCO2_MAX_ATM):
        raise OpenCalciteError(f"pCO2 {p} atm outside (0, {PCO2_MAX_ATM}] atm ({PCO2_DOMAIN_BASIS})")
    cfg = _config(include_ion_pairs=include_ion_pairs, spectator_nacl_M=spectator_nacl_M, kLa_per_s=kLa_per_s,
                  k_diss=k_diss, kf=kf)
    sub = {} if substitute is None else substitute
    if not isinstance(sub, dict):
        raise OpenCalciteError("substitute must be a dict {slot: SourcedConstant}")
    allowed = set(SLOTS) - (set() if cfg["include_ion_pairs"] else set(ION_PAIR_SLOTS))
    if set(sub) - allowed:
        raise OpenCalciteError(f"substitute slots {sorted(set(sub) - allowed)} are not among {sorted(allowed)}")
    if KC_SLOT in sub and shift != 0.0:
        raise OpenCalciteError("substituting Kc and shifting it in the same run is refused (one mutation at a time)")
    sp = open_calcite_species(cfg["spectator_nacl_M"] > 0)
    H2O = sp["H2O"]
    # 1. every temperature-dependent quantity, as a tagged constant (nothing is constructed from them yet)
    tagged = {DAVIES_A_SLOT: davies_A(T), RHO_W_SLOT: water_density(T)}
    rows = {}
    st_cal = ((sp["calcite"], -1), (sp["Ca"], 1), (sp["CO3"], 1))
    tagged[KC_SLOT], rows[KC_SLOT] = _law_constant(PB82_LOG_KC, T, st_cal, (), KC_SLOT, shift=shift)
    spec = [
        ("HCO3- formation", PB82_K2.reversed("log_K_HCO3_formation_PB82", "CO3-2 + H+ = HCO3-"),
         ((sp["CO3"], -1), (sp["H"], -1), (sp["HCO3"], 1)), ()),
        ("CO2(aq) formation", PB82_K1.reversed("log_K_CO2_formation_PB82", "HCO3- + H+ = CO2(aq) + H2O"),
         ((sp["HCO3"], -1), (sp["H"], -1), (sp["CO2"], 1), (H2O, 1)), (H2O,)),
        ("water formation", PHREEQC_DAT_KW.reversed("log_K_water_formation_phreeqc_dat", "H+ + OH- = H2O"),
         ((sp["H"], -1), (sp["OH"], -1), (H2O, 1)), (H2O,)),
    ]
    if cfg["include_ion_pairs"]:
        spec += [
            ("CaCO3(aq) pair", PB82_CACO3, ((sp["Ca"], -1), (sp["CO3"], -1), (sp["CaCO3aq"], 1)), ()),
            ("CaHCO3+ pair", PB82_CAHCO3, ((sp["Ca"], -1), (sp["HCO3"], -1), (sp["CaHCO3"], 1)), ()),
        ]
    for nm, law, st, unit in spec:
        tagged["K " + nm], rows["K " + nm] = _law_constant(law, T, st, unit, "K " + nm)
    tagged[KH_SLOT] = PB82_KH_CO2.sourced_constant(T, basis="molal")    # what GasLiquidBoundary.from_law evaluates
    for slot, c in sub.items():
        tagged[slot] = c
    # 2. every tag must belong to the world temperature, BEFORE any rate law / boundary / world exists
    require_constants_at(T, tagged)
    A, rho = tagged[DAVIES_A_SLOT], tagged[RHO_W_SLOT]
    # 3. construction, from the verified constants only
    rxns = [Reaction("calcite dissolution", st_cal,
                     ActivitySolubilityRate(cfg["k_diss"], tagged[KC_SLOT], st_cal, davies_A=A.value,
                                            ionic_strength_max=IONIC_STRENGTH_MAX))]
    for nm, _law, st, unit in spec:
        rxns.append(Reaction(nm, st, ActivityReversibleRate(cfg["kf"], tagged["K " + nm], st, unit_activity=unit,
                                                            davies_A=A.value, ionic_strength_max=IONIC_STRENGTH_MAX)))
    species = [s for k, s in sp.items() if cfg["include_ion_pairs"] or k not in ("CaCO3aq", "CaHCO3")]
    cell = Compartment("cell", ChemicalSystem(species, rxns, VOLUME_L))
    henry = tagged[KH_SLOT]
    gas = GasLiquidBoundary("pCO2 reservoir", "cell", sp["CO2"], henry,
                            "molar" if _is_molar_standard_state(henry.units) else "molal", p, cfg["kLa_per_s"], VOLUME_L)
    rows[KH_SLOT] = {"name": KH_SLOT, "law": PB82_KH_CO2.name, "reaction_as_written": PB82_KH_CO2.reaction,
                     "tier": PB82_KH_CO2.tier, "T_K": T, "basis": "molal law -> molar target via rho_w(T)",
                     "log10K_molal": PB82_KH_CO2.log10_K(T), "log10K_molar": math.log10(gas.henry_molar()),
                     "uncertainty_log10": PB82_KH_CO2.uncertainty_log10(T)[0],
                     "uncertainty_kind": PB82_KH_CO2.uncertainty_log10(T)[1], "law_digest": PB82_KH_CO2.digest(),
                     "source": PB82_KH_CO2.source, "mutated": False}
    for slot, c in sub.items():
        if slot in rows:
            rows[slot] = _substituted_row(slot, c)
    order = [KC_SLOT] + ["K " + nm for nm, *_ in spec] + [KH_SLOT]
    world = build_open_world([cell], [gas], T)
    V = VOLUME_L
    initial = {sp["calcite"]: SOLID_MOL, H2O: N_WATER_MOL, sp["H"]: 1e-7 * V, sp["OH"]: 1e-7 * V,
               sp["CO2"]: gas.target_conc_molar() * V}
    if "Na" in sp:
        initial[sp["Na"]] = cfg["spectator_nacl_M"] * V
        initial[sp["Cl"]] = cfg["spectator_nacl_M"] * V
    return _Assembled(world, sp, {"cell": initial}, gas, tuple(rxns), tuple(rows[k] for k in order), A, rho,
                      tuple(sorted(sub)))


# ------------------------------------------------------------------------------------------------ residuals
def _activity_state(conc: dict, A: float) -> tuple:
    ionic = 0.5 * sum(max(c, 0.0) * s.charge ** 2 for s, c in conc.items() if s.charge)
    s = math.sqrt(ionic)
    log_g1 = -A * (s / (1.0 + s) - 0.3 * ionic)
    act = {sp: 10.0 ** (log_g1 * sp.charge ** 2) * max(c, 0.0) for sp, c in conc.items()}
    return ionic, act, log_g1


def equilibrium_residuals(asm: _Assembled, amounts: dict) -> dict:
    """|Omega - 1|, |c_CO2/c_sat - 1| and |Q/K - 1| per reaction, recomputed here from the final state."""
    conc = {s: amounts[s] / VOLUME_L for s in amounts if s.phase is not Phase.PURE_LIQUID and s.phase is not Phase.SOLID}
    ionic, act, _ = _activity_state(conc, asm.davies_A.value)
    out = {}
    for r in asm.rxns:
        law = r.rate_law
        K = law.ksp.value if isinstance(law, ActivitySolubilityRate) else law.K.value
        unit = getattr(law, "unit_activity", ())
        num = den = 1.0
        for s, nu in r.stoich:
            if s.phase in (Phase.SOLID, Phase.PURE_LIQUID) or s in unit:
                continue
            if nu > 0:
                num *= act[s] ** nu
            else:
                den *= act[s] ** (-nu)
        out[r.name] = abs(num / den / K - 1.0)
    out["CO2(aq)/c_sat"] = abs(conc[asm.sp["CO2"]] / asm.gas.target_conc_molar() - 1.0)
    return out


# ------------------------------------------------------------------------------------------------ identity
_MODEL_MODULE = "experiments.sandbox_foundation.open_calcite_xxv"
_PREFIX = "experiments.sandbox_foundation"


def _module_path(modname: str) -> Path:
    spec = importlib.util.find_spec(modname)
    if spec is None or spec.origin is None:
        raise OpenCalciteError(f"cannot locate in-tree module {modname}")
    return Path(spec.origin)


def code_closure(root: str = _MODEL_MODULE) -> dict:
    """{module: sha256(file bytes)} for ``root`` and every in-tree module it imports, transitively (AST scan of ALL
    import statements, including function-level ones)."""
    seen, todo = {}, [root]
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        path = _module_path(m)
        data = path.read_bytes()
        seen[m] = hashlib.sha256(data).hexdigest()
        for node in ast.walk(ast.parse(data)):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for n in names:
                if not n.startswith(_PREFIX + "."):
                    continue
                try:
                    spec = importlib.util.find_spec(n)
                except (ImportError, ValueError):
                    spec = None                       # "module.attribute": not a module, nothing to follow
                if spec is not None and spec.origin and spec.origin.endswith(".py"):
                    todo.append(n)
    return dict(sorted(seen.items()))


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=repr)


def model_identity_digest(*, include_ion_pairs=True, spectator_nacl_M=0.0, kLa_per_s=KLA_DEFAULT_PER_S,
                          k_diss=K_DISS_DEFAULT, kf=KF_DEFAULT) -> str:
    """sha256 over (model name/version, the code closure, every temperature law's full descriptor, and every structural
    and numerical parameter).  The STATE (T_K, pCO2, logKc_shift) is not in it: it is the model a preregistration pins;
    each result's run_identity_digest binds this digest to its state."""
    return model_identity_digest_for_code(code_closure(), include_ion_pairs=include_ion_pairs,
                                          spectator_nacl_M=spectator_nacl_M, kLa_per_s=kLa_per_s, k_diss=k_diss, kf=kf)


def model_identity_digest_for_code(code: dict, *, include_ion_pairs=True, spectator_nacl_M=0.0,
                                   kLa_per_s=KLA_DEFAULT_PER_S, k_diss=K_DISS_DEFAULT, kf=KF_DEFAULT) -> str:
    """The digest of ``model_identity_digest`` over a GIVEN code closure ({module: sha256}).  A caller that has read
    the closure bytes once (to bind them to the running code) digests exactly those bytes, not a second disk read."""
    if not isinstance(code, dict) or set(code) != set(code_closure()):
        raise OpenCalciteError("code must be {module: sha256} over exactly the model's code closure")
    cfg = _config(include_ion_pairs=include_ion_pairs, spectator_nacl_M=spectator_nacl_M, kLa_per_s=kLa_per_s,
                  k_diss=k_diss, kf=kf)
    laws = [PB82_LOG_KC, PB82_K1, PB82_K2, PB82_KH_CO2, PHREEQC_DAT_KW] + (
        [PB82_CACO3, PB82_CAHCO3] if cfg["include_ion_pairs"] else [])
    payload = {"model": MODEL_NAME, "version": MODEL_VERSION, "code": dict(sorted(code.items())),
               "laws": [repr(law.descriptor()) for law in laws], "config": cfg}
    return hashlib.sha256(_canon(payload).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ the run
@dataclass(frozen=True)
class OpenCalciteResult:
    T_K: float
    pCO2_atm: float
    logKc_shift: float
    Ca_total_M: float
    DIC_M: float
    pH_activity: float               # -log10(gamma_H [H+] / 1 mol/L), molar basis
    Ca_total_molal_equiv: float      # Ca_total_M / rho_w(T)  (dilute-limit identity used for the constants)
    DIC_molal_equiv: float
    pH_molal_equiv: float            # pH_activity + log10(rho_w(T))
    ionic_strength_M: float
    species_M: dict
    receipt: dict
    trajectory: object = field(default=None, compare=False, repr=False)


def _summarise(asm: _Assembled, amounts: dict) -> dict:
    sp = asm.sp
    conc = {s: amounts[s] / VOLUME_L for s in amounts if s.phase is Phase.AQUEOUS}
    ionic, act, log_g1 = _activity_state(conc, asm.davies_A.value)
    g = lambda k: conc.get(sp[k], 0.0) if k in sp else 0.0  # noqa: E731
    ca = g("Ca") + g("CaHCO3") + g("CaCO3aq")
    dic = g("CO2") + g("HCO3") + g("CO3") + g("CaHCO3") + g("CaCO3aq")
    pH = -math.log10(act[sp["H"]])
    return {"Ca_total_M": ca, "DIC_M": dic, "pH_activity": pH, "I_M": ionic,
            "species_M": {s.name: c for s, c in conc.items()}}


def build_open_calcite_world(T_K, pCO2_atm, *, logKc_shift=0.0, include_ion_pairs=True, spectator_nacl_M=0.0,
                             kLa_per_s=KLA_DEFAULT_PER_S, k_diss=K_DISS_DEFAULT, kf=KF_DEFAULT,
                             substitute=None) -> OpenCalciteResult:
    """Assemble the open world at (T_K, pCO2_atm), integrate it to a CERTIFIED steady state, and return the composition
    with a receipt naming every constant (tier, T_K, basis), the activity model, the ledger and the identity digests.
    ``substitute``: see ``assemble_open_calcite_world`` (mutation controls only; marks the run MUTATED)."""
    asm = assemble_open_calcite_world(T_K, pCO2_atm, logKc_shift=logKc_shift, include_ion_pairs=include_ion_pairs,
                                      spectator_nacl_M=spectator_nacl_M, kLa_per_s=kLa_per_s, k_diss=k_diss, kf=kf,
                                      substitute=substitute)
    T = float(T_K)
    state = asm.initial
    chunks, residuals, traj = [], None, None
    for i in range(MAX_CHUNKS):
        verify_world_boundaries(asm.world, [asm.gas])
        traj = asm.world.integrate(state, duration=FIRST_CHUNK_S * CHUNK_GROWTH ** i, n_steps=1, scheme="monolithic",
                                   rtol=RTOL, atol=ATOL, require_certified_execution=True)
        rc = traj.receipt
        if not (rc.material_balance_closed and rc.positivity_held and rc.execution_identity_certified):
            raise OpenCalciteError(f"integration receipt refused: material_balance_closed={rc.material_balance_closed}, "
                                   f"positivity={rc.positivity_verdict}, certified={rc.execution_identity_certified}")
        final = traj.amounts["cell"][-1]
        chunks.append({"ledger": boundary_ledger(traj), "structural_tier": rc.structural_tier,
                       "admitted_tier": rc.admitted_tier, "positivity_verdict": rc.positivity_verdict,
                       "execution_identity_basis": rc.execution_identity_basis, "source_domain": rc.source_domain,
                       "bulk_electroneutrality": getattr(rc.charge_validity, "bulk_electroneutrality", None)})
        residuals = equilibrium_residuals(asm, final)
        state = {"cell": dict(final)}
        if max(residuals.values()) <= EQ_RTOL:
            break
    else:
        raise SteadyStateNotCertifiedError(f"no certified steady state after {MAX_CHUNKS} chunks; residuals {residuals}")
    s = _summarise(asm, state["cell"])
    if s["I_M"] > IONIC_STRENGTH_MAX:
        raise OpenCalciteError("steady-state ionic strength outside the declared Davies domain")
    cfg = dict(include_ion_pairs=include_ion_pairs, spectator_nacl_M=spectator_nacl_M, kLa_per_s=kLa_per_s,
               k_diss=k_diss, kf=kf)
    mid = model_identity_digest(**cfg)
    run_state = {"model_identity_digest": mid, "T_K": T, "pCO2_atm": float(pCO2_atm), "logKc_shift": float(logKc_shift)}
    if asm.substituted:
        run_state["substitute"] = {k: repr(substitute[k]) for k in asm.substituted}
    run_id = hashlib.sha256(_canon(run_state).encode()).hexdigest()
    rho = asm.rho_w.value
    receipt = {
        "model": MODEL_NAME, "version": MODEL_VERSION, "model_identity_digest": mid, "run_identity_digest": run_id,
        "state": {"T_K": T, "pCO2_atm": float(pCO2_atm), "logKc_shift": float(logKc_shift)},
        "mutated": float(logKc_shift) != 0.0 or bool(asm.substituted), "substituted_slots": list(asm.substituted),
        "config": _config(**cfg),
        "constants": list(asm.constants),
        "davies_A": {"value": asm.davies_A.value, "status": asm.davies_A.status, "T_K": asm.davies_A.T_K,
                     "source": asm.davies_A.source},
        "rho_w_kg_per_L": rho, "rho_w_T_K": asm.rho_w.T_K, "gas_boundary": {"name": asm.gas.name, "p_atm": asm.gas.p_atm,
                                                "c_sat_M": asm.gas.target_conc_molar(), "kLa_tier": asm.gas.kLa_tier,
                                                "digest": asm.gas.digest()},
        "ion_pairs": {"included": bool(include_ion_pairs), "CaOH+": "OMITTED (no temperature law in either database)"},
        "steady_state_certificate": {"eq_rtol": EQ_RTOL, "residuals": residuals, "chunks": len(chunks)},
        "chunks": chunks,
        "claim_level": ["NUMERICALLY_EXECUTABLE", "WITHIN_DECLARED_FORMULA_DOMAIN"],
        "kinetic_tier": ASSUMED_PARAMETER,
        "not_claimed": "agreement with nature; COMPARED_TO_REFERENCE_IMPLEMENTATION lives in the verification harness",
    }
    return OpenCalciteResult(
        T_K=T, pCO2_atm=float(pCO2_atm), logKc_shift=float(logKc_shift), Ca_total_M=s["Ca_total_M"], DIC_M=s["DIC_M"],
        pH_activity=s["pH_activity"], Ca_total_molal_equiv=s["Ca_total_M"] / rho, DIC_molal_equiv=s["DIC_M"] / rho,
        pH_molal_equiv=s["pH_activity"] + math.log10(rho), ionic_strength_M=s["I_M"], species_M=s["species_M"],
        receipt=receipt, trajectory=traj)
