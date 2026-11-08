"""OPERATION XXV Phase III-B -- the open calcite + water + CO2(g) world (open_calcite_xxv.py).

Every state evaluated here lies OUTSIDE the reserved holdout region (T in [288.15, 303.15] K AND pCO2 in [1e-4, 1e-2]
atm); ``_state`` asserts it before any evaluation.

PASS = (1) every constant is stamped with the world temperature and named in the receipt with its tier and basis;
(2) refusal outside 273.15-363.15 K and above 1 atm pCO2, and the kernel refuses an off-temperature world; (3) a
certified steady state whose ledger closes with the boundary term; (4) independent of kLa and k_diss; (5) dCa/dpCO2 > 0
and dCa/dT < 0 on the allowed grid; (6) logKc_shift = +0.30 raises Ca by ~10^0.1 (cube-root law); (7) the identity
digest binds code + parameters; (8) live PHREEQC agreement (model-vs-model), skipped where phreeqpython is absent.
"""
from __future__ import annotations

import functools
import math

import pytest

from experiments.sandbox_foundation import open_calcite_xxv as OC
from experiments.sandbox_foundation.benchmarks.open_calcite_xxv import run_open_calcite_xxv as HV
from experiments.sandbox_foundation.gas_boundary_xxv import GasBoundaryTemperatureError, build_open_world
from experiments.sandbox_foundation.general_coupled import CoupledSourceDomainError, CoupledWorld
from experiments.sandbox_foundation.general_kernel import SourceDomainError
from experiments.sandbox_foundation.temperature_law_xxv import TemperatureLawDomainError


def _state(T, p):
    assert not HV.in_reserved_box(T, p), "test state inside the reserved holdout region"
    return T, p


@functools.lru_cache(maxsize=None)
def _run(T, p, **kw):
    return OC.build_open_calcite_world(*_state(T, p), **kw)


def test_reserved_box_guard_refuses_without_evaluating():
    for T, p in ((288.15, 1e-4), (298.15, 10 ** -3.4), (303.15, 1e-2)):
        assert HV.in_reserved_box(T, p)
        with pytest.raises(HV.ReservedRegionError):
            HV.assert_outside_reserved_box(T, p)
    for T, p in HV.allowed_grid():
        assert not HV.in_reserved_box(T, p)


def test_assembled_constants_are_stamped_and_named():
    asm = OC.assemble_open_calcite_world(*_state(313.15, 0.1))
    for r in asm.rxns:
        k = getattr(r.rate_law, "ksp", None) or r.rate_law.K
        assert k.T_K == 313.15 and "transported from molal" in k.units
        assert r.rate_law.davies_A == asm.davies_A.value
    names = {row["name"] for row in asm.constants}
    assert names == {"Kc_calcite", "K HCO3- formation", "K CO2(aq) formation", "K water formation",
                     "K CaCO3(aq) pair", "K CaHCO3+ pair", "KH_CO2"}
    assert all(row["T_K"] == 313.15 and row["tier"] and row["law_digest"] for row in asm.constants)
    no_pairs = OC.assemble_open_calcite_world(313.15, 0.1, include_ion_pairs=False)
    assert {row["name"] for row in no_pairs.constants} == names - {"K CaCO3(aq) pair", "K CaHCO3+ pair"}


def test_domain_refusals():
    for T in (273.14, 363.16):
        with pytest.raises(TemperatureLawDomainError):
            OC.assemble_open_calcite_world(T, 0.1)
    for p in (0.0, 1.5, math.nan):
        with pytest.raises(OC.OpenCalciteError):
            OC.assemble_open_calcite_world(313.15, p)


def test_kernel_refuses_the_world_at_another_temperature():
    asm = OC.assemble_open_calcite_world(*_state(313.15, 0.1))
    with pytest.raises(GasBoundaryTemperatureError):
        build_open_world(asm.world.compartments, [asm.gas], 333.15)
    off = CoupledWorld(asm.world.compartments, [], [asm.gas.external_boundary(313.15)], temperature_K=333.15)
    with pytest.raises(CoupledSourceDomainError):
        off.integrate(asm.initial, duration=1.0, n_steps=1, scheme="monolithic")
    assert issubclass(CoupledSourceDomainError, SourceDomainError)


