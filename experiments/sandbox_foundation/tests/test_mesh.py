"""Oriented-face chain mesh: red/green tests.  Ooh yeah, can do!  SYNTHETIC / idealized throughout; a finite
numerical check is NOT a universal proof.

The reference for pure diffusion is scipy's matrix exponential of a Laplacian built from B_space, g and V -- NOT
the stepper -- so agreement is evidence, not self-consistency."""
import math

import numpy as np
import pytest
from scipy.linalg import expm

from experiments.sandbox_foundation.fixtures import isomer_mechanism, tracer_system
from experiments.sandbox_foundation.mesh import (
    MAX_CELLS, MAX_DENSE_BYTES, DuplicateFaceError, Face, FluxEvent, Mesh, MeshState, MeshSystem, MissingFaceError,
    ResourceBudgetError, TopologyError, _preflight_dense, audit_mesh, chain_mesh, coupled_rhs, interface_report,
    reaction_step_mesh, run_mesh, transition_residual, transport_step_mesh)
from experiments.sandbox_foundation.twocell import (
    InvalidParameterError, Ledger, Mechanism, NegativeAmountError, ReactionRate, SandboxError,
    SpeciesBoundary, State, TimestepError, transport_step)

VOL = (1.0e-6, 2.0e-6, 1.5e-6)      # m^3
AREA = (1.0e-4, 2.0e-4)             # m^2, 2 faces
DIST = (1.0e-2, 1.5e-2)             # m
D = (1.0e-5, 3.0e-5)                # m^2/s  -> g/V ~ O(0.1/s)
N0 = np.array([[4.0, 1.0], [0.0, 2.0], [0.5, 0.0]])


def sys3(boundaries=None, mech=None, species=("A", "B"), diff=D):
    return MeshSystem(species, diff, chain_mesh(VOL, AREA, DIST), boundaries, mech)


def st3(n=N0):
    return MeshState(n)


# ------------------------------------------------------------------------------------------------ incidence
def test_every_face_column_of_B_space_sums_to_zero():
    mesh = chain_mesh(VOL, AREA, DIST)
    B = mesh.B_space
    assert B.shape == (3, 2)
    np.testing.assert_array_equal(np.ones(3) @ B, np.zeros(2))   # ones^T @ B_space == 0, EXACTLY
    np.testing.assert_array_equal(mesh.column_sums(), np.zeros(2))
    np.testing.assert_array_equal(B, [[-1, 0], [1, -1], [0, 1]])
    assert not B.flags.writeable
    # also true for a random-orientation, non-chain graph (it is a structural property, not a chain accident)
    g = Mesh((1.0,) * 4, (Face(0, 1, 1, 1), Face(2, 1, 1, 1), Face(2, 3, 1, 1), Face(3, 0, 1, 1)), "graph")
    np.testing.assert_array_equal(np.ones(4) @ g.B_space, np.zeros(4))


# ------------------------------------------------------------------------------------------------ 1 closed
def test_closed_system_conserves_global_inventory_over_multistep_run():
    s = sys3()
    s0 = st3()
    res = run_mesh(s, s0, 4.0, 400)
    assert s.transport_dt_max() > 4.0 / 400
    tot0, tot1 = s0.n.sum(axis=0), res.state.n.sum(axis=0)
    assert np.max(np.abs(tot1 - tot0)) < 1e-12
    assert audit_mesh(s, s0, res.state, res.ledger)["inventory_residual"] < 1e-12
    assert res.state.n[2, 1] > 0.3 and res.state.n[1, 0] > 0.3        # matter actually moved (not vacuous)
    assert np.all(res.state.n >= 0)


# ------------------------------------------------------------------------------------------------ 2 open
def test_open_system_inventory_change_equals_recorded_external_exchange_exactly():
    bnd = (SpeciesBoundary("prescribed_flow", (0.02, 0.0)), SpeciesBoundary(),
           SpeciesBoundary("prescribed_flow", (-0.01, 0.005)))
    s = sys3(bnd)
    s0 = st3()
    res = run_mesh(s, s0, 4.0, 400)
    a = audit_mesh(s, s0, res.state, res.ledger)
    ext = a["external_amount_mol"]
    # independent expectation: (net flow) * dt * n_steps
    expect = np.array([0.02 - 0.01, 0.005]) * 4.0
    np.testing.assert_allclose(ext, expect, rtol=0, atol=1e-12)
    dn = res.state.n.sum(axis=0) - s0.n.sum(axis=0)
    assert np.max(np.abs(dn - ext)) < 1e-12
    assert a["inventory_residual"] < 1e-12
    assert np.max(np.abs(ext)) > 0.0


