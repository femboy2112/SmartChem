"""Wave E -- red/green tests for the passive-interface contract (mesh.py) and the minimal valve/membrane apparatus
(interface.py).  Ooh yeah, can do!  SYNTHETIC / idealized / isothermal throughout; a finite numerical check is NOT
a universal proof.

Every derived formula is checked against an INDEPENDENT hand value or an independent code path (the Lyapunov
diffusion rate from lyapunov.py), and each red-team surface (#12, #13, #14) has a test that a planted mutation --
a flipped sign, a dropped log-mean, a negative L, a leak across a shut wall, a smuggled ion -- would turn RED."""
import math

import numpy as np
import pytest

from experiments.sandbox_foundation import lyapunov
from experiments.sandbox_foundation.interface import (
    Apparatus, ChargedTransportNotAdmitted, Tracer, three_chamber_membrane, transport, two_chamber_valve)
from experiments.sandbox_foundation.mesh import (
    Face, Mesh, R_GAS, assert_passive, chain_mesh, face_dissipation, face_fick_flux, face_log_mean_concentration,
    face_log_mean_mobility, face_potential_difference, mesh_diffusion_dissipation_rate, passive_interface_residual)
from experiments.sandbox_foundation.twocell import (
    InvalidParameterError, Ledger, NegativeAmountError, State, System)

T0 = 298.15  # K, the isothermal reference for every chemical-potential computation here

# a two-cell chain and a per-face conductance, used across the E1 derivation tests
VOL2 = (1.0e-6, 2.0e-6)
MESH2 = chain_mesh(VOL2, [1.0e-4], [1.0e-2])        # 1 face
G2 = np.array([[2.5e-9]])                            # (F=1, S=1) m^3/s
C2 = np.array([[5.0], [1.0]])                        # (C=2, S=1) mol/m^3 ; cell 0 (tail) richer


# ======================================================================================= E1: the derivation
def test_potential_difference_is_RT_log_ratio_derived_from_B_space():
    dmu = face_potential_difference(MESH2, C2, T0)
    # Delta(mu) = mu(head) - mu(tail) = RT ln(c_head/c_tail); head=cell1, tail=cell0
    expect = R_GAS * T0 * math.log(C2[1, 0] / C2[0, 0])
    assert dmu.shape == (1, 1)
    assert dmu[0, 0] == pytest.approx(expect, rel=1e-14)
    # it IS the B_space-weighted sum of the two potentials (ties orientation to the incidence matrix)
    ln_c = np.log(C2)
    via_B = R_GAS * T0 * (MESH2.B_space.T @ ln_c)
    np.testing.assert_allclose(dmu, via_B, rtol=1e-14, atol=0)


def test_log_mean_mobility_derivation_units_and_fick_reconstruction():
    c_lm = face_log_mean_concentration(MESH2, C2)
    hand_lm = (C2[0, 0] - C2[1, 0]) / math.log(C2[0, 0] / C2[1, 0])
    assert c_lm[0, 0] == pytest.approx(hand_lm, rel=1e-14)
    assert 1.0 < c_lm[0, 0] < 5.0                                   # log-mean lies strictly between the endpoints
    L = face_log_mean_mobility(MESH2, G2, C2, T0)
    assert L[0, 0] == pytest.approx(G2[0, 0] * hand_lm / (R_GAS * T0), rel=1e-14)
    assert L[0, 0] > 0.0                                            # positive semidefinite response
    # THE reconstruction: J = -L . Delta(mu) must reproduce the EXISTING Fick flux g(c_tail - c_head) exactly
    dmu = face_potential_difference(MESH2, C2, T0)
    J_from_law = -L * dmu
    J_fick = face_fick_flux(MESH2, G2, C2)
    np.testing.assert_allclose(J_from_law, J_fick, rtol=1e-13, atol=0)


