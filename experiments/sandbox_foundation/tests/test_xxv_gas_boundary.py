"""OPERATION XXV Phase III-B -- the generic gas-liquid (Henry) boundary (gas_boundary_xxv.py).

PASS = (1) the operator's source names no substance; (2) the SAME operator drives two different gases (CO2 with the
P&B law, O2 with the phreeqc.dat law) and a third, single-temperature record (the existing 25 C KH_CO2_25C, molar
basis); (3) each reaches c = K_H(T) p (molal law transported to molar with rho_w(T)); (4) the material balance closes
WITH the boundary term; (5) the steady state is independent of kLa; (6) a constant produced for T is refused at any
other world temperature, and a tampered installed boundary is detected.
"""
from __future__ import annotations

import inspect
import math
import re

import pytest

from experiments.sandbox_foundation import gas_boundary_xxv as GB
from experiments.sandbox_foundation.carbonate_equilibrium import KH_CO2_25C
from experiments.sandbox_foundation.general_coupled import Compartment, CoupledWorld, ExternalBoundary
from experiments.sandbox_foundation.general_kernel import ChemicalSystem, Phase, SourceDomainError, Species
from experiments.sandbox_foundation.standard_state import molal_to_molar_logK
from experiments.sandbox_foundation.temperature_law_xxv import (
    PB82_KH_CO2,
    PHREEQC_DAT_O2_HENRY,
    water_density_kg_per_L,
)

CO2aq = Species.of("CO2(aq)", {"C": 1, "O": 2}, 0, Phase.AQUEOUS)
O2aq = Species.of("O2(aq)", {"O": 2}, 0, Phase.AQUEOUS)
T_TEST = 313.15


def test_operator_source_names_no_substance():
    src = inspect.getsource(GB)
    pattern = (r"\b(CO2|O2|N2|H2|NH3|CH4|H2S|Ca|Na|Cl|HCO3|CO3|calcite|carbon|oxygen|nitrogen|ammonia|"
               r"carbonate|bicarbonate|methane)\b")
    assert re.findall(pattern, src, flags=re.IGNORECASE) == []


def _run(gb, T, *, duration=4000.0, c0=0.0):
    world = GB.build_open_world([Compartment("aq", ChemicalSystem([gb.dissolved], [], gb.volume_L))], [gb], T)
    GB.verify_world_boundaries(world, [gb])
    tr = world.integrate({"aq": {gb.dissolved: c0 * gb.volume_L}}, duration=duration, n_steps=20,
                         scheme="monolithic", rtol=1e-11, atol=1e-16)
    return tr, tr.amounts["aq"][-1][gb.dissolved] / gb.volume_L


@pytest.mark.parametrize("law, sp, p", [(PB82_KH_CO2, CO2aq, 0.1), (PHREEQC_DAT_O2_HENRY, O2aq, 0.21)])
def test_same_operator_two_gases_reach_henry_and_close_the_ledger(law, sp, p):
    gb = GB.GasLiquidBoundary.from_law(law, T_TEST, name="reservoir", compartment="aq", dissolved=sp, p_atm=p,
                                       kLa_per_s=0.05, volume_L=2.0)
    want = 10.0 ** molal_to_molar_logK(law.log10_K(T_TEST), 1, water_density_kg_per_L(T_TEST)) * p
    assert gb.target_conc_molar() == pytest.approx(want, rel=1e-12)
    tr, c = _run(gb, T_TEST)
    assert c == pytest.approx(want, rel=1e-8)
    led = GB.boundary_ledger(tr)
    assert led["material_balance_closed"] is True
    supplied = c * gb.volume_L
    for el, n in sp.composition:
        assert led["external_flux_mol"][el] == pytest.approx(n * supplied, rel=1e-8)
        assert led["raw_material_change_mol"][el] == pytest.approx(led["external_flux_mol"][el], rel=1e-8)