# ------------------------------------------------------------------------------------------------ 3 ledger
def test_face_events_match_accepted_transition_and_interface_residual_is_exactly_zero():
    s = sys3((SpeciesBoundary("prescribed_flow", (0.01, 0.0)), SpeciesBoundary(), SpeciesBoundary()))
    s0 = st3()
    led, ev = Ledger(), []
    s1, rep = transport_step_mesh(s, s0, 0.05, ledger=led, events=ev)
    assert not rep.substepped
    # per-cell, per-species: recorded entries == actual accepted transition (state path differs from ledger path)
    assert transition_residual(s, s0, s1, led) < 1e-15
    # multi-step too
    led2, ev2 = Ledger(), []
    r = run_mesh(s, s0, 2.0, 200, ledger=led2, events=ev2)
    assert transition_residual(s, s0, r.state, led2) < 1e-13
    # interface residual: sum of the two sides is EXACTLY 0, per face / quantity / step
    rep2 = interface_report(ev2, s, strict=True)
    assert rep2["interface_residual"] == 0.0 and not rep2["missing"] and not rep2["duplicated"]
    assert len(ev2) == 200 * 2 * 2 * 2          # steps x faces x sides x species
    assert any(e.amount != 0.0 for e in ev2)
    # event orientation is the B_space entry; opposite signs on the two sides of every face
    B = s.mesh.B_space
    for e in ev2:
        assert isinstance(e, FluxEvent) and B[e.cell, e.face] == e.orientation
        assert e.constitutive_model and e.timestep == pytest.approx(0.01)
    by = {}
    for e in ev2:
        by.setdefault((e.step, e.face, e.quantity), []).append(e)
    for evs in by.values():
        assert len(evs) == 2 and evs[0].amount == -evs[1].amount and evs[0].orientation == -evs[1].orientation
    # ledger-level too
    assert max(abs(math.fsum(e.amount for e in led2.filter(kind="INTERFACE", cell=None).entries
                             if (e.step, e.note, e.quantity) == k))
               for k in {(e.step, e.note, e.quantity) for e in led2.filter(kind="INTERFACE").entries}) == 0.0


def test_orientation_is_a_labelling_choice_not_physics():
    flipped = Mesh(VOL, (Face(1, 0, AREA[0], DIST[0]), Face(2, 1, AREA[1], DIST[1])), "chain")
    a = run_mesh(sys3(), st3(), 2.0, 200).state.n
    b = run_mesh(MeshSystem(("A", "B"), D, flipped), st3(), 2.0, 200).state.n
    assert np.max(np.abs(a - b)) < 1e-14
    np.testing.assert_array_equal(flipped.B_space, -chain_mesh(VOL, AREA, DIST).B_space)


# ------------------------------------------------------------------------------------------------ 4 refusals
def test_missing_face_is_detected_in_topology():
    with pytest.raises(MissingFaceError):
        Mesh(VOL, (Face(0, 1, AREA[0], DIST[0]),), "chain")                    # 2-1 face absent
    with pytest.raises(MissingFaceError):
        Mesh(VOL, (Face(0, 1, 1, 1),), "graph")                                # cell 2 disconnected
    with pytest.raises(TopologyError):                                         # typed, bounded
        Mesh(VOL, (), "chain")


def test_duplicated_face_is_detected_in_topology():
    f = Face(0, 1, AREA[0], DIST[0])
    with pytest.raises(DuplicateFaceError):
        Mesh(VOL, (f, f, Face(1, 2, AREA[1], DIST[1])), "chain")
    with pytest.raises(DuplicateFaceError):                                    # reversed orientation is the same pair
        Mesh(VOL, (f, Face(1, 0, 1, 1), Face(1, 2, 1, 1)), "chain")