def test_dissipation_witness_is_nonpositive_and_two_routes_agree():
    w = face_dissipation(MESH2, G2, C2, T0)
    assert np.all(w <= 0.0) and w[0, 0] < 0.0                       # a real gradient dissipates (#12)
    # route 1 (law form -L Delta(mu)^2) and route 2 (direct Delta(mu).J) agree to roundoff -> not a tautology
    assert passive_interface_residual(MESH2, G2, C2, T0) < 1e-13
    # a SIGN-FLIP mutation (J := -J, i.e. uphill transport) would make the product POSITIVE -- caught:
    dmu = face_potential_difference(MESH2, C2, T0)
    J = face_fick_flux(MESH2, G2, C2)
    assert float(dmu[0, 0] * (-J[0, 0])) > 0.0                      # the mutant's witness is +, our test rejects it


def test_limiting_case_equal_concentrations_is_finite_zero_dissipation():
    c_eq = np.array([[3.0], [3.0]])
    assert face_potential_difference(MESH2, c_eq, T0)[0, 0] == 0.0  # Delta(mu) = 0
    assert face_fick_flux(MESH2, G2, c_eq)[0, 0] == 0.0             # J = 0
    assert face_dissipation(MESH2, G2, c_eq, T0)[0, 0] == 0.0      # witness = 0, no NaN
    # c_lm -> the common value c (l'Hopital), so L stays FINITE (no false singularity)
    assert face_log_mean_concentration(MESH2, c_eq)[0, 0] == pytest.approx(3.0, rel=1e-14)
    assert np.isfinite(face_log_mean_mobility(MESH2, G2, c_eq, T0)[0, 0])


def test_limiting_case_zero_concentration_keeps_sign_no_nan():
    c_empty = np.array([[4.0], [0.0]])                             # head cell empty
    J = face_fick_flux(MESH2, G2, c_empty)
    assert np.isfinite(J[0, 0]) and J[0, 0] > 0.0                  # Fick flux stays finite (g * c_tail)
    assert face_log_mean_concentration(MESH2, c_empty)[0, 0] == pytest.approx(0.0, abs=1e-12)  # c_lm -> 0
    w = face_dissipation(MESH2, G2, c_empty, T0)
    assert not np.isnan(w[0, 0]) and w[0, 0] <= 0.0                # sign right (ideal-dilute log singularity)


def test_impermeable_face_has_zero_witness_even_with_a_gradient():
    g0 = np.array([[0.0]])                                          # a WALL
    assert face_fick_flux(MESH2, g0, C2)[0, 0] == 0.0
    assert face_dissipation(MESH2, g0, C2, T0)[0, 0] == 0.0        # masked to exactly 0, never 0*inf = NaN
    assert_passive(MESH2, g0, C2, T0)                               # a wall is trivially passive


def test_per_face_witness_reconciles_with_global_dPhi_dt_and_lyapunov():
    # mesh global diffusion dissipation (mol/s) and the per-face witness sum (W) must satisfy sum = R T * dPhi/dt
    c = C2
    global_rate = mesh_diffusion_dissipation_rate(MESH2, G2, c)    # mol/s, <= 0
    witness_sum = float(np.sum(face_dissipation(MESH2, G2, c, T0)))  # W, <= 0
    assert global_rate < 0.0 and witness_sum < 0.0
    assert witness_sum == pytest.approx(R_GAS * T0 * global_rate, rel=1e-13)
    # and the global rate itself matches lyapunov.diffusion_dissipation_rate via an INDEPENDENT 2-cell System
    sysL = System(("T",), VOL2, (100.0, 200.0), (2.5e-9 * 1.0e-2 / 1.0e-4,), 1.0e-4, 1.0e-2, 0.0)
    # system.g = D*A/d must equal our per-face g (confirm we compare the same conductance)
    assert sysL.g[0] == pytest.approx(G2[0, 0], rel=1e-14)
    stateL = State.make(sysL, c * np.asarray(VOL2)[:, None], T_K=(T0, T0))
    lyap_rate = lyapunov.diffusion_dissipation_rate(sysL, stateL)
    assert global_rate == pytest.approx(lyap_rate, rel=1e-13)
    assert witness_sum == pytest.approx(R_GAS * T0 * lyap_rate, rel=1e-13)


def test_orientation_is_a_labelling_choice_for_the_witness():
    flipped = Mesh(VOL2, (Face(1, 0, 1.0e-4, 1.0e-2),), "chain")    # same pair, reversed orientation
    w = face_dissipation(MESH2, G2, C2, T0)
    w_flip = face_dissipation(flipped, G2, C2, T0)
    # both Delta(mu) and J flip sign under relabelling; their PRODUCT (the witness) is invariant
    np.testing.assert_allclose(w, w_flip, rtol=1e-14, atol=0)
    assert face_potential_difference(flipped, C2, T0)[0, 0] == pytest.approx(
        -face_potential_difference(MESH2, C2, T0)[0, 0], rel=1e-14)


