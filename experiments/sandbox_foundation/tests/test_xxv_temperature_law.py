"""OPERATION XXV Phase III-B -- typed temperature laws (temperature_law_xxv.py).  Constants only: no speciation.

PASS = (1) every coefficient equals the vendored, sha-pinned database text exactly (decimal arithmetic), and the known
digit-level divergences between the two databases are surfaced, not hidden; (2) the 298.15 K values reproduce the
P&B abstract; (3) evaluation outside the domain raises a SourceDomainError; (4) a SourcedConstant produced at T is
stamped T and the existing XXIV-2A check refuses it at any other world temperature; (5) molal->molar transport is the
existing standard_state identity; (6) UNSTATED uncertainty stays UNSTATED; (7) the existing 25 C constants did not move.
"""
from __future__ import annotations

import dataclasses
import math

import pytest

from experiments.sandbox_foundation import admissibility as adm
from experiments.sandbox_foundation import temperature_law_xxv as TL
from experiments.sandbox_foundation.aqueous_equilibrium import DAVIES_A_25C, KW_25C
from experiments.sandbox_foundation.carbonate_equilibrium import K1_CARBONIC_25C, K2_CARBONIC_25C, KH_CO2_25C
from experiments.sandbox_foundation.general_kernel import Phase, Reaction, SourceDomainError, Species
from experiments.sandbox_foundation.solid_equilibrium import ActivityReversibleRate
from experiments.sandbox_foundation.standard_state import RHO_W_25C_KG_PER_L, molal_to_molar_logK


def test_every_coefficient_matches_the_pinned_database_text():
    chk = TL.database_transcription_check()
    assert set(chk) == {law.name for law in TL.ALL_LAWS}
    assert all(row["match"] for row in chk.values()), {k: v for k, v in chk.items() if not v["match"]}


def test_database_divergences_are_surfaced():
    chk = TL.database_transcription_check()
    # phreeqc.dat prints CaCO3(aq) b = -0.299440; wateq4f (and the law) -0.299444
    assert chk["log_K_CaCO3aq_PB82"]["phreeqc.dat_equals_law"] is False
    assert chk["log_K_CaCO3aq_PB82"]["phreeqc.dat"][0][1] == "-0.299440"
    # phreeqc.dat's combined CaHCO3+ law implies b = 0.31294045, not 0.31294
    assert chk["log_K_CaHCO3+_PB82"]["phreeqc.dat_implied_equals_law"] is False
    assert chk["log_K_CaHCO3+_PB82"]["phreeqc.dat_implied_pair"][1] == "0.31294045"
    # phreeqc.dat's CO2(g) is a different fit, not P&B
    assert chk["log_KH_CO2_PB82"]["phreeqc.dat_DIFFERENT_FIT"][0][0] == "10.5624"


@pytest.mark.parametrize("law, expected, tol", [
    (TL.PB82_LOG_KC, -8.480, 0.0005),        # abstract: -8.480 +/- 0.020
    (TL.PB82_CAHCO3, 1.11, 0.005),            # abstract: 1.11 +/- 0.07
    (TL.PB82_CACO3, 3.22, 0.005),             # abstract: 3.22 +/- 0.14
    (TL.PB82_K2, -10.3289, 0.0001),
    (TL.PB82_K1, -6.3519, 0.0001),
    (TL.PB82_KH_CO2, -1.4679, 0.0001),
])
def test_298_values_reproduce_the_abstract_and_database(law, expected, tol):
    assert abs(law.log10_K(298.15) - expected) <= tol


@pytest.mark.parametrize("law", TL.ALL_LAWS)
def test_out_of_domain_raises_a_source_domain_error(law):
    for T in (law.T_min_K - 0.01, law.T_max_K + 0.01, float("nan"), float("inf"), -5.0):
        with pytest.raises(SourceDomainError) as ei:
            law.log10_K(T)
        assert ei.value.verdict == "OUT_OF_SOURCE_DOMAIN"
    law.log10_K(law.T_min_K)
    law.log10_K(law.T_max_K)


def test_calcite_domain_is_0_to_90_C_and_co2_system_0_to_100_C():
    assert (TL.PB82_LOG_KC.T_min_K, TL.PB82_LOG_KC.T_max_K) == (273.15, 363.15)
    for law in (TL.PB82_KH_CO2, TL.PB82_K1, TL.PB82_K2):
        assert (law.T_min_K, law.T_max_K) == (273.15, 373.15)
        assert law.domain_basis == TL.DOMAIN_STATED_BY_SOURCE
    for law in (TL.PB82_CAHCO3, TL.PB82_CACO3, TL.PHREEQC_DAT_KW, TL.PHREEQC_DAT_O2_HENRY):
        assert law.domain_basis == TL.DOMAIN_ASSERTED_BY_THIS_MODULE


def test_constant_is_stamped_and_refused_at_any_other_world_temperature():
    law = TL.PB82_K2.reversed("HCO3 formation", "CO3-2 + H+ = HCO3-")
    c = law.sourced_constant(295.15)
    assert c.T_K == 295.15 and c.status == "SOURCED"
    A = Phase.AQUEOUS
    co3, h, hco3 = (Species.of("CO3-2", {"C": 1, "O": 3}, -2, A), Species.of("H+", {"H": 1}, 1, A),
                    Species.of("HCO3-", {"C": 1, "H": 1, "O": 3}, -1, A))
    st = ((co3, -1), (h, -1), (hco3, 1))
    rxn = Reaction("hco3", st, ActivityReversibleRate(1.0, c, st))
    assert adm.temperature_domain_violations([("cell", rxn)], 295.15) == []
    assert adm.temperature_domain_violations([("cell", rxn)], 298.15) == [("cell", "hco3", "K", 295.15)]