def test_invalid_topology_negative_area_and_bounds_are_refused_typed():
    with pytest.raises(TopologyError):
        Mesh(VOL, (Face(0, 0, 1, 1), Face(0, 1, 1, 1), Face(1, 2, 1, 1)), "chain")         # self-loop
    with pytest.raises(TopologyError):
        Mesh(VOL, (Face(0, 1, 1, 1), Face(1, 7, 1, 1)), "graph")                           # index out of range
    with pytest.raises(TopologyError):
        Mesh(VOL, (Face(0, 1, 1, 1), Face(1, 2, 1, 1), Face(0, 2, 1, 1)), "chain")         # non-adjacent in a chain
    with pytest.raises(TopologyError):
        Mesh(VOL, (Face(0, 1, 1, 1), Face(1, 2, 1, 1)), "torus")
    with pytest.raises(TopologyError):
        Face(0.5, 1, 1, 1)
    with pytest.raises(TopologyError):
        chain_mesh(VOL, AREA[:1], DIST)                                                    # wrong face count
    with pytest.raises(TopologyError):
        chain_mesh((1.0,) * (MAX_CELLS + 1), (1.0,) * MAX_CELLS, (1.0,) * MAX_CELLS)       # bounded refusal
    for bad in (-1.0e-4, 0.0, float("nan"), float("inf")):
        with pytest.raises(InvalidParameterError):
            Face(0, 1, bad, 1.0)
        with pytest.raises(InvalidParameterError):
            chain_mesh(VOL, (AREA[0], bad), DIST)
    with pytest.raises(InvalidParameterError):
        Face(0, 1, 1.0, -1.0)                                                              # negative distance
    with pytest.raises(InvalidParameterError):
        chain_mesh((1.0, -1.0, 1.0), AREA, DIST)                                           # negative volume
    with pytest.raises(InvalidParameterError):
        MeshSystem(("A", "B"), (1.0,), chain_mesh(VOL, AREA, DIST))                        # diffusivity count
    with pytest.raises(InvalidParameterError):
        MeshSystem(("A", "B"), (1.0, -1.0), chain_mesh(VOL, AREA, DIST))
    for exc in (MissingFaceError, DuplicateFaceError, TopologyError):
        assert issubclass(exc, SandboxError)


def test_overlarge_timestep_is_refused_then_substepped_only_with_flag():
    s = sys3()
    dtm = s.transport_dt_max()
    # independent hand value: min_i V_i / sum g incident, max over species
    g = np.array([[D[k] * AREA[f] / DIST[f] for k in range(2)] for f in range(2)])
    hand = min(VOL[0] / g[0].max(), VOL[1] / (g[0] + g[1]).max(), VOL[2] / g[1].max())
    assert dtm == pytest.approx(hand, rel=1e-14)
    with pytest.raises(TimestepError):
        transport_step_mesh(s, st3(), dtm * 1.01)
    with pytest.raises(TimestepError):
        run_mesh(s, st3(), dtm * 1.5, 1)
    s1, rep = transport_step_mesh(s, st3(), dtm * 3.0, policy="substep")
    assert rep.substepped and rep.substeps >= 3 and np.all(s1.n >= 0)
    with pytest.raises(InvalidParameterError):
        transport_step_mesh(s, st3(), dtm * 2, policy="yolo")


def test_overlarge_outflow_is_refused_not_clamped():
    s = sys3((SpeciesBoundary("prescribed_flow", (-1.0e3, 0.0)), SpeciesBoundary(), SpeciesBoundary()))
    with pytest.raises(NegativeAmountError):
        transport_step_mesh(s, st3(), 0.01)
    with pytest.raises(NegativeAmountError):
        MeshState(np.array([[-1.0, 0.0]]))


def test_dropped_or_duplicated_face_event_is_detected_in_the_event_log():
    s = sys3()
    ev = []
    transport_step_mesh(s, st3(), 0.05, events=ev)
    assert interface_report(ev, s)["interface_residual"] == 0.0
    dropped = ev[:3] + ev[4:]                                           # one side of one face lost
    rep = interface_report(dropped, s)
    assert len(rep["missing"]) == 1 and not rep["duplicated"]
    with pytest.raises(MissingFaceError):
        interface_report(dropped, s, strict=True)
    dup = ev + [ev[2]]                                                  # one event recorded twice
    rep = interface_report(dup, s)
    assert len(rep["duplicated"]) == 1 and not rep["missing"]
    with pytest.raises(DuplicateFaceError):
        interface_report(dup, s, strict=True)
    gone = [e for e in ev if e.face != 1]                               # a whole face never reported
    assert len(interface_report(gone, s)["missing"]) == 2               # 2 species
    wrongside = [ev[0], ev[1], FluxEvent(**{**ev[2].__dict__, "cell": ev[0].cell})] + ev[3:]
    assert interface_report(wrongside, s)["duplicated"]                 # same cell twice != two distinct sides