def test_assert_passive_refuses_a_fabricated_injecting_interface():
    # a NEGATIVE conductance is not physical; it would make the witness POSITIVE (free-energy injection).  The
    # constructor forbids it in the apparatus, but the raw contract guard must ALSO catch it (defence in depth).
    g_bad = np.array([[-2.5e-9]])
    with pytest.raises(InvalidParameterError):
        assert_passive(MESH2, g_bad, C2, T0)


# ======================================================================================= E2: the apparatus
def _tot(n):
    return np.asarray(n, float).sum(axis=0)


def test_neutral_apparatus_constructs_and_the_contract_holds():
    app = two_chamber_valve(species=(Tracer("T"),), conductance=[[3.0e-9]], T_K=T0)
    n0 = np.array([[6.0e-6], [1.0e-6]])                             # mol; cell 0 richer
    assert np.all(app.dissipation(n0) <= 0.0)                      # the passive-interface law holds on the apparatus


def test_impermeable_boundary_produces_no_flux():
    app = two_chamber_valve(species=(Tracer("T"),), conductance=[[0.0]], T_K=T0)   # base wall
    n0 = np.array([[6.0e-6], [1.0e-6]])
    n1 = transport(app, n0, dt=1.0)
    np.testing.assert_array_equal(n1, n0)                          # NOTHING moved


def test_open_passive_interface_transports_downhill():
    app = two_chamber_valve(species=(Tracer("T"),), conductance=[[3.0e-9]], theta=1.0, T_K=T0)
    n0 = np.array([[6.0e-6], [1.0e-6]])                            # cell 0 (tail) richer -> flux into cell 1
    dt = app.transport_dt_max() * 0.5
    led = Ledger()
    n1 = transport(app, n0, dt=dt, ledger=led)
    assert n1[0, 0] < n0[0, 0] and n1[1, 0] > n0[1, 0]            # matter went high -> low (downhill)
    assert np.all(app.dissipation(n0) < 0.0)                      # and it dissipated (#12)
    assert _tot(n1) == pytest.approx(_tot(n0), rel=0, abs=1e-18)  # conserved


def test_selectively_permeable_membrane_passes_one_blocks_the_other():
    # left membrane passes X only, right membrane passes Y only -> X and Y are routed differently
    app = three_chamber_membrane(species=(Tracer("X"), Tracer("Y")),
                                 left_pass=(True, False), right_pass=(False, True), T_K=T0)
    n0 = np.array([[5.0e-6, 5.0e-6], [1.0e-6, 1.0e-6], [1.0e-6, 1.0e-6]])
    dt = app.transport_dt_max() * 0.5
    n1 = transport(app, n0, dt=dt)
    # across face 0 (left): X moves (cell0 loses, cell1 gains), Y is walled (cell0/cell1 Y unchanged by face 0)
    assert n1[0, 0] < n0[0, 0] and n1[1, 0] > n0[1, 0]           # X diffused left->mid
    assert n1[0, 1] == pytest.approx(n0[0, 1], abs=1e-18)        # Y blocked at the left wall: cell 0 Y frozen
    assert _tot(n1) == pytest.approx(_tot(n0), rel=0, abs=1e-18)


def test_valve_opening_creates_no_matter_closing_preserves_independent_inventories():
    base = [[3.0e-9]]
    shut = two_chamber_valve(species=(Tracer("T"),), conductance=base, theta=0.0, T_K=T0)
    n0 = np.array([[6.0e-6], [1.0e-6]])
    # CLOSED valve: each chamber keeps its OWN inventory, independently (not merely the global sum)
    n_shut = transport(shut, n0, dt=1.0)
    np.testing.assert_array_equal(n_shut, n0)
    # OPEN the same valve (reversible: a NEW apparatus, same base) -> transport conserves the global total exactly
    opened = shut.set_valve(0, 1.0)
    n_open = transport(opened, n0, dt=opened.transport_dt_max() * 0.5)
    assert _tot(n_open) == pytest.approx(_tot(n0), rel=0, abs=1e-18)   # opening created no matter
    assert not np.array_equal(n_open, n0)                              # but it DID let matter flow


