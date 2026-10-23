"""Wave B follow-up -- admission is enforced on the DIAGNOSTIC / analysis rate paths, not just reaction_cell.

The break: an admitted mechanism advertises label SOURCE_VERIFIED, but Mechanism.rate_vector / source_density and
lyapunov's reaction helpers used to hand back numbers out of the admitted window or from a retracted source.
SYNTHETIC / experimental sandbox."""
import json

import numpy as np
import pytest

from experiments.sandbox_foundation import lyapunov as ly
from experiments.sandbox_foundation.fixtures import isomer_mechanism, single_cell_system
from experiments.sandbox_foundation.mechanism_types import (
    AdmissionDomainError, AdmissionPolicy, SourceStore)
from experiments.sandbox_foundation.tests.test_mechanism_types import _iso_ex, write_source
from experiments.sandbox_foundation.twocell import State

C = np.array([1.0, 2.0])
C_STAR = np.array([1.0, 2.0])          # k_f*1 = 2e-3 = k_r*2 -> detailed balanced for the sourced iso law


def _admitted(tmp_path, version="1"):
    st = SourceStore(tmp_path)
    pol = AdmissionPolicy((st,))
    p = write_source(tmp_path, version=version)                        # window 280-320 K
    return _iso_ex(st.law_from_source("iso", version, "iso")).to_twocell(pol), p


def _state(mech, T):
    sysm = single_cell_system(mech)
    return sysm, State.make(sysm, np.array([[1.0, 2.0], [2.0, 1.0]]), [T, T])


def _every_read(mech, T):
    """Each prediction-grade numeric read of the mechanism, at temperature T."""
    sysm, st = _state(mech, T)
    return {
        "rate_vector": lambda: mech.rate_vector(C, T_K=T),
        "source_density": lambda: mech.source_density(C, T_K=T),
        "reaction_dissipation_rate": lambda: ly.reaction_dissipation_rate(sysm, st, C_STAR),
        "dPhi_dt_chain_rule": lambda: ly.dPhi_dt_chain_rule(sysm, st, C_STAR),
        "total_dissipation_rate": lambda: ly.total_dissipation_rate(sysm, st, C_STAR),
        "is_detailed_balance_equilibrium": lambda: ly.is_detailed_balance_equilibrium(sysm, C_STAR, T_K=T),
    }


NAMES = ["rate_vector", "source_density", "reaction_dissipation_rate", "dPhi_dt_chain_rule",
         "total_dissipation_rate", "is_detailed_balance_equilibrium"]


@pytest.mark.parametrize("name", NAMES)
def test_in_window_admitted_read_still_computes(tmp_path, name):          # positive control: gate is not a blanket refuse
    mech, _ = _admitted(tmp_path)
    assert mech.label == "SOURCE_VERIFIED"
    _every_read(mech, 300.0)[name]()


@pytest.mark.parametrize("name", NAMES)
def test_out_of_window_admitted_read_refuses(tmp_path, name):             # (1) 500 K vs 280-320 K, like reaction_cell
    mech, _ = _admitted(tmp_path)
    with pytest.raises(AdmissionDomainError):
        _every_read(mech, 500.0)[name]()


def test_windowed_admitted_bare_read_with_no_temperature_refuses(tmp_path):
    mech, _ = _admitted(tmp_path)
    with pytest.raises(AdmissionDomainError):
        mech.rate_vector(C)
    with pytest.raises(AdmissionDomainError):
        mech.source_density(C)


@pytest.mark.parametrize("name", NAMES)
def test_retracted_source_read_refuses_even_in_window(tmp_path, name):    # (2) retraction needs no T: in-window 300 K
    mech, p = _admitted(tmp_path)
    reads = _every_read(mech, 300.0)
    art = json.loads(p.read_text())
    art["status"] = "retracted"
    p.write_text(json.dumps(art))
    with pytest.raises(AdmissionDomainError):
        reads[name]()


def test_plain_mechanism_diagnostics_are_unchanged():                     # (3) polarity guard: no Applicability -> no gate
    mech = isomer_mechanism()
    assert mech.applicability is None
    np.testing.assert_allclose(mech.rate_vector(C), [1.5 * 1.0 - 0.5 * 2.0])
    np.testing.assert_allclose(mech.rate_vector(C, T_K=9999.0), mech.rate_vector(C))      # T ignored, no window
    np.testing.assert_allclose(mech.source_density(C), mech.N @ mech.rate_vector(C))
    sysm, st = _state(mech, 500.0)
    c_star = np.array([1.0, 3.0])                                          # 1.5*1 == 0.5*3
    assert ly.is_detailed_balance_equilibrium(sysm, c_star)
    assert ly.reaction_dissipation_rate(sysm, st, c_star) <= 0.0
    assert np.isfinite(ly.dPhi_dt_chain_rule(sysm, st, c_star))
    assert np.isfinite(ly.total_dissipation_rate(sysm, st, c_star))