# ------------------------------------------------------------------------------------------------ positivity
def test_positivity_and_maximum_principle_at_the_bound():
    s = sys3()
    dtm = s.transport_dt_max()
    n = N0.copy()
    st = st3(n)
    c0 = st.concentration(s)
    lo, hi = c0.min(axis=0), c0.max(axis=0)
    for k in range(300):
        st, rep = transport_step_mesh(s, st, dtm, step=k)       # exactly AT the bound: admitted
        assert not rep.substepped
        c = st.concentration(s)
        assert np.all(st.n >= 0)
        assert np.all(c >= lo - 1e-15) and np.all(c <= hi + 1e-15)   # discrete maximum principle


# ------------------------------------------------------------------------------------------------ 5 expm
def diffusion_laplacian(mesh, g_s):
    """L = B diag(g) B^T V^-1 so that dn/dt = -L n  (built ONLY from B_space, g and V)."""
    B = mesh.B_space
    return B @ np.diag(g_s) @ B.T @ np.diag(1.0 / np.asarray(mesh.volumes_m3))


def expm_reference(system, n0, t):
    out = np.empty_like(n0)
    for s in range(n0.shape[1]):
        out[:, s] = expm(-diffusion_laplacian(system.mesh, system.g[:, s]) * t) @ n0[:, s]
    return out


def test_three_cell_diffusion_matches_matrix_exponential():
    s = sys3()
    t = 10.0
    ref = expm_reference(s, N0, t)
    # B_space is also cross-checked against an independently hand-built incidence
    np.testing.assert_array_equal(s.mesh.B_space, np.array([[-1.0, 0.0], [1.0, -1.0], [0.0, 1.0]]))
    errs = {}
    for nsteps in (2000, 4000, 8000, 16000):
        errs[nsteps] = np.max(np.abs(run_mesh(s, st3(), t, nsteps).state.n - ref))
    print("\nMAX ABS DISCREPANCY vs expm(-L t) @ n0, t=10 s:", {k: f"{v:.3e}" for k, v in errs.items()})
    # first-order explicit Euler: error halves as dt halves (observed order ~1), and is small in absolute terms
    ratios = [errs[a] / errs[b] for a, b in ((2000, 4000), (4000, 8000), (8000, 16000))]
    assert all(1.8 < r < 2.2 for r in ratios), ratios
    assert errs[16000] < 5e-5
    # the reference itself is nontrivial: mass moved and the closed total is the expm invariant
    assert np.max(np.abs(ref - N0)) > 0.3
    np.testing.assert_allclose(ref.sum(axis=0), N0.sum(axis=0), rtol=0, atol=1e-13)


# ------------------------------------------------------------------------------------------------ 6 two-cell reduction
@pytest.mark.parametrize("boundaries", [None, (SpeciesBoundary("prescribed_flow", (0.3,)),
                                               SpeciesBoundary("prescribed_flow", (-0.1,)))])
def test_two_cell_reduction_reproduces_twocell_transport_step(boundaries):
    sysm = tracer_system(boundaries=boundaries)
    msys = MeshSystem.from_two_cell(sysm)
    assert msys.mesh.n_cells == 2 and msys.mesh.n_faces == 1
    s_tc = State(np.array([[4.0], [0.5]]), np.array([1.0, 1.0]))
    s_ms = MeshState(np.array([[4.0], [0.5]]))
    assert msys.transport_dt_max() == sysm.transport_dt_max()
    worst = 0.0
    led_tc, led_ms = Ledger(), Ledger()
    for k in range(50):
        s_tc, _ = transport_step(sysm, s_tc, 0.05, ledger=led_tc, step=k)
        s_ms, _ = transport_step_mesh(msys, s_ms, 0.05, ledger=led_ms, step=k)
        worst = max(worst, float(np.max(np.abs(s_tc.n - s_ms.n))))
    print(f"\n2-CELL REDUCTION max |mesh - twocell| over 50 steps: {worst:.3e}")
    assert worst < 1e-14
    # ledgers agree entry by entry (interface + external), same cell, same amount to roundoff
    a = [(e.step, e.kind, e.cell, e.amount) for e in led_tc.entries]
    b = [(e.step, e.kind, e.cell, e.amount) for e in led_ms.entries]
    assert len(a) == len(b)
    assert max(abs(x[3] - y[3]) for x, y in zip(sorted(a), sorted(b))) < 1e-14