def test_every_internal_transfer_has_equal_and_opposite_ledger_entries():
    app = three_chamber_membrane(species=(Tracer("X"), Tracer("Y")), T_K=T0)
    n0 = np.array([[5.0e-6, 2.0e-6], [1.0e-6, 4.0e-6], [3.0e-6, 1.0e-6]])
    led, ev = Ledger(), []
    transport(app, n0, dt=app.transport_dt_max() * 0.4, ledger=led, events=ev)
    # per (face, quantity): exactly two entries on the two incident cells, summing to EXACTLY 0
    groups = {}
    for e in led.entries:
        groups.setdefault((e.note, e.quantity), []).append(e)
    assert groups                                                   # non-vacuous
    for key, evs in groups.items():
        assert len(evs) == 2
        assert math.fsum(e.amount for e in evs) == 0.0              # equal and opposite, exactly
        assert sorted(e.cell for e in evs) != [0, 0]               # two DISTINCT cells
    # only INTERFACE entries: no reaction sources, no external work drawn
    assert {e.kind for e in led.entries} == {"INTERFACE"}


def test_passive_transport_adds_no_reaction_and_no_external_energy():
    app = two_chamber_valve(species=(Tracer("T"),), conductance=[[3.0e-9]], T_K=T0)
    led = Ledger()
    transport(app, np.array([[6.0e-6], [1.0e-6]]), dt=app.transport_dt_max() * 0.5, ledger=led)
    assert all(e.kind == "INTERFACE" and e.operator == "interface" for e in led.entries)
    assert all(e.unit == "mol" for e in led.entries)               # matter only -- no energy/work ledger entries


def test_isolated_compartments_are_a_legitimate_disconnected_transport_case():
    # 4 cells, 3 faces; shut the MIDDLE valve -> two transport-isolated groups {0,1} and {2,3}, each conserved
    mesh = chain_mesh((1.0e-6,) * 4, [1.0e-4] * 3, [1.0e-2] * 3)
    base = np.full((3, 1), 3.0e-9)
    app = Apparatus((Tracer("T"),), mesh, base, valves=(1.0, 0.0, 1.0), T_K=T0)
    n0 = np.array([[6.0e-6], [1.0e-6], [5.0e-6], [2.0e-6]])
    n1 = transport(app, n0, dt=app.transport_dt_max() * 0.5)
    left0, right0 = n0[0:2].sum(), n0[2:4].sum()
    left1, right1 = n1[0:2].sum(), n1[2:4].sum()
    assert left1 == pytest.approx(left0, abs=1e-18)                # group {0,1} inventory independently conserved
    assert right1 == pytest.approx(right0, abs=1e-18)              # group {2,3} inventory independently conserved
    assert n1[0, 0] != n0[0, 0] and n1[2, 0] != n0[2, 0]          # transport DID happen WITHIN each group


def test_overlarge_apparatus_step_is_refused_not_clamped():
    app = two_chamber_valve(species=(Tracer("T"),), conductance=[[3.0e-9]], T_K=T0)
    with pytest.raises(Exception):                                  # over the positivity bound -> typed refusal
        transport(app, np.array([[6.0e-6], [1.0e-6]]), dt=app.transport_dt_max() * 1.01)


# ======================================================================================= E3: charged-species guard
def test_charged_species_is_refused_fail_closed():
    with pytest.raises(ChargedTransportNotAdmitted):               # red-team #14: no silent fake electrolyte
        Apparatus((Tracer("Na+", charge=+1), Tracer("Ac-", charge=-1)),
                  MESH2, np.array([[1.0e-9], [1.0e-9]]).reshape(1, 2), T_K=T0)
    with pytest.raises(ChargedTransportNotAdmitted):               # even a single cation is refused
        two_chamber_valve(species=(Tracer("H+", charge=+1),), conductance=[[1.0e-9]], T_K=T0)


def test_neutral_tracers_are_admitted():
    app = two_chamber_valve(species=(Tracer("T", charge=0),), conductance=[[1.0e-9]], T_K=T0)
    assert app.g.shape == (1, 1)                                   # a neutral prototype builds fine


