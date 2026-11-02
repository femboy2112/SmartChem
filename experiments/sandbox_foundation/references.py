"""INDEPENDENT reference solutions (closed forms + scipy monolithic solves).  Deliberately imports NOTHING from
twocell.py, so agreement between the two is evidence, not self-consistency.  All idealized/synthetic."""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm


def two_node_relaxation(x_A0, x_B0, cap_A, cap_B, coupling, t):
    """Closed form for dX_A/dt = coupling*(x_B - x_A) etc. with x_i = X_i/cap_i (X = amount or energy).
    Returns (x_A(t), x_B(t)).  Used for tracer (cap=V, coupling=g) and heat (cap=C, coupling=G)."""
    x_eq = (cap_A * x_A0 + cap_B * x_B0) / (cap_A + cap_B)
    rate = coupling * (1.0 / cap_A + 1.0 / cap_B)
    d = (x_A0 - x_B0) * np.exp(-rate * t)
    return x_eq + cap_B * d / (cap_A + cap_B), x_eq - cap_A * d / (cap_A + cap_B)


def two_node_solve_ivp(x_A0, x_B0, cap_A, cap_B, coupling, t):
    """Second independent method: DOP853, tight tolerance, on the amount/energy form."""
    def f(_t, y):
        q = coupling * (y[1] / cap_B - y[0] / cap_A)
        return [q, -q]
    sol = solve_ivp(f, (0, t), [x_A0 * cap_A, x_B0 * cap_B], method="DOP853", rtol=1e-12, atol=1e-14)
    return sol.y[0, -1] / cap_A, sol.y[1, -1] / cap_B


def isomerization_analytic(nP0, nQ0, kf, kr, t):
    """Closed form for the closed, well-mixed linear P <-> Q:  dP/dt = -kf P + kr Q."""
    tot = nP0 + nQ0
    P_eq = kr * tot / (kf + kr)
    P = P_eq + (nP0 - P_eq) * np.exp(-(kf + kr) * t)
    return P, tot - P


def bimolecular_analytic(a0, b0, k, V, t):
    """Closed form for irreversible A + B -> C, rate = k c_A c_B, unequal initial amounts (a0 != b0), cell volume V.
    Returns the extent xi(t) in mol."""
    ca, cb = a0 / V, b0 / V
    e = np.exp((ca - cb) * k * t)
    x = ca * cb * (1.0 - e) / (cb - ca * e)  # concentration extent
    return x * V


def composite_linear_reference(V, g, kf, kr, n0, t_end, method="expm"):
    """Monolithic (un-split) solution of: two cells, species (P, Q, T), P<->Q first-order in BOTH cells, face
    transport of every species with coefficient g[s] (m^3/s).  n0 shape (2,3) mol.  Returns (2,3) at t_end."""
    V = np.asarray(V, float)
    g = np.asarray(g, float)
    Mx = np.zeros((6, 6))  # state ordering: [cell][species] -> idx = 3*cell + s
    for cell in (0, 1):
        o = 1 - cell
        for s in range(3):
            Mx[3 * cell + s, 3 * cell + s] -= g[s] / V[cell]
            Mx[3 * cell + s, 3 * o + s] += g[s] / V[o]
        Mx[3 * cell + 0, 3 * cell + 0] -= kf
        Mx[3 * cell + 0, 3 * cell + 1] += kr
        Mx[3 * cell + 1, 3 * cell + 1] -= kr
        Mx[3 * cell + 1, 3 * cell + 0] += kf
    y0 = np.asarray(n0, float).reshape(6)
    if method == "expm":
        return (expm(Mx * t_end) @ y0).reshape(2, 3)
    sol = solve_ivp(lambda _t, y: Mx @ y, (0, t_end), y0, method="DOP853", rtol=1e-13, atol=1e-15)
    return sol.y[:, -1].reshape(2, 3)