def test_two_cell_over_bound_policy_matches_twocell_too():
    sysm = tracer_system()
    msys = MeshSystem.from_two_cell(sysm)
    with pytest.raises(TimestepError):
        transport_step(sysm, State(np.array([[4.0], [0.5]]), np.array([1.0, 1.0])), 10.0)
    with pytest.raises(TimestepError):
        transport_step_mesh(msys, MeshState(np.array([[4.0], [0.5]])), 10.0)


# ------------------------------------------------------------------------------------------------ coupled reaction
def reaction_system(kf=1.5, kr=0.5):
    return MeshSystem(("P", "Q"), D, chain_mesh(VOL, AREA, DIST), mechanism=isomer_mechanism(kf, kr))


def test_coupled_rhs_is_the_sum_of_its_three_terms_and_conserves_inventory_when_closed():
    s = reaction_system()
    n = N0
    rhs = coupled_rhs(s, n)
    V = np.asarray(VOL)[:, None]
    c = n / V
    react = np.array([V[i, 0] * s.mechanism.N @ s.mechanism.rate_vector(c[i]) for i in range(3)])
    diff = -np.array([diffusion_laplacian(s.mesh, s.g[:, k]) @ n[:, k] for k in range(2)]).T
    np.testing.assert_allclose(rhs, react + diff, rtol=1e-13, atol=1e-15)
    # element/charge inventory E @ sum_cells(dn/dt) == 0 (closed system)
    np.testing.assert_allclose(s.mechanism.E @ rhs.sum(axis=0), 0.0, atol=1e-13)
    assert np.max(np.abs(react)) > 0 and np.max(np.abs(diff)) > 0


def test_reaction_diffusion_conserves_elements_and_tracks_monolithic_expm_with_first_order_splitting_error():
    s = reaction_system()
    kf, kr = 1.5, 0.5
    # INDEPENDENT monolithic generator on n flattened cell-major (index cell*2 + species); P<->Q first order
    M = np.zeros((6, 6))
    for k in range(2):
        L = diffusion_laplacian(s.mesh, s.g[:, k])
        for i in range(3):
            for j in range(3):
                M[2 * i + k, 2 * j + k] -= L[i, j]
    for i in range(3):
        M[2 * i, 2 * i] -= kf
        M[2 * i, 2 * i + 1] += kr
        M[2 * i + 1, 2 * i + 1] -= kr
        M[2 * i + 1, 2 * i] += kf
    t = 1.0
    ref = (expm(M * t) @ N0.reshape(6)).reshape(3, 2)
    errs = []
    for nsteps in (50, 100, 200):
        led = Ledger()
        r = run_mesh(s, st3(), t, nsteps, ("transport", "reaction"), ledger=led)
        # element/charge inventory (rows of E) conserved across the coupled run, closed system
        E = s.mechanism.E
        assert np.max(np.abs(E @ (r.state.n.sum(axis=0) - N0.sum(axis=0)))) < 1e-9
        errs.append(float(np.max(np.abs(r.state.n - ref))))
    print("\nLIE-SPLIT reaction-diffusion vs monolithic expm (50,100,200 steps):", [f"{e:.3e}" for e in errs])
    assert errs[0] / errs[1] > 1.7 and errs[1] / errs[2] > 1.7       # first order in dt (MEASURED, not proved)
    assert errs[2] < 5e-3
    with pytest.raises(InvalidParameterError):
        reaction_step_mesh(sys3(), st3(), 0.1)                       # no mechanism => refused


# ======================================================================================================
# Round IV -- Wave D: matrix-free RHS + a bounded budget (D1), a non-chain graph verified against expm (D2),
# and multi-reaction conservative positivity (D3).
# ======================================================================================================
def _graph(cells, edges, vol=1.0, area=1.0, dist=1.0):
    faces = tuple(Face(a, b, area, dist) for a, b in edges)
    return Mesh((vol,) * cells, faces, "graph")