def test_bad_conductance_and_valve_params_are_typed_refusals():
    with pytest.raises(InvalidParameterError):
        Apparatus((Tracer("T"),), MESH2, np.array([[-1.0e-9]]), T_K=T0)        # negative conductance
    with pytest.raises(InvalidParameterError):
        Apparatus((Tracer("T"),), MESH2, np.array([[1.0e-9]]), valves=(1.5,), T_K=T0)  # valve out of [0,1]
    with pytest.raises(InvalidParameterError):
        Apparatus((Tracer("T"),), MESH2, np.array([[1.0e-9, 1.0e-9]]), T_K=T0)  # wrong species width
    with pytest.raises(NegativeAmountError):
        transport(two_chamber_valve(T_K=T0), np.array([[-1.0e-6], [1.0e-6]]), dt=1e-3)


# ================================= Secondary: thread per-cell T_K through reaction_step_mesh (Wave B handoff)
# The mesh has NO energy state (MeshState holds amounts only), so T cannot be DERIVED from U as twocell does -- it
# must be SUPPLIED.  These tests pin that an admitted-WINDOWED mechanism runs in-domain and refuses out-of-domain on
# the MESH reaction path, and that the plain (unwindowed) path is unchanged.
import dataclasses  # noqa: E402

from experiments.sandbox_foundation.fixtures import isomer_mechanism  # noqa: E402
from experiments.sandbox_foundation.mechanism_types import AdmissionDomainError, Applicability  # noqa: E402
from experiments.sandbox_foundation.mesh import (  # noqa: E402
    MeshState, MeshSystem, chain_mesh, reaction_step_mesh)


def _windowed_isomer(window=(300.0, 400.0)):
    """SYNTHETIC P<->Q with a temperature window; guarded=(None,) so no source-currency check, just the T window."""
    app = Applicability(domains=(("P<->Q", window, None),), guarded=(None,), policy=None)
    return dataclasses.replace(isomer_mechanism(), applicability=app)


def _rxn_system(mech):
    return MeshSystem(("P", "Q"), (0.0, 0.0), chain_mesh((1.0e-3, 1.0e-3), [1.0e-4], [1.0e-2]), mechanism=mech)


def test_windowed_mechanism_runs_in_domain_on_the_mesh_path():
    sysm = _rxn_system(_windowed_isomer())
    st = MeshState(np.array([[1.0, 0.0], [1.0, 0.0]]))
    s1, rep = reaction_step_mesh(sysm, st, 0.1, T_K=350.0)        # 350 K in [300, 400] -> runs in-domain
    assert np.any(s1.n != st.n)                                  # P <-> Q actually advanced
    assert np.max(np.abs(s1.n.sum(axis=1) - st.n.sum(axis=1))) < 1e-9   # isomerization conserves per-cell total


def test_windowed_mechanism_refuses_out_of_domain_and_without_temperature():
    sysm = _rxn_system(_windowed_isomer())
    st = MeshState(np.array([[1.0, 0.0], [1.0, 0.0]]))
    with pytest.raises(AdmissionDomainError):                    # 500 K outside the window -> refused on the mesh
        reaction_step_mesh(sysm, st, 0.1, T_K=500.0)
    with pytest.raises(AdmissionDomainError):                    # NO temperature + windowed law -> fail closed
        reaction_step_mesh(sysm, st, 0.1)
    # per-cell temperatures: one in-window, one out -> the out-of-window cell refuses
    with pytest.raises(AdmissionDomainError):
        reaction_step_mesh(sysm, st, 0.1, T_K=(350.0, 500.0))


def test_plain_mechanism_is_unchanged_by_the_new_T_K_argument():
    sysm = _rxn_system(isomer_mechanism())                       # no applicability
    st = MeshState(np.array([[1.0, 0.0], [1.0, 0.0]]))
    a, _ = reaction_step_mesh(sysm, st, 0.1)                     # T_K=None, old behaviour
    b, _ = reaction_step_mesh(sysm, st, 0.1, T_K=350.0)          # supplied T is simply ignored (no window)
    np.testing.assert_array_equal(a.n, b.n)