def test_molar_transport_is_the_standard_state_identity():
    for law in TL.ALL_LAWS:
        T = 313.15
        got = math.log10(law.sourced_constant(T, basis="molar").value)
        want = molal_to_molar_logK(law.log10_K(T), law.nu_aq, TL.water_density_kg_per_L(T))
        assert got == pytest.approx(want, abs=1e-12)
        assert math.log10(law.sourced_constant(T, basis="molal").value) == pytest.approx(law.log10_K(T), abs=1e-12)


def test_unstated_uncertainty_stays_unstated():
    for law in (TL.PB82_KH_CO2, TL.PB82_K1, TL.PB82_K2, TL.PHREEQC_DAT_KW, TL.PHREEQC_DAT_O2_HENRY):
        assert law.uncertainty_status == TL.UNSTATED
        u, kind = law.uncertainty_log10(310.0)
        assert kind == TL.TRANSCRIPTION_FLOOR_ONLY and 0 < u < 1e-2
        note = law.sourced_constant(310.0).note
        assert "UNSTATED" in note and "FLOOR" in note and "NOT a measurement uncertainty" in note
    assert TL.PB82_LOG_KC.uncertainty_log10(310.0) == (0.020, TL.STATED)
    assert TL.PB82_CAHCO3.stated_uncertainty_log10 == 0.07 and TL.PB82_CACO3.stated_uncertainty_log10 == 0.14


def test_reversal_is_exact_and_involutive():
    r = TL.PB82_K1.reversed("x", "y")
    assert r.coefficient_values == tuple(-v for v in TL.PB82_K1.coefficient_values)
    assert r.nu_aq == -TL.PB82_K1.nu_aq
    assert r.reversed("z", "w").coefficient_values == TL.PB82_K1.coefficient_values
    assert r.log10_K(300.0) == pytest.approx(-TL.PB82_K1.log10_K(300.0), abs=1e-12)


def test_law_is_immutable_and_validated():
    with pytest.raises(dataclasses.FrozenInstanceError):
        TL.PB82_LOG_KC.T_max_K = 400.0
    good = dict((f.name, getattr(TL.PB82_LOG_KC, f.name)) for f in dataclasses.fields(TL.PB82_LOG_KC))
    for bad in ({"coefficients": (1.0, 0, 0, 0, 0, 0)}, {"coefficients": ("x",) * 6}, {"tier": "VIBES"},
                {"T_min_K": 400.0}, {"stated_uncertainty_log10": 0.0}, {"basis": "molar"},
                {"domain_basis": "TRUST_ME"}, {"source": " "}):
        with pytest.raises(ValueError):
            TL.AnalyticTemperatureLaw(**{**good, **bad})


def test_existing_25C_constants_did_not_move():
    # the existing 25 C worlds keep their own constants; nothing was swapped to P&B
    assert K1_CARBONIC_25C.value == 10 ** (-6.35) and K2_CARBONIC_25C.value == 10 ** (-10.33)
    assert KH_CO2_25C.value == 0.0344 and KW_25C.value == 1.0e-14 and DAVIES_A_25C.value == 0.509


def _log_band(c):
    return c.uncertainty / (c.value * math.log(10.0))


def test_reconciliation_with_existing_25C_constants():
    """The 298.15 K law values against the existing 25 C records, judged by each record's OWN error bar."""
    T = 298.15
    for law, old in ((TL.PB82_K1, K1_CARBONIC_25C), (TL.PB82_K2, K2_CARBONIC_25C)):
        assert abs(law.log10_K(T) - math.log10(old.value)) <= _log_band(old), law.name
    kh_molar = TL.PB82_KH_CO2.sourced_constant(T, basis="molar").value
    assert abs(kh_molar - KH_CO2_25C.value) <= KH_CO2_25C.uncertainty
    # RECORDED DISCREPANCY: phreeqc.dat's pKw(25 C) = 13.9948 lies 0.0052 outside KW_25C's band (1.0e-14 +/- 1e-16 is
    # +/-0.0043 in log10), although KW_25C's own note cites the high-precision pKw ~ 13.995.  Not swapped, not hidden.
    d_kw = abs(TL.PHREEQC_DAT_KW.log10_K(T) - math.log10(KW_25C.value))
    assert _log_band(KW_25C) < d_kw < 0.006
    assert abs(-TL.PHREEQC_DAT_KW.log10_K(T) - 13.995) < 0.0005


def test_water_properties():
    assert TL.water_density_kg_per_L(298.15) == pytest.approx(RHO_W_25C_KG_PER_L, abs=3e-6)
    assert TL.davies_A(298.15).value == DAVIES_A_25C.value               # anchored: 25 C worlds unchanged
    a = [TL.davies_A(T).value for T in (273.15, 298.15, 333.15, 373.15)]
    assert a == sorted(a)
    assert TL.davies_A(333.15).T_K == 333.15 and TL.davies_A(333.15).status == "DERIVED"
    for f in (TL.water_density_kg_per_L, TL.davies_A):
        with pytest.raises(SourceDomainError):
            f(272.0)


def test_water_density_is_a_temperature_tagged_value():
    # XXV runner review finding 3: rho_w used to travel as a bare float no temperature check could see
    for T in (273.15, 298.15, 313.15, 363.15):
        rho = TL.water_density(T)
        assert type(rho).__name__ == "SourcedConstant" and rho.T_K == T and rho.status == "DERIVED"
        assert rho.value == TL.water_density_kg_per_L(T)
        assert 0 < rho.uncertainty < 1e-5 and "FLOOR only" in rho.note       # a resolution floor, labelled as one
    with pytest.raises(SourceDomainError):
        TL.water_density(424.0)