def test_RIV_D1_coupled_rhs_is_matrix_free_identical_and_budget_bounded():
    # equivalence to the explicit dense Kronecker form on a non-chain (cycle) graph, exactly
    msys = MeshSystem(("A", "B"), (0.1, 0.2), _graph(3, [(0, 1), (1, 2), (2, 0)]))
    n = np.array([[2.0, 0.0], [0.0, 1.0], [1.0, 0.5]])
    got = coupled_rhs(msys, n)
    B, S = msys.mesh.B_space, 2
    c = n / 1.0
    Jrows = np.array([c[f.tail] - c[f.head] for f in msys.mesh.faces])
    J = (msys.g * Jrows).reshape(-1)
    dense = (np.kron(B, np.eye(S)) @ J).reshape(3, S)
    np.testing.assert_array_equal(got, dense)                       # EXACT, not approximate
    # the preflight refuses a dense ask beyond the budget, before allocating
    huge = int(MAX_DENSE_BYTES // 8) + 1
    with pytest.raises(ResourceBudgetError):
        _preflight_dense((huge,))
    _preflight_dense((MAX_CELLS, 2))                                # a legal shape passes silently


def test_RIV_D2_cycle_graph_diffusion_matches_matrix_exponential():
    # unit-scale geometry so g = D (area/dist = 1) and dt_max = V/(2*max D) = 1/0.2 = 5 s is generous
    msys = MeshSystem(("A", "B"), (0.05, 0.1), _graph(3, [(0, 1), (1, 2), (2, 0)], vol=1.0, area=1.0, dist=1.0))
    assert np.allclose(np.ones(3) @ msys.mesh.B_space, 0.0)          # conservation, structural
    n0 = np.array([[3.0, 0.0], [0.0, 2.0], [1.0, 1.0]])
    t = 5.0
    ref = expm_reference(msys, n0, t)
    errs = {ns: np.max(np.abs(run_mesh(msys, MeshState(n0), t, ns).state.n - ref)) for ns in (2000, 4000, 8000)}
    ratios = [errs[a] / errs[b] for a, b in ((2000, 4000), (4000, 8000))]
    assert all(1.7 < r < 2.3 for r in ratios), (errs, ratios)       # first-order Euler convergence
    assert errs[8000] < 1e-3
    np.testing.assert_allclose(ref.sum(axis=0), n0.sum(axis=0), rtol=0, atol=1e-12)   # closed: total conserved
    assert np.max(np.abs(ref - n0)) > 0.2                           # the reference actually moved mass


def test_RIV_D2_fork_graph_diffusion_matches_matrix_exponential():
    # a star / fork: centre cell 0 joined to 1, 2, 3; unit-scale geometry (dt_max = 1/(3*0.1) = 3.33 s)
    msys = MeshSystem(("A",), (0.1,), _graph(4, [(0, 1), (0, 2), (0, 3)], vol=1.0, area=1.0, dist=1.0))
    n0 = np.array([[5.0], [0.0], [0.0], [0.0]])
    t = 4.0
    ref = expm_reference(msys, n0, t)
    got = run_mesh(msys, MeshState(n0), t, 8000).state.n
    assert np.max(np.abs(got - ref)) < 1e-3
    np.testing.assert_allclose(got.sum(), 5.0, rtol=0, atol=1e-9)   # conserved


def test_RIV_D2_graph_missing_duplicate_and_self_loop_faces_are_refused():
    with pytest.raises(MissingFaceError):
        _graph(4, [(0, 1), (1, 2)])                                 # cell 3 disconnected
    with pytest.raises(DuplicateFaceError):
        _graph(3, [(0, 1), (1, 0), (1, 2)])                         # 0-1 twice (either orientation)
    with pytest.raises(TopologyError):
        _graph(3, [(0, 0), (1, 2)])                                 # self-loop


def _two_reaction_mech():
    # r1: A + B -> C   r2: A + D -> E   (shared limiting reactant A); elements X,Y,Z
    reactant = np.array([[1, 1], [1, 0], [0, 0], [0, 1], [0, 0]], float)
    product = np.array([[0, 0], [0, 0], [1, 0], [0, 0], [0, 1]], float)
    E = np.array([[1, 0, 1, 0, 1], [0, 1, 1, 0, 0], [0, 0, 0, 1, 1]], float)
    return Mechanism(("A", "B", "C", "D", "E"), reactant, product, ("X", "Y", "Z"), E,
                     (ReactionRate(1.0e3, None, False), ReactionRate(1.0e3, None, False)))


def test_RIV_D3_two_reaction_competing_limiting_species_conserves_exactly():
    mech = _two_reaction_mech()
    msys = MeshSystem(mech.species, (0.0,) * 5, chain_mesh([1.0, 1.0], [1.0], [1.0]), mechanism=mech)
    # A is the scarce shared reactant; B, D abundant.  Both cells react.
    n0 = np.array([[1.0, 10.0, 0.0, 10.0, 0.0], [1.0, 10.0, 0.0, 10.0, 0.0]])
    st = MeshState(n0)
    tot0 = mech.E @ n0.sum(axis=0)
    any_clamped = False
    for k in range(3):
        st, rep = reaction_step_mesh(msys, st, 50.0, step=k)
        any_clamped = any_clamped or rep.clamped
        assert rep.clamp_residual < 1e-12                          # conservative backtrack: no leak beyond roundoff
        np.testing.assert_allclose(mech.E @ st.n.sum(axis=0), tot0, rtol=0, atol=1e-9)   # inventory conserved
    assert any_clamped                                             # the depletion step DID exercise the R>1 clamp
    assert np.all(st.n >= 0.0)                                     # positivity preserved
    assert np.all(st.n[:, 0] == 0.0)                              # the shared limiting reactant A lands at 0


# ======================================================================================================
# Wave E follow-up (dalembert KILL 1): the passivity certificate must NOT fail OPEN on a NaN witness.
# A cell emptying into an underflowed flux forms Delta(mu).J = inf*0 = NaN; the diagnostic must report the
# honest signed -inf, and the certificate must fail CLOSED on the raw indeterminate -- never let np.max swallow it.
# ======================================================================================================
def test_WaveE_face_dissipation_is_signed_minus_inf_never_nan_when_a_cell_empties():
    from experiments.sandbox_foundation.mesh import face_dissipation
    mesh = chain_mesh((1.0e-6, 1.0e-6), [1.0e-4], [1.0e-2])
    g = np.array([[1.0e-8]])
    # cell 0 exactly empty, cell 1 a denormal trace -> the Fick flux underflows to signed -0.0 while Delta(mu)
    # overflows to +inf, so the raw product is 0*inf = NaN.  The honest ideal-dilute limit is a signed -inf
    # (dissipation diverging, never injection), because Delta(mu) and J carry opposite signs at every face.
    c = np.array([[0.0], [1.0e-317]])
    w = face_dissipation(mesh, g, c, 298.15)
    assert not np.isnan(w).any()                                   # the module's "NEVER a NaN" docstring, made true
    assert w[0, 0] == -np.inf                                      # pinned to the signed dilute-dissipation limit


def test_WaveE_assert_passive_refuses_a_nan_witness_face_in_a_multiface_chain():
    from experiments.sandbox_foundation.mesh import assert_passive
    mesh = chain_mesh((1.0, 1.0, 1.0, 1.0), [1.0e-4, 1.0e-4, 1.0e-4], [1.0e-2, 1.0e-2, 1.0e-2])
    g = np.full((3, 1), 1.0e-8)
    # face 2 (cells 2,3 = 0, 1e-317) forms a 0*inf = NaN witness; faces 0,1 are finite/-inf.  np.max over the NaN
    # returns False on '> tol', so the OLD guard silently PASSED -- one NaN face blinding the whole certificate.
    c = np.array([[5.0], [1.0], [0.0], [1.0e-317]])
    with pytest.raises(InvalidParameterError):
        assert_passive(mesh, g, c, 298.15)


def test_WaveE_assert_passive_admits_the_legitimate_signed_minus_inf_dilute_limit():
    from experiments.sandbox_foundation.mesh import assert_passive, face_dissipation
    mesh = chain_mesh((1.0e-6, 1.0e-6), [1.0e-4], [1.0e-2])
    g = np.array([[1.0e-8]])
    # cell 0 empty, cell 1 at a NORMAL concentration -> J stays finite (g*c_head), so Delta(mu).J is a CLEAN -inf,
    # not an inf*0 indeterminate.  A genuine dissipation limit must PASS: fail-closed is for NaN, not for -inf.
    c = np.array([[0.0], [1.0]])
    assert face_dissipation(mesh, g, c, 298.15)[0, 0] == -np.inf
    assert_passive(mesh, g, c, 298.15)                             # admitted -- a -inf is dissipative, not unverified