def test_certified_steady_state_and_closed_ledger():
    r = _run(313.15, 0.1)
    rc = r.receipt
    assert max(rc["steady_state_certificate"]["residuals"].values()) <= OC.EQ_RTOL
    for ch in rc["chunks"]:
        assert ch["ledger"]["material_balance_closed"] is True
        assert ch["structural_tier"] == "STRUCTURALLY_CONSERVING"
        assert ch["execution_identity_basis"] == "AUDITED_BUILTIN"
        assert ch["source_domain"].startswith("SUPPORTED")
    flux_C = sum(ch["ledger"]["external_flux_mol"]["C"] for ch in rc["chunks"])
    sp = r.species_M
    co2_initial = rc["gas_boundary"]["c_sat_M"]
    # carbon from the gas = DIC - CO2 present initially - carbon from dissolved calcite (= Ca total)
    assert flux_C == pytest.approx(r.DIC_M - co2_initial - r.Ca_total_M, rel=1e-6, abs=1e-12)
    assert sp["CO2(aq)"] == pytest.approx(co2_initial, rel=1e-7)
    assert rc["claim_level"] == ["NUMERICALLY_EXECUTABLE", "WITHIN_DECLARED_FORMULA_DOMAIN"]
    assert rc["mutated"] is False and rc["ion_pairs"]["included"] is True
    assert 0 < r.ionic_strength_M <= OC.IONIC_STRENGTH_MAX


def test_steady_state_independent_of_kinetic_scales():
    base = _run(313.15, 0.1).Ca_total_M
    for kw in ({"kLa_per_s": 0.01}, {"kLa_per_s": 0.5}, {"k_diss": 1e-5}):
        assert _run(313.15, 0.1, **kw).Ca_total_M == pytest.approx(base, rel=1e-6), kw


def test_monotone_in_pCO2_and_T_on_the_allowed_grid():
    ps = (10 ** -3.5, 1e-2, 0.1)
    ca_p = [_run(333.15, p).Ca_total_M for p in ps]
    assert all(b > a for a, b in zip(ca_p, ca_p[1:]))
    ts = (278.15, 313.15, 333.15)
    ca_t = [_run(T, 0.1).Ca_total_M for T in ts]
    assert all(b < a for a, b in zip(ca_t, ca_t[1:]))


def test_mutated_logKc_raises_Ca_by_about_the_cube_root():
    base = _run(313.15, 0.1)
    mut = _run(313.15, 0.1, logKc_shift=0.30)
    ratio = mut.Ca_total_M / base.Ca_total_M
    assert mut.receipt["mutated"] is True
    assert any(row.get("mutated") for row in mut.receipt["constants"])
    # Ideal cube-root law: 10^(0.30/3) = 1.2589.  The model sits ABOVE it for two physical reasons, both one-signed:
    # Davies feedback (more dissolution -> higher I -> lower gamma -> more dissolution; alone: 1.2886 at this state) and
    # the ion pairs (CaCO3(aq) scales with Kc itself, CaHCO3+ with Ca*HCO3; together: 1.3010).
    assert 10 ** 0.1 < ratio < 10 ** 0.1 * 1.04
    no_pairs = _run(313.15, 0.1, include_ion_pairs=False)
    ratio_np = _run(313.15, 0.1, logKc_shift=0.30, include_ion_pairs=False).Ca_total_M / no_pairs.Ca_total_M
    assert 10 ** 0.1 < ratio_np < ratio
    assert mut.receipt["model_identity_digest"] == base.receipt["model_identity_digest"]
    assert mut.receipt["run_identity_digest"] != base.receipt["run_identity_digest"]


def test_ion_pair_switch_and_spectator_are_exposed():
    base = _run(313.15, 0.1)
    no_pairs = _run(313.15, 0.1, include_ion_pairs=False)
    salt = _run(313.15, 0.1, spectator_nacl_M=0.01)
    assert no_pairs.Ca_total_M < base.Ca_total_M                  # the pairs carry dissolved Ca
    assert salt.Ca_total_M > base.Ca_total_M                      # inert salt lowers activities -> more dissolves
    assert salt.species_M["Na+"] == pytest.approx(0.01, rel=1e-12)


def test_model_identity_digest_binds_code_and_parameters():
    d = OC.model_identity_digest()
    assert d == OC.model_identity_digest() and len(d) == 64
    assert d != OC.model_identity_digest(include_ion_pairs=False)
    assert d != OC.model_identity_digest(kLa_per_s=0.06)
    closure = OC.code_closure()
    for m in ("open_calcite_xxv", "gas_boundary_xxv", "temperature_law_xxv", "solid_equilibrium", "general_coupled",
              "general_kernel", "standard_state", "aqueous_equilibrium", "admissibility"):
        assert f"experiments.sandbox_foundation.{m}" in closure


@pytest.mark.parametrize("T, p", [(278.15, 1.0), (333.15, 10 ** -3.5)])
def test_live_phreeqc_agreement_model_vs_model(T, p):
    pytest.importorskip("phreeqpython")
    row = HV.compare_point(*_state(T, p))
    d = row["rel_diff_vs_pb82"]
    assert abs(d["Ca_total"]) < 0.02 and abs(d["DIC"]) < 0.02 and abs(d["pH_abs_diff"]) < 0.01, d
    assert abs(row["phreeqc_pb82_co2"]["si_calcite"]) < 1e-6