def test_steady_state_is_independent_of_kLa():
    out = []
    for kla in (0.01, 0.5):
        gb = GB.GasLiquidBoundary.from_law(PB82_KH_CO2, T_TEST, name="r", compartment="aq", dissolved=CO2aq,
                                           p_atm=0.3, kLa_per_s=kla, volume_L=1.0)
        out.append(_run(gb, T_TEST, duration=6000.0, c0=0.05)[1])      # starts SUPERsaturated: degasses
    assert out[0] == pytest.approx(out[1], rel=1e-8)
    assert out[0] == pytest.approx(gb.target_conc_molar(), rel=1e-8)


def test_off_temperature_world_is_refused():
    gb = GB.GasLiquidBoundary.from_law(PB82_KH_CO2, T_TEST, name="r", compartment="aq", dissolved=CO2aq, p_atm=0.1,
                                       kLa_per_s=0.05, volume_L=1.0)
    comp = [Compartment("aq", ChemicalSystem([CO2aq], [], 1.0))]
    assert GB.boundary_temperature_violations([gb], T_TEST) == []
    assert GB.boundary_temperature_violations([gb], 298.15) == [("r", "henry", T_TEST)]
    with pytest.raises(SourceDomainError):
        GB.build_open_world(comp, [gb], 298.15)
    with pytest.raises(GB.GasBoundaryTemperatureError):
        gb.external_boundary(T_TEST + 0.02)
    gb.external_boundary(T_TEST + 0.009)                       # inside the shared 0.01 K tolerance


def test_single_temperature_record_through_the_same_operator():
    # the existing 25 C Sander record (molar basis): admitted at 298.15 K, refused anywhere else
    gb = GB.GasLiquidBoundary("r", "aq", CO2aq, KH_CO2_25C, "molar", 0.1, 0.05, 1.0)
    assert gb.target_conc_molar() == pytest.approx(0.0344 * 0.1, rel=1e-15)
    _, c = _run(gb, 298.15)
    assert c == pytest.approx(0.00344, rel=1e-8)
    with pytest.raises(SourceDomainError):
        GB.build_open_world([Compartment("aq", ChemicalSystem([CO2aq], [], 1.0))], [gb], T_TEST)
    with pytest.raises(GB.GasBoundaryError):
        GB.GasLiquidBoundary("r", "aq", CO2aq, KH_CO2_25C, "molal", 0.1, 0.05, 1.0)   # basis contradicts units


def test_tampered_installed_boundary_is_detected():
    gb = GB.GasLiquidBoundary.from_law(PB82_KH_CO2, T_TEST, name="r", compartment="aq", dissolved=CO2aq, p_atm=0.1,
                                       kLa_per_s=0.05, volume_L=1.0)
    forged = ExternalBoundary("r", "aq", CO2aq, mode="fixed_activity", k_transfer=0.05,
                              target_conc=gb.target_conc_molar() * 1.01)
    world = CoupledWorld([Compartment("aq", ChemicalSystem([CO2aq], [], 1.0))], [], [forged], temperature_K=T_TEST)
    with pytest.raises(GB.GasBoundaryError):
        GB.verify_world_boundaries(world, [gb])


def test_declaration_is_validated():
    ion = Species.of("X+", {"X": 1}, 1, Phase.AQUEOUS)
    gas = Species.of("X(g)", {"X": 1}, 0, Phase.GAS)
    h = PB82_KH_CO2.sourced_constant(T_TEST, basis="molal")
    for sp in (ion, gas):
        with pytest.raises(GB.GasBoundaryError):
            GB.GasLiquidBoundary("r", "aq", sp, h, "molal", 0.1, 0.05, 1.0)
    for p, kla in ((-0.1, 0.05), (math.nan, 0.05), (0.1, 0.0)):
        with pytest.raises(GB.GasBoundaryError):
            GB.GasLiquidBoundary("r", "aq", CO2aq, h, "molal", p, kla, 1.0)
    with pytest.raises(GB.GasBoundaryError):
        GB.GasLiquidBoundary.from_law(PB82_KH_CO2.reversed("x", "y"), T_TEST, name="r", compartment="aq",
                                      dissolved=CO2aq, p_atm=0.1, kLa_per_s=0.05, volume_L=1.0)
    assert GB.GasLiquidBoundary("r", "aq", CO2aq, h, "molal", 0.1, 0.05, 1.0).kLa_tier == "ASSUMED_PARAMETER"
